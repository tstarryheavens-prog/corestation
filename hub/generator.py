#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ContentHub Generator Engine
===========================
5大テーマ（闘病記、HEMS、XCB暗号資産、AI自動化、オルカン投資）のコンテンツ生成と
A8.net等の広告・収益リンク自動埋め込み、日英多言語展開を統括するエンジン。
"""

import os
import sys
import json
import argparse
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_DIR = os.path.join(BASE_DIR, "config")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
MEDIA_DIR = os.path.join(BASE_DIR, "media")

THEMES_PATH = os.path.join(CONFIG_DIR, "themes.json")
MONETIZATION_PATH = os.path.join(CONFIG_DIR, "monetization.json")

def load_json(path):
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def get_monetization_snippets(category, lang="ja"):
    mone_data = load_json(MONETIZATION_PATH).get("monetization", {})
    cat_data = mone_data.get(category, {})
    if not cat_data:
        return ""

    snippets = []
    items = cat_data.get("items", [])
    for it in items:
        if lang == "ja":
            cta = it.get("cta_text_ja", it.get("service_name", ""))
            link = it.get("affiliate_url", "")
            banner = it.get("banner_html", "")
            if banner:
                snippets.append(f"\n> **広告・推奨サービス**\n> {cta}\n> {banner}")
            elif link:
                snippets.append(f"\n> {cta} ➔ [{it.get('service_name')}]({link})")
        else:
            cta = it.get("cta_text_en", it.get("service_name", ""))
            link = it.get("affiliate_url", "")
            if cta and link:
                snippets.append(f"\n> **Recommended Tool**: [{cta}]({link})")

    # Global exchanges / Donations if any
    if lang == "en" and "global_exchanges" in cat_data:
        for ex in cat_data["global_exchanges"]:
            snippets.append(f"\n> **Official / Recommended Exchange**: [{ex.get('service_name')}]({ex.get('affiliate_url')})")
            
    if "crypto_donation" in cat_data:
        don = cat_data["crypto_donation"]
        label = don.get(f"label_{lang}", don.get("label_en", "Donation"))
        xcb = don.get("xcb_address")
        snippets.append(f"\n---\n### {label}\n- **XCB**: `{xcb}`\n- **ETH/USDT**: `{don.get('eth_address')}`\n")

    return "\n".join(snippets)

def generate_blog_post(theme_info, topic, lang="ja"):
    name = theme_info[f"name_{lang}"] if f"name_{lang}" in theme_info else theme_info["name_ja"]
    tone = theme_info[f"tone_{lang}"] if f"tone_{lang}" in theme_info else theme_info["tone_ja"]
    tags = theme_info.get("tags", [])
    mone_snippets = get_monetization_snippets(theme_info.get("monetization_category", ""), lang=lang)
    today = datetime.now().strftime("%Y-%m-%d")

    if lang == "ja":
        content = f"""---
title: "{topic}"
category: "{name}"
date: "{today}"
tags: {json.dumps(tags, ensure_ascii=False)}
lang: "ja"
---

# {topic}

## はじめに
本記事では、**{name}** に関する最新の実践知と検証データをお届けします。

> **執筆方針・トーン**: {tone}

## 1. 今回のポイント・背景
- **背景**: {theme_info.get("description", "")}
- **重要なポイント**: 実践的な手順と検証結果を詳しく解説します。

## 2. 実践・詳細解説
（ここに具体的な内容・コード・運用データが入ります）

{mone_snippets}

## 3. まとめ
継続的な運用と記録が成果に繋がります。ご質問や感想はコメントやSNSにてお気軽にお寄せください！

"""
    else:
        content = f"""---
title: "{topic}"
category: "{name}"
date: "{today}"
tags: {json.dumps(tags, ensure_ascii=False)}
lang: "en"
---

# {topic}

## Introduction
Welcome to this guide on **{name}**. In this article, we share practical insights, operational data, and implementation steps.

> **Approach & Tone**: {tone}

## Key Takeaways
- **Context**: {theme_info.get("description", "")}
- **Key Insight**: Step-by-step verified methodology and technical details.

