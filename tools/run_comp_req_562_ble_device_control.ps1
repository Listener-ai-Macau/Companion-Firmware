param(
    [string]$OutputDirectory = '',
    [string]$HostSource = '',
    [string]$NameSource = '',
    [string]$RepairSource = '',
    [string]$GattSource = '',
    [string]$MutationLabel = ''
)
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$out = if ($OutputDirectory) { (New-Item -ItemType Directory -Force $OutputDirectory).FullName } else { Join-Path $root '.cache/validation/comp-req-562-ble-device-control' }
New-Item -ItemType Directory -Force $out | Out-Null
$exe = Join-Path $out 'comp-req-562-ble-device-control.exe'
$log = Join-Path $out 'compile.log'
$stdoutPath = Join-Path $out 'stdout.log'
$stderrPath = Join-Path $out 'stderr.log'
$resultPath = Join-Path $out 'result.json'
foreach ($path in @($exe, $log, $stdoutPath, $stderrPath, $resultPath)) {
    if (Test-Path -LiteralPath $path) { Remove-Item -LiteralPath $path -Force }
}

$compiler = $null
$vcvars = $null
$knownVcvars = 'C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat'
if (Test-Path -LiteralPath $knownVcvars) {
    $vcvars = $knownVcvars
    $compilerCandidate = Get-ChildItem -LiteralPath 'C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Tools\MSVC' -Filter cl.exe -File -Recurse -ErrorAction SilentlyContinue |
        Where-Object { $_.FullName -match '\\bin\\Hostx64\\x64\\cl\.exe$' } |
        Sort-Object FullName -Descending |
        Select-Object -First 1
    if ($compilerCandidate) { $compiler = $compilerCandidate.FullName }
}
$roots = @($env:ProgramFiles, ${env:ProgramFiles(x86)}) | Where-Object { $_ }
foreach ($rootPath in $(if ($compiler) { @() } else { $roots })) {
    $found = Get-ChildItem -LiteralPath $rootPath -Filter cl.exe -File -Recurse -ErrorAction SilentlyContinue |
        Where-Object { $_.FullName -match '\\VC\\Tools\\MSVC\\[^\\]+\\bin\\Hostx64\\x64\\cl\.exe$' } |
        Select-Object -First 1
    if ($found) {
        $compiler = $found.FullName
        $vcvars = Join-Path $found.Directory.Parent.Parent.Parent.Parent.Parent.Parent.FullName 'Auxiliary/Build/vcvars64.bat'
        break
    }
}
if (!$compiler -or !(Test-Path -LiteralPath $vcvars)) { throw 'MSVC unavailable' }
$vendorRoot = Join-Path $root 'third_party/STM32CubeWB'
if (!(Test-Path -LiteralPath (Join-Path $vendorRoot 'Middlewares/ST/STM32_WPAN/ble/core/auto/ble_types.h'))) {
    $siblingVendor = Join-Path $root '..\..\Companion-Firmware\third_party\STM32CubeWB'
    if (Test-Path -LiteralPath (Join-Path $siblingVendor 'Middlewares/ST/STM32_WPAN/ble/core/auto/ble_types.h')) {
        $vendorRoot = (Resolve-Path $siblingVendor).Path
    } else {
        throw 'STM32CubeWB checkout unavailable; refusing download or vendor mutation'
    }
}

