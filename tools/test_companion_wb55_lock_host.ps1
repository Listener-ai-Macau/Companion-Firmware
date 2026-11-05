$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$helper = Join-Path $PSScriptRoot "companion_wb55_lock.ps1"
. $helper
$token = [guid]::NewGuid().ToString("N")
$job = $null
$postRelease = $null
try {
    $job = Start-Job -ScriptBlock {
        param($HelperPath, $Purpose)
        . $HelperPath
        $context = Enter-CompanionWb55Lock -Purpose $Purpose
        try {
            Start-Sleep -Seconds 3
            return [ordered]@{ mode = $context.mode; run_id = $context.run_id }
        } finally {
            Exit-CompanionWb55Lock
        }
    } -ArgumentList $helper, "host-lock-selftest-$token"

    $deadline = [DateTime]::UtcNow.AddSeconds(10)
    $held = $false
    while ([DateTime]::UtcNow -lt $deadline -and -not $held) {
        $lockDirectory = Join-Path (Split-Path $PSScriptRoot -Parent) ".cache\validation\wb55-locks"
        foreach ($path in @(Get-ChildItem -LiteralPath $lockDirectory -Filter "companion-wb55-lock-*.json" -ErrorAction SilentlyContinue)) {
            try {
                $evidence = Get-Content -LiteralPath $path.FullName -Raw | ConvertFrom-Json
                if ($evidence.status -eq "HELD" -and $evidence.purpose -eq "host-lock-selftest-$token") {
                    $held = $true
                    break
                }
            } catch {
            }
        }
        if (-not $held) { Start-Sleep -Milliseconds 100 }
    }
    if (-not $held) {
        throw "lock holder did not publish a HELD evidence artifact"
    }

    $contentionRefused = $false
    try {
        $unexpected = Enter-CompanionWb55Lock -Purpose "host-lock-contention-$token"
        Exit-CompanionWb55Lock
        throw "second lock acquisition unexpectedly succeeded: $($unexpected.run_id)"
    } catch {
        if ($_.Exception.Message -like "Companion-WB55 hardware lock is already held*") {
            $contentionRefused = $true
        } else {
            throw
        }
    }
    if (-not $contentionRefused) {
        throw "second lock acquisition was not refused"
    }

    Wait-Job -Job $job -Timeout 10 | Out-Null
    if ($job.State -ne "Completed") {
        throw "lock holder did not release within the expected window"
    }
    $holderResult = Receive-Job -Job $job
    if ($holderResult.mode -ne "owner") {
        throw "lock holder did not own the mutex"
    }

    $postRelease = Enter-CompanionWb55Lock -Purpose "host-lock-postrelease-$token"
    if ($postRelease.mode -ne "owner") {
        throw "lock did not become available after release"
    }
    $childResultPath = Join-Path ([System.IO.Path]::GetTempPath()) "companion-wb55-lock-child-$token.json"
    $escapedHelper = $helper.Replace("'", "''")
    $escapedResult = $childResultPath.Replace("'", "''")
    $childCommand = "& { . '$escapedHelper'; `$context = Enter-CompanionWb55Lock -Purpose 'host-lock-child-$token'; `$context | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath '$escapedResult' -Encoding UTF8; Exit-CompanionWb55Lock }"
    $child = Start-Process -FilePath (Get-Command pwsh -ErrorAction Stop).Source -ArgumentList @("-NoProfile", "-Command", $childCommand) -Wait -PassThru -WindowStyle Hidden
    if ($child.ExitCode -ne 0 -or -not (Test-Path -LiteralPath $childResultPath -PathType Leaf)) {
        throw "child did not verify the inherited lock grant"
    }
    $childResult = Get-Content -LiteralPath $childResultPath -Raw | ConvertFrom-Json
    if ($childResult.mode -ne "inherited" -or $childResult.run_id -ne $postRelease.run_id) {
        throw "child lock grant did not match the owning recovery process"
    }
    Remove-Item -LiteralPath $childResultPath -Force
    Write-Output "PASS: Companion-WB55 host mutex rejects contention and releases cleanly."
} finally {
    if ($postRelease) {
        Exit-CompanionWb55Lock
    }
    if ($job) {
        if ($job.State -eq "Running") {
            Stop-Job -Job $job -ErrorAction SilentlyContinue
        }
        Remove-Job -Job $job -Force -ErrorAction SilentlyContinue
    }
}
