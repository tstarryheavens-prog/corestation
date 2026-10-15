#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CoreStation Static Site Generator for AdSense Approval & SEO
=============================================================
Generates:
1. articles/[id].html for all 27 knowledge articles
2. privacy.html (Standalone Google AdSense Compliant Privacy Policy)
3. disclaimer.html (Standalone Legal & Investment Disclaimer)
4. about.html (Standalone About & Contact with verified operator info)
5. sitemap.xml & robots.txt
6. Updates index.html with static fallback article cards & crawler-friendly links
"""

import os
import json
import html
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARTICLES_DIR = os.path.join(BASE_DIR, "articles")
DATA_DIR = os.path.join(BASE_DIR, "data")
LOCAL_ARTICLES_PATH = os.path.join(DATA_DIR, "local_articles.js")

os.makedirs(ARTICLES_DIR, exist_ok=True)

# 1. Load articles from local_articles.js
with open(LOCAL_ARTICLES_PATH, "r", encoding="utf-8") as f:
    text = f.read()

prefix = "window.__CORE_LOCAL_ARTICLES__ = "
idx = text.find(prefix)
if idx == -1:
    raise ValueError("Prefix not found in local_articles.js")

json_str = text[idx + len(prefix):].rstrip().rstrip(";")
articles = json.loads(json_str)
print(f"[SSG] Loaded {len(articles)} articles from local_articles.js")

# 2. Write articles/article.css
article_css_content = """/* CoreStation Article Dedicated Styles */
body.article-page-body {
  background-color: var(--bg-base, #0b0f19);
  color: var(--text-main, #e2e8f0);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  margin: 0;
  padding: 0;
  line-height: 1.8;
}

.article-header-nav {
  background: rgba(15, 23, 42, 0.95);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid var(--border-color, #1e293b);
  position: sticky;
  top: 0;
  z-index: 100;
  padding: 12px 24px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.article-brand {
  display: flex;
  align-items: center;
  gap: 12px;
  text-decoration: none;
  color: #fff;
  font-weight: 700;
  font-size: 1.15rem;
}

.article-brand img {
  width: 32px;
  height: 32px;
}

.article-nav-links {
  display: flex;
  gap: 16px;
  align-items: center;
}

.article-nav-links a {
  color: #94a3b8;
  text-decoration: none;
  font-size: 0.9rem;
  font-weight: 500;
  transition: color 0.2s ease;
}

.article-nav-links a:hover {
  color: #38bdf8;
}

.article-container {
  max-width: 880px;
  margin: 0 auto;
  padding: 32px 20px 64px;
}

.breadcrumb {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  font-size: 0.85rem;
  color: #64748b;
  margin-bottom: 24px;
}

.breadcrumb a {
  color: #38bdf8;
  text-decoration: none;
}

.breadcrumb span.sep {
  color: #475569;
}

.article-card-main {
  background: var(--bg-surface, #131d31);
  border: 1px solid var(--border-color, #1e293b);
  border-radius: 16px;
  padding: 36px 40px;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.25);
}

@media (max-width: 640px) {
  .article-card-main {
    padding: 24px 18px;
  }
}

.article-meta-header {
  border-bottom: 1px solid #1e293b;
  padding-bottom: 20px;
  margin-bottom: 28px;
}

.article-badge {
  display: inline-block;
  background: linear-gradient(135deg, #3b82f6, #6366f1);
  color: #fff;
  font-size: 0.75rem;
  font-weight: 700;
  padding: 4px 10px;
  border-radius: 6px;
  margin-bottom: 12px;
}

.article-main-title {
  font-size: 1.85rem;
  font-weight: 800;
  line-height: 1.4;
  color: #f8fafc;
  margin: 0 0 14px;
}

@media (max-width: 640px) {
  .article-main-title {
    font-size: 1.4rem;
  }
}

.article-submeta {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  font-size: 0.85rem;
  color: #94a3b8;
}

.article-content-body {
  color: #cbd5e1;
  font-size: 1.05rem;
  line-height: 1.9;
}

.article-content-body h2 {
  color: #f1f5f9;
  font-size: 1.45rem;
  margin-top: 40px;
  padding-bottom: 8px;
}

.article-content-body h3 {
  color: #e2e8f0;
  font-size: 1.2rem;
  margin-top: 28px;
}

.article-content-body p {
  margin-bottom: 1.5em;
}

.article-content-body table {
  width: 100%;
  border-collapse: collapse;
  margin: 24px 0;
  font-size: 0.9rem;
}

.article-content-body th, .article-content-body td {
  padding: 10px 14px;
  border: 1px solid #334155;
}

.article-content-body th {
  background: #1e293b;
  color: #f8fafc;
  font-weight: 700;
}

.article-content-body a {
  color: #38bdf8;
}

.article-bottom-cta {
  margin-top: 48px;
  padding: 24px;
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.12) 0%, rgba(99, 102, 241, 0.12) 100%);
  border: 1px solid rgba(59, 130, 246, 0.3);
  border-radius: 12px;
  text-align: center;
}

.article-bottom-cta h3 {
  margin-top: 0;
  color: #60a5fa;
  font-size: 1.25rem;
}

.article-cta-btn {
  display: inline-block;
  background: linear-gradient(135deg, #3b82f6, #6366f1);
  color: #fff;
  padding: 10px 24px;
  border-radius: 8px;
  text-decoration: none;
  font-weight: 700;
  font-size: 0.95rem;
  margin-top: 12px;
  transition: transform 0.2s, box-shadow 0.2s;
}

.article-cta-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 14px rgba(59, 130, 246, 0.4);
}

.article-related-section {
  margin-top: 48px;
}

.related-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 16px;
  margin-top: 16px;
}

.related-card {
  background: #131d31;
  border: 1px solid #1e293b;
  border-radius: 10px;
  padding: 16px;
  text-decoration: none;
  color: inherit;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  transition: border-color 0.2s ease, transform 0.2s ease;
}

.related-card:hover {
  border-color: #38bdf8;
  transform: translateY(-2px);
}

.related-card-title {
  font-size: 0.95rem;
  font-weight: 700;
  color: #f1f5f9;
  line-height: 1.4;
  margin-bottom: 8px;
}

.related-card-date {
  font-size: 0.75rem;
  color: #64748b;
}

.article-footer {
  border-top: 1px solid #1e293b;
  padding: 32px 20px;
  margin-top: 64px;
  text-align: center;
  font-size: 0.85rem;
  color: #64748b;
}

.article-footer-links {
  display: flex;
  justify-content: center;
  gap: 20px;
  flex-wrap: wrap;
  margin-bottom: 12px;
}

.article-footer-links a {
  color: #94a3b8;
  text-decoration: none;
}

.article-footer-links a:hover {
  color: #38bdf8;
}
"""

with open(os.path.join(ARTICLES_DIR, "article.css"), "w", encoding="utf-8") as f:
    f.write(article_css_content)
print("[SSG] Created articles/article.css")

# 3. Build articles/[id].html for each article
for i, art in enumerate(articles):
    art_id = art.get("id")
    title = html.escape(art.get("title", ""))
    summary = html.escape(art.get("summary", ""))
    cat_name = html.escape(art.get("categoryName", "技術ナレッジ"))
    date_str = art.get("date", "2026-09-18")
    content = art.get("content", "")

    # Related articles (3 other articles)
    related = [a for a in articles if a.get("id") != art_id][:3]
    related_html = ""
    for r in related:
        r_title = html.escape(r.get("title", ""))
        r_id = r.get("id")
        r_date = r.get("date", "")
        related_html += f"""
          <a href="{r_id}.html" class="related-card">
            <div class="related-card-title">{r_title}</div>
            <div class="related-card-date">📅 {r_date}</div>
          </a>
        """

    article_page_html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title} | CoreStation ナレッジ</title>
  <meta name="description" content="{summary}">
  <link rel="canonical" href="https://corestation.pages.dev/articles/{art_id}">
  <link rel="icon" type="image/svg+xml" href="../assets/core-icon.svg">
  
  <!-- OGP / Social Sharing -->
  <meta property="og:title" content="{title}">
  <meta property="og:description" content="{summary}">
  <meta property="og:url" content="https://corestation.pages.dev/articles/{art_id}">
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
  <link rel="stylesheet" href="../style.css?v=20261006_4">
  <link rel="stylesheet" href="article.css?v=20261015_1">

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
        "mainEntityOfPage": "https://corestation.pages.dev/articles/{art_id}"
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
            "item": "https://corestation.pages.dev/articles/{art_id}"
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
      <span>{cat_name}</span>
    </nav>

    <!-- Main Article Card -->
    <article class="article-card-main">
      <header class="article-meta-header">
        <span class="article-badge">{cat_name}</span>
        <h1 class="article-main-title">{title}</h1>
        <div class="article-submeta">
          <span>📅 公開日: {date_str}</span>
          <span>✍️ 執筆: リコロ (Ricolo)</span>
          <span>🔒 監修: CoreStation 技術検証チーム</span>
        </div>
      </header>

      <!-- Article Content Body -->
      <div class="article-content-body">
        {content}
      </div>

      <!-- Bottom CTA Banner -->
      <section class="article-bottom-cta">
        <h3>⚡ Core Blockchain (XCB) の最新データをチェック！</h3>
        <p style="color: #94a3b8; font-size: 0.95rem; margin-bottom: 0;">
          リアルタイム採掘報酬、最新ブロック高、難易度推移、確定申告CSV生成は「CoreStation」で完全無料公開中！
        </p>
        <a href="../#dashboard" class="article-cta-btn">🚀 CoreStation ダッシュボードへ戻る</a>
      </section>

      <!-- Related Articles Section -->
      <section class="article-related-section">
        <h3 style="color: #f1f5f9; font-size: 1.25rem; border-left: 4px solid #38bdf8; padding-left: 12px;">📚 関連記事・おすすめトピック</h3>
        <div class="related-grid">
          {related_html}
        </div>
      </section>
    </article>
  </main>

  <!-- Global Footer -->
  <footer class="article-footer">
    <div class="article-footer-links">
      <a href="../">ダッシュボード</a>
      <a href="../privacy.html">プライバシーポリシー</a>
      <a href="../disclaimer.html">免責事項</a>
      <a href="../about.html">運営者情報・お問い合わせ</a>
      <a href="https://corestation.hatenadiary.com/" target="_blank" rel="noopener noreferrer">公式ブログ (はてな) ↗</a>
    </div>
    <div>&copy; 2026 CoreStation / Ricolo. All Rights Reserved.</div>
  </footer>

</body>
</html>"""

    art_file_path = os.path.join(ARTICLES_DIR, f"{art_id}.html")
    with open(art_file_path, "w", encoding="utf-8") as f:
        f.write(article_page_html)

print(f"[SSG] Successfully generated {len(articles)} standalone HTML articles in articles/")

# 4. Generate privacy.html
privacy_html = """<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>プライバシーポリシー (Privacy Policy) | CoreStation</title>
  <meta name="description" content="CoreStation（コアステーション）における個人情報保護方針、Cookieの取り扱い、Google AdSense広告配信およびアクセス解析ツールに関するプライバシーポリシーです。">
  <link rel="canonical" href="https://corestation.pages.dev/privacy">
  <link rel="icon" type="image/svg+xml" href="assets/core-icon.svg">
  
  <!-- Google AdSense Verification & Auto-Ads Tag -->
  <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-1988464307898443" crossorigin="anonymous"></script>

  <!-- Stylesheets -->
  <link rel="stylesheet" href="style.css?v=20261006_4">
  <link rel="stylesheet" href="articles/article.css?v=20261015_1">
</head>
<body class="article-page-body">

  <header class="article-header-nav">
    <a href="./#dashboard" class="article-brand">
      <img src="assets/core-icon.svg" alt="CoreStation Logo">
      <span>CoreStation</span>
    </a>
    <nav class="article-nav-links">
      <a href="./#dashboard">📊 ダッシュボード</a>
      <a href="./#articles">📚 記事一覧</a>
      <a href="./about.html">🏢 運営者情報</a>
    </nav>
  </header>

  <main class="article-container">
    <nav class="breadcrumb">
      <a href="./">ホーム</a>
      <span class="sep">&gt;</span>
      <span>プライバシーポリシー</span>
    </nav>

    <article class="article-card-main">
      <header class="article-meta-header">
        <h1 class="article-main-title">📜 プライバシーポリシー (Privacy Policy)</h1>
        <div class="article-submeta">
          <span>制定日: 2026年9月12日</span>
          <span>最終改定日: 2026年10月15日</span>
        </div>
      </header>

      <div class="article-content-body">
        <h2>1. 個人情報の収集および利用目的</h2>
        <p>
          当サイト（CoreStation: <code>https://corestation.pages.dev/</code>、以下「当サイト」といいます）では、お問い合わせやご意見をいただく際、お名前（ハンドルネーム）やメールアドレス等の個人情報をご提供いただく場合があります。<br>
          収集した個人情報は、ご質問への回答や必要な情報をご連絡するためにのみ利用し、目的外の利用はいたしません。
        </p>

        <h2>2. Cookie（クッキー）の利用について</h2>
        <p>
          当サイトでは、ユーザーの利便性向上、トラフィック分析、および広告配信のためにCookieを利用しています。<br>
          Cookieはブラウザを識別するための技術ですが、特定の個人を直接識別する情報（氏名、生年月日、住所、電話番号等）は含まれておりません。ブラウザの設定によりCookieを無効化することも可能です。
        </p>

        <h2>3. 広告配信サービス（Google AdSense等）について</h2>
        <p>
          当サイトは、第三者配信事業者（Google AdSenseを含む）の提供する広告サービスを利用しています。<br>
          Googleなどの第三者広告配信事業者は、Cookieを使用して、ユーザーが当サイトや他のウェブサイトに過去にアクセスした際の情報に基づいて広告を配信します。
        </p>
        <div style="background: rgba(59, 130, 246, 0.1); padding: 16px; border-left: 4px solid #3b82f6; border-radius: 6px; margin: 16px 0;">
          <strong>パーソナライズ広告の無効化について：</strong><br>
          ユーザーは、<a href="https://adssettings.google.com/" target="_blank" rel="noopener noreferrer" style="color: #60a5fa; font-weight: 600;">Google広告設定</a> にアクセスすることで、パーソナライズ広告を無効にできます。<br>
          また、<a href="https://www.aboutads.info/choices/" target="_blank" rel="noopener noreferrer" style="color: #60a5fa; font-weight: 600;">www.aboutads.info</a> にアクセスして、第三者配信事業者がパーソナライズド広告に使用するCookieを一括して無効化することも可能です。
        </div>

        <h2>4. アクセス解析ツールについて</h2>
        <p>
          当サイトでは、トラフィックデータの収集のためにアクセス解析ツールを利用する場合があります。このトラフィックデータは匿名で収集されており、個人を特定するものではありません。
        </p>

        <h2>5. プライバシーポリシーの改定</h2>
        <p>
          当サイトは、法令の改正やサービス運営方針の変更に伴い、本プライバシーポリシーを予告なく改定することがあります。改定後のプライバシーポリシーは、当サイトに掲載された時点で効力を発揮します。
        </p>

        <h2>6. お問い合わせ先</h2>
        <p>
          当サイトの個人情報の取扱いに関するご相談は、<a href="about.html">運営者情報・お問い合わせページ</a>記載の窓口よりご連絡ください。
        </p>
      </div>
    </article>
  </main>

  <footer class="article-footer">
    <div class="article-footer-links">
      <a href="./">ダッシュボード</a>
      <a href="privacy.html">プライバシーポリシー</a>
      <a href="disclaimer.html">免責事項</a>
      <a href="about.html">運営者情報・お問い合わせ</a>
    </div>
    <div>&copy; 2026 CoreStation / Ricolo. All Rights Reserved.</div>
  </footer>

</body>
</html>"""

with open(os.path.join(BASE_DIR, "privacy.html"), "w", encoding="utf-8") as f:
    f.write(privacy_html)
print("[SSG] Created privacy.html")

# 5. Generate disclaimer.html
disclaimer_html = """<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>免責事項・リスク開示 (Disclaimer) | CoreStation</title>
  <meta name="description" content="CoreStation（コアステーション）における投資判断、税務計算、ハードウェア設定チューニング等に関する免責事項およびリスク開示です。">
  <link rel="canonical" href="https://corestation.pages.dev/disclaimer">
  <link rel="icon" type="image/svg+xml" href="assets/core-icon.svg">
  
  <!-- Google AdSense Verification & Auto-Ads Tag -->
  <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-1988464307898443" crossorigin="anonymous"></script>

  <!-- Stylesheets -->
  <link rel="stylesheet" href="style.css?v=20261006_4">
  <link rel="stylesheet" href="articles/article.css?v=20261015_1">
</head>
<body class="article-page-body">

  <header class="article-header-nav">
    <a href="./#dashboard" class="article-brand">
      <img src="assets/core-icon.svg" alt="CoreStation Logo">
      <span>CoreStation</span>
    </a>
    <nav class="article-nav-links">
      <a href="./#dashboard">📊 ダッシュボード</a>
      <a href="./#articles">📚 記事一覧</a>
      <a href="./about.html">🏢 運営者情報</a>
    </nav>
  </header>

  <main class="article-container">
    <nav class="breadcrumb">
      <a href="./">ホーム</a>
      <span class="sep">&gt;</span>
      <span>免責事項・リスク開示</span>
    </nav>

    <article class="article-card-main">
      <header class="article-meta-header">
        <h1 class="article-main-title">⚠️ 免責事項・リスク開示 (Disclaimer)</h1>
        <div class="article-submeta">
          <span>最終改定日: 2026年10月15日</span>
        </div>
      </header>

      <div class="article-content-body">
        <h2>1. 投資判断・金融商品取引に関する免責</h2>
        <p>
          当サイトに掲載されている暗号資産（Core Blockchain / XCB / CTN等）に関する情報は、ブロックチェーンの技術的仕組み、マイニングソフトウェアの設定方法、分散型ネットワーク運用の情報提供を目的としており、<strong>投資助言業務や特定の暗号資産の売買を勧誘・推奨するものではありません。</strong><br>
          暗号資産は価格変動が極めて大きく、元本割れや資産価値の喪失リスクを伴います。暗号資産の取引および投資判断は、必ずご自身の責任と判断において行ってください。
        </p>

        <h2>2. 税務情報および確定申告に関する免責</h2>
        <p>
          当サイトに掲載しているマイニング所得の計算方法、税務上の取り扱い、および本サイトで生成されるCSVデータは、公開された税法情報に基づく一般的な支援ツールです。税理士法に定める「個別の税務相談」を提供するものではありません。<br>
          実際の税務申告および必要経費の計上等にあたっては、所轄の税務署または税理士等の専門家にご相談の上、ご自身で最終確認をお願いいたします。
        </p>

        <h2>3. ハードウェア設定・マイニングチューニングに関する免責</h2>
        <p>
          当サイトで紹介しているCPUの低電圧化（Curve Optimizer等）、BIOSの電力制限（Eco-Mode等）、スレッド数設定などのチューニング情報は、筆者の環境での実測・検証結果に基づくものです。<br>
          設定変更に伴う機器の故障、発熱、クラッシュ、保証対象外となる行為、電気代の増加等に関して、当サイトおよび運営者は一切の責任を負いかねます。すべて自己責任にて実行してください。
        </p>

        <h2>4. 掲載情報の正確性および外部リンクについて</h2>
        <p>
          当サイトに掲載されている情報については、可能な限り正確な情報を掲載するよう努めておりますが、技術のアップデートや時間の経過に伴い、内容に誤りや変更が生じる場合があります。掲載内容によって生じた損害等について、当サイトは一切の責任を負いません。<br>
          また、当サイトからリンクされた外部サイトで提供されるサービスや情報についても同様に責任を負いません。
        </p>
      </div>
    </article>
  </main>

  <footer class="article-footer">
    <div class="article-footer-links">
      <a href="./">ダッシュボード</a>
      <a href="privacy.html">プライバシーポリシー</a>
      <a href="disclaimer.html">免責事項</a>
      <a href="about.html">運営者情報・お問い合わせ</a>
    </div>
    <div>&copy; 2026 CoreStation / Ricolo. All Rights Reserved.</div>
  </footer>

</body>
</html>"""

with open(os.path.join(BASE_DIR, "disclaimer.html"), "w", encoding="utf-8") as f:
    f.write(disclaimer_html)
print("[SSG] Created disclaimer.html")

# 6. Generate about.html
about_html = """<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>運営者情報 ＆ お問い合わせ (About & Contact) | CoreStation</title>
  <meta name="description" content="CoreStation（コアステーション）の運営者情報、サイト運営目的、技術検証ハードウェア環境、およびお問い合わせ窓口について。">
  <link rel="canonical" href="https://corestation.pages.dev/about">
  <link rel="icon" type="image/svg+xml" href="assets/core-icon.svg">
  
  <!-- Google AdSense Verification & Auto-Ads Tag -->
  <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-1988464307898443" crossorigin="anonymous"></script>

  <!-- Stylesheets -->
  <link rel="stylesheet" href="style.css?v=20261006_4">
  <link rel="stylesheet" href="articles/article.css?v=20261015_1">
</head>
<body class="article-page-body">

  <header class="article-header-nav">
    <a href="./#dashboard" class="article-brand">
      <img src="assets/core-icon.svg" alt="CoreStation Logo">
      <span>CoreStation</span>
    </a>
    <nav class="article-nav-links">
      <a href="./#dashboard">📊 ダッシュボード</a>
      <a href="./#articles">📚 記事一覧</a>
      <a href="./about.html">🏢 運営者情報</a>
    </nav>
  </header>

  <main class="article-container">
    <nav class="breadcrumb">
      <a href="./">ホーム</a>
      <span class="sep">&gt;</span>
      <span>運営者情報 ＆ お問い合わせ</span>
    </nav>

    <article class="article-card-main">
      <header class="article-meta-header">
        <h1 class="article-main-title">🏢 運営者情報 ＆ お問い合わせ (About & Contact)</h1>
      </header>

      <div class="article-content-body">
        <h2>1. サイト概要</h2>
        <table>
          <tr>
            <th style="width: 140px;">サイト名</th>
            <td>CoreStation（コアステーション）</td>
          </tr>
          <tr>
            <th>URL</th>
            <td><a href="https://corestation.pages.dev/">https://corestation.pages.dev/</a></td>
          </tr>
          <tr>
            <th>運営目的</th>
            <td>
              Core Blockchain（XCB）における完全自立型マイニングノードの運用支援、確定申告用資産データの管理、および耐量子暗号・PoDE等の技術仕様に関する客観的情報の普及・発信。
            </td>
          </tr>
          <tr>
            <th>公式ブログ</th>
            <td><a href="https://corestation.hatenadiary.com/" target="_blank" rel="noopener noreferrer">CoreStation はてなブログ ↗</a></td>
          </tr>
          <tr>
            <th>執筆担当・キャラクター</th>
            <td>リコロ（Ricolo / 自作PC＆ゲーム好きWeb3ライター）</td>
          </tr>
        </table>

        <h2>2. 技術検証・実測ハードウェア環境</h2>
        <p>当サイトの解説記事・マイニングベンチマークは、以下の実機環境で検証・実測を行っています。</p>
        <ul>
          <li><strong>リグ 1 (メイン):</strong> AMD Ryzen 9 7950X (16C/32T), DDR5-6000 64GB, Eco Mode 105W/Curve Optimizer -25</li>
          <li><strong>リグ 2:</strong> Intel Core i9-14900 (24C/32T), DDR5-5600 32GB, PL1 125W 制限</li>
          <li><strong>リグ 3:</strong> Intel Core i5-13500 (14C/20T), DDR4-3200 32GB</li>
          <li><strong>常時稼働NASサーバー:</strong> ASUSTOR AS3102T (Docker / Python 3 / SQLite)</li>
        </ul>

        <h2>3. お問い合わせ窓口</h2>
        <p>当サイトの掲載内容に関するご質問、技術的な誤りのご指摘、または各種お問い合わせは、以下の窓口までお寄せください。</p>

        <div style="background: rgba(59, 130, 246, 0.1); border: 1px solid rgba(59, 130, 246, 0.3); border-radius: 8px; padding: 20px; margin: 20px 0;">
          <ul style="margin: 0; padding-left: 20px; line-height: 1.8;">
            <li>
              <strong>公式ブログ コメント欄:</strong><br>
              各記事のコメント欄（<a href="https://corestation.hatenadiary.com/" target="_blank" rel="noopener noreferrer">corestation.hatenadiary.com</a>）よりお寄せください。
            </li>
            <li style="margin-top: 10px;">
              <strong>GitHub リポジトリ / Issue:</strong><br>
              ソースコードや技術的課題のご報告は <a href="https://github.com/tstarryheavens-prog/corestation/issues" target="_blank" rel="noopener noreferrer">GitHub Issues ↗</a> へお寄せください。
            </li>
          </ul>
        </div>
      </div>
    </article>
  </main>

  <footer class="article-footer">
    <div class="article-footer-links">
      <a href="./">ダッシュボード</a>
      <a href="privacy.html">プライバシーポリシー</a>
      <a href="disclaimer.html">免責事項</a>
      <a href="about.html">運営者情報・お問い合わせ</a>
    </div>
    <div>&copy; 2026 CoreStation / Ricolo. All Rights Reserved.</div>
  </footer>

</body>
</html>"""

with open(os.path.join(BASE_DIR, "about.html"), "w", encoding="utf-8") as f:
    f.write(about_html)
print("[SSG] Created about.html")

# 7. Generate sitemap.xml
today = datetime.now().strftime("%Y-%m-%d")
sitemap_urls = [
    ("https://corestation.pages.dev/", "1.0", "daily"),
    ("https://corestation.pages.dev/privacy", "0.5", "monthly"),
    ("https://corestation.pages.dev/disclaimer", "0.5", "monthly"),
    ("https://corestation.pages.dev/about", "0.7", "monthly"),
]

for art in articles:
    art_id = art.get("id")
    date_val = art.get("date", today)
    sitemap_urls.append((f"https://corestation.pages.dev/articles/{art_id}", "0.8", "weekly"))

sitemap_xml = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
for u, priority, changefreq in sitemap_urls:
    sitemap_xml.append("  <url>")
    sitemap_xml.append(f"    <loc>{u}</loc>")
    sitemap_xml.append(f"    <lastmod>{today}</lastmod>")
    sitemap_xml.append(f"    <changefreq>{changefreq}</changefreq>")
    sitemap_xml.append(f"    <priority>{priority}</priority>")
    sitemap_xml.append("  </url>")
sitemap_xml.append("</urlset>")

with open(os.path.join(BASE_DIR, "sitemap.xml"), "w", encoding="utf-8") as f:
    f.write("\n".join(sitemap_xml))
print(f"[SSG] Created sitemap.xml with {len(sitemap_urls)} URLs")

# 8. Generate robots.txt
robots_txt = """User-agent: *
Allow: /

Sitemap: https://corestation.pages.dev/sitemap.xml
"""

with open(os.path.join(BASE_DIR, "robots.txt"), "w", encoding="utf-8") as f:
    f.write(robots_txt)
print("[SSG] Created robots.txt")

# 9. Update index.html for SEO & Crawlers
index_path = os.path.join(BASE_DIR, "index.html")
with open(index_path, "r", encoding="utf-8") as f:
    index_content = f.read()

# 9.1 Add SEO meta tags to head if not present
seo_head_tags = """  <meta name="description" content="CoreStationは、Core Blockchain (XCB) のノード稼働状況、ウォレット資産、確定申告台帳、およびRyzen/Xeonによる分散マイニング検証ガイドを提供する独立系ポータルサイトです。">
  <link rel="canonical" href="https://corestation.pages.dev/">
  <link rel="sitemap" type="application/xml" title="Sitemap" href="/sitemap.xml">
  <!-- OGP & Social Meta -->
  <meta property="og:type" content="website">
  <meta property="og:site_name" content="CoreStation">
  <meta property="og:title" content="CoreStation - Core Blockchain (XCB) ノード＆資産管理ステーション">
  <meta property="og:description" content="Core Blockchain (XCB) のノード稼働状況、ウォレット残高、確定申告台帳、実測検証記事を提供するオウンドメディア。">
  <meta property="og:url" content="https://corestation.pages.dev/">
  <meta property="og:image" content="https://corestation.pages.dev/assets/core-icon.svg">
  <meta name="twitter:card" content="summary">"""

if '<meta name="description"' not in index_content:
    index_content = index_content.replace(
        '<title>CoreStation - Core Blockchain (XCB) ノード＆資産管理ステーション</title>',
        '<title>CoreStation - Core Blockchain (XCB) ノード＆資産管理ステーション</title>\n' + seo_head_tags
    )

# 9.2 Update drawer-nav with legal links
legal_nav_links = """        <div class="nav-section-title">規約・運営情報</div>
        <a href="privacy.html" class="drawer-link">
          <span class="nav-icon">📜</span>
          <span>プライバシーポリシー</span>
        </a>
        <a href="disclaimer.html" class="drawer-link">
          <span class="nav-icon">⚠️</span>
          <span>免責事項・リスク開示</span>
        </a>
        <a href="about.html" class="drawer-link">
          <span class="nav-icon">🏢</span>
          <span>運営者情報・お問い合わせ</span>
        </a>"""

if '<span>プライバシーポリシー</span>' not in index_content:
    index_content = index_content.replace(
        '<div class="nav-section-title">外部リンク &amp; コミュニティ</div>',
        legal_nav_links + '\n\n        <div class="nav-section-title">外部リンク &amp; コミュニティ</div>'
    )

# 9.3 Update footer legal links with direct static URLs
old_footer = """      <div class="footer-legal-links">
        <button type="button" class="footer-legal-btn" onclick="openLegalModal('privacyPolicyModal')">📜 プライバシーポリシー</button>
        <span class="footer-legal-sep">•</span>
        <button type="button" class="footer-legal-btn" onclick="openLegalModal('disclaimerModal')">⚠️ 免責事項・リスク開示</button>
        <span class="footer-legal-sep">•</span>
        <button type="button" class="footer-legal-btn" onclick="openLegalModal('aboutContactModal')">🏢 運営者情報・お問い合わせ</button>
      </div>"""

new_footer = """      <div class="footer-legal-links">
        <a href="privacy.html" class="footer-legal-btn">📜 プライバシーポリシー</a>
        <span class="footer-legal-sep">•</span>
        <a href="disclaimer.html" class="footer-legal-btn">⚠️ 免責事項・リスク開示</a>
        <span class="footer-legal-sep">•</span>
        <a href="about.html" class="footer-legal-btn">🏢 運営者情報・お問い合わせ</a>
      </div>"""

if old_footer in index_content:
    index_content = index_content.replace(old_footer, new_footer)

# 9.4 Update archive title count dynamically
import re
index_content = re.sub(r'全\d+記事', f'全{len(articles)}記事', index_content)

# 9.5 Populate articlesArchiveContainer with static fallback links for crawlers
static_cards_html = []
for art in articles:
    art_id = art.get("id")
    art_title = html.escape(art.get("title", ""))
    art_summary = html.escape(art.get("summary", ""))
    art_cat = html.escape(art.get("categoryName", "ガイド"))
    art_date = html.escape(art.get("date", "2026-09-06"))
    static_cards_html.append(f'''              <a href="articles/{art_id}" class="article-card" style="text-decoration: none; color: inherit; display: flex; flex-direction: column; justify-content: space-between;" data-article-id="{art_id}">
                <div>
                  <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <span class="badge-online" style="font-size: 11px; padding: 2px 8px;">{art_cat}</span>
                    <span style="font-size: 11px; color: var(--text-light, #94a3b8);">🔒 独立静的ページ</span>
                  </div>
                  <h3 class="article-card-title">{art_title}</h3>
                  <p class="article-card-desc">{art_summary}</p>
                </div>
                <div class="article-card-meta">
                  <span>📅 {art_date}</span>
                  <span class="article-read-btn"><span>📖 記事を読む ↗</span></span>
                </div>
              </a>''')

static_articles_block = "\n".join(static_cards_html)

start_tag = '<div class="article-grid" id="articlesArchiveContainer">'
end_tag = '</div>\n          </div>\n        </section>'
start_idx = index_content.find(start_tag)
if start_idx != -1:
    end_idx = index_content.find(end_tag, start_idx)
    if end_idx != -1:
        index_content = index_content[:start_idx + len(start_tag)] + "\n" + static_articles_block + "\n            " + index_content[end_idx:]
        print(f"[SSG] Replaced articlesArchiveContainer with {len(articles)} fallback cards")
    else:
        print("[SSG] Warning: end_tag for articlesArchiveContainer not found")
else:
    print("[SSG] Warning: start_tag for articlesArchiveContainer not found")

with open(index_path, "w", encoding="utf-8") as f:
    f.write(index_content)
print("[SSG] Updated index.html successfully")

