param(
    [string] $PortName = "COM13",
    [int] $BaudRate = 115200,
    [string] $ProgrammerSerial = "066EFF535570514867221931",
    [switch] $SkipOperatorPrompt
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repo = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$runRoot = Join-Path $repo ".cache\validation\comp-req-771-same-source-flash\hardware-run"
$privateRoot = Join-Path $runRoot "private"
$programmer = "C:\ST\STM32CubeIDE_2.1.1\STM32CubeIDE\plugins\com.st.stm32cube.ide.mcu.externaltools.cubeprogrammer.win32_2.2.400.202601091506\tools\bin\STM32_Programmer_CLI.exe"
$loader = Join-Path $repo "cubeide\Companion_BLE_Ota_Loader\build\Companion_BLE_Ota_Loader.hex"
$provisionChunks = @()
$oldProvision = Join-Path $repo "cubeide\Companion_Nucleo_WB55RG_Bringup\build_comp_req_771_provision_auto\Companion_Nucleo_WB55RG_Bringup.hex"
$app = Join-Path $repo "cubeide\Companion_Nucleo_WB55RG_Bringup\build_comp_req_771_current_ota_product\Companion_Nucleo_WB55RG_Bringup.hex"
$precheckPath = Join-Path $repo ".cache\validation\comp-req-771-same-source-flash\PRECHECK_READY.json"
$cempManifestPath = Join-Path $repo ".cache\validation\comp-req-771-browser-life-source-pack-auto\cemp\manifest.json"
$backupA = Join-Path $privateRoot "preflash-full-a.bin"
$backupB = Join-Path $privateRoot "preflash-full-b.bin"
$finalReadback = Join-Path $privateRoot "final-full-readback.bin"
$serialLog = Join-Path $runRoot "hardware-serial.log"
$runLog = Join-Path $runRoot "hardware-run.json"
$programmerCallsLog = Join-Path $runRoot "programmer-calls.json"
$machineArtifact = Join-Path $runRoot "MACHINE_READY.json"
$operatorResult = Join-Path $runRoot "operator-result.json"
$operatorNote = Join-Path $runRoot "operator-note.txt"
$aiwRepo = if ($env:AI_WORKFLOW_REPO) {
    $env:AI_WORKFLOW_REPO
} else {
    "C:\Users\Billy\Desktop\Denzic\ai-collaboration-workflow"
}
$aiw = Join-Path $aiwRepo "scripts\aiw.ps1"
$pwshVerifier = Join-Path $aiwRepo "scripts\verify_pwsh7.ps1"
$events = [System.Collections.Generic.List[object]]::new()
$programmerCalls = [System.Collections.Generic.List[object]]::new()
$serialText = [System.Text.StringBuilder]::new()
$serialPort = $null
$swdMutex = $null
$swdOwned = $false
$writeStarted = $false
$machineReady = $false
$restoreAttempted = $false
$restored = $false
$assetWriteStarted = $false
$assetProvisioned = $false
$assetRestored = $false
$hardwareContact = $false

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
    $programmerCalls | ConvertTo-Json -Depth 5 |
        Set-Content -LiteralPath $programmerCallsLog -Encoding UTF8
    [ordered]@{
        schema = "companion.comp_req_771.same_source_flash_run.v1"
        requirement = "COMP-REQ-771"
        status = $Status
        hardware_contact = [int]$hardwareContact
        flash = $writeStarted
        mass_erase = $false
        read_unprotect = $false
        option_bytes = $false
        programmer_serial = $ProgrammerSerial
        serial_port = $PortName
        swd_com_lock_acquired = $swdOwned
        restore_attempted = $restoreAttempted
        restored = $restored
        external_asset_write_started = $assetWriteStarted
        external_asset_provisioned = $assetProvisioned
        external_asset_restored = $assetRestored
        programmer_calls = $programmerCalls
        events = $events
    } | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $runLog -Encoding UTF8
}

function Invoke-Programmer {
    param([string] $Name, [string[]] $Arguments)
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
        Add-Event $Name "FAIL" @{ exit_code = $exitCode }
        throw "STM32CubeProgrammer failed during $Name"
    }
    Add-Event $Name "PASS" @{ arguments = ($Arguments -join " ") }
}

