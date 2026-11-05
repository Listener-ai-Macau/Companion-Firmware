param(
    [switch] $CheckOnly,
    [switch] $Execute,
    [switch] $SelfTestEmptyCapture,
    [switch] $SelfTestResetTimeout,
    [switch] $SelfTestSerialOpenRetry,
    [switch] $WorkflowLockHeld,
    [string] $Port,
    [int] $BaudRate = 115200,
    [int] $Seconds = 15,
    [switch] $ResetAfterOpen,
    [string] $ReadySignalPath,
    [ValidateRange(5, 60)]
    [int] $ResetTimeoutSeconds = 15,
    [ValidateRange(1, 60)]
    [int] $SerialOpenRetrySeconds = 15,
    [string] $ProgrammerPath,
    [string] $ProgrammerRoot = "C:\ST\STM32CubeIDE_2.1.1\STM32CubeIDE\plugins",
    [switch] $PromptOperator,
    [int] $PromptTimeoutSeconds = 90,
    [string] $PromptTitle = "Companion NUCLEO 串口抓日志确认",
    [string] $PromptMessage,
    [string] $PromptExpectedText,
    [string] $PromptProgressText = "操作确认",
    [string] $PromptScopeText = "当前仅执行这一项人工操作；结果会和本次串口日志绑定。",
    [string] $PromptButtons = "通过,失败,跳过,中止",
    [string] $PromptResultPath,
    [string] $OutDir
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
. (Join-Path $PSScriptRoot "companion_wb55_lock.ps1")
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$outputDir = if ($OutDir) {
    New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
    (Resolve-Path -LiteralPath $OutDir).Path
} else {
    $path = Join-Path $repoRoot ".cache\validation\nucleo-serial-$stamp"
    New-Item -ItemType Directory -Force -Path $path | Out-Null
    (Resolve-Path -LiteralPath $path).Path
}
$rawLog = Join-Path $outputDir "nucleo-serial-raw.log"
$summaryJson = Join-Path $outputDir "nucleo-serial-summary.json"
$operatorPromptResultPath = if ($PromptResultPath) {
    [System.IO.Path]::GetFullPath($PromptResultPath)
} elseif ($PromptOperator) {
    Join-Path $outputDir "operator-prompt-observation.txt"
} else {
    $null
}
$script:operatorPromptSelection = $null
$script:operatorPromptBytesRead = 0
$operatorPromptText = if ([string]::IsNullOrWhiteSpace($PromptMessage)) {
    "等待屏幕回到日常待机表情后，完成本项操作。确认观察结果后，直接在此窗口选择通过、失败、跳过或中止；备注中的每一项都会进入后续 triage。"
} else {
    $PromptMessage
}
$operatorPromptExpectedText = if ([string]::IsNullOrWhiteSpace($PromptExpectedText)) {
    "本项的串口机器证据和你的真实观察必须一致；不确定或异常时选失败并写备注。"
} else {
    $PromptExpectedText
}
function Find-CubeProgrammerCli {
    param([string] $RequestedPath)

    $candidates = @()
    if ($RequestedPath) { $candidates += $RequestedPath }
    if ($env:STM32CUBEPROGRAMMER_CLI) { $candidates += $env:STM32CUBEPROGRAMMER_CLI }
    if ($env:STM32CUBEPROGRAMMER_PATH) { $candidates += (Join-Path $env:STM32CUBEPROGRAMMER_PATH "STM32_Programmer_CLI.exe") }
    if ($ProgrammerRoot) { $candidates += (Join-Path $ProgrammerRoot "**\STM32_Programmer_CLI.exe") }

    foreach ($commandName in @("STM32_Programmer_CLI.exe", "STM32_Programmer_CLI")) {
        $command = Get-Command $commandName -ErrorAction SilentlyContinue
        if ($command) { $candidates += $command.Source }
    }

    $candidates += @(
        "C:\ST\STM32CubeIDE_*\STM32CubeIDE\plugins\com.st.stm32cube.ide.mcu.externaltools.cubeprogrammer.win32_*\tools\bin\STM32_Programmer_CLI.exe",
        "C:\Program Files\STMicroelectronics\STM32CubeIDE_*\STM32CubeIDE\plugins\com.st.stm32cube.ide.mcu.externaltools.cubeprogrammer.win32_*\tools\bin\STM32_Programmer_CLI.exe",
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

function Get-SerialPortFromName {
    param([AllowNull()][string] $Name)

    if ([string]::IsNullOrWhiteSpace($Name)) { return $null }
    $match = [regex]::Match($Name, "\(COM(?<n>\d+)\)")
    if ($match.Success) { return "COM$($match.Groups["n"].Value)" }
    return $null
}

function Get-StLinkSerialCandidates {
    $rows = @()
    try {
        $devices = @(Get-CimInstance Win32_PnPEntity -ErrorAction Stop | Where-Object {
            $name = [string]$_.Name
            $desc = [string]$_.Description
            $manufacturer = [string]$_.Manufacturer
            $pnp = [string]$_.PNPDeviceID
            ($name -match "\(COM\d+\)") -and
                (($name + " " + $desc + " " + $manufacturer + " " + $pnp) -match "(?i)ST-LINK|STM32|STMicroelectronics|VID_0483")
        })
        foreach ($device in $devices) {
            $portName = Get-SerialPortFromName -Name ([string]$device.Name)
            if (-not $portName) { continue }
            $rows += [pscustomobject]@{
                port = $portName
                name = [string]$device.Name
                manufacturer = [string]$device.Manufacturer
                pnp_device_id = [string]$device.PNPDeviceID
                source = "Win32_PnPEntity"
            }
        }
    } catch {
        Write-Warning "Could not enumerate PnP serial devices: $($_.Exception.Message)"
    }

    return @($rows | Sort-Object port -Unique)
}

function Resolve-CapturePort {
    param([AllowNull()][string] $RequestedPort)

    $availablePorts = @([System.IO.Ports.SerialPort]::GetPortNames() | Sort-Object)
    $candidates = @(Get-StLinkSerialCandidates)

    if (-not [string]::IsNullOrWhiteSpace($RequestedPort)) {
        if ($availablePorts -notcontains $RequestedPort) {
            throw "Requested port '$RequestedPort' is not present. Present ports: $($availablePorts -join ', ')"
        }
        return [pscustomobject]@{
            port = $RequestedPort
            candidates = $candidates
            available_ports = $availablePorts
            auto_detected = $false
        }
    }

    if ($candidates.Count -eq 1) {
        return [pscustomobject]@{
            port = [string]$candidates[0].port
            candidates = $candidates
            available_ports = $availablePorts
            auto_detected = $true
        }
    }

    if ($candidates.Count -eq 0) {
        throw "No ST-LINK/STM32 VCP COM port found. Present ports: $($availablePorts -join ', '). Pass -Port COMx after checking Windows Device Manager."
    }

    $candidateLines = ($candidates | ForEach-Object { "$($_.port): $($_.name)" }) -join "; "
    throw "Multiple ST-LINK/STM32 VCP COM ports found. Pass -Port COMx explicitly. Candidates: $candidateLines"
}

function Resolve-WorkflowAiwPath {
    $roots = @()
    if ($env:AI_WORKFLOW_REPO) { $roots += $env:AI_WORKFLOW_REPO }
    $roots += "C:\Users\Billy\Desktop\Denzic\ai-collaboration-workflow"
    foreach ($root in $roots) {
        $candidate = Join-Path $root "scripts\aiw.ps1"
        if (Test-Path -LiteralPath $candidate) { return (Resolve-Path -LiteralPath $candidate).Path }
    }
    throw "The canonical aiw operator-prompt helper was not found. Set AI_WORKFLOW_REPO or restore ai-collaboration-workflow."
}

function Show-OperatorPrompt {
    param(
        [Parameter(Mandatory = $true)][string] $Title,
        [Parameter(Mandatory = $true)][string] $Message,
        [Parameter(Mandatory = $true)][System.IO.Ports.SerialPort] $SerialPort
    )

    $aiwPath = Resolve-WorkflowAiwPath
    $pwshPath = (Get-Command pwsh -ErrorAction Stop).Source
    $arguments = @(
        "-NoProfile", "-File", $aiwPath, "operator-prompt",
        "-Title", $Title,
        "-ProgressText", $PromptProgressText,
        "-ScopeText", $PromptScopeText,
        "-Message", $Message,
        "-ExpectedText", $operatorPromptExpectedText,
        "-Input",
        "-ReviewStyle",
        "-Buttons", $PromptButtons,
        "-OutputPath", $operatorPromptResultPath,
        "-TimeoutSeconds", "$PromptTimeoutSeconds",
        "-Json"
    )
    $startInfo = [System.Diagnostics.ProcessStartInfo]::new()
    $startInfo.FileName = $pwshPath
    $startInfo.UseShellExecute = $false
    $startInfo.RedirectStandardOutput = $true
    $startInfo.RedirectStandardError = $true
    # Windows PowerShell 5.1 ProcessStartInfo has no ArgumentList; prefer it on
    # modern runtimes, fall back to a quoted Arguments string otherwise.
    $hasArgumentList = $null -ne ($startInfo.PSObject.Properties['ArgumentList'])
    if ($hasArgumentList) {
        try {
            foreach ($argument in $arguments) {
                [void]$startInfo.ArgumentList.Add([string]$argument)
            }
        } catch {
            $hasArgumentList = $false
        }
    }
    if (-not $hasArgumentList) {
        $quoted = foreach ($argument in $arguments) {
            $text = [string]$argument
            if ($text -match '[\s"]') {
                '"' + ($text -replace '"', '\"') + '"'
            } else {
                $text
            }
        }
        $startInfo.Arguments = [string]::Join(' ', $quoted)
    }
    $promptProcess = [System.Diagnostics.Process]::Start($startInfo)
    while (-not $promptProcess.HasExited) {
        try {
            $script:operatorPromptBytesRead +=
                Read-SerialAvailable -SerialPort $SerialPort
        } catch [TimeoutException] {
        }
        Start-Sleep -Milliseconds 100
    }
    $promptOutput = $promptProcess.StandardOutput.ReadToEnd()
    $promptError = $promptProcess.StandardError.ReadToEnd()
    if ($promptProcess.ExitCode -ne 0) {
        throw "Canonical operator-prompt failed with exit code $($promptProcess.ExitCode): $promptError"
    }
    $promptResult = $promptOutput | ConvertFrom-Json
    $script:operatorPromptSelection = [string]$promptResult.selected
}

function Write-Summary {
    param(
        [Parameter(Mandatory = $true)][string] $Status,
        [AllowNull()][string] $PortName,
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][object[]] $Candidates,
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][string[]] $AvailablePorts,
        [int] $BytesRead,
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][string[]] $Errors,
        [Parameter(Mandatory = $true)][string] $Mode
    )

    $summary = [ordered]@{
        schema = "companion.nucleo_serial.capture.v1"
        status = $Status
        mode = $Mode
        generated_at = (Get-Date).ToString("o")
        port = $PortName
        baud_rate = $BaudRate
        seconds = $Seconds
        reset_after_open = [bool]$ResetAfterOpen
        reset_timeout_seconds = $ResetTimeoutSeconds
        serial_open_retry_seconds = $SerialOpenRetrySeconds
        serial_open_attempts = $script:serialOpenAttempts
        prompt_operator = [bool]$PromptOperator
        prompt_title = $PromptTitle
        prompt_message = if ($PromptOperator) { $operatorPromptText } else { $null }
        prompt_expected_text = if ($PromptOperator) { $operatorPromptExpectedText } else { $null }
        prompt_style = if ($PromptOperator) { "aiw_operator_prompt_v1" } else { $null }
        prompt_progress_text = if ($PromptOperator) { $PromptProgressText } else { $null }
        prompt_scope_text = if ($PromptOperator) { $PromptScopeText } else { $null }
        prompt_buttons = if ($PromptOperator) { $PromptButtons } else { $null }
        prompt_result_path = $operatorPromptResultPath
        prompt_selection = $script:operatorPromptSelection
        raw_log = $rawLog
        candidates = @($Candidates)
        available_ports = @($AvailablePorts)
        bytes_read = $BytesRead
        errors = @($Errors)
    }
    $summary | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $summaryJson -Encoding UTF8
    Write-Output "companion_nucleo_serial_result_json=$($summary | ConvertTo-Json -Depth 8 -Compress)"
    Write-Output "Summary: $summaryJson"
}

