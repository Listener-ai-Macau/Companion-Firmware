#requires -Version 7.0
[CmdletBinding()]
param(
    [string]$PreviewPath = "docs\art\iterations\companion-pet-expression-v9-rig-v2-expanded-source\candidate\preview.html",
    [string]$OutputDir = "docs\art\iterations\companion-pet-expression-v9-rig-v2-expanded-source\candidate",
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

$samples = @(
    [ordered]@{ name = "baseline"; virtual_time_ms = 1000 },
    [ordered]@{ name = "gaze_focus"; virtual_time_ms = 3100 },
    [ordered]@{ name = "brow_answer"; virtual_time_ms = 3520 },
    [ordered]@{ name = "lower_face_reply"; virtual_time_ms = 3900 },
    [ordered]@{ name = "static_rest"; virtual_time_ms = 9000 }
)

function Capture-Sample {
    param([hashtable]$Sample)
    $shot = Join-Path $output ("presence-browser-" + $Sample.name + ".png")
    $profile = Join-Path $repoRoot (".cache\v9-expanded-presence-browser-" + $Sample.name)
    $url = "file:///" + ($preview -replace "\\", "/") + "?state=daily_attention_left"
    Remove-Item -LiteralPath $shot -Force -ErrorAction SilentlyContinue
    $process = Start-Process -FilePath $edge -ArgumentList @(
        "--headless=new", "--disable-gpu", "--hide-scrollbars", "--run-all-compositor-stages-before-draw",
        "--virtual-time-budget=$($Sample.virtual_time_ms)", "--window-size=1000,980",
        "--user-data-dir=$profile", "--screenshot=$shot", $url
    ) -PassThru -Wait -WindowStyle Hidden
    if ($process.ExitCode -ne 0) { throw "Edge capture failed for $($Sample.name) with $($process.ExitCode)" }
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while (-not (Test-Path -LiteralPath $shot) -and (Get-Date) -lt $deadline) { Start-Sleep -Milliseconds 200 }
    if (-not (Test-Path -LiteralPath $shot)) { throw "Edge did not create screenshot for $($Sample.name)" }
    $item = Get-Item -LiteralPath $shot
    if ($item.Length -lt 4000) { throw "Edge screenshot is unexpectedly small for $($Sample.name): $($item.Length)" }
    $darkPixels = [int](& python -c "from PIL import Image; import sys; im=Image.open(sys.argv[1]).convert('RGB'); print(sum(1 for r,g,b in im.getdata() if r<80 and g<80 and b<80))" $shot)
    if ($LASTEXITCODE -ne 0 -or $darkPixels -lt 800) {
        throw "Edge screenshot did not render the expanded Rig presence layers for $($Sample.name): dark_pixels=$darkPixels"
    }
    return [ordered]@{
        name = $Sample.name
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
print(json.dumps(diffs))
'@ ($captures | ForEach-Object { $_.path })
if ($LASTEXITCODE -ne 0) { throw "Unable to compare browser capture frames." }
$differences = @($comparisonJson | ConvertFrom-Json)
if ($differences.Count -ne 4 -or $differences[0] -lt 60 -or $differences[1] -lt 100 -or $differences[2] -lt 60 -or $differences[3] -ne 0) {
    throw "Browser presence captures did not show gaze, brow, lower-face motion and static-rest return: $($differences -join ',')"
}

$report = [ordered]@{
    schema = "companion.v9_expanded_expression_rig_presence_browser_capture.v1"
    status = "PASS_EXPANDED_COMPONENT_PRESENCE_BROWSER_CAPTURE"
    preview = $preview
    preview_sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $preview).Hash.ToUpperInvariant()
    selected_state = "daily_attention_left"
    captures = $captures
    baseline_pixel_differences = [ordered]@{
        gaze_focus = $differences[0]
        brow_answer = $differences[1]
        lower_face_reply = $differences[2]
        static_rest = $differences[3]
    }
    state_rotation = "forbidden"
    full_face_source_card_playback = "forbidden"
    runtime_resource_activated = $false
}
$reportPath = Join-Path $output "presence-browser-capture-report.json"
$report | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $reportPath -Encoding utf8
Write-Output "PASS: captured expanded Rig selected-state component presence browser evidence."
