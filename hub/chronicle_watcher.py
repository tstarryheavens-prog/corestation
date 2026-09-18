#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Core Chronicle Watcher & Auto-Article Generator
==============================================
Core Blockchain（コアクロニクル、公式Telegram、GitHubリリース等）の
最新情報更新を定期監視し、新着情報を引用・客観的かつ分かりやすく噛み砕いて
Gemini 2.5 Flashで自動解説記事（HTML形式）を生成し、はてなブログおよびローカルデータへ自動公開・更新する。
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
CONFIG_DIR = os.path.join(BASE_DIR, "config")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
LAST_SEEN_FILE = os.path.join(CONFIG_DIR, "last_seen_chronicle.json")
PUBLISHER_SCRIPT = os.path.join(BASE_DIR, "hatena_publisher.py")

# Core Blockchain 情報ソース
SOURCES = [
    {
        "name": "Core Blockchain Japan (公式Telegram)",
        "url": "https://t.me/s/Core_Blockchain_Japan",
        "type": "telegram"
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

def fetch_telegram_updates(url):
    """Fetch public Telegram channel messages without API token."""
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
    )
    ctx = get_ssl_context()
    updates = []
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
            html = resp.read().decode("utf-8")
            
            # Extract telegram post bubbles
            posts = re.findall(
                r'data-post="([^"]+)".*?<div class="tgme_widget_message_text[^>]*>(.*?)</div>',
                html,
                re.DOTALL
            )
            for post_id, raw_text in posts[-5:]:  # Check last 5 messages
                clean_text = re.sub(r'<br\s*/?>', '\n', raw_text)
                clean_text = re.sub(r'<[^>]+>', '', clean_text).strip()
                if clean_text:
                    updates.append({
                        "id": post_id,
                        "source": "Core Blockchain 公式アナウンス",
                        "text": clean_text,
                        "url": f"https://t.me/{post_id}"
                    })
    except Exception as e:
        print(f"⚠️ Telegram fetch error: {e}", file=sys.stderr)
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

def generate_article_with_gemini(raw_text, source_url, source_name):
    """Generate professional and accessible blog HTML using Google Gemini API."""
    api_key = load_gemini_key()
    if not api_key:
        return None, None

    prompt = f"""あなたは自作PCとゲームが大好きな女性技術ライター「リコロ（Ricolo）」です！
Core Blockchain (XCB) の公式速報・最新アナウンスを深く読み解き、初心者やマイナー向けに要点を整理し、自作PCやゲームの比喩を交えながら明るく親しみやすい女子目線で解説ブログ記事（HTML形式）を執筆してください。

【公式アナウンス原文】
{raw_text}

【記事の執筆ルール】
1. キャラクター＆トーン:
   - 名前: リコロ（自作PC大好きゲーム女子）
   - 冒頭の挨拶: 「どうも！自作PC大好きゲーム女子、リコロです！✍🏻🎮💻✨」
   - トーン: 元気で明るく親しみやすい語り口。自作PC（Ryzen・グラボ・冷却等）やゲーム（放置ゲー・RPG・クラフト等）の例え話を適度に織り交ぜる。
   - 締めくくり: 「それでは、また次回の解説記事でお会いしましょう！リコロでした〜！ばいば〜い！🎮👾✨」など末尾の表現も自由に生き生きとキャラクターを維持する。
2. 構成:
   - つかみ・導入（「公式から激アツなアップデートが届きました〜！」）
   - 原文引用（<blockquote style="margin: 10px 0; padding: 10px; background: #fff; border-left: 3px solid #ffa726; font-size: 14px; color: #555; white-space: pre-wrap;"> で囲み、引用元リンク: {source_url} を明記）
   - 3行でわかる！今回の神アプデ要点まとめ
   - マイナー・ホルダーはどう動くべきか？（実践アドバイス）
   - 自サイト CoreStation（https://corestation.pages.dev/）への誘導ボタン
   - 締めくくり
3. 出力フォーマット:
   - 1行目にタイトルを 【速報・解説】〜 形式で出力（絵文字付き 🎮⚡️ など）
   - 2行目以降に <div style="line-height: 1.8; font-size: 16px; color: #333;"> で始まるHTMLタグのみを出力（Markdownの ```html や ``` バッククォート囲みは一切出力しないでください）。
"""

    endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ],
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
        with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            candidate = data["candidates"][0]["content"]["parts"][0]["text"]
            
            # Clean up response
            lines = candidate.strip().splitlines()
            title = lines[0].replace("#", "").strip()
            body = "\n".join(lines[1:]).strip()
            # Remove any stray ```html or ```
            body = re.sub(r'^```(?:html)?\s*', '', body, flags=re.MULTILINE)
            body = re.sub(r'\s*```$', '', body, flags=re.MULTILINE).strip()
            
            print("✨ Geminiによる記事執筆が完了しました！")
            return title, body
    except Exception as e:
        print(f"⚠️ Gemini API呼び出しエラー: {e}。テンプレートフォールバックを使用します。", file=sys.stderr)
        return None, None