function Save-SerialSnapshot {
    param([string] $Content)
    $lastError = $null
    for ($attempt = 1; $attempt -le 10; $attempt++) {
        try {
            $stream = [System.IO.File]::Open(
                $serialLog,
                [System.IO.FileMode]::Create,
                [System.IO.FileAccess]::Write,
                [System.IO.FileShare]::ReadWrite)
            try {
                $writer = [System.IO.StreamWriter]::new(
                    $stream, [System.Text.UTF8Encoding]::new($false))
                try {
                    $writer.Write($Content)
                    $writer.Flush()
                } finally {
                    $writer.Dispose()
                }
            } finally {
                $stream.Dispose()
            }
            return
        } catch {
            $lastError = $_.Exception
            Start-Sleep -Milliseconds 50
        }
    }
    throw "Unable to persist serial evidence after retries: $($lastError.Message)"
}

function Append-SerialMarker {
    param([string] $Marker)
    [void]$serialText.Append("`r`n--- $Marker ---`r`n")
    Save-SerialSnapshot $serialText.ToString()
}

function Read-SerialWindow {
    param(
        [int] $Seconds,
        [switch] $StopOnProductEvidence,
        [switch] $StopOnProvisionEvidence
    )
    $start = $serialText.Length
    $deadline = (Get-Date).AddSeconds($Seconds)
    while ((Get-Date) -lt $deadline) {
        $chunk = $serialPort.ReadExisting()
        if ($chunk.Length -gt 0) {
            [void]$serialText.Append($chunk)
            Save-SerialSnapshot $serialText.ToString()
            if ($StopOnProductEvidence -and
                (Test-ProductEvidence $serialText.ToString(
                    $start, $serialText.Length - $start))) {
                break
            }
            if ($StopOnProvisionEvidence -and
                (Test-ProvisionEvidence $serialText.ToString(
                    $start, $serialText.Length - $start))) {
                break
            }
        }
        Start-Sleep -Milliseconds 100
    }
    return $serialText.ToString($start, $serialText.Length - $start)
}

function Start-OtaApplication {
    param([string] $Name, [string] $Image, [string] $Marker)
    $script:writeStarted = $true
    Invoke-Programmer "$Name-write" @(
        "-c", "port=SWD", "sn=$ProgrammerSerial", "mode=UR", "reset=HWrst",
        "freq=4000", "-w", $Image, "-v"
    )
    $serialPort.DiscardInBuffer()
    Append-SerialMarker $Marker
    Invoke-Programmer "$Name-loader-handoff" @(
        "-c", "port=SWD", "sn=$ProgrammerSerial", "mode=UR", "reset=HWrst",
        "freq=4000", "-rst"
    )
}

