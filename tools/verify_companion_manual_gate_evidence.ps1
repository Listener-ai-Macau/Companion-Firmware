param(
    [string] $PackagePath,
    [string] $NativeBleBenchPath,
    [string] $A1A2SummaryPath,
    [string] $BleOtaEvidencePath,
    [string] $WiredFlashEvidencePath,
    [string] $TypeUiEvidencePath,
    [string] $OutDir,
    [switch] $IncludeTypeHarness,
    [switch] $IncludeTypeUiGate,
    [switch] $ChecklistOnly
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
if ([string]::IsNullOrWhiteSpace($OutDir)) {
    $OutDir = Join-Path $repoRoot ".cache\validation\companion-manual-gates-$stamp"
}
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
$outDirResolved = (Resolve-Path -LiteralPath $OutDir).Path

function Resolve-CompanionPackage {
    param([string] $Path)

    if (-not [string]::IsNullOrWhiteSpace($Path)) {
        return (Resolve-Path -LiteralPath $Path).Path
    }

    $packageRoot = Join-Path $repoRoot ".cache\ota_firmware"
    $latest = Get-ChildItem -LiteralPath $packageRoot -Filter "companion-ota-*.zip" -File -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1
    if (-not $latest) {
        return $null
    }
    return $latest.FullName
}

function Get-ZipEntry {
    param(
        [Parameter(Mandatory = $true)] $Archive,
        [Parameter(Mandatory = $true)][string] $Name
    )

    $normalized = ($Name -replace "\\", "/").TrimStart("/")
    $matches = @($Archive.Entries | Where-Object {
            -not $_.FullName.EndsWith("/") -and
            (($_.FullName -replace "\\", "/").TrimStart("/")) -eq $normalized
        })
    if ($matches.Count -ne 1) {
        throw "Expected exactly one zip entry '$normalized', found $($matches.Count)."
    }
    return $matches[0]
}

function Get-ZipEntryText {
    param([Parameter(Mandatory = $true)] $Entry)

    $stream = $Entry.Open()
    try {
        $reader = [System.IO.StreamReader]::new($stream, [System.Text.Encoding]::UTF8)
        try {
            return $reader.ReadToEnd()
        } finally {
            $reader.Dispose()
        }
    } finally {
        $stream.Dispose()
    }
}

function Get-CompanionPackageInfo {
    param([string] $Path)

    if ([string]::IsNullOrWhiteSpace($Path)) {
        return $null
    }

    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $archive = [System.IO.Compression.ZipFile]::OpenRead($Path)
    try {
        $manifest = (Get-ZipEntryText -Entry (Get-ZipEntry -Archive $archive -Name "ota_manifest.json")) | ConvertFrom-Json
        return [ordered]@{
            path = $Path
            file_name = [System.IO.Path]::GetFileName($Path)
            version = [string]$manifest.version
            hardware_revision = [string]$manifest.hardware_revision
            protocol = [string]$manifest.protocol.name
            firmware_sha256 = ([string]$manifest.file.sha256).ToLowerInvariant()
        }
    } finally {
        $archive.Dispose()
    }
}

function Get-JsonAnyProperty {
    param(
        [Parameter(Mandatory = $true)] $Object,
        [Parameter(Mandatory = $true)][string[]] $Names
    )

    if ($null -eq $Object) {
        return $null
    }
    foreach ($name in $Names) {
        $property = $Object.PSObject.Properties[$name]
        if ($property) {
            return $property.Value
        }
    }
    return $null
}

function Resolve-LatestA1A2Summary {
    $root = Join-Path $repoRoot ".cache\validation"
    $latest = Get-ChildItem -LiteralPath $root -Filter "companion-type-a1-a2-summary.json" -Recurse -File -ErrorAction SilentlyContinue |
        Where-Object { $_.DirectoryName -match "companion-type-a1-a2-" } |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1
    if ($latest) { return $latest.FullName }
    return $null
}

function Resolve-LatestNativeBleBench {
    $root = Join-Path $repoRoot ".cache\validation"
    $latest = Get-ChildItem -LiteralPath $root -Filter "companion-ble-real-bench.json" -Recurse -File -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1
    if ($latest) { return $latest.FullName }
    return $null
}

function Read-EvidenceText {
    param([string] $Path)

    if ([string]::IsNullOrWhiteSpace($Path) -or -not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        return $null
    }
    return Get-Content -LiteralPath $Path -Raw -Encoding UTF8
}

function ConvertFrom-EvidenceJson {
    param(
        [string] $Text,
        [string[]] $Prefixes = @()
    )

    if ([string]::IsNullOrWhiteSpace($Text)) {
        return $null
    }

    $trimmed = $Text.Trim()
    if ($trimmed.StartsWith("{") -and $trimmed.EndsWith("}")) {
        try { return $trimmed | ConvertFrom-Json } catch {}
    }

    foreach ($line in ($Text -split "\r?\n")) {
        $candidate = $line.Trim()
        foreach ($prefix in $Prefixes) {
            if ($candidate.StartsWith($prefix, [System.StringComparison]::Ordinal)) {
                $candidate = $candidate.Substring($prefix.Length).Trim()
                break
            }
        }
        if ($candidate.StartsWith("{") -and $candidate.EndsWith("}")) {
            try { return $candidate | ConvertFrom-Json } catch {}
        }
    }
    return $null
}

function New-GateResult {
    param(
        [Parameter(Mandatory = $true)][string] $Name,
        [Parameter(Mandatory = $true)][string] $Status,
        [string] $EvidencePath,
        [string[]] $Checks = @(),
        [string[]] $Errors = @(),
        [string] $ExpectedEvidence
    )

    return [ordered]@{
        name = $Name
        status = $Status
        evidence_path = $EvidencePath
        expected_evidence = $ExpectedEvidence
        checks = @($Checks)
        errors = @($Errors)
    }
}

function Test-CompanionA1A2Gate {
    param([string] $Path)

    $checks = [System.Collections.Generic.List[string]]::new()
    $errors = [System.Collections.Generic.List[string]]::new()
    if ([string]::IsNullOrWhiteSpace($Path)) {
        return New-GateResult -Name "legacy Type A1/A2 bench validation" -Status "MISSING" -ExpectedEvidence "Run tools\verify_companion_type_a1_a2.ps1 -Execute under workflow lock and keep companion-type-a1-a2-summary.json."
    }
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        return New-GateResult -Name "legacy Type A1/A2 bench validation" -Status "MISSING" -EvidencePath $Path -ExpectedEvidence "A1/A2 JSON summary file must exist."
    }

    $summary = (Get-Content -LiteralPath $Path -Raw -Encoding UTF8) | ConvertFrom-Json
    $status = [string](Get-JsonAnyProperty -Object $summary -Names @("status"))
    if ($status -eq "PASS") { $checks.Add("summary status PASS") | Out-Null } else { $errors.Add("summary status is '$status', expected PASS") | Out-Null }

    $summaryErrors = @(Get-JsonAnyProperty -Object $summary -Names @("errors"))
    if ($summaryErrors.Count -eq 0) { $checks.Add("summary errors empty") | Out-Null } else { $errors.Add("summary contains $($summaryErrors.Count) error(s)") | Out-Null }

    $maxMissing = [int](Get-JsonAnyProperty -Object $summary -Names @("max_missing_packets", "maxMissingPackets"))
    $results = @(Get-JsonAnyProperty -Object $summary -Names @("results"))
    $a1 = @($results | Where-Object { [string](Get-JsonAnyProperty -Object $_ -Names @("case")) -eq "A1" })
    $a2 = @($results | Where-Object { [string](Get-JsonAnyProperty -Object $_ -Names @("case")) -eq "A2" })
    if ($a1.Count -ge 5) { $checks.Add("A1 result count $($a1.Count) >= 5") | Out-Null } else { $errors.Add("A1 result count $($a1.Count) < 5") | Out-Null }
    if ($a2.Count -ge 1) { $checks.Add("A2 result count $($a2.Count) >= 1") | Out-Null } else { $errors.Add("A2 result missing") | Out-Null }

    foreach ($item in $results) {
        $caseId = [string](Get-JsonAnyProperty -Object $item -Names @("case"))
        $round = [string](Get-JsonAnyProperty -Object $item -Names @("round"))
        $itemStatus = [string](Get-JsonAnyProperty -Object $item -Names @("status"))
        $pcm = [int64](Get-JsonAnyProperty -Object $item -Names @("pcm_bytes", "pcmBytes"))
        $missing = [int](Get-JsonAnyProperty -Object $item -Names @("missing_packets", "missingPackets"))
        if ($itemStatus -ne "PASS") { $errors.Add("$caseId round $round status is $itemStatus") | Out-Null }
        if ($pcm -le 0) { $errors.Add("$caseId round $round pcm_bytes is $pcm") | Out-Null }
        if ($missing -gt $maxMissing) { $errors.Add("$caseId round $round missing_packets $missing > $maxMissing") | Out-Null }
    }
    if ($errors.Count -eq 0) { $checks.Add("all A1/A2 rounds have PCM and missing_packets within limit") | Out-Null }

    $gateStatus = if ($errors.Count -eq 0) { "PASS" } else { "FAIL" }
    return New-GateResult -Name "legacy Type A1/A2 bench validation" -Status $gateStatus -EvidencePath $Path -Checks $checks -Errors $errors -ExpectedEvidence "PASS JSON and Markdown under .cache\validation\companion-type-a1-a2-*."
}

