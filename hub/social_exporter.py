#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CoreStation Global Social & Community Exporter
==============================================
Generates high-engagement X (Twitter) threads and Reddit Markdown posts
from CoreStation English engineering benchmarks and post-quantum technical reports.
Dispatches payloads to Make.com Webhook for 100% automated X posting via Buffer.
"""

import os
import sys
import re
import json
import ssl
import urllib.request
import urllib.error
from pathlib import Path

WORKSPACE_DIR = Path("/Volumes/Docker/CoreGeeksEXp")
EN_ARTICLES_DIR = WORKSPACE_DIR / "en/articles"
OUTPUT_DIR = WORKSPACE_DIR / "hub/output"
CONFIG_FILE = WORKSPACE_DIR / "hub/config/social_config.json"

ssl_ctx = ssl._create_unverified_context()

os.makedirs(OUTPUT_DIR, exist_ok=True)
CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)

DEFAULT_WEBHOOK = "https://hook.us2.make.com/1mymkcylqd514tth9tv1nker4p0wnttp"

def load_config() -> dict:
    if CONFIG_FILE.exists():
        try:
            return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"make_webhook_url": DEFAULT_WEBHOOK}

def parse_html_meta(html_path: Path) -> dict:
    text = html_path.read_text(encoding="utf-8")
    title_m = re.search(r"<title>(.*?)</title>", text, re.IGNORECASE)
    desc_m = re.search(r'<meta\s+name="description"\s+content="(.*?)"', text, re.IGNORECASE)
    
    title = title_m.group(1).split("|")[0].strip() if title_m else html_path.stem
    desc = desc_m.group(1).strip() if desc_m else ""
    return {"title": title, "desc": desc}

def generate_social_payload(slug: str, publish: bool = False):
    html_file = EN_ARTICLES_DIR / f"{slug}.html"
    if not html_file.exists():
        print(f"Error: {html_file} not found.", file=sys.stderr)
        return

    meta = parse_html_meta(html_file)
    title = meta["title"]
    desc = meta["desc"]
    url = f"https://corestation.pages.dev/en/articles/{slug}"

    if "ryzen" in slug:
        tweet_1 = "⚡ AMD Ryzen 9 7950X Efficiency Study:\nBenchmarking Catch-22 PoDE on Zen 4. Eco Mode (105W) cuts socket draw by 41% with only 7.8% hashrate drop (2,358 H/s).\n\nHardware benchmarks & PBO settings 👇"
        tweet_2 = "📊 Empirical Power Telemetry:\n• Stock 170W: 2,560 H/s @ 228W socket (0.089W / H/s, 95°C throttle)\n• Eco Mode 105W: 2,358 H/s @ 142W socket (0.060W / H/s, 68°C)\n• +47.8% efficiency gain!"
        tweet_3 = f"🛠️ Silicon Tuning Protocol:\nCurve Optimizer -25 all-core undervolt + DDR5-6000 CL30 memory synchrony stabilizes 4.75 GHz all-core clocks.\n\nFull benchmark telemetry:\n🔗 {url}"
        reddit_title = f"[Hardware Benchmark] AMD Ryzen 9 7950X Catch-22 PoDE Optimization (Stock vs 105W/65W Eco Mode)"
        reddit_body = f"""**Executive Summary:**
In high-tariff electricity environments, raw hashrate is a vanity metric; Joules per kHash is reality. We tested the AMD Ryzen 9 7950X (16C/32T) under Core Blockchain's Catch-22 PoDE consensus algorithm across continuous 48-hour workloads.

**Key Telemetry Results:**
1. **Stock 170W**: 2,560 H/s @ 228W (0.0898 W/(H/s)) - 94.8°C thermal throttling.
2. **Eco Mode 105W (Sweet Spot)**: 2,358 H/s @ 142W (0.0602 W/(H/s)) - 68.2°C rock solid. **47.8% efficiency gain.**
3. **Curve Optimizer**: -25 all-core undervolt sustained 4.75 GHz clocks at only ~1.04V Vcore.

**Full Report, PBO BIOS Settings & Telemetry Charts:**
{url}
"""
    elif "quantum" in slug:
        tweet_1 = "🛡️ Cryptography Architecture Paper:\nWhy Bitcoin & Ethereum ECDSA will fall to Shor's algorithm, and how Core Blockchain implements lattice-based ML-DSA (Dilithium) natively.\n\nPost-quantum security breakdown 👇"
        tweet_2 = "🔬 The Mathematics of Q-Day:\nDiscrete logarithms (secp256k1) collapse in polynomial time O(n³) on FTQC. Lattice Learning With Errors (LWE) offers mathematical intractability against quantum attacks."
        tweet_3 = f"🌐 Catch-22 & Post-Quantum Defense:\nPairing ED448 high-speed signing with ML-DSA lattice keys to guarantee multi-decade security without sacrificing finality.\n\nFull paper:\n🔗 {url}"
        reddit_title = f"[Cryptographic Analysis] Quantum Resistance in Core Blockchain: NIST ML-DSA vs Legacy ECDSA"
        reddit_body = f"""**Abstract & Context:**