function Read-SerialAvailable {
    param([Parameter(Mandatory = $true)][System.IO.Ports.SerialPort] $SerialPort)

    $text = $SerialPort.ReadExisting()
    if ($text.Length -le 0) { return 0 }
    Write-Host -NoNewline $text
    Add-Content -LiteralPath $rawLog -Value $text -NoNewline
    return [System.Text.Encoding]::UTF8.GetByteCount($text)
}

function Open-SerialWithRetry {
    param(
        [Parameter(Mandatory = $true)][scriptblock] $OpenAction,
        [Parameter(Mandatory = $true)][string] $PortName,
        [Parameter(Mandatory = $true)][int] $RetrySeconds
    )

    $deadline = [DateTime]::UtcNow.AddSeconds($RetrySeconds)
    $lastError = $null
    $attempts = 0
    while ($true) {
        $attempts++
        try {
            & $OpenAction
            $script:serialOpenAttempts = $attempts
            return
        } catch [System.IO.IOException] {
            $lastError = $_.Exception.Message
        } catch [System.UnauthorizedAccessException] {
            $lastError = $_.Exception.Message
        }
        if ([DateTime]::UtcNow -ge $deadline) {
            $script:serialOpenAttempts = $attempts
            throw "Could not open serial port $PortName after $attempts attempt(s) across $RetrySeconds second(s): $lastError"
        }
        Start-Sleep -Milliseconds 250
    }
}

