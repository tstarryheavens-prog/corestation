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
import argparse

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


COMMUNITY_NOTES_TEXT = """1. **CorePass KYB（企業認証）とPing Exchangeビジネス取引への反応**:
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
"""

# ============================================================================
# 長文義務（community 用）: プロンプトに載せる規則・追記章・追記プロンプト生成
# ============================================================================

CHAPTERS_PER_ROUND = 3

LONGFORM_RULES_TEXT = """2. 記事量と構成の義務（最優先・必須）:
   - 本文は純テキスト（HTMLタグ・空白・全角スペースを除いた文字数）で10,000字以上。目標13,000字。10,000字に満たない記事は公開しません。
   - h2見出しを最低8本立てる。各見出しの下には900〜1,500字のかたまりのある解説を書く。
   - 本文は必ずHTMLで構造化する: 章のタイトルは <h2>、細分区切りは <h3>、段落は <p>、口コミ引用は <blockquote>、比較は <table>。タグを使わないプレーンテキストの塊としての出力は禁止。
   - 口コミの引用列で終わらせず、「なぜその声が出ているのか」「マイナーの収支や運用に何が起きるのか」「読者はどう動くべきか」を説明する段落を中心に構成する。
   - 一次情報で確認できていない数値（難易度・日産XCB・電力・着金額など）は、必ず『（要確認）』と明記してコミュニティ目線の情報であることを伝える。
   - 途中で切り上げず、指定字数に達するまで同じ話題を別の角度（仕組み・実務・検証・リスク・比較）から深掘りして書き切る。"""

