# CoreGeeks マイニングウォレット クローン (Asustor AS3102T 自立運用版)

本システムは、**`core-geeks.com`（およびそのAPIサーバー）が廃止・閉鎖された後も、Asustor AS3102T 上で完全自立して永続稼働するマイニングウォレット管理システム**です。

---

## 💡 特徴・実現されたこと

1. **過去履歴データの完全退避（アーカイブ完了）**:
   - `core-geeks.com` 稼働中のデータ（**510日分の日次マイニング集計**、**全4,215件の確定申告用取引明細**、**51,840件の5分刻み為替レート**）をすべてNAS上のローカルSQLiteデータベース（`data/wallet.db`）に救出・保存済みです。
   - 外部サイトが閉鎖されても、過去のマイニング履歴や確定申告データが消える心配はありません。

2. **Asustor AS3102T（メモリ2GB）に最適化**:
   - 外部ライブラリを一切使わず、**Python標準機能（`http.server` + `sqlite3`）のみ**でWebとAPIを同時に配信。
   - コンテナのメモリ消費量はわずか **約15MB〜25MB** で、AS3102TのCPU（Celeron N3050）や2GBメモリに一切負荷をかけません。

3. **完全自立動作（ローカルファースト）**:
   - ブラウザからのアクセスはすべてNAS内部のローカルAPI（`/api/...`）を参照するため、高速かつプライベートに動作します。

---

## 🚀 Asustor AS3102T での起動方法

### 方法1: Docker / Container Center / Portainer（推奨）

Asustor ADMの「App Central」から「Docker-ce」または「Portainer-ce」をインストールしている場合に利用できます。

1. **NASにSSH接続またはターミナルを開く**:
   ```bash
   cd /volume1/Docker/CoreGeeksEXp
   # （またはマウントパス: /Volumes/Docker/CoreGeeksEXp）
   ```

2. **コンテナを起動**:
   ```bash
   docker compose up -d --build
   ```

3. **ブラウザでアクセス**:
   ```
   http://<NASのIPアドレス>:8088/
   ```
   ※ 例: `http://192.168.2.100:8088/`

---

### 方法2: Asustor ADM の Python3 で直接起動（Dockerなしでも可能）

Dockerを使用せず、App Centralの「Python 3」を使って直接サービスとして動かすことも可能です。

1. **起動コマンド**:
   ```bash
   python3 /volume1/Docker/CoreGeeksEXp/server.py 8088 &
   ```
2. NAS起動時に自動実行したい場合は、ADMの **設定 > 定期タスク (Periodic Tasks)** に上記コマンドを登録してください。

---

## 🔄 データの同期・手動バックアップ

`core-geeks.com` が完全に停止する前に追加の最新データを取り込みたい場合は、以下のコマンドを実行するだけで自動差分更新されます。

```bash
python3 sync.py
```

---

## 📂 ディレクトリ構成

```
CoreGeeksEXp/
├── index.html           # メインダッシュボードHTML
├── style.css            # CoreGeeksテーマCSS
├── app.js               # フロントエンド制御（ローカルAPI優先接続）
├── server.py            # 超軽量ローカルAPI & Webサーバー（メモリ~15MB）
├── sync.py              # データ同期・バックアップエンジン
├── Dockerfile           # AS3102T用軽量Python Alpineコンテナ
├── docker-compose.yml   # 永続化ボリューム対応Docker Compose
├── README.md            # 本ドキュメント
├── assets/              # ロゴ、ファビコン等
└── data/                # ローカル永続データベース（SQLite）＆ナレッジアーカイブ
    ├── wallet.db        # 510日分の日次集計・4,215件のトランザクションを格納
    ├── initial_data.js  # 即時表示用プリセットデータ
    ├── local_articles.js # 自サーバー保存型公式技術・確定申告ガイド記事
    ├── backup_daily.json
    ├── backup_transactions.json
    └── backup_rates.json
```
