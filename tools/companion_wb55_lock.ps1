Set-StrictMode -Version Latest

$script:CompanionWb55Mutex = $null
$script:CompanionWb55Owned = $false
$script:CompanionWb55Context = $null
$script:CompanionWb55PreviousGrant = @{}

function Get-CompanionWb55LockDirectory {
    $repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
    $directory = Join-Path $repoRoot ".cache\validation\wb55-locks"
    New-Item -ItemType Directory -Force -Path $directory | Out-Null
    return $directory
}

function Read-CompanionWb55LockEvidence {
    param([Parameter(Mandatory = $true)][string] $Path)

    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "Companion-WB55 lock grant evidence is missing: $Path"
    }
    try {
        return Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json -AsHashtable
    } catch {
        throw "Companion-WB55 lock grant evidence is not valid JSON: $($_.Exception.Message)"
    }
}

function Write-CompanionWb55LockEvidence {
    param(
        [Parameter(Mandatory = $true)][System.Collections.IDictionary] $Evidence,
        [Parameter(Mandatory = $true)][string] $Path
    )

    $Evidence | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $Path -Encoding UTF8
}

function Test-CompanionWb55InheritedGrant {
    $runId = [string]$env:COMPANION_WB55_LOCK_RUN_ID
    $evidencePath = [string]$env:COMPANION_WB55_LOCK_EVIDENCE_PATH
    if ([string]::IsNullOrWhiteSpace($runId) -and [string]::IsNullOrWhiteSpace($evidencePath)) {
        return $null
    }
    if ([string]::IsNullOrWhiteSpace($runId) -or [string]::IsNullOrWhiteSpace($evidencePath)) {
        throw "Companion-WB55 inherited lock grant is incomplete."
    }

    $evidence = Read-CompanionWb55LockEvidence -Path $evidencePath
    if ($evidence.schema_id -ne "companion.wb55.hardware_lock.v1" -or
        $evidence.status -ne "HELD" -or
        $evidence.resource -ne "Companion-WB55" -or
        $evidence.run_id -ne $runId) {
        throw "Companion-WB55 inherited lock grant is not an active matching lock."
    }
    $ownerPid = [int]$evidence.owner_process_id
    try {
        $null = Get-Process -Id $ownerPid -ErrorAction Stop
        $current = Get-CimInstance Win32_Process -Filter "ProcessId=$PID" -ErrorAction Stop
    } catch {
        throw "Companion-WB55 inherited lock owner is no longer alive."
    }
    if ([int]$current.ParentProcessId -ne $ownerPid) {
        throw "Companion-WB55 inherited lock must come from the direct owning recovery process."
    }
    return [pscustomobject]@{
        mode = "inherited"
        run_id = $runId
        evidence_path = $evidencePath
        owner_process_id = $ownerPid
        purpose = [string]$evidence.purpose
    }
}

function Enter-CompanionWb55Lock {
    param([Parameter(Mandatory = $true)][string] $Purpose)

    if ($script:CompanionWb55Context) {
        return $script:CompanionWb55Context
    }

    $inherited = Test-CompanionWb55InheritedGrant
    if ($inherited) {
        $script:CompanionWb55Context = $inherited
        return $script:CompanionWb55Context
    }

    $mutex = [System.Threading.Mutex]::new($false, "Local\Companion-WB55-Hardware-Exclusive-v1")
    $acquired = $false
    try {
        try {
            $acquired = $mutex.WaitOne(0)
        } catch [System.Threading.AbandonedMutexException] {
            $acquired = $true
        }
        if (-not $acquired) {
            throw "Companion-WB55 hardware lock is already held; no flash, serial, or panel action was started."
        }

        $runId = [guid]::NewGuid().ToString("N")
        $evidencePath = Join-Path (Get-CompanionWb55LockDirectory) "companion-wb55-lock-$runId.json"
        $evidence = [ordered]@{
            schema_id = "companion.wb55.hardware_lock.v1"
            status = "HELD"
            resource = "Companion-WB55"
            run_id = $runId
            owner_process_id = $PID
            acquired_at = (Get-Date).ToUniversalTime().ToString("o")
            purpose = $Purpose
            lock_mechanism = "Local\\Companion-WB55-Hardware-Exclusive-v1"
        }
        Write-CompanionWb55LockEvidence -Evidence $evidence -Path $evidencePath

        foreach ($name in @("COMPANION_WB55_LOCK_RUN_ID", "COMPANION_WB55_LOCK_EVIDENCE_PATH")) {
            $script:CompanionWb55PreviousGrant[$name] = [Environment]::GetEnvironmentVariable($name, "Process")
        }
        [Environment]::SetEnvironmentVariable("COMPANION_WB55_LOCK_RUN_ID", $runId, "Process")
        [Environment]::SetEnvironmentVariable("COMPANION_WB55_LOCK_EVIDENCE_PATH", $evidencePath, "Process")

        $script:CompanionWb55Mutex = $mutex
        $script:CompanionWb55Owned = $true
        $script:CompanionWb55Context = [pscustomobject]@{
            mode = "owner"
            run_id = $runId
            evidence_path = $evidencePath
            owner_process_id = $PID
            purpose = $Purpose
        }
        return $script:CompanionWb55Context
    } catch {
        if ($acquired) {
            $mutex.ReleaseMutex()
        }
        $mutex.Dispose()
        throw
    }
}

function Exit-CompanionWb55Lock {
    if (-not $script:CompanionWb55Context) {
        return
    }

    try {
        if ($script:CompanionWb55Owned) {
            $evidence = Read-CompanionWb55LockEvidence -Path $script:CompanionWb55Context.evidence_path
            if ($evidence.run_id -ne $script:CompanionWb55Context.run_id -or $evidence.owner_process_id -ne $PID) {
                throw "Companion-WB55 lock evidence changed before release."
            }
            $evidence.status = "RELEASED"
            $evidence.released_at = (Get-Date).ToUniversalTime().ToString("o")
            Write-CompanionWb55LockEvidence -Evidence $evidence -Path $script:CompanionWb55Context.evidence_path
        }
    } finally {
        if ($script:CompanionWb55Owned -and $script:CompanionWb55Mutex) {
            $script:CompanionWb55Mutex.ReleaseMutex()
            $script:CompanionWb55Mutex.Dispose()
        }
        if ($script:CompanionWb55Owned) {
            foreach ($name in @("COMPANION_WB55_LOCK_RUN_ID", "COMPANION_WB55_LOCK_EVIDENCE_PATH")) {
                [Environment]::SetEnvironmentVariable($name, $script:CompanionWb55PreviousGrant[$name], "Process")
            }
        }
        $script:CompanionWb55Mutex = $null
        $script:CompanionWb55Owned = $false
        $script:CompanionWb55Context = $null
        $script:CompanionWb55PreviousGrant = @{}
    }
}

function Get-CompanionWb55LockEvidenceSummary {
    param([AllowNull()][object] $Context)

    if (-not $Context) {
        return $null
    }
    return [ordered]@{
        mechanism = "Local\\Companion-WB55-Hardware-Exclusive-v1"
        mode = [string]$Context.mode
        run_id = [string]$Context.run_id
        evidence_path = [string]$Context.evidence_path
        owner_process_id = [int]$Context.owner_process_id
        purpose = [string]$Context.purpose
    }
}