CONTINUATION_CHAPTERS = [
    "CorePass KYB と Ping Exchange 取引がマイナー・ホルダーに与える実務インパクト",
    "CPUマイナーのハッシュレート実測談義（Ryzen・EPYC設定とワットパフォーマンス）",
    "WSL2 / Ubuntu で CoreMiner を安定運用する手順とトラブルシューティング",
    "Catch That Rabbit プールの分割着金と収支シミュレーションの読み方",
    "Difficulty 上昇トレンドとネットワークハッシュレートから読む今週の環境",
    "「パブリックステルス」開発思想への本音とフェアローンチの評価",
    "取引所流動性・価格発見への期待ともどかしさ",
    "初心者の参加とコミュニティサポート体制のリアル",
    "ハードウェア相場（CPU・GPU・中古市場）が採掘採算に与える影響",
    "コミュニティで頻出する誤解と、リコロによる正しい理解の整理",
    "リコロの次の検証計画（次にどんなデータをどのように採るか）",
    "今週マイナー仲間がやるべきチェックリストと判断基準",
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

    return f"""あなたは自作PCと暗号資産が大好きな女性技術ライター兼アナリスト「リコロ（Ricolo）」です！
すでに執筆済みの【コミュニティ定点観測】特集記事に、<h2> 見出しの新しい章を追記してください（追記ラウンド {round_no}）。

【情報ソース】
{source_name} ({source_url})

【記事の土台となっているコミュニティの生の声・議論メモ】
{raw_text}

【すでに書き終わっている見出し（この内容は書かない。同じ書き出し・同じ口コミ引用の再利用も禁止）】
{existing_txt}

【今回あなたが書く章（この順で、すべて <h2> 見出しを立てる）】
{todo_txt}

【執筆ルール（必須）】
- 今回のラウンドだけで純テキスト（HTMLタグ・空白・全角スペースを除いた文字数）{remaining_chars}字以上を書く。1章あたり900〜1,500字を目安にする。
- 記事全体の h2 見出しは合計 {MIN_HEADINGS} 本以上必要。今回はそのうち上記の章を担当する。
- キャラクターはリコロ（自作PC大好きゲーム女子）のまま。口コミは「💬 マイナーAさんの声」のように引用ボックスで示す。
- 段落中心。声→その背景（仕組みや数字）→収支や運用への影響→取るべき行動、の順に因果を説明する。見出しごとに150〜350字の段落を3〜5個目安。
- 一次情報で確認できない数値（Difficulty・日産XCB・消費電力・着金額など）は必ず『（要確認）』と明記する。
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

def _generate_community_digest_first_pass(vol_num):
    """Generate the first-pass community digest (title, slug, summary, body) using Gemini API."""
    api_key = load_gemini_key()
    if not api_key:
        print("❌ GEMINI_API_KEY が見つかりません。", file=sys.stderr)
        return None

    today_str = datetime.now().strftime("%Y年%m月%d日")

    prompt = f"""あなたは自作PCと暗号資産が大好きな女性技術ライター兼アナリスト「リコロ（Ricolo）」です！
Core Blockchain (XCB) の公式Discord、Telegramコミュニティチャット（@corecoincc, @Core_Blockchain_Japan）、X（旧Twitter: #XCB #CoreBlockchain #PoDE）、Reddit（r/gpumining, r/CryptoCurrency）、Catch That Rabbitプール等の最新の「コミュニティの生の声・リアルな反応・議論・口コミ」を多角的にまとめ、【リコロのコミュニティ定点観測 Vol.{vol_num}】として充実した特集記事を執筆してください。

【取り上げるべき最近の主なコミュニティの議論・生の声】
{COMMUNITY_NOTES_TEXT}
【記事の執筆ルール】
1. キャラクター＆トーン:
   - 名前: リコロ（Ricolo）
   - 冒頭の挨拶: 「どうも！自作PC大好きゲーム女子、リコロです！✍🏻🎮💻✨」
   - トーン: 元気で親しみやすく、かつハードウェアやブロックチェーンの仕組みについてはプロレベルにロジカルで分かりやすい。
   - 口コミ・引用は「💬 マイナーAさんの声」「💬 ホルダーBさんの声」のように見やすくボックス化や引用タグでデザインする。
   - 締めくくり: 「それでは、また次回のコミュニティ定点観測でお会いしましょう！リコロでした〜！ばいば〜い！🎮👾✨」
{LONGFORM_RULES_TEXT}
3. 構成:
   - つかみ・導入（「今回は公式発表だけでなく、世界中のマイナーやホルダー仲間がSNSやチャットで何を話しているのか、生の声を集めてみました！」）
   - 目次または要点ハイライト（今週のコミュニティ3大トピック）
   - トピック1: CorePass KYB＆Ping Exchangeビジネス取引に対するコミュニティの期待と議論
   - トピック2: 【マイナー座談会】Ryzen設定・ハッシュレート効率・プール分割着金のリアル
   - トピック3: 「パブリックステルス」への本音：VCなしフェアローンチの強みと今後の課題
   - リコロの考察＆まとめ（客観的な分析とマイナー仲間へのメッセージ）
   - CoreStation（https://corestation.pages.dev/）への誘導
   - 締めくくり
4. 出力フォーマット（厳密に以下の書式を守ってください）:
---META---
TITLE: 【リコロのコミュニティ定点観測 Vol.{vol_num}】マイナー＆ホルダーの生の声まとめ！CorePass KYBの反響・Ryzen採掘効率の議論・リアルな本音を徹底解剖！🎮💬🔥
SLUG: community-voice-roundup-vol{vol_num}
SUMMARY: Core Blockchain (XCB) の公式チャットやSNS、マイニングプールで今何が話題？CorePass KYBへの期待、Ryzenの採掘効率・Ecoモード検証、フェアローンチへの本音など、コミュニティのリアルな生声を自作PC女子リコロが徹底レポート！
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
        print(f"🧠 Google Gemini API を呼び出して【コミュニティ定点観測 Vol.{vol_num}】を執筆中...")
        with urllib.request.urlopen(req, context=ctx, timeout=GEMINI_TIMEOUT_SECONDS) as resp:
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

                print(f"✨ Gemini による初稿が完成しました: {title}")
                return {
                    "title": title,
                    "slug": slug,
                    "summary": summary,
                    "body": body_html
                }
    except Exception as e:
        print(f"⚠️ Gemini API呼び出しエラー: {e}", file=sys.stderr)
    return None

def generate_community_digest(vol_num):
    """初回執筆 + 長文ゲート（純テキスト10,000字に達するまで追記ラウンドを繰り返す）。

    戻り値は既存互換の dict(title/slug/summary/body) に chars / longform_rounds /
    heading_count / publish_ok を加えたもの。publish_ok が True のときだけ公開する。
    """
    art = _generate_community_digest_first_pass(vol_num)
    if not art:
        return None
    return enforce_longform_gate(
        art,
        raw_text=COMMUNITY_NOTES_TEXT,
        source_url="https://corestation.pages.dev/",
        source_name="公式Discord・Telegram(@Core_Blockchain_Japan)・X(#XCB #CoreBlockchain #PoDE)・Reddit・Catch That Rabbitプールの生の声"
    )

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
    if DRY_RUN:
        print("🧪 [dry-run] サイト統合をスキップ: articles/<slug>.html / initial_data.js / local_articles.js / index.html / sitemap.xml")
        return
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
    if DRY_RUN:
        print("🧪 [dry-run] git add/commit/push をスキップ")
        return
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

def run_community_digest_pipeline(dry_run=None):
    """Executes the full pipeline for community sentiment roundup.

    純テキスト10,000字（MIN_ARTICLE_CHARS）に達した記事だけを公開する。
    未達の回は vol_count を増やさず、次回実行で同じ巻番号として再試行し、
    試行回数は last_seen の longform_attempts に記録する。
    """
    if dry_run is None:
        dry_run = DRY_RUN
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 🔍 コミュニティ・SNS生の声定点観測パイプラインを開始...")
    if dry_run:
        print("🧪 [dry-run] 公開作用（はてな投稿 / articles・data・index・sitemap更新 / git push / SNS / vol_count更新）はすべてスキップします。")

    last_seen = load_last_seen()
    vol_num = last_seen.get("vol_count", 0) + 1
    attempts = dict(last_seen.get("longform_attempts") or {})
    attempt_key = f"vol{vol_num}"
    prev_attempts = attempts.get(attempt_key, 0)
    today_str = datetime.now().strftime("%Y-%m-%d")

    def _persist_attempts():
        if dry_run:
            return
        last_seen["longform_attempts"] = attempts
        save_last_seen(last_seen)

    if MAX_LONGFORM_ATTEMPTS and prev_attempts >= MAX_LONGFORM_ATTEMPTS:
        print(f"🚫 公開スキップ(再試行上限{MAX_LONGFORM_ATTEMPTS}回到達): {attempt_key} "
              f"試行回数={prev_attempts} → vol_count は {vol_num} のまま打ち切り", file=sys.stderr)
        return False

    print(f"🔎 {attempt_key} の執筆を開始します（過去の試行 {prev_attempts} 回）")
    art = generate_community_digest(vol_num)
    if not art:
        attempts[attempt_key] = prev_attempts + 1
        _persist_attempts()
        print(f"🚫 公開スキップ(生成失敗): vol={vol_num} Gemini応答なし 試行回数={attempts[attempt_key]} "
              f"vol_count未更新=次回再試行", file=sys.stderr)
        return False

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
            art, post_id=attempt_key,
            reason=f"plain_char_len={chars} < MIN_ARTICLE_CHARS={MIN_ARTICLE_CHARS} "
                   f"(追記 {MAX_CONTINUATION_ROUNDS} ラウンド実施後も未達)")
        attempts[attempt_key] = prev_attempts + 1
        _persist_attempts()
        print(f"🚫 公開スキップ(長文ゲート未達): slug={slug} plain_char_len={chars} "
              f"< MIN_ARTICLE_CHARS={MIN_ARTICLE_CHARS} h2={heading_count}本 "
              f"Gemini呼出し={rounds}回 試行回数={attempts[attempt_key]} ドラフト={draft_path} "
              f"vol_count未更新=次回再試行 title={title}", file=sys.stderr)
        return False

    # 1. Save temp output（ドラフト保存。外部公開ではない）
    temp_file = os.path.join(OUTPUT_DIR, f"{slug}.html")
    with open(temp_file, "w", encoding="utf-8") as f:
        f.write(full_blog_html)
    print(f"📝 ドラフト保存: {temp_file} (本文 {chars} 字 / h2 {heading_count} 本 / Gemini {rounds} 呼)")

    if dry_run:
        print(f"🧪 [dry-run] 公開作用をスキップ: はてなブログ投稿 / サイト統合 / git push / SNS配信 / vol_count更新。"
              f" 生成字数={chars} 保存先={temp_file}")
        return True

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
    attempts.pop(attempt_key, None)
    last_seen["longform_attempts"] = attempts
    save_last_seen(last_seen)
    print(f"✅ コミュニティ定点観測 Vol.{vol_num} の全公開・デプロイが完了しました！ (本文 {chars} 字 / h2 {heading_count} 本)")
    return True


def parse_cli_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Core Community Watcher（純テキスト10,000字以上の記事だけを公開）")
    parser.add_argument("--dry-run", action="store_true",
                        help="公開作用（はてなブログ投稿 / articles/HTML / local_articles.js / index.html / "
                             "sitemap / git push / SNS / vol_count更新）をすべてスキップし、"
                             "生成字数と保存先だけを出力します")
    return parser.parse_args(argv)


if __name__ == "__main__":
    cli = parse_cli_args()
    if cli.dry_run:
        DRY_RUN = True
    run_community_digest_pipeline()