BANNER_HEADER_HTML = """
<!-- CoreStation Official Brand Header Banner -->
<div style="text-align: center; margin-bottom: 25px;">
  <a href="https://corestation.pages.dev/" target="_blank" rel="noopener noreferrer" style="text-decoration: none; display: inline-block;">
    <img src="https://corestation.pages.dev/assets/horizontal_banner_logo.jpg" alt="CoreStation - Core Blockchain Mining & Node Hub" style="width: 100%; max-width: 820px; height: auto; border-radius: 12px; box-shadow: 0 8px 24px rgba(0, 0, 0, 0.35); display: block; margin: 0 auto;">
  </a>
</div>
"""

def generate_rico_article(update_item):
    """Generate friendly Rico-style blog HTML from raw update."""
    raw_text = update_item["text"]
    
    # Try Gemini first
    ai_title, ai_body = generate_article_with_gemini(raw_text, update_item.get("url", ""), update_item.get("source", ""))
    if ai_title and ai_body:
        full_html = BANNER_HEADER_HTML + "\n" + ai_body
        return ai_title, full_html

    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    summary_title = lines[0][:40] if lines else "最新アップデート情報"

    today = datetime.now().strftime("%Y年%m月%d日")
    
    html = f"""<div style="line-height: 1.8; font-size: 16px; color: #333;">

{BANNER_HEADER_HTML}

  <p style="font-size: 18px; font-weight: bold; color: #0284c7;">
    どうも！自作PC大好きゲーム女子、リコロです！✍🏻🎮💻✨
  </p>

  <p>
    Core Blockchain（XCB）に関する<strong>最新の公式アップデート・アナウンス</strong>が発表されました。
  </p>

  <p>
    「公式の英語発表や技術用語が難しくて分かりにくい」という方のために、<strong>要点をわかりやすく整理して解説</strong>していきます！
  </p>

  <div style="background-color: #f0f9ff; border-left: 5px solid #0284c7; padding: 15px; margin: 20px 0; border-radius: 4px;">
    <strong style="color: #0369a1; font-size: 17px;">📢 公式発表の原文引用（Core Chronicle / Telegram速報）</strong>
    <blockquote style="margin: 10px 0 0 0; padding: 10px; background: #fff; border-left: 3px solid #0ea5e9; font-size: 14px; color: #555; white-space: pre-wrap;">
{raw_text}
    </blockquote>
    <p style="margin: 8px 0 0 0; font-size: 12px; color: #888;">
      引用元: <a href="{update_item['url']}" target="_blank" rel="noopener noreferrer">{update_item['source']}</a> ({today}確認)
    </p>
  </div>

  <hr style="border: none; border-top: 2px dashed #ddd; margin: 30px 0;">

  <h2 style="border-left: 6px solid #0284c7; padding-left: 12px; margin: 30px 0 15px; color: #212121; font-size: 22px;">
    1. 今回の重要ポイントまとめ💡
  </h2>

  <div style="background: #e8f5e9; border: 1px solid #81c784; padding: 15px; border-radius: 8px; margin: 15px 0;">
    <strong>🎯 重要ポイント要約：</strong>
    <ul style="margin-bottom: 0; padding-left: 20px;">
      <li>公式コミュニティにて新しい進捗・アナウンスが正式発表されました。</li>
      <li>ネットワークの健全性や開発エコシステムの拡大が順調に進展しています。</li>
      <li>マイナーやホルダーにとって今後の価値向上に繋がる重要なお知らせです。</li>
    </ul>
  </div>

  <hr style="border: none; border-top: 2px dashed #ddd; margin: 30px 0;">

    </p>
    <p style="text-align: center; margin: 15px 0;">
      <a href="https://corestation.pages.dev/" target="_blank" rel="noopener noreferrer" style="background-color: #1976d2; color: white; padding: 12px 24px; font-weight: bold; text-decoration: none; border-radius: 30px; display: inline-block; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
        👉 CoreStation 公式ステーションを開く（完全無料）
      </a>
    </p>
    <p style="margin-bottom: 0;">
      確定申告データの出力や最新のオンチェーン状況も一括チェックできます！
    </p>
  </div>

  <hr style="border: none; border-top: 2px dashed #ddd; margin: 30px 0;">

  <h2 style="border-left: 6px solid #ff9800; padding-left: 12px; margin: 30px 0 15px; color: #212121; font-size: 22px;">
    まとめ！✨
  </h2>

  <p>
    日々進化し続けるCore Blockchain、これからも目が離せませんね！<br>
    最新の動きがあったら、どこよりも分かりやすくお届けしていきます！
  </p>

  <p style="font-size: 17px; font-weight: bold; color: #e65100; margin-top: 30px;">
    速報が役に立った方は、ぜひ読者登録やスター（⭐️）、SNSシェアをよろしくお願いします！🥰✍🏻
  </p>

  <p>
    それでは、また次回の更新でお会いしましょう！リコロでした〜！ばいば〜い！🎮👾✨
  </p>

</div>"""
    
    title = f"【速報・解説】Core Blockchain最新アップデート！公式アナウンスの重要ポイントをリコロが超解説🎮⚡️"
    return title, html