function Test-ProductEvidence {
    param([string] $Text)
    $refreshMatches = [regex]::Matches(
        $Text,
        "accepted_product_driver .*changed=1 control=0x([0-9A-Fa-f]+) " +
        "bytes=(\d+) transaction_ms=(\d+) busy_ms=(\d+) .*" +
        "previous_plane_sync=(\d+) plane_sync_ms=(\d+) maintenance=(\d+) " +
        "decision=(\d+) reason=(\d+) partial_before=(\d+) " +
        "transport=(\S+) has_busy=(\d+) result=1")
    $refreshControls = @($refreshMatches | ForEach-Object {
        $_.Groups[1].Value.ToUpperInvariant()
    })
    $refreshBytes = @($refreshMatches | ForEach-Object {
        [int]$_.Groups[2].Value
    })
    $refreshTransactions = @($refreshMatches | ForEach-Object {
        [int]$_.Groups[3].Value
    })
    $refreshBusy = @($refreshMatches | ForEach-Object {
        [int]$_.Groups[4].Value
    })
    $refreshPreviousPlaneSync = @($refreshMatches | ForEach-Object {
        [int]$_.Groups[5].Value
    })
    $refreshPlaneSyncMs = @($refreshMatches | ForEach-Object {
        [int]$_.Groups[6].Value
    })
    $refreshMaintenance = @($refreshMatches | ForEach-Object {
        [int]$_.Groups[7].Value
    })
    $refreshTransports = @($refreshMatches | ForEach-Object {
        $_.Groups[11].Value
    })
    $refreshHasBusy = @($refreshMatches | ForEach-Object {
        [int]$_.Groups[12].Value
    })
    $motionMatches = [regex]::Matches(
        $Text, "\[screen-motion\] auto_complete .*interval_ms=(\d+).*phase=(\d+)")
    $motionIntervals = @($motionMatches | ForEach-Object {
        [int]$_.Groups[1].Value
    })
    $motionPhases = @($motionMatches | ForEach-Object {
        [int]$_.Groups[2].Value
    })
    $lifeMatches = [regex]::Matches(
        $Text,
        "\[screen-life\] family=(\w+) action=(\w+) episode=(\d+) phrase=(\d+) phase=(\w+) variation=(\d+) dwell_commits=(\d+) clip=(\S+) frame_index=(\d+)")
    $firstLifeMatches = @($lifeMatches | Select-Object -First 6)
    $lifeEvidenceValid = $firstLifeMatches.Count -eq 6
    $expectedMotionPhases = @()
    foreach ($match in $firstLifeMatches) {
        $family = $match.Groups[1].Value
        $action = $match.Groups[2].Value
        $episode = [int]$match.Groups[3].Value
        $phase = $match.Groups[5].Value
        $clip = $match.Groups[8].Value
        $frameIndex = [int]$match.Groups[9].Value
        $clipPattern = "^life_{0}_e{1}_s\d+_{2}_{3}$" -f
            [regex]::Escape($family),
            $episode,
            [regex]::Escape($action),
            [regex]::Escape($phase)
        if (
            $family -notin $script:lifeFamilies -or
            $episode -lt 0 -or $episode -ge 32 -or
            $clip -notmatch $clipPattern -or
            -not $script:lifeFrameIndexByClip.ContainsKey($clip) -or
            $script:lifeFrameIndexByClip[$clip] -ne $frameIndex -or
            -not $script:motionPhaseByName.ContainsKey($phase)
        ) {
            $lifeEvidenceValid = $false
        } else {
            $expectedMotionPhases += $script:motionPhaseByName[$phase]
        }
    }
    return (
        $Text -match "\[stage\] uart ok" -and
        $Text -match "\[screen-assets\].*store=ready.*identity=comp_req_638.*mount=ok" -and
        $Text -match $script:expectedPackPattern -and
        $refreshMatches.Count -ge 7 -and
        $refreshControls[0] -eq "FF" -and
        $refreshBytes[0] -eq 5000 -and
        @($refreshControls[1..5] | Where-Object { $_ -ne "CF" }).Count -eq 0 -and
        @($refreshBytes[1..5] | Where-Object { $_ -ne 2772 }).Count -eq 0 -and
        $refreshControls[6] -eq "FF" -and
        $refreshBytes[6] -eq 5000 -and
        @($refreshPreviousPlaneSync | Where-Object { $_ -ne 1 }).Count -eq 0 -and
        @($refreshPlaneSyncMs | Where-Object { $_ -lt 0 -or $_ -gt 700 }).Count -eq 0 -and
        $refreshMaintenance[6] -eq 1 -and
        @($refreshTransactions | Where-Object {
            $_ -le 0 -or $_ -gt 700
        }).Count -eq 0 -and
        @($refreshBusy | Where-Object {
            $_ -le 0 -or $_ -gt 600
        }).Count -eq 0 -and
        @($refreshTransports | Where-Object {
            $_ -ne "software_direct_bsrr_diagnostic"
        }).Count -eq 0 -and
        @($refreshHasBusy | Where-Object { $_ -ne 1 }).Count -eq 0 -and
        $motionIntervals.Count -ge 6 -and
        $lifeEvidenceValid -and
        (($motionPhases[0..5] -join ",") -eq
            ($expectedMotionPhases -join ",")) -and
        @($motionIntervals | Where-Object {
            $_ -notin @(480, 960, 1440, 1920)
        }).Count -eq 0 -and
        @($motionIntervals | Select-Object -Unique).Count -ge 2 -and
        $Text -notmatch "\[gatt\] recording_control" -and
        $Text -notmatch "(?i)hard.?fault" -and
        $Text -notmatch "(?i)\[epaper\].*(error|result=0)"
    )
}

