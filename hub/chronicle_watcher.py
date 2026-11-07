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
import argparse

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

DRY_RUN = False  # --dry-run / --sample-file で True になる（すべての公開作用を止めるフラグ）

# ============================================================================
# 長文記事ゲート（純テキスト10,000字未満の記事は公開しない）共有ヘルパー
# chronicle_watcher.py / community_watcher.py 共通。
# 依存: os, sys, json, re, urllib.request, ssl, datetime, OUTPUT_DIR,
#        load_gemini_key(), get_ssl_context(), CONTINUATION_CHAPTERS,
#        CHAPTERS_PER_ROUND, build_continuation_prompt()
# ============================================================================

MIN_ARTICLE_CHARS = 10000          # この字数に満たない記事は一切公開しない
TARGET_ARTICLE_CHARS = 13000       # 生成目標
MIN_HEADINGS = 8                   # h2 見出しの本数下限（プロンプト側の義務）
MAX_OUTPUT_TOKENS = 16000          # Gemini 2.5 Flash は 65536 出力可能
GEMINI_TIMEOUT_SECONDS = 300       # 4000トークン時代は35s。16000トークンは長時間かかる
MAX_CONTINUATION_ROUNDS = 4        # 追記ラウンドの上限
MAX_LONGFORM_ATTEMPTS = 6          # 未達記事の自動再試行は最大6回（超えたら人手レビュー対象として打ち切り）
SHORTFALL_DIR = os.path.join(OUTPUT_DIR, "shortfall")
os.makedirs(SHORTFALL_DIR, exist_ok=True)

_SCRIPT_STYLE_RE = re.compile(r'<(?:script|style)\b[^>]*>.*?</(?:script|style)\s*>', re.IGNORECASE | re.DOTALL)
_HTML_COMMENT_RE = re.compile(r'<!--.*?-->', re.DOTALL)
_HTML_TAG_RE = re.compile(r'<[^>]*>')
_WHITESPACE_RE = re.compile(r'[\s\u3000\u00a0\ufeff]+')
_H2_RE = re.compile(r'<h2\b[^>]*>(.*?)</h2>', re.IGNORECASE | re.DOTALL)


def strip_article_markup(html_text):
    """script/style ブロック・HTMLコメント・タグ・空白(全角スペース含む)を除去した本文テキストを返す。"""
    if not html_text:
        return ""
    text = _SCRIPT_STYLE_RE.sub(' ', html_text)
    text = _HTML_COMMENT_RE.sub(' ', text)
    text = _HTML_TAG_RE.sub(' ', text)
    return _WHITESPACE_RE.sub('', text)


def plain_char_len(html_text):
    """記事本文の実質文字数（タグ・空白・全角スペースを除去した文字数）。"""
    return len(strip_article_markup(html_text))


def normalize_heading(text):
    """見出しの比較用正規化（タグ・空白・記号を落として小文字化）。"""
    t = _HTML_COMMENT_RE.sub(' ', text or '')
    t = _HTML_TAG_RE.sub('', t)
    t = _WHITESPACE_RE.sub('', t)
    t = re.sub(r'[^\w\u3000-\u30ff\u4e00-\u9fffア-ン・]', '', t, flags=re.UNICODE)
    return t.lower()


def extract_h2_headings(html_text):
    """本文から h2 見出しの文字列リストを取り出す。"""
    headings = []
    for raw in _H2_RE.findall(html_text or ''):
        txt = _HTML_COMMENT_RE.sub(' ', raw)
        txt = _HTML_TAG_RE.sub('', txt)
        txt = _WHITESPACE_RE.sub('', txt).strip()
        if txt:
            headings.append(txt)
    return headings


