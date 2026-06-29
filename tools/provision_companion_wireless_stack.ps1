param(
    [switch] $CheckOnly,
    [switch] $Execute,
    [switch] $WorkflowLockHeld,
    [switch] $ReadFusInfo,
    [switch] $InstallBleStack,
    [string] $ProgrammerPath,
    [string] $Port = "SWD",
    [switch] $PromptOperator,
    [int] $PromptTimeoutSeconds = 90,
    [string] $OutDir
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$bleStackRelative = "third_party\STM32CubeWB\Projects\STM32WB_Copro_Wireless_Binaries\STM32WB5x\stm32wb5x_BLE_Stack_full_fw.bin"
$releaseNotesRelative = "third_party\STM32CubeWB\Projects\STM32WB_Copro_Wireless_Binaries\STM32WB5x\Release_Notes.html"
$bleStackBinary = Join-Path $repoRoot $bleStackRelative
$releaseNotes = Join-Path $repoRoot $releaseNotesRelative

$installAddress = "0x080D0000"
$fusInfoAddress = "0x20030030"
$fusFallbackAddress = "0x20010010"
$connectArgs = @("port=$Port", "mode=UR", "reset=HWrst", "freq=4000")
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$outputDir = if ($OutDir) {
    New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
    (Resolve-Path -LiteralPath $OutDir).Path
} else {
    $path = Join-Path $repoRoot ".cache\validation\companion-wireless-stack-$stamp"
    New-Item -ItemType Directory -Force -Path $path | Out-Null
    (Resolve-Path -LiteralPath $path).Path
}
$rawLog = Join-Path $outputDir "companion-wireless-stack-raw.log"
$summaryJson = Join-Path $outputDir "companion-wireless-stack-summary.json"
$summaryMd = Join-Path $outputDir "companion-wireless-stack-summary.md"

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

function Assert-Path {
    param(
        [Parameter(Mandatory = $true)][string] $Path,
        [Parameter(Mandatory = $true)][string] $Label
    )

    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "Missing $Label`: $Path. Run tools\bootstrap_stm32cubewb.ps1 first."
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
        $popup = New-Object -ComObject WScript.Shell
        $result = $popup.Popup($Message, $PromptTimeoutSeconds, $Title, 49)
        if ($result -ne 1) {
            throw "Operator cancelled Companion wireless-stack action."
        }
    } catch {
        if ($_.Exception.Message -eq "Operator cancelled Companion wireless-stack action.") { throw }
        Write-Warning "Could not show desktop prompt: $($_.Exception.Message)"
        Write-Output $Title
        Write-Output $Message
        $answer = Read-Host "输入 OK 继续，其他内容取消"
        if ($answer -ne "OK") {
            throw "Operator cancelled Companion wireless-stack action."
        }
    }
}

function Invoke-Programmer {
    param(
        [Parameter(Mandatory = $true)][string] $Programmer,
        [Parameter(Mandatory = $true)][string[]] $Arguments,
        [Parameter(Mandatory = $true)][string] $Label,
        [switch] $AllowFailure
    )

    $line = "RUN: $Programmer $($Arguments -join ' ')"
    Write-Host ""
    Write-Host $line
    Add-Content -LiteralPath $rawLog -Value ""
    Add-Content -LiteralPath $rawLog -Value $line
    $output = & $Programmer @Arguments 2>&1
    $exitCode = $LASTEXITCODE
    $output | ForEach-Object {
        $text = [string]$_
        Write-Host $text
        Add-Content -LiteralPath $rawLog -Value $text
    }
    if ($exitCode -ne 0 -and -not $AllowFailure) {
        throw "$Label failed with exit code $exitCode."
    }
    return [pscustomobject]@{
        label = $Label
        command = $line
        exit_code = $exitCode
        output = ($output -join [Environment]::NewLine)
    }
}

function Get-FusWordFromText {
    param([string] $Text)

    $matches = [regex]::Matches($Text, "(?i)\b(?:0x)?([0-9a-f]{8})\b")
    foreach ($match in $matches) {
        $value = $match.Groups[1].Value.ToUpperInvariant()
        if ($value -match "^(00050300|010[0-9A-F]0[0-9A-F]00|01020[0-9A-F]00|02020[0-9A-F]00)$") {
            return $value
        }
    }
    return $null
}

function Get-FusClassification {
    param([AllowNull()][string] $Word)

    if ([string]::IsNullOrWhiteSpace($Word)) {
        return "unknown"
    }
    if ($Word -eq "00050300") {
        return "fus_v0_5_3_needs_1_2_0_first"
    }
    if ($Word -match "^010[0-1]0[0-9A-F]00$") {
        return "fus_v1_x_needs_1_2_0_first"
    }
    if ($Word -match "^01020[0-9A-F]00$") {
        return "fus_v1_2_needs_latest_fus"
    }
    if ($Word -match "^02020[0-9A-F]00$") {
        return "fus_v2_2_ready_for_wireless_stack"
    }
    return "unknown"
}

