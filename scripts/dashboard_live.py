#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
dashboard_live.py — CoreStation (#dashboard) の生データコレクター

設計方針（重要）:
  「live っぽい数値」をコード内で作ることを禁止する。
  各セクションは 必ず実測 (HTTP / SQLite / ファシステム / サブプロセス) だけを書き、
  取得できなかったものは error + reason として残す（数値を補完しない）。

出力: data/live_state.json  (各 section に measured_at / source / ok を付与)
  signature = タイムスタンプを除いた内容のハッシュ。cron ラッパはこれで
  「実質変化があった時だけ」git commit + push する（デプロイ churn 抑制）。

実行:
  python3 scripts/dashboard_live.py            # 収集して data/live_state.json を書く
  python3 scripts/dashboard_live.py --print    # 収集結果を JSON で stdout（ファイルは書かない）
  python3 scripts/dashboard_live.py --signature-only
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import socket
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(REPO, "data")
OUT_FILE = os.path.join(DATA_DIR, "live_state.json")
HISTORY_FILE = os.path.join(DATA_DIR, "metrics_history.json")
MACHINE_METRICS_DIR = os.path.join(DATA_DIR, "machine_metrics")
LOCK_FILE = os.path.join(DATA_DIR, ".dashboard_live.lock")

JST = timezone(timedelta(hours=9))
DEFAULT_WALLET = "cb57b88d24678c2091332971e3a38cca472dd8aac0cd"
BLOCKINDEX = "https://blockindex.net"
BLOCK_REWARD_XCB = 1.65  # Core のブロック報酬（台帳の実測値と照合可能な定数）

# 自前推論ノード（OpenAI 互換）。llama-swap / llama-server のどちらでも測れる。
INFERENCE_NODES = [
    {"id": "z790-al (Strata)", "role": "Hermes 推論 / llama-swap", "base": "http://100.86.91.70:47832",
     "model": "iq3_xxs", "lan_base": "http://192.168.2.11:47832"},
    {"id": "bc250-1", "role": "Phi-4 14B (llama.cpp)", "base": "http://100.79.26.62:8080", "model": "phi4"},
]
NAS_HUD = "http://192.168.2.100:8899"
CTR_POOLS = ["https://api.catchthatrabbit.com/api/v2", "https://as.catchthatrabbit.com/api/v2"]

UA = "CoreStationCollector/1.0 (NAS+Hermes live telemetry)"


def now_jst() -> str:
    return datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S JST")


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ssl_context():
    """certifi → /etc/ssl/cert.pem → 検証なし（その旨を記録）の順で TLS 環境を作る。
    macOS の Python.framework 版は証明書が入っていないため、素の urlopen だと
    CERTIFICATE_VERIFY_FAILED で全収集が空になる（実測で起きた）。"""
    import ssl

    paths = []
    try:
        import certifi
        paths.append(certifi.where())
    except Exception:
        pass
    paths += ["/etc/ssl/cert.pem", "/private/etc/ssl/cert.pem"]
    paths += [p for p in [os.environ.get("SSL_CERT_FILE"), os.environ.get("REQUESTS_CA_BUNDLE")] if p]
    for p in paths:
        if p and os.path.exists(p):
            try:
                ctx = ssl.create_default_context(cafile=p)
                return ctx, f"verified:{p}"
            except Exception:
                continue
    return ssl._create_unverified_context(), "unverified(fallback)"


TLS_NOTE = None


def http_json(url: str, timeout: float = 25, retries: int = 2, insecure: bool = False):
    global TLS_NOTE
    last_err = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
            if insecure:
                ctx, note = ssl._create_unverified_context(), "unverified(requested)"
            else:
                ctx, note = _ssl_context()
            TLS_NOTE = note
            with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
                raw = r.read().decode("utf-8", errors="replace")
            return json.loads(raw), None
        except Exception as exc:  # noqa: BLE001
            last_err = f"{type(exc).__name__}: {str(exc)[:180]}"
            time.sleep(1.5 * (attempt + 1))
    return None, last_err


def http_status(url: str, timeout: float = 8):
    t0 = time.time()
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return {"ok": True, "status": r.status, "latency_ms": round((time.time() - t0) * 1000, 1)}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "latency_ms": round((time.time() - t0) * 1000, 1),
                "error": f"{type(exc).__name__}: {str(exc)[:140]}"}