def clean_model_html(text):
    """コードフェンスや ---META---/---BODY--- の混入を除いて HTML 本文だけ返す。"""
    if not text:
        return ""
    t = text.strip()
    if '---BODY---' in t:
        t = t.split('---BODY---', 1)[1]
    if '---META---' in t:
        t = t.split('---META---', 1)[0]
    t = re.sub(r'^[ \t]*```(?:html|HTML)?[ \t]*\r?\n?', '', t, flags=re.MULTILINE)
    t = re.sub(r'\r?\n?[ \t]*```[ \t]*$', '', t, flags=re.MULTILINE)
    return t.strip()


def append_body_sections(body_html, extra_html):
    """追加章(<h2>〜)を本文の末尾、外側のラッパ div があればその内側に差し込む。"""
    extra = (extra_html or '').strip()
    if not extra:
        return body_html
    body = (body_html or '').strip()
    if not body:
        return extra
    if body.rstrip().endswith('</div>'):
        trimmed = body.rstrip()
        idx = trimmed.rfind('</div>')
        return trimmed[:idx].rstrip() + "\n" + extra + "\n" + trimmed[idx:]
    return body + "\n" + extra


def call_gemini_text(prompt, max_output_tokens=MAX_OUTPUT_TOKENS, timeout=GEMINI_TIMEOUT_SECONDS,
                     temperature=0.7, label=""):
    """gemini-2.5-flash を呼んで本文テキストを返す。失敗時 None（キーはログに出さない）。"""
    api_key = load_gemini_key()
    if not api_key:
        print("❌ GEMINI_API_KEY が見つかりません。", file=sys.stderr)
        return None

    endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_output_tokens
        }
    }
    req = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    ctx = get_ssl_context()
    started = datetime.now()
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"⚠️ Gemini API呼び出しエラー{label}: {e}", file=sys.stderr)
        return None

    candidates = data.get("candidates") or []
    if not candidates:
        block = (data.get("promptFeedback") or {}).get("blockReason", "n/a")
        print(f"⚠️ Gemini: 候補なし{label} (blockReason={block})", file=sys.stderr)
        return None

    parts = (candidates[0].get("content") or {}).get("parts") or []
    text = "".join(p.get("text", "") for p in parts).strip()
    usage = data.get("usageMetadata") or {}
    elapsed = (datetime.now() - started).total_seconds()
    print(f"🧠 Gemini応答{label}: 応答 {len(text)} 文字 / {elapsed:.1f}s "
          f"(finishReason={candidates[0].get('finishReason')}, "
          f"tokens={usage.get('candidatesTokenCount', '?')}/{usage.get('totalTokenCount', '?')})")
    if not text:
        return None
    return text


def pick_continuation_chapters(body_html, requested, round_no):
    """まだ書いていない章を CHAPTERS_PER_ROUND 本選ぶ（依頼済み・既存見出しと重複するものは除外）。"""
    existing = [normalize_heading(h) for h in extract_h2_headings(body_html)]
    todo = []
    for chapter in CONTINUATION_CHAPTERS:
        norm = normalize_heading(chapter)
        if not norm or norm in requested:
            continue
        if any(e and (norm in e or e in norm) for e in existing):
            continue
        todo.append(chapter)
        if len(todo) >= CHAPTERS_PER_ROUND:
            break
    if not todo:
        # プールを使い切ったら汎用の深掘り章で続行する（重複防止のため毎回新しい章名）
        todo = [f"追加検証パート{round_no}: 実測手順と失敗パターン、および未確認論点の整理"]
    return todo


