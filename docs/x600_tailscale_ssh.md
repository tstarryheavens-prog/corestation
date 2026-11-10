# X600 を実測対象にする手順（2026-11-10 実測ベース・訂正版）

## 訂正: Windows では Tailscale SSH が使えない

`tailscale set --ssh` は X600 で次のように拒否されました（2026-11-10 実測）:

```
The Tailscale SSH server is not supported on windows.
https://tailscale.com/kb/1208/tailscale-ssh
```

これは仕様です。Tailscale 公式（KB 1208 / 「Tailscale SSH server support on Windows」）で、
**Tailscale SSH のサーバー側は Linux と macOS（open source tailscale / tailscaled）だけ**。
Windows はクライアントとしては全プラットフォームで使えますが、**Windows マシン側で Tailscale SSH を受けることはできません**。

なので X600 を測る経路は **Windows 標準の OpenSSH サーバー + 公開鍵認証**です（Tailscale は LAN 経路の代替になるだけで、SSH 自体は sshd が受ける）。

## 2026-11-10 実測で確定した身元

| 対象 | 実測値 | 実測根拠 |
|---|---|---|
| tailnet ノード `x600.tail8fffd8.ts.net` |HostName=`X600`, os=windows, IP `100.123.199.109`, **online**, ping **5〜9 ms** | `tailscale status --json` |
| X600 の LAN IP | **192.168.2.14** | `tailscale ping 100.123.199.109` → `... via 192.168.2.14:41641 in 7ms`（direct 通信）。さらに 192.168.2.14 の RDP 証明書 CN = **X600** |
| X600 のポート | 3389 OPEN（RDP）、**22 閉**（OpenSSH 未導入） | TCP 到達実測 |
| 192.168.2.12 | z790（Windows、tailnet 名と CN=Z790 が一致） | tailscale ping / RDP 証明書 CN |
| 192.168.2.13 | Z690（Windows） | RDP 証明書 CN |
| 192.168.2.100 | tokage（NAS・運営 HUD） | tailscale ping + 8899 の `<title>` |
| 192.168.2.155 | bc250-1（Ubuntu） | tailscale status direct |
| 192.168.2.11 | z790-al（Ubuntu 推論 hub） | tailscale status direct |

`scripts/lan_scan.py` が同じ方法（RDP 証明書 CN / HTTP title / tailscale ping の via）で一覧を張り直し、`data/lan_identities.json` に保存します。

## 1) X600 側（PowerShell を「管理者として実行」）

```powershell
new-item -ItemType Directory -Force C:\corestation | Out-Null
iwr https://corestation.pages.dev/tools/setup_x600.ps1 -OutFile C:\corestation\setup_x600.ps1
iwr https://corestation.pages.dev/tools/worker_reporter.ps1 -OutFile C:\corestation\worker_reporter.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File C:\corestation\setup_x600.ps1
```

スクリプトがやること（電源操作・再起動・マイナーの設定変更はしません）:

1. OpenSSH クライアント / サーバー capability を確認（無ければ追加）
2. `sshd` を自動起動にして開始、`sshd` の既定ファイアウォール規則の**送信元を LAN（192.168.2.0/24）と tailnet（100.64.0.0/10）だけに絞る**
3. 収集専用の公開鍵を `C:\ProgramData\ssh\administrators_authorized_keys` に追記（既存行は保持）、ACL を `SYSTEM` と `Administrators` 単独に fix
4. `no-port-forwarding,no-agent-forwarding,no-X11-forwarding,no-pty,from="192.168.2.10,100.68.123.120,100.86.91.70"` を鍵行に付ける
5. `whoami` と `Get-LocalUser` を印字（**ここで出たユーザー名**を鍵行の `from` とACLに入れる）
6. `worker_reporter.ps1` を初回実行して `C:\corestation\corestation_metrics.json` を書き、5 分毎の定期実行（SYSTEM）を登録

実行後に出る `-CollectorPublicKey` の行をそのまま実行するか、Hub 側で鍵を表示:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File C:\corestation\setup_x600.ps1 -ShowKeyOnly
```

鍵自体は Hub 側にあります（秘密鍵は X600 に置かない・コミットしない）:

```
/Users/kazukitonogi/.ssh/x600_collector_ed25519.pub
```

### 手動でやる場合（スクリプトを使わない）

```powershell
Add-WindowsCapability -Online -Name "OpenSSH.Server~~~~0.0.1.0"
Set-Service sshd -StartupType Automatic
Start-Service sshd
Set-NetFirewallRule -DisplayName "OpenSSH-Server-In-TCP" -RemoteAddress 192.168.2.0/24,100.64.0.0/10
# 鍵は「そのまま 1 行」で追記（折り返し禁止）
Add-Content -Path C:\ProgramData\ssh\administrators_authorized_keys -Value $pubkey
icacls C:\ProgramData\ssh\administrators_authorized_keys /inheritance:r /grant "SYSTEM:F" /grant "BUILTIN\Administrators:F"
```

注意: Windows の OpenSSH は管理者アカウントの鍵を `administrators_authorized_keys` で受け取ります。このファイルの ACL に継承（User / Authenticated Users など）が残っていると鍵が無視されて認証に失敗します。

## 2) Tailscale 側の設定

- `tailscale set --ssh` は不要（Windows では受ける側にならないため）。`tailscale up` だけで十分です。
- 管理コンソールの Access controls で **tailnet policy を変更しないこと**（2026-11-08 19:50 JST 実測で hub への SSH まで落ちた）。
- LAN 直接が通るので（X600 は direct 7 ms）、Hub からの SSH は LAN IP `192.168.2.14` 優先、tailnet IP はフォールバックとして使います。

## 3) Hub 側（MacBook）で確認・取り込み

```bash
cd /Volumes/Docker/CoreGeeksEXp
bash scripts/x600_pull_metrics.sh          # 22 が開いていれば C:\corestation\corestation_metrics.json を data/machine_metrics/X600.json へ
bash scripts/x600_pull_metrics.sh --check  # 身元 tailnet / TCP 22 / ping の切り分けだけ
python3 scripts/dashboard_live.py --deploy # ダッシュボードへ反映
```

`x600_pull_metrics.sh` は LAN IP → tailnet の順で 22 を確認して引きに行き、開いていなければ理由を出ます（`ssh: connect to host 192.168.2.14 port 22: Connection refused` → sshd 未起動）。H/s 実測が入るまでダッシュボードの H/s は `未取得` のままです（0 や推算は入れません）。

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
| CPU / マザーボード温度（WMI thermal zone） | `MSAcpi_ThermalZoneTemperature` を `/10 - 273.15`（thermal zone が無いマシンでは null） |
| NIC の MAC と IPv4（身元照合・WoL 用） | `Get-NetAdapter` / `Get-NetIPAddress` |
| 測れない | AMD GPU の温度・電力（この方法では取れない）、CPU パッケージ電力。正確に測るなら LibreHardwareMonitor / HWiNFO 側が必要 |

## WoL（電源が入っていない時）

X600 が生きていて MAC が取れたら `data/x600_mac.txt` に控えて `bash scripts/x600_wake.sh --wake`（magic packet を 192.168.2.255:7 / :9 と 255.255.255.255 へ、最大 60 秒応答待ち）。BIOS / OS 側で Wake on LAN が有効なことが条件。MAC は `worker_reporter.ps1` の `macAddresses` が確実な源です（macOS の ARP 表は 192.168.2.* を返さない実測あり）。
