#!/usr/bin/env bash
# X600 の実測メトリクスを Hub（kazukimacbook-air）から引きに行く（読取り専用）
#
# 経路: Windows 標準 OpenSSH（Tailscale SSH サーバーは Windows 未サポートなので使わない）
#   1) LAN 192.168.2.14（tailscale ping の direct endpoint から実測した X600 の LAN IP）
#   2) tailnet IP（tailscale status --json の HostName=x600 から自動解決）
# 認証: 鍵のみ（~/.ssh/x600_collector_ed25519）。パスワードは一切使わない。
# 前提: X600 側で tools/setup_x600.ps1 実行済み（OpenSSH サーバー + 収集鍵 + C:\corestation\corestation_metrics.json）
#
# 使い方:
#   bash scripts/x600_pull_metrics.sh
#   X600_SSH_USER=<whoami の値> bash scripts/x600_pull_metrics.sh
set -uo pipefail

TS="$(command -v tailscale || echo /usr/local/bin/tailscale)"
REPO="${REPO:-/Volumes/Docker/CoreGeeksEXp}"
OUT_DIR="$REPO/data/machine_metrics"
CONF="$REPO/data/x600_ssh.json"
KEY="${X600_SSH_KEY:-$HOME/.ssh/x600_collector_ed25519}"
REMOTE_PATH='C:/corestation/corestation_metrics.json'
PY=/Library/Frameworks/Python.framework/Versions/3.12/bin/python3
mkdir -p "$OUT_DIR"

USER_NAME="${X600_SSH_USER:-}"
LAN_IP="${X600_HOST:-}"
if [ -z "$USER_NAME" ] || [ -z "$LAN_IP" ]; then
  if [ -f "$CONF" ]; then
    USER_NAME="${USER_NAME:-$("$PY" -c "import json,sys;print((json.load(open('$CONF')).get('user') or ''))" 2>/dev/null)}"
    LAN_IP="${LAN_IP:-$("$PY" -c "import json,sys;print((json.load(open('$CONF')).get('lanIp') or ''))" 2>/dev/null)}"
  fi
fi
[ -z "$LAN_IP" ] && LAN_IP="192.168.2.14"   # 2026-11-10 tailscale ping x600 → via 192.168.2.14:41641 で実測

TAILNET_IP=""
if [ -x "$TS" ]; then
  TAILNET_IP="$("$TS" status --json 2>/dev/null | "$PY" -c "
import json,sys
d=json.load(sys.stdin)
for k,p in (d.get('Peer') or {}).items():
    if str(p.get('HostName','')).lower()=='x600' or str(p.get('DNSName','')).lower().startswith('x600.'):
        ips=p.get('TailscaleIPs') or []
        print(ips[0] if ips else ''); break
" 2>/dev/null)"
fi

if [ -z "$USER_NAME" ]; then
  echo "[pull] X600 の Windows ユーザー名が未設定（data/x600_ssh.json か X600_SSH_USER で渡す）"
  echo "[pull] LAN=$LAN_IP tailnet=${TAILNET_IP:-未取得} — setup_x600.ps1 の最後の 'X600_SSH_USER=...' 行が必要"
  exit 1
fi
if [ ! -f "$KEY" ]; then
  echo "[pull] 収集鍵が無い: ${KEY} （setup_x600.ps1 を X600 側で実行して公開鍵を登録させてください）"
  exit 1
fi

echo "[pull] user=$USER_NAME LAN=${LAN_IP:--} tailnet=${TAILNET_IP:-未取得} key=$(basename "$KEY")"

TARGETS=()
for t in "$LAN_IP" "$TAILNET_IP"; do
  [ -n "$t" ] && TARGETS+=("$t")
done

OPEN=""
for t in "${TARGETS[@]}"; do
  if nc -G 5 -z -w 4 "$t" 22 2>/dev/null; then
    echo "[pull] TCP 22 OPEN: $t"
    OPEN="$t"
    break
  else
    echo "[pull] TCP 22 応答なし: ${t} （sshd 未起動 / ファイアウォール / tailnet policy）"
  fi
done
if [ -z "$OPEN" ]; then
  echo "[pull] どの経路でも SSH(22) が開いていません。X600 側で setup_x600.ps1（OpenSSH サーバー + LAN/tailnet 許可）を実行してください"
  exit 2
fi

JSON=""
ERR=""
for attempt in 1 2; do
  ERR="$(mktemp)"
  JSON="$(ssh -i "$KEY" -o IdentitiesOnly=yes -o BatchMode=yes -o ConnectTimeout=8 \
      -o StrictHostKeyChecking=accept-new "$USER_NAME@$OPEN" \
      "powershell -NoProfile -Command \"Get-Content -Raw '$REMOTE_PATH'\"" 2>"$ERR")"
  if [ -n "$JSON" ]; then break; fi
  echo "[pull] attempt $attempt 失敗: $(head -c 220 "$ERR" | tr '\n' ' ')"
  rm -f "$ERR"
  sleep 2
done

if [ -z "$JSON" ]; then
  echo "[pull] SSH は到達したがメトリクスが取れない（鍵未登録 / ファイル未生成）。最後のエラー:"
  [ -n "$ERR" ] && tail -3 "$ERR"
  exit 3
fi

"$PY" - "$OUT_DIR/X600.json" "$JSON" "$OPEN" "$REMOTE_PATH" <<'PY'
import json, sys, datetime
out_path, raw, via, remote_path = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
raw = raw.strip().lstrip("\ufeff")
try:
    data = json.loads(raw)
except json.JSONDecodeError as e:
    print(f"[pull]  remote {remote_path} が JSON として読めない: {e}")
    sys.exit(4)
data.setdefault("machine_id", "X600")
data["pulledAt"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
data["pulledVia"] = f"OpenSSH over {via} (kazukimacbook-air -> X600)"
data["pulledSource"] = remote_path
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
miners = data.get("miners") or []
gpus = data.get("gpus") or []
print(f"[pull] wrote {out_path}")
print(f"[pull] hashrate={data.get('hashrate')} (source={data.get('hashrateSource')}) "
      f"cpuTemp={data.get('cpu',{}).get('temperatureC')} gpuTemps={[g.get('temperatureC') for g in gpus]} "
      f"powerW={data.get('powerW') or (sum([g.get('powerW') or 0 for g in gpus]) or None)} "
      f"minerProcs={[m.get('processName') for m in miners]} workerNames={[m.get('workerName') for m in miners]} "
      f"pool={[m.get('poolHost') for m in miners]} stratumSessions={data.get('stratumSessionCount')} "
      f"unmeasured={data.get('unmeasured') or data.get('reasons')}")
PY
