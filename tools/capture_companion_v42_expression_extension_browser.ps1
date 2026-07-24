#requires -Version 7.0
[CmdletBinding()]
param(
    [string]$PreviewPath,
    [string]$OutputDir,
    [ValidateRange(1, 60)]
    [int]$TimeoutSeconds = 20
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $repoRoot
if (-not $PreviewPath) { throw "PreviewPath is required." }
if (-not $OutputDir) { throw "OutputDir is required." }
$preview = (Resolve-Path $PreviewPath).Path
$output = [System.IO.Path]::GetFullPath((Join-Path $repoRoot $OutputDir))
$edge = "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
if (-not (Test-Path -LiteralPath $edge)) { throw "Missing Edge headless executable: $edge" }
New-Item -ItemType Directory -Force -Path $output | Out-Null
$shot = Join-Path $output "v42-chinese-overview-headless-r6.png"
$profile = Join-Path $repoRoot ".cache\v42-expression-extension-browser-r6"
$url = "file:///" + ($preview -replace "\\", "/")
Remove-Item -LiteralPath $shot -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath $profile -Recurse -Force -ErrorAction SilentlyContinue
$process = $null
try {
    $process = Start-Process -FilePath $edge -ArgumentList @(
        "--headless=new", "--disable-gpu", "--hide-scrollbars", "--allow-file-access-from-files",
        "--run-all-compositor-stages-before-draw", "--virtual-time-budget=10000", "--window-size=1400,1900",
        "--user-data-dir=$profile", "--screenshot=$shot", $url
    ) -PassThru -WindowStyle Hidden
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while (-not (Test-Path -LiteralPath $shot) -and (Get-Date) -lt $deadline) {
        if ($process.WaitForExit(200)) { break }
    }
    if (-not (Test-Path -LiteralPath $shot)) {
        $exitCode = if ($process.HasExited) { $process.ExitCode } else { "timeout" }
        throw "Edge did not create the V42 screenshot before $TimeoutSeconds s (exit=$exitCode)"
    }
    if ($process.HasExited -and $process.ExitCode -ne 0) { throw "Edge capture failed with $($process.ExitCode)" }
}
finally {
    if ($null -ne $process -and -not $process.HasExited) {
        Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
        $process.WaitForExit(2000) | Out-Null
    }
    Remove-Item -LiteralPath $profile -Recurse -Force -ErrorAction SilentlyContinue
}
$item = Get-Item -LiteralPath $shot
if ($item.Length -lt 4000) { throw "V42 screenshot is unexpectedly small: $($item.Length) bytes" }
Write-Output "PASS: captured V42 browser wall screenshot $shot ($($item.Length) bytes)."