def enforce_longform_gate(art, raw_text, source_url, source_name):
    """本文が MIN_ARTICLE_CHARS に達するまで追記ラウンドを繰り返し、公開可否を art に書き込む。"""
    if not art:
        return None
    body = art.get("body") or ""
    chars = plain_char_len(body)
    headings = extract_h2_headings(body)
    requested = []
    rounds = 0

    print(f"📏 初回生成の本文字数: {chars} 字 (h2 {len(headings)} 本) / 公開下限 {MIN_ARTICLE_CHARS} 字・目標 {TARGET_ARTICLE_CHARS} 字")

    while chars < MIN_ARTICLE_CHARS and rounds < MAX_CONTINUATION_ROUNDS:
        round_no = rounds + 1
        todo = pick_continuation_chapters(body, requested, round_no)
        requested.extend(normalize_heading(c) for c in todo)
        remaining = max(TARGET_ARTICLE_CHARS - chars, (MIN_ARTICLE_CHARS - chars) + 1500)
        prompt = build_continuation_prompt(source_name, source_url, raw_text, body, todo, remaining, round_no)
        print(f"✍️ 追記ラウンド{round_no}/{MAX_CONTINUATION_ROUNDS}: 不足 {MIN_ARTICLE_CHARS - chars} 字 → 追記ノルマ {remaining} 字 "
              f"(書く章: {' / '.join(todo)})")
        extra_raw = call_gemini_text(prompt, label=f" 追記ラウンド{round_no}")
        extra = clean_model_html(extra_raw)
        if not extra:
            print(f"⚠️ 追記ラウンド{round_no}: Gemini から本文を取得できず打ち切り", file=sys.stderr)
            break
        before = chars
        body = append_body_sections(body, extra)
        chars = plain_char_len(body)
        headings = extract_h2_headings(body)
        rounds = round_no
        print(f"📏 追記ラウンド{round_no} 完了: {before} 字 → {chars} 字 (h2 {len(headings)} 本)")

    art["body"] = body
    art["chars"] = chars
    art["longform_rounds"] = rounds + 1
    art["heading_count"] = len(headings)
    art["publish_ok"] = chars >= MIN_ARTICLE_CHARS

    if art["publish_ok"]:
        print(f"✅ 長文ゲート通過: 本文 {chars} 字 / h2 {len(headings)} 本 / Gemini 呼出し {rounds + 1} 回"
              + ("（目標字数には未達だが下限はクリア）" if chars < TARGET_ARTICLE_CHARS else ""))
        if len(headings) < MIN_HEADINGS:
            print(f"⚠️ h2 見出しが {len(headings)} 本しかありません（義務 {MIN_HEADINGS} 本未満）。"
                  f"文字数ゲートは通過しているため公開されますが、構成の構造確認を推奨します。", file=sys.stderr)
    else:
        print(f"🚫 長文ゲート未達: 本文 {chars} 字 < 下限 {MIN_ARTICLE_CHARS} 字 "
              f"(Gemini 呼出し {rounds + 1} 回, h2 {len(headings)} 本) → 公開しない", file=sys.stderr)
    return art


def save_shortfall_draft(art, post_id="", reason=""):
    """未達ドラフトを hub/output/shortfall/<slug>.html に保存し、パスを返す（公開はしない）。"""
    slug = re.sub(r'[^A-Za-z0-9_.-]+', '_', str(art.get("slug") or "untitled")).strip('_.-') or "untitled"
    path = os.path.join(SHORTFALL_DIR, f"{slug}.html")
    header = (
        "<!-- SHORTFALL DRAFT / 非公開（10,000字ゲート未達）\n"
        f"     generated: {datetime.now().isoformat()}\n"
        f"     slug: {art.get('slug')}\n"
        f"     title: {art.get('title')}\n"
        f"     plain_char_len: {art.get('chars')} (MIN_ARTICLE_CHARS={MIN_ARTICLE_CHARS}, TARGET={TARGET_ARTICLE_CHARS})\n"
        f"     h2_headings: {art.get('heading_count')} (MIN_HEADINGS={MIN_HEADINGS})\n"
        f"     gemini_calls: {art.get('longform_rounds')}\n"
        f"     source_post_id: {post_id}\n"
        f"     reason: {reason}\n"
        "-->\n"
    )
    meta = (f"---META---\nTITLE: {art.get('title')}\nSLUG: {art.get('slug')}\n"
            f"SUMMARY: {art.get('summary')}\n---BODY---\n")
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(header + meta + (art.get("body") or ""))
    except Exception as e:
        print(f"⚠️ ドラフト保存失敗 ({path}): {e}", file=sys.stderr)
        return None
    return path