function Test-ProvisionEvidence {
    param(
        [string] $Text,
        [int] $ExpectedBytes = 0,
        [int] $ExpectedOffset = -1
    )
    $beginOkay = if ($ExpectedBytes -gt 0) {
        if ($ExpectedOffset -ge 0) {
            $Text -match (
                "\[screen-assets-provision\] begin " +
                "chunk_offset=$ExpectedOffset " +
                "chunk_bytes=$ExpectedBytes")
        } else {
            $Text -match (
                "\[screen-assets-provision\] begin .*blob_bytes=" +
                [string]$ExpectedBytes)
        }
    } else {
        $Text -match "\[screen-assets-provision\] begin"
    }
    return (
        $beginOkay -and
        $Text -match "\[screen-assets-provision\] result=pass action=(already_current|erase_write_verify|already_current_chunk|erase_write_verify_chunk)" -and
        $Text -notmatch "(?i)hard.?fault"
    )
}

function Restore-PreflashImage {
    if (-not $writeStarted -or $machineReady -or $restoreAttempted) {
        return
    }
    $script:restoreAttempted = $true
    $assetRestoreFailure = $null
    if ($assetProvisioned) {
        # The browser-life pack is already whole-pack verified and is the
        # intended product resource. A hard-coded older pack would not restore
        # the actual preflight state and would undo the requested source.
        $script:assetRestored = $true
        Add-Event "retain-verified-browser-life-cemp" "PASS"
    } elseif ($assetWriteStarted) {
        try {
            Start-OtaApplication "restore-old-assets" $oldProvision "RESTORE OLD CEMP"
            $restoreAssetText = Read-SerialWindow -Seconds 120
            if (-not (Test-ProvisionEvidence $restoreAssetText)) {
                throw "Previous external CEMP restore did not report pass"
            }
            $script:assetRestored = $true
            Add-Event "restore-previous-external-cemp" "PASS"
        } catch {
            $assetRestoreFailure = $_.Exception.Message
            Add-Event "restore-previous-external-cemp" "FAIL" @{
                message = $assetRestoreFailure
            }
        }
    }
    Invoke-Programmer "restore-preflash" @(
        "-c", "port=SWD", "sn=$ProgrammerSerial", "mode=UR", "reset=HWrst",
        "freq=4000",
        "-w", $backupA, "0x08000000",
        "-v", $backupA, "0x08000000",
        "-rst"
    )
    $restoreReadback = Join-Path $privateRoot "restore-readback.bin"
    Invoke-Programmer "restore-readback" @(
        "-c", "port=SWD", "sn=$ProgrammerSerial", "mode=UR", "reset=HWrst",
        "freq=4000",
        "-u", "0x08000000", "0x80000", $restoreReadback
    )
    if ((Get-FileHash -LiteralPath $restoreReadback -Algorithm SHA256).Hash -ne
        (Get-FileHash -LiteralPath $backupA -Algorithm SHA256).Hash) {
        throw "Preflash image restore readback mismatch"
    }
    $script:restored = $true
    Add-Event "restore-preflash-identity" "PASS" @{
        sha256 = (Get-FileHash -LiteralPath $backupA -Algorithm SHA256).Hash
    }
    if ($null -ne $assetRestoreFailure) {
        throw "Internal preflash image restored; external CEMP restore failed: $assetRestoreFailure"
    }
}

