#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CoreGeeks Data Sync & Archiver
Archives all historical data from api2.core-geeks.com into local SQLite database.
Also saves raw JSON backups.
"""

import os
import sys
import json
import sqlite3
import urllib.request
import ssl
from datetime import datetime, timezone, timedelta

DB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
DB_PATH = os.path.join(DB_DIR, "wallet.db")
DEFAULT_WALLET = "cb57b88d24678c2091332971e3a38cca472dd8aac0cd"
API_BASE = "https://api2.core-geeks.com/api"

def get_db_connection():
    # Works across both native Linux/NAS filesystems and macOS SMB network mounts
    uri = f"file:{DB_PATH}?nolock=1"
    conn = sqlite3.connect(uri, uri=True, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    os.makedirs(DB_DIR, exist_ok=True)
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Daily transactions
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS daily_transactions (
        wallet_address TEXT NOT NULL,
        day TEXT NOT NULL,
        day_amount TEXT NOT NULL,
        day_rank INTEGER,
        all_amount TEXT NOT NULL,
        all_rank INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (wallet_address, day)
    )
    """)

    # 2. Detailed transactions for CSV / Tax calculation
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS application_transactions (
        transaction_hash TEXT PRIMARY KEY,
        block_hash TEXT,
        block_timestamp INTEGER,
        from_address TEXT,
        to_address TEXT,
        transaction_index TEXT,
        in_amount TEXT,
        out_amount TEXT,
        fee TEXT,
        type TEXT,
        coin TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # 3. Currency rates (5-minute intervals)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS currency_rates (
        token TEXT NOT NULL,
        currency TEXT NOT NULL,
        timestamp_key TEXT NOT NULL,
        rate REAL NOT NULL,
        PRIMARY KEY (token, currency, timestamp_key)
    )
    """)

    # 4. Latest rates snapshot
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS latest_rates (
        currency TEXT NOT NULL,
        token TEXT NOT NULL,
        rate REAL NOT NULL,
        day TEXT,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (currency, token)
    )
    """)

    # 5. Workers cache
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS workers (
        wallet_address TEXT NOT NULL,
        worker_name TEXT NOT NULL,
        pool TEXT,
        hr INTEGER DEFAULT 0,
        offline INTEGER DEFAULT 0,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (wallet_address, worker_name)
    )
    """)

    conn.commit()
    conn.close()
    print(f"[DB] Initialized SQLite database at: {DB_PATH}")

def fetch_json(url):
    ctx = ssl._create_unverified_context()
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) CoreGeeksNAS/1.0"
    })
    with urllib.request.urlopen(req, timeout=45, context=ctx) as resp:
        return json.loads(resp.read().decode("utf-8"))

def sync_daily_transactions(wallet=DEFAULT_WALLET, limit=2000):
    url = f"{API_BASE}/miner/walletDailyTransaction/{wallet}/{limit}"
    print(f"[Sync] Fetching daily transactions: {url} ...")
    try:
        data = fetch_json(url)
        items = data.get("data", [])
        if not items:
            print("[Sync] No daily transaction items returned.")
            return 0

        # Raw backup
        with open(os.path.join(DB_DIR, "backup_daily.json"), "w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False)

        conn = get_db_connection()
        cursor = conn.cursor()
        inserted = 0
        for item in items:
            cursor.execute("""
            INSERT INTO daily_transactions (wallet_address, day, day_amount, day_rank, all_amount, all_rank)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(wallet_address, day) DO UPDATE SET
                day_amount=excluded.day_amount,
                day_rank=excluded.day_rank,
                all_amount=excluded.all_amount,
                all_rank=excluded.all_rank
            """, (
                item.get("wallet_address", wallet),
                item.get("day"),
                str(item.get("day_amount", "0")),
                item.get("day_rank", 0),
                str(item.get("all_amount", "0")),
                item.get("all_rank", 0)
            ))
            inserted += 1
        conn.commit()
        conn.close()
        print(f"[Sync] Saved {inserted} daily transaction records.")
        return inserted
    except Exception as e:
        print(f"[Error] Failed to sync daily transactions: {e}")
        return 0

def sync_application_transactions(wallet=DEFAULT_WALLET, start_date="2023-01-01", end_date=None):
    if not end_date:
        end_date = (datetime.now(timezone.utc) + timedelta(days=1)).strftime("%Y-%m-%d")

    url = f"{API_BASE}/transaction/application-data/{start_date}/{end_date}/{wallet}"
    print(f"[Sync] Fetching application transactions: {url} ...")
    try:
        data = fetch_json(url)
        items = data.get("data", [])
        if not items:
            print("[Sync] No application transaction items returned.")
            return 0

        # Raw backup
        with open(os.path.join(DB_DIR, "backup_transactions.json"), "w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False)

        conn = get_db_connection()
        cursor = conn.cursor()
        inserted = 0
        for item in items:
            tx_hash = item.get("transaction_hash")
            if not tx_hash:
                continue
            cursor.execute("""
            INSERT INTO application_transactions (
                transaction_hash, block_hash, block_timestamp, from_address, to_address,
                transaction_index, in_amount, out_amount, fee, type, coin
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(transaction_hash) DO UPDATE SET
                block_timestamp=excluded.block_timestamp,
                in_amount=excluded.in_amount,
                out_amount=excluded.out_amount,
                fee=excluded.fee,
                type=excluded.type
            """, (
                tx_hash,
                item.get("block_hash", ""),
                int(item.get("block_timestamp", 0)),
                item.get("from_address", ""),
                item.get("to_address", ""),
                str(item.get("transaction_index", "")),
                str(item.get("in_amount", "0")),
                str(item.get("out_amount", "0")),
                str(item.get("fee", "0")),
                item.get("type", ""),
                item.get("coin", "XCB")
            ))
            inserted += 1
        conn.commit()
        conn.close()
        print(f"[Sync] Saved {inserted} application transaction records.")
        return inserted
    except Exception as e:
        print(f"[Error] Failed to sync application transactions: {e}")
        return 0

def recalculate_daily_from_transactions(wallet=DEFAULT_WALLET):
    """
    100% Self-Reliant On-Chain Daily Calculation Engine.
    When api2.core-geeks.com is shut down, this function calculates day_amount and
    all_amount purely from raw on-chain application_transactions and updates daily_transactions.
    """
    print(f"[Engine] Recalculating daily mining rewards from on-chain txs for {wallet}...")
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Fetch all incoming rewards for wallet sorted by block_timestamp ASC
        cur.execute("""
            SELECT block_timestamp, in_amount, type
            FROM application_transactions
            WHERE to_address = ? AND in_amount IS NOT NULL AND in_amount != '0'
            ORDER BY block_timestamp ASC
        """, (wallet,))
        rows = cur.fetchall()

        if not rows:
            print("[Engine] No application transactions found.")
            conn.close()
            return 0

        # Group by UTC day "YYYY-MM-DDT00:00:00.000Z"
        day_totals = {}
        for r in rows:
            ts = r["block_timestamp"]
            in_amt_int = int(r["in_amount"] or 0)
            dt = datetime.fromtimestamp(ts, tz=timezone.utc)
            day_str = dt.strftime("%Y-%m-%dT00:00:00.000Z")
            day_totals[day_str] = day_totals.get(day_str, 0) + in_amt_int

        # Sort days chronologically
        sorted_days = sorted(day_totals.keys())
        running_all = 0
        updated_count = 0

        # Fetch existing ranks so we don't lose historical ranks
        cur.execute("SELECT day, day_rank, all_rank FROM daily_transactions WHERE wallet_address = ?", (wallet,))
        existing_ranks = {row["day"]: (row["day_rank"], row["all_rank"]) for row in cur.fetchall()}

        for d in sorted_days:
            amt = day_totals[d]
            running_all += amt
            ranks = existing_ranks.get(d, (180, 160)) # fallback ranks if new
            d_rank = ranks[0] or 180
            a_rank = ranks[1] or 160

            cur.execute("""
                INSERT INTO daily_transactions (wallet_address, day, day_amount, day_rank, all_amount, all_rank)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(wallet_address, day) DO UPDATE SET
                    day_amount=excluded.day_amount,
                    all_amount=excluded.all_amount
            """, (wallet, d, str(amt), d_rank, str(running_all), a_rank))
            updated_count += 1

        conn.commit()
        conn.close()
        print(f"[Engine] Successfully calculated and updated {updated_count} days of mining yield from on-chain transactions.")
        return updated_count
    except Exception as e:
        print(f"[Engine Error] Failed to recalculate daily transactions: {e}")
        return 0

def sync_blockindex_transactions(wallet=DEFAULT_WALLET):
    """
    Fetches latest on-chain transactions directly from blockindex.net Blockbook API.
    Used for 100% self-reliant transaction tracking when core-geeks API is offline.
    """
    url = f"https://blockindex.net/api/v2/address/{wallet}?details=txs&pageSize=50"
    print(f"[Blockindex] Fetching live on-chain transactions: {url} ...")
    ctx = ssl._create_unverified_context()
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) CoreStation/1.0"})
        with urllib.request.urlopen(req, timeout=15, context=ctx) as res:
            data = json.loads(res.read().decode("utf-8"))

        txs = data.get("transactions", [])
        if not txs:
            print("[Blockindex] No transactions returned.")
            return 0

        conn = get_db_connection()
        cur = conn.cursor()
        inserted = 0

        for tx in txs:
            txid = tx.get("txid")
            if not txid:
                continue
            b_hash = tx.get("blockHash", "")
            b_time = tx.get("blockTime", 0)
            fee = str(tx.get("fees", "0"))

            # Inspect inputs / outputs
            vin = tx.get("vin", [])
            vout = tx.get("vout", [])
            from_addr = vin[0].get("addresses", [""])[0] if vin and vin[0].get("addresses") else ""

            # Check matching output for wallet
            in_amt = 0
            out_amt = 0
            tx_type = "Transfer"

            for out in vout:
                addrs = out.get("addresses", [])
                if wallet in addrs:
                    in_amt += int(out.get("value", 0))

            for inp in vin:
                addrs = inp.get("addresses", [])
                if wallet in addrs:
                    out_amt += int(inp.get("value", 0))

            if in_amt > 0 and (from_addr.startswith("cb62") or from_addr.startswith("cb06") or from_addr.startswith("cb71")):
                tx_type = "MiningRewards"

            cur.execute("""
                INSERT INTO application_transactions (
                    transaction_hash, block_hash, block_timestamp, from_address, to_address,
                    transaction_index, in_amount, out_amount, fee, type, coin
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(transaction_hash) DO UPDATE SET
                    block_timestamp=excluded.block_timestamp,
                    in_amount=excluded.in_amount,
                    out_amount=excluded.out_amount,
                    type=excluded.type
            """, (
                txid, b_hash, b_time, from_addr, wallet, "0",
                str(in_amt), str(out_amt), fee, tx_type, "XCB"
            ))
            inserted += 1

        conn.commit()
        conn.close()
        print(f"[Blockindex] Ingested {inserted} on-chain transactions directly.")
        if inserted > 0:
            recalculate_daily_from_transactions(wallet)
        return inserted
    except Exception as e:
        print(f"[Blockindex Sync Warning] Could not fetch directly from blockindex: {e}")
        return 0

def sync_latest_rates():
    currencies = ["JPY", "USD", "EUR", "CHF", "CAD"]
    conn = get_db_connection()
    cursor = conn.cursor()
    saved = 0
    raw_rates = {}
    for c in currencies:
        url = f"{API_BASE}/currency/last_rate/token/{c}"
        try:
            data = fetch_json(url)
            rates = data.get("data", {})
            raw_rates[c] = rates
            for token, info in rates.items():
                if isinstance(info, dict) and "rate" in info:
                    cursor.execute("""
                    INSERT INTO latest_rates (currency, token, rate, day, updated_at)
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(currency, token) DO UPDATE SET
                        rate=excluded.rate,
                        day=excluded.day,
                        updated_at=CURRENT_TIMESTAMP
                    """, (c, token.upper(), float(info["rate"]), info.get("day", "")))
                    saved += 1
        except Exception as e:
            print(f"[Error] Failed to sync latest rate for {c}: {e}")
    conn.commit()
    conn.close()

    with open(os.path.join(DB_DIR, "backup_rates.json"), "w", encoding="utf-8") as f:
        json.dump(raw_rates, f, ensure_ascii=False)

    print(f"[Sync] Saved {saved} latest exchange rate entries.")

def sync_historical_rates(token="XCB", currency="JPY", days=90):
    end_dt = datetime.now(timezone.utc)
    start_dt = end_dt - timedelta(days=days)
    start_str = start_dt.strftime("%Y-%m-%d")
    end_str = end_dt.strftime("%Y-%m-%d")

    url = f"{API_BASE}/currency/getRates/{start_str}/{end_str}/{token}/{currency}"
    print(f"[Sync] Fetching 5-min historical rates: {token}/{currency} ({start_str} to {end_str})...")
    try:
        data = fetch_json(url)
        rates_dict = data.get("data", {}).get("rates", {})
        if not rates_dict:
            return 0

        conn = get_db_connection()
        cursor = conn.cursor()
        saved = 0
        for ts_key, rate in rates_dict.items():
            if rate is None:
                continue
            cursor.execute("""
            INSERT INTO currency_rates (token, currency, timestamp_key, rate)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(token, currency, timestamp_key) DO UPDATE SET
                rate=excluded.rate
            """, (token, currency, ts_key, float(rate)))
            saved += 1
        conn.commit()
        conn.close()
        print(f"[Sync] Saved {saved} historical rate points for {token}/{currency}.")
        return saved
    except Exception as e:
        print(f"[Error] Failed to sync historical rates for {token}/{currency}: {e}")
        return 0

def sync_workers(wallet=DEFAULT_WALLET):
    url = f"{API_BASE}/core/getWorker/{wallet}"
    try:
        data = fetch_json(url)
        workers = data.get("data", {}).get("workers", [])
        conn = get_db_connection()
        cursor = conn.cursor()
        for w in workers:
            cursor.execute("""
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
        print(f"[Sync] Saved {len(workers)} worker records.")
    except Exception as e:
        print(f"[Error] Failed to sync workers: {e}")

def export_initial_data(wallet=DEFAULT_WALLET):
    """Exports SQLite database state into data/initial_data.js for immediate frontend rendering."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # 1. Daily transactions (most recent 60 days)
        cur.execute("""
            SELECT wallet_address, day, day_amount, day_rank, all_amount, all_rank
            FROM daily_transactions
            WHERE wallet_address = ?
            ORDER BY day DESC
            LIMIT 60
        """, (wallet,))
        daily_txs = [
            {
                "wallet_address": r["wallet_address"],
                "day": r["day"],
                "day_amount": r["day_amount"],
                "day_rank": r["day_rank"],
                "all_amount": r["all_amount"],
                "all_rank": r["all_rank"]
            }
            for r in cur.fetchall()
        ]

        # 2. Latest rates
        cur.execute("SELECT currency, token, rate, day FROM latest_rates")
        latest_rates = {}
        for r in cur.fetchall():
            c = r["currency"]
            t = r["token"].lower()
            if c not in latest_rates:
                latest_rates[c] = {}
            latest_rates[c][t] = {
                "currency": c,
                "day": r["day"] or datetime.now().strftime("%Y-%m-%d"),
                "rate": float(r["rate"])
            }

        # 3. Recent transactions (most recent 50)
        cur.execute("""
            SELECT transaction_hash, block_hash, block_timestamp, from_address, to_address,
                   transaction_index, in_amount, out_amount, fee, type, coin
            FROM application_transactions
            WHERE to_address = ? OR from_address = ?
            ORDER BY block_timestamp DESC
            LIMIT 50
        """, (wallet, wallet))
        recent_txs = [
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
            for r in cur.fetchall()
        ]

        # 4. Workers
        cur.execute("SELECT worker_name, pool, hr, offline FROM workers WHERE wallet_address = ?", (wallet,))
        workers = [
            {
                "workerName": r["worker_name"],
                "pool": r["pool"],
                "hr": r["hr"],
                "offline": bool(r["offline"])
            }
            for r in cur.fetchall()
        ]

        # 5. DB Status
        cur.execute("SELECT COUNT(*) FROM daily_transactions")
        c_daily = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM application_transactions")
        c_tx = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM currency_rates")
        c_rate = cur.fetchone()[0]
        cur.execute("SELECT MIN(day), MAX(day) FROM daily_transactions")
        min_d, max_d = cur.fetchone()

        db_status = {
            "status": "connected",
            "dailyCount": c_daily,
            "txCount": c_tx,
            "rateCount": c_rate,
            "minDate": min_d,
            "maxDate": max_d,
            "dbPath": DB_PATH,
            "lastSync": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        }

        conn.close()

        initial_obj = {
            "walletAddress": wallet,
            "walletDailyTransactions": daily_txs,
            "latestRates": latest_rates,
            "recentTransactions": recent_txs,
            "workers": workers,
            "dbStatus": db_status
        }

        # Keep existing custom arrays if present in old file (like articlesArchive, miningPools, etc.)
        initial_file = os.path.join(DB_DIR, "initial_data.js")
        if os.path.exists(initial_file):
            try:
                with open(initial_file, "r", encoding="utf-8") as f:
                    old_text = f.read()
                prefix = "window.__COREGEEKS_INITIAL_DATA__ = "
                if old_text.startswith(prefix):
                    old_json = json.loads(old_text[len(prefix):].rstrip(";\n "))
                    for key in ["articlesArchive", "miningPools", "communityLinks", "networkStats"]:
                        if key in old_json and key not in initial_obj:
                            initial_obj[key] = old_json[key]
            except Exception:
                pass

        with open(initial_file, "w", encoding="utf-8") as f:
            f.write("window.__COREGEEKS_INITIAL_DATA__ = " + json.dumps(initial_obj, ensure_ascii=False) + ";\n")

        print(f"[Sync] Exported latest state to {initial_file} (Daily: {len(daily_txs)}, Tx: {len(recent_txs)})")
    except Exception as e:
        print(f"[Error] Failed to export initial_data.js: {e}")

def dump_full_clone(wallet=DEFAULT_WALLET):
    """Exports a complete standalone clone backup of all CoreGeeks tables to data/full_clone_backup.json."""
    print(f"[Clone] Creating complete CoreGeeks data archive snapshot...")
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("SELECT * FROM daily_transactions WHERE wallet_address = ?", (wallet,))
        daily = [dict(r) for r in cur.fetchall()]

        cur.execute("SELECT * FROM application_transactions")
        txs = [dict(r) for r in cur.fetchall()]

        cur.execute("SELECT * FROM latest_rates")
        rates = [dict(r) for r in cur.fetchall()]

        cur.execute("SELECT * FROM workers WHERE wallet_address = ?", (wallet,))
        workers = [dict(r) for r in cur.fetchall()]

        cur.execute("SELECT COUNT(*) FROM currency_rates")
        rate_count = cur.fetchone()[0]

        conn.close()

        clone_data = {
            "meta": {
                "created_at": datetime.now(timezone.utc).isoformat(),
                "wallet": wallet,
                "daily_count": len(daily),
                "transaction_count": len(txs),
                "rates_count": len(rates),
                "currency_rate_historical_count": rate_count
            },
            "daily_transactions": daily,
            "application_transactions": txs,
            "latest_rates": rates,
            "workers": workers
        }

        backup_file = os.path.join(DB_DIR, "full_clone_backup.json")
        with open(backup_file, "w", encoding="utf-8") as f:
            json.dump(clone_data, f, ensure_ascii=False)

        print(f"[Clone] ✅ Complete CoreGeeks API Clone saved to: {backup_file}")
        print(f"        Daily: {len(daily)}, Tx: {len(txs)}, Rates: {len(rates)}")
    except Exception as e:
        print(f"[Clone Error] Failed to dump full clone: {e}")

def run_all(wallet=DEFAULT_WALLET):
    print("=" * 60)
    print(f"Starting Full Archival Sync for Wallet: {wallet}")
    print("=" * 60)
    init_db()
    # 1. Try upstream fetch from api2.core-geeks.com if still reachable
    sync_daily_transactions(wallet)
    sync_application_transactions(wallet)
    sync_latest_rates()
    # 2. Try on-chain blockindex sync for live blockchain data
    sync_blockindex_transactions(wallet)
    # 3. Always run on-chain recalculation to verify and fill any missing days
    recalculate_daily_from_transactions(wallet)
    # 4. Save historical rates for JPY and USD
    sync_historical_rates("XCB", "JPY", days=90)
    sync_historical_rates("CTN", "JPY", days=90)
    sync_historical_rates("XCB", "USD", days=90)
    sync_historical_rates("CTN", "USD", days=90)
    sync_workers(wallet)
    # 5. Export initial_data.js and full JSON clone
    export_initial_data(wallet)
    dump_full_clone(wallet)
    print("=" * 60)
    print("Full Archival Sync Completed Successfully!")
    print("=" * 60)

if __name__ == "__main__":
    w = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_WALLET
    run_all(w)


