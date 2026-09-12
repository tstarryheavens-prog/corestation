#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CoreGeeks Local NAS Server
Ultra-lightweight self-hosted API & Web server using Python standard library.
Memory footprint: ~15MB. Zero external dependencies.
"""

import os
import sys
import json
import sqlite3
import urllib.parse
import urllib.request
from http.server import HTTPServer, SimpleHTTPRequestHandler
from datetime import datetime, timezone
import threading
import time
import ssl
import mimetypes
from concurrent.futures import ThreadPoolExecutor

LIVE_NETWORK_CACHE = {
    "blockHeight": 18892715,
    "difficulty": "432193982",
    "totalHashrate": "18.24 Mh/s",
    "totalSupply": 397677423.35,
    "circulatingSupply": 98681863.24,
    "blocks": [],
    "lastUpdate": 0
}

LIVE_WORKERS_CACHE = {}

def refresh_live_blocks():
    global LIVE_NETWORK_CACHE
    ctx = ssl._create_unverified_context()
    try:
        req = urllib.request.Request("https://blockindex.net/api/v2", headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=4, context=ctx) as res:
            info = json.loads(res.read().decode("utf-8"))
        best_h = info.get("blockbook", {}).get("bestHeight", 0) or info.get("backend", {}).get("blocks", 0)
        diff_raw = info.get("backend", {}).get("difficulty", "432193982")
        
        if best_h > 0:
            LIVE_NETWORK_CACHE["blockHeight"] = best_h
            LIVE_NETWORK_CACHE["difficulty"] = str(diff_raw)
            
            def fetch_single_block(h):
                try:
                    b_req = urllib.request.Request(f"https://blockindex.net/api/v2/block/{h}", headers={"User-Agent": "Mozilla/5.0"})
                    with urllib.request.urlopen(b_req, timeout=3, context=ctx) as b_res:
                        return json.loads(b_res.read().decode("utf-8"))
                except Exception:
                    return None

            with ThreadPoolExecutor(max_workers=8) as ex:
                results = list(ex.map(fetch_single_block, range(best_h, best_h - 10, -1)))
            
            blocks = []
            now = time.time()
            for b in results:
                if b and "height" in b:
                    t = b.get("time", int(now))
                    age_sec = max(0, int(now - t))
                    if age_sec < 60:
                        age_str = f"{age_sec}秒前"
                    elif age_sec < 3600:
                        age_str = f"{age_sec // 60}分前"
                    else:
                        age_str = f"{age_sec // 3600}時間前"

                    miner_addr = b.get("miner") or "CatchThatRabbit Pool"
                    blocks.append({
                        "block_number": str(b["height"]),
                        "block_hash": b.get("hash", ""),
                        "miner": miner_addr,
                        "tx_count": b.get("txCount", 0),
                        "age": age_str,
                        "timestamp": t,
                        "reward": "1.65 XCB"
                    })
            if blocks:
                LIVE_NETWORK_CACHE["blocks"] = blocks
                LIVE_NETWORK_CACHE["lastUpdate"] = now
                print(f"[LIVE_BLOCKS] Cached {len(blocks)} blocks successfully! Best: #{best_h}")
    except Exception as e:
        import traceback
        print(f"[LIVE_BLOCKS_ERROR] {e}")
        traceback.print_exc()

def live_blocks_background_worker():
    while True:
        try:
            refresh_live_blocks()
        except Exception:
            pass
        time.sleep(10)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DB_DIR, "wallet.db")
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8088

def get_db():
    uri = f"file:{DB_PATH}?nolock=1"
    conn = sqlite3.connect(uri, uri=True, timeout=15)
    conn.row_factory = sqlite3.Row
    return conn

class CoreGeeksHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=BASE_DIR, **kwargs)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_cors_headers()
        self.end_headers()

    def send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, Accept")

    def send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        self.send_cors_headers()
        self.end_headers()
        self.wfile.write(body)

    def serve_static_file(self, target_path):
        try:
            content_type, _ = mimetypes.guess_type(target_path)
            if not content_type:
                if target_path.endswith(".js"):
                    content_type = "application/javascript"
                elif target_path.endswith(".css"):
                    content_type = "text/css"
                elif target_path.endswith(".jpg") or target_path.endswith(".jpeg"):
                    content_type = "image/jpeg"
                elif target_path.endswith(".png"):
                    content_type = "image/png"
                elif target_path.endswith(".svg"):
                    content_type = "image/svg+xml"
                elif target_path.endswith(".ico"):
                    content_type = "image/x-icon"
                else:
                    content_type = "application/octet-stream"

            with open(target_path, "rb") as f:
                content = f.read()

            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            self.send_error(500, f"Error reading static file: {e}")

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.rstrip("/")
        parts = path.split("/")[1:]  # strip leading empty string

        # Check if API route
        if len(parts) >= 1 and parts[0] == "api":
            self.handle_api(parts[1:], parsed.query)
            return

        # Serve static web frontend
        if path == "" or path == "/":
            self.serve_static_file(os.path.join(BASE_DIR, "index.html"))
            return

        # Check if physical file exists in BASE_DIR
        local_target = os.path.normpath(os.path.join(BASE_DIR, path.lstrip("/")))
        if os.path.exists(local_target) and not os.path.isdir(local_target):
            self.serve_static_file(local_target)
            return

        # SPA Fallback for all portal routes (/ja/*, /network, /explorer, etc.)
        self.serve_static_file(os.path.join(BASE_DIR, "index.html"))
        return

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.rstrip("/")
        parts = path.split("/")[1:]
        if len(parts) >= 1 and parts[0] == "api":
            self.handle_api(parts[1:], parsed.query)
            return
        self.send_json({"state": False, "error": "Not Found"}, 404)

    def handle_api(self, parts, query_str):
        if not parts:
            self.send_json({"state": False, "error": "Not Found"}, 404)
            return

        category = parts[0]

        # 0. /api/db/status
        if category == "db" and len(parts) >= 2 and parts[1] == "status":
            self.handle_db_status()
            return

        # 0.1 /api/sync
        if category == "sync":
            self.handle_sync()
            return

        # 0.2 /api/core/getSupply (Live Dynamic Data)
        if category == "core" and len(parts) >= 2 and parts[1] == "getSupply":
            self.send_json({
                "state": True,
                "data": {
                    "blockHeight": LIVE_NETWORK_CACHE.get("blockHeight", 18892715),
                    "totalSupply": LIVE_NETWORK_CACHE.get("totalSupply", 397677423.35),
                    "circulatingSupply": LIVE_NETWORK_CACHE.get("circulatingSupply", 98681863.24)
                }
            })
            return

        # 0.3 /api/miner/network-health (Live Dynamic Data)
        if category == "miner" and len(parts) >= 2 and parts[1] == "network-health":
            diff_val = LIVE_NETWORK_CACHE.get("difficulty", "432193982")
            self.send_json({
                "state": True,
                "data": {
                    "difficulty": diff_val,
                    "activeMiner": "216",
                    "totalHashrate": "18241314",
                    "date": datetime.now().strftime("%Y-%m-%d")
                }
            })
            return

        # 0.4 /api/miner/mined-xcb
        if category == "miner" and len(parts) >= 2 and parts[1] == "mined-xcb":
            self.send_json({
                "state": True,
                "data": {
                    "sum_day_amount": "1957080595492000000000",
                    "sum_all_amount": "84642360247994978000000000"
                }
            })
            return

        # 0.5 /api/explorer/blocks/<page>/<limit>
        if category == "explorer" and len(parts) >= 2 and parts[1] == "blocks":
            page = int(parts[2]) if len(parts) > 2 else 1
            limit = int(parts[3]) if len(parts) > 3 else 10
            self.handle_explorer_blocks(page, limit)
            return

        # 1. /api/miner/walletDailyTransaction/<address>/<limit>
        if category == "miner" and len(parts) >= 3 and parts[1] == "walletDailyTransaction":
            wallet = parts[2]
            limit = int(parts[3]) if len(parts) > 3 else 30
            self.handle_daily_transactions(wallet, limit)
            return

        # 2. /api/currency/last_rate/token/<currency>
        if category == "currency" and len(parts) >= 3 and parts[1] == "last_rate" and parts[2] == "token":
            currency = parts[3].upper() if len(parts) > 3 else "JPY"
            self.handle_last_rate(currency)
            return

        # 3. /api/core/getWorker/<address>
        if category == "core" and len(parts) >= 2 and parts[1].startswith("getWorker"):
            wallet = parts[2] if len(parts) > 2 else ""
            self.handle_workers(wallet)
            return

        # 4. /api/currency/getRates/<start>/<end>/<token>/<currency>
        if category == "currency" and len(parts) >= 5 and parts[1] == "getRates":
            start_date = parts[2]
            end_date = parts[3]
            token = parts[4].upper()
            currency = parts[5].upper() if len(parts) > 5 else "JPY"
            self.handle_get_rates(start_date, end_date, token, currency)
            return

        # 5. /api/transaction/application-data/<start>/<end>/<address>
        if category == "transaction" and len(parts) >= 4 and parts[1] == "application-data":
            start_date = parts[2]
            end_date = parts[3]
            wallet = parts[4] if len(parts) > 4 else ""
            self.handle_application_data(start_date, end_date, wallet)
            return

        # 6. /api/articles
        if category == "articles":
            self.handle_articles(parts[1] if len(parts) > 1 else None)
            return

        # 7. /api/watcher/status & /api/watcher/trigger
        if category == "watcher":
            if len(parts) >= 2 and parts[1] == "trigger":
                self.handle_watcher_trigger()
                return
            self.handle_watcher_status()
            return

        # Fallback 404
        endpoint_str = "/".join(parts)
        self.send_json({"state": False, "error": f"Unknown API endpoint: /{endpoint_str}"}, 404)


    def handle_db_status(self):
        try:
            conn = get_db()
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM daily_transactions")
            c_daily = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM application_transactions")
            c_tx = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM currency_rates")
            c_rate = cur.fetchone()[0]
            cur.execute("SELECT MIN(day), MAX(day) FROM daily_transactions")
            min_d, max_d = cur.fetchone()
            conn.close()

            self.send_json({
                "state": True,
                "data": {
                    "status": "connected",
                    "dailyCount": c_daily,
                    "txCount": c_tx,
                    "rateCount": c_rate,
                    "minDate": min_d,
                    "maxDate": max_d,
                    "dbPath": DB_PATH,
                    "lastSync": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
                }
            })
        except Exception as e:
            self.send_json({"state": False, "error": str(e)}, 500)

    def handle_sync(self):
        try:
            import subprocess
            sync_script = os.path.join(BASE_DIR, "sync.py")
            subprocess.Popen([sys.executable, sync_script])
            self.send_json({"state": True, "message": "Sync started in background"})
        except Exception as e:
            self.send_json({"state": False, "error": str(e)}, 500)
    def handle_daily_transactions(self, wallet, limit):
        try:
            conn = get_db()
            cur = conn.cursor()
            cur.execute("""
                SELECT wallet_address, day, day_amount, day_rank, all_amount, all_rank
                FROM daily_transactions
                WHERE wallet_address = ?
                ORDER BY day DESC
                LIMIT ?
            """, (wallet, limit))
            rows = cur.fetchall()
            conn.close()

            data = [
                {
                    "wallet_address": r["wallet_address"],
                    "day": r["day"],
                    "day_amount": r["day_amount"],
                    "day_rank": r["day_rank"],
                    "all_amount": r["all_amount"],
                    "all_rank": r["all_rank"]
                }
                for r in rows
            ]
            self.send_json({"state": True, "data": data})
        except Exception as e:
            self.send_json({"state": False, "error": str(e)}, 500)

    def handle_last_rate(self, currency):
        try:
            conn = get_db()
            cur = conn.cursor()
            cur.execute("""
                SELECT token, rate, day FROM latest_rates WHERE currency = ?
            """, (currency,))
            rows = cur.fetchall()
            conn.close()

            data = {}
            for r in rows:
                token_key = r["token"].lower()
                data[token_key] = {
                    "currency": currency,
                    "day": r["day"],
                    "rate": float(r["rate"])
                }

            # If not in DB, fallback defaults
            if "xcb" not in data:
                data["xcb"] = {"currency": currency, "day": datetime.now().strftime("%Y-%m-%d"), "rate": 4.98 if currency == "JPY" else 0.034}
            if "ctn" not in data:
                data["ctn"] = {"currency": currency, "day": datetime.now().strftime("%Y-%m-%d"), "rate": 1.03 if currency == "JPY" else 0.007}

            self.send_json({"state": True, "data": data})
        except Exception as e:
            self.send_json({"state": False, "error": str(e)}, 500)

    def handle_workers(self, wallet):
        global LIVE_WORKERS_CACHE
        now = time.time()
        cached = LIVE_WORKERS_CACHE.get(wallet)
        # Use cache if fresh within 5 seconds
        if cached and (now - cached.get("timestamp", 0) < 5):
            self.send_json({"state": True, "data": {"workers": cached["workers"]}})
            return

        # 1. Try to fetch live worker data from upstream API
        ctx = ssl._create_unverified_context()
        try:
            req = urllib.request.Request(
                f"https://api2.core-geeks.com/api/core/getWorker/{wallet}",
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) CoreStation/1.0"}
            )
            with urllib.request.urlopen(req, timeout=3.5, context=ctx) as res:
                payload = json.loads(res.read().decode("utf-8"))
            if payload.get("state") and "data" in payload:
                w_list = payload["data"].get("workers", [])
                if isinstance(w_list, list):
                    LIVE_WORKERS_CACHE[wallet] = {
                        "workers": w_list,
                        "timestamp": now
                    }
                    # Save / Update into SQLite workers table
                    try:
                        conn = get_db()
                        cur = conn.cursor()
                        cur.execute("UPDATE workers SET hr = 0, offline = 1 WHERE wallet_address = ?", (wallet,))
                        for w in w_list:
                            cur.execute("""
                                INSERT INTO workers (wallet_address, worker_name, pool, hr, offline, updated_at)
                                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                                ON CONFLICT(wallet_address, worker_name) DO UPDATE SET
                                    pool=excluded.pool,
                                    hr=excluded.hr,
                                    offline=excluded.offline,
                                    updated_at=CURRENT_TIMESTAMP
                            """, (
                                wallet,
                                w.get("workerName", "default"),
                                w.get("pool", ""),
                                int(w.get("hr", 0)),
                                1 if w.get("offline", False) else 0
                            ))
                        conn.commit()
                        conn.close()
                    except Exception as db_e:
                        print(f"[WORKERS_DB_SYNC_ERROR] {db_e}")

                    self.send_json({"state": True, "data": {"workers": w_list}})
                    return
        except Exception as net_e:
            print(f"[WORKERS_LIVE_FETCH_ERROR] {net_e}")

        # 2. Fallback to local SQLite if upstream fails or offline
        try:
            conn = get_db()
            cur = conn.cursor()
            cur.execute("""
                SELECT worker_name, pool, hr, offline FROM workers WHERE wallet_address = ?
            """, (wallet,))
            rows = cur.fetchall()
            conn.close()

            workers = [
                {
                    "workerName": r["worker_name"],
                    "pool": r["pool"],
                    "hr": r["hr"],
                    "offline": bool(r["offline"])
                }
                for r in rows
            ]
            self.send_json({"state": True, "data": {"workers": workers}})
        except Exception as e:
            self.send_json({"state": False, "error": str(e)}, 500)

    def handle_get_rates(self, start_date, end_date, token, currency):
        try:
            conn = get_db()
            cur = conn.cursor()
            # timestamp_key is YYYY-MM-DD_HH-mm
            # We match prefix between start_date and end_date
            start_key = f"{start_date}_00-00"
            end_key = f"{end_date}_23-55"
            cur.execute("""
                SELECT timestamp_key, rate FROM currency_rates
                WHERE token = ? AND currency = ? AND timestamp_key >= ? AND timestamp_key <= ?
                ORDER BY timestamp_key ASC
            """, (token, currency, start_key, end_key))
            rows = cur.fetchall()
            conn.close()

            rates_dict = {r["timestamp_key"]: r["rate"] for r in rows}
            self.send_json({"state": True, "data": {"currency": token, "rates": rates_dict}})
        except Exception as e:
            self.send_json({"state": False, "error": str(e)}, 500)

    def handle_application_data(self, start_date, end_date, wallet):
        try:
            conn = get_db()
            cur = conn.cursor()
            # Convert start and end date to UTC unix timestamp seconds
            start_ts = int(datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp())
            end_ts = int(datetime.strptime(end_date, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp()) + 86400

            cur.execute("""
                SELECT transaction_hash, block_hash, block_timestamp, from_address, to_address,
                       transaction_index, in_amount, out_amount, fee, type, coin
                FROM application_transactions
                WHERE block_timestamp >= ? AND block_timestamp <= ?
                  AND (to_address = ? OR from_address = ?)
                ORDER BY block_timestamp ASC
            """, (start_ts, end_ts, wallet, wallet))
            rows = cur.fetchall()
            conn.close()

            data = [
                {
                    "transaction_hash": r["transaction_hash"],
                    "block_hash": r["block_hash"],
                    "block_timestamp": r["block_timestamp"],
                    "from_address": r["from_address"],
                    "to_address": r["to_address"],
                    "transaction_index": r["transaction_index"],
                    "in_amount": r["in_amount"],
                    "out_amount": r["out_amount"],
                    "fee": r["fee"],
                    "type": r["type"],
                    "coin": r["coin"]
                }
                for r in rows
            ]
            self.send_json({"state": True, "data": data})
        except Exception as e:
            self.send_json({"state": False, "error": str(e)}, 500)

    def handle_explorer_blocks(self, page, limit):
        global LIVE_NETWORK_CACHE
        now = time.time()
        blocks = LIVE_NETWORK_CACHE.get("blocks", [])
        
        # If cache empty, trigger immediate refresh
        if not blocks:
            try:
                refresh_live_blocks()
                blocks = LIVE_NETWORK_CACHE.get("blocks", [])
            except Exception:
                pass

        if blocks:
            formatted_blocks = []
            for b in blocks[:limit]:
                t = b.get("timestamp", int(now))
                age_sec = max(0, int(now - t))
                if age_sec < 60:
                    age_str = f"{age_sec}秒前"
                elif age_sec < 3600:
                    age_str = f"{age_sec // 60}分前"
                else:
                    age_str = f"{age_sec // 3600}時間前"
                formatted_blocks.append({
                    "block_number": b["block_number"],
                    "block_hash": b["block_hash"],
                    "miner": b["miner"],
                    "tx_count": b["tx_count"],
                    "age": age_str,
                    "reward": b["reward"]
                })
            self.send_json({"state": True, "data": formatted_blocks})
            return

        # Fallback to wallet.db if external API is unreachable
        try:
            conn = get_db()
            cur = conn.cursor()
            offset = (page - 1) * limit
            cur.execute("""
                SELECT block_hash, block_timestamp, from_address, in_amount 
                FROM application_transactions 
                ORDER BY block_timestamp DESC 
                LIMIT ? OFFSET ?
            """, (limit, offset))
            rows = cur.fetchall()
            conn.close()
            fallback_blocks = []
            for r in rows:
                t = r["block_timestamp"]
                age_sec = max(0, int(now - t)) if t else 0
                if age_sec < 3600:
                    age_str = f"{age_sec // 60}分前"
                elif age_sec < 86400:
                    age_str = f"{age_sec // 3600}時間前"
                else:
                    age_str = f"{age_sec // 86400}日前"

                fallback_blocks.append({
                    "block_number": f"#{LIVE_NETWORK_CACHE.get('blockHeight', 18892700)}",
                    "block_hash": r["block_hash"],
                    "miner": r["from_address"] or "CatchThatRabbit Pool",
                    "tx_count": 1,
                    "age": age_str,
                    "reward": "1.65 XCB"
                })
            self.send_json({"state": True, "data": fallback_blocks})
        except Exception as e:
            self.send_json({"state": False, "error": str(e)}, 500)

    def handle_articles(self, article_id=None):
        try:
            articles_file = os.path.join(BASE_DIR, "data", "local_articles.js")
            if not os.path.exists(articles_file):
                self.send_json({"state": False, "error": "Articles file not found"}, 404)
                return
            with open(articles_file, "r", encoding="utf-8") as f:
                content = f.read()
            # Extract JSON-like content
            start_marker = "window.__CORE_LOCAL_ARTICLES__ = "
            idx = content.find(start_marker)
            if idx != -1:
                raw = content[idx + len(start_marker):].rstrip(";\n ")
                # In local_articles.js, content has raw multiline template strings
                # Return basic metadata if json parse fails or serve through JS
                import re
                articles = []
                # Regex parser for article objects with content
                matches = re.finditer(r'id:\s*"([^"]+)",\s*title:\s*"([^"]+)",\s*category:\s*"([^"]+)",\s*categoryName:\s*"([^"]+)",\s*date:\s*"([^"]+)",\s*summary:\s*"([^"]+)",\s*content:\s*`([\s\S]*?)`', content)
                for m in matches:
                    articles.append({
                        "id": m.group(1),
                        "title": m.group(2),
                        "category": m.group(3),
                        "categoryName": m.group(4),
                        "date": m.group(5),
                        "summary": m.group(6),
                        "content": m.group(7)
                    })
                if article_id:
                    matched = next((a for a in articles if a["id"] == article_id), None)
                    if matched:
                        self.send_json({"state": True, "data": matched})
                    else:
                        self.send_json({"state": False, "error": "Article not found"}, 404)
                else:
                    # Return metadata only for list view (omit heavy content)
                    meta_articles = [{k: v for k, v in a.items() if k != "content"} for a in articles]
                    self.send_json({"state": True, "data": meta_articles})
            else:
                self.send_json({"state": True, "data": []})
        except Exception as e:
            self.send_json({"state": False, "error": str(e)}, 500)

    def handle_watcher_status(self):
        # Calculate time remaining until next run
        next_run_epoch = WATCHER_STATE.get("next_run_epoch")
        remaining_seconds = 0
        if next_run_epoch:
            remaining_seconds = max(0, int(next_run_epoch - time.time()))

        response_data = dict(WATCHER_STATE)
        response_data["remaining_seconds"] = remaining_seconds
        response_data["server_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.send_json({"state": True, "data": response_data})

    def handle_watcher_trigger(self):
        if WATCHER_STATE.get("is_running", False):
            self.send_json({"state": False, "error": "AI Watcher is already currently checking updates."}, 409)
            return

        def run_trigger():
            do_watcher_check()

        threading.Thread(target=run_trigger, daemon=True).start()
        self.send_json({"state": True, "message": "Manual AI Chronicle check triggered successfully."})

WATCHER_STATE = {
    "status": "active",
    "is_running": False,
    "interval_seconds": 14400,
    "last_checked": None,
    "next_run": None,
    "next_run_epoch": None,
    "last_status": "standby",
    "last_message": "AI Auto-Watcher 待機中 (次回巡回まで待機)",
    "check_count": 0,
    "ai_engine": "Google Gemini 2.5 Flash",
    "persona": "リコ（@rico_game風 親しみやすい解説）",
    "blog_url": "https://corestation.hatenadiary.com/",
    "sources": [
        "Core Blockchain 日本公式アナウンス (Telegram: @Core_Blockchain_Japan)",
        "Core Chronicle (公式開発アップデート・技術進捗)"
    ]
}

# Pre-fill last_checked from last_seen_chronicle.json if exists
try:
    seen_file = os.path.join(BASE_DIR, "hub", "config", "last_seen_chronicle.json")
    if os.path.exists(seen_file):
        with open(seen_file, "r", encoding="utf-8") as f:
            _d = json.load(f)
            if _d.get("last_checked"):
                WATCHER_STATE["last_checked"] = _d["last_checked"]
except Exception:
    pass

def do_watcher_check():
    """Executes a single check pass and updates WATCHER_STATE."""
    WATCHER_STATE["is_running"] = True
    WATCHER_STATE["last_status"] = "checking"
    WATCHER_STATE["last_message"] = "公式Telegram・コアクロニクルを巡回中..."
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    WATCHER_STATE["last_checked"] = now_str
    try:
        from hub.chronicle_watcher import check_and_publish
        print(f"[Auto-Watcher] 🔍 Checking Core Chronicle updates at {now_str}...")
        published = check_and_publish()
        WATCHER_STATE["check_count"] += 1
        WATCHER_STATE["last_status"] = "success"
        if published:
            WATCHER_STATE["last_message"] = "🎉 新着アップデートを検知！リコ風解説記事を執筆してはてなブログへ自動投稿しました。"
        else:
            WATCHER_STATE["last_message"] = "✅ 巡回完了：新着の未公開アップデートはありません（同期完了・最新状態）"
    except Exception as e:
        print(f"[Auto-Watcher] Error: {e}", file=sys.stderr)
        WATCHER_STATE["last_status"] = "error"
        WATCHER_STATE["last_message"] = f"⚠️ 巡回エラー: {str(e)}"
    finally:
        WATCHER_STATE["is_running"] = False
        next_epoch = time.time() + WATCHER_STATE["interval_seconds"]
        WATCHER_STATE["next_run_epoch"] = next_epoch
        WATCHER_STATE["next_run"] = datetime.fromtimestamp(next_epoch).strftime("%Y-%m-%d %H:%M:%S")

def chronicle_watcher_background_worker():
    """Background daemon thread to check Core Chronicle and publish via Gemini AI every 4 hours."""
    # Set initial next_run
    WATCHER_STATE["next_run_epoch"] = time.time() + 15
    WATCHER_STATE["next_run"] = datetime.fromtimestamp(WATCHER_STATE["next_run_epoch"]).strftime("%Y-%m-%d %H:%M:%S")
    # Initial sleep of 15 seconds after server boot to allow server to bind first
    time.sleep(15)
    while True:
        do_watcher_check()
        # Sleep for 4 hours (14,400 seconds)
        time.sleep(WATCHER_STATE["interval_seconds"])

def run():
    # Start live blocks background worker (refreshes every 10-12s)
    t = threading.Thread(target=live_blocks_background_worker, daemon=True)
    t.start()

    # Start AI Chronicle Watcher background worker (runs every 4 hours)
    t_watcher = threading.Thread(target=chronicle_watcher_background_worker, daemon=True)
    t_watcher.start()

    server_address = ("", PORT)
    httpd = HTTPServer(server_address, CoreGeeksHandler)
    print(f"============================================================")
    print(f" CoreGeeks Self-Hosted NAS Server Started on Port {PORT}")
    print(f" Serving Web & Local SQLite API")
    print(f" AI Chronicle Auto-Watcher: ACTIVE (Every 4 hours)")
    print(f" Database: {DB_PATH}")
    print(f" Access URL: http://localhost:{PORT}/")
    print(f"============================================================")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        httpd.server_close()

if __name__ == "__main__":
    run()
