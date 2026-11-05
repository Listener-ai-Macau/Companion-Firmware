param(
    [string] $PortName = "COM13",
    [int] $BaudRate = 115200,
    [string] $ProgrammerSerial = "066EFF535570514867221931",
    [switch] $FullInternalOtaChain
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repo = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$runRoot = Join-Path $repo ".cache\validation\comp-req-771-accepted-path-comparison\hardware-run"
$privateRoot = Join-Path $runRoot "private"
$programmer = "C:\ST\STM32CubeIDE_2.1.1\STM32CubeIDE\plugins\com.st.stm32cube.ide.mcu.externaltools.cubeprogrammer.win32_2.2.400.202601091506\tools\bin\STM32_Programmer_CLI.exe"
$loader = Join-Path $repo "cubeide\Companion_BLE_Ota_Loader\build\Companion_BLE_Ota_Loader.hex"
$image = Join-Path $repo "cubeide\Companion_Nucleo_WB55RG_Bringup\build_comp_req_616_ota_compare\Companion_CompReq616_OtaCompare.hex"
$backupA = Join-Path $privateRoot "preflash-full-a.bin"
$backupB = Join-Path $privateRoot "preflash-full-b.bin"
$finalReadback = Join-Path $privateRoot "compare-full-readback.bin"
$serialLog = Join-Path $runRoot "hardware-serial.log"
$runLog = Join-Path $runRoot "hardware-run.json"
$callsLog = Join-Path $runRoot "programmer-calls.json"
$machineArtifact = Join-Path $runRoot "MACHINE_READY.json"
$events = [System.Collections.Generic.List[object]]::new()
$calls = [System.Collections.Generic.List[object]]::new()
$serial = $null
$mutex = $null
$owned = $false
$hardwareContact = $false
$writeStarted = $false
$machineReady = $false
$restoreAttempted = $false
$restored = $false

New-Item -ItemType Directory -Force -Path $privateRoot | Out-Null

function Add-Event {
    param([string] $Name, [string] $Status, [hashtable] $Detail = @{})
    $events.Add([ordered]@{
        at = (Get-Date).ToUniversalTime().ToString("o")
        name = $Name
        status = $Status
        detail = $Detail
    })
}

function Save-Run {
    param([string] $Status)
    $calls | ConvertTo-Json -Depth 5 |
        Set-Content -LiteralPath $callsLog -Encoding UTF8
    [ordered]@{
        schema = "companion.comp_req_771.accepted_path_compare_run.v1"
        requirement = "COMP-REQ-771"
        status = $Status
        hardware_contact = [int]$hardwareContact
        flash = $writeStarted
        full_internal_ota_chain = [bool]$FullInternalOtaChain
        external_flash_write = $false
        mass_erase = $false
        read_unprotect = $false
        option_bytes = $false
        programmer_serial = $ProgrammerSerial
        serial_port = $PortName
        swd_com_lock_acquired = $owned
        restore_attempted = $restoreAttempted
        restored = $restored
        events = $events
    } | ConvertTo-Json -Depth 10 |
        Set-Content -LiteralPath $runLog -Encoding UTF8
}

function Invoke-Programmer {
    param([string] $Name, [string[]] $Arguments)
    $log = Join-Path $runRoot "$Name-programmer.log"
    $output = & $programmer @Arguments 2>&1
    $exitCode = $LASTEXITCODE
    $output | Set-Content -LiteralPath $log -Encoding UTF8
    $calls.Add([ordered]@{
        name = $Name
        exit_code = $exitCode
        arguments = ($Arguments -join " ")
        log = $log
    })
    if ($exitCode -ne 0) {
        Add-Event $Name "FAIL" @{ exit_code = $exitCode }
        throw "STM32CubeProgrammer failed during $Name"
    }
    Add-Event $Name "PASS" @{ arguments = ($Arguments -join " ") }
}

function Capture-Serial {
    param([int] $Seconds)
    $builder = [System.Text.StringBuilder]::new()
    $deadline = (Get-Date).AddSeconds($Seconds)
    while ((Get-Date) -lt $deadline) {
        $chunk = $serial.ReadExisting()
        if ($chunk.Length -gt 0) {
            [void]$builder.Append($chunk)
            $text = $builder.ToString()
            $text | Set-Content -LiteralPath $serialLog -Encoding UTF8
            if ([regex]::Matches($text, "\[comp-req-616\] frame=").Count -ge 12) {
                break
            }
        }
        Start-Sleep -Milliseconds 100
    }
    $text = $builder.ToString()
    $text | Set-Content -LiteralPath $serialLog -Encoding UTF8
    return $text
}

function Assert-IHexMatchesReadback {
    param(
        [string] $HexPath,
        [byte[]] $Readback,
        [uint32] $ReadbackBase
    )
    [uint32] $upper = 0
    [int64] $checked = 0
    foreach ($line in Get-Content -LiteralPath $HexPath) {
        if (-not $line.StartsWith(":") -or $line.Length -lt 11) {
            throw "Invalid Intel HEX line in $HexPath"
        }
        $count = [Convert]::ToByte($line.Substring(1, 2), 16)
        $offset = [Convert]::ToUInt16($line.Substring(3, 4), 16)
        $type = [Convert]::ToByte($line.Substring(7, 2), 16)
        if ($type -eq 4) {
            $upper = [uint32](
                [Convert]::ToUInt16($line.Substring(9, 4), 16)) -shl 16
            continue
        }
        if ($type -eq 1) {
            break
        }
        if ($type -ne 0) {
            continue
        }
        $address = $upper + [uint32]$offset
        for ($index = 0; $index -lt $count; $index++) {
            $absolute = $address + [uint32]$index
            if ($absolute -lt $ReadbackBase -or
                $absolute -ge $ReadbackBase + [uint32]$Readback.Length) {
                throw "HEX address is outside final readback: 0x$($absolute.ToString('X8'))"
            }
            $expected = [Convert]::ToByte(
                $line.Substring(9 + ($index * 2), 2), 16)
            $observed = $Readback[$absolute - $ReadbackBase]
            if ($expected -ne $observed) {
                throw "Final readback mismatch at 0x$($absolute.ToString('X8'))"
            }
            $checked++
        }
    }
    if ($checked -eq 0) {
        throw "No Intel HEX data bytes checked for $HexPath"
    }
    return $checked
}

try {
    if (-not (Test-Path -LiteralPath $programmer) -or
        -not (Test-Path -LiteralPath $loader) -or
        -not (Test-Path -LiteralPath $image)) {
        throw "Required programmer or comparison image is missing"
    }
    $mutex = [System.Threading.Mutex]::new(
        $false, "Local\Companion-WB55-SWD-COM-Exclusive-v1")
    try {
        $owned = $mutex.WaitOne(0)
    } catch [System.Threading.AbandonedMutexException] {
        $owned = $true
    }
    if (-not $owned) {
        throw "Companion WB55 SWD/COM lock is already held; zero hardware contact."
    }
    Add-Event "swd-com-lock" "PASS"

    $serial = [System.IO.Ports.SerialPort]::new(
        $PortName, $BaudRate, [System.IO.Ports.Parity]::None, 8,
        [System.IO.Ports.StopBits]::One)
    $serial.ReadTimeout = 100
    $serial.Open()
    $hardwareContact = $true
    $serial.DiscardInBuffer()
    Add-Event "serial-open" "PASS" @{ port = $PortName; baud = $BaudRate }

    Invoke-Programmer "preflash-backup-a" @(
        "-c", "port=SWD", "sn=$ProgrammerSerial", "mode=UR", "reset=HWrst",
        "freq=4000", "-u", "0x08000000", "0x80000", $backupA
    )
    Invoke-Programmer "preflash-backup-b" @(
        "-c", "port=SWD", "sn=$ProgrammerSerial", "mode=UR", "reset=HWrst",
        "freq=4000", "-u", "0x08000000", "0x80000", $backupB
    )
    $preflight = Get-Content -LiteralPath (
        Join-Path $runRoot "preflash-backup-a-programmer.log") -Raw
    $voltageMatch = [regex]::Match(
        $preflight, "Voltage\s*:\s*([0-9]+(?:\.[0-9]+)?)V")
    if ($preflight -notmatch [regex]::Escape($ProgrammerSerial) -or
        $preflight -notmatch "Board\s*:\s*NUCLEO-WB55RG" -or
        $preflight -notmatch "Device ID\s*:\s*0x495" -or
        -not $voltageMatch.Success) {
        throw "Read-only board identity preflight failed"
    }
    $voltage = [double]::Parse(
        $voltageMatch.Groups[1].Value,
        [System.Globalization.CultureInfo]::InvariantCulture)
    if ($voltage -lt 2.7 -or $voltage -gt 3.6) {
        throw "Board voltage is outside the admitted 2.7V..3.6V range"
    }
    $backupHashA = (Get-FileHash -LiteralPath $backupA -Algorithm SHA256).Hash
    $backupHashB = (Get-FileHash -LiteralPath $backupB -Algorithm SHA256).Hash
    if ((Get-Item -LiteralPath $backupA).Length -ne 0x80000 -or
        (Get-Item -LiteralPath $backupB).Length -ne 0x80000 -or
        $backupHashA -ne $backupHashB) {
        throw "Dual preflash backup admission failed"
    }
    Add-Event "read-only-board-identity" "PASS" @{
        board = "NUCLEO-WB55RG"
        device_id = "0x495"
        voltage = $voltage
    }
    Add-Event "preflash-backup-admitted" "PASS" @{
        bytes = 0x80000
        sha256 = $backupHashA
    }

    $writeStarted = $true
    if ($FullInternalOtaChain) {
        Invoke-Programmer "formal-ota-loader-write" @(
            "-c", "port=SWD", "sn=$ProgrammerSerial", "mode=UR", "reset=HWrst",
            "freq=4000", "-w", $loader, "-v"
        )
    }
    Invoke-Programmer "accepted-path-app-write" @(
        "-c", "port=SWD", "sn=$ProgrammerSerial", "mode=UR", "reset=HWrst",
        "freq=4000", "-w", $image, "-v"
    )
    $serial.DiscardInBuffer()
    Invoke-Programmer "accepted-path-loader-handoff" @(
        "-c", "port=SWD", "sn=$ProgrammerSerial", "mode=UR", "reset=HWrst",
        "freq=4000", "-rst"
    )
    $trace = Capture-Serial -Seconds 45
    # Historical runner prints the boolean success value inverted:
    # result=0 means the panel adapter returned true.
    $frames = [regex]::Matches($trace, "\[comp-req-616\] frame=.*result=0")
    $busy = [regex]::Matches($trace, "busy_ms=(\d+)")
    $busyValues = @($busy | ForEach-Object { [int]$_.Groups[1].Value })
    if ($trace -notmatch "\[comp-req-616\] init=1" -or
        $frames.Count -lt 12 -or
        @($busyValues | Where-Object { $_ -gt 0 -and $_ -le 600 }).Count -lt 12 -or
        $trace -match "\[comp-req-616\] frame=.*result=1|fault") {
        throw "Accepted-path runtime evidence did not meet the 12-frame BUSY gate"
    }
    Add-Event "accepted-path-runtime" "PASS" @{
        frames = $frames.Count
        busy_min_ms = ($busyValues | Measure-Object -Minimum).Minimum
        busy_max_ms = ($busyValues | Measure-Object -Maximum).Maximum
    }

    Invoke-Programmer "compare-full-readback" @(
        "-c", "port=SWD", "sn=$ProgrammerSerial", "mode=UR", "reset=HWrst",
        "freq=4000", "-u", "0x08000000", "0x80000", $finalReadback
    )
    $before = [System.IO.File]::ReadAllBytes($backupA)
    $after = [System.IO.File]::ReadAllBytes($finalReadback)
    if ($after.Length -ne 0x80000) {
        throw "Final internal flash readback length mismatch"
    }
    if ($FullInternalOtaChain) {
        $loaderChecked = Assert-IHexMatchesReadback `
            -HexPath $loader -Readback $after -ReadbackBase 0x08000000
        $appChecked = Assert-IHexMatchesReadback `
            -HexPath $image -Readback $after -ReadbackBase 0x08000000
        Add-Event "formal-loader-app-readback-exact" "PASS" @{
            loader_programmed_bytes = $loaderChecked
            app_programmed_bytes = $appChecked
        }
    } else {
        for ($index = 0; $index -lt 0x7000; $index++) {
            if ($before[$index] -ne $after[$index]) {
                throw "Protected OTA loader prefix changed at offset 0x$($index.ToString('X'))"
            }
        }
        Add-Event "ota-loader-prefix-preserved" "PASS" @{ bytes = 0x7000 }
    }

    $serial.DiscardInBuffer()
    Invoke-Programmer "compare-final-reset" @(
        "-c", "port=SWD", "sn=$ProgrammerSerial", "mode=UR", "reset=HWrst",
        "freq=4000", "-rst"
    )
    $trace = Capture-Serial -Seconds 45
    $frames = [regex]::Matches(
        $trace, "\[comp-req-616\] frame=.*result=0")
    $busy = [regex]::Matches($trace, "busy_ms=(\d+)")
    $busyValues = @($busy | ForEach-Object { [int]$_.Groups[1].Value })
    if ($trace -notmatch "\[comp-req-616\] init=1" -or
        $frames.Count -lt 12 -or
        @($busyValues | Where-Object { $_ -gt 0 -and $_ -le 600 }).Count -lt 12 -or
        $trace -match "\[comp-req-616\] frame=.*result=1|fault") {
        throw "Final ordinary reset did not preserve the accepted-path runtime"
    }
    Add-Event "post-readback-ordinary-reset-runtime" "PASS" @{
        frames = $frames.Count
        busy_min_ms = ($busyValues | Measure-Object -Minimum).Minimum
        busy_max_ms = ($busyValues | Measure-Object -Maximum).Maximum
    }

    $machineReady = $true
    [ordered]@{
        schema = "companion.comp_req_771.accepted_path_compare_machine.v1"
        requirement = "COMP-REQ-771"
        status = "MACHINE_READY"
        comparison = "comp_req_616_immediate_eyebrow_refined_successor"
        browser_source_claim = "diagnostic_only_not_current_browser_cemp"
        image_sha256 = (Get-FileHash -LiteralPath $image -Algorithm SHA256).Hash
        image_range = "0x08007000..0x0803EBAB"
        ota_magic = "0x94448A29"
        full_internal_ota_chain = [bool]$FullInternalOtaChain
        loader_sha256 = (Get-FileHash -LiteralPath $loader -Algorithm SHA256).Hash
        external_flash_write = $false
        protected_loader_bytes = 0x7000
        protected_loader_preserved = -not [bool]$FullInternalOtaChain
        formal_loader_readback_exact = [bool]$FullInternalOtaChain
        observed_frames = $frames.Count
        busy_min_ms = ($busyValues | Measure-Object -Minimum).Minimum
        busy_max_ms = ($busyValues | Measure-Object -Maximum).Maximum
        serial_log = $serialLog
        run_log = $runLog
    } | ConvertTo-Json -Depth 6 |
        Set-Content -LiteralPath $machineArtifact -Encoding UTF8
    Save-Run "MACHINE_READY"
    Write-Output "MACHINE_READY"
} catch {
    Add-Event "exception" "FAIL" @{ message = $_.Exception.Message }
    if ($writeStarted -and (Test-Path -LiteralPath $backupA)) {
        $restoreAttempted = $true
        try {
            Invoke-Programmer "restore-preflash-full" @(
                "-c", "port=SWD", "sn=$ProgrammerSerial", "mode=UR", "reset=HWrst",
                "freq=4000", "-w", $backupA, "0x08000000",
                "-v", $backupA, "0x08000000", "-rst"
            )
            $restored = $true
            Add-Event "restore-preflash-full" "PASS"
        } catch {
            Add-Event "restore-preflash-full" "FAIL" @{
                message = $_.Exception.Message
            }
        }
    }
    Save-Run "NO_GO"
    throw
} finally {
    if ($serial -ne $null) {
        if ($serial.IsOpen) {
            $serial.Close()
        }
        $serial.Dispose()
    }
    if ($owned -and $mutex -ne $null) {
        $mutex.ReleaseMutex()
    }
    if ($mutex -ne $null) {
        $mutex.Dispose()
    }
}