function Invoke-ProgrammerResetWithTimeout {
    param(
        [Parameter(Mandatory = $true)][string] $Programmer,
        [Parameter(Mandatory = $true)][string[]] $Arguments,
        [Parameter(Mandatory = $true)][int] $TimeoutSeconds
    )

    $resetStdout = Join-Path $outputDir "stm32-reset-stdout.log"
    $resetStderr = Join-Path $outputDir "stm32-reset-stderr.log"
    $resetLine = "RUN: $Programmer $($Arguments -join ' ')"
    # The caller captures this function's only success-stream value as the
    # programmer exit code, so keep diagnostics on the information stream.
    Write-Host $resetLine
    Write-Host "RUN: reset_timeout_seconds=$TimeoutSeconds"
    Add-Content -LiteralPath $rawLog -Value $resetLine
    Add-Content -LiteralPath $rawLog -Value "RUN: reset_timeout_seconds=$TimeoutSeconds"
    $process = Start-Process `
        -FilePath $Programmer `
        -ArgumentList $Arguments `
        -RedirectStandardOutput $resetStdout `
        -RedirectStandardError $resetStderr `
        -WindowStyle Hidden `
        -PassThru
    $completed = $process.WaitForExit($TimeoutSeconds * 1000)
    if (-not $completed) {
        Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
        if (Test-Path -LiteralPath $resetStdout) {
            Get-Content -LiteralPath $resetStdout | ForEach-Object {
                Write-Host $_
                Add-Content -LiteralPath $rawLog -Value ([string]$_)
            }
        }
        if (Test-Path -LiteralPath $resetStderr) {
            Get-Content -LiteralPath $resetStderr | ForEach-Object {
                Write-Host $_
                Add-Content -LiteralPath $rawLog -Value ([string]$_)
            }
        }
        throw "reset timed out after $TimeoutSeconds second(s). stdout=$resetStdout stderr=$resetStderr"
    }
    $process.WaitForExit()
    if (Test-Path -LiteralPath $resetStdout) {
        Get-Content -LiteralPath $resetStdout | ForEach-Object {
            Write-Host $_
            Add-Content -LiteralPath $rawLog -Value ([string]$_)
        }
    }
    if (Test-Path -LiteralPath $resetStderr) {
        Get-Content -LiteralPath $resetStderr | ForEach-Object {
            Write-Host $_
            Add-Content -LiteralPath $rawLog -Value ([string]$_)
        }
    }
    Write-Host "RUN: reset_stdout=$resetStdout"
    Write-Host "RUN: reset_stderr=$resetStderr"
    return [int]$process.ExitCode
}

