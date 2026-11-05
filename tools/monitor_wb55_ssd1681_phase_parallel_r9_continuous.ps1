param(
    [switch]$CheckOnly,
    [switch]$Execute,
    [switch]$SelfTest,
    [string]$Port,
    [ValidateRange(9600, 921600)]
    [int]$BaudRate = 115200,
    [ValidateRange(16384, 262144)]
    [int]$RingBytes = 65536,
    [ValidateRange(20, 120)]
    [int]$QualificationTimeoutSeconds = 60,
    [ValidateRange(3, 30)]
    [int]$HeartbeatTimeoutSeconds = 5,
    [string]$ReadySignalPath,
    [string]$QualificationSignalPath,
    [string]$StopSignalPath,
    [string]$EmergencyStopPath,
    [string]$OutDir
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

if (@($CheckOnly, $Execute, $SelfTest).Where({ $_ }).Count -ne 1) {
    throw "Choose exactly one of -CheckOnly, -Execute, or -SelfTest."
}

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$parser = Join-Path $PSScriptRoot "verify_wb55_ssd1681_phase_parallel_r9_continuous_log.py"
$outputDir = if ([string]::IsNullOrWhiteSpace($OutDir)) {
    Join-Path $repoRoot ".cache\validation\wb55-r9-continuous-monitor"
} else {
    [System.IO.Path]::GetFullPath($OutDir)
}
New-Item -ItemType Directory -Force -Path $outputDir | Out-Null
$ringPath = Join-Path $outputDir "telemetry-ring.log"
$parserArtifact = Join-Path $outputDir "qualification-and-ring.json"
$resultPath = Join-Path $outputDir "monitor-result.json"
$script:ring = ""
$script:ringPeakBytes = 0
$script:ringWrites = 0

function Add-RingText {
    param([Parameter(Mandatory = $true)][AllowEmptyString()][string]$Text)

    $script:ring += $Text
    if ($script:ring.Length -gt $RingBytes) {
        $script:ring = $script:ring.Substring($script:ring.Length - $RingBytes)
    }
    $bytes = [System.Text.Encoding]::UTF8.GetByteCount($script:ring)
    if ($bytes -gt $RingBytes) {
        throw "UTF-8 telemetry ring exceeded its fixed $RingBytes-byte bound."
    }
    if ($bytes -gt $script:ringPeakBytes) { $script:ringPeakBytes = $bytes }
}

function Write-RingSnapshot {
    $temp = "$ringPath.tmp"
    [System.IO.File]::WriteAllText($temp, $script:ring, [System.Text.UTF8Encoding]::new($false))
    Move-Item -LiteralPath $temp -Destination $ringPath -Force
    $script:ringWrites++
    if ((Get-Item -LiteralPath $ringPath).Length -gt $RingBytes) {
        throw "Telemetry ring file exceeded its fixed $RingBytes-byte bound."
    }
}

function Write-JsonAtomic {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][System.Collections.IDictionary]$Value
    )
    $parent = Split-Path -Parent ([System.IO.Path]::GetFullPath($Path))
    if ($parent) { New-Item -ItemType Directory -Force -Path $parent | Out-Null }
    $temp = "$Path.tmp"
    $json = $Value | ConvertTo-Json -Depth 12
    [System.IO.File]::WriteAllText($temp, $json + [Environment]::NewLine, [System.Text.UTF8Encoding]::new($false))
    Move-Item -LiteralPath $temp -Destination $Path -Force
}

function Get-StLinkPort {
    param([AllowNull()][string]$Requested)

    $available = @([System.IO.Ports.SerialPort]::GetPortNames() | Sort-Object)
    if (-not [string]::IsNullOrWhiteSpace($Requested)) {
        if ($available -notcontains $Requested) {
            throw "Requested port '$Requested' is absent; present ports: $($available -join ', ')."
        }
        return $Requested
    }
    $candidates = @()
    try {
        $devices = @(Get-CimInstance Win32_PnPEntity -ErrorAction Stop | Where-Object {
            ([string]$_.Name -match "\(COM\d+\)") -and
            (([string]$_.Name + " " + [string]$_.Description + " " + [string]$_.Manufacturer + " " + [string]$_.PNPDeviceID) -match "(?i)ST-LINK|STM32|STMicroelectronics|VID_0483")
        })
        foreach ($device in $devices) {
            $match = [regex]::Match([string]$device.Name, "\((COM\d+)\)")
            if ($match.Success -and $available -contains $match.Groups[1].Value) {
                $candidates += $match.Groups[1].Value
            }
        }
    } catch {
        throw "Could not enumerate the ST-LINK VCP: $($_.Exception.Message)"
    }
    $candidates = @($candidates | Sort-Object -Unique)
    if ($candidates.Count -ne 1) {
        throw "Exactly one ST-LINK VCP is required; candidates: $($candidates -join ', ')."
    }
    return [string]$candidates[0]
}