function Write-Summary {
    param(
        [Parameter(Mandatory = $true)][string] $Status,
        [AllowNull()][string] $FusWord,
        [AllowNull()][string] $FusSource,
        [Parameter(Mandatory = $true)][string] $FusClass,
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][object[]] $Steps,
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][string[]] $Errors,
        [Parameter(Mandatory = $true)][string] $Mode
    )

    $summary = [ordered]@{
        schema = "companion.wb55_wireless_stack.provisioning.v1"
        status = $Status
        mode = $Mode
        generated_at = (Get-Date).ToString("o")
        programmer = $programmer
        port = $Port
        ble_stack_binary = $bleStackBinary
        ble_stack_sha256 = if (Test-Path -LiteralPath $bleStackBinary -PathType Leaf) { (Get-FileHash -LiteralPath $bleStackBinary -Algorithm SHA256).Hash.ToLowerInvariant() } else { $null }
        install_address = $installAddress
        install_address_source = "$releaseNotesRelative Wireless Coprocessor Binary Table, STM32WB5xxG(1M), V1.24.0, FUS_v2 only"
        connect_args = $connectArgs
        prompt_operator = [bool]$PromptOperator
        fus_word = $FusWord
        fus_word_source = $FusSource
        fus_classification = $FusClass
        raw_log = $rawLog
        steps = @($Steps)
        errors = @($Errors)
    }
    $summary | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $summaryJson -Encoding UTF8

    $md = @(
        "# Companion WB55 Wireless Stack Provisioning",
        "",
        "- Status: $Status",
        "- Mode: $Mode",
        "- BLE stack: ``$bleStackRelative``",
        "- Install address: ``$installAddress``",
        "- Install address source: current STM32CubeWB v1.24.0 Release_Notes Wireless Coprocessor Binary Table, STM32WB5xxG(1M), FUS_v2 only",
        "- FUS word: $FusWord",
        "- FUS classification: $FusClass",
        "- Raw log: ``$rawLog``"
    )
    if ($Errors.Count -gt 0) {
        $md += ""
        $md += "## Errors"
        foreach ($errorItem in $Errors) {
            $md += "- $errorItem"
        }
    }
    $md | Set-Content -LiteralPath $summaryMd -Encoding UTF8
    Write-Output "companion_wireless_stack_result_json=$($summary | ConvertTo-Json -Depth 8 -Compress)"
    Write-Output "Summary: $summaryJson"
}

$programmer = Find-CubeProgrammerCli -RequestedPath $ProgrammerPath
$lockReadCommand = "pwsh -NoProfile -File C:\Users\Billy\Desktop\Denzic\ai-collaboration-workflow\scripts\aiw.ps1 with-lock -Resource Companion-WB55 -Purpose `"Companion WB55 FUS diagnostic`" -Run pwsh -NoProfile -File .\tools\provision_companion_wireless_stack.ps1 -Execute -WorkflowLockHeld -ReadFusInfo"
$lockInstallCommand = "pwsh -NoProfile -File C:\Users\Billy\Desktop\Denzic\ai-collaboration-workflow\scripts\aiw.ps1 with-lock -Resource Companion-WB55 -Purpose `"Companion WB55 BLE stack provisioning`" -Run pwsh -NoProfile -File .\tools\provision_companion_wireless_stack.ps1 -Execute -WorkflowLockHeld -InstallBleStack"

if (-not $ReadFusInfo -and -not $InstallBleStack) {
    $CheckOnly = $true
}

Assert-Path -Path $bleStackBinary -Label "WB55 BLE full stack binary"
Assert-Path -Path $releaseNotes -Label "STM32CubeWB Release_Notes.html"

if ($CheckOnly -and -not $Execute) {
    Write-Output "CHECK: STM32CubeProgrammer CLI found: $([bool]$programmer)"
    if ($programmer) { Write-Output "CHECK: Programmer: $programmer" }
    Write-Output "CHECK: BLE stack binary: $bleStackRelative"
    Write-Output "CHECK: BLE stack SHA256: $((Get-FileHash -LiteralPath $bleStackBinary -Algorithm SHA256).Hash.ToLowerInvariant())"
    Write-Output "CHECK: Install address: $installAddress"
    Write-Output "CHECK: Install address source: $releaseNotesRelative Wireless Coprocessor Binary Table, STM32WB5xxG(1M), V1.24.0, FUS_v2 only"
    Write-Output "CHECK: Connect args: $($connectArgs -join ' ')"
    Write-Output "CHECK: FUS read command: STM32_Programmer_CLI.exe -c $($connectArgs -join ' ') -startfus ; STM32_Programmer_CLI.exe -c $($connectArgs -join ' ') -r32 $fusInfoAddress 1"
    Write-Output "CHECK: BLE stack install command: STM32_Programmer_CLI.exe -c $($connectArgs -join ' ') -fwupgrade $bleStackRelative $installAddress firstinstall=0"
    Write-Output "CHECK: Blocking operator prompt: $([bool]$PromptOperator)"
    Write-Output "CHECK: Add -PromptOperator only when the wireless-stack operation is waiting for a real human action or observation."
    Write-Output "CHECK: Real hardware commands must run inside workflow lock:"
    Write-Output "  $lockReadCommand"
    Write-Output "  $lockInstallCommand"
    Write-Summary -Status "DRY-RUN" -FusWord $null -FusSource $null -FusClass "not_read" -Steps @() -Errors @() -Mode "check-only"
    exit 0
}

