param(
    [string] $PackagePath,
    [string] $ProgrammerPath,
    [string] $Port = "SWD",
    [string] $OutDir,
    [string] $DeviceName = "companion",
    [string] $BluetoothAddress,
    [int] $TimeoutSeconds = 20,
    [int] $LoaderBootDelayMs = 8000,
    [int] $PostOtaSettleSeconds = 8,
    [switch] $PrepareLoaderWithSwd,
    [switch] $PromptOperator,
    [switch] $Execute,
    [switch] $WorkflowLockHeld
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
if ([string]::IsNullOrWhiteSpace($OutDir)) {
    $OutDir = Join-Path $repoRoot ".cache\validation\companion-ble-ota-$stamp"
}
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
$outDirResolved = (Resolve-Path -LiteralPath $OutDir).Path

function Resolve-CompanionPackage {
    param([string] $Path)

    if (-not [string]::IsNullOrWhiteSpace($Path)) {
        return (Resolve-Path -LiteralPath $Path).Path
    }

    $packageRoot = Join-Path $repoRoot ".cache\ota_firmware"
    $latest = Get-ChildItem -LiteralPath $packageRoot -Filter "companion-ota-*.zip" -File -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1
    if (-not $latest) {
        throw "No Companion OTA package found under $packageRoot. Run tools\package_ota_firmware.ps1 first."
    }
    return $latest.FullName
}

function Find-CubeProgrammerCli {
    param([string] $RequestedPath)

    $candidates = @()
    if ($RequestedPath) { $candidates += $RequestedPath }
    if ($env:STM32CUBEPROGRAMMER_CLI) { $candidates += $env:STM32CUBEPROGRAMMER_CLI }
    if ($env:STM32CUBEPROGRAMMER_PATH) { $candidates += (Join-Path $env:STM32CUBEPROGRAMMER_PATH "STM32_Programmer_CLI.exe") }
    foreach ($commandName in @("STM32_Programmer_CLI.exe", "STM32_Programmer_CLI")) {
        $cmd = Get-Command $commandName -ErrorAction SilentlyContinue
        if ($cmd) { $candidates += $cmd.Source }
    }
    $candidates += @(
        "C:\ST\STM32CubeIDE_*\STM32CubeIDE\plugins\com.st.stm32cube.ide.mcu.externaltools.cubeprogrammer.win32_*\tools\bin\STM32_Programmer_CLI.exe",
        "C:\Program Files\STMicroelectronics\STM32CubeIDE_*\STM32CubeIDE\plugins\com.st.stm32cube.ide.mcu.externaltools.cubeprogrammer.win32_*\tools\bin\STM32_Programmer_CLI.exe",
        "C:\Program Files\STMicroelectronics\STM32Cube\STM32CubeIDE\STM32CubeIDE\plugins\com.st.stm32cube.ide.mcu.externaltools.cubeprogrammer.win32_*\tools\bin\STM32_Programmer_CLI.exe",
        "C:\Program Files\STMicroelectronics\STM32Cube\STM32CubeProgrammer\bin\STM32_Programmer_CLI.exe",
        "C:\ST\STM32CubeProgrammer\bin\STM32_Programmer_CLI.exe"
    )

    foreach ($candidate in $candidates) {
        if ([string]::IsNullOrWhiteSpace($candidate)) { continue }
        $matches = Get-ChildItem -Path $candidate -File -ErrorAction SilentlyContinue |
            Sort-Object FullName -Descending
        foreach ($match in @($matches)) {
            return $match.FullName
        }
        if (Test-Path -LiteralPath $candidate -PathType Leaf) {
            return (Resolve-Path -LiteralPath $candidate).Path
        }
    }
    return $null
}

function Get-AppSectorCount {
    param([Parameter(Mandatory = $true)][string] $FirmwarePath)

    $sectorSize = 0x1000
    $size = (Get-Item -LiteralPath $FirmwarePath).Length
    $sectors = [int][Math]::Ceiling([double]$size / [double]$sectorSize)
    if ($sectors -lt 1) {
        throw "Cannot prepare STM32WB OTA loader erase handoff for empty firmware."
    }
    if ($sectors -gt 255) {
        throw "Firmware requires $sectors flash sectors, but STM32WB OTA SRAM handoff stores the count in one byte."
    }
    return $sectors
}

function Invoke-PrepareBleOtaLoaderWithSwd {
    param(
        [Parameter(Mandatory = $true)][string] $Programmer,
        [Parameter(Mandatory = $true)][string] $PortName,
        [Parameter(Mandatory = $true)][int] $SectorCount,
        [Parameter(Mandatory = $true)][string] $LogPath
    )

    $handoffBase = "0x20000000"
    $sectorByte = "0x{0:X2}" -f $SectorCount
    $handoffBytes = @("0x01", "0x07", $sectorByte, "0xC3")
    $connectArgs = @("port=$PortName", "mode=UR", "reset=HWrst", "freq=4000")
    $args = @("-c") + $connectArgs + @("-w8", $handoffBase) + $handoffBytes + @("-r8", $handoffBase, "4", "-rst")

    Write-Host "Preparing STM32WB OTA loader erase handoff: $handoffBase = $($handoffBytes -join ' ')"
    $output = & $Programmer @args 2>&1
    $exitCode = if ($null -eq $LASTEXITCODE) { 0 } else { [int]$LASTEXITCODE }
    $output | Tee-Object -FilePath $LogPath
    if ($exitCode -ne 0) {
        throw "STM32CubeProgrammer OTA loader handoff failed with exit code $exitCode. See $LogPath"
    }
    if ($LoaderBootDelayMs -gt 0) {
        Start-Sleep -Milliseconds $LoaderBootDelayMs
    }
}

function Show-OperatorPrompt {
    param(
        [Parameter(Mandatory = $true)][string] $Title,
        [Parameter(Mandatory = $true)][string] $Message
    )

    try {
        [System.Media.SystemSounds]::Exclamation.Play()
        [Console]::Beep(880, 220)
    } catch {
        Write-Warning "Could not play operator prompt sound: $($_.Exception.Message)"
    }

    try {
        Add-Type -AssemblyName System.Windows.Forms
        [System.Windows.Forms.MessageBox]::Show(
            $Message,
            $Title,
            [System.Windows.Forms.MessageBoxButtons]::OK,
            [System.Windows.Forms.MessageBoxIcon]::Information
        ) | Out-Null
    } catch {
        Write-Host ""
        Write-Host "=== $Title ==="
        Write-Host $Message
        Write-Host ""
    }
}

function ConvertTo-CommandLine {
    param(
        [Parameter(Mandatory = $true)][string] $FilePath,
        [string[]] $Arguments = @()
    )

    $parts = @($FilePath) + $Arguments
    return ($parts | ForEach-Object {
        $text = [string] $_
        if ($text -match '[\s"`]' -or $text -eq "") {
            '"' + ($text -replace '"', '\"') + '"'
        } else {
            $text
        }
    }) -join " "
}

function Copy-ZipEntryToFile {
    param(
        [Parameter(Mandatory = $true)] $Archive,
        [Parameter(Mandatory = $true)][string] $EntryName,
        [Parameter(Mandatory = $true)][string] $Destination
    )

    $normalized = ($EntryName -replace "\\", "/").TrimStart("/")
    $entry = @($Archive.Entries | Where-Object {
            -not $_.FullName.EndsWith("/") -and
            (($_.FullName -replace "\\", "/").TrimStart("/")) -eq $normalized
        }) | Select-Object -First 1
    if (-not $entry) {
        throw "Package zip missing $EntryName."
    }

    $inputStream = $entry.Open()
    try {
        $outputStream = [System.IO.File]::Open($Destination, [System.IO.FileMode]::Create, [System.IO.FileAccess]::Write, [System.IO.FileShare]::None)
        try {
            $inputStream.CopyTo($outputStream)
        } finally {
            $outputStream.Dispose()
        }
    } finally {
        $inputStream.Dispose()
    }
}

function Expand-CompanionOtaPayload {
    param(
        [Parameter(Mandatory = $true)][string] $Path,
        [Parameter(Mandatory = $true)][string] $DestinationDir
    )

    $manifestPath = Join-Path $DestinationDir "ota_manifest.json"
    $firmwarePath = Join-Path $DestinationDir "firmware_ota.bin"
    if ((Test-Path -LiteralPath $Path -PathType Container)) {
        Copy-Item -LiteralPath (Join-Path $Path "ota_manifest.json") -Destination $manifestPath -Force
        Copy-Item -LiteralPath (Join-Path $Path "firmware_ota.bin") -Destination $firmwarePath -Force
    } else {
        Add-Type -AssemblyName System.IO.Compression.FileSystem
        $archive = [System.IO.Compression.ZipFile]::OpenRead($Path)
        try {
            Copy-ZipEntryToFile -Archive $archive -EntryName "ota_manifest.json" -Destination $manifestPath
            Copy-ZipEntryToFile -Archive $archive -EntryName "firmware_ota.bin" -Destination $firmwarePath
        } finally {
            $archive.Dispose()
        }
    }

    return [ordered]@{
        manifest_path = $manifestPath
        firmware_path = $firmwarePath
    }
}

function Invoke-CompanionOtaTool {
    param(
        [Parameter(Mandatory = $true)][string[]] $Arguments,
        [Parameter(Mandatory = $true)][string] $RawLogPath
    )

    Push-Location $repoRoot
    try {
        try {
            & python @Arguments 2>&1 | Tee-Object -FilePath $RawLogPath | Out-Host
        } catch {
            $message = "Invoke-CompanionOtaTool failed before normal output: $($_.Exception.Message)"
            $message | Set-Content -LiteralPath $RawLogPath -Encoding UTF8
            Write-Host $message
            return 1
        }
        if ($null -eq $LASTEXITCODE) {
            return 0
        }
        return [int]$LASTEXITCODE
    } finally {
        Pop-Location
    }
}

function ConvertTo-CompanionBleOtaMarkdown {
    param(
        [Parameter(Mandatory = $true)] $Summary
    )

    $lines = @(
        "# Companion BLE OTA Validation",
        "",
        "- Status: $($Summary["status"])",
        "- Mode: $($Summary["mode"])",
        "- Package: ``$($Summary["package_path"])``",
        "- Manifest: ``$($Summary["manifest_path"])``",
        "- Firmware: ``$($Summary["firmware_path"])``",
        "- Prepare loader with SWD: $($Summary["prepare_loader_with_swd"])",
        "- Raw log: ``$($Summary["raw_log"])``"
    )
    if ($Summary["prepare_log"]) {
        $lines += "- Prepare log: ``$($Summary["prepare_log"])``"
    }
    if ($Summary["transfer_report_json"]) {
        $lines += "- Transfer report JSON: ``$($Summary["transfer_report_json"])``"
    }
    foreach ($errorItem in @($Summary["errors"])) {
        $lines += "- Error: $errorItem"
    }
    return $lines
}

$resolvedPackage = Resolve-CompanionPackage -Path $PackagePath
$payload = Expand-CompanionOtaPayload -Path $resolvedPackage -DestinationDir $outDirResolved
$manifestText = Get-Content -LiteralPath $payload.manifest_path -Raw -Encoding UTF8
$manifest = $manifestText | ConvertFrom-Json
$rawLog = Join-Path $outDirResolved "companion-ble-ota-raw.log"
$prepareLog = Join-Path $outDirResolved "companion-ble-ota-prepare-loader.log"
$transferReportJson = Join-Path $outDirResolved "firmware_ota_result.json"
$summaryJson = Join-Path $outDirResolved "companion-ble-ota-summary.json"
$summaryMd = Join-Path $outDirResolved "companion-ble-ota-summary.md"
$programmer = if ($PrepareLoaderWithSwd) { Find-CubeProgrammerCli -RequestedPath $ProgrammerPath } else { $null }
$appSectorCount = if ($PrepareLoaderWithSwd) { Get-AppSectorCount -FirmwarePath $payload.firmware_path } else { $null }
$toolArgs = @(
    ".\tools\companion_ble_ota_v2.py",
    "--manifest", $payload.manifest_path,
    "--firmware", $payload.firmware_path,
    "--name", $DeviceName,
    "--timeout", [string]$TimeoutSeconds,
    "--output", $transferReportJson,
    "--json"
)
if (-not [string]::IsNullOrWhiteSpace($BluetoothAddress)) {
    $toolArgs += @("--address", $BluetoothAddress)
}
$commandLine = ConvertTo-CommandLine -FilePath "python" -Arguments $toolArgs
$lockCommand = "pwsh -NoProfile -File C:\Users\Billy\Desktop\Denzic\ai-collaboration-workflow\scripts\aiw.ps1 with-lock -Resource Companion-WB55,BLE-Companion -Purpose `"Companion BLE OTA validation`" -Run pwsh -NoProfile -File .\tools\verify_companion_ble_ota.ps1 -Execute -WorkflowLockHeld -PackagePath `"$resolvedPackage`""
if ($PrepareLoaderWithSwd) {
    $lockCommand += " -PrepareLoaderWithSwd"
}
if (-not [string]::IsNullOrWhiteSpace($ProgrammerPath)) {
    $lockCommand += " -ProgrammerPath `"$ProgrammerPath`""
}

if (-not $Execute) {
    $summary = [ordered]@{
        schema = "companion.ble_ota.validation.v1"
        status = "DRY_RUN"
        mode = "dry-run"
        generated_at = (Get-Date).ToString("o")
        package_path = $resolvedPackage
        manifest_path = $payload.manifest_path
        firmware_path = $payload.firmware_path
        manifest = [ordered]@{
            version = [string]$manifest.version
            protocolName = [string]$manifest.protocol.name
            protocol_name = [string]$manifest.protocol.name
        }
        manifest_version = [string]$manifest.version
        protocol = [string]$manifest.protocol.name
        command = $commandLine
        lock_command = $lockCommand
        prepare_loader_with_swd = [bool]$PrepareLoaderWithSwd
        prepare_log = if ($PrepareLoaderWithSwd) { $prepareLog } else { $null }
        programmer = $programmer
        port = $Port
        app_sector_count = $appSectorCount
        prompt_operator = [bool]$PromptOperator
        raw_log = $rawLog
        transfer_report_json = $null
        errors = @()
    }
    $summary | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $summaryJson -Encoding UTF8
    ConvertTo-CompanionBleOtaMarkdown -Summary $summary | Set-Content -LiteralPath $summaryMd -Encoding UTF8
    Write-Host "DRY-RUN: Companion BLE OTA validation is ready."
    Write-Host "Package: $resolvedPackage"
    Write-Host "Manifest: $($payload.manifest_path)"
    Write-Host "Firmware: $($payload.firmware_path)"
    Write-Host "Transport: Companion-owned companion_ota_v2 host tool"
    Write-Host "Run with workflow hardware lock:"
    Write-Host "  $lockCommand"
    if ($PrepareLoaderWithSwd) {
        Write-Host "Loader SWD handoff: 0x20000000 = 0x01 0x07 $('0x{0:X2}' -f $appSectorCount) 0xC3 via $programmer"
    }
    Write-Host "Blocking operator prompt: $([bool]$PromptOperator). Add -PromptOperator only for real-time human action or observation."
    Write-Host "Summary: $summaryJson"
    exit 0
}

if (-not $WorkflowLockHeld) {
    Write-Host "Use the workflow hardware lock before executing:"
    Write-Host "  $lockCommand"
    throw "Refusing to run Companion BLE OTA validation without -WorkflowLockHeld."
}

if ($PrepareLoaderWithSwd) {
    if (-not $programmer) {
        throw "STM32CubeProgrammer CLI not found. Pass -ProgrammerPath, set STM32CUBEPROGRAMMER_CLI, or omit -PrepareLoaderWithSwd."
    }
    Invoke-PrepareBleOtaLoaderWithSwd -Programmer $programmer -PortName $Port -SectorCount $appSectorCount -LogPath $prepareLog
}

if ($PromptOperator) {
    Show-OperatorPrompt `
        -Title "Companion BLE OTA 验证即将开始" `
        -Message "请确认 Companion 已开机，电脑蓝牙可用，且没有其它 BLE 工具正在连接 Companion。点击 OK 后会开始蓝牙升级；升级过程中不要断电。设备重启或短暂断开再恢复是正常现象。"
}

$errors = [System.Collections.Generic.List[string]]::new()
$startedAt = (Get-Date).ToUniversalTime().ToString("o")
$exitCode = Invoke-CompanionOtaTool -Arguments $toolArgs -RawLogPath $rawLog
$transferReport = $null
if (Test-Path -LiteralPath $transferReportJson -PathType Leaf) {
    $transferReport = Get-Content -LiteralPath $transferReportJson -Raw -Encoding UTF8 | ConvertFrom-Json
} else {
    $errors.Add("Companion OTA transfer report JSON was not written: $transferReportJson") | Out-Null
}

if ($exitCode -ne 0) {
    $errors.Add("companion_ble_ota_v2.py exited with code $exitCode.") | Out-Null
}
if ($transferReport -and [string]$transferReport.status -ne "PASS") {
    $errors.Add("Companion OTA transfer report status is '$($transferReport.status)', expected PASS.") | Out-Null
}
if ($transferReport -and $transferReport.transfer) {
    if ([string]$transferReport.transfer.transport -ne "companion_ota_v2") {
        $errors.Add("Companion OTA transfer transport is '$($transferReport.transfer.transport)', expected companion_ota_v2.") | Out-Null
    }
    if (-not [bool]$transferReport.transfer.versionConfirmed) {
        $errors.Add("Companion OTA report did not confirm completion/reboot handoff.") | Out-Null
    }
} elseif ($transferReport) {
    $errors.Add("Companion OTA report did not include transfer details.") | Out-Null
}
if ($PostOtaSettleSeconds -gt 0) {
    Start-Sleep -Seconds $PostOtaSettleSeconds
}

$finishedAt = (Get-Date).ToUniversalTime().ToString("o")
$status = if ($errors.Count -eq 0) { "PASS" } else { "FAIL" }
$summary = [ordered]@{
    schema = "companion.ble_ota.validation.v1"
    status = $status
    mode = "execute"
    started_at_utc = $startedAt
    finished_at_utc = $finishedAt
    package_path = $resolvedPackage
    manifest_path = $payload.manifest_path
    firmware_path = $payload.firmware_path
    manifest = if ($transferReport) { $transferReport.manifest } else { [ordered]@{ version = [string]$manifest.version; protocolName = [string]$manifest.protocol.name; protocol_name = [string]$manifest.protocol.name } }
    manifest_version = [string]$manifest.version
    protocol = [string]$manifest.protocol.name
    firmwareSha256 = if ($transferReport) { $transferReport.firmwareSha256 } else { $null }
    firmware_sha256 = if ($transferReport) { $transferReport.firmware_sha256 } else { $null }
    transfer = if ($transferReport) { $transferReport.transfer } else { $null }
    command = $commandLine
    prepare_loader_with_swd = [bool]$PrepareLoaderWithSwd
    prepare_log = if ($PrepareLoaderWithSwd) { $prepareLog } else { $null }
    programmer = $programmer
    port = $Port
    app_sector_count = $appSectorCount
    prompt_operator = [bool]$PromptOperator
    raw_log = $rawLog
    transfer_report_json = if ($transferReport) { $transferReportJson } else { $null }
    exit_code = $exitCode
    errors = @($errors)
}

$summary | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $summaryJson -Encoding UTF8
ConvertTo-CompanionBleOtaMarkdown -Summary $summary | Set-Content -LiteralPath $summaryMd -Encoding UTF8

Write-Host "companion_ble_ota_result_json=$($summary | ConvertTo-Json -Depth 12 -Compress)"
Write-Host "Summary: $summaryJson"
if ($transferReport) {
    Write-Host "Companion OTA transfer evidence: $transferReportJson"
}

if ($status -ne "PASS") {
    throw "Companion BLE OTA validation failed. See $summaryJson"
}