function Test-CompanionNativeBleGate {
    param([string] $Path)

    $checks = [System.Collections.Generic.List[string]]::new()
    $errors = [System.Collections.Generic.List[string]]::new()
    if ([string]::IsNullOrWhiteSpace($Path)) {
        return New-GateResult -Name "real Companion-native BLE GATT bench validation" -Status "MISSING" -ExpectedEvidence "Run tools\companion_ble_real_bench.py against real Companion hardware under workflow lock and keep companion-ble-real-bench.json."
    }
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        return New-GateResult -Name "real Companion-native BLE GATT bench validation" -Status "MISSING" -EvidencePath $Path -ExpectedEvidence "Native BLE bench JSON summary file must exist."
    }

    $summary = (Get-Content -LiteralPath $Path -Raw -Encoding UTF8) | ConvertFrom-Json
    $status = [string](Get-JsonAnyProperty -Object $summary -Names @("status"))
    if ($status -eq "PASS") { $checks.Add("native BLE bench status PASS") | Out-Null } else { $errors.Add("native BLE bench status is '$status', expected PASS") | Out-Null }

    $operationsValue = Get-JsonAnyProperty -Object $summary -Names @("operations")
    $operations = @()
    if ($operationsValue) {
        $operations = @($operationsValue)
    }
    $operationNames = @($operations | ForEach-Object { [string](Get-JsonAnyProperty -Object $_ -Names @("operation")) })
    foreach ($required in @("scan", "service_discovery", "status_read", "card_write", "recording_control_and_list", "recording_chunk_refusal", "settings_write", "diagnostics_log_pull", "delete_privacy_refusal", "ota_readiness")) {
        if ($operationNames -contains $required) {
            $checks.Add("native BLE operation '$required' present") | Out-Null
        } else {
            $errors.Add("native BLE operation '$required' missing") | Out-Null
        }
    }

    $discovery = @($operations | Where-Object { [string](Get-JsonAnyProperty -Object $_ -Names @("operation")) -eq "service_discovery" }) | Select-Object -First 1
    if ($discovery) {
        $serviceCount = [int](Get-JsonAnyProperty -Object $discovery -Names @("service_count"))
        $charCount = [int](Get-JsonAnyProperty -Object $discovery -Names @("characteristic_count"))
        if ($serviceCount -ge 10) { $checks.Add("native BLE service_count $serviceCount >= 10") | Out-Null } else { $errors.Add("native BLE service_count $serviceCount < 10") | Out-Null }
        if ($charCount -ge 20) { $checks.Add("native BLE characteristic_count $charCount >= 20") | Out-Null } else { $errors.Add("native BLE characteristic_count $charCount < 20") | Out-Null }
    }

    $gateStatus = if ($errors.Count -eq 0) { "PASS" } else { "FAIL" }
    return New-GateResult -Name "real Companion-native BLE GATT bench validation" -Status $gateStatus -EvidencePath $Path -Checks $checks -Errors $errors -ExpectedEvidence "PASS JSON from tools\companion_ble_real_bench.py showing scan, service discovery, native writes/reads, diagnostics, privacy refusal, and OTA readiness."
}

