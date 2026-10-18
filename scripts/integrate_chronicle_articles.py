#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Integrate Core Chronicle Updates (1605, 1606) into CoreStation Standalone Articles,
initial_data.js, local_articles.js, index.html, and sitemap.xml.
"""

import os
import sys
import re
import json
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARTICLES_DIR = os.path.join(BASE_DIR, "articles")
DATA_DIR = os.path.join(BASE_DIR, "data")
INITIAL_DATA_PATH = os.path.join(DATA_DIR, "initial_data.js")
LOCAL_ARTICLES_PATH = os.path.join(DATA_DIR, "local_articles.js")
INDEX_PATH = os.path.join(BASE_DIR, "index.html")
SITEMAP_PATH = os.path.join(BASE_DIR, "sitemap.xml")

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

def add_article_to_system(slug, title, summary, date_str, body_html, category="ecosystem", category_name="速報・公式アナウンス"):
    print(f"🚀 Adding article: {slug} - {title}")
    
    # 1. Write standalone HTML
    out_path = os.path.join(ARTICLES_DIR, f"{slug}.html")
    full_html = build_standalone_article_html(slug, title, summary, date_str, body_html)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(full_html)
    print(f"  ✅ Created {out_path}")

    # 2. Update data/initial_data.js
    with open(INITIAL_DATA_PATH, "r", encoding="utf-8") as f:
        init_data_content = f.read()

    article_archive_needle = '"articlesArchive": ['
    if article_archive_needle in init_data_content and f'"id": "{slug}"' not in init_data_content:
        archive_item = f"""    {{
      "id": "{slug}",
      "title": {json.dumps(title, ensure_ascii=False)},
      "category": "{category}",
      "categoryName": "{category_name}",
      "date": "{date_str}",
      "summary": {json.dumps(summary, ensure_ascii=False)}
    }},\n"""
        init_data_content = init_data_content.replace(article_archive_needle, article_archive_needle + "\n" + archive_item)
        with open(INITIAL_DATA_PATH, "w", encoding="utf-8") as f:
            f.write(init_data_content)
        print("  ✅ Updated data/initial_data.js")

    # 3. Update data/local_articles.js
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
                "content": body_html
            }
            articles_list.insert(0, new_item)
            new_local_content = prefix + json.dumps(articles_list, ensure_ascii=False, indent=2) + ";\n"
            with open(LOCAL_ARTICLES_PATH, "w", encoding="utf-8") as f:
                f.write(new_local_content)
            print("  ✅ Updated data/local_articles.js")
        except Exception as e:
            print(f"  ⚠️ Error parsing local_articles.js: {e}")

    # 4. Update index.html
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
        print("  ✅ Updated index.html")

    # 5. Update sitemap.xml
    with open(SITEMAP_PATH, "r", encoding="utf-8") as f:
        sitemap_xml = f.read()

    if f"/articles/{slug}</loc>" not in sitemap_xml:
        sitemap_entry = f"""  <url>
    <loc>https://corestation.pages.dev/articles/{slug}</loc>
    <lastmod>{date_str}</lastmod>
    <changefreq>weekly</changefreq>
    <priority>0.85</priority>
  </url>\n"""
        # Insert before closing </urlset>
        sitemap_xml = sitemap_xml.replace("</urlset>", sitemap_entry + "</urlset>")
        with open(SITEMAP_PATH, "w", encoding="utf-8") as f:
            f.write(sitemap_xml)
        print("  ✅ Updated sitemap.xml")

def clean_body_html(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Remove the banner header and ricolo author box since standalone article has them natively
    content = re.sub(r'<!-- CoreStation Official Brand Header Banner -->.*?</div>\s*</div>', '', content, flags=re.DOTALL)
    content = re.sub(r'<!-- Ricolo Official Author Profile Box -->.*?</div>\s*</div>', '', content, flags=re.DOTALL)
    
    # Strip wrapping divs if present
    content = re.sub(r'^\s*<div style="line-height:[^>]*>', '', content)
    content = re.sub(r'</div>\s*$', '', content)
    return content.strip()

def main():
    today = "2026-10-18"

    # Article 1: 1605 (Ping Exchange Maintenance & KYB Launch)
    html_1605 = clean_body_html(os.path.join(BASE_DIR, "hub", "output", "chronicle_update_codetechcc_1605.html"))
    add_article_to_system(
        slug="ping-exchange-kyb-maintenance-launch",
        title="【速報・解説】Core BlockchainのPing Exchangeが大型アプデ！新KYB取引サービス正式ローンチの全貌🚀✨",
        summary="2026年10月15日、Ping Exchangeが一時メンテナンスを経て「新KYB取引サービス」を正式ローンチ！企業向け本人確認インフラと取引所が直結し、組織レベルのデジタル資産運用が可能に。重要ポイントとマイナー・ホルダーへの影響を自作PC女子リコロが徹底解説。",
        date_str=today,
        body_html=html_1605,
        category="ecosystem",
        category_name="速報・公式アナウンス"
    )

    # Article 2: 1606 (Ping Exchange Business Trading Live)
    html_1606 = clean_body_html(os.path.join(BASE_DIR, "hub", "output", "chronicle_update_codetechcc_1606.html"))
    add_article_to_system(
        slug="ping-exchange-business-trading-live",
        title="【速報・解説】Core Blockchainがビジネス取引の新章を開く！Ping Exchangeビジネス取引インフラ稼働の全貌🎮⚡️",
        summary="CorePassの企業分散ID（KYB）が遂にPing Exchangeで実働開始！「ID・権限・説明責任」が一体化した世界初のビジネス取引インフラの全貌と、XCB/CTN経済圏への影響を自作PC女子リコロがわかりやすく深掘り解説。",
        date_str=today,
        body_html=html_1606,
        category="ecosystem",
        category_name="速報・公式アナウンス"
    )

if __name__ == "__main__":
    main()
