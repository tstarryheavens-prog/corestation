# z790-al で CoreStation の実測＆巡回を常駐させる（推奨構成）

MacBook はスリープするため cron が飛び、さらに macOS の TCC が SMB マウント `/Volumes/Docker` への
cron / launchd からのアクセスを `Operation not permitted` で拒否します（2026-11-07 実測で確認）。
CoreStation のコンテンツと実測値を本当に毎更新させるには、**常に動いている z790-al** で回すのが最短です。

## 1. z790-al に SSH で入れるようにする（1回だけ・z790-al 側で実行）
```bash
# Tailscale SSH を有効化（推奨・キー配布不要）
sudo tailscale set --ssh
# または通常の sshd
sudo apt install -y openssh-server && sudo systemctl enable --now ssh
```
Mac 側から確認: `ssh 100.86.91.70 hostname`

## 2. z790-al で一括セットアップ
```bash
git clone https://github.com/tstarryheavens-prog/corestation.git ~/corestation
cd ~/corestation && bash scripts/z790al_setup.sh
```
`scripts/z790al_setup.sh` がやること:
- 前提チェック（git / python3 / systemctl / certifi）
- リポジトリ clone or pull
- systemd user timer 3本のインストールと有効化
  - `corestation-live.timer` … 15分毎に `dashboard_live.py --no-probe`
  - `corestation-live-full.timer` … 3時間毎に `--deploy`（署名変化 && 最小間隔を満たす時だけ git push → Pages 再ビルド）
  - `corestation-catchup.timer` … 7,10,13,16,19,21 時に巡回の遅延追撃（12h 以上空いてるときだけ）
- 初回実行とログの確認

`Persistent=true` が入っているので、マシンの再起動後も飛んだ分を1回取り戻します。

## 3. 必要なパス／環境変数
| 項目 | 既定 | z790-al での指定 |
|---|---|---|
| リポジトリ | スクリプト位置から自動 | `CORESTATION_HOME` |
| SQLite | `<repo>/data/wallet.db` | `CORESTATION_DB=/volume1/Docker/CoreGeeksEXp/data/wallet.db`（SMB マウントまたは Syncthing で同期したコピー） |
| NAS HUD | `http://192.168.2.100:8899` | `NAS_HUD_URL` |
| GitHub push | 環境の git 認証 | `git remote set-url origin https://<TOKEN>@github.com/...`（`--deploy` は push 必須） |

`data/wallet.db` は gitignored（11MB）なので、z790-al 側では SMB マウントか Syncthing 同期で置いてください。
置けない場合は DB セクションだけ `wallet.db が見つからない` として正直に「未取得」表示になります。

## 4. 採掘リグの実測 H/s（7950X が z790-al に載っている場合）
```bash
coreminer --algo core --url stratum+tcp://as.catchthatrabbit.com:8008 --password d \
  --workerName 7950X -i 0 2>&1 | \
  python3 ~/corestation/scripts/worker_reporter.py --stdin --watch --host 7950X --pool as.catchthatrabbit.com
```
`data/machine_metrics/7950X.json` に書かれ、次の collect でダッシュボードの
「採掘速度 (Hashrate)」とワーカー表に **実測** として出ます（取れない項目は null＝未取得のまま）。

## 5. 確認
```bash
systemctl --user list-timers | grep corestation
journalctl --user -u corestation-live.service -n 20
curl -s https://corestation.pages.dev/data/live_state.json | head -c 240
curl -s https://corestation.pages.dev/api/workers | head -c 300
```
