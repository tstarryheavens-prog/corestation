#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Hatena Blog Auto-Publisher (AtomPub API)
========================================
はてなブログの公式AtomPub APIを使用して、
記事の新規投稿（下書き・即時公開）、更新を完全自動化するスクリプト。
"""

import os
import sys
import json
import base64
import urllib.request
import urllib.error
import argparse
from datetime import datetime
import xml.sax.saxutils as saxutils

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config", "hatena_config.json")

def load_config():
    if not os.path.exists(CONFIG_PATH):
        raise FileNotFoundError(f"Configuration file not found: {CONFIG_PATH}")
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def build_entry_xml(title, body, categories=None, is_draft=False):
    """Build Atom entry XML for Hatena Blog."""
    draft_val = "yes" if is_draft else "no"
    escaped_title = saxutils.escape(title)
    # CDATA is safest for HTML content
    cdata_body = f"<![CDATA[\n{body}\n]]>"
    
    categories_xml = ""
    if categories:
        for cat in categories:
            categories_xml += f'  <category term="{saxutils.escape(cat)}" />\n'

    xml = f"""<?xml version="1.0" encoding="utf-8"?>
<entry xmlns="http://www.w3.org/2005/Atom"
       xmlns:app="http://www.w3.org/2007/app">
  <title>{escaped_title}</title>
  <content type="text/html">
{cdata_body}
  </content>
{categories_xml}  <app:control>
    <app:draft>{draft_val}</app:draft>
  </app:control>
</entry>"""
    return xml.encode("utf-8")

def publish_entry(title, body, categories=None, is_draft=False, entry_id=None):
    """Publish or update an article on Hatena Blog via AtomPub API."""
    cfg = load_config()
    hatena_id = cfg["hatena_id"]
    blog_domain = cfg["blog_domain"]
    api_key = cfg["api_key"]

    if entry_id:
        endpoint = f"https://blog.hatena.ne.jp/{hatena_id}/{blog_domain}/atom/entry/{entry_id}"
        method = "PUT"
    else:
        endpoint = f"https://blog.hatena.ne.jp/{hatena_id}/{blog_domain}/atom/entry"
        method = "POST"

    xml_data = build_entry_xml(title, body, categories, is_draft)

    # Basic Auth over HTTPS
    auth_str = f"{hatena_id}:{api_key}"
    auth_b64 = base64.b64encode(auth_str.encode("utf-8")).decode("utf-8")

    req = urllib.request.Request(
        endpoint,
        data=xml_data,
        headers={
            "Content-Type": "application/xml; charset=utf-8",
            "Authorization": f"Basic {auth_b64}"
        },
        method=method
    )

    import ssl
    ctx = ssl.create_default_context()
    try:
        import certifi
        ctx.load_verify_locations(certifi.where())
    except Exception:
        # Fallback for macOS standard python without certifi installed
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

    try:
        with urllib.request.urlopen(req, context=ctx) as resp:
            status = resp.status
            response_body = resp.read().decode("utf-8")
            if status in [200, 201]:
                print(f"🎉 投稿に成功しました！(HTTP {status})")
                
                # Extract URL if possible
                import re
                match = re.search(r'<link rel="alternate" type="text/html" href="([^"]+)"', response_body)
                if match:
                    entry_url = match.group(1)
                    print(f"🔗 記事URL: {entry_url}")
                    return entry_url
                return True
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode("utf-8")
        print(f"❌ 投稿に失敗しました (HTTP {e.code}): {err_msg}", file=sys.stderr)
        raise
    except Exception as e:
        print(f"❌ 通信エラー: {e}", file=sys.stderr)
        raise

def main():
    parser = argparse.ArgumentParser(description="Hatena Blog Publisher")
    parser.add_argument("--file", help="Path to markdown/html/text file to publish")
    parser.add_argument("--title", help="Article title")
    parser.add_argument("--category", nargs="*", default=["暗号資産", "マイニング", "確定申告"], help="Categories/Tags")
    parser.add_argument("--draft", action="store_true", help="Save as draft instead of publishing")
    parser.add_argument("--entry-id", help="Existing Entry ID to update (e.g. 14945776032076815564)")

    args = parser.parse_args()

    if not args.file or not os.path.exists(args.file):
        print("Error: Valid --file argument is required.")
        sys.exit(1)

    with open(args.file, "r", encoding="utf-8") as f:
        raw_content = f.read()

    # Extract title from markdown if not specified
    title = args.title
    body = raw_content
    lines = raw_content.splitlines()
    if not title and lines:
        for line in lines:
            if line.startswith("# "):
                title = line.replace("# ", "").strip()
                break
    if not title:
        title = "無題の記事"

    is_draft = args.draft
    mode_str = "下書き保存" if is_draft else "即時公開"
    action_str = f"更新 (Entry: {args.entry_id})" if args.entry_id else "新規投稿"
    print(f"🚀 はてなブログへ自動{action_str}中 ({mode_str}): 『{title}』...")

    publish_entry(title, body, categories=args.category, is_draft=is_draft, entry_id=args.entry_id)

if __name__ == "__main__":
    main()
