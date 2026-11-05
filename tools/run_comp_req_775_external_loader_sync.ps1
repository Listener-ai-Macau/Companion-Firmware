#requires -Version 7.0
param(
    [switch]$Execute,
    [string]$BundlePath = (
        ".cache\validation\comp-req-775-incremental-sync\resource-ota\" +
        "generation-1.cuot"
    ),
    [string]$BootstrapImage,
    [string]$PortName = "COM13",
    [int]$BootCaptureSeconds = 35,
    [switch]$CaptureMenuBoundary,
    [int]$MenuCaptureSeconds = 120,
    [switch]$PerformanceProbe,
    [string]$BrowserSourceManifestPath = (
        ".cache\validation\comp-req-775-incremental-sync\" +
        "offline-initial-batched\current-source-pack\source-pack-manifest.json"
    ),
    [string]$GenerationVerificationPath,
    [switch]$AllowCurrentPageResourceRevision,
    [switch]$AllowGenerationCompaction,
    [string]$ProgrammerSerial = "066EFF535570514867221931",
    [string]$ReceiptPath = (
        ".cache\validation\comp-req-775-incremental-sync\" +
        "hardware-external-loader\SYNC_RECEIPT.json"
    )
)

$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot
function Resolve-RepoPath {
    param([Parameter(Mandatory = $true)][string]$Value)
    if ([IO.Path]::IsPathRooted($Value)) {
        return [IO.Path]::GetFullPath($Value)
    }
    return [IO.Path]::GetFullPath((Join-Path $repo $Value))
}

$bundle = $null
if (-not [string]::IsNullOrWhiteSpace($BundlePath)) {
    $bundle = Resolve-RepoPath $BundlePath
}
$bootstrap = $null
if (-not [string]::IsNullOrWhiteSpace($BootstrapImage)) {
    $bootstrap = Resolve-RepoPath $BootstrapImage
}
if ($null -ne $bootstrap -and $PSBoundParameters.ContainsKey("BundlePath")) {
    throw "Pass either -BundlePath or -BootstrapImage, not both."
}
$receipt = Resolve-RepoPath $ReceiptPath
$syncTool = Join-Path $repo "tools\sync_companion_ui_assets_stlink.py"
$loader = Join-Path $repo (
    "tools\external_loader\wb55_spi1_nor\build\" +
    "Companion_WB55_SPI1_NOR_UI_2MiB.stldr"
)
$workspace = Split-Path -Parent $receipt
$offlinePath = Join-Path $repo (
    ".cache\validation\comp-req-775-incremental-sync\OFFLINE_READY.json"
)
$resourceOfflinePath = Join-Path $repo (
    ".cache\validation\comp-req-775-incremental-sync\" +
    "RESOURCE_OTA_OFFLINE_READY.json"
)
$recordingResourceBuilder = Join-Path $repo (
    "tools\build_companion_recording_resources.py"
)
$recordingResourcePack = Join-Path $repo (
    ".cache\validation\comp-req-775-recording-resources\" +
    "companion_recording_resources.crrp"
)
$performanceReceiptPath = Join-Path $repo (
    ".cache\validation\comp-req-775-incremental-sync\resource-ota\" +
    "generation-2-receipt.json"
)
$pagePath = Join-Path $repo (
    ".cache\validation\comp-req-628-status-bar\index.html"
)
$sourceManifestPath = Resolve-RepoPath $BrowserSourceManifestPath
$bootLog = Join-Path $workspace "ordinary-reset-serial.log"
$bootEvidencePath = Join-Path $workspace "ordinary-reset-evidence.json"
$bootVerifier = Join-Path $repo (
    "tools\faraday_upper_art\verify_comp_req_775_boot_log.py"
)
$menuLog = Join-Path $workspace "menu-boundary-serial.log"
$menuEvidencePath = Join-Path $workspace "menu-boundary-evidence.json"
$menuVerifier = Join-Path $repo (
    "tools\faraday_upper_art\verify_comp_req_775_menu_log.py"
)
$bootChainVerifier = Join-Path $repo (
    "tools\faraday_upper_art\verify_comp_req_775_boot_chain_preflight.py"
)
$formalLoader = Join-Path $repo (
    "cubeide\Companion_BLE_Ota_Loader\build\Companion_BLE_Ota_Loader.hex"
)
$programmer = "C:\ST\STM32CubeProgrammer\bin\STM32_Programmer_CLI.exe"
$bootChainEvidencePath = Join-Path $workspace "boot-chain-preflight.json"
$fixedUrl = (
    "http://127.0.0.1:4185/.cache/validation/" +
    "comp-req-628-status-bar/index.html"
)

