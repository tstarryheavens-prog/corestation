# CoreStation X600 セットアップ（X600 本体の PowerShell を「管理者として実行」で 1 回だけ）
#
# 【重要】Tailscale SSH は Windows では「サーバー側」が未サポート（公式仕様の現状）:
#   サーバー側として動くのは Linux / macOS の open source tailscale+tailscaled のみ。
#   Windows クライアントで `tailscale set --ssh` を叩くと "The Tailscale SSH server is not supported on windows" で拒否される。
#   → なので Windows 標準の **OpenSSH サーバー**を立てて、**鍵認証（パスワード不要）**で Hub (kazukimacbook-air) から読む。
#   Tailscale は「経路」としてはそのまま使う（tailnet IP 100.x 越しにも、LAN 192.168.2.x 越しにも届く）。
#
# このスクリプトがやらないこと: 電源操作・再起動・マイナーの起動/停止・マイナー設定の変更・Windows Update。
# 秘密情報は保存しない。書き込むのは「収集専用の公開鍵」だけ（送信元 IP 限定・ポートフォワード無効）。削除はいつでもできる。
#
# 実行:
#   powershell -NoProfile -ExecutionPolicy Bypass -File .\setup_x600.ps1
# 収集鍵を入れたくない場合:
#   powershell -NoProfile -ExecutionPolicy Bypass -File .\setup_x600.ps1 -CollectorPublicKey ""
# SSH サーバーを立てたくない場合の代替（NAS 共有へ書き出すだけ / tailnet policy 変更不要）:
#   ... -ShareOutFile "\\192.168.2.100\Docker\CoreGeeksEXp\data\machine_metrics\X600.json"
#   （この場合は X600 側に NAS の SMB 資格情報が要る。パスワードはこの画面には打ち込まないこと）

[CmdletBinding()]
param(
  [string]$Hostname = "X600",
  [string]$MetricDir = "C:\corestation",
  [int]$ReportEveryMinutes = 5,
  # Hub 側のコレクターが使う公開鍵（公開情報。source を自宅 LAN と tailnet に限定して書き込む）
  [string]$CollectorPublicKey = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIBa+tNq1UQb2kb7dhCd+a+WWJPpmGPm1WSKO6201R359 hermes-corestation-collector",
  [string]$CollectorSource = "192.168.2.10,100.68.123.120,100.86.91.70",
  # SSH を許可する送信元（自宅 LAN と tailnet の CGNAT 帯だけ）
  [string]$AllowFromSubnets = "192.168.2.0/24,100.64.0.0/10",
  [string]$ShareOutFile = ""
)

$ErrorActionPreference = "Stop"
function Step($m) { Write-Host "`n== $m ==" -ForegroundColor Cyan }

$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) { throw "このスクリプトは「管理者として実行」が必要です。" }

Step "現在の状態（実測）"
Write-Host "ComputerName : $env:COMPUTERNAME"
Write-Host "SSH_USER     : $(whoami)"          # ← この 1 行を Hub 側に教えてほしい
Write-Host "LAN IPv4     : $((Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.PrefixOrigin -ne 'WellKnown' -and $_.IPAddress -notlike '169.*' } | ForEach-Object { $_.IPAddress }) -join ', ')"

# ---- 1) Tailscale（経路。--ssh は Windows では使わない） ----
Step "Tailscale 状態"
$ts = Get-Command tailscale -ErrorAction SilentlyContinue
if (-not $ts) {
  Write-Host "tailscale CLI が見つからないので Tailscale 経路はスキップします（LAN 192.168.2.x だけで測れます）" -ForegroundColor Yellow
  $tsExe = $null
} else {
  $tsExe = if ($ts -is [string]) { $ts } else { $ts.Source }
  & $tsExe version 2>$null | Select-Object -First 1 | Out-Host
  $tailIp = & $tsExe ip -4 2>$null
  if ($tailIp) { Write-Host "tailnet IP : $tailIp" } else { Write-Host "tailnet 未参加（ブラウザ認可が必要）" -ForegroundColor Yellow }
  Write-Host '注意: `tailscale set --ssh` は Windows では不可（サーバー側未サポート）。ここでは OpenSSH サーバーを使う。' -ForegroundColor Yellow
}

