/**
 * Core Blockchain / XCB Local Knowledge & Articles Archive
 * Hosted 100% locally on Asustor AS3102T NAS
 * Immune to core-geeks.com shutdown
 */
window.__CORE_LOCAL_ARTICLES__ = [
  {
    id: "tax-guide",
    title: "XCBマイニング報酬の確定申告・所得計算マニュアル",
    category: "tax",
    categoryName: "税務・確定申告",
    date: "2026-09-06",
    summary: "暗号資産マイニング（XCB）における所得税法上の取り扱い、取得時点の時価（PingExchange）による収入計算、必要経費の算定基準、および本NASアプリの申告用CSVの利用手順を網羅した完全ガイド。",
    content: `
      <h3>1. マイニング報酬の税法上の位置づけ（日本国内法）</h3>
      <p>暗号資産のマイニング（採掘）によって得られた報酬は、日本の税法上、原則として<strong>「雑所得」（または事業規模の場合は事業所得）</strong>として課税対象になります。給与所得などの他の所得と合算して総合課税の対象となります。</p>
      
      <div class="article-alert info">
        <strong>💡 所得計上のタイミング</strong><br>
        マイニング報酬が発生した時点（ウォレットにプールから着金した時点）の時価で総収入金額を計上します。売却・日本円換金時だけでなく、<strong>採掘した瞬間にも課税所得が発生する</strong>点に注意が必要です。
      </div>

      <h3>2. 所得金額の計算式</h3>
      <div class="article-code-box">
        <code>所得金額 = 総収入金額（採掘時の時価合計） - 必要経費</code>
      </div>
      <ul>
        <li><strong>総収入金額:</strong> 各トランザクションでウォレット（<code>cb57b88d24678c2091332971e3a38cca472dd8aac0cd</code>）に着金したXCB数量 × 着金日時のPingExchange時価レート（JPY換算）。</li>
        <li><strong>必要経費:</strong> マイニングを行うために直接要した費用（後述）。</li>
      </ul>

      <h3>3. 本NASアプリの「申告用データCSV」の活用方法</h3>
      <p>本システム（CoreGeeks Private NAS Clone）では、ローカルSQLiteデータベース（<code>wallet.db</code>）に全取引履歴（4,215件以上）と当時のPingExchange為替レートを完全保存しています。</p>
      <ol>
        <li>上部またはウォレット画面の<strong>「申告用データを開く / CSV出力」</strong>ボタンをクリックします。</li>
        <li>申告対象の年度（例: 2026年1月1日〜2026年12月31日）を開始日・終了日に入力します。</li>
        <li>基準通貨を「<strong>JPY (円)</strong>」に指定します。</li>
        <li><strong>「期間指定CSVダウンロード」</strong>または<strong>「全件一括ダウンロード」</strong>をクリックすると、確定申告計算ソフト（cryptact, Gtax等）やExcelでそのまま取り込めるUTF-8 BOM付きCSVファイルが即座に生成されます。</li>
      </ol>

      <h3>4. 認められる必要経費の代表例</h3>
      <table class="article-table">
        <thead>
          <tr>
            <th>経費科目</th>
            <th>内容・按分の考え方</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td><strong>電気料金</strong></td>
            <td>マイニングマシン（リグ）が消費した電力量（ワットモニター等で計測した消費電力 × 稼働時間 × 電気単価）を計算し按分計上。</td>
          </tr>
          <tr>
            <td><strong>マイニング機器代</strong></td>
            <td>
              10万円未満: 消耗品費として一括計上可能。<br>
              10万円以上〜30万円未満（中小企業特例）: 少額減価償却資産として一括可能。<br>
              30万円以上: パソコン・サーバー等の法定耐用年数（4〜5年）に基づき減価償却。
            </td>
          </tr>
          <tr>
            <td><strong>インターネット通信費</strong></td>
            <td>プール接続に使用した通信回線費用の一部（事業利用割合に応じて按分）。</td>
          </tr>
          <tr>
            <td><strong>消耗品・パーツ代</strong></td>
            <td>交換用ファン、ライザーカード、サーマルグリス、LANケーブル等。</td>
          </tr>
        </tbody>
      </table>

      <div class="article-alert warning">
        <strong>⚠️ 免責事項</strong><br>
        本マニュアルおよびCSV出力データは情報提供を目的としており、税理士法上の個別具体的な税務相談を構成するものではありません。実際の確定申告にあたっては、所轄の税務署または税理士等の専門家にご確認ください。
      </div>
    `
  },
  {
    id: "mining-setup",
    title: "Core Blockchain (XCB) マイニング設定完全ガイド (PoDE / Catch That Rabbit)",
    category: "mining",
    categoryName: "マイニング設定",
    date: "2026-09-06",
    summary: "耐ASICコンセンサスアルゴリズム「PoDE (Ouroboros-X)」の基礎、Catch That Rabbit プールの接続先サーバー、SRBMiner-MULTI / CoreMiner の推奨設定・最適化コマンドを解説。",
    content: `
      <h3>1. PoDE (Proof of Distributed Efficiency) と Ouroboros-X</h3>
      <p>Core Blockchainは、専用ASICによるハッシュパワーの独占を排除し、世界中の一般ハードウェア（CPU/GPU）によって分散化を維持するために設計された<strong>「Ouroboros-X」</strong>暗号アルゴリズムを採用しています。</p>
      <ul>
        <li><strong>アルゴリズム:</strong> Ouroboros-X (PoDE)</li>
        <li><strong>対応ハードウェア:</strong> 高性能CPU（AVX-512 / AVX2推奨）、AMD / NVIDIA GPU</li>
        <li><strong>ブロック生成間隔:</strong> 約14秒</li>
        <li><strong>報酬分配:</strong> マイニングプール経由で約2時間ごとに自動分配</li>
      </ul>

      <h3>2. Catch That Rabbit (CTR) プール接続情報</h3>
      <p>最も安定した公式対応プール「Catch That Rabbit」の推奨エンドポイント一覧です。日本国内からは<strong>シンガポール</strong>または<strong>香港</strong>ノードが最小レイテンシとなります。</p>
      
      <table class="article-table">
        <thead>
          <tr>
            <th>地域</th>
            <th>Stratum ホスト</th>
            <th>ポート</th>
            <th>プール手数料</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td><strong>シンガポール (日本推奨)</strong></td>
            <td><code>sg.catchthatrabbit.com</code></td>
            <td><code>8008</code></td>
            <td>1.0%</td>
          </tr>
          <tr>
            <td><strong>香港 (アジア近接)</strong></td>
            <td><code>hk.catchthatrabbit.com</code></td>
            <td><code>8008</code></td>
            <td>1.0%</td>
          </tr>
          <tr>
            <td><strong>北米 (US East)</strong></td>
            <td><code>us.catchthatrabbit.com</code></td>
            <td><code>8008</code></td>
            <td>1.0%</td>
          </tr>
          <tr>
            <td><strong>欧州 (ドイツ)</strong></td>
            <td><code>eu.catchthatrabbit.com</code></td>
            <td><code>8008</code></td>
            <td>1.0%</td>
          </tr>
        </tbody>
      </table>

      <h3>3. SRBMiner-MULTI 推奨コマンドライン</h3>
      <p>SRBMiner-MULTIを使用する場合の起動スクリプト例です。ウォレットアドレスの後に <code>.Worker名</code> を付与します。</p>

      <div class="article-code-box">
        <pre><code># Linux / HiveOS
./SRBMiner-MULTI --algorithm ouroboros \\
  --pool stratum+tcp://sg.catchthatrabbit.com:8008 \\
  --wallet cb57b88d24678c2091332971e3a38cca472dd8aac0cd.Rig01 \\
  --password x --cpu-threads 0

# Windows (.bat)
SRBMiner-MULTI.exe --algorithm ouroboros ^
  --pool stratum+tcp://sg.catchthatrabbit.com:8008 ^
  --wallet cb57b88d24678c2091332971e3a38cca472dd8aac0cd.Rig01 ^
  --password x --cpu-threads 0</code></pre>
      </div>

      <h3>4. CoreMiner (C++ 公式オープンソース) 起動例</h3>
      <div class="article-code-box">
        <pre><code>./coreminer -P stratum+tcp://cb57b88d24678c2091332971e3a38cca472dd8aac0cd.Rig01@sg.catchthatrabbit.com:8008</code></pre>
      </div>

      <h3>5. Worker監視とステータス反映</h3>
      <p>プールに有効なシェア（Accepted Shares）が送信されると、Catch That Rabbitのプール管理画面（<code>https://catchthatrabbit.com/wallet/{アドレス}</code>）にリアルタイムでハッシュレートとWorker名が反映されます。マシン停止時は約10〜15分でプール側ステータスがオフラインになります。</p>
    `
  },
  {
    id: "corepass-guide",
    title: "CorePass ウォレット & PingExchange 連携・セキュリティガイド",
    category: "guide",
    categoryName: "ウォレット・取引",
    date: "2026-09-06",
    summary: "分散型デジタルID「CorePass」の作成手順、本人確認（KYC）、リカバリーフレーズのオフライン保全、および分散型取引所「PingExchange」での取引・スワップ手順を整理。",
    content: `
      <h3>1. CorePass とは</h3>
      <p><strong>CorePass</strong> は、Core Blockchain 上に構築された次世代の分散型デジタルID＆自己主権型ウォレットです。ユーザーは自身の個人データを第三者企業に預けることなく、暗号化されたIDクレデンシャルとして手元で安全に管理できます。</p>

      <h3>2. 初期設定とセキュリティの鉄則</h3>
      <div class="article-alert warning">
        <strong>🔐 シードフレーズ（復元用パスフレーズ）の保管</strong><br>
        アプリ作成時に表示される12〜24単語のシードフレーズは、絶対にスクリーンショットやクラウド（Googleドライブ、iCloud等）に保存しないでください。<strong>必ず物理的な紙またはメタルプレートに手書きで記録し、金庫等の安全な場所に保管</strong>してください。
      </div>

      <ul>
        <li><strong>PINコード:</strong> アプリ起動時および送金トランザクション署名時に毎回要求されます。推測されやすい連番や生年月日は避けてください。</li>
        <li><strong>KYCレベル:</strong> PingExchange等のサービス利用には、CorePass内での公的身分証明書（パスポートや運転免許証）による認証が要求される場合があります。データはピアツーピアで検証され、中央サーバーには保存されません。</li>
      </ul>

      <h3>3. PingExchange との連携手順</h3>
      <p>PingExchange（<code>https://ping.exchange</code>）は、Core Blockchain ネイティブのハイブリッド分散型取引所です。</p>
      <ol>
        <li>PCブラウザで <a href="https://ping.exchange" target="_blank" rel="noopener noreferrer">https://ping.exchange ↗</a> にアクセスします。</li>
        <li>画面右上の「Connect Wallet」または「Login with CorePass」を選択します。</li>
        <li>表示されたQRコードをスマホの CorePass アプリのカメラで読み取ります。</li>
        <li>CorePass側で承認（Approve）し、PINコードを入力すると即座にセキュアログインが完了します。</li>
      </ol>

      <h3>4. XCB / CTN の取引と送金</h3>
      <p>採掘したXCBは、PingExchange上でCTN（Core Token）やステーブルコイン等とスワップ・売却が可能です。送金時のガス代（手数料）は通常 <code>0.000021 XCB</code> と極めて低廉に設定されています。</p>
    `
  },
  {
    id: "core-ecosystem",
    title: "Core Blockchain エコシステム & 公式技術リソース集",
    category: "coretech",
    categoryName: "技術・仕様",
    date: "2026-09-06",
    summary: "Core Blockchain (XCB)、Core Token (CTN)、Wall Money (DeFi) の役割分担と、公式GitHub、Blockindexエクスプローラー、コミュニティへのリンク集。",
    content: `
      <h3>1. Core Blockchain アーキテクチャ概要</h3>
      <p>Core Blockchain は、高セキュリティ・低消費電力・耐量子暗号基盤を視野に入れたレイヤー1ブロックチェーンです。</p>
      <ul>
        <li><strong>XCB (Core Coin):</strong> レイヤー1のネイティブ暗号資産。PoDEマイニングによって新規発行され、ネットワークのセキュリティとガス代の基軸となります。</li>
        <li><strong>CTN (Core Token):</strong> エコシステム内のユーティリティトークン。DeFiや分散型アプリケーション（dApps）のガバナンスや手数料割引に活用されます。</li>
        <li><strong>Wall Money:</strong> Coreネットワーク上で動作する分散型金融（DeFi）プラットフォーム。</li>
      </ul>

      <h3>2. ブロックチェーンの直接検証（Blockindex）</h3>
      <p>中央集権的なウェブサイト（core-geeks.com等）が終了した場合でも、ブロックチェーン自体の台帳データは完全に不変です。以下の独立したエクスプローラーから常時オンチェーン検証が可能です：</p>
      <ul>
        <li><strong>Blockindex Core Explorer:</strong> <a href="https://blockindex.net/address/cb57b88d24678c2091332971e3a38cca472dd8aac0cd" target="_blank" rel="noopener noreferrer">https://blockindex.net ↗</a></li>
        <li>自ウォレットの全履歴・トランザクションハッシュ・ブロック高を直接照会できます。</li>
      </ul>

      <h3>3. 公式GitHubリポジトリ</h3>
      <p>コア開発の進捗やソースコードはオープンソースとしてGitHub上で公開されています：</p>
      <ul>
        <li><strong>Go言語ノード実装:</strong> <a href="https://github.com/core-coin/core" target="_blank" rel="noopener noreferrer">github.com/core-coin/core ↗</a></li>
        <li><strong>CoreMiner C++ 実装:</strong> <a href="https://github.com/catchthatrabbit/coreminer" target="_blank" rel="noopener noreferrer">github.com/catchthatrabbit/coreminer ↗</a></li>
      </ul>

      <h3>4. 公式コミュニティ</h3>
      <p>トラブルシューティングや最新のハードフォーク・アップグレード情報は公式Telegramでアナウンスされます：</p>
      <ul>
        <li><strong>日本語公式Telegram:</strong> <a href="https://t.me/s/Core_Blockchain_Japan" target="_blank" rel="noopener noreferrer">t.me/s/Core_Blockchain_Japan ↗</a></li>
        <li><strong>グローバル公式Telegram:</strong> <a href="https://t.me/coreblockchaincc" target="_blank" rel="noopener noreferrer">t.me/coreblockchaincc ↗</a></li>
      </ul>
    `
  },
  {
    id: "coreminer-versions",
    title: "CoreMiner (catchthatrabbit) 全バージョン詳細更新履歴＆技術変遷分析",
    category: "mining",
    categoryName: "マイナー分析",
    date: "2026-09-06",
    summary: "v0.19.60から最新v0.19.89までの全30リリースを徹底分析。RandomY (RandomX 1.2.1) アルゴリズム刷新、xcb_getWork へのRPCプロトコル移行、Apple Silicon (macOS ARM64) 対応、systemd自動起動、cloud-init自動配備など、マイニング効率と安定性に直結する技術的進化を完全解剖。",
    content: `
      <div class="article-alert info">
        <strong>⚡ 結論：現在どのバージョンを使うべきか？</strong><br>
        必ず<strong>最新版（v0.19.89）または最低でも v0.19.87 以降</strong>を使用してください。<br>
        v0.19.84以前の古いバージョンでは、ノードのRPCが旧イーサリアム互換（<code>eth_getWork</code>）のままとなっており、最新プールやノードでリジェクトされる致命的な問題があるほか、RandomYの旧エンジンによりハッシュレート効率が低下します。
      </div>

      <h3>1. CoreMiner バージョン進化の4大フェーズ</h3>
      <p>公式リポジトリ（<code>catchthatrabbit/coreminer</code>）は、Core Blockchainのメインネット稼働とプール（Catch That Rabbit）の発展に伴い、以下の4つの世代を経て進化してきました。</p>

      <table class="article-table">
        <thead>
          <tr>
            <th>フェーズ・世代</th>
            <th>バージョン範囲</th>
            <th>主な進化と技術的マイルストーン</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td><strong>第1期：基盤構築とクロスプラットフォーム化</strong></td>
            <td><code>v0.19.60</code> 〜 <code>v0.19.72</code><br>(2022年5月〜10月)</td>
            <td>
              ・Apple Silicon（Darwin ARM64 / M1, M2）のネイティブコンパイル・実行対応。<br>
              ・スレッド細分化パラメータ（<code>-t</code>, <code>--mining-threads</code>）の実装。<br>
              ・DockerコンテナのAlpine Linux化による極小化（約20MB）。
            </td>
          </tr>
          <tr>
            <td><strong>第2期：自動化・耐障害性と運用安定化</strong></td>
            <td><code>v0.19.73</code> 〜 <code>v0.19.84</code><br>(2023年2月〜9月)</td>
            <td>
              ・Alpine環境（musl libc）でのビルドエラー解消（<code>execinfo.h</code> 依存排除）。<br>
              ・CLIでのバージョン確認（<code>--version</code>）と更新通知機能の実装。<br>
              ・設定ファイル（<code>config.json</code>）による複数プール・ドングル設定の拡張。<br>
              ・Linux <code>systemd</code> による自動起動（autostart）ユニット追加。<br>
              ・<code>mine.sh</code> の切断復帰時における無限ループ不具合の修正。
            </td>
          </tr>
          <tr>
            <td><strong>第3期：コア暗号エンジン刷新とプロトコル革新</strong></td>
            <td><code>v0.19.85</code> 〜 <code>v0.19.88</code><br>(2024年10月〜11月)</td>
            <td>
              ・<strong>【重要】RandomY 刷新:</strong> RandomX 1.2.1 をベースとした最新暗号エンジンへ移行。JIT最適化とキャッシュ効率の劇的向上。<br>
              ・<strong>【重要】RPCメソッド変更:</strong> 旧来の <code>eth_getWork</code> から Core Blockchain 正式仕様の <strong><code>xcb_getWork</code></strong> へ完全移行。
            </td>
          </tr>
          <tr>
            <td><strong>第4期：現代的CI/CD・クラウド自動配備</strong></td>
            <td><code>v0.19.89</code> 〜 現在<br>(2025年5月〜)</td>
            <td>
              ・GitHub Actionsに <code>ubuntu-24.04-arm</code> ホストを採用し、ARM64バイナリの自動生成を高速化。<br>
              ・<code>cloud-init-coreminer.yaml</code> を追加し、クラウドVPSでの1クリック自動構築に対応。<br>
              ・<code>mine.sh</code> に対話型ワーカー名設定（プレーン名、Fediverse形式、ランダム名）を追加。<br>
              ・外部監視用 JSON-RPC API ドキュメント（<code>miner_getstatdetail</code>, <code>miner_ping</code>）の完全整備。
            </td>
          </tr>
        </tbody>
      </table>

      <h3>2. 最重要アップデートの詳細技術分析</h3>

      <h4>① RPCメソッドの変更：<code>eth_getWork</code> から <code>xcb_getWork</code> へ（v0.19.87）</h4>
      <p>CoreMinerは初期、イーサリアム系のマイナー構造（<code>ethminer</code>）からフォークして開発されていたため、プールやローカルノードとの採掘ジョブ通信に <code>{"method": "eth_getWork"}</code> を使用していました。</p>
      <p>しかし、Core Blockchain独自のノード（<code>core-coin/core</code>）がネイティブ仕様へと完全に分離・アップデートされたことで、<strong><code>xcb_getWork</code></strong> への呼出名変更が行われました。この変更を含む v0.19.87 以降でないと、最新のCoreブロックチェーンノードと直接マイニングを行うことができません。</p>

      <h4>② RandomY (RandomX 1.2.1) へのエンジン刷新（v0.19.85〜v0.19.86）</h4>
      <p>Core BlockchainのPoDEコンセンサスアルゴリズムは、Monero等で実績のあるRandomX系アルゴリズム「RandomY」を採用しています。</p>
      <ul>
        <li><strong>JITコンパイラの改善:</strong> x86_64およびARM64における実行時マシンコード生成が高速化。</li>
        <li><strong>Huge Pages (大容量メモリページ) との親和性向上:</strong> 2MB / 1GB ページ利用時のTLBミスヒットを大幅に削減。</li>
        <li><strong>命令セット最適化:</strong> 最新CPU（AMD Zen3/Zen4/Zen5, Intel Core 12〜14世代, Apple Mシリーズ）でのAVX2 / AVX-512 演算スループットが向上。</li>
      </ul>

      <h4>③ Apple Silicon (Darwin ARM64) ネイティブ対応（v0.19.60）</h4>
      <p>M1/M2/M3/M4などのApple Silicon Macで、Rosetta 2を介さずネイティブARM64バイナリとして動作可能になりました。これにより消費電力あたりの採掘効率（ワットパフォーマンス）が極めて高くなっています。</p>

      <h3>3. 全バージョン変更履歴対照表（v0.19.60 〜 v0.19.89）</h3>
      <table class="article-table">
        <thead>
          <tr>
            <th>バージョン</th>
            <th>公開日</th>
            <th>変更内容・コミット要約</th>
            <th>影響度</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td><code>v0.19.89</code></td>
            <td>2025-05-27</td>
            <td>ubuntu-24.04-arm GitHubランナー採用、Boost URL修正、cloud-init対応、mine.sh対話ワーカー命名、APIドキュメント拡充</td>
            <td><span class="badge-online" style="background:#16a34a;">推奨</span></td>
          </tr>
          <tr>
            <td><code>v0.19.88</code></td>
            <td>2024-11-02</td>
            <td>xcb_getWork 反映後の公式安定リリースビルドの生成</td>
            <td><span class="badge-online" style="background:#16a34a;">安定</span></td>
          </tr>
          <tr>
            <td><code>v0.19.87</code></td>
            <td>2024-11-01</td>
            <td><strong>RPC通信メソッドを eth_getWork から xcb_getWork へ変更</strong>、CMake 3.5ビルド調整</td>
            <td><span class="badge-online" style="background:#dc2626;">重大</span></td>
          </tr>
          <tr>
            <td><code>v0.19.86</code></td>
            <td>2024-10-31</td>
            <td>最新RandomYエンジンを搭載した公式Dockerイメージの自動ビルド構築</td>
            <td><span class="badge-online" style="background:#ea580c;">高</span></td>
          </tr>
          <tr>
            <td><code>v0.19.85</code></td>
            <td>2024-10-31</td>
            <td><strong>RandomX 1.2.1 ベースの最新 RandomY エンジンへサブモジュール刷新</strong></td>
            <td><span class="badge-online" style="background:#dc2626;">重大</span></td>
          </tr>
          <tr>
            <td><code>v0.19.84</code></td>
            <td>2023-09-28</td>
            <td>公式README更新・ドキュメント整備（プール接続ガイド更新）</td>
            <td><span>通常</span></td>
          </tr>
          <tr>
            <td><code>v0.19.83</code></td>
            <td>2023-08-25</td>
            <td>Core Blockchainコア開発者 Rastislav によるドキュメント最適化</td>
            <td><span>通常</span></td>
          </tr>
          <tr>
            <td><code>v0.19.82</code></td>
            <td>2023-08-16</td>
            <td><strong>mine.sh ラッパースクリプトの切断時無限ループ不具合を修正</strong></td>
            <td><span class="badge-online" style="background:#ea580c;">高</span></td>
          </tr>
          <tr>
            <td><code>v0.19.81</code></td>
            <td>2023-05-11</td>
            <td>Linux systemd 向け autostart（自動起動サービス）機能の追加</td>
            <td><span class="badge-online" style="background:#0284c7;">機能追加</span></td>
          </tr>
          <tr>
            <td><code>v0.19.80</code></td>
            <td>2023-02-24</td>
            <td>config.json 拡張（複数プールプリセット、外付けドングル暗号キー対応）</td>
            <td><span class="badge-online" style="background:#0284c7;">機能追加</span></td>
          </tr>
          <tr>
            <td><code>v0.19.79</code></td>
            <td>2023-02-13</td>
            <td>--version オプション実装、バージョン更新チェック機能の追加</td>
            <td><span>通常</span></td>
          </tr>
          <tr>
            <td><code>v0.19.73〜78</code></td>
            <td>2023-02-08〜11</td>
            <td>Hunterキャッシュ活用、Alpine(musl)ビルド修正(execinfo.h排除)、CMakeビルド版数引数化</td>
            <td><span>改善</span></td>
          </tr>
          <tr>
            <td><code>v0.19.72</code></td>
            <td>2022-10-06</td>
            <td>公式Dockerイメージを alpine:latest ベースに移行（軽量化＆スキャン）</td>
            <td><span>改善</span></td>
          </tr>
          <tr>
            <td><code>v0.19.71</code></td>
            <td>2022-09-22</td>
            <td>pool.sh スクリプトへ $ARGS 引数透過機能を追加</td>
            <td><span>通常</span></td>
          </tr>
          <tr>
            <td><code>v0.19.69〜70</code></td>
            <td>2022-09-13</td>
            <td>tar.gz 自動アーカイブおよびGitHubリリースタグ連携のCI整備</td>
            <td><span>改善</span></td>
          </tr>
          <tr>
            <td><code>v0.19.64〜68</code></td>
            <td>2022-08-22〜25</td>
            <td>スレッド指定オプション -t / --threads 実装、起動スクリプトの引数同期</td>
            <td><span class="badge-online" style="background:#0284c7;">機能追加</span></td>
          </tr>
          <tr>
            <td><code>v0.19.61〜63</code></td>
            <td>2022-08-10〜11</td>
            <td>--mining-threads パラメータ追加、Stratum接続パスの正規化</td>
            <td><span>改善</span></td>
          </tr>
          <tr>
            <td><code>v0.19.60</code></td>
            <td>2022-05-07〜07-07</td>
            <td>初期オープンソース公開版、Apple Silicon (Darwin ARM64) ネイティブ対応追加</td>
            <td><span class="badge-online" style="background:#16a34a;">起点</span></td>
          </tr>
        </tbody>
      </table>

      <h3>4. マイナー向け実践的チューニングTips</h3>
      <ol>
        <li>
          <strong>Huge Pages (2MB) の有効化（Linux/HiveOS）:</strong><br>
          RandomYは高速メモリアクセスを多用するため、OS側でHuge Pagesを有効にすることでハッシュレートが <strong>20〜30% 向上</strong> します：
          <div class="article-code-box">
            <pre><code>sudo sysctl -w vm.nr_hugepages=1280
echo "vm.nr_hugepages=1280" | sudo tee -a /etc/sysctl.conf</code></pre>
          </div>
        </li>
        <li>
          <strong>スレッド数設定の黄金比:</strong><br>
          単純にCPUの論理コア数（スレッド数）を最大に設定すると、L3キャッシュ競合によって逆にハッシュレートが低下します。<br>
          <strong>「CPUのL3キャッシュ総容量 ÷ 2MB」</strong>（例: L3が32MBなら 16スレッド）を目安に <code>-t</code> を設定するのが最も高効率です。
        </li>
        <li>
          <strong>SRBMiner-MULTI との比較:</strong><br>
          CoreMinerは公式C++実装で極めて安定しており、CPU専業リグやmacOS環境で抜群の安定性を誇ります。一方、GPU（AMD/NVIDIA）との同時マイニングを行いたい場合は SRBMiner-MULTI も選択肢となります。
        </li>
      </ol>
    `

  },
  {
    id: "cpu-tuning-guide",
    title: "Core i9-14900 / Ryzen 9 7950X / Core i5-13500 推奨マイニング設定＆最適化完全ガイド",
    category: "mining",
    categoryName: "CPU設定ガイド",
    date: "2026-09-06",
    summary: "AMD Ryzen 9 7950X、Intel Core i9-14900、Core i5-13500の3大CPUにおけるXCB (RandomY / PoDE) マイニング推奨スレッド数、BIOS電力制限（PL1/PL2、Eco Mode）、Curve Optimizer、CoreMiner / SRBMiner起動コマンド、想定ハッシュレートを徹底解説。",
    content: `
      <div class="article-alert info">
        <strong>⚡ RandomY (PoDE) マイニングにおけるCPU選定・設定の鉄則</strong><br>
        RandomY（RandomX 1.2.1互換）では、<strong>「スレッドあたり2MBのL3キャッシュ」</strong>を消費します。<br>
        CPUの論理スレッド数を上限まで指定するのではなく、<strong>「L3キャッシュ総容量 ÷ 2MB」</strong>を上限としてスレッド数（<code>-t</code>）を設定することが、ハッシュレート低下（キャッシュ競合）を防ぐ最大の鍵です。
      </div>

      <h3>1. AMD Ryzen 9 7950X (Zen 4) 推奨設定</h3>
      <table class="article-table">
        <tbody>
          <tr><th>コア / スレッド</th><td>16コア / 32スレッド（全コア同一のフル性能コア）</td></tr>
          <tr><th>L3キャッシュ</th><td>64MB (32MB CCD × 2基)</td></tr>
          <tr><th>推奨スレッド数</th><td><strong>30 〜 32 スレッド (<code>-t 30</code> 推奨)</strong></td></tr>
          <tr><th>想定ハッシュレート</th><td><strong>約 22,000 〜 25,000 H/s</strong></td></tr>
          <tr><th>想定消費電力</th><td>定格: 約200W / 105W Eco Mode時: 約125W</td></tr>
        </tbody>
      </table>

      <h4>最適化チューニング手順:</h4>
      <ol>
        <li>
          <strong>105W Eco Mode (PPT 142W / TDC 110A / EDC 150A):</strong><br>
          BIOS（AMD CBS / Precision Boost Overdrive）で「Eco Mode (105W)」を適用。定格（230W）から消費電力と発熱が40%以上激減する一方、ハッシュレートは95%以上維持されます（ワットパフォーマンス最強設定）。
        </li>
        <li>
          <strong>Curve Optimizer (低電圧化):</strong><br>
          All Cores <code>-20</code> 〜 <code>-30</code> に設定。動作電圧が下がり、電力制限内でのブーストクロックが向上します。
        </li>
        <li>
          <strong>Huge Pages (2MB) 有効化:</strong><br>
          Linux/HiveOSでは <code>sudo sysctl -w vm.nr_hugepages=1280</code> を実行。
        </li>
      </ol>

      <h4>起動コマンド例:</h4>
      <div class="article-code-box">
        <pre><code># CoreMiner (Linux)
./coreminer -t 30 -P stratum+tcp://cb57b88d24678c2091332971e3a38cca472dd8aac0cd.7950X@sg.catchthatrabbit.com:8008

# SRBMiner-MULTI (Linux / Windows)
./SRBMiner-MULTI --algorithm pode --pool sg.catchthatrabbit.com:8008 --wallet cb57b88d24678c2091332971e3a38cca472dd8aac0cd.7950X --cpu-threads 30</code></pre>
      </div>

      <hr style="border:none; border-top: 1px solid #e2e8f0; margin: 28px 0;">

      <h3>2. Intel Core i9-14900 / 14900K 推奨設定</h3>
      <table class="article-table">
        <tbody>
          <tr><th>コア / スレッド</th><td>24コア (8 P-cores + 16 E-cores) / 32スレッド</td></tr>
          <tr><th>L3キャッシュ</th><td>36MB、L2キャッシュ: 32MB</td></tr>
          <tr><th>推奨スレッド数</th><td><strong>16 〜 18 スレッド (<code>-t 18</code>) ※32スレッド全開は厳禁</strong></td></tr>
          <tr><th>想定ハッシュレート</th><td><strong>約 13,500 〜 15,500 H/s</strong></td></tr>
          <tr><th>想定消費電力</th><td>電力制限時: 約140W 〜 180W (定格無制限時は300W超で危険)</td></tr>
        </tbody>
      </table>

      <h4>最適化チューニング手順:</h4>
      <div class="article-alert warning">
        <strong>⚠️ 32スレッド全開によるキャッシュ破綻に注意</strong><br>
        L3キャッシュが36MBしかないため、36MB ÷ 2MB = <strong>最大18スレッド</strong> が理論限界です。32スレッド指定するとL3キャッシュの衝突（スラッシング）により、ハッシュレートが半減（8,000 H/s以下）することがあります。
      </div>
      <ol>
        <li>
          <strong>電力制限 (PL1=125W〜150W / PL2=180W):</strong><br>
          第14世代Core i9特有のVcore過電圧によるCPU劣化やクラッシュを防ぐため、BIOSでIntel Default Profile（Baseline）を適用し、長期間PL1を125W〜150W、PL2を180W、IccMaxを307A〜400Aに確実に制限してください。
        </li>
        <li>
          <strong>Adaptive Vcore Offset (低電圧化):</strong><br>
          <code>-0.050V</code> 〜 <code>-0.075V</code> のマイナスオフセットを設定し、サーマルスロットリングを回避。
        </li>
        <li>
          <strong>スレッド割り当て:</strong><br>
          Pコア8個（16スレッド）＋ Eコア2スレッド（合計18スレッド）が最もバランス良くハッシュレートを叩き出します。
        </li>
      </ol>

      <h4>起動コマンド例:</h4>
      <div class="article-code-box">
        <pre><code># CoreMiner (Linux)
./coreminer -t 18 -P stratum+tcp://cb57b88d24678c2091332971e3a38cca472dd8aac0cd.14900@sg.catchthatrabbit.com:8008

# SRBMiner-MULTI (Linux / Windows)
./SRBMiner-MULTI --algorithm pode --pool sg.catchthatrabbit.com:8008 --wallet cb57b88d24678c2091332971e3a38cca472dd8aac0cd.14900 --cpu-threads 18</code></pre>
      </div>

      <hr style="border:none; border-top: 1px solid #e2e8f0; margin: 28px 0;">

      <h3>3. Intel Core i5-13500 推奨設定</h3>
      <table class="article-table">
        <tbody>
          <tr><th>コア / スレッド</th><td>14コア (6 P-cores + 8 E-cores) / 20スレッド</td></tr>
          <tr><th>L3キャッシュ</th><td>24MB、L2キャッシュ: 11.5MB</td></tr>
          <tr><th>推奨スレッド数</th><td><strong>10 〜 12 スレッド (<code>-t 11</code> 推奨)</strong></td></tr>
          <tr><th>想定ハッシュレート</th><td><strong>約 6,800 〜 7,800 H/s</strong></td></tr>
          <tr><th>想定消費電力</th><td>約 65W 〜 85W</td></tr>
        </tbody>
      </table>

      <h4>最適化チューニング手順:</h4>
      <ol>
        <li>
          <strong>推奨スレッド数の根拠:</strong><br>
          L3キャッシュが24MBのため、24MB ÷ 2MB = <strong>最大12スレッド</strong> が上限です。OSのバックグラウンドタスク用に1スレッド残した <strong>11スレッド（<code>-t 11</code>）</strong> が最もフレーム落ちなくスムーズに動作します。
        </li>
        <li>
          <strong>低発熱・高信頼性常時稼働:</strong><br>
          標準TDPが65W（PL1=65W, PL2=154W）と非常に扱いやすく、BIOSでPL1を65W〜80Wに設定しておけば、小型ケースや安価な空冷クーラーでもCPU温度60℃台で24時間365日静音マイニングが可能です。
        </li>
      </ol>

      <h4>起動コマンド例:</h4>
      <div class="article-code-box">
        <pre><code># CoreMiner (Linux)
./coreminer -t 11 -P stratum+tcp://cb57b88d24678c2091332971e3a38cca472dd8aac0cd.13500@sg.catchthatrabbit.com:8008

# SRBMiner-MULTI (Linux / Windows)
./SRBMiner-MULTI --algorithm pode --pool sg.catchthatrabbit.com:8008 --wallet cb57b88d24678c2091332971e3a38cca472dd8aac0cd.13500 --cpu-threads 11</code></pre>
      </div>

      <hr style="border:none; border-top: 1px solid #e2e8f0; margin: 28px 0;">

      <h3>4. 3モデルの比較・ワットパフォーマンスまとめ</h3>
      <table class="article-table">
        <thead>
          <tr>
            <th>CPUモデル</th>
            <th>L3キャッシュ</th>
            <th>推奨スレッド数</th>
            <th>想定採掘速度</th>
            <th>消費電力 (推奨時)</th>
            <th>ワット効率評価</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td><strong>Ryzen 9 7950X</strong></td>
            <td>64 MB</td>
            <td><strong>30 〜 32</strong></td>
            <td><strong>22,000〜25,000 H/s</strong></td>
            <td>約 125 W (Eco Mode)</td>
            <td>★★★★★ (180 H/s・W)</td>
          </tr>
          <tr>
            <td><strong>Core i9-14900</strong></td>
            <td>36 MB</td>
            <td><strong>16 〜 18</strong></td>
            <td><strong>13,500〜15,500 H/s</strong></td>
            <td>約 150 W (PL制限時)</td>
            <td>★★★☆☆ (95 H/s・W)</td>
          </tr>
          <tr>
            <td><strong>Core i5-13500</strong></td>
            <td>24 MB</td>
            <td><strong>10 〜 12</strong></td>
            <td><strong>6,800〜7,800 H/s</strong></td>
            <td>約 70 W (定格付近)</td>
            <td>★★★★☆ (105 H/s・W)</td>
          </tr>
        </tbody>
      </table>
    `

  },
  {
    id: "tokenomics-halving-history",
    title: "Core Blockchain (XCB) 半減期・供給量・価値遷移の時系列完全クロニクル",
    category: "coretech",
    categoryName: "トークノミクス",
    date: "2026-09-06",
    summary: "2022年のメインネット創成期から2026年現在までのXCB供給量、半減・発行減衰メカニズム、PingExchangeにおける価格推移（0.7円〜11.6円）、採掘難易度と日次採掘量の激変を時系列表と詳細分析で完全総括。",
    content: `
      <div class="article-alert info">
        <strong>📊 結論：XCBの半減期と価値形成の本質</strong><br>
        Core Blockchain（XCB）は、ビットコインのような単なる4年ごとの機械的半減期とは異なり、<strong>「PoDE (Proof of Distributed Efficiency) による難易度連動減衰」</strong>と<strong>「実需主導の循環供給制約（全供給の約25%のみ市場流通）」</strong>によって価値が形成されています。<br>
        2023年夏の「1日20〜24 XCB」から、2024年の「1日10 XCB」、そして2026年現在の「1日1.5〜7 XCB」へと、<strong>採掘難易度の急上昇と実質半減サイクル</strong>が進行しています。
      </div>

      <h3>1. 通貨供給量（サプライ）の現状と基本仕様</h3>
      <table class="article-table">
        <tbody>
          <tr><th>ブロック高 (Block Height)</th><td>約 <strong>18,891,500 ブロック</strong> (約7秒ごとに生成)</td></tr>
          <tr><th>総供給量 (Total Supply)</th><td><strong>397,677,423 XCB</strong> (約3.97億 XCB)</td></tr>
          <tr><th>循環供給量 (Circulating Supply)</th><td><strong>98,681,863 XCB</strong> (約9,868万 XCB、全体の約24.8%)</td></tr>
          <tr><th>累計採掘済みXCB (Total Mined)</th><td><strong>84,642,360 XCB</strong> (約8,464万 XCB)</td></tr>
          <tr><th>基本ブロック報酬</th><td>1ブロックあたり <strong>5 XCB</strong>（マイナープール分配: 約 <strong>1.65 XCB</strong>）</td></tr>
          <tr><th>主要取引所</th><td><strong>PingExchange</strong> (分散型P2P取引所、XCB/USDCペア)</td></tr>
        </tbody>
      </table>

      <h3>2. XCB 価値遷移・半減期時系列クロニクル (2022年〜2026年)</h3>
      <p>創成期から現在に至るまでの主要なマイルストーン、時価レート、採掘難易度、および1日あたりの採掘量の変遷です。</p>

      <table class="article-table">
        <thead>
          <tr>
            <th>年代・フェーズ</th>
            <th>時期</th>
            <th>主な出来事・マイルストーン</th>
            <th>XCB時価 (USD / JPY)</th>
            <th>1日採掘量目安</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td><strong>第1期：メインネット創成期</strong></td>
            <td>2022年<br>5月〜12月</td>
            <td>
              ・Core Blockchain PoDEメインネット稼働開始<br>
              ・CorePass 分散型ID構想発表<br>
              ・公式CoreMiner (v0.19.60) オープンソース公開<br>
              ・Apple Silicon (M1/M2) ネイティブ対応
            </td>
            <td><strong>$0.005 〜 $0.015</strong><br>(約 0.7 〜 2.0 円)</td>
            <td>50〜100+ XCB/日<br>(黎明期独占状態)</td>
          </tr>
          <tr>
            <td><strong>第2期：エコシステム確立期</strong></td>
            <td>2023年<br>1月〜12月</td>
            <td>
              ・Catch That Rabbit 公式プール本格稼働<br>
              ・PingExchangeでのXCB/USDC P2P取引開始<br>
              ・CoreGeeksマイニングポータル開設<br>
              ・日本コミュニティ（Telegram, note）の急拡大
            </td>
            <td><strong>$0.015 〜 $0.035</strong><br>(約 2.2 〜 5.2 円)</td>
            <td><strong>約 20 〜 24 XCB/日</strong><br>(安定採掘の黄金期)</td>
          </tr>
          <tr>
            <td><strong>第3期：第1次半減・難易度急騰期</strong></td>
            <td>2024年<br>1月〜12月</td>
            <td>
              ・<strong>【重要】実質半減期到来:</strong> マイナー激増によりDifficultyが急騰、採掘量が10 XCB/日、さらに一時2 XCB/日へ激減<br>
              ・RPCメソッドを <code>eth_getWork</code> から <code>xcb_getWork</code> へ公式改修<br>
              ・RandomY を最新 RandomX 1.2.1 ベースへ全面刷新<br>
              ・希少性急上昇により価格が11円台へ高騰
            </td>
            <td><strong>$0.030 〜 $0.075</strong><br>(約 4.5 〜 <strong>11.6 円</strong> 最高値圏)</td>
            <td><strong>約 2 〜 12 XCB/日</strong><br>(難易度急騰による逓減)</td>
          </tr>
          <tr>
            <td><strong>第4期：DePIN・RWA実用化期</strong></td>
            <td>2025年<br>1月〜12月</td>
            <td>
              ・DePIN（分散型物理インフラ）およびRWA（実世界資産）連携構想<br>
              ・ネットワーク総ハッシュレートが18〜20 Mh/sへ定着<br>
              ・CoreMiner v0.19.89 リリース（クラウド自動構築・ARM64高速化）<br>
              ・Wall Money DeFi基盤のテストネット展開
            </td>
            <td><strong>$0.040 〜 $0.080</strong><br>(約 6.0 〜 12.0 円)</td>
            <td>約 8 〜 12 XCB/日<br>(リグ増設マイナーが優勢)</td>
          </tr>
          <tr>
            <td><strong>第5期：自立分散・安定成熟期</strong></td>
            <td>2026年<br>(現在)</td>
            <td>
              ・総供給量3.97億XCB、市場流通約9,868万XCB（約25%）到達<br>
              ・累計採掘量8,464万XCB突破<br>
              ・core-geeks.com廃止に伴う本NAS自立分散型管理への完全移行<br>
              ・確定申告用取引履歴（4,215件）の資産保全
            </td>
            <td><strong>$0.0319</strong><br>(約 <strong>4.81 〜 5.00 円</strong>)</td>
            <td>約 1.5 〜 7.1 XCB/日<br>(定常採掘期)</td>
          </tr>
        </tbody>
      </table>

      <h3>3. 価値（価格）が上昇・維持される3大ドライバー</h3>
      <ol>
        <li>
          <strong>流通供給量の厳格なロック（低浮動株構造）:</strong><br>
          総供給量3.97億XCBのうち、市場に流通しているのはわずか **約24.8%（約9,868万XCB）** です。残りはエコシステム基盤や長期ステーキング、DePINノード担保として拘束されているため、売り圧力が極めて限定的です。
        </li>
        <li>
          <strong>マイニング報酬の自然半減（ディケイ効果）:</strong><br>
          2023年の「1日20XCB超」から、2024〜2026年には「1日1〜7XCB」へと採掘難易度が劇的に上昇。1枚あたりのXCBを採掘するために必要な電気代・計算コスト（限界費用）が数倍に跳ね上がったことで、市場価格のフロア（下値支持線）が切り上がりました。
        </li>
        <li>
          <strong>CorePass ID & PingExchange の実需ユーティリティ:</strong><br>
          XCBは単なる投機コインではなく、CorePassでのKYC暗号化署名、PingExchangeでのガス代（0.000021 XCB）、およびスマートコントラクト実行手数料として日々消費されています。
        </li>
      </ol>

      <h3>4. 今後の見通し：2026年後半〜2030年の供給・実需・価格予測</h3>
      <p>過去4年間のデータ推移（発行減衰、難易度上昇、流通量制約）に基づき、今後のCore Blockchain（XCB）における<strong>採掘環境、実需エコシステム、および価格シナリオ</strong>を多角的に分析・予測します。</p>

      <h4>① 採掘環境・供給曲線の見通し：さらなる希少化と原価切り上がり</h4>
      <ul>
        <li><strong>新規発行インフレ率の極小化:</strong> 現在すでに総供給約3.97億XCBのうち累計採掘が8,400万XCBを超え、年間の新規供給ペースは急速に鈍化しています。2027〜2028年にかけて年間インフレ率は1.5%〜2.0%以下へ収束する見込みです。</li>
        <li><strong>マイナーの損益分岐点（原価）の上昇:</strong> 採掘難易度の上昇に伴い、1 XCBを獲得するために要する消費電力は年々増加しています。現在の実効原価（約4〜5円）は、2027年には<strong>8円〜12円水準</strong>へ切り上がると見込まれ、これが強力な価格の下値支持線（フロアプライス）となります。</li>
        <li><strong>マイニングハードウェアの世代交代:</strong> 電力効率の低い旧世代CPUは順次採掘停止に追い込まれ、AMD Zen 4 (7950X) / Zen 5 や高効率ARM64サーバーノードへの集約が決定づけられます。</li>
      </ul>

      <h4>② エコシステム・実需ドライバーの進展</h4>
      <table class="article-table">
        <thead>
          <tr>
            <th>成長エンジン</th>
            <th>時期・ターゲット</th>
            <th>XCB需要への直接的影響</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td><strong>DePIN & RWA 統合</strong></td>
            <td>2026年後半〜2027年</td>
            <td>実世界のIoTセンサー・物理インフラの検証ノード担保としてXCBがロックされ、市場流通量がさらにタイト化。</td>
          </tr>
          <tr>
            <td><strong>CorePass DID 企業採用</strong></td>
            <td>2027年〜2028年</td>
            <td>分散型個人認証（KYC）のピアツーピア署名時にXCBガスが恒常的にバーン・消費される実需ループの定着。</td>
          </tr>
          <tr>
            <td><strong>Wall Money (DeFi) 本格稼働</strong></td>
            <td>2026年末〜2027年</td>
            <td>XCB/CTNペアのレンディング、ステーブルコイン流動性プール展開によるオンチェーンTVL（預かり資産）の急拡大。</td>
          </tr>
          <tr>
            <td><strong>PingExchange 流動性拡張</strong></td>
            <td>継続展開</td>
            <td>P2P板取引に加え、自動マーケットメーカー（AMM）機能や法定通貨オンランプの強化による参加障壁の低下。</td>
          </tr>
        </tbody>
      </table>

      <h4>③ 2026〜2030年の市場価格シナリオ別予測</h4>
      <table class="article-table">
        <thead>
          <tr>
            <th>シナリオ</th>
            <th>想定価格帯 (USD / JPY)</th>
            <th>発生条件・カタリスト</th>
            <th>実現確率目安</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td><strong>基本シナリオ<br>(堅調な実需成長)</strong></td>
            <td><strong>$0.06 〜 $0.15</strong><br>(約 <strong>9円 〜 22円</strong>)</td>
            <td>
              ・流通量制約（約1億XCB固定）とマイナーの原価切り上がりが継続。<br>
              ・過去最高値（11.6円）を安定奪還し、DePIN実証ノードの拡大に伴い年率20〜30%のペースで価格レンジが上昇。
            </td>
            <td><span class="badge-online" style="background:#0284c7;">60% (最有力)</span></td>
          </tr>
          <tr>
            <td><strong>強気シナリオ<br>(エコシステム爆発期)</strong></td>
            <td><strong>$0.25 〜 $0.50</strong><br>(約 <strong>38円 〜 75円</strong>)</td>
            <td>
              ・大手国際暗号資産取引所（グローバルCEX）への上場・流動性供給。<br>
              ・欧州・アジア圏でのCorePass身元認証の大規模公的採用、DePINノードの世界的普及。
            </td>
            <td><span class="badge-online" style="background:#16a34a;">25%</span></td>
          </tr>
          <tr>
            <td><strong>保守・弱気シナリオ<br>(市況低迷・成長鈍化)</strong></td>
            <td><strong>$0.025 〜 $0.035</strong><br>(約 <strong>3.8円 〜 5.2円</strong>)</td>
            <td>
              ・暗号資産市場全体の長期低迷期、または新機能実装の遅延。<br>
              ・ただしマイナーの電気代損益分岐点（約4円）が強力な岩盤支持線として機能。
            </td>
            <td><span class="badge-online" style="background:#64748b;">15%</span></td>
          </tr>
        </tbody>
      </table>

      <h4>④ マイナーがとるべき実践的運用戦略</h4>
      <ol>
        <li><strong>「電気代のみ最小限換金、残りは中長期HODL」が鉄則:</strong><br>
        マイニングの最大の利点は「市場価格に関わらず毎日原価でXCBを積立取得できる」点にあります。日々の電気代相当分のみをPingExchangeで売却（または自費補填）し、残りのXCBは流通供給がタイト化する次期上昇サイクルまで手元で安全に保管するのが最も期待値の高い戦略です。</li>
        <li><strong>本NASアプリによる確定申告・取得原価の正確な保全:</strong><br>
        将来XCBの価値が上昇した際、過去の取得単価（時価）が明確でないと税務上過剰な課税リスクを負うことになります。本システムで保存している全4,215件の確定申告用CSVを定期的にバックアップしておくことが極めて重要です。</li>
        <li><strong>高効率CPU（Ryzen 9 7950X等）へのリグ更新:</strong><br>
        難易度が上昇し続ける局面では、ワットパフォーマンス（H/s per Watt）がマイナーの生存率を決定づけます。エコモード105W等の低電圧チューニングを徹底してください。</li>
      </ol>
    `

  },
  {
    id: "dev-update-2026",
    title: "Core Blockchain 最新開発動向・技術進捗レポート (2025-2026年最新版)",
    category: "technology",
    categoryName: "最新開発動向",
    date: "2026-09-12",
    summary: "gocore v2.2メジャーアップデート、スマートコントラクト標準群（CBC-20/CIP群）の策定、0G(SMS)完全オフライン送金TxMS、Ed448耐量子暗号基盤、Ylem言語、CoreMiner v0.19.89までの最新開発状況を徹底解説。",
    content: `
      <h3>1. 公式ノード「gocore」のメジャーアップデート（v2.2系統）</h3>
      <p>Core Blockchainのコアクライアントである<code>go-core</code>（gocore）は、2025年秋から2026年にかけて相次いでメジャーアップデート（v2.1.12 → v2.2.0 → v2.2.1 → v2.2.2）が実施され、Ethereumフォークからの完全な独自進化を遂げました。</p>
      
      <div class="article-alert info">
        <strong>💡 gocore v2.2の主な技術的マイルストーン</strong><br>
        <ul>
          <li><strong>スマートコントラクトAPI（<code>sc.*</code>）の全面実装:</strong> REVM（Rust EVM）ベースのCore Virtual Machine（CVM）とのネイティブ連携が完了し、<code>sc.getKYC</code>や<code>sc.call</code>などの専用名前空間が解放されました。</li>
          <li><strong>ネイティブトランザクション合成（<code>xcb.composeTransaction</code>）:</strong> 従来の複雑なオフチェーン署名ステップを簡素化し、ウォレット側でエナジー（Energy）計算と22バイトICANアドレス変換を自動処理可能に。</li>
          <li><strong>リアルタイムWSSサブスクリプション:</strong> ブロック生成・トランザクションイベントのWebSocketプッシュ通知が安定化。</li>
          <li><strong>Darwin ARM64（Apple Silicon M1〜M4）ネイティブ最適化:</strong> macOS環境でのノード同期速度が大幅に向上。</li>
        </ul>
      </div>

      <h3>2. CIP（Core Improvement Proposals）標準規格の大規模策定（2026年9月最新）</h3>
      <p>2026年9月4日、Core公式よりエコシステムのスマートコントラクトおよびトークン経済を標準化する<strong>包括的なCIP規格群（CIP-20〜CIP-4626）</strong>の最新定義が正式公開されました。これにより、Core Blockchain上でのDeFiやNFT、エンタープライズサービスの開発基盤が完全に整いました。</p>

      <table class="article-table">
        <thead>
          <tr>
            <th>規格番号</th>
            <th>標準名称</th>
            <th>概要と技術的意義</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td><strong>CIP-20 (CBC-20)</strong></td>
            <td>Core Blockchain Contract トークン標準</td>
            <td>ERC-20を代替するCoreネイティブのファンジブルトークン規格。22バイトICANアドレス（<code>cb...</code>）に完全対応し、Gasではなく「Energy」で手数料を消費する設計。</td>
          </tr>
          <tr>
            <td><strong>CIP-721</strong></td>
            <td>CoreNFT 非代替性トークン標準</td>
            <td>デジタルアートや実世界資産（RWA）、CorePass ID連携証明書を発行・移転するためのNFT標準。</td>
          </tr>
          <tr>
            <td><strong>CIP-712 / 2612 / 3009</strong></td>
            <td>エナジーレス（ガスレス）署名＆メタトランザクション</td>
            <td>ユーザーがXCB（エナジー）を事前保有していなくても、オフチェーンでのEIP-712互換暗号署名により第三者リレイヤーが手数料を代行支払できる仕組み。DAppsへの参入障壁をゼロ化。</td>
          </tr>
          <tr>
            <td><strong>CIP-4626</strong></td>
            <td>トークン化イールドVault標準</td>
            <td>DeFiの利回り・ステーキング資産の運用規格。単一の標準APIで利息計算や預け入れ・引き出しを統一。</td>
          </tr>
          <tr>
            <td><strong>CIP-104</strong></td>
            <td>分散型オンチェーン価格オラクル規格</td>
            <td>DEX（分散型取引所）やレンディングプロトコル向けに、PingExchange等のリアルタイム価格データをオンチェーンに安全に提供する標準インターフェース。</td>
          </tr>
          <tr>
            <td><strong>CIP-150 / 151</strong></td>
            <td>Key-Value メタデータ保存＆トークン追跡</td>
            <td>ブロックチェーン上に任意のキー・バリューデータを効率的かつ低コストに格納・追跡するストレージ拡張仕様。</td>
          </tr>
          <tr>
            <td><strong>CorePass KYC連携</strong></td>
            <td>分散型ID（DID）オンチェーン検証</td>
            <td><code>sc.getKYC()</code> APIを通じて、スマートコントラクト側がユーザーの身元確認状態（AML/CFT準拠）を個人情報を直接露出することなくオンチェーンで直接検証可能。</td>
          </tr>
        </tbody>
      </table>

      <h3>3. 画期的イノベーション：0G (SMS) オフライン送金プロトコル（TxMS）</h3>
      <p>Core Blockchainの開発陣が最も注力している独自技術の一つが、インターネット通信（4G/5G/Wi-Fi）が一切存在しない環境でもトランザクションを実行できる<strong>「0G (TxMS: Transaction via SMS) プロトコル」</strong>です。</p>

      <div class="article-alert success">
        <strong>📡 TxMS（SMSトランザクション）の仕組みと強み</strong><br>
        1. <strong>オフライン署名:</strong> スマートフォン端末（CorePass等）内でローカルにEd448秘密鍵を用いてトランザクションを生成・署名。<br>
        2. <strong>SMSペイロード化:</strong> 署名済みデータを極小バイト数に圧縮し、SMS（ショートメッセージ）の本文に格納。<br>
        3. <strong>ゲートウェイ中継:</strong> 世界各地に分散配置されたTxMSゲートウェイ局（<code>txms-server</code>）がSMSを受信し、Core Blockchainネットワークへ即座にブロードキャスト。<br>
        4. <strong>実用シーン:</strong> 地震・津波等の大災害による通信網遮断時、海底ケーブル切断、あるいはインターネットインフラが未整備の僻地・発展途上国でも金融送金が継続可能。
      </div>

      <h3>4. 224ビット耐量子暗号（Ed448-Goldilocks）と独自言語「Ylem」</h3>
      <p>BitcoinやEthereumなどの主要ブロックチェーンが採用している楕円曲線暗号<code>secp256k1</code>（128ビットセキュリティ水準）に対し、Core Blockchainは極めて強力な<strong>Ed448-Goldilocks曲線（224ビットセキュリティ水準）</strong>をネイティブ採用しています。</p>
      <ul>
        <li><strong>耐量子計算機性能:</strong> Shorのアルゴリズムを用いた量子コンピュータによる攻撃に対しても、従来の暗号資産より遥かに高い安全マージンを確保。</li>
        <li><strong>SHAKE256ハッシュ関数:</strong> SHA-256ではなく可変長ハッシュ関数SHAKE256を全面採用。アドレス生成やブロックダイジェストに活用。</li>
        <li><strong>Ylem（イーレム）言語コンパイラ:</strong> Solidityをベースにしつつ、Ed448署名検証やICANアドレス、エナジー体系に特化した独自スマートコントラクト言語「Ylem」の開発が加速（2026年最新版）。</li>
      </ul>

      <h3>5. マイニング動向（CoreMiner v0.19.89 と DePIN連携）</h3>
      <p>マイナーにとって最も重要な採掘ソフトウェア・アルゴリズム面でも重要な転換が行われています。</p>

      <table class="article-table">
        <thead>
          <tr>
            <th>項目</th>
            <th>以前の仕様</th>
            <th>最新の仕様（2025-2026）</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td><strong>RPCプロトコル</strong></td>
            <td><code>eth_getWork</code> (Ethereum互換)</td>
            <td><strong><code>xcb_getWork</code></strong> (Core完全ネイティブ仕様に完全統一)</td>
          </tr>
          <tr>
            <td><strong>マイニングソフト</strong></td>
            <td>coreminer v0.19.7x / 0.19.85</td>
            <td><strong>coreminer v0.19.89</strong> (最新RandomYキャッシュ・マルチプラットフォーム最適化)</td>
          </tr>
          <tr>
            <td><strong>採掘アルゴリズム</strong></td>
            <td>RandomY (初期実装)</td>
            <td><strong>RandomY (RandomX 1.2.1準拠版)</strong>: メモリ帯域の最適化とCPU負荷の均等化</td>
          </tr>
          <tr>
            <td><strong>ハードウェア展開</strong></td>
            <td>自作PC / サーバーCPUのみ</td>
            <td><strong>ORB i2（8W超低消費電力IoTノード）</strong>、LunaMesh分散無線ネットワークとの連携</td>
          </tr>
        </tbody>
      </table>


      <h3>6. YouTube & Telegram 公式発表（実利用・決済エコシステムの最新進捗）</h3>
      <p>CoDeTechおよびCore Blockchain開発陣は、公式YouTubeチャンネル（<code>@CoDeTechCC</code>）の独自ドキュメンタリーシリーズ<strong>「Core Chronicle」</strong>や公式Telegramアナウンス（<code>@CoDeTechCC</code>）にて、2026年7月〜8月に相次いで画期的な実利用フェーズへの移行を発表しました。</p>

      <div class="article-alert success">
        <strong>📺 YouTube最新エピソード「Core Chronicle #13」：ソーシャルID送金の実演</strong><br>
        2026年7月28日、CoDeTech CEO兼Core Blockchain共同創業者であるOckert Loubser氏により、<strong>「CoreID × Wall Money × Core Settlement Network」</strong>による新送金インフラが公開されました。<br>
        <ul>
          <li><strong>ウォレットアドレス・銀行口座番号が不要:</strong> X（旧Twitter）やFediverse（Mastodon等）のSNSアカウント宛てに、直接<strong>XCB、CTN、USDX、EURX、CNYX、THBX</strong>などのデジタル資産をワンクリックで送金・チップ支援可能に。</li>
          <li>クリエイターやコミュニティが第三者決済サービスを介さず、普段のSNSアカウントそのものを直接受取口座（決済エンドポイント）として利用できます。</li>
        </ul>
      </div>

      <table class="article-table">
        <thead>
          <tr>
            <th>発表日付</th>
            <th>公開チャネル</th>
            <th>発表内容と実用上の意義</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td><strong>2026年7月21日</strong></td>
            <td>公式Telegram</td>
            <td><strong>4大法定通貨ステーブルコイン（USDX, EURX, CNYX, THBX）正式デプロイ</strong><br>米ドル・ユーロ・中国人民元・タイバーツにペッグされた公式ステーブルトークンがCore Blockchainメインネット上に稼働。</td>
          </tr>
          <tr>
            <td><strong>2026年7月</strong></td>
            <td>YouTube (CC11 / 11.5)</td>
            <td><strong>「CorePay」EC決済ゲートウェイ公開（WooCommerce / Shopify連携）</strong><br>世界中のWordPressやShopifyオンラインストアへCore Blockchain決済（XCB/CTN）を導入可能なマーチャント向けプラグインが正式稼働。</td>
          </tr>
          <tr>
            <td><strong>2026年7月12日</strong></td>
            <td>公式Shorts動画</td>
            <td><strong>実店舗リアル決済デモ（CorePass → Wall Money → バーチャルカード）</strong><br>CorePassからWall Moneyへ暗号資産を移転し、即座にバーチャルVisaカードへチャージしてスーパーマーケットで食料品を直接購入・決済する完全実利用フローを実演。</td>
          </tr>
          <tr>
            <td><strong>2026年7月8日</strong></td>
            <td>公式Shorts動画</td>
            <td><strong>CorePass KYB（法人確認）＆ MoneyX 準備金監査基盤</strong><br>企業向けの身元確認（KYB）機能が実稼働。100%検証可能な法定通貨準備金裏付けを持つステーブル基盤「MoneyX」を統合。</td>
          </tr>
          <tr>
            <td><strong>2026年上半期</strong></td>
            <td>YouTube (CC8 全4話)</td>
            <td><strong>「Core Tokenizer」RWA（実世界資産）トークン化シリーズ</strong><br>不動産・金・証券などの現実資産をCore Blockchain上で安全にトークン化・発行するための専用プラットフォーム構想と実装。</td>
          </tr>
        </tbody>
      </table>

      <h4>💡 まとめ：エコシステムの成熟とマイナーへの影響</h4>
      <p>Core Blockchainは、単なる「CPUで採掘できるPoWコイン」の域を脱し、<strong>「耐量子暗号」「オフライン0G送金」「分散型身元認証（CorePass）」「包括的スマートコントラクトDeFi基盤（CIP群）」</strong>を兼ね備えた第3世代の独立レイヤー1ブロックチェーンへと着実に進化しています。</p>
      <p>マイナーにとっては、今後CBC-20トークンやDAppsのオンチェーントランザクションが増加することにより、ブロック報酬に加えてエナジー消費（取引手数料）としてのXCB還元が期待できる構造へとステップアップしています。</p>
    `
  },
  {
    id: "enterprise-adoption-arax-audit",
    title: "Core Blockchainの企業・国家採用動向 ＆ 米上場企業ARAX (ARAT) の信用・財務実態徹底検証",
    category: "technology",
    categoryName: "企業採用・信用調査",
    date: "2026-09-12",
    summary: "EU環境規制（Euro 7/デジタル製品パスポート）、NATO DIANA、スロバキア/スイス公的セクター、EC決済等の採用・検討状況と、SEC提出書類（10-K）に基づく米上場企業ARAX Holdings Corpの財務・信用・実績の客観的評価レポート。",
    content: `
      <h3>1. 調査の背景と目的</h3>
      <p>暗号資産プロジェクトにおいて「大企業が採用」「国家が提携」といった誇大広告は日常茶飯事ですが、Core Blockchain（XCB）および開発元CoDeTech（スロバキア）、提携上場企業ARAX Holdings Corp（米国）の実態はどうなのでしょうか？</p>
      <p>本レポートでは、<strong>欧州連合（EU）の公式法規制フレームワーク、米証券取引委員会（SEC）への公式提出書類（Form 10-K）、および公式開示データ</strong>に基づき、企業・国家の採用検討状況と「米上場企業ARAX」の信用・実績を客観的・中立的に検証します。</p>

      <h3>2. 国・公的機関・国際組織との関わり・採用検討状況</h3>
      <p>Core Blockchainは、投機的なミームコイン等とは根本的に異なり、当初から<strong>「スイス・EUの厳格な法令（GDPR / eIDAS / MiCA）に完全準拠したエンタープライズ・公共インフラ」</strong>として設計されています。</p>

      <table class="article-table">
        <thead>
          <tr>
            <th>国・機関・規制</th>
            <th>採用・検討・準拠の内容</th>
            <th>技術的・実用的な意義</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td><strong>欧州連合 (EU)<br>デジタル製品パスポート (DPP)</strong></td>
            <td>EU持続可能製品エコデザイン規則（ESPR）準拠のオンチェーン製品履歴管理</td>
            <td>EU全域で製造・流通する全製品の原材料、耐久性、カーボンフットプリントをブロックチェーンに記録し、QRコードやRFIDで誰でも追跡可能にするサプライチェーン基盤（ARAX BaaPにて実証）。</td>
          </tr>
          <tr>
            <td><strong>欧州連合 (EU)<br>Euro 7 排ガス・環境規制</strong></td>
            <td>環境車両パスポート（Environmental Vehicle Passport / EVP）</td>
            <td>自動車メーカーや物流フリート事業者向けに、Euro 7排ガス基準やEVバッテリーの健康状態をオンチェーンでリアルタイム監視・証明する公式対応ソリューション。</td>
          </tr>
          <tr>
            <td><strong>国際防衛機構<br>NATO DIANA</strong></td>
            <td>軍民両用（デュアルユース）の通信・危機管理レジリエンス技術</td>
            <td>有事・大規模災害でネット回線が途絶した環境でも動作する「0G（SMS送金・通信 TxMS）」「自律型ドローン・無線メッシュ（LunaMesh）」「224ビット耐量子暗号（Ed448）」が、NATOの公募技術要件（レジリエントな分散インフラ）に合致し、実証・提案を展開中。</td>
          </tr>
          <tr>
            <td><strong>中欧公的セクター<br>(スロバキア・スイス)</strong></td>
            <td>元国会議員（ファウンダー）およびFINMA法規制顧問の参画</td>
            <td>CoDeTech共同創業者のRastislav Vašička氏はスロバキア国民議会（国会）元議員。またスイス暗号資産法・FINMA規制の第一人者Lars Schlichting弁護士（Kellerhals Carrard）が法律顧問を務め、スイス・ルガーノ市等でP2P通信実証を実施。</td>
          </tr>
          <tr>
            <td><strong>新興国・途上国<br>(アフリカ・タイ等)</strong></td>
            <td>金融包摂（Unbanked層支援）＆ ステーブルコイン</td>
            <td>銀行口座を持たない人々へ通常セルラーSMSだけで金融サービスを提供する0G決済を展開。また2026年7月にはタイバーツ連動ステーブルコイン「THBX」を含む4通貨がメインネットにデプロイ。</td>
          </tr>
        </tbody>
      </table>

      <h3>3. 民間企業・商用プラットフォームでの採用・統合事例</h3>
      <ul>
        <li><strong>WooCommerce / WordPress（世界最大のEC基盤）:</strong><br>
        公式決済プラグイン「<strong>CorePay</strong>」がリリースされ、世界中のWordPressオンラインストアでXCBおよびCoreToken（CTN）による暗号資産決済を直接導入可能に。</li>
        <li><strong>Shopify（世界第2位のECプラットフォーム）:</strong><br>
        ArkおよびShopifyストアとの連携（Core Chronicle #8 Ep.1）を通じて、コマース決済およびRWA（実世界資産）トークン決済のインフラ統合が進行。</li>
        <li><strong>The Nemesis（Web3メタバースプラットフォーム）:</strong><br>
        提携・買収に伴い、数万人規模のメタバースプラットフォーム内のユーザー認証に<strong>CorePass（分散型ID）</strong>を全面統合。LunaMeshを通じたP2Pストリーミング配信の実証を完了。</li>
        <li><strong>Wall Money（実店舗決済ネオバンク）:</strong><br>
        CorePassと連動し、暗号資産を即座に国際ブランド（Visa等のバーチャルデビットカード）へチャージして、スーパーマーケットなどの実店舗レジで食品購入・決済する完全実利用オフレールを公開。</li>
      </ul>

      <h3>4. 米上場企業「ARAX Holdings Corp (ARAT)」の信用と実績の客観的検証</h3>
      <p>コミュニティ内で頻繁に言及される「米上場企業ARAX」について、<strong>米証券取引委員会（SEC）への公式提出書類（Form 10-K 年次報告書 / CIK: 0001566243）</strong>から、その財務・信用・実態を検証しました。</p>

      <div class="article-alert info">
        <strong>💡 結論：「米上場企業」だが、巨大企業ではなく「初期スタートアップ（マイクロキャップ）」</strong><br>
        NASDAQやNYSEのような本則主要市場ではなく、米国の新興・中小企業向け<strong>店頭市場「OTCQB」</strong>に上場しています。年次監査（10-K）や四半期開示（10-Q）を定期提出している正規の上場企業ですが、規模としては初期ベンチャーです。
      </div>

      <table class="article-table">
        <thead>
          <tr>
            <th>項目</th>
            <th>SEC 10-K 公開数値（直近報告）</th>
            <th>実態と客観的評価</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td><strong>上場市場</strong></td>
            <td><strong>米店頭市場 OTCQB</strong> (ティッカー: ARAT)</td>
            <td>NASDAQ等と比べ上場基準が緩やかな店頭市場（ペニーストック）。</td>
          </tr>
          <tr>
            <td><strong>SEC登録状況</strong></td>
            <td>CIK: 0001566243 (正規登録)</td>
            <td>米国の会計監査法人による監査を受けており、財務情報は完全公開。</td>
          </tr>
          <tr>
            <td><strong>年間売上高</strong></td>
            <td>約 <strong>90.9万ドル</strong> (約 <strong>1.3億〜1.4億円</strong>)</td>
            <td>中小企業・初期スタートアップ規模の売上高。</td>
          </tr>
          <tr>
            <td><strong>純損益</strong></td>
            <td>約 <strong>658万ドルの赤字</strong></td>
            <td>先行開発投資・買収・管理費用による大幅な赤字フェーズ。</td>
          </tr>
          <tr>
            <td><strong>総資産</strong></td>
            <td>約 <strong>216万ドル</strong> (約 <strong>3.2億円</strong>)</td>
            <td>資産規模は非常にコンパクト。</td>
          </tr>
          <tr>
            <td><strong>金融ライセンス</strong></td>
            <td>スイス「Cilandro」エンティティで取得</td>
            <td>欧州でのCBDC・フィンテック提供の法的基盤を確保。</td>
          </tr>
          <tr>
            <td><strong>Core Blockchainとの契約</strong></td>
            <td>10-Kに明記（独占的SaaS/BaaP開発）</td>
            <td>「Core Blockchain上で独占的に動作するソフトウェアを開発し収益化する」とSECに正式宣誓。</td>
          </tr>
        </tbody>
      </table>

      <h4>⚖️ 信用のプラス面 vs 注意すべきリスク</h4>
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin: 16px 0;">
        <div style="padding: 12px; border-radius: 8px; background: rgba(34, 197, 94, 0.08); border: 1px solid rgba(34, 197, 94, 0.2);">
          <strong style="color: #16a34a;">🟢 信用のプラス面（評価できる点）</strong>
          <ul style="margin: 8px 0 0 16px; font-size: 13.5px; padding: 0;">
            <li><strong>SECへの法定開示と公認監査:</strong> 財務諸表や役員、契約関係をすべてSEC EDGARに公開しており、完全な透明性がある。</li>
            <li><strong>Core Blockchainを公式事業の核に位置づけ:</strong> 単なる提携発表ではなく、米連邦当局へ提出する公式報告書でCore技術を核に据えている。</li>
            <li><strong>スイス金融ライセンス保有:</strong> 欧州の厳格な規制下で正規のフィンテック事業基盤を持つ。</li>
          </ul>
        </div>
        <div style="padding: 12px; border-radius: 8px; background: rgba(239, 68, 68, 0.08); border: 1px solid rgba(239, 68, 68, 0.2);">
          <strong style="color: #dc2626;">🔴 注意すべきリスク（過大評価禁物）</strong>
          <ul style="margin: 8px 0 0 16px; font-size: 13.5px; padding: 0;">
            <li><strong>「大企業」ではない:</strong> 年商1億円強、数億円の赤字を抱えるマイクロキャップであり、AppleやCoinbase等とは次元が異なる。</li>
            <li><strong>OTCQB特有の流動性リスク:</strong> 株式の売買高が少なく、株価ボラティリティが極めて高い。</li>
            <li><strong>実需はまだ立ち上げ段階:</strong> プロダクトはリリースされているが、世界中で爆発的に利益を上げている段階ではない。</li>
          </ul>
        </div>
      </div>

      <h3>5. 総括：マイナー・投資家が持つべき健全な視点</h3>
      <p>Core BlockchainとARAXの関係は、<strong>「スイス・EUの規制に準拠した最先端の分散技術（Core/CoDeTech）」を「米国の公開企業（ARAX）を通じて正規の資本市場・企業DXへと繋ぐパイプ」</strong>として機能しています。</p>
      <p>「米上場企業」という言葉の響きだけで過度な幻想を抱くのではなく、<strong>「SECの監査基準を満たした透明な初期ベンチャーが、EUの環境規制（Euro 7/DPP）やNATO系公募、EC決済という非常に堅実な実需に向けて製品を投入している」</strong>という客観的な事実に基づき、オンチェーンでの実利用・トランザクション推移を冷静にウォッチしていくことが最も賢明なスタンスです。</p>
    `
  },
  {
    id: "comparative-analysis-enterprise-blockchains",
    title: "エンタープライズ・実需型ブロックチェーン徹底比較：VeChain / Energy Web / Hedera / IOTA / Quant と対比する Core Blockchain の独自ポジション",
    category: "technology",
    categoryName: "市場・競合比較分析",
    date: "2026-09-12",
    summary: "VeChain(VET)、Energy Web(EWT)、Hedera(HBAR)、IOTA、Quant(QNT)など、企業・公的実需を重視する主要プロジェクトとCore Blockchainの「企業構成・合意形成・EU規制対応・耐量子・通信インフラ」を徹底対比。Coreが持つ独自の差別化要因と中長期展望を完全解説。",
    content: `
      <h3>1. 暗号資産市場の二大潮流：「個人投機型」vs「企業・法規制主導型」</h3>
      <p>暗号資産（仮想通貨）の世界は、大きく分けると2つの全く異なる思想と市場に二極化しています。</p>
      <ul>
        <li><strong>① 個人投機・DeFi・ミームコイン型（Solana, 各種L2, ドージコイン等）:</strong><br>
        短期的な価格急騰やエアドロップ、SNSでのバズによって個人投資家が熱狂する市場。爆発的な流動性が生まれる一方、規制当局（SEC等）からの摘発リスクや、実需の持続性に課題を抱えます。</li>
        <li><strong>② 企業・法規制主導型（B2B / B2G実需型）:</strong><br>
        スイスや欧州連合（EU）の厳格な法律（GDPR / eIDAS / MiCA）や国際標準に完全準拠し、企業のサプライチェーン、製品パスポート、公的インフラとして採用を目指す市場。</li>
      </ul>
      <p><strong>Core Blockchain（XCB）は完全に「後者（企業・法規制主導型）」に位置づけられるプロジェクト</strong>です。本稿では、類似の思想・企業構成を持つ世界の主要エンタープライズブロックチェーンとCoreを徹底対比し、その強みと独自ポジションを浮き彫りにします。</p>

      <h3>2. 6大プロジェクトの基本スペック＆企業構成 徹底比較表</h3>
      <table class="article-table">
        <thead>
          <tr>
            <th>プロジェクト名</th>
            <th>開発・運営母体</th>
            <th>企業構成・資本市場ビークル</th>
            <th>合意形成 (Consensus)</th>
            <th>強みとする実需領域</th>
            <th>主な法的・規制準拠</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td><strong>Core Blockchain<br>(XCB)</strong></td>
            <td>CoDeTech (スロバキア)<br>Core Foundation</td>
            <td><strong>ARAX Holdings Corp</strong><br>(米店頭市場 OTCQB: ARAT)</td>
            <td><strong>PoDE (Ouroboros-X)</strong><br>耐ASIC分散型PoW (CPU採掘)</td>
            <td>EU製品パスポート(DPP)、Euro 7(EVP)、0G(SMS送金)、分散ID(CorePass)、EC決済</td>
            <td>EU GDPR / eIDAS / MiCA準拠、米SEC開示、スイス金融ライセンス</td>
          </tr>
          <tr>
            <td><strong>VeChain<br>(VET)</strong></td>
            <td>VeChain Foundation<br>(シンガポール/欧州)</td>
            <td><strong>DNV</strong> (世界的大手第三者認証機関)<br><strong>PwC</strong> (4大監査法人)</td>
            <td><strong>PoA (Proof of Authority)</strong><br>101の公認機関ノードによる認証</td>
            <td>サプライチェーン追跡、食品安全、カーボンフットプリント、高級品真贋証明</td>
            <td>中国国家規格、欧州サプライチェーン法</td>
          </tr>
          <tr>
            <td><strong>Energy Web<br>(EWT)</strong></td>
            <td>Energy Web Foundation<br>(スイス・ツーク)</td>
            <td><strong>Energy Web コンソーシアム</strong><br>(Shell, Volkswagen, TotalEnergies等)</td>
            <td><strong>PoA (Proof of Authority)</strong><br>大手電力・自動車企業による運営</td>
            <td>EVバッテリーパスポート、再生可能エネルギー証明、電力系統グリッド調整</td>
            <td>EU電池指令、EUグリーンディール規制、スイス財団法</td>
          </tr>
          <tr>
            <td><strong>Hedera<br>(HBAR)</strong></td>
            <td>Swirlds (米開発企業)<br>Hedera Foundation</td>
            <td><strong>Hedera Governing Council</strong><br>(Google, IBM, Dell, 野村HD等30社以上)</td>
            <td><strong>Hashgraph</strong><br>(特許取得済みの非同期ビザンチン耐性 DAG)</td>
            <td>エンタープライズデータ保全、銀行間決済、Web3メタバース</td>
            <td>米国法規制、グローバル上場企業コンプライアンス</td>
          </tr>
          <tr>
            <td><strong>IOTA<br>(IOTA)</strong></td>
            <td>IOTA Foundation<br>(ドイツ・ベルリン公的財団)</td>
            <td><strong>EU EBSI</strong> (欧州ブロックチェーン基盤)<br>産学官パートナーシップ</td>
            <td><strong>Tangle (DAG)</strong><br>マイナー不在・手数料ゼロ構造</td>
            <td>IoTデバイス間通信、欧州公的サプライチェーン、スマートシティ</td>
            <td>EU公的調達基準、ドイツ財団法</td>
          </tr>
          <tr>
            <td><strong>Quant Network<br>(QNT)</strong></td>
            <td>Quant Network Ltd<br>(英国ロンドン)</td>
            <td><strong>SIA / Nexi</strong> (欧州中央銀行金融中継網)<br>LACChain (米州開発銀行)</td>
            <td><strong>Overledger</strong><br>(複数ブロックチェーン間のOS/API中継)</td>
            <td>中央銀行デジタル通貨 (CBDC)、銀行間送金、国際相互運用</td>
            <td>ISO / TC 307 国際標準規格、英国FCA金融規制</td>
          </tr>
        </tbody>
      </table>

      <h3>3. 各プロジェクトの詳細特徴とCore Blockchainとの対比</h3>

      <h4>① VeChain (VET) vs Core：サプライチェーンと製品パスポートの競合・親和性</h4>
      <p>VeChainは「ブロックチェーンによる製品トレーサビリティ」の先駆者であり、ウォルマート・チャイナやBMWなどとの実績を誇ります。</p>
      <ul>
        <li><strong>類似点:</strong> Core（ARAX）が推進する「EUデジタル製品パスポート（DPP）」やサプライチェーン追跡は、VeChainが切り拓いた市場と完全に重なります。</li>
        <li><strong>相違点とCoreの強み:</strong> VeChainは101の公認組織がブロックを生成する「PoA（権限証明）」を採用しており、準中央集権的です。一方、Coreは<strong>一般のCPUマイナーが支える真のPoW（PoDE）</strong>であり、ネットワークの改ざん耐性と中立性において勝ります。また、Coreは最初から<strong>224ビット耐量子暗号（Ed448）</strong>を組み込んでいます。</li>
      </ul>

      <h4>② Energy Web (EWT) vs Core：欧州自動車・環境規制へのアプローチ</h4>
      <p>Energy Webはスイス拠点で、フォルクスワーゲンや欧州エネルギー大手を巻き込み、EVバッテリーのライフサイクル追跡（バッテリーパスポート）をリードしています。</p>
      <ul>
        <li><strong>類似点:</strong> Core（ARAX）がSEC提出書類に掲げている「EU Euro 7 車両環境パスポート（EVP）」とターゲット規制が酷似しています。ともにスイスの法的枠組みを活用しています。</li>
        <li><strong>相違点とCoreの強み:</strong> Energy Webが「エネルギー・自動車分野」に特化した業界専用チェーンであるのに対し、Coreは<strong>汎用スマートコントラクト（CVM / CBC-20）、分散型ID（CorePass）、実店舗デビットカード決済（Wall Money）、EC決済（CorePay）まで網羅した包括的なL1エコシステム</strong>を自前で持っています。</li>
      </ul>

      <h4>③ Hedera (HBAR) vs Core：エンタープライズ・ガバナンスの思想</h4>
      <p>Hederaは、GoogleやIBM、ボーイングなどの世界的巨大上場企業連合が直接ノードを運営することで、企業の圧倒的信頼を獲得しています。</p>
      <ul>
        <li><strong>類似点:</strong> 「法的に身元が明確な正規法人が商用化と責任を担う」というエンタープライズ重視の姿勢。</li>
        <li><strong>相違点とCoreの強み:</strong> Hederaは「超大企業による寡占評議会」であり、一般ユーザーがマイナーとしてネットワークの合意形成に参加することはできません。Coreは**「米上場企業ARAXが商用窓口を担いつつ、合意形成は世界中の自律的な分散マイナー（PoDE）が行う」**という、資本主義とWeb3非中央集権のハイブリッド構造を実現しています。</li>
      </ul>

      <h3>4. Core Blockchainだけの「3大差別化要因（USP）」</h3>
      <p>VeChain、Hedera、Energy Webなどの強力な先行プロジェクトと比較した際、<strong>Core Blockchainだけが持つ決定的な強み</strong>は以下の3点です：</p>

      <div class="article-alert success">
        <strong>🚀 Core Blockchain独自の3大優位性</strong><br>
        <ol>
          <li><strong>真の非中央集権 PoW（PoDE: Proof of Distributed Efficiency）:</strong><br>
          競合の多く（VeChain, Energy Web, Hedera）はPoAや限られた評議会による「許可型（Permissioned）」であり、中央集権化の批判を免れません。CoreはASICを排除したCPU PoWにより、誰でも自宅から参加できる分散性を維持しています。</li>
          <li><strong>0G (TxMS) ＆ LunaMesh による「ネット遮断・有事レジリエンス」:</strong><br>
          インターネット（4G/5G/Wi-Fi）が途絶した環境でも、<strong>通常のセルラーSMSだけで暗号送金が完結する「0Gプロトコル」や、ドローン間自律通信「LunaMesh」</strong>は他チェーンには一切存在しません。これがNATO DIANA（防衛イノベーション）の公募要件に合致する最大の理由です。</li>
          <li><strong>224ビット耐量子暗号（Ed448-Goldilocks）のネイティブ実装:</strong><br>
          BitcoinやEthereum、Hedera、VeChainに至るまで、大半のチェーンは標準の「secp256k1（128ビットセキュリティ）」を採用しています。Coreは将来の量子コンピュータ脅威を見据え、当初から224ビットセキュリティ水準のEd448とSHAKE256ハッシュで設計されています。</li>
        </ol>
      </div>

      <h3>5. 投資家・マイナーが知っておくべき「時間軸」と「成熟度」の現実</h3>
      <p>これらの比較から導き出される、マイナーにとって最も重要な教訓は**「時間軸の捉え方」**です。</p>
      <ul>
        <li><strong>先行組（VeChainやHedera）も5〜7年の歳月を要した:</strong><br>
        企業向け・国家規制対応のブロックチェーンは、PoC（概念実証）から法制化、企業の基幹システム導入まで2〜5年単位の長い実証サイクルを必要とします。VeChainも2015年の発足から実社会での本格稼働まで何年もかかりました。</li>
        <li><strong>Core Blockchainの現在地（2025〜2026年）:</strong><br>
        2022年のジェネシスから2025年までは「プロトコルの完成・耐量子暗号・ノード安定化（gocore v2.2）」のインフラ構築フェーズでした。そして<strong>2026年現在、CIP標準策定、4大ステーブルコインデプロイ、CorePay EC決済、ARAX BaaPによる実証という「商用化・実需導入の初期フェーズ」</strong>へと移行したばかりです。</li>
      </ul>

      <h4>💡 結論：Coreマイニングの本質的価値</h4>
      <p>Core Blockchainは、短期的な市場の流行を追うコインではなく、<strong>「EU環境法制や有事レジリエンス通信という、将来確実に必要とされるインフラ実需を狙い撃ちした堅牢なレイヤー1」</strong>です。</p>
      <p>日々のマイニングで得られるXCBは、将来こうした企業DXやオンチェーントランザクションが本格拡大した際に「必須のエナジー（手数料資源）」として消費される基礎資産となります。目先の市場価格のノイズに惑わされず、着実に原価でXCBを蓄積していくことが最も理にかなった長期戦略と言えます。</p>
    `
  }
];
