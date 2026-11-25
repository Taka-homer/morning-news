# 朝のニュース便

Yahoo!ニュース・トピックス（主要・経済・IT）と建築系専門メディアのRSSからニュースの見出しを取得し、
LINE Messaging API の Push API で自分のLINEへ1通にまとめて送るプログラムです。

- 毎朝 GitHub Actions で自動配信（手元PCからの手動実行も可能）
- 送信先は自分1名のみ
- 有料サービスは使用しません（LINE公式アカウントの無料プラン＋無料のRSS＋GitHub Actionsの無料枠）

## ファイル構成

| ファイル | 内容 |
|---|---|
| `morning_news.py` | ニュースを取得して送信するプログラム（メイン） |
| `news.py` | RSSからニュースを取得する処理（カテゴリ・件数の設定もここ） |
| `line_push.py` | LINEへ送信する共通処理 |
| `send_test.py` | テストメッセージを1通送るプログラム |
| `.github/workflows/morning-news.yml` | GitHub Actions で毎朝自動実行する設定 |
| `requirements.txt` | 必要なPythonライブラリ |
| `.env.example` | 設定ファイルのひな形（値は空） |
| `.env` | 実際の認証情報（自分で作成。Gitに含めない） |
| `.gitignore` | `.env` などをGit管理から除外 |

## 事前準備（LINE Developers）

