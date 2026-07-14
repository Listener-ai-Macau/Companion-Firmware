param(
    [string]$ProjectDir = (Join-Path $PSScriptRoot '..\cubeide\Companion_Nucleo_WB55RG_Bringup'),
    [string]$MakePath = 'C:\ST\STM32CubeIDE_2.1.1\STM32CubeIDE\plugins\com.st.stm32cube.ide.mcu.externaltools.make.win32_2.2.100.202601091506\tools\bin\make.exe',
    [switch]$OtaApp,
    [switch]$BootSelfTests,
    [int]$MicPreampShift = -1,
    [ValidateSet('', 'i2s', 'pdm')]
    [string]$MicBackend = '',
    [ValidateRange(-1, 255)]
    [int]$PdmRawSaiMckdiv = -1,
    [ValidateRange(-1, 1)]
    [int]$PdmRawSaiUseDma = -1,
    [ValidateRange(-1, 1)]
    [int]$PdmUseCic3Filter = -1,
    [ValidateRange(-1, 1)]
    [int]$PdmCic3ChunkAccumulate = -1,
    [ValidateRange(-1, 1)]
    [int]$PdmBitOrderLsb = -1,
    [ValidateSet('', 'Og', 'O1', 'O2', 'O3', 'Os')]
    [string]$Optimization = '',
    [int]$FlashRecordingStageBlocks = -1,
    [switch]$BleAudioStreamFlashRecordings,
    [switch]$EpaperSsd1681Bringup,
    [string]$EpaperSsd1681CsPort = '',
    [string]$EpaperSsd1681CsPin = '',
    [string]$EpaperSsd1681DcPort = '',
    [string]$EpaperSsd1681DcPin = '',
    [string]$EpaperSsd1681RstPort = '',
    [string]$EpaperSsd1681RstPin = '',
    [ValidateSet(0, 1)]
    [int]$EpaperSsd1681HasBusy = 1,
    [string]$EpaperSsd1681BusyPort = '',
    [string]$EpaperSsd1681BusyPin = '',
    [ValidateSet(0, 180)]
    [int]$EpaperSsd1681Rotation = 180,
    [ValidateSet(0, 1)]
    [int]$EpaperSsd1681MirrorX = 1,
    [ValidateSet(0, 1)]
    [int]$EpaperMenu = 1,
    [switch]$EpaperEmoteDemo,
    [switch]$EpaperDailyTapDemo,
    [switch]$EpaperDailyStrokeDemo,
    [ValidateSet('left', 'right', 'up', 'down')]
    [string]$EpaperDailyStrokeDemoDirection = 'down',
    [switch]$EpaperMaintenanceDiagnostic,
    [switch]$EpaperRefreshCadenceDiagnostic,
    [switch]$EpaperSsd1681VendorPartialDiagnostic,
    [switch]$EpaperSsd1681DirectGpioSpiDiagnostic,
    [switch]$EpaperSsd1681OfficialFullDiagnostic,
    [switch]$EpaperSsd1681VerboseTrace,
    [ValidateScript({ $_ -eq -1 -or ($_ -ge 1 -and $_ -le 255) })]
    [int]$Ft6336TouchThreshold = -1,
    [switch]$EpaperProductExpressionDemo,
    [ValidateSet('listening', 'thinking', 'speaking', 'happy', 'sleepy', 'recording', 'sync_complete', 'low_battery', 'error')]
    [string]$EpaperProductExpressionDemoExpression = 'listening',
    [ValidateRange(1000, 60000)]
    [int]$EpaperProductExpressionDemoEndAfterMs = 10000,
    [ValidateSet('', 'cs', 'dc', 'res', 'sck', 'mosi')]
    [string]$EpaperSsd1681WireProbe = '',
    [ValidateRange(1, 120)]
    [int]$EpaperSsd1681WireProbeCycles = 5,
    [ValidateRange(100, 60000)]
    [int]$EpaperSsd1681WireProbeDwellMs = 2000,
    [ValidateSet('', 'expression', 'white', 'black', 'checkerboard')]
    [string]$EpaperSsd1681DiagnosticPattern = '',
    [ValidateRange(1, 120)]
    [int]$EpaperSsd1681DiagnosticRepeats = 1,
    [ValidateRange(0, 60000)]
    [int]$EpaperSsd1681DiagnosticIntervalMs = 0,
    [switch]$EpaperSsd1681DiagnosticPartial,
    [switch]$ScreenAssetProvision,
    [switch]$Force
)

