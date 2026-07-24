#requires -Version 7.0
<#
.SYNOPSIS
Default-off owner review for the COMP-REQ-536/537/538 browser successor.

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
$validationRelative = "docs\validation\companion-browser-epaper-parity-successor-comp-req-536-538"
$validationDir = Join-Path $repoRoot $validationRelative
$pageRelative = "docs\art\iterations\companion-pet-expression-v9-two-track-rig-v7\candidate\wb55-browser-parity-attempt-01\index.html"
$reviewUrl = "http://127.0.0.1:4173/docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/candidate/wb55-browser-parity-attempt-01/index.html"
$ownerResultPath = Join-Path $validationDir "owner-review.json"
$ownerRawPath = Join-Path $validationDir "owner-review.raw.json"
$ownerNotePath = Join-Path $validationDir "owner-review.note.txt"
$ownerFaultPath = Join-Path $validationDir "owner-review-fault.json"
$promptLockPath = Join-Path $validationDir ".owner-review.prompt-active.lock"

$bindings = [ordered]@{
    page = @($pageRelative, "6176B9B3A7948291F430B5C47EBB5CDB2DA339BEEA86FBD1C72920D74438DD10", $true)
    machine = @("$validationRelative\MACHINE_READY.json", "988FBD722F28CFFCCCB425A5C4D0F63B5ABF34589C2F90327ED66BB986DB7676", $true)
    negatives = @("$validationRelative\source-bound-negatives.json", "03594FBCFB115E4DC069EC87CF7B11C190A57D413F6902018CCEED6192A4BFA5", $true)
    focused = @("$validationRelative\focused-oracle.json", "6F3E806C4703E677DE9E2D108F8D3241546D87D41D05D099731A89BCD1603271", $true)
    replay = @("$validationRelative\replay-run\browser-replay-result.json", "4108424DA67141EA31F7755CF3974CA982093B1D7B1FEE8A8263B25B9CDD5B26", $true)
    pixel = @("$validationRelative\replay-run\pixel-dom-route-artifact.json", "C44BB53F2D07BE61D5EE27521E9237412EC1CFADCFEE57D6C9ED3636BEBBBE2F", $true)
    screenshots = @("$validationRelative\replay-run\screenshot-manifest.json", "81C10D5E17A633AC8F2411C82658C3A05F60963BDDBB36D592DADE19C901512C", $true)
    parity = @("$validationRelative\parity-verifier.json", "D8CDA1082AC334FB4CEABB097D52EF8D6EFB9374455A8369A6720A848DC2EACB", $true)
    manifest = @("docs\art\exports\companion-browser-epaper-parity-comp-req-536-538\visual-frame-manifest.json", "198ED5AFBA59F06BE507E0BC6C1778363DB1E401AF17A8859A2A3D0665DB36DB", $true)
    source_gate = @("tools\faraday_upper_art\verify_companion_browser_epaper_source_bound_comp_req_536_538.py", "76077D1153265CDCAABC2B857268D2A8B3B8AE2C2A0AD29379C24D1FB71E2B1A", $true)
    negative_gate = @("tools\faraday_upper_art\test_companion_browser_epaper_source_bound_negatives_comp_req_536_538.py", "C0656F1B797D870C6CBE3704D3D5D0F5FD877F717E6326A9D0E9C47531B33021", $true)
}

$promptContract = [ordered]@{
    title = "Companion 浏览器总体体验验收"
    buttons = @("通过", "失败")
    progress_text = "1/1 浏览器总体体验"
    scope_text = "仅验收同一 4173 总体页面中的表情、菜单、录音附件与 200x200 墨水屏预览；browser-only。"
    message = @"
请在总体页面按正常速度实际操作：
1. 观察无操作时的确定性高光小动作：约每 480 ms 离散一步，短序列后精确回到基线，没有平滑插值或随机闪烁。
2. 严格双击开启录音附件：只增加一个小型录音状态标记和三道等高、等粗、等曲率的短波前；波前逐帧向脸旁听觉点收拢并吸收，再从外缘补入。
3. 录音附件开启时继续单点和拖动，确认底层表情与眼神照常响应，附件只出现一份，不冻结、不重启、不增加第二张脸或第二套眼珠。
4. 再次严格双击关闭，确认只移除录音附件，保留当时已经演化的表情和眼神。
5. 检查长按菜单、四根菜单、Device > UI assets、返回；始终居中、方向正确、无旧层、裁切、404、重叠、调试参数或麦克风权限请求。
"@
    expected_text = "选择通过表示 COMP-REQ-536/537/538 browser-only successor 成为人工回归合同；选择失败会保留机器证据并返回 Faraday 迭代。备注允许留空。"
}

