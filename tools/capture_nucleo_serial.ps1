param(
    [switch] $CheckOnly,
    [switch] $Execute,
    [switch] $SelfTestEmptyCapture,
    [switch] $SelfTestResetTimeout,
    [switch] $WorkflowLockHeld,
    [string] $Port,
    [int] $BaudRate = 115200,
    [int] $Seconds = 15,
    [switch] $ResetAfterOpen,
    [ValidateRange(5, 60)]
    [int] $ResetTimeoutSeconds = 15,
    [string] $ProgrammerPath,
    [string] $ProgrammerRoot = "C:\ST\STM32CubeIDE_2.1.1\STM32CubeIDE\plugins",
    [switch] $PromptOperator,
    [int] $PromptTimeoutSeconds = 90,
    [string] $PromptTitle = "Companion NUCLEO 串口抓日志确认",
    [string] $PromptMessage,
    [string] $OutDir
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
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
$operatorPromptText = if ([string]::IsNullOrWhiteSpace($PromptMessage)) {
    "请确认 NUCLEO-WB55RG 已通过板载 ST-LINK USB 接好，Type/其它串口监视器已停止占用设备。请保持此窗口打开并完成本次操作；点击 OK 后会收集操作期间的设备日志$(if ($ResetAfterOpen) { '，目标板已先复位' } else { '' })。点击 Cancel 取消。"
} else {
    $PromptMessage
}
$lockCommand = "pwsh -NoProfile -File C:\Users\Billy\Desktop\Denzic\ai-collaboration-workflow\scripts\aiw.ps1 with-lock -Resource Companion-WB55 -Purpose `"Companion NUCLEO serial capture`" -Run pwsh -NoProfile -File .\tools\capture_nucleo_serial.ps1 -Execute -WorkflowLockHeld -Seconds $Seconds -ResetAfterOpen"

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
            throw "Operator cancelled Companion NUCLEO serial capture."
        }
    } catch {
        if ($_.Exception.Message -eq "Operator cancelled Companion NUCLEO serial capture.") { throw }
        Write-Warning "Could not show desktop prompt: $($_.Exception.Message)"
        Write-Output $Title
        Write-Output $Message
        $answer = Read-Host "输入 OK 继续抓日志，其他内容取消"
        if ($answer -ne "OK") {
            throw "Operator cancelled Companion NUCLEO serial capture."
        }
    }
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
        prompt_operator = [bool]$PromptOperator
        prompt_title = $PromptTitle
        prompt_message = if ($PromptOperator) { $operatorPromptText } else { $null }
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

if ($SelfTestEmptyCapture) {
    if ($CheckOnly -or $Execute -or $SelfTestResetTimeout) {
        throw "Use only one of -CheckOnly, -Execute, -SelfTestEmptyCapture, or -SelfTestResetTimeout."
    }
    "" | Set-Content -LiteralPath $rawLog -Encoding UTF8
    $errors.Add("No serial bytes captured during $Seconds second(s); refusing empty runtime evidence.") | Out-Null
    Write-Summary -Status "FAIL" -PortName "SELFTEST" -Candidates @() -AvailablePorts @() -BytesRead 0 -Errors @($errors) -Mode "selftest-empty-capture"
    throw "Companion NUCLEO serial capture empty-log self-test failed as expected. See $summaryJson"
}

if ($SelfTestResetTimeout) {
    if ($CheckOnly -or $Execute -or $SelfTestEmptyCapture) {
        throw "Use only one of -CheckOnly, -Execute, -SelfTestEmptyCapture, or -SelfTestResetTimeout."
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

try {
    $resolved = Resolve-CapturePort -RequestedPort $Port
} catch {
    $errors.Add($_.Exception.Message) | Out-Null
    $available = @([System.IO.Ports.SerialPort]::GetPortNames() | Sort-Object)
    Write-Summary -Status "FAIL" -PortName $Port -Candidates @() -AvailablePorts $available -BytesRead 0 -Errors @($errors) -Mode "resolve-port"
    throw
}

if ($CheckOnly -and -not $Execute) {
    Write-Output "CHECK: Selected port: $($resolved.port)"
    Write-Output "CHECK: Auto detected: $($resolved.auto_detected)"
    Write-Output "CHECK: Present ports: $($resolved.available_ports -join ', ')"
    Write-Output "CHECK: Blocking operator prompt: $([bool]$PromptOperator)"
    Write-Output "CHECK: Reset timeout seconds: $ResetTimeoutSeconds"
    foreach ($candidate in @($resolved.candidates)) {
        Write-Output "CHECK: ST-LINK candidate $($candidate.port): $($candidate.name)"
    }
    Write-Output "CHECK: STM32CubeProgrammer CLI found: $([bool]$programmer)"
    if ($programmer) { Write-Output "CHECK: Programmer: $programmer" }
    Write-Output "CHECK: Real serial capture must run inside workflow lock:"
    Write-Output "  $lockCommand"
    Write-Output "CHECK: Add -PromptOperator only when the capture is waiting for a real human action or observation."
    Write-Summary -Status "DRY-RUN" -PortName $resolved.port -Candidates @($resolved.candidates) -AvailablePorts @($resolved.available_ports) -BytesRead 0 -Errors @() -Mode "check-only"
    exit 0
}

if (-not $Execute) {
    throw "Refusing to open Companion NUCLEO serial port without -Execute. Use -CheckOnly for dry-run output."
}

if (-not $WorkflowLockHeld) {
    throw "Refusing to open Companion NUCLEO serial port without workflow lock acknowledgement. Run through aiw with-lock -Resource Companion-WB55 and pass -WorkflowLockHeld inside the locked command."
}

if ($ResetAfterOpen -and -not $programmer) {
    throw "STM32CubeProgrammer CLI not found. Pass -ProgrammerPath, set STM32CUBEPROGRAMMER_CLI, or omit -ResetAfterOpen."
}

$serial = [System.IO.Ports.SerialPort]::new($resolved.port, $BaudRate, [System.IO.Ports.Parity]::None, 8, [System.IO.Ports.StopBits]::One)
$serial.ReadTimeout = 250
$serial.NewLine = "`n"

try {
    "" | Set-Content -LiteralPath $rawLog -Encoding UTF8
    $serial.Open()
    $serial.DiscardInBuffer()
    $serial.DiscardOutBuffer()
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
        Show-OperatorPrompt -Title $PromptTitle -Message $operatorPromptText
    }

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
    if ($serial.IsOpen) {
        $serial.Close()
    }
    $serial.Dispose()
}

if ($errors.Count -eq 0 -and $bytesRead -le 0) {
    $errors.Add("No serial bytes captured during $Seconds second(s); refusing empty runtime evidence.") | Out-Null
}

$status = if ($errors.Count -eq 0) { "PASS" } else { "FAIL" }
Write-Summary -Status $status -PortName $resolved.port -Candidates @($resolved.candidates) -AvailablePorts @($resolved.available_ports) -BytesRead $bytesRead -Errors @($errors) -Mode "capture"
if ($status -ne "PASS") {
    throw "Companion NUCLEO serial capture failed. See $summaryJson"
}
