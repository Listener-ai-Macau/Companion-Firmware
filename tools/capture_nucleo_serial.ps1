param(
    [string]$Port = 'COM13',
    [int]$BaudRate = 115200,
    [int]$Seconds = 15,
    [switch]$ResetAfterOpen,
    [string]$ProgrammerRoot = 'C:\ST\STM32CubeIDE_2.1.1\STM32CubeIDE\plugins'
)

$ErrorActionPreference = 'Stop'

$serial = [System.IO.Ports.SerialPort]::new($Port, $BaudRate, [System.IO.Ports.Parity]::None, 8, [System.IO.Ports.StopBits]::One)
$serial.ReadTimeout = 250
$serial.NewLine = "`n"

try {
    $serial.Open()
    if ($ResetAfterOpen) {
        $programmer = Get-ChildItem -LiteralPath $ProgrammerRoot -Recurse -Filter STM32_Programmer_CLI.exe |
            Select-Object -First 1 -ExpandProperty FullName
        if (-not $programmer) {
            throw "STM32_Programmer_CLI.exe not found under $ProgrammerRoot"
        }
        & $programmer -c port=SWD mode=UR reset=HWrst freq=4000 -rst | Out-Host
        if ($LASTEXITCODE -ne 0) {
            throw "reset failed with exit code $LASTEXITCODE"
        }
    }
    $deadline = [DateTime]::UtcNow.AddSeconds($Seconds)
    while ([DateTime]::UtcNow -lt $deadline) {
        try {
            $text = $serial.ReadExisting()
            if ($text.Length -gt 0) {
                Write-Host -NoNewline $text
            }
        } catch [TimeoutException] {
        }
        Start-Sleep -Milliseconds 100
    }
} finally {
    if ($serial.IsOpen) {
        $serial.Close()
    }
    $serial.Dispose()
}
