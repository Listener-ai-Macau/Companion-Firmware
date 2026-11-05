<#
.SYNOPSIS
Companion 真机验收会话（Listener 风格：单弹窗逐步 + 串口全程抓日志）。

.DESCRIPTION
1. 预检 COM13 ST-Link 与 BLE companion 广播
2. 后台持续抓串口日志
3. 用 aiw operator-prompt 一次只开一个中文弹窗（N/M）
4. 关键录音步可调用 Type BLE 同步弹窗（SW3）
5. 你的通过/失败/备注写入 session 目录；失败备注会保留供修复

用法：
  pwsh -NoProfile -File tools\run_companion_real_acceptance_session.ps1
  pwsh -NoProfile -File tools\run_companion_real_acceptance_session.ps1 -SkipBleSyncPopup
#>

param(
    [string]$SerialPort = "COM13",
    [int]$BaudRate = 115200,
    [string]$BleAddress = "00:80:E1:27:B8:EA",
    [string]$BleName = "companion",
    [switch]$SkipBleSyncPopup,
    [switch]$MachinePrecheckOnly
)

$ErrorActionPreference = "Stop"
$FirmwareRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$CompanionRoot = (Resolve-Path (Join-Path $FirmwareRoot "..")).Path
$TypeRoot = Join-Path $CompanionRoot "Companion-Type"
$Workflow = "C:\Users\Billy\Desktop\Denzic\ai-collaboration-workflow"
$OperatorPrompt = Join-Path $Workflow "scripts\operator_prompt.ps1"

if (-not (Test-Path -LiteralPath $OperatorPrompt)) {
    throw "operator_prompt.ps1 not found: $OperatorPrompt"
}

$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$SessionDir = Join-Path $FirmwareRoot "docs\validation\comp-req-642-real-acceptance\session-$stamp"
New-Item -ItemType Directory -Force -Path $SessionDir, (Join-Path $SessionDir "operator"), (Join-Path $SessionDir "logs") | Out-Null

$SerialLog = Join-Path $SessionDir "logs\serial-full.log"
$SessionJson = Join-Path $SessionDir "session.json"
$PrecheckJson = Join-Path $SessionDir "precheck.json"

function Write-Session {
    param($Obj)
    $Obj | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $SessionJson -Encoding UTF8
}

function Invoke-Operator {
    param(
        [string]$Progress,
        [string]$Title,
        [string]$Scope,
        [string]$Message,
        [string]$Expected,
        [string]$OutName
    )
    # OutName is a bare stem (no extension). operator_prompt writes exactly OutputPath.
    $safeName = ($OutName -replace '\.json$', '')
    $outPath = Join-Path $SessionDir "operator\$safeName.json"
    $msg = @"
$Message

串口日志（全程）：$SerialLog
会话目录：$SessionDir

有问题请在备注里写清楚现象；我会按备注抓日志修。
"@
    # WinForms needs a normal interactive process (not -NoNewWindow) so the UI is visible.
    # -STA ensures the apartment model WinForms expects.
    $argList = @(
        "-NoProfile",
        "-STA",
        "-File", $OperatorPrompt,
        "-Title", $Title,
        "-ProgressText", $Progress,
        "-ScopeText", $Scope,
        "-Message", $msg,
        "-ExpectedText", $Expected,
        "-ReviewStyle",
        "-Input",
        "-Buttons", "通过,失败,跳过,中止",
        "-OutputPath", $outPath,
        "-Json",
        "-Position", "Center",
        "-Width", 760,
        "-Height", 460
    )
    $p = Start-Process -FilePath "pwsh" -ArgumentList $argList -Wait -PassThru -WindowStyle Normal
    $result = $null
    if (Test-Path -LiteralPath $outPath) {
        try {
            $raw = Get-Content -LiteralPath $outPath -Raw -Encoding UTF8
            # operator_prompt -Json prints JSON to stdout file content may be the json object
            $result = $raw | ConvertFrom-Json
        } catch {
            $result = [ordered]@{ raw = (Get-Content -LiteralPath $outPath -Raw -Encoding UTF8) }
        }
    }
    return [ordered]@{
        exitCode = $p.ExitCode
        path = $outPath
        result = $result
    }
}

# --- Precheck: serial + BLE ---
$pre = [ordered]@{
    schema = "companion.real_acceptance.precheck.v1"
    startedAt = (Get-Date).ToUniversalTime().ToString("o")
    serialPort = $SerialPort
    bleAddress = $BleAddress
    checks = [ordered]@{}
}