if (-not $Execute) {
    throw "Refusing to touch Companion WB55 hardware without -Execute. Use -CheckOnly for dry-run output."
}

if (-not $WorkflowLockHeld) {
    throw "Refusing to touch Companion WB55 hardware without workflow lock acknowledgement. Run through aiw with-lock -Resource Companion-WB55 and pass -WorkflowLockHeld inside the locked command."
}

$steps = [System.Collections.Generic.List[object]]::new()
$errors = [System.Collections.Generic.List[string]]::new()
$fusWord = $null
$fusSource = $null
$fusClass = "unknown"
$status = "PASS"
$mode = if ($InstallBleStack) { "install-ble-stack" } else { "read-fus-info" }

if (-not $programmer) {
    throw "STM32CubeProgrammer CLI not found. Install STM32CubeProgrammer, add STM32_Programmer_CLI.exe to PATH, or pass -ProgrammerPath."
}

$actionText = if ($InstallBleStack) { "安装/更新 CPU2 BLE full stack" } else { "读取 FUS 状态" }
if ($PromptOperator) {
    try {
        Show-OperatorPrompt -Title "Companion WB55 无线栈操作确认" -Message "请确认 NUCLEO-WB55RG 已通过板载 ST-LINK USB 接好，Type/串口监视器/其它刷机工具已停止占用设备。点击 OK 后会检查或安装蓝牙无线栈；安装过程中不要拔线、不要断电。点击 Cancel 取消。"
    } catch {
        $status = "CANCELLED"
        $errors.Add($_.Exception.Message) | Out-Null
        Write-Summary -Status $status -FusWord $fusWord -FusSource $fusSource -FusClass $fusClass -Steps @($steps) -Errors @($errors) -Mode $mode
        throw "Companion WB55 wireless stack action cancelled before hardware access. See $summaryJson"
    }
}

try {
    $steps.Add((Invoke-Programmer -Programmer $programmer -Arguments (@("-c") + $connectArgs + @("-startfus")) -Label "start FUS")) | Out-Null

    $primaryRead = Invoke-Programmer -Programmer $programmer -Arguments (@("-c") + $connectArgs + @("-r32", $fusInfoAddress, "1")) -Label "read FUS version at $fusInfoAddress" -AllowFailure
    $steps.Add($primaryRead) | Out-Null
    if ($primaryRead.exit_code -eq 0) {
        $fusWord = Get-FusWordFromText -Text $primaryRead.output
        if ($fusWord) { $fusSource = $fusInfoAddress }
    }

    if (-not $fusWord) {
        $fallbackRead = Invoke-Programmer -Programmer $programmer -Arguments (@("-c") + $connectArgs + @("-r32", $fusFallbackAddress, "1")) -Label "read FUS version at $fusFallbackAddress" -AllowFailure
        $steps.Add($fallbackRead) | Out-Null
        if ($fallbackRead.exit_code -eq 0) {
            $fusWord = Get-FusWordFromText -Text $fallbackRead.output
            if ($fusWord) { $fusSource = $fusFallbackAddress }
        }
    }

    $fusClass = Get-FusClassification -Word $fusWord

    if ($InstallBleStack) {
        if ($fusClass -ne "fus_v2_2_ready_for_wireless_stack") {
            throw "FUS word '$fusWord' classified as '$fusClass'. This script will not auto-upgrade FUS; follow ST incremental FUS upgrade steps first."
        }

        $steps.Add((Invoke-Programmer -Programmer $programmer -Arguments (@("-c") + $connectArgs + @("-fwupgrade", $bleStackBinary, $installAddress, "firstinstall=0")) -Label "install stm32wb5x_BLE_Stack_full_fw.bin")) | Out-Null
        $steps.Add((Invoke-Programmer -Programmer $programmer -Arguments (@("-c") + $connectArgs + @("-ob", "nSWboot0=1", "nboot1=1", "nboot0=1")) -Label "restore default option-byte boot configuration")) | Out-Null
        $steps.Add((Invoke-Programmer -Programmer $programmer -Arguments (@("-c") + $connectArgs + @("-rst")) -Label "reset after BLE stack install" -AllowFailure)) | Out-Null
    }
} catch {
    $status = "FAIL"
    $errors.Add($_.Exception.Message) | Out-Null
}

Write-Summary -Status $status -FusWord $fusWord -FusSource $fusSource -FusClass $fusClass -Steps @($steps) -Errors @($errors) -Mode $mode

if ($status -ne "PASS") {
    throw "Companion WB55 wireless stack provisioning failed. See $summaryJson"
}