$resolved = $null
$programmer = Find-CubeProgrammerCli -RequestedPath $ProgrammerPath
$errors = [System.Collections.Generic.List[string]]::new()
$bytesRead = 0
$script:serialOpenAttempts = 0

if ($SelfTestEmptyCapture) {
    if ($CheckOnly -or $Execute -or $SelfTestResetTimeout -or $SelfTestSerialOpenRetry) {
        throw "Use only one of -CheckOnly, -Execute, -SelfTestEmptyCapture, -SelfTestResetTimeout, or -SelfTestSerialOpenRetry."
    }
    "" | Set-Content -LiteralPath $rawLog -Encoding UTF8
    $errors.Add("No serial bytes captured during $Seconds second(s); refusing empty runtime evidence.") | Out-Null
    Write-Summary -Status "FAIL" -PortName "SELFTEST" -Candidates @() -AvailablePorts @() -BytesRead 0 -Errors @($errors) -Mode "selftest-empty-capture"
    throw "Companion NUCLEO serial capture empty-log self-test failed as expected. See $summaryJson"
}

if ($SelfTestResetTimeout) {
    if ($CheckOnly -or $Execute -or $SelfTestEmptyCapture -or $SelfTestSerialOpenRetry) {
        throw "Use only one of -CheckOnly, -Execute, -SelfTestEmptyCapture, -SelfTestResetTimeout, or -SelfTestSerialOpenRetry."
    }
    "" | Set-Content -LiteralPath $rawLog -Encoding UTF8
    try {
        $stubArgs = @("-NoProfile", "-Command", "Start-Sleep -Seconds 30")
        Invoke-ProgrammerResetWithTimeout -Programmer "pwsh" -Arguments $stubArgs -TimeoutSeconds 5 | Out-Null
    } catch {
        $errors.Add($_.Exception.Message) | Out-Null
    }
    Write-Summary -Status "FAIL" -PortName "SELFTEST" -Candidates @() -AvailablePorts @() -BytesRead 0 -Errors @($errors) -Mode "selftest-reset-timeout"
    throw "Companion NUCLEO serial reset-timeout self-test failed as expected. See $summaryJson"
}