$ErrorActionPreference = 'Stop'

function Get-NormalizedPath {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )
    return [System.IO.Path]::GetFullPath($Path)
}

function Test-PathUnderRoot {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,
        [Parameter(Mandatory = $true)]
        [string]$Root
    )
    $normalizedPath = Get-NormalizedPath -Path $Path
    $normalizedRoot = (Get-NormalizedPath -Path $Root).TrimEnd([System.IO.Path]::DirectorySeparatorChar, [System.IO.Path]::AltDirectorySeparatorChar)
    return $normalizedPath.StartsWith($normalizedRoot + [System.IO.Path]::DirectorySeparatorChar, [System.StringComparison]::OrdinalIgnoreCase)
}

function Test-LockOwnerAlive {
    param(
        [Parameter(Mandatory = $true)]
        [string]$OwnerPath
    )
    if (-not (Test-Path -LiteralPath $OwnerPath)) {
        return $true
    }
    try {
        $owner = Get-Content -LiteralPath $OwnerPath -Raw | ConvertFrom-Json
        if ($null -eq $owner.pid) {
            return $true
        }
        $process = Get-Process -Id ([int]$owner.pid) -ErrorAction SilentlyContinue
        return $null -ne $process
    } catch {
        return $true
    }
}

function Acquire-BuildLock {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RepoRoot,
        [Parameter(Mandatory = $true)]
        [string]$ProjectDir,
        [Parameter(Mandatory = $true)]
        [string[]]$MakeArgs,
        [int]$TimeoutSeconds = 180
    )
    $lockRoot = Join-Path $RepoRoot '.cache\locks'
    $lockDir = Join-Path $lockRoot 'build_nucleo_bringup.lock'
    $ownerPath = Join-Path $lockDir 'owner.json'
    New-Item -ItemType Directory -Force -Path $lockRoot | Out-Null
    $started = Get-Date
    $reportedWait = $false
    while ($true) {
        try {
            New-Item -ItemType Directory -Path $lockDir -ErrorAction Stop | Out-Null
            $owner = [ordered]@{
                pid = $PID
                started_utc = (Get-Date).ToUniversalTime().ToString('o')
                project_dir = (Get-NormalizedPath -Path $ProjectDir)
                make_args = $MakeArgs
            }
            $owner | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $ownerPath -Encoding UTF8
            Write-Host "build_nucleo_bringup: acquired build lock $lockDir"
            return [pscustomobject]@{
                LockDir = $lockDir
                LockRoot = $lockRoot
                OwnerPath = $ownerPath
            }
        } catch {
            if (-not (Test-LockOwnerAlive -OwnerPath $ownerPath)) {
                if (-not (Test-PathUnderRoot -Path $lockDir -Root $lockRoot)) {
                    throw "Refusing to remove suspicious build lock path: $lockDir"
                }
                Write-Host "build_nucleo_bringup: removing stale build lock $lockDir"
                Remove-Item -LiteralPath $lockDir -Recurse -Force
                continue
            }
            $elapsed = (Get-Date) - $started
            if ($elapsed.TotalSeconds -ge $TimeoutSeconds) {
                throw "Waited too long for build lock: $lockDir"
            }
            if (-not $reportedWait) {
                Write-Host "build_nucleo_bringup: waiting for build lock $lockDir"
                $reportedWait = $true
            }
            Start-Sleep -Seconds 1
        }
    }
}