# ---- 2) Windows OpenSSH サーバー（鍵認証だけ） ----
Step "OpenSSH サーバー"
$cap = Get-WindowsCapability -Online -Name "OpenSSH.Server~~~~0.0.1.0" -ErrorAction SilentlyContinue
if (-not $cap) { throw "OpenSSH.Server capability が取得できません（Windows 11 以降 / インターネット接続 needed）。手動: 設定 > アプリ > 追加機能 > OpenSSH サーバー" }
if ($cap.State -ne "Installed") {
  Write-Host "OpenSSH サーバーを追加インストールします..."
  Add-WindowsCapability -Online -Name "OpenSSH.Server~~~~0.0.1.0" | Out-Host
} else {
  Write-Host "すでにインストール済み"
}
Set-Service -Name sshd -StartupType Automatic -ErrorAction SilentlyContinue
Start-Service sshd -ErrorAction SilentlyContinue
Get-Service sshd | Format-Table Name, Status, StartType -AutoSize | Out-Host

# ファイアウォール: 自宅 LAN と tailnet からの 22 だけ許可（既定の Any 許可は絞り込む）
$subs = $AllowFromSubnets.Split(",") | ForEach-Object { $_.Trim() }
$rule = Get-NetFirewallRule -DisplayName "OpenSSH-Server-In-TCP" -ErrorAction SilentlyContinue
if ($rule) {
  Set-NetFirewallRule -DisplayName "OpenSSH-Server-In-TCP" -RemoteAddress $subs -Action Allow | Out-Null
  Write-Host "既存の OpenSSH 受信規則を $AllowFromSubnets のみに絞り込みました"
} else {
  New-NetFirewallRule -Name "CoreStation-SSH-In-TCP" -DisplayName "CoreStation collector SSH (LAN/tailnet only)" `
    -Direction Inbound -Action Allow -Protocol TCP -LocalPort 22 -RemoteAddress $subs -Profile Any | Out-Null
  Write-Host "受信規則を作成: TCP 22 <- $AllowFromSubnets"
}
Start-Sleep -Seconds 2
$listeners = Get-NetTCPConnection -LocalPort 22 -State Listen -ErrorAction SilentlyContinue
if ($listeners) {
  Write-Host "sshd 待受（実測）: $((($listeners | ForEach-Object { "$($_.LocalAddress):$($_.LocalPort)" }) | Sort-Object -Unique) -join ', ')"
} else {
  Write-Host "TCP 22 が listen していません — sshd を確認してください（Service の起動に失敗している可能性）" -ForegroundColor Yellow
}

# ---- 3) 収集専用公開鍵（送信元 IP 限定） ----
if ($CollectorPublicKey) {
  Step "収集鍵の配置（鍵認証のみ / パスログインは使わない）"
  if ($CollectorPublicKey -notmatch '^ssh-ed25519\s') { throw "CollectorPublicKey が ssh-ed25519 形式ではありません" }
  $keyLine = "no-port-forwarding,no-agent-forwarding,no-X11-forwarding,no-pty,from=`"$CollectorSource`" $CollectorPublicKey"
  if ($isAdmin) {
    # Administrators グループのアカウントは authorized_keys ではなく administrators_authorized_keys を使う（OpenSSH for Windows の仕様）
    $keyFile = "C:\ProgramData\ssh\administrators_authorized_keys"
  } else {
    $sshDir = Join-Path $env:USERPROFILE ".ssh"
    if (-not (Test-Path $sshDir)) { New-Item -ItemType Directory -Path $sshDir -Force | Out-Null }
    $keyFile = Join-Path $sshDir "authorized_keys"
  }
  $dir = Split-Path $keyFile -Parent
  if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
  $existing = if (Test-Path $keyFile) { Get-Content -Path $keyFile -ErrorAction SilentlyContinue } else { @() }
  $fingerprint = ($CollectorPublicKey -split '\s+')[1].Substring(0, 18)
  if (($existing | Where-Object { $_ -like "*$fingerprint*" }).Count -gt 0) {
    Write-Host "この鍵は登録済み（スキップ）"
  } else {
    Add-Content -Path $keyFile -Value $keyLine -Encoding ASCII
    Write-Host "登録: $keyFile"
  }
  if ($isAdmin) {
    # administrators_authorized_keys は「継承なし + SYSTEM/Administrators のみ」でないと OpenSSH が鍵を無視する
    icacls $keyFile /inheritance:r /grant "SYSTEM:F" /grant "BUILTIN\Administrators:F" | Out-Host
    Write-Host "ACL（実測）:"; icacls $keyFile | Out-Host
  }
  Write-Host "source 限定: $CollectorSource"
  Write-Host "取り消すには: このファイルから該当行を削除（他マシンへの影響なし）" -ForegroundColor Yellow
}

