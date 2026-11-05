param(
    [string]$Output = ".cache/validation/comp775-host-gates/phase-lock/MACHINE_READY.json",
    [string]$NegativeLog = ".cache/validation/comp775-wave-every-activation-r52-final-20260810/long-recording/nucleo-serial-raw.log"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$oracle = Join-Path $repoRoot "tools\faraday_upper_art\verify_comp_req_775_phase_lock.py"
$negativePath = if ([IO.Path]::IsPathRooted($NegativeLog)) {
    $NegativeLog
} else {
    Join-Path $repoRoot $NegativeLog
}
$outputPath = if ([IO.Path]::IsPathRooted($Output)) {
    $Output
} else {
    Join-Path $repoRoot $Output
}
$outDir = Join-Path $repoRoot ".cache\host-tests\comp-req-775-phase-lock"
$candidatePath = Join-Path $outDir "independent-clocks-shared-carrier.log"
foreach ($required in @($oracle, $negativePath)) {
    if (-not (Test-Path -LiteralPath $required)) {
        throw "Missing phase-lock oracle dependency: $required"
    }
}
New-Item -ItemType Directory -Force -Path $outDir | Out-Null
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $outputPath) | Out-Null

$rows = [Collections.Generic.List[string]]::new()
$rows.Add("[record-visual] action=overlay_start result=1 tracks=wave_authored_life_blink_accessory_independent wave_every_activation=1") | Out-Null
$visibleMs = 1000
$faceDueMs = 960
# Keep this decimal so Windows PowerShell does not sign-extend the 0xE prefix.
$request = [uint64]3758096640 # 0xE0000100
$faceIndices = @(4, 7, 11, 16, 20, 26, 31, 36)
$faceDwells = @(1, 2, 4, 1, 3, 2, 4, 1)
$blinkIndices = @(14, 29)
for ($index = 1; $index -le 40; $index++) {
    $isFace = $faceIndices -contains $index
    $isBlink = $blinkIndices -contains $index
    $carrier = if ($isFace) { "authored_life" } elseif ($isBlink) { "authored_blink" } else { "pure_wave" }
    $only = if ($carrier -eq "pure_wave") { 1 } else { 0 }
    $rows.Add("[record-phase] track=wave request=$request due_source=recording_scheduler visible_ms=$visibleMs only=$only carrier=$carrier face_clock_advanced=0 accessory_clock_advanced=0") | Out-Null
    if ($isFace) {
        $facePosition = [Array]::IndexOf($faceIndices, $index)
        $faceDueMs += 480 * $faceDwells[$facePosition]
        $rows.Add("[record-phase] track=face request=$request due_source=authored_absolute_deadline due_ms=$faceDueMs visible_ms=$visibleMs frame=$($index + 200) wave_carried=1 wave_drives_face=0") | Out-Null
    }
    if ($isBlink) {
        $rows.Add("[record-phase] track=blink request=$request phase=closed due_source=blink_scheduler visible_ms=$visibleMs wave_carried=1 wave_drives_blink=0") | Out-Null
    }
    if ($index -eq 9) {
        $rows.Add("[accessory-clock] track=charging due_source=charging_wall_clock due_ms=$visibleMs frame=1 remaining_ms=700 pending_for_next_activation=1 wave_clock_advanced=0 life_clock_advanced=0 blink_clock_advanced=0") | Out-Null
    }
    $request++
    $visibleMs += 455
}
$rows.Add("[record-visual] action=stop_queue result=1 signal=10") | Out-Null
$rows | Set-Content -LiteralPath $candidatePath -Encoding ascii

& python $oracle $candidatePath --negative-log $negativePath --output $outputPath
if ($LASTEXITCODE -ne 0) {
    throw "Phase-lock oracle rejected its independent shared-carrier fixture or missed the r52 Owner negative."
}