function Release-BuildLock {
    param(
        [Parameter(Mandatory = $true)]
        [pscustomobject]$Lock
    )
    if ($null -eq $Lock.LockDir -or $null -eq $Lock.LockRoot) {
        return
    }
    if (-not (Test-Path -LiteralPath $Lock.LockDir)) {
        return
    }
    if (-not (Test-PathUnderRoot -Path $Lock.LockDir -Root $Lock.LockRoot)) {
        throw "Refusing to remove suspicious build lock path: $($Lock.LockDir)"
    }
    Remove-Item -LiteralPath $Lock.LockDir -Recurse -Force
    Write-Host "build_nucleo_bringup: released build lock $($Lock.LockDir)"
}

if (-not (Test-Path -LiteralPath $MakePath)) {
    throw "make.exe not found: $MakePath"
}
if (-not (Test-Path -LiteralPath $ProjectDir)) {
    throw "Project directory not found: $ProjectDir"
}

$RepoRoot = Get-NormalizedPath -Path (Join-Path $PSScriptRoot '..')

$makeArgs = @("-C", $ProjectDir)
if ($EpaperSsd1681VendorPartialDiagnostic -and $EpaperSsd1681DirectGpioSpiDiagnostic) {
    throw "Choose one SSD1681 A/B diagnostic at a time: vendor partial or direct GPIO SPI."
}
if ($Force -or $EpaperDailyTapDemo -or $EpaperDailyStrokeDemo -or $EpaperMaintenanceDiagnostic -or $EpaperRefreshCadenceDiagnostic -or $EpaperSsd1681VendorPartialDiagnostic -or $EpaperSsd1681DirectGpioSpiDiagnostic -or $EpaperSsd1681OfficialFullDiagnostic -or $EpaperSsd1681VerboseTrace -or $Ft6336TouchThreshold -ge 0 -or $EpaperProductExpressionDemo) {
    $makeArgs += "-B"
}
if ($OtaApp) {
    $makeArgs += @(
        "OTA_APP=1",
        "BUILD_DIR=build_ota",
        "TARGET=Companion_Nucleo_WB55RG_Bringup_ota_app"
    )
}
if ($BootSelfTests) {
    $makeArgs += "BOOT_SELFTESTS=1"
}
if ($MicPreampShift -ge 0) {
    if ($MicPreampShift -gt 8) {
        throw "MicPreampShift must be between 0 and 8."
    }
    $makeArgs += "MIC_PREAMP_SHIFT=$MicPreampShift"
}
if ($MicBackend -eq 'i2s') {
    $makeArgs += "MIC_BACKEND=1"
} elseif ($MicBackend -eq 'pdm') {
    $makeArgs += "MIC_BACKEND=2"
}
if ($PdmRawSaiMckdiv -ge 0) {
    $makeArgs += "PDM_RAW_SAI_MCKDIV=$PdmRawSaiMckdiv"
}
if ($PdmRawSaiUseDma -ge 0) {
    $makeArgs += "PDM_RAW_SAI_USE_DMA=$PdmRawSaiUseDma"
}
if ($PdmUseCic3Filter -ge 0) {
    $makeArgs += "PDM_USE_CIC3_FILTER=$PdmUseCic3Filter"
}
if ($PdmCic3ChunkAccumulate -ge 0) {
    $makeArgs += "PDM_CIC3_CHUNK_ACCUMULATE=$PdmCic3ChunkAccumulate"
}
if ($PdmBitOrderLsb -ge 0) {
    $makeArgs += "PDM_BIT_ORDER_LSB=$PdmBitOrderLsb"
}
if ($Optimization -ne '') {
    $makeArgs += "C_OPT=-$Optimization"
}
if ($FlashRecordingStageBlocks -ge 0) {
    if ($FlashRecordingStageBlocks -eq 0) {
        throw "FlashRecordingStageBlocks must be greater than 0."
    }
    $makeArgs += "FLASH_RECORDING_STAGE_BLOCKS=$FlashRecordingStageBlocks"
}
if ($BleAudioStreamFlashRecordings) {
    $makeArgs += "BLE_AUDIO_STREAM_FLASH_RECORDINGS=1"
}
if ($EpaperSsd1681Bringup) {
    $makeArgs += "EPAPER_SSD1681_BRINGUP=1"
}
if ($ScreenAssetProvision) {
    if ($Optimization -eq '') {
        # This one-shot writer embeds the external CEMP pack in MCU Flash.
        # Keep the normal product build at its default optimization level.
        $makeArgs += "C_OPT=-Os"
    }
    $makeArgs += @(
        "EPAPER_SSD1681_BRINGUP=1",
        "EPAPER_MENU=$EpaperMenu",
        "SCREEN_ASSET_PROVISION=1",
        "BUILD_DIR=build_screen_asset_provision",
        "TARGET=Companion_Nucleo_WB55RG_ScreenAssetProvision"
    )
}
if ($EpaperSsd1681CsPort -ne '') {
    $makeArgs += "EPAPER_SSD1681_CS_PORT=$EpaperSsd1681CsPort"
}
if ($EpaperSsd1681CsPin -ne '') {
    $makeArgs += "EPAPER_SSD1681_CS_PIN=$EpaperSsd1681CsPin"
}
if ($EpaperSsd1681DcPort -ne '') {
    $makeArgs += "EPAPER_SSD1681_DC_PORT=$EpaperSsd1681DcPort"
}
if ($EpaperSsd1681DcPin -ne '') {
    $makeArgs += "EPAPER_SSD1681_DC_PIN=$EpaperSsd1681DcPin"
}
if ($EpaperSsd1681RstPort -ne '') {
    $makeArgs += "EPAPER_SSD1681_RST_PORT=$EpaperSsd1681RstPort"
}
if ($EpaperSsd1681RstPin -ne '') {
    $makeArgs += "EPAPER_SSD1681_RST_PIN=$EpaperSsd1681RstPin"
}
if ($EpaperSsd1681HasBusy -ge 0) {
    $makeArgs += "EPAPER_SSD1681_HAS_BUSY=$EpaperSsd1681HasBusy"
}
if ($EpaperSsd1681BusyPort -ne '') {
    $makeArgs += "EPAPER_SSD1681_BUSY_PORT=$EpaperSsd1681BusyPort"
}
if ($EpaperSsd1681BusyPin -ne '') {
    $makeArgs += "EPAPER_SSD1681_BUSY_PIN=$EpaperSsd1681BusyPin"
}
if ($EpaperSsd1681Bringup) {
    $makeArgs += "EPAPER_SSD1681_ROTATION=$EpaperSsd1681Rotation"
    $makeArgs += "EPAPER_SSD1681_MIRROR_X=$EpaperSsd1681MirrorX"
    $makeArgs += "EPAPER_MENU=$EpaperMenu"
}
if ($EpaperSsd1681VerboseTrace) {
    $makeArgs += @(
        "EPAPER_SSD1681_VERBOSE_TRACE=1",
        "TOUCH_VERBOSE_TRACE=1",
        "BUILD_DIR=build_verbose_trace",
        "TARGET=Companion_Nucleo_WB55RG_VerboseTrace"
    )
}
if ($Ft6336TouchThreshold -ge 0) {
    $makeArgs += "FT6336_TOUCH_THRESHOLD=0x{0:X2}u" -f $Ft6336TouchThreshold
}
if ($EpaperEmoteDemo) {
    $makeArgs += @(
        "EPAPER_EMOTE_DEMO=1",
        "BUILD_DIR=build_emote_demo",
        "TARGET=Companion_Nucleo_WB55RG_EmoteDemo"
    )
}
if ($EpaperDailyTapDemo) {
    $makeArgs += @(
        "EPAPER_DAILY_TAP_DEMO=1",
        "BUILD_DIR=build_daily_tap_demo",
        "TARGET=Companion_Nucleo_WB55RG_DailyTapDemo"
    )
}
if ($EpaperDailyStrokeDemo) {
    $dailyStrokeDirectionValue = switch ($EpaperDailyStrokeDemoDirection) {
        'left' { 1 }
        'right' { 2 }
        'up' { 3 }
        'down' { 4 }
    }
    $makeArgs += @(
        "EPAPER_DAILY_STROKE_DEMO=1",
        "EPAPER_DAILY_STROKE_DEMO_DIRECTION=$dailyStrokeDirectionValue",
        "BUILD_DIR=build_daily_stroke_demo_$EpaperDailyStrokeDemoDirection",
        "TARGET=Companion_Nucleo_WB55RG_DailyStrokeDemo_$EpaperDailyStrokeDemoDirection"
    )
}
if ($EpaperMaintenanceDiagnostic) {
    $makeArgs += @(
        "EPAPER_MAINTENANCE_DIAGNOSTIC=1",
        "BUILD_DIR=build_maintenance_diagnostic",
        "TARGET=Companion_Nucleo_WB55RG_MaintenanceDiagnostic"
    )
}
if ($EpaperRefreshCadenceDiagnostic) {
    $makeArgs += @(
        "EPAPER_REFRESH_CADENCE_DIAGNOSTIC=1",
        "EPAPER_SSD1681_VERBOSE_TRACE=1",
        "TOUCH_VERBOSE_TRACE=1",
        "BUILD_DIR=build_refresh_cadence_diagnostic",
        "TARGET=Companion_Nucleo_WB55RG_RefreshCadenceDiagnostic"
    )
}
if ($EpaperSsd1681VendorPartialDiagnostic) {
    $makeArgs += @(
        "EPAPER_REFRESH_CADENCE_DIAGNOSTIC=1",
        "EPAPER_SSD1681_VENDOR_PARTIAL_DIAGNOSTIC=1",
        "EPAPER_SSD1681_VERBOSE_TRACE=1",
        "TOUCH_VERBOSE_TRACE=1",
        "BUILD_DIR=build_vendor_partial_diagnostic",
        "TARGET=Companion_Nucleo_WB55RG_VendorPartialDiagnostic"
    )
}
if ($EpaperSsd1681DirectGpioSpiDiagnostic) {
    $makeArgs += @(
        "EPAPER_REFRESH_CADENCE_DIAGNOSTIC=1",
        "EPAPER_SSD1681_DIRECT_GPIO_SPI_DIAGNOSTIC=1",
        "EPAPER_SSD1681_VERBOSE_TRACE=1",
        "TOUCH_VERBOSE_TRACE=1",
        "BUILD_DIR=build_direct_gpio_spi_diagnostic",
        "TARGET=Companion_Nucleo_WB55RG_DirectGpioSpiDiagnostic"
    )
}
if ($EpaperSsd1681OfficialFullDiagnostic) {
    if ($EpaperSsd1681DiagnosticPattern -notin @('white', 'black')) {
        throw "Official SSD1681 full diagnostic requires -EpaperSsd1681DiagnosticPattern white or black."
    }
    $makeArgs += @(
        "EPAPER_SSD1681_OFFICIAL_FULL_DIAGNOSTIC=1",
        "EPAPER_SSD1681_VERBOSE_TRACE=1",
        "TOUCH_VERBOSE_TRACE=1",
        "BUILD_DIR=build_official_full_diagnostic_$EpaperSsd1681DiagnosticPattern",
        "TARGET=Companion_Nucleo_WB55RG_OfficialFullDiagnostic_$EpaperSsd1681DiagnosticPattern"
    )
}
if ($EpaperProductExpressionDemo) {
    $productExpressionSignal = switch ($EpaperProductExpressionDemoExpression) {
        'listening' { 'COMP_EPAPER_EXPRESSION_SIGNAL_WAKE_DETECTED' }
        'thinking' { 'COMP_EPAPER_EXPRESSION_SIGNAL_RECORDING_STOP' }
        'speaking' { 'COMP_EPAPER_EXPRESSION_SIGNAL_SPEAKER_PROMPT' }
        'happy' { 'COMP_EPAPER_EXPRESSION_SIGNAL_SPEAKER_RESULT' }
        'sleepy' { 'COMP_EPAPER_EXPRESSION_SIGNAL_SETTINGS_SLEEPY' }
        'recording' { 'COMP_EPAPER_EXPRESSION_SIGNAL_RECORDING_START' }
        'sync_complete' { 'COMP_EPAPER_EXPRESSION_SIGNAL_RECORDING_FINISHED' }
        'low_battery' { 'COMP_EPAPER_EXPRESSION_SIGNAL_LOW_BATTERY' }
        'error' { 'COMP_EPAPER_EXPRESSION_SIGNAL_ERROR' }
    }
    $productExpressionEndSignal = switch ($EpaperProductExpressionDemoExpression) {
        'recording' { 'COMP_EPAPER_EXPRESSION_SIGNAL_RECORDING_STOP' }
        'sleepy' { 'COMP_EPAPER_EXPRESSION_SIGNAL_RECOVERY' }
        'low_battery' { 'COMP_EPAPER_EXPRESSION_SIGNAL_BATTERY_RECOVERED' }
        'error' { 'COMP_EPAPER_EXPRESSION_SIGNAL_RECOVERY' }
        default { 'COMP_EPAPER_EXPRESSION_SIGNAL_COUNT' }
    }
    $makeArgs += @(
        "EPAPER_PRODUCT_EXPRESSION_DEMO=1",
        "EPAPER_PRODUCT_EXPRESSION_DEMO_SIGNAL=$productExpressionSignal",
        "EPAPER_PRODUCT_EXPRESSION_DEMO_END_SIGNAL=$productExpressionEndSignal",
        "EPAPER_PRODUCT_EXPRESSION_DEMO_END_AFTER_MS=$($EpaperProductExpressionDemoEndAfterMs)u",
        "BUILD_DIR=build_product_expression_demo",
        "TARGET=Companion_Nucleo_WB55RG_ProductExpressionDemo"
    )
}
if ($EpaperSsd1681WireProbe -ne '') {
    $wireProbe = switch ($EpaperSsd1681WireProbe) {
        'cs' { 1 }
        'dc' { 2 }
        'res' { 3 }
        'sck' { 4 }
        'mosi' { 5 }
    }
    $makeArgs += "EPAPER_SSD1681_WIRE_PROBE=$wireProbe"
    $makeArgs += "EPAPER_SSD1681_WIRE_PROBE_CYCLES=$EpaperSsd1681WireProbeCycles"
    $makeArgs += "EPAPER_SSD1681_WIRE_PROBE_DWELL_MS=$EpaperSsd1681WireProbeDwellMs"
}
if ($EpaperSsd1681DiagnosticPattern -ne '') {
    $diagnosticPattern = switch ($EpaperSsd1681DiagnosticPattern) {
        'expression' { 0 }
        'white' { 1 }
        'black' { 2 }
        'checkerboard' { 3 }
    }
    $makeArgs += "EPAPER_SSD1681_DIAGNOSTIC_PATTERN=$diagnosticPattern"
    $makeArgs += "EPAPER_SSD1681_DIAGNOSTIC_REPEATS=$EpaperSsd1681DiagnosticRepeats"
    $makeArgs += "EPAPER_SSD1681_DIAGNOSTIC_INTERVAL_MS=$EpaperSsd1681DiagnosticIntervalMs"
    if ($EpaperSsd1681DiagnosticPartial) {
        $makeArgs += "EPAPER_SSD1681_DIAGNOSTIC_PARTIAL=1"
    }
}

$buildLock = Acquire-BuildLock -RepoRoot $RepoRoot -ProjectDir $ProjectDir -MakeArgs $makeArgs
try {
    & $MakePath @makeArgs
    $buildExitCode = $LASTEXITCODE
    if ($buildExitCode -ne 0) {
        throw "bring-up build failed with exit code $buildExitCode"
    }
} finally {
    Release-BuildLock -Lock $buildLock
}
