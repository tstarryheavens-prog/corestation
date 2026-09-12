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

def run_all(wallet=DEFAULT_WALLET):
    print("=" * 60)
    print(f"Starting Full Archival Sync for Wallet: {wallet}")
    print("=" * 60)
    init_db()
    sync_daily_transactions(wallet)
    sync_application_transactions(wallet)
    sync_latest_rates()
    # Save historical rates for JPY and USD
    sync_historical_rates("XCB", "JPY", days=90)
    sync_historical_rates("CTN", "JPY", days=90)
    sync_historical_rates("XCB", "USD", days=90)
    sync_historical_rates("CTN", "USD", days=90)
    sync_workers(wallet)
    print("=" * 60)
    print("Full Archival Sync Completed Successfully!")
    print("=" * 60)

if __name__ == "__main__":
    w = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_WALLET
    run_all(w)
