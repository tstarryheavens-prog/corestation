#!/bin/bash
# MacBook はスリープするため cron は飛ぶ。起きてきたときに「走り忘れていた巡回」を 1 回だけ追撃する。
# 公開ゲート（純テキスト 10,000 字以上）は watcher 側で守られているので、ここでは実行判定だけを行う。
set -u
REPO="/Volumes/Docker/CoreGeeksEXp"
PY="/Library/Frameworks/Python.framework/Versions/3.12/bin/python3"
LOG="$REPO/logs/watcher_catchup.log"
cd "$REPO" || { echo "[catchup] repo が見つからない $(date '+%F %T')"; exit 0; }
mkdir -p logs

HOUR=$(date +%-H)
# 深夜早朝に自動公開しないための時間帯ゲート（7:00〜22:00 のときだけ追撃実行）
if [ "$HOUR" -lt 7 ] || [ "$HOUR" -ge 22 ]; then
  echo "[catchup] 時間帯ゲートでスキップ $(date '+%F %T')" >> "$LOG"
  exit 0
fi

age_hours() { # hub/config の last_checked ISO から経過時間を計算（取れなければ 999999）
  "$PY" - "$1" <<'PY'
import json, os, sys
from datetime import datetime, timezone
path = sys.argv[1]
try:
    with open(path, encoding="utf-8") as f:
        raw = (json.load(f).get("last_checked") or "").strip()
    if not raw:
        print(999999); raise SystemExit(0)
    dt = datetime.fromisoformat(raw)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    print(round((datetime.now(timezone.utc) - dt).total_seconds() / 3600.0, 2))
except Exception:
    print(999999)
PY
}

CH=$(age_hours "hub/config/last_seen_chronicle.json")
CM=$(age_hours "hub/config/last_seen_community.json")
echo "[catchup] $(date '+%F %T') chronicle_age_h=$CH community_age_h=$CM" >> "$LOG"

if [ "$(printf '%s' "$CH" | cut -d. -f1)" -ge 12 ]; then
  echo "--- chronicle_watcher 追撃実行 ---" >> "$LOG"
  "$PY" hub/chronicle_watcher.py >> "$LOG" 2>&1
fi

if [ "$(printf '%s' "$CM" | cut -d. -f1)" -ge 192 ]; then  # 週次ジョブ: 8日以上の遅延だけを追撃
  echo "--- community_watcher 追撃実行 ---" >> "$LOG"
  "$PY" hub/community_watcher.py >> "$LOG" 2>&1
fi
exit 0
