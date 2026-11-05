param(
    [string]$Output = ".cache/validation/comp775-host-gates/paired-replay/MACHINE_READY.json"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$manifestPath = Join-Path $repoRoot ".cache\validation\comp-req-775-browser-device-single-source-final\97-recording-browser-timeline\source-pack-full\source-pack-manifest.json"
$runner = Join-Path $repoRoot "tools\test_motion_coordinator_host.ps1"
$outDir = Join-Path $repoRoot ".cache\host-tests\comp-req-775-paired-replay"
$tracePath = Join-Path $outDir "paired-trace.txt"
$outputPath = if ([IO.Path]::IsPathRooted($Output)) {
    $Output
} else {
    Join-Path $repoRoot $Output
}
foreach ($required in @($manifestPath, $runner)) {
    if (-not (Test-Path -LiteralPath $required)) {
        throw "Missing paired replay dependency: $required"
    }
}
New-Item -ItemType Directory -Force -Path $outDir | Out-Null
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $outputPath) | Out-Null

$runnerOutput = @(& $runner)
if ($LASTEXITCODE -ne 0) {
    throw "Motion coordinator host test failed with exit code $LASTEXITCODE."
}
$runnerOutput | Set-Content -LiteralPath $tracePath -Encoding ascii
$pairLines = @($runnerOutput | Where-Object { $_ -like "PAIR|*" })
$seededLines = @($runnerOutput | Where-Object { $_ -like "SEEDED|*" })
$manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
$phaseNames = @("hold", "orient", "anticipate", "accent", "follow", "settle")
$failures = [Collections.Generic.List[string]]::new()
$tuples = [Collections.Generic.List[object]]::new()
$seededTuples = [Collections.Generic.List[object]]::new()

if ($pairLines.Count -ne 60) {
    $failures.Add("expected 60 paired rows, observed $($pairLines.Count)") | Out-Null
}
foreach ($line in $pairLines) {
    $f = $line -split '\|'
    if ($f.Count -ne 20) {
        $failures.Add("malformed paired row: $line") | Out-Null
        continue
    }
    $index = [int]$f[1]
    $off = [ordered]@{
        family = $f[2]; action = $f[3]; episode = [int]$f[4]
        phrase = [int]$f[5]; phase = [int]$f[6]; variation = [int]$f[7]
        action_step = [int]$f[8]; dwell = [int]$f[9]
    }
    $on = [ordered]@{
        family = $f[10]; action = $f[11]; episode = [int]$f[12]
        phrase = [int]$f[13]; phase = [int]$f[14]; variation = [int]$f[15]
        action_step = [int]$f[16]; dwell = [int]$f[17]
    }
    $offTuple = @($off.family, $off.action, $off.episode, $off.phrase,
        $off.phase, $off.variation, $off.action_step, $off.dwell) -join '|'
    $onTuple = @($on.family, $on.action, $on.episode, $on.phrase,
        $on.phase, $on.variation, $on.action_step, $on.dwell) -join '|'
    if ($offTuple -cne $onTuple) {
        $failures.Add("pair $index authored tuple differs off=$offTuple on=$onTuple") | Out-Null
        continue
    }
    if ($off.phase -lt 0 -or $off.phase -ge $phaseNames.Count) {
        $failures.Add("pair $index invalid phase $($off.phase)") | Out-Null
        continue
    }
    $phaseName = $phaseNames[$off.phase]
    $matches = @($manifest.states | Where-Object {
        $_.kind -eq "life" -and $_.family -ceq $off.family -and
        $_.life_action -ceq $off.action -and
        [int]$_.action_episode -eq $off.episode -and
        [int]$_.phrase -eq $off.phrase -and $_.phase -ceq $phaseName -and
        [int]$_.variation -eq $off.variation -and
        [int]$_.action_step -eq $off.action_step -and
        [int]$_.dwell_commits -eq $off.dwell
    })
    if ($matches.Count -ne 1) {
        $failures.Add("pair $index maps to $($matches.Count) manifest frames") | Out-Null
        continue
    }
    $frameOff = [int]$matches[0].unique_frame_index
    # Both modes resolve through the same immutable source-pack manifest.
    $frameOn = [int]$matches[0].unique_frame_index
    $tuples.Add([ordered]@{
        index = $index
        family = $off.family
        action = $off.action
        phrase = $off.phrase
        phase = $phaseName
        frame_off = $frameOff
        frame_on = $frameOn
        dwell = $off.dwell
        due_ms_off = [int64]$f[18]
        due_ms_on = [int64]$f[19]
    }) | Out-Null
}

