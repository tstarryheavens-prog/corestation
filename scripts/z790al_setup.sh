#!/usr/bin/env bash
# z790-al（常駐 Ubuntu）で CoreStation の実測コレクター＆巡回を恒久実行するための準備スクリプト。
# MacBook のスリープ / macOS TCC（SMB マウントへの権限拒否）問題を防ぐため、常に動いているマシンに移す。
#
# 使い方（z790-al 上で、通常のユーザーセッションで）:
#   bash scripts/z790al_setup.sh
set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/tstarryheavens-prog/corestation.git}"
DEST="${CORESTATION_HOME:-$HOME/corestation}"
BRANCH="${BRANCH:-main}"

echo "== 前提チェック =="
for c in git python3 systemctl; do
  command -v "$c" >/dev/null 2>&1 || { echo "  不足: $c (例: sudo apt install git python3)"; exit 1; }
done
python3 - <<'PY'
import sys
print(f"  python {sys.version.split()[0]}")
try:
    import certifi; print("  certifi OK")
except Exception:
    print("  certifi 無し（pip install certifi を推奨。無い場合は /etc/ssl/cert.pem を使います）")
PY

echo "== リポジトリ =="
if [ -d "$DEST/.git" ]; then
  echo "  既存: $DEST（git pull します）"
  git -C "$DEST" pull --ff-only origin "$BRANCH"
else
  echo "  clone: $REPO_URL -> $DEST"
  git clone --branch "$BRANCH" "$REPO_URL" "$DEST"
fi
echo "  最新: $(git -C "$DEST" log -1 --format='%h %ad %s' --date=format:'%Y-%m-%d %H:%M')"

echo "== git push できるか（デプロイゲートは push が必要です） =="
if ! git -C "$DEST" push --dry-run origin "$BRANCH" >/dev/null 2>&1; then
  echo "  ⚠️ push 権限が未取得です。GitHub トークン設定後に --deploy が有効になります。"
  echo "     例: git remote set-url origin https://<TOKEN>@github.com/tstarryheavens-prog/corestation.git"
fi

echo "== systemd user timer をインストール =="
UNIT_DIR="$HOME/.config/systemd/user"
mkdir -p "$UNIT_DIR"
HERE="$(cd "$(dirname "$0")" && pwd)"
for f in corestation-live.service corestation-live.timer \
         corestation-live-full.service corestation-live-full.timer \
         corestation-catchup.service corestation-catchup.timer; do
  cp "$HERE/systemd/$f" "$UNIT_DIR/$f"
  # インストール先リポジトリを環境変数で差し込む
  sed -i "s#__CORESTATION_HOME__|$DEST|g; s#^Environment=.*#Environment=CORESTATION_HOME=$DEST#" "$UNIT_DIR/$f" 2>/dev/null || true
done
systemctl --user daemon-reload
systemctl --user enable --now corestation-live.timer corestation-live-full.timer corestation-catchup.timer
systemctl --user list-timers --all | grep corestation || true

echo "== 1回実行して確認 =="
bash "$HERE/dashboard_live_cron.sh" || true
python3 "$DEST/scripts/dashboard_live.py" --no-probe 2>&1 | tail -2

echo
echo "完了。次から z790-al 上で:"
echo "  journalctl --user -u corestation-live.service -f        # コレクターログ"
echo "  systemd-run --user --unit=corestation-once python3 $DEST/scripts/dashboard_live.py --no-probe"
echo "マイニングリグの実測を出すには（同じマシンで）:"
echo "  coreminer ... 2>&1 | python3 $DEST/scripts/worker_reporter.py --stdin --watch --host 7950X --pool as.catchthatrabbit.com"
