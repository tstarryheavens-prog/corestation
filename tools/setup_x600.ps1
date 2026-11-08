# CoreStation X600 セットアップ（X600 本体の PowerShell を「管理者として実行」で1回だけ）
# やること: Tailscale 導入 → tailnet に参加（--ssh 有効）→ 読取り専用の worker_reporter.ps1 を定期実行として登録
# このスクリプトは電源操作・再起動・マイナーの設定変更・マイナーの起動/停止を一切しません。
# 秘密情報は保存しません。Tailscale のログインはブラウザで本人が行います（この画面にパスワードは出ません）。
#
# 実行:
#   powershell -NoProfile -ExecutionPolicy Bypass -File .\setup_x600.ps1
# 非対話で参加させる場合（Tailscale 管理コンソールで発行した auth key を X600 側でのみ渡す）:
#   $env:TS_AUTHKEY="tsauth-..."; powershell -NoProfile -ExecutionPolicy Bypass -File .\setup_x600.ps1

[CmdletBinding()]
param(
  [string]$Hostname = "X600",
  [string]$MetricDir = "C:\corestation",
  [string]$InstallerUrl = "https://pkgs.tailscale.com/stable/tailscale-setup-latest.exe",
  [int]$ReportEveryMinutes = 5,
  # Tailscale を使わず NAS 共有に直接書き出す場合（tailnet policy の変更が不要な代替経路）
  # 例: -ShareOutFile "\\192.168.2.100\Docker\CoreGeeksEXp\data\machine_metrics\X600.json"
  [string]$ShareOutFile = ""
)

$ErrorActionPreference = "Stop"
function Step($m) { Write-Host "`n== $m ==" -ForegroundColor Cyan }

$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) { throw "このスクリプトは「管理者として実行」が必要です。" }

Step "現在の状態"
Write-Host "ComputerName : $env:COMPUTERNAME"
Write-Host "User         : $(whoami)"
Write-Host "Power 設定   : sleep=$(powercfg -query 2>$null | Select-String -Pattern 'Standby' | Select-Object -First 1)"

# ---- 1) Tailscale 導入 ----
Step "Tailscale 導入"
$ts = Get-Command tailscale -ErrorAction SilentlyContinue
if (-not $ts) {
  $tmp = Join-Path $env:TEMP "tailscale-setup-latest.exe"
  Write-Host "インストーラをダウンロード: $InstallerUrl"
  Invoke-WebRequest -Uri $InstallerUrl -OutFile $tmp -UseBasicParsing
  Write-Host "サイレントインストール中..."
  $p = Start-Process -FilePath $tmp -ArgumentList "/SP-","/NORESTART","/VERYSILENT" -Wait -PassThru
  Write-Host "installer exit=$($p.ExitCode)"
  $ts = Get-Command tailscale -ErrorAction SilentlyContinue
  if (-not $ts) {
    $guess = Join-Path $env:ProgramFiles "Tailscale\tailscale.exe"
    if (Test-Path $guess) { $ts = (Get-Item $guess).FullName }
  }
}
if (-not $ts) { throw "tailscale CLI が見つかりません。インストール後に再実行してください。" }
$tsExe = if ($ts -is [string]) { $ts } else { $ts.Source }
Write-Host "tailscale: $tsExe"
& $tsExe version 2>$null | Select-Object -First 2

# ---- 2) tailnet 参加（SSH 有効） ----
Step "tailnet 参加（--ssh）"
$ipNow = & $tsExe ip -4 2>$null
if ($ipNow) {
  Write-Host "すでに接続済み: $ipNow"
  & $tsExe set --ssh 2>&1 | Out-Host
} else {
  if ($env:TS_AUTHKEY) {
    Write-Host "TS_AUTHKEY を使って非対話で参加します（キーはこの画面には表示しません）"
    & $tsExe up --ssh --hostname=$Hostname --auth-key=$env:TS_AUTHKEY 2>&1 | Out-Host
  } else {
    Write-Host "ブラウザで Tailscale ログインを開きます。表示される URL を開いて、自分の tailnet アカウント（t.starryheavens@）で認可してください。"
    Start-Process -FilePath $tsExe -ArgumentList "up","--ssh","--hostname=$Hostname" -Wait
  }
}
$ip = (& $tsExe ip -4 2>$null)
if (-not $ip) { throw "tailnet に参加できませんでした（ブラウザ認可が済むまで待ってから再実行）。" }
Write-Host "tailnet IP : $ip"
& $tsExe status 2>&1 | Select-Object -First 12 | Out-Host

# ---- 3) worker_reporter.ps1 配置（読取り専用） ----
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

# ---- 4) 定期実行（SYSTEM で動かし、ログオン状態に依存しない） ----
Step "定期実行の登録"
$taskName = "CoreStation_X600_reporter"
$outTarget = if ($ShareOutFile) { $ShareOutFile } else { Join-Path $MetricDir "corestation_metrics.json" }
# schtasks の /tr は引用符が壊れやすいので .cmd ラッパを経由する
$runner = Join-Path $MetricDir "run_reporter.cmd"
"@echo off`r`npowershell -NoProfile -ExecutionPolicy Bypass -File `"$repLocal`" -MachineId $Hostname -OutFile `"$outTarget`"" | Set-Content -Path $runner -Encoding ASCII
schtasks /create /tn $taskName /tr "$runner" /sc minute /mo $ReportEveryMinutes /ru SYSTEM /f | Out-Host
schtasks /run /tn $taskName | Out-Host
Write-Host "出力先: $outTarget"

Step "完了 — ここから先は Hub 側で自動"
Write-Host @"
X600 の tailnet IP   : $ip
メトリクスファイル   : $(Join-Path $MetricDir 'corestation_metrics.json')（毎 $ReportEveryMinutes 分更新・読取り専用）
定期タスク           : $taskName (SYSTEM)

次の 1 点だけ Tailscale 管理コンソール（Access controls）で許可が必要です:
  1) port 22 への acls 許可（Hub/MacBook -> X600）
  2) ssh ルールで X600 の Windows ユーザー名（上の whoami 表示）を許可
許可されると Hub (kazukimacbook-air / z790-al) から SSH で実測取り込みが自動で走ります。
"@