$incs = @(
    'app/companion_pendant/platform',
    'app/companion_pendant/gatt',
    'tools/fixtures',
    'third_party/denzic-platform/device_control/embedded/c/include',
    'third_party/denzic-platform/observability/embedded/c/include',
    'third_party/denzic-platform/ota/embedded/c/include',
    (Join-Path $vendorRoot 'Middlewares/ST/STM32_WPAN/ble/core/auto'),
    (Join-Path $vendorRoot 'Middlewares/ST/STM32_WPAN/ble/core/template'),
    (Join-Path $vendorRoot 'Middlewares/ST/STM32_WPAN/ble/core'),
    (Join-Path $vendorRoot 'Middlewares/ST/STM32_WPAN'),
    (Join-Path $vendorRoot 'Middlewares/ST/STM32_WPAN/ble'),
    (Join-Path $vendorRoot 'Middlewares/ST/STM32_WPAN/interface/patterns/ble_thread'),
    (Join-Path $vendorRoot 'Middlewares/ST/STM32_WPAN/interface/patterns/ble_thread/tl'),
    (Join-Path $vendorRoot 'Middlewares/ST/STM32_WPAN/utilities'),
    (Join-Path $vendorRoot 'Middlewares/ST/STM32_WPAN/ble/svc/Inc'),
    (Join-Path $vendorRoot 'Middlewares/ST/STM32_WPAN/ble/svc/Src'),
    (Join-Path $vendorRoot 'Projects/P-NUCLEO-WB55.Nucleo/Applications/BLE/BLE_p2pServer/STM32_WPAN/App'),
    (Join-Path $vendorRoot 'Projects/P-NUCLEO-WB55.Nucleo/Applications/BLE/BLE_p2pServer/Core/Inc'),
    (Join-Path $vendorRoot 'Drivers/CMSIS/Core/Include'),
    (Join-Path $vendorRoot 'Drivers/CMSIS/Include'),
    (Join-Path $vendorRoot 'Drivers/CMSIS/Device/ST/STM32WBxx/Include'),
    (Join-Path $vendorRoot 'Drivers/STM32WBxx_HAL_Driver/Inc')
)
$hostPath = if ($HostSource) { (Resolve-Path $HostSource).Path } else { Join-Path $root 'tools/comp_req_562_ble_device_control_host.c' }
$namePath = if ($NameSource) { (Resolve-Path $NameSource).Path } else { Join-Path $root 'app/companion_pendant/platform/companion_ble_name.c' }
$repairPath = if ($RepairSource) { (Resolve-Path $RepairSource).Path } else { Join-Path $root 'app/companion_pendant/platform/companion_ble_repair.c' }
$gattPath = if ($GattSource) { (Resolve-Path $GattSource).Path } else { Join-Path $root 'app/companion_pendant/gatt/companion_gatt_stm32wb.c' }
$sources = @(
    $hostPath,
    'tools/fixtures/companion_gatt_host_stubs.c',
    $gattPath,
    $namePath,
    'app/companion_pendant/platform/companion_ble_name_entry.c',
    $repairPath,
    'app/companion_pendant/platform/companion_platform_adapters.c',
    'app/companion_pendant/platform/companion_product_entry_glue.c',
    'app/companion_pendant/platform/companion_product_identity.c',
    'third_party/denzic-platform/device_control/embedded/c/src/denzic_device_control_v1.c',
    'third_party/denzic-platform/observability/embedded/c/src/denzic_diag_log_gatt_v1.c',
    'third_party/denzic-platform/ota/embedded/c/src/denzic_ota_orchestration_v1.c'
)
$incArgs = ($incs | ForEach-Object {
    $includePath = if ([IO.Path]::IsPathRooted($_)) { $_ } else { Join-Path $root $_ }
    '/I"' + $includePath + '"'
}) -join ' '
$srcArgs = ($sources | ForEach-Object {
    $sourcePath = if ([IO.Path]::IsPathRooted($_)) { $_ } else { Join-Path $root $_ }
    '"' + $sourcePath + '"'
}) -join ' '
$halRtc = Join-Path $vendorRoot 'Drivers/STM32WBxx_HAL_Driver/Inc/stm32wbxx_hal_rtc.h'
$cmd = 'call "' + $vcvars + '" >nul && cl.exe /nologo /Brepro /TC /std:c11 /O2 /W4 /WX /wd4100 /wd4311 /wd4312 /DSTM32WB55xx /D__WEAK= /DCOMPANION_BLE_REPAIR_PLATFORM_GATE=1 /FI"' + (Join-Path $root 'tools/fixtures/companion_gatt_msvc_compat.h') + '" /FI"' + $halRtc + '" ' + $incArgs + ' ' + $srcArgs + ' /Fe:"' + $exe + '" /link /OPT:REF /INCREMENTAL:NO'
cmd /d /s /c $cmd *> $log
$compileExit = $LASTEXITCODE
$runExit = -1
if ($compileExit -eq 0) {
    # PowerShell 7 converts ordinary native stderr diagnostics into terminating
    # ErrorRecord objects under ErrorActionPreference=Stop. Redirect at the
    # cmd boundary so PowerShell observes only cmd's real exit code.
    $runCommand = '""' + $exe + '" 1>"' + $stdoutPath + '" 2>"' + $stderrPath + '""'
    & $env:ComSpec /d /s /c $runCommand
    $runExit = $LASTEXITCODE
}
$sha = { param($path) if (Test-Path -LiteralPath $path) { (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToUpper() } else { $null } }
$sourceHashes = @{}
foreach ($sourcePath in $sources) {
    $resolvedSource = if ([IO.Path]::IsPathRooted($sourcePath)) { $sourcePath } else { Join-Path $root $sourcePath }
    $sourceHashes[$resolvedSource] = & $sha $resolvedSource
}
$result = [pscustomobject]@{
    schema = 'companion.comp_req_562.ble_device_control.host.v1'
    status = if ($compileExit -eq 0 -and $runExit -eq 0) { 'PASS' } else { 'NO_GO' }
    compile_exit = $compileExit
    run_exit = $runExit
    compile_command = $cmd
    compile_log_sha256 = & $sha $log
    executable_sha256 = & $sha $exe
    stdout_sha256 = & $sha $stdoutPath
    stderr_sha256 = & $sha $stderrPath
    stdout = if (Test-Path $stdoutPath) { [IO.File]::ReadAllText($stdoutPath) } else { '' }
    stderr = if (Test-Path $stderrPath) { [IO.File]::ReadAllText($stderrPath) } else { '' }
    hardware_contact = 0
    ble_write = 0
    bond_erase = 0
    radio_commands = 0
    vendor_root = $vendorRoot
    mutation_label = $MutationLabel
    source_sha256 = [pscustomobject]$sourceHashes
}
$resultJson = ConvertTo-Json -InputObject $result -Depth 4
[IO.File]::WriteAllText($resultPath, $resultJson + [Environment]::NewLine, [Text.UTF8Encoding]::new($false))
if ($compileExit -ne 0) { exit $compileExit }
if ($runExit -ne 0) { exit $runExit }
