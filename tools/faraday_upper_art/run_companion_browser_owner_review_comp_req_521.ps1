#requires -Version 7.0
<#
.SYNOPSIS
Default-off owner review for the COMP-REQ-508/518/520/521 browser successor.

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
$validationRelative = "docs\validation\companion-browser-natural-expression-successor-comp-req-518-520-521"
$validationDir = Join-Path $repoRoot $validationRelative
$pageRelative = "docs\art\iterations\companion-pet-expression-v9-two-track-rig-v7\candidate\wb55-browser-parity-attempt-01\index.html"
$reviewUrl = "http://127.0.0.1:4173/docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/candidate/wb55-browser-parity-attempt-01/index.html"
$pageSha = "24B5720F14B6793B201C4E74AD8BDB2219EE4F8CC941454983876979DA9ADAB1"
$machineSha = "16973DD68F45E0897AA7C0F7D5003A51EE9C095C599C55820E82625445B1DCC4"
$negativeSha = "1161156D89BEC5CB12B4AB4928E699214B0A80C915A41FD0AB13EB0CC543ECAF"
$replaySha = "50027010EC4923ADD5B73B71F56DFBEA48DF0268427955F34D48C1B368913B37"
$pixelSha = "1688A1FF837A9F771E6950967F5891F5922D432180392863CAA431EAC8116382"
$screenshotSha = "4E577A7C4E65A5C349B88C887CC59BE7446B10B62EC06CE255D4F17BF5500651"
$determinismSha = "FC290AAFB6CEB203F885B81992DE63895AD026A8F0B2BC6FCA6B6B41FF383330"
$focusedRecordingSha = "60EF928EE104035F1DE7756A0600A499A6B9A84D28869BDB8AB9A1A1290C526E"
$focusedNaturalSha = "93A1D3BF6D701A74007CCE5E5F9C1556630D3AAA7BCD5DD16C63718593BD5A4A"
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
1. 单点后先朝触点定向，等待约 650 ms，确认表情自然过渡一次；连续向左、右、上、下拖动并回中心，确认旧眼珠和高光被替换，无残留或双层。
2. 原地长按看进度饰品并进入菜单，点击四根菜单、Device > UI assets、Calm/Curious/Warm，再返回表情。
3. 严格双击进入录音，确认全程只有同一张稳定倾听脸；波纹只从外侧向脸旁倾听点收拢并吸收，紧凑录音状态图标只出现一次，没有大麦克风图形，也不会自动进入思考脸。
4. 录音中单击不退出；再次严格双击恰好一次返回，并精确恢复进入前的表情和眼神。
5. 判断 200x200 屏幕居中、方向正确，始终只有一张脸、一套眼珠和高光，无 404、无多余调试参数。
"@
    expected_text = "选择通过表示本次 COMP-REQ-508/518/520/521 browser-only successor 可成为人工回归合同；选择失败会保留机器证据并返回 Faraday 迭代。备注允许留空。"
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
        focused_recording = @("$validationRelative\focused-recording-temporal.json", $focusedRecordingSha)
        focused_natural = @("$validationRelative\focused-natural-expression.json", $focusedNaturalSha)
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
        if ($machine.status -ne "MACHINE_READY" -or @($machine.failed_checks).Count -ne 0) {
            $failures.Add("MACHINE_READY is not a clean source-bound PASS")
        }
        if ($negative.status -ne "PASS" -or
            [int]$negative.negative_case_count -ne 19 -or
            [int]$negative.rejected_negative_count -ne 19) {
            $failures.Add("source-bound negative matrix is incomplete")
        }
        if ($determinism.status -ne "PASS_TWO_CLEAN_REPLAYS_BYTE_IDENTICAL" -or
            -not [bool]$determinism.byte_identical -or
            $determinism.run_a.aggregate_sha256 -ne $determinism.run_b.aggregate_sha256) {
            $failures.Add("clean replay determinism is not a byte-identical PASS")
        }
        if ([int]$replay.totals.scenario_count -ne 42 -or
            [int]$replay.totals.snapshot_count -ne 258 -or
            [int]$replay.totals.recording_negative_checks -ne 54 -or
            [int]$replay.totals.stale_pupil_pixel_count -ne 0 -or
            [int]$replay.totals.microphone_requests -ne 0) {
            $failures.Add("replay semantic totals drifted")
        }
    }
    foreach ($path in @($ownerResultPath, $ownerRawPath, $ownerNotePath, $promptLockPath)) {
        if (Test-Path -LiteralPath $path) {
            $failures.Add("owner lifecycle file already exists: $([IO.Path]::GetFileName($path))")
        }
    }
    return [ordered]@{
        schema = "companion.browser-owner-review-checkonly.v3"
        requirements = @("COMP-REQ-508", "COMP-REQ-518", "COMP-REQ-520", "COMP-REQ-521")
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
        schema = "companion.browser-owner-review.v3"
        requirements = @("COMP-REQ-508", "COMP-REQ-518", "COMP-REQ-520", "COMP-REQ-521")
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