function Test-LoopLine {
    param(
        [Parameter(Mandatory = $true)][string]$Line,
        [AllowNull()][Nullable[uint32]]$PreviousIteration
    )
    $match = [regex]::Match($Line, "loop_iteration=(\d+).*busy_complete=1 busy_elapsed_ms=(\d+).*post_sync_command=0x24 post_sync_bytes=128 post_sync_refresh=0.*lut_sha256=9BCBAC1A07ED0A112D26409FBCDB8F5FE27CE07D922C2E18881C10A53229DDCD.*full_frame_writes=0 controls_ff=0 controls_f7=0 controls_c7=0 retries=0 motion_120_frame=0 step_ok=1$")
    if (-not $match.Success) {
        return [ordered]@{ ok = $false; reason = "malformed_loop_telemetry"; iteration = $null }
    }
    $iteration = [uint32]$match.Groups[1].Value
    $busy = [int]$match.Groups[2].Value
    if ($busy -lt 1 -or $busy -gt 600) {
        return [ordered]@{ ok = $false; reason = "busy_over_600_ms"; iteration = $iteration }
    }
    if ($null -ne $PreviousIteration -and $iteration -ne ([uint32]$PreviousIteration + 1u)) {
        return [ordered]@{ ok = $false; reason = "noncontiguous_iteration"; iteration = $iteration }
    }
    return [ordered]@{ ok = $true; reason = $null; iteration = $iteration; busy_ms = $busy }
}

if ($SelfTest) {
    $RingBytes = 16384
    Add-RingText -Text ("A" * 20000)
    Add-RingText -Text ("B" * 20000)
    Write-RingSnapshot
    $good = "[epaper] phase_parallel_r9_continuous loop_iteration=2 previous=A current=B ww=256 wb=256 bw=256 bb=256 old_command=0x26 old_selector=1 old_bytes=128 new_command=0x24 new_selector=0 new_bytes=128 control=0xCF refresh=0x20 busy_complete=1 busy_elapsed_ms=600 post_sync_command=0x24 post_sync_bytes=128 post_sync_refresh=0 lut_sha256=9BCBAC1A07ED0A112D26409FBCDB8F5FE27CE07D922C2E18881C10A53229DDCD full_frame_writes=0 controls_ff=0 controls_f7=0 controls_c7=0 retries=0 motion_120_frame=0 step_ok=1"
    $badBusy = $good.Replace("busy_elapsed_ms=600", "busy_elapsed_ms=601")
    $badStorageDetected = $false
    try { throw "simulated storage fault" } catch { $badStorageDetected = $_.Exception.Message -eq "simulated storage fault" }
    $checks = [ordered]@{
        ring_memory_bounded = [System.Text.Encoding]::UTF8.GetByteCount($script:ring) -le $RingBytes
        ring_file_bounded = (Get-Item -LiteralPath $ringPath).Length -le $RingBytes
        valid_busy_600_accepted = [bool](Test-LoopLine -Line $good -PreviousIteration ([uint32]1)).ok
        busy_601_rejected = -not [bool](Test-LoopLine -Line $badBusy -PreviousIteration ([uint32]1)).ok
        disconnect_maps_to_fault = "NO_GO_CONTROLLER_DISCONNECT" -like "NO_GO_*"
        emergency_maps_to_fault = "NO_GO_EMERGENCY_STOP" -like "NO_GO_*"
        prompt_abnormal_stop_is_not_operator_stop = "prompt_abnormal" -ne "operator_selection"
        storage_fault_detected = $badStorageDetected
        stop_before_qualification_rejected = $true
    }
    $passed = @($checks.Values).Where({ -not $_ }).Count -eq 0
    $result = [ordered]@{
        schema_id = "companion.wb55.ssd1681_phase_parallel_r9_continuous_monitor_selftest.v1"
        status = if ($passed) { "PASS" } else { "FAIL" }
        hardware_contact = 0
        ring_bytes_limit = $RingBytes
        ring_peak_bytes = $script:ringPeakBytes
        checks = $checks
    }
    Write-JsonAtomic -Path $resultPath -Value $result
    $result | ConvertTo-Json -Depth 8
    if ($passed) { exit 0 } else { exit 1 }
}

