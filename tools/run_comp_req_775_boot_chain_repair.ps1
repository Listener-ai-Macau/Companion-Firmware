#requires -Version 7.0
param(
    [switch]$Execute,
    [string]$PortName = "COM13",
    [string]$ProgrammerSerial = "066EFF535570514867221931"
)

$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot
$cli = "C:\ST\STM32CubeProgrammer\bin\STM32_Programmer_CLI.exe"
$loader = Join-Path $repo (
    "cubeide\Companion_BLE_Ota_Loader\build\Companion_BLE_Ota_Loader.hex"
)
$buildReceipt = Join-Path $repo (
    ".cache\validation\comp-req-775-incremental-sync\" +
    "FIRMWARE_BUILD_READY.json"
)
$runRoot = Join-Path $repo (
    ".cache\validation\comp-req-775-incremental-sync\" +
    "hardware-external-loader-acceptance\boot-chain-repair"
)
$receiptPath = Join-Path $runRoot "BOOT_CHAIN_MACHINE_READY.json"
$loaderSha = (
    "7AF74009DCDCC82601DE1F04BEC94248F" +
    "C5CE48C9B44F6298A44B0763FBD8324"
)
$pageSha = (
    "AA5235193309CAA9B42F467DA1CE2D75" +
    "BF96EB2197F26410D22356A45ABC6857"
)
$sourceManifest = Join-Path $repo (
    ".cache\validation\comp-req-775-incremental-sync\" +
    "offline-initial-batched\current-source-pack\source-pack-manifest.json"
)
$bootVerifier = Join-Path $repo (
    "tools\faraday_upper_art\verify_comp_req_775_boot_log.py"
)

foreach ($required in @(
    $cli, $loader, $buildReceipt, $sourceManifest, $bootVerifier
)) {
    if (-not (Test-Path -LiteralPath $required -PathType Leaf)) {
        throw "Missing boot-chain input: $required"
    }
}
$build = Get-Content -LiteralPath $buildReceipt -Raw |
    ConvertFrom-Json -AsHashtable
$app = Join-Path $repo ([string]$build.firmware.hex)
if (-not (Test-Path -LiteralPath $app -PathType Leaf)) {
    throw "Missing current App from build receipt: $app"
}
$appSha = [string]$build.firmware.hex_sha256
$checks = [ordered]@{
    formal_loader_hex_identity = (
        (Get-FileHash -LiteralPath $loader -Algorithm SHA256).Hash -eq
        $loaderSha
    )
    current_app_hex_identity = (
        (Get-FileHash -LiteralPath $app -Algorithm SHA256).Hash -eq
        $appSha
    )
    app_build_ready = (
        [string]$build.status -eq "FIRMWARE_BUILD_READY" -and
        [bool]$build.checks.ota_vector_at_0x08007000 -and
        [bool]$build.checks.hex_programs_only_ota_app_region -and
        [bool]$build.checks.generation_runtime_linked -and
        [bool]$build.checks.real_ssd1681_driver_linked
    )
}
if ($checks.Values -contains $false) {
    throw "Boot-chain source identity preflight failed."
}
if (-not $Execute) {
    [ordered]@{
        schema = "companion.comp_req_775.boot_chain_repair.v1"
        status = "CHECK_ONLY"
        checks = $checks
        loader_sha256 = $loaderSha
        app_sha256 = $appSha
        loader_write_scope = "0x08000000..<0x0800420E defined bytes"
        app_write_scope = "0x08007000..<0x08080000 defined bytes"
        receipt = $receiptPath
        hardware_contact = 0
    } | ConvertTo-Json -Depth 8
    exit 0
}