function Test-CompanionBleOtaGate {
    param(
        [string] $Path,
        $PackageInfo
    )

    $checks = [System.Collections.Generic.List[string]]::new()
    $errors = [System.Collections.Generic.List[string]]::new()
    if ([string]::IsNullOrWhiteSpace($Path)) {
        return New-GateResult -Name "real Companion BLE OTA bench validation" -Status "MISSING" -ExpectedEvidence "Run tools\verify_companion_ble_ota.ps1 -Execute under workflow lock and provide firmware_ota_result.json, its raw log, or companion-ble-ota-summary.json."
    }
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        return New-GateResult -Name "real Companion BLE OTA bench validation" -Status "MISSING" -EvidencePath $Path -ExpectedEvidence "BLE OTA evidence file must exist; prefer tools\verify_companion_ble_ota.ps1 output."
    }

    $text = Read-EvidenceText -Path $Path
    $json = ConvertFrom-EvidenceJson -Text $text -Prefixes @("firmware_ota_result_json=", "companion_ble_ota_result_json=")
    if ($json) {
        $wrapperReportPath = [string](Get-JsonAnyProperty -Object $json -Names @("transfer_report_json", "transferReportJson", "type_report_json", "typeReportJson"))
        if ($wrapperReportPath) {
            if (-not [System.IO.Path]::IsPathRooted($wrapperReportPath)) {
                $wrapperReportPath = Join-Path (Split-Path -Parent $Path) $wrapperReportPath
            }
            if (Test-Path -LiteralPath $wrapperReportPath -PathType Leaf) {
                $json = (Get-Content -LiteralPath $wrapperReportPath -Raw -Encoding UTF8) | ConvertFrom-Json
                $checks.Add("loaded Companion OTA transfer report from wrapper") | Out-Null
            } else {
                $errors.Add("Companion BLE OTA wrapper transfer_report_json does not exist: $wrapperReportPath") | Out-Null
            }
        }

        $status = [string](Get-JsonAnyProperty -Object $json -Names @("status"))
        if ($status -eq "PASS") { $checks.Add("OTA report status PASS") | Out-Null } else { $errors.Add("OTA report status is '$status', expected PASS") | Out-Null }

        $manifest = Get-JsonAnyProperty -Object $json -Names @("manifest")
        $transfer = Get-JsonAnyProperty -Object $json -Names @("transfer")
        $protocol = [string](Get-JsonAnyProperty -Object $manifest -Names @("protocolName", "protocol_name"))
        $version = [string](Get-JsonAnyProperty -Object $manifest -Names @("version"))
        $firmwareSha = ([string](Get-JsonAnyProperty -Object $json -Names @("firmwareSha256", "firmware_sha256"))).ToLowerInvariant()
        $transport = [string](Get-JsonAnyProperty -Object $transfer -Names @("transport"))
        $bytes = [int64](Get-JsonAnyProperty -Object $transfer -Names @("bytesTransferred", "bytes_transferred"))
        $confirmed = [bool](Get-JsonAnyProperty -Object $transfer -Names @("versionConfirmed", "version_confirmed"))

        if ($protocol -eq "denzic_ota_v1") { $checks.Add("manifest protocol denzic_ota_v1") | Out-Null } else { $errors.Add("manifest protocol is '$protocol'") | Out-Null }
        if ($transport -eq "denzic_ota_v1") { $checks.Add("transfer transport denzic_ota_v1") | Out-Null } else { $errors.Add("transfer transport is '$transport'") | Out-Null }
        if ($bytes -gt 0) { $checks.Add("bytesTransferred $bytes > 0") | Out-Null } else { $errors.Add("bytesTransferred is $bytes") | Out-Null }
        if ($confirmed) { $checks.Add("Denzic OTA v1 completion/reboot handoff observed") | Out-Null } else { $errors.Add("versionConfirmed is false") | Out-Null }
        if ($PackageInfo) {
            if ($version -eq $PackageInfo.version) { $checks.Add("OTA version matches package $($PackageInfo.version)") | Out-Null } else { $errors.Add("OTA version '$version' does not match package '$($PackageInfo.version)'") | Out-Null }
            if ($firmwareSha -eq $PackageInfo.firmware_sha256) { $checks.Add("OTA firmware sha256 matches package") | Out-Null } else { $errors.Add("OTA firmware sha256 does not match package") | Out-Null }
        }
    } else {
        $lower = $text.ToLowerInvariant()
        if ($lower.Contains("denzic_ota_v1")) { $checks.Add("log mentions denzic_ota_v1") | Out-Null } else { $errors.Add("log does not mention denzic_ota_v1") | Out-Null }
        if ($lower.Contains("pass") -or $lower.Contains("completed") -or $lower.Contains("done")) { $checks.Add("log contains success wording") | Out-Null } else { $errors.Add("log does not contain success wording") | Out-Null }
        if ($lower.Contains("fail") -or $lower.Contains("error")) { $errors.Add("log contains fail/error wording; provide the structured companion_ble_ota_result_json line for a stronger check") | Out-Null }
        if ($PackageInfo -and $lower.Contains($PackageInfo.version.ToLowerInvariant())) { $checks.Add("log mentions package version $($PackageInfo.version)") | Out-Null }
    }

    $gateStatus = if ($errors.Count -eq 0) { "PASS" } else { "FAIL" }
    return New-GateResult -Name "real Companion BLE OTA bench validation" -Status $gateStatus -EvidencePath $Path -Checks $checks -Errors $errors -ExpectedEvidence "The bench host transfers the same Companion package over BLE and reports status=PASS, versionConfirmed=true, and transport=denzic_ota_v1."
}

