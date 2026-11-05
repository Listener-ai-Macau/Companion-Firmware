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
if ($RingBytes -ne 65536) { throw "R10 monitor ring is fixed at exactly 65536 bytes." }
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$out = if ($OutDir) { [IO.Path]::GetFullPath($OutDir) } else { Join-Path $root ".cache\validation\wb55-r10-ball-monitor" }
$ringPath = Join-Path $out "telemetry-ring.log"
$parserArtifact = Join-Path $out "r10-log-parser.json"
$qualificationSnapshotPath = Join-Path $out "qualification-snapshot.log"
$qualificationArtifact = Join-Path $out "qualification-parser.json"
$finalLoopArtifact = Join-Path $out "final-loop-parser.json"
$resultPath = Join-Path $out "monitor-result.json"
$parserScript = Join-Path $PSScriptRoot "verify_wb55_ssd1681_r10_ball_log.py"
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
    $m=[regex]::Match($Line,'loop_iteration=(\d+)'); if(-not $m.Success){throw "Malformed R10 loop telemetry."}
    $iteration=[uint32]$m.Groups[1].Value
    if($null -ne $Previous -and $iteration -ne $Previous+1u){throw "Non-contiguous R10 loop iteration."}
    $positions=@(32,40,48,56,64,56,48,40)
    $current=[int]$positions[([int](($iteration-1u)%8u))]
    $previous=if($iteration -eq 1u){40}else{[int]$positions[([int](($iteration-2u)%8u))]}
    & python $parserScript --validate-loop-line $Line --loop-sequence $iteration --loop-previous-x $previous --loop-current-x $current | Out-Null
    if($LASTEXITCODE -ne 0){throw "R10 full loop frame contract rejected iteration $iteration."}
    return $iteration
}
$serial=$null; $status="NO_GO_MONITOR_UNSTARTED"; $qualified=$false; $observationReady=$false; $lineBuffer=""; $lastIteration=$null; $loopRecords=0; $errorText=$null; $finalizationAttempted=$false
if ($FinalizationSelfTest) {
    $badLog = Join-Path $out "finalization-malformed.log"
    $badArtifact = Join-Path $out "finalization-parser.json"
    $emergency = Join-Path $out "emergency-stop.json"
    $badLine = "[epaper] phase_parallel_r10_ball schema=v1 loop_iteration=1 malformed_complete=1`n"
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
        Write-Json $emergency ([ordered]@{schema_id="companion.wb55.ssd1681.r10_ball.emergency_stop.v1";reason=$status;detail=$errorText;hardware_contact=0})
        Write-Json $resultPath ([ordered]@{schema_id="companion.wb55.ssd1681.r10_ball.monitor.v1";status=$status;hardware_contact=0;popup_count=0;write_counter_sum=0;retry_count=0;stop_requested_after_qualification=$true;finalization_attempted=$true;error=$errorText})
        exit 1
    }
}
if ($SelfTest -or $CheckOnly) {
    Add-Ring ("R10 CheckOnly`n" * 10000); Snapshot
    $r=[ordered]@{schema_id="companion.wb55.ssd1681.r10_ball.monitor.v1";status=if($SelfTest){"PASS_SELFTEST"}else{"READY_NO_HARDWARE_CONTACT"};hardware_contact=0;write_counter_sum=0;popup_count=0;retry_count=0;ring_bytes_limit=65536;ring_peak_bytes=$script:ringPeakBytes;ring_final_bytes=(Get-Item $ringPath).Length;ring_fixed=$true;qualification_parser="verify_wb55_ssd1681_r10_ball_log.py";qualification_snapshot_bounded=$true;fail_closed=@("busy_over_600_ms","malformed_hash","malformed_window","malformed_position","malformed_count","disconnect","storage_fault","qualification_no_go","stop_before_qualification")}
    Write-Json $resultPath $r; $r|ConvertTo-Json -Depth 10; exit 0
}
foreach($path in @($ReadySignalPath,$QualificationSignalPath,$StopSignalPath,$EmergencyStopPath)){if(-not $path){throw "Execute requires all lifecycle signal paths."}}
try {
    $resolved=Get-Port $Port; $serial=[IO.Ports.SerialPort]::new($resolved,115200,[IO.Ports.Parity]::None,8,[IO.Ports.StopBits]::One); $serial.ReadTimeout=250; $serial.Open(); $serial.DiscardInBuffer()
    Write-Json $ReadySignalPath ([ordered]@{schema_id="companion.wb55.ssd1681.r10_ball.monitor_ready.v1";status="READY";process_id=$PID;port=$resolved;ring_bytes_limit=$RingBytes})
    while($true){
        if(Test-Path $EmergencyStopPath){$status="NO_GO_EMERGENCY_STOP";throw "Emergency stop received."}
        if(Test-Path $StopSignalPath){if(-not $qualified){$status="NO_GO_STOP_BEFORE_QUALIFICATION";throw "Stop arrived before qualification."};$status="STOP_REQUESTED_AFTER_QUALIFICATION";break}
        if(@([IO.Ports.SerialPort]::GetPortNames()) -notcontains $resolved){$status="NO_GO_CONTROLLER_DISCONNECT";throw "Serial controller disconnected."}
        $chunk=$serial.ReadExisting(); if($chunk.Length -eq 0){Start-Sleep -Milliseconds 25;continue}; Add-Ring $chunk; $lineBuffer += $chunk
        if($lineBuffer.Length -gt 8192 -and -not $lineBuffer.Contains("`n")){throw "Telemetry record exceeded line bound."}
        while($lineBuffer.Contains("`n")){ $cut=$lineBuffer.IndexOf("`n");$line=$lineBuffer.Substring(0,$cut).TrimEnd("`r");$lineBuffer=$lineBuffer.Substring($cut+1)
            if($line -match '\[epaper\] phase_parallel_r10_ball.*qualification_result=no_go'){throw "Firmware qualification returned no_go."}
            if($line -match '\[epaper\] phase_parallel_r10_ball.* fault '){throw "Firmware emitted an R10 fault record."}
            if($line -match '\[epaper\] phase_parallel_r10_ball.*observation_ready'){$observationReady=$true}
            if($line -match '\[epaper\] phase_parallel_r10_ball.*loop_iteration='){ $lastIteration=Test-Loop $line $lastIteration;$loopRecords++ }
            if($observationReady -and -not $qualified -and $loopRecords -ge 1){
                Snapshot; Copy-Item -LiteralPath $ringPath -Destination $qualificationSnapshotPath -Force
                if((Get-Item $qualificationSnapshotPath).Length -gt 65536){throw "Qualification snapshot exceeded fixed 65536-byte bound."}
                $parserStdout = (& python $parserScript --log $qualificationSnapshotPath --minimum-loop-iterations 1 --hardware-contact 1 --artifact $qualificationArtifact --write | Out-String).Trim()
                if($LASTEXITCODE -ne 0){throw "R10 parser rejected qualification ring."}
                if(-not (Test-Path -LiteralPath $qualificationArtifact -PathType Leaf)){throw "R10 parser returned PASS without writing qualification artifact."}
                $artifactText = (Get-Content -LiteralPath $qualificationArtifact -Raw).Trim()
                if($artifactText -ne $parserStdout){throw "R10 parser artifact does not match its printed parsed object."}
                $qualificationParsed = $artifactText | ConvertFrom-Json
                if($qualificationParsed.status -ne "PASS_R10_BALL_LOG" -or $qualificationParsed.qualification_frames -ne 16 -or $qualificationParsed.ring_bytes -ne 65536 -or $qualificationParsed.hardware_contact -ne 1){throw "R10 qualification artifact is absent, mismatched, incomplete, or not hardware_contact=1."}
                Copy-Item -LiteralPath $qualificationArtifact -Destination $parserArtifact -Force
                Write-Json $QualificationSignalPath ([ordered]@{schema_id="companion.wb55.ssd1681.r10_ball.qualification.v1";status="PASS_R10_QUALIFICATION_READY";process_id=$PID;parser_artifact=$qualificationArtifact;qualification_snapshot=$qualificationSnapshotPath;qualification_frames=16;ring_bytes_limit=65536;hardware_contact=1})
                $qualified=$true
            }
        }
    }
    if(-not $qualified -or -not (Test-Path $qualificationSnapshotPath) -or -not (Test-Path $qualificationArtifact)){throw "Qualification snapshot was not preserved."}
    $finalizationAttempted=$true; Snapshot; & python $parserScript --loop-log $ringPath --minimum-loop-iterations 1 --hardware-contact 1 --artifact $finalLoopArtifact --write | Out-Null; if($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $finalLoopArtifact -PathType Leaf)){throw "Final R10 loop parser rejected telemetry or did not persist its artifact."}
} catch { $errorText=$_.Exception.Message; if($finalizationAttempted){$status="NO_GO_FINALIZATION"} elseif($status -eq "NO_GO_MONITOR_UNSTARTED"){$status="NO_GO_MONITOR_FAULT"}; if($EmergencyStopPath -and -not(Test-Path $EmergencyStopPath)){Write-Json $EmergencyStopPath ([ordered]@{schema_id="companion.wb55.ssd1681.r10_ball.emergency_stop.v1";reason=$status;detail=$errorText})} } finally {
    if($serial){$serial.Close();$serial.Dispose()}; try{Snapshot}catch{}
    Write-Json $resultPath ([ordered]@{schema_id="companion.wb55.ssd1681.r10_ball.monitor.v1";status=$status;hardware_contact=1;popup_count=0;retry_count=0;qualified=$qualified;loop_records_seen=$loopRecords;ring_path=$ringPath;ring_bytes_limit=65536;ring_peak_bytes=$script:ringPeakBytes;ring_final_bytes=if(Test-Path $ringPath){(Get-Item $ringPath).Length}else{$null};ring_snapshot_writes=$script:ringWrites;qualification_snapshot=if(Test-Path $qualificationSnapshotPath){$qualificationSnapshotPath}else{$null};qualification_artifact=if(Test-Path $qualificationArtifact){$qualificationArtifact}else{$null};final_loop_artifact=if(Test-Path $finalLoopArtifact){$finalLoopArtifact}else{$null};unbounded_log_created=$false;finalization_attempted=$finalizationAttempted;error=$errorText})
}
if($status -eq "STOP_REQUESTED_AFTER_QUALIFICATION"){exit 0}; exit 1