1. [LINE Developers コンソール](https://developers.line.biz/console/) で Messaging API チャネルを用意する
2. **チャネルアクセストークン（長期）**：「Messaging API設定」タブの一番下で発行
3. **自分のユーザーID**：「チャネル基本設定」タブの下部「あなたのユーザーID」（`U` から始まる33文字）
4. 「Messaging API設定」タブのQRコードから、**自分のLINEでこの公式アカウントを友だち追加**しておく
   （友だち追加していない／ブロックしていると、API受付は成功してもスマホには届きません）

## 環境構築（Windows PowerShell）

プロジェクトのフォルダで PowerShell を開いて実行します。

```powershell
# 1. 仮想環境を作成
python -m venv .venv

# 2. 仮想環境を有効化
.\.venv\Scripts\Activate.ps1
```

「スクリプトの実行が無効」というエラーが出た場合は、次を実行してから再度有効化してください
（この PowerShell ウィンドウの間だけ有効な設定です）。

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

行頭に `(.venv)` と表示されたら有効化できています。続けてライブラリをインストールします。

```powershell
# 3. ライブラリをインストール
python -m pip install -r requirements.txt
```

## .env の作成

```powershell
# ひな形をコピーして .env を作成
Copy-Item .env.example .env

# メモ帳で開いて編集
notepad .env
```

メモ帳で `=` の後ろに値を入力して保存します（引用符やスペースは不要）。

```
LINE_CHANNEL_ACCESS_TOKEN=ここに発行したトークン
LINE_USER_ID=Uから始まるユーザーID
```

注意：
- `.env` は他人に見せない・送らない・Gitにコミットしない（`.gitignore` で除外済み）
- このフォルダは OneDrive 配下のため、`.env` も OneDrive に同期されます。気になる場合は共有設定に注意してください
- トークンが漏れた疑いがあるときは、LINE Developers コンソールで再発行してください

## 実行

### ニュースを送る

```powershell
# まず送信せずに本文を確認（メッセージ数を消費しない）
python morning_news.py --dry-run

# 問題なければ送信
python morning_news.py
```

### テストメッセージを送る

```powershell
python send_test.py
```

（仮想環境を有効化していない場合は `python` の代わりに `.\.venv\Scripts\python.exe` を使ってください）

## 毎朝の自動配信（GitHub Actions）

`.github/workflows/morning-news.yml` により、毎日 **6:30（日本時間）** に GitHub のサーバーで `morning_news.py` が実行されます。
PCの電源が切れていても届きます。

### 初回セットアップ

1. GitHub で **Private（非公開）** リポジトリを作成する（README などは追加しない）
   - Private にする理由：実行ログに送信本文が残るため。また Public だと 60日間更新がないと定期実行が自動停止されます
2. 手元のフォルダを GitHub に push する（PowerShell）

   ```powershell
   git init
   git add .
   git status        # ここに .env が無いことを必ず確認
   git commit -m "朝のニュース便を追加"
   git branch -M main
   git remote add origin https://github.com/<ユーザー名>/<リポジトリ名>.git
   git push -u origin main
   ```

3. リポジトリの **Settings → Secrets and variables → Actions → New repository secret** で次の2つを登録する
   - `LINE_CHANNEL_ACCESS_TOKEN`
   - `LINE_USER_ID`
4. **Actions** タブ →「朝のニュース便」→ **Run workflow** で手動実行し、スマホに届くか確認する

### 配信時刻を変える

`morning-news.yml` の `cron` を編集して push します。時刻は **UTC（日本時間 − 9時間）** で書きます。

| 日本時間 | cron |
|---|---|
| 6:00 | `"0 21 * * *"` |
| 6:30 | `"30 21 * * *"` |
| 7:30 | `"30 22 * * *"` |

- GitHub の混雑により、起動は数分〜数十分遅れることがあります（まれに大きく遅れたり、実行されないこともあります）
- 毎時0分ちょうどは混雑しやすいため、少しずらすのがおすすめです

### 失敗したとき

- 送信やニュース取得（全カテゴリ）に失敗すると、そのワークフロー実行は「失敗（赤い×）」になり、GitHub からメールで通知されます
- Actions タブで該当の実行を開くと、エラー内容（HTTPステータスや確認ポイント）を確認できます。自動再送はしません
- Secrets の値はログに `***` と伏せて表示され、プログラム自体も認証情報を表示しません

### 料金

Private リポジトリでも GitHub Actions は毎月 2,000 分まで無料です。この処理は1回1分未満なので、毎日実行しても無料枠に収まります。

## 届くメッセージの例

```
朝のニュース便 10/24（土）

■主要
・能動サイバー防御要請 政府側慎重
https://news.yahoo.co.jp/pickup/6599979?source=rss
・（以下、主要5件・経済3件・IT3件）

■建築（国内）
・LIXIL、洗面化粧台や外装材など一部値上げ　27年4月受注分から（新建ハウジング）
https://www.s-housing.jp/archives/436000
・（以下、国内5件）

■建築（海外）
・Studio Gang completes women's leadership campus in Wisconsin（Dezeen）
https://www.dezeen.com/2026/11/24/studio-gang-wisconsin-womens-leadership-center/
・（以下、海外5件）

出典：Yahoo!ニュース、建築は国内外の各専門メディア・Googleニュース
```

## ニュースのカテゴリ・件数を変える

`news.py` の `FEEDS` を編集します。

```python
FEEDS = [
    ("主要", "https://news.yahoo.co.jp/rss/topics/top-picks.xml", 5),
    ("経済", "https://news.yahoo.co.jp/rss/topics/business.xml", 3),
    ("IT", "https://news.yahoo.co.jp/rss/topics/it.xml", 3),
]
```

ほかに使えるカテゴリ：`domestic`（国内）、`world`（国際）、`science`（科学）など。
URLの `top-picks` の部分を置き換えます。

- 48時間より古い記事は載せません（`MAX_AGE_HOURS`）
- 同じ記事が複数のカテゴリにある場合は、先のカテゴリにだけ載せます
- RSSはYahoo!ニュースの利用規約の範囲（個人利用）で使ってください。取得は実行1回につき各カテゴリ1回だけです

### 建築カテゴリ

建築は `news.py` の `ARCH_CATEGORIES` で設定し、国内・海外を各5件（`limit`）届けます。

| カテゴリ | 専門メディア（`feeds`） |
|---|---|
| 建築（国内） | 新建ハウジング・建設通信新聞・日刊建設工業新聞 |
| 建築（海外） | ArchDaily・Dezeen・designboom・Construction Dive（英語の見出しのまま届きます） |

各カテゴリとも、次の順に集めます。

1. 専門メディアの48時間以内の記事。1媒体2件まで（`ARCH_MAX_PER_SOURCE`）
2. 足りなければ7日前まで（`ARCH_BACKFILL_DAYS`）さかのぼる。古い記事には「11/20の記事」のように日付が付きます
3. それでも足りなければ、Googleニュースで建設DX・人手不足などの注目技術・業界課題の記事を探す（`topic`）

各見出しの後ろには媒体名が付きます。取得できなかった媒体は、画面（GitHub Actions のログ）に `[警告]` と表示されます。

## 結果の見方：「API受付成功」と「スマホでの受信」は別物です

| 段階 | 意味 | 確認方法 |
|---|---|---|
| ① API受付成功 | LINEのサーバーが送信リクエストを受け付けた | 画面に `[API受付成功]`（HTTP 200）と表示される |
| ② スマホで受信 | 実際に自分のLINEアプリにメッセージが届いた | スマホのLINEアプリで公式アカウントのトークを開いて確認 |

①が成功しても②が保証されるわけではありません。①成功なのに届かない場合は、次を確認してください。

- 公式アカウントを友だち追加しているか／ブロックしていないか
- `LINE_USER_ID` が「自分のユーザーID」か（別チャネルや別人のIDではないか）
- スマホのLINEの通知設定

## エラー時の動作

- **設定値が不足**：送信せずに、不足している項目名（例：`LINE_USER_ID`）を表示して終了します
- **ニュースの取得失敗**：失敗したカテゴリは画面に `[警告]` を表示し、本文では「（取得できませんでした）」として残りを送ります。全カテゴリが0件のときは送信しません
- **本文が長すぎる**：LINEの上限（5000文字）を超える場合は送信しません
- **タイムアウト**：接続5秒・応答20秒で打ち切ります。通信途中で切れた場合は届いている可能性もあるため、再実行前にスマホを確認してください
- **送信失敗**：自動再送はしません。HTTPステータス、確認ポイント、LINEからのエラー内容、リクエストIDを表示します

| HTTPステータス | 主な原因 |
|---|---|
| 400 | ユーザーIDの誤りなど、リクエスト内容が不正 |
| 401 | チャネルアクセストークンの誤り・失効 |
| 429 | 月間の無料メッセージ数の上限、またはレート制限 |
| 5xx | LINE側の一時的な障害 |

認証情報（トークン・ユーザーID）の値は画面に表示しません。

## 料金について

LINE公式アカウントの無料プラン（コミュニケーションプラン）には月ごとの無料メッセージ数の上限があり、
上限を超えると送信できなくなります（自動で課金されることはありません）。テスト送信も1通としてカウントされます。
