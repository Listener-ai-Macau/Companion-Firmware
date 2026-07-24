[CmdletBinding()]
param(
    [string]$RoutePath = 'docs/validation/companion-v24-glance-readable-special-expression-component-performance-preview-20260720.json',
    [string]$WritePath = 'docs/validation/companion-v24-glance-readable-special-expression-component-browser-render-20260720.json'
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

function Capture-Scene([string]$Uri, [string]$Scene, [int]$VirtualTimeMs, [string]$Screenshot) {
    $targetUri = "${Uri}?scene=$Scene"
    if ($VirtualTimeMs -gt 0) {
        $targetUri += '&autoplay=1'
    }
    & npx --no-install playwright screenshot --browser chromium --viewport-size '600,440' `
        --wait-for-timeout $VirtualTimeMs --timeout 30000 $targetUri $Screenshot | Out-Host
    $exitCode = $LASTEXITCODE
    if ($exitCode -ne 0 -or -not (Test-Path -LiteralPath $Screenshot)) {
        throw "Playwright did not write the $Scene screenshot."
    }
    return $exitCode
}

if (-not (Test-Path -LiteralPath $routeAbsolute)) {
    throw "Route report is missing: $routeAbsolute"
}
$route = Get-Content -Raw -LiteralPath $routeAbsolute | ConvertFrom-Json -AsHashtable
if ($route.status -ne 'PASS_V24_SPECIAL_COMPONENT_PERFORMANCE_RUNTIME_INACTIVE') {
    throw 'Route report is not a passing runtime-inactive V24 component candidate.'
}
$playerRelative = [string]$route.browser_player.path
$playerAbsolute = Join-Path $repoRoot $playerRelative
if (-not (Test-Path -LiteralPath $playerAbsolute)) {
    throw "Browser player is missing: $playerAbsolute"
}
if (-not (Get-Command npx -ErrorAction SilentlyContinue)) {
    throw 'npx with the installed Playwright CLI is required for the browser render inspection.'
}
$artifactDirectory = Split-Path -Parent $playerAbsolute
$playerUri = ([Uri]$playerAbsolute).AbsoluteUri
$captures = @(
    @{ scene = 'daily_micro'; virtual_time_ms = 100; label = 'daily' },
    @{ scene = 'menu_active'; virtual_time_ms = 2700; label = 'menu-hold' },
    @{ scene = 'recording_active'; virtual_time_ms = 2450; label = 'recording-hold' },
    @{ scene = 'charging_active'; virtual_time_ms = 2500; label = 'charging-hold' }
)
$screenshots = @()
foreach ($capture in $captures) {
    $screenshot = Join-Path $artifactDirectory ("browser-$($capture.label)-native-200x200-20260720.png")
    $exitCode = Capture-Scene $playerUri $capture.scene $capture.virtual_time_ms $screenshot
    $screenshots += [ordered]@{
        scene = $capture.scene
        virtual_time_ms = $capture.virtual_time_ms
        edge_exit_code = $exitCode
        path = Get-RelativePath $screenshot
        sha256 = Get-Sha256 $screenshot
    }
}
$playerText = Get-Content -Raw -LiteralPath $playerAbsolute
$checks = [ordered]@{
    route_is_runtime_inactive_candidate = $route.runtime_resource_activated -eq $false -and $route.active_candidate_binding -eq 'forbidden'
    native_200x200_component_stage = $playerText.Contains('#stage{position:relative;width:200px;height:200px')
    explicit_event_player = $playerText.Contains('const scenes=new Map(DATA.performances.map') -and $playerText.Contains('if(cursor+1>=active.frame_indices.length){stop();return;}')
    every_screenshot_written = @($screenshots | Where-Object { -not (Test-Path -LiteralPath (Join-Path $repoRoot $_.path)) }).Count -eq 0
}
$failures = @($checks.GetEnumerator() | Where-Object { -not $_.Value } | ForEach-Object Key)
$report = [ordered]@{
    schema = 'companion.v24_glance_readable_special_expression_component_browser_render_inspection.v1'
    status = if ($failures.Count -eq 0) { 'PASS_V24_BROWSER_RENDER_INSPECTION_NATIVE_200X200' } else { 'FAIL_V24_BROWSER_RENDER_INSPECTION' }
    claim_scope = 'actual browser screenshots for a runtime-inactive candidate component compositor; not a behavior binding, flash, panel output, or physical acceptance'
    browser_engine = 'playwright-chromium'
    route = [ordered]@{ path = $RoutePath.Replace('\', '/'); sha256 = Get-Sha256 $routeAbsolute }
    player = [ordered]@{ path = $playerRelative; sha256 = Get-Sha256 $playerAbsolute }
    screenshots = $screenshots
    checks = $checks
    failures = $failures
}
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $writeAbsolute) | Out-Null
$report | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $writeAbsolute -Encoding UTF8
if ($failures.Count -ne 0) {
    Write-Error "FAIL: V24 browser render inspection: $($failures -join ', ')"
    exit 1
}
Write-Host "PASS: V24 browser render inspection -> $(Get-RelativePath $writeAbsolute)"