function Test-CompanionWiredGate {
    param(
        [string] $Path,
        $PackageInfo
    )

    $checks = [System.Collections.Generic.List[string]]::new()
    $errors = [System.Collections.Generic.List[string]]::new()
    if ([string]::IsNullOrWhiteSpace($Path)) {
        return New-GateResult -Name "real Companion wired flash from same package" -Status "MISSING" -ExpectedEvidence "Provide tools\verify_companion_wired_flash.ps1 execute output, tools\flash.ps1 output, or companion_wired_flash_result_json for the same Companion package."
    }
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        return New-GateResult -Name "real Companion wired flash from same package" -Status "MISSING" -EvidencePath $Path -ExpectedEvidence "Wired flash evidence file must exist."
    }

    $text = Read-EvidenceText -Path $Path
    $json = ConvertFrom-EvidenceJson -Text $text -Prefixes @("wired_firmware_result_json=", "companion_wired_flash_result_json=")
    if ($json) {
        $wrapperReportPath = [string](Get-JsonAnyProperty -Object $json -Names @("type_report_json", "typeReportJson", "wired_report_json", "wiredReportJson"))
        if ($wrapperReportPath) {
            if (-not [System.IO.Path]::IsPathRooted($wrapperReportPath)) {
                $wrapperReportPath = Join-Path (Split-Path -Parent $Path) $wrapperReportPath
            }
            if (Test-Path -LiteralPath $wrapperReportPath -PathType Leaf) {
                $json = (Get-Content -LiteralPath $wrapperReportPath -Raw -Encoding UTF8) | ConvertFrom-Json
                $checks.Add("loaded Type wired_firmware_result_json from Companion wired flash wrapper") | Out-Null
            } else {
                $errors.Add("Companion wired flash wrapper type_report_json does not exist: $wrapperReportPath") | Out-Null
            }
        }

        $status = [string](Get-JsonAnyProperty -Object $json -Names @("status"))
        $mode = [string](Get-JsonAnyProperty -Object $json -Names @("mode"))
        $extra = Get-JsonAnyProperty -Object $json -Names @("extra")
        $flash = $null
        if ($extra) {
            $flash = Get-JsonAnyProperty -Object $extra -Names @("result")
        }
        if (-not $flash) {
            $flash = $json
        }

        $action = [string](Get-JsonAnyProperty -Object $flash -Names @("action"))
        $kind = [string](Get-JsonAnyProperty -Object $flash -Names @("kind"))
        $port = [string](Get-JsonAnyProperty -Object $flash -Names @("port"))
        $version = [string](Get-JsonAnyProperty -Object $flash -Names @("version"))
        $log = [string](Get-JsonAnyProperty -Object $flash -Names @("log"))
        $isCompanionFactoryFlash = ($mode -eq "execute" -and $action -eq "flash" -and $kind -eq "companion-wired-factory")
        if ($status -eq "PASS") { $checks.Add("wired Type report status PASS") | Out-Null } else { $errors.Add("wired Type report status is '$status', expected PASS") | Out-Null }
        if ($mode -eq "flash" -or $isCompanionFactoryFlash) { $checks.Add("wired execution mode accepted for companion factory flash") | Out-Null } else { $errors.Add("wired Type report mode is '$mode', expected flash") | Out-Null }
        if ($action -eq "flash") { $checks.Add("wired action flash") | Out-Null } else { $errors.Add("wired action is '$action'") | Out-Null }
        if ($kind -eq "factory" -or $kind -eq "companion-wired-factory") { $checks.Add("wired package kind factory") | Out-Null } else { $errors.Add("wired package kind is '$kind'") | Out-Null }
        if ($port -eq "SWD") { $checks.Add("wired port SWD") | Out-Null } else { $errors.Add("wired port is '$port'") | Out-Null }
        if ($log.Contains("STM32WB wired factory flash completed and verified by STM32CubeProgrammer")) { $checks.Add("STM32CubeProgrammer verification logged") | Out-Null } else { $errors.Add("wired log missing STM32CubeProgrammer completion") | Out-Null }
        if ($PackageInfo) {
            if ($version -eq $PackageInfo.version -or ((-not [string]::IsNullOrWhiteSpace($version)) -and $version.Contains([string]$PackageInfo.version))) { $checks.Add("wired version matches package $($PackageInfo.version)") | Out-Null } else { $errors.Add("wired version '$version' does not match package '$($PackageInfo.version)'") | Out-Null }
        }
    } else {
        $lower = $text.ToLowerInvariant()
        if ($lower.Contains("pass: companion wired factory package flashed")) { $checks.Add("flash.ps1 PASS line present") | Out-Null } else { $errors.Add("flash.ps1 PASS line missing") | Out-Null }
        if ($lower.Contains("factory artifact ota_loader") -and $lower.Contains("factory artifact app")) { $checks.Add("ota_loader and app factory artifacts were written") | Out-Null } else { $errors.Add("log must show ota_loader and app factory artifacts") | Out-Null }
        if ($lower.Contains("stm32cubeprogrammer")) { $checks.Add("STM32CubeProgrammer mentioned") | Out-Null } else { $errors.Add("STM32CubeProgrammer not mentioned") | Out-Null }
    }

    $gateStatus = if ($errors.Count -eq 0) { "PASS" } else { "FAIL" }
    return New-GateResult -Name "real Companion wired flash from same package" -Status $gateStatus -EvidencePath $Path -Checks $checks -Errors $errors -ExpectedEvidence "The same package factory ota_loader and app are flashed over ST-LINK/SWD."
}