try {
    $requiredPaths = @(
        $programmer, $loader, $oldProvision, $app, $precheckPath,
        $cempManifestPath, $aiw, $pwshVerifier
    )
    foreach ($path in $requiredPaths) {
        if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
            throw "Required file missing: $path"
        }
    }
    $precheck = Get-Content -LiteralPath $precheckPath -Raw | ConvertFrom-Json
    $allPrecheckReady = -not (
        $precheck.checks.PSObject.Properties.Value -contains $false)
    if ($precheck.status -ne "PRECHECK_READY" -or -not $allPrecheckReady) {
        throw "COMP-REQ-771 offline precheck is not ready"
    }
    $provisionChunks = @(
        $precheck.provision_chunks |
            Sort-Object -Property offset -Descending |
            ForEach-Object {
                $name = [string]$_.name
                $index = [int]($name -replace '^provision_chunk_', '')
                [ordered]@{
                    index = $index
                    offset = [int]$_.offset
                    bytes = [int]$_.bytes
                    image = Join-Path $repo (
                        [string]$precheck.images.$name.path)
                }
            }
    )
    if ($provisionChunks.Count -lt 1 -or
        $provisionChunks[-1].offset -ne 0 -or
        $provisionChunks[-1].index -ne 0) {
        throw "Invalid external CEMP provision order in precheck"
    }
    $requiredPaths += @($provisionChunks | ForEach-Object { $_.image })
    $script:expectedCempBytes = [int]$precheck.cemp.bytes
    $script:expectedCempSha = [string]$precheck.cemp.sha256
    $pagePath = Join-Path $repo (
        ".cache\validation\comp-req-628-status-bar\index.html")
    $cempPath = Join-Path $repo ([string]$precheck.cemp.path)
    $identityFiles = [ordered]@{
        page = [ordered]@{
            path = $pagePath
            sha256 = [string]$precheck.page_sha256
        }
        cemp = [ordered]@{
            path = $cempPath
            sha256 = [string]$precheck.cemp.sha256
        }
        loader = [ordered]@{
            path = $loader
            sha256 = [string]$precheck.images.loader.sha256
        }
        app = [ordered]@{
            path = $app
            sha256 = [string]$precheck.images.app.sha256
        }
    }
    foreach ($chunk in $provisionChunks) {
        $name = "provision_chunk_$($chunk.index)"
        $identityFiles[$name] = [ordered]@{
            path = $chunk.image
            sha256 = [string]$precheck.images.$name.sha256
        }
    }
    foreach ($identity in $identityFiles.GetEnumerator()) {
        if (-not (Test-Path -LiteralPath $identity.Value.path -PathType Leaf)) {
            throw "Required file missing: $($identity.Value.path)"
        }
        $observedSha = (
            Get-FileHash -LiteralPath $identity.Value.path -Algorithm SHA256
        ).Hash
        if ($observedSha -ne $identity.Value.sha256) {
            throw "Precheck identity drift: $($identity.Key)"
        }
    }
    $script:expectedPackPattern = (
        "pack=comp_req_638_browser_epaper_external_nor revision=638 clips={0} frames={1}" -f
        [int]$precheck.cemp.clip_count,
        [int]$precheck.cemp.frame_count)
    $script:lifeFamilies = @(
        "calm", "curious", "warm", "delighted", "thoughtful", "alert")
    $script:motionPhaseByName = @{
        hold = 0
        orient = 1
        anticipate = 2
        accent = 3
        follow = 4
        settle = 5
    }
    $script:lifeFrameIndexByClip = @{}
    $cempManifest = Get-Content -LiteralPath $cempManifestPath -Raw |
        ConvertFrom-Json
    $frameCursor = 0
    foreach ($clip in $cempManifest.clips) {
        if ($clip.name -like "life_*") {
            $script:lifeFrameIndexByClip[[string]$clip.name] = $frameCursor
        }
        $frameCursor += @($clip.frames).Count
    }
    & $pwshVerifier
    if (-not $?) {
        throw "PowerShell 7 verification failed before hardware contact"
    }
    Add-Event "pwsh7-verification" "PASS"

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
    Add-Event "swd-com-lock" "PASS"

    $serialPort = [System.IO.Ports.SerialPort]::new(
        $PortName, $BaudRate, [System.IO.Ports.Parity]::None, 8,
        [System.IO.Ports.StopBits]::One)
    $serialPort.ReadTimeout = 100
    $serialPort.Open()
    $hardwareContact = $true
    $serialPort.DiscardInBuffer()
    Add-Event "serial-open" "PASS" @{ port = $PortName; baud = $BaudRate }

    Invoke-Programmer "preflash-backup-a" @(
        "-c", "port=SWD", "sn=$ProgrammerSerial", "mode=UR", "reset=HWrst",
        "freq=4000",
        "-u", "0x08000000", "0x80000", $backupA
    )
    Invoke-Programmer "preflash-backup-b" @(
        "-c", "port=SWD", "sn=$ProgrammerSerial", "mode=UR", "reset=HWrst",
        "freq=4000",
        "-u", "0x08000000", "0x80000", $backupB
    )
    $preflightText = Get-Content -LiteralPath (
        Join-Path $runRoot "preflash-backup-a-programmer.log") -Raw
    $voltageMatch = [regex]::Match(
        $preflightText, "Voltage\s*:\s*([0-9]+(?:\.[0-9]+)?)V")
    if ($preflightText -notmatch [regex]::Escape($ProgrammerSerial) -or
        $preflightText -notmatch "Board\s*:\s*NUCLEO-WB55RG" -or
        $preflightText -notmatch "Device ID\s*:\s*0x495" -or
        -not $voltageMatch.Success) {
        throw "Read-only board identity preflight failed"
    }
    $voltage = [double]::Parse(
        $voltageMatch.Groups[1].Value,
        [System.Globalization.CultureInfo]::InvariantCulture)
    if ($voltage -lt 2.7 -or $voltage -gt 3.6) {
        throw "Board voltage is outside the admitted 2.7V..3.6V range"
    }
    Add-Event "read-only-board-identity" "PASS" @{
        board = "NUCLEO-WB55RG"
        device_id = "0x495"
        voltage = $voltage
    }
    if ((Get-Item -LiteralPath $backupA).Length -ne 0x80000 -or
        (Get-Item -LiteralPath $backupB).Length -ne 0x80000 -or
        (Get-FileHash -LiteralPath $backupA -Algorithm SHA256).Hash -ne
        (Get-FileHash -LiteralPath $backupB -Algorithm SHA256).Hash) {
        throw "Dual preflash backup admission failed"
    }
    Add-Event "preflash-backup-admitted" "PASS" @{
        bytes = 0x80000
        sha256 = (Get-FileHash -LiteralPath $backupA -Algorithm SHA256).Hash
    }

    $writeStarted = $true
    Invoke-Programmer "loader-write" @(
        "-c", "port=SWD", "sn=$ProgrammerSerial", "mode=UR", "reset=HWrst",
        "freq=4000", "-w", $loader, "-v"
    )
    $assetWriteStarted = $true
    foreach ($chunk in $provisionChunks) {
        $chunkName = "browser-life-assets-chunk-$($chunk.index)"
        Start-OtaApplication $chunkName $chunk.image (
            "PROVISION BROWSER LIFE CEMP CHUNK $($chunk.index)")
        $provisionText = Read-SerialWindow -Seconds 180 -StopOnProvisionEvidence
        if (-not (Test-ProvisionEvidence `
                $provisionText `
                -ExpectedBytes $chunk.bytes `
                -ExpectedOffset $chunk.offset)) {
            throw "Browser-life external CEMP chunk $($chunk.index) did not report pass"
        }
        Add-Event "$chunkName-provision" "PASS" @{
            offset = $chunk.offset
            bytes = $chunk.bytes
            header_commit = $chunk.index -eq 0
        }
    }
    Add-Event "browser-life-cemp-provision" "PASS" @{
        bytes = $script:expectedCempBytes
        sha256 = $script:expectedCempSha
        chunks = $provisionChunks.Count
        order = (@($provisionChunks | ForEach-Object { $_.index }) -join ",")
        external_ui_capacity_bytes = 0x200000
    }
    $assetProvisioned = $true
    Start-OtaApplication "product-first" $app "FINAL PRODUCT BOOT"
    $productText = Read-SerialWindow -Seconds 180 -StopOnProductEvidence

    if (-not (Test-ProductEvidence $productText)) {
        throw "Product boot did not prove the browser-parity CEMP life choreography"
    }
    Add-Event "same-source-product-runtime" "PASS"

    Invoke-Programmer "final-full-readback" @(
        "-c", "port=SWD", "sn=$ProgrammerSerial", "mode=UR", "reset=HWrst",
        "freq=4000",
        "-u", "0x08000000", "0x80000", $finalReadback
    )
    $serialPort.DiscardInBuffer()
    Append-SerialMarker "POST-READBACK PRODUCT BOOT"
    Invoke-Programmer "final-product-reset" @(
        "-c", "port=SWD", "sn=$ProgrammerSerial", "mode=UR", "reset=HWrst",
        "freq=4000", "-rst"
    )
    $postReadbackText = Read-SerialWindow -Seconds 180 -StopOnProductEvidence
    if (-not (Test-ProductEvidence $postReadbackText)) {
        throw "Final readback/reset boot did not preserve the browser-parity CEMP runtime"
    }
    Add-Event "post-readback-product-runtime" "PASS"
    $programmerCalls | ConvertTo-Json -Depth 5 |
        Set-Content -LiteralPath $programmerCallsLog -Encoding UTF8
    & python (Join-Path $repo "tools\verify_comp_req_771_hardware_result.py") `
        --run-root $runRoot
    if ($LASTEXITCODE -ne 0) {
        throw "COMP-REQ-771 hardware result verifier failed"
    }
    $machine = Get-Content -LiteralPath $machineArtifact -Raw | ConvertFrom-Json
    if ($machine.status -ne "MACHINE_READY") {
        throw "COMP-REQ-771 machine artifact is not ready"
    }
    $machineReady = $true
    Add-Event "machine-verification" "PASS" @{ artifact = $machineArtifact }
    Save-Run "MACHINE_READY_AWAITING_OPERATOR"

    if ($SkipOperatorPrompt) {
        Add-Event "operator-review" "SKIPPED" @{
            reason = "owner requested direct physical inspection without popup"
        }
        Save-Run "MACHINE_READY_OPERATOR_PROMPT_SKIPPED"
        return
    }

    $promptJson = & $aiw operator-prompt `
        -Title "Companion 真实墨水屏同源验收" `
        -ProgressText "COMP-REQ-771" `
        -ScopeText "正式 OTA Loader、0x08007000 应用和浏览器同源 CEMP 已通过机器校验并保持运行。" `
        -Message "请观察桌上的 200x200 墨水屏，可等待自然编舞与眨眼，也可触摸体验。请确认状态栏始终常驻，整脸、嘴型、饰件和浏览器固定页面一致。" `
        -ExpectedText "屏幕非空、方向正确、纯 1bpp；首帧已完整清理，状态栏不消失，周期维护后残影明显受控；线条至少达到此前最满意 616 实屏基线，无截断、断线、高光越界或明显异常刷新。" `
        -ReviewStyle `
        -Input `
        -Buttons "通过,需修改,中止" `
        -OutputPath $operatorNote `
        -Json
    if ($LASTEXITCODE -ne 0) {
        throw "Canonical operator prompt failed"
    }
    $promptJson | Set-Content -LiteralPath $operatorResult -Encoding UTF8
    $selection = ($promptJson | ConvertFrom-Json).selected
    Add-Event "operator-review" "RECORDED" @{
        selected = $selection
        result = $operatorResult
        note = $operatorNote
    }
    Save-Run "COMPLETE_$selection"
} catch {
    Add-Event "run" "FAIL" @{ message = $_.Exception.Message }
    try {
        Restore-PreflashImage
    } catch {
        Add-Event "restore" "FAIL" @{ message = $_.Exception.Message }
        Save-Run "RESTORE_FAILED"
        throw
    }
    $finalStatus = if ($restored) {
        "NO_GO_RESTORED"
    } else {
        "NO_GO_ZERO_WRITES"
    }
    Save-Run $finalStatus
    throw
} finally {
    if ($serialPort) {
        if ($serialPort.IsOpen) {
            $serialPort.Close()
        }
        $serialPort.Dispose()
    }
    if ($swdOwned -and $swdMutex) {
        $swdMutex.ReleaseMutex()
    }
    if ($swdMutex) {
        $swdMutex.Dispose()
    }
}