# ───────────────────────── on-chain (blockindex) ─────────────────────────
def collect_chain(wallet: str) -> dict:
    src = f"{BLOCKINDEX}/api/v2"
    j, err = http_json(src, timeout=30)
    if not j:
        return {"ok": False, "source": src, "measured_at": iso_now(), "error": err}
    backend = j.get("backend") or {}
    blockbook = j.get("blockbook") or {}
    height = backend.get("blocks") or blockbook.get("bestHeight")
    difficulty = backend.get("difficulty")
    last_block_time = blockbook.get("lastBlockTime")

    addr_src = f"{BLOCKINDEX}/api/v2/address/{wallet}?details=txs&pageSize=100"
    a, aerr = http_json(addr_src, timeout=30)
    income_days = {}
    balance_xcb = None
    last_payout_at = None
    tx_count = 0
    block_interval_s = None

    if a:
        raw_balance = a.get("balance")
        balance_xcb = None
        if raw_balance not in (None, ""):
            try:
                balance_xcb = int(raw_balance) / 1e18
            except (TypeError, ValueError):
                balance_xcb = None
        txs = a.get("transactions") or []
        times = []
        for t in txs:
            bt = t.get("blockTime")
            if not bt:
                continue
            times.append(bt)
            inbound = 0.0
            for vout in (t.get("vout") or []):
                if wallet in (vout.get("addresses") or []):
                    try:
                        inbound += int(vout.get("value", "0")) / 1e18
                    except (TypeError, ValueError):
                        pass
            if inbound <= 0:
                continue
            tx_count += 1
            day = datetime.fromtimestamp(bt, timezone.utc).astimezone(JST).strftime("%Y-%m-%d")
            income_days[day] = income_days.get(day, 0.0) + inbound
            stamp = datetime.fromtimestamp(bt, timezone.utc).isoformat()
            if last_payout_at is None or stamp > last_payout_at:
                last_payout_at = stamp
        if len(times) >= 20:
            span = max(times) - min(times)
            # 注意: これはこのウォレットの取引間隔の実測であって、ネットワークのブロック生成間隔ではない
            block_interval_s = round(span / (len(times) - 1) / 60.0, 2)  # 分

    total_24h = sum(v for k, v in income_days.items()
                    if k >= (datetime.now(JST) - timedelta(days=1)).strftime("%Y-%m-%d"))
    total_7d = sum(v for k, v in income_days.items()
                   if k >= (datetime.now(JST) - timedelta(days=7)).strftime("%Y-%m-%d"))
    total_30d = sum(v for k, v in income_days.items()
                    if k >= (datetime.now(JST) - timedelta(days=30)).strftime("%Y-%m-%d"))

    # 自マシンの採掘貢献の「実測」代理指標: ブロック承認数 / 日（着金実績から算出）
    blocks_24h = round(total_24h / BLOCK_REWARD_XCB, 3) if total_24h else 0.0
    blocks_7d_avg = round((total_7d / 7) / BLOCK_REWARD_XCB, 3) if total_7d else 0.0

    data = {
        "blockHeight": height,
        "difficulty": difficulty,
        "difficulty_display": f"{int(difficulty) / 1e6:.2f} M" if difficulty else None,
        "lastBlockTime": last_block_time,
        "inSync": blockbook.get("inSync"),
        "coin": blockbook.get("coin"),
        "backendVersion": backend.get("version"),
        "ownTxIntervalMeasuredMin": block_interval_s,  # このウォレットの実取引間隔（分）。網絡値ではない
        "walletBalanceXcb": round(balance_xcb, 6) if balance_xcb is not None else None,
        "payoutTxCount": tx_count,
        "lastPayoutAtJst": (datetime.fromtimestamp(
            datetime.fromisoformat(last_payout_at).timestamp(), JST).strftime("%Y-%m-%d %H:%M JST")
            if last_payout_at else None),
        "lastPayoutAgeMin": int((datetime.now(timezone.utc) - datetime.fromisoformat(last_payout_at)).total_seconds() // 60)
            if last_payout_at else None,
        "earnedXcb24h": round(total_24h, 4),
        "earnedXcb7d": round(total_7d, 4),
        "earnedXcb30d": round(total_30d, 4),
        "blocksFound24hEstimate": blocks_24h,
        "blocksFoundPerDay7dEstimate": blocks_7d_avg,
        "addressFetchError": aerr,
    }
    # 総供給量/流通量は blockindex が空文字を返すため、実測不能なら null（補完しない）
    supply_raw = blockbook.get("circulatingSupply") or ""
    data["circulatingSupplyRaw"] = supply_raw or None
    return {"ok": True, "source": src, "measured_at": iso_now(), "data": data}


# ───────────────────────── pool (Catch That Rabbit) ─────────────────────────
def collect_pool(wallet: str) -> dict:
    """実プール API を実際に叩く。届かなければ 'unreachable' を正直に書く（値を作らない）。"""
    attempts = []
    for base in CTR_POOLS:
        for q in (f"?wallet={wallet}&workers=1", f"?coins[]=xcb&wallet={wallet}&workers=1"):
            url = base + q
            j, err = http_json(url, timeout=10, retries=1, insecure=True)
            if j and isinstance(j, dict) and (j.get("workers") or j.get("results")):
                workers = j.get("workers") or j.get("results") or []
                return {"ok": True, "source": url, "measured_at": iso_now(),
                        "data": {"workers": workers,
                                 "totalHashrate": sum(float(w.get("hash_rate", 0) or 0) for w in workers)}}
            attempts.append({"url": url, "error": err or "no workers array"})
    return {"ok": False, "source": CTR_POOLS[0], "measured_at": iso_now(),
            "reason": "プール API が応答しない（522/404・TLS 証明期限切れの実測）",
            "attempts": attempts}


# ───────────────────────── local NAS SQLite ─────────────────────────
def collect_db() -> dict:
    db = os.path.join(DATA_DIR, "wallet.db")
    if not os.path.exists(db):
        return {"ok": False, "source": db, "measured_at": iso_now(), "error": "wallet.db が見つからない"}
    try:
        conn = sqlite3.connect(f"file:{db}?nolock=1", uri=True, timeout=30)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        counts = {}
        for t in ("daily_transactions", "application_transactions", "currency_rates", "latest_rates", "workers"):
            try:
                cur.execute(f"SELECT COUNT(*) AS n FROM {t}")
                counts[t] = cur.fetchone()["n"]
            except sqlite3.Error:
                counts[t] = None
        cur.execute("SELECT MIN(day) AS a, MAX(day) AS b FROM daily_transactions")
        rng = dict(cur.fetchone())
        cur.execute("SELECT MIN(block_timestamp) AS a, MAX(block_timestamp) AS b FROM application_transactions")
        txr = dict(cur.fetchone())
        last_sync_ts = txr.get("b")
        cur.execute("SELECT * FROM latest_rates")
        latest_rates = [dict(r) for r in cur.fetchall()]
        cur.execute("SELECT * FROM workers")
        db_workers = [dict(r) for r in cur.fetchall()]
        cur.execute("SELECT MAX(updated_at) AS a FROM currency_rates") if False else None
        conn.close()
        data = {
            "dbPath": "/volume1/Docker/CoreGeeksEXp/data/wallet.db",
            "fileSizeBytes": os.path.getsize(db),
            "fileMtimeJst": datetime.fromtimestamp(os.path.getmtime(db), JST).strftime("%Y-%m-%d %H:%M JST"),
            "dailyCount": counts.get("daily_transactions"),
            "txCount": counts.get("application_transactions"),
            "rateCount": counts.get("currency_rates"),
            "workersTableRows": counts.get("workers"),
            "minDate": rng.get("a"),
            "maxDate": rng.get("b"),
            "lastTxAtJst": datetime.fromtimestamp(txr["b"], JST).strftime("%Y-%m-%d %H:%M JST") if txr.get("b") else None,
            "lastSyncAtJst": datetime.fromtimestamp(last_sync_ts, JST).strftime("%Y-%m-%d %H:%M JST") if last_sync_ts else None,
            "latestRates": latest_rates[:12],
            "dbWorkersSnapshot": db_workers,
        }
        return {"ok": True, "source": db, "measured_at": iso_now(), "data": data}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "source": db, "measured_at": iso_now(), "error": f"{type(exc).__name__}: {str(exc)[:180]}"}