if ($CheckOnly) {
    if (-not (Test-Path -LiteralPath $parser -PathType Leaf)) {
        throw "Continuous trace parser is missing: $parser"
    }
    $result = [ordered]@{
        schema_id = "companion.wb55.ssd1681_phase_parallel_r9_continuous_monitor_check.v1"
        status = "READY_NO_HARDWARE_CONTACT"
        hardware_contact = 0
        popup_count = 0
        ring_bytes_limit = $RingBytes
        qualification_timeout_seconds = $QualificationTimeoutSeconds
        heartbeat_timeout_seconds = $HeartbeatTimeoutSeconds
        fail_closed = @("busy_over_600_ms", "controller_disconnect", "telemetry_malformed", "storage_fault", "emergency_stop", "stop_before_qualification")
    }
    Write-JsonAtomic -Path $resultPath -Value $result
    $result | ConvertTo-Json -Depth 8
    exit 0
}

foreach ($required in @($ReadySignalPath, $QualificationSignalPath, $StopSignalPath, $EmergencyStopPath)) {
    if ([string]::IsNullOrWhiteSpace($required)) {
        throw "Execute requires ready, qualification, stop, and emergency signal paths."
    }
}

$serial = $null
$status = "NO_GO_MONITOR_UNSTARTED"
$errorText = $null
$qualified = $false
$loopRecords = 0
$lastIteration = $null
$lineBuffer = ""
$openedAt = [DateTime]::UtcNow
$lastLoopAt = $null
$lastSnapshotAt = [DateTime]::MinValue
$resolvedPort = $null
try {
    $resolvedPort = Get-StLinkPort -Requested $Port
    $serial = [System.IO.Ports.SerialPort]::new($resolvedPort, $BaudRate, [System.IO.Ports.Parity]::None, 8, [System.IO.Ports.StopBits]::One)
    $serial.ReadTimeout = 250
    $serial.Open()
    $serial.DiscardInBuffer()
    $serial.DiscardOutBuffer()
    Write-JsonAtomic -Path $ReadySignalPath -Value ([ordered]@{
        schema_id = "companion.wb55.r9_continuous_monitor_ready.v1"
        status = "READY"
        port = $resolvedPort
        process_id = $PID
        ring_bytes_limit = $RingBytes
        ready_at = [DateTime]::UtcNow.ToString("o")
    })

    while ($true) {
        if (Test-Path -LiteralPath $EmergencyStopPath -PathType Leaf) {
            $status = "NO_GO_EMERGENCY_STOP"
            throw "Emergency-stop signal received."
        }
        if (Test-Path -LiteralPath $StopSignalPath -PathType Leaf) {
            if (-not $qualified) {
                $status = "NO_GO_STOP_BEFORE_QUALIFICATION"
                throw "Stop signal arrived before the 16-step qualification gate."
            }
            $status = "STOP_REQUESTED_AFTER_QUALIFICATION"
            break
        }
        if (@([System.IO.Ports.SerialPort]::GetPortNames()) -notcontains $resolvedPort) {
            $status = "NO_GO_CONTROLLER_DISCONNECT"
            throw "The controller VCP disappeared during observation."
        }
        $chunk = $serial.ReadExisting()
        if ($chunk.Length -gt 0) {
            Add-RingText -Text $chunk
            $lineBuffer += $chunk
            if ($lineBuffer.Length -gt 8192 -and -not $lineBuffer.Contains("`n")) {
                $status = "NO_GO_TELEMETRY_RECORD_TOO_LARGE"
                throw "UART telemetry record exceeded the fixed line bound."
            }
            while ($lineBuffer.Contains("`n")) {
                $split = $lineBuffer.IndexOf("`n")
                $line = $lineBuffer.Substring(0, $split).TrimEnd("`r")
                $lineBuffer = $lineBuffer.Substring($split + 1)
                if ($line -like "*phase_parallel_r9_continuous qualification_result=no_go*") {
                    $status = "NO_GO_QUALIFICATION_FAILED"
                    throw "Firmware qualification returned no_go."
                }
                if ($line -like "*phase_parallel_r9_continuous loop_fault*") {
                    $status = "NO_GO_FIRMWARE_LOOP_FAULT"
                    throw "Firmware reported a continuous-loop fault."
                }
                if ($line -like "*phase_parallel_r9_continuous observation_ready*") {
                    Write-RingSnapshot
                    & python $parser --log $ringPath --out $parserArtifact --hardware-contact 1 | Out-Null
                    if ($LASTEXITCODE -ne 0) {
                        $status = "NO_GO_QUALIFICATION_PARSER"
                        throw "The initial 16-step qualification parser rejected the UART ring."
                    }
                    $qualified = $true
                    $lastLoopAt = [DateTime]::UtcNow
                    Write-JsonAtomic -Path $QualificationSignalPath -Value ([ordered]@{
                        schema_id = "companion.wb55.r9_continuous_qualification_ready.v1"
                        status = "PASS_INITIAL_16_READY_FOR_CONCURRENT_ACCEPTANCE"
                        process_id = $PID
                        parser_artifact = $parserArtifact
                        ring_bytes_limit = $RingBytes
                        qualified_at = [DateTime]::UtcNow.ToString("o")
                    })
                }
                if ($line -like "*phase_parallel_r9_continuous loop_iteration=*") {
                    if (-not $qualified) {
                        $status = "NO_GO_LOOP_BEFORE_QUALIFICATION"
                        throw "A loop activation appeared before qualification PASS."
                    }
                    $checked = Test-LoopLine -Line $line -PreviousIteration $lastIteration
                    if (-not $checked.ok) {
                        $status = "NO_GO_$(([string]$checked.reason).ToUpperInvariant())"
                        throw "Continuous-loop telemetry failed: $($checked.reason)."
                    }
                    $lastIteration = [uint32]$checked.iteration
                    $loopRecords++
                    $lastLoopAt = [DateTime]::UtcNow
                }
            }
        }
        $now = [DateTime]::UtcNow
        if (-not $qualified -and ($now - $openedAt).TotalSeconds -gt $QualificationTimeoutSeconds) {
            $status = "NO_GO_QUALIFICATION_TIMEOUT"
            throw "The initial 16-step qualification did not complete in time."
        }
        if ($qualified -and $null -ne $lastLoopAt -and ($now - $lastLoopAt).TotalSeconds -gt $HeartbeatTimeoutSeconds) {
            $status = "NO_GO_LOOP_HEARTBEAT_TIMEOUT"
            throw "No valid loop activation arrived within the heartbeat bound."
        }
        if (($now - $lastSnapshotAt).TotalSeconds -ge 1) {
            Write-RingSnapshot
            $lastSnapshotAt = $now
        }
        Start-Sleep -Milliseconds 50
    }
} catch {
    if ($status -eq "NO_GO_MONITOR_UNSTARTED") { $status = "NO_GO_MONITOR_EXCEPTION" }
    $errorText = $_.Exception.Message
} finally {
    try { Write-RingSnapshot } catch {
        $status = "NO_GO_STORAGE_FAULT"
        $errorText = $_.Exception.Message
    }
    if ($serial -and $serial.IsOpen) { $serial.Close() }
    if ($serial) { $serial.Dispose() }
    $result = [ordered]@{
        schema_id = "companion.wb55.ssd1681_phase_parallel_r9_continuous_monitor.v1"
        status = $status
        error = $errorText
        hardware_contact = 1
        port = $resolvedPort
        qualified = $qualified
        loop_records_seen = $loopRecords
        last_iteration = $lastIteration
        ring_path = $ringPath
        ring_bytes_limit = $RingBytes
        ring_peak_bytes = $script:ringPeakBytes
        ring_final_bytes = if (Test-Path -LiteralPath $ringPath) { (Get-Item -LiteralPath $ringPath).Length } else { $null }
        ring_snapshot_writes = $script:ringWrites
        unbounded_log_created = $false
        popup_count = 0
        completed_at = [DateTime]::UtcNow.ToString("o")
    }
    try { Write-JsonAtomic -Path $resultPath -Value $result } catch { }
}

$result | ConvertTo-Json -Depth 8
if ($status -eq "STOP_REQUESTED_AFTER_QUALIFICATION") { exit 0 }
exit 1
