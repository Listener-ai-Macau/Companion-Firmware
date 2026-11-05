param(
    [switch]$CheckOnly,
    [switch]$Execute,
    [switch]$SelfTest,
    [string]$Port,
    [ValidateRange(4096,65536)][int]$RingBytes = 65536,
    [string]$ReadySignalPath,
    [string]$QualificationSignalPath,
    [string]$StopSignalPath,
    [string]$EmergencyStopPath,
    [string]$OutDir
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
[Console]::OutputEncoding = [Text.Encoding]::UTF8
if (@($CheckOnly,$Execute,$SelfTest).Where({ $_ }).Count -ne 1) { throw 'Choose exactly one of -CheckOnly, -Execute, or -SelfTest.' }
if ($RingBytes -ne 65536) { throw 'COMP-REQ-616 monitor ring is fixed at exactly 65536 bytes.' }

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$parser = Join-Path $PSScriptRoot 'verify_comp_req_616_canonical_sync_log.py'
$out = if ($OutDir) { [IO.Path]::GetFullPath($OutDir) } else { Join-Path $repoRoot '.cache\validation\comp-req-616-monitor' }
New-Item -ItemType Directory -Force -Path $out | Out-Null
$ringPath = Join-Path $out 'telemetry-ring.log'
$qualificationSnapshot = Join-Path $out 'qualification-snapshot.log'
$qualificationArtifact = Join-Path $out 'qualification-parser.json'
$finalSnapshot = Join-Path $out 'final-snapshot.log'
$resultPath = Join-Path $out 'monitor-result.json'
$lineBuffer = ''
$ring = ''
$ringPeak = 0
$ringWrites = 0
$framesSeen = 0
$stopCommandWrites = 0
$cleanupSeen = $false
$stopCommand = "COMP_REQ_616_STOP`r`n"
$ready = $false
$status = 'NO_GO_MONITOR_UNSTARTED'
$errorText = $null

function Write-Json([string]$Path,[object]$Value) {
    $parent = Split-Path -Parent ([IO.Path]::GetFullPath($Path))
    if ($parent) { New-Item -ItemType Directory -Force -Path $parent | Out-Null }
    $tmp = "$Path.tmp"
    [IO.File]::WriteAllText($tmp,(($Value | ConvertTo-Json -Depth 16) + "`n"),[Text.UTF8Encoding]::new($false))
    Move-Item -LiteralPath $tmp -Destination $Path -Force
}
function Add-Ring([string]$Text) {
    $script:ring += $Text
    while ([Text.Encoding]::UTF8.GetByteCount($script:ring) -gt $RingBytes) {
        $newline = $script:ring.IndexOf("`n")
        if ($newline -lt 0) { throw 'Telemetry ring overflowed before a line boundary.' }
        $script:ring = $script:ring.Substring($newline + 1)
    }
    $script:ringPeak = [Math]::Max($script:ringPeak,[Text.Encoding]::UTF8.GetByteCount($script:ring))
}
function Snapshot-Ring {
    [IO.File]::WriteAllText($ringPath,$script:ring,[Text.UTF8Encoding]::new($false))
    $script:ringWrites++
    if ((Get-Item -LiteralPath $ringPath).Length -gt $RingBytes) { throw 'Telemetry ring exceeded fixed bound.' }
}
function Resolve-Port([string]$Requested) {
    $ports = @([IO.Ports.SerialPort]::GetPortNames())
    if ($Requested) {
        if ($ports -notcontains $Requested) { throw "Requested serial port is absent: $Requested" }
        return $Requested
    }
    $candidates = @()
    foreach ($device in @(Get-CimInstance Win32_PnPEntity -ErrorAction Stop | Where-Object {
        $value = ([string]$_.Name + ' ' + [string]$_.Description + ' ' + [string]$_.Manufacturer + ' ' + [string]$_.PNPDeviceID)
        ([string]$_.Name -match '\(COM\d+\)') -and $value -match '(?i)ST-LINK|STM32|STMicroelectronics|VID_0483'
    })) {
        $match = [regex]::Match([string]$device.Name,'\((COM\d+)\)')
        if ($match.Success -and $ports -contains $match.Groups[1].Value) { $candidates += $match.Groups[1].Value }
    }
    $candidates = @($candidates | Sort-Object -Unique)
    if ($candidates.Count -ne 1) { throw "Exactly one ST-LINK VCP is required; found: $($candidates -join ', ')" }
    return [string]$candidates[0]
}
function Invoke-Parser([string]$Log,[string]$Artifact,[bool]$RequireCleanup,[int]$HardwareContact) {
    $arguments = @($parser,'--log',$Log,'--out',$Artifact,'--write','--hardware-contact',"$HardwareContact")
    if ($RequireCleanup) { $arguments += '--require-cleanup' }
    & python @arguments | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "COMP-REQ-616 serial parser rejected $Log." }
    return Get-Content -LiteralPath $Artifact -Raw | ConvertFrom-Json
}
function Fill-CheckOnlyRing {
    $sample = "COMP-REQ-616 CheckOnly`n"
    $sampleBytes = [Text.Encoding]::UTF8.GetByteCount($sample)
    $repeat = [Math]::Floor($RingBytes / $sampleBytes)
    $script:ring = $sample * ($repeat + 1)
    $script:ring = $script:ring.Substring($sample.Length)
    $script:ringPeak = [Text.Encoding]::UTF8.GetByteCount($script:ring)
}