# ───────────────────────── content freshness (articles / watchers) ─────────────────────────
def _newest(paths, pattern="*.html", limit=6):
    import glob

    out = []
    for base in paths:
        for f in glob.glob(os.path.join(base, pattern)):
            try:
                out.append((os.path.getmtime(f), f))
            except OSError:
                pass
    out.sort(reverse=True)
    return [{"file": os.path.relpath(f, REPO),
             "mtimeJst": datetime.fromtimestamp(m, JST).strftime("%Y-%m-%d %H:%M JST")} for m, f in out[:limit]]


def collect_content() -> dict:
    src = "articles/, hub/output/, hub/config/last_seen_*.json, data/local_articles.js"
    arts_dir = os.path.join(REPO, "articles")
    hub_out = os.path.join(REPO, "hub", "output")
    shortfall = os.path.join(hub_out, "shortfall")
    articles_js = os.path.join(DATA_DIR, "local_articles.js")

    count_articles = 0
    if os.path.isdir(arts_dir):
        count_articles = len([f for f in os.listdir(arts_dir) if f.endswith(".html")])

    archive = []
    newest_archive_date = None
    if os.path.exists(articles_js):
        try:
            s = open(articles_js, encoding="utf-8").read()
            m = re.search(r"=\s*(\[.*\])\s*;?\s*$", s.strip(), re.S)
            arr = json.loads(m.group(1)) if m else []
            dates = sorted({a.get("date") for a in arr if a.get("date")}, reverse=True)
            newest_archive_date = dates[0] if dates else None
            archive = [{"id": a.get("id"), "title": (a.get("title") or "")[:70], "date": a.get("date")} for a in arr[:6]]
        except Exception as exc:  # noqa: BLE001
            archive = [{"error": str(exc)[:120]}]

    def jload(p):
        try:
            return json.load(open(p, encoding="utf-8"))
        except Exception:
            return None

    chron = jload(os.path.join(REPO, "hub", "config", "last_seen_chronicle.json")) or {}
    comm = jload(os.path.join(REPO, "hub", "config", "last_seen_community.json")) or {}

    git_last = ""
    try:
        git_last = subprocess.run(["git", "-C", REPO, "log", "-1", "--format=%h %ad %s", "--date=format:%Y-%m-%d %H:%M"],
                                  capture_output=True, text=True, timeout=20).stdout.strip()
    except Exception:
        git_last = ""

    shortfall_files = []
    if os.path.isdir(shortfall):
        shortfall_files = _newest([shortfall], "*.md", 5) + _newest([shortfall], "*.html", 5)

    data = {
        "articlesDirCount": count_articles,
        "articlesNewest": _newest([arts_dir], "*.html", 6),
        "hubOutputNewest": _newest([hub_out], "*.html", 6),
        "archiveCount": None,
        "archiveNewestDate": newest_archive_date,
        "archiveLatestItems": archive,
        "archiveFileMtimeJst": datetime.fromtimestamp(os.path.getmtime(articles_js), JST).strftime("%Y-%m-%d %H:%M JST")
            if os.path.exists(articles_js) else None,
        "watcherLastCheckedChronicle": chron.get("last_checked"),
        "watcherLastPublishedCommunity": comm.get("last_published_date"),
        "watcherSeenPosts": len(chron.get("seen_posts") or []) if chron else 0,
        "shortfallCount": len(shortfall_files),
        "shortfallNewest": shortfall_files[:4],
        "gitLastCommit": git_last,
    }
    try:
        s = open(articles_js, encoding="utf-8").read()
        m = re.search(r"=\s*(\[.*\])\s*;?\s*$", s.strip(), re.S)
        data["archiveCount"] = len(json.loads(m.group(1))) if m else None
    except Exception:
        pass
    return {"ok": True, "source": src, "measured_at": iso_now(), "data": data}