function Get-CanonicalFileSha256 {
    param(
        [Parameter(Mandatory = $true)][string] $Path,
        [Parameter(Mandatory = $true)][bool] $IsText
    )
    $bytes = [IO.File]::ReadAllBytes($Path)
    if ($IsText) {
        $stream = [IO.MemoryStream]::new()
        try {
            for ($index = 0; $index -lt $bytes.Length; $index++) {
                if ($bytes[$index] -eq 13) {
                    if ($index + 1 -ge $bytes.Length -or $bytes[$index + 1] -ne 10) {
                        throw "Text identity contains a bare carriage return."
                    }
                    continue
                }
                $stream.WriteByte($bytes[$index])
            }
            $bytes = $stream.ToArray()
        } finally {
            $stream.Dispose()
        }
    }
    return [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($bytes))
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
    $failures = [System.Collections.Generic.List[string]]::new()
    $identities = [System.Collections.Generic.List[object]]::new()
    foreach ($entry in $bindings.GetEnumerator()) {
        $path = Join-Path $repoRoot $entry.Value[0]
        $observed = if (Test-Path -LiteralPath $path -PathType Leaf) {
            Get-CanonicalFileSha256 -Path $path -IsText ([bool]$entry.Value[2])
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
        $replay = Get-Content -LiteralPath (Join-Path $validationDir "replay-run\browser-replay-result.json") -Raw -Encoding UTF8 | ConvertFrom-Json
        $parity = Get-Content -LiteralPath (Join-Path $validationDir "parity-verifier.json") -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($machine.status -ne "MACHINE_READY" -or @($machine.failed_checks).Count -ne 0) {
            $failures.Add("machine gate is not a clean MACHINE_READY")
        }
        if ($machine.owner_gate -ne "PENDING") {
            $failures.Add("machine gate incorrectly claims owner completion")
        }
        if ($negative.status -ne "PASS" -or
            [int]$negative.negative_case_count -ne 17 -or
            [int]$negative.rejected_negative_count -ne 17) {
            $failures.Add("source-bound tamper matrix is incomplete")
        }
        if ($replay.status -ne "PASS" -or
            [int]$replay.counts.combinations -ne 6 -or
            [int]$replay.counts.scenarios -ne 42 -or
            [int]$replay.counts.microphone_requests -ne 0) {
            $failures.Add("42-scenario replay drifted")
        }
        if ($parity.status -ne "PASS" -or
            [int]$parity.observed.state_count -ne 71 -or
            -not [bool]$parity.checks.browser_to_c_pixel_diff_zero) {
            $failures.Add("browser/PBM/C parity drifted")
        }
    }
    foreach ($path in @($ownerResultPath, $ownerRawPath, $ownerNotePath, $promptLockPath)) {
        if (Test-Path -LiteralPath $path) {
            $failures.Add("owner lifecycle file already exists: $([IO.Path]::GetFileName($path))")
        }
    }
    return [ordered]@{
        schema = "companion.browser-owner-review-checkonly.v5"
        requirements = @("COMP-REQ-521", "COMP-REQ-536", "COMP-REQ-537", "COMP-REQ-538")
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
    $servedBytes = [Text.Encoding]::UTF8.GetBytes($response.Content)
    $servedPath = Join-Path $env:TEMP ("companion-owner-page-" + [guid]::NewGuid().ToString("N") + ".html")
    try {
        [IO.File]::WriteAllBytes($servedPath, $servedBytes)
        $servedSha = Get-CanonicalFileSha256 -Path $servedPath -IsText $true
    } finally {
        if (Test-Path -LiteralPath $servedPath) {
            Remove-Item -LiteralPath $servedPath -Force
        }
    }
    if ($response.StatusCode -ne 200 -or $servedSha -ne $bindings.page[1]) {
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
        schema = "companion.browser-owner-review.v1"
        requirements = @("COMP-REQ-536", "COMP-REQ-537", "COMP-REQ-538")
        selected = [string]$promptResult.selected
        note = $note.TrimEnd()
        machine_ready_sha256 = $bindings.machine[1]
        page_canonical_sha256 = $bindings.page[1]
        url = $reviewUrl
    }
    $ownerRecord | ConvertTo-Json -Depth 8 |
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
            machine_ready_sha256 = $bindings.machine[1]
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
