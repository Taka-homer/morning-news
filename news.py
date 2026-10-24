"""Yahoo!ニュース・トピックスのRSSから見出しを取得する。"""

import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

import requests

# (表示名, RSSのURL, 載せる最大件数)
FEEDS = [
    ("主要", "https://news.yahoo.co.jp/rss/topics/top-picks.xml", 5),
    ("経済", "https://news.yahoo.co.jp/rss/topics/business.xml", 3),
    ("IT", "https://news.yahoo.co.jp/rss/topics/it.xml", 3),
]

# これより古い記事は載せない（更新が止まったフィードを見分けるため）
MAX_AGE_HOURS = 48

# (接続タイムアウト秒, 応答待ちタイムアウト秒)
TIMEOUT = (5, 10)
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

    return results
