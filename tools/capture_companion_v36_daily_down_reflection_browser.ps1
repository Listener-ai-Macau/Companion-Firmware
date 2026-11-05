#requires -Version 7.0
[CmdletBinding()]
param(
    [string]$PreviewPath = "docs\art\iterations\companion-pet-expression-v9-extension-v36-directional-eye-gaze-source\candidate\component-export-attempt-09\preview\daily-down-reflection-player.html",
    [string]$PreviewGatePath = "docs\validation\companion-v36-daily-down-reflection-browser-preview-20260720.json",
    [string]$OutputDir = "docs\art\iterations\companion-pet-expression-v9-extension-v36-directional-eye-gaze-source\candidate\component-export-attempt-09\preview\browser-captures",
    [string]$ReportPath = "docs\validation\companion-v36-daily-down-reflection-browser-capture-20260720.json",
    [ValidateRange(1, 60)]
    [int]$TimeoutSeconds = 20
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $repoRoot
$preview = (Resolve-Path $PreviewPath).Path
$previewGate = (Resolve-Path $PreviewGatePath).Path
$output = [System.IO.Path]::GetFullPath((Join-Path $repoRoot $OutputDir))
$report = [System.IO.Path]::GetFullPath((Join-Path $repoRoot $ReportPath))
$edge = "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
if (-not (Test-Path -LiteralPath $edge)) { throw "Missing Edge headless executable: $edge" }
New-Item -ItemType Directory -Force -Path $output | Out-Null

$cacheRoot = [System.IO.Path]::GetFullPath((Join-Path $repoRoot ".cache"))
New-Item -ItemType Directory -Force -Path $cacheRoot | Out-Null
$samples = @(
    [ordered]@{ phase = "rest"; virtual_time_ms = 400 },
    [ordered]@{ phase = "eyes_lower_1"; virtual_time_ms = 2270 },
    [ordered]@{ phase = "eyes_lower_2"; virtual_time_ms = 2430 },
    [ordered]@{ phase = "down_hold"; virtual_time_ms = 2700 },
    [ordered]@{ phase = "eyes_return"; virtual_time_ms = 3460 },
    [ordered]@{ phase = "rest_dwell"; virtual_time_ms = 3700 }
)

$captures = @()
foreach ($sample in $samples) {
    $shot = Join-Path $output ("v36-daily-down-browser-" + $sample.phase + ".png")
    $profile = Join-Path $cacheRoot ("v36-daily-down-browser-" + [Guid]::NewGuid().ToString("N"))
    $profileFull = [System.IO.Path]::GetFullPath($profile)
    if (-not $profileFull.StartsWith($cacheRoot + [System.IO.Path]::DirectorySeparatorChar, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to use a browser profile outside repository cache: $profileFull"
    }
    Remove-Item -LiteralPath $shot -Force -ErrorAction SilentlyContinue
    $process = $null
    try {
        $url = "file:///" + ($preview -replace "\\", "/") + "?capture=" + $sample.phase
        $process = Start-Process -FilePath $edge -ArgumentList @(
            "--headless=new", "--disable-gpu", "--hide-scrollbars", "--run-all-compositor-stages-before-draw",
            "--virtual-time-budget=$($sample.virtual_time_ms)", "--window-size=640,560",
            "--user-data-dir=$profileFull", "--screenshot=$shot", $url
        ) -PassThru -WindowStyle Hidden
        $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
        while (-not (Test-Path -LiteralPath $shot) -and (Get-Date) -lt $deadline) {
            if ($process.WaitForExit(200)) { break }
        }
        if (-not (Test-Path -LiteralPath $shot)) {
            $exitCode = if ($process.HasExited) { $process.ExitCode } else { "timeout" }
            throw "Edge did not create screenshot for $($sample.phase) before $TimeoutSeconds s (exit=$exitCode)"
        }
        if ($process.HasExited -and $process.ExitCode -ne 0) {
            throw "Edge capture failed for $($sample.phase) with $($process.ExitCode)"
        }
    }
    finally {
        if ($null -ne $process -and -not $process.HasExited) {
            Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
            $process.WaitForExit(2000) | Out-Null
        }
        if (Test-Path -LiteralPath $profileFull) {
            Remove-Item -LiteralPath $profileFull -Recurse -Force -ErrorAction Stop
        }
    }
    $item = Get-Item -LiteralPath $shot
    if ($item.Length -lt 1000) { throw "Edge screenshot is unexpectedly small for $($sample.phase): $($item.Length)" }
    $captures += $shot
}

& python tools\verify_companion_v36_daily_down_reflection_browser_capture.py `
    --preview-gate $previewGate `
    --write $report `
    --capture $captures
if ($LASTEXITCODE -ne 0) { throw "V36 Daily-down browser capture verification failed." }
Write-Output "PASS: Edge rendered every V36 Daily-down component choreography phase at native 200x200 parity."