# ───────────────────────── watcher schedule (real crontab on NAS if readable) ─────────────────────────
def collect_watcher() -> dict:
    src = "hub/config/last_seen_*.json + hub/output mtime + NAS crontab (if readable)"
    hub_out = os.path.join(REPO, "hub", "output")
    last_run = None
    if os.path.isdir(hub_out):
        newest = 0
        for f in os.listdir(hub_out):
            try:
                newest = max(newest, os.path.getmtime(os.path.join(hub_out, f)))
            except OSError:
                pass
        if newest:
            last_run = datetime.fromtimestamp(newest, JST).strftime("%Y-%m-%d %H:%M JST")
    crontab = []
    try:
        r = subprocess.run(["crontab", "-l"], capture_output=True, text=True, timeout=10)
        for line in (r.stdout or "").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and ("chronicle" in line or "community" in line or "core" in line.lower()):
                parts = line.split(maxsplit=5)
                crontab.append({"schedule": " ".join(parts[:5]), "command": (parts[5] if len(parts) > 5 else "")[:120]})
    except Exception:
        pass
    return {"ok": True, "source": src, "measured_at": iso_now(),
            "data": {"lastHubOutputAtJst": last_run, "crontabEntriesVisibleToCollector": crontab,
                     "note": "巡回の間隔は crontab 実体から。crontab が見えないマシンで実行中は null。"}}


