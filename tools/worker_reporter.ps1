# CoreStation worker reporter (X600 / Windows) — 読取り専用
# H/s・温度・消費電力・ストラーム接続を "測れるものだけ" 集めて JSON に書く。
# 再起動・設定変更・電源操作・マイナーの起動/停止は一切しない。測れない項目は null のまま。
# 例:  powershell -NoProfile -ExecutionPolicy Bypass -File C:\corestation\worker_reporter.ps1
[CmdletBinding()]
param(
  [string]$OutFile = "C:\corestation\corestation_metrics.json",
  [string]$MachineId = "X600",
  [string]$LogRoot = ""   # マイナーログの探索ルート（空ならプロセスの起動ディレクトリから推定）
)

$ErrorActionPreference = "Continue"
$now = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ss.fffZ")
$reasons = New-Object System.Collections.Generic.List[string]

function New-NullMap { @{} }

# ---- 1) マイナープロセスの実測（存在・コマンドライン・worker 名） ----
$minerNames = @("coreminer", "SRBMiner-MULTI", "SRBMiner", "xmrig", "TeamRedMiner", "nbminer", "lolminer", "T-Rex", "phoenixminer", "miner")
$procs = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
  Where-Object { $n = $_.Name -replace '\.exe$',''; ($minerNames | Where-Object { $n -match [regex]::Escape($_) }).Count -gt 0 }

$miners = @()
foreach ($p in $procs) {
  $cl = [string]$p.CommandLine
  $worker = $null
  if ($cl -match '--worker(?:name)?[=\s]+"?([^"\s]+)') { $worker = $Matches[1] }
  elseif ($cl -match 'worker[=\s]+"?([^"\s]+)') { $worker = $Matches[1] }
  $pool = $null
  if ($cl -match '(stratum2?://)?([a-z0-9.\-]+\.catchthatrabbit\.com)(?::(\d+))?') { $pool = $Matches[2] + $(if ($Matches[3]) { ":" + $Matches[3] } else { "" }) }
  elseif ($cl -match '([a-z0-9.\-]+\.[a-z]{2,})?:1?8008') { $pool = $Matches[1] }
  $miners += [ordered]@{
    processName = $p.Name
    processId   = $p.ProcessId
    cpuPercent  = $p.CPU                       # CIM が持つ累計 CPU 時間ベース（percent ではない）
    workerName  = $worker                      # マイナーが実際に使っている worker 名（実測）
    poolHost    = $pool
    commandLineHash = if ($cl) { (Get-FileHash -InputStream ([IO.MemoryStream]::new([Text.Encoding]::UTF8.GetBytes($cl))) -Algorithm SHA256).Hash } else { $null }
  }
}
if (-not $miners -or $miners.Count -eq 0) { $reasons.Add("マイナープロセスが見つからない（採掘が走っていない or 別名で実行中）") }

# ---- 2) H/s: マイナーログの実測パース（無ければ null） ----
$hashrate = $null; $hashrateUnit = $null; $hashrateSource = $null; $hashrateAt = $null
$logFiles = @()
if ($LogRoot -and (Test-Path $LogRoot)) {
  $logFiles = Get-ChildItem -Path $LogRoot -Recurse -Include *.log,*.txt -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 8
} else {
  foreach ($p in $procs) {
    $base = $null
    try { $base = (Get-Process -Id $p.ProcessId).Path } catch { }
    if (-not $base -and $p.ExecutablePath) { $base = $p.ExecutablePath }
    if ($base) {
      $dir = Split-Path $base -Parent
      $logFiles += Get-ChildItem -Path $dir -Recurse -Include *.log,*.txt -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 4
    }
  }
  $logFiles = $logFiles | Sort-Object LastWriteTime -Descending -Unique | Select-Object -First 8
}
$unitMult = @{ "h" = 1.0; "kh" = 1e3; "mh" = 1e6; "gh" = 1e9; "th" = 1e12 }
foreach ($f in $logFiles) {
  try {
    $tail = Get-Content -Path $f.FullName -Tail 400 -ErrorAction Stop
    for ($i = $tail.Count - 1; $i -ge 0; $i--) {
      $line = $tail[$i]
      if ($line -match '([0-9]+(?:\.[0-9]+)?)\s*(TH|GH|MH|kH|H)\s*/\s*s') {
        $u = $Matches[2].ToLower()
        $hashrate = [double]$Matches[1] * $unitMult[$u]
        $hashrateUnit = $Matches[2] + "/s"; $hashrateSource = $f.FullName; $hashrateAt = (Get-Item $f.FullName).LastWriteTime.ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
        break
      }
    }
    if ($hashrate) { break }
  } catch { }
}
if (-not $hashrate) { $reasons.Add("ログから H/s を見つけられない（null のまま）") }