function Test-CompanionTypeUiGate {
    param(
        [string] $Path,
        $PackageInfo
    )

    $checks = [System.Collections.Generic.List[string]]::new()
    $errors = [System.Collections.Generic.List[string]]::new()
    if ([string]::IsNullOrWhiteSpace($Path)) {
        return New-GateResult -Name "Type temporary Companion debug page" -Status "MISSING" -ExpectedEvidence "Provide a screenshot or exported log showing Companion page probe, A1, A2, same-package controls, and 总体验收 command pass."
    }
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        return New-GateResult -Name "Type temporary Companion debug page" -Status "MISSING" -EvidencePath $Path -ExpectedEvidence "Type UI evidence file must exist."
    }

    $item = Get-Item -LiteralPath $Path
    if ($item.Length -gt 0) { $checks.Add("evidence file is non-empty") | Out-Null } else { $errors.Add("evidence file is empty") | Out-Null }
    $text = $null
    if ($item.Extension -notmatch '^\.(png|jpg|jpeg|webp)$') {
        $text = Read-EvidenceText -Path $Path
    }
    $json = ConvertFrom-EvidenceJson -Text $text -Prefixes @("companion_type_ui_manual_result_json=")
    if ($json) {
        $schema = [string](Get-JsonAnyProperty -Object $json -Names @("schema"))
        $status = [string](Get-JsonAnyProperty -Object $json -Names @("status"))
        $confirmed = [bool](Get-JsonAnyProperty -Object $json -Names @("operator_confirmed", "operatorConfirmed"))
        $packagePath = [string](Get-JsonAnyProperty -Object $json -Names @("package_path", "packagePath"))
        $copiedEvidence = [string](Get-JsonAnyProperty -Object $json -Names @("copied_evidence_path", "copiedEvidencePath"))
        $promptTranscript = [string](Get-JsonAnyProperty -Object $json -Names @("prompt_transcript", "promptTranscript"))
        if ($schema -eq "companion.type_ui_manual.validation.v1") { $checks.Add("Type UI manual schema matched") | Out-Null } else { $errors.Add("Type UI schema is '$schema'") | Out-Null }
        if ($status -eq "PASS") { $checks.Add("Type UI manual status PASS") | Out-Null } else { $errors.Add("Type UI manual status is '$status', expected PASS") | Out-Null }
        if ($confirmed) { $checks.Add("operator confirmed BLE subscription, A1, A2, OTA/wired entries, and aggregate acceptance entry") | Out-Null } else { $errors.Add("operator_confirmed is false") | Out-Null }
        $requiredActions = @(Get-JsonAnyProperty -Object $json -Names @("required_actions", "requiredActions"))
        $requiredText = [string]::Join("`n", @($requiredActions | ForEach-Object { [string]$_ }))
        if ($requiredText.Contains("总体验收") -and $requiredText.Contains("Companion hardware acceptance")) {
            $checks.Add("Type UI required actions include the aggregate hardware acceptance command") | Out-Null
        } else {
            $errors.Add("Type UI required actions do not mention 总体验收 / Companion hardware acceptance") | Out-Null
        }
        if ($PackageInfo) {
            if ([System.IO.Path]::GetFileName($packagePath) -eq $PackageInfo.file_name) {
                $checks.Add("Type UI package matches $($PackageInfo.file_name)") | Out-Null
            } else {
                $errors.Add("Type UI package '$packagePath' does not match '$($PackageInfo.path)'") | Out-Null
            }
        }
        if ($copiedEvidence -and (Test-Path -LiteralPath $copiedEvidence -PathType Leaf)) {
            $checks.Add("Type UI copied evidence exists") | Out-Null
        } elseif ($promptTranscript -and (Test-Path -LiteralPath $promptTranscript -PathType Leaf)) {
            $checks.Add("Type UI prompt transcript exists") | Out-Null
        } else {
            $errors.Add("Type UI wrapper evidence is missing copied_evidence_path or prompt_transcript") | Out-Null
        }
    } elseif ($item.Extension -match '^\.(png|jpg|jpeg|webp)$') {
        $checks.Add("screenshot evidence extension $($item.Extension)") | Out-Null
    } else {
        $lower = $text.ToLowerInvariant()
        foreach ($token in @("companion", "a1", "a2")) {
            if ($lower.Contains($token)) { $checks.Add("log mentions $token") | Out-Null } else { $errors.Add("log missing $token") | Out-Null }
        }
        if ($lower.Contains("pass") -or $lower.Contains("complete") -or $lower.Contains("完成")) { $checks.Add("log contains success wording") | Out-Null } else { $errors.Add("log missing success wording") | Out-Null }
    }

    $gateStatus = if ($errors.Count -eq 0) { "PASS" } else { "FAIL" }
    return New-GateResult -Name "Type temporary Companion debug page" -Status $gateStatus -EvidencePath $Path -Checks $checks -Errors $errors -ExpectedEvidence "Manual UI pass through Settings > Companion Pendant bring-up, including visible BLE OTA, wired flash, and 总体验收 entries."
}

