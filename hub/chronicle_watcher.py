#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Core Chronicle Watcher & Autonomous Multi-Platform Article Publisher
===================================================================
1. Core Blockchain (Official Telegram, Core Chronicle, GitHub) の最新アップデートを自動巡回監視。
2. 新着情報を検知すると Google Gemini API により自作PC女子「リコロ（Ricolo）」の高品質な解説記事を自律執筆。
3. はてなブログへ即時自動投稿（AtomPub経由）。
4. CoreStation 本サイト向け Standalone HTML（articles/<slug>.html）を自動生成。
5. data/initial_data.js、data/local_articles.js、index.html、sitemap.xml を完全同期更新。
6. Git 自動コミット＆プッシュを実行し、Cloudflare Pages へ全世界リアルタイム即時デプロイ。
"""

import os
import sys
import json
import urllib.request
import urllib.error
import re
import ssl
from datetime import datetime
import subprocess
import html

import xml.etree.ElementTree as ET

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)
CONFIG_DIR = os.path.join(BASE_DIR, "config")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
ARTICLES_DIR = os.path.join(ROOT_DIR, "articles")
DATA_DIR = os.path.join(ROOT_DIR, "data")
INITIAL_DATA_PATH = os.path.join(DATA_DIR, "initial_data.js")
LOCAL_ARTICLES_PATH = os.path.join(DATA_DIR, "local_articles.js")
INDEX_PATH = os.path.join(ROOT_DIR, "index.html")
SITEMAP_PATH = os.path.join(ROOT_DIR, "sitemap.xml")
LAST_SEEN_FILE = os.path.join(CONFIG_DIR, "last_seen_chronicle.json")
PUBLISHER_SCRIPT = os.path.join(BASE_DIR, "hatena_publisher.py")

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(ARTICLES_DIR, exist_ok=True)

# Core Blockchain 公式情報ソース
SOURCES = [
    {
        "name": "Core Blockchain / CoDeTech 英語本家アナウンス (Telegram: @codetechcc)",
        "url": "https://t.me/s/codetechcc",
        "type": "telegram"
    },
    {
        "name": "Core Blockchain Japan 日本公式コミュニティ (Telegram: @Core_Blockchain_Japan)",
        "url": "https://t.me/s/Core_Blockchain_Japan",
        "type": "telegram"
    },
    {
        "name": "Core Blockchain / CoDeTech 英語本家公式YouTube (@CoDeTechCC / Core Chronicle)",
        "channel_id": "UCRvIwSXU04Yaw4rkRzkJNHQ",
        "type": "youtube"
    }
]

def get_ssl_context():
    ctx = ssl.create_default_context()
    try:
        import certifi
        ctx.load_verify_locations(certifi.where())
    except Exception:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    return ctx

def load_last_seen():
    if os.path.exists(LAST_SEEN_FILE):
        with open(LAST_SEEN_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"last_checked": "", "seen_posts": []}

def save_last_seen(data):
    with open(LAST_SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def fetch_telegram_updates(url, source_name="Core Blockchain 公式アナウンス"):
    """Fetch public Telegram channel messages without API token."""
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
    )
    ctx = get_ssl_context()
    updates = []
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
            page_html = resp.read().decode("utf-8")
            msg_blocks = page_html.split('data-post="')
            for b in msg_blocks[1:]:
                post_id = b.split('"')[0]
                txt_m = re.search(r'<div class="tgme_widget_message_text[^>]*>(.*?)</div>', b, re.DOTALL)
                if txt_m:
                    raw_text = txt_m.group(1)
                    raw_text = re.sub(r'<br\s*/?>', '\n', raw_text)
                    clean_text = html.unescape(re.sub(r'<[^>]+>', '', raw_text)).strip()
                    is_greeting = clean_text.lower() in ["good morning!", "good morning", "good day", "gm"]
                    if clean_text and not is_greeting and (len(clean_text) >= 30 or "http" in clean_text):
                        updates.append({
                            "id": post_id,
                            "source": source_name,
                            "text": clean_text,
                            "url": f"https://t.me/{post_id}"
                        })
    except Exception as e:
        print(f"⚠️ Telegram fetch error ({url}): {e}", file=sys.stderr)
    return updates

def fetch_youtube_updates(channel_id, source_name="Core Blockchain 公式YouTube (CoDeTech)"):
    """Fetch latest YouTube videos from channel Atom RSS feed without API key."""
    url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
    )
    ctx = get_ssl_context()
    updates = []
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
            xml_data = resp.read()
            root = ET.fromstring(xml_data)
            ns = {
                'atom': 'http://www.w3.org/2005/Atom',
                'yt': 'http://www.youtube.com/xml/schemas/2015',
                'media': 'http://search.yahoo.com/mrss/'
            }
            for entry in root.findall('atom:entry', ns)[:5]:
                video_id_el = entry.find('yt:videoId', ns)
                video_id = video_id_el.text if video_id_el is not None else None
                title_el = entry.find('atom:title', ns)
                title = title_el.text if title_el is not None else ""
                link_el = entry.find('atom:link', ns)
                link = link_el.attrib['href'] if link_el is not None else f"https://www.youtube.com/watch?v={video_id}"

                media_group = entry.find('media:group', ns)
                desc = ""
                if media_group is not None:
                    desc_el = media_group.find('media:description', ns)
                    if desc_el is not None and desc_el.text:
                        desc = desc_el.text.strip()

                post_id = f"youtube/{video_id}"
                text_content = f"【Core Chronicle 公式YouTube動画公開】\nタイトル: {title}\nURL: {link}\n\n概要・説明:\n{desc}"
                updates.append({
                    "id": post_id,
                    "source": source_name,
                    "text": text_content,
                    "url": link
                })
    except Exception as e:
        print(f"⚠️ YouTube fetch error ({channel_id}): {e}", file=sys.stderr)
    return updates

GEMINI_CONFIG_PATH = os.path.join(CONFIG_DIR, "gemini_config.json")

def load_gemini_key():
    env_key = os.environ.get("GEMINI_API_KEY")
    if env_key:
        return env_key
    if os.path.exists(GEMINI_CONFIG_PATH):
        try:
            with open(GEMINI_CONFIG_PATH, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                return cfg.get("api_key", "").strip()
        except Exception:
            pass
    return ""

BANNER_HEADER_HTML = """
<!-- CoreStation Official Brand Header Banner -->
<div style="text-align: center; margin-bottom: 25px;">
  <a href="https://corestation.pages.dev/" target="_blank" rel="noopener noreferrer" style="text-decoration: none; display: inline-block;">
    <img src="https://corestation.pages.dev/assets/horizontal_banner_logo.jpg" alt="CoreStation - Core Blockchain Mining & Node Hub" style="width: 100%; max-width: 820px; height: auto; border-radius: 12px; box-shadow: 0 8px 24px rgba(0, 0, 0, 0.35); display: block; margin: 0 auto;">
  </a>