foreach ($required in @(
    $syncTool,
    $loader,
    $offlinePath,
    $resourceOfflinePath,
    $recordingResourceBuilder,
    $recordingResourcePack,
    $performanceReceiptPath,
    $pagePath,
    $sourceManifestPath,
    $bootVerifier,
    $menuVerifier,
    $bootChainVerifier,
    $formalLoader,
    $programmer
)) {
    if (-not (Test-Path -LiteralPath $required -PathType Leaf)) {
        throw "Missing required input: $required"
    }
}
& python $recordingResourceBuilder --check | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "Recording resource pack is stale or does not match its sources."
}
$recordingResourceSha = (
    Get-FileHash -LiteralPath $recordingResourcePack -Algorithm SHA256
).Hash
if ($null -ne $bootstrap) {
    if (-not (Test-Path -LiteralPath $bootstrap -PathType Leaf)) {
        throw "Missing bootstrap image: $bootstrap"
    }
} elseif (-not (Test-Path -LiteralPath $bundle -PathType Leaf)) {
    throw "Missing bundle: $bundle"
}
if ($PerformanceProbe -and $null -ne $bootstrap) {
    throw "Performance probe requires the registered one-frame CUOT bundle."
}
if ($PerformanceProbe -and $CaptureMenuBoundary) {
    throw "Menu boundary capture is forbidden on the synthetic probe resource."
}

$offline = Get-Content -LiteralPath $offlinePath -Raw |
    ConvertFrom-Json -AsHashtable
$resourceOffline = Get-Content -LiteralPath $resourceOfflinePath -Raw |
    ConvertFrom-Json -AsHashtable
if ([string]$offline.status -ne "PASS_OFFLINE_HARDWARE_PENDING" -or
    [string]$resourceOffline.status -ne "MACHINE_READY_OFFLINE" -or
    [string]$offline.fixed_url -ne $fixedUrl -or
    -not [bool]$resourceOffline.checks.existing_app_ota_loader_unchanged -or
    -not [bool]$resourceOffline.checks.external_loader_exact_2mib) {
    throw "Offline contract evidence is not ready."
}
$pageSha = (Get-FileHash -LiteralPath $pagePath -Algorithm SHA256).Hash
if ($pageSha -ne [string]$offline.page_sha256 -and
    -not $AllowCurrentPageResourceRevision) {
    throw "Fixed page SHA differs from OFFLINE_READY."
}
$httpHandler = [Net.Http.HttpClientHandler]::new()
# The fixed browser contract is served only from loopback.  Do not let a
# machine/user HTTP proxy turn this local identity check into a remote 503.
$httpHandler.UseProxy = $false
$httpClient = [Net.Http.HttpClient]::new($httpHandler)
try {
    $httpBytes = $httpClient.GetByteArrayAsync($fixedUrl).GetAwaiter().GetResult()
} finally {
    $httpClient.Dispose()
    $httpHandler.Dispose()
}
$httpSha = [Convert]::ToHexString(
    [Security.Cryptography.SHA256]::HashData($httpBytes)
)
if ($httpSha -ne $pageSha) {
    throw "Fixed URL body differs from the local accepted page."
}
$otaLoaderStatus = & git -C $repo status --porcelain -- (
    "cubeide/Companion_BLE_Ota_Loader"
)
if ($LASTEXITCODE -ne 0 -or -not [string]::IsNullOrWhiteSpace(
        ($otaLoaderStatus -join "`n"))) {
    throw "Existing BLE App OTA Loader has worktree changes."
}

