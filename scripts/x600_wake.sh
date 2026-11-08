#!/usr/bin/env bash
# X600 の Wake-on-LAN サポート（実測で MAC を取得 → magic packet を送る）
#   bash scripts/x600_wake.sh            # 生存確認 + ARP から MAC を控える
#   bash scripts/x600_wake.sh --wake     # magic packet を送る（BIOS/OS 側で WoL 有効が必要）
set -uo pipefail
REPO="${REPO:-/Volumes/Docker/CoreGeeksEXp}"
# WoL の対象 IP も思い込まない（192.168.2.13 は RDP 証明書 CN 実測で Z690）
HOST="${X600_HOST:-}"
if [ -z "$HOST" ]; then
  echo "[wake] X600_HOST が未設定です。X600 の LAN IP は未確定（192.168.2.13 は Z690 と実測済み）。"
  echo "[wake] python3 scripts/lan_scan.py → data/lan_identities.json で身元を確認し、export X600_HOST=<IP> で再実行してください。"
  exit 1
fi
MACFILE="$REPO/data/x600_mac.txt"
BCAST="${WOL_BROADCAST:-192.168.2.255}"

mkdir -p "$(dirname "$MACFILE")"

alive() { ping -c1 -t1 "$HOST" >/dev/null 2>&1; }

if [ "${1:-}" = "--wake" ]; then
  MAC=""
  [ -f "$MACFILE" ] && MAC="$(cat "$MACFILE")"
  if [ -z "$MAC" ]; then
    MAC="$(arp -n "$HOST" 2>/dev/null | awk 'NR>1{print $3}' | head -1)"
  fi
  if [ -z "$MAC" ] || [ "$MAC" = "<incomplete>" ]; then
    echo "[wake] MAC が分かりません（$HOST が一度でも生存して ARP に出るまで取れません）。まず引数なしで実行してください。"
    exit 1
  fi
  echo "[wake] magic packet -> $MAC via $BCAST:7 / :9"
  /Library/Frameworks/Python.framework/Versions/3.12/bin/python3 - "$MAC" "$BCAST" <<'PY'
import socket, re, sys, time
mac = re.sub(r'[^0-9a-fA-F]', '', sys.argv[1]).upper()
bcast = sys.argv[2]
if len(mac) != 12:
    raise SystemExit(f"MAC が不正です: {mac}")
frame = bytes.fromhex("ffffffffffff") + bytes.fromhex(mac) * 16
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
for port in (7, 9):
    s.sendto(frame, (bcast, port))
    s.sendto(frame, ("255.255.255.255", port))
print("sent")
s.close()
time.sleep(2)
PY
  for i in 1 2 3 4 5 6; do
    sleep 10
    if alive; then echo "[wake] $HOST 起動を確認（${i}0 秒）"; exit 0; fi
  done
  echo "[wake] 60 秒待っても応答なし（WoL 無効 / NIC 電源 OFF / 電源コードOFF の可能性）"
  exit 2
fi

echo "== 生存確認 =="
if alive; then
  ping -c2 -t1 "$HOST" 2>&1 | tail -2
else
  echo "$HOST は応答なし（電源 OFF またはスリープ）"
fi
MAC="$(arp -n "$HOST" 2>/dev/null | awk 'NR>1{print $3}' | head -1)"
if [ -n "$MAC" ] && [ "$MAC" != "<incomplete>" ]; then
  echo "$MAC" > "$MACFILE"
  echo "MAC 記録: $MAC -> $MACFILE（今後 --wake で起こせます）"
else
  if [ -f "$MACFILE" ]; then echo "ARP に出ないが過去の記録あり: $(cat "$MACFILE")"; else echo "MAC 未取得（一度生存した瞬間に取得します）"; fi
fi
