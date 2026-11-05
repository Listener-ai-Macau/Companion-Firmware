param(
    [string] $ProgrammerSerial = "066EFF535570514867221931"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repo = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$runRoot = Join-Path $repo ".cache\validation\comp-req-771-same-source-flash"
$hardwareRoot = Join-Path $runRoot "hardware-run"
$privateRoot = Join-Path $hardwareRoot "private"
$programmerRoot = "C:\ST\STM32CubeIDE_2.1.1\STM32CubeIDE\plugins\com.st.stm32cube.ide.mcu.externaltools.cubeprogrammer.win32_2.2.400.202601091506\tools\bin"
$programmer = Join-Path $programmerRoot "STM32_Programmer_CLI.exe"
$gdbServer = "C:\ST\STM32CubeIDE_2.1.1\STM32CubeIDE\plugins\com.st.stm32cube.ide.mcu.externaltools.stlink-gdb-server.win32_2.2.400.202601091506\tools\bin\ST-LINK_gdbserver.exe"
$gdb = "C:\ST\STM32CubeIDE_2.1.1\STM32CubeIDE\plugins\com.st.stm32cube.ide.mcu.externaltools.gnu-tools-for-stm32.14.3.rel1.win32_1.0.100.202602081740\tools\bin\arm-none-eabi-gdb.exe"
$loader = Join-Path $repo "cubeide\Companion_BLE_Ota_Loader\build\Companion_BLE_Ota_Loader.hex"
$appRoot = Join-Path $repo "cubeide\Companion_Nucleo_WB55RG_Bringup\build_comp_req_770_ota_driver_r7"
$app = Join-Path $appRoot "Companion_Nucleo_WB55RG_Bringup.hex"
$elf = Join-Path $appRoot "Companion_Nucleo_WB55RG_Bringup.elf"
$backupA = Join-Path $privateRoot "preflash-full-a.bin"
$backupB = Join-Path $privateRoot "preflash-full-b.bin"
$readback = Join-Path $privateRoot "gdb-restore-readback.bin"
$commands = Join-Path $runRoot "gdb-attach.txt"
$gdbOutput = Join-Path $hardwareRoot "gdb-attach-output.log"
$serverLog = Join-Path $hardwareRoot "gdb-server.log"
$server = $null
$mutex = [System.Threading.Mutex]::new(
    $false, "Local\Companion-WB55-SWD-COM-Exclusive-v1")
$owned = $false
$writeStarted = $false
$restored = $false

function Invoke-Programmer {
    param([string] $Name, [string[]] $Arguments)
    $output = & $programmer @Arguments 2>&1
    $output | Set-Content -LiteralPath (
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
    foreach ($path in @(
        $programmer, $gdbServer, $gdb, $loader, $app, $elf,
        $backupA, $backupB, $commands)) {
        if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
            throw "Missing diagnostic input: $path"
        }
    }
    $backupHash = (Get-FileHash -LiteralPath $backupA -Algorithm SHA256).Hash
    if ($backupHash -ne
        (Get-FileHash -LiteralPath $backupB -Algorithm SHA256).Hash) {
        throw "Dual backups are not identical"
    }

    $writeStarted = $true
    Invoke-Programmer "gdb-loader-write" @(
        "-c", "port=SWD", "sn=$ProgrammerSerial", "mode=UR",
        "reset=HWrst", "freq=4000", "-w", $loader, "-v")
    Invoke-Programmer "gdb-product-write" @(
        "-c", "port=SWD", "sn=$ProgrammerSerial", "mode=UR",
        "reset=HWrst", "freq=4000", "-w", $app, "-v")
    Invoke-Programmer "gdb-product-reset" @(
        "-c", "port=SWD", "sn=$ProgrammerSerial", "mode=UR",
        "reset=HWrst", "freq=4000", "-rst")
    Start-Sleep -Seconds 15

    $server = Start-Process -FilePath $gdbServer -WindowStyle Hidden -PassThru `
        -ArgumentList @(
            "-g", "-d", "-i", $ProgrammerSerial, "-cp", $programmerRoot,
            "-p", "61234", "-f", $serverLog, "-l", "31")
    $ready = $false
    for ($attempt = 0; $attempt -lt 20; $attempt++) {
        Start-Sleep -Milliseconds 250
        if (Test-NetConnection 127.0.0.1 -Port 61234 `
                -InformationLevel Quiet -WarningAction SilentlyContinue) {
            $ready = $true
            break
        }
        if ($server.HasExited) {
            break
        }
    }
    if (-not $ready) {
        throw "GDB server did not become ready"
    }
    & $gdb --batch -x $commands $elf 2>&1 |
        Set-Content -LiteralPath $gdbOutput -Encoding UTF8
    if ($LASTEXITCODE -ne 0) {
        throw "GDB attach failed"
    }
} finally {
    if ($server -and -not $server.HasExited) {
        Stop-Process -Id $server.Id -Force
        $server.WaitForExit()
    }
    if ($writeStarted) {
        Invoke-Programmer "gdb-restore-preflash" @(
            "-c", "port=SWD", "sn=$ProgrammerSerial", "mode=UR",
            "reset=HWrst", "freq=4000",
            "-w", $backupA, "0x08000000",
            "-v", $backupA, "0x08000000", "-rst")
        Invoke-Programmer "gdb-restore-readback" @(
            "-c", "port=SWD", "sn=$ProgrammerSerial", "mode=UR",
            "reset=HWrst", "freq=4000",
            "-u", "0x08000000", "0x80000", $readback)
        $restored = (
            (Get-Item -LiteralPath $readback).Length -eq 0x80000 -and
            (Get-FileHash -LiteralPath $readback -Algorithm SHA256).Hash -eq
            (Get-FileHash -LiteralPath $backupA -Algorithm SHA256).Hash)
    }
    [ordered]@{
        schema = "companion.comp_req_771.gdb_diagnostic.v1"
        status = if ($restored) { "DIAGNOSTIC_RESTORED" } else { "NO_GO" }
        hardware_contact = 1
        flash = $writeStarted
        restored = $restored
        gdb_output = $gdbOutput
    } | ConvertTo-Json | Set-Content -LiteralPath (
        Join-Path $hardwareRoot "gdb-diagnostic.json") -Encoding UTF8
    if ($owned) {
        $mutex.ReleaseMutex()
    }
    $mutex.Dispose()
}
