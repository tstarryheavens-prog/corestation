#!/usr/bin/env bash
# X600 の実測メトリクスを tailnet 越しに Hub（MacBook / z790-al）へ取り込む
# 前提: X600 側で tools/setup_x600.ps1 実行済み（Tailscale + --ssh + C:\corestation\corestation_metrics.json）
#      および tailnet policy で port 22 と ssh users が許可されている
# 使い方: bash scripts/x600_pull_metrics.sh
set -uo pipefail

TS="$(command -v tailscale || echo /usr/local/bin/tailscale)"
REPO="${REPO:-/Volumes/Docker/CoreGeeksEXp}"
OUT_DIR="$REPO/data/machine_metrics"
NAMES="${X600_TAILNET_NAMES:-x600,7950x}"
REMOTE_PATH='C:/corestation/corestation_metrics.json'

mkdir -p "$OUT_DIR"

IP=""
if [ -x "$TS" ]; then
  for n in ${NAMES//,/ }; do
    IP="$("$TS" status --json 2>/dev/null | /usr/bin/python3 -c "
import json,sys
d=json.load(sys.stdin)
name=sys.argv[1].lower()
for k,p in (d.get('Peer') or {}).items():
    if name in str(p.get('HostName','')).lower():
        ips=p.get('TailscaleIPs') or []
        print(ips[0] if ips else '')
        break
" "$n")"
    [ -n "$IP" ] && break
  done
fi

if [ -z "$IP" ]; then
  echo "[pull] tailnet に X600 ノードが無い（X600 側で setup_x600.ps1 を実行してください）"
  exit 1
fi
echo "[pull] X600 tailnet IP: $IP"

if ! nc -G 5 -z -w 4 "$IP" 22 2>/dev/null; then
  echo "[pull] SSH(22) that netnet で応答なし — Tailscale policy で port 22 / ssh users を許可する必要があります"
  exit 2
fi

JSON=""
for attempt in 1 2; do
  JSON="$(ssh -o BatchMode=yes -o ConnectTimeout=8 -o StrictHostKeyChecking=accept-new "$IP" \
    "powershell -NoProfile -Command \"Get-Content -Raw '$REMOTE_PATH'\"" 2>/dev/null)"
  [ -n "$JSON" ] && break
done

if [ -z "$JSON" ]; then
  echo "[pull] SSH は開いたがメトリクスを取得できませんでした（認証待ち / ファイル未生成の可能性）"
  exit 3
fi

/Library/Frameworks/Python.framework/Versions/3.12/bin/python3 - "$OUT_DIR/X600.json" "$JSON" <<'PY'
import json, sys
out_path, raw = sys.argv[1], sys.argv[2]
raw = raw.strip().lstrip("\ufeff")
data = json.loads(raw)
data.setdefault("machine_id", "X600")
data["pulled_at"] = __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()
data["pulled_via"] = "tailscale SSH (MacBook -> X600)"
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
print(f"[pull] wrote {out_path}")
print(f"[pull] hashrate={data.get('hashrate')} temperature={data.get('cpu',{}).get('temperatureC')} gpu_temps={[g.get('temperatureC') for g in data.get('gpus',[])]} power={sum([g.get('powerW') or 0 for g in data.get('gpus',[])]) or data.get('powerW')} miners={data.get('minerCount')} stratum={data.get('stratumSessionCount')} worker={ [m.get('workerName') for m in data.get('miners',[])] }")
PY
