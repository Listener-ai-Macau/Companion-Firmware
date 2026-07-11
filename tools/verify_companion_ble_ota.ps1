param(
    [string] $PackagePath,
    [string] $TypeRepoRoot = (Join-Path $PSScriptRoot "..\..\Companion-Type"),
    [Alias("ListenerExe")]
    [string] $CompanionExe,
    [string] $ProgrammerPath,
    [string] $Port = "SWD",
    [string] $OutDir,
    [int] $LoaderBootDelayMs = 8000,
    [switch] $PrepareLoaderWithSwd,
    [switch] $PromptOperator,
    [switch] $Execute,
    [switch] $WorkflowLockHeld
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$typeRoot = (Resolve-Path $TypeRepoRoot).Path
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

function Resolve-CompanionExe {
    param([string] $Requested)

    $candidates = @()
    if ($Requested) { $candidates += $Requested }
    $candidates += @(
        "C:\Program Files\Companion Type\companion-type.exe",
        (Join-Path $typeRoot "apps\windows\src-tauri\target\release\companion-type.exe"),
        (Join-Path $typeRoot "apps\windows\src-tauri\target\debug\companion-type.exe"),
        (Join-Path $typeRoot "apps\windows\src-tauri\target\debug\companion-type"),
        (Join-Path $typeRoot "apps\windows\src-tauri\target\release\companion-type")
    )

    foreach ($candidate in $candidates) {
        if ([string]::IsNullOrWhiteSpace($candidate)) { continue }
        if (Test-Path -LiteralPath $candidate -PathType Leaf) {
            return (Resolve-Path -LiteralPath $candidate).Path
        }
    }
    throw "companion-type executable not found. Build Companion-Type first or pass -CompanionExe."
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

function ConvertTo-SafeFileName {
    param([Parameter(Mandatory = $true)][string] $Name)
    return (($Name.ToLowerInvariant() -replace '[^a-z0-9_.-]+', '-') -replace '^-|-$', '')
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

function Get-FirmwareOtaResultFromLog {
    param([Parameter(Mandatory = $true)][string] $Text)

    foreach ($line in ($Text -split "\r?\n")) {
        $trimmed = $line.Trim()
        if ($trimmed.StartsWith("firmware_ota_result_json=", [System.StringComparison]::Ordinal)) {
            return $trimmed.Substring("firmware_ota_result_json=".Length) | ConvertFrom-Json
        }
    }
    return $null
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
    if ($Summary["type_report_json"]) {
        $lines += "- Type report JSON: ``$($Summary["type_report_json"])``"
    }
    foreach ($errorItem in @($Summary["errors"])) {
        $lines += "- Error: $errorItem"
    }
    return $lines
}

$resolvedPackage = Resolve-CompanionPackage -Path $PackagePath
$companionExePath = Resolve-CompanionExe -Requested $CompanionExe
if ($Execute -and -not $companionExePath.StartsWith("C:\Program Files\Companion Type\", [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Real Companion OTA acceptance must run the MSI-installed Companion Type from C:\Program Files\Companion Type. Install the current MSI before -Execute."
}
$payload = Expand-CompanionOtaPayload -Path $resolvedPackage -DestinationDir $outDirResolved
$manifestText = Get-Content -LiteralPath $payload.manifest_path -Raw -Encoding UTF8
$manifest = $manifestText | ConvertFrom-Json
$rawLog = Join-Path $outDirResolved "companion-ble-ota-raw.log"
$prepareLog = Join-Path $outDirResolved "companion-ble-ota-prepare-loader.log"
$typeReportJson = Join-Path $outDirResolved "firmware_ota_result.json"
$summaryJson = Join-Path $outDirResolved "companion-ble-ota-summary.json"
$summaryMd = Join-Path $outDirResolved "companion-ble-ota-summary.md"
$programmer = if ($PrepareLoaderWithSwd) { Find-CubeProgrammerCli -RequestedPath $ProgrammerPath } else { $null }
$appSectorCount = if ($PrepareLoaderWithSwd) { Get-AppSectorCount -FirmwarePath $payload.firmware_path } else { $null }
$commandArgs = @("--firmware-ota-transfer", $payload.manifest_path, $payload.firmware_path)
$commandLine = '"' + $companionExePath + '" ' + (($commandArgs | ForEach-Object { '"' + ($_ -replace '"', '\"') + '"' }) -join " ")
$lockCommand = "pwsh -NoProfile -File C:\Users\Billy\Desktop\Denzic\ai-collaboration-workflow\scripts\aiw.ps1 with-lock -Resource Companion-WB55,BLE-Companion -Purpose `"Companion BLE OTA validation`" -Run pwsh -NoProfile -File .\tools\verify_companion_ble_ota.ps1 -Execute -WorkflowLockHeld -PackagePath `"$resolvedPackage`""
if ($PrepareLoaderWithSwd) {
    $lockCommand += " -PrepareLoaderWithSwd"
}

if (-not $Execute) {
    $summary = [ordered]@{
        schema = "companion.ble_ota.validation.v1"
        status = "DRY_RUN"
        mode = "dry-run"
        generated_at = (Get-Date).ToString("o")
        package_path = $resolvedPackage
        companion_exe = $companionExePath
        manifest_path = $payload.manifest_path
        firmware_path = $payload.firmware_path
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
        type_report_json = $null
        errors = @()
    }
    $summary | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $summaryJson -Encoding UTF8
    ConvertTo-CompanionBleOtaMarkdown -Summary $summary | Set-Content -LiteralPath $summaryMd -Encoding UTF8
    Write-Host "DRY-RUN: Companion BLE OTA validation is ready."
    Write-Host "Package: $resolvedPackage"
    Write-Host "CompanionExe: $companionExePath"
    Write-Host "Manifest: $($payload.manifest_path)"
    Write-Host "Firmware: $($payload.firmware_path)"
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
        -Message "请确认 Companion 已开机，电脑蓝牙可用，Companion Type 没有正在录音或传输。点击 OK 后会开始蓝牙升级；升级过程中不要断电、不要关闭 Companion Type。设备重启或短暂断开再恢复是正常现象。"
}

$errors = [System.Collections.Generic.List[string]]::new()
$startedAt = (Get-Date).ToUniversalTime().ToString("o")
$exitCode = 0
$typeReport = $null

try {
    Push-Location $typeRoot
    try {
        & $companionExePath @commandArgs 2>&1 | Tee-Object -FilePath $rawLog
        $exitCode = if ($null -eq $LASTEXITCODE) { 0 } else { [int]$LASTEXITCODE }
    } finally {
        Pop-Location
    }

    $rawText = Get-Content -LiteralPath $rawLog -Raw -Encoding UTF8
    $typeReport = Get-FirmwareOtaResultFromLog -Text $rawText
    if ($typeReport) {
        $typeReport | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $typeReportJson -Encoding UTF8
    } else {
        $errors.Add("firmware_ota_result_json line was not found in Type output.") | Out-Null
    }
    if ($exitCode -ne 0) {
        $errors.Add("companion-type exited with code $exitCode.") | Out-Null
    }
    if ($typeReport -and [string]$typeReport.status -ne "PASS") {
        $errors.Add("Type OTA report status is '$($typeReport.status)', expected PASS.") | Out-Null
    }
    if ($typeReport -and [string]$typeReport.protocol -ne "denzic_ota_v1") {
        $errors.Add("Companion Type OTA protocol is '$($typeReport.protocol)', expected denzic_ota_v1.") | Out-Null
    }
    if ($typeReport -and ([int64]$typeReport.firmwareBytes -le 0 -or [int64]$typeReport.dataWrites -le 0 -or [int64]$typeReport.statusReads -le 0)) {
        $errors.Add("Companion Type OTA report lacks positive firmware/data/status evidence.") | Out-Null
    }
    if ($typeReport -and -not [bool]$typeReport.activeLinkConfirmed) {
        $errors.Add("Companion Type OTA report did not confirm an active BLE link.") | Out-Null
    }
} catch {
    $errors.Add($_.Exception.Message) | Out-Null
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
    companion_exe = $companionExePath
    manifest_path = $payload.manifest_path
    firmware_path = $payload.firmware_path
    manifest_version = [string]$manifest.version
    protocol = [string]$manifest.protocol.name
    command = $commandLine
    prepare_loader_with_swd = [bool]$PrepareLoaderWithSwd
    prepare_log = if ($PrepareLoaderWithSwd) { $prepareLog } else { $null }
    programmer = $programmer
    port = $Port
    app_sector_count = $appSectorCount
    prompt_operator = [bool]$PromptOperator
    raw_log = $rawLog
    type_report_json = if ($typeReport) { $typeReportJson } else { $null }
    exit_code = $exitCode
    errors = @($errors)
}

$summary | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $summaryJson -Encoding UTF8
ConvertTo-CompanionBleOtaMarkdown -Summary $summary | Set-Content -LiteralPath $summaryMd -Encoding UTF8

Write-Host "companion_ble_ota_result_json=$($summary | ConvertTo-Json -Depth 8 -Compress)"
Write-Host "Summary: $summaryJson"
if ($typeReport) {
    Write-Host "Type report evidence: $typeReportJson"
}

if ($status -ne "PASS") {
    throw "Companion BLE OTA validation failed. See $summaryJson"
}
