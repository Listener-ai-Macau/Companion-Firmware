param()

$ErrorActionPreference = 'Stop'

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent $scriptDir
$pythonScript = Join-Path $scriptDir 'verify_recording_fsm_static.py'

if (-not (Test-Path -LiteralPath $pythonScript)) {
    throw "Missing recording FSM static checker: $pythonScript"
}

Push-Location $repoRoot
try {
    & python $pythonScript
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
} finally {
    Pop-Location
}