</div>
"""

RICOLO_AUTHOR_BOX_HTML = """
<!-- Ricolo Official Author Profile Box -->
<div style="margin-top: 40px; padding: 20px; background: linear-gradient(135deg, rgba(139, 92, 246, 0.08) 0%, rgba(56, 189, 248, 0.08) 100%); border-radius: 12px; border: 1px solid rgba(139, 92, 246, 0.25); display: flex; align-items: center; gap: 18px; box-shadow: 0 4px 15px rgba(0,0,0,0.05);">
  <img src="https://cdn-ak.f.st-hatena.com/images/fotolife/c/corestation/20260919/20260919020141.jpg" alt="リコロ (Ricolo)" style="width: 80px; height: 80px; border-radius: 50%; object-fit: cover; border: 3px solid #8b5cf6; box-shadow: 0 2px 10px rgba(139, 92, 246, 0.35); flex-shrink: 0;">
  <div>
    <div style="font-size: 16px; font-weight: bold; color: #1e293b; margin-bottom: 4px;">この記事を書いた人：リコロ（Ricolo）🎮💻✨</div>
    <div style="font-size: 13px; color: #64748b; line-height: 1.6;">自作PCとCore Blockchainが大好きなゲーム女子ライター。公式DiscordやTelegramの最新開発情報、PoDE・マイニング検証をわかりやすく解説中！</div>
  </div>