. (Join-Path $repo "tools\companion_wb55_lock.ps1")
$lock = $null
$swdMutex = $null
$swdOwned = $false
$serialPort = $null
try {
    $lock = Enter-CompanionWb55Lock -Purpose (
        "COMP-REQ-775 restore formal Loader and current generation App"
    )
    $swdMutex = [Threading.Mutex]::new(
        $false, "Local\Companion-WB55-SWD-COM-Exclusive-v1"
    )
    try {
        $swdOwned = $swdMutex.WaitOne(0)
    } catch [Threading.AbandonedMutexException] {
        $swdOwned = $true
    }
    if (-not $swdOwned) {
        throw "SWD/COM mutex is already held."
    }
    New-Item -ItemType Directory -Force -Path $runRoot | Out-Null
    $before = Join-Path $runRoot "internal-before.bin"
    $after = Join-Path $runRoot "internal-after.bin"
    $programmerCalls = [Collections.Generic.List[object]]::new()
    function Invoke-Programmer {
        param(
            [Parameter(Mandatory = $true)][string]$Name,
            [Parameter(Mandatory = $true)][string[]]$Arguments
        )
        $log = Join-Path $runRoot "$Name.log"
        & $cli @Arguments 2>&1 |
            Tee-Object -FilePath $log |
            Out-Null
        $exitCode = $LASTEXITCODE
        $programmerCalls.Add([ordered]@{
            name = $Name
            arguments = $Arguments
            exit_code = $exitCode
            log = $log
        })
        if ($exitCode -ne 0) {
            throw "CubeProgrammer $Name failed with exit $exitCode."
        }
    }
    $connect = @(
        "-c", "port=SWD", "sn=$ProgrammerSerial",
        "mode=UR", "reset=HWrst", "freq=4000"
    )
    Invoke-Programmer -Name "01-read-before" -Arguments @(
        $connect + @("-u", "0x08000000", "0x80000", $before)
    )
    Invoke-Programmer -Name "02-loader-write-verify" -Arguments @(
        $connect + @("-w", $loader, "-v")
    )
    Invoke-Programmer -Name "03-app-write-verify" -Arguments @(
        $connect + @("-w", $app, "-v")
    )
    Invoke-Programmer -Name "04-read-after" -Arguments @(
        $connect + @("-u", "0x08000000", "0x80000", $after)
    )

    $compareSource = @'
import json
import sys
from pathlib import Path

def parse_ihex(path):
    memory = {}
    upper = 0
    for line in Path(path).read_text(encoding="ascii").splitlines():
        if not line.startswith(":"):
            continue
        record = bytes.fromhex(line[1:])
        count = record[0]
        address = int.from_bytes(record[1:3], "big")
        kind = record[3]
        data = record[4:4 + count]
        if kind == 0:
            for offset, value in enumerate(data):
                memory[upper + address + offset] = value
        elif kind == 2:
            upper = int.from_bytes(data, "big") << 4
        elif kind == 4:
            upper = int.from_bytes(data, "big") << 16
    return memory

def compare(memory, readback):
    mismatches = []
    for address, expected in memory.items():
        observed = readback[address - 0x08000000]
        if observed != expected:
            mismatches.append({
                "address": f"0x{address:08X}",
                "expected": expected,
                "observed": observed,
            })
            if len(mismatches) >= 16:
                break
    return {
        "defined_bytes": len(memory),
        "start": f"0x{min(memory):08X}",
        "end_exclusive": f"0x{max(memory) + 1:08X}",
        "matches": not mismatches,
        "first_mismatches": mismatches,
    }

readback = Path(sys.argv[3]).read_bytes()
print(json.dumps({
    "loader": compare(parse_ihex(sys.argv[1]), readback),
    "app": compare(parse_ihex(sys.argv[2]), readback),
}))
'@
    $identity = ($compareSource | python - $loader $app $after) |
        ConvertFrom-Json -AsHashtable
    if (-not $identity.loader.matches -or -not $identity.app.matches) {
        throw "Final Loader/App readback identity failed."
    }

    $serialPort = [IO.Ports.SerialPort]::new(
        $PortName, 115200, [IO.Ports.Parity]::None, 8,
        [IO.Ports.StopBits]::One
    )
    $serialPort.ReadTimeout = 120
    $serialPort.Open()
    $serialPort.DiscardInBuffer()
    Invoke-Programmer -Name "05-reset" -Arguments @($connect + @("-rst"))
    $capture = [Collections.Generic.List[string]]::new()
    $deadline = (Get-Date).AddSeconds(60)
    while ((Get-Date) -lt $deadline) {
        try {
            $line = $serialPort.ReadLine().Trim()
            if ($line.Length -gt 0) {
                $capture.Add($line)
                $joined = $capture -join "`n"
                if (
                    $joined -match "\[screen-assets\] ui_generation=active" -and
                    $joined -match "identity=comp_req_638 mount=ok" -and
                    $joined -match (
                        "accepted_product_driver.*has_busy=1.*result=1"
                    ) -and
                    $joined -match "\[screen-life\].*frame_index=\d+"
                ) {
                    break
                }
            }
        } catch [TimeoutException] {
        }
    }
    $serialPort.Close()
    $serialPort.Dispose()
    $serialPort = $null
    $bootLog = Join-Path $runRoot "boot-serial.log"
    (($capture -join "`n") + "`n") |
        Set-Content -LiteralPath $bootLog -Encoding utf8
    $bootEvidencePath = Join-Path $runRoot "BOOT_EVIDENCE.json"
    & python $bootVerifier `
        --log $bootLog `
        --source-manifest $sourceManifest `
        --page-sha256 $pageSha `
        --allow-missing-recording-resource `
        --receipt $bootEvidencePath | Out-Null
    $bootExit = $LASTEXITCODE
    $bootEvidence = Get-Content -LiteralPath $bootEvidencePath -Raw |
        ConvertFrom-Json -AsHashtable
    $receipt = [ordered]@{
        schema = "companion.comp_req_775.boot_chain_repair.v1"
        status = $(if ($bootExit -eq 0) {
            "MACHINE_READY"
        } else {
            "FAILED"
        })
        source_checks = $checks
        loader = $identity.loader
        loader_sha256 = $loaderSha
        app = $identity.app
        app_sha256 = $appSha
        boot_evidence = $bootEvidence
        programmer_calls = $programmerCalls
        internal_flash_restore_only = $true
        external_flash_write_bytes = 0
        recording_partition_write_bytes = 0
        fus_write_bytes = 0
        otp_write_bytes = 0
        option_byte_write_bytes = 0
        ordinary_reset_performed = $true
        hardware_contact = 1
        workflow_lock = Get-CompanionWb55LockEvidenceSummary $lock
        swd_mutex = "Local\Companion-WB55-SWD-COM-Exclusive-v1"
    }
    $receipt | ConvertTo-Json -Depth 12 |
        Set-Content -LiteralPath $receiptPath -Encoding utf8
    $receipt | ConvertTo-Json -Depth 12
    if ($receipt.status -ne "MACHINE_READY") {
        exit 3
    }
} finally {
    if ($serialPort) {
        try {
            $serialPort.Close()
        } catch {
        }
        $serialPort.Dispose()
    }
    if ($swdOwned -and $swdMutex) {
        $swdMutex.ReleaseMutex()
    }
    if ($swdMutex) {
        $swdMutex.Dispose()
    }
    Exit-CompanionWb55Lock
}