function ConvertTo-ManualGateMarkdown {
    param(
        [Parameter(Mandatory = $true)] $Report,
        [Parameter(Mandatory = $true)] $GateResults
    )

    $lines = @(
        "# Companion Manual Gate Evidence",
        "",
        "- Status: $($Report["status"])",
        "- Checklist only: $($Report["checklist_only"])",
        "- Generated: $($Report["generated_at"])",
        "- Package: ``$($Report["package_path"])``",
        "",
        "## Gates"
    )

    foreach ($gate in $GateResults) {
        $lines += ""
        $lines += "### $($gate["name"])"
        $lines += ""
        $lines += "- Status: $($gate["status"])"
        if ($gate["evidence_path"]) {
            $lines += "- Evidence: ``$($gate["evidence_path"])``"
        }
        $lines += "- Expected: $($gate["expected_evidence"])"
        foreach ($check in @($gate["checks"])) {
            $lines += "- PASS: $check"
        }
        foreach ($errorItem in @($gate["errors"])) {
            $lines += "- FAIL: $errorItem"
        }
    }
    return $lines
}

$resolvedPackage = Resolve-CompanionPackage -Path $PackagePath
$packageInfo = Get-CompanionPackageInfo -Path $resolvedPackage
if ([string]::IsNullOrWhiteSpace($NativeBleBenchPath)) {
    $NativeBleBenchPath = Resolve-LatestNativeBleBench
}
if ($IncludeTypeHarness -and [string]::IsNullOrWhiteSpace($A1A2SummaryPath)) {
    $A1A2SummaryPath = Resolve-LatestA1A2Summary
}

