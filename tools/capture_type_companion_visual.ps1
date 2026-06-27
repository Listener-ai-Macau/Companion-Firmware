param(
    [string] $TypeRepoRoot = (Join-Path $PSScriptRoot "..\..\..\Listener\Listener-Type"),
    [string] $OutputDir,
    [int] $Port = 5187,
    [string] $BrowserPath
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$typeRoot = (Resolve-Path $TypeRepoRoot).Path

if ([string]::IsNullOrWhiteSpace($OutputDir)) {
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $OutputDir = Join-Path $repoRoot ".cache\validation\type-companion-visual-$stamp"
}
$resolvedOutputDir = (New-Item -ItemType Directory -Force -Path $OutputDir).FullName

function Resolve-BrowserPath {
    param([string] $RequestedPath)

    if (-not [string]::IsNullOrWhiteSpace($RequestedPath)) {
        return (Resolve-Path $RequestedPath).Path
    }

    $candidates = @(
        (Join-Path ${env:ProgramFiles(x86)} "Microsoft\Edge\Application\msedge.exe"),
        (Join-Path $env:ProgramFiles "Microsoft\Edge\Application\msedge.exe"),
        (Join-Path $env:LOCALAPPDATA "Microsoft\Edge\Application\msedge.exe"),
        (Join-Path $env:ProgramFiles "Google\Chrome\Application\chrome.exe"),
        (Join-Path ${env:ProgramFiles(x86)} "Google\Chrome\Application\chrome.exe")
    )

    foreach ($candidate in $candidates) {
        if ($candidate -and (Test-Path -LiteralPath $candidate)) {
            return (Resolve-Path $candidate).Path
        }
    }

    throw "No headless browser found. Install Microsoft Edge or pass -BrowserPath."
}

function Stop-ProcessTree {
    param([Parameter(Mandatory = $true)][int] $RootProcessId)

    $children = @(Get-CimInstance Win32_Process | Where-Object { $_.ParentProcessId -eq $RootProcessId })
    foreach ($child in $children) {
        Stop-ProcessTree -RootProcessId ([int] $child.ProcessId)
    }
    Stop-Process -Id $RootProcessId -Force -ErrorAction SilentlyContinue
}

function Wait-HttpReady {
    param(
        [Parameter(Mandatory = $true)][string] $Url,
        [Parameter(Mandatory = $true)][int] $TimeoutSeconds
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        try {
            $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 2
            if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 500) {
                return
            }
        } catch {
            Start-Sleep -Milliseconds 250
        }
    }

    throw "Timed out waiting for Type dev server at $Url."
}

function Invoke-BrowserCommand {
    param(
        [Parameter(Mandatory = $true)][string] $Name,
        [Parameter(Mandatory = $true)][string[]] $Arguments,
        [int] $TimeoutSeconds = 30,
        [string] $StdoutPath,
        [string] $StderrPath,
        [string] $ArtifactPath,
        [switch] $AllowTimeoutWithArtifact
    )

    $startArgs = @{
        FilePath = $browser
        ArgumentList = $Arguments
        WindowStyle = "Hidden"
        PassThru = $true
    }
    if (-not [string]::IsNullOrWhiteSpace($StdoutPath)) {
        $startArgs.RedirectStandardOutput = $StdoutPath
    }
    if (-not [string]::IsNullOrWhiteSpace($StderrPath)) {
        $startArgs.RedirectStandardError = $StderrPath
    }

    $process = Start-Process @startArgs
    $completed = $process.WaitForExit($TimeoutSeconds * 1000)
    if (-not $completed) {
        Stop-ProcessTree -RootProcessId $process.Id
        if ($AllowTimeoutWithArtifact -and
            -not [string]::IsNullOrWhiteSpace($ArtifactPath) -and
            (Test-Path -LiteralPath $ArtifactPath)) {
            return [ordered]@{
                exit_code = $null
                timed_out = $true
            }
        }
        throw "$Name timed out after $TimeoutSeconds second(s)."
    }

    $process.Refresh()
    if ($process.ExitCode -ne 0) {
        throw "$Name failed with exit code $($process.ExitCode)."
    }

    return [ordered]@{
        exit_code = $process.ExitCode
        timed_out = $false
    }
}