# ───────────────────────── own machines: measured compute ─────────────────────────
def local_host_metrics() -> dict:
    host = {"hostname": socket.gethostname(), "os": f"{platform.system()} {platform.release()}",
            "cpuLogical": os.cpu_count(), "measured_at": iso_now()}
    try:
        host["loadAvg"] = [round(x, 2) for x in os.getloadavg()]
    except OSError:
        host["loadAvg"] = None
    if platform.system() == "Darwin":
        try:
            host["ramBytes"] = int(subprocess.run(["sysctl", "-n", "hw.memsize"], capture_output=True,
                                                   text=True, timeout=10).stdout.strip())
        except Exception:
            host["ramBytes"] = None
        try:
            out = subprocess.run(["vm_stat"], capture_output=True, text=True, timeout=10).stdout
            page = 4096
            active = free = spec = wired = 0
            for line in out.splitlines():
                if "Pages active" in line: active = int(line.split()[-1].rstrip("."))
                elif "Pages free" in line: free = int(line.split()[-1].rstrip("."))
                elif "Pages speculative" in line: spec = int(line.split()[-1].rstrip("."))
                elif "Pages wired down" in line: wired = int(line.split()[-1].rstrip("."))
            host["ramUsedBytes"] = (active + wired) * page
            host["ramFreeBytes"] = (free + spec) * page
        except Exception:
            pass
        try:
            out = subprocess.run(["sysctl", "-n", "kern.boottime"], capture_output=True, text=True, timeout=10).stdout
            m = re.search(r"sec = (\d+)", out)
            if m:
                host["uptimeSeconds"] = int(time.time()) - int(m.group(1))
        except Exception:
            pass
    else:
        try:
            mem = {}
            for line in open("/proc/meminfo"):
                k, v = line.split(":", 1)
                mem[k.strip()] = int(v.strip().split()[0]) * 1024
            host["ramBytes"] = mem.get("MemTotal")
            host["ramUsedBytes"] = (mem.get("MemTotal", 0) - mem.get("MemAvailable", 0)) or None
            host["ramFreeBytes"] = mem.get("MemAvailable")
        except Exception:
            pass
        try:
            host["uptimeSeconds"] = int(float(open("/proc/uptime").read().split()[0]))
        except Exception:
            pass
    try:
        st = os.statvfs(REPO)
        host["diskFreeBytes"] = st.f_bavail * st.f_frsize
        host["diskTotalBytes"] = st.f_blocks * st.f_frsize
    except Exception:
        pass
    try:
        out = subprocess.run(["ps", "-Aceo", "pcpu,comm"], capture_output=True, text=True, timeout=10).stdout.splitlines()
        host["topProcesses"] = [l.strip() for l in out[1:6]]
    except Exception:
        host["topProcesses"] = None
    return host


