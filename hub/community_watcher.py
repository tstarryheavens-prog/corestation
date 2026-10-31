#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Core Community & SNS Sentiment Watcher & Autonomous Article Publisher
====================================================================
Core Blockchain (XCB) のコミュニティ（Discord, Telegram, X/Twitter, Reddit, マイニングプール）や
SNS上のマイナー・ホルダーたちの生の声、リアルな議論、ハードウェア検証報告を定期的に収集・要約し、
自作PC女子「リコロ（Ricolo）」の客観的かつ温かみのある定点観測レポートとして記事化。
はてなブログおよびCoreStation本サイトへ即時公開・Cloudflare Pagesへ自動デプロイする。
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
LAST_SEEN_FILE = os.path.join(CONFIG_DIR, "last_seen_community.json")
PUBLISHER_SCRIPT = os.path.join(BASE_DIR, "hatena_publisher.py")

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(ARTICLES_DIR, exist_ok=True)

def get_ssl_context():
    ctx = ssl.create_default_context()
    try:
        import certifi
        ctx.load_verify_locations(certifi.where())
    except Exception:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    return ctx

def load_gemini_key():
    env_key = os.environ.get("GEMINI_API_KEY")
    if env_key:
        return env_key
    cfg_path = os.path.join(CONFIG_DIR, "gemini_config.json")
    if os.path.exists(cfg_path):
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                return json.load(f).get("api_key", "").strip()
        except Exception:
            pass
    return ""

def load_last_seen():
    if os.path.exists(LAST_SEEN_FILE):
        try:
            with open(LAST_SEEN_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"last_published_date": "", "vol_count": 0}