$browser = Resolve-BrowserPath -RequestedPath $BrowserPath
$url = "http://127.0.0.1:$Port/?visual=settings-companion&theme=dark"
$stdoutLog = Join-Path $resolvedOutputDir "vite.stdout.log"
$stderrLog = Join-Path $resolvedOutputDir "vite.stderr.log"
$screenshotPath = Join-Path $resolvedOutputDir "type-companion-visual.png"
$domPath = Join-Path $resolvedOutputDir "type-companion-visual.dom.html"
$domStderrPath = Join-Path $resolvedOutputDir "type-companion-visual.dom.stderr.log"
$screenshotProfile = Join-Path $resolvedOutputDir "edge-profile-screenshot"
$domProfile = Join-Path $resolvedOutputDir "edge-profile-dom"
New-Item -ItemType Directory -Force -Path $screenshotProfile | Out-Null
New-Item -ItemType Directory -Force -Path $domProfile | Out-Null

$viteProcess = $null
try {
    $viteProcess = Start-Process `
        -FilePath "npm.cmd" `
        -ArgumentList @("run", "dev", "--", "--host", "127.0.0.1", "--port", "$Port", "--strictPort") `
        -WorkingDirectory $typeRoot `
        -RedirectStandardOutput $stdoutLog `
        -RedirectStandardError $stderrLog `
        -WindowStyle Hidden `
        -PassThru

    Wait-HttpReady -Url $url -TimeoutSeconds 25

    $screenshotResult = Invoke-BrowserCommand `
        -Name "Headless browser screenshot" `
        -Arguments @(
        "--headless=new",
        "--disable-gpu",
        "--disable-background-networking",
        "--disable-extensions",
        "--no-first-run",
        "--window-size=1280,1200",
        "--virtual-time-budget=3500",
        "--user-data-dir=$screenshotProfile",
        "--screenshot=$screenshotPath",
        $url
    ) `
        -TimeoutSeconds 30 `
        -ArtifactPath $screenshotPath `
        -AllowTimeoutWithArtifact
    if (-not (Test-Path -LiteralPath $screenshotPath)) {
        throw "Headless browser did not create screenshot: $screenshotPath"
    }
    $screenshotLength = (Get-Item -LiteralPath $screenshotPath).Length
    if ($screenshotLength -lt 50000) {
        throw "Screenshot is unexpectedly small ($screenshotLength bytes): $screenshotPath"
    }

    $domResult = Invoke-BrowserCommand `
        -Name "Headless browser DOM dump" `
        -Arguments @(
        "--headless=new",
        "--disable-gpu",
        "--disable-background-networking",
        "--disable-extensions",
        "--no-first-run",
        "--window-size=1280,1200",
        "--virtual-time-budget=3500",
        "--user-data-dir=$domProfile",
        "--dump-dom",
        $url
    ) `
        -TimeoutSeconds 30 `
        -StdoutPath $domPath `
        -StderrPath $domStderrPath `
        -ArtifactPath $domPath `
        -AllowTimeoutWithArtifact
    if (-not (Test-Path -LiteralPath $domPath)) {
        throw "Headless browser did not create DOM dump: $domPath"
    }
    $domLength = (Get-Item -LiteralPath $domPath).Length
    if ($domLength -lt 10000) {
        throw "DOM dump is unexpectedly small ($domLength bytes): $domPath"
    }

    $dom = Get-Content -LiteralPath $domPath -Raw -Encoding UTF8
    foreach ($token in @(
        "Companion Pendant bring-up",
        "A1 smoke",
        "A2 smoke",
        "蓝牙 OTA",
        "总体验收",
        "ST-LINK / SWD"
    )) {
        if (-not $dom.Contains($token)) {
            throw "Companion visual DOM missing expected token: $token"
        }
    }

    $summary = [ordered]@{
        schema = "companion.type_visual.v1"
        status = "PASS"
        generated_at = (Get-Date).ToString("o")
        type_repo_root = $typeRoot
        url = $url
        browser = $browser
        screenshot = $screenshotPath
        dom = $domPath
        dom_stderr = $domStderrPath
        vite_stdout = $stdoutLog
        vite_stderr = $stderrLog
        screenshot_bytes = $screenshotLength
        dom_bytes = $domLength
        screenshot_exit_code = $screenshotResult["exit_code"]
        screenshot_timed_out = $screenshotResult["timed_out"]
        dom_exit_code = $domResult["exit_code"]
        dom_timed_out = $domResult["timed_out"]
    }
    $summaryPath = Join-Path $resolvedOutputDir "type-companion-visual-summary.json"
    $summary | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $summaryPath -Encoding utf8

    Write-Output "PASS: Type Companion visual route rendered."
    Write-Output "URL: $url"
    Write-Output "Screenshot: $screenshotPath"
    Write-Output "DOM: $domPath"
    Write-Output "Summary: $summaryPath"
    Write-Output "type_companion_visual_result_json=$($summary | ConvertTo-Json -Compress -Depth 6)"
} finally {
    if ($viteProcess -and -not $viteProcess.HasExited) {
        Stop-ProcessTree -RootProcessId $viteProcess.Id
    }
}