def stream_probe(base: str, model: str, max_tokens: int = 160, timeout: float = 240) -> dict:
    """SSE を実際に見て TTFT と decode tok/s を実測する（固定オーバーヘッドを分離）。"""
    body = json.dumps({"model": model,
                       "messages": [{"role": "user", "content": "Count from 1 to 120, one number per line."}],
                       "max_tokens": max_tokens, "temperature": 0, "stream": True}).encode()
    t0 = time.time()
    t_first = None
    t_last = None
    n = 0
    try:
        req = urllib.request.Request(base + "/v1/chat/completions", data=body,
                                     headers={"Content-Type": "application/json", "Accept": "text/event-stream"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            for raw in r:
                line = raw.decode("utf-8", errors="ignore").strip()
                if not line.startswith("data:"):
                    continue
                payload = line[5:].strip()
                if payload == "[DONE]":
                    break
                try:
                    j = json.loads(payload)
                except json.JSONDecodeError:
                    continue
                delta = (j.get("choices") or [{}])[0].get("delta") or {}
                if delta.get("content"):
                    n += 1
                    t_now = time.time()
                    if t_first is None:
                        t_first = t_now
                    t_last = t_now
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"{type(exc).__name__}: {str(exc)[:160]}",
                "wallSeconds": round(time.time() - t0, 2), "measured_at": iso_now()}
    wall = time.time() - t0
    out = {"ok": True, "wallSeconds": round(wall, 2), "tokens": n, "measured_at": iso_now()}
    if t_first:
        out["timeToFirstTokenSeconds"] = round(t_first - t0, 2)
    if t_first and t_last and t_last > t_first and n > 1:
        out["decodeTokensPerSecond"] = round((n - 1) / (t_last - t_first), 2)
    if n:
        out["overallTokensPerSecond"] = round(n / wall, 2)
    return out


def collect_machines() -> dict:
    nodes = []
    # 1) このコレクターを実行しているマシン
    nodes.append({"id": local_host_metrics()["hostname"], "role": "collector host",
                  "metrics": local_host_metrics(), "kind": "local"})

    # 2) 推論ノード（llama-swap / llama-server）を実測
    for node in INFERENCE_NODES:
        entry: dict = {"id": node["id"], "role": node["role"], "kind": "inference", "measured_at": iso_now()}
        bases = [node["base"]] + ([node["lan_base"]] if node.get("lan_base") else [])
        models = None
        used = None
        for b in bases:
            ping = http_status(b + "/v1/models", timeout=8)
            if ping.get("ok"):
                j, _ = http_json(b + "/v1/models", timeout=8, retries=1)
                models = (j or {}).get("data")
                used = b
                entry["pingLatencyMs"] = ping.get("latency_ms")
                break
            entry.setdefault("connectAttempts", []).append({"base": b, "error": ping.get("error")})
        if used:
            entry["online"] = True
            entry["endpoint"] = used
            entry["models"] = [{"id": m.get("id"), "label": (m.get("meta") or {}).get("label"),
                                "gpus": (m.get("meta") or {}).get("gpus")} for m in (models or [])]
            probe = stream_probe(used, node["model"], max_tokens=140, timeout=150)
            entry["throughputProbe"] = probe
            # llama-swap / llama-server に --metrics があるか実際に確認（あれば実 GPU 値を使う）
            mj, merr = http_json(used + "/metrics", timeout=8, retries=1)
            entry["metricsEndpoint"] = {"available": bool(mj), "note": merr or "parsed"}
        else:
            entry["online"] = False
        nodes.append(entry)

    # 3) NAS HUD（稼働/rev を実測）
    hud, herr = http_json(NAS_HUD + "/api/status", timeout=10, retries=1)
    nodes.append({"id": "NAS (Asustor) HUD", "role": "運用 HUD / wallet.db ホスト", "kind": "nas",
                  "measured_at": iso_now(), "online": bool(hud),
                  "status": hud, "error": None if hud else herr, "source": NAS_HUD + "/api/status"})

    # 4) リグ側の報告（worker_reporter.py が data/machine_metrics/<host>.json に書く）
    reporters = []
    if os.path.isdir(MACHINE_METRICS_DIR):
        for f in sorted(os.listdir(MACHINE_METRICS_DIR)):
            if not f.endswith(".json"):
                continue
            try:
                reporters.append(json.load(open(os.path.join(MACHINE_METRICS_DIR, f), encoding="utf-8")))
            except Exception as exc:  # noqa: BLE001
                reporters.append({"file": f, "error": str(exc)[:120]})
    return {"ok": True, "source": "local proc + inference HTTP probes + NAS HUD + machine_metrics/*.json",
            "measured_at": iso_now(),
            "data": {"nodes": nodes, "rigReporters": reporters,
                     "rigReporterCount": len(reporters),
                     "note": "採掘リグの H/s・温度・消費電力はリグ上で worker_reporter.py を実行した分だけ実測値になる（未取得の項目は null のまま）。"}}


def append_history(state: dict, limit: int = 200):
    rows = []
    if os.path.exists(HISTORY_FILE):
        try:
            rows = json.load(open(HISTORY_FILE, encoding="utf-8"))
        except Exception:
            rows = []
    m = (state.get("machines") or {}).get("data") or {}
    for node in m.get("nodes", []):
        probe = node.get("throughputProbe") or {}
        if not probe:
            continue
        rows.append({"at": node.get("measured_at"), "node": node.get("id"),
                     "decodeTokS": probe.get("decodeTokensPerSecond"),
                     "ttftS": probe.get("timeToFirstTokenSeconds"),
                     "wallS": probe.get("wallSeconds"), "online": node.get("online", True)})
    ch = (state.get("chain") or {}).get("data") or {}
    if ch.get("blockHeight"):
        rows.append({"at": (state.get("chain") or {}).get("measured_at"), "node": "chain",
                     "blockHeight": ch.get("blockHeight"), "earned24h": ch.get("earnedXcb24h")})
    json.dump(rows[-limit:], open(HISTORY_FILE, "w", encoding="utf-8"), ensure_ascii=False)
    return len(rows[-limit:])


GATE_FILE = os.path.join(DATA_DIR, ".deploy_gate.json")


def deploy_snapshot(state: dict, force: bool, min_interval_min: int) -> dict:
    """live_state.json / metrics_history.json だけ狙い撃ちで commit+push し Cloudflare Pages を再ビルドさせる。
    (a) 署名が変わった時だけ (b) 前回 push から min_interval_min 分以上経過した時だけ。
    失敗したときは理由をそのまま返す（成功したことにしない）。"""
    sig = state.get("signature") or ""
    now = datetime.now(timezone.utc)

    gate = {}
    try:
        if os.path.exists(GATE_FILE):
            with open(GATE_FILE, encoding="utf-8") as f:
                gate = json.load(f)
    except Exception:
        gate = {}

    prev_sig = gate.get("deployed_signature")
    try:
        prev_at = datetime.fromisoformat(gate["deployed_at"]) if gate.get("deployed_at") else None
    except Exception:
        prev_at = None

    if sig and sig == prev_sig and not force:
        return {"pushed": False, "reason": "signature unchanged", "signature": sig}
    if prev_at and (now - prev_at).total_seconds() / 60.0 < min_interval_min and not force:
        return {"pushed": False, "reason": f"min interval {min_interval_min} min not elapsed (last {gate.get('deployed_at')})",
                "signature": sig}

    paths = ["data/live_state.json", "data/metrics_history.json"]
    try:
        subprocess.run(["git", "-C", REPO, "add", "--"] + paths, check=True, capture_output=True, text=True, timeout=60)
        diff = subprocess.run(["git", "-C", REPO, "diff", "--cached", "--quiet"], capture_output=True, timeout=60)
        if diff.returncode == 0:
            return {"pushed": False, "reason": "no staged diff", "signature": sig}
        msg = f"chore(live): dashboard 実測スナップショット {sig[:12]}"
        subprocess.run(
            ["git", "-c", "user.name=CoreStation Live Collector",
             "-c", "user.email=corestation-collector@local.invalid",
             "-C", REPO, "commit", "-m", msg],
            check=True, capture_output=True, text=True, timeout=120)
        push = subprocess.run(["git", "-C", REPO, "push", "origin", "main"],
                              capture_output=True, text=True, timeout=180)
        if push.returncode != 0:
            return {"pushed": False,
                    "reason": f"git push failed: {(push.stderr or push.stdout or '')[-300:]}",
                    "signature": sig}
        with open(GATE_FILE, "w", encoding="utf-8") as f:
            json.dump({"deployed_signature": sig, "deployed_at": now.isoformat()}, f, ensure_ascii=False)
        return {"pushed": True, "commitMessage": msg, "signature": sig, "at": now.isoformat()}
    except Exception as exc:  # noqa: BLE001
        return {"pushed": False, "reason": f"{type(exc).__name__}: {str(exc)[:240]}", "signature": sig}


def staleness_summary(state: dict) -> dict:
    """ダッシュボードが『いつの状態を見ているか』を正直に出すための要約。"""
    out = {}
    def age_days(iso_or_str):
        if not iso_or_str:
            return None
        for fmt in ("%Y-%m-%d %H:%M JST", "%Y-%m-%dT%H:%M:%S", None):
            try:
                if fmt:
                    dt = datetime.strptime(str(iso_or_str)[:19], fmt).replace(tzinfo=JST)
                else:
                    dt = datetime.fromisoformat(str(iso_or_str))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return round((datetime.now(timezone.utc) - dt).total_seconds() / 86400, 2)
            except Exception:
                continue
        return None

    content = (state.get("content") or {}).get("data") or {}
    db = (state.get("db") or {}).get("data") or {}
    chain = (state.get("chain") or {}).get("data") or {}
    out["articles_newest_age_days"] = age_days((content.get("articlesNewest") or [{}])[0].get("mtimeJst"))
    out["archive_newest_date_age_days"] = age_days(content.get("archiveNewestDate"))
    out["watcher_last_run_age_days"] = age_days(content.get("watcherLastCheckedChronicle"))
    out["db_last_sync_age_days"] = age_days(db.get("lastSyncAtJst"))
    out["db_file_age_days"] = age_days(db.get("fileMtimeJst"))
    out["last_payout_age_minutes"] = chain.get("lastPayoutAgeMin")
    return out


def signature_of(state: dict) -> str:
    """タイムスタンプ系を除いた『実質内容』のハッシュ（push 判定用）。"""
    def strip(obj):
        if isinstance(obj, dict):
            return {k: strip(v) for k, v in obj.items()
                    if k not in ("measured_at", "generated_at", "signature", "wallSeconds",
                                 "pingLatencyMs", "latency_ms", "lastPayoutAgeMin", "ttftS")}
        if isinstance(obj, list):
            return [strip(v) for v in obj]
        return obj
    return hashlib.sha256(json.dumps(strip(state), ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:16]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--wallet", default=DEFAULT_WALLET)
    ap.add_argument("--print", dest="do_print", action="store_true", help="JSON を stdout（ファイル書込なし）")
    ap.add_argument("--signature-only", action="store_true")
    ap.add_argument("--no-probe", action="store_true", help="推論スループット probe をスキップ（速い）")
    ap.add_argument("--deploy", action="store_true",
                    help="実測スナップショットを git commit/push して Pages を再ビルド（署名変化 & 最小間隔を満たすときだけ）")
    ap.add_argument("--force-deploy", action="store_true", help="署名・最小間隔に関係なく push する")
    ap.add_argument("--min-deploy-interval-min", type=int, default=120, help="--deploy の最小 push 間隔（分）")
    args = ap.parse_args()

    if os.path.exists(LOCK_FILE):
        try:
            age = time.time() - os.path.getmtime(LOCK_FILE)
            if age < 600:
                print(f"[skip] 前回の収集が実行中 (lock age {age:.0f}s)")
                return 0
        except OSError:
            pass
    open(LOCK_FILE, "w").write(str(int(time.time())))

    global INFERENCE_NODES
    if args.no_probe:
        INFERENCE_NODES = []

    try:
        # 各収集は独立 → 並列実行（直列だと blockindex+probe+pool で 10 分超になる）
        from concurrent.futures import ThreadPoolExecutor

        with ThreadPoolExecutor(max_workers=6) as ex:
            def safe(fn, *a):
                try:
                    return fn(*a)
                except Exception as exc:  # noqa: BLE001
                    return {"ok": False, "source": getattr(fn, "__name__", "?"),
                            "measured_at": iso_now(),
                            "error": f"{type(exc).__name__}: {str(exc)[:200]}"}

            f_chain = ex.submit(safe, collect_chain, args.wallet)
            f_pool = ex.submit(safe, collect_pool, args.wallet)
            f_db = ex.submit(safe, collect_db)
            f_content = ex.submit(safe, collect_content)
            f_watcher = ex.submit(safe, collect_watcher)
            f_machines = ex.submit(safe, collect_machines)
            state = {
                "generated_at": iso_now(),
                "generated_at_jst": now_jst(),
                "schema": "corestation-live/1",
                "chain": f_chain.result(),
                "pool": f_pool.result(),
                "db": f_db.result(),
                "content": f_content.result(),
                "watcher": f_watcher.result(),
                "machines": f_machines.result(),
            }
    finally:
        try:
            os.remove(LOCK_FILE)
        except OSError:
            pass
    if not args.do_print:
        append_history(state)
    state["tls"] = {"note": TLS_NOTE or "n/a", "measured_at": iso_now()}
    state["staleness"] = staleness_summary(state)
    state["deployGate"] = {"minIntervalMin": args.min_deploy_interval_min,
                           "deployFlag": bool(args.deploy)}
    state["signature"] = signature_of(state)

    if args.do_print or args.signature_only:
        if args.signature_only:
            print(state["signature"])
        else:
            print(json.dumps(state, ensure_ascii=False, indent=2))
        return 0

    os.makedirs(DATA_DIR, exist_ok=True)
    tmp = OUT_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    os.replace(tmp, OUT_FILE)

    if args.deploy:
        res = deploy_snapshot(state, args.force_deploy, args.min_deploy_interval_min)
        state["deploy"] = res
        with open(OUT_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        print(f"[deploy] pushed={res.get('pushed')} reason={res.get('reason', '-')} "
              f"sig={(res.get('signature') or '')[:12]}")

    ch = state["chain"]
    db = state["db"]
    mc = (state.get("machines") or {}).get("data") or {}
    print(f"[live] chain={'OK' if ch.get('ok') else 'NG'} "
          f"height={(ch.get('data') or {}).get('blockHeight')} "
          f"earned24h={(ch.get('data') or {}).get('earnedXcb24h')} "
          f"db={'OK' if db.get('ok') else 'NG'} nodes={len(mc.get('nodes', []))} "
          f"rigReporters={mc.get('rigReporterCount')} sig={state['signature']} -> {OUT_FILE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
