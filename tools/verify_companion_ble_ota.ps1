param(
    [string] $PackagePath,
    [string] $TypeRepoRoot = (Join-Path $PSScriptRoot "..\..\..\Listener\Listener-Type"),
    [string] $ListenerExe,
    [string] $OutDir,
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

function Resolve-ListenerExe {
    param([string] $Requested)

    $candidates = @()
    if ($Requested) { $candidates += $Requested }
    $candidates += @(
        (Join-Path $typeRoot "src-tauri\target\debug\listener-type.exe"),
        (Join-Path $typeRoot "src-tauri\target\release\listener-type.exe"),
        (Join-Path $typeRoot "src-tauri\target\debug\listener-type"),
        (Join-Path $typeRoot "src-tauri\target\release\listener-type")
    )

    foreach ($candidate in $candidates) {
        if ([string]::IsNullOrWhiteSpace($candidate)) { continue }
        if (Test-Path -LiteralPath $candidate -PathType Leaf) {
            return (Resolve-Path -LiteralPath $candidate).Path
        }
    }
    throw "listener-type executable not found. Build Listener-Type first or pass -ListenerExe."
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

function Set-CompanionTypeEnvironment {
    $env:LISTENER_TYPE_APP_PROFILE = "companion"
    $env:LISTENER_TYPE_BLE_TARGET_NAME = "companion"
    $env:LISTENER_TYPE_HIDE_MAIN_ON_START = "1"
    $env:LISTENER_TYPE_DISABLE_BACKGROUND_BLE = "1"
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
        "- Raw log: ``$($Summary["raw_log"])``"
    )
    if ($Summary["type_report_json"]) {
        $lines += "- Type report JSON: ``$($Summary["type_report_json"])``"
    }
    foreach ($errorItem in @($Summary["errors"])) {
        $lines += "- Error: $errorItem"
    }
    return $lines
}

$resolvedPackage = Resolve-CompanionPackage -Path $PackagePath
$listenerExePath = Resolve-ListenerExe -Requested $ListenerExe
$payload = Expand-CompanionOtaPayload -Path $resolvedPackage -DestinationDir $outDirResolved
$manifestText = Get-Content -LiteralPath $payload.manifest_path -Raw -Encoding UTF8
$manifest = $manifestText | ConvertFrom-Json
$rawLog = Join-Path $outDirResolved "companion-ble-ota-raw.log"
$typeReportJson = Join-Path $outDirResolved "firmware_ota_result.json"
$summaryJson = Join-Path $outDirResolved "companion-ble-ota-summary.json"
$summaryMd = Join-Path $outDirResolved "companion-ble-ota-summary.md"
$commandArgs = @("--firmware-ota-transfer", $payload.manifest_path, $payload.firmware_path)
$commandLine = '"' + $listenerExePath + '" ' + (($commandArgs | ForEach-Object { '"' + ($_ -replace '"', '\"') + '"' }) -join " ")
$lockCommand = "pwsh -NoProfile -File C:\Users\Billy\Desktop\Denzic\ai-collaboration-workflow\scripts\aiw.ps1 with-lock -Resource Companion-WB55,BLE-Companion -Purpose `"Companion BLE OTA validation`" -Run pwsh -NoProfile -File .\tools\verify_companion_ble_ota.ps1 -Execute -WorkflowLockHeld -PackagePath `"$resolvedPackage`""

if (-not $Execute) {
    $summary = [ordered]@{
        schema = "companion.ble_ota.validation.v1"
        status = "DRY_RUN"
        mode = "dry-run"
        generated_at = (Get-Date).ToString("o")
        package_path = $resolvedPackage
        listener_exe = $listenerExePath
        manifest_path = $payload.manifest_path
        firmware_path = $payload.firmware_path
        manifest_version = [string]$manifest.version
        protocol = [string]$manifest.protocol.name
        command = $commandLine
        lock_command = $lockCommand
        raw_log = $rawLog
        type_report_json = $null
        errors = @()
    }
    $summary | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $summaryJson -Encoding UTF8
    ConvertTo-CompanionBleOtaMarkdown -Summary $summary | Set-Content -LiteralPath $summaryMd -Encoding UTF8
    Write-Host "DRY-RUN: Companion BLE OTA validation is ready."
    Write-Host "Package: $resolvedPackage"
    Write-Host "ListenerExe: $listenerExePath"
    Write-Host "Manifest: $($payload.manifest_path)"
    Write-Host "Firmware: $($payload.firmware_path)"
    Write-Host "Run with workflow hardware lock:"
    Write-Host "  $lockCommand"
    Write-Host "Summary: $summaryJson"
    exit 0
}

if (-not $WorkflowLockHeld) {
    Write-Host "Use the workflow hardware lock before executing:"
    Write-Host "  $lockCommand"
    throw "Refusing to run Companion BLE OTA validation without -WorkflowLockHeld."
}

Show-OperatorPrompt `
    -Title "Companion BLE OTA 验证即将开始" `
    -Message "请确认 Companion 已刷入 OTA loader，设备蓝牙名为 companion，Listener Type 后台未在录音/传输，电脑蓝牙可连接。点击 OK 后脚本会通过 Type headless BLE OTA 把同一个 Companion package 传输到设备，并把 firmware_ota_result_json 证据写入：$outDirResolved"

$errors = [System.Collections.Generic.List[string]]::new()
$startedAt = (Get-Date).ToUniversalTime().ToString("o")
$exitCode = 0
$typeReport = $null

try {
    Push-Location $typeRoot
    try {
        Set-CompanionTypeEnvironment
        & $listenerExePath @commandArgs 2>&1 | Tee-Object -FilePath $rawLog
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
        $errors.Add("listener-type exited with code $exitCode.") | Out-Null
    }
    if ($typeReport -and [string]$typeReport.status -ne "PASS") {
        $errors.Add("Type OTA report status is '$($typeReport.status)', expected PASS.") | Out-Null
    }
    if ($typeReport -and [string]$typeReport.transfer.transport -ne "stm32wb_st_ble_ota") {
        $errors.Add("Type OTA transfer transport is '$($typeReport.transfer.transport)', expected stm32wb_st_ble_ota.") | Out-Null
    }
    if ($typeReport -and -not [bool]$typeReport.transfer.versionConfirmed) {
        $errors.Add("Type OTA report did not confirm STM32WB ST reboot handoff.") | Out-Null
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
    listener_exe = $listenerExePath
    manifest_path = $payload.manifest_path
    firmware_path = $payload.firmware_path
    manifest_version = [string]$manifest.version
    protocol = [string]$manifest.protocol.name
    command = $commandLine
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
