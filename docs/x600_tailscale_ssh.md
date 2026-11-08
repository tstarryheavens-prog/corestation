# X600 を tailnet に入れて Hub から実測するための手順（2026-11-08 実測ベース）

## 今の実測（このファイルを書いた時点で確認した事実）
- `192.168.2.13`（X600）: 2026-11-08 18:37 JST 時点では TCP 445 / 3389 到達・latency 5.8 ms。**20:1x JST には ping 100%  loss、445 / 3389 / 22 すべて応答なし**（電源 OFF またはスリープ）。
- tailnet (`tail8fffd8.ts.net`) の既知ノード: `kazukimacbook-air` `bc250` `bc250-1` `z790-al` `z790`(windows, offline 1日) `z690`(windows, offline 15日) `z690-wsl` `tokage` `muse` `iphone182`。**X600 というノードは存在しない**＝X600 は Tailscale 未導入。
- `ssh kazuki@100.86.91.70`（z790-al）は現状 `tailnet policy does not permit you to SSH as user "kazuki"` で拒否される → **tailnet policy に SSH 許可が必要です**。

## 1) X600 側（X600 を電源 ON にして、PowerShell を「管理者として実行」）
```powershell
cd C:\corestation
powershell -NoProfile -ExecutionPolicy Bypass -File .\setup_x600.ps1
```
`setup_x600.ps1` がやること（電源操作・再起動・マイナーの設定変更はしません）:
1. Tailscale が無ければ `https://pkgs.tailscale.com/stable/tailscale-setup-latest.exe` を取得してサイレントインストール
2. `tailscale up --ssh --hostname=X600`（ブラウザで自分の tailnet アカウントにログイン）
3. `worker_reporter.ps1` を `C:\corestation\` に置き、初回実行して `C:\corestation\corestation_metrics.json` を書く
4. `schtasks` で 5 分毎の定期実行（SYSTEM アカウント）を登録

ファイルがまだ X600 に無い場合は、X600 上で:
```powershell
new-item -ItemType Directory -Force C:\corestation | Out-Null
iwr https://corestation.pages.dev/tools/setup_x600.ps1 -OutFile C:\corestation\setup_x600.ps1
iwr https://corestation.pages.dev/tools/worker_reporter.ps1 -OutFile C:\corestation\worker_reporter.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File C:\corestation\setup_x600.ps1
```

## 2) Tailscale 管理コンソール（Access controls）に足す許可
`whoami`（setup スクリプトが印字する）で **X600 の Windows ユーザー名**を確認し、`users` にその名前を入れる。

```json
{
  "acls": [
    { "action": "accept", "src": ["100.68.123.120", "100.86.91.70"], "dst": ["100.x.x.x:22"] }
  ],
  "ssh": [
    {
      "action": "accept",
      "src": ["t.starryheavens@example.com"],
      "dst": ["100.x.x.x"],
      "users": ["<X600 の Windows ユーザー名>", "kazuki"]
    }
  ]
}
```
- `100.x.x.x` は setup 後に印字される X600 の tailnet IP（または `tag:` を付けても良い）。
- z790-al への SSH を通すなら `dst` に `100.86.91.70:22` / `100.86.91.70` も追加する。
- port 22 への `acls` と `ssh` の**両方**がないと Tailscale SSH は通らない。

## 3) Hub 側（MacBook / z790-al）で確認・取り込み
```bash
cd /Volumes/Docker/CoreGeeksEXp
bash scripts/x600_ssh_check.sh      # tailnet に X600 が出たか / SSH 22 が開いたかを実測
bash scripts/x600_pull_metrics.sh   # C:\corestation\corestation_metrics.json を data/machine_metrics/X600.json へ
python3 scripts/dashboard_live.py --deploy   # ダッシュボードに反映
```
`dashboard_live.py` は `data/machine_metrics/*.json` を読み、X600 ノードの `hashrate` / `temperature` / `power` を**実測分だけ**埋めます（無い項目は null のまま。0 や推算は入れません）。

### 代替経路（Tailscale 不要・ACL 変更不要）
X600 が NAS 共有に書き込めるなら、tailnet を使わず共有へ直接メトリクスを出せます:
```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File C:\corestation\setup_x600.ps1 -ShareOutFile "\\192.168.2.100\Docker\CoreGeeksEXp\data\machine_metrics\X600.json"
```
注意: 既定の定期実行は **SYSTEM アカウント**で動くため、認証の要る SMB 共有には書けません。共有に書く場合は `-ShareOutFile` を使う前にその共有がゲスト書き込み可か確認するか、ログオンユーザーで実行してください（その場合は `schtasks /ru ""` ではなくログオンユーザー登録）。

## worker_reporter.ps1 が測れるもの / 測れないもの
| 測れる（実測） | 方法 |
|---|---|
| マイナープロセスの有無・worker 名・接続プール | `Win32_Process` のコマンドライン |
| H/s | マイナーのログファイル末尾 400 行を正規表現で抽出（無ければ null） |
| NVIDIA GPU の温度 / 使用率 / 消費電力 / クロック | `nvidia-smi --query-gpu=...` |
| CPU 使用率 / コア数 | `Win32_Processor` |
| stratum セッション数（プールに張っている TCP） | `Get-NetTCPConnection` |
| プールの名前解決と `:8008` の TCP OPEN | `Resolve-DnsName` + TcpClient |
| 稼働時間 | `Win32_OperatingSystem.LastBootUpTime` |
| CPU / マザーボードの温度（WMI thermal zone） | `MSAcpi_ThermalZoneTemperature` を `/10 - 273.15` で変換（この thermal zone を持たないマシンでは null） |
| 測れない | AMD GPU の温度・電力（この方法では取れない）、CPU パッケージ電力（WMI thermal zone が無いマシンでは null）。正確に測るなら LibreHardwareMonitor / HWiNFO 側が必要 |

## 電源が入っていない時の起動（WoL）
- collector は毎巡回で `arp -n 192.168.2.13` を読み、MAC が取れた瞬間 `data/x600_mac.txt` に控えて `live_state.json` の X600 ノードに `mac` / `wolReady` として出す（取れていない間は `mac: null`、カードには `WoL: MAC 未取得`）。
- 実測注意（2026-11-08 23:1x JST）: `route -n get 192.168.2.13` は `interface: en0`（この Mac は 192.168.2.10/24）なのに `arp -n 192.168.2.13` は `no entry`（TCP 445/3389/135/139 は OPEN・6-7 ms、137/udp は応答なし）。**この Mac の ARP 表からは MAC を確定できない**（macOS の ARP 表に出てこない）。確実な源はリグ側の報告で、`worker_reporter.ps1` は `Get-NetAdapter` / `Get-NetIPAddress` から MAC と IPv4 を実測して `macAddresses` / `lanIpv4` として出す。これで (1) MAC が取れて WoL が使えるようになり (2) 「192.168.2.13 = このマシン」もリグ実測で確定する（collector は `lanIdentityVerified` として記録し、ダッシュボードに `IP 照合` として出す）。
- 控えた後は `bash scripts/x600_wake.sh --wake`（magic packet を 192.168.2.255:7 / :9 と 255.255.255.255 へ送信、最大 60 秒応答を待つ）。BIOS / OS 側で Wake on LAN が有効なことが条件。

