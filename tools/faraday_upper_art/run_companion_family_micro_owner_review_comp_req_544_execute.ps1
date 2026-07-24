#requires -Version 7.0
[CmdletBinding()]
param(
    [switch] $CheckOnly,
    [switch] $Execute,
    [switch] $OwnerStartAcknowledged,
    [Parameter(Mandatory = $true)]
    [ValidatePattern("^[0-9A-Fa-f]{64}$")]
    [string] $ExpectedPacketSha256,
    [ValidateRange(60, 3600)]
    [int] $OperatorTimeoutSeconds = 1800
)

$ErrorActionPreference = "Stop"
$modeCount = @($CheckOnly.IsPresent, $Execute.IsPresent).Where({ $_ }).Count
if ($modeCount -ne 1) { throw "Choose exactly one of -CheckOnly or -Execute." }
if ($Execute -and -not $OwnerStartAcknowledged) {
    throw "Execute requires -OwnerStartAcknowledged."
}

$repoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..\..")).Path
$validationDir = Join-Path $repoRoot "docs\validation\companion-browser-family-micro-choreography-comp-req-544"
$packetPath = Join-Path $validationDir "owner-review-packet.json"
$resultPath = Join-Path $validationDir "owner-review.json"
$rawPath = Join-Path $validationDir "owner-review.raw.json"
$notePath = Join-Path $validationDir "owner-review.note.txt"
$faultPath = Join-Path $validationDir "owner-review-fault.json"
$lockPath = Join-Path $validationDir ".owner-review.prompt-active.lock"
$url = "http://127.0.0.1:4173/docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/candidate/wb55-browser-parity-attempt-01/index.html"

