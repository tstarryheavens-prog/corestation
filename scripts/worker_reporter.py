#!/usr/bin/env python3
"""
worker_reporter.py — 採掘リグの実測（H/s・温度・消費電力・受理率）を
CoreStation のコレクターが読める形で data/machine_metrics/ に書き出す報告役。

思想: 数値を作らない。取れない項目は null のまま書く。
        ダッシュボード側は null を「未取得」として表示する（dashboard_live.py / functions/api/workers.js）。

使い方:
  1) coreminer の標準出力/ログを(pipe で)読み取る
       coreminer --algo core --url stratum+tcp://as.catchthatrabbit.com:8008 \\
           --password d --workerName 7950X -i 0 2>&1 | \\
         python3 scripts/worker_reporter.py --stdin --host 7950X --pool as.catchthatrabbit.com
  2) すでにログがある場合
       python3 scripts/worker_reporter.py --log ~/coreminer.log --host 7950X
  3) 自分で数値を出せるマイナー/監視スクリプトから直接
       python3 scripts/worker_reporter.py --hashrate 2361.4 --threads 16 --temperature-c 63 --power-w 145 --host 7950X
  4) 常駐して 60 秒ごとに書き直す
       ... | python3 scripts/worker_reporter.py --stdin --watch --host 7950X

出力: data/machine_metrics/<host>.json  (dashboard_live.py が rigReporters として拾う)
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timezone

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
METRICS_DIR = os.path.join(REPO, "data", "machine_metrics")

# coreminer / xmr-stak 系の常见的な出力行
PATTERNS = [
    # "h/s: 2361.4  (2.36 kh/s)"  /  "Hashrate: 2361.4 h/s"
    (re.compile(r"(?:hashrate|h/s|speed)[^\d]{0,12}([\d][\d,\.]*)\s*(?:h/s|hs|kh/s|mh/s)?", re.I), "hashrateHs"),
    # "accepted: 1452 (99.7%)" / "share: 12.3%"
    (re.compile(r"accept[^\d]{0,10}(\d+)", re.I), "acceptedShares"),
    (re.compile(r"([\d\.]+)\s*%"), "acceptedPct"),
    # "temp: 63C" / "GPU0: 63 C"
    (re.compile(r"(?:temp|gpu[ _]?\d?)[^\d]{0,8}([\d\.]{1,5})\s*°?\s*C", re.I), "temperatureC"),
    # "power: 145W"
    (re.compile(r"power[^\d]{0,8}([\d\.]{1,6})\s*W", re.I), "powerW"),
    # "threads: 16"
    (re.compile(r"thread[s]?[^\d]{0,6}(\d+)", re.I), "threads"),
]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_stream(lines) -> dict:
    """ログ/ストリーム行から数値を拾う。見つからNone のまま返す（埋めない）。"""
    found: dict = {}
    for line in lines:
        for pat, key in PATTERNS:
            if key in found:
                continue
            m = pat.search(line)
            if not m:
                continue
            try:
                val = float(m.group(1).replace(",", ""))
            except ValueError:
                continue
            found[key] = val
    return found


def write_report(host: str, payload: dict) -> str:
    os.makedirs(METRICS_DIR, exist_ok=True)
    safe = re.sub(r"[^A-Za-z0-9_.-]", "_", host)[:48] or "rig"
    path = os.path.join(METRICS_DIR, f"{safe}.json")
    payload.setdefault("schema", "corestation-rig/1")
    payload["host"] = host
    payload["measured_at"] = now_iso()
    # 取得できていない項目を 0 にしない（null のまま = ダッシュボードで「未取得」）
    for k in ("hashrateHs", "temperatureC", "powerW", "acceptedPct", "threads"):
        payload.setdefault(k, None)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)
    return path


def main() -> int:
    ap = argparse.ArgumentParser(description="採掘リグの実測を CoreStationコレクターへ報告する")
    ap.add_argument("--host", default=os.uname().nodename if hasattr(os, "uname") else "rig",
                    help="リグ/ワーカー名（ダッシュボードに表示される）")
    ap.add_argument("--worker", default=None, help="--host が無い場合の別名")
    ap.add_argument("--pool", default=None)
    ap.add_argument("--stdin", action="store_true", help="標準入力（マイナーの出力）を parse する")
    ap.add_argument("--log", default=None, help="parse するログファイル")
    ap.add_argument("--watch", action="store_true", help="--stdin/--log を常駐で追跡して 60 秒ごとに書き直す")
    ap.add_argument("--interval", type=int, default=60, help="--watch の書き直し間隔（秒）")
    ap.add_argument("--hashrate", type=float, default=None, help="H/s を直接指定（実測が出せる監視スクリプト用）")
    ap.add_argument("--threads", type=int, default=None)
    ap.add_argument("--temperature-c", dest="temperature_c", type=float, default=None)
    ap.add_argument("--power-w", dest="power_w", type=float, default=None)
    ap.add_argument("--accepted-pct", dest="accepted_pct", type=float, default=None)
    ap.add_argument("--offline", action="store_true", help="このリグを停止状態として報告する")
    args = ap.parse_args()

    payload: dict = {
        "worker": args.worker or args.host,
        "pool": args.pool,
        "hashrateHs": args.hashrate,
        "threads": args.threads,
        "temperatureC": args.temperature_c,
        "powerW": args.power_w,
        "acceptedPct": args.accepted_pct,
        "online": not args.offline,
        "statusDesc": "報告停止" if args.offline else "実測報告中",
        "source": "worker_reporter",
    }

    if args.stdin:
        lines = []
        try:
            for line in sys.stdin:
                lines.append(line.rstrip())
                if len(lines) > 4000:
                    lines = lines[-2000:]
                parsed = parse_stream(lines[-400:])
                for k, v in parsed.items():
                    if payload.get(k) in (None, 0) and v:
                        payload[k] = v
                if args.watch and lines and len(lines) % 40 == 0:
                    path = write_report(args.host, dict(payload))
                    print(f"[reporter] -> {path} H/s={payload.get('hashrateHs')}", flush=True)
        except KeyboardInterrupt:
            pass
    elif args.log:
        with open(args.log, encoding="utf-8", errors="replace") as f:
            payload.update(parse_stream(f.readlines()[-4000:]))

    path = write_report(args.host, payload)
    print(f"[reporter] wrote {path}")
    print(json.dumps(payload, ensure_ascii=False, indent=2))

    if args.watch and not args.stdin:
        # --log --watch: ログの追記を追跡
        last_size = 0
        while True:
            time.sleep(max(10, args.interval))
            try:
                size = os.path.getsize(args.log)
                if size != last_size:
                    with open(args.log, encoding="utf-8", errors="replace") as f:
                        payload.update(parse_stream(f.readlines()[-4000:]))
                    last_size = size
                payload["measured_at"] = now_iso()
                write_report(args.host, payload)
                print(f"[reporter] refreshed {path} H/s={payload.get('hashrateHs')}", flush=True)
            except Exception as exc:  # noqa: BLE001
                print(f"[reporter] error: {type(exc).__name__}: {exc}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