## Detailed Walkthrough
(Insert practical findings, code blocks, or real-time metrics here)

{mone_snippets}

## Conclusion
Stay tuned for more updates. Feel free to join the discussion and share your feedback!

"""
    return content

def generate_note_post(theme_info, topic):
    name = theme_info.get("name_ja")
    mone_snippets = get_monetization_snippets(theme_info.get("monetization_category", ""), lang="ja")
    today = datetime.now().strftime("%Y-%m-%d")

    return f"""# {topic}

【テーマ】{name} | 日付: {today}

こんにちは。いつもご覧いただきありがとうございます。

今回は「{topic}」について、日々の記録と気づきをありのままに綴ってみたいと思います。

---

### ■ 今日の記録と想い
（ここに日々の体調、治療、生活の工夫、または取り組み内容を記載）

---

### ■ 読者の皆様へ
同じ境遇の方や、同じ目標に向かって進む方の少しでも力になれれば嬉しいです。

{mone_snippets}

スキ（❤️）やコメント、フォローをいただけると日々の大きな励みになります！
いつも温かい応援を本当にありがとうございます。
"""

def generate_shorts_script(theme_info, topic, lang="ja"):
    name = theme_info[f"name_{lang}"] if f"name_{lang}" in theme_info else theme_info["name_ja"]
    mone_cat = theme_info.get("monetization_category", "")
    mone_snippets = get_monetization_snippets(mone_cat, lang=lang)

    if lang == "ja":
        return f"""# 🎬 ショート動画台本 (YouTube Shorts / TikTok / Reels)
- **タイトル**: {topic}
- **対象テーマ**: {name}
- **想定尺**: 約40〜55秒 (縦型 1080x1920)

---

### 【シーン構成・タイムテーブル】

| 秒数 | 画面演出 (Visual) | 音声ナレーション (Voice) | テロップ文字 (On Screen) |
| :--- | :--- | :--- | :--- |
| **0:00 - 0:05**<br>(フック) | 画面ドアップ、CoreStationやアプリの動きのある画面 | 「まだ〇〇で損してませんか？実は...」 | ⚠️ 知らないと損する！<br>驚きの事実 |
| **0:05 - 0:20**<br>(本題) | グラフ、UIの操作画面、具体的な数字を見せる | 「今回は{name}における実践データと検証結果を大公開します。」 | 📊 実際の運用データ<br>【結果を公開】 |
| **0:20 - 0:40**<br>(解決策) | スイッチ切り替え、設定画面、重要ポイントの強調 | 「重要なのはこの1点。これをするだけで効率が劇的に変わります。」 | 💡 成功の秘訣はココ！<br>今すぐできる手順 |
| **0:40 - 0:50**<br>(CTA) | サイトアイコン、プロフィールへの誘導矢印 | 「詳しい手順やツールは、概要欄・プロフィールのリンクからチェックしてみてね！」 | 🔗 詳細は概要欄へ！<br>チャンネル登録もよろしくね |

---

### 📝 概要欄 & 固定コメント用テンプレート
{topic} についてサクッと解説しました！
詳しい手順・ツールはこちらから👇
{mone_snippets}
#Shorts #{name.replace(' ', '')} #資産形成 #自動化
"""
    else:
        return f"""# 🎬 Short Video Script (YouTube Shorts / TikTok / Reels)
- **Title**: {topic}
- **Theme**: {name}
- **Length**: ~45-55 sec (Vertical 1080x1920)

---

### 【Scene Breakdown & Voice Script】

| Time | Visual Presentation | Voiceover (Voice) | On-Screen Caption |
| :--- | :--- | :--- | :--- |
| **0:00 - 0:05**<br>(Hook) | Fast cut of dynamic dashboard / metrics | "Are you still doing this the hard way? Watch this." | ⚠️ Don't Miss This Secret! |
| **0:05 - 0:20**<br>(Core Info) | Close-up on live charts, real-time figures | "Here is the exact breakdown for {name} based on real operational data." | 📊 Real-Time Metrics<br>Full Verification |
| **0:20 - 0:40**<br>(Solution) | Screen walkthrough of configuration or code | "The key is simple: automate this step and let the system do the work." | 💡 The Key Takeaway<br>Step-by-Step |
| **0:40 - 0:50**<br>(CTA) | Channel logo, link arrow pointing down | "Check the full setup link in the description below, and don't forget to subscribe!" | 🔗 Link in Description!<br>Subscribe for More |