if ($SelfTest) {
    & python $parser '--self-test' | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'COMP-REQ-616 serial parser self-test failed.' }
    Fill-CheckOnlyRing; Snapshot-Ring
    $self = [ordered]@{schema='companion.comp_req_616.monitor.v1';status='PASS_SELFTEST';hardware_contact=0;write_counter_sum=0;programmer_calls=0;serial_open_count=0;reset_count=0;refresh_count=0;popup_count=0;retry_count=0;ring_bytes_limit=$RingBytes;ring_fixed=$true;ring_peak_bytes=$script:ringPeak;ring_final_bytes=(Get-Item $ringPath).Length}
    Write-Json $resultPath $self; $self | ConvertTo-Json -Depth 10; exit 0
}
if ($CheckOnly) {
    & python $parser '--self-test' | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'COMP-REQ-616 serial parser self-test failed.' }
    Fill-CheckOnlyRing; Snapshot-Ring
    $check = [ordered]@{schema='companion.comp_req_616.monitor.v1';status='READY_NO_HARDWARE_CONTACT';hardware_contact=0;write_counter_sum=0;programmer_calls=0;serial_open_count=0;reset_count=0;refresh_count=0;popup_count=0;retry_count=0;ring_bytes_limit=$RingBytes;ring_fixed=$true;ring_peak_bytes=$script:ringPeak;ring_final_bytes=(Get-Item $ringPath).Length;parser_sha256=(Get-FileHash $parser -Algorithm SHA256).Hash.ToUpperInvariant()}
    Write-Json $resultPath $check; $check | ConvertTo-Json -Depth 10; exit 0
}