</div>
"""

def generate_article_with_gemini(raw_text, source_url, source_name):
    """Generate structured article content (title, slug, summary, body) using Gemini API."""
    api_key = load_gemini_key()
    if not api_key:
        return None

    prompt = f"""あなたは自作PCとゲームが大好きな女性技術アナリスト兼ライター「リコロ（Ricolo）」です！
Core Blockchain (XCB) の公式速報・最新アナウンスを深く読み解き、初心者やマイナー向けに要点を整理し、自作PCやゲームの比喩を交えながら明るく親しみやすい女子目線で解説記事を執筆してください。

【情報ソース】
{source_name} ({source_url})

【公式アナウンス原文】
{raw_text}

【記事の執筆ルール】
1. キャラクター＆トーン:
   - 名前: リコロ（自作PC大好きゲーム女子）
   - 冒頭の挨拶: 「どうも！自作PC大好きゲーム女子、リコロです！✍🏻🎮💻✨」
   - トーン: 元気で明るく親しみやすい語り口。自作PC（Ryzen・グラボ・冷却等）やゲーム（放置ゲー・RPG・クラフト等）の例え話を適度に織り交ぜる。
   - 締めくくり: 「それでは、また次回の解説記事でお会いしましょう！リコロでした〜！ばいば〜い！🎮👾✨」など末尾の表現も自由に生き生きとキャラクターを維持する。
   - ※重要【英語原文への対応】: 原文が英語（本家アナウンス等）の場合は、内容の核となる重要ポイントを初心者にも分かりやすい自然で明快な日本語に翻訳・要約した上で、リコロ独自の自作PC・ゲーム目線で解説してください。
2. 構成:
   - つかみ・導入（「公式から激アツなアップデートが届きました〜！」）
   - 原文引用（<blockquote style="margin: 10px 0; padding: 10px; background: #fff; border-left: 3px solid #ffa726; font-size: 14px; color: #555; white-space: pre-wrap;"> で囲み、引用元リンク: {source_url} を明記）
   - 3行でわかる！今回の神アプデ要点まとめ（箇条書き）
   - 自作PC＆ゲーム目線での深掘り解説（h2やh3タグを使用）
   - マイナー・ホルダーはどう動くべきか？（実践アドバイス）
   - CoreStation（https://corestation.pages.dev/）への誘導
   - 締めくくり
