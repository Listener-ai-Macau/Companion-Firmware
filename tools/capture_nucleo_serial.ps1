param(
    [switch] $CheckOnly,
    [switch] $Execute,
    [switch] $WorkflowLockHeld,
    [string] $Port,
    [int] $BaudRate = 115200,
    [int] $Seconds = 15,
    [switch] $ResetAfterOpen,
    [string] $ProgrammerPath,
    [string] $ProgrammerRoot = "C:\ST\STM32CubeIDE_2.1.1\STM32CubeIDE\plugins",
    [int] $PromptTimeoutSeconds = 90,
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

$resolved = $null
$programmer = Find-CubeProgrammerCli -RequestedPath $ProgrammerPath
$errors = [System.Collections.Generic.List[string]]::new()
$bytesRead = 0

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
    foreach ($candidate in @($resolved.candidates)) {
        Write-Output "CHECK: ST-LINK candidate $($candidate.port): $($candidate.name)"
    }
    Write-Output "CHECK: STM32CubeProgrammer CLI found: $([bool]$programmer)"
    if ($programmer) { Write-Output "CHECK: Programmer: $programmer" }
    Write-Output "CHECK: Real serial capture must run inside workflow lock:"
    Write-Output "  $lockCommand"
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

Show-OperatorPrompt -Title "Companion NUCLEO 串口抓日志确认" -Message "请确认 NUCLEO-WB55RG 已通过板载 ST-LINK USB 接好，Type/其它串口监视器已停止占用端口。脚本将打开 $($resolved.port)，波特率 $BaudRate，抓取 $Seconds 秒日志$(if ($ResetAfterOpen) { '，并通过 ST-LINK 复位一次目标板' } else { '' })。输出日志：$rawLog。点击 OK 继续；超时或 Cancel 将取消。"

$serial = [System.IO.Ports.SerialPort]::new($resolved.port, $BaudRate, [System.IO.Ports.Parity]::None, 8, [System.IO.Ports.StopBits]::One)
$serial.ReadTimeout = 250
$serial.NewLine = "`n"

try {
    "" | Set-Content -LiteralPath $rawLog -Encoding UTF8
    $serial.Open()
    if ($ResetAfterOpen) {
        $resetArgs = @("-c", "port=SWD", "mode=UR", "reset=HWrst", "freq=4000", "-rst")
        $resetLine = "RUN: $programmer $($resetArgs -join ' ')"
        Write-Output $resetLine
        Add-Content -LiteralPath $rawLog -Value $resetLine
        $resetOutput = & $programmer @resetArgs 2>&1
        $resetOutput | ForEach-Object {
            Write-Output $_
            Add-Content -LiteralPath $rawLog -Value ([string]$_)
        }
        if ($LASTEXITCODE -ne 0) {
            throw "reset failed with exit code $LASTEXITCODE"
        }
    }

    $deadline = [DateTime]::UtcNow.AddSeconds($Seconds)
    while ([DateTime]::UtcNow -lt $deadline) {
        try {
            $text = $serial.ReadExisting()
            if ($text.Length -gt 0) {
                $bytesRead += [System.Text.Encoding]::UTF8.GetByteCount($text)
                Write-Host -NoNewline $text
                Add-Content -LiteralPath $rawLog -Value $text -NoNewline
            }
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

$status = if ($errors.Count -eq 0) { "PASS" } else { "FAIL" }
Write-Summary -Status $status -PortName $resolved.port -Candidates @($resolved.candidates) -AvailablePorts @($resolved.available_ports) -BytesRead $bytesRead -Errors @($errors) -Mode "capture"
if ($status -ne "PASS") {
    throw "Companion NUCLEO serial capture failed. See $summaryJson"
}
