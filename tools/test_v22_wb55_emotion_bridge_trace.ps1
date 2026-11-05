# Exercise the V22 WB55 trace parser without touching a board, panel, or Flash.
param(
    [ValidateRange(0, 9)]
    [int]$Edge = 0,
    [string]$EvidencePath = ""
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
if (-not $EvidencePath) {
    $EvidencePath = Join-Path $repoRoot "docs\validation\companion-v22-emotion-separation-wb55-trace-contract-20260719.json"
}
$replayRoot = Join-Path $repoRoot ".cache\validation\v22-wb55-trace-contract"
$replayJson = Join-Path $replayRoot "observed-browser-replay.json"
$replayHtml = Join-Path $replayRoot "observed-browser-replay.html"

& python (Join-Path $PSScriptRoot "verify_companion_v22_wb55_emotion_bridge_trace.py") `
    --self-test `
    --edge $Edge `
    --replay $replayJson `
    --replay-html $replayHtml `
    --write $EvidencePath
if ($LASTEXITCODE -ne 0) {
    throw "V22 WB55 trace contract self-test failed."
}

$html = Get-Content -LiteralPath $replayHtml -Raw
if ($html -match "bridge-frames-200x200" -or $html -match "attempt-01-generated-emotion-separation\.png" -or
    $html -notmatch "component_layer_directory" -or $html -notmatch "component-layers" -or
    $html -notmatch "observed_request_to_next_step_ms" -or
    $html -notmatch "browser_next_final_frame_visible_delay_ms") {
    throw "Observed browser replay is not a component-only, trace-paced page."
}
$replay = Get-Content -LiteralPath $replayJson -Raw | ConvertFrom-Json
for ($index = 0; $index -lt $replay.browser_observed_replay_timeline.Count; ++$index) {
    $step = $replay.browser_observed_replay_timeline[$index]
    if ($index -eq $replay.browser_observed_replay_timeline.Count - 1) {
        if ($null -ne $step.browser_next_final_frame_visible_delay_ms) {
            throw "The settled final frame must not schedule an automatic replay."
        }
        continue
    }
    $next = $replay.browser_observed_replay_timeline[$index + 1]
    $expectedVisibleDelay = [int]$step.post_refresh_hold_ms + [int]$next.observed_refresh_elapsed_ms
    if ([int]$step.browser_next_final_frame_visible_delay_ms -ne $expectedVisibleDelay) {
        throw "Browser final-frame visibility timing drifted at step $index."
    }
}

$edgeBrowser = "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
if (-not (Test-Path -LiteralPath $edgeBrowser)) {
    throw "Missing Edge headless executable: $edgeBrowser"
}
$screenshot = Join-Path $replayRoot "observed-browser-replay.png"
$edgeProfile = Join-Path $replayRoot "edge-profile"
Remove-Item -LiteralPath $screenshot -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath $edgeProfile -Recurse -Force -ErrorAction SilentlyContinue
$fileUrl = "file:///" + ($replayHtml -replace "\\", "/")
$process = $null
try {
    $process = Start-Process -FilePath $edgeBrowser -ArgumentList @(
        "--headless=new", "--disable-gpu", "--hide-scrollbars", "--run-all-compositor-stages-before-draw",
        "--virtual-time-budget=300", "--window-size=1120,1060",
        "--user-data-dir=$edgeProfile", "--screenshot=$screenshot", $fileUrl
    ) -PassThru -WindowStyle Hidden
    if (-not $process.WaitForExit(20000)) {
        throw "Timed out rendering the observed browser replay."
    }
    if ($process.ExitCode -ne 0 -or -not (Test-Path -LiteralPath $screenshot)) {
        throw "Observed browser replay screenshot was not created."
    }
    $darkPixels = [int](& python -c "from PIL import Image; import sys; image=Image.open(sys.argv[1]).convert('RGB'); print(sum(1 for red,green,blue in image.getdata() if red < 80 and green < 80 and blue < 80))" $screenshot)
    if ($LASTEXITCODE -ne 0 -or $darkPixels -lt 8000) {
        throw "Observed browser replay did not render the component bridge: dark_pixels=$darkPixels"
    }
}
finally {
    if ($null -ne $process -and -not $process.HasExited) {
        Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
        $process.WaitForExit(2000) | Out-Null
    }
    Remove-Item -LiteralPath $edgeProfile -Recurse -Force -ErrorAction SilentlyContinue
}

Write-Output "PASS: V22 WB55 trace contract self-test written to $EvidencePath"