# ---- 3) GPU 実測（NVIDIA があれば nvidia-smi / AMD は温度が取れないので null） ----
$gpus = @()
$nv = Get-Command nvidia-smi -ErrorAction SilentlyContinue
if ($nv) {
  try {
    $csv = & nvidia-smi --query-gpu=index,name,temperature.gpu,utilization.gpu,power.draw,power.limit,clocks.current.sm --format=csv,noheader,nounits 2>$null
    foreach ($row in $csv) {
      $c = $row -split ',\s*'
      if ($c.Count -ge 6) {
        $gpus += [ordered]@{ vendor="NVIDIA"; index=[int]$c[0]; name=$c[1]; temperatureC=[double]$c[2]; utilizationPercent=[double]$c[3];
                             powerW=[double]$c[4]; powerLimitW=[double]$c[5]; smClockMHz=$(if ($c.Count -ge 7) { [double]$c[6] } else { $null }) }
      }
    }
  } catch { $reasons.Add("nvidia-smi が失敗") }
} else {
  $reasons.Add("nvidia-smi が無い（AMD GPU の温度/電力はこの方法では取れない → null）")
  $ads = Get-CimInstance Win32_VideoController -ErrorAction SilentlyContinue
  foreach ($a in $ads) { $gpus += [ordered]@{ vendor="WMI"; index=$null; name=$a.Name; temperatureC=$null; utilizationPercent=$null; powerW=$null; powerLimitW=$null; smClockMHz=$null } }
}

# ---- 4) CPU 実測（負荷・温度が取れる場合だけ） ----
$cpu = [ordered]@{ name=$null; loadPercent=$null; temperatureC=$null; cores=$null }
$cpuInfo = Get-CimInstance Win32_Processor -ErrorAction SilentlyContinue | Select-Object -First 1
if ($cpuInfo) {
  $cpu.name = $cpuInfo.Name; $cpu.cores = $cpuInfo.NumberOfCores
  if ($null -ne $cpuInfo.LoadPercentage) { $cpu.loadPercent = [double]$cpuInfo.LoadPercentage }
}
$tz = Get-CimInstance -Namespace root/wmi -ClassName MSAcpi_ThermalZoneTemperature -ErrorAction SilentlyContinue | Select-Object -First 1
if ($tz -and $tz.CurrentTemperature) { $cpu.temperatureC = [math]::Round((($tz.CurrentTemperature / 10.0) - 273.15), 1) } else { $reasons.Add("WMI thermal zone が無い/読めない（CPU 温度 null。正確に測るなら HWiNFO/LibreHardwareMonitor 側が必要）") }

# ---- 5) ストラーム接続の実測（プールに張っている TCP セッション数） ----
$stratum = @()
try {
  $conns = Get-NetTCPConnection -State Established -ErrorAction Stop |
    Where-Object { $_.RemotePort -in @(8008,5555,3333,14444,4444) }
  foreach ($c in $conns) {
    $stratum += [ordered]@{ remoteAddress = $c.RemoteAddress; remotePort = $c.RemotePort; localPort = $c.LocalPort;
                            processId = $c.OwningProcess;
                            processName = try { (Get-Process -Id $c.OwningProcess -ErrorAction Stop).ProcessName } catch { $null } }
  }
} catch { $reasons.Add("Get-NetTCPConnection が読めない") }

# ---- 6) 稼働時間・OS ----
$os = Get-CimInstance Win32_OperatingSystem -ErrorAction SilentlyContinue
$uptimeH = $null
if ($os -and $os.LastBootUpTime) { $uptimeH = [math]::Round(((Get-Date) - $os.LastBootUpTime).TotalHours, 2) }

# ---- 7) DNS / プール解決（接続先が生きているか） ----
$poolResolve = @()
foreach ($host_ in @("as.catchthatrabbit.com","as1.catchthatrabbit.com","sg.catchthatrabbit.com")) {
  try {
    $rec = Resolve-DnsName -Name $host_ -ErrorAction Stop | Where-Object { $_.IPAddress } | Select-Object -First 2
    $tcp = $false
    foreach ($r in $rec) {
      $t = New-Object System.Net.Sockets.TcpClient
      try { $t.Connect($r.IPAddress, 8008); $tcp = $true } catch { } finally { $t.Close() }
      if ($tcp) { break }
    }
    $poolResolve += [ordered]@{ host = $host_; resolved = ($rec | ForEach-Object { $_.IPAddress }) -join ","; stratum8008TcpOpen = $tcp }
  } catch { $poolResolve += [ordered]@{ host = $host_; resolved = $null; stratum8008TcpOpen = $false } }
}

$out = [ordered]@{
  schema            = "corestation-rig/1"
  machine_id        = $MachineId
  computer_name     = $env:COMPUTERNAME
  measured_at       = $now
  source            = "worker_reporter.ps1 (read-only: CIM + nvidia-smi + WMI + logs + TCP)"
  miners            = $miners
  minerCount        = $miners.Count
  hashrate          = $hashrate          # null = 未取得（0 にしない）
  hashrateUnit      = $hashrateUnit
  hashrateSource    = $hashrateSource
  hashrateAt        = $hashrateAt
  gpus              = $gpus
  cpu               = $cpu
  stratumSessions   = $stratum
  stratumSessionCount = $stratum.Count
  poolResolve       = $poolResolve
  uptimeHours       = $uptimeH
  unavailable_reason = $reasons
}

$dir = Split-Path $OutFile -Parent
if ($dir -and -not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
$out | ConvertTo-Json -Depth 6 | Set-Content -Path $OutFile -Encoding UTF8
Write-Output "wrote $OutFile (minerCount=$($miners.Count), hashrate=$(if ($hashrate) { "$hashrate $($hashrateUnit)" } else { 'null' }), gpus=$($gpus.Count), stratum=$($stratum.Count))"
