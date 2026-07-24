param(
    [switch]$CheckOnly,
    [switch]$Execute,
    [switch]$SelfTest,
    [switch]$FinalizationSelfTest,
    [string]$Port,
    [int]$RingBytes = 65536,
    [string]$ReadySignalPath,
    [string]$QualificationSignalPath,
    [string]$StopSignalPath,
    [string]$EmergencyStopPath,
    [string]$OutDir
)
$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
[Console]::OutputEncoding = [Text.Encoding]::UTF8
if (@($CheckOnly,$Execute,$SelfTest,$FinalizationSelfTest).Where({$_}).Count -ne 1) { throw "Choose exactly one monitor mode." }
if ($RingBytes -ne 65536) { throw "R11 monitor ring is fixed at exactly 65536 bytes." }
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$out = if ($OutDir) { [IO.Path]::GetFullPath($OutDir) } else { Join-Path $root ".cache\validation\wb55-r11-throw-arc-monitor" }
$ringPath = Join-Path $out "telemetry-ring.log"
$parserArtifact = Join-Path $out "r11-log-parser.json"
$qualificationSnapshotPath = Join-Path $out "qualification-snapshot.log"
$qualificationArtifact = Join-Path $out "qualification-parser.json"
$finalLoopSnapshotPath = Join-Path $out "final-loop-snapshot.log"
$finalLoopArtifact = Join-Path $out "final-loop-parser.json"
$resultPath = Join-Path $out "monitor-result.json"
$parserScript = Join-Path $PSScriptRoot "verify_wb55_ssd1681_r11_native_cached_mode2_throw_arc_log.py"
New-Item -ItemType Directory -Force -Path $out | Out-Null
$script:ring = ""; $script:ringPeakBytes = 0; $script:ringWrites = 0
function Write-Json([string]$Path,[object]$Value) { $tmp="$Path.tmp"; [IO.File]::WriteAllText($tmp,(($Value|ConvertTo-Json -Depth 16)+[Environment]::NewLine),[Text.UTF8Encoding]::new($false)); Move-Item -LiteralPath $tmp -Destination $Path -Force }
function Add-Ring([string]$Text) {
    $script:ring += $Text
    while ([Text.Encoding]::UTF8.GetByteCount($script:ring) -gt $RingBytes) {
        $newline = $script:ring.IndexOf("`n")
        if ($newline -lt 0) { throw "Telemetry ring overflowed before a complete line boundary." }
        $script:ring = $script:ring.Substring($newline + 1)
    }
    $script:ringPeakBytes = [Math]::Max($script:ringPeakBytes,[Text.Encoding]::UTF8.GetByteCount($script:ring))
}
function Snapshot { [IO.File]::WriteAllText($ringPath,$script:ring,[Text.UTF8Encoding]::new($false)); $script:ringWrites++; if ((Get-Item $ringPath).Length -gt $RingBytes) { throw "Telemetry ring exceeded fixed bound." } }
function Test-CompactFrameLine([string]$Line) {
    return $Line.StartsWith("[r11] s=v1 ") -and ($Line -match '(?:^|\s)(q|i)=')
}
function Assert-R11LineBound([string]$Line) {
    if ((Test-CompactFrameLine $Line) -and [Text.Encoding]::ASCII.GetByteCount($Line + "`r`n") -gt 192) {
        throw "R11 compact telemetry record exceeded 192 bytes including CRLF."
    }
}
function Assert-R11CandidateLine([string]$Line,[bool]$HadCr) {
    if (-not $Line.StartsWith("[r11]")) { return }
    if (-not $HadCr) { throw "R11 line must end in CRLF." }
    if ($Line -match '^\[r11\] s=v1 (?:.*\s)?i=\d+(?:\s|$)') { return }
    if ($Line.StartsWith("[r11] s=")) {
        & python $parserScript --validate-loop-line $Line 2>$null | Out-Null
        if($LASTEXITCODE -ne 0){throw "Malformed R11 compact candidate record."}
        return
    }
    & python -c "import sys;sys.path.insert(0,r'$root\tools');import verify_wb55_ssd1681_r11_native_cached_mode2_throw_arc_log as m;m.parse_metadata(sys.argv[1])" $Line 2>$null | Out-Null
    if($LASTEXITCODE -ne 0){throw "Malformed or unknown R11 metadata record."}
}
function Get-Port([string]$Requested) {
    $ports = @([IO.Ports.SerialPort]::GetPortNames())
    if ($Requested) { if ($ports -notcontains $Requested) { throw "Requested serial port is absent." }; return $Requested }
    $candidates = @()
    foreach ($device in @(Get-CimInstance Win32_PnPEntity -ErrorAction Stop | Where-Object { ([string]$_.Name -match '\(COM\d+\)') -and (([string]$_.Name+" "+$_.Description+" "+$_.Manufacturer+" "+$_.PNPDeviceID) -match '(?i)ST-LINK|STM32|STMicroelectronics|VID_0483') })) {
        $m=[regex]::Match([string]$device.Name,'\((COM\d+)\)'); if($m.Success -and $ports -contains $m.Groups[1].Value){$candidates += $m.Groups[1].Value}
    }
    $candidates=@($candidates|Sort-Object -Unique); if($candidates.Count -ne 1){throw "Exactly one ST-LINK VCP is required."}; return [string]$candidates[0]
}
function Test-Loop([string]$Line,[Nullable[uint32]]$Previous) {
    $m=[regex]::Match($Line,'(?:^|\s)i=(\d+)'); if(-not $m.Success){throw "Malformed R11 loop telemetry."}
    $iteration=[uint32]$m.Groups[1].Value
    if($null -ne $Previous -and $iteration -ne ($Previous + 1)){throw "Non-contiguous R11 loop iteration."}
    $positions=@(44,56,68,80,92,104,116,128,116,104,92,80,68,56,44,32)
    $current=[int]$positions[([int](($iteration-1)%16))]
    $previous=if($iteration -eq 1){32}else{[int]$positions[([int](($iteration-2)%16))]}
    & python $parserScript --validate-loop-line $Line --sequence-key i --sequence $iteration --previous $previous --current $current | Out-Null
    if($LASTEXITCODE -ne 0){throw "R11 full loop frame contract rejected iteration $iteration."}
    return $iteration
}
$serial=$null; $status="NO_GO_MONITOR_UNSTARTED"; $qualified=$false; $observationReady=$false; $lineBuffer=""; $lastIteration=$null; $lastLoopLines=@(); $loopRecords=0; $cadenceMeasurements=0; $maxStartDeltaMs=$null; $qualificationParsed=$null; $errorText=$null; $finalizationAttempted=$false
if ($FinalizationSelfTest) {
    $badLog = Join-Path $out "finalization-malformed.log"
    $badArtifact = Join-Path $out "finalization-parser.json"
    $emergency = Join-Path $out "emergency-stop.json"
    $badLine = "[r11] s=v1 i=1 malformed_complete=1`r`n"
    [IO.File]::WriteAllText($badLog, $badLine, [Text.UTF8Encoding]::new($false))
    $status = "STOP_REQUESTED_AFTER_QUALIFICATION"
    $finalizationAttempted = $true
    try {
        & python $parserScript --loop-log $badLog --minimum-loop-iterations 1 --hardware-contact 0 --artifact $badArtifact --write | Out-Null
        if ($LASTEXITCODE -eq 0) { throw "simulated final parser unexpectedly accepted malformed complete line." }
        throw "simulated final parser exception after STOP."
    } catch {
        $errorText = $_.Exception.Message
        $status = "NO_GO_FINALIZATION"
        Write-Json $emergency ([ordered]@{schema_id="companion.wb55.ssd1681.r11_native_cached_mode2_throw_arc.emergency_stop.v1";reason=$status;detail=$errorText;hardware_contact=0})
        Write-Json $resultPath ([ordered]@{schema_id="companion.wb55.ssd1681.r11_native_cached_mode2_throw_arc.monitor.v1";status=$status;hardware_contact=0;popup_count=0;write_counter_sum=0;retry_count=0;stop_requested_after_qualification=$true;finalization_attempted=$true;error=$errorText})
        exit 1
    }
}
if ($SelfTest -or $CheckOnly) {
    $selfChecks = [ordered]@{}
    if ($SelfTest) {
        $startPrefix = "[r11] start candidate=r11_native_cached_mode2_throw_arc "
        $startLine = $startPrefix + ("x" * (534 - [Text.Encoding]::ASCII.GetByteCount($startPrefix)))
        $startAccepted = $true
        try { Assert-R11LineBound $startLine } catch { $startAccepted = $false }
        $overlongFrame = "[r11] s=v1 i=1 " + ("x" * 500)
        $frameRejected = $false
        try { Assert-R11LineBound $overlongFrame } catch { $frameRejected = $true }
        $selfChecks.start_description_534_bytes_bypasses_compact_limit = $startAccepted -and ([Text.Encoding]::ASCII.GetByteCount($startLine) -eq 534)
        $selfChecks.overlong_loop_frame_rejected = $frameRejected
        $selfChecks.compact_limit_includes_crlf = [Text.Encoding]::ASCII.GetByteCount($overlongFrame + "`r`n") -gt 192
        & python $parserScript --self-test | Out-Null
        if($LASTEXITCODE -ne 0){throw "R11 parser self-test rejected combined serial or compact records."}
        $q16 = (& python -c "import sys;sys.path.insert(0,r'$root\tools');import verify_wb55_ssd1681_r11_native_cached_mode2_throw_arc_log as m;p,n=m.node_for(16);print(f'[r11] s=v1 q=16 p={p[0]},{p[1]} n={n[0]},{n[1]} w={m.WINDOW} h={m.payload(n)} r=0 t=460 b=600 d=480 a=1 x=0 y=1 f=0 c=1 l=0 v=0 g=1')").Trim()
        $u32 = (& python -c "import sys;sys.path.insert(0,r'$root\tools');import verify_wb55_ssd1681_r11_native_cached_mode2_throw_arc_log as m;s=4294967295;p,n=m.node_for(s);print(f'[r11] s=v1 i={s} p={p[0]},{p[1]} n={n[0]},{n[1]} w={m.WINDOW} h={m.payload(n)} r=0 t=460 b=600 d=480 a=1 x=0 y=1 f=0 c=1 l=0 v=0 g=1')").Trim()
        & python $parserScript --validate-loop-line $q16 --sequence-key q --sequence 16 --previous 44 --current 32 | Out-Null
        if($LASTEXITCODE -ne 0){throw "Parser rejected its rendered q=16 worst-case fixture."}
        & python $parserScript --validate-loop-line $u32 --sequence-key i --sequence 4294967295 --previous 56 --current 44 | Out-Null
        if($LASTEXITCODE -ne 0){throw "Parser rejected its rendered UINT32_MAX loop fixture."}
        $q16Bytes = [Text.Encoding]::ASCII.GetByteCount($q16 + "`r`n")
        $u32Bytes = [Text.Encoding]::ASCII.GetByteCount($u32 + "`r`n")
        $over192 = $q16 + ("x" * ([Math]::Max(1,193 - $q16Bytes)))
        $over192Rejected = $false
        try { Assert-R11LineBound $over192 } catch { $over192Rejected = $true }
        $malformedMetadataRejected = $false
        try { Assert-R11CandidateLine "[r11] unknown_metadata=1" $true } catch { $malformedMetadataRejected = $true }
        $unrelatedAccepted = $true
        try { Assert-R11CandidateLine "[epaper] unrelated=1" $true } catch { $unrelatedAccepted = $false }
        $selfChecks.qualification_q16_parser_rendered_within_192 = $q16Bytes -le 192
        $selfChecks.loop_uint32_max_parser_rendered_within_192 = $u32Bytes -le 192
        $selfChecks.loop_i_first_field_recognized = $u32 -match '^\[r11\] s=v1 (?:.*\s)?i=\d+(?:\s|$)'
        $selfChecks.over_192_complete_record_rejected = $over192Rejected
        $selfChecks.malformed_r11_rejected_immediately = $malformedMetadataRejected
        $selfChecks.unrelated_combined_serial_line_ignored = $unrelatedAccepted
        $selfChecks.combined_serial_metadata_proof_delegated_to_parser = $true
        $selfChecks.two_loop_cadence_gate_delegated_to_parser = $true
    }
    Add-Ring ("R11 CheckOnly`n" * 10000); Snapshot
    if ($SelfTest -and @($selfChecks.Values).Where({ -not $_ }).Count -ne 0) { throw "R11 monitor self-test failed." }
    $r=[ordered]@{schema_id="companion.wb55.ssd1681.r11_native_cached_mode2_throw_arc.monitor.v4";status=if($SelfTest){"PASS_SELFTEST"}else{"READY_NO_HARDWARE_CONTACT"};hardware_contact=0;write_counter_sum=0;programmer_calls=0;serial_open_count=0;reset_count=0;refresh_count=0;popup_count=0;retry_count=0;ring_bytes_limit=65536;ring_peak_bytes=$script:ringPeakBytes;ring_final_bytes=(Get-Item $ringPath).Length;ring_fixed=$true;qualification_parser="verify_wb55_ssd1681_r11_native_cached_mode2_throw_arc_log.py";qualification_snapshot_bounded=$true;self_checks=$selfChecks;fail_closed=@("busy_over_600_ms","transaction_over_460_ms","cadence_over_480_ms","malformed_r11","malformed_hash","malformed_window","malformed_position","malformed_count","disconnect","storage_fault","qualification_no_go","stop_before_qualification")}
    Write-Json $resultPath $r; $r|ConvertTo-Json -Depth 10; exit 0
}
foreach($path in @($ReadySignalPath,$QualificationSignalPath,$StopSignalPath,$EmergencyStopPath)){if(-not $path){throw "Execute requires all lifecycle signal paths."}}
try {
    $resolved=Get-Port $Port; $serial=[IO.Ports.SerialPort]::new($resolved,115200,[IO.Ports.Parity]::None,8,[IO.Ports.StopBits]::One); $serial.ReadTimeout=250; $serial.Open(); $serial.DiscardInBuffer()
    Write-Json $ReadySignalPath ([ordered]@{schema_id="companion.wb55.ssd1681.r11_native_cached_mode2_throw_arc.monitor_ready.v1";status="READY";process_id=$PID;port=$resolved;ring_bytes_limit=$RingBytes})
    while($true){
        if(Test-Path $EmergencyStopPath){$status="NO_GO_EMERGENCY_STOP";throw "Emergency stop received."}
        if(Test-Path $StopSignalPath){if(-not $qualified){$status="NO_GO_STOP_BEFORE_QUALIFICATION";throw "Stop arrived before qualification."};$status="STOP_REQUESTED_AFTER_QUALIFICATION";break}
        if(@([IO.Ports.SerialPort]::GetPortNames()) -notcontains $resolved){$status="NO_GO_CONTROLLER_DISCONNECT";throw "Serial controller disconnected."}
        $chunk=$serial.ReadExisting(); if($chunk.Length -eq 0){Start-Sleep -Milliseconds 25;continue}; Add-Ring $chunk; $lineBuffer += $chunk
        if($lineBuffer.Length -gt 8192 -and -not $lineBuffer.Contains("`n")){throw "Telemetry record exceeded line bound."}
        while($lineBuffer.Contains("`n")){ $cut=$lineBuffer.IndexOf("`n");$hadCr=($cut -gt 0 -and $lineBuffer[$cut-1] -eq "`r");$line=$lineBuffer.Substring(0,$cut).TrimEnd("`r");$lineBuffer=$lineBuffer.Substring($cut+1)
            Assert-R11LineBound $line
            Assert-R11CandidateLine $line $hadCr
            if($line -match '^\[r11\] qualification_result=no_go(?:\s|$)'){throw "Firmware qualification returned no_go."}
            if($line -match '^\[r11\].*\sfault(?:\s|$)' -or $line -match '^\[epaper\] r11_native_cached_mode2_throw_arc fault(?:\s|$)'){throw "Firmware emitted an R11 fault record."}
            if($line -match '^\[r11\] observation_ready(?:\s|$)'){$observationReady=$true}
            if($line -match '^\[r11\] s=v1 (?:.*\s)?i=\d+(?:\s|$)'){
                $lastIteration=Test-Loop $line $lastIteration
                $lastLoopLines += $line
                if($lastLoopLines.Count -gt 2){$lastLoopLines=@($lastLoopLines[-2],$lastLoopLines[-1])}
                $loopRecords++
            }
            if($observationReady -and -not $qualified -and $loopRecords -ge 2){
                Snapshot; Copy-Item -LiteralPath $ringPath -Destination $qualificationSnapshotPath -Force
                if((Get-Item $qualificationSnapshotPath).Length -gt 65536){throw "Qualification snapshot exceeded fixed 65536-byte bound."}
                $parserStdout = (& python $parserScript --log $qualificationSnapshotPath --minimum-loop-iterations 2 --hardware-contact 1 --artifact $qualificationArtifact --write | Out-String).Trim()
                if($LASTEXITCODE -ne 0){throw "R11 parser rejected qualification ring."}
                if(-not (Test-Path -LiteralPath $qualificationArtifact -PathType Leaf)){throw "R11 parser returned PASS without writing qualification artifact."}
                $artifactText = (Get-Content -LiteralPath $qualificationArtifact -Raw).Trim()
                if($artifactText -ne $parserStdout){throw "R11 parser artifact does not match its printed parsed object."}
                $qualificationParsed = $artifactText | ConvertFrom-Json
                if($qualificationParsed.status -ne "PASS_R11_NATIVE_CACHED_MODE2_THROW_ARC_LOG" -or
                   $qualificationParsed.metadata_proof -ne $true -or
                   [string]$qualificationParsed.metadata.baseline.source_resets -ne "1" -or
                   [string]$qualificationParsed.metadata.baseline.source_ff -ne "1" -or
                   [string]$qualificationParsed.metadata.qualification_result.movement_source_resets -ne "0" -or
                   [string]$qualificationParsed.metadata.qualification_result.movement_source_ff -ne "0" -or
                   [string]$qualificationParsed.metadata.qualification_result.movement_source_cf -ne "1" -or
                   $qualificationParsed.qualification_frames -ne 16 -or
                   $qualificationParsed.qualification_cadence_measurements -lt 15 -or
                   $qualificationParsed.loop_records -lt 2 -or
                   $qualificationParsed.cadence_measurements -lt 1 -or
                   $qualificationParsed.max_start_delta_ms -gt 480 -or
                   $qualificationParsed.ring_bytes -ne 65536 -or
                   $qualificationParsed.hardware_contact -ne 1){throw "R11 qualification artifact lacks parsed metadata, 16 qualification records, two contiguous loops, real cadence, or hardware contact proof."}
                $cadenceMeasurements=[int]$qualificationParsed.cadence_measurements; $maxStartDeltaMs=[int]$qualificationParsed.max_start_delta_ms
                Copy-Item -LiteralPath $qualificationArtifact -Destination $parserArtifact -Force
                Write-Json $QualificationSignalPath ([ordered]@{schema_id="companion.wb55.ssd1681.r11_native_cached_mode2_throw_arc.qualification.v2";status="PASS_R11_QUALIFICATION_READY";process_id=$PID;parser_artifact=$qualificationArtifact;qualification_snapshot=$qualificationSnapshotPath;qualification_frames=16;qualification_cadence_measurements=[int]$qualificationParsed.qualification_cadence_measurements;loop_records=[int]$qualificationParsed.loop_records;cadence_measurements=$cadenceMeasurements;max_start_delta_ms=$maxStartDeltaMs;ring_bytes_limit=65536;hardware_contact=1})
                $qualified=$true
            }
        }
    }
    if(-not $qualified -or -not (Test-Path $qualificationSnapshotPath) -or -not (Test-Path $qualificationArtifact)){throw "Qualification snapshot was not preserved."}
    if($lastLoopLines.Count -ne 2){throw "Final R11 evidence lacks the latest two contiguous loop records."}
    $finalizationAttempted=$true
    Snapshot
    $qualificationLines = @(Get-Content -LiteralPath $qualificationSnapshotPath | Where-Object { $_ -notmatch '^\[r11\] s=v1 (?:.*\s)?i=\d+(?:\s|$)' })
    $finalLines = @($qualificationLines) + @($lastLoopLines)
    [IO.File]::WriteAllText($finalLoopSnapshotPath,(($finalLines -join "`r`n") + "`r`n"),[Text.UTF8Encoding]::new($false))
    if((Get-Item -LiteralPath $finalLoopSnapshotPath).Length -gt 65536){throw "Final R11 parser snapshot exceeded the fixed 65536-byte bound."}
    & python $parserScript --log $finalLoopSnapshotPath --minimum-loop-iterations 2 --hardware-contact 1 --artifact $finalLoopArtifact --write | Out-Null
    if($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $finalLoopArtifact -PathType Leaf)){throw "Final R11 loop parser rejected telemetry or did not persist its artifact."}
} catch { $errorText=$_.Exception.Message; if($finalizationAttempted){$status="NO_GO_FINALIZATION"} elseif($status -eq "NO_GO_MONITOR_UNSTARTED"){$status="NO_GO_MONITOR_FAULT"}; if($EmergencyStopPath -and -not(Test-Path $EmergencyStopPath)){Write-Json $EmergencyStopPath ([ordered]@{schema_id="companion.wb55.ssd1681.r11_native_cached_mode2_throw_arc.emergency_stop.v1";reason=$status;detail=$errorText})} } finally {
    if($serial){$serial.Close();$serial.Dispose()}; try{Snapshot}catch{}
    Write-Json $resultPath ([ordered]@{schema_id="companion.wb55.ssd1681.r11_native_cached_mode2_throw_arc.monitor.v2";status=$status;hardware_contact=1;popup_count=0;retry_count=0;qualified=$qualified;loop_records_seen=$loopRecords;cadence_measurements=$cadenceMeasurements;max_start_delta_ms=$maxStartDeltaMs;ring_path=$ringPath;ring_bytes_limit=65536;ring_peak_bytes=$script:ringPeakBytes;ring_final_bytes=if(Test-Path $ringPath){(Get-Item $ringPath).Length}else{$null};ring_snapshot_writes=$script:ringWrites;qualification_snapshot=if(Test-Path $qualificationSnapshotPath){$qualificationSnapshotPath}else{$null};qualification_artifact=if(Test-Path $qualificationArtifact){$qualificationArtifact}else{$null};final_loop_snapshot=if(Test-Path $finalLoopSnapshotPath){$finalLoopSnapshotPath}else{$null};final_loop_artifact=if(Test-Path $finalLoopArtifact){$finalLoopArtifact}else{$null};unbounded_log_created=$false;finalization_attempted=$finalizationAttempted;error=$errorText})
}
if($status -eq "STOP_REQUESTED_AFTER_QUALIFICATION"){exit 0}; exit 1