# Serial open smoke
try {
    Add-Type -AssemblyName System.IO.Ports | Out-Null
    $sp = [System.IO.Ports.SerialPort]::new($SerialPort, $BaudRate, [System.IO.Ports.Parity]::None, 8, [System.IO.Ports.StopBits]::One)
    $sp.ReadTimeout = 200
    $sp.Open()
    Start-Sleep -Milliseconds 300
    $probe = ""
    try { $probe = $sp.ReadExisting() } catch {}
    $sp.Close(); $sp.Dispose()
    $pre.checks.serial_open = [ordered]@{ status = "PASS"; sampleChars = $probe.Length }
} catch {
    $pre.checks.serial_open = [ordered]@{ status = "FAIL"; error = "$_" }
}

# BLE scan
try {
    $bleOut = Join-Path $SessionDir "logs\ble-scan-precheck.json"
    $py = @"
import asyncio, json
from bleak import BleakScanner
async def main():
    found = await BleakScanner.discover(timeout=8.0, return_adv=True)
    hits = []
    for addr,(dev,adv) in found.items():
        name = dev.name or getattr(adv,'local_name',None) or ''
        if 'companion' in (name or '').lower() or addr.upper()=='$($BleAddress.ToUpper())':
            hits.append({'address':addr,'name':name,'rssi':getattr(adv,'rssi',None)})
    open(r'$($bleOut.Replace('\','/'))','w',encoding='utf-8').write(json.dumps({'hits':hits,'total':len(found)},indent=2))
    print('hits', len(hits), 'total', len(found))
asyncio.run(main())
"@
    $pyPath = Join-Path $SessionDir "logs\ble_scan_precheck.py"
    Set-Content -LiteralPath $pyPath -Value $py -Encoding UTF8
    $p = Start-Process -FilePath "python" -ArgumentList @($pyPath) -Wait -PassThru -NoNewWindow
    $hits = @()
    if (Test-Path $bleOut) {
        $j = Get-Content $bleOut -Raw | ConvertFrom-Json
        $hits = @($j.hits)
    }
    $pre.checks.ble_scan = [ordered]@{
        status = if ($hits.Count -ge 1) { "PASS" } else { "FAIL" }
        hits = $hits
        exitCode = $p.ExitCode
    }
} catch {
    $pre.checks.ble_scan = [ordered]@{ status = "FAIL"; error = "$_" }
}

$pre.endedAt = (Get-Date).ToUniversalTime().ToString("o")
$pre | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $PrecheckJson -Encoding UTF8

if ($pre.checks.serial_open.status -ne "PASS") {
    Write-Host "PRECHECK FAIL: serial $SerialPort - $($pre.checks.serial_open.error)"
}
if ($pre.checks.ble_scan.status -ne "PASS") {
    Write-Host "PRECHECK FAIL: BLE companion not seen"
}

if ($MachinePrecheckOnly) {
    Write-Host "Precheck only -> $PrecheckJson"
    exit 0
}

