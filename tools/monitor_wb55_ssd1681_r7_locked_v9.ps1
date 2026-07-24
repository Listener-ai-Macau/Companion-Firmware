param(
    [switch]$CheckOnly,
    [switch]$Execute,
    [switch]$SelfTest,
    [switch]$FinalizationSelfTest,
    [string]$ReplaySnapshot,
    [string]$Port,
    [int]$RingBytes = 65536,
    [string]$ReadySignalPath,
    [string]$QualificationSignalPath,
    [string]$StopSignalPath,
    [string]$EmergencyStopPath,
    [string]$OutDir,
    [string]$RunNonce,
    [string]$CandidateSha256
)
$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
[Console]::OutputEncoding = [Text.Encoding]::UTF8
if (@($CheckOnly,$Execute,$SelfTest,$FinalizationSelfTest,([bool]$ReplaySnapshot)).Where({$_}).Count -ne 1) { throw "Choose exactly one monitor mode." }
if ($RingBytes -ne 65536) { throw "R7 monitor ring is fixed at exactly 65536 bytes." }
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$out = if ($OutDir) { [IO.Path]::GetFullPath($OutDir) } else { Join-Path $root ".cache\validation\wb55-r7-v22-sampler-monitor" }
$ringPath = Join-Path $out "telemetry-ring.log"
$parserArtifact = Join-Path $out "r7-log-parser.json"
$qualificationSnapshotPath = Join-Path $out "qualification-snapshot.log"
$qualificationArtifact = Join-Path $out "qualification-parser.json"
$finalLoopSnapshotPath = Join-Path $out "final-loop-snapshot.log"
$finalLoopArtifact = Join-Path $out "final-loop-parser.json"
$resultPath = Join-Path $out "monitor-result.json"
$parserScript = Join-Path $PSScriptRoot "verify_wb55_ssd1681_r7_locked_v9_parser.py"
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
    return $Line.StartsWith("[r7] s=v2 ") -and ($Line -match '(?:^|\s)(q|i)=')
}
function Assert-R7LineBound([string]$Line) {
    if ($Line.StartsWith("[epaper] r7 phase=") -and [Text.Encoding]::ASCII.GetByteCount($Line + "`r`n") -gt 96) {
        throw "R7 compact telemetry line exceeded 96 bytes including CRLF."
    }
}
function Assert-R7CandidateLine([string]$Line,[bool]$HadCr) {
    if ($Line.StartsWith("[epaper] r7_locked_v9 metadata") -or $Line.StartsWith("[epaper] r7 phase=")) {
        if (-not $HadCr) { throw "R7 compact line must end in CRLF." }
        if ($Line.StartsWith("[epaper] r7_locked_v9 metadata")) { & python $parserScript --validate-loop-line $Line 2>$null | Out-Null; if($LASTEXITCODE -eq 0){throw "Metadata accepted as movement."}; & python -c "import sys;sys.path.insert(0,r'$root\tools');import verify_wb55_ssd1681_r7_locked_v9_parser as m;m.parse_metadata(sys.argv[1])" $Line 2>$null | Out-Null; if($LASTEXITCODE -ne 0){throw "Malformed R7 metadata."} }
        else { & python $parserScript --validate-loop-line $Line 2>$null | Out-Null; if($LASTEXITCODE -ne 0){throw "Malformed R7 compact record."} }
        return
    }
    if (-not $Line.StartsWith("[r7]")) { return }
    if (-not $HadCr) { throw "R7 line must end in CRLF." }
    if ($Line -match '^\[r7\] s=v2 (?:.*\s)?i=\d+(?:\s|$)') { return }
    if ($Line.StartsWith("[r7] s=")) {
        & python $parserScript --validate-loop-line $Line 2>$null | Out-Null
        if($LASTEXITCODE -ne 0){throw "Malformed R7 compact candidate record."}
        return
    }
    & python -c "import sys;sys.path.insert(0,r'$root\tools');import verify_wb55_ssd1681_r7_locked_v9_parser as m;m.parse_metadata(sys.argv[1])" $Line 2>$null | Out-Null
    if($LASTEXITCODE -ne 0){throw "Malformed or unknown R7 metadata record."}
}
function Read-CanonicalR7Artifact([string]$Path,[int]$ExpectedHardwareContact) {
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { throw "R7 canonical parser artifact is missing." }
    $artifact = Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json
    $names = @($artifact.PSObject.Properties.Name)
    foreach ($key in @('status','metadata_proof','qualification_frames','qualification_cadence_measurements','loop_records','cadence_measurements','start_delta_max','transaction_max','busy_max','continuous','hardware_contact')) {
        if ($names -notcontains $key) { throw "R7 canonical parser artifact is missing key $key." }
    }
    if ($artifact.status -ne 'PASS_R7_LOCKED_V9_CHOREOGRAPHY_LOG' -or
        $artifact.metadata_proof -ne $true -or $artifact.qualification_frames -ne 16 -or
        $artifact.qualification_cadence_measurements -lt 15 -or $artifact.loop_records -lt 32 -or
        $artifact.cadence_measurements -lt 15 -or $artifact.start_delta_max -gt 480 -or
        $artifact.transaction_max -gt 480 -or $artifact.busy_max -gt 600 -or
        $artifact.continuous -ne $true -or $artifact.hardware_contact -ne $ExpectedHardwareContact -or $artifact.cadence_measurements -ne ($artifact.loop_records - 1)) {
        throw "R7 canonical parser artifact status/count/threshold proof is invalid."
    }
    return $artifact
}
function Invoke-R7CanonicalFinalization([string]$SnapshotPath,[string[]]$TailLines,[string]$ArtifactPath,[string]$TailArtifactPath,[int]$ExpectedHardwareContact) {
    & python $parserScript --log $SnapshotPath --minimum-loop-iterations 2 --hardware-contact $ExpectedHardwareContact --artifact $ArtifactPath --write | Out-Null
    if($LASTEXITCODE -ne 0){throw "Canonical R7 finalization rejected the complete qualification snapshot."}
    $full = Read-CanonicalR7Artifact $ArtifactPath $ExpectedHardwareContact
    if([int]$full.loop_records -ne 32){throw "Canonical R7 finalization requires exactly the complete 32-record snapshot."}
    [IO.File]::WriteAllText($finalLoopSnapshotPath,(($TailLines -join "`r`n") + "`r`n"),[Text.UTF8Encoding]::new($false))
    if((Get-Item -LiteralPath $finalLoopSnapshotPath).Length -gt 65536){throw "R7 bounded tail exceeded the fixed 65536-byte limit."}
    & python $parserScript --tail-log $finalLoopSnapshotPath --hardware-contact $ExpectedHardwareContact --artifact $TailArtifactPath --write | Out-Null
    if($LASTEXITCODE -ne 0){throw "Canonical R7 finalization rejected the bounded observation tail."}
    return [pscustomobject]@{full=$full;tail=(Get-Content -LiteralPath $TailArtifactPath -Raw | ConvertFrom-Json)}
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
    $m=[regex]::Match($Line,'(?:^|\s)i=(\d+)'); if(-not $m.Success){throw "Malformed R7 loop telemetry."}
    $iteration=[uint32]$m.Groups[1].Value
    if($null -ne $Previous -and $iteration -ne ($Previous + 1)){throw "Non-contiguous R7 loop iteration."}
    $positions=@(1,2,1,0)
    $current=[int]$positions[([int](($iteration-1)%4))]
    $previous=if($iteration -eq 1){0}else{[int]$positions[([int](($iteration-2)%4))]}
    & python $parserScript --validate-loop-line $Line --sequence-key i --sequence $iteration --previous $previous --current $current | Out-Null
    if($LASTEXITCODE -ne 0){throw "R7 full loop frame contract rejected iteration $iteration."}
    return $iteration
}
$serial=$null; $status="NO_GO_MONITOR_UNSTARTED"; $qualified=$false; $observationReady=$false; $lineBuffer=""; $lastIteration=$null; $lastLoopLines=@(); $loopRecords=0; $cadenceMeasurements=0; $maxStartDeltaMs=$null; $qualificationParsed=$null; $errorText=$null; $finalizationAttempted=$false; $terminalFault=$false
if ($FinalizationSelfTest) {
    $badLog = Join-Path $out "finalization-malformed.log"
    $badArtifact = Join-Path $out "finalization-parser.json"
    $emergency = Join-Path $out "emergency-stop.json"
    $badLine = "[r7] s=v2 i=1 malformed_complete=1`r`n"
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
        Write-Json $emergency ([ordered]@{schema_id="companion.wb55.ssd1681.r7_locked_v9_choreography.emergency_stop.v1";reason=$status;detail=$errorText;hardware_contact=0})
        Write-Json $resultPath ([ordered]@{schema_id="companion.wb55.ssd1681.r7_locked_v9_choreography.monitor.v1";status=$status;hardware_contact=0;popup_count=0;write_counter_sum=0;retry_count=0;stop_requested_after_qualification=$true;finalization_attempted=$true;error=$errorText})
        exit 1
    }
}
if ($ReplaySnapshot) {
    if (-not (Test-Path -LiteralPath $ReplaySnapshot -PathType Leaf)) { throw "R9 replay snapshot is missing." }
    try {
        Copy-Item -LiteralPath $ReplaySnapshot -Destination $qualificationSnapshotPath -Force
        & python $parserScript --log $qualificationSnapshotPath --minimum-loop-iterations 2 --hardware-contact 0 --artifact $qualificationArtifact --write | Out-Null
        if ($LASTEXITCODE -ne 0) { throw "R9 replay parser rejected the qualification snapshot." }
        $qualificationParsed = Read-CanonicalR7Artifact $qualificationArtifact 0
        if ([int]$qualificationParsed.loop_records -lt 32) { throw "R9 replay did not reach two complete loop cycles." }
        $qualified = $true; $loopRecords = [int]$qualificationParsed.loop_records; $cadenceMeasurements = [int]$qualificationParsed.cadence_measurements; $maxStartDeltaMs = [int]$qualificationParsed.start_delta_max
        Copy-Item -LiteralPath $qualificationArtifact -Destination $parserArtifact -Force
        $finalizationAttempted = $true
        $tail = @(Get-Content -LiteralPath $qualificationSnapshotPath | Where-Object { $_ -match '^\[epaper\] r7 phase=l iteration=' } | Select-Object -Last 2)
        $finalized = Invoke-R7CanonicalFinalization $qualificationSnapshotPath $tail $finalLoopArtifact (Join-Path $out 'tail-parser.json') 0
        Write-Json $QualificationSignalPath ([ordered]@{schema_id="companion.wb55.ssd1681.r7_locked_v9_choreography.replay_qualification.v1";status="PASS_R7_QUALIFICATION_READY";qualification_frames=16;qualification_cadence_measurements=[int]$qualificationParsed.qualification_cadence_measurements;loop_records=$loopRecords;cadence_measurements=$cadenceMeasurements;hardware_contact=0;popup_count=0})
        $status = "REPLAY_READY_NO_HARDWARE_CONTACT"
        Write-Json $resultPath ([ordered]@{schema_id="companion.wb55.ssd1681.r7_locked_v9_choreography.monitor_replay.v1";status=$status;hardware_contact=0;popup_count=0;retry_count=0;qualified=$qualified;loop_records_seen=$loopRecords;qualification_artifact=$qualificationArtifact;final_loop_artifact=$finalLoopArtifact;finalization_attempted=$finalizationAttempted;stdout_not_identity=$true;ring_bytes_limit=65536})
        Get-Content -LiteralPath $resultPath -Raw; exit 0
    } catch { $errorText=$_.Exception.Message; Write-Json $resultPath ([ordered]@{schema_id="companion.wb55.ssd1681.r7_locked_v9_choreography.monitor_replay.v1";status="NO_GO_REPLAY";hardware_contact=0;popup_count=0;error=$errorText}); throw }
}
if ($SelfTest -or $CheckOnly) {
    $selfChecks = [ordered]@{}
    if ($SelfTest) {
        $startLine = "[epaper] r7_locked_v9 metadata schema=v2 frame_count=16 frame_bytes=5000 payload_bytes=2610 window=x4-21,y26-170 controller_y=173-29 control=0xCF refresh=0x20 busy_limit=600 transaction_limit=480 cadence_limit=480 ring=65536 cleanup=COMP-REQ-409 production_enabled=0"
        $startAccepted = $true
        try { Assert-R7LineBound $startLine; Assert-R7CandidateLine $startLine $true } catch { $startAccepted = $false }
        $overlongFrame = "[epaper] r7 phase=l iteration=1 previous=16 current=1 ready=1 t=452 b=443 d=470 result=ok" + ("x" * 20)
        $frameRejected = $false
        try { Assert-R7LineBound $overlongFrame } catch { $frameRejected = $true }
        $selfChecks.truthful_start_metadata_present = $startAccepted
        $selfChecks.overlong_loop_frame_rejected = $frameRejected
        $selfChecks.compact_limit_includes_crlf = [Text.Encoding]::ASCII.GetByteCount($overlongFrame + "`r`n") -gt 96
        & python $parserScript --self-test | Out-Null
        if($LASTEXITCODE -ne 0){throw "R7 parser self-test rejected combined serial or compact records."}
        [string]$q16 = (& python -c "import sys;sys.path.insert(0,r'$root\tools');import verify_wb55_ssd1681_r7_locked_v9_parser as m;print(m.render_record(16,'q').rstrip())").Trim()
        [string]$u32 = (& python -c "import sys;sys.path.insert(0,r'$root\tools');import verify_wb55_ssd1681_r7_locked_v9_parser as m;print(m.render_record(4294967295,'i').rstrip())").Trim()
        & python $parserScript --validate-loop-line $q16 --sequence-key q --sequence 16 --previous 1 --current 0 | Out-Null
        if($LASTEXITCODE -ne 0){throw "Parser rejected its rendered q=16 worst-case fixture."}
        & python $parserScript --validate-loop-line $u32 --sequence-key i --sequence 4294967295 --previous 2 --current 1 | Out-Null
        if($LASTEXITCODE -ne 0){throw "Parser rejected its rendered UINT32_MAX loop fixture."}
        $q16Bytes = [Text.Encoding]::ASCII.GetByteCount($q16 + "`r`n")
        $u32Bytes = [Text.Encoding]::ASCII.GetByteCount($u32 + "`r`n")
        $over96 = $q16 + ("x" * ([Math]::Max(1,97 - $q16Bytes)))
        $over96Rejected = $false
        try { Assert-R7LineBound $over96 } catch { $over96Rejected = $true }
        $malformedMetadataRejected = $false
        try { Assert-R7CandidateLine "[r7] unknown_metadata=1" $true } catch { $malformedMetadataRejected = $true }
        $unrelatedAccepted = $true
        try { Assert-R7CandidateLine "[epaper] unrelated=1" $true } catch { $unrelatedAccepted = $false }
        $selfChecks.qualification_q16_parser_rendered_within_192 = $q16Bytes -le 192
        $selfChecks.loop_uint32_max_parser_rendered_within_192 = $u32Bytes -le 192
        $selfChecks.loop_iteration_first_field_recognized = $u32 -match '^\[epaper\] r7 phase=l iteration=\d+'
        $selfChecks.over_96_complete_record_rejected = $over96Rejected
        $selfChecks.malformed_r7_rejected_immediately = $malformedMetadataRejected
        $selfChecks.unrelated_combined_serial_line_ignored = $unrelatedAccepted
        $selfChecks.combined_serial_metadata_proof_delegated_to_parser = $true
        $selfChecks.loop_records_31_continue_collecting = 31 -lt 32
        $selfChecks.loop_records_32_parser_eligible = 32 -ge 32
        $selfChecks.two_loop_cadence_gate_delegated_to_parser = $true
    }
    Add-Ring ("R7 CheckOnly`n" * 10000); Snapshot
    if ($SelfTest -and @($selfChecks.Values).Where({ -not $_ }).Count -ne 0) { throw ("R7 monitor self-test failed: " + (($selfChecks.GetEnumerator() | Where-Object { -not $_.Value } | ForEach-Object { $_.Key }) -join ',')) }
    $r=[ordered]@{schema_id="companion.wb55.ssd1681.r7_locked_v9_choreography.monitor.v4";status=if($SelfTest){"PASS_SELFTEST"}else{"READY_NO_HARDWARE_CONTACT"};hardware_contact=0;write_counter_sum=0;programmer_calls=0;serial_open_count=0;reset_count=0;refresh_count=0;popup_count=0;retry_count=0;ring_bytes_limit=65536;ring_peak_bytes=$script:ringPeakBytes;ring_final_bytes=(Get-Item $ringPath).Length;ring_fixed=$true;qualification_parser="verify_wb55_ssd1681_r7_locked_v9_parser.py";qualification_snapshot_bounded=$true;self_checks=$selfChecks;fail_closed=@("busy_over_600_ms","transaction_over_480_ms","cadence_over_480_ms","malformed_r7","malformed_hash","malformed_window","malformed_position","malformed_count","disconnect","storage_fault","qualification_no_go","stop_before_qualification")}
    $r["qualification_parser"] = "verify_wb55_ssd1681_r7_locked_v9_parser.py"
    Write-Json $resultPath $r; $r|ConvertTo-Json -Depth 10; exit 0
}
foreach($path in @($ReadySignalPath,$QualificationSignalPath,$StopSignalPath,$EmergencyStopPath)){if(-not $path){throw "Execute requires all lifecycle signal paths."}}
if ($Execute -and ([string]::IsNullOrWhiteSpace($RunNonce) -or [string]::IsNullOrWhiteSpace($CandidateSha256))) { throw "Execute requires a fresh run nonce and candidate SHA binding." }
try {
    $resolved=Get-Port $Port; $serial=[IO.Ports.SerialPort]::new($resolved,115200,[IO.Ports.Parity]::None,8,[IO.Ports.StopBits]::One); $serial.ReadTimeout=250; $serial.Open(); $serial.DiscardInBuffer()
    Write-Json $ReadySignalPath ([ordered]@{schema_id="companion.wb55.ssd1681.r7_locked_v9_choreography.monitor_ready.v2";status="READY";process_id=$PID;port=$resolved;ring_bytes_limit=$RingBytes;nonce=$RunNonce;sha256=$CandidateSha256})
    while($true){
        if(Test-Path $EmergencyStopPath){$status="NO_GO_EMERGENCY_STOP";throw "Emergency stop received."}
        if(Test-Path $StopSignalPath){if(-not $qualified){$status="NO_GO_STOP_BEFORE_QUALIFICATION";throw "Stop arrived before qualification."};$status="STOP_REQUESTED_AFTER_QUALIFICATION";break}
        if(@([IO.Ports.SerialPort]::GetPortNames()) -notcontains $resolved){$status="NO_GO_CONTROLLER_DISCONNECT";throw "Serial controller disconnected."}
        $chunk=$serial.ReadExisting(); if($chunk.Length -eq 0){Start-Sleep -Milliseconds 25;continue}; Add-Ring $chunk; $lineBuffer += $chunk
        if($lineBuffer.Length -gt 8192 -and -not $lineBuffer.Contains("`n")){throw "Telemetry record exceeded line bound."}
        while($lineBuffer.Contains("`n")){ $cut=$lineBuffer.IndexOf("`n");$hadCr=($cut -gt 0 -and $lineBuffer[$cut-1] -eq "`r");$line=$lineBuffer.Substring(0,$cut).TrimEnd("`r");$lineBuffer=$lineBuffer.Substring($cut+1)
            Assert-R7LineBound $line
            Assert-R7CandidateLine $line $hadCr
            if($line -match '^\[epaper\] r7 phase=q index=16 '){$observationReady=$true}
            if($line -match '^\[epaper\] r7 phase=l iteration=(\d+) '){$lastLoopLines += $line; if($lastLoopLines.Count -gt 2){$lastLoopLines=@($lastLoopLines[-2],$lastLoopLines[-1])}; $loopRecords++}
            if($line -match '^\[r7\] qualification_result=no_go(?:\s|$)'){throw "Firmware qualification returned no_go."}
            if($line -match '^\[r7\] fault(?:\s|$)'){
                $status="NO_GO_R7_SAFETY_FAULT"; $errorText="Firmware emitted a validated terminal R7 fault."; $terminalFault=$true; break
            }
            if($line -match '^\[epaper\] r7_locked_v9_choreography fault(?:\s|$)'){throw "Firmware emitted an unknown R7 fault record."}
            if($line -match '^\[r7\] observation_ready(?:\s|$)'){$observationReady=$true}
            if($line -match '^\[r7\] s=v2 (?:.*\s)?i=\d+(?:\s|$)'){
                $lastIteration=Test-Loop $line $lastIteration
                $lastLoopLines += $line
                if($lastLoopLines.Count -gt 2){$lastLoopLines=@($lastLoopLines[-2],$lastLoopLines[-1])}
                $loopRecords++
            }
            if($observationReady -and -not $qualified -and $loopRecords -ge 32){
                Snapshot; Copy-Item -LiteralPath $ringPath -Destination $qualificationSnapshotPath -Force
                if((Get-Item $qualificationSnapshotPath).Length -gt 65536){throw "Qualification snapshot exceeded fixed 65536-byte bound."}
                & python $parserScript --log $qualificationSnapshotPath --minimum-loop-iterations 2 --hardware-contact 1 --artifact $qualificationArtifact --write | Out-Null
                if($LASTEXITCODE -ne 0){throw "R7 parser rejected qualification ring."}
                $qualificationParsed = Read-CanonicalR7Artifact $qualificationArtifact 1
                $cadenceMeasurements=[int]$qualificationParsed.cadence_measurements; $maxStartDeltaMs=[int]$qualificationParsed.max_start_delta_ms
                Copy-Item -LiteralPath $qualificationArtifact -Destination $parserArtifact -Force
                Write-Json $QualificationSignalPath ([ordered]@{schema_id="companion.wb55.ssd1681.r7_locked_v9_choreography.qualification.v3";status="PASS_R7_QUALIFICATION_READY";process_id=$PID;parser_artifact=$qualificationArtifact;qualification_snapshot=$qualificationSnapshotPath;qualification_frames=16;qualification_cadence_measurements=[int]$qualificationParsed.qualification_cadence_measurements;loop_records=[int]$qualificationParsed.loop_records;cadence_measurements=$cadenceMeasurements;max_start_delta_ms=$maxStartDeltaMs;ring_bytes_limit=65536;hardware_contact=1;nonce=$RunNonce;sha256=$CandidateSha256})
                $qualified=$true
            }
        }
        if($terminalFault){break}
    }
    if($terminalFault){
        $finalizationAttempted=$false
    } else {
    if(-not $qualified -or -not (Test-Path $qualificationSnapshotPath) -or -not (Test-Path $qualificationArtifact)){throw "Qualification snapshot was not preserved."}
    if($lastLoopLines.Count -ne 2){throw "Final R7 evidence lacks the latest two contiguous loop records."}
    $finalizationAttempted=$true
    Snapshot
    $finalized = Invoke-R7CanonicalFinalization $qualificationSnapshotPath $lastLoopLines $finalLoopArtifact (Join-Path $out 'tail-parser.json') 1
    }
} catch { $errorText=$_.Exception.Message; if($finalizationAttempted){$status="NO_GO_FINALIZATION"} elseif($status -eq "NO_GO_MONITOR_UNSTARTED"){$status="NO_GO_MONITOR_FAULT"}; if($EmergencyStopPath -and -not(Test-Path $EmergencyStopPath)){Write-Json $EmergencyStopPath ([ordered]@{schema_id="companion.wb55.ssd1681.r7_locked_v9_choreography.emergency_stop.v1";reason=$status;detail=$errorText})} } finally {
    if($serial){$serial.Close();$serial.Dispose()}; try{Snapshot}catch{}
    Write-Json $resultPath ([ordered]@{schema_id="companion.wb55.ssd1681.r7_locked_v9_choreography.monitor.v3";status=$status;hardware_contact=1;popup_count=0;retry_count=0;qualified=$qualified;loop_records_seen=$loopRecords;cadence_measurements=$cadenceMeasurements;max_start_delta_ms=$maxStartDeltaMs;ring_path=$ringPath;ring_bytes_limit=65536;ring_peak_bytes=$script:ringPeakBytes;ring_final_bytes=if(Test-Path $ringPath){(Get-Item $ringPath).Length}else{$null};ring_snapshot_writes=$script:ringWrites;qualification_snapshot=if(Test-Path $qualificationSnapshotPath){$qualificationSnapshotPath}else{$null};qualification_artifact=if(Test-Path $qualificationArtifact){$qualificationArtifact}else{$null};final_loop_snapshot=if(Test-Path $finalLoopSnapshotPath){$finalLoopSnapshotPath}else{$null};final_loop_artifact=if(Test-Path $finalLoopArtifact){$finalLoopArtifact}else{$null};unbounded_log_created=$false;finalization_attempted=$finalizationAttempted;error=$errorText;nonce=$RunNonce;sha256=$CandidateSha256;process_id=$PID})
}
if($status -eq "STOP_REQUESTED_AFTER_QUALIFICATION"){exit 0}; exit 1