3. 出力フォーマット（厳密に以下の書式を守ってください）:
---META---
TITLE: 【速報・解説】絵文字付きの魅力的なタイトル
SLUG: 半角英小文字とハイフンのみの簡潔な識別子（例: core-update-20261018）
SUMMARY: 100〜150文字程度の客観的かつ魅力的な記事要約
---BODY---
<div style="line-height: 1.8; font-size: 16px; color: #333;">
記事のHTML本文（```htmlなどのコードフェンスは含めないでください）
</div>
"""

    endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 4000
        }
    }

    req = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    ctx = get_ssl_context()
    try:
        print("🧠 Google Gemini API を呼び出して解説記事を執筆中...")
        with urllib.request.urlopen(req, context=ctx, timeout=35) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            candidate = data["candidates"][0]["content"]["parts"][0]["text"].strip()
            
            # Parse META and BODY
            meta_match = re.search(r'---META---(.*?)---BODY---(.*)', candidate, re.DOTALL)
            if meta_match:
                meta_text = meta_match.group(1).strip()
                body_html = meta_match.group(2).strip()
                
                title = "【速報・解説】Core Blockchain最新アップデート！🎮⚡️"
                slug = f"core-update-{datetime.now().strftime('%Y%m%d%H%M%S')}"
                summary = "Core Blockchainの公式最新アップデートを自作PC女子リコロが徹底解説！"
                
                for line in meta_text.splitlines():
                    if line.startswith("TITLE:"):
                        title = line.replace("TITLE:", "").strip()
                    elif line.startswith("SLUG:"):
                        raw_slug = line.replace("SLUG:", "").strip().lower()
                        slug = re.sub(r'[^a-z0-9\-]+', '-', raw_slug).strip('-')
                    elif line.startswith("SUMMARY:"):
                        summary = line.replace("SUMMARY:", "").strip()
                
                # Clean body
                body_html = re.sub(r'^```(?:html)?\s*', '', body_html, flags=re.MULTILINE)
                body_html = re.sub(r'\s*```$', '', body_html, flags=re.MULTILINE).strip()
                
                print(f"✨ Geminiによる記事執筆が完了しました！ ({title})")
                return {
                    "title": title,
                    "slug": slug,
                    "summary": summary,
                    "body": body_html
                }
            else:
                # Fallback parse
                lines = candidate.splitlines()
                title = lines[0].replace("#", "").strip()
                body_html = "\n".join(lines[1:]).strip()
                body_html = re.sub(r'^```(?:html)?\s*', '', body_html, flags=re.MULTILINE)
                body_html = re.sub(r'\s*```$', '', body_html, flags=re.MULTILINE).strip()
                slug = f"core-update-{datetime.now().strftime('%Y%m%d%H%M%S')}"
                summary = "Core Blockchainの公式最新アップデートを自作PC女子リコロが徹底解説！"
                return {
                    "title": title,
                    "slug": slug,
                    "summary": summary,
                    "body": body_html
                }
    except Exception as e:
        print(f"⚠️ Gemini API呼び出しエラー: {e}", file=sys.stderr)
        return None

def build_standalone_article_html(slug, title, summary, date_str, body_html):
    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title} | CoreStation ナレッジ</title>
  <meta name="description" content="{summary}">
  <link rel="canonical" href="https://corestation.pages.dev/articles/{slug}">
  <link rel="icon" type="image/svg+xml" href="../assets/core-icon.svg">
  
  <!-- OGP / Social Sharing -->
  <meta property="og:title" content="{title}">
  <meta property="og:description" content="{summary}">
  <meta property="og:url" content="https://corestation.pages.dev/articles/{slug}">
  <meta property="og:type" content="article">
  <meta property="og:image" content="https://corestation.pages.dev/assets/horizontal_banner_logo.jpg">
  <meta name="twitter:card" content="summary_large_image">
  
  <!-- Google AdSense Verification & Auto-Ads Tag -->
  <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-1988464307898443" crossorigin="anonymous"></script>

  <!-- A8.net 広告掲載URL管理・リンクマネージャー (A8 Link Manager) -->
  <script src="//statics.8me.jp/a8link/a8linkmgr.js"></script>
  <script>
    a8linkmgr({{ "config_id": "AiCzxW5LM9avBb8VJ393" }});
  </script>

  <!-- Stylesheets -->
  <link rel="stylesheet" href="../style.css?v=20261018_2">
  <link rel="stylesheet" href="article.css?v=20261018_2">

  <!-- Schema.org JSON-LD (Article & Breadcrumb) -->
  <script type="application/ld+json">
  {{
    "@context": "https://schema.org",
    "@graph": [
      {{
        "@type": "Article",
        "headline": "{title}",
        "description": "{summary}",
        "datePublished": "{date_str}T00:00:00+09:00",
        "dateModified": "{date_str}T00:00:00+09:00",
        "author": {{
          "@type": "Person",
          "name": "リコロ (Ricolo)"
        }},
        "publisher": {{
          "@type": "Organization",
          "name": "CoreStation",
          "logo": {{
            "@type": "ImageObject",
            "url": "https://corestation.pages.dev/assets/core-icon.svg"
          }}
        }},
        "mainEntityOfPage": "https://corestation.pages.dev/articles/{slug}"
      }},
      {{
        "@type": "BreadcrumbList",
        "itemListElement": [
          {{
            "@type": "ListItem",
            "position": 1,
            "name": "ホーム (ダッシュボード)",
            "item": "https://corestation.pages.dev/"
          }},
          {{
            "@type": "ListItem",
            "position": 2,
            "name": "ナレッジアーカイブ",
            "item": "https://corestation.pages.dev/#articles"
          }},
          {{
            "@type": "ListItem",
            "position": 3,
            "name": "{title}",
            "item": "https://corestation.pages.dev/articles/{slug}"
          }}
        ]
      }}
    ]
  }}
  </script>
