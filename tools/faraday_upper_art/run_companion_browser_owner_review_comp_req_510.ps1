#requires -Version 7.0
<#
.SYNOPSIS
Default-off owner review for the COMP-REQ-508/509/510 browser successor.

.DESCRIPTION
CheckOnly is filesystem-only. Execute requires explicit owner acknowledgement,
an exact reachable 4173 page, and a single prompt lock.
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
$validationRelative = "docs\validation\companion-browser-owner-review-ready-comp-req-508"
$validationDir = Join-Path $repoRoot $validationRelative
$pageRelative = "docs\art\iterations\companion-pet-expression-v9-two-track-rig-v7\candidate\wb55-browser-parity-attempt-01\index.html"
$reviewUrl = "http://127.0.0.1:4173/docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/candidate/wb55-browser-parity-attempt-01/index.html"
$pageSha = "9990C4316AF8F4D656F2C2B057AB789846A10CD21E18367336FC6BD277631EB7"
$machineSha = "94962CA64121D0BBE9BF69D45BAA6D20D4EEE4B54C8C7F6CB8868C69DB6BA911"
$negativeSha = "0656B0362536C1B029D1BB3154E0C5A567B08ABF8C61F3BBC1F5B3FD4680469F"
$replaySha = "8FCAD0AC4C5370EFBBBC6C3785B6E115AA1E77C69EA81C0E137207AC1D33721C"
$pixelSha = "91E6793F01B8368933E61115E93AD7280B435A9A1429D4B2DE743B61878BD1F3"
$screenshotSha = "1886C6193AE846C11116462A20A1DCDC093DB4BD65BED36C9B19CB762965460A"
$determinismSha = "EAE756749EDC2030D18CB349137598F2C33642BB381DD64F6CD12C4DE73A51DB"
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
请在总体页面实际操作：
1. 单点后表情与眼神朝触点响应一次；连续向左、右、上、下拖动并回中心，确认旧眼珠和高光被替换，没有残留或双层。
2. 原地长按进入菜单，点击四根菜单、Device > UI assets、Calm/Curious/Warm，再返回表情。
3. 用鼠标或触控双击进入录音，确认没有麦克风图标；声波向脸侧倾听点收拢，脸先专注倾听再进入安静思考。
4. 录音中单击不退出；再次双击恰好一次返回，并恢复进入前的表情和眼神。
5. 判断 200x200 屏幕居中、方向正确，始终只有一张脸、一套眼珠和高光，无 404、无多余调试参数。
"@
    expected_text = "选择通过表示本次 COMP-REQ-508/509/510 browser-only successor 可成为人工回归合同；选择失败会保留机器 PASS 并返回 Faraday 迭代。备注允许留空。"
}

function Get-Sha256 {
    param([Parameter(Mandatory = $true)][string] $Path)
    return (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToUpperInvariant()
}

function Resolve-WorkflowRoot {
    param([string] $Requested)
    $candidate = if (-not [string]::IsNullOrWhiteSpace($Requested)) {
        $Requested
    } elseif (-not [string]::IsNullOrWhiteSpace($env:AI_WORKFLOW_REPO)) {
        $env:AI_WORKFLOW_REPO
    } else {
        "C:\Users\Billy\Desktop\Denzic\ai-collaboration-workflow"
    }
    if (-not (Test-Path -LiteralPath (Join-Path $candidate "docs\agent_quickstart.md") -PathType Leaf)) {
        $candidate = "C:\Users\Billy\Desktop\Denzic\ai-collaboration-workflow"
    }
    return (Resolve-Path -LiteralPath $candidate).Path
}

function Get-Readiness {
    $bindings = [ordered]@{
        page = @($pageRelative, $pageSha)
        machine = @("$validationRelative\MACHINE_READY.json", $machineSha)
        negative = @("$validationRelative\source-bound-negative-result.json", $negativeSha)
        replay = @("$validationRelative\browser-replay-result.json", $replaySha)
        pixel = @("$validationRelative\pixel-dom-route-artifact.json", $pixelSha)
        screenshots = @("$validationRelative\screenshot-manifest.json", $screenshotSha)
        determinism = @("$validationRelative\clean-replay-determinism.json", $determinismSha)
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
        $negative = Get-Content -LiteralPath (Join-Path $validationDir "source-bound-negative-result.json") -Raw -Encoding UTF8 | ConvertFrom-Json
        $replay = Get-Content -LiteralPath (Join-Path $validationDir "browser-replay-result.json") -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($machine.status -ne "BROWSER_OWNER_REVIEW_READY_SUCCESSOR" -or @($machine.failed_checks).Count -ne 0) {
            $failures.Add("MACHINE_READY is not a clean successor PASS")
        }
        if ($negative.status -ne "PASS" -or [int]$negative.negative_count -ne 27 -or [int]$negative.rejected_count -ne 27) {
            $failures.Add("source-bound negative matrix is incomplete")
        }
        if ([int]$replay.totals.route_recording_entries -ne 12 -or
            [int]$replay.totals.route_recording_exits -ne 12 -or
            [int]$replay.totals.recording_negative_checks -ne 54) {
            $failures.Add("recording route/event totals are incomplete")
        }
        foreach ($counter in @("process", "browser", "popup", "hardware", "write")) {
            if ([int]$machine.side_effect_counters.$counter -ne 0) {
                $failures.Add("MACHINE_READY side-effect counter nonzero: $counter")
            }
        }
    }
    foreach ($path in @($ownerResultPath, $ownerRawPath, $ownerNotePath, $promptLockPath)) {
        if (Test-Path -LiteralPath $path) {
            $failures.Add("owner lifecycle file already exists: $([IO.Path]::GetFileName($path))")
        }
    }
    return [ordered]@{
        schema = "companion.browser-owner-review-checkonly.v2"
        requirements = @("COMP-REQ-508", "COMP-REQ-509", "COMP-REQ-510")
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
    return [pscustomobject]$readiness
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
        schema = "companion.browser-owner-review.v2"
        requirements = @("COMP-REQ-508", "COMP-REQ-509", "COMP-REQ-510")
        status = if ([string]$promptResult.selected -eq "通过") {
            "PASS_OWNER_BROWSER_EXPERIENCE_ACCEPTED"
        } else {
            "FAIL_OWNER_BROWSER_EXPERIENCE_RETURN_TO_ITERATION"
        }
        selected = [string]$promptResult.selected
        note = $note
        machine_ready = [ordered]@{
            path = "$($validationRelative.Replace('\', '/'))/MACHINE_READY.json"
            sha256 = $machineSha
        }
        page_sha256 = $pageSha
        url = $reviewUrl
    }
    $ownerRecord | ConvertTo-Json -Depth 12 |
        Set-Content -LiteralPath $ownerResultPath -Encoding utf8NoBOM
    return [pscustomobject]$ownerRecord
} catch {
    if ($promptAttempted -and -not (Test-Path -LiteralPath $ownerResultPath)) {
        [ordered]@{
            schema = "companion.browser-owner-review-fault.v1"
            status = "NO_GO"
            error = $_.Exception.Message
            raw_result_exists = Test-Path -LiteralPath $ownerRawPath
            note_exists = Test-Path -LiteralPath $ownerNotePath
        } | ConvertTo-Json -Depth 8 |
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
