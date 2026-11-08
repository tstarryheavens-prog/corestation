#!/usr/bin/env python3
"""LAN ホストの身元を実測で寄せる（推測・肩書きは書かない）。

- ping で生存確認
- TCP ポート OPEN 実測
- RDP(3389) の自己署名証明書の CN = その PC のコンピューター名
- HTTP/HTTPS の <title> = 装置の自己申告
- tailscale status の "direct <LAN IP>:port" = tailnet ノード名 <-> LAN IP の対応（Tailscale 実測）

出力: data/lan_identities.json  (measured_at 付き。取れなかった項目は null)
read-only: 認証・ログイン・書き込みは一切しない。
"""
import ipaddress
import json
import os
import re
import socket
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

REPO = os.environ.get("REPO_DIR") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(REPO, "data", "lan_identities.json")
SUBNET = os.environ.get("LAN_SUBNET", "192.168.2.0/24")
PORTS = [22, 135, 139, 445, 3389, 5900, 8520, 8899, 47832, 8080, 9090, 80, 443, 631]
MAX_HOSTS = int(os.environ.get("LAN_SCAN_MAX", "300"))


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def sh(cmd, timeout=20):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, (r.stdout or "") + (r.stderr or "")
    except Exception as exc:  # noqa: BLE001
        return 124, f"{type(exc).__name__}: {exc}"


def ping(host):
    rc, out = sh(["ping", "-c", "1", "-t", "1", host], 6)
    ms = None
    m = re.search(r"=([\d.]+)/([\d.]+)/([\d.]+)/", out)
    if m:
        ms = round(float(m.group(2)), 1)
    return rc == 0, ms


def tcp_probe(host, port, timeout=1.2):
    t0 = time.perf_counter()
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return port, round((time.perf_counter() - t0) * 1000, 1)
    except OSError:
        return None, None


def ssh_banner(host):
    try:
        with socket.create_connection((host, 22), timeout=3) as s:
            s.settimeout(3)
            line = s.recv(200).split(b"\n", 1)[0]
            return line.decode("utf-8", "ignore").strip() or None
    except OSError:
        return None


def rdp_cert_cn(host):
    """RDP の自己署名証明書 CN（= Windows のコンピューター名になる）を実測する。"""
    rc, out = sh(["openssl", "s_client", "-connect", f"{host}:3389"], 20)
    inp = "\n".join(["", ""])
    try:
        p = subprocess.run(["openssl", "s_client", "-connect", f"{host}:3389"],
                           input="", capture_output=True, text=True, timeout=20)
        out = (p.stdout or "") + (p.stderr or "")
    except Exception as exc:  # noqa: BLE001
        return None, str(exc)
    m = re.search(r"subject=.*?CN\s*=\s*([^,/]+?)(?:\n|,|/|$)", out)
    if not m:
        m = re.search(r"subject=:/CN=([^/]+)", out)
    if m:
        cn = m.group(1).strip()
        if cn and len(cn) <= 64:
            return cn, "rdp certificate CN"
    return None, None


def http_title(host, port):
    scheme = "https" if port in (443, 8443) else "http"
    rc, out = sh(["curl", "-sk", "-m", "8", f"{scheme}://{host}:{port}/"], 12)
    m = re.search(r"<title[^>]*>(.*?)</title>", out or "", re.I | re.S)
    if m:
        t = re.sub(r"\s+", " ", m.group(1)).strip()
        return (t[:120] or None), f"{scheme}:{port} title"
    return None, None


def tailnet_direct_endpoints():
    """tailscale status の 'direct <ip>:<port>' から ノード名 <-> LAN IP を実測対応付ける。"""
    ts = None
    for cand in ("/usr/local/bin/tailscale", "/usr/bin/tailscale"):
        if os.path.exists(cand):
            ts = cand
            break
    rc, out = sh([ts, "status"], 20) if ts else (127, "tailscale CLI が無い")
    pairs = {}
    for line in out.splitlines():
        m = re.search(r"direct\s+(\d+\.\d+\.\d+\.\d+):\d+", line)
        if m:
            parts = line.split()
            name = parts[1] if len(parts) > 1 else "?"
            pairs[m.group(1)] = {"tailnetName": name, "source": "tailscale status direct endpoint"}
    return pairs, (None if ts and rc == 0 else (out[:160] or "tailscale status 失敗"))


def main():
    net = ipaddress.ip_network(SUBNET, strict=False)
    hosts = [str(h) for h in net.hosts()][:MAX_HOSTS]
    alive = {}
    with ThreadPoolExecutor(max_workers=24) as ex:
        for host, (ok, ms) in zip(hosts, ex.map(ping, hosts)):
            if ok:
                alive[host] = {"pingMs": ms}
    time.sleep(0.5)
    endpoints, tailnet_error = tailnet_direct_endpoints()
    if endpoints:
        for ip, meta in endpoints.items():
            alive.setdefault(ip, {"pingMs": None})
            alive[ip]["tailnet"] = meta

    ports_pairs = [(h, p) for h in alive for p in PORTS]
    with ThreadPoolExecutor(max_workers=48) as ex:
        for (host, port), (op, ms) in zip(ports_pairs, ex.map(lambda a: tcp_probe(*a), ports_pairs)):
            if op is not None:
                alive[host].setdefault("openPorts", []).append(op)

    records = []
    for host, info in sorted(alive.items()):
        open_ports = sorted(set(info.get("openPorts") or []))
        rec = {"ip": host, "pingMs": info.get("pingMs"), "openPorts": open_ports,
               "tailnet": info.get("tailnet"), "identity": None, "identitySource": None}
        if 22 in open_ports:
            rec["sshBanner"] = ssh_banner(host)
        if 3389 in open_ports:
            cn, src = rdp_cert_cn(host)
            if cn:
                rec["identity"], rec["identitySource"] = cn, src
        if rec["identity"] is None:
            for port in (443, 80, 8080, 8899, 8520, 631, 9090):
                if port in open_ports:
                    title, src = http_title(host, port)
                    if title:
                        rec["identity"], rec["identitySource"] = title, src
                        break
        if rec["identity"] is None and rec.get("sshBanner"):
            rec["identity"], rec["identitySource"] = rec["sshBanner"], "ssh banner"
        records.append(rec)

    payload = {"schema": "corestation-lan/1", "measuredAt": now_iso(), "subnet": SUBNET,
               "aliveCount": len(records), "hosts": records,
               "tailnetError": tailnet_error,
               "note": "身元は RDP 証明書 CN / HTTP title / SSH banner / tailscale direct endpoint の実測のみ。取れないものは null。"}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=1)
    print(f"[lan_scan] alive={len(records)} -> {OUT}")
    for r in records:
        if r.get("identity") or r.get("tailnet") or r.get("openPorts"):
            print(f"  {r['ip']:<15} ports={r['openPorts']} identity={r.get('identity')} ({r.get('identitySource')}) tailnet={(r.get('tailnet') or {}).get('tailnetName')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
