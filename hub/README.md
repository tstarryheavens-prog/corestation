# 統合マルチメディア発信＆収益化ハブ (ContentHub)

本ディレクトリ（`hub/`）は、**闘病日記・HEMS・仮想通貨XCB・AI・オルカン投資**の5大テーマを一元管理し、**A8.net等の広告自動挿入・日英多言語展開・ブログ記事・ショート動画台本・AI音声生成**を完全自動化するための統合環境です。

---

## 📁 ディレクトリ構成

```text
hub/
├── config/
│   ├── themes.json          # 5大テーマの読者層、トーン、推奨プラットフォーム設定
│   └── monetization.json    # A8.net広告タグ、提携リンク、海外取引所、寄付アドレス集
├── output/                  # 生成された記事・台本・音声ファイル等の出力先
├── media/
│   └── tts_generator.py     # ショート動画用AIナレーション音声生成（日/英 両対応）
├── generator.py             # 統合コンテンツ生成＆広告注入エンジン
└── README.md                # 本ドキュメント
```

---

## 🎯 統括する5大テーマ

| テーマID | テーマ名 | 主な発信先 | 組み込まれる主な広告・リンク |
| :--- | :--- | :--- | :--- |
| `health-journal` | 闘病日記・ライフログ | note, X | noteサポート・投げ銭、関連書籍 |
| `hems-smart-home` | HEMS・スマートホーム・節電 | ブログ, Shorts, X | スマートプラグ、Nature Remo E、節電機器 |
| `xcb-crypto` | Core Blockchain (XCB)・マイニング | ブログ, Shorts, Hashnode, X | Cryptact(税金ソフト), bitFlyer, 海外取引所, XCB寄付 |
| `ai-technology` | 最新AI・自動化・プログラミング | ブログ, Shorts, Hashnode, note | Python/AIプログラミング学習、開発ツール |
| `all-country-investing` | オルカン投資・新NISA・資産形成 | ブログ, Shorts, note, X | SBI証券、楽天証券（A8.net口座開設アフィリエイト） |

---

## 🚀 使い方（コマンド実行例）

私（AIエージェント）に**「オルカンの解説記事を作って」「XCBの英語ショート動画を作って」**とチャットで指示するだけで自動実行されますが、ターミナルから手動で実行することも可能です。

### 1. 利用可能なテーマ一覧の表示
```bash
python3 hub/generator.py --list-themes
```

### 2. オルカン投資の全セット（ブログ・note・Shorts・SNS）を一括生成
```bash
python3 hub/generator.py --theme all-country-investing --type all --lang ja --topic "新NISAでオルカン1本を選ぶべき理由"
```

### 3. XCBの情報を英語と日本語で同時生成
```bash
python3 hub/generator.py --theme xcb-crypto --type all --lang both --topic "Asustor NASによる自立型XCBノード運用の実際"
```

### 4. ショート動画用のAIナレーション音声を生成
```bash
# 日本語ナレーション（Kyoko）
python3 hub/media/tts_generator.py --text "オルカン投資で堅実に資産形成を始めましょう。" --out hub/output/invest_narration.m4a --lang ja

# 英語ナレーション（Samantha）
python3 hub/media/tts_generator.py --text "Welcome to CoreStation. Let's manage our crypto assets." --out hub/output/xcb_narration.m4a --lang en
```

---

## 💰 広告タグの差し替え方法

A8.netで提携した実際の広告コード（バナーHTMLやテキストリンクURL）は、
[`hub/config/monetization.json`](file:///Volumes/Docker/CoreGeeksEXp/hub/config/monetization.json)
を開き、該当する項目の `YOUR_A8_...` 部分をお手持ちのコードに置き換えるだけで完了します。
一度設定すれば、以降生成されるすべての記事や動画概要欄に自動反映されます。
