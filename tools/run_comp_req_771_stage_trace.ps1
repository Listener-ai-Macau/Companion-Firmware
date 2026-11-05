param(
    [string] $PortName = "COM13",
    [string] $ProgrammerSerial = "066EFF535570514867221931"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repo = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$hardwareRoot = Join-Path $repo ".cache\validation\comp-req-771-same-source-flash\hardware-run"
$privateRoot = Join-Path $hardwareRoot "private"
$programmer = "C:\ST\STM32CubeIDE_2.1.1\STM32CubeIDE\plugins\com.st.stm32cube.ide.mcu.externaltools.cubeprogrammer.win32_2.2.400.202601091506\tools\bin\STM32_Programmer_CLI.exe"
$loader = Join-Path $repo "cubeide\Companion_BLE_Ota_Loader\build\Companion_BLE_Ota_Loader.hex"
$app = Join-Path $repo "cubeide\Companion_Nucleo_WB55RG_Bringup\build_comp_req_771_ota_trace_r15\Companion_Nucleo_WB55RG_Bringup.hex"
$backup = Join-Path $privateRoot "preflash-full-a.bin"
$readback = Join-Path $privateRoot "stage-trace-restore-readback.bin"
$serialLog = Join-Path $hardwareRoot "stage-trace-serial.log"
$port = $null
$owned = $false
$writeStarted = $false
$restored = $false
$mutex = [System.Threading.Mutex]::new(
    $false, "Local\Companion-WB55-SWD-COM-Exclusive-v1")

function Invoke-Programmer {
    param([string] $Name, [string[]] $Arguments)
    & $programmer @Arguments 2>&1 | Set-Content -LiteralPath (
        Join-Path $hardwareRoot "$Name-programmer.log") -Encoding UTF8
    if ($LASTEXITCODE -ne 0) {
        throw "Programmer failed: $Name"
    }
}

try {
    try {
        $owned = $mutex.WaitOne(0)
    } catch [System.Threading.AbandonedMutexException] {
        $owned = $true
    }
    if (-not $owned) {
        throw "SWD/COM mutex is busy"
    }
    foreach ($path in @($programmer, $loader, $app, $backup)) {
        if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
            throw "Missing trace input: $path"
        }
    }
    $port = [System.IO.Ports.SerialPort]::new(
        $PortName, 115200, [System.IO.Ports.Parity]::None, 8,
        [System.IO.Ports.StopBits]::One)
    $port.Open()
    $port.DiscardInBuffer()

    $writeStarted = $true
    Invoke-Programmer "stage-trace-loader-write" @(
        "-c", "port=SWD", "sn=$ProgrammerSerial", "mode=UR",
        "reset=HWrst", "freq=4000", "-w", $loader, "-v")
    Invoke-Programmer "stage-trace-product-write" @(
        "-c", "port=SWD", "sn=$ProgrammerSerial", "mode=UR",
        "reset=HWrst", "freq=4000", "-w", $app, "-v")
    $port.DiscardInBuffer()
    Invoke-Programmer "stage-trace-product-reset" @(
        "-c", "port=SWD", "sn=$ProgrammerSerial", "mode=UR",
        "reset=HWrst", "freq=4000", "-rst")
    $text = [System.Text.StringBuilder]::new()
    $deadline = (Get-Date).AddSeconds(20)
    while ((Get-Date) -lt $deadline) {
        $chunk = $port.ReadExisting()
        if ($chunk.Length -gt 0) {
            [void]$text.Append($chunk)
            $text.ToString() |
                Set-Content -LiteralPath $serialLog -Encoding UTF8
        }
        Start-Sleep -Milliseconds 100
    }
} finally {
    if ($port) {
        if ($port.IsOpen) {
            $port.Close()
        }
        $port.Dispose()
    }
    if ($writeStarted) {
        Invoke-Programmer "stage-trace-restore" @(
            "-c", "port=SWD", "sn=$ProgrammerSerial", "mode=UR",
            "reset=HWrst", "freq=4000",
            "-w", $backup, "0x08000000",
            "-v", $backup, "0x08000000", "-rst")
        Invoke-Programmer "stage-trace-restore-readback" @(
            "-c", "port=SWD", "sn=$ProgrammerSerial", "mode=UR",
            "reset=HWrst", "freq=4000",
            "-u", "0x08000000", "0x80000", $readback)
        $restored = (
            (Get-Item -LiteralPath $readback).Length -eq 0x80000 -and
            (Get-FileHash -LiteralPath $readback -Algorithm SHA256).Hash -eq
            (Get-FileHash -LiteralPath $backup -Algorithm SHA256).Hash)
    }
    [ordered]@{
        schema = "companion.comp_req_771.stage_trace.v1"
        status = if ($restored) { "TRACE_RESTORED" } else { "NO_GO" }
        hardware_contact = 1
        flash = $writeStarted
        restored = $restored
        serial_log = $serialLog
    } | ConvertTo-Json | Set-Content -LiteralPath (
        Join-Path $hardwareRoot "stage-trace.json") -Encoding UTF8
    if ($owned) {
        $mutex.ReleaseMutex()
    }
    $mutex.Dispose()
}
