"""朝のニュース便：ニュース見出しを取得し、自分のLINEへ1通送信する（手動実行用）。

使い方:
  python morning_news.py            # 取得して送信
  python morning_news.py --dry-run  # 取得して本文を表示するだけ（送信しない）
"""

import argparse
import sys
from datetime import datetime, timedelta, timezone

from line_push import send_text
from news import collect_news

JST = timezone(timedelta(hours=9))
WEEKDAYS = "月火水木金土日"

# LINEのテキストメッセージは最大5000文字
MAX_MESSAGE_LENGTH = 5000


def build_message(results, now):
    """取得結果からLINEに送る本文を組み立てる。"""
    lines = [f"朝のニュース便 {now:%m/%d}（{WEEKDAYS[now.weekday()]}）"]
    for name, articles, error in results:
        lines.append("")
        lines.append(f"■{name}")
        if error:
            lines.append("（取得できませんでした）")
        elif not articles:
            lines.append("（新しい記事はありません）")
        for article in articles:
            extras = [x for x in (article.get("source"), article.get("note")) if x]
            suffix = f"（{'・'.join(extras)}）" if extras else ""
            lines.append(f"・{article['title']}{suffix}")
            lines.append(article["link"])
    lines.append("")
    lines.append("出典：Yahoo!ニュース、建築は国内外の各専門メディア・Googleニュース")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="ニュース見出しを自分のLINEへ送信します。")
    parser.add_argument("--dry-run", action="store_true", help="送信せず、本文を表示するだけにする")
    args = parser.parse_args()

    print("ニュースを取得しています...")
    results = collect_news()

    for name, articles, error in results:
        if error:
            print(f"[警告] {name}：取得に失敗しました（{error}）")
        else:
            print(f"  {name}：{len(articles)}件")

    total = sum(len(articles) for _, articles, _ in results)
    if total == 0:
        print("[中止] 記事を1件も取得できなかったため、送信しませんでした。")
        return 1

    message = build_message(results, datetime.now(JST))
    if len(message) > MAX_MESSAGE_LENGTH:
        print(f"[中止] 本文が{len(message)}文字あり、LINEの上限（{MAX_MESSAGE_LENGTH}文字）を超えています。")
        print("  news.py の FEEDS で件数を減らしてください。")
        return 1

    print()
    print("----- 送信する本文 -----")
    print(message)
    print("------------------------")
    print()

    if args.dry_run:
        print("[確認のみ] --dry-run のため送信していません。")
        return 0

    return send_text(message)


if __name__ == "__main__":
    sys.exit(main())
