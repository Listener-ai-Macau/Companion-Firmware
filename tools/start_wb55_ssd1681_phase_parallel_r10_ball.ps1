param(
    [switch]$CheckOnly,
    [switch]$Execute,
    [switch]$ClaimOnly,
    [string]$OutRoot,
    [string]$AuthorizationArtifact,
    [string]$ProgrammerRoot="C:\ST\STM32CubeIDE_2.1.1\STM32CubeIDE\plugins"
)
$ErrorActionPreference="Stop";Set-StrictMode -Version Latest;[Console]::OutputEncoding=[Text.Encoding]::UTF8
if(@($CheckOnly,$Execute,$ClaimOnly).Where({$_}).Count -ne 1){throw "Choose exactly one of -CheckOnly, -Execute, or -ClaimOnly."}
$root=(Resolve-Path (Join-Path $PSScriptRoot "..")).Path;$runRoot=[IO.Path]::GetFullPath($OutRoot);if(Test-Path $runRoot){throw "R10 persistent output root must be fresh."};New-Item -ItemType Directory -Force -Path $runRoot|Out-Null
$runner=Join-Path $PSScriptRoot "run_wb55_ssd1681_phase_parallel_r10_ball.ps1";$monitor=Join-Path $PSScriptRoot "monitor_wb55_ssd1681_phase_parallel_r10_ball.ps1";$supervisor=Join-Path $PSScriptRoot "supervise_wb55_ssd1681_phase_parallel_r10_ball_prompt.ps1";$parser=Join-Path $PSScriptRoot "verify_wb55_ssd1681_r10_ball_log.py";$hex=Join-Path $root "cubeide\Companion_Nucleo_WB55RG_Bringup\build_ssd1681_r10_ball\Companion_Nucleo_WB55RG_Ssd1681R10Ball.hex";$machineRoot=Join-Path $root "docs\validation"
function Hash([string]$Path){if(-not(Test-Path $Path)){return $null};return (Get-FileHash $Path -Algorithm SHA256).Hash.ToUpperInvariant()}
function Write-Json([string]$Path,[object]$Value){[IO.File]::WriteAllText($Path,(($Value|ConvertTo-Json -Depth 16)+[Environment]::NewLine),[Text.UTF8Encoding]::new($false))}
function Full([string]$Path){if(-not $Path){throw "A path is required."};return [IO.Path]::GetFullPath($Path)}
function Same-Path([string]$A,[string]$B){return [StringComparer]::OrdinalIgnoreCase.Equals((Full $A),(Full $B))}
function Validate-MachineManifest([string]$Path,[hashtable]$Expected){
    $candidate=Full $Path;$docs=Full $machineRoot;$relative=[IO.Path]::GetRelativePath($docs,$candidate)
    if(-not $candidate.EndsWith('.json',[StringComparison]::OrdinalIgnoreCase) -or
       $relative -eq '..' -or $relative.StartsWith('..'+[IO.Path]::DirectorySeparatorChar) -or
       $relative.Contains([IO.Path]::DirectorySeparatorChar) -or
       $relative.Contains([IO.Path]::AltDirectorySeparatorChar) -or
       -not(Test-Path -LiteralPath $candidate -PathType Leaf)){throw "machine_ready_path must be a repository docs/validation leaf JSON."}
    $manifest=Get-Content -LiteralPath $candidate -Raw|ConvertFrom-Json
    if([string]$manifest.schema_id -notmatch '^companion\.wb55\.ssd1681\..*machine_ready\.v[0-9]+$' -or
       [string]$manifest.status -notmatch '^MACHINE_READY_' -or $manifest.hardware_contact -ne 0 -or
       $manifest.execute_authorized -eq $true -or $manifest.authorization_created -eq $true){throw "machine_ready manifest status or safety boundary is invalid."}
    $artifacts=$manifest.artifacts
    if([string]$artifacts.hex -ne [string]$Expected.candidate_hex_sha256 -or
       [string]$artifacts.runner -ne [string]$Expected.runner_sha256 -or
       [string]$artifacts.monitor -ne [string]$Expected.monitor_sha256 -or
       [string]$artifacts.supervisor -ne [string]$Expected.supervisor_sha256 -or
       [string]$artifacts.launcher -ne [string]$Expected.launcher_sha256 -or
       [string]$artifacts.parser_sha256 -ne [string]$Expected.parser_sha256){throw "machine_ready manifest artifact hashes do not match current tools."}
    return $candidate
}
function Atomic-Claim([string]$Path,[object]$Value){$stream=$null;try{$stream=[IO.File]::Open($Path,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None);$bytes=[Text.UTF8Encoding]::new($false).GetBytes((($Value|ConvertTo-Json -Depth 8)+[Environment]::NewLine));$stream.Write($bytes,0,$bytes.Length);$stream.Flush($true)}catch{throw "R10 authorization claim already exists or is unavailable."}finally{if($stream){$stream.Dispose()}}}
function Claim-R10([string]$Source,[string]$BoundRoot,[hashtable]$Expected){
    $sourceFull=Full $Source;$rootFull=Full $BoundRoot
    if($sourceFull.EndsWith('.consumed.json',[StringComparison]::OrdinalIgnoreCase) -or $sourceFull.EndsWith('.spent',[StringComparison]::OrdinalIgnoreCase)){throw "Consumed or spent authorization cannot be claimed."}
    if(-not(Test-Path $sourceFull -PathType Leaf)){throw "Fresh authorization source is missing."}
    $a=Get-Content $sourceFull -Raw|ConvertFrom-Json
    if($a.status -ne 'AUTHORIZED_R10_BALL_ONCE' -or $a.consumed -ne $false -or $a.requirement_id -notin @('COMP-REQ-322','COMP-REQ-323')){throw "Invalid or consumed R10 authorization."}
    if(-not $a.output_root -or -not(Same-Path ([string]$a.output_root) $rootFull)){throw "Authorization output_root mismatch."}
    $machinePath=Validate-MachineManifest ([string]$a.machine_ready_path) $Expected
    $boundExpected=[ordered]@{};foreach($k in $Expected.Keys){$boundExpected[$k]=$Expected[$k]};$boundExpected.machine_ready_path=$machinePath;$boundExpected.machine_ready_sha256=Hash $machinePath
    foreach($k in $boundExpected.Keys){if([string]$a.$k -ne [string]$boundExpected[$k]){throw "R10 authorization hash mismatch: $k"}}
    $sourceSha=Hash $sourceFull;$claimPath="$sourceFull.claim.json";$spentPath="$sourceFull.spent";$receiptPath="$sourceFull.consumed.json"
    Atomic-Claim $claimPath ([ordered]@{schema_id='companion.wb55.ssd1681.r10_ball.authorization_claim.v1';status='CLAIMED';source_authorization=$sourceFull;output_root=$rootFull})
    try{[IO.File]::Move($sourceFull,$spentPath)}catch{throw "Authorization claim was recorded but source spend failed; refusing to continue."}
    $receipt=[ordered]@{schema_id='companion.wb55.ssd1681.r10_ball.authorization_receipt.v1';status='CONSUMED_AUTHORIZED_R10_BALL_ONCE';consumed=$true;claim_id=(Hash $claimPath);claim_marker=$claimPath;source_authorization_path=$sourceFull;source_spent_path=$spentPath;source_authorization_sha256=$sourceSha;output_root=$rootFull;claimed_utc=([DateTime]::UtcNow.ToString('o'));requirement_id=[string]$a.requirement_id}
    foreach($k in $boundExpected.Keys){$receipt[$k]=$boundExpected[$k]};Write-Json $receiptPath $receipt;return $receiptPath
}
$expected=[ordered]@{candidate_hex_sha256=Hash $hex;runner_sha256=Hash $runner;monitor_sha256=Hash $monitor;supervisor_sha256=Hash $supervisor;launcher_sha256=Hash $PSCommandPath;parser_sha256=Hash $parser}
if($Execute -or $ClaimOnly){
    if(-not $AuthorizationArtifact){throw "Execute requires a fresh root-issued authorization."}
    $authorizationReceipt=Claim-R10 $AuthorizationArtifact $runRoot $expected
    if($ClaimOnly){Write-Output "CLAIMED_NO_HARDWARE: receipt=$authorizationReceipt";exit 0}
}
$stdout=Join-Path $runRoot "runner.stdout.log";$stderr=Join-Path $runRoot "runner.stderr.log";$launch=Join-Path $runRoot "persistent-launch.json"
$args=@("-NoProfile","-File",$runner,$(if($CheckOnly){"-CheckOnly"}else{"-Execute"}),"-PhaseParallelR10Ball","-OutRoot",$runRoot,"-ProgrammerRoot",$ProgrammerRoot)
if($Execute){$args+=@("-AuthorizationArtifact",[IO.Path]::GetFullPath($authorizationReceipt))}
$p=Start-Process -FilePath "pwsh" -ArgumentList $args -RedirectStandardOutput $stdout -RedirectStandardError $stderr -WindowStyle Hidden -PassThru
$report=[ordered]@{schema_id="companion.wb55.ssd1681.r10_ball.persistent_launcher.v3";mode=if($CheckOnly){"check_only"}else{"execute"};status=if($CheckOnly){"CHECK_RUNNING"}else{"STARTED_DETACHED"};process_id=$p.Id;runner=$runner;arguments=$args;output_root=$runRoot;stdout=$stdout;stderr=$stderr;durable_stdout_redirected=$true;durable_stderr_redirected=$true;hardware_contact=if($CheckOnly){0}else{$null};write_counter_sum=if($CheckOnly){0}else{$null};popup_count=if($CheckOnly){0}else{$null};retry_count=if($CheckOnly){0}else{$null};authorization_artifact=if($Execute){[IO.Path]::GetFullPath($authorizationReceipt)}else{$null};authorization_hashes=if($Execute){$expected}else{$null}}
if($Execute){Write-Json $launch $report;Write-Output "STARTED_DETACHED: pid=$($p.Id) artifact=$launch";exit 0}
if(-not $p.WaitForExit(180000)){Stop-Process -Id $p.Id -Force;throw "R10 CheckOnly child timed out."};$p.WaitForExit();$report.exit_code=$p.ExitCode;$report.child_exited=$true
$stagePath=Join-Path $runRoot "stage-run.json";if($p.ExitCode -ne 0 -or -not(Test-Path $stagePath)){ $report.status="NO_GO_CHECK_CHILD";Write-Json $launch $report;throw "R10 CheckOnly child failed." }
$stage=Get-Content $stagePath -Raw|ConvertFrom-Json;$writes=0;foreach($pname in @("preclean_write_calls","postclean_write_calls","candidate_write_calls","restore_write_calls","panel_writes","panel_refresh_commands","panel_hard_resets")){if($null -ne $stage.counters.$pname){$writes+=[int64]$stage.counters.$pname}}
$report.stage_status=$stage.status;$report.hardware_contact=$stage.hardware_contact;$report.write_counter_sum=$writes;$report.popup_count=if($stage.operator_prompt.invoked){1}else{0};$report.retry_count=$stage.counters.automatic_retries;$report.status=if($stage.status -eq "READY_NO_HARDWARE_CONTACT" -and $stage.hardware_contact -eq 0 -and $writes -eq 0 -and $report.popup_count -eq 0 -and $report.retry_count -eq 0 -and $stage.pre_execute_prompt.invoked -eq $false){"READY_NO_HARDWARE_CONTACT"}else{"NO_GO_CHECK_STAGE"};Write-Json $launch $report
if($report.status -ne "READY_NO_HARDWARE_CONTACT"){throw "R10 CheckOnly failed closed: $($report.status)"};Write-Output "READY_NO_HARDWARE_CONTACT: artifact=$launch"