foreach ($path in @($ReadySignalPath,$QualificationSignalPath,$StopSignalPath,$EmergencyStopPath)) {
    if ([string]::IsNullOrWhiteSpace($path)) { throw 'Execute requires all lifecycle signal paths.' }
}
try {
    $resolved = Resolve-Port $Port
    $serial = [IO.Ports.SerialPort]::new($resolved,115200,[IO.Ports.Parity]::None,8,[IO.Ports.StopBits]::One)
    $serial.ReadTimeout = 250
    $serial.Open(); $serial.DiscardInBuffer()
    Write-Json $ReadySignalPath ([ordered]@{schema='companion.comp_req_616.monitor_ready.v1';status='READY';process_id=$PID;port=$resolved;ring_bytes_limit=$RingBytes})
    while ($true) {
        if (Test-Path -LiteralPath $EmergencyStopPath -PathType Leaf) { throw 'Emergency stop received.' }
        if (Test-Path -LiteralPath $StopSignalPath -PathType Leaf) {
            if (-not $ready) { throw 'Stop arrived before the complete first cycle.' }
            if ($stopCommandWrites -eq 0) {
                $serial.Write($stopCommand)
                $serial.BaseStream.Flush()
                $stopCommandWrites++
                Add-Ring "[host] stop_command_sent=COMP_REQ_616_STOP`r`n"
            }
        }
        if (@([IO.Ports.SerialPort]::GetPortNames()) -notcontains $resolved) { throw 'ST-LINK VCP disconnected.' }
        $chunk = $serial.ReadExisting()
        if ($chunk.Length -eq 0) { Start-Sleep -Milliseconds 25; continue }
        $lineBuffer += $chunk
        if ($lineBuffer.Length -gt 8192 -and -not $lineBuffer.Contains("`n")) { throw 'Telemetry line exceeded bound.' }
        while ($lineBuffer.Contains("`n")) {
            $cut = $lineBuffer.IndexOf("`n")
            if ($cut -gt 0 -and $lineBuffer[$cut - 1] -ne "`r") { throw 'Telemetry record must use CRLF.' }
            $line = $lineBuffer.Substring(0,$cut).TrimEnd("`r")
            $lineBuffer = $lineBuffer.Substring($cut + 1)
            # Keep the bounded ring focused on the parser contract.  Boot,
            # touch, and periodic health chatter can otherwise evict init
            # before the 182-frame cycle completes.
            if ($line.StartsWith('[comp-req-616]')) { Add-Ring "$line`r`n" }
            if ($line.StartsWith('[comp-req-616] frame=')) { $framesSeen++ }
            if ($line.StartsWith('[comp-req-616] cleanup=single_fast_white ')) {
                if ($stopCommandWrites -ne 1) { throw 'Cleanup arrived without exactly one host stop command.' }
                if (-not (Test-Path -LiteralPath $qualificationSnapshot -PathType Leaf)) { throw 'Qualification snapshot is missing before cleanup.' }
                $qualificationText = Get-Content -LiteralPath $qualificationSnapshot -Raw
                [IO.File]::WriteAllText($finalSnapshot, $qualificationText + $line + "`r`n", [Text.UTF8Encoding]::new($false))
                $parsed = Invoke-Parser $finalSnapshot $qualificationArtifact $true 1
                if ($parsed.status -ne 'PASS_COMP_REQ_616_CANONICAL_SYNC_LOG') { throw 'Cleanup parser did not pass.' }
                $cleanupSeen = $true
                $status = 'STOP_REQUESTED_AFTER_CLEANUP'
                break
            }
            if ($line.StartsWith('[comp-req-616] observation_ready ')) {
                if ($ready) { throw 'Duplicate observation_ready record.' }
                Snapshot-Ring
                [IO.File]::Copy($ringPath,$qualificationSnapshot,$true)
                $parsed = Invoke-Parser $qualificationSnapshot $qualificationArtifact $false 1
                if ($parsed.status -ne 'PASS_COMP_REQ_616_CANONICAL_SYNC_LOG' -or $parsed.frame_count -ne 182) { throw 'First-cycle qualification did not pass.' }
                Write-Json $QualificationSignalPath ([ordered]@{schema='companion.comp_req_616.qualification.v1';status='PASS_COMP_REQ_616_QUALIFICATION_READY';process_id=$PID;parser_artifact=$qualificationArtifact;qualification_snapshot=$qualificationSnapshot;qualification_frames=$parsed.frame_count;hardware_contact=1;ring_bytes_limit=$RingBytes})
                $ready = $true
            }
        }
        if ($cleanupSeen) { break }
    }
} catch {
    $errorText = $_.Exception.Message
    $status = if ($ready) { 'NO_GO_MONITOR_FAULT_AFTER_QUALIFICATION' } else { 'NO_GO_MONITOR_FAULT_ZERO_CONTACT' }
    if (-not (Test-Path -LiteralPath $EmergencyStopPath -PathType Leaf)) { Write-Json $EmergencyStopPath ([ordered]@{schema='companion.comp_req_616.emergency_stop.v1';reason=$status;detail=$errorText}) }
} finally {
    if ($serial) { if ($serial.IsOpen) { $serial.Close() }; $serial.Dispose() }
    try { Snapshot-Ring } catch {}
    Write-Json $resultPath ([ordered]@{schema='companion.comp_req_616.monitor.v1';status=$status;hardware_contact=1;qualified=$ready;frame_records_seen=$framesSeen;stop_command='COMP_REQ_616_STOP';stop_command_writes=$stopCommandWrites;cleanup_seen=$cleanupSeen;ring_path=$ringPath;ring_bytes_limit=$RingBytes;ring_fixed=$true;ring_peak_bytes=$script:ringPeak;ring_final_bytes=if(Test-Path $ringPath){(Get-Item $ringPath).Length}else{$null};ring_snapshot_writes=$script:ringWrites;qualification_artifact=if(Test-Path $qualificationArtifact){$qualificationArtifact}else{$null};qualification_snapshot=if(Test-Path $qualificationSnapshot){$qualificationSnapshot}else{$null};final_snapshot=if(Test-Path $finalSnapshot){$finalSnapshot}else{$null};unbounded_log_created=$false;error=$errorText})
}
if ($status -eq 'STOP_REQUESTED_AFTER_CLEANUP') { exit 0 }
exit 1
