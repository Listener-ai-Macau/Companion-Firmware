[CmdletBinding()]
param(
    [string]$RoutePath = 'docs/validation/companion-v9-v22-touch-emotion-route-preview-20260720.json',
    [string]$WritePath = 'docs/validation/companion-v9-v22-touch-emotion-route-browser-render-20260720.json'
)

$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$routeAbsolute = Join-Path $repoRoot $RoutePath
$writeAbsolute = Join-Path $repoRoot $WritePath

function Get-Sha256([string]$Path) {
    (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToUpperInvariant()
}

function Get-RelativePath([string]$Path) {
    [System.IO.Path]::GetRelativePath($repoRoot, $Path).Replace('\', '/')
}

function Capture-RouteScene([string]$Edge, [string]$Uri, [string]$Scene, [int]$VirtualTimeMs, [bool]$AutoPlay, [string]$Screenshot) {
    $profile = Join-Path ([System.IO.Path]::GetTempPath()) ("companion-v9-v22-browser-" + [Guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Force -Path $profile | Out-Null
    $sceneUri = "${Uri}?scene=$Scene"
    if ($AutoPlay) {
        $sceneUri += '&autoplay=1'
    }
    $arguments = @(
        '--headless=new', '--no-first-run', '--no-default-browser-check', '--disable-gpu', '--hide-scrollbars', '--allow-file-access-from-files',
        "--user-data-dir=$profile", '--window-size=520,420', "--virtual-time-budget=$VirtualTimeMs", "--screenshot=$Screenshot", $sceneUri
    )
    $startInfo = [System.Diagnostics.ProcessStartInfo]::new()
    $startInfo.FileName = $Edge
    $startInfo.UseShellExecute = $false
    foreach ($argument in $arguments) {
        [void]$startInfo.ArgumentList.Add($argument)
    }
    $process = [System.Diagnostics.Process]::new()
    $process.StartInfo = $startInfo
    [void]$process.Start()
    $deadline = [DateTime]::UtcNow.AddSeconds(20)
    while (-not (Test-Path -LiteralPath $Screenshot) -and -not $process.HasExited -and [DateTime]::UtcNow -lt $deadline) {
        Start-Sleep -Milliseconds 200
    }
    if (-not (Test-Path -LiteralPath $Screenshot)) {
        if (-not $process.HasExited) {
            $process.Kill($true)
            [void]$process.WaitForExit(5000)
        }
        throw "Browser timed out while capturing the $Scene screenshot."
    }
    $terminatedAfterScreenshot = $false
    $exitCode = $null
    if ($process.HasExited) {
        $exitCode = $process.ExitCode
    } else {
        $process.Kill($true)
        [void]$process.WaitForExit(5000)
        $terminatedAfterScreenshot = $true
    }
    return [ordered]@{
        exit_code = $exitCode
        terminated_after_screenshot = $terminatedAfterScreenshot
    }
}

if (-not (Test-Path -LiteralPath $routeAbsolute)) {
    throw "Route report is missing: $routeAbsolute"
}
$route = Get-Content -Raw -LiteralPath $routeAbsolute | ConvertFrom-Json -AsHashtable
if ($route.status -ne 'PASS_V9_V22_TOUCH_EMOTION_ROUTE_RUNTIME_INACTIVE') {
    throw 'Route report is not a passing runtime-inactive candidate.'
}
$playerRelative = [string]$route.browser_player.path
$playerAbsolute = Join-Path $repoRoot $playerRelative
if (-not (Test-Path -LiteralPath $playerAbsolute)) {
    throw "Browser player is missing: $playerAbsolute"
}
$edge = @(
    'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',
    'C:\Program Files\Microsoft\Edge\Application\msedge.exe'
) | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
if (-not $edge) {
    throw 'Microsoft Edge is required for the browser render inspection.'
}
$artifactDirectory = Split-Path -Parent $playerAbsolute
$dailyScreenshot = Join-Path $artifactDirectory 'browser-daily-200x200-20260720.png'
$warmScreenshot = Join-Path $artifactDirectory 'browser-familiar-touch-warm-200x200-11000ms-20260720.png'
$playerUri = ([Uri]$playerAbsolute).AbsoluteUri
$dailyCapture = Capture-RouteScene $edge $playerUri 'daily_micro' 2000 $false $dailyScreenshot
$warmCapture = Capture-RouteScene $edge $playerUri 'familiar_touch' 11000 $true $warmScreenshot
$playerText = Get-Content -Raw -LiteralPath $playerAbsolute
$checks = [ordered]@{
    route_is_runtime_inactive_candidate = $route.runtime_resource_activated -eq $false
    native_200x200_component_stage = $playerText.Contains('#stage{position:relative;width:200px;height:200px')
    explicit_event_player = $playerText.Contains("const scenes=new Map(DATA.performances.map") -and
        $playerText.Contains("if(cursor+1>=active.frame_indices.length){stop();return;}")
    daily_screenshot_written = Test-Path -LiteralPath $dailyScreenshot
    familiar_touch_warm_screenshot_written = Test-Path -LiteralPath $warmScreenshot
}
$failures = @($checks.GetEnumerator() | Where-Object { -not $_.Value } | ForEach-Object Key)
$report = [ordered]@{
    schema = 'companion.v9_v22_touch_emotion_browser_render_inspection.v1'
    status = if ($failures.Count -eq 0) { 'PASS_BROWSER_RENDER_INSPECTION_NATIVE_200X200' } else { 'FAIL_BROWSER_RENDER_INSPECTION' }
    claim_scope = 'actual_browser_render_screenshots_for_runtime_inactive_candidate_not_runtime_binding_flash_or_physical_acceptance'
    route = [ordered]@{ path = $RoutePath.Replace('\', '/'); sha256 = Get-Sha256 $routeAbsolute }
    player = [ordered]@{ path = $playerRelative; sha256 = Get-Sha256 $playerAbsolute }
    screenshots = @(
        [ordered]@{ scene = 'daily_micro'; virtual_time_ms = 2000; autoplay = $false; expected_art_pose = 'v9_daily'; edge_exit_code = $dailyCapture.exit_code; edge_terminated_after_screenshot = $dailyCapture.terminated_after_screenshot; path = Get-RelativePath $dailyScreenshot; sha256 = Get-Sha256 $dailyScreenshot },
        [ordered]@{ scene = 'familiar_touch'; virtual_time_ms = 11000; autoplay = $true; expected_art_pose = 'v22_warm'; edge_exit_code = $warmCapture.exit_code; edge_terminated_after_screenshot = $warmCapture.terminated_after_screenshot; path = Get-RelativePath $warmScreenshot; sha256 = Get-Sha256 $warmScreenshot }
    )
    checks = $checks
    failures = $failures
}
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $writeAbsolute) | Out-Null
$report | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $writeAbsolute -Encoding UTF8
if ($failures.Count -ne 0) {
    Write-Error "FAIL: browser render inspection: $($failures -join ', ')"
    exit 1
}
Write-Host "PASS: browser render inspection -> $(Get-RelativePath $writeAbsolute)"