def check_and_publish():
    """Check sources, detect new updates, and auto-publish to Hatena Blog."""
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 🔍 コアクロニクル・公式アップデートの巡回を開始...")
    last_seen = load_last_seen()
    seen_ids = set(last_seen.get("seen_posts", []))

    all_updates = []
    for src in SOURCES:
        if src["type"] == "telegram":
            items = fetch_telegram_updates(src["url"])
            all_updates.extend(items)

    new_posts = [u for u in all_updates if u["id"] not in seen_ids]

    if not new_posts:
        print("✅ 新着の更新はありませんでした。次回巡回まで待機します。")
        last_seen["last_checked"] = datetime.now().isoformat()
        save_last_seen(last_seen)
        return False

    print(f"🎉 {len(new_posts)} 件の新着アップデートを検知しました！")
    for post in new_posts:
        title, html_content = generate_rico_article(post)
        
        # Save temp file
        temp_file = os.path.join(OUTPUT_DIR, f"chronicle_update_{post['id'].replace('/', '_')}.html")
        with open(temp_file, "w", encoding="utf-8") as f:
            f.write(html_content)

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
            if res.returncode == 0:
                seen_ids.add(post["id"])
        except Exception as e:
            print(f"❌ 投稿エラー: {e}", file=sys.stderr)

    last_seen["seen_posts"] = list(seen_ids)[-100:]  # Keep last 100 IDs
    last_seen["last_checked"] = datetime.now().isoformat()
    save_last_seen(last_seen)
    return True

if __name__ == "__main__":
    check_and_publish()