# ============================================================================
# 長文義務（chronicle 用）: プロンプトに載せる規則・追記章・追記プロンプト生成
# ============================================================================

CHAPTERS_PER_ROUND = 3

LONGFORM_RULES_TEXT = """2. 記事量と構成の義務（最優先・必須）:
   - 本文は純テキスト（HTMLタグ・空白・全角スペースを除いた文字数）で10,000字以上。目標13,000字。10,000字に満たない記事は公開しません。
   - h2見出しを最低8本立てる。各見出しの下には900〜1,500字のかたまりのある解説を書く。
   - 本文は必ずHTMLで構造化する: 章のタイトルは <h2>、細分区切りは <h3>、段落は <p>、引用は <blockquote>、比較は <table>。タグを使わないプレーンテキストの塊としての出力は禁止。
   - 箇条書きの羅列で終わらせず、「なぜそうなるのか」「マイナー／ホルダーに何が起きるのか」「具体的にどう動くべきか」という因果関係を説明する段落を中心に構成する。
   - 原文や公式一次情報で確認できていない数値・固有名詞・日付は、必ず『（要確認）』と明記して推定であることを読者に伝える。
   - 途中で切り上げず、指定字数に達するまで同じテーマを別の角度（仕組み・実務・検証・リスク・比較）から深掘りして書き切る。"""

CONTINUATION_CHAPTERS = [
    "公式アナウンスの技術内容をゼロから噛み砕く（用語・仕組み・なぜ必要とされたのか）",
    "コンセンサス（PoDE）とネットワーク安全性に与える影響",
    "自作PCハードウェア目線の掘り下げ（CPU選定・電力・発熱と冷却）",
    "マイニング設定の実務チェックリストと変更手順",
    "実測データ（ハッシュレート・Difficulty・日産XCB）との照合手順と検証計画",
    "マイナー／ホルダーが今取るべきアクションと判断の分岐",
    "想定されるリスク・落とし穴とよくある失敗パターン",
    "一次情報で確認できない論点の『要確認』一覧と公式での確認方法",
    "過去のアップデートや他チェーンとの比較から見る今回の変更の重要性",
    "初心者向けQ&A（よくある質問とリコロの回答）",
    "CoreStationのダッシュボードでできる検証とデータの見方",
    "今後の監視計画（どの公式情報をいつ・どう確認するか）",
]


def build_continuation_prompt(source_name, source_url, raw_text, existing_body, todo_chapters,
                              remaining_chars, round_no):
    """既存本文へ <h2> 章を追記させるための継続プロンプト。"""
    existing = extract_h2_headings(existing_body)
    if existing:
        existing_txt = "\n".join(f"   - {h}" for h in existing)
    else:
        existing_txt = "   - （まだ h2 見出しがありません）"
    todo_txt = "\n".join(f"{i + 1}. {c}" for i, c in enumerate(todo_chapters))

    return f"""あなたは自作PCとゲームが大好きな女性技術アナリスト兼ライター「リコロ（Ricolo）」です！
すでに執筆済みの Core Blockchain 解説記事に、<h2> 見出しの新しい章を追記してください（追記ラウンド {round_no}）。

【情報ソース】
{source_name} ({source_url})

【公式アナウンス原文】
{raw_text}

【すでに書き終わっている見出し（この内容は書かない。同じ書き出し・同じ自作PC比喩・同じ数値の再利用も禁止）】
{existing_txt}

【今回あなたが書く章（この順で、すべて <h2> 見出しを立てる）】
{todo_txt}

【執筆ルール（必須）】
- 今回のラウンドだけで純テキスト（HTMLタグ・空白・全角スペースを除いた文字数）{remaining_chars}字以上を書く。1章あたり900〜1,500字を目安にする。
- 記事全体の h2 見出しは合計 {MIN_HEADINGS} 本以上必要。今回はそのうち上記の章を担当する。
- キャラクターはリコロ（自作PC大好きゲーム女子）のまま。元気で親しみやすいが、技術説明はプロレベルにロジカルに。
- 段落中心。仕組み→原因→マイナーへの影響→取るべき行動、の順に因果を説明する。見出しごとに150〜350字の段落を3〜5個目安。
- 原文や公式一次情報で確認できていない数値・固有名詞は必ず『（要確認）』と明記する。
- 箇条書きを使う場合でも、必ずその前後に説明段落を添える。
- 既存本文の要約・言い直しは書かない。新しい切り口と新しい情報だけを書く。
- 冒頭の挨拶（「どうも！自作PC大好きゲーム女子、リコロです！」）と締めくくりの挨拶は記事に既に存在するため書かない。
- 出力は追記するHTML本文だけ。<h2> 見出し <p> 段落 <blockquote> 引用 <table> などHTMLのみ。コードフェンス（```）、---META---、---BODY---、前置き、説明文、見出しリストの復唱は一切出力しない。"""


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

