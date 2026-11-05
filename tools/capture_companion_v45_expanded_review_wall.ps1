#requires -Version 7.0
[CmdletBinding()]
param(
    [string]$PreviewPath = "docs\art\iterations\companion-pet-expression-v9-two-track-rig-v7\candidate\wb55-browser-parity-attempt-01\v45-expanded-review-wall.html",
    [string]$OutputDir = "docs\art\iterations\companion-pet-expression-v9-two-track-rig-v7\candidate\wb55-browser-parity-attempt-01\expanded-wall-capture-r1",
    [ValidateRange(1, 60)]
    [int]$TimeoutSeconds = 30
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $repoRoot
$preview = (Resolve-Path $PreviewPath).Path
$output = [System.IO.Path]::GetFullPath((Join-Path $repoRoot $OutputDir))
$edge = "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
if (-not (Test-Path -LiteralPath $edge)) { throw "Missing Edge headless executable: $edge" }
New-Item -ItemType Directory -Force -Path $output | Out-Null
$shot = Join-Path $output "v45-expanded-review-wall.png"
$profile = Join-Path $repoRoot ".cache\v45-expanded-wall-browser-r1"
$url = "file:///" + ($preview -replace "\\", "/")
Remove-Item -LiteralPath $shot -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath $profile -Recurse -Force -ErrorAction SilentlyContinue
$process = $null
try {
    $process = Start-Process -FilePath $edge -ArgumentList @(
        "--headless=new", "--disable-gpu", "--hide-scrollbars", "--allow-file-access-from-files",
        "--run-all-compositor-stages-before-draw", "--virtual-time-budget=12000", "--window-size=1200,6000",
        "--user-data-dir=$profile", "--screenshot=$shot", $url
    ) -PassThru -WindowStyle Hidden
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while (-not (Test-Path -LiteralPath $shot) -and (Get-Date) -lt $deadline) {
        if ($process.WaitForExit(200)) { break }
    }
    if (-not (Test-Path -LiteralPath $shot)) {
        $exitCode = if ($process.HasExited) { $process.ExitCode } else { "timeout" }
        throw "Edge did not create the expanded-wall screenshot before $TimeoutSeconds s (exit=$exitCode)"
    }
    if ($process.HasExited -and $process.ExitCode -ne 0) { throw "Expanded-wall capture failed with $($process.ExitCode)" }
}
finally {
    if ($null -ne $process -and -not $process.HasExited) {
        Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
        $process.WaitForExit(2000) | Out-Null
    }
    Remove-Item -LiteralPath $profile -Recurse -Force -ErrorAction SilentlyContinue
}
$item = Get-Item -LiteralPath $shot
if ($item.Length -lt 10000) { throw "Expanded-wall screenshot is unexpectedly small: $($item.Length) bytes" }
Write-Output "PASS: captured V45 expanded review wall screenshot $shot ($($item.Length) bytes)."
