"""朝のニュース便：LINEへテストメッセージを1通送信する（手動実行用）。"""

import sys

from line_push import send_text

MESSAGE_TEXT = "朝のニュース便：テスト配信です"


if __name__ == "__main__":
    sys.exit(send_text(MESSAGE_TEXT))