def _generate_article_first_pass(raw_text, source_url, source_name):
    """初回パス（Gemini 1呼出し）で骨子を生成する。10,000字ゲートは generate_article_with_gemini が担当。"""
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
{LONGFORM_RULES_TEXT}
3. 構成:
   - つかみ・導入（「公式から激アツなアップデートが届きました〜！」）
   - 原文引用（<blockquote style="margin: 10px 0; padding: 10px; background: #fff; border-left: 3px solid #ffa726; font-size: 14px; color: #555; white-space: pre-wrap;"> で囲み、引用元リンク: {source_url} を明記）
   - 3行でわかる！今回の神アプデ要点まとめ（箇条書き）
   - 自作PC＆ゲーム目線での深掘り解説（h2やh3タグを使用）
   - マイナー・ホルダーはどう動くべきか？（実践アドバイス）
   - CoreStation（https://corestation.pages.dev/）への誘導
   - 締めくくり
4. 出力フォーマット（厳密に以下の書式を守ってください）:
---META---
TITLE: 【速報・解説】絵文字付きの魅力的なタイトル
SLUG: 半角英小文字とハイフンのみの簡潔な識別子（例: core-update-20261018）
SUMMARY: 100〜150文字程度の客観的かつ魅力的な記事要約
---BODY---
<div style="line-height: 1.8; font-size: 16px; color: #333;">
記事のHTML本文（<h2> 見出し・<h3> 小見出し・<p> 段落・<blockquote> 引用で構造化すること。```htmlなどのコードフェンスは含めないでください）
</div>
"""

    endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": MAX_OUTPUT_TOKENS
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
        with urllib.request.urlopen(req, context=ctx, timeout=GEMINI_TIMEOUT_SECONDS) as resp:
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
                
                print(f"✨ Gemini による初稿が完成しました: {title}")
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

def generate_article_with_gemini(raw_text, source_url, source_name):
    """初回執筆 + 長文ゲート（純テキスト10,000字に達するまで追記ラウンドを繰り返す）。

    戻り値は既存互換の dict(title/slug/summary/body) に以下を加えたもの:
      chars(=plain_char_len), longform_rounds(Gemini呼出し回数), heading_count, publish_ok
    公開してよいのは publish_ok が True のときだけ。生成失敗時は None（既存と互換）。
    """
    art = _generate_article_first_pass(raw_text, source_url, source_name)
    if not art:
        return None
    return enforce_longform_gate(art, raw_text=raw_text, source_url=source_url, source_name=source_name)

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
    if DRY_RUN:
        print("🧪 [dry-run] サイト統合をスキップ: articles/<slug>.html / initial_data.js / local_articles.js / index.html / sitemap.xml")
        return
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
    if DRY_RUN:
        print("🧪 [dry-run] git add/commit/push をスキップ")
        return
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
    if DRY_RUN:
        print("🧪 [dry-run] sync.py によるオンチェーン同期をスキップ")
        return True
    print("⛓️ オンチェーン採掘データ＆ワーカー最新状態の定期同期を実行中...")
    try:
        sync_script = os.path.join(ROOT_DIR, "sync.py")
        subprocess.run([sys.executable, sync_script], cwd=ROOT_DIR, check=True)
        print("✅ オンチェーン採掘データ同期が正常に完了しました。")
        return True
    except Exception as e:
        print(f"⚠️ オンチェーン採掘データ同期中にエラー: {e}", file=sys.stderr)
        return False

def check_and_publish(sample_file=None):
    """Main execution loop for checking updates and publishing across all platforms.

    純テキスト10,000字未満の記事は公開しない（はてな投稿 / articles・data・index・sitemap更新 /
    git push / SNS配信をすべてスキップし、hub/output/shortfall/ にドラフトを保存して再試行に回す）。
    sample_file を渡すと固定のサンプル raw_text で生成検証する（公開作用は自動スキップ）。
    """
    if DRY_RUN:
        print("🧪 [dry-run] 公開作用（はてな投稿 / sites統合 / git push / SNS / 状態更新 / sync.py）はすべてスキップします。")
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 🔍 コアクロニクル・公式アップデートの巡回監視＆最新データ同期を開始...")

    # 1. 常にオンチェーン採掘実績＆ワーカー状態を最新化（dry-run ではスキップ）
    sync_onchain_mining_data()

    # 2. 公式アナウンス・SNSの巡回チェック
    last_seen = load_last_seen()
    seen_ids = set(last_seen.get("seen_posts", []))
    attempts = dict(last_seen.get("longform_attempts") or {})  # 長文ゲート未達の試行回数

    all_updates = []
    if sample_file:
        with open(sample_file, "r", encoding="utf-8") as f:
            sample_raw = f.read().strip()
        if not sample_raw:
            print(f"❌ サンプル raw_text が空です: {sample_file}", file=sys.stderr)
            return False
        all_updates = [{
            "id": f"sample/{os.path.basename(sample_file)}",
            "source": "検証用サンプル raw_text (chronicle_watcher --sample-file)",
            "text": sample_raw,
            "url": "https://corestation.pages.dev/ (検証用サンプルソース)"
        }]
        print(f"🧪 サンプル raw_text ({len(sample_raw)} 字) で生成検証します: {sample_file}")
    else:
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
        last_seen["longform_attempts"] = {k: v for k, v in attempts.items() if k not in seen_ids}
        if DRY_RUN:
            print(f"🧪 [dry-run] 状態ファイルは書き換えません: {LAST_SEEN_FILE}")
        else:
            save_last_seen(last_seen)

        # 新着記事がなくても、オンチェーン採掘データ等の差分があれば即時コミット＆デプロイ
        deploy_to_cloudflare(f"feat(mining): auto-sync on-chain rewards and worker status [{datetime.now().strftime('%Y-%m-%d %H:%M')}]")
        return False

    print(f"🎉 {len(new_posts)} 件の新着アップデートを検知しました！")
    today_str = datetime.now().strftime("%Y-%m-%d")
    any_published = False

    for post in new_posts:
        post_key = post["id"]
        prev_attempts = attempts.get(post_key, 0)
        if MAX_LONGFORM_ATTEMPTS and prev_attempts >= MAX_LONGFORM_ATTEMPTS:
            print(f"🚫 長文ゲート再試行上限({MAX_LONGFORM_ATTEMPTS}回)到達のため打ち切り: {post_key} "
                  f"(試行 {prev_attempts} 回) → 既読扱いでスキップ", file=sys.stderr)
            seen_ids.add(post_key)
            attempts.pop(post_key, None)
            continue

        print(f"🔎 新着処理開始: {post_key} (過去の試行 {prev_attempts} 回)")
        art = generate_article_with_gemini(post["text"], post.get("url", ""), post.get("source", ""))
        if not art:
            attempts[post_key] = prev_attempts + 1
            print(f"🚫 公開スキップ(生成失敗): post_id={post_key} Gemini応答なし "
                  f"試行={attempts[post_key]} seen未更新(次回再試行)", file=sys.stderr)
            continue

        title = art["title"]
        slug = art["slug"]
        summary = art["summary"]
        body_html = art["body"]
        chars = art.get("chars", plain_char_len(body_html))
        rounds = art.get("longform_rounds", 1)
        heading_count = art.get("heading_count", len(extract_h2_headings(body_html)))
        full_blog_html = BANNER_HEADER_HTML + "\n" + body_html + "\n" + RICOLO_AUTHOR_BOX_HTML

        # 0. 【長文ゲート】10,000字に満たない記事は公開作用をすべてスキップしドラフトだけ保存
        if not art.get("publish_ok", False):
            draft_path = save_shortfall_draft(
                art, post_id=post_key,
                reason=f"plain_char_len={chars} < MIN_ARTICLE_CHARS={MIN_ARTICLE_CHARS} "
                       f"(追記 {MAX_CONTINUATION_ROUNDS} ラウンド実施後も未達)")
            attempts[post_key] = prev_attempts + 1
            print(f"🚫 公開スキップ(長文ゲート未達): slug={slug} plain_char_len={chars} "
                  f"< MIN_ARTICLE_CHARS={MIN_ARTICLE_CHARS} h2={heading_count}本 "
                  f"Gemini呼出し={rounds}回 試行回数={attempts[post_key]} "
                  f"ドラフト={draft_path} seen未更新=次回再試行 title={title}", file=sys.stderr)
            continue

        # 1. Save temp output（ドラフト保存。外部公開ではない）
        temp_file = os.path.join(OUTPUT_DIR, f"chronicle_update_{post['id'].replace('/', '_')}.html")
        with open(temp_file, "w", encoding="utf-8") as f:
            f.write(full_blog_html)
        print(f"📝 ドラフト保存: {temp_file} (本文 {chars} 字 / h2 {heading_count} 本 / Gemini {rounds} 呼)")

        if DRY_RUN:
            print(f"🧪 [dry-run] 公開作用をスキップ: はてなブログ投稿 / サイト統合 / git push / SNS配信。"
                  f" 生成字数={chars} 保存先={temp_file}")
            any_published = True
            continue

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
        attempts.pop(post_key, None)
        any_published = True

    if any_published and not DRY_RUN:
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
    attempts = {k: v for k, v in attempts.items() if k not in seen_ids}
    last_seen["longform_attempts"] = attempts
    if DRY_RUN:
        print(f"🧪 [dry-run] 状態ファイルは書き換えません（未達の記事は次回実行でも再試行されます）: {LAST_SEEN_FILE}")
    else:
        save_last_seen(last_seen)
    return any_published

def parse_cli_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Core Chronicle Watcher（純テキスト10,000字以上の記事だけを公開）")
    parser.add_argument("--dry-run", action="store_true",
                        help="公開作用（はてなブログ投稿 / articles/HTML / local_articles.js / index.html / "
                             "sitemap / git push / SNS / 状態ファイル更新 / sync.py）をすべてスキップし、"
                             "生成字数と保存先だけを出力します")
    parser.add_argument("--sample-file", dest="sample_file", default=None,
                        help="固定のサンプル raw_text ファイルで生成検証する（公開作用は自動でスキップ）")
    return parser.parse_args(argv)


if __name__ == "__main__":
    cli = parse_cli_args()
    if cli.dry_run or cli.sample_file:
        DRY_RUN = True
    check_and_publish(sample_file=cli.sample_file)
