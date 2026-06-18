param(
    [switch] $CheckOnly,
    [ValidateSet("Debug", "Release")]
    [string] $Configuration = "Debug",
    [string] $CubeIdePath,
    [string] $Workspace
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$projectRelative = "third_party\STM32CubeWB\Projects\P-NUCLEO-WB55.Nucleo\Applications\BLE\BLE_p2pServer\STM32CubeIDE"
$projectPath = Join-Path $repoRoot $projectRelative
$projectName = "BLE_p2pServer"

if (-not $Workspace) {
    $Workspace = Join-Path $repoRoot "build\stm32cubeide-workspace"
}

function Assert-Path {
    param(
        [Parameter(Mandatory = $true)][string] $Path,
        [Parameter(Mandatory = $true)][string] $Label
    )

    if (-not (Test-Path -LiteralPath $Path)) {
        throw "Missing $Label`: $Path. Run tools\bootstrap_stm32cubewb.ps1 first."
    }
}

function Find-CubeIdeCommand {
    param([string] $RequestedPath)

    $candidates = @()
    if ($RequestedPath) { $candidates += $RequestedPath }
    if ($env:STM32CUBEIDE_PATH) { $candidates += $env:STM32CUBEIDE_PATH }
    if ($env:STM32CUBEIDE_EXE) { $candidates += $env:STM32CUBEIDE_EXE }

    foreach ($commandName in @("stm32cubeidec.exe", "stm32cubeidec")) {
        $command = Get-Command $commandName -ErrorAction SilentlyContinue
        if ($command) { $candidates += $command.Source }
    }

    $candidates += @(
        "C:\ST\STM32CubeIDE_*\STM32CubeIDE\stm32cubeidec.exe",
        "C:\ST\STM32CubeIDE\STM32CubeIDE\stm32cubeidec.exe",
        "C:\Program Files\STMicroelectronics\STM32Cube\STM32CubeIDE\STM32CubeIDE\stm32cubeidec.exe",
        "C:\Program Files\STMicroelectronics\STM32CubeIDE\STM32CubeIDE\stm32cubeidec.exe"
    )

    foreach ($candidate in $candidates) {
        if ([string]::IsNullOrWhiteSpace($candidate)) { continue }
        $matches = @(Get-ChildItem -Path $candidate -File -ErrorAction SilentlyContinue | Sort-Object FullName -Descending)
        if ($matches.Count -gt 0) { return $matches[0].FullName }
        if (Test-Path -LiteralPath $candidate -PathType Leaf) { return (Resolve-Path -LiteralPath $candidate).Path }
    }

    return $null
}

Assert-Path -Path $projectPath -Label "BLE_p2pServer CubeIDE project"
Assert-Path -Path (Join-Path $projectPath ".project") -Label "CubeIDE .project"
Assert-Path -Path (Join-Path $projectPath ".cproject") -Label "CubeIDE .cproject"

$cubeIde = Find-CubeIdeCommand -RequestedPath $CubeIdePath

if ($CheckOnly) {
    if ($cubeIde) {
        Write-Output "CHECK: STM32CubeIDE command-line tool found: $cubeIde"
    } else {
        Write-Output "CHECK: STM32CubeIDE command-line tool not found. Install STM32CubeIDE or set -CubeIdePath/STM32CUBEIDE_PATH before running a real build."
    }
    Write-Output "CHECK: Official starter project exists: $projectRelative"
    Write-Output "CHECK: No hardware is required for this check path."
    exit 0
}

if (-not $cubeIde) {
    throw "STM32CubeIDE command-line tool not found. Install STM32CubeIDE, add stm32cubeidec.exe to PATH, or pass -CubeIdePath."
}

New-Item -ItemType Directory -Force -Path $Workspace | Out-Null

$buildTarget = "$projectName/$Configuration"
$args = @(
    "-nosplash",
    "-application", "org.eclipse.cdt.managedbuilder.core.headlessbuild",
    "-data", $Workspace,
    "-import", $projectPath,
    "-cleanBuild", $buildTarget
)

Write-Output "Building $buildTarget with $cubeIde"
& $cubeIde @args
if ($LASTEXITCODE -ne 0) {
    throw "STM32CubeIDE headless build failed with exit code $LASTEXITCODE for $buildTarget."
}

Write-Output "PASS: STM32CubeIDE headless build completed for $buildTarget."