if ($seededLines.Count -ne 24) {
    $failures.Add("expected 24 seeded entry rows, observed $($seededLines.Count)") | Out-Null
}
foreach ($line in $seededLines) {
    $f = $line -split '\|'
    if ($f.Count -ne 11) {
        $failures.Add("malformed seeded row: $line") | Out-Null
        continue
    }
    $seedName = $f[1]
    $index = [int]$f[2]
    $family = $f[3]
    $action = $f[4]
    $episode = [int]$f[5]
    $phrase = [int]$f[6]
    $phase = [int]$f[7]
    $variation = [int]$f[8]
    $actionStep = [int]$f[9]
    $dwell = [int]$f[10]
    if ($phase -lt 0 -or $phase -ge $phaseNames.Count) {
        $failures.Add("seeded $seedName/$index invalid phase $phase") | Out-Null
        continue
    }
    $phaseName = $phaseNames[$phase]
    $matches = @($manifest.states | Where-Object {
        $_.kind -eq "life" -and $_.family -ceq $family -and
        $_.life_action -ceq $action -and
        [int]$_.action_episode -eq $episode -and
        [int]$_.phrase -eq $phrase -and $_.phase -ceq $phaseName -and
        [int]$_.variation -eq $variation -and
        [int]$_.action_step -eq $actionStep -and
        [int]$_.dwell_commits -eq $dwell
    })
    if ($matches.Count -ne 1) {
        $failures.Add("seeded $seedName/$index maps to $($matches.Count) manifest frames") | Out-Null
        continue
    }
    $seededTuples.Add([ordered]@{
        seed = $seedName
        index = $index
        episode = $episode
        family = $family
        action = $action
        phrase = $phrase
        phase = $phaseName
        variation = $variation
        dwell = $dwell
        frame = [int]$matches[0].unique_frame_index
    }) | Out-Null
}

$checks = [ordered]@{
    paired_rows_exactly_60 = $pairLines.Count -eq 60
    every_authored_tuple_identical = $failures.Count -eq 0
    every_pair_maps_to_one_source_frame = $tuples.Count -eq 60
    frame_identical_off_on = $tuples.Count -eq 60 -and
        @($tuples | Where-Object { $_.frame_off -ne $_.frame_on }).Count -eq 0
    absolute_due_identical_off_on = $tuples.Count -eq 60 -and
        @($tuples | Where-Object { $_.due_ms_off -ne $_.due_ms_on }).Count -eq 0
    dwell_always_one_to_four = $tuples.Count -eq 60 -and
        @($tuples | Where-Object { $_.dwell -lt 1 -or $_.dwell -gt 4 }).Count -eq 0
    authored_cadence_is_480_ms = @(
        Select-String -LiteralPath (Join-Path $repoRoot "app\companion_pendant\epaper\motion_coordinator.h") `
            -SimpleMatch "#define COMP_EPAPER_MOTION_CADENCE_MS 480u"
    ).Count -eq 1
    seeded_entry_rows_exactly_24 = $seededLines.Count -eq 24
    seeded_entries_all_map_to_source_pack = $seededTuples.Count -eq 24
    seeded_entries_start_at_distinct_authored_episodes =
        @($seededTuples | Where-Object { $_.seed -eq "A" -and $_.index -eq 0 }).Count -eq 1 -and
        @($seededTuples | Where-Object { $_.seed -eq "B" -and $_.index -eq 0 }).Count -eq 1 -and
        [int]@($seededTuples | Where-Object { $_.seed -eq "A" -and $_.index -eq 0 })[0].episode -ne
        [int]@($seededTuples | Where-Object { $_.seed -eq "B" -and $_.index -eq 0 })[0].episode
    seeded_entries_have_distinct_visible_frames =
        @($seededTuples | ForEach-Object { [int]$_.frame } |
            Sort-Object -Unique).Count -ge 8
}
$ready = @($checks.Values | Where-Object { -not $_ }).Count -eq 0
$receipt = [ordered]@{
    schema = "companion.comp_req_775.paired_recording_off_on_replay.v1"
    status = if ($ready) { "MACHINE_READY" } else { "NO_GO" }
    checks = $checks
    failures = @($failures)
    tuple_contract = "family/action/phrase/phase/frame/dwell exact"
    paired_count = $tuples.Count
    tuples = @($tuples)
    seeded_entry_count = $seededTuples.Count
    seeded_entries = @($seededTuples)
    source = [ordered]@{
        manifest = $manifestPath
        trace = $tracePath
    }
}
$receipt | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $outputPath -Encoding utf8
$receipt | ConvertTo-Json -Depth 5
if (-not $ready) { exit 1 }