</head>
<body class="article-page-body">

  <!-- Header Navigation -->
  <header class="article-header-nav">
    <a href="../#dashboard" class="article-brand">
      <img src="../assets/core-icon.svg" alt="CoreStation Logo">
      <span>CoreStation</span>
    </a>
    <nav class="article-nav-links">
      <a href="../#dashboard">📊 ダッシュボード</a>
      <a href="../#articles">📚 記事一覧</a>
      <a href="../#guide">🚀 導入手順</a>
      <a href="../about.html">🏢 運営者情報</a>
    </nav>
  </header>

  <main class="article-container">
    <!-- Breadcrumb -->
    <nav class="breadcrumb" aria-label="パンくずリスト">
      <a href="../">ホーム</a>
      <span class="sep">&gt;</span>
      <a href="../#articles">ナレッジアーカイブ</a>
      <span class="sep">&gt;</span>
      <span>速報・公式アナウンス</span>
    </nav>

    <!-- Main Article Card -->
    <article class="article-card-main">
      <header class="article-meta-header">
        <span class="article-badge">速報・公式アップデート</span>
        <h1 class="article-main-title">{title}</h1>
        <div class="article-submeta">
          <span>📅 公開日: {date_str}</span>
          <span>✍️ 執筆: リコロ (Ricolo)</span>
          <span>🔒 監修: CoreStation 技術検証チーム</span>
        </div>
      </header>

      <!-- Article Content Body -->
      <div class="article-content-body">
{body_html}
      </div>

      <!-- Author Profile Card -->
      <footer class="article-author-card" style="margin-top: 40px; padding: 24px; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px; display: flex; align-items: center; gap: 20px; flex-wrap: wrap;">
        <img src="../assets/ricolo-avatar.png" alt="リコロ (Ricolo)" style="width: 80px; height: 80px; border-radius: 50%; border: 2px solid #0284c7; object-fit: cover;">
        <div style="flex: 1; min-width: 240px;">
          <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 6px;">
            <strong style="font-size: 1.15rem; color: #0f172a;">リコロ (Ricolo)</strong>
            <span style="font-size: 0.85rem; background: #e0f2fe; color: #0369a1; padding: 2px 8px; border-radius: 4px; font-weight: 600;">自作PC女子 / 暗号資産アナリスト</span>
          </div>
          <p style="font-size: 0.92rem; color: #475569; line-height: 1.6; margin: 0;">
            Ryzen 9 7950X / Xeon E5 を複数台運用し、PoDEマイニングと耐量子ブロックチェーンの検証に没頭するハードウェア好き。難しいブロックチェーンの仕組みを、初心者にもわかりやすくロジカルにお届けします！
          </p>
        </div>
      </footer>

      <!-- Bottom Navigation / Links -->
      <div style="margin-top: 30px; display: flex; justify-content: space-between; flex-wrap: wrap; gap: 15px;">
        <a href="../#dashboard" class="btn-secondary" style="padding: 10px 18px; border-radius: 8px; text-decoration: none;">← ダッシュボードへ戻る</a>
        <a href="core-blockchain-ecosystem-complete-guide.html" class="btn-primary" style="padding: 10px 18px; border-radius: 8px; text-decoration: none;">エコシステム徹底解説を読む →</a>
      </div>
    </article>
  </main>

  <!-- Footer -->
  <footer style="margin-top: 60px; padding: 30px 20px; text-align: center; border-top: 1px solid #1e293b; color: #64748b; font-size: 0.9rem;">
    <p>© 2026 CoreStation. All rights reserved. 独立系ブロックチェーン実測検証ポータル</p>
  </footer>
