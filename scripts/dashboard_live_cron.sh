#!/bin/bash
# CoreStation 実測コレクターの実行ラッパー（launchd / cron 両対応）
# 通常実行は軽く（probe なし）。3時間に1度だけ推論 probe 込みのフル計測 + Pages デプロイ判定を行う。
set -u
REPO="/Volumes/Docker/CoreGeeksEXp"
PY="/Library/Frameworks/Python.framework/Versions/3.12/bin/python3"
LOG="$REPO/logs/dashboard_live.log"
STAMP="$REPO/data/.last_full_run"
FULL_INTERVAL=10800   # 3時間

cd "$REPO" || { echo "[live] repo が見つからない（NAS アンマウント?） $(date '+%F %T')"; exit 0; }
mkdir -p logs

NOW=$(date +%s)
LAST=$(cat "$STAMP" 2>/dev/null || echo 0)

if [ $((NOW - LAST)) -ge $FULL_INTERVAL ]; then
  echo "=== full run $(date '+%F %T') ===" >> "$LOG"
  "$PY" scripts/dashboard_live.py --deploy --min-deploy-interval-min 120 >> "$LOG" 2>&1
  echo "$NOW" > "$STAMP"
else
  "$PY" scripts/dashboard_live.py --no-probe >> "$LOG" 2>&1
fi
exit 0
