param()

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$scriptPath = Join-Path $PSScriptRoot "verify_ota_contract_static.py"
$python = Get-Command python -ErrorAction SilentlyContinue
if ($python) {
    & $python.Source $scriptPath
    exit $LASTEXITCODE
}

$py = Get-Command py -ErrorAction SilentlyContinue
if ($py) {
    & $py.Source -3 $scriptPath
    exit $LASTEXITCODE
}

throw "Python 3 is required to run tools\verify_ota_contract_static.py."
