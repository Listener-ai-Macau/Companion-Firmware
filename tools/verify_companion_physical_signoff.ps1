param(
    [string] $OutDir,
    [string] $EvidenceMarkdown,
    [switch] $Execute,
    [switch] $WorkflowLockHeld
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
if ([string]::IsNullOrWhiteSpace($OutDir)) {
    $OutDir = Join-Path $repoRoot ".cache\validation\companion-physical-signoff-$stamp"
}
if ([string]::IsNullOrWhiteSpace($EvidenceMarkdown)) {
    $EvidenceMarkdown = Join-Path $repoRoot "docs\validation\companion_pendant_mvp_go_no_go.md"
}

New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
$outDirResolved = (Resolve-Path -LiteralPath $OutDir).Path
$summaryJson = Join-Path $outDirResolved "companion-physical-signoff-summary.json"
$summaryMd = Join-Path $outDirResolved "companion-physical-signoff-summary.md"
$promptTranscript = Join-Path $outDirResolved "companion-physical-signoff-prompt.md"
$evidenceMarkdownResolved = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($EvidenceMarkdown)

function Show-OperatorPrompt {
    param(
        [Parameter(Mandatory = $true)][string] $Title,
        [Parameter(Mandatory = $true)][string] $Message,
        [System.Windows.Forms.MessageBoxButtons] $Buttons = [System.Windows.Forms.MessageBoxButtons]::OK,
        [System.Windows.Forms.MessageBoxIcon] $Icon = [System.Windows.Forms.MessageBoxIcon]::Information
    )

    try {
        Add-Type -AssemblyName System.Windows.Forms
        [System.Media.SystemSounds]::Exclamation.Play()
        [Console]::Beep(880, 180)
        return [System.Windows.Forms.MessageBox]::Show($Message, $Title, $Buttons, $Icon)
    } catch {
        Write-Host ""
        Write-Host "=== $Title ==="
        Write-Host $Message
        Write-Host ""
        if ($Buttons -eq [System.Windows.Forms.MessageBoxButtons]::YesNoCancel) {
            $answer = Read-Host "输入 Y=通过，N=失败，C=不适用/未安装"
            if ($answer -match '^[Yy]') { return [System.Windows.Forms.DialogResult]::Yes }
            if ($answer -match '^[Cc]') { return [System.Windows.Forms.DialogResult]::Cancel }
            return [System.Windows.Forms.DialogResult]::No
        }
        if ($Buttons -eq [System.Windows.Forms.MessageBoxButtons]::YesNo) {
            $answer = Read-Host "输入 Y=是，N=否"
            if ($answer -match '^[Yy]') { return [System.Windows.Forms.DialogResult]::Yes }
            return [System.Windows.Forms.DialogResult]::No
        }
        return [System.Windows.Forms.DialogResult]::OK
    }
}

function Read-OperatorText {
    param(
        [Parameter(Mandatory = $true)][string] $Title,
        [Parameter(Mandatory = $true)][string] $Message,
        [string] $Default = ""
    )

    try {
        Add-Type -AssemblyName Microsoft.VisualBasic
        [System.Media.SystemSounds]::Question.Play()
        [Console]::Beep(660, 160)
        return [Microsoft.VisualBasic.Interaction]::InputBox($Message, $Title, $Default)
    } catch {
        Write-Host ""
        Write-Host "=== $Title ==="
        Write-Host $Message
        return Read-Host "输入"
    }
}

function Convert-DialogToResult {
    param([System.Windows.Forms.DialogResult] $Result)

    if ($Result -eq [System.Windows.Forms.DialogResult]::Yes) { return "PASS" }
    if ($Result -eq [System.Windows.Forms.DialogResult]::Cancel) { return "N/A" }
    return "FAIL"
}

function Ask-Check {
    param(
        [Parameter(Mandatory = $true)][string] $Id,
        [Parameter(Mandatory = $true)][string] $Title,
        [Parameter(Mandatory = $true)][string] $Instruction
    )

    $dialog = Show-OperatorPrompt `
        -Title $Title `
        -Message ($Instruction + [Environment]::NewLine + [Environment]::NewLine + "点击 Yes=真实看到通过；No=失败或没看到；Cancel=硬件未安装/不适用。") `
        -Buttons ([System.Windows.Forms.MessageBoxButtons]::YesNoCancel) `
        -Icon ([System.Windows.Forms.MessageBoxIcon]::Question)
    $result = Convert-DialogToResult -Result $dialog
    $note = ""
    if ($result -ne "PASS") {
        $note = Read-OperatorText -Title "$Title 说明" -Message "请写明原因，例如：屏没接、没有刷新、按钮没反应、显示内容不对。留空也可以。"
    }
    return [ordered]@{
        id = $Id
        title = $Title
        result = $result
        note = $note
    }
}

function Read-Measurement {
    param(
        [Parameter(Mandatory = $true)][string] $Id,
        [Parameter(Mandatory = $true)][string] $Label,
        [Parameter(Mandatory = $true)][string] $Prompt
    )

    $value = Read-OperatorText -Title "功耗测量：$Label" -Message ($Prompt + [Environment]::NewLine + [Environment]::NewLine + "请输入电流 mA，例如 12.4。没有仪表或未测就输入 NA。")
    $numeric = $false
    $number = $null
    if ($value -match '^\s*[0-9]+(\.[0-9]+)?\s*$') {
        $numeric = $true
        $number = [double]$value
    }
    return [ordered]@{
        id = $Id
        label = $Label
        raw = $value
        measured = $numeric
        current_ma = $number
    }
}

function ConvertTo-SignoffMarkdown {
    param([Parameter(Mandatory = $true)] $Summary)

    $lines = @(
        "# Companion Pendant MVP Physical Signoff",
        "",
        "- Status: $($Summary.status)",
        "- Started: $($Summary.started_at)",
        "- Finished: $($Summary.finished_at)",
        "- Operator: $($Summary.operator)",
        "- Output: ``$($Summary.output_dir)``",
        "- Prompt transcript: ``$($Summary.prompt_transcript)``",
        "",
        "## Automated Evidence Already Passed",
        "",
        "- Operator chain: ``C:\Users\Billy\Desktop\Denzic\Companion\Companion-Firmware\.cache\validation\companion-operator-chain-20260630-121232\companion-operator-chain-summary.json``",
        "- Real SAI microphone -> QSPI flash -> BLE pull -> CRC/SHA -> delete: ``C:\Users\Billy\Desktop\Denzic\Companion\Companion-Firmware\.cache\validation\companion-flash-recording-chain-20260630-124303\companion-flash-recording-chain.json``",
        "- Real BLE GATT bench: ``.cache\validation\companion-v1-real-ble-gatt-20260630-114513\companion-ble-real-bench.json``",
        "",
        "## Physical Checks",
        "",
        "| Check | Result | Note |",
        "|---|---:|---|"
    )
    foreach ($check in @($Summary.physical_checks)) {
        $lines += "| $($check.title) | $($check.result) | $($check.note) |"
    }
    $lines += ""
    $lines += "## Power Measurements"
    $lines += ""
    $lines += "| State | Current mA | Raw entry |"
    $lines += "|---|---:|---|"
    foreach ($measurement in @($Summary.power_measurements)) {
        $ma = if ($measurement.measured) { "{0:N3}" -f [double]$measurement.current_ma } else { "" }
        $lines += "| $($measurement.label) | $ma | $($measurement.raw) |"
    }
    $lines += ""
    $lines += "## PCB Go/No-Go"
    $lines += ""
    $lines += "- Decision: $($Summary.pcb_decision.decision)"
    $lines += "- Reason: $($Summary.pcb_decision.reason)"
    $lines += "- Human accepted current recommendation: $($Summary.pcb_decision.accepted_current_no_go)"
    $lines += ""
    $lines += "## Notes"
    $lines += ""
    $lines += $Summary.operator_notes
    return $lines
}

$lockCommand = "pwsh -NoProfile -File C:\Users\Billy\Desktop\Denzic\ai-collaboration-workflow\scripts\aiw.ps1 with-lock -Resource Companion-WB55 -Purpose `"Companion final physical signoff`" -Run pwsh -NoProfile -File .\tools\verify_companion_physical_signoff.ps1 -Execute -WorkflowLockHeld"

if (-not $Execute) {
    $dryRun = [ordered]@{
        schema = "companion.physical_signoff.v1"
        status = "DRY_RUN"
        generated_at = (Get-Date).ToString("o")
        repo_root = $repoRoot
        output_dir = $outDirResolved
        evidence_markdown = $evidenceMarkdownResolved
        lock_command = $lockCommand
        checks = @(
            "real e-paper default/recording/sync-complete/BLE-written cards",
            "real button capture affordance",
            "power measurements for boot/idle, advertising, connected idle, recording, e-paper refresh, chunk transfer, charge/external-power",
            "PCB go/no-go decision"
        )
    }
    $dryRun | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $summaryJson -Encoding UTF8
    Write-Host "DRY-RUN: Companion physical signoff guide is ready."
    Write-Host "Run under workflow hardware lock:"
    Write-Host "  $lockCommand"
    Write-Host "Summary: $summaryJson"
    exit 0
}

if (-not $WorkflowLockHeld) {
    Write-Host "Use the workflow hardware lock before executing:"
    Write-Host "  $lockCommand"
    throw "Refusing to run physical signoff without -WorkflowLockHeld."
}

$startedAt = (Get-Date).ToString("o")
$operator = Read-OperatorText -Title "Companion 最终物理验收" -Message "请输入验收人名字或缩写，用于 evidence 记录。" -Default "Billy"

$intro = @(
    "接下来会逐步确认 Companion pendant 的最后物理链路。",
    "",
    "你需要真实观察或测量：",
    "1. e-paper 默认卡、录音卡、同步完成卡、BLE 写入短句卡。",
    "2. 按真实按钮后是否有 capture/录音 affordance。",
    "3. 用电流表或功耗仪记录各状态电流。",
    "4. 接受或推翻当前 PCB 暂不 go 的建议。",
    "",
    "每一步请按真实结果点 Yes / No / Cancel。Cancel 表示硬件未安装或本轮不适用。"
) -join [Environment]::NewLine
[void](Show-OperatorPrompt -Title "开始 Companion 物理验收" -Message $intro)

$physicalChecks = @()
$physicalChecks += Ask-Check -Id "epaper_default" -Title "e-paper 默认卡" -Instruction "请看真实目标 e-paper：上电或空闲状态能看到默认/固定卡片，且内容完整、没有明显花屏或错位。"
$physicalChecks += Ask-Check -Id "epaper_recording" -Title "e-paper 录音状态卡" -Instruction "让设备进入录音状态，观察真实 e-paper 是否显示录音/捕获状态卡，状态变化清楚。"
$physicalChecks += Ask-Check -Id "epaper_sync_complete" -Title "e-paper 同步完成卡" -Instruction "让设备完成同步/传输后，观察真实 e-paper 是否显示同步完成状态卡。"
$physicalChecks += Ask-Check -Id "epaper_ble_written_card" -Title "BLE 写入短句卡" -Instruction "确认 BLE 写入的短句或 fixture payload 能显示在真实 e-paper 上；期望短句类似 1234567 chain verified 或本轮测试短句。"
$physicalChecks += Ask-Check -Id "button_capture_affordance" -Title "真实按钮 capture affordance" -Instruction "请按一次 Companion 真实按钮，观察设备是否出现明确的录音/capture affordance，例如显示切换、状态反馈、LED/日志/主机状态变化。"

$powerMeasurements = @()
$powerMeasurements += Read-Measurement -Id "boot_idle" -Label "boot/idle" -Prompt "设备启动完成并处于空闲状态时，读取电流。"
$powerMeasurements += Read-Measurement -Id "advertising" -Label "BLE advertising" -Prompt "设备未连接、正在 BLE 广播时，读取电流。"
$powerMeasurements += Read-Measurement -Id "connected_idle" -Label "connected idle" -Prompt "BLE 已连接但没有录音/刷新/传输时，读取电流。"
$powerMeasurements += Read-Measurement -Id "recording" -Label "recording" -Prompt "正在录音并写入本地存储时，读取电流。"
$powerMeasurements += Read-Measurement -Id "epaper_refresh" -Label "e-paper refresh" -Prompt "e-paper 正在刷新时，读取峰值或稳定读数；如只能读峰值，请在备注说明。"
$powerMeasurements += Read-Measurement -Id "chunk_transfer" -Label "BLE chunk transfer" -Prompt "BLE 正在拉取录音 chunk 时，读取电流。"
$powerMeasurements += Read-Measurement -Id "charge_external_power" -Label "charge/external-power" -Prompt "外部供电/充电状态下，读取电流或输入 NA 并说明硬件原因。"

$acceptNoGo = Show-OperatorPrompt `
    -Title "PCB Go/No-Go 决策" `
    -Message "当前自动证据建议：继续 dev-board 迭代，暂不进入第一版 pendant PCB。`n`n点击 Yes 表示接受这个 no-go-for-PCB 建议；点击 No 表示你要推翻或修改这个决策。" `
    -Buttons ([System.Windows.Forms.MessageBoxButtons]::YesNo) `
    -Icon ([System.Windows.Forms.MessageBoxIcon]::Question)

if ($acceptNoGo -eq [System.Windows.Forms.DialogResult]::Yes) {
    $decision = "continue_dev_board_iteration_before_first_pendant_pcb"
    $decisionReason = "Operator accepted the current no-go-for-PCB recommendation after physical signoff prompts."
    $acceptedCurrentNoGo = $true
} else {
    $decision = Read-OperatorText -Title "请输入新的 PCB 决策" -Message "请输入 GO / NO-GO / ITERATE / CHANGE_PARTS，并补充一句原因。"
    $decisionReason = Read-OperatorText -Title "PCB 决策原因" -Message "请写明为什么推翻或修改当前 no-go-for-PCB 建议。"
    $acceptedCurrentNoGo = $false
}

$operatorNotes = Read-OperatorText -Title "补充说明" -Message "可选：记录照片/视频路径、仪表型号、异常现象、哪些硬件未安装。留空也可以。"
$finalConfirm = Show-OperatorPrompt `
    -Title "提交 Companion 物理验收 evidence" `
    -Message "请确认：刚才填写的是你真实看到和测到的结果。点击 Yes 会写入 JSON/Markdown evidence；点击 No 会写入取消状态。" `
    -Buttons ([System.Windows.Forms.MessageBoxButtons]::YesNo) `
    -Icon ([System.Windows.Forms.MessageBoxIcon]::Warning)

$allPhysicalPass = $true
foreach ($check in $physicalChecks) {
    if ($check.result -ne "PASS") { $allPhysicalPass = $false }
}
$allPowerMeasured = $true
foreach ($measurement in $powerMeasurements) {
    if (-not $measurement.measured) { $allPowerMeasured = $false }
}
$status = "PASS"
if ($finalConfirm -ne [System.Windows.Forms.DialogResult]::Yes) {
    $status = "CANCELLED"
} elseif (-not $allPhysicalPass -or -not $allPowerMeasured) {
    $status = "PENDING_HUMAN"
}

$finishedAt = (Get-Date).ToString("o")
$summary = [ordered]@{
    schema = "companion.physical_signoff.v1"
    status = $status
    started_at = $startedAt
    finished_at = $finishedAt
    operator = $operator
    repo_root = $repoRoot
    output_dir = $outDirResolved
    summary_json = $summaryJson
    summary_markdown = $summaryMd
    evidence_markdown = $evidenceMarkdownResolved
    prompt_transcript = $promptTranscript
    physical_checks = @($physicalChecks)
    power_measurements = @($powerMeasurements)
    physical_all_pass = $allPhysicalPass
    power_all_measured = $allPowerMeasured
    pcb_decision = [ordered]@{
        accepted_current_no_go = $acceptedCurrentNoGo
        decision = $decision
        reason = $decisionReason
    }
    operator_notes = $operatorNotes
}

$transcriptLines = @(
    "# Companion Physical Signoff Prompt Transcript",
    "",
    "- Started: $startedAt",
    "- Finished: $finishedAt",
    "- Operator: $operator",
    "- Final dialog: $finalConfirm",
    "",
    "## Intro Prompt",
    "",
    $intro
)
$transcriptLines | Set-Content -LiteralPath $promptTranscript -Encoding UTF8
$summary | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $summaryJson -Encoding UTF8
$md = ConvertTo-SignoffMarkdown -Summary ([pscustomobject]$summary)
$md | Set-Content -LiteralPath $summaryMd -Encoding UTF8
$md | Set-Content -LiteralPath $evidenceMarkdownResolved -Encoding UTF8

Write-Host "companion_physical_signoff_result_json=$($summary | ConvertTo-Json -Depth 10 -Compress)"
Write-Host "Summary: $summaryJson"
Write-Host "Markdown: $summaryMd"
Write-Host "Evidence: $evidenceMarkdownResolved"

if ($status -eq "CANCELLED") {
    throw "Companion physical signoff was cancelled by operator. See $summaryJson"
}

if ($status -ne "PASS") {
    Write-Warning "Companion physical signoff is not complete: status=$status. Evidence was recorded, but workflow should remain waiting."
}