</body>
</html>
"""

def integrate_article_to_site(slug, title, summary, date_str, body_html, category="ecosystem", category_name="速報・公式アナウンス"):
    """Integrates new article into standalone HTML, initial_data.js, local_articles.js, index.html, and sitemap.xml."""
    print(f"📁 CoreStation 本サイト側へ記事を統合中: {slug}")
    
    # Clean body for standalone site
    clean_body = re.sub(r'<!-- CoreStation Official Brand Header Banner -->.*?</div>\s*</div>', '', body_html, flags=re.DOTALL)
    clean_body = re.sub(r'<!-- Ricolo Official Author Profile Box -->.*?</div>\s*</div>', '', clean_body, flags=re.DOTALL)
    clean_body = re.sub(r'^\s*<div style="line-height:[^>]*>', '', clean_body)
    clean_body = re.sub(r'</div>\s*$', '', clean_body).strip()

    # 1. Standalone HTML
    out_path = os.path.join(ARTICLES_DIR, f"{slug}.html")
    full_html = build_standalone_article_html(slug, title, summary, date_str, clean_body)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(full_html)
    print(f"  ✅ 生成完了: {out_path}")

    # 2. data/initial_data.js
    if os.path.exists(INITIAL_DATA_PATH):
        with open(INITIAL_DATA_PATH, "r", encoding="utf-8") as f:
            init_data = f.read()
        needle = '"articlesArchive": ['
        if needle in init_data and f'"id": "{slug}"' not in init_data:
            item_str = f"""    {{
      "id": "{slug}",
      "title": {json.dumps(title, ensure_ascii=False)},
      "category": "{category}",
      "categoryName": "{category_name}",
      "date": "{date_str}",
      "summary": {json.dumps(summary, ensure_ascii=False)}
    }},\n"""
            init_data = init_data.replace(needle, needle + "\n" + item_str)
            with open(INITIAL_DATA_PATH, "w", encoding="utf-8") as f:
                f.write(init_data)
            print("  ✅ 更新完了: data/initial_data.js")

    # 3. data/local_articles.js
    if os.path.exists(LOCAL_ARTICLES_PATH):
        with open(LOCAL_ARTICLES_PATH, "r", encoding="utf-8") as f:
            local_content = f.read()
        prefix = "window.__CORE_LOCAL_ARTICLES__ = "
        if prefix in local_content and f'"id": "{slug}"' not in local_content:
            idx = local_content.find(prefix)
            json_part = local_content[idx + len(prefix):].rstrip().rstrip(";")
            try:
                articles_list = json.loads(json_part)
                new_item = {
                    "id": slug,
                    "title": title,
                    "category": category,
                    "categoryName": category_name,
                    "date": date_str,
                    "summary": summary,
                    "content": clean_body
                }
                articles_list.insert(0, new_item)
                new_local_content = prefix + json.dumps(articles_list, ensure_ascii=False, indent=2) + ";\n"
                with open(LOCAL_ARTICLES_PATH, "w", encoding="utf-8") as f:
                    f.write(new_local_content)
                print("  ✅ 更新完了: data/local_articles.js")
            except Exception as e:
                print(f"  ⚠️ local_articles.js JSON解析エラー: {e}")

    # 4. index.html
    if os.path.exists(INDEX_PATH):
        with open(INDEX_PATH, "r", encoding="utf-8") as f:
            index_html = f.read()
        grid_needle = '<div class="article-grid" id="articlesArchiveContainer">'
        if grid_needle in index_html and f'data-article-id="{slug}"' not in index_html:
            card_html = f"""              <a href="articles/{slug}" class="article-card" style="text-decoration: none; color: inherit; display: flex; flex-direction: column; justify-content: space-between;" data-article-id="{slug}">
                <div>
                  <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <span class="badge-online" style="font-size: 11px; padding: 2px 8px; background: rgba(56, 189, 248, 0.2); color: #38bdf8;">速報・公式アップデート</span>
                    <span style="font-size: 11px; color: var(--text-light, #94a3b8);">🔒 独立静的ページ</span>
                  </div>
                  <h3 class="article-card-title">{title}</h3>
                  <p class="article-card-desc">{summary}</p>
                </div>
                <div class="article-card-meta">
                  <span>📅 {date_str}</span>
                  <span class="article-read-btn"><span>📖 記事を読む ↗</span></span>
                </div>
              </a>\n"""
            index_html = index_html.replace(grid_needle, grid_needle + "\n" + card_html)
            with open(INDEX_PATH, "w", encoding="utf-8") as f:
                f.write(index_html)
            print("  ✅ 更新完了: index.html")

    # 5. sitemap.xml
    if os.path.exists(SITEMAP_PATH):
        with open(SITEMAP_PATH, "r", encoding="utf-8") as f:
            sitemap_xml = f.read()
        if f"/articles/{slug}</loc>" not in sitemap_xml:
            sitemap_entry = f"""  <url>
    <loc>https://corestation.pages.dev/articles/{slug}</loc>
    <lastmod>{date_str}</lastmod>
    <changefreq>weekly</changefreq>
    <priority>0.85</priority>
  </url>\n"""
            sitemap_xml = sitemap_xml.replace("</urlset>", sitemap_entry + "</urlset>")
            with open(SITEMAP_PATH, "w", encoding="utf-8") as f:
                f.write(sitemap_xml)
            print("  ✅ 更新完了: sitemap.xml")

def deploy_to_cloudflare(commit_msg=None):
    """Commit changes and push to origin main to trigger Cloudflare Pages build."""
    print("🚀 Cloudflare Pages への自動デプロイ（Git push）を開始...")
    try:
        cmd_add = ["git", "add", "-A"]
        subprocess.run(cmd_add, cwd=ROOT_DIR, check=True)

        status_res = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT_DIR, capture_output=True, text=True)
        if not status_res.stdout.strip():
            print("ℹ️ デプロイ対象の変更差分はありません。")
            return

        msg = commit_msg or f"feat(auto-watcher): auto-publish latest updates from Core Chronicle [{datetime.now().strftime('%Y-%m-%d %H:%M')}]"
        cmd_commit = [
            "git", "-c", "user.name=CoreStation Auto Watcher",
            "-c", "user.email=watcher@corestation.local",
            "commit", "-m", msg
        ]
        subprocess.run(cmd_commit, cwd=ROOT_DIR, check=True)

        cmd_push = ["git", "push", "origin", "main"]
        push_res = subprocess.run(cmd_push, cwd=ROOT_DIR, capture_output=True, text=True, timeout=60)
        print(push_res.stdout)
        if push_res.returncode == 0:
            print("🎉 Cloudflare Pages への本番デプロイが完了しました！")
        else:
            print(f"⚠️ Git push 警告: {push_res.stderr}", file=sys.stderr)
    except Exception as e:
        print(f"⚠️ 自動デプロイエラー: {e}", file=sys.stderr)

def sync_onchain_mining_data():
    """Runs sync.py to ensure initial_data.js and wallet.db have the latest on-chain rewards and worker status."""
    print("⛓️ オンチェーン採掘データ＆ワーカー最新状態の定期同期を実行中...")
    try:
        sync_script = os.path.join(ROOT_DIR, "sync.py")
        subprocess.run([sys.executable, sync_script], cwd=ROOT_DIR, check=True)
        print("✅ オンチェーン採掘データ同期が正常に完了しました。")
        return True
    except Exception as e:
        print(f"⚠️ オンチェーン採掘データ同期中にエラー: {e}", file=sys.stderr)
        return False

def check_and_publish():
    """Main execution loop for checking updates and publishing across all platforms."""
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 🔍 コアクロニクル・公式アップデートの巡回監視＆最新データ同期を開始...")

    # 1. 常にオンチェーン採掘実績＆ワーカー状態を最新化
    sync_onchain_mining_data()

    # 2. 公式アナウンス・SNSの巡回チェック
    last_seen = load_last_seen()
    seen_ids = set(last_seen.get("seen_posts", []))

    all_updates = []
    for src in SOURCES:
        if src["type"] == "telegram":
            items = fetch_telegram_updates(src["url"], src["name"])
            all_updates.extend(items)
        elif src["type"] == "youtube":
            items = fetch_youtube_updates(src["channel_id"], src["name"])
            all_updates.extend(items)

    # 初回シード保護（未登録時は最新1件のみ残して既読化）
    if not seen_ids and all_updates:
        print(f"📦 初回起動を検知：過去ログ {len(all_updates)-1} 件を既読としてシード設定します。")
        for u in all_updates[:-1]:
            seen_ids.add(u["id"])

    new_posts = [u for u in all_updates if u["id"] not in seen_ids]

    if not new_posts:
        print("✅ 新着の公式更新はありませんでした。オンチェーン採掘データの差分があればデプロイします。")
        last_seen["last_checked"] = datetime.now().isoformat()
        last_seen["seen_posts"] = list(seen_ids)[-100:]
        save_last_seen(last_seen)

        # 新着記事がなくても、オンチェーン採掘データ等の差分があれば即時コミット＆デプロイ
        deploy_to_cloudflare(f"feat(mining): auto-sync on-chain rewards and worker status [{datetime.now().strftime('%Y-%m-%d %H:%M')}]")
        return False

    print(f"🎉 {len(new_posts)} 件の新着アップデートを検知しました！")
    today_str = datetime.now().strftime("%Y-%m-%d")
    any_published = False

    for post in new_posts:
        art = generate_article_with_gemini(post["text"], post.get("url", ""), post.get("source", ""))
        if not art:
            continue

        title = art["title"]
        slug = art["slug"]
        summary = art["summary"]
        body_html = art["body"]
        full_blog_html = BANNER_HEADER_HTML + "\n" + body_html + "\n" + RICOLO_AUTHOR_BOX_HTML

        # 1. Save temp output
        temp_file = os.path.join(OUTPUT_DIR, f"chronicle_update_{post['id'].replace('/', '_')}.html")
        with open(temp_file, "w", encoding="utf-8") as f:
            f.write(full_blog_html)

        # 2. Publish to Hatena Blog
        print(f"🚀 はてなブログへ自動投稿を実行中: 『{title}』...")
        try:
            cmd = [
                sys.executable,
                PUBLISHER_SCRIPT,
                "--file", temp_file,
                "--title", title,
                "--category", "暗号資産", "速報", "XCB", "アップデート"
            ]
            res = subprocess.run(cmd, capture_output=True, text=True)
            print(res.stdout)
        except Exception as e:
            print(f"❌ はてなブログ投稿エラー: {e}", file=sys.stderr)

        # 3. Integrate into CoreStation Site (Standalone HTML, Data, Index, Sitemap)
        integrate_article_to_site(
            slug=slug,
            title=title,
            summary=summary,
            date_str=today_str,
            body_html=body_html,
            category="ecosystem",
            category_name="速報・公式アナウンス"
        )

        seen_ids.add(post["id"])
        any_published = True

    if any_published:
        # 4. Trigger Cloudflare Pages deployment
        deploy_to_cloudflare()

        # 4.5 Dispatch to Make.com & X (Twitter)
        try:
            social_script = os.path.join(BASE_DIR, "social_exporter.py")
            if os.path.exists(social_script) and new_posts:
                latest_slug = new_posts[0].get("id", "").replace("/", "_")
                print("🚀 Make.com / Buffer 経由での X 自動配信をトリガー...")
                subprocess.run([sys.executable, social_script, latest_slug, "--publish"], capture_output=True, text=True, timeout=30)
        except Exception as e:
            print(f"⚠️ SNS配信エラー (スキップ): {e}")

    last_seen["seen_posts"] = list(seen_ids)[-100:]
    last_seen["last_checked"] = datetime.now().isoformat()
    save_last_seen(last_seen)
    return any_published

if __name__ == "__main__":
    check_and_publish()
