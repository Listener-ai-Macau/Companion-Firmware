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

# This is a legal direct affect edge. The samples correspond to source hold,
# highlight lead, brow answer, lower-face reply, and target hold.
$sourceEmotion = "curious"
$targetEmotion = "affectionate"
$samples = @(
    [ordered]@{ name = "source_hold"; cue = "source_hold"; virtual_time_ms = 500 },
    [ordered]@{ name = "gaze_lead"; cue = "gaze_lead"; virtual_time_ms = 900 },
    [ordered]@{ name = "brow_answer"; cue = "brow_answer"; virtual_time_ms = 1450 },
    [ordered]@{ name = "lower_face_reply"; cue = "lower_face_reply"; virtual_time_ms = 1850 },
    [ordered]@{ name = "target_hold"; cue = "target_hold"; virtual_time_ms = 2700 }
)

function Capture-Sample {
    param([hashtable]$Sample)
    $shot = Join-Path $output ("emotion-bridge-browser-" + $Sample.name + ".png")
    $profile = Join-Path $repoRoot (".cache\v9-expanded-emotion-bridge-browser-" + $Sample.name)
    $url = "file:///" + ($preview -replace "\\", "/") + "?state=$sourceEmotion&target=$targetEmotion"
    Remove-Item -LiteralPath $shot -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $profile -Recurse -Force -ErrorAction SilentlyContinue
    $process = $null
    try {
        $process = Start-Process -FilePath $edge -ArgumentList @(
            "--headless=new", "--disable-gpu", "--hide-scrollbars", "--run-all-compositor-stages-before-draw",
            "--virtual-time-budget=$($Sample.virtual_time_ms)", "--window-size=1000,980",
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
    if ($LASTEXITCODE -ne 0 -or $darkPixels -lt 800) {
        throw "Edge screenshot did not render the expanded Rig bridge layers for $($Sample.name): dark_pixels=$darkPixels"
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
print(json.dumps(diffs))
'@ ($captures | ForEach-Object { $_.path })
if ($LASTEXITCODE -ne 0) { throw "Unable to compare emotion-bridge browser capture frames." }
$differences = @($comparisonJson | ConvertFrom-Json)
if ($differences.Count -ne 4 -or $differences[0] -lt 60 -or $differences[1] -lt 100 -or $differences[2] -lt 120 -or $differences[3] -lt 180) {
    throw "Browser emotion bridge did not show progressive component choreography: $($differences -join ',')"
}

$report = [ordered]@{
    schema = "companion.v9_expanded_expression_rig_emotion_bridge_browser_capture.v1"
    status = "PASS_EXPANDED_COMPONENT_EMOTION_BRIDGE_BROWSER_CAPTURE"
    preview = $preview
    preview_sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $preview).Hash.ToUpperInvariant()
    source_emotion = $sourceEmotion
    target_emotion = $targetEmotion
    bridge_policy = "directed affect edge; highlights lead, brows answer, lower face replies, approved accent follows"
    captures = $captures
    source_hold_pixel_differences = [ordered]@{
        gaze_lead = $differences[0]
        brow_answer = $differences[1]
        lower_face_reply = $differences[2]
        target_hold = $differences[3]
    }
    state_rotation = "forbidden"
    full_face_source_card_playback = "forbidden"
    runtime_resource_activated = $false
}
$reportPath = Join-Path $output "emotion-bridge-browser-capture-report.json"
$report | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $reportPath -Encoding utf8
Write-Output "PASS: captured one directed expanded Rig emotion bridge in the browser from the same component plan used by WBA."
