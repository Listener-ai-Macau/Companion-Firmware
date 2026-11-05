param(
    [string]$ProjectDir = (Join-Path $PSScriptRoot '..\cubeide\Companion_Nucleo_WB55RG_Bringup'),
    [string]$MakePath = 'C:\ST\STM32CubeIDE_2.1.1\STM32CubeIDE\plugins\com.st.stm32cube.ide.mcu.externaltools.make.win32_2.2.100.202601091506\tools\bin\make.exe',
    [switch]$UseFreeRTOS,
    [switch]$OtaApp,
    [switch]$BootSelfTests,
    [ValidateRange(0, 60000)]
    [int]$LowPowerIdleDiagnosticDelayMs = 0,
    [string]$BrowserInteractionSourceManifestPath = '',
    [string]$BrowserGenerationManifestPath = '',
    [ValidateRange(-1, 60000)]
    [int]$LowPowerIdleDiagnosticWakeHoldMs = -1,
    [int]$MicPreampShift = -1,
    [ValidateSet('', 'i2s', 'pdm')]
    [string]$MicBackend = '',
    [ValidateSet('', 'falling', 'rising')]
    [string]$MicClockStrobing = '',
    [ValidateRange(-1, 46)]
    [int]$FreeRtosHeapKib = -1,
    [ValidateRange(-1, 2816)]
    [int]$RtosRecStackWords = -1,
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
    [switch]$EpaperSsd1681R7RuntimeBridgeDiagnostic,
    [switch]$EpaperSsd1681R7RuntimeContinuousDiagnostic,
    [switch]$EpaperSsd1681R7VisualRuntimeDiagnostic,
    [switch]$EpaperSsd1681R7VisualRuntimeContinuousDiagnostic,
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
    [switch]$EpaperStableDailyRecoveryDemo,
    [switch]$EpaperV9ManualStepDiagnostic,
    [switch]$EpaperDailyTapDemo,
    [switch]$EpaperDailyStrokeDemo,
    [ValidateSet('left', 'right', 'up', 'down')]
    [string]$EpaperDailyStrokeDemoDirection = 'down',
    [switch]$EpaperDailyRigDemo,
    [ValidateSet('left', 'right', 'up', 'down', 'loop')]
    [string]$EpaperDailyRigDemoDirection = 'loop',
    [switch]$EpaperV22EmotionBridgeDemo,
    [ValidateRange(0, 9)]
    [int]$EpaperV22EmotionBridgeDemoEdge = 0,
    [switch]$EpaperMaintenanceDiagnostic,
    [switch]$EpaperRefreshCadenceDiagnostic,
    [ValidateRange(1, 40)]
    [int]$EpaperRefreshCadenceDiagnosticGroups = 1,
    [switch]$EpaperSsd1681BallMotionDiagnostic,
    [switch]$EpaperSsd1681VendorPartialDiagnostic,
    [switch]$EpaperSsd1681VendorPartialOperatorLoopDiagnostic,
    [switch]$EpaperSsd1681VendorPartialMultiRegionOperatorLoopDiagnostic,
    [switch]$EpaperSsd1681VendorPartialSlowMotionDiagnostic,
    [switch]$EpaperSsd1681VendorPartialOldNewRamDiagnostic,
    [switch]$EpaperSsd1681VendorPartialCleanupDrawDiagnostic,
    [switch]$EpaperSsd1681VendorPartialCleanupDrawOperatorLoopDiagnostic,
    [switch]$EpaperSsd1681VendorPartialDrawFinalDiagnostic,
    [switch]$EpaperSsd1681VendorPartialDrawFinalOperatorLoopDiagnostic,
    [switch]$EpaperSsd1681VendorPartialNoUnionSettleDiagnostic,
    [switch]$EpaperSsd1681VendorPartialNoUnionSettleOperatorLoopDiagnostic,
    [switch]$EpaperSsd1681VendorPartialCurrentUnionOldSettleDiagnostic,
    [switch]$EpaperSsd1681VendorPartialCurrentUnionOldSettleOperatorLoopDiagnostic,
    [switch]$EpaperSsd1681VendorPartialRemovedBlackRepairCurrentUnionDiagnostic,
    [switch]$EpaperSsd1681VendorPartialRemovedBlackRepairCurrentUnionOperatorLoopDiagnostic,
    [switch]$EpaperSsd1681VendorPartialDisjointCurrentStageDiagnostic,
    [switch]$EpaperSsd1681VendorPartialDisjointCurrentStageOperatorLoopDiagnostic,
    [switch]$EpaperSsd1681VendorPartialDisjointNoUnionSettleDiagnostic,
    [switch]$EpaperSsd1681VendorPartialDisjointNoUnionSettleOperatorLoopDiagnostic,
    [switch]$EpaperSsd1681VendorPartialAddedFirstOldCleanupDiagnostic,
    [switch]$EpaperSsd1681VendorPartialAddedFirstOldCleanupOperatorLoopDiagnostic,
    [switch]$EpaperSsd1681VendorT03FastStateDiagnostic,
    [switch]$EpaperSsd1681DifferentialMultiRegionDiagnostic,
    [switch]$EpaperSsd1681Vendor1sLutDiagnostic,
    [switch]$EpaperSsd1681Vendor1sLutOperatorLoopDiagnostic,
    [switch]$EpaperSsd1681DirectGpioSpiDiagnostic,
    [switch]$EpaperSsd1681OfficialFullDiagnostic,
    [switch]$EpaperSsd1681OfficialWhiteRailProbe,
    [switch]$EpaperSsd1681ReadOnlyControllerStateDiagnostic,
    [switch]$EpaperSsd1681ResetReadControllerStateDiagnostic,
    [switch]$EpaperSsd1681RamPingPongFingerprintDiagnostic,
    [switch]$EpaperSsd1681RamCommandTargetR8Diagnostic,
    [switch]$EpaperSsd1681RamPingPongPointProbeDiagnostic,
    [switch]$EpaperSsd1681FastPointProbeDiagnostic,
    [switch]$EpaperSsd1681FastPointProbeInverseSeedDiagnostic,
    [switch]$EpaperSsd1681CustomMode2TransitionSafetyDiagnostic,
    [switch]$EpaperSsd1681CustomMode2ObservableR6Diagnostic,
    [switch]$EpaperSsd1681PhaseParallelR9Diagnostic,
    [switch]$EpaperSsd1681PhaseParallelR9ContinuousObservationDiagnostic,
    [switch]$EpaperSsd1681R10BallDiagnostic,
    [switch]$EpaperSsd1681R10NativeTwoPassFineStrideDiagnostic,
    [switch]$EpaperSsd1681R10NativeSingleUnionLargeCadenceDiagnostic,
    [switch]$EpaperSsd1681R10NativeGuardedCorridorLargeCadenceDiagnostic,
    [switch]$EpaperSsd1681R10NativeGuardedCorridorNoResetCadenceDiagnostic,
    [switch]$EpaperSsd1681R10NativeGuardedCorridorCachedMode2CadenceDiagnostic,
    [switch]$EpaperSsd1681R11NativeCachedMode2ThrowArcDiagnostic,
    [switch]$EpaperSsd1681R12V22CalmCuriousWarmSamplerDiagnostic,
    [switch]$EpaperSsd1681DualPlaneWhiteCleanDiagnostic,
    [switch]$EpaperSsd1681SingleFlashWhiteCleanupDiagnostic,
    [switch]$EpaperSsd1681R7LockedV9ChoreographyDiagnostic,
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
            return $false
        }
        $process = Get-Process -Id ([int]$owner.pid) -ErrorAction SilentlyContinue
        return $null -ne $process
    } catch {
        # The lock directory is created before owner.json is populated. If a
        # build is interrupted in that narrow window, an empty/corrupt owner
        # file must not become an immortal lock. Acquire-BuildLock still
        # validates the exact lock path before removing it.
        return $false
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
# Product image layout: always OTA App at 0x08007000 unless an isolated
# diagnostic explicitly opts into ALLOW_LEGACY_DIRECT_APP via Makefile.
# FreeRTOS product builds must NEVER produce a 0x08000000 hex — that overwrites
# the resident OTA Loader when passed raw to CubeProgrammer.
$productOtaAppExpected = $true
if ($UseFreeRTOS) {
    $makeArgs += @(
        "COMPANION_USE_FREERTOS=1",
        "OTA_APP=1",
        "BUILD_DIR=build_freertos",
        "TARGET=Companion_Nucleo_WB55RG_FreeRTOS",
        "C_OPT=-Os",
        # This is the Companion product image, not the legacy procedural UI.
        # Keep the browser export, generated contract headers and panel runtime
        # on the same dependency graph for every FreeRTOS OTA App build.
        "EPAPER_SSD1681_BRINGUP=1",
        "EPAPER_SSD1681_ACCEPTED_CACHED_MODE2_PRODUCT=1",
        "EPAPER_COMP_REQ_638_SOURCE_PACK=1",
        "EPAPER_MENU=1",
        "EPAPER_SSD1681_DIRECT_GPIO_SPI_DIAGNOSTIC=1",
        "EPAPER_SSD1681_HAS_BUSY=1",
        "EPAPER_SSD1681_USE_SOFTWARE_SPI=1",
        "EPAPER_SSD1681_DIRECT_GPIO_SPI_NOP_COUNT=0",
        "BROWSER_SOURCE_PACK_REPO_PATH=.cache/validation/comp-req-775-menu-hold-milestone-source-pack-v3",
        "BROWSER_CEMP_CONTRACT_PREGENERATED=1"
    )
    if ([string]::IsNullOrWhiteSpace($BrowserInteractionSourceManifestPath) -ne
        [string]::IsNullOrWhiteSpace($BrowserGenerationManifestPath)) {
        throw 'Browser interaction source and generation manifests must be supplied together.'
    }
    if (-not [string]::IsNullOrWhiteSpace($BrowserInteractionSourceManifestPath)) {
        $interactionManifest = Get-NormalizedPath -Path $BrowserInteractionSourceManifestPath
        $generationManifest = Get-NormalizedPath -Path $BrowserGenerationManifestPath
        if (-not (Test-Path -LiteralPath $interactionManifest -PathType Leaf)) {
            throw "Browser interaction source manifest not found: $interactionManifest"
        }
        if (-not (Test-Path -LiteralPath $generationManifest -PathType Leaf)) {
            throw "Browser generation manifest not found: $generationManifest"
        }
        if (-not (Test-PathUnderRoot -Path $interactionManifest -Root $RepoRoot)) {
            throw "Browser interaction source manifest must stay under the repository: $interactionManifest"
        }
        if (-not (Test-PathUnderRoot -Path $generationManifest -Root $RepoRoot)) {
            throw "Browser generation manifest must stay under the repository: $generationManifest"
        }
        $makeArgs += "BROWSER_INTERACTION_SOURCE_MANIFEST=$interactionManifest"
    }
}
if (@($EpaperSsd1681ReadOnlyControllerStateDiagnostic,
      $EpaperSsd1681ResetReadControllerStateDiagnostic,
      $EpaperSsd1681RamPingPongFingerprintDiagnostic,
      $EpaperSsd1681RamCommandTargetR8Diagnostic,
      $EpaperSsd1681RamPingPongPointProbeDiagnostic,
      $EpaperSsd1681FastPointProbeDiagnostic,
      $EpaperSsd1681FastPointProbeInverseSeedDiagnostic,
      $EpaperSsd1681CustomMode2TransitionSafetyDiagnostic,
      $EpaperSsd1681CustomMode2ObservableR6Diagnostic,
      $EpaperSsd1681PhaseParallelR9Diagnostic,
      $EpaperSsd1681PhaseParallelR9ContinuousObservationDiagnostic,
      $EpaperSsd1681R10BallDiagnostic,
      $EpaperSsd1681R10NativeTwoPassFineStrideDiagnostic,
      $EpaperSsd1681R10NativeSingleUnionLargeCadenceDiagnostic,
      $EpaperSsd1681R10NativeGuardedCorridorLargeCadenceDiagnostic,
      $EpaperSsd1681R10NativeGuardedCorridorNoResetCadenceDiagnostic,
      $EpaperSsd1681R10NativeGuardedCorridorCachedMode2CadenceDiagnostic,
      $EpaperSsd1681R11NativeCachedMode2ThrowArcDiagnostic).Where({ $_ }).Count -gt 1) {
    throw "Choose exactly one SSD1681 isolated lower-driver diagnostic."
}
if ($EpaperSsd1681ReadOnlyControllerStateDiagnostic -or
    $EpaperSsd1681ResetReadControllerStateDiagnostic -or
    $EpaperSsd1681RamPingPongFingerprintDiagnostic -or
    $EpaperSsd1681RamCommandTargetR8Diagnostic -or
    $EpaperSsd1681RamPingPongPointProbeDiagnostic -or
    $EpaperSsd1681FastPointProbeDiagnostic -or
    $EpaperSsd1681FastPointProbeInverseSeedDiagnostic -or
    $EpaperSsd1681CustomMode2TransitionSafetyDiagnostic -or
    $EpaperSsd1681CustomMode2ObservableR6Diagnostic -or
    $EpaperSsd1681PhaseParallelR9Diagnostic -or
    $EpaperSsd1681PhaseParallelR9ContinuousObservationDiagnostic -or
    $EpaperSsd1681R10BallDiagnostic -or
    $EpaperSsd1681R10NativeTwoPassFineStrideDiagnostic -or
    $EpaperSsd1681R10NativeSingleUnionLargeCadenceDiagnostic -or
    $EpaperSsd1681R10NativeGuardedCorridorLargeCadenceDiagnostic -or
    $EpaperSsd1681R10NativeGuardedCorridorNoResetCadenceDiagnostic -or
    $EpaperSsd1681R10NativeGuardedCorridorCachedMode2CadenceDiagnostic -or
    $EpaperSsd1681R11NativeCachedMode2ThrowArcDiagnostic) {
    $allowedReadOnlyArguments = @(
        "ProjectDir",
        "MakePath",
        "EpaperSsd1681ReadOnlyControllerStateDiagnostic",
        "EpaperSsd1681ResetReadControllerStateDiagnostic",
        "EpaperSsd1681RamPingPongFingerprintDiagnostic",
        "EpaperSsd1681RamCommandTargetR8Diagnostic",
        "EpaperSsd1681RamPingPongPointProbeDiagnostic",
        "EpaperSsd1681FastPointProbeDiagnostic",
        "EpaperSsd1681FastPointProbeInverseSeedDiagnostic",
        "EpaperSsd1681CustomMode2TransitionSafetyDiagnostic",
        "EpaperSsd1681CustomMode2ObservableR6Diagnostic",
        "EpaperSsd1681PhaseParallelR9Diagnostic",
        "EpaperSsd1681PhaseParallelR9ContinuousObservationDiagnostic",
        "EpaperSsd1681R10BallDiagnostic",
        "EpaperSsd1681R10NativeTwoPassFineStrideDiagnostic",
        "EpaperSsd1681R10NativeSingleUnionLargeCadenceDiagnostic",
        "EpaperSsd1681R10NativeGuardedCorridorLargeCadenceDiagnostic",
        "EpaperSsd1681R10NativeGuardedCorridorNoResetCadenceDiagnostic",
        "EpaperSsd1681R10NativeGuardedCorridorCachedMode2CadenceDiagnostic",
        "EpaperSsd1681R11NativeCachedMode2ThrowArcDiagnostic",
        "Force"
    )
    $conflictingArguments = @($PSBoundParameters.Keys | Where-Object {
        $_ -notin $allowedReadOnlyArguments
    })
    if ($conflictingArguments.Count -ne 0) {
        throw "Read-only controller-state diagnostic is isolated; conflicting arguments: $($conflictingArguments -join ', ')."
    }
}
if (($EpaperSsd1681VendorPartialDiagnostic -and ($EpaperSsd1681DirectGpioSpiDiagnostic -or $EpaperSsd1681VendorPartialOperatorLoopDiagnostic -or $EpaperSsd1681VendorPartialMultiRegionOperatorLoopDiagnostic -or $EpaperSsd1681VendorPartialSlowMotionDiagnostic)) -or
    ($EpaperSsd1681VendorPartialOperatorLoopDiagnostic -and
     ($EpaperSsd1681DirectGpioSpiDiagnostic -or $EpaperSsd1681Vendor1sLutDiagnostic -or $EpaperSsd1681VendorPartialMultiRegionOperatorLoopDiagnostic -or $EpaperSsd1681VendorPartialSlowMotionDiagnostic)) -or
    ($EpaperSsd1681VendorPartialMultiRegionOperatorLoopDiagnostic -and
     ($EpaperSsd1681DirectGpioSpiDiagnostic -or $EpaperSsd1681Vendor1sLutDiagnostic -or $EpaperSsd1681VendorPartialSlowMotionDiagnostic)) -or
    ($EpaperSsd1681VendorPartialSlowMotionDiagnostic -and
     ($EpaperSsd1681DirectGpioSpiDiagnostic -or $EpaperSsd1681Vendor1sLutDiagnostic)) -or
    (($EpaperSsd1681Vendor1sLutDiagnostic -or $EpaperSsd1681Vendor1sLutOperatorLoopDiagnostic) -and
     ($EpaperSsd1681VendorPartialDiagnostic -or $EpaperSsd1681VendorPartialOperatorLoopDiagnostic -or $EpaperSsd1681VendorPartialMultiRegionOperatorLoopDiagnostic -or $EpaperSsd1681VendorPartialSlowMotionDiagnostic -or $EpaperSsd1681DirectGpioSpiDiagnostic)) -or
    ($EpaperSsd1681Vendor1sLutDiagnostic -and $EpaperSsd1681Vendor1sLutOperatorLoopDiagnostic)) {
    throw "Choose one isolated SSD1681 diagnostic at a time."
}
if ($EpaperSsd1681DifferentialMultiRegionDiagnostic -and
    ($EpaperSsd1681VendorPartialDiagnostic -or $EpaperSsd1681VendorPartialOperatorLoopDiagnostic -or
     $EpaperSsd1681VendorPartialMultiRegionOperatorLoopDiagnostic -or $EpaperSsd1681VendorPartialSlowMotionDiagnostic -or
     $EpaperSsd1681Vendor1sLutDiagnostic -or $EpaperSsd1681Vendor1sLutOperatorLoopDiagnostic -or
     $EpaperSsd1681DirectGpioSpiDiagnostic -or $EpaperSsd1681OfficialFullDiagnostic -or
     $EpaperSsd1681OfficialWhiteRailProbe -or $EpaperSsd1681BallMotionDiagnostic -or
     $EpaperRefreshCadenceDiagnostic -or $EpaperSsd1681DiagnosticPattern -ne '' -or
     $EpaperSsd1681DiagnosticPartial -or $ScreenAssetProvision -or $EpaperProductExpressionDemo)) {
    throw "Differential multi-region is an isolated source-bound transport diagnostic."
}
if ($Force -or $LowPowerIdleDiagnosticDelayMs -gt 0 -or $EpaperDailyTapDemo -or $EpaperDailyStrokeDemo -or $EpaperDailyRigDemo -or $EpaperStableDailyRecoveryDemo -or $EpaperMaintenanceDiagnostic -or $EpaperRefreshCadenceDiagnostic -or $EpaperSsd1681VendorPartialDiagnostic -or $EpaperSsd1681VendorPartialOperatorLoopDiagnostic -or $EpaperSsd1681VendorPartialMultiRegionOperatorLoopDiagnostic -or $EpaperSsd1681VendorPartialSlowMotionDiagnostic -or $EpaperSsd1681VendorPartialDisjointCurrentStageDiagnostic -or $EpaperSsd1681VendorPartialDisjointCurrentStageOperatorLoopDiagnostic -or $EpaperSsd1681DifferentialMultiRegionDiagnostic -or $EpaperSsd1681Vendor1sLutDiagnostic -or $EpaperSsd1681Vendor1sLutOperatorLoopDiagnostic -or $EpaperSsd1681DirectGpioSpiDiagnostic -or $EpaperSsd1681OfficialFullDiagnostic -or $EpaperSsd1681OfficialWhiteRailProbe -or $EpaperSsd1681ReadOnlyControllerStateDiagnostic -or $EpaperSsd1681ResetReadControllerStateDiagnostic -or $EpaperSsd1681RamPingPongFingerprintDiagnostic -or $EpaperSsd1681RamCommandTargetR8Diagnostic -or $EpaperSsd1681RamPingPongPointProbeDiagnostic -or $EpaperSsd1681FastPointProbeDiagnostic -or $EpaperSsd1681FastPointProbeInverseSeedDiagnostic -or $EpaperSsd1681CustomMode2TransitionSafetyDiagnostic -or $EpaperSsd1681CustomMode2ObservableR6Diagnostic -or $EpaperSsd1681PhaseParallelR9Diagnostic -or $EpaperSsd1681PhaseParallelR9ContinuousObservationDiagnostic -or $EpaperSsd1681R10BallDiagnostic -or $EpaperSsd1681VerboseTrace -or $Ft6336TouchThreshold -ge 0 -or $EpaperProductExpressionDemo) {
    $makeArgs += "-B"
}
if ($OtaApp) {
    if ($UseFreeRTOS) {
        # FreeRTOS already forced OTA_APP=1 + build_freertos; keep that product dir.
        $makeArgs += @("OTA_APP=1")
    } else {
        $makeArgs += @(
            "OTA_APP=1",
            "BUILD_DIR=build_ota",
            "TARGET=Companion_Nucleo_WB55RG_Bringup_ota_app"
        )
    }
}
if ($BootSelfTests) {
    $makeArgs += "BOOT_SELFTESTS=1"
}
if ($LowPowerIdleDiagnosticDelayMs -gt 0) {
    if (-not $UseFreeRTOS) {
        throw "LowPowerIdleDiagnosticDelayMs is supported only by the FreeRTOS product OTA App build."
    }
    $makeArgs += "LOW_POWER_IDLE_DIAGNOSTIC_DELAY_MS=$LowPowerIdleDiagnosticDelayMs"
}
if ($LowPowerIdleDiagnosticWakeHoldMs -ge 0) {
    if (-not $UseFreeRTOS -or -not $OtaApp -or $LowPowerIdleDiagnosticDelayMs -le 0) {
        throw "LowPowerIdleDiagnosticWakeHoldMs requires the FreeRTOS OTA App diagnostic-delay build."
    }
    $makeArgs += "LOW_POWER_IDLE_DIAGNOSTIC_WAKE_HOLD_MS=$LowPowerIdleDiagnosticWakeHoldMs"
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
if ($MicClockStrobing -eq 'falling') {
    $makeArgs += "MIC_CLOCK_STROBING=SAI_CLOCKSTROBING_FALLINGEDGE"
} elseif ($MicClockStrobing -eq 'rising') {
    $makeArgs += "MIC_CLOCK_STROBING=SAI_CLOCKSTROBING_RISINGEDGE"
}
if ($FreeRtosHeapKib -ge 0) {
    if ($FreeRtosHeapKib -lt 32) {
        throw "FreeRtosHeapKib must be between 32 and 46."
    }
    $makeArgs += "FREERTOS_HEAP_KIB=$FreeRtosHeapKib"
}
if ($RtosRecStackWords -ge 0) {
    if ($RtosRecStackWords -lt 1024) {
        throw "RtosRecStackWords must be between 1024 and 2816."
    }
    $makeArgs += "RTOS_REC_STACK_WORDS=$RtosRecStackWords"
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
if ($EpaperSsd1681Bringup -or $EpaperSsd1681DifferentialMultiRegionDiagnostic -or $EpaperSsd1681VendorPartialDisjointCurrentStageDiagnostic -or $EpaperSsd1681VendorPartialDisjointCurrentStageOperatorLoopDiagnostic -or $EpaperSsd1681Vendor1sLutDiagnostic -or $EpaperSsd1681OfficialWhiteRailProbe -or $EpaperSsd1681ReadOnlyControllerStateDiagnostic -or $EpaperSsd1681ResetReadControllerStateDiagnostic -or $EpaperSsd1681RamPingPongFingerprintDiagnostic -or $EpaperSsd1681RamCommandTargetR8Diagnostic -or $EpaperSsd1681RamPingPongPointProbeDiagnostic -or $EpaperSsd1681FastPointProbeDiagnostic -or $EpaperSsd1681FastPointProbeInverseSeedDiagnostic -or $EpaperSsd1681CustomMode2TransitionSafetyDiagnostic -or $EpaperSsd1681CustomMode2ObservableR6Diagnostic -or $EpaperSsd1681PhaseParallelR9Diagnostic -or $EpaperSsd1681PhaseParallelR9ContinuousObservationDiagnostic -or $EpaperSsd1681R10BallDiagnostic -or $EpaperSsd1681R10NativeTwoPassFineStrideDiagnostic -or $EpaperSsd1681R10NativeSingleUnionLargeCadenceDiagnostic -or $EpaperSsd1681R10NativeGuardedCorridorLargeCadenceDiagnostic -or $EpaperSsd1681R10NativeGuardedCorridorNoResetCadenceDiagnostic -or $EpaperSsd1681VerboseTrace) {
    $makeArgs += "EPAPER_SSD1681_BRINGUP=1"
}
if ($EpaperV22EmotionBridgeDemo -and $EpaperDailyRigDemo) {
    throw "V22 emotion-bridge demo and the historical Daily Rig demo are mutually exclusive."
}
if ($EpaperV22EmotionBridgeDemo -and -not $ScreenAssetProvision) {
    throw "V22 emotion-bridge demo requires -ScreenAssetProvision so its candidate CRIG remains an explicit one-shot external-NOR payload."
}
if ($EpaperStableDailyRecoveryDemo -and -not $ScreenAssetProvision) {
    throw "Stable Daily recovery requires -ScreenAssetProvision so the exact locked V9 CEMP is an explicit one-shot external-NOR payload."
}
if ($EpaperV9ManualStepDiagnostic -and -not $ScreenAssetProvision) {
    throw "V9 manual-step diagnostic requires -ScreenAssetProvision so every press uses the exact locked V9 CEMP."
}
if (($EpaperStableDailyRecoveryDemo -or $EpaperV9ManualStepDiagnostic) -and ($EpaperEmoteDemo -or $EpaperDailyTapDemo -or $EpaperDailyStrokeDemo -or $EpaperDailyRigDemo -or $EpaperV22EmotionBridgeDemo -or $EpaperProductExpressionDemo)) {
    throw "The stable V9 recovery and V9 manual-step diagnostic builds cannot share another expression or Rig demo."
}
if ($EpaperStableDailyRecoveryDemo -and $EpaperV9ManualStepDiagnostic) {
    throw "Stable Daily recovery and V9 manual-step diagnostic are separate production-off images."
}
if ($ScreenAssetProvision) {
    if ($Optimization -eq '') {
        # This one-shot writer embeds the external CEMP pack in MCU Flash.
        # Keep the normal product build at its default optimization level.
        $makeArgs += "C_OPT=-Os"
    }
    if ($EpaperV9ManualStepDiagnostic) {
        $makeArgs += @(
            "EPAPER_SSD1681_BRINGUP=1",
            "EPAPER_MENU=$EpaperMenu",
            "EPAPER_V9_MANUAL_STEP_DIAGNOSTIC=1",
            "EPAPER_SSD1681_VERBOSE_TRACE=1",
            "TOUCH_VERBOSE_TRACE=1",
            "SCREEN_ASSET_PROVISION=1",
            "BUILD_DIR=build_v9_manual_step_diagnostic",
            "TARGET=Companion_Nucleo_WB55RG_V9ManualStepDiagnostic"
        )
    } elseif ($EpaperStableDailyRecoveryDemo) {
        $makeArgs += @(
            "EPAPER_SSD1681_BRINGUP=1",
            "EPAPER_MENU=$EpaperMenu",
            "EPAPER_STABLE_DAILY_RECOVERY_DEMO=1",
            "SCREEN_ASSET_PROVISION=1",
            "BUILD_DIR=build_v9_stable_daily_recovery",
            "TARGET=Companion_Nucleo_WB55RG_V9StableDailyRecovery"
        )
    } elseif ($EpaperV22EmotionBridgeDemo) {
        $makeArgs += @(
            "EPAPER_SSD1681_BRINGUP=1",
            "EPAPER_MENU=$EpaperMenu",
            "EPAPER_V22_EMOTION_BRIDGE_DEMO=1",
            "EPAPER_V22_EMOTION_BRIDGE_DEMO_EDGE=$EpaperV22EmotionBridgeDemoEdge",
            "SCREEN_ASSET_PROVISION=1",
            "BUILD_DIR=build_v22_emotion_bridge_demo_$EpaperV22EmotionBridgeDemoEdge",
            "TARGET=Companion_Nucleo_WB55RG_V22EmotionBridgeDemo_$EpaperV22EmotionBridgeDemoEdge"
        )
    } elseif ($EpaperDailyRigDemo) {
        $dailyRigDirectionValue = switch ($EpaperDailyRigDemoDirection) {
            'left' { 1 }
            'right' { 2 }
            'up' { 3 }
            'down' { 4 }
            'loop' { 0 }
        }
        $makeArgs += @(
            "EPAPER_SSD1681_BRINGUP=1",
            "EPAPER_MENU=$EpaperMenu",
            "EPAPER_DAILY_RIG_DEMO=1",
            "EPAPER_DAILY_RIG_DEMO_DIRECTION=$dailyRigDirectionValue",
            "SCREEN_ASSET_PROVISION=1",
            "BUILD_DIR=build_daily_rig_screen_asset_provision_$EpaperDailyRigDemoDirection",
            "TARGET=Companion_Nucleo_WB55RG_DailyRigScreenAssetProvision_$EpaperDailyRigDemoDirection"
        )
    } else {
        $makeArgs += @(
            "EPAPER_SSD1681_BRINGUP=1",
            "EPAPER_MENU=$EpaperMenu",
            "SCREEN_ASSET_PROVISION=1",
            "BUILD_DIR=build_screen_asset_provision",
            "TARGET=Companion_Nucleo_WB55RG_ScreenAssetProvision"
        )
    }
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
if ($EpaperSsd1681Bringup -or $EpaperSsd1681DifferentialMultiRegionDiagnostic -or $EpaperSsd1681VendorPartialDisjointCurrentStageDiagnostic -or $EpaperSsd1681VendorPartialDisjointCurrentStageOperatorLoopDiagnostic -or $EpaperSsd1681VendorPartialDisjointNoUnionSettleDiagnostic -or $EpaperSsd1681VendorPartialDisjointNoUnionSettleOperatorLoopDiagnostic -or $EpaperSsd1681VendorPartialAddedFirstOldCleanupDiagnostic -or $EpaperSsd1681VendorPartialAddedFirstOldCleanupOperatorLoopDiagnostic -or $EpaperSsd1681OfficialWhiteRailProbe -or $EpaperSsd1681VerboseTrace -or $EpaperSsd1681VendorPartialOperatorLoopDiagnostic -or $EpaperSsd1681VendorPartialMultiRegionOperatorLoopDiagnostic -or $EpaperSsd1681VendorPartialSlowMotionDiagnostic -or $EpaperSsd1681Vendor1sLutDiagnostic -or $EpaperSsd1681Vendor1sLutOperatorLoopDiagnostic) {
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
    $cadenceBuildDir = if ($EpaperRefreshCadenceDiagnosticGroups -eq 1) {
        "build_refresh_cadence_diagnostic"
    } else {
        "build_refresh_cadence_diagnostic_g$EpaperRefreshCadenceDiagnosticGroups"
    }
    $cadenceTarget = if ($EpaperRefreshCadenceDiagnosticGroups -eq 1) {
        "Companion_Nucleo_WB55RG_RefreshCadenceDiagnostic"
    } else {
        "Companion_Nucleo_WB55RG_RefreshCadenceDiagnosticG$EpaperRefreshCadenceDiagnosticGroups"
    }
    $makeArgs += @(
        "EPAPER_SSD1681_BRINGUP=1",
        "EPAPER_MENU=1",
        "EPAPER_REFRESH_CADENCE_DIAGNOSTIC=1",
        "EPAPER_REFRESH_CADENCE_DIAGNOSTIC_GROUPS=$EpaperRefreshCadenceDiagnosticGroups",
        "EPAPER_SSD1681_CADENCE_MICRO_MOTION_DIAGNOSTIC=1",
        "EPAPER_SSD1681_DIAGNOSTIC_PATTERN=5",
        "EPAPER_SSD1681_VERBOSE_TRACE=1",
        "TOUCH_VERBOSE_TRACE=1",
        "BUILD_DIR=$cadenceBuildDir",
        "TARGET=$cadenceTarget"
    )
}
if ($EpaperDailyRigDemo -and -not $ScreenAssetProvision) {
    $dailyRigDirectionValue = switch ($EpaperDailyRigDemoDirection) {
        'left' { 1 }
        'right' { 2 }
        'up' { 3 }
        'down' { 4 }
        'loop' { 0 }
    }
    $makeArgs += @(
        "EPAPER_DAILY_RIG_DEMO=1",
        "EPAPER_DAILY_RIG_DEMO_DIRECTION=$dailyRigDirectionValue",
        "BUILD_DIR=build_daily_rig_demo_$EpaperDailyRigDemoDirection",
        "TARGET=Companion_Nucleo_WB55RG_DailyRigDemo_$EpaperDailyRigDemoDirection"
    )
}
if ($EpaperSsd1681BallMotionDiagnostic) {
    if ($EpaperSsd1681DiagnosticPattern -ne '' -or
         $EpaperRefreshCadenceDiagnostic -or
         $EpaperSsd1681VendorPartialDiagnostic -or
         $EpaperSsd1681VendorPartialOperatorLoopDiagnostic -or
         $EpaperSsd1681VendorPartialMultiRegionOperatorLoopDiagnostic -or
         $EpaperSsd1681Vendor1sLutDiagnostic -or
         $EpaperSsd1681Vendor1sLutOperatorLoopDiagnostic -or
         $EpaperSsd1681DirectGpioSpiDiagnostic -or
        $EpaperSsd1681OfficialFullDiagnostic -or
        $EpaperSsd1681OfficialWhiteRailProbe) {
        throw "Ball-motion diagnostic is an isolated current-profile image; do not combine it with another screen diagnostic."
    }
    $makeArgs += @(
        "EPAPER_SSD1681_BRINGUP=1",
        "EPAPER_MENU=1",
        "EPAPER_SSD1681_BALL_MOTION_DIAGNOSTIC=1",
        "EPAPER_SSD1681_VERBOSE_TRACE=1",
        "TOUCH_VERBOSE_TRACE=1",
        "BUILD_DIR=build_ball_motion_diagnostic",
        "TARGET=Companion_Nucleo_WB55RG_BallMotionDiagnostic"
    )
}
if ($EpaperSsd1681OfficialWhiteRailProbe) {
    if ($EpaperSsd1681OfficialFullDiagnostic -or $EpaperSsd1681VendorPartialOperatorLoopDiagnostic -or $EpaperSsd1681VendorPartialMultiRegionOperatorLoopDiagnostic -or $EpaperSsd1681Vendor1sLutDiagnostic -or $EpaperSsd1681Vendor1sLutOperatorLoopDiagnostic -or
        $EpaperSsd1681DiagnosticPattern -ne '' -or
        $EpaperSsd1681DiagnosticPartial -or
        $EpaperSsd1681DiagnosticRepeats -ne 1 -or
        $EpaperSsd1681DiagnosticIntervalMs -ne 0) {
        throw "Official White rail probe has a fixed isolated profile; do not combine it with another diagnostic option."
    }
    $makeArgs += @(
        "EPAPER_SSD1681_BRINGUP=1",
        "EPAPER_SSD1681_OFFICIAL_FULL_DIAGNOSTIC=1",
        "EPAPER_SSD1681_VERBOSE_TRACE=1",
        "TOUCH_VERBOSE_TRACE=1",
        "EPAPER_SSD1681_DIAGNOSTIC_PATTERN=1",
        "EPAPER_SSD1681_DIAGNOSTIC_REPEATS=30",
        "EPAPER_SSD1681_DIAGNOSTIC_INTERVAL_MS=5000",
        "BUILD_DIR=build_official_full_rail_probe_white",
        "TARGET=Companion_Nucleo_WB55RG_OfficialFullRailProbeWhite"
    )
}
if ($EpaperSsd1681ReadOnlyControllerStateDiagnostic) {
    $makeArgs += @(
        "EPAPER_SSD1681_BRINGUP=1",
        "EPAPER_SSD1681_READ_ONLY_CONTROLLER_STATE_DIAGNOSTIC=1",
        "BUILD_DIR=build_ssd1681_read_only_controller_state",
        "TARGET=Companion_Nucleo_WB55RG_Ssd1681ReadOnlyControllerState"
    )
}
if ($EpaperSsd1681ResetReadControllerStateDiagnostic) {
    $makeArgs += @(
        "EPAPER_SSD1681_BRINGUP=1",
        "EPAPER_SSD1681_RESET_READ_CONTROLLER_STATE_DIAGNOSTIC=1",
        "BUILD_DIR=build_ssd1681_reset_read_controller_state",
        "TARGET=Companion_Nucleo_WB55RG_Ssd1681ResetReadControllerState"
    )
}
if ($EpaperSsd1681RamPingPongFingerprintDiagnostic) {
    $makeArgs += @(
        "EPAPER_SSD1681_BRINGUP=1",
        "EPAPER_SSD1681_RAM_PING_PONG_FINGERPRINT_DIAGNOSTIC=1",
        "BUILD_DIR=build_ssd1681_ram_ping_pong_fingerprint",
        "TARGET=Companion_Nucleo_WB55RG_Ssd1681RamPingPongFingerprint"
    )
}
if ($EpaperSsd1681RamCommandTargetR8Diagnostic) {
    $makeArgs += @(
        "EPAPER_SSD1681_BRINGUP=1",
        "EPAPER_SSD1681_RAM_COMMAND_TARGET_R8_DIAGNOSTIC=1",
        "BUILD_DIR=build_ssd1681_ram_command_target_r8",
        "TARGET=Companion_Nucleo_WB55RG_Ssd1681RamCommandTargetR8"
    )
}
if ($EpaperSsd1681RamPingPongPointProbeDiagnostic) {
    $makeArgs += @(
        "EPAPER_SSD1681_BRINGUP=1",
        "EPAPER_SSD1681_RAM_PING_PONG_POINT_PROBE_DIAGNOSTIC=1",
        "BUILD_DIR=build_ssd1681_ram_ping_pong_point_probe",
        "TARGET=Companion_Nucleo_WB55RG_Ssd1681RamPingPongPointProbe"
    )
}
if ($EpaperSsd1681FastPointProbeDiagnostic) {
    $makeArgs += @(
        "EPAPER_SSD1681_BRINGUP=1",
        "EPAPER_SSD1681_FAST_POINT_PROBE_DIAGNOSTIC=1",
        "BUILD_DIR=build_ssd1681_fast_point_probe",
        "TARGET=Companion_Nucleo_WB55RG_Ssd1681FastPointProbe"
    )
}
if ($EpaperSsd1681FastPointProbeInverseSeedDiagnostic) {
    $makeArgs += @(
        "EPAPER_SSD1681_BRINGUP=1",
        "EPAPER_SSD1681_FAST_POINT_PROBE_INVERSE_SEED_DIAGNOSTIC=1",
        "BUILD_DIR=build_ssd1681_fast_point_probe_inverse_seed",
        "TARGET=Companion_Nucleo_WB55RG_Ssd1681FastPointProbeInverseSeed"
    )
}
if ($EpaperSsd1681CustomMode2TransitionSafetyDiagnostic) {
    $makeArgs += @(
        "EPAPER_SSD1681_BRINGUP=1",
        "EPAPER_SSD1681_CUSTOM_MODE2_TRANSITION_SAFETY_DIAGNOSTIC=1",
        "BUILD_DIR=build_ssd1681_custom_mode2_transition_safety",
        "TARGET=Companion_Nucleo_WB55RG_Ssd1681CustomMode2TransitionSafety"
    )
}
if ($EpaperSsd1681CustomMode2ObservableR6Diagnostic) {
    $makeArgs += @(
        "EPAPER_SSD1681_BRINGUP=1",
        "EPAPER_SSD1681_CUSTOM_MODE2_OBSERVABLE_R6_DIAGNOSTIC=1",
        "BUILD_DIR=build_ssd1681_custom_mode2_observable_r6",
        "TARGET=Companion_Nucleo_WB55RG_Ssd1681CustomMode2ObservableR6"
    )
}
if ($EpaperSsd1681PhaseParallelR9Diagnostic) {
    $makeArgs += @(
        "EPAPER_SSD1681_BRINGUP=1",
        "EPAPER_SSD1681_PHASE_PARALLEL_R9_DIAGNOSTIC=1",
        "BUILD_DIR=build_ssd1681_phase_parallel_r9",
        "TARGET=Companion_Nucleo_WB55RG_Ssd1681PhaseParallelR9"
    )
}
if ($EpaperSsd1681PhaseParallelR9ContinuousObservationDiagnostic) {
    $makeArgs += @(
        "EPAPER_SSD1681_BRINGUP=1",
        "EPAPER_SSD1681_PHASE_PARALLEL_R9_CONTINUOUS_OBSERVATION_DIAGNOSTIC=1",
        "BUILD_DIR=build_ssd1681_phase_parallel_r9_continuous_observation",
        "TARGET=Companion_Nucleo_WB55RG_Ssd1681PhaseParallelR9ContinuousObservation"
    )
}
if ($EpaperSsd1681R10BallDiagnostic) {
    $makeArgs += @(
        "EPAPER_SSD1681_BRINGUP=1",
        "EPAPER_SSD1681_R10_BALL_DIAGNOSTIC=1",
        "BUILD_DIR=build_ssd1681_r10_ball",
        "TARGET=Companion_Nucleo_WB55RG_Ssd1681R10Ball"
    )
}
if ($EpaperSsd1681R10NativeTwoPassFineStrideDiagnostic) {
    $makeArgs += @(
        "EPAPER_SSD1681_BRINGUP=1",
        "EPAPER_SSD1681_R10_NATIVE_TWO_PASS_FINE_STRIDE_DIAGNOSTIC=1",
        "BUILD_DIR=build_ssd1681_r10_native_two_pass_fine_stride",
        "TARGET=Companion_Nucleo_WB55RG_Ssd1681R10NativeTwoPassFineStride"
    )
}
if ($EpaperSsd1681R10NativeSingleUnionLargeCadenceDiagnostic) {
    $makeArgs += @(
        "EPAPER_SSD1681_BRINGUP=1",
        "EPAPER_SSD1681_R10_NATIVE_SINGLE_UNION_LARGE_CADENCE_DIAGNOSTIC=1",
        "BUILD_DIR=build_ssd1681_r10_native_single_union_large_cadence",
        "TARGET=Companion_Nucleo_WB55RG_Ssd1681R10NativeSingleUnionLargeCadence"
    )
}
if ($EpaperSsd1681R10NativeGuardedCorridorLargeCadenceDiagnostic) {
    $makeArgs += @(
        "EPAPER_SSD1681_BRINGUP=1",
        "EPAPER_SSD1681_R10_NATIVE_GUARDED_CORRIDOR_LARGE_CADENCE_DIAGNOSTIC=1",
        "BUILD_DIR=build_ssd1681_r10_native_guarded_corridor_large_cadence",
        "TARGET=Companion_Nucleo_WB55RG_Ssd1681R10NativeGuardedCorridorLargeCadence"
    )
}
if ($EpaperSsd1681R10NativeGuardedCorridorNoResetCadenceDiagnostic) {
    $makeArgs += @(
        "EPAPER_SSD1681_BRINGUP=1",
        "EPAPER_SSD1681_R10_NATIVE_GUARDED_CORRIDOR_NO_RESET_CADENCE_DIAGNOSTIC=1",
        "BUILD_DIR=build_ssd1681_r10_native_guarded_corridor_no_reset_cadence",
        "TARGET=Companion_Nucleo_WB55RG_Ssd1681R10NativeGuardedCorridorNoResetCadence"
    )
}
if ($EpaperSsd1681R10NativeGuardedCorridorCachedMode2CadenceDiagnostic) {
    $makeArgs += @(
        "EPAPER_SSD1681_BRINGUP=1",
        "EPAPER_SSD1681_R10_NATIVE_GUARDED_CORRIDOR_CACHED_MODE2_CADENCE_DIAGNOSTIC=1",
        "BUILD_DIR=build_ssd1681_r10_native_guarded_corridor_cached_mode2_cadence",
        "TARGET=Companion_Nucleo_WB55RG_Ssd1681R10NativeGuardedCorridorCachedMode2Cadence"
    )
}
if ($EpaperSsd1681R11NativeCachedMode2ThrowArcDiagnostic) {
    $makeArgs += @(
        "EPAPER_SSD1681_BRINGUP=1",
        "EPAPER_SSD1681_R11_NATIVE_CACHED_MODE2_THROW_ARC_DIAGNOSTIC=1",
        "BUILD_DIR=build_ssd1681_r11_native_cached_mode2_throw_arc",
        "TARGET=Companion_Nucleo_WB55RG_Ssd1681R11NativeCachedMode2ThrowArc"
    )
}
if ($EpaperSsd1681R12V22CalmCuriousWarmSamplerDiagnostic) {
    $makeArgs += @(
        "EPAPER_SSD1681_BRINGUP=1",
        "EPAPER_SSD1681_R12_V22_CALM_CURIOUS_WARM_SAMPLER_DIAGNOSTIC=1",
        "BUILD_DIR=build_ssd1681_r12_v22_calm_curious_warm_sampler",
        "TARGET=Companion_Nucleo_WB55RG_Ssd1681R12V22CalmCuriousWarmSampler"
    )
}
if ($EpaperSsd1681DualPlaneWhiteCleanDiagnostic) {
    $makeArgs += @(
        "EPAPER_SSD1681_BRINGUP=1",
        "EPAPER_SSD1681_DUAL_PLANE_WHITE_CLEAN_DIAGNOSTIC=1",
        "BUILD_DIR=build_ssd1681_dual_plane_white_clean",
        "TARGET=Companion_Nucleo_WB55RG_Ssd1681DualPlaneWhiteClean"
    )
}
if ($EpaperSsd1681SingleFlashWhiteCleanupDiagnostic) {
    $makeArgs += @(
        "EPAPER_SSD1681_BRINGUP=1",
        "EPAPER_SSD1681_SINGLE_FLASH_WHITE_CLEANUP_DIAGNOSTIC=1",
        "BUILD_DIR=build_ssd1681_single_flash_white_cleanup",
        "TARGET=Companion_Nucleo_WB55RG_Ssd1681SingleFlashWhiteCleanup"
    )
}
if ($EpaperSsd1681R7LockedV9ChoreographyDiagnostic) {
    $makeArgs += @(
        "EPAPER_SSD1681_BRINGUP=1",
        "EPAPER_SSD1681_R7_LOCKED_V9_CHOREOGRAPHY_DIAGNOSTIC=1",
        "BUILD_DIR=build_ssd1681_r7_locked_v9_choreography",
        "TARGET=Companion_Nucleo_WB55RG_Ssd1681R7LockedV9Choreography"
    )
}
if ($EpaperSsd1681R7RuntimeBridgeDiagnostic) {
    $makeArgs += @(
        "EPAPER_SSD1681_BRINGUP=1",
        "EPAPER_SSD1681_R7_RUNTIME_BRIDGE_DIAGNOSTIC=1",
        "EPAPER_SSD1681_HAS_BUSY=1",
        "BUILD_DIR=build_ssd1681_r7_runtime_bridge",
        "TARGET=Companion_Nucleo_WB55RG_Ssd1681RuntimeBridge"
    )
}
if ($EpaperSsd1681R7RuntimeContinuousDiagnostic) {
    $makeArgs += @(
        "EPAPER_SSD1681_BRINGUP=1",
        "EPAPER_SSD1681_R7_RUNTIME_BRIDGE_DIAGNOSTIC=1",
        "EPAPER_SSD1681_R7_RUNTIME_CONTINUOUS_DIAGNOSTIC=1",
        "EPAPER_SSD1681_HAS_BUSY=1",
        "BUILD_DIR=build_ssd1681_r7_runtime_continuous",
        "TARGET=Companion_Nucleo_WB55RG_Ssd1681RuntimeContinuous"
    )
}
if ($EpaperSsd1681R7VisualRuntimeDiagnostic) {
    $makeArgs += @(
        "EPAPER_SSD1681_BRINGUP=1",
        "EPAPER_MENU=1",
        "EPAPER_SSD1681_R7_VISUAL_RUNTIME_DIAGNOSTIC=1",
        "EPAPER_SSD1681_HAS_BUSY=1",
        "BUILD_DIR=build_ssd1681_r7_visual_runtime",
        "TARGET=Companion_Nucleo_WB55RG_Ssd1681R7VisualRuntime"
    )
}
if ($EpaperSsd1681R7VisualRuntimeContinuousDiagnostic) {
    $makeArgs += @(
        "EPAPER_SSD1681_BRINGUP=1",
        "EPAPER_MENU=1",
        "EPAPER_SSD1681_R7_VISUAL_RUNTIME_CONTINUOUS_DIAGNOSTIC=1",
        "EPAPER_SSD1681_HAS_BUSY=1",
        "BUILD_DIR=build_ssd1681_r7_visual_runtime_continuous",
        "TARGET=Companion_Nucleo_WB55RG_Ssd1681R7VisualRuntimeContinuous"
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
if ($EpaperSsd1681DifferentialMultiRegionDiagnostic) {
    $makeArgs += @(
        "EPAPER_SSD1681_BRINGUP=1",
        "EPAPER_REFRESH_CADENCE_DIAGNOSTIC=1",
        "EPAPER_SSD1681_BALL_MOTION_DIAGNOSTIC=1",
        "EPAPER_SSD1681_DIFFERENTIAL_MULTI_REGION_DIAGNOSTIC=1",
        "EPAPER_SSD1681_VERBOSE_TRACE=1",
        "TOUCH_VERBOSE_TRACE=1",
        "EPAPER_SSD1681_DIAGNOSTIC_PATTERN=4",
        "EPAPER_SSD1681_DIAGNOSTIC_REPEATS=6",
        "EPAPER_SSD1681_DIAGNOSTIC_INTERVAL_MS=250",
        "BUILD_DIR=build_differential_multi_region_diagnostic",
        "TARGET=Companion_Nucleo_WB55RG_DifferentialMultiRegionDiagnostic"
    )
}
if ($EpaperSsd1681Vendor1sLutDiagnostic) {
    if ($EpaperSsd1681OfficialFullDiagnostic -or $EpaperSsd1681BallMotionDiagnostic -or
        $EpaperSsd1681OfficialWhiteRailProbe -or $EpaperRefreshCadenceDiagnostic -or
        $EpaperSsd1681DiagnosticPattern -ne '' -or $EpaperSsd1681DiagnosticPartial -or
        $EpaperSsd1681DiagnosticRepeats -ne 1 -or $EpaperSsd1681DiagnosticIntervalMs -ne 0 -or
        $EpaperProductExpressionDemo -or $ScreenAssetProvision) {
        throw "Vendor one-second LUT diagnostic is a fixed isolated image; do not combine it with another screen or asset option."
    }
    $makeArgs += @(
        "EPAPER_SSD1681_BRINGUP=1",
        "EPAPER_SSD1681_VENDOR_1S_LUT_DIAGNOSTIC=1",
        "EPAPER_SSD1681_VERBOSE_TRACE=1",
        "TOUCH_VERBOSE_TRACE=1",
        "EPAPER_SSD1681_DIAGNOSTIC_PATTERN=4",
        "EPAPER_SSD1681_DIAGNOSTIC_REPEATS=6",
        "EPAPER_SSD1681_DIAGNOSTIC_INTERVAL_MS=250",
        "BUILD_DIR=build_vendor_1s_lut_diagnostic",
        "TARGET=Companion_Nucleo_WB55RG_Vendor1sLutDiagnostic"
    )
}
if ($EpaperSsd1681VendorPartialOperatorLoopDiagnostic) {
    if ($EpaperSsd1681OfficialFullDiagnostic -or $EpaperSsd1681BallMotionDiagnostic -or
        $EpaperSsd1681OfficialWhiteRailProbe -or $EpaperRefreshCadenceDiagnostic -or
        $EpaperSsd1681DiagnosticPattern -ne '' -or $EpaperSsd1681DiagnosticPartial -or
        $EpaperSsd1681DiagnosticRepeats -ne 1 -or $EpaperSsd1681DiagnosticIntervalMs -ne 0 -or
        $EpaperProductExpressionDemo -or $ScreenAssetProvision) {
        throw "Vendor partial operator loop is a fixed isolated image; do not combine it with another screen or asset option."
    }
    $makeArgs += @(
        "EPAPER_SSD1681_BRINGUP=1",
        "EPAPER_SSD1681_VENDOR_PARTIAL_OPERATOR_LOOP_DIAGNOSTIC=1",
        "EPAPER_SSD1681_VERBOSE_TRACE=1",
        "TOUCH_VERBOSE_TRACE=1",
        "EPAPER_SSD1681_DIAGNOSTIC_PATTERN=4",
        "EPAPER_SSD1681_DIAGNOSTIC_REPEATS=360",
        "EPAPER_SSD1681_DIAGNOSTIC_INTERVAL_MS=250",
        "BUILD_DIR=build_vendor_partial_operator_loop_diagnostic",
        "TARGET=Companion_Nucleo_WB55RG_VendorPartialOperatorLoopDiagnostic"
    )
}
if ($EpaperSsd1681VendorPartialMultiRegionOperatorLoopDiagnostic) {
    if ($EpaperSsd1681OfficialFullDiagnostic -or $EpaperSsd1681BallMotionDiagnostic -or
        $EpaperSsd1681OfficialWhiteRailProbe -or $EpaperRefreshCadenceDiagnostic -or
        $EpaperSsd1681DiagnosticPattern -ne '' -or $EpaperSsd1681DiagnosticPartial -or
        $EpaperSsd1681DiagnosticRepeats -ne 1 -or $EpaperSsd1681DiagnosticIntervalMs -ne 0 -or
        $EpaperProductExpressionDemo -or $ScreenAssetProvision) {
        throw "Vendor partial multi-region operator loop is a fixed isolated image; do not combine it with another screen or asset option."
    }
    $makeArgs += @(
        "EPAPER_SSD1681_BRINGUP=1",
        "EPAPER_SSD1681_VENDOR_PARTIAL_MULTI_REGION_OPERATOR_LOOP_DIAGNOSTIC=1",
        "EPAPER_SSD1681_VERBOSE_TRACE=1",
        "TOUCH_VERBOSE_TRACE=1",
        "EPAPER_SSD1681_DIAGNOSTIC_PATTERN=4",
        "EPAPER_SSD1681_DIAGNOSTIC_REPEATS=360",
        "EPAPER_SSD1681_DIAGNOSTIC_INTERVAL_MS=250",
        "BUILD_DIR=build_vendor_partial_multi_region_operator_loop_diagnostic",
        "TARGET=Companion_Nucleo_WB55RG_VendorPartialMultiRegionOperatorLoopDiagnostic"
    )
}
if ($EpaperSsd1681VendorPartialSlowMotionDiagnostic) {
    if ($EpaperSsd1681OfficialFullDiagnostic -or $EpaperSsd1681BallMotionDiagnostic -or
        $EpaperSsd1681OfficialWhiteRailProbe -or $EpaperRefreshCadenceDiagnostic -or
        $EpaperSsd1681DiagnosticPattern -ne '' -or $EpaperSsd1681DiagnosticPartial -or
        $EpaperSsd1681DiagnosticRepeats -ne 1 -or $EpaperSsd1681DiagnosticIntervalMs -ne 0 -or
        $EpaperProductExpressionDemo -or $ScreenAssetProvision) {
        throw "Vendor partial slow-motion diagnostic is a fixed isolated image; do not combine it with another screen or asset option."
    }
    $makeArgs += @(
        "EPAPER_SSD1681_BRINGUP=1",
        "EPAPER_SSD1681_VENDOR_PARTIAL_SLOW_MOTION_DIAGNOSTIC=1",
        "EPAPER_SSD1681_VERBOSE_TRACE=1",
        "TOUCH_VERBOSE_TRACE=1",
        "EPAPER_SSD1681_DIAGNOSTIC_PATTERN=4",
        "EPAPER_SSD1681_DIAGNOSTIC_REPEATS=360",
        "EPAPER_SSD1681_DIAGNOSTIC_INTERVAL_MS=250",
        "BUILD_DIR=build_vendor_partial_slow_motion_diagnostic",
        "TARGET=Companion_Nucleo_WB55RG_VendorPartialSlowMotionDiagnostic"
    )
}
if ($EpaperSsd1681VendorPartialOldNewRamDiagnostic) {
    if ($EpaperSsd1681OfficialFullDiagnostic -or $EpaperSsd1681BallMotionDiagnostic -or
        $EpaperSsd1681OfficialWhiteRailProbe -or $EpaperRefreshCadenceDiagnostic -or
        $EpaperSsd1681DiagnosticPattern -ne '' -or $EpaperSsd1681DiagnosticPartial -or
        $EpaperSsd1681DiagnosticRepeats -ne 1 -or $EpaperSsd1681DiagnosticIntervalMs -ne 0 -or
        $EpaperProductExpressionDemo -or $ScreenAssetProvision) {
        throw "Vendor partial old/new RAM diagnostic is a fixed isolated image; do not combine it with another screen or asset option."
    }
    $makeArgs += @(
        "EPAPER_SSD1681_BRINGUP=1",
        "EPAPER_SSD1681_VENDOR_PARTIAL_OLD_NEW_RAM_DIAGNOSTIC=1",
        "EPAPER_SSD1681_VERBOSE_TRACE=1",
        "TOUCH_VERBOSE_TRACE=1",
        "EPAPER_SSD1681_DIAGNOSTIC_PATTERN=4",
        "EPAPER_SSD1681_DIAGNOSTIC_REPEATS=360",
        "EPAPER_SSD1681_DIAGNOSTIC_INTERVAL_MS=250",
        "BUILD_DIR=build_vendor_partial_old_new_ram_diagnostic",
        "TARGET=Companion_Nucleo_WB55RG_VendorPartialOldNewRamDiagnostic"
    )
}
if ($EpaperSsd1681VendorPartialCleanupDrawDiagnostic -or
    $EpaperSsd1681VendorPartialCleanupDrawOperatorLoopDiagnostic) {
    if ($EpaperSsd1681VendorPartialCleanupDrawDiagnostic -and
        $EpaperSsd1681VendorPartialCleanupDrawOperatorLoopDiagnostic) {
        throw "Choose either the fixed cleanup/draw machine trace or its bounded operator loop, not both."
    }
    if ($EpaperSsd1681OfficialFullDiagnostic -or $EpaperSsd1681BallMotionDiagnostic -or
        $EpaperSsd1681OfficialWhiteRailProbe -or $EpaperRefreshCadenceDiagnostic -or
        $EpaperSsd1681DiagnosticPattern -ne '' -or $EpaperSsd1681DiagnosticPartial -or
        $EpaperSsd1681DiagnosticRepeats -ne 1 -or $EpaperSsd1681DiagnosticIntervalMs -ne 0 -or
        $EpaperProductExpressionDemo -or $ScreenAssetProvision) {
        throw "Vendor partial cleanup/draw diagnostic is a fixed isolated image; do not combine it with another screen or asset option."
    }
    $cleanupDrawRepeats = if ($EpaperSsd1681VendorPartialCleanupDrawOperatorLoopDiagnostic) { 360 } else { 49 }
    $cleanupDrawBuildDir = if ($EpaperSsd1681VendorPartialCleanupDrawOperatorLoopDiagnostic) {
        "build_vendor_partial_cleanup_draw_operator_loop_diagnostic"
    } else {
        "build_vendor_partial_cleanup_draw_diagnostic"
    }
    $cleanupDrawTarget = if ($EpaperSsd1681VendorPartialCleanupDrawOperatorLoopDiagnostic) {
        "Companion_Nucleo_WB55RG_VendorPartialCleanupDrawOperatorLoopDiagnostic"
    } else {
        "Companion_Nucleo_WB55RG_VendorPartialCleanupDrawDiagnostic"
    }
    $makeArgs += @(
        "EPAPER_SSD1681_BRINGUP=1",
        "EPAPER_SSD1681_VENDOR_PARTIAL_CLEANUP_DRAW_DIAGNOSTIC=1",
        "EPAPER_SSD1681_VERBOSE_TRACE=1",
        "TOUCH_VERBOSE_TRACE=1",
        "EPAPER_SSD1681_DIAGNOSTIC_PATTERN=4",
        "EPAPER_SSD1681_DIAGNOSTIC_REPEATS=$cleanupDrawRepeats",
        "EPAPER_SSD1681_DIAGNOSTIC_INTERVAL_MS=250",
        "BUILD_DIR=$cleanupDrawBuildDir",
        "TARGET=$cleanupDrawTarget"
    )
}
if ($EpaperSsd1681VendorPartialDrawFinalDiagnostic -or
    $EpaperSsd1681VendorPartialDrawFinalOperatorLoopDiagnostic) {
    if ($EpaperSsd1681VendorPartialDrawFinalDiagnostic -and
        $EpaperSsd1681VendorPartialDrawFinalOperatorLoopDiagnostic) {
        throw "Choose either the fixed draw/final machine trace or its bounded operator loop, not both."
    }
    if ($EpaperSsd1681VendorPartialCleanupDrawDiagnostic -or
        $EpaperSsd1681VendorPartialCleanupDrawOperatorLoopDiagnostic -or
        $EpaperSsd1681OfficialFullDiagnostic -or $EpaperSsd1681BallMotionDiagnostic -or
        $EpaperSsd1681OfficialWhiteRailProbe -or $EpaperRefreshCadenceDiagnostic -or
        $EpaperSsd1681DiagnosticPattern -ne '' -or $EpaperSsd1681DiagnosticPartial -or
        $EpaperSsd1681DiagnosticRepeats -ne 1 -or $EpaperSsd1681DiagnosticIntervalMs -ne 0 -or
        $EpaperProductExpressionDemo -or $ScreenAssetProvision) {
        throw "Vendor partial draw/final diagnostic is a fixed isolated image; do not combine it with another screen or asset option."
    }
    $drawFinalRepeats = if ($EpaperSsd1681VendorPartialDrawFinalOperatorLoopDiagnostic) { 360 } else { 49 }
    $drawFinalBuildDir = if ($EpaperSsd1681VendorPartialDrawFinalOperatorLoopDiagnostic) {
        "build_vendor_partial_draw_final_operator_loop_diagnostic"
    } else {
        "build_vendor_partial_draw_final_diagnostic"
    }
    $drawFinalTarget = if ($EpaperSsd1681VendorPartialDrawFinalOperatorLoopDiagnostic) {
        "Companion_Nucleo_WB55RG_VendorPartialDrawFinalOperatorLoopDiagnostic"
    } else {
        "Companion_Nucleo_WB55RG_VendorPartialDrawFinalDiagnostic"
    }
    $makeArgs += @(
        "EPAPER_SSD1681_BRINGUP=1",
        "EPAPER_SSD1681_VENDOR_PARTIAL_DRAW_FINAL_DIAGNOSTIC=1",
        "EPAPER_SSD1681_VERBOSE_TRACE=1",
        "TOUCH_VERBOSE_TRACE=1",
        "EPAPER_SSD1681_DIAGNOSTIC_PATTERN=4",
        "EPAPER_SSD1681_DIAGNOSTIC_REPEATS=$drawFinalRepeats",
        "EPAPER_SSD1681_DIAGNOSTIC_INTERVAL_MS=250",
        "BUILD_DIR=$drawFinalBuildDir",
        "TARGET=$drawFinalTarget"
    )
}
if ($EpaperSsd1681VendorPartialNoUnionSettleDiagnostic -or
    $EpaperSsd1681VendorPartialNoUnionSettleOperatorLoopDiagnostic) {
    if ($EpaperSsd1681VendorPartialNoUnionSettleDiagnostic -and
        $EpaperSsd1681VendorPartialNoUnionSettleOperatorLoopDiagnostic) {
        throw "Choose either the fixed no-union machine trace or its bounded operator loop, not both."
    }
    if ($EpaperSsd1681VendorPartialCleanupDrawDiagnostic -or
        $EpaperSsd1681VendorPartialCleanupDrawOperatorLoopDiagnostic -or
        $EpaperSsd1681VendorPartialDrawFinalDiagnostic -or
        $EpaperSsd1681VendorPartialDrawFinalOperatorLoopDiagnostic -or
        $EpaperSsd1681OfficialFullDiagnostic -or $EpaperSsd1681BallMotionDiagnostic -or
        $EpaperSsd1681OfficialWhiteRailProbe -or $EpaperRefreshCadenceDiagnostic -or
        $EpaperSsd1681DiagnosticPattern -ne '' -or $EpaperSsd1681DiagnosticPartial -or
        $EpaperSsd1681DiagnosticRepeats -ne 1 -or $EpaperSsd1681DiagnosticIntervalMs -ne 0 -or
        $EpaperProductExpressionDemo -or $ScreenAssetProvision) {
        throw "Vendor partial no-union settle diagnostic is a fixed isolated image; do not combine it with another screen or asset option."
    }
    $noUnionRepeats = if ($EpaperSsd1681VendorPartialNoUnionSettleOperatorLoopDiagnostic) { 360 } else { 49 }
    $noUnionBuildDir = if ($EpaperSsd1681VendorPartialNoUnionSettleOperatorLoopDiagnostic) {
        "build_vendor_partial_no_union_settle_operator_loop_diagnostic"
    } else {
        "build_vendor_partial_no_union_settle_diagnostic"
    }
    $noUnionTarget = if ($EpaperSsd1681VendorPartialNoUnionSettleOperatorLoopDiagnostic) {
        "Companion_Nucleo_WB55RG_VendorPartialNoUnionSettleOperatorLoopDiagnostic"
    } else {
        "Companion_Nucleo_WB55RG_VendorPartialNoUnionSettleDiagnostic"
    }
    $makeArgs += @(
        "EPAPER_SSD1681_BRINGUP=1",
        "EPAPER_SSD1681_VENDOR_PARTIAL_NO_UNION_SETTLE_DIAGNOSTIC=1",
        "EPAPER_SSD1681_VERBOSE_TRACE=1",
        "TOUCH_VERBOSE_TRACE=1",
        "EPAPER_SSD1681_DIAGNOSTIC_PATTERN=4",
        "EPAPER_SSD1681_DIAGNOSTIC_REPEATS=$noUnionRepeats",
        "EPAPER_SSD1681_DIAGNOSTIC_INTERVAL_MS=250",
        "BUILD_DIR=$noUnionBuildDir",
        "TARGET=$noUnionTarget"
    )
}
if ($EpaperSsd1681VendorPartialCurrentUnionOldSettleDiagnostic -or
    $EpaperSsd1681VendorPartialCurrentUnionOldSettleOperatorLoopDiagnostic) {
    if ($EpaperSsd1681VendorPartialCurrentUnionOldSettleDiagnostic -and
        $EpaperSsd1681VendorPartialCurrentUnionOldSettleOperatorLoopDiagnostic) {
        throw "Choose either the fixed current-union old-settle machine trace or its bounded operator loop, not both."
    }
    if ($EpaperSsd1681VendorPartialCleanupDrawDiagnostic -or
        $EpaperSsd1681VendorPartialCleanupDrawOperatorLoopDiagnostic -or
        $EpaperSsd1681VendorPartialDrawFinalDiagnostic -or
        $EpaperSsd1681VendorPartialDrawFinalOperatorLoopDiagnostic -or
        $EpaperSsd1681VendorPartialNoUnionSettleDiagnostic -or
        $EpaperSsd1681VendorPartialNoUnionSettleOperatorLoopDiagnostic -or
        $EpaperSsd1681OfficialFullDiagnostic -or $EpaperSsd1681BallMotionDiagnostic -or
        $EpaperSsd1681OfficialWhiteRailProbe -or $EpaperRefreshCadenceDiagnostic -or
        $EpaperSsd1681DiagnosticPattern -ne '' -or $EpaperSsd1681DiagnosticPartial -or
        $EpaperSsd1681DiagnosticRepeats -ne 1 -or $EpaperSsd1681DiagnosticIntervalMs -ne 0 -or
        $EpaperProductExpressionDemo -or $ScreenAssetProvision) {
        throw "Vendor partial current-union old-settle diagnostic is a fixed isolated image; do not combine it with another screen or asset option."
    }
    $currentUnionRepeats = if ($EpaperSsd1681VendorPartialCurrentUnionOldSettleOperatorLoopDiagnostic) { 360 } else { 49 }
    $currentUnionBuildDir = if ($EpaperSsd1681VendorPartialCurrentUnionOldSettleOperatorLoopDiagnostic) {
        "build_vendor_partial_current_union_old_settle_operator_loop_diagnostic"
    } else {
        "build_vendor_partial_current_union_old_settle_diagnostic"
    }
    $currentUnionTarget = if ($EpaperSsd1681VendorPartialCurrentUnionOldSettleOperatorLoopDiagnostic) {
        "Companion_Nucleo_WB55RG_VendorPartialCurrentUnionOldSettleOperatorLoopDiagnostic"
    } else {
        "Companion_Nucleo_WB55RG_VendorPartialCurrentUnionOldSettleDiagnostic"
    }
    $makeArgs += @(
        "EPAPER_SSD1681_BRINGUP=1",
        "EPAPER_SSD1681_VENDOR_PARTIAL_CURRENT_UNION_OLD_SETTLE_DIAGNOSTIC=1",
        "EPAPER_SSD1681_VERBOSE_TRACE=1",
        "TOUCH_VERBOSE_TRACE=1",
        "EPAPER_SSD1681_DIAGNOSTIC_PATTERN=4",
        "EPAPER_SSD1681_DIAGNOSTIC_REPEATS=$currentUnionRepeats",
        "EPAPER_SSD1681_DIAGNOSTIC_INTERVAL_MS=250",
        "BUILD_DIR=$currentUnionBuildDir",
        "TARGET=$currentUnionTarget"
    )
}
if ($EpaperSsd1681VendorPartialRemovedBlackRepairCurrentUnionDiagnostic -or
    $EpaperSsd1681VendorPartialRemovedBlackRepairCurrentUnionOperatorLoopDiagnostic) {
    if ($EpaperSsd1681VendorPartialRemovedBlackRepairCurrentUnionDiagnostic -and
        $EpaperSsd1681VendorPartialRemovedBlackRepairCurrentUnionOperatorLoopDiagnostic) {
        throw "Choose either the fixed removed-black repair/current-union machine trace or its bounded operator loop, not both."
    }
    if ($EpaperSsd1681VendorPartialCleanupDrawDiagnostic -or
        $EpaperSsd1681VendorPartialCleanupDrawOperatorLoopDiagnostic -or
        $EpaperSsd1681VendorPartialDrawFinalDiagnostic -or
        $EpaperSsd1681VendorPartialDrawFinalOperatorLoopDiagnostic -or
        $EpaperSsd1681VendorPartialNoUnionSettleDiagnostic -or
        $EpaperSsd1681VendorPartialNoUnionSettleOperatorLoopDiagnostic -or
        $EpaperSsd1681VendorPartialCurrentUnionOldSettleDiagnostic -or
        $EpaperSsd1681VendorPartialCurrentUnionOldSettleOperatorLoopDiagnostic -or
        $EpaperSsd1681OfficialFullDiagnostic -or $EpaperSsd1681BallMotionDiagnostic -or
        $EpaperSsd1681OfficialWhiteRailProbe -or $EpaperRefreshCadenceDiagnostic -or
        $EpaperSsd1681DiagnosticPattern -ne '' -or $EpaperSsd1681DiagnosticPartial -or
        $EpaperSsd1681DiagnosticRepeats -ne 1 -or $EpaperSsd1681DiagnosticIntervalMs -ne 0 -or
        $EpaperProductExpressionDemo -or $ScreenAssetProvision) {
        throw "Vendor partial removed-black repair/current-union diagnostic is a fixed isolated image; do not combine it with another screen or asset option."
    }
    $removedBlackRepeats = if ($EpaperSsd1681VendorPartialRemovedBlackRepairCurrentUnionOperatorLoopDiagnostic) { 360 } else { 49 }
    $removedBlackBuildDir = if ($EpaperSsd1681VendorPartialRemovedBlackRepairCurrentUnionOperatorLoopDiagnostic) {
        "build_vendor_partial_removed_black_repair_current_union_operator_loop_diagnostic"
    } else {
        "build_vendor_partial_removed_black_repair_current_union_diagnostic"
    }
    $removedBlackTarget = if ($EpaperSsd1681VendorPartialRemovedBlackRepairCurrentUnionOperatorLoopDiagnostic) {
        "Companion_Nucleo_WB55RG_VendorPartialRemovedBlackRepairCurrentUnionOperatorLoopDiagnostic"
    } else {
        "Companion_Nucleo_WB55RG_VendorPartialRemovedBlackRepairCurrentUnionDiagnostic"
    }
    $makeArgs += @(
        "EPAPER_SSD1681_BRINGUP=1",
        "EPAPER_SSD1681_VENDOR_PARTIAL_REMOVED_BLACK_REPAIR_CURRENT_UNION_DIAGNOSTIC=1",
        "EPAPER_SSD1681_VERBOSE_TRACE=1",
        "TOUCH_VERBOSE_TRACE=1",
        "EPAPER_SSD1681_DIAGNOSTIC_PATTERN=4",
        "EPAPER_SSD1681_DIAGNOSTIC_REPEATS=$removedBlackRepeats",
        "EPAPER_SSD1681_DIAGNOSTIC_INTERVAL_MS=250",
        "BUILD_DIR=$removedBlackBuildDir",
        "TARGET=$removedBlackTarget"
    )
}
if ($EpaperSsd1681VendorPartialDisjointCurrentStageDiagnostic -and $EpaperSsd1681VendorPartialDisjointCurrentStageOperatorLoopDiagnostic) {
    throw "Choose either the bounded trace image or the observer-loop image, not both."
}
if ($EpaperSsd1681VendorPartialDisjointCurrentStageDiagnostic) {
    if ($EpaperSsd1681VendorPartialDiagnostic -or $EpaperSsd1681VendorPartialOperatorLoopDiagnostic -or
        $EpaperSsd1681VendorPartialMultiRegionOperatorLoopDiagnostic -or $EpaperSsd1681VendorPartialSlowMotionDiagnostic -or
        $EpaperSsd1681VendorPartialOldNewRamDiagnostic -or $EpaperSsd1681VendorPartialCleanupDrawDiagnostic -or
        $EpaperSsd1681VendorPartialCleanupDrawOperatorLoopDiagnostic -or $EpaperSsd1681VendorPartialDrawFinalDiagnostic -or
        $EpaperSsd1681VendorPartialDrawFinalOperatorLoopDiagnostic -or $EpaperSsd1681VendorPartialNoUnionSettleDiagnostic -or
        $EpaperSsd1681VendorPartialNoUnionSettleOperatorLoopDiagnostic -or $EpaperSsd1681VendorPartialCurrentUnionOldSettleDiagnostic -or
        $EpaperSsd1681VendorPartialCurrentUnionOldSettleOperatorLoopDiagnostic -or
        $EpaperSsd1681VendorPartialRemovedBlackRepairCurrentUnionDiagnostic -or
        $EpaperSsd1681VendorPartialRemovedBlackRepairCurrentUnionOperatorLoopDiagnostic -or
        $EpaperSsd1681VendorPartialDisjointCurrentStageOperatorLoopDiagnostic -or
        $EpaperSsd1681VendorPartialDisjointNoUnionSettleDiagnostic -or
        $EpaperSsd1681VendorPartialDisjointNoUnionSettleOperatorLoopDiagnostic -or
        $EpaperSsd1681VendorT03FastStateDiagnostic -or $EpaperSsd1681DifferentialMultiRegionDiagnostic -or
        $EpaperSsd1681Vendor1sLutDiagnostic -or $EpaperSsd1681Vendor1sLutOperatorLoopDiagnostic -or
        $EpaperSsd1681DirectGpioSpiDiagnostic -or $EpaperSsd1681OfficialFullDiagnostic -or
        $EpaperSsd1681OfficialWhiteRailProbe -or $EpaperSsd1681BallMotionDiagnostic -or
        $EpaperRefreshCadenceDiagnostic -or $EpaperSsd1681DiagnosticPattern -ne '' -or
        $EpaperSsd1681DiagnosticPartial -or $EpaperSsd1681DiagnosticRepeats -ne 1 -or
        $EpaperSsd1681DiagnosticIntervalMs -ne 0 -or $EpaperProductExpressionDemo -or
        $ScreenAssetProvision) {
        throw "Vendor partial disjoint current-stage diagnostic is a fixed isolated image; do not combine it with another screen or asset option."
    }
    $makeArgs += @(
        "EPAPER_SSD1681_BRINGUP=1",
        "EPAPER_SSD1681_VENDOR_PARTIAL_DISJOINT_CURRENT_STAGE_DIAGNOSTIC=1",
        "EPAPER_SSD1681_VERBOSE_TRACE=1",
        "TOUCH_VERBOSE_TRACE=1",
        "EPAPER_SSD1681_DIAGNOSTIC_PATTERN=6",
        "EPAPER_SSD1681_DIAGNOSTIC_REPEATS=50",
        "EPAPER_SSD1681_DIAGNOSTIC_INTERVAL_MS=250",
        "BUILD_DIR=build_vendor_partial_disjoint_current_stage_diagnostic",
        "TARGET=Companion_Nucleo_WB55RG_VendorPartialDisjointCurrentStageDiagnostic"
    )
}
if ($EpaperSsd1681VendorPartialDisjointCurrentStageOperatorLoopDiagnostic) {
    if ($EpaperSsd1681VendorPartialDiagnostic -or $EpaperSsd1681VendorPartialOperatorLoopDiagnostic -or
        $EpaperSsd1681VendorPartialMultiRegionOperatorLoopDiagnostic -or $EpaperSsd1681VendorPartialSlowMotionDiagnostic -or
        $EpaperSsd1681VendorPartialOldNewRamDiagnostic -or $EpaperSsd1681VendorPartialCleanupDrawDiagnostic -or
        $EpaperSsd1681VendorPartialCleanupDrawOperatorLoopDiagnostic -or $EpaperSsd1681VendorPartialDrawFinalDiagnostic -or
        $EpaperSsd1681VendorPartialDrawFinalOperatorLoopDiagnostic -or $EpaperSsd1681VendorPartialNoUnionSettleDiagnostic -or
        $EpaperSsd1681VendorPartialNoUnionSettleOperatorLoopDiagnostic -or $EpaperSsd1681VendorPartialCurrentUnionOldSettleDiagnostic -or
        $EpaperSsd1681VendorPartialCurrentUnionOldSettleOperatorLoopDiagnostic -or
        $EpaperSsd1681VendorPartialRemovedBlackRepairCurrentUnionDiagnostic -or
        $EpaperSsd1681VendorPartialRemovedBlackRepairCurrentUnionOperatorLoopDiagnostic -or
        $EpaperSsd1681VendorPartialDisjointCurrentStageDiagnostic -or
        $EpaperSsd1681VendorPartialDisjointNoUnionSettleDiagnostic -or
        $EpaperSsd1681VendorPartialDisjointNoUnionSettleOperatorLoopDiagnostic -or
        $EpaperSsd1681VendorT03FastStateDiagnostic -or $EpaperSsd1681DifferentialMultiRegionDiagnostic -or
        $EpaperSsd1681Vendor1sLutDiagnostic -or $EpaperSsd1681Vendor1sLutOperatorLoopDiagnostic -or
        $EpaperSsd1681DirectGpioSpiDiagnostic -or $EpaperSsd1681OfficialFullDiagnostic -or
        $EpaperSsd1681OfficialWhiteRailProbe -or $EpaperSsd1681BallMotionDiagnostic -or
        $EpaperRefreshCadenceDiagnostic -or $EpaperSsd1681DiagnosticPattern -ne '' -or
        $EpaperSsd1681DiagnosticPartial -or $EpaperSsd1681DiagnosticRepeats -ne 1 -or
        $EpaperSsd1681DiagnosticIntervalMs -ne 0 -or $EpaperProductExpressionDemo -or
        $ScreenAssetProvision) {
        throw "Vendor partial disjoint current-stage observer loop is a fixed isolated image; do not combine it with another screen or asset option."
    }
    $makeArgs += @(
        "EPAPER_SSD1681_BRINGUP=1",
        "EPAPER_SSD1681_VENDOR_PARTIAL_DISJOINT_CURRENT_STAGE_DIAGNOSTIC=1",
        "EPAPER_SSD1681_VERBOSE_TRACE=1",
        "TOUCH_VERBOSE_TRACE=1",
        "EPAPER_SSD1681_DIAGNOSTIC_PATTERN=6",
        "EPAPER_SSD1681_DIAGNOSTIC_REPEATS=360",
        "EPAPER_SSD1681_DIAGNOSTIC_INTERVAL_MS=250",
        "BUILD_DIR=build_vendor_partial_disjoint_current_stage_operator_loop_diagnostic",
        "TARGET=Companion_Nucleo_WB55RG_VendorPartialDisjointCurrentStageOperatorLoopDiagnostic"
    )
}
if ($EpaperSsd1681VendorPartialDisjointNoUnionSettleDiagnostic -and $EpaperSsd1681VendorPartialDisjointNoUnionSettleOperatorLoopDiagnostic) {
    throw "Choose either the bounded disjoint no-union trace image or its observer-loop image, not both."
}
if ($EpaperSsd1681VendorPartialDisjointNoUnionSettleDiagnostic -or $EpaperSsd1681VendorPartialDisjointNoUnionSettleOperatorLoopDiagnostic) {
    if ($EpaperSsd1681VendorPartialDiagnostic -or $EpaperSsd1681VendorPartialOperatorLoopDiagnostic -or
        $EpaperSsd1681VendorPartialMultiRegionOperatorLoopDiagnostic -or $EpaperSsd1681VendorPartialSlowMotionDiagnostic -or
        $EpaperSsd1681VendorPartialOldNewRamDiagnostic -or $EpaperSsd1681VendorPartialCleanupDrawDiagnostic -or
        $EpaperSsd1681VendorPartialCleanupDrawOperatorLoopDiagnostic -or $EpaperSsd1681VendorPartialDrawFinalDiagnostic -or
        $EpaperSsd1681VendorPartialDrawFinalOperatorLoopDiagnostic -or $EpaperSsd1681VendorPartialNoUnionSettleDiagnostic -or
        $EpaperSsd1681VendorPartialNoUnionSettleOperatorLoopDiagnostic -or $EpaperSsd1681VendorPartialCurrentUnionOldSettleDiagnostic -or
        $EpaperSsd1681VendorPartialCurrentUnionOldSettleOperatorLoopDiagnostic -or
        $EpaperSsd1681VendorPartialRemovedBlackRepairCurrentUnionDiagnostic -or
        $EpaperSsd1681VendorPartialRemovedBlackRepairCurrentUnionOperatorLoopDiagnostic -or
        $EpaperSsd1681VendorPartialDisjointCurrentStageDiagnostic -or
        $EpaperSsd1681VendorPartialDisjointCurrentStageOperatorLoopDiagnostic -or
        $EpaperSsd1681VendorT03FastStateDiagnostic -or $EpaperSsd1681DifferentialMultiRegionDiagnostic -or
        $EpaperSsd1681Vendor1sLutDiagnostic -or $EpaperSsd1681Vendor1sLutOperatorLoopDiagnostic -or
        $EpaperSsd1681DirectGpioSpiDiagnostic -or $EpaperSsd1681OfficialFullDiagnostic -or
        $EpaperSsd1681OfficialWhiteRailProbe -or $EpaperSsd1681BallMotionDiagnostic -or
        $EpaperRefreshCadenceDiagnostic -or $EpaperSsd1681DiagnosticPattern -ne '' -or
        $EpaperSsd1681DiagnosticPartial -or $EpaperSsd1681DiagnosticRepeats -ne 1 -or
        $EpaperSsd1681DiagnosticIntervalMs -ne 0 -or $EpaperProductExpressionDemo -or
        $ScreenAssetProvision) {
        throw "Vendor partial disjoint no-union settle diagnostic is a fixed isolated image; do not combine it with another screen or asset option."
    }
    $disjointNoUnionObserver = $EpaperSsd1681VendorPartialDisjointNoUnionSettleOperatorLoopDiagnostic.IsPresent
    $disjointNoUnionRepeats = if ($disjointNoUnionObserver) { 360 } else { 50 }
    $disjointNoUnionBuildDir = if ($disjointNoUnionObserver) {
        "build_vendor_partial_disjoint_no_union_settle_operator_loop_diagnostic"
    } else {
        "build_vendor_partial_disjoint_no_union_settle_diagnostic"
    }
    $disjointNoUnionTarget = if ($disjointNoUnionObserver) {
        "Companion_Nucleo_WB55RG_VendorPartialDisjointNoUnionSettleOperatorLoopDiagnostic"
    } else {
        "Companion_Nucleo_WB55RG_VendorPartialDisjointNoUnionSettleDiagnostic"
    }
    $makeArgs += @(
        "EPAPER_SSD1681_BRINGUP=1",
        "EPAPER_SSD1681_VENDOR_PARTIAL_DISJOINT_NO_UNION_SETTLE_DIAGNOSTIC=1",
        "EPAPER_SSD1681_VERBOSE_TRACE=1",
        "TOUCH_VERBOSE_TRACE=1",
        "EPAPER_SSD1681_DIAGNOSTIC_PATTERN=6",
        "EPAPER_SSD1681_DIAGNOSTIC_REPEATS=$disjointNoUnionRepeats",
        "EPAPER_SSD1681_DIAGNOSTIC_INTERVAL_MS=250",
        "BUILD_DIR=$disjointNoUnionBuildDir",
        "TARGET=$disjointNoUnionTarget"
    )
}
if ($EpaperSsd1681VendorPartialAddedFirstOldCleanupDiagnostic -and $EpaperSsd1681VendorPartialAddedFirstOldCleanupOperatorLoopDiagnostic) {
    throw "Choose either the bounded added-first old-cleanup image or its observer-loop image, not both."
}
if ($EpaperSsd1681VendorPartialAddedFirstOldCleanupDiagnostic -or $EpaperSsd1681VendorPartialAddedFirstOldCleanupOperatorLoopDiagnostic) {
    if ($EpaperSsd1681VendorPartialDiagnostic -or $EpaperSsd1681VendorPartialOperatorLoopDiagnostic -or
        $EpaperSsd1681VendorPartialMultiRegionOperatorLoopDiagnostic -or $EpaperSsd1681VendorPartialSlowMotionDiagnostic -or
        $EpaperSsd1681VendorPartialOldNewRamDiagnostic -or $EpaperSsd1681VendorPartialCleanupDrawDiagnostic -or
        $EpaperSsd1681VendorPartialCleanupDrawOperatorLoopDiagnostic -or $EpaperSsd1681VendorPartialDrawFinalDiagnostic -or
        $EpaperSsd1681VendorPartialDrawFinalOperatorLoopDiagnostic -or $EpaperSsd1681VendorPartialNoUnionSettleDiagnostic -or
        $EpaperSsd1681VendorPartialNoUnionSettleOperatorLoopDiagnostic -or $EpaperSsd1681VendorPartialCurrentUnionOldSettleDiagnostic -or
        $EpaperSsd1681VendorPartialCurrentUnionOldSettleOperatorLoopDiagnostic -or
        $EpaperSsd1681VendorPartialRemovedBlackRepairCurrentUnionDiagnostic -or
        $EpaperSsd1681VendorPartialRemovedBlackRepairCurrentUnionOperatorLoopDiagnostic -or
        $EpaperSsd1681VendorPartialDisjointCurrentStageDiagnostic -or
        $EpaperSsd1681VendorPartialDisjointCurrentStageOperatorLoopDiagnostic -or
        $EpaperSsd1681VendorPartialDisjointNoUnionSettleDiagnostic -or
        $EpaperSsd1681VendorPartialDisjointNoUnionSettleOperatorLoopDiagnostic -or
        $EpaperSsd1681VendorT03FastStateDiagnostic -or $EpaperSsd1681DifferentialMultiRegionDiagnostic -or
        $EpaperSsd1681Vendor1sLutDiagnostic -or $EpaperSsd1681Vendor1sLutOperatorLoopDiagnostic -or
        $EpaperSsd1681DirectGpioSpiDiagnostic -or $EpaperSsd1681OfficialFullDiagnostic -or
        $EpaperSsd1681OfficialWhiteRailProbe -or $EpaperSsd1681BallMotionDiagnostic -or
        $EpaperRefreshCadenceDiagnostic -or $EpaperSsd1681DiagnosticPattern -ne '' -or
        $EpaperSsd1681DiagnosticPartial -or $EpaperSsd1681DiagnosticRepeats -ne 1 -or
        $EpaperSsd1681DiagnosticIntervalMs -ne 0 -or $EpaperProductExpressionDemo -or
        $ScreenAssetProvision) {
        throw "Vendor partial added-first old-cleanup diagnostic is a fixed isolated image; do not combine it with another screen or asset option."
    }
    $addedFirstObserver = $EpaperSsd1681VendorPartialAddedFirstOldCleanupOperatorLoopDiagnostic.IsPresent
    $addedFirstRepeats = if ($addedFirstObserver) { 360 } else { 50 }
    $addedFirstBuildDir = if ($addedFirstObserver) {
        "build_vendor_partial_added_first_old_cleanup_operator_loop_diagnostic"
    } else {
        "build_vendor_partial_added_first_old_cleanup_diagnostic"
    }
    $addedFirstTarget = if ($addedFirstObserver) {
        "Companion_Nucleo_WB55RG_VendorPartialAddedFirstOldCleanupOperatorLoopDiagnostic"
    } else {
        "Companion_Nucleo_WB55RG_VendorPartialAddedFirstOldCleanupDiagnostic"
    }
    $makeArgs += @(
        "EPAPER_SSD1681_BRINGUP=1",
        "EPAPER_SSD1681_VENDOR_PARTIAL_ADDED_FIRST_OLD_CLEANUP_DIAGNOSTIC=1",
        "EPAPER_SSD1681_VERBOSE_TRACE=1",
        "TOUCH_VERBOSE_TRACE=1",
        "EPAPER_SSD1681_DIAGNOSTIC_PATTERN=6",
        "EPAPER_SSD1681_DIAGNOSTIC_REPEATS=$addedFirstRepeats",
        "EPAPER_SSD1681_DIAGNOSTIC_INTERVAL_MS=250",
        "BUILD_DIR=$addedFirstBuildDir",
        "TARGET=$addedFirstTarget"
    )
}
if ($EpaperSsd1681VendorT03FastStateDiagnostic) {
    if ($EpaperSsd1681OfficialFullDiagnostic -or $EpaperSsd1681BallMotionDiagnostic -or
        $EpaperSsd1681OfficialWhiteRailProbe -or $EpaperRefreshCadenceDiagnostic -or
        $EpaperSsd1681DiagnosticPattern -ne '' -or $EpaperSsd1681DiagnosticPartial -or
        $EpaperSsd1681DiagnosticRepeats -ne 1 -or $EpaperSsd1681DiagnosticIntervalMs -ne 0 -or
        $EpaperProductExpressionDemo -or $ScreenAssetProvision) {
        throw "Vendor T03 fast-state diagnostic is a fixed isolated image; do not combine it with another screen or asset option."
    }
    $makeArgs += @(
        "EPAPER_SSD1681_BRINGUP=1",
        "EPAPER_SSD1681_VENDOR_T03_FAST_STATE_DIAGNOSTIC=1",
        "EPAPER_SSD1681_VERBOSE_TRACE=1",
        "TOUCH_VERBOSE_TRACE=1",
        "EPAPER_SSD1681_DIAGNOSTIC_PATTERN=4",
        "EPAPER_SSD1681_DIAGNOSTIC_REPEATS=360",
        "EPAPER_SSD1681_DIAGNOSTIC_INTERVAL_MS=250",
        "BUILD_DIR=build_vendor_t03_fast_state_diagnostic",
        "TARGET=Companion_Nucleo_WB55RG_VendorT03FastStateDiagnostic"
    )
}
if ($EpaperSsd1681Vendor1sLutOperatorLoopDiagnostic) {
    if ($EpaperSsd1681OfficialFullDiagnostic -or $EpaperSsd1681BallMotionDiagnostic -or
        $EpaperSsd1681OfficialWhiteRailProbe -or $EpaperRefreshCadenceDiagnostic -or
        $EpaperSsd1681DiagnosticPattern -ne '' -or $EpaperSsd1681DiagnosticPartial -or
        $EpaperSsd1681DiagnosticRepeats -ne 1 -or $EpaperSsd1681DiagnosticIntervalMs -ne 0 -or
        $EpaperProductExpressionDemo -or $ScreenAssetProvision) {
        throw "Vendor one-second LUT operator loop is a fixed isolated image; do not combine it with another screen or asset option."
    }
    $makeArgs += @(
        "EPAPER_SSD1681_BRINGUP=1",
        "EPAPER_SSD1681_VENDOR_1S_LUT_OPERATOR_LOOP_DIAGNOSTIC=1",
        "EPAPER_SSD1681_VERBOSE_TRACE=1",
        "TOUCH_VERBOSE_TRACE=1",
        "EPAPER_SSD1681_DIAGNOSTIC_PATTERN=4",
        "EPAPER_SSD1681_DIAGNOSTIC_REPEATS=360",
        "EPAPER_SSD1681_DIAGNOSTIC_INTERVAL_MS=250",
        "BUILD_DIR=build_vendor_1s_lut_operator_loop_diagnostic",
        "TARGET=Companion_Nucleo_WB55RG_Vendor1sLutOperatorLoopDiagnostic"
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
        "EPAPER_SSD1681_BRINGUP=1",
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
    if ($UseFreeRTOS) {
        $contractPreparer = Join-Path $RepoRoot `
            'tools\faraday_upper_art\build_comp_req_775_firmware.py'
        $contractBuildDir = Join-Path $ProjectDir 'build_freertos'
        if (-not (Test-Path -LiteralPath $contractPreparer -PathType Leaf)) {
            throw "Product browser contract preparer missing: $contractPreparer"
        }
        $contractArgs = @('--prepare-contracts-for-build-dir', $contractBuildDir)
        if (-not [string]::IsNullOrWhiteSpace($BrowserInteractionSourceManifestPath)) {
            $contractArgs += @(
                '--product-source-manifest', $interactionManifest,
                '--generation-manifest', $generationManifest
            )
        }
        & python $contractPreparer @contractArgs | Out-Host
        if ($LASTEXITCODE -ne 0) {
            throw "Product browser contract preparation failed with exit code $LASTEXITCODE"
        }
    }
    & $MakePath @makeArgs
    $buildExitCode = $LASTEXITCODE
    if ($buildExitCode -ne 0) {
        throw "bring-up build failed with exit code $buildExitCode"
    }
} finally {
    Release-BuildLock -Lock $buildLock
}

# Fail closed: product hex must sit only in OTA App region (never cover Loader).
# Isolated diagnostics that intentionally use a non-product layout are skipped when
# makeArgs contain ALLOW_LEGACY_DIRECT_APP=1.
$legacyDirect = ($makeArgs -contains 'ALLOW_LEGACY_DIRECT_APP=1') -or ($makeArgs -contains 'OTA_APP=0')
if ($productOtaAppExpected -and -not $legacyDirect) {
    $buildDirName = 'build'
    $targetName = 'Companion_Nucleo_WB55RG_Bringup'
    foreach ($arg in $makeArgs) {
        if ($arg -like 'BUILD_DIR=*') { $buildDirName = $arg.Substring('BUILD_DIR='.Length) }
        if ($arg -like 'TARGET=*') { $targetName = $arg.Substring('TARGET='.Length) }
    }
    $hexPath = Join-Path $ProjectDir (Join-Path $buildDirName "$targetName.hex")
    $otaAppGuard = Join-Path $RepoRoot 'tools\faraday_upper_art\verify_companion_ota_app_hex.py'
    $layoutReceipt = Join-Path $RepoRoot (
        ".cache\validation\build-nucleo\ota-app-layout-$targetName.json"
    )
    if (-not (Test-Path -LiteralPath $hexPath -PathType Leaf)) {
        throw "Product build finished but hex is missing: $hexPath"
    }
    if (-not (Test-Path -LiteralPath $otaAppGuard -PathType Leaf)) {
        throw "OTA App layout guard missing: $otaAppGuard"
    }
    Write-Host "GUARD: verify OTA App layout (refuse 0x08000000 Loader overwrite risk): $hexPath"
    & python $otaAppGuard --hex $hexPath --receipt $layoutReceipt | Out-Host
    if ($LASTEXITCODE -ne 0) {
        throw (
            "Refusing product hex that can overwrite the resident OTA Loader " +
            "(must start at 0x08007000 with OTA_APP=1). receipt=$layoutReceipt"
        )
    }
    Write-Host "GUARD: ota_app_layout=MACHINE_READY receipt=$layoutReceipt"
}