---

### 📝 Description & Pinned Comment Template
Quick breakdown on {topic}!
Full tools and resources below 👇
{mone_snippets}
#Shorts #Crypto #Web3 #Automation
"""

def generate_sns_post(theme_info, topic, lang="ja"):
    name = theme_info[f"name_{lang}"] if f"name_{lang}" in theme_info else theme_info["name_ja"]
    tags = " ".join([f"#{t}" for t in theme_info.get("tags", [])])

    if lang == "ja":
        return f"""【{name}】{topic}

日々の実践データと気づきをまとめました。
何事もコツコツと検証を積み重ねることが大きな成果に繋がりますね。

詳しい手順やコード、ツールの活用法はブログ・動画で公開中👇
（リンク設置）

{tags}
"""
    else:
        return f"""【{name}】{topic}

Sharing key findings and operational data from our latest test run.
Automation and consistency are the game changers.

Full breakdown & setup instructions here 👇
(Link here)

#Tech #Web3 #OpenSource
"""

def main():
    parser = argparse.ArgumentParser(description="ContentHub Multi-Theme Publishing Engine")
    parser.add_argument("--theme", help="Theme ID (e.g. health-journal, hems-smart-home, xcb-crypto, ai-technology, all-country-investing)")
    parser.add_argument("--type", choices=["blog", "note", "shorts", "sns", "all"], default="blog", help="Output content format")
    parser.add_argument("--lang", choices=["ja", "en", "both"], default="ja", help="Target language")
    parser.add_argument("--topic", default="", help="Topic or title for the generated content")
    parser.add_argument("--list-themes", action="store_true", help="List available themes")

    args = parser.parse_args()

    themes_data = load_json(THEMES_PATH).get("themes", {})

    if args.list_themes:
        print("\n=== Available Publishing Themes ===")
        for tid, tinfo in themes_data.items():
            print(f"• {tid}: {tinfo.get('name_ja')} ({tinfo.get('name_en')})")
            print(f"  Primary: {', '.join(tinfo.get('primary_platforms', []))}")
        print("===================================\n")
        return

    if not args.theme:
        print("Error: --theme is required unless --list-themes is specified.")
        parser.print_help()
        sys.exit(1)

    if args.theme not in themes_data:
        print(f"Error: Unknown theme '{args.theme}'. Available themes: {list(themes_data.keys())}")
        sys.exit(1)

    theme_info = themes_data[args.theme]
    topic = args.topic or f"{theme_info.get('name_ja')} の最新実践ノート"

    langs = ["ja", "en"] if args.lang == "both" else [args.lang]
    types = ["blog", "note", "shorts", "sns"] if args.type == "all" else [args.type]

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    generated_files = []

    for l in langs:
        for t in types:
            if t == "blog":
                body = generate_blog_post(theme_info, topic, lang=l)
                filename = f"{timestamp}_{args.theme}_blog_{l}.md"
            elif t == "note":
                if l != "ja":
                    continue  # note is Japanese only
                body = generate_note_post(theme_info, topic)
                filename = f"{timestamp}_{args.theme}_note.md"
            elif t == "shorts":
                body = generate_shorts_script(theme_info, topic, lang=l)
                filename = f"{timestamp}_{args.theme}_shorts_{l}.md"
            elif t == "sns":
                body = generate_sns_post(theme_info, topic, lang=l)
                filename = f"{timestamp}_{args.theme}_sns_{l}.txt"

            filepath = os.path.join(OUTPUT_DIR, filename)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(body)
            generated_files.append((filepath, t, l))

    print(f"\n✅ Content Generation Complete for [{args.theme}] ({topic})")
    for path, t, l in generated_files:
        print(f"  [{t.upper()} | {l.upper()}] -> {path}")

if __name__ == "__main__":
    main()