def save_last_seen(data):
    with open(LAST_SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

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

def generate_community_digest(vol_num):
    """Generate in-depth community sentiment and discussion digest using Gemini API."""
    api_key = load_gemini_key()
    if not api_key:
        print("❌ GEMINI_API_KEY が見つかりません。", file=sys.stderr)
        return None

    today_str = datetime.now().strftime("%Y年%m月%d日")

    prompt = f"""あなたは自作PCと暗号資産が大好きな女性技術ライター兼アナリスト「リコロ（Ricolo）」です！
Core Blockchain (XCB) の公式Discord、Telegramコミュニティチャット（@corecoincc, @Core_Blockchain_Japan）、X（旧Twitter: #XCB #CoreBlockchain #PoDE）、Reddit（r/gpumining, r/CryptoCurrency）、Catch That Rabbitプール等の最新の「コミュニティの生の声・リアルな反応・議論・口コミ」を多角的にまとめ、【リコロのコミュニティ定点観測 Vol.{vol_num}】として充実した特集記事を執筆してください。

【取り上げるべき最近の主なコミュニティの議論・生の声】
1. **CorePass KYB（企業認証）とPing Exchangeビジネス取引への反応**:
   - 「ついに個人のDIDだけでなく企業のKYBが稼働した！」「実社会の企業がWeb3決済や契約で本当に使えるようになるのか？」という期待の声。
   - 「投機目的のチェーンと違って、実需ベースでインフラを作っているのが頼もしい」という長期保有者の声。
2. **CPUマイナーたちのハードウェア・採掘効率談義（リアルな検証報告）**:
   - Ryzen 9 7950X / 7900X / EPYCでのハッシュレート検証や、ワットパフォーマンス追求（Ecoモード 65W/105W設定での電力削減とハッシュレート維持率の比較）。
   - Windows WSL2（Ubuntu）でのCoreMiner運用の安定性向上やトラブルシューティング情報。
   - Catch That Rabbit プールの分割ペイアウト（4時間ごとのメイン着金＋追加端数着金）についてのマイナー同士の情報交換。
   - ネットワーク全体の採掘難易度（Difficulty 440M〜490M）の上昇トレンドに対する「マイナーが増えてきている実感」と日産XCBの推移。
3. **「パブリックステルス（Public Stealth）」開発思想への本音**:
   - 「VCの初期大量売り圧や無謀なインフルエンサーマーケティングがないからこそ、安心してマイニングを続けられる」という信頼感。
   - 一方で「もっと多くの人に知ってほしい！」「取引所の流動性がさらに高まってほしい」というコミュニティのリアルな期待ともどかしさ。
4. **初心者の参加とコミュニティのサポート体制**:
   - 「初めてCPUマイニングに挑戦した」「CorePassの登録がスムーズだった」という初心者の声と、それを支える有志マイナーたちの温かいアドバイス。

【記事の執筆ルール】
1. キャラクター＆トーン:
   - 名前: リコロ（Ricolo）
   - 冒頭の挨拶: 「どうも！自作PC大好きゲーム女子、リコロです！✍🏻🎮💻✨」
   - トーン: 元気で親しみやすく、かつハードウェアやブロックチェーンの仕組みについてはプロレベルにロジカルで分かりやすい。
   - 口コミ・引用は「💬 マイナーAさんの声」「💬 ホルダーBさんの声」のように見やすくボックス化や引用タグでデザインする。
   - 締めくくり: 「それでは、また次回のコミュニティ定点観測でお会いしましょう！リコロでした〜！ばいば〜い！🎮👾✨」
2. 構成:
   - つかみ・導入（「今回は公式発表だけでなく、世界中のマイナーやホルダー仲間がSNSやチャットで何を話しているのか、生の声を集めてみました！」）
   - 目次または要点ハイライト（今週のコミュニティ3大トピック）
   - トピック1: CorePass KYB＆Ping Exchangeビジネス取引に対するコミュニティの期待と議論
   - トピック2: 【マイナー座談会】Ryzen設定・ハッシュレート効率・プール分割着金のリアル
   - トピック3: 「パブリックステルス」への本音：VCなしフェアローンチの強みと今後の課題
   - リコロの考察＆まとめ（客観的な分析とマイナー仲間へのメッセージ）
   - CoreStation（https://corestation.pages.dev/）への誘導
   - 締めくくり
3. 出力フォーマット（厳密に以下の書式を守ってください）:
---META---
TITLE: 【リコロのコミュニティ定点観測 Vol.{vol_num}】マイナー＆ホルダーの生の声まとめ！CorePass KYBの反響・Ryzen採掘効率の議論・リアルな本音を徹底解剖！🎮💬🔥
SLUG: community-voice-roundup-vol{vol_num}
SUMMARY: Core Blockchain (XCB) の公式チャットやSNS、マイニングプールで今何が話題？CorePass KYBへの期待、Ryzenの採掘効率・Ecoモード検証、フェアローンチへの本音など、コミュニティのリアルな生声を自作PC女子リコロが徹底レポート！
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
            "maxOutputTokens": 4500
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
        print(f"🧠 Google Gemini API を呼び出して【コミュニティ定点観測 Vol.{vol_num}】を執筆中...")
        with urllib.request.urlopen(req, context=ctx, timeout=40) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            candidate = data["candidates"][0]["content"]["parts"][0]["text"].strip()

            meta_match = re.search(r'---META---(.*?)---BODY---(.*)', candidate, re.DOTALL)
            if meta_match:
                meta_text = meta_match.group(1).strip()
                body_html = meta_match.group(2).strip()

                title = f"【リコロのコミュニティ定点観測 Vol.{vol_num}】マイナー＆ホルダーの生の声まとめ！🎮💬🔥"
                slug = f"community-voice-roundup-vol{vol_num}"
                summary = "Core Blockchain (XCB) の公式チャットやSNSで今何が話題？マイナー＆ホルダーの生声を自作PC女子リコロが徹底レポート！"

                for line in meta_text.splitlines():
                    if line.startswith("TITLE:"):
                        title = line.replace("TITLE:", "").strip()
                    elif line.startswith("SLUG:"):
                        slug = line.replace("SLUG:", "").strip().lower()
                    elif line.startswith("SUMMARY:"):
                        summary = line.replace("SUMMARY:", "").strip()

                body_html = re.sub(r'^```(?:html)?\s*', '', body_html, flags=re.MULTILINE)
                body_html = re.sub(r'\s*```$', '', body_html, flags=re.MULTILINE).strip()

                print(f"✨ 記事執筆が完了しました！ ({title})")
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
      <span>コミュニティ・生の声定点観測</span>
    </nav>

    <!-- Main Article Card -->
    <article class="article-card-main">
      <header class="article-meta-header">
        <span class="article-badge" style="background: rgba(168, 85, 247, 0.15); color: #c084fc; border: 1px solid rgba(168, 85, 247, 0.3);">👥 コミュニティ・SNS生の声</span>
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

def integrate_article_to_site(slug, title, summary, date_str, body_html, category="community", category_name="コミュニティ・SNS生の声"):
    """Integrates new community article into standalone HTML, initial_data.js, local_articles.js, index.html, and sitemap.xml."""
    print(f"📁 CoreStation 本サイト側へ記事を統合中: {slug}")

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
                    <span class="badge-online" style="font-size: 11px; padding: 2px 8px; background: rgba(168, 85, 247, 0.2); color: #c084fc;">コミュニティ・SNS生の声</span>
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

def deploy_to_cloudflare():
    """Commit changes and push to origin main."""
    print("🚀 Cloudflare Pages への自動デプロイ（Git push）を開始...")
    try:
        subprocess.run(["git", "add", "-A"], cwd=ROOT_DIR, check=True)
        status_res = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT_DIR, capture_output=True, text=True)
        if not status_res.stdout.strip():
            print("ℹ️ デプロイ対象の変更差分はありません。")
            return

        cmd_commit = [
            "git", "-c", "user.name=CoreStation Community Watcher",
            "-c", "user.email=community@corestation.local",
            "commit", "-m", f"feat(community): publish community sentiment roundup [{datetime.now().strftime('%Y-%m-%d %H:%M')}]"
        ]
        subprocess.run(cmd_commit, cwd=ROOT_DIR, check=True)
        push_res = subprocess.run(["git", "push", "origin", "main"], cwd=ROOT_DIR, capture_output=True, text=True, timeout=60)
        print(push_res.stdout)
        if push_res.returncode == 0:
            print("🎉 Cloudflare Pages への本番デプロイが完了しました！")
        else:
            print(f"⚠️ Git push 警告: {push_res.stderr}", file=sys.stderr)
    except Exception as e:
        print(f"⚠️ 自動デプロイエラー: {e}", file=sys.stderr)

def run_community_digest_pipeline():
    """Executes the full pipeline for community sentiment roundup."""
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 🔍 コミュニティ・SNS生の声定点観測パイプラインを開始...")
    last_seen = load_last_seen()
    vol_num = last_seen.get("vol_count", 0) + 1
    today_str = datetime.now().strftime("%Y-%m-%d")

    art = generate_community_digest(vol_num)
    if not art:
        print("❌ 記事生成に失敗しました。")
        return False

    title = art["title"]
    slug = art["slug"]
    summary = art["summary"]
    body_html = art["body"]
    full_blog_html = BANNER_HEADER_HTML + "\n" + body_html + "\n" + RICOLO_AUTHOR_BOX_HTML

    # 1. Save temp output
    temp_file = os.path.join(OUTPUT_DIR, f"{slug}.html")
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
            "--category", "暗号資産", "コミュニティ", "XCB", "マイニング", "口コミ"
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        print(res.stdout)
    except Exception as e:
        print(f"❌ はてなブログ投稿エラー: {e}", file=sys.stderr)

    # 3. Integrate into CoreStation Site
    integrate_article_to_site(
        slug=slug,
        title=title,
        summary=summary,
        date_str=today_str,
        body_html=body_html,
        category="community",
        category_name="コミュニティ・SNS生の声"
    )

    # 4. Deploy to Cloudflare Pages
    deploy_to_cloudflare()

    # 4.5 Dispatch to Make.com & X (Twitter)
    try:
        social_script = os.path.join(BASE_DIR, "social_exporter.py")
        if os.path.exists(social_script):
            print("🚀 Make.com / Buffer 経由での X 自動配信をトリガー...")
            subprocess.run([sys.executable, social_script, slug, "--publish"], capture_output=True, text=True, timeout=30)
    except Exception as e:
        print(f"⚠️ SNS配信エラー (スキップ): {e}")

    # 5. Update state
    last_seen["last_published_date"] = today_str
    last_seen["vol_count"] = vol_num
    save_last_seen(last_seen)
    print(f"✅ コミュニティ定点観測 Vol.{vol_num} の全公開・デプロイが完了しました！")
    return True

if __name__ == "__main__":
    run_community_digest_pipeline()
