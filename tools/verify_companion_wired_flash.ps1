param(
    [string] $PackagePath,
    [string] $TypeRepoRoot = (Join-Path $PSScriptRoot "..\..\..\Listener\Listener-Type"),
    [string] $ListenerExe,
    [string] $OutDir,
    [string] $Port = "SWD",
    [uint32] $Baud = 0,
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
    $OutDir = Join-Path $repoRoot ".cache\validation\companion-wired-flash-$stamp"
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

function Get-JsonAnyProperty {
    param(
        [Parameter(Mandatory = $true)] $Object,
        [Parameter(Mandatory = $true)][string[]] $Names
    )

    if ($null -eq $Object) {
        return $null
    }
    foreach ($name in $Names) {
        $property = $Object.PSObject.Properties[$name]
        if ($property) {
            return $property.Value
        }
    }
    return $null
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

function Get-WiredFirmwareResultFromLog {
    param([Parameter(Mandatory = $true)][string] $Text)

    foreach ($line in ($Text -split "\r?\n")) {
        $trimmed = $line.Trim()
        if ($trimmed.StartsWith("wired_firmware_result_json=", [System.StringComparison]::Ordinal)) {
            return $trimmed.Substring("wired_firmware_result_json=".Length) | ConvertFrom-Json
        }
    }
    return $null
}

function Get-WiredResultObject {
    param($Report)

    $extra = Get-JsonAnyProperty -Object $Report -Names @("extra")
    $result = $null
    if ($extra) {
        $result = Get-JsonAnyProperty -Object $extra -Names @("result")
    }
    if ($result) {
        return $result
    }
    return $Report
}

function Get-WiredPackageObject {
    param($Report)

    $extra = Get-JsonAnyProperty -Object $Report -Names @("extra")
    if (-not $extra) {
        return $null
    }
    return Get-JsonAnyProperty -Object $extra -Names @("package")
}

function Invoke-ListenerTypeCommand {
    param(
        [Parameter(Mandatory = $true)][string[]] $Arguments,
        [Parameter(Mandatory = $true)][string] $RawLogPath
    )

    Push-Location $typeRoot
    try {
        & $listenerExePath @Arguments 2>&1 | Tee-Object -FilePath $RawLogPath | Out-Host
        if ($null -eq $LASTEXITCODE) {
            return 0
        }
        return [int]$LASTEXITCODE
    } finally {
        Pop-Location
    }
}

function Test-WiredCheckReport {
    param(
        $Report,
        [int] $ExitCode
    )

    $errors = [System.Collections.Generic.List[string]]::new()
    if ($ExitCode -ne 0) {
        $errors.Add("listener-type exited with code $ExitCode.") | Out-Null
    }
    if (-not $Report) {
        $errors.Add("wired_firmware_result_json line was not found in Type output.") | Out-Null
        return @($errors)
    }

    $status = [string](Get-JsonAnyProperty -Object $Report -Names @("status"))
    $mode = [string](Get-JsonAnyProperty -Object $Report -Names @("mode"))
    $package = Get-WiredPackageObject -Report $Report
    $kind = [string](Get-JsonAnyProperty -Object $package -Names @("kind"))
    $project = [string](Get-JsonAnyProperty -Object $package -Names @("project"))
    $target = [string](Get-JsonAnyProperty -Object $package -Names @("target"))

    if ($status -ne "PASS") { $errors.Add("Type wired check status is '$status', expected PASS.") | Out-Null }
    if ($mode -ne "check") { $errors.Add("Type wired check mode is '$mode', expected check.") | Out-Null }
    if ($kind -ne "factory") { $errors.Add("Type wired package kind is '$kind', expected factory.") | Out-Null }
    if ($project -ne "Companion-Firmware") { $errors.Add("Type wired package project is '$project', expected Companion-Firmware.") | Out-Null }
    if ($target -ne "NUCLEO-WB55RG") { $errors.Add("Type wired package target is '$target', expected NUCLEO-WB55RG.") | Out-Null }
    return @($errors)
}

function Test-WiredFlashReport {
    param(
        $Report,
        [int] $ExitCode,
        [string] $ExpectedPort
    )

    $errors = [System.Collections.Generic.List[string]]::new()
    if ($ExitCode -ne 0) {
        $errors.Add("listener-type exited with code $ExitCode.") | Out-Null
    }
    if (-not $Report) {
        $errors.Add("wired_firmware_result_json line was not found in Type output.") | Out-Null
        return @($errors)
    }

    $status = [string](Get-JsonAnyProperty -Object $Report -Names @("status"))
    $mode = [string](Get-JsonAnyProperty -Object $Report -Names @("mode"))
    $flash = Get-WiredResultObject -Report $Report
    $action = [string](Get-JsonAnyProperty -Object $flash -Names @("action"))
    $kind = [string](Get-JsonAnyProperty -Object $flash -Names @("kind"))
    $port = [string](Get-JsonAnyProperty -Object $flash -Names @("port"))
    $log = [string](Get-JsonAnyProperty -Object $flash -Names @("log"))

    if ($status -ne "PASS") { $errors.Add("Type wired flash status is '$status', expected PASS.") | Out-Null }
    if ($mode -ne "flash") { $errors.Add("Type wired flash mode is '$mode', expected flash.") | Out-Null }
    if ($action -ne "flash") { $errors.Add("Type wired flash action is '$action', expected flash.") | Out-Null }
    if ($kind -ne "factory" -and $kind -ne "companion-wired-factory") { $errors.Add("Type wired flash kind is '$kind', expected factory.") | Out-Null }
    if ($port -ne $ExpectedPort) { $errors.Add("Type wired flash port is '$port', expected $ExpectedPort.") | Out-Null }
    if (-not $log.Contains("STM32WB wired factory flash completed and verified by STM32CubeProgrammer")) {
        $errors.Add("Type wired flash log did not include STM32CubeProgrammer completion.") | Out-Null
    }
    return @($errors)
}

function ConvertTo-CompanionWiredMarkdown {
    param(
        [Parameter(Mandatory = $true)] $Summary
    )

    $lines = @(
        "# Companion Wired Flash Validation",
        "",
        "- Status: $($Summary["status"])",
        "- Mode: $($Summary["mode"])",
        "- Package: ``$($Summary["package_path"])``",
        "- ListenerExe: ``$($Summary["listener_exe"])``",
        "- Port: ``$($Summary["port"])``",
        "- Command: ``$($Summary["command"])``",
        "- Raw log: ``$($Summary["raw_log"])``"
    )
    if ($Summary["type_report_json"]) {
        $lines += "- Type report JSON: ``$($Summary["type_report_json"])``"
    }
    if ($Summary["lock_command"]) {
        $lines += "- Hardware lock command: ``$($Summary["lock_command"])``"
    }
    foreach ($errorItem in @($Summary["errors"])) {
        $lines += "- Error: $errorItem"
    }
    return $lines
}

$resolvedPackage = Resolve-CompanionPackage -Path $PackagePath
$listenerExePath = Resolve-ListenerExe -Requested $ListenerExe
$rawLog = Join-Path $outDirResolved "companion-wired-flash-raw.log"
$typeReportJson = Join-Path $outDirResolved "wired_firmware_result.json"
$summaryJson = Join-Path $outDirResolved "companion-wired-flash-summary.json"
$summaryMd = Join-Path $outDirResolved "companion-wired-flash-summary.md"
$lockCommand = "pwsh -NoProfile -File C:\Users\Billy\Desktop\Denzic\ai-collaboration-workflow\scripts\aiw.ps1 with-lock -Resource Companion-WB55 -Purpose `"Companion wired factory flash validation`" -Run pwsh -NoProfile -File .\tools\verify_companion_wired_flash.ps1 -Execute -WorkflowLockHeld -PackagePath `"$resolvedPackage`""

if (-not $Execute) {
    $commandArgs = @("--wired-firmware-check", $resolvedPackage)
    $commandLine = ConvertTo-CommandLine -FilePath $listenerExePath -Arguments $commandArgs
    $exitCode = Invoke-ListenerTypeCommand -Arguments $commandArgs -RawLogPath $rawLog
    $rawText = Get-Content -LiteralPath $rawLog -Raw -Encoding UTF8
    $typeReport = Get-WiredFirmwareResultFromLog -Text $rawText
    if ($typeReport) {
        $typeReport | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $typeReportJson -Encoding UTF8
    }
    $errors = @(Test-WiredCheckReport -Report $typeReport -ExitCode $exitCode)
    $status = if ($errors.Count -eq 0) { "PASS" } else { "FAIL" }
    $summary = [ordered]@{
        schema = "companion.wired_flash.validation.v1"
        status = $status
        mode = "dry-run"
        generated_at = (Get-Date).ToString("o")
        package_path = $resolvedPackage
        listener_exe = $listenerExePath
        port = $Port
        command = $commandLine
        lock_command = $lockCommand
        raw_log = $rawLog
        type_report_json = if ($typeReport) { $typeReportJson } else { $null }
        exit_code = $exitCode
        errors = @($errors)
    }
    $summary | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $summaryJson -Encoding UTF8
    ConvertTo-CompanionWiredMarkdown -Summary $summary | Set-Content -LiteralPath $summaryMd -Encoding UTF8
    Write-Host "DRY-RUN: Companion wired flash validation is ready for hardware execution."
    Write-Host "$status`: Companion wired flash dry-run check complete."
    Write-Host "Package: $resolvedPackage"
    Write-Host "ListenerExe: $listenerExePath"
    Write-Host "Run real wired flash with workflow hardware lock:"
    Write-Host "  $lockCommand"
    Write-Host "Summary: $summaryJson"
    Write-Host "companion_wired_flash_result_json=$($summary | ConvertTo-Json -Depth 8 -Compress)"
    if ($typeReport) {
        Write-Host "Type report evidence: $typeReportJson"
    }
    if ($status -ne "PASS") {
        throw "Companion wired flash dry-run check failed. See $summaryJson"
    }
    exit 0
}

if (-not $WorkflowLockHeld) {
    Write-Host "Use the workflow hardware lock before executing:"
    Write-Host "  $lockCommand"
    throw "Refusing to run Companion wired flash validation without -WorkflowLockHeld."
}

Show-OperatorPrompt `
    -Title "Companion 有线刷机验证即将开始" `
    -Message "请确认 NUCLEO-WB55RG 已通过内置 ST-LINK 的 USB 数据线连接，Companion 目标板供电稳定，当前没有其它工具占用 STM32CubeProgrammer/ST-LINK。点击 OK 后脚本会通过 Type headless 有线刷机把同一个 Companion package 写入设备，并把 wired_firmware_result_json 证据写入：$outDirResolved"

$commandArgs = @("--wired-firmware-flash", $resolvedPackage, $Port)
if ($Baud -gt 0) {
    $commandArgs += [string]$Baud
}
$commandLine = ConvertTo-CommandLine -FilePath $listenerExePath -Arguments $commandArgs
$startedAt = (Get-Date).ToUniversalTime().ToString("o")
$exitCode = Invoke-ListenerTypeCommand -Arguments $commandArgs -RawLogPath $rawLog
$rawText = Get-Content -LiteralPath $rawLog -Raw -Encoding UTF8
$typeReport = Get-WiredFirmwareResultFromLog -Text $rawText
if ($typeReport) {
    $typeReport | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $typeReportJson -Encoding UTF8
}
$errors = @(Test-WiredFlashReport -Report $typeReport -ExitCode $exitCode -ExpectedPort $Port)
$finishedAt = (Get-Date).ToUniversalTime().ToString("o")
$status = if ($errors.Count -eq 0) { "PASS" } else { "FAIL" }
$summary = [ordered]@{
    schema = "companion.wired_flash.validation.v1"
    status = $status
    mode = "execute"
    started_at_utc = $startedAt
    finished_at_utc = $finishedAt
    package_path = $resolvedPackage
    listener_exe = $listenerExePath
    port = $Port
    baud = if ($Baud -gt 0) { $Baud } else { $null }
    command = $commandLine
    raw_log = $rawLog
    type_report_json = if ($typeReport) { $typeReportJson } else { $null }
    exit_code = $exitCode
    errors = @($errors)
}

$summary | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $summaryJson -Encoding UTF8
ConvertTo-CompanionWiredMarkdown -Summary $summary | Set-Content -LiteralPath $summaryMd -Encoding UTF8

Write-Host "companion_wired_flash_result_json=$($summary | ConvertTo-Json -Depth 8 -Compress)"
Write-Host "Summary: $summaryJson"
if ($typeReport) {
    Write-Host "Type report evidence: $typeReportJson"
}

if ($status -ne "PASS") {
    throw "Companion wired flash validation failed. See $summaryJson"
}