# --- Background serial tailer ---
$serialJobScript = @"
`$ErrorActionPreference = 'Continue'
Add-Type -AssemblyName System.IO.Ports | Out-Null
`$log = '$($SerialLog.Replace("'","''"))'
`$portName = '$SerialPort'
`$baud = $BaudRate
try {
  `$sp = [System.IO.Ports.SerialPort]::new(`$portName, `$baud, [System.IO.Ports.Parity]::None, 8, [System.IO.Ports.StopBits]::One)
  `$sp.ReadTimeout = 200
  `$sp.DtrEnable = `$false
  `$sp.RtsEnable = `$false
  `$sp.Open()
  Add-Content -LiteralPath `$log -Value ("# serial capture start " + (Get-Date).ToString('o') + " port=" + `$portName) -Encoding UTF8
  while (`$true) {
    try {
      `$chunk = `$sp.ReadExisting()
      if (`$chunk) { Add-Content -LiteralPath `$log -Value `$chunk -NoNewline -Encoding UTF8 }
    } catch {}
    Start-Sleep -Milliseconds 50
  }
} catch {
  Add-Content -LiteralPath `$log -Value ("# serial capture error: " + `$_) -Encoding UTF8
}
"@
$serialJob = Start-Job -ScriptBlock ([scriptblock]::Create($serialJobScript))
Start-Sleep -Milliseconds 400

$session = [ordered]@{
    schema = "companion.real_acceptance.session.v1"
    startedAt = (Get-Date).ToUniversalTime().ToString("o")
    sessionDir = $SessionDir
    serialLog = $SerialLog
    serialJobId = $serialJob.Id
    precheck = $PrecheckJson
    steps = @()
    status = "RUNNING"
}

Write-Session $session

$total = 7
function Add-Step($id, $title, $payload) {
    $script:session.steps += [ordered]@{
        id = $id
        title = $title
        at = (Get-Date).ToUniversalTime().ToString("o")
        payload = $payload
    }
    Write-Session $script:session
}

try {
    # 1/7 board power + face
    $r = Invoke-Operator -Progress "1/$total" -Title "Companion 真机验收" `
        -Scope "板子上电与日常脸" `
        -Message "请确认：1) NUCLEO/挂件板已上电 2) 墨水屏有日常脸或可辨画面 3) 串口 COM13 已插好。看完点按钮。" `
        -Expected "上电正常；屏幕有可见画面；不要求完美艺术。" `
        -OutName "01-board-power-face.json"
    Add-Step "01" "board power and face" $r
    if ($r.result.selected -eq "中止") { throw "owner aborted at step 01" }
    if ($r.result.selected -eq "失败") { Write-Host "STEP01 FAIL note=$($r.result.note)" }

    # 2/7 machine BLE radio already proven + human confirm
    $bleProbe = Join-Path $SessionDir "logs\real-ble-probe.json"
    try {
        python (Join-Path $FirmwareRoot "tools\run_companion_real_user_path_ble.py") `
            --name $BleName --address $BleAddress --timeout 20 --connect-retries 3 `
            --output $bleProbe | Out-Null
    } catch {}
    $bleStatus = "unknown"
    if (Test-Path $bleProbe) {
        $bj = Get-Content $bleProbe -Raw | ConvertFrom-Json
        $bleStatus = $bj.status
    }
    $r = Invoke-Operator -Progress "2/$total" -Title "Companion 真机验收" `
        -Scope "BLE 真机连通（机器已代跑一遍）" `
        -Message "机器刚对 $BleAddress 做了扫连/读状态/录音列表。结果：$bleStatus`n证据：$bleProbe`n请你在手机/电脑蓝牙设置里确认仍能看到 companion。无需手动连也行。" `
        -Expected "广播名 companion 可见；机器结果为 PASS_REAL_RADIO 更佳。" `
        -OutName "02-ble-visible.json"
    Add-Step "02" "ble visible" $r
    if ($r.result.selected -eq "中止") { throw "owner aborted at step 02" }

    # 3/7 touch single response — bring serial window forward if possible
    try {
        $serialWindows = Get-Process pwsh -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowTitle -match '串口|COM13|Serial' }
        foreach ($w in $serialWindows) {
            # no-op: user keeps serial monitor open from launcher
        }
    } catch {}
    $r = Invoke-Operator -Progress "3/$total" -Title "Companion 真机验收" `
        -Scope "单击触摸响应（请同时看串口窗口）" `
        -Message "请保持「串口监视」窗口可见。在触摸屏脸部区域单击 1 次，看屏幕响应，并扫一眼串口是否出现 touch/gesture 行。" `
        -Expected "单击有可见响应或串口有 touch 日志；无死机。" `
        -OutName "03-touch-tap"
    Add-Step "03" "touch tap" $r
    if ($r.result.selected -eq "中止") { throw "owner aborted at step 03" }

    # 4/7 double-tap or long-press menu
    $r = Invoke-Operator -Progress "4/$total" -Title "Companion 真机验收" `
        -Scope "手势：双击录音 或 长按进菜单（按你板子当前固件行为）" `
        -Message "请尝试：A) 双击开始/停止录音 或 B) 长按约 3 秒进菜单。以实际表现为准，在备注写你做了什么、看到了什么。" `
        -Expected "手势可区分；不会持续死机；异常写备注。" `
        -OutName "04-gesture-record-or-menu.json"
    Add-Step "04" "gesture" $r
    if ($r.result.selected -eq "中止") { throw "owner aborted at step 04" }

    # 5/7 Type SW3 BLE sync popup (Listener-style guided)
    if (-not $SkipBleSyncPopup -and (Test-Path (Join-Path $TypeRoot "tools\run_companion_type_ble_sync_popup.ps1"))) {
        # Open Type folder + start SW3 popup environment for the user
        try { Start-Process explorer.exe $TypeRoot } catch {}
        $r = Invoke-Operator -Progress "5/$total" -Title "Companion 真机验收" `
            -Scope "即将打开 Type SW3 录音同步环境" `
            -Message "点「通过」后会立刻打开 Companion-Type 的 SW3 录音/同步引导窗（会占串口 COM13）。请按那个窗口提示按板载 SW3。手边准备好板子。" `
            -Expected "你已准备好按 SW3；板子在手边。" `
            -OutName "05-ready-for-sw3-sync"
        Add-Step "05a" "ready for type sync" $r
        if ($r.result.selected -ne "中止" -and $r.result.selected -ne "跳过") {
            $typeLog = Join-Path $SessionDir "logs\type-ble-sync-popup"
            New-Item -ItemType Directory -Force -Path $typeLog | Out-Null
            Push-Location $TypeRoot
            try {
                $p = Start-Process -FilePath "pwsh" -ArgumentList @(
                    "-NoProfile", "-STA", "-File", "tools\run_companion_type_ble_sync_popup.ps1",
                    "-SerialPort", $SerialPort,
                    "-RecordSeconds", "2"
                ) -Wait -PassThru -WindowStyle Normal
                Add-Step "05b" "type ble sync popup" ([ordered]@{ exitCode = $p.ExitCode })
            } finally {
                Pop-Location
            }
            # copy latest type validation artifacts if present
            $typeVal = Join-Path $TypeRoot "docs\validation"
            foreach ($f in @(
                "companion-type-native-ble-sync-popup.json",
                "companion-type-native-ble-sync-sw3-serial.log",
                "companion-type-native-ble-sync-smoke.log"
            )) {
                $src = Join-Path $typeVal $f
                if (Test-Path $src) { Copy-Item $src (Join-Path $SessionDir "logs\$f") -Force }
            }
        }
    } else {
        Add-Step "05" "type ble sync popup" ([ordered]@{ status = "SKIPPED" })
    }

    $r = Invoke-Operator -Progress "5/$total" -Title "Companion 真机验收" `
        -Scope "SW3 / Type 同步结果" `
        -Message "若刚做了 Type 同步：请确认录音是否同步到主机、UI 是否诚实。没做则跳过。" `
        -Expected "同步成功或失败原因清楚；备注写现象。" `
        -OutName "05-sw3-sync-result.json"
    Add-Step "05c" "sw3 sync human result" $r
    if ($r.result.selected -eq "中止") { throw "owner aborted at step 05" }

    # 6/7 screen overall quality
    $r = Invoke-Operator -Progress "6/$total" -Title "Companion 真机验收" `
        -Scope "屏幕与刷新观感" `
        -Message "整体看：脸是否可接受、残影是否严重、方向是否正确。备注写最刺眼的问题。" `
        -Expected "可演示/不可演示你定；问题写进备注即进入修复。" `
        -OutName "06-screen-quality.json"
    Add-Step "06" "screen quality" $r
    if ($r.result.selected -eq "中止") { throw "owner aborted at step 06" }

    # 7/7 session close
    $r = Invoke-Operator -Progress "7/$total" -Title "Companion 真机验收" `
        -Scope "本轮结束" `
        -Message "本轮真机验收结束。串口日志：$SerialLog`n全部备注会留在 $SessionDir`n若有失败项我会按备注修。" `
        -Expected "点通过结束；若还有总评写备注。" `
        -OutName "07-session-close.json"
    Add-Step "07" "session close" $r

    $session.status = "COMPLETED"
    $session.endedAt = (Get-Date).ToUniversalTime().ToString("o")
    Write-Session $session
    Write-Host "SESSION DONE: $SessionDir"
}
catch {
    $session.status = "ABORTED_OR_ERROR"
    $session.error = "$_"
    $session.endedAt = (Get-Date).ToUniversalTime().ToString("o")
    Write-Session $session
    Write-Host "SESSION STOPPED: $_"
    Write-Host "Logs: $SessionDir"
}
finally {
    if ($serialJob) {
        Stop-Job -Job $serialJob -ErrorAction SilentlyContinue
        Receive-Job -Job $serialJob -ErrorAction SilentlyContinue | Out-Null
        Remove-Job -Job $serialJob -Force -ErrorAction SilentlyContinue
    }
    Add-Content -LiteralPath $SerialLog -Value ("`n# serial capture end " + (Get-Date).ToString("o")) -Encoding UTF8
}
