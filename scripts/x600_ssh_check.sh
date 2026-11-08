#!/usr/bin/env bash
# X600 が tailnet に出てきたかを Hub 側で実測確認する（認証・ログインはしない）
# 使い方: bash scripts/x600_ssh_check.sh
set -uo pipefail

TS="$(command -v tailscale || echo /usr/local/bin/tailscale)"
LAN_HOST="${X600_HOST:-192.168.2.13}"
NAMES="${X600_TAILNET_NAMES:-x600,7950x}"

echo "== tailnet status =="
if [ -x "$TS" ]; then
  "$TS" status 2>&1 | sed -n '1,15p'
else
  echo "tailscale CLI が見つからない"
fi

echo
echo "== LAN $LAN_HOST 実測 =="
ping -c1 -t1 "$LAN_HOST" 2>&1 | tail -2
for p in 445 3389 22; do
  if nc -G 5 -vz -w 3 "$LAN_HOST" "$p" 2>&1 | grep -q "succeeded\|open"; then
    echo "TCP $p: OPEN"
  else
    echo "TCP $p: 応答なし"
  fi
done

echo
echo "== tailnet 上の X600 ノード検索 =="
FOUND=""
if [ -x "$TS" ]; then
  IFS=',' read -ra NAMES_ARR <<< "$NAMES"
  for n in "${NAMES_ARR[@]}"; do
    line="$("$TS" status 2>/dev/null | grep -i "$n" || true)"
    if [ -n "$line" ]; then echo "$line"; FOUND="$n"; break; fi
  done
fi
if [ -z "$FOUND" ]; then
  echo "tailnet に X600 ノードが見えない（X600 側で tools/setup_x600.ps1 を実行する必要がある）"
  exit 0
fi

IP="$("$TS" status --json 2>/dev/null | /usr/bin/python3 -c "
import json,sys
d=json.load(sys.stdin)
name=sys.argv[1].lower()
for k,p in (d.get('Peer') or {}).items():
    if name in str(p.get('HostName','')).lower():
        ips=p.get('TailscaleIPs') or []
        print(ips[0] if ips else '')
        break
" "$FOUND")"
echo "tailnet IP: ${IP:-未取得}"
[ -n "${IP:-}" ] && "$TS" ping -c 3 "$IP" 2>&1 | tail -4
if [ -n "${IP:-}" ]; then
  if nc -G 5 -vz -w 4 "$IP" 22 2>&1 | grep -q "succeeded\|open"; then
    echo "SSH(22) over tailnet: OPEN  → ssh ${IP} で実測取り込み可能"
  else
    echo "SSH(22) over tailnet: 応答なし → Tailscale 管理コンソールの ACL で port 22 と ssh users を許可してください"
  fi
fi
