#requires -Version 7.0
[CmdletBinding()]
param(
    [string]$PreviewPath = "docs\art\iterations\companion-pet-expression-v9-extension-v15-sleep-rig-pose-source\candidate\dynamic-proof-attempt-01\preview.html",
    [string]$OutputDir = "docs\art\iterations\companion-pet-expression-v9-extension-v15-sleep-rig-pose-source\candidate\dynamic-proof-attempt-01",
    [ValidateRange(1, 60)]
    [int]$TimeoutSeconds = 20,
    [switch]$AssertOneShotStatic
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $repoRoot
$preview = (Resolve-Path $PreviewPath).Path
$output = [System.IO.Path]::GetFullPath((Join-Path $repoRoot $OutputDir))
$edge = "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
if (-not (Test-Path -LiteralPath $edge)) { throw "Missing Edge headless executable: $edge" }
New-Item -ItemType Directory -Force -Path $output | Out-Null

function Capture-Phase {
    param([string]$Phase)
    $shot = Join-Path $output "browser-$Phase.png"
    $profile = Join-Path $repoRoot (".cache\v15-sleep-browser-" + $Phase)
    $url = "file:///" + ($preview -replace "\\", "/") + "?phase=$Phase"
    Remove-Item -LiteralPath $shot -Force -ErrorAction SilentlyContinue
    $process = Start-Process -FilePath $edge -ArgumentList @(
        "--headless=new", "--disable-gpu", "--hide-scrollbars", "--run-all-compositor-stages-before-draw",
        "--virtual-time-budget=1000", "--window-size=1280,840",
        "--user-data-dir=$profile", "--screenshot=$shot", $url
    ) -PassThru -Wait -WindowStyle Hidden
    if ($process.ExitCode -ne 0) { throw "Edge capture failed for $Phase with $($process.ExitCode)" }
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while (-not (Test-Path -LiteralPath $shot) -and (Get-Date) -lt $deadline) { Start-Sleep -Milliseconds 200 }
    if (-not (Test-Path -LiteralPath $shot)) { throw "Edge did not create screenshot for $Phase" }
    $item = Get-Item -LiteralPath $shot
    if ($item.Length -lt 4000) { throw "Edge screenshot is unexpectedly small for ${Phase}: $($item.Length)" }
    $darkPixels = [int](& python -c "from PIL import Image; import sys; im=Image.open(sys.argv[1]).convert('RGB').crop((150,20,773,643)); print(sum(1 for r,g,b in im.getdata() if r<80 and g<80 and b<80))" $shot)
    if ($LASTEXITCODE -ne 0 -or $darkPixels -lt 4500) { throw "Edge screenshot did not render V15 component layers for ${Phase}: dark_pixels=$darkPixels" }
    return [ordered]@{ phase = $Phase; path = $shot; sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $shot).Hash.ToUpperInvariant(); bytes = $item.Length; screen_dark_pixels = $darkPixels }
}

function Assert-OneShotStatic {
    $profile = Join-Path $repoRoot ".cache\v15-sleep-browser-one-shot"
    $url = "file:///" + ($preview -replace "\\", "/")
    $dom = & $edge "--headless=new" "--disable-gpu" "--run-all-compositor-stages-before-draw" "--virtual-time-budget=10000" `
        "--user-data-dir=$profile" "--dump-dom" $url
    if ($LASTEXITCODE -ne 0) { throw "Edge default replay DOM capture failed with $LASTEXITCODE" }
    if ($dom -notmatch '<div id="phase">settle-01-of-01</div>') {
        throw "Edge did not settle the one-shot V15 preview after the finite replay."
    }
    return "settle-01-of-01"
}

$captures = @((Capture-Phase -Phase "entry"), (Capture-Phase -Phase "response"), (Capture-Phase -Phase "hold"))
$defaultSettlePhase = if ($AssertOneShotStatic) { Assert-OneShotStatic } else { $null }
$report = [ordered]@{
    schema = "companion.v15_sleep_component_choreography_browser_capture.v1"
    status = "PASS_V15_SLEEP_COMPONENT_CHOREOGRAPHY_BROWSER_CAPTURE"
    preview = $preview
    preview_sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $preview).Hash.ToUpperInvariant()
    captures = $captures
    runtime_resource_activated = $false
    active_candidate_binding = "forbidden"
    full_pose_cell_playback = "forbidden"
    playback_mode = if ($AssertOneShotStatic) { "one_shot_then_static" } else { "not_asserted" }
    default_settle_phase = $defaultSettlePhase
}
$reportPath = Join-Path $output "browser-capture-report.json"
$report | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $reportPath -Encoding utf8
Write-Output "PASS: captured V15 browser entry, response and hold component-layer evidence."