if ($SelfTestSerialOpenRetry) {
    if ($CheckOnly -or $Execute -or $SelfTestEmptyCapture -or $SelfTestResetTimeout) {
        throw "Use only one of -CheckOnly, -Execute, -SelfTestEmptyCapture, -SelfTestResetTimeout, or -SelfTestSerialOpenRetry."
    }
    $script:simulatedSerialOpenAttempts = 0
    Open-SerialWithRetry -PortName "SELFTEST" -RetrySeconds 1 -OpenAction {
        $script:simulatedSerialOpenAttempts++
        if ($script:simulatedSerialOpenAttempts -lt 3) {
            throw [System.IO.IOException]::new("simulated temporary VCP absence")
        }
    }
    if ($script:simulatedSerialOpenAttempts -ne 3 -or $script:serialOpenAttempts -ne 3) {
        throw "Serial-open retry self-test did not make exactly three attempts."
    }
    "serial-open retry self-test passed after $script:simulatedSerialOpenAttempts attempts" | Set-Content -LiteralPath $rawLog -Encoding UTF8
    Write-Summary -Status "PASS" -PortName "SELFTEST" -Candidates @() -AvailablePorts @() -BytesRead 0 -Errors @() -Mode "selftest-serial-open-retry"
    exit 0
}

try {
    $resolved = Resolve-CapturePort -RequestedPort $Port
} catch {
    $errors.Add($_.Exception.Message) | Out-Null
    $available = @([System.IO.Ports.SerialPort]::GetPortNames() | Sort-Object)
    Write-Summary -Status "FAIL" -PortName $Port -Candidates @() -AvailablePorts $available -BytesRead 0 -Errors @($errors) -Mode "resolve-port"
    throw
}

if ($CheckOnly -and -not $Execute) {
    if ($PromptOperator) {
        Write-Output "CHECK: Canonical operator prompt: $(Resolve-WorkflowAiwPath)"
        Write-Output "CHECK: Prompt result path: $operatorPromptResultPath"
    }
    Write-Output "CHECK: Selected port: $($resolved.port)"
    Write-Output "CHECK: Auto detected: $($resolved.auto_detected)"
    Write-Output "CHECK: Present ports: $($resolved.available_ports -join ', ')"
    Write-Output "CHECK: Blocking operator prompt: $([bool]$PromptOperator)"
    if ($PromptOperator) {
        Write-Output "CHECK: Final review buttons: $PromptButtons"
    }
    Write-Output "CHECK: Reset timeout seconds: $ResetTimeoutSeconds"
    foreach ($candidate in @($resolved.candidates)) {
        Write-Output "CHECK: ST-LINK candidate $($candidate.port): $($candidate.name)"
    }
    Write-Output "CHECK: STM32CubeProgrammer CLI found: $([bool]$programmer)"
    if ($programmer) { Write-Output "CHECK: Programmer: $programmer" }
    Write-Output "CHECK: Real serial capture acquires the Companion-WB55 exclusive mutex and writes a lock-evidence artifact."
    Write-Output "CHECK: Add -PromptOperator only when the capture is waiting for a real human action or observation."
    Write-Summary -Status "DRY-RUN" -PortName $resolved.port -Candidates @($resolved.candidates) -AvailablePorts @($resolved.available_ports) -BytesRead 0 -Errors @() -Mode "check-only"
    exit 0
}

if (-not $Execute) {
    throw "Refusing to open Companion NUCLEO serial port without -Execute. Use -CheckOnly for dry-run output."
}

if ($ResetAfterOpen -and -not $programmer) {
    throw "STM32CubeProgrammer CLI not found. Pass -ProgrammerPath, set STM32CUBEPROGRAMMER_CLI, or omit -ResetAfterOpen."
}

