"""LINE Messaging API の Push API で自分1名へテキストを送信する共通処理。

.env から LINE_CHANNEL_ACCESS_TOKEN と LINE_USER_ID を読み込む。
認証情報の値は画面に表示しない。失敗しても自動再送はしない。
"""

import os

import requests
from dotenv import load_dotenv

PUSH_API_URL = "https://api.line.me/v2/bot/message/push"
REQUIRED_KEYS = ("LINE_CHANNEL_ACCESS_TOKEN", "LINE_USER_ID")

# (接続タイムアウト秒, 応答待ちタイムアウト秒)
TIMEOUT = (5, 10)


def load_settings():
    """環境変数を読み込み、設定値と不足している項目名のリストを返す。"""
    load_dotenv()
    settings = {key: os.getenv(key, "").strip() for key in REQUIRED_KEYS}
    missing = [key for key, value in settings.items() if not value]
    return settings, missing


def send_push(token, user_id, text):
    """Push API を1回だけ呼び出し、レスポンスを返す。"""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }
    body = {
        "to": user_id,
        "messages": [{"type": "text", "text": text}],
    }
    return requests.post(PUSH_API_URL, headers=headers, json=body, timeout=TIMEOUT)


def explain_http_error(status):
    """主なHTTPステータスに対する確認ポイントを返す。"""
    hints = {
        400: "リクエスト内容が不正です。LINE_USER_ID が正しいか（U から始まる33文字）、本文が長すぎないかを確認してください。",
        401: "認証に失敗しました。LINE_CHANNEL_ACCESS_TOKEN が正しいか、再発行で無効になっていないか確認してください。",
        403: "権限がありません。チャネルの種類・設定を確認してください。",
        429: "送信上限またはレート制限に達しました。今月の無料メッセージ数が上限に達していないか確認してください。",
    }
    if status in hints:
        return hints[status]
    if status >= 500:
        return "LINE側のサーバーエラーです。時間をおいて手動で再実行してください。"
    return "想定外のエラーです。下記のレスポンス内容を確認してください。"


def send_text(text):
    """設定を確認して text を送信し、結果を表示する。終了コード（成功0／失敗1）を返す。"""
    settings, missing = load_settings()
    if missing:
        print("[中止] 次の設定値が不足しているため、送信しませんでした:")
        for key in missing:
            print(f"  - {key}")
        print(".env ファイルにこれらの項目を入力してから再実行してください。")
        return 1

    user_id = settings["LINE_USER_ID"]
    if not (user_id.startswith("U") and len(user_id) == 33):
        print("[注意] LINE_USER_ID の形式が想定（U から始まる33文字）と異なります。送信は試みます。")

    print("LINEへメッセージを送信します...")
    try:
        response = send_push(settings["LINE_CHANNEL_ACCESS_TOKEN"], user_id, text)
    except requests.exceptions.Timeout:
        print("[失敗] LINEサーバーからの応答がタイムアウトしました。")
        print("  通信が途中で切れた場合、実際には届いている可能性があります。")
        print("  再実行する前に、スマホのLINEで受信していないか確認してください。")
        return 1
    except requests.exceptions.ConnectionError:
        print("[失敗] LINEサーバーに接続できませんでした。インターネット接続を確認してください。")
        return 1
    except requests.exceptions.RequestException as e:
        print(f"[失敗] 通信エラーが発生しました: {type(e).__name__}")
        return 1

    request_id = response.headers.get("X-Line-Request-Id", "(なし)")

    if response.status_code == 200:
        print("[API受付成功] LINEサーバーが送信リクエストを受け付けました。")
        print(f"  HTTPステータス: {response.status_code}")
        print(f"  リクエストID: {request_id}")
        print("  ※ これは「LINEが受け付けた」ことを示すものです。")
        print("    実際に届いたかは、スマホのLINEアプリでメッセージを確認してください。")
        return 0

    print("[失敗] LINEサーバーが送信リクエストを受け付けませんでした。（自動再送はしません）")
    print(f"  HTTPステータス: {response.status_code}")
    print(f"  リクエストID: {request_id}")
    print(f"  確認ポイント: {explain_http_error(response.status_code)}")
    # レスポンス本文はLINEからのエラー説明で、認証情報は含まれない
    print(f"  レスポンス内容: {response.text}")
    return 1