function Get-Sha256([string] $Path) {
    return (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash
}

function Get-Readiness {
    $failures = [Collections.Generic.List[string]]::new()
    if (-not (Test-Path -LiteralPath $packetPath -PathType Leaf)) {
        $failures.Add("packet missing")
        return [ordered]@{ status = "NO_GO"; failures = @($failures) }
    }
    $packetSha = Get-Sha256 $packetPath
    if ($packetSha -ne $ExpectedPacketSha256.ToUpperInvariant()) {
        $failures.Add("packet SHA mismatch")
    }
    $packet = Get-Content -Raw -Encoding UTF8 -LiteralPath $packetPath |
        ConvertFrom-Json -Depth 30
    if ($packet.status -ne "READY_DEFAULT_OFF" -or
        [bool]$packet.execute_authorized) {
        $failures.Add("packet is not default-off")
    }
    foreach ($binding in $packet.bindings) {
        $path = Join-Path $repoRoot ([string]$binding.path).Replace("/", "\")
        if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
            $failures.Add("binding missing: $($binding.id)")
        } elseif ((Get-Sha256 $path) -ne ([string]$binding.sha256).ToUpperInvariant()) {
            $failures.Add("binding drift: $($binding.id)")
        }
    }
    foreach ($path in @($resultPath, $rawPath, $notePath, $lockPath)) {
        if (Test-Path -LiteralPath $path) {
            $failures.Add("owner lifecycle exists: $([IO.Path]::GetFileName($path))")
        }
    }
    return [ordered]@{
        status = if ($failures.Count) { "NO_GO" } else { "PASS_CHECKONLY_NO_EXECUTE" }
        packet_sha256 = $packetSha
        failures = @($failures)
        counters = [ordered]@{
            process = 0; browser = 0; popup = 0; owner_prompt = 0
            hardware_contact = 0; write = 0; microphone_permission_request = 0
        }
    }
}

$readiness = Get-Readiness
if ($CheckOnly) {
    $readiness | ConvertTo-Json -Depth 10
    if ($readiness.status -ne "PASS_CHECKONLY_NO_EXECUTE") { exit 1 }
    exit 0
}
if ($readiness.status -ne "PASS_CHECKONLY_NO_EXECUTE") {
    throw ($readiness.failures -join "; ")
}

$lock = $null
$promptAttempted = $false
try {
    $response = Invoke-WebRequest -UseBasicParsing -Uri $url -TimeoutSec 3
    if ($response.StatusCode -ne 200) { throw "review page unavailable" }
    $lock = [IO.File]::Open(
        $lockPath, [IO.FileMode]::CreateNew, [IO.FileAccess]::ReadWrite,
        [IO.FileShare]::None
    )
    $null = Start-Process -FilePath $url -PassThru
    $workflowRoot = if (
        $env:AI_WORKFLOW_REPO -and
        (Test-Path -LiteralPath (Join-Path $env:AI_WORKFLOW_REPO "scripts\aiw.ps1"))
    ) { $env:AI_WORKFLOW_REPO } else {
        "C:\Users\Billy\Desktop\Denzic\ai-collaboration-workflow"
    }
    $promptAttempted = $true
    $promptOutput = & pwsh -NoProfile -File (Join-Path $workflowRoot "scripts\aiw.ps1") operator-prompt `
        -Title "Companion 非眨眼动态编舞验收" `
        -ProgressText "请至少观察 12 秒，并切换几种表情体验。" `
        -ScopeText "仅验收 200x200 表情动态、慢眨眼及既有手势。" `
        -Message "平时应由眼神、眉、嘴角和脸颊形成各表情自己的动态编舞；眨眼约八秒才出现一次，并以四个墨水屏离散帧缓慢完成。请同时试单击、拖动、双击录音和三秒长按菜单。" `
        -ExpectedText "“通过”表示没有任何仍需修改的问题；仅看过候选不能选择“通过”。若还有动作过快、过慢、机械、静止或其他质量问题，请选择“失败”并写备注。" `
        -ObservationLabel "备注（失败时请写出最明显的可见问题）" `
        -ReviewStyle -Input -Buttons "通过,失败" -OutputPath $notePath `
        -TimeoutSeconds $OperatorTimeoutSeconds -Json
    $rawText = $promptOutput -join [Environment]::NewLine
    Set-Content -LiteralPath $rawPath -Value $rawText -Encoding utf8NoBOM
    if ($LASTEXITCODE -ne 0) { throw "operator-prompt failed: $LASTEXITCODE" }
    $promptResult = $rawText | ConvertFrom-Json
    if (@("通过", "失败") -notcontains [string]$promptResult.selected) {
        throw "invalid owner selection"
    }
    $note = if (Test-Path -LiteralPath $notePath) {
        Get-Content -Raw -Encoding UTF8 -LiteralPath $notePath
    } else { "" }
    $blocking = $note -match "必须修改|需要修改|请修改|失败|问题|不通过|缺陷|太快|太慢|机械|静止"
    $accepted = [string]$promptResult.selected -eq "通过" -and -not $blocking
    $packet = Get-Content -Raw -Encoding UTF8 -LiteralPath $packetPath |
        ConvertFrom-Json -Depth 30
    [ordered]@{
        schema = "companion.family-micro-owner-review.comp-req-544.v1"
        requirement = "COMP-REQ-544"
        selected = [string]$promptResult.selected
        note = $note.TrimEnd()
        blocking_note = $blocking
        accepted = $accepted
        status = if ($accepted) { "ACCEPTED_OWNER_PASS" } else {
            "NOT_ACCEPTED_OWNER_CHANGES_REQUIRED"
        }
        machine_ready_sha256 = [string]$packet.machine_ready_sha256
        packet_sha256 = $ExpectedPacketSha256.ToUpperInvariant()
        candidate_sha256 = [string]$packet.candidate_sha256
        url = $url
    } | ConvertTo-Json -Depth 8 |
        Set-Content -LiteralPath $resultPath -Encoding utf8NoBOM
    Get-Content -Raw -Encoding UTF8 -LiteralPath $resultPath
} catch {
    if (-not (Test-Path -LiteralPath $resultPath)) {
        [ordered]@{
            schema = "companion.family-micro-owner-review-fault.comp-req-544.v1"
            status = "FAULT"
            error = $_.Exception.Message
            prompt_attempted = $promptAttempted
        } | ConvertTo-Json -Depth 6 |
            Set-Content -LiteralPath $faultPath -Encoding utf8NoBOM
    }
    throw
} finally {
    if ($null -ne $lock) { $lock.Dispose() }
    if (Test-Path -LiteralPath $lockPath) {
        Remove-Item -LiteralPath $lockPath -Force
    }
}