$sourceSha = $(if ($null -ne $bootstrap) {
    (Get-FileHash -LiteralPath $bootstrap -Algorithm SHA256).Hash
} else {
    (Get-FileHash -LiteralPath $bundle -Algorithm SHA256).Hash
})
$sourceReceipt = $null
if ($null -eq $bootstrap) {
    $receiptRoot = Join-Path $repo (
        ".cache\validation\comp-req-775-incremental-sync\resource-ota"
    )
    foreach ($candidate in Get-ChildItem -LiteralPath $receiptRoot `
            -Filter "*-receipt.json" -File) {
        $parsed = Get-Content -LiteralPath $candidate.FullName -Raw |
            ConvertFrom-Json -AsHashtable
        if ([string]$parsed.bundle.sha256 -eq $sourceSha) {
            $sourceReceipt = $parsed
            break
        }
    }
    if ($null -eq $sourceReceipt) {
        throw "CUOT source has no matching machine receipt."
    }
    $sourceResourceId = [string]$sourceReceipt.generation.resource_id
    $sourceBaseCempSha = [string]$sourceReceipt.base_cemp.sha256
} else {
    [byte[]]$bootstrapBytes = [IO.File]::ReadAllBytes($bootstrap)
    if ($bootstrapBytes.Length -ne 0x200000 -or
        [Text.Encoding]::ASCII.GetString($bootstrapBytes, 0, 4) -ne "CEMP") {
        throw "Bootstrap source is not a 2 MiB CEMP partition."
    }
    [int]$baseBytes = [BitConverter]::ToUInt32($bootstrapBytes, 8)
    [byte[]]$basePayload = $bootstrapBytes[0..($baseBytes - 1)]
    $sourceBaseCempSha = [Convert]::ToHexString(
        [Security.Cryptography.SHA256]::HashData($basePayload)
    )
    $rootOffset = $null
    foreach ($offset in @(0x1FE000, 0x1FF000)) {
        if ([Text.Encoding]::ASCII.GetString(
                $bootstrapBytes, $offset, 4) -eq "CUIR") {
            if ($null -ne $rootOffset) {
                throw "Bootstrap contains more than one root marker."
            }
            $rootOffset = $offset
        }
    }
    if ($null -eq $rootOffset) {
        throw "Bootstrap has no generation root."
    }
    [byte[]]$resourceIdBytes = $bootstrapBytes[
        ($rootOffset + 44)..($rootOffset + 75)
    ]
    $sourceResourceId = [Convert]::ToHexString($resourceIdBytes)
}
if ($sourceBaseCempSha -ne [string]$offline.base_cemp_sha256) {
    if (-not $AllowCurrentPageResourceRevision) {
        throw "Selected source does not match the fixed browser resource contract."
    }
    if ($null -ne $bootstrap) {
        $sourceRoot = Split-Path -Parent $sourceManifestPath
        $candidateCempRoot = Join-Path $sourceRoot "cemp"
        $candidateCempManifestPath = Join-Path $candidateCempRoot "manifest.json"
        $candidateCempVerificationPath = Join-Path $candidateCempRoot "verification.json"
        if (-not (Test-Path -LiteralPath $candidateCempManifestPath -PathType Leaf) -or
            -not (Test-Path -LiteralPath $candidateCempVerificationPath -PathType Leaf)) {
            throw (
                "Current-page base CEMP revision is missing its manifest or " +
                "source-bound verification."
            )
        }
        $candidateCempManifest = Get-Content `
            -LiteralPath $candidateCempManifestPath -Raw |
            ConvertFrom-Json -AsHashtable
        $candidateCempVerification = Get-Content `
            -LiteralPath $candidateCempVerificationPath -Raw |
            ConvertFrom-Json -AsHashtable
        $sourceManifestSha = (
            Get-FileHash -LiteralPath $sourceManifestPath -Algorithm SHA256
        ).Hash
        $candidateCempManifestSha = (
            Get-FileHash -LiteralPath $candidateCempManifestPath -Algorithm SHA256
        ).Hash
        $candidateChecksPass = $true
        foreach ($check in $candidateCempVerification.checks.Values) {
            if (-not [bool]$check) {
                $candidateChecksPass = $false
                break
            }
        }
        if ([string]$candidateCempVerification.status -ne
                "PASS_CEMP_EXTERNAL_SOURCE_BOUND" -or
            [string]$candidateCempVerification.pack_sha256 -ne
                $sourceBaseCempSha -or
            [string]$candidateCempVerification.manifest_sha256 -ne
                $candidateCempManifestSha -or
            -not $candidateChecksPass -or
            [int]$candidateCempVerification.failures.Count -ne 0 -or
            [string]$candidateCempManifest.source.browser_page_sha256 -ne
                $pageSha -or
            [string]$candidateCempManifest.source.source_pack_manifest_sha256 -ne
                $sourceManifestSha) {
            throw (
                "Current-page base CEMP revision is not bound to the selected " +
                "page, source manifest, bootstrap payload, and roundtrip proof."
            )
        }
    } else {
        if ([string]::IsNullOrWhiteSpace($GenerationVerificationPath)) {
            throw "Current-page CUOT requires -GenerationVerificationPath."
        }
        $generationVerification = Resolve-RepoPath $GenerationVerificationPath
        if (-not (Test-Path -LiteralPath $generationVerification -PathType Leaf)) {
            throw "Generation equivalence verification is missing."
        }
        $generationEvidence = Get-Content `
            -LiteralPath $generationVerification -Raw |
            ConvertFrom-Json -AsHashtable
        $selectedSourceManifest = Get-Content `
            -LiteralPath $sourceManifestPath -Raw |
            ConvertFrom-Json -AsHashtable
        if ([string]$generationEvidence.status -ne
                "PASS_UI_ASSET_GENERATION_EQUIVALENT" -or
            [string]$generationEvidence.base_cemp_sha256 -ne
                $sourceBaseCempSha -or
            [string]$generationEvidence.resource_id -ne
                $sourceResourceId -or
            [string]$generationEvidence.page_sha256 -ne $pageSha -or
            -not [bool]$generationEvidence.strict_1bpp -or
            [int]$generationEvidence.states_checked -ne
                [int]$selectedSourceManifest.invariants.state_count) {
            throw (
                "Current-page CUOT is not bound to the selected base CEMP, " +
                "page, resource id, state count, and strict 1bpp proof."
            )
        }
    }
}
if ($AllowCurrentPageResourceRevision -and $null -eq $bootstrap -and
    $sourceBaseCempSha -eq [string]$offline.base_cemp_sha256) {
    if ([string]::IsNullOrWhiteSpace($GenerationVerificationPath)) {
        throw "Current-page CUOT requires -GenerationVerificationPath."
    }
    $generationVerification = Resolve-RepoPath $GenerationVerificationPath
    if (-not (Test-Path -LiteralPath $generationVerification -PathType Leaf)) {
        throw "Generation equivalence verification is missing."
    }
    $generationEvidence = Get-Content `
        -LiteralPath $generationVerification -Raw |
        ConvertFrom-Json -AsHashtable
    $selectedSourceManifest = Get-Content `
        -LiteralPath $sourceManifestPath -Raw |
        ConvertFrom-Json -AsHashtable
    if ([string]$generationEvidence.status -ne
            "PASS_UI_ASSET_GENERATION_EQUIVALENT" -or
        [string]$generationEvidence.base_cemp_sha256 -ne
            $sourceBaseCempSha -or
        [string]$generationEvidence.resource_id -ne
            $sourceResourceId -or
        [string]$generationEvidence.page_sha256 -ne $pageSha -or
        -not [bool]$generationEvidence.strict_1bpp -or
        [int]$generationEvidence.states_checked -ne
            [int]$selectedSourceManifest.invariants.state_count) {
        throw (
            "Current-page CUOT is not bound to the selected base CEMP, " +
            "page, resource id, state count, and strict 1bpp proof."
        )
    }
}
$performanceReceipt = Get-Content -LiteralPath $performanceReceiptPath -Raw |
    ConvertFrom-Json -AsHashtable
if ($PerformanceProbe) {
    if ($sourceResourceId -ne
            [string]$performanceReceipt.generation.resource_id -or
        [int]$sourceReceipt.generation.blob_bytes -ne
            [int]$offline.generation.one_frame_blob_bytes -or
        [uint32]$sourceReceipt.generation.blob_crc32 -ne
            [uint32]$performanceReceipt.generation.blob_crc32 -or
        [uint32]$sourceReceipt.generation.manifest_crc32 -ne
            [uint32]$performanceReceipt.generation.manifest_crc32) {
        throw "Performance probe is not the registered one-frame delta."
    }
} elseif (-not $AllowCurrentPageResourceRevision -and
          $sourceResourceId -ne [string]$offline.resource_id) {
    throw "Selected source does not match the fixed browser resource contract."
} elseif ($AllowCurrentPageResourceRevision) {
    $sourceManifest = Get-Content -LiteralPath $sourceManifestPath -Raw |
        ConvertFrom-Json -AsHashtable
    if ([string]$sourceManifest.status -ne "PASS" -or
        [string]$sourceManifest.source.page_sha256 -ne $pageSha -or
        [int]$sourceManifest.format.width -ne 200 -or
        [int]$sourceManifest.format.height -ne 200 -or
        [int]$sourceManifest.format.frame_bytes -ne 5000 -or
        [int]$sourceManifest.invariants.state_count -le 0) {
        throw (
            "Current-page resource revision does not preserve the fixed " +
            "browser 200x200 1bpp source contract."
        )
    }
}

$arguments = @(
    $syncTool,
    "--loader", $loader,
    "--probe-serial", $ProgrammerSerial,
    "--workspace", $workspace,
    "--receipt", $receipt,
    "--recording-resource-pack", $recordingResourcePack,
    "--allow-hardware",
    "--workflow-lock-held",
    "--swd-mutex-held"
)
if ($null -ne $bootstrap) {
    $arguments += @("--bootstrap-image", $bootstrap)
    if ($AllowCurrentPageResourceRevision -and
        $sourceBaseCempSha -ne [string]$offline.base_cemp_sha256) {
        $arguments += "--allow-base-migration"
    }
} else {
    $arguments += @("--bundle", $bundle)
    if ($AllowGenerationCompaction) {
        $arguments += "--allow-generation-compaction"
    }
}

if (-not $Execute) {
    $executeCommand = (
        "pwsh -NoProfile -File .\tools\" +
        "run_comp_req_775_external_loader_sync.ps1 -Execute"
    )
    if ($null -ne $bootstrap) {
        $executeCommand += " -BootstrapImage `"$bootstrap`""
    } elseif ($PSBoundParameters.ContainsKey("BundlePath")) {
        $executeCommand += " -BundlePath `"$bundle`""
    }
    if ($CaptureMenuBoundary) {
        $executeCommand += " -CaptureMenuBoundary"
    }
    if ($PerformanceProbe) {
        $executeCommand += " -PerformanceProbe"
    }
    if ($PSBoundParameters.ContainsKey("BrowserSourceManifestPath")) {
        $executeCommand += (
            " -BrowserSourceManifestPath `"$sourceManifestPath`""
        )
    }
    if ($PSBoundParameters.ContainsKey("GenerationVerificationPath")) {
        $executeCommand += (
            " -GenerationVerificationPath `"$generationVerification`""
        )
    }
    if ($AllowCurrentPageResourceRevision) {
        $executeCommand += " -AllowCurrentPageResourceRevision"
    }
    if ($AllowGenerationCompaction) {
        $executeCommand += " -AllowGenerationCompaction"
    }
    [ordered]@{
        schema = "companion.comp_req_775.external_loader_runner.v1"
        status = "CHECK_ONLY"
        source = $(if ($null -ne $bootstrap) { $bootstrap } else { $bundle })
        source_kind = $(if ($null -ne $bootstrap) {
            "bootstrap_partition"
        } else {
            "cuot"
        })
        loader = $loader
        receipt = $receipt
        programmer_serial = $ProgrammerSerial
        port_name = $PortName
        capture_menu_boundary = [bool]$CaptureMenuBoundary
        performance_probe = [bool]$PerformanceProbe
        preflight = [ordered]@{
            fixed_url = $fixedUrl
            http_status = 200
            page_sha256 = $pageSha
            http_body_sha256 = $httpSha
            base_cemp_sha256 = $sourceBaseCempSha
            resource_id = $sourceResourceId
            fixed_page_target = (
                -not [bool]$PerformanceProbe -and
                (
                    $sourceResourceId -eq [string]$offline.resource_id -or
                    [bool]$AllowCurrentPageResourceRevision
                )
            )
            current_page_resource_revision = (
                [bool]$AllowCurrentPageResourceRevision
            )
            generation_compaction = [bool]$AllowGenerationCompaction
            existing_app_ota_loader_unchanged = $true
            external_loader_exact_2mib = $true
            recording_resource_pack_sha256 = $recordingResourceSha
            boot_chain_read_only_fail_closed = $true
        }
        execute_command = $executeCommand
        hardware_contact = 0
    } | ConvertTo-Json -Depth 4
    exit 0
}

. (Join-Path $repo "tools\companion_wb55_lock.ps1")
$lockContext = $null
$swdMutex = $null
$swdOwned = $false
$serialPort = $null
try {
    $lockContext = Enter-CompanionWb55Lock -Purpose (
        "COMP-REQ-775 External Loader UI resource sync"
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
        throw (
            "Companion WB55 SWD/COM lock is already held; " +
            "zero hardware contact."
        )
    }
    [Environment]::SetEnvironmentVariable(
        "COMPANION_WB55_SWD_MUTEX_HELD", "1", "Process"
    )
    New-Item -ItemType Directory -Force -Path $workspace | Out-Null
    & python $bootChainVerifier `
        --programmer $programmer `
        --programmer-serial $ProgrammerSerial `
        --loader-hex $formalLoader `
        --workspace $workspace `
        --receipt $bootChainEvidencePath `
        --allow-hardware `
        --workflow-lock-held `
        --swd-mutex-held | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw (
            "Boot-chain read-only preflight failed before external Flash " +
            "contact; see $bootChainEvidencePath"
        )
    }
    $bootChainEvidence = Get-Content -LiteralPath $bootChainEvidencePath -Raw |
        ConvertFrom-Json -AsHashtable
    $serialPort = [IO.Ports.SerialPort]::new(
        $PortName, 115200, [IO.Ports.Parity]::None, 8,
        [IO.Ports.StopBits]::One
    )
    $serialPort.ReadTimeout = 120
    $serialPort.Open()
    $serialPort.DiscardInBuffer()
    & python @arguments
    if ($LASTEXITCODE -ne 0) {
        throw "External Loader resource sync failed with exit $LASTEXITCODE"
    }
    $capture = [Collections.Generic.List[string]]::new()
    $deadline = (Get-Date).AddSeconds($BootCaptureSeconds)
    while ((Get-Date) -lt $deadline) {
        try {
            $line = $serialPort.ReadLine().Trim()
            if ($line.Length -gt 0) {
                $capture.Add($line)
                $joined = $capture -join "`n"
                if ($joined -match "\[screen-assets\] ui_generation=active" -and
                    $joined -match "identity=comp_req_638 mount=ok" -and
                    $joined -match (
                        "\[rec-resource\] mount=ok base=0x001DC000 " +
                        "pack_bytes=133851 g7_bytes=112000 opus_bytes=21723"
                    ) -and
                    $joined -match (
                        "accepted_product_driver.*control=0xFF.*" +
                        "has_busy=1.*result=1"
                    ) -and
                    # The boot verifier requires choreography to cross the
                    # legacy five-partial boundary.  Do not stop at the first
                    # CF frame (partial_before=1), which creates a guaranteed
                    # short-log false negative.
                    $joined -match (
                        "accepted_product_driver.*control=0xCF.*" +
                        "partial_before=(?:[5-9]|[1-9][0-9]+).*" +
                        "has_busy=1.*result=1"
                    ) -and
                    $joined -match "\[screen-life\].*frame_index=\d+") {
                    break
                }
            }
        } catch [TimeoutException] {
        }
    }
    $serialPort.Close()
    $serialPort.Dispose()
    $serialPort = $null
    $bootText = $capture -join "`n"
    [IO.File]::WriteAllText(
        $bootLog,
        $(if ($bootText.Length -gt 0) { $bootText + "`n" } else { "" }),
        [Text.UTF8Encoding]::new($false)
    )
    & python $bootVerifier `
        --log $bootLog `
        --source-manifest $sourceManifestPath `
        --page-sha256 $pageSha `
        --receipt $bootEvidencePath | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "Ordinary-reset screen evidence failed; see $bootLog"
    }
    $bootEvidence = Get-Content -LiteralPath $bootEvidencePath -Raw |
        ConvertFrom-Json -AsHashtable
    $result = Get-Content -LiteralPath $receipt -Raw |
        ConvertFrom-Json -AsHashtable
    $bootChecks = [ordered]@{
        ordinary_reset_performed = [bool]$result.ordinary_reset_performed
        partition_readback_verified = [bool]$result.partition_readback_verified
        ui_generation_active = [bool]$bootEvidence.checks.ui_generation_active
        base_cemp_mount_ok = [bool]$bootEvidence.checks.base_cemp_mount_ok
        real_busy_path_observed = (
            [bool]$bootEvidence.checks.real_busy_path_observed
        )
        browser_runtime_first_frame_exact = (
            [bool]$bootEvidence.checks.browser_runtime_first_frame_exact
        )
        target_resource_matches_fixed_page = (
            [string]$result.target_root.resource_id -eq $sourceResourceId
        )
        target_base_cemp_matches_fixed_page = (
            [string]$result.cemp.target.sha256 -eq $sourceBaseCempSha
        )
        no_runtime_fault = [bool]$bootEvidence.checks.no_runtime_fault
    }
    if ($bootChecks.Values -contains $false) {
        throw "Ordinary-reset screen evidence failed; see $bootLog"
    }
    $menuEvidence = $null
    if ($CaptureMenuBoundary) {
        $serialPort = [IO.Ports.SerialPort]::new(
            $PortName, 115200, [IO.Ports.Parity]::None, 8,
            [IO.Ports.StopBits]::One
        )
        $serialPort.ReadTimeout = 120
        $serialPort.Open()
        $serialPort.DiscardInBuffer()
        Write-Host (
            "ACTION: hold anywhere for about 3 seconds to enter the menu; " +
            "after the refresh completes, swipe right to return."
        )
        $menuCapture = [Collections.Generic.List[string]]::new()
        $menuDeadline = (Get-Date).AddSeconds($MenuCaptureSeconds)
        while ((Get-Date) -lt $menuDeadline) {
            try {
                $line = $serialPort.ReadLine().Trim()
                if ($line.Length -gt 0) {
                    $menuCapture.Add($line)
                    $menuText = $menuCapture -join "`n"
                    $driverCount = [regex]::Matches(
                        $menuText,
                        (
                            "accepted_product_driver.*maintenance=1.*" +
                            "has_busy=1.*result=1"
                        )
                    ).Count
                    if ($menuText -match (
                            "\[touch-ui\] daily_to_menu " +
                            "gesture=any_long_press"
                        ) -and
                        $menuText -match "\[screen\] menu_boundary=enter" -and
                        $menuText -match (
                            "\[touch-ui\] menu_right_swipe_exit"
                        ) -and
                        $menuText -match "\[screen\] menu_boundary=exit" -and
                        $driverCount -ge 2) {
                        break
                    }
                }
            } catch [TimeoutException] {
            }
        }
        $serialPort.Close()
        $serialPort.Dispose()
        $serialPort = $null
        $menuText = $menuCapture -join "`n"
        [IO.File]::WriteAllText(
            $menuLog,
            $(if ($menuText.Length -gt 0) {
                $menuText + "`n"
            } else {
                ""
            }),
            [Text.UTF8Encoding]::new($false)
        )
        & python $menuVerifier `
            --log $menuLog `
            --receipt $menuEvidencePath | Out-Null
        if ($LASTEXITCODE -ne 0) {
            throw "Menu boundary evidence failed; see $menuLog"
        }
        $menuEvidence = Get-Content -LiteralPath $menuEvidencePath -Raw |
            ConvertFrom-Json -AsHashtable
    }
    $result.status = $(if ($PerformanceProbe) {
        "MACHINE_READY_RESTORE_REQUIRED"
    } elseif ($CaptureMenuBoundary) {
        "MACHINE_READY_OPERATOR_PENDING"
    } else {
        "MACHINE_READY_MENU_PENDING"
    })
    $result.workflow_lock = Get-CompanionWb55LockEvidenceSummary $lockContext
    $result.runner = "tools/run_comp_req_775_external_loader_sync.ps1"
    $result.boot_chain_preflight = $bootChainEvidence
    $result.browser_contract = [ordered]@{
        fixed_url = $fixedUrl
        http_status = 200
        page_sha256 = $pageSha
        http_body_sha256 = $httpSha
        source_manifest = $sourceManifestPath
        source_manifest_page_sha256 = $pageSha
        resource_id = $sourceResourceId
        base_cemp_sha256 = $sourceBaseCempSha
        fixed_page_target = -not [bool]$PerformanceProbe
        contract = $(if ($PerformanceProbe) {
            "registered synthetic one-frame performance probe"
        } else {
            "fixed browser resource"
        })
    }
    $result.existing_app_ota = [ordered]@{
        loader_worktree_unchanged = $true
        behavior_changed = $false
        resource_ota_is_separate_target = $true
    }
    $result.ordinary_reset = [ordered]@{
        log = $bootLog
        log_sha256 = (
            Get-FileHash -LiteralPath $bootLog -Algorithm SHA256
        ).Hash
        checks = $bootChecks
        first_browser_frame = $bootEvidence.first_browser_frame
    }
    $result.menu_boundary = $(if ($CaptureMenuBoundary) {
        [ordered]@{
            log = $menuLog
            log_sha256 = [string]$menuEvidence.log_sha256
            evidence = $menuEvidence
        }
    } else {
        $null
    })
    $result.remaining_machine_gate = $(if ($PerformanceProbe) {
        (
            "restore exact fixed-browser generation, capture menu " +
            "boundaries, then prove final no-op"
        )
    } elseif ($CaptureMenuBoundary) {
        $null
    } else {
        "menu enter/exit maintenance-boundary real-BUSY capture"
    })
    $result.remaining_human_gate = (
        "canonical Chinese fixed-browser versus physical-screen review"
    )
    $result | ConvertTo-Json -Depth 16 |
        Set-Content -LiteralPath $receipt -Encoding utf8
} catch {
    if (Test-Path -LiteralPath $receipt -PathType Leaf) {
        try {
            $failed = Get-Content -LiteralPath $receipt -Raw |
                ConvertFrom-Json -AsHashtable
            $failed.status = "FAILED"
            $failed.error = $_.Exception.Message
            $failed.runner = "tools/run_comp_req_775_external_loader_sync.ps1"
            $failed | ConvertTo-Json -Depth 16 |
                Set-Content -LiteralPath $receipt -Encoding utf8
        } catch {
        }
    }
    throw
} finally {
    if ($serialPort) {
        if ($serialPort.IsOpen) {
            $serialPort.Close()
        }
        $serialPort.Dispose()
    }
    [Environment]::SetEnvironmentVariable(
        "COMPANION_WB55_SWD_MUTEX_HELD", $null, "Process"
    )
    if ($swdOwned -and $swdMutex) {
        $swdMutex.ReleaseMutex()
    }
    if ($swdMutex) {
        $swdMutex.Dispose()
    }
    if ($null -ne $lockContext) {
        Exit-CompanionWb55Lock
    }
}