$hardwareLock = $null
try {
    $hardwareLock = Enter-CompanionWb55Lock -Purpose "serial capture $($resolved.port)"
    Write-Output "LOCK: Companion-WB55 $($hardwareLock.mode) run=$($hardwareLock.run_id)"
} catch {
    $errors.Add($_.Exception.Message) | Out-Null
    Write-Summary -Status "FAIL" -PortName $resolved.port -Candidates @($resolved.candidates) -AvailablePorts @($resolved.available_ports) -BytesRead 0 -Errors @($errors) -Mode "lock"
    throw
}

$serial = $null

try {
    $serial = [System.IO.Ports.SerialPort]::new($resolved.port, $BaudRate, [System.IO.Ports.Parity]::None, 8, [System.IO.Ports.StopBits]::One)
    $serial.ReadTimeout = 250
    $serial.NewLine = "`n"
    "" | Set-Content -LiteralPath $rawLog -Encoding UTF8
    Open-SerialWithRetry -PortName $resolved.port -RetrySeconds $SerialOpenRetrySeconds -OpenAction {
        $serial.Open()
    }
    $serial.DiscardInBuffer()
    $serial.DiscardOutBuffer()
    if (-not [string]::IsNullOrWhiteSpace($ReadySignalPath)) {
        $readyParent = Split-Path -Parent ([System.IO.Path]::GetFullPath($ReadySignalPath))
        if (-not [string]::IsNullOrWhiteSpace($readyParent)) {
            New-Item -ItemType Directory -Force -Path $readyParent | Out-Null
        }
        [ordered]@{
            schema_id = "companion.nucleo.serial_ready.v1"
            status = "READY"
            port = $resolved.port
            process_id = $PID
            ready_at = (Get-Date).ToUniversalTime().ToString("o")
        } | ConvertTo-Json | Set-Content -LiteralPath $ReadySignalPath -Encoding UTF8
    }
    if ($ResetAfterOpen) {
        $resetArgs = @("-c", "port=SWD", "mode=UR", "reset=HWrst", "freq=4000", "-rst")
        $resetExitCode = Invoke-ProgrammerResetWithTimeout -Programmer $programmer -Arguments $resetArgs -TimeoutSeconds $ResetTimeoutSeconds
        if ($resetExitCode -ne 0) {
            throw "reset failed with exit code $resetExitCode"
        }
    }

    if ($PromptOperator) {
        if ($ResetAfterOpen) {
            # Keep the first boot/Stop evidence needed by a focused wake check.
            $bootDeadline = [DateTime]::UtcNow.AddSeconds(5)
            while ([DateTime]::UtcNow -lt $bootDeadline) {
                try {
                    $bytesRead += Read-SerialAvailable -SerialPort $serial
                } catch [TimeoutException] {
                }
                Start-Sleep -Milliseconds 100
            }
        }
        Show-OperatorPrompt -Title $PromptTitle -Message $operatorPromptText `
            -SerialPort $serial
        $bytesRead += $script:operatorPromptBytesRead
    }

    # The final review window stays open while the operator performs the action.
    # Its closed serial buffer contains the focused touch/result burst, then the
    # bounded drain below records the response without opening a second popup.
    $deadline = [DateTime]::UtcNow.AddSeconds($Seconds)
    while ([DateTime]::UtcNow -lt $deadline) {
        try {
            $bytesRead += Read-SerialAvailable -SerialPort $serial
        } catch [TimeoutException] {
        }
        Start-Sleep -Milliseconds 100
    }
} catch {
    $errors.Add($_.Exception.Message) | Out-Null
} finally {
    if ($serial -and $serial.IsOpen) {
        $serial.Close()
    }
    if ($serial) {
        $serial.Dispose()
    }
    if ($hardwareLock) {
        Exit-CompanionWb55Lock
    }
}

if ($errors.Count -eq 0 -and $bytesRead -le 0) {
    $errors.Add("No serial bytes captured during $Seconds second(s); refusing empty runtime evidence.") | Out-Null
}

$status = if ($errors.Count -eq 0) { "PASS" } else { "FAIL" }
Write-Summary -Status $status -PortName $resolved.port -Candidates @($resolved.candidates) -AvailablePorts @($resolved.available_ports) -BytesRead $bytesRead -Errors @($errors) -Mode "capture"
if ($status -ne "PASS") {
    throw "Companion NUCLEO serial capture failed. See $summaryJson"
}
