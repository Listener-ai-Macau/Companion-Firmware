$ErrorActionPreference = 'Stop'
Set-Location (Split-Path -Parent $PSScriptRoot)
python .\tools\test_v9_expression_rig_pipeline.py
