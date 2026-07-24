#requires -Version 7.0
<#
.SYNOPSIS
Default-off owner review for the COMP-REQ-533/534 browser successor.

.DESCRIPTION
CheckOnly is offline and read-only. Execute requires explicit acknowledgement,
an already-running exact 4173 page, and one canonical Chinese operator prompt.
#>

[CmdletBinding()]
param(
    [switch] $CheckOnly,
    [switch] $Execute,
    [switch] $OwnerStartAcknowledged,
    [ValidateRange(60, 3600)]
    [int] $OperatorTimeoutSeconds = 1800,
    [string] $WorkflowRepo = ""
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$modeCount = @($CheckOnly.IsPresent, $Execute.IsPresent).Where({ $_ }).Count
if ($modeCount -ne 1) {
    throw "Default-off: choose exactly one of -CheckOnly or -Execute."
}
if ($Execute -and -not $OwnerStartAcknowledged) {
    throw "Execute requires explicit -OwnerStartAcknowledged."
}

$repoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..\..")).Path
$validationRelative = "docs\validation\companion-browser-three-wave-state-view-successor-comp-req-533-534"
$validationDir = Join-Path $repoRoot $validationRelative
$pageRelative = "docs\art\iterations\companion-pet-expression-v9-two-track-rig-v7\candidate\wb55-browser-parity-attempt-01\index.html"
$reviewUrl = "http://127.0.0.1:4173/docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/candidate/wb55-browser-parity-attempt-01/index.html"
$pageSha = "0C29D5FF40D80C41461F0738C1C747A6C2B27A5DA74B5C79E166621A7566D9DA"
$machineSha = "97F757617A7828B61B11FEC3621861820C088C8047CD1836EC473680844BBB8A"
$negativeSha = "49407A5D461375E1B467B787CAB6A79F760011FC6F79190D4645CD6EB8013AD6"
$replaySha = "842073FF357B7ADF03775B432E87C67B45824F6EC271FE59D5B7CE46A05CF94C"
$pixelSha = "21CA3E864CE8523C497F38ABC758B1ADE34BB92EF755F63D9DFA2FC7A4F5B4F6"
$screenshotSha = "4806A36D7E0BA0C456CA588888E237911D8D5B46B55F0B9E1B6DA238976A8BC5"
$determinismSha = "7A65317B4FF4296543AF94D0D16662C6D4464726328BB9F172BE0ACFEA3674A7"
$focusedSha = "9FC4A390A71A431029A3B50E6DC117D441D832694E7BDEA5E53A11A306DE7626"
$ownerResultPath = Join-Path $validationDir "owner-review.json"
$ownerRawPath = Join-Path $validationDir "owner-review.raw.json"
$ownerNotePath = Join-Path $validationDir "owner-review.note.txt"
$ownerFaultPath = Join-Path $validationDir "owner-review-fault.json"
$promptLockPath = Join-Path $validationDir ".owner-review.prompt-active.lock"

$promptContract = [ordered]@{
    title = "Companion 浏览器总体体验验收"
    buttons = @("通过", "失败")
    progress_text = "1/1 浏览器总体体验"
    scope_text = "仅验收同一 4173 总体页面中的表情、菜单与录音预览；browser-only，不接触硬件或 production。"
    message = @"
请在总体页面按正常速度实际操作：
1. 严格双击进入录音，确认全程是同一张稳定倾听脸，只有一个小型录音状态图标。
2. 确认每个录音帧恰好三道黑白波弧；每道凸面朝脸旁倾听点，约每 480 ms 离散向内一步，吸收后才从外缘重启，没有平滑插值或向外跳。
3. 再次严格双击退出，确认精确恢复进入前的表情和眼神；单点、拖动、长按菜单、Device > UI assets 与菜单返回保持原行为。
4. 查看 200x200 真屏旁的中文状态图：持续情感、交互模式、过渡阶段、触发事件、合法后续与页面实际变化同步；真屏内部无说明和调试参数。
5. 判断所有表情共享同一视觉锚点，切换不跳位、不裁切，始终一张脸、一套眼珠与高光，无旧层、404、重叠或麦克风权限请求。
"@
    expected_text = "选择通过表示 COMP-REQ-533/534 browser-only successor 成为人工回归合同；选择失败会保留机器证据并返回 Faraday 迭代。备注允许留空。"
}

function Get-Sha256 {
    param([Parameter(Mandatory = $true)][string] $Path)
    return (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToUpperInvariant()
}

function Resolve-WorkflowRoot {
    param([string] $Requested)
    $fallback = "C:\Users\Billy\Desktop\Denzic\ai-collaboration-workflow"
    $candidate = if (-not [string]::IsNullOrWhiteSpace($Requested)) {
        $Requested
    } elseif (-not [string]::IsNullOrWhiteSpace($env:AI_WORKFLOW_REPO)) {
        $env:AI_WORKFLOW_REPO
    } else {
        $fallback
    }
    if (-not (Test-Path -LiteralPath (Join-Path $candidate "docs\agent_quickstart.md") -PathType Leaf)) {
        $candidate = $fallback
    }
    return (Resolve-Path -LiteralPath $candidate).Path
}

function Get-Readiness {
    $bindings = [ordered]@{
        page = @($pageRelative, $pageSha)
        machine = @("$validationRelative\MACHINE_READY.json", $machineSha)
        negative = @("$validationRelative\source-bound-negatives.json", $negativeSha)
        replay = @("$validationRelative\determinism-run\browser-replay-result.json", $replaySha)
        pixel = @("$validationRelative\determinism-run\pixel-dom-route-artifact.json", $pixelSha)
        screenshots = @("$validationRelative\determinism-run\screenshot-manifest.json", $screenshotSha)
        determinism = @("$validationRelative\deterministic-replay-receipt.json", $determinismSha)
        focused = @("$validationRelative\after-fix\geometry-temporal-state-oracle.json", $focusedSha)
    }
    $failures = [System.Collections.Generic.List[string]]::new()
    $identities = [System.Collections.Generic.List[object]]::new()
    foreach ($entry in $bindings.GetEnumerator()) {
        $path = Join-Path $repoRoot $entry.Value[0]
        $observed = if (Test-Path -LiteralPath $path -PathType Leaf) {
            Get-Sha256 -Path $path
        } else {
            $null
        }
        if ($observed -ne $entry.Value[1]) {
            $failures.Add("binding drift: $($entry.Key)")
        }
        $identities.Add([ordered]@{
            id = $entry.Key
            path = $entry.Value[0].Replace("\", "/")
            expected_sha256 = $entry.Value[1]
            observed_sha256 = $observed
            match = $observed -eq $entry.Value[1]
        })
    }
    if ($failures.Count -eq 0) {
        $machine = Get-Content -LiteralPath (Join-Path $validationDir "MACHINE_READY.json") -Raw -Encoding UTF8 | ConvertFrom-Json
        $negative = Get-Content -LiteralPath (Join-Path $validationDir "source-bound-negatives.json") -Raw -Encoding UTF8 | ConvertFrom-Json
        $replay = Get-Content -LiteralPath (Join-Path $validationDir "determinism-run\browser-replay-result.json") -Raw -Encoding UTF8 | ConvertFrom-Json
        $determinism = Get-Content -LiteralPath (Join-Path $validationDir "deterministic-replay-receipt.json") -Raw -Encoding UTF8 | ConvertFrom-Json
        $focused = Get-Content -LiteralPath (Join-Path $validationDir "after-fix\geometry-temporal-state-oracle.json") -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($machine.status -ne "MACHINE_READY" -or @($machine.failed_checks).Count -ne 0) {
            $failures.Add("MACHINE_READY is not a clean source-bound PASS")
        }
        if ($negative.status -ne "PASS" -or
            [int]$negative.negative_case_count -ne 16 -or
            [int]$negative.rejected_negative_count -ne 16) {
            $failures.Add("source-bound negative matrix is incomplete")
        }
        if ($determinism.status -ne "PASS_TWO_CLEAN_REPLAYS_BYTE_IDENTICAL" -or
            -not [bool]$determinism.byte_identical -or
            $determinism.run_a.aggregate_sha256 -ne $determinism.run_b.aggregate_sha256) {
            $failures.Add("clean replay determinism is not byte-identical")
        }
        if ([int]$replay.totals.replay_combinations -ne 6 -or
            [int]$replay.totals.scenario_count -ne 42 -or
            [int]$replay.totals.snapshot_count -ne 258 -or
            [int]$replay.totals.natural_bridge_ordered -ne 6 -or
            [int]$replay.totals.recording_negative_checks -ne 54 -or
            [int]$replay.totals.stale_pupil_pixel_count -ne 0 -or
            [int]$replay.totals.microphone_requests -ne 0) {
            $failures.Add("replay semantic totals drifted")
        }
        if ($focused.status -ne "PASS" -or
            @($focused.failed_checks).Count -ne 0 -or
            [int]$focused.observed.contractStepMs -ne 480 -or
            @($focused.observed.arcIdentities).Count -ne 3) {
            $failures.Add("focused geometry/temporal oracle drifted")
        }
    }
    foreach ($path in @($ownerResultPath, $ownerRawPath, $ownerNotePath, $promptLockPath)) {
        if (Test-Path -LiteralPath $path) {
            $failures.Add("owner lifecycle file already exists: $([IO.Path]::GetFileName($path))")
        }
    }
    return [ordered]@{
        schema = "companion.browser-owner-review-checkonly.v4"
        requirements = @("COMP-REQ-521", "COMP-REQ-533", "COMP-REQ-534")
        status = if ($failures.Count -eq 0) { "PASS_CHECKONLY_NO_EXECUTE" } else { "NO_GO" }
        default_off = $true
        execute_performed = $false
        url = $reviewUrl
        prompt_contract = $promptContract
        identities = @($identities)
        failures = @($failures)
        counters = [ordered]@{
            process = 0
            browser = 0
            popup = 0
            hardware = 0
            write = 0
            microphone_permission_request = 0
            server_start = 0
            owner_prompt = 0
        }
    }
}

if ($CheckOnly) {
    $readiness = Get-Readiness
    if ($readiness.status -ne "PASS_CHECKONLY_NO_EXECUTE") {
        throw ($readiness.failures -join "; ")
    }
    $readiness | ConvertTo-Json -Depth 12
    exit 0
}

$lock = $null
$promptAttempted = $false
try {
    $readiness = Get-Readiness
    if ($readiness.status -ne "PASS_CHECKONLY_NO_EXECUTE") {
        throw ($readiness.failures -join "; ")
    }
    $response = Invoke-WebRequest -UseBasicParsing -Uri $reviewUrl -TimeoutSec 8
    $servedSha = [Convert]::ToHexString(
        [Security.Cryptography.SHA256]::HashData(
            [Text.Encoding]::UTF8.GetBytes($response.Content)
        )
    )
    if ($response.StatusCode -ne 200 -or $servedSha -ne $pageSha) {
        throw "Exact 4173 successor page is not reachable."
    }
    $lock = [IO.File]::Open(
        $promptLockPath,
        [IO.FileMode]::CreateNew,
        [IO.FileAccess]::ReadWrite,
        [IO.FileShare]::None
    )
    $null = Start-Process -FilePath $reviewUrl -PassThru
    $workflowRoot = Resolve-WorkflowRoot -Requested $WorkflowRepo
    $aiwPath = Join-Path $workflowRoot "scripts\aiw.ps1"
    $promptAttempted = $true
    $promptOutput = & pwsh -NoProfile -File $aiwPath operator-prompt `
        -Title $promptContract.title `
        -ProgressText $promptContract.progress_text `
        -ScopeText $promptContract.scope_text `
        -Message $promptContract.message `
        -ExpectedText $promptContract.expected_text `
        -ObservationLabel "备注（可留空；失败时请写出可见问题）" `
        -ReviewStyle -Input -Buttons "通过,失败" `
        -OutputPath $ownerNotePath `
        -TimeoutSeconds $OperatorTimeoutSeconds `
        -Json
    $rawText = $promptOutput -join [Environment]::NewLine
    Set-Content -LiteralPath $ownerRawPath -Value $rawText -Encoding utf8NoBOM
    if ($LASTEXITCODE -ne 0) {
        throw "Canonical aiw operator-prompt failed with exit code $LASTEXITCODE."
    }
    $promptResult = $rawText | ConvertFrom-Json
    if (@("通过", "失败") -notcontains [string]$promptResult.selected) {
        throw "Canonical prompt returned an invalid selection."
    }
    $note = if (Test-Path -LiteralPath $ownerNotePath -PathType Leaf) {
        Get-Content -LiteralPath $ownerNotePath -Raw -Encoding UTF8
    } else {
        ""
    }
    $ownerRecord = [ordered]@{
        schema = "companion.browser-owner-review.v4"
        requirements = @("COMP-REQ-521", "COMP-REQ-533", "COMP-REQ-534")
        status = if ([string]$promptResult.selected -eq "通过") {
            "PASS_OWNER_BROWSER_EXPERIENCE_ACCEPTED"
        } else {
            "FAIL_OWNER_BROWSER_EXPERIENCE_REJECTED"
        }
        selected = [string]$promptResult.selected
        note = $note
        note_sha256 = Get-Sha256 -Path $ownerNotePath
        raw_sha256 = Get-Sha256 -Path $ownerRawPath
        machine_ready_sha256 = $machineSha
        page_sha256 = $pageSha
        url = $reviewUrl
        prompt_contract = $promptContract
    }
    $ownerRecord | ConvertTo-Json -Depth 12 |
        Set-Content -LiteralPath $ownerResultPath -Encoding utf8NoBOM
    $ownerRecord
} catch {
    if (-not (Test-Path -LiteralPath $ownerResultPath -PathType Leaf)) {
        $fault = [ordered]@{
            schema = "companion.browser-owner-review-fault.v1"
            status = "FAULT"
            error = $_.Exception.Message
            prompt_attempted = $promptAttempted
            raw_exists = Test-Path -LiteralPath $ownerRawPath
            note_exists = Test-Path -LiteralPath $ownerNotePath
            machine_ready_sha256 = $machineSha
        }
        $fault | ConvertTo-Json -Depth 6 |
            Set-Content -LiteralPath $ownerFaultPath -Encoding utf8NoBOM
    }
    throw
} finally {
    if ($null -ne $lock) {
        $lock.Dispose()
    }
    if (Test-Path -LiteralPath $promptLockPath) {
        Remove-Item -LiteralPath $promptLockPath -Force
    }
}
