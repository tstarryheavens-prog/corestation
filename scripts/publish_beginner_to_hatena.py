#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Publish 5 Beginner Articles to Hatena Blog (corestation.hatenadiary.com)
via AtomPub API with delay between posts.
"""

import os
import sys
import time

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HUB_DIR = os.path.join(BASE_DIR, "hub")
sys.path.insert(0, HUB_DIR)

from hatena_publisher import publish_entry

POSTS = [
    {
        "title": "【超初心者向け】仮想通貨（暗号資産）とは何か？ビットコイン誕生の歴史からブロックチェーンの本質までゼロからわかる完全入門",
        "file": os.path.join(HUB_DIR, "output", "beginner_crypto-beginner-what-is-cryptocurrency-history.html"),
        "category": ["暗号資産", "仮想通貨入門", "ビットコイン", "ブロックチェーン", "歴史"]
    },
    {
        "title": "【初心者の疑問】仮想通貨を持つと何が学べる？実際に保有して初めて見えてくる「得られる体験」と「失うリスク」のリアル",
        "file": os.path.join(HUB_DIR, "output", "beginner_crypto-beginner-learn-gains-and-risks.html"),
        "category": ["暗号資産", "金融リテラシー", "資産運用", "リスク管理", "自己主権"]
    },
    {
        "title": "【図解でスッキリ】仮想通貨のエンジン「合意形成アルゴリズム」入門：PoW・PoSからCoreのPoDEまで初心者向けに徹底比較！",
        "file": os.path.join(HUB_DIR, "output", "beginner_crypto-beginner-consensus-algorithms-pow-pos-pode.html"),
        "category": ["ブロックチェーン", "PoW", "PoS", "PoDE", "CoreBlockchain", "技術解説"]
    },
    {
        "title": "【99%が消える魔境】メジャーではない草コイン・マイナーコインの「目利き」完全フレームワーク：XCBのような本物を見抜く7つのチェック基準",
        "file": os.path.join(HUB_DIR, "output", "beginner_crypto-beginner-how-to-evaluate-altcoins-xcb.html"),
        "category": ["草コイン", "アルトコイン", "銘柄選び", "CoreBlockchain", "XCB", "フェアローンチ"]
    },
    {
        "title": "【安全第一の資産運用】初心者が無理なく始める暗号資産投資の始め方：長期積立の基本と、押し売りなしの「国内安全取引所」の選び方",
        "file": os.path.join(HUB_DIR, "output", "beginner_crypto-beginner-investing-and-exchange-guide.html"),
        "category": ["暗号資産投資", "積立投資", "ドルコスト平均法", "国内取引所", "Coincheck", "bitFlyer"]
    }
]

def main():
    print("=" * 65)
    print("🚀 Publishing 5 Beginner Series Articles to Hatena Blog...")
    print("=" * 65)

    results = []
    for i, post in enumerate(POSTS, 1):
        print(f"\n[{i}/5] Publishing: 『{post['title']}』...")
        if not os.path.exists(post["file"]):
            print(f"❌ File not found: {post['file']}")
            continue

        with open(post["file"], "r", encoding="utf-8") as f:
            body = f.read()

        try:
            entry_url = publish_entry(
                title=post["title"],
                body=body,
                categories=post["category"],
                is_draft=False  # Publish immediately
            )
            print(f"✅ Success! URL: {entry_url}")
            results.append((post["title"], entry_url))
        except Exception as e:
            print(f"❌ Error publishing {post['title']}: {e}")

        if i < len(POSTS):
            print("⏳ Waiting 3 seconds before next post to respect API rate limits...")
            time.sleep(3)

    print("\n" + "=" * 65)
    print("🎉 Hatena Blog Publishing Summary:")
    print("=" * 65)
    for title, url in results:
        print(f"• {title}\n  -> {url}")

if __name__ == "__main__":
    main()