While classical ECDSA (secp256k1) secures modern layer-1 networks like Bitcoin and Ethereum, it is fundamentally vulnerable to Shor's algorithm on fault-tolerant quantum computers (FTQC).

This architecture analysis details Core Blockchain's dual-signature implementation of NIST-standardized Post-Quantum Cryptography (ML-DSA / CRYSTALS-Dilithium) and how Catch-22 PoDE memory barriers eliminate quantum Grover quadratic acceleration.

**Full Technical Paper:**
{url}
"""
    elif "coreminer" in slug:
        tweet_1 = "🚀 CoreMiner Linux & WSL2 Tuning:\nLeaving default settings wastes up to 24% of your CPU hashing power. Guide to 1GB HugePages, taskset thread pinning, and NUMA node alignment.\n\nStep-by-step tutorial 👇"
        tweet_2 = "⏱️ Optimization Gains:\n• Standard 4KB Pages: 1,902 H/s (TLB cache stalls)\n• 2MB HugePages: 2,180 H/s (+14.6% boost)\n• 1GB HugePages + Core Pinning: 2,358 H/s (+23.9% gain)"
        tweet_3 = f"🐧 Ubuntu & Windows 11 WSL2:\nIncludes .wslconfig buffer allocation, sysctl memory persistence, and multi-CCD taskset affinity commands.\n\nFull guide:\n🔗 {url}"
        reddit_title = f"[Mining Tutorial] CoreMiner Linux & WSL2 Performance Optimization: HugePages & Thread Pinning"
        reddit_body = f"""**Overview:**
Catch-22 generates massive scratchpad matrices per worker thread, which rapidly exhausts the CPU's Translation Lookaside Buffer (TLB) under default 4KB memory pages.

By configuring HugePages and locking threads to physical cores across dual-CCD Ryzen and Xeon processors, hashing throughput increases by up to +23.9%.

**Full Command Reference & WSL2 Config:**
{url}
"""
    else:
        clean_desc = desc[:100].replace("\n", " ")
        tweet_1 = f"💻 CoreStation Technical Update:\n{clean_desc}...\n\nRead full report 👇"
        tweet_2 = f"📊 Telemetry & Data:\n{clean_desc}\n\nExplore interactive benchmarks:\n🔗 {url}"
        tweet_3 = f"🌐 CoreStation Global Hub:\nIndependent node operations, hardware tuning, and post-quantum research.\n🔗 {url}"
        reddit_title = f"[Technical Report] {title}"
        reddit_body = f"{desc}\n\nFull report: {url}"

    # Twitter character limit safety guard (280 half-width characters, URL consumes 23)
    max_tweet1_len = 220
    if len(tweet_1) > max_tweet1_len:
        tweet_1 = tweet_1[:max_tweet1_len - 3] + "..."

    x_thread = "\n\n--- TWEET BREAK ---\n\n".join([tweet_1, tweet_2, tweet_3])

    out_file = OUTPUT_DIR / f"social_{slug}.txt"
    with open(out_file, "w", encoding="utf-8") as f:
        f.write("=== X (TWITTER) THREAD ===\n\n" + x_thread + "\n\n" + "="*40 + "\n\n=== REDDIT POST ===\n\n" + reddit_body)

    print(f"✅ Generated social distribution payload for '{slug}':\n   Saved to: {out_file}")

    if publish:
        cfg = load_config()
        webhook_url = cfg.get("make_webhook_url", DEFAULT_WEBHOOK)

        payload = {
            "slug": slug,
            "title": title,
            "url": url,
            "tweet_1": tweet_1,
            "tweet_2": tweet_2,
            "tweet_3": tweet_3,
            "reddit_title": reddit_title,
            "reddit_body": reddit_body
        }

        print("🚀 Dispatching automated social payload to Make.com Webhook...")
        req = urllib.request.Request(
            webhook_url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json; charset=utf-8", "User-Agent": "CoreStation-Social-Bot/1.0"}
        )
        try:
            with urllib.request.urlopen(req, timeout=15, context=ssl_ctx) as res:
                body = res.read().decode("utf-8")
                print(f"🎉 Successfully dispatched to Make.com! Response: {body}")
        except Exception as e:
            print(f"❌ Failed to dispatch to Make.com Webhook: {e}", file=sys.stderr)

if __name__ == "__main__":
    slug_arg = "ryzen-7950x-xcb-mining-efficiency-eco-mode"
    publish_arg = False

    args = sys.argv[1:]
    if args:
        if args[0] != "--publish":
            slug_arg = args[0]
        if "--publish" in args:
            publish_arg = True

    generate_social_payload(slug_arg, publish=publish_arg)