# ---- 4) worker_reporter.ps1 配置（読取り専用） ----
Step "worker_reporter.ps1 配置"
if (-not (Test-Path $MetricDir)) { New-Item -ItemType Directory -Path $MetricDir -Force | Out-Null }
$repLocal = Join-Path $MetricDir "worker_reporter.ps1"
$src = Join-Path (Split-Path $MyInvocation.MyCommand.Path -Parent) "worker_reporter.ps1"
if (Test-Path $src) {
  Copy-Item -Path $src -Destination $repLocal -Force
  Write-Host "同梱の worker_reporter.ps1 をコピー: $repLocal"
} else {
  $url = "https://corestation.pages.dev/tools/worker_reporter.ps1"
  Write-Host "Pages から取得: $url"
  Invoke-WebRequest -Uri $url -OutFile $repLocal -UseBasicParsing
}
& powershell -NoProfile -ExecutionPolicy Bypass -File $repLocal -MachineId $Hostname -OutFile (Join-Path $MetricDir "corestation_metrics.json") | Out-Host

Step "定期実行の登録"
$taskName = "CoreStation_X600_reporter"
$outTarget = if ($ShareOutFile) { $ShareOutFile } else { Join-Path $MetricDir "corestation_metrics.json" }
$runner = Join-Path $MetricDir "run_reporter.cmd"
"@echo off`r`npowershell -NoProfile -ExecutionPolicy Bypass -File `"$repLocal`" -MachineId $Hostname -OutFile `"$outTarget`"" | Set-Content -Path $runner -Encoding ASCII
schtasks /create /tn $taskName /tr "$runner" /sc minute /mo $ReportEveryMinutes /ru SYSTEM /f | Out-Host
schtasks /run /tn $taskName | Out-Host
Write-Host "出力先: $outTarget"

Step "Hub 側で必要な設定（tailnet を経由する場合だけ）"
Write-Host @"
Tailscale 管理コンソール > Access controls（policy）に、X600 の tailnet 名宛てだけ追加する:
  "acls": [ { "action": "accept", "src": ["kazukimacbook-air"], "dst": ["x600:22"] } ]
（いま tailnet は port 22 を通していないので、tailnet 越しの SSH はこの許可がないと開通しない）
LAN 192.168.2.0/24 越しだけなら policy の変更は不要。
"@

Step "完了 — Hub 側へ教えてほしい値"
Write-Host "X600_SSH_USER=$(whoami)"
Write-Host "X600_LAN_IP=$(((Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.PrefixOrigin -eq 'Dhcp' -or $_.PrefixOrigin -eq 'Manual' } | ForEach-Object { $_.IPAddress }) -join ','))"
if ($tsExe) { $tailNow = (& $tsExe ip -4 2>$null); Write-Host "X600_TAILNET_IP=$tailNow" }
Write-Host "（この 3 行をそのまま貼ってもらえれば Hub 側の取り込み設定を確定して、その場で実測を取りに行きます）"
