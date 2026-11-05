param(
    [switch]$CheckOnly,
    [switch]$Execute,
    [switch]$ClaimOnly,
    [switch]$SelfTest,
    [string]$OutRoot,
    [string]$AuthorizationArtifact,
    [string]$ProgrammerRoot = "C:\ST\STM32CubeIDE_2.1.1\STM32CubeIDE\plugins"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
[Console]::OutputEncoding = [Text.Encoding]::UTF8

if (@($CheckOnly,$Execute,$ClaimOnly,$SelfTest).Where({$_}).Count -ne 1) {
    throw "Choose exactly one of -CheckOnly, -Execute, -ClaimOnly, or -SelfTest."
}
if ([string]::IsNullOrWhiteSpace($OutRoot)) { throw "A fresh -OutRoot is required." }
if (($Execute -or $ClaimOnly) -and [string]::IsNullOrWhiteSpace($AuthorizationArtifact)) {
    throw "R7 Execute/ClaimOnly requires a fresh root-issued authorization; hardware_contact=0."
}

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$runRoot = [IO.Path]::GetFullPath($OutRoot)
if (Test-Path -LiteralPath $runRoot) { throw "R7 persistent output root must be fresh." }
$runner = Join-Path $PSScriptRoot "run_wb55_ssd1681_r7_locked_v9.ps1"
$monitor = Join-Path $PSScriptRoot "monitor_wb55_ssd1681_r7_locked_v9.ps1"
$supervisor = Join-Path $PSScriptRoot "supervise_wb55_ssd1681_r7_locked_v9.ps1"
$parser = Join-Path $PSScriptRoot "verify_wb55_ssd1681_r7_locked_v9_parser.py"
$hex = Join-Path $repoRoot "cubeide\Companion_Nucleo_WB55RG_Bringup\build_ssd1681_r7_locked_v9_choreography\Companion_Nucleo_WB55RG_Ssd1681R7LockedV9Choreography.hex"
$machineRoot = Join-Path $repoRoot "docs\validation"

function Get-Hash([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { return $null }
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToUpperInvariant()
}
function Get-FullPath([string]$Path) {
    if ([string]::IsNullOrWhiteSpace($Path)) { throw "A path is required." }
    return [IO.Path]::GetFullPath($Path)
}
function Test-SamePath([string]$A,[string]$B) {
    return [StringComparer]::OrdinalIgnoreCase.Equals((Get-FullPath $A),(Get-FullPath $B))
}
function Write-JsonAtomic([string]$Path,[object]$Value) {
    $temp = "$Path.tmp"
    [IO.File]::WriteAllText($temp,(($Value | ConvertTo-Json -Depth 16) + [Environment]::NewLine),[Text.UTF8Encoding]::new($false))
    Move-Item -LiteralPath $temp -Destination $Path -Force
}
function Write-CreateNewJson([string]$Path,[object]$Value) {
    $stream = $null
    try {
        $stream = [IO.File]::Open($Path,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
        $bytes = [Text.UTF8Encoding]::new($false).GetBytes((($Value | ConvertTo-Json -Depth 12) + [Environment]::NewLine))
        $stream.Write($bytes,0,$bytes.Length)
        $stream.Flush($true)
    } catch {
        throw "R7 authorization claim or receipt already exists or is unavailable."
    } finally {
        if ($stream) { $stream.Dispose() }
    }
}
function Assert-AuthorizationIdentity([object]$Authorization,[string]$BoundRoot) {
    if ($null -eq $Authorization) { throw "R7 authorization is absent." }
    if ([string]$Authorization.schema_id -ne 'companion.wb55.ssd1681.r7_locked_v9_choreography.authorization.v1' -or
        [string]$Authorization.status -ne 'AUTHORIZED_R7_LOCKED_V9_CHOREOGRAPHY_ONCE' -or
        $Authorization.consumed -ne $false -or
        [string]$Authorization.candidate -ne 'r7_locked_v9_choreography' -or
        [string]$Authorization.authority_scope -ne 'one_shot_physical_review' -or
        [string]$Authorization.requirement_id -ne 'COMP-REQ-413') {
        throw "Invalid, legacy, or consumed R7 authorization."
    }
    if (-not $Authorization.output_root -or -not (Test-SamePath ([string]$Authorization.output_root) $BoundRoot)) {
        throw "R7 authorization output_root mismatch."
    }
}
function Assert-AuthorizationBindings([object]$Authorization,[System.Collections.IDictionary]$Expected) {
    foreach ($key in $Expected.Keys) {
        if ([string]$Authorization.$key -ne [string]$Expected[$key]) { throw "R7 authorization hash mismatch: $key" }
    }
}
function Assert-MachineManifestSafety([object]$Manifest) {
    if ($null -eq $Manifest -or $null -eq $Manifest.execute_authorized -or $Manifest.execute_authorized -ne $false -or $Manifest.authorization_created -eq $true) {
        throw "R7 MACHINE_READY strict safety fields are absent or unsafe."
    }
}
function Validate-MachineManifest([string]$Path,[System.Collections.IDictionary]$Expected) {
    $candidate = Get-FullPath $Path
    $docs = Get-FullPath $machineRoot
    $relative = [IO.Path]::GetRelativePath($docs,$candidate)
    if (-not $candidate.EndsWith('.json',[StringComparison]::OrdinalIgnoreCase) -or
        $relative -eq '..' -or $relative.StartsWith('..' + [IO.Path]::DirectorySeparatorChar) -or
        $relative.Contains([IO.Path]::DirectorySeparatorChar) -or
        $relative.Contains([IO.Path]::AltDirectorySeparatorChar) -or
        -not (Test-Path -LiteralPath $candidate -PathType Leaf)) {
        throw "machine_ready_path must be a repository docs/validation leaf JSON."
    }
    $manifest = Get-Content -LiteralPath $candidate -Raw | ConvertFrom-Json
    if ([string]$manifest.schema_id -notmatch '^companion\.wb55\.ssd1681\..*machine_ready\.v[0-9]+$' -or
        [string]$manifest.status -notmatch '^MACHINE_READY_' -or $manifest.hardware_contact -ne 0) {
        throw "R7 MACHINE_READY manifest safety boundary is invalid."
    }
    Assert-MachineManifestSafety $manifest
    $artifacts = $manifest.artifacts
    if ([string]$artifacts.hex -ne [string]$Expected.candidate_hex_sha256 -or
        [string]$artifacts.runner -ne [string]$Expected.runner_sha256 -or
        [string]$artifacts.monitor -ne [string]$Expected.monitor_sha256 -or
        [string]$artifacts.supervisor -ne [string]$Expected.supervisor_sha256 -or
        [string]$artifacts.launcher -ne [string]$Expected.launcher_sha256 -or
        [string]$artifacts.parser_sha256 -ne [string]$Expected.parser_sha256) {
        throw "R7 MACHINE_READY artifact hashes do not match current tools."
    }
    return $candidate
}
function Claim-R7Authorization([string]$Source,[string]$BoundRoot,[System.Collections.IDictionary]$Expected) {
    $sourceFull = Get-FullPath $Source
    $rootFull = Get-FullPath $BoundRoot
    if ($sourceFull.EndsWith('.consumed.json',[StringComparison]::OrdinalIgnoreCase) -or
        $sourceFull.EndsWith('.spent',[StringComparison]::OrdinalIgnoreCase) -or
        -not (Test-Path -LiteralPath $sourceFull -PathType Leaf)) {
        throw "Fresh R7 authorization source is missing or already consumed."
    }
    $authorization = Get-Content -LiteralPath $sourceFull -Raw | ConvertFrom-Json
    Assert-AuthorizationIdentity $authorization $rootFull
    $machinePath = Validate-MachineManifest ([string]$authorization.machine_ready_path) $Expected
    $boundExpected = [ordered]@{}
    foreach ($key in $Expected.Keys) { $boundExpected[$key] = $Expected[$key] }
    $boundExpected.machine_ready_path = $machinePath
    $boundExpected.machine_ready_sha256 = Get-Hash $machinePath
    Assert-AuthorizationBindings $authorization $boundExpected

    $sourceSha = Get-Hash $sourceFull
    $claimPath = "$sourceFull.claim.json"
    $spentPath = "$sourceFull.spent"
    $receiptPath = "$sourceFull.consumed.json"
    Write-CreateNewJson $claimPath ([ordered]@{schema_id='companion.wb55.ssd1681.r7_locked_v9_choreography.authorization_claim.v1';status='CLAIMED';source_authorization=$sourceFull;output_root=$rootFull;candidate=[string]$authorization.candidate;authority_scope=[string]$authorization.authority_scope;requirement_id=[string]$authorization.requirement_id})
    try { [IO.File]::Move($sourceFull,$spentPath) } catch { throw "R7 authorization claim was recorded but atomic source spend failed; refusing to continue." }
    $receipt = [ordered]@{schema_id='companion.wb55.ssd1681.r7_locked_v9_choreography.authorization_receipt.v1';status='CONSUMED_AUTHORIZED_R7_LOCKED_V9_CHOREOGRAPHY_ONCE';consumed=$true;claim_id=(Get-Hash $claimPath);claim_marker=$claimPath;source_authorization_path=$sourceFull;source_spent_path=$spentPath;source_authorization_sha256=$sourceSha;output_root=$rootFull;claimed_utc=([DateTime]::UtcNow.ToString('o'));candidate=[string]$authorization.candidate;authority_scope=[string]$authorization.authority_scope;requirement_id=[string]$authorization.requirement_id}
    foreach ($key in $boundExpected.Keys) { $receipt[$key] = $boundExpected[$key] }
    Write-CreateNewJson $receiptPath $receipt
    return $receiptPath
}

$expected = [ordered]@{candidate_hex_sha256=Get-Hash $hex;runner_sha256=Get-Hash $runner;monitor_sha256=Get-Hash $monitor;supervisor_sha256=Get-Hash $supervisor;launcher_sha256=Get-Hash $PSCommandPath;parser_sha256=Get-Hash $parser}

if ($SelfTest) {
    New-Item -ItemType Directory -Path $runRoot | Out-Null
    $selfPath = Join-Path $runRoot "launcher-selftest.json"
    $bindingFixture = [ordered]@{candidate_hex_sha256='A';runner_sha256='B'}
    $valid = [pscustomobject]@{schema_id='companion.wb55.ssd1681.r7_locked_v9_choreography.authorization.v1';status='AUTHORIZED_R7_LOCKED_V9_CHOREOGRAPHY_ONCE';consumed=$false;candidate='r7_locked_v9_choreography';authority_scope='one_shot_physical_review';requirement_id='COMP-REQ-413';output_root=$runRoot;candidate_hex_sha256='A';runner_sha256='B'}
    $checks = [ordered]@{}
    $checks.unauthorized_execute_fails_before_contact = try { Assert-AuthorizationIdentity $null $runRoot; $false } catch { $true }
    $checks.valid_r7_comp_req_413_identity_and_hashes_pass = try { Assert-AuthorizationIdentity $valid $runRoot; Assert-AuthorizationBindings $valid $bindingFixture; $true } catch { $false }
    $wrongCandidate = $valid.PSObject.Copy(); $wrongCandidate.candidate = 'r10_native_guarded_corridor_cached_mode2_cadence'
    $checks.wrong_candidate_rejected = try { Assert-AuthorizationIdentity $wrongCandidate $runRoot; $false } catch { $true }
    $wrongRoot = $valid.PSObject.Copy(); $wrongRoot.output_root = "$runRoot-wrong"
    $checks.wrong_root_rejected = try { Assert-AuthorizationIdentity $wrongRoot $runRoot; $false } catch { $true }
    $wrongHash = $valid.PSObject.Copy(); $wrongHash.runner_sha256 = 'WRONG'
    $checks.wrong_hash_rejected = try { Assert-AuthorizationBindings $wrongHash $bindingFixture; $false } catch { $true }
    foreach ($requirementId in @('COMP-REQ-370','COMP-REQ-371','COMP-REQ-372','COMP-REQ-373','COMP-REQ-374','COMP-REQ-375','COMP-REQ-376','COMP-REQ-377','COMP-REQ-378','COMP-REQ-379','COMP-REQ-380','COMP-REQ-381','COMP-REQ-382','COMP-REQ-383','COMP-REQ-384','COMP-REQ-385','COMP-REQ-386','COMP-REQ-388','COMP-REQ-389','COMP-REQ-390','COMP-REQ-391','COMP-REQ-392','COMP-REQ-393','COMP-REQ-394','COMP-REQ-395','COMP-REQ-396','COMP-REQ-397','COMP-REQ-398','COMP-REQ-399','COMP-REQ-400','COMP-REQ-401','COMP-REQ-402','COMP-REQ-403','COMP-REQ-412','COMP-REQ-323','COMP-REQ-999')) {
        $wrongRequirement = $valid.PSObject.Copy(); $wrongRequirement.requirement_id = $requirementId
        $checks["requirement_$($requirementId.Replace('-','_'))_rejected"] = try { Assert-AuthorizationIdentity $wrongRequirement $runRoot; $false } catch { $true }
    }
    $checks.no_authorization_claim_spent_or_receipt_created = @(Get-ChildItem -LiteralPath $runRoot -Force | Where-Object { $_.Name -match 'authorization|claim|spent|receipt|consumed' }).Count -eq 0
    $missingExecuteAuthorized = [pscustomobject]@{schema_id='companion.wb55.ssd1681.r7_locked_v9_choreography.machine_ready.v2';status='MACHINE_READY_R7_LOCKED_V9_OFFLINE_ONLY';hardware_contact=0;authorization_created=$false}
    $checks.missing_execute_authorized_rejected = try { Assert-MachineManifestSafety $missingExecuteAuthorized; $false } catch { $true }
    $passed = @($checks.Values).Where({-not $_}).Count -eq 0
    $result = [ordered]@{schema_id='companion.wb55.ssd1681.r7_locked_v9_choreography.launcher_selftest.v1';status=if($passed){'PASS_SELFTEST'}else{'FAIL_SELFTEST'};hardware_contact=0;write_counter_sum=0;programmer_calls=0;serial_open_count=0;reset_count=0;refresh_count=0;popup_count=0;retry_count=0;authorization_created=$false;checks=$checks}
    Write-JsonAtomic $selfPath $result
    $result | ConvertTo-Json -Depth 10
    if ($passed) { exit 0 } else { exit 1 }
}

New-Item -ItemType Directory -Path $runRoot | Out-Null
$authorizationReceipt = $null
if ($Execute -or $ClaimOnly) {
    $authorizationReceipt = Claim-R7Authorization $AuthorizationArtifact $runRoot $expected
    if ($ClaimOnly) { Write-Output "CLAIMED_NO_HARDWARE: receipt=$authorizationReceipt"; exit 0 }
}

$stdout = Join-Path $runRoot "runner.stdout.log"
$stderr = Join-Path $runRoot "runner.stderr.log"
$launch = Join-Path $runRoot "persistent-launch.json"
$arguments = @("-NoProfile","-File",$runner,$(if($CheckOnly){"-CheckOnly"}else{"-Execute"}),"-R7Sampler","-OutRoot",$runRoot,"-ProgrammerRoot",$ProgrammerRoot)
if ($Execute) { $arguments += @("-AuthorizationArtifact",[IO.Path]::GetFullPath($authorizationReceipt)) }
$process = Start-Process -FilePath "pwsh" -ArgumentList $arguments -RedirectStandardOutput $stdout -RedirectStandardError $stderr -WindowStyle Hidden -PassThru
$report = [ordered]@{schema_id='companion.wb55.ssd1681.r7_locked_v9_choreography.persistent_launcher.v4';mode=if($CheckOnly){'check_only'}else{'execute'};status=if($CheckOnly){'CHECK_RUNNING'}else{'STARTED_DETACHED'};process_id=$process.Id;runner=$runner;arguments=$arguments;output_root=$runRoot;stdout=$stdout;stderr=$stderr;hardware_contact=if($CheckOnly){0}else{$null};write_counter_sum=if($CheckOnly){0}else{$null};programmer_calls=if($CheckOnly){0}else{$null};serial_open_count=if($CheckOnly){0}else{$null};reset_count=if($CheckOnly){0}else{$null};refresh_count=if($CheckOnly){0}else{$null};popup_count=if($CheckOnly){0}else{$null};retry_count=if($CheckOnly){0}else{$null};authorization_artifact=if($Execute){[IO.Path]::GetFullPath($authorizationReceipt)}else{$null};authorization_hashes=if($Execute){$expected}else{$null}}
if ($Execute) { Write-JsonAtomic $launch $report; Write-Output "STARTED_DETACHED: pid=$($process.Id) artifact=$launch"; exit 0 }

if (-not $process.WaitForExit(180000)) { Stop-Process -Id $process.Id -Force; throw "R7 CheckOnly child timed out." }
$process.WaitForExit(); $process.Refresh(); $report.exit_code = [int]$process.ExitCode; $report.child_exited = $true
$stagePath = Join-Path $runRoot "stage-run.json"
if (-not (Test-Path -LiteralPath $stagePath -PathType Leaf)) { $report.status='NO_GO_CHECK_CHILD'; Write-JsonAtomic $launch $report; throw "R7 CheckOnly child failed." }
$stage = Get-Content -LiteralPath $stagePath -Raw | ConvertFrom-Json
$writeCounter = 0
foreach ($name in @('preclean_write_calls','postclean_write_calls','candidate_write_calls','restore_write_calls','panel_writes','panel_refresh_commands','panel_hard_resets')) { if ($null -ne $stage.counters.$name) { $writeCounter += [int64]$stage.counters.$name } }
$programmerCalls = [int64]$stage.counters.preclean_programmer_processes + [int64]$stage.counters.postclean_programmer_processes + [int64]$stage.counters.candidate_programmer_processes + [int64]$stage.counters.restore_programmer_processes
$report.stage_status = $stage.status
$report.hardware_contact = [int]$stage.hardware_contact
$report.write_counter_sum = $writeCounter
$report.programmer_calls = $programmerCalls
$report.serial_open_count = [int64]$stage.counters.serial_capture_processes
$report.reset_count = [int64]$stage.counters.panel_hard_resets
$report.refresh_count = [int64]$stage.counters.panel_refresh_commands
$report.popup_count = if($stage.operator_prompt.invoked){1}else{0}
$report.retry_count = [int64]$stage.counters.automatic_retries
$allZero = $report.hardware_contact -eq 0 -and $report.write_counter_sum -eq 0 -and $report.programmer_calls -eq 0 -and $report.serial_open_count -eq 0 -and $report.reset_count -eq 0 -and $report.refresh_count -eq 0 -and $report.popup_count -eq 0 -and $report.retry_count -eq 0
$report.status = if($stage.status -eq 'READY_NO_HARDWARE_CONTACT' -and $allZero -and $stage.pre_execute_prompt.invoked -eq $false){'READY_NO_HARDWARE_CONTACT'}else{'NO_GO_CHECK_STAGE'}
Write-JsonAtomic $launch $report
if ($report.status -ne 'READY_NO_HARDWARE_CONTACT') { throw "R7 CheckOnly failed closed: $($report.status)" }
Write-Output "READY_NO_HARDWARE_CONTACT: artifact=$launch"
