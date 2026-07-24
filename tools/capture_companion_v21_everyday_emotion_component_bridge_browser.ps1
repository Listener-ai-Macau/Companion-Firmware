#requires -Version 7.0
[CmdletBinding()]
param(
    [string]$PreviewPath = "docs\art\iterations\companion-pet-expression-v9-extension-v21-everyday-emotion-distinction-source\candidate\component-bridge-v2\preview.html",
    [string]$OutputDir = "docs\art\iterations\companion-pet-expression-v9-extension-v21-everyday-emotion-distinction-source\candidate\component-bridge-v2",
    [ValidateRange(1, 60)]
    [int]$TimeoutSeconds = 20
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $repoRoot
$preview = (Resolve-Path $PreviewPath).Path
$output = [System.IO.Path]::GetFullPath((Join-Path $repoRoot $OutputDir))
$edge = "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
if (-not (Test-Path -LiteralPath $edge)) { throw "Missing Edge headless executable: $edge" }
New-Item -ItemType Directory -Force -Path $output | Out-Null

$source = "calm"
$target = "curious"
$samples = @(
    [ordered]@{ name = "source_hold"; cue = "source_hold"; virtual_time_ms = 400 },
    [ordered]@{ name = "primary_highlight_lead"; cue = "primary_highlight_lead"; virtual_time_ms = 720 },
    [ordered]@{ name = "sparkle_arrive"; cue = "sparkle_arrive"; virtual_time_ms = 900 },
    [ordered]@{ name = "brow_apex"; cue = "brow_apex"; virtual_time_ms = 1080 },
    [ordered]@{ name = "lower_face_apex"; cue = "lower_face_apex"; virtual_time_ms = 1360 },
    [ordered]@{ name = "target_hold"; cue = "target_hold"; virtual_time_ms = 1800 },
    [ordered]@{ name = "highlight_settle"; cue = "highlight_settle"; virtual_time_ms = 3500 },
    [ordered]@{ name = "target_persistent"; cue = "target_persistent"; virtual_time_ms = 5200 }
)

function Capture-Sample {
    param([hashtable]$Sample)
    $shot = Join-Path $output ("v21-component-bridge-browser-" + $Sample.name + ".png")
    $profile = Join-Path $repoRoot (".cache\v21-component-bridge-browser-" + $Sample.name)
    $url = "file:///" + ($preview -replace "\\", "/") + "?state=$source&target=$target"
    Remove-Item -LiteralPath $shot -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $profile -Recurse -Force -ErrorAction SilentlyContinue
    $process = $null
    try {
        $process = Start-Process -FilePath $edge -ArgumentList @(
            "--headless=new", "--disable-gpu", "--hide-scrollbars", "--run-all-compositor-stages-before-draw",
            "--virtual-time-budget=$($Sample.virtual_time_ms)", "--window-size=1120,1060",
            "--user-data-dir=$profile", "--screenshot=$shot", $url
        ) -PassThru -WindowStyle Hidden
        $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
        while (-not (Test-Path -LiteralPath $shot) -and (Get-Date) -lt $deadline) {
            if ($process.WaitForExit(200)) { break }
        }
        if (-not (Test-Path -LiteralPath $shot)) {
            $exitCode = if ($process.HasExited) { $process.ExitCode } else { "timeout" }
            throw "Edge did not create screenshot for $($Sample.name) before $TimeoutSeconds s (exit=$exitCode)"
        }
        if ($process.HasExited -and $process.ExitCode -ne 0) {
            throw "Edge capture failed for $($Sample.name) with $($process.ExitCode)"
        }
    }
    finally {
        if ($null -ne $process -and -not $process.HasExited) {
            Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
            $process.WaitForExit(2000) | Out-Null
        }
        Remove-Item -LiteralPath $profile -Recurse -Force -ErrorAction SilentlyContinue
    }
    $item = Get-Item -LiteralPath $shot
    if ($item.Length -lt 4000) { throw "Edge screenshot is unexpectedly small for $($Sample.name): $($item.Length)" }
    $darkPixels = [int](& python -c "from PIL import Image; import sys; im=Image.open(sys.argv[1]).convert('RGB'); print(sum(1 for r,g,b in im.getdata() if r<80 and g<80 and b<80))" $shot)
    if ($LASTEXITCODE -ne 0 -or $darkPixels -lt 8000) {
        throw "Browser did not render the V21 component bridge for $($Sample.name): dark_pixels=$darkPixels"
    }
    return [ordered]@{
        name = $Sample.name
        cue = $Sample.cue
        virtual_time_ms = $Sample.virtual_time_ms
        path = $shot
        sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $shot).Hash.ToUpperInvariant()
        bytes = $item.Length
        dark_pixels = $darkPixels
    }
}

$captures = @($samples | ForEach-Object { Capture-Sample -Sample $_ })
$comparisonJson = & python -c @'
from pathlib import Path
from PIL import Image, ImageChops
import json, sys
paths = [Path(value) for value in sys.argv[1:]]
images = [Image.open(path).convert("RGB") for path in paths]
baseline = images[0]
diffs = []
for image in images[1:]:
    diff = ImageChops.difference(baseline, image)
    diffs.append(sum(1 for pixel in diff.getdata() if pixel != (0, 0, 0)))
persistent = ImageChops.difference(images[-2], images[-1])
print(json.dumps({"baseline": diffs, "settle_to_persistent": sum(1 for pixel in persistent.getdata() if pixel != (0, 0, 0))}))
'@ ($captures | ForEach-Object { $_.path })
if ($LASTEXITCODE -ne 0) { throw "Unable to compare V21 component bridge browser captures." }
$comparison = $comparisonJson | ConvertFrom-Json
$differences = @($comparison.baseline)
$settleToPersistent = [int]$comparison.settle_to_persistent
if ($differences.Count -ne 7 -or $differences[0] -lt 80 -or $differences[1] -lt 120 -or
    $differences[2] -lt 300 -or $differences[3] -lt 450 -or $differences[4] -lt 550 -or $differences[5] -lt 550 -or
    $differences[6] -lt 550 -or $settleToPersistent -ne 0) {
    throw "Browser bridge did not show a progressive component choreography: $($differences -join ',')"
}

$report = [ordered]@{
    schema = "companion.v21_everyday_emotion_component_bridge_browser_capture.v2"
    status = "PASS_V21_COMPONENT_EMOTION_BRIDGE_BROWSER_CAPTURE_RESEARCH_REFINED"
    preview = $preview
    preview_sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $preview).Hash.ToUpperInvariant()
    source_emotion = $source
    target_emotion = $target
    bridge_policy = "selected legal edge only; primary highlights lead; sparkles follow; brows/lower face reach apex; no automatic reverse"
    captures = $captures
    source_hold_pixel_differences = [ordered]@{
        primary_highlight_lead = $differences[0]
        sparkle_arrive = $differences[1]
        brow_apex = $differences[2]
        lower_face_apex = $differences[3]
        target_hold = $differences[4]
        highlight_settle = $differences[5]
        target_persistent = $differences[6]
    }
    settle_to_target_persistent_pixel_difference = $settleToPersistent
    state_rotation = "forbidden"
    full_face_source_card_playback = "forbidden"
    browser_rendering = "registered_component_dom_layers_only"
    runtime_resource_activated = $false
}
$reportPath = Join-Path $output "browser-capture-report.json"
$report | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $reportPath -Encoding utf8
Write-Output "PASS: Edge captured the research-refined V21 browser bridge from the exact registered component plan used by 200x200 PBM output."
