param(
    [string] $PackagePath,
    [string] $TypeRepoRoot = (Join-Path $PSScriptRoot "..\..\..\Listener\Listener-Type"),
    [string] $ListenerExe,
    [string] $EvidencePath,
    [string] $OutDir,
    [string] $ProgrammerPath,
    [string] $Port = "SWD",
    [uint32] $Baud = 0,
    [int] $ProbeTimeoutMs = 30000,
    [int] $PostFlashAppSettleSeconds = 5,
    [int] $A1TimeoutMs = 45000,
    [int] $A1Rounds = 6,
    [string] $A1PlaybackTextList = "",
    [int] $A2TimeoutMs = 120000,
    [int] $MaxMissingPackets = 0,
    [switch] $SkipWirelessStackProvisioning,
    [switch] $IncludeTypeHarness,
    [switch] $IncludeTypeUiGate,
    [switch] $PromptOperator,
    [switch] $Execute,
    [switch] $WorkflowLockHeld
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$typeRoot = $null
if ($IncludeTypeHarness -or $IncludeTypeUiGate) {
    $typeRoot = (Resolve-Path $TypeRepoRoot).Path
}
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
if ([string]::IsNullOrWhiteSpace($OutDir)) {
    $OutDir = Join-Path $repoRoot ".cache\validation\companion-hardware-acceptance-$stamp"
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

function Get-SafeLogName {
    param([Parameter(Mandatory = $true)][string] $Name)
    return (($Name.ToLowerInvariant() -replace '[^a-z0-9_.-]+', '-') -replace '^-|-$', '') + ".log"
}

function Find-CubeProgrammerCli {
    param([string] $RequestedPath)

    $candidates = @()
    if ($RequestedPath) { $candidates += $RequestedPath }
    if ($env:STM32CUBEPROGRAMMER_CLI) { $candidates += $env:STM32CUBEPROGRAMMER_CLI }
    if ($env:STM32CUBEPROGRAMMER_PATH) { $candidates += (Join-Path $env:STM32CUBEPROGRAMMER_PATH "STM32_Programmer_CLI.exe") }

    foreach ($commandName in @("STM32_Programmer_CLI.exe", "STM32_Programmer_CLI")) {
        $command = Get-Command $commandName -ErrorAction SilentlyContinue
        if ($command) { $candidates += $command.Source }
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
        $matches = @(Get-ChildItem -Path $candidate -File -ErrorAction SilentlyContinue | Sort-Object FullName -Descending)
        if ($matches.Count -gt 0) { return $matches[0].FullName }
        if (Test-Path -LiteralPath $candidate -PathType Leaf) { return (Resolve-Path -LiteralPath $candidate).Path }
    }

    return $null
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

function Invoke-AcceptanceStep {
    param(
        [Parameter(Mandatory = $true)][string] $Name,
        [Parameter(Mandatory = $true)][string] $WorkingDirectory,
        [Parameter(Mandatory = $true)][string] $FilePath,
        [string[]] $Arguments = @()
    )

    $logPath = Join-Path $outDirResolved (Get-SafeLogName $Name)
    $commandLine = ConvertTo-CommandLine -FilePath $FilePath -Arguments $Arguments
    $started = Get-Date
    $status = "PASS"
    $message = "ok"
    $exitCode = 0

    Write-Host ""
    Write-Host "== $Name =="
    Write-Host $commandLine

    Push-Location $WorkingDirectory
    try {
        & $FilePath @Arguments 2>&1 | Tee-Object -FilePath $logPath
        $exitCode = if ($null -eq $LASTEXITCODE) { 0 } else { [int]$LASTEXITCODE }
        if ($exitCode -ne 0) {
            throw "$Name failed with exit code $exitCode."
        }
    } catch {
        $status = "FAIL"
        $message = $_.Exception.Message
        throw
    } finally {
        Pop-Location
        $ended = Get-Date
        $script:steps.Add([ordered]@{
            name = $Name
            status = $status
            command = $commandLine
            working_directory = $WorkingDirectory
            exit_code = $exitCode
            log = $logPath
            started_at = $started.ToString("o")
            ended_at = $ended.ToString("o")
            duration_ms = [int64]($ended - $started).TotalMilliseconds
            message = $message
        }) | Out-Null
    }
}

function ConvertTo-HardwareAcceptanceMarkdown {
    param([Parameter(Mandatory = $true)] $Report)

    $lines = @(
        "# Companion Hardware Acceptance",
        "",
        "- Status: $($Report["status"])",
        "- Mode: $($Report["mode"])",
        "- Package: ``$($Report["package_path"])``",
        "- Output dir: ``$($Report["output_dir"])``",
        "- Hardware lock command: ``$($Report["lock_command"])``",
        "",
        "## Evidence",
        "",
        "- Native BLE GATT: ``$($Report["evidence"]["native_ble_gatt"])``",
        "- Post-OTA native BLE GATT: ``$($Report["evidence"]["post_ota_native_ble_gatt"])``",
        "- Wired flash: ``$($Report["evidence"]["wired_flash"])``",
        "- BLE OTA: ``$($Report["evidence"]["ble_ota"])``",
        "- Wireless stack: ``$($Report["evidence"]["wireless_stack"])``",
        "- Manual gate report: ``$($Report["evidence"]["manual_gate_report"])``",
        "",
        "## Steps"
    )
    if ($Report["evidence"]["a1_a2"]) {
        $lines = $lines[0..7] + "- Legacy Type A1/A2: ``$($Report["evidence"]["a1_a2"])``" + $lines[8..($lines.Count - 1)]
    } else {
        $lines = $lines[0..7] + "- Legacy Type A1/A2: skipped (independent Companion release gate)" + $lines[8..($lines.Count - 1)]
    }
    if ($Report["evidence"]["type_ui"]) {
        $lines = $lines[0..8] + "- Type UI: ``$($Report["evidence"]["type_ui"])``" + $lines[9..($lines.Count - 1)]
    } else {
        $lines = $lines[0..8] + "- Type UI: skipped (independent Companion release gate)" + $lines[9..($lines.Count - 1)]
    }
    foreach ($step in @($Report["steps"])) {
        $message = if ($step.Contains("message")) { $step["message"] } else { "" }
        $lines += "- $($step["name"]): $($step["status"]) ($message)"
    }
    if (@($Report["errors"]).Count -gt 0) {
        $lines += ""
        $lines += "## Errors"
        foreach ($errorItem in @($Report["errors"])) {
            $lines += "- $errorItem"
        }
    }
    return $lines
}

$resolvedPackage = Resolve-CompanionPackage -Path $PackagePath
$summaryJson = Join-Path $outDirResolved "companion-hardware-acceptance-summary.json"
$summaryMd = Join-Path $outDirResolved "companion-hardware-acceptance-summary.md"
$a1Dir = Join-Path $outDirResolved "a1-a2"
$bleDir = Join-Path $outDirResolved "ble-ota"
$wiredDir = Join-Path $outDirResolved "wired-flash"
$nativeBleDir = Join-Path $outDirResolved "native-ble-gatt"
$postOtaNativeBleDir = Join-Path $outDirResolved "post-ota-native-ble-gatt"
$typeUiDir = Join-Path $outDirResolved "type-ui-manual"
$manualDir = Join-Path $outDirResolved "manual-gate-evidence"
$wirelessDir = Join-Path $outDirResolved "wireless-stack"
$a1Summary = Join-Path $a1Dir "companion-type-a1-a2-summary.json"
$bleSummary = Join-Path $bleDir "companion-ble-ota-summary.json"
$wiredSummary = Join-Path $wiredDir "companion-wired-flash-summary.json"
$nativeBleSummary = Join-Path $nativeBleDir "companion-ble-real-bench.json"
$postOtaNativeBleSummary = Join-Path $postOtaNativeBleDir "companion-ble-real-bench.json"
$typeUiSummary = Join-Path $typeUiDir "companion-type-ui-manual-summary.json"
$manualSummary = Join-Path $manualDir "companion-manual-gate-evidence-summary.json"
$wirelessSummary = Join-Path $wirelessDir "companion-wireless-stack-summary.json"
$programmer = Find-CubeProgrammerCli -RequestedPath $ProgrammerPath
$programmerForCommand = if ($programmer) { $programmer } else { "STM32_Programmer_CLI.exe" }

$aiw = "C:\Users\Billy\Desktop\Denzic\ai-collaboration-workflow\scripts\aiw.ps1"
$lockCommand = "pwsh -NoProfile -File $aiw with-lock -Resource Companion-WB55,BLE-Companion -Purpose `"Companion hardware acceptance`" -Run pwsh -NoProfile -File .\tools\verify_companion_hardware_acceptance.ps1 -Execute -WorkflowLockHeld -PackagePath `"$resolvedPackage`""
if ($IncludeTypeUiGate) {
    $lockCommand += " -IncludeTypeUiGate -EvidencePath <type-ui-screenshot-or-log>"
}
if ($IncludeTypeHarness) {
    $lockCommand += " -IncludeTypeHarness"
}

$steps = [System.Collections.Generic.List[object]]::new()
$errors = [System.Collections.Generic.List[string]]::new()

$wirelessArgs = @(
    "-NoProfile", "-File", ".\tools\provision_companion_wireless_stack.ps1",
    "-Execute", "-WorkflowLockHeld",
    "-InstallBleStack",
    "-OutDir", $wirelessDir
)
$acceptanceA1PlaybackTexts = @($A1PlaybackTextList -split "\|" | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | ForEach-Object { $_.Trim() })
if ($acceptanceA1PlaybackTexts.Count -eq 0) {
    $acceptanceA1PlaybackTexts = @(
        "打开设置",
        "新建文件",
        "保存文件",
        "打开设置",
        "新建文件",
        "保存文件"
    )
}

$a1Args = @(
    "-NoProfile", "-File", ".\tools\verify_companion_type_a1_a2.ps1",
    "-Execute", "-WorkflowLockHeld",
    "-TypeRepoRoot", $typeRoot,
    "-OutDir", $a1Dir,
    "-SkipInitialProbe",
    "-ProbeTimeoutMs", [string]$ProbeTimeoutMs,
    "-A1TimeoutMs", [string]$A1TimeoutMs,
    "-A1Rounds", [string]$A1Rounds,
    "-A1PlaybackTextList", ($acceptanceA1PlaybackTexts -join "|"),
    "-A2TimeoutMs", [string]$A2TimeoutMs,
    "-MaxMissingPackets", [string]$MaxMissingPackets
)
$bleArgs = @(
    "-NoProfile", "-File", ".\tools\verify_companion_ble_ota.ps1",
    "-Execute", "-WorkflowLockHeld",
    "-PrepareLoaderWithSwd",
    "-PackagePath", $resolvedPackage,
    "-OutDir", $bleDir
)
$wiredArgs = @(
    "-NoProfile", "-File", ".\tools\verify_companion_wired_flash.ps1",
    "-Execute", "-WorkflowLockHeld",
    "-PackagePath", $resolvedPackage,
    "-OutDir", $wiredDir,
    "-Port", $Port
)
$nativeBleArgs = @(
    ".\tools\companion_ble_real_bench.py",
    "--name", "companion",
    "--timeout", "20",
    "--notify-timeout", "10",
    "--output", $nativeBleSummary,
    "--json"
)
$postOtaNativeBleArgs = @(
    ".\tools\companion_ble_real_bench.py",
    "--name", "companion",
    "--timeout", "20",
    "--notify-timeout", "10",
    "--output", $postOtaNativeBleSummary,
    "--json"
)
$postFlashResetScript = @"
& '$programmerForCommand' -c port=$Port mode=UR reset=HWrst freq=4000 -w8 0x20000000 0x00 0x07 0x00 0xC3 -r8 0x20000000 4 -rst
if (`$LASTEXITCODE -ne 0) { exit `$LASTEXITCODE }
Start-Sleep -Seconds $PostFlashAppSettleSeconds
"@
$postFlashResetArgs = @("-NoProfile", "-Command", $postFlashResetScript)
$typeUiArgs = @(
    "-NoProfile", "-File", ".\tools\verify_companion_type_ui_manual.ps1",
    "-Execute", "-WorkflowLockHeld",
    "-PackagePath", $resolvedPackage,
    "-TypeRepoRoot", $typeRoot,
    "-OutDir", $typeUiDir
)
if (-not [string]::IsNullOrWhiteSpace($ListenerExe)) {
    $a1Args += @("-ListenerExe", $ListenerExe)
}
if ($Baud -gt 0) {
    $wiredArgs += @("-Baud", [string]$Baud)
}
if (-not [string]::IsNullOrWhiteSpace($ProgrammerPath)) {
    $bleArgs += @("-ProgrammerPath", $ProgrammerPath)
    $wiredArgs += @("-ProgrammerPath", $ProgrammerPath)
}
if (-not [string]::IsNullOrWhiteSpace($EvidencePath)) {
    $typeUiArgs += @("-EvidencePath", $EvidencePath)
}

$manualArgs = @(
    "-NoProfile", "-File", ".\tools\verify_companion_manual_gate_evidence.ps1",
    "-PackagePath", $resolvedPackage,
    "-NativeBleBenchPath", $postOtaNativeBleSummary,
    "-BleOtaEvidencePath", $bleSummary,
    "-WiredFlashEvidencePath", $wiredSummary,
    "-OutDir", $manualDir
)
if ($IncludeTypeHarness) {
    $manualArgs += @("-A1A2SummaryPath", $a1Summary, "-IncludeTypeHarness")
}
if ($IncludeTypeUiGate) {
    $manualArgs += @("-TypeUiEvidencePath", $typeUiSummary, "-IncludeTypeUiGate")
}

if (-not $Execute) {
    $dryRunSteps = @(
        [ordered]@{ name = "ensure CPU2 BLE wireless stack"; status = $(if ($SkipWirelessStackProvisioning) { "SKIPPED" } else { "DRY_RUN" }); message = $(if ($SkipWirelessStackProvisioning) { "skipped by -SkipWirelessStackProvisioning; only use after a PASS provisioning summary exists" } else { "not executed; reads FUS and installs STM32CubeWB BLE full stack before CPU1 BLE apps" }); command = ConvertTo-CommandLine -FilePath "pwsh" -Arguments $wirelessArgs; evidence = $wirelessSummary },
        [ordered]@{ name = "real Companion wired flash from same package"; status = "DRY_RUN"; message = "not executed; flashes the same package OTA loader and unified Companion VKA1 app before A1/A2"; command = ConvertTo-CommandLine -FilePath "pwsh" -Arguments $wiredArgs; evidence = $wiredSummary },
        [ordered]@{ name = "post-flash Companion app handoff reset"; status = "DRY_RUN"; message = "not executed; rewrites OTA app handoff, hard-resets the board, then waits $PostFlashAppSettleSeconds seconds before BLE capture"; command = ConvertTo-CommandLine -FilePath "pwsh" -Arguments $postFlashResetArgs; evidence = $null },
        [ordered]@{ name = "real Companion-native BLE GATT bench validation"; status = "DRY_RUN"; message = "not executed; exercises the Companion-native GATT contract without Listener-Type"; command = ConvertTo-CommandLine -FilePath "python" -Arguments $nativeBleArgs; evidence = $nativeBleSummary },
        [ordered]@{ name = "real Companion BLE OTA bench validation"; status = "DRY_RUN"; message = "not executed; transfers the same package over the Companion OTA v2 path"; command = ConvertTo-CommandLine -FilePath "pwsh" -Arguments $bleArgs; evidence = $bleSummary }
    )
    if ($IncludeTypeHarness) {
        $dryRunSteps += [ordered]@{ name = "legacy Type A1/A2 bench validation"; status = "DRY_RUN"; message = "not executed; optional compatibility evidence only"; command = ConvertTo-CommandLine -FilePath "pwsh" -Arguments $a1Args; evidence = $a1Summary }
    }
    if ($IncludeTypeUiGate) {
        $dryRunSteps += [ordered]@{ name = "Type temporary Companion debug page"; status = "DRY_RUN"; message = "not executed; optional legacy Type UI gate against the same unified Companion VKA1 app"; command = ConvertTo-CommandLine -FilePath "pwsh" -Arguments $typeUiArgs; evidence = $typeUiSummary }
    }
    $dryRunSteps += [ordered]@{ name = "post-OTA Companion-native BLE GATT bench validation"; status = "DRY_RUN"; message = "not executed; verifies the app boots and exposes native GATT after BLE OTA"; command = ConvertTo-CommandLine -FilePath "python" -Arguments $postOtaNativeBleArgs; evidence = $postOtaNativeBleSummary }
    $dryRunSteps += [ordered]@{ name = "manual gate evidence verifier"; status = "DRY_RUN"; message = "not executed until all required gate summaries exist"; command = ConvertTo-CommandLine -FilePath "pwsh" -Arguments $manualArgs; evidence = $manualSummary }
    $report = [ordered]@{
        schema = "companion.hardware_acceptance.validation.v1"
        status = "DRY_RUN"
        mode = "dry-run"
        generated_at = (Get-Date).ToString("o")
        repo_root = $repoRoot
        type_repo_root = $typeRoot
        package_path = $resolvedPackage
        output_dir = $outDirResolved
        lock_command = $lockCommand
        evidence = [ordered]@{
            native_ble_gatt = $nativeBleSummary
            post_ota_native_ble_gatt = $postOtaNativeBleSummary
            a1_a2 = if ($IncludeTypeHarness) { $a1Summary } else { $null }
            ble_ota = $bleSummary
            wired_flash = $wiredSummary
            type_ui = if ($IncludeTypeUiGate) { $typeUiSummary } else { $null }
            wireless_stack = $wirelessSummary
            manual_gate_report = $manualSummary
        }
        steps = $dryRunSteps
        errors = @()
    }
    $report | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $summaryJson -Encoding UTF8
    ConvertTo-HardwareAcceptanceMarkdown -Report $report | Set-Content -LiteralPath $summaryMd -Encoding UTF8
    Write-Host "DRY-RUN: Companion hardware acceptance runner is ready."
    Write-Host "Package: $resolvedPackage"
    Write-Host "Run with workflow hardware lock:"
    Write-Host "  $lockCommand"
    Write-Host "Summary: $summaryJson"
    exit 0
}

if (-not $WorkflowLockHeld) {
    Write-Host "Use the workflow hardware lock before executing:"
    Write-Host "  $lockCommand"
    throw "Refusing to run Companion hardware acceptance without -WorkflowLockHeld."
}

$startedAt = (Get-Date).ToUniversalTime().ToString("o")
if ($PromptOperator) {
    Show-OperatorPrompt `
        -Title "Companion 总体验收即将开始" `
        -Message "请确认 Companion 已接好 ST-LINK USB，电脑蓝牙可用，Companion-native host 工具可运行。点击 OK 后会依次做有线刷机、原生 BLE GATT 和蓝牙升级；过程中按后续弹窗操作，刷机或升级时不要拔线、不要断电。"
}

try {
    if ($SkipWirelessStackProvisioning) {
        $steps.Add([ordered]@{
            name = "ensure CPU2 BLE wireless stack"
            status = "SKIPPED"
            command = ConvertTo-CommandLine -FilePath "pwsh" -Arguments $wirelessArgs
            working_directory = $repoRoot
            exit_code = 0
            log = $null
            started_at = (Get-Date).ToString("o")
            ended_at = (Get-Date).ToString("o")
            duration_ms = 0
            message = "Skipped by -SkipWirelessStackProvisioning; caller must provide prior PASS wireless-stack evidence."
        }) | Out-Null
    } else {
        Invoke-AcceptanceStep -Name "ensure CPU2 BLE wireless stack" -WorkingDirectory $repoRoot -FilePath "pwsh" -Arguments $wirelessArgs
    }
    if (-not $programmer) {
        throw "STM32CubeProgrammer CLI not found for post-flash Companion app handoff reset. Pass -ProgrammerPath or set STM32CUBEPROGRAMMER_CLI."
    }
    Invoke-AcceptanceStep -Name "real Companion wired flash from same package" -WorkingDirectory $repoRoot -FilePath "pwsh" -Arguments $wiredArgs
    Invoke-AcceptanceStep -Name "post-flash Companion app handoff reset" -WorkingDirectory $repoRoot -FilePath "pwsh" -Arguments $postFlashResetArgs
    Invoke-AcceptanceStep -Name "real Companion-native BLE GATT bench validation" -WorkingDirectory $repoRoot -FilePath "python" -Arguments $nativeBleArgs
    if ($IncludeTypeHarness) {
        Invoke-AcceptanceStep -Name "legacy Type A1/A2 bench validation" -WorkingDirectory $repoRoot -FilePath "pwsh" -Arguments $a1Args
    }
    if ($IncludeTypeUiGate) {
        Invoke-AcceptanceStep -Name "Type temporary Companion debug page" -WorkingDirectory $repoRoot -FilePath "pwsh" -Arguments $typeUiArgs
    }
    Invoke-AcceptanceStep -Name "real Companion BLE OTA bench validation" -WorkingDirectory $repoRoot -FilePath "pwsh" -Arguments $bleArgs
    Invoke-AcceptanceStep -Name "post-OTA Companion-native BLE GATT bench validation" -WorkingDirectory $repoRoot -FilePath "python" -Arguments $postOtaNativeBleArgs
    Invoke-AcceptanceStep -Name "manual gate evidence verifier" -WorkingDirectory $repoRoot -FilePath "pwsh" -Arguments $manualArgs
} catch {
    $errors.Add($_.Exception.Message) | Out-Null
}

$finishedAt = (Get-Date).ToUniversalTime().ToString("o")
$status = if ($errors.Count -eq 0) { "PASS" } else { "FAIL" }
$report = [ordered]@{
    schema = "companion.hardware_acceptance.validation.v1"
    status = $status
    mode = "execute"
    started_at_utc = $startedAt
    finished_at_utc = $finishedAt
    repo_root = $repoRoot
    type_repo_root = $typeRoot
    package_path = $resolvedPackage
    output_dir = $outDirResolved
    lock_command = $lockCommand
    evidence = [ordered]@{
        native_ble_gatt = $nativeBleSummary
        post_ota_native_ble_gatt = $postOtaNativeBleSummary
        a1_a2 = if ($IncludeTypeHarness) { $a1Summary } else { $null }
        ble_ota = $bleSummary
        wired_flash = $wiredSummary
        type_ui = if ($IncludeTypeUiGate) { $typeUiSummary } else { $null }
        wireless_stack = $wirelessSummary
        manual_gate_report = $manualSummary
    }
    steps = @($steps)
    errors = @($errors)
}
$report | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $summaryJson -Encoding UTF8
ConvertTo-HardwareAcceptanceMarkdown -Report $report | Set-Content -LiteralPath $summaryMd -Encoding UTF8

Write-Host "companion_hardware_acceptance_result_json=$($report | ConvertTo-Json -Depth 12 -Compress)"
Write-Host "Summary: $summaryJson"
Write-Host "Markdown: $summaryMd"

if ($status -ne "PASS") {
    throw "Companion hardware acceptance failed. See $summaryJson"
}