$gates = [System.Collections.Generic.List[object]]::new()
$gates.Add((Test-CompanionNativeBleGate -Path $NativeBleBenchPath)) | Out-Null
if ($IncludeTypeHarness) {
    $gates.Add((Test-CompanionA1A2Gate -Path $A1A2SummaryPath)) | Out-Null
}
$gates.Add((Test-CompanionBleOtaGate -Path $BleOtaEvidencePath -PackageInfo $packageInfo)) | Out-Null
$gates.Add((Test-CompanionWiredGate -Path $WiredFlashEvidencePath -PackageInfo $packageInfo)) | Out-Null
if ($IncludeTypeUiGate) {
    $gates.Add((Test-CompanionTypeUiGate -Path $TypeUiEvidencePath -PackageInfo $packageInfo)) | Out-Null
}

$blocking = @($gates | Where-Object { $_.status -ne "PASS" })
$status = if ($blocking.Count -eq 0) {
    "PASS"
} elseif ($ChecklistOnly) {
    "CHECKLIST_PENDING"
} else {
    "FAIL"
}

$summaryJson = Join-Path $outDirResolved "companion-manual-gate-evidence-summary.json"
$summaryMd = Join-Path $outDirResolved "companion-manual-gate-evidence-summary.md"
$report = [ordered]@{
    schema = "companion.manual_gate_evidence.v1"
    status = $status
    checklist_only = [bool]$ChecklistOnly
    generated_at = (Get-Date).ToString("o")
    repo_root = $repoRoot
    package_path = $resolvedPackage
    package = $packageInfo
    type_harness_included = [bool]$IncludeTypeHarness
    type_ui_gate_included = [bool]$IncludeTypeUiGate
    output_dir = $outDirResolved
    summary_markdown = $summaryMd
    gates = @($gates)
}

$report | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $summaryJson -Encoding UTF8
ConvertTo-ManualGateMarkdown -Report $report -GateResults $gates |
    Set-Content -LiteralPath $summaryMd -Encoding UTF8

Write-Output "$status`: Companion manual gate evidence check complete."
Write-Output "Report: $summaryJson"
Write-Output "Markdown: $summaryMd"
Write-Output "Package: $resolvedPackage"
Write-Output "Blocking gates: $($blocking.Count)"

if ($status -eq "FAIL") {
    throw "Companion manual gate evidence is incomplete or failing. See $summaryJson"
}
