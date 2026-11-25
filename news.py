"""Yahoo!ニュース・トピックスと建築系ニュースのRSSから見出しを取得する。"""

import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import quote

import requests

# (表示名, RSSのURL, 載せる最大件数)
FEEDS = [
    ("主要", "https://news.yahoo.co.jp/rss/topics/top-picks.xml", 5),
    ("経済", "https://news.yahoo.co.jp/rss/topics/business.xml", 3),
    ("IT", "https://news.yahoo.co.jp/rss/topics/it.xml", 3),
]

# これより古い記事は載せない（更新が止まったフィードを見分けるため）
MAX_AGE_HOURS = 48

# ----- 建築カテゴリ -----


def google_news_url(query, lang):
    """Googleニュース検索のRSSのURLを作る。lang は "ja" か "en"。"""
    locale = "&hl=ja&gl=JP&ceid=JP:ja" if lang == "ja" else "&hl=en-US&gl=US&ceid=US:en"
    return "https://news.google.com/rss/search?q=" + quote(query) + locale


# 建築カテゴリの一覧。各カテゴリの設定：
#   name   表示名
#   limit  載せる件数
#   feeds  専門メディア (媒体名, RSSのURL)
#   topic  専門メディアで足りないときに使う、注目技術・業界課題のGoogleニュース検索
ARCH_CATEGORIES = [
    {
        "name": "建築（国内）",
        "limit": 5,
        "feeds": [
            ("新建ハウジング", "https://www.s-housing.jp/feed"),
            ("建設通信新聞", "https://www.kensetsunews.com/feed"),
            ("日刊建設工業新聞", "https://www.decn.co.jp/?feed=rss2"),
        ],
        "topic": google_news_url(
            "(建設 OR 建築) (DX OR 人手不足 OR 新技術 OR 2024年問題) when:7d", "ja"
        ),
    },
    {
        "name": "建築（海外）",
        "limit": 5,
        "feeds": [
            ("ArchDaily", "https://feeds.feedburner.com/Archdaily"),
            ("Dezeen", "https://www.dezeen.com/architecture/feed/"),
            ("designboom", "https://www.designboom.com/architecture/feed/"),
            ("Construction Dive", "https://www.constructiondive.com/feeds/news/"),
        ],
        "topic": google_news_url(
            '(architecture OR "construction industry") (building OR "labor shortage" OR innovation)'
            " -stock -rating when:7d",
            "en",
        ),
    },
]
# 1媒体に偏らないよう、まずは1媒体あたりこの件数までにする
ARCH_MAX_PER_SOURCE = 2
# 48時間以内の記事で足りないときは、この日数までさかのぼる
ARCH_BACKFILL_DAYS = 7

# (接続タイムアウト秒, 応答待ちタイムアウト秒)
TIMEOUT = (5, 20)
USER_AGENT = "morning-news-bin/1.0 (personal use)"


def parse_pubdate(text):
    """RSSの日付文字列を datetime に変換する。読めなければ None。"""
    try:
        return parsedate_to_datetime(text)
    except (TypeError, ValueError):
        return None


def fetch_feed(url):
    """RSSを1回取得し、(記事リスト, エラーメッセージ) を返す。成功時のエラーは None。

    記事は {"title", "link", "published"} の辞書。自動再試行はしない。
    """
    try:
        response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT)
    except requests.exceptions.Timeout:
        return [], "タイムアウトしました"
    except requests.exceptions.ConnectionError:
        return [], "接続できませんでした"
    except requests.exceptions.RequestException as e:
        return [], f"通信エラー（{type(e).__name__}）"

    if response.status_code != 200:
        return [], f"HTTPステータス {response.status_code}"

    try:
        root = ET.fromstring(response.content)
    except ET.ParseError:
        return [], "RSSの形式を読み取れませんでした"

    articles = []
    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        if title and link:
            articles.append({
                "title": title,
                "link": link,
                "published": parse_pubdate(item.findtext("pubDate")),
            })
    return articles, None


def collect_news(now=None):
    """全フィードを取得し、[(表示名, 記事リスト, エラー)] を返す。

    古い記事を除き、同じ記事がほかのカテゴリに既に載っていれば重複させない。
    """
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=MAX_AGE_HOURS)
    seen_links = set()
    results = []

    for name, url, limit in FEEDS:
        articles, error = fetch_feed(url)
        picked = []
        for article in articles:
            published = article["published"]
            if published is not None and published < cutoff:
                continue
            if article["link"] in seen_links:
                continue
            seen_links.add(article["link"])
            picked.append(article)
            if len(picked) >= limit:
                break
        results.append((name, picked, error))

    for category in ARCH_CATEGORIES:
        results.append(collect_architecture(category, now, seen_links))
    return results


def collect_architecture(category, now, seen_links):
    """建築ニュースを category["limit"] 件集め、(表示名, 記事リスト, エラー) を返す。

    1. 専門メディアの48時間以内の記事（1媒体 ARCH_MAX_PER_SOURCE 件まで）
    2. 足りなければ専門メディアの記事を ARCH_BACKFILL_DAYS 日前までさかのぼる
    3. それでも足りなければ、Googleニュースで注目技術・業界課題の記事を探す
    48時間より古い記事には "note" に日付を入れる。
    """
    fresh_cutoff = now - timedelta(hours=MAX_AGE_HOURS)
    backfill_cutoff = now - timedelta(days=ARCH_BACKFILL_DAYS)
    oldest = datetime.min.replace(tzinfo=timezone.utc)
    errors = []

    limit = category["limit"]
    candidates = []
    for source, url in category["feeds"]:
        articles, error = fetch_feed(url)
        if error:
            errors.append(f"{source}：{error}")
            # ほかの媒体で埋まると本文には出ないため、ログにだけ残す
            print(f"[警告] {category['name']}：{source} を取得できませんでした（{error}）")
        for article in articles:
            article["source"] = source
            candidates.append(article)
    # 新しい順（日付が読めない記事は最後）
    candidates.sort(key=lambda a: a["published"] or oldest, reverse=True)

    picked = []
    per_source = {}

    def take(article):
        seen_links.add(article["link"])
        published = article["published"]
        if published is not None and published < fresh_cutoff:
            article["note"] = f"{published.astimezone(timezone(timedelta(hours=9))):%m/%d}の記事"
        picked.append(article)
        per_source[article["source"]] = per_source.get(article["source"], 0) + 1

    def fill(pool, cutoff, cap=None):
        for article in pool:
            if len(picked) >= limit:
                return
            published = article["published"]
            if published is not None and published < cutoff:
                continue
            if article["link"] in seen_links:
                continue
            if cap is not None and per_source.get(article["source"], 0) >= cap:
                continue
            take(article)

    fill(candidates, fresh_cutoff, cap=ARCH_MAX_PER_SOURCE)
    fill(candidates, fresh_cutoff)
    fill(candidates, backfill_cutoff, cap=ARCH_MAX_PER_SOURCE)
    fill(candidates, backfill_cutoff)

    if len(picked) < limit:
        topics, error = fetch_feed(category["topic"])
        if error:
            errors.append(f"Googleニュース：{error}")
        for article in topics:
            article["source"] = "Googleニュース"
        topics.sort(key=lambda a: a["published"] or oldest, reverse=True)
        fill(topics, backfill_cutoff)

    error = "、".join(errors) if errors and not picked else None
    return (category["name"], picked, error)
