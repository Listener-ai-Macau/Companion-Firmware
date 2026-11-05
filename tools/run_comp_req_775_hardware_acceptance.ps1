param(
    [switch] $Execute,
    [switch] $ResumeInstalledApp,
    [switch] $RecoverMissingLoader,
    [switch] $UpgradeChangedApp,
    [string] $PortName = "COM13",
    [string] $ProgrammerSerial = "066EFF535570514867221931",
    [int] $BootCaptureSeconds = 35,
    [int] $MenuCaptureSeconds = 120
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repo = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$artifacts = Join-Path $repo ".cache\validation\comp-req-775-incremental-sync"
$runRoot = Join-Path $artifacts "hardware-run"
$privateRoot = Join-Path $runRoot "private"
$machinePath = Join-Path $runRoot "HARDWARE_MACHINE_READY.json"
$installCheckpointPath = Join-Path $runRoot "INSTALL_CHECKPOINT.json"
$firmwareReadyPath = Join-Path $artifacts "FIRMWARE_BUILD_READY.json"
$offlineReadyPath = Join-Path $artifacts "OFFLINE_READY.json"
$recordingReadyPath = Join-Path (
    Split-Path -Parent $artifacts) (
        "comp-req-775-recording-resources\companion_recording_resources.json")
$hexPath = Join-Path $repo "cubeide\Companion_Nucleo_WB55RG_Bringup\build_comp_req_775_external_map\Companion_Nucleo_WB55RG_Bringup.hex"
$loaderHexPath = Join-Path $repo "cubeide\Companion_BLE_Ota_Loader\build\Companion_BLE_Ota_Loader.hex"
$acceptedLoaderReceiptPath = Join-Path $repo ".cache\validation\comp-req-771-accepted-path-comparison\hardware-run\MACHINE_READY.json"
$programmer = "C:\ST\STM32CubeProgrammer\bin\STM32_Programmer_CLI.exe"
$fixedUrl = "http://127.0.0.1:4185/.cache/validation/comp-req-628-status-bar/index.html"
$hardwareAssets = Join-Path $runRoot "sync"
$loaderBefore = Join-Path $privateRoot "loader-before.bin"
$loaderAfter = Join-Path $privateRoot "loader-after.bin"
$loaderRecovered = Join-Path $privateRoot "loader-recovered.bin"
$loaderRecoveryCheckpointPath = Join-Path $runRoot "LOADER_RECOVERY_CHECKPOINT.json"
$appBeforeSync = Join-Path $privateRoot "ota-app-before-sync.bin"
$appAfterSync = Join-Path $privateRoot "ota-app-after-sync.bin"
$appAfterLoaderRecovery = Join-Path $privateRoot "ota-app-after-loader-recovery.bin"
$appProtocolUpgrade = Join-Path $privateRoot "ota-app-protocol-upgrade.bin"
$appProtocolUpgradeCheckpointPath = Join-Path (
    $runRoot) "APP_PROTOCOL_UPGRADE_CHECKPOINT.json"
$loaderAfterAppProtocolUpgrade = Join-Path (
    $privateRoot) "loader-after-app-protocol-upgrade.bin"
$bootLog = Join-Path $runRoot "ordinary-reset-serial.log"
$menuLog = Join-Path $runRoot "menu-boundary-serial.log"
$preSyncBootLog = Join-Path $runRoot "pre-sync-boot-serial.log"
$programmerCalls = [System.Collections.Generic.List[object]]::new()
$priorProgrammerCalls = @()
$events = [System.Collections.Generic.List[object]]::new()
$hardwareContact = $false
$lockContext = $null
$swdMutex = $null
$swdOwned = $false
$serialPort = $null
$receipt = $null
$loaderRecoveryPerformed = $false
$loaderRecoveryCheckpoint = $null
$loaderBaselinePath = $loaderBefore
$appProtocolUpgradePerformed = $false
$appProtocolUpgradeCheckpoint = $null
$appBaselinePath = $appBeforeSync
$expectedLoaderHexSha256 = "7AF74009DCDCC82601DE1F04BEC94248FC5CE48C9B44F6298A44B0763FBD8324"
$missingLoaderPrefixSha256 = "FF8A46D29571DD2F14D75FB79730B710922D5009B047E30C9FA2265A2FC05B69"
$initialAppHexSha256 = "6BE4A8182C665C4DC51591BB2422B508DB5A2604DEC326208BEC3080667CAE86"
$initialAppRegionSha256 = "C225288591C29D73207C68E19986A83917B1696F21A1AF3D17167EEF7D19E7D1"
$initialAppProgrammedBytes = 319240

New-Item -ItemType Directory -Force -Path $runRoot, $privateRoot | Out-Null

function Add-Event {
    param(
        [Parameter(Mandatory = $true)][string] $Name,
        [Parameter(Mandatory = $true)][string] $Status,
        [hashtable] $Detail = @{}
    )
    $events.Add([ordered]@{
        at = (Get-Date).ToUniversalTime().ToString("o")
        name = $Name
        status = $Status
        detail = $Detail
    })
}

function Invoke-Programmer {
    param(
        [Parameter(Mandatory = $true)][string] $Name,
        [Parameter(Mandatory = $true)][string[]] $Arguments
    )
    $log = Join-Path $runRoot "$Name-programmer.log"
    $output = & $programmer @Arguments 2>&1
    $exitCode = $LASTEXITCODE
    $output | Set-Content -LiteralPath $log -Encoding UTF8
    $programmerCalls.Add([ordered]@{
        name = $Name
        exit_code = $exitCode
        arguments = ($Arguments -join " ")
        log = $log
    })
    if ($exitCode -ne 0) {
        throw "STM32CubeProgrammer failed at $Name; see $log"
    }
    Add-Event $Name "PASS"
}

function Invoke-PythonReceipt {
    param(
        [Parameter(Mandatory = $true)][string] $Name,
        [Parameter(Mandatory = $true)][string[]] $Arguments
    )
    $log = Join-Path $runRoot "$Name.log"
    $lines = @(& python @Arguments 2>&1)
    $exitCode = $LASTEXITCODE
    $lines | Set-Content -LiteralPath $log -Encoding UTF8
    if ($exitCode -ne 0 -or $lines.Count -eq 0) {
        throw "$Name failed; see $log"
    }
    $parsed = $lines[-1] | ConvertFrom-Json -AsHashtable
    Add-Event $Name "PASS" @{ status = [string]$parsed.status }
    return $parsed
}

function Get-IntelHexLayout {
    param([Parameter(Mandatory = $true)][string] $Path)

    $bytes = [System.Collections.Generic.Dictionary[uint32, byte]]::new()
    [uint32]$linearBase = 0
    $sawEof = $false
    foreach ($line in Get-Content -LiteralPath $Path) {
        if ($line.Length -lt 11 -or $line[0] -ne ":") {
            throw "Malformed Intel HEX record in $Path"
        }
        $record = [System.Collections.Generic.List[byte]]::new()
        for ($index = 1; $index -lt $line.Length; $index += 2) {
            if ($index + 1 -ge $line.Length) {
                throw "Odd-length Intel HEX record in $Path"
            }
            $record.Add([Convert]::ToByte($line.Substring($index, 2), 16))
        }
        $sum = 0
        foreach ($value in $record) {
            $sum = ($sum + [int]$value) -band 0xFF
        }
        if ($sum -ne 0) {
            throw "Intel HEX checksum mismatch in $Path"
        }
        $count = [int]$record[0]
        if ($record.Count -ne $count + 5) {
            throw "Intel HEX byte-count mismatch in $Path"
        }
        [uint32]$offset = ([uint32]$record[1] -shl 8) -bor $record[2]
        $type = [int]$record[3]
        switch ($type) {
            0 {
                for ($dataIndex = 0; $dataIndex -lt $count; $dataIndex++) {
                    [uint32]$address = $linearBase + $offset + $dataIndex
                    if ($bytes.ContainsKey($address) -and
                        $bytes[$address] -ne $record[4 + $dataIndex]) {
                        throw ("Conflicting Intel HEX byte at 0x{0:X8}" -f $address)
                    }
                    $bytes[$address] = $record[4 + $dataIndex]
                }
            }
            1 { $sawEof = $true }
            4 {
                if ($count -ne 2) {
                    throw "Malformed extended linear address in $Path"
                }
                $linearBase = (
                    (([uint32]$record[4] -shl 8) -bor $record[5]) -shl 16)
            }
            5 { }
            default {
                throw "Unsupported Intel HEX record type $type in $Path"
            }
        }
    }
    if (-not $sawEof -or $bytes.Count -eq 0) {
        throw "Intel HEX has no complete data image: $Path"
    }
    $addresses = @($bytes.Keys | Sort-Object)
    return [ordered]@{
        bytes = $bytes
        programmed_bytes = $bytes.Count
        min_address = [uint32]$addresses[0]
        max_address = [uint32]$addresses[-1]
    }
}

function Get-LayoutUInt32 {
    param(
        [Parameter(Mandatory = $true)] $Layout,
        [Parameter(Mandatory = $true)][uint32] $Address
    )
    $value = [uint32]0
    for ($index = 0; $index -lt 4; $index++) {
        [uint32]$byteAddress = $Address + $index
        if (-not $Layout.bytes.ContainsKey($byteAddress)) {
            throw ("Intel HEX vector byte missing at 0x{0:X8}" -f $byteAddress)
        }
        $value = $value -bor ([uint32]$Layout.bytes[$byteAddress] -shl (8 * $index))
    }
    return $value
}

function Assert-LayoutMatchesReadback {
    param(
        [Parameter(Mandatory = $true)] $Layout,
        [Parameter(Mandatory = $true)][string] $ReadbackPath,
        [Parameter(Mandatory = $true)][uint32] $BaseAddress
    )
    $readback = [System.IO.File]::ReadAllBytes($ReadbackPath)
    foreach ($entry in $Layout.bytes.GetEnumerator()) {
        [long]$offset = [long]$entry.Key - [long]$BaseAddress
        if ($offset -lt 0 -or $offset -ge $readback.Length -or
            $readback[$offset] -ne $entry.Value) {
            throw ("Loader readback mismatch at 0x{0:X8}" -f $entry.Key)
        }
    }
}

function Capture-OrdinaryReset {
    $capture = [System.Collections.Generic.List[string]]::new()
    $script:serialPort = [System.IO.Ports.SerialPort]::new(
        $PortName, 115200, [System.IO.Ports.Parity]::None, 8,
        [System.IO.Ports.StopBits]::One)
    $script:serialPort.ReadTimeout = 120
    $script:serialPort.Open()
    $script:serialPort.DiscardInBuffer()
    Invoke-Programmer "ordinary-product-reset" @(
        "-c", "port=SWD", "sn=$ProgrammerSerial", "mode=UR",
        "reset=HWrst", "freq=4000", "-rst"
    )
    $deadline = (Get-Date).AddSeconds($BootCaptureSeconds)
    while ((Get-Date) -lt $deadline) {
        try {
            $line = $script:serialPort.ReadLine().Trim()
            if ($line.Length -gt 0) {
                $capture.Add($line)
                $joined = $capture -join "`n"
                if ($joined -match "\[ui-sync\] transport=ready" -and
                    $joined -match "\[screen-assets\] ui_generation=active" -and
                    $joined -match "mount=ok" -and
                    $joined -match "accepted_product_driver.*result=1") {
                    break
                }
            }
        } catch [System.TimeoutException] {
        }
    }
    $script:serialPort.Close()
    $script:serialPort.Dispose()
    $script:serialPort = $null
    $capture | Set-Content -LiteralPath $bootLog -Encoding UTF8
    return $capture -join "`n"
}

function Restart-ProductForSync {
    $capture = [System.Collections.Generic.List[string]]::new()
    $transportReadySeen = $false
    $script:serialPort = [System.IO.Ports.SerialPort]::new(
        $PortName, 115200, [System.IO.Ports.Parity]::None, 8,
        [System.IO.Ports.StopBits]::One)
    $script:serialPort.ReadTimeout = 120
    $script:serialPort.Open()
    $script:serialPort.DiscardInBuffer()
    try {
        Invoke-Programmer "ota-loader-app-handoff-before-resource-sync" @(
            "-c", "port=SWD", "sn=$ProgrammerSerial", "mode=UR",
            "reset=HWrst", "freq=4000",
            "-w8", "0x20000000", "0x00", "0x07", "0x00", "0xC3",
            "-r8", "0x20000000", "4", "-rst"
        )
        $deadline = (Get-Date).AddSeconds(30)
        while ((Get-Date) -lt $deadline) {
            try {
                $line = $script:serialPort.ReadLine().Trim()
                if ($line.Length -gt 0) {
                    $capture.Add($line)
                    if ($line -match "\[ui-sync\] transport=ready") {
                        $transportReadySeen = $true
                        break
                    }
                }
            } catch [System.TimeoutException] {
            }
        }
    } finally {
        $script:serialPort.Close()
        $script:serialPort.Dispose()
        $script:serialPort = $null
    }
    $text = $capture -join "`n"
    [System.IO.File]::WriteAllText(
        $preSyncBootLog,
        $(if ($text.Length -gt 0) { $text + "`n" } else { "" }),
        [System.Text.UTF8Encoding]::new($false)
    )
    if (-not $transportReadySeen) {
        try {
            Invoke-Programmer "product-sync-start-failure-diagnostic" @(
                "-c", "port=SWD", "sn=$ProgrammerSerial", "mode=HOTPLUG",
                "freq=4000",
                "-score",
                "-coreReg",
                "R0", "R1", "R2", "R3", "R4", "R5", "R6", "R7",
                "R8", "R9", "R10", "R11", "R12",
                "PC", "LR", "MSP", "PSP", "XPSR", "CONTROL",
                "-r32", "0x20000000", "4",
                "-r32", "0xE000ED08", "4",
                "-r32", "0xE000ED24", "28"
            )
        } catch {
            Add-Event "product-sync-start-failure-diagnostic" "UNAVAILABLE" @{
                message = $_.Exception.Message
            }
        }
        throw "Product did not expose UI sync after ordinary reset; see $preSyncBootLog"
    }
    Add-Event "product-sync-transport-ready" "PASS" @{
        log = $preSyncBootLog
    }
}

function Get-MenuBoundaryEvidence {
    param([Parameter(Mandatory = $true)][string] $Text)

    $driverPattern = (
        "accepted_product_driver.*changed=1.*control=0xFF.*bytes=5000.*" +
        "ready_checks=[1-9][0-9]*.*" +
        "maintenance=1.*transport=software_direct_bsrr_diagnostic.*" +
        "has_busy=1.*result=1")
    $dailyMarker = "[touch-ui] daily_to_menu gesture=any_long_press"
    $enterMarker = "[screen] menu_boundary=enter"
    $rightMarker = "[touch-ui] menu_right_swipe_exit"
    $exitMarker = "[screen] menu_boundary=exit"
    $dailyIndex = $Text.IndexOf($dailyMarker, [StringComparison]::Ordinal)
    $enterIndex = $Text.IndexOf($enterMarker, [StringComparison]::Ordinal)
    $rightIndex = $Text.IndexOf($rightMarker, [StringComparison]::Ordinal)
    $exitIndex = $Text.IndexOf($exitMarker, [StringComparison]::Ordinal)
    $driverMatches = [regex]::Matches($Text, $driverPattern)
    $enterDriver = @($driverMatches | Where-Object {
        $_.Index -gt $enterIndex -and
        ($rightIndex -lt 0 -or $_.Index -lt $rightIndex)
    } | Select-Object -First 1)
    $exitDriver = @($driverMatches | Where-Object {
        $_.Index -gt $exitIndex
    } | Select-Object -First 1)
    $runtimeFailurePattern = (
        "(?im)^\[(?:epaper|screen|screen-assets|ui-sync|rec-resource)\].*" +
        "(?:\bfault\b|terminal_fault=1|mount=(?:fail|unavailable)|" +
        "result=0|transport=unavailable|ui_generation=base_only|" +
        "selftest.*=fail)")
    $checks = [ordered]@{
        one_long_press_entry = (
            [regex]::Matches(
                $Text,
                [regex]::Escape($dailyMarker)).Count -eq 1)
        one_menu_enter_boundary = (
            [regex]::Matches(
                $Text,
                [regex]::Escape($enterMarker)).Count -eq 1)
        enter_maintenance_real_busy_ok = $enterDriver.Count -eq 1
        one_right_swipe_exit = (
            [regex]::Matches(
                $Text,
                [regex]::Escape($rightMarker)).Count -eq 1)
        one_menu_exit_boundary = (
            [regex]::Matches(
                $Text,
                [regex]::Escape($exitMarker)).Count -eq 1)
        exit_maintenance_real_busy_ok = $exitDriver.Count -eq 1
        ordered_entry_then_exit = (
            $dailyIndex -ge 0 -and
            $dailyIndex -lt $enterIndex -and
            $enterDriver.Count -eq 1 -and
            $enterIndex -lt $enterDriver[0].Index -and
            $enterDriver[0].Index -lt $rightIndex -and
            $rightIndex -lt $exitIndex -and
            $exitDriver.Count -eq 1 -and
            $exitIndex -lt $exitDriver[0].Index)
        no_runtime_fault = $Text -notmatch $runtimeFailurePattern
    }
    return [ordered]@{
        exact = $checks.Values -notcontains $false
        checks = $checks
        accepted_maintenance_refreshes = $driverMatches.Count
    }
}

function Capture-MenuBoundary {
    $capture = [System.Collections.Generic.List[string]]::new()
    $evidence = $null
    $script:serialPort = [System.IO.Ports.SerialPort]::new(
        $PortName, 115200, [System.IO.Ports.Parity]::None, 8,
        [System.IO.Ports.StopBits]::One)
    $script:serialPort.ReadTimeout = 120
    $script:serialPort.Open()
    $script:serialPort.DiscardInBuffer()
    Write-Host (
        "ACTION REQUIRED: hold anywhere for about 3 seconds to enter the " +
        "menu; after it finishes refreshing, swipe right to return.")
    try {
        $deadline = (Get-Date).AddSeconds($MenuCaptureSeconds)
        while ((Get-Date) -lt $deadline) {
            try {
                $line = $script:serialPort.ReadLine().Trim()
                if ($line.Length -gt 0) {
                    $capture.Add($line)
                    $evidence = Get-MenuBoundaryEvidence (
                        $capture -join "`n")
                    if ($evidence.exact) {
                        break
                    }
                }
            } catch [System.TimeoutException] {
            }
        }
    } finally {
        $script:serialPort.Close()
        $script:serialPort.Dispose()
        $script:serialPort = $null
    }
    $text = $capture -join "`n"
    $capture | Set-Content -LiteralPath $menuLog -Encoding UTF8
    if ($null -eq $evidence) {
        $evidence = Get-MenuBoundaryEvidence $text
    }
    return [ordered]@{
        text = $text
        evidence = $evidence
    }
}

try {
    if (-not (Test-Path -LiteralPath $programmer -PathType Leaf)) {
        throw "STM32CubeProgrammer CLI is missing: $programmer"
    }
    if ($RecoverMissingLoader -and -not $ResumeInstalledApp) {
        throw "Missing-Loader recovery requires -ResumeInstalledApp"
    }
    if ($UpgradeChangedApp -and -not $ResumeInstalledApp) {
        throw "Changed-App protocol upgrade requires -ResumeInstalledApp"
    }
    if ($RecoverMissingLoader -and $UpgradeChangedApp) {
        throw "Recover Loader and upgrade App in separate auditable runs"
    }
    if (-not (Test-Path -LiteralPath $loaderHexPath -PathType Leaf) -or
        -not (Test-Path -LiteralPath $acceptedLoaderReceiptPath -PathType Leaf)) {
        throw "Accepted OTA Loader artifact or receipt is missing"
    }
    $loaderHexSha256 = (
        Get-FileHash -LiteralPath $loaderHexPath -Algorithm SHA256).Hash
    $acceptedLoaderReceipt = Get-Content -Raw -LiteralPath (
        $acceptedLoaderReceiptPath) | ConvertFrom-Json -AsHashtable
    $loaderLayout = Get-IntelHexLayout $loaderHexPath
    $loaderStackPointer = Get-LayoutUInt32 $loaderLayout 0x08000000
    $loaderResetHandler = Get-LayoutUInt32 $loaderLayout 0x08000004
    if ($loaderHexSha256 -ne $expectedLoaderHexSha256 -or
        [string]$acceptedLoaderReceipt.status -ne "MACHINE_READY" -or
        [string]$acceptedLoaderReceipt.loader_sha256 -ne
            $expectedLoaderHexSha256 -or
        [uint32]$loaderLayout.min_address -ne [uint32]0x08000000 -or
        [uint32]$loaderLayout.max_address -ne [uint32]0x0800420D -or
        [int]$loaderLayout.programmed_bytes -ne 16910 -or
        $loaderStackPointer -ne [uint32]0x20030000 -or
        $loaderResetHandler -ne [uint32]0x08003D15 -or
        $loaderResetHandler -lt [uint32]0x08000001 -or
        $loaderResetHandler -ge [uint32]0x08007000) {
        throw "Accepted OTA Loader identity, range, or vector precheck failed"
    }
    Add-Event "accepted-loader-offline-precheck" "PASS" @{
        sha256 = $loaderHexSha256
        programmed_bytes = [int]$loaderLayout.programmed_bytes
        min_address = ("0x{0:X8}" -f $loaderLayout.min_address)
        max_address = ("0x{0:X8}" -f $loaderLayout.max_address)
        stack_pointer = ("0x{0:X8}" -f $loaderStackPointer)
        reset_handler = ("0x{0:X8}" -f $loaderResetHandler)
    }
    & python (Join-Path $repo "tools\verify_comp_req_773_menu_boundary_fast_full.py")
    if ($LASTEXITCODE -ne 0) {
        throw "COMP-REQ-773 menu-boundary protection failed"
    }
    & python (Join-Path $repo "tools\faraday_upper_art\verify_comp_req_775_incremental_sync.py")
    if ($LASTEXITCODE -ne 0) {
        throw "COMP-REQ-775 offline verification failed"
    }
    $offline = Get-Content -Raw -LiteralPath $offlineReadyPath |
        ConvertFrom-Json -AsHashtable
    $firmware = Get-Content -Raw -LiteralPath $firmwareReadyPath |
        ConvertFrom-Json -AsHashtable
    $recordingReady = Get-Content -Raw -LiteralPath $recordingReadyPath |
        ConvertFrom-Json -AsHashtable
    $appLayout = Get-IntelHexLayout $hexPath
    if ($offline.status -ne "PASS_OFFLINE_HARDWARE_PENDING" -or
        $firmware.status -ne "FIRMWARE_BUILD_READY" -or
        $recordingReady.status -ne "MACHINE_READY_OFFLINE" -or
        -not $firmware.checks.forced_full_build -or
        (Get-FileHash -LiteralPath $hexPath -Algorithm SHA256).Hash -ne
            $firmware.firmware.hex_sha256 -or
        [uint32]$appLayout.min_address -ne [uint32]0x08007000 -or
        [uint32]$appLayout.max_address -ge [uint32]0x08080000 -or
        [int]$appLayout.programmed_bytes -ne
            [int]$firmware.firmware.hex_programmed_bytes) {
        throw "Offline or firmware identity precheck is stale"
    }
    if ($UpgradeChangedApp -and
        [string]$firmware.firmware.hex_sha256 -eq $initialAppHexSha256) {
        throw "Changed-App upgrade refused: candidate equals initial App"
    }
    $response = Invoke-WebRequest -UseBasicParsing -Uri $fixedUrl -TimeoutSec 5
    if ([int]$response.StatusCode -ne 200) {
        throw "Fixed browser acceptance URL did not return HTTP 200"
    }
    Add-Event "offline-precheck" "PASS" @{
        fixed_url = $fixedUrl
        http_status = 200
        firmware_hex_sha256 = [string]$firmware.firmware.hex_sha256
    }
    $syntheticMenuLog = @"
[touch-ui] daily_to_menu gesture=any_long_press duration_ms=3001 selection=0 revision=1
[screen] menu_boundary=enter view=13 page=0 refresh=fast_if_baseline
[epaper] accepted_product_driver request=1 changed=1 control=0xFF bytes=5000 transaction_ms=1 busy_ms=1 ready_checks=1 previous_plane_sync=0 plane_sync_ms=0 maintenance=1 decision=1 reason=1 partial_before=0 transport=software_direct_bsrr_diagnostic has_busy=1 result=1
[touch-ui] menu_right_swipe_exit view=13 page=0 start=20,100 end=160,100
[screen] menu_boundary=exit expression=idle refresh=fast_if_baseline
[epaper] accepted_product_driver request=2 changed=1 control=0xFF bytes=5000 transaction_ms=1 busy_ms=1 ready_checks=1 previous_plane_sync=0 plane_sync_ms=0 maintenance=1 decision=1 reason=1 partial_before=0 transport=software_direct_bsrr_diagnostic has_busy=1 result=1
"@
    if (-not (Get-MenuBoundaryEvidence $syntheticMenuLog).exact) {
        throw "Menu-boundary evidence parser self-test failed"
    }
    $deltaPrecheck = Invoke-PythonReceipt "real-delta-offline-precheck" @(
        (Join-Path $repo "tools\faraday_upper_art\run_comp_req_775_real_delta.py"),
        "--artifacts", $hardwareAssets, "--precheck-only"
    )
    if ($deltaPrecheck.status -ne "PASS_REAL_DELTA_PRECHECK" -or
        [int]$deltaPrecheck.hardware_contact -ne 0) {
        throw "Fresh-export real-delta precheck failed"
    }

    if (-not $Execute) {
        $receipt = [ordered]@{
            schema = "companion.comp_req_775.hardware_acceptance.v1"
            status = "PRECHECK_READY_HARDWARE_NOT_TOUCHED"
            fixed_url = $fixedUrl
            offline_receipt_sha256 = (
                Get-FileHash -LiteralPath $offlineReadyPath -Algorithm SHA256
            ).Hash
            firmware = $firmware.firmware
            events = $events
            hardware_contact = 0
            internal_flash_write_bytes = 0
        }
        $receipt | ConvertTo-Json -Depth 12 |
            Set-Content -LiteralPath $machinePath -Encoding UTF8
        Write-Output "PRECHECK_COMP_REQ_775_HARDWARE hardware_contact=0 execute_required=1"
        return
    }

    $installCheckpoint = $null
    if ($ResumeInstalledApp) {
        if (-not (Test-Path -LiteralPath $installCheckpointPath -PathType Leaf)) {
            throw "Resume requested without INSTALL_CHECKPOINT.json"
        }
        $installCheckpoint = Get-Content -Raw -LiteralPath (
            $installCheckpointPath) | ConvertFrom-Json -AsHashtable
        if ($installCheckpoint.status -ne "FAILED" -or
            [string]$installCheckpoint.error -notmatch
                "canonical-initial-sync failed" -or
            @($installCheckpoint.programmer_calls | Where-Object {
                $_.name -eq "ota-app-write-once" -and
                $_.arguments -match "(?:^| )-w(?: |$)"
            }).Count -ne 1 -or
            -not (Test-Path -LiteralPath $loaderBefore -PathType Leaf) -or
            -not (Test-Path -LiteralPath $appBeforeSync -PathType Leaf) -or
            (Get-Content -Raw -LiteralPath (
                Join-Path $runRoot "ota-app-write-once-programmer.log")
            ) -notmatch "Download verified successfully") {
            throw "Installed-App resume checkpoint is incomplete or unsafe"
        }
        $priorProgrammerCalls = @($installCheckpoint.programmer_calls)
        if (-not $RecoverMissingLoader -and
            (Test-Path -LiteralPath $loaderRecoveryCheckpointPath -PathType Leaf)) {
            $loaderRecoveryCheckpoint = Get-Content -Raw -LiteralPath (
                $loaderRecoveryCheckpointPath) | ConvertFrom-Json -AsHashtable
            if ([string]$loaderRecoveryCheckpoint.status -ne
                    "LOADER_RECOVERY_READY" -or
                [string]$loaderRecoveryCheckpoint.loader.hex_sha256 -ne
                    $expectedLoaderHexSha256 -or
                -not (Test-Path -LiteralPath $loaderRecovered -PathType Leaf) -or
                -not (Test-Path -LiteralPath $appAfterLoaderRecovery -PathType Leaf)) {
                throw "Loader recovery checkpoint is incomplete or unsafe"
            }
            $priorProgrammerCalls = @(
                $loaderRecoveryCheckpoint.programmer_calls)
            $loaderBaselinePath = $loaderRecovered
            $appBaselinePath = $appAfterLoaderRecovery
        }
        if (Test-Path -LiteralPath (
                $appProtocolUpgradeCheckpointPath) -PathType Leaf) {
            if ($UpgradeChangedApp) {
                throw "Changed-App protocol upgrade was already checkpointed"
            }
            $appProtocolUpgradeCheckpoint = Get-Content -Raw -LiteralPath (
                $appProtocolUpgradeCheckpointPath) |
                ConvertFrom-Json -AsHashtable
            if ([string]$appProtocolUpgradeCheckpoint.status -ne
                    "APP_PROTOCOL_UPGRADE_READY" -or
                [string]$appProtocolUpgradeCheckpoint.app.hex_sha256 -ne
                    [string]$firmware.firmware.hex_sha256 -or
                -not (Test-Path -LiteralPath (
                    $appProtocolUpgrade) -PathType Leaf) -or
                -not (Test-Path -LiteralPath (
                    $loaderAfterAppProtocolUpgrade) -PathType Leaf)) {
                throw "App protocol upgrade checkpoint is incomplete or unsafe"
            }
            $priorProgrammerCalls = @(
                $appProtocolUpgradeCheckpoint.programmer_calls)
            $appBaselinePath = $appProtocolUpgrade
            $loaderBaselinePath = $loaderAfterAppProtocolUpgrade
        } elseif ($UpgradeChangedApp -and
            $null -eq $loaderRecoveryCheckpoint) {
            throw "Changed-App upgrade requires the recovered Loader checkpoint"
        }
    }

    . (Join-Path $repo "tools\companion_wb55_lock.ps1")
    $lockContext = Enter-CompanionWb55Lock -Purpose (
        "COMP-REQ-775 one-time OTA App install and external UI delta acceptance")
    $swdMutex = [System.Threading.Mutex]::new(
        $false, "Local\Companion-WB55-SWD-COM-Exclusive-v1")
    try {
        $swdOwned = $swdMutex.WaitOne(0)
    } catch [System.Threading.AbandonedMutexException] {
        $swdOwned = $true
    }
    if (-not $swdOwned) {
        throw "Companion WB55 SWD/COM lock is already held; zero hardware contact."
    }
    Add-Event "hardware-locks" "PASS" @{
        workflow = (Get-CompanionWb55LockEvidenceSummary $lockContext)
        swd_com = "Local\Companion-WB55-SWD-COM-Exclusive-v1"
    }

    $hardwareContact = $true
    if ($ResumeInstalledApp) {
        $loaderResume = Join-Path $privateRoot "loader-resume.bin"
        $appResume = Join-Path $privateRoot "ota-app-resume.bin"
        Invoke-Programmer "loader-read-resume" @(
            "-c", "port=SWD", "sn=$ProgrammerSerial", "mode=UR",
            "reset=HWrst", "freq=4000",
            "-u", "0x08000000", "0x7000", $loaderResume
        )
        Invoke-Programmer "ota-app-read-resume" @(
            "-c", "port=SWD", "sn=$ProgrammerSerial", "mode=UR",
            "reset=HWrst", "freq=4000",
            "-u", "0x08007000", "0x79000", $appResume
        )
        $expectedLoaderResumePath = $loaderBefore
        $expectedAppResumePath = $appBaselinePath
        if ($null -ne $loaderRecoveryCheckpoint) {
            $expectedLoaderResumePath = $loaderRecovered
        }
        if ($null -ne $appProtocolUpgradeCheckpoint) {
            $expectedLoaderResumePath = $loaderAfterAppProtocolUpgrade
        }
        if ((Get-FileHash -LiteralPath $loaderResume -Algorithm SHA256).Hash -ne
                (Get-FileHash -LiteralPath (
                    $expectedLoaderResumePath) -Algorithm SHA256).Hash -or
            (Get-FileHash -LiteralPath $appResume -Algorithm SHA256).Hash -ne
                (Get-FileHash -LiteralPath (
                    $expectedAppResumePath) -Algorithm SHA256).Hash) {
            throw "Installed App or Loader differs from verified checkpoint"
        }
        Add-Event "installed-app-checkpoint-resumed" "PASS" @{
            prior_ota_app_writes = $(
                if ($null -ne $appProtocolUpgradeCheckpoint) { 2 } else { 1 })
            current_ota_app_writes = 0
            recovered_loader_checkpoint = [int]($null -ne $loaderRecoveryCheckpoint)
            app_protocol_upgrade_checkpoint = [int](
                $null -ne $appProtocolUpgradeCheckpoint)
        }
        if ($RecoverMissingLoader) {
            $observedMissingLoaderSha = (
                Get-FileHash -LiteralPath $loaderResume -Algorithm SHA256).Hash
            if ($observedMissingLoaderSha -ne $missingLoaderPrefixSha256) {
                throw "Missing-Loader recovery refused: board prefix identity changed"
            }
            Invoke-Programmer "accepted-loader-recovery-write-once" @(
                "-c", "port=SWD", "sn=$ProgrammerSerial", "mode=UR",
                "reset=HWrst", "freq=4000", "-w", $loaderHexPath, "-v"
            )
            Invoke-Programmer "accepted-loader-recovery-readback" @(
                "-c", "port=SWD", "sn=$ProgrammerSerial", "mode=UR",
                "reset=HWrst", "freq=4000",
                "-u", "0x08000000", "0x7000", $loaderRecovered
            )
            Assert-LayoutMatchesReadback `
                -Layout $loaderLayout `
                -ReadbackPath $loaderRecovered `
                -BaseAddress 0x08000000
            Invoke-Programmer "ota-app-read-after-loader-recovery" @(
                "-c", "port=SWD", "sn=$ProgrammerSerial", "mode=UR",
                "reset=HWrst", "freq=4000",
                "-u", "0x08007000", "0x79000", $appAfterLoaderRecovery
            )
            $appBeforeRecoverySha = (
                Get-FileHash -LiteralPath $appResume -Algorithm SHA256).Hash
            $appAfterRecoverySha = (
                Get-FileHash -LiteralPath (
                    $appAfterLoaderRecovery) -Algorithm SHA256).Hash
            if ($appBeforeRecoverySha -ne $appAfterRecoverySha) {
                throw "OTA App changed during missing-Loader recovery"
            }
            $loaderRecoveryPerformed = $true
            $loaderBaselinePath = $loaderRecovered
            $loaderRecoveryCheckpoint = [ordered]@{
                schema = "companion.comp_req_775.loader_recovery.v1"
                status = "LOADER_RECOVERY_READY"
                reason = "accepted OTA Loader was absent from board prefix"
                loader = [ordered]@{
                    hex_sha256 = $loaderHexSha256
                    programmed_bytes = [int]$loaderLayout.programmed_bytes
                    min_address = ("0x{0:X8}" -f $loaderLayout.min_address)
                    max_address = ("0x{0:X8}" -f $loaderLayout.max_address)
                    prior_prefix_sha256 = $observedMissingLoaderSha
                    readback_region_sha256 = (
                        Get-FileHash -LiteralPath (
                            $loaderRecovered) -Algorithm SHA256).Hash
                }
                ota_app = [ordered]@{
                    preserved = $true
                    before_sha256 = $appBeforeRecoverySha
                    after_sha256 = $appAfterRecoverySha
                }
                programmer_calls = @(
                    $priorProgrammerCalls) + @($programmerCalls)
                protected_boundaries = [ordered]@{
                    loader_write = 1
                    ota_app_write_this_recovery = 0
                    fus_write = 0
                    otp_write = 0
                    option_byte_write = 0
                    external_flash_write = 0
                }
                hardware_contact = 1
            }
            $loaderRecoveryCheckpoint | ConvertTo-Json -Depth 16 |
                Set-Content -LiteralPath (
                    $loaderRecoveryCheckpointPath) -Encoding UTF8
            Add-Event "accepted-loader-recovered" "PASS" @{
                hex_sha256 = $loaderHexSha256
                app_preserved_sha256 = $appAfterRecoverySha
                checkpoint = $loaderRecoveryCheckpointPath
            }
        }
        if ($UpgradeChangedApp) {
            $observedInitialAppSha = (
                Get-FileHash -LiteralPath $appResume -Algorithm SHA256).Hash
            if ($observedInitialAppSha -ne $initialAppRegionSha256) {
                throw "Changed-App upgrade refused: installed App identity changed"
            }
            Invoke-Programmer "ota-app-protocol-upgrade-write-once" @(
                "-c", "port=SWD", "sn=$ProgrammerSerial", "mode=UR",
                "reset=HWrst", "freq=4000", "-w", $hexPath, "-v"
            )
            Invoke-Programmer "ota-app-protocol-upgrade-readback" @(
                "-c", "port=SWD", "sn=$ProgrammerSerial", "mode=UR",
                "reset=HWrst", "freq=4000",
                "-u", "0x08007000", "0x79000", $appProtocolUpgrade
            )
            Assert-LayoutMatchesReadback `
                -Layout $appLayout `
                -ReadbackPath $appProtocolUpgrade `
                -BaseAddress 0x08007000
            Invoke-Programmer "loader-read-after-app-protocol-upgrade" @(
                "-c", "port=SWD", "sn=$ProgrammerSerial", "mode=UR",
                "reset=HWrst", "freq=4000",
                "-u", "0x08000000", "0x7000",
                $loaderAfterAppProtocolUpgrade
            )
            $loaderBeforeUpgradeSha = (
                Get-FileHash -LiteralPath $loaderResume -Algorithm SHA256).Hash
            $loaderAfterUpgradeSha = (
                Get-FileHash -LiteralPath (
                    $loaderAfterAppProtocolUpgrade) -Algorithm SHA256).Hash
            if ($loaderBeforeUpgradeSha -ne $loaderAfterUpgradeSha) {
                throw "Loader changed during App protocol upgrade"
            }
            $appProtocolUpgradePerformed = $true
            $appBaselinePath = $appProtocolUpgrade
            $loaderBaselinePath = $loaderAfterAppProtocolUpgrade
            $appProtocolUpgradeCheckpoint = [ordered]@{
                schema = "companion.comp_req_775.app_protocol_upgrade.v1"
                status = "APP_PROTOCOL_UPGRADE_READY"
                reason = "USART1 FIFO and ORE-safe UI sync transport fix"
                app = [ordered]@{
                    prior_hex_sha256 = $initialAppHexSha256
                    prior_region_sha256 = $observedInitialAppSha
                    hex_sha256 = [string]$firmware.firmware.hex_sha256
                    programmed_bytes = [int]$appLayout.programmed_bytes
                    min_address = ("0x{0:X8}" -f $appLayout.min_address)
                    max_address = ("0x{0:X8}" -f $appLayout.max_address)
                    readback_region_sha256 = (
                        Get-FileHash -LiteralPath (
                            $appProtocolUpgrade) -Algorithm SHA256).Hash
                }
                loader = [ordered]@{
                    preserved = $true
                    before_sha256 = $loaderBeforeUpgradeSha
                    after_sha256 = $loaderAfterUpgradeSha
                }
                programmer_calls = @(
                    $priorProgrammerCalls) + @($programmerCalls)
                protected_boundaries = [ordered]@{
                    loader_write_this_upgrade = 0
                    ota_app_write_this_upgrade = 1
                    fus_write = 0
                    otp_write = 0
                    option_byte_write = 0
                    external_flash_write = 0
                }
                hardware_contact = 1
            }
            $appProtocolUpgradeCheckpoint | ConvertTo-Json -Depth 16 |
                Set-Content -LiteralPath (
                    $appProtocolUpgradeCheckpointPath) -Encoding UTF8
            Add-Event "ota-app-protocol-upgraded" "PASS" @{
                hex_sha256 = [string]$firmware.firmware.hex_sha256
                loader_preserved_sha256 = $loaderAfterUpgradeSha
                checkpoint = $appProtocolUpgradeCheckpointPath
            }
        }
    } else {
        Invoke-Programmer "loader-read-before" @(
            "-c", "port=SWD", "sn=$ProgrammerSerial", "mode=UR",
            "reset=HWrst", "freq=4000",
            "-u", "0x08000000", "0x7000", $loaderBefore
        )
        Invoke-Programmer "ota-app-write-once" @(
            "-c", "port=SWD", "sn=$ProgrammerSerial", "mode=UR",
            "reset=HWrst", "freq=4000", "-w", $hexPath, "-v"
        )
        Invoke-Programmer "ota-app-start" @(
            "-c", "port=SWD", "sn=$ProgrammerSerial", "mode=UR",
            "reset=HWrst", "freq=4000", "-rst"
        )
        Start-Sleep -Seconds 2
        Invoke-Programmer "ota-app-read-before-resource-sync" @(
            "-c", "port=SWD", "sn=$ProgrammerSerial", "mode=UR",
            "reset=HWrst", "freq=4000",
            "-u", "0x08007000", "0x79000", $appBeforeSync
        )
    }
    Restart-ProductForSync
    # The FIFO retains one paced 4-byte query while startup finishes; that RX
    # activity also wakes the low-power service path. Never repeat before ACK.
    Add-Event "product-sync-service-settle" "PASS" @{
        query_policy = "single_paced_after_transport_ready"
    }

    $initialSync = Invoke-PythonReceipt "canonical-initial-sync" @(
        (Join-Path $repo "tools\sync_companion_ui_assets.py"),
        "--port", $PortName, "--artifacts", $hardwareAssets
    )
    if ($initialSync.status -notin @(
            "PASS", "PASS_ALREADY_CURRENT",
            "PASS_RESOURCE_UPDATED_UI_ALREADY_CURRENT")) {
        throw "Initial canonical sync was not accepted"
    }
    $acceptedSidecar = Join-Path (
        Join-Path $hardwareAssets "accepted") (
            "$([string]$initialSync.resource_id).json")
    if (-not (Test-Path -LiteralPath $acceptedSidecar -PathType Leaf)) {
        $canonicalSidecar = Join-Path $artifacts "generation-1.json"
        New-Item -ItemType Directory -Force -Path (
            Split-Path -Parent $acceptedSidecar) | Out-Null
        Copy-Item -LiteralPath $canonicalSidecar -Destination $acceptedSidecar
    }
    $realDelta = Invoke-PythonReceipt "real-one-frame-delta" @(
        (Join-Path $repo "tools\faraday_upper_art\run_comp_req_775_real_delta.py"),
        "--port", $PortName, "--artifacts", $hardwareAssets
    )
    if ($realDelta.status -ne "PASS_REAL_DELTA_RESTORED") {
        throw "Real one-frame delta did not restore canonical resources"
    }
    $noOpSync = Invoke-PythonReceipt "canonical-noop-sync" @(
        (Join-Path $repo "tools\sync_companion_ui_assets.py"),
        "--port", $PortName, "--artifacts", $hardwareAssets
    )
    if ($noOpSync.status -ne "PASS_ALREADY_CURRENT" -or
        [int]$noOpSync.external_flash_write_bytes -ne 0 -or
        [int]$noOpSync.internal_flash_write_bytes -ne 0 -or
        [int]$noOpSync.elapsed_ms -gt 10000) {
        throw "Canonical no-op sync exceeded the zero-write 10 second gate"
    }
    $recordingReadback = $noOpSync.recording_resources.before
    $expectedRecordingCrc = [string]$recordingReady.pack.crc32
    $expectedRecordingBytes = [int]$recordingReady.pack.bytes
    $actualRecordingCrc = (
        [string]$recordingReadback.crc32 -replace "^0[xX]", ""
    ).ToUpperInvariant()
    if ([string]$recordingReadback.present -ne "1" -or
        [int]$recordingReadback.pack_bytes -ne $expectedRecordingBytes -or
        $actualRecordingCrc -ne $expectedRecordingCrc.ToUpperInvariant()) {
        throw "Recording resource pack readback identity mismatch"
    }

    Invoke-Programmer "loader-read-after" @(
        "-c", "port=SWD", "sn=$ProgrammerSerial", "mode=UR",
        "reset=HWrst", "freq=4000",
        "-u", "0x08000000", "0x7000", $loaderAfter
    )
    Invoke-Programmer "ota-app-read-after-resource-sync" @(
        "-c", "port=SWD", "sn=$ProgrammerSerial", "mode=UR",
        "reset=HWrst", "freq=4000",
        "-u", "0x08007000", "0x79000", $appAfterSync
    )
    $loaderBeforeSha = (
        Get-FileHash -LiteralPath $loaderBaselinePath -Algorithm SHA256).Hash
    $loaderAfterSha = (
        Get-FileHash -LiteralPath $loaderAfter -Algorithm SHA256).Hash
    if ($loaderBeforeSha -ne $loaderAfterSha) {
        throw "Loader bytes changed during COMP-REQ-775 acceptance"
    }
    $loaderWasRecovered = (
        $loaderRecoveryPerformed -or $null -ne $loaderRecoveryCheckpoint)
    $appWasProtocolUpgraded = (
        $appProtocolUpgradePerformed -or
        $null -ne $appProtocolUpgradeCheckpoint)
    $appBeforeSyncSha = (
        Get-FileHash -LiteralPath $appBaselinePath -Algorithm SHA256).Hash
    $appAfterSyncSha = (
        Get-FileHash -LiteralPath $appAfterSync -Algorithm SHA256).Hash
    if ($appBeforeSyncSha -ne $appAfterSyncSha) {
        throw "OTA App bytes changed during external UI resource sync"
    }
    Add-Event "loader-preserved" "PASS" @{
        bytes = 0x7000
        sha256 = $loaderAfterSha
    }

    $bootText = Capture-OrdinaryReset
    $sourceManifestPath = Join-Path (
        Join-Path $hardwareAssets "current-source-pack") (
            "source-pack-manifest.json")
    $sourceManifest = Get-Content -Raw -LiteralPath $sourceManifestPath |
        ConvertFrom-Json
    $firstLifePattern = (
        "\[screen-life\] family=(?<family>\w+) action=(?<action>\w+) " +
        "episode=(?<episode>\d+) phrase=(?<phrase>\d+) " +
        "phase=(?<phase>\w+) variation=(?<variation>\d+) " +
        "dwell_commits=(?<dwell>\d+) clip=(?<clip>\S+) " +
        "frame_index=(?<frame>\d+)")
    $firstLife = [regex]::Match($bootText, $firstLifePattern)
    $firstFrameEvidence = [ordered]@{
        exact = $false
        state_id = $null
        browser_frame_sha256 = $null
        unique_frame_index = $null
        observed_clip = $null
        observed_frame_index = $null
    }
    if ($firstLife.Success) {
        $observedFrame = [int]$firstLife.Groups["frame"].Value
        $observedClip = $firstLife.Groups["clip"].Value
        $candidates = @($sourceManifest.states | Where-Object {
            $_.kind -eq "life" -and
            $_.family -eq $firstLife.Groups["family"].Value -and
            $_.life_action -eq $firstLife.Groups["action"].Value -and
            [int]$_.action_episode -eq
                [int]$firstLife.Groups["episode"].Value -and
            [int]$_.phrase -eq [int]$firstLife.Groups["phrase"].Value -and
            $_.phase -eq $firstLife.Groups["phase"].Value -and
            [int]$_.variation -eq
                [int]$firstLife.Groups["variation"].Value -and
            [int]$_.dwell_commits -eq
                [int]$firstLife.Groups["dwell"].Value -and
            [int]$_.unique_frame_index -eq $observedFrame
        })
        if ($candidates.Count -eq 1) {
            $state = $candidates[0]
            $expectedClip = "frame_{0:D4}" -f [int]$state.unique_frame_index
            $firstFrameEvidence = [ordered]@{
                exact = (
                    $observedClip -eq $expectedClip -and
                    [string]$sourceManifest.source.page_sha256 -eq
                        [string]$offline.page_sha256)
                state_id = [string]$state.id
                browser_frame_sha256 = [string]$state.browser_frame_sha256
                unique_frame_index = [int]$state.unique_frame_index
                observed_clip = $observedClip
                observed_frame_index = $observedFrame
            }
        }
    }
    $acceptedDriverPattern = (
        "accepted_product_driver.*changed=1.*ready_checks=[1-9][0-9]*.*" +
        "transport=software_direct_bsrr_diagnostic.*has_busy=1.*result=1")
    $screenMountPattern = (
        "\[screen-assets\] policy=comp_req_638_external_cemp " +
        "store=ready prefix=read:43454D50 activation=allowed " +
        "identity=comp_req_638 mount=ok")
    $runtimeFailurePattern = (
        "(?im)^\[(?:epaper|screen|screen-assets|ui-sync|rec-resource)\].*" +
        "(?:\bfault\b|terminal_fault=1|mount=(?:fail|unavailable)|" +
        "result=0|transport=unavailable|ui_generation=base_only|" +
        "selftest.*=fail)")
    $bootChecks = [ordered]@{
        sync_transport_ready = $bootText -match "\[ui-sync\] transport=ready"
        ui_generation_active = $bootText -match "\[screen-assets\] ui_generation=active"
        base_cemp_mount_ok = $bootText -match $screenMountPattern
        real_driver_first_frame_ok = $bootText -match $acceptedDriverPattern
        real_busy_path_observed = $bootText -match $acceptedDriverPattern
        browser_runtime_first_frame_exact = $firstFrameEvidence.exact
        no_runtime_fault = $bootText -notmatch $runtimeFailurePattern
    }
    if ($bootChecks.Values -contains $false) {
        throw "Ordinary reset boot evidence failed; see $bootLog"
    }

    $menuCapture = Capture-MenuBoundary
    $menuEvidence = $menuCapture.evidence
    if (-not $menuEvidence.exact) {
        throw "Menu enter/exit hardware evidence failed; see $menuLog"
    }
    Add-Event "menu-boundary-real-panel" "PASS" @{
        log = $menuLog
        accepted_maintenance_refreshes = (
            [int]$menuEvidence.accepted_maintenance_refreshes)
    }

    $deltaReceipt = Get-Content -Raw -LiteralPath (
        Join-Path $hardwareAssets "real-delta-receipt.json") |
        ConvertFrom-Json -AsHashtable
    $receipt = [ordered]@{
        schema = "companion.comp_req_775.hardware_acceptance.v1"
        status = "MACHINE_READY_OPERATOR_PENDING"
        fixed_url = $fixedUrl
        fixed_url_http_status = 200
        firmware = $firmware.firmware
        loader = [ordered]@{
            preserved = $true
            bytes = 0x7000
            before_sha256 = $loaderBeforeSha
            after_sha256 = $loaderAfterSha
            recovery_required = [bool]$loaderWasRecovered
            recovery_hex_sha256 = $(
                if ($loaderWasRecovered) { $loaderHexSha256 } else { $null })
            recovery_programmed_bytes = $(
                if ($loaderWasRecovered) {
                    [int]$loaderLayout.programmed_bytes
                } else { 0 })
        }
        ota_app_resource_sync = [ordered]@{
            preserved = $true
            bytes = 0x79000
            before_sha256 = $appBeforeSyncSha
            after_sha256 = $appAfterSyncSha
            protocol_upgrade_required = [bool]$appWasProtocolUpgraded
            protocol_upgrade_hex_sha256 = $(
                if ($appWasProtocolUpgraded) {
                    [string]$firmware.firmware.hex_sha256
                } else { $null })
        }
        initial_sync = $initialSync
        real_delta = $deltaReceipt
        no_op_sync = $noOpSync
        recording_resources = [ordered]@{
            present = 1
            pack_bytes = $expectedRecordingBytes
            pack_crc32 = $expectedRecordingCrc
            pack_sha256 = [string]$recordingReady.pack.sha256
            external_base = "0x001DC000"
            external_limit = "0x001FD000"
            flash_test_scratch = "0x001FD000..0x001FE000"
            recording_region_base = "0x00200000"
            recording_region_limit = "0x01000000"
            readback = $recordingReadback
        }
        ordinary_reset = [ordered]@{
            log = $bootLog
            log_sha256 = (
                Get-FileHash -LiteralPath $bootLog -Algorithm SHA256).Hash
            checks = $bootChecks
            first_browser_frame = $firstFrameEvidence
        }
        menu_boundary = [ordered]@{
            log = $menuLog
            log_sha256 = (
                Get-FileHash -LiteralPath $menuLog -Algorithm SHA256).Hash
            evidence = $menuEvidence
        }
        programmer_calls = @($priorProgrammerCalls) + @($programmerCalls)
        events = $events
        protected_boundaries = [ordered]@{
            mass_erase = 0
            loader_write = [int]$loaderWasRecovered
            option_byte_write = 0
            otp_write = 0
            ota_app_write = $(if ($appWasProtocolUpgraded) { 2 } else { 1 })
            ota_app_protocol_upgrade_write = [int]$appWasProtocolUpgraded
            ui_resource_internal_flash_write_bytes = 0
            recording_region_bytes = 0xE00000
        }
        hardware_contact = 1
        internal_flash_write_bytes = (
            $initialAppProgrammedBytes +
            $(if ($appWasProtocolUpgraded) {
                [int]$firmware.firmware.hex_programmed_bytes
            } else { 0 }) +
            $(if ($loaderWasRecovered) {
                [int]$loaderLayout.programmed_bytes
            } else { 0 }))
        remaining_gate = "canonical Chinese operator review"
    }
    $receipt | ConvertTo-Json -Depth 20 |
        Set-Content -LiteralPath $machinePath -Encoding UTF8
    Write-Output (
        "MACHINE_READY_COMP_REQ_775 no_op_ms={0} one_frame_ms={1} loader_preserved=1 loader_recovery={2} app_protocol_upgrade={3}" -f
        [int]$noOpSync.elapsed_ms,
        [int]$deltaReceipt.one_frame.elapsed_ms,
        [int]$loaderWasRecovered,
        [int]$appWasProtocolUpgraded)
} catch {
    Add-Event "run" "FAIL" @{ message = $_.Exception.Message }
    $receipt = [ordered]@{
        schema = "companion.comp_req_775.hardware_acceptance.v1"
        status = "FAILED"
        error = $_.Exception.Message
        events = $events
        programmer_calls = @($priorProgrammerCalls) + @($programmerCalls)
        hardware_contact = [int]$hardwareContact
    }
    $receipt | ConvertTo-Json -Depth 20 |
        Set-Content -LiteralPath $machinePath -Encoding UTF8
    throw
} finally {
    if ($serialPort) {
        if ($serialPort.IsOpen) { $serialPort.Close() }
        $serialPort.Dispose()
    }
    if ($swdOwned -and $swdMutex) {
        $swdMutex.ReleaseMutex()
    }
    if ($swdMutex) { $swdMutex.Dispose() }
    if ($lockContext) { Exit-CompanionWb55Lock }
}
