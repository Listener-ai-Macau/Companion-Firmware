param(
    [switch] $CheckOnly,
    [switch] $Execute,
    [switch] $WorkflowLockHeld,
    [switch] $FlashReference,
    [switch] $FlashNucleoBringup,
    [switch] $FlashAudioFixture,
    [switch] $FlashPackage,
    [string] $ImagePath,
    [string] $PackagePath,
    [string] $ProgrammerPath,
    [string] $Port = "SWD"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$referenceHexRelative = "third_party\STM32CubeWB\Projects\P-NUCLEO-WB55.Nucleo\Applications\BLE\BLE_p2pServer\Binary\BLE_p2pServer_reference.hex"
$bleStackRelative = "third_party\STM32CubeWB\Projects\STM32WB_Copro_Wireless_Binaries\STM32WB5x\stm32wb5x_BLE_Stack_full_fw.bin"
$nucleoBringupHexRelative = "cubeide\Companion_Nucleo_WB55RG_Bringup\build\Companion_Nucleo_WB55RG_Bringup.hex"
$audioFixtureHexRelative = "cubeide\Companion_BLE_Audio_Fixture\build\Companion_BLE_Audio_Fixture.hex"
$referenceHex = Join-Path $repoRoot $referenceHexRelative
$bleStackBinary = Join-Path $repoRoot $bleStackRelative
$nucleoBringupHex = Join-Path $repoRoot $nucleoBringupHexRelative
$audioFixtureHex = Join-Path $repoRoot $audioFixtureHexRelative

function Assert-Path {
    param(
        [Parameter(Mandatory = $true)][string] $Path,
        [Parameter(Mandatory = $true)][string] $Label
    )

    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "Missing $Label`: $Path. Run tools\bootstrap_stm32cubewb.ps1 first."
    }
}

function Find-CubeProgrammerCli {
    param([string] $RequestedPath)

    $candidates = @()
    if ($RequestedPath) { $candidates += $RequestedPath }
    if ($env:STM32CUBEPROGRAMMER_CLI) { $candidates += $env:STM32CUBEPROGRAMMER_CLI }
    if ($env:STM32CUBEPROGRAMMER_PATH) { $candidates += (Join-Path $env:STM32CUBEPROGRAMMER_PATH "STM32_Programmer_CLI.exe") }

    foreach ($commandName in @("STM32_Programmer_CLI.exe", "STM32_Programmer_CLI")) {
        $command = Get-Command $commandName -ErrorAction SilentlyContinue
        if ($command) { $candidates += $command.Source }
    }

    $candidates += @(
        "C:\ST\STM32CubeIDE_*\STM32CubeIDE\plugins\com.st.stm32cube.ide.mcu.externaltools.cubeprogrammer.win32_*\tools\bin\STM32_Programmer_CLI.exe",
        "C:\Program Files\STMicroelectronics\STM32CubeIDE_*\STM32CubeIDE\plugins\com.st.stm32cube.ide.mcu.externaltools.cubeprogrammer.win32_*\tools\bin\STM32_Programmer_CLI.exe",
        "C:\Program Files\STMicroelectronics\STM32Cube\STM32CubeIDE\STM32CubeIDE\plugins\com.st.stm32cube.ide.mcu.externaltools.cubeprogrammer.win32_*\tools\bin\STM32_Programmer_CLI.exe",
        "C:\Program Files\STMicroelectronics\STM32Cube\STM32CubeProgrammer\bin\STM32_Programmer_CLI.exe",
        "C:\ST\STM32CubeProgrammer\bin\STM32_Programmer_CLI.exe"
    )

    foreach ($candidate in $candidates) {
        if ([string]::IsNullOrWhiteSpace($candidate)) { continue }
        $matches = @(Get-ChildItem -Path $candidate -File -ErrorAction SilentlyContinue | Sort-Object FullName -Descending)
        if ($matches.Count -gt 0) { return $matches[0].FullName }
        if (Test-Path -LiteralPath $candidate -PathType Leaf) { return (Resolve-Path -LiteralPath $candidate).Path }
    }

    return $null
}

$programmer = Find-CubeProgrammerCli -RequestedPath $ProgrammerPath
$referenceLockCommand = "pwsh -NoProfile -File <ai-collaboration-workflow>\scripts\aiw.ps1 with-lock -Resource Companion-WB55 -Purpose `"flash Companion WB55 official BLE starter`" -Run pwsh -NoProfile -File .\tools\flash.ps1 -Execute -WorkflowLockHeld -FlashReference"
$nucleoLockCommand = "pwsh -NoProfile -File <ai-collaboration-workflow>\scripts\aiw.ps1 with-lock -Resource Companion-WB55 -Purpose `"flash Companion NUCLEO bring-up`" -Run pwsh -NoProfile -File .\tools\flash.ps1 -Execute -WorkflowLockHeld -FlashNucleoBringup"
$audioFixtureLockCommand = "pwsh -NoProfile -File <ai-collaboration-workflow>\scripts\aiw.ps1 with-lock -Resource Companion-WB55 -Purpose `"flash Companion BLE audio fixture`" -Run pwsh -NoProfile -File .\tools\flash.ps1 -Execute -WorkflowLockHeld -FlashAudioFixture"
$packageLockCommand = "pwsh -NoProfile -File <ai-collaboration-workflow>\scripts\aiw.ps1 with-lock -Resource Companion-WB55 -Purpose `"flash Companion wired factory package`" -Run pwsh -NoProfile -File .\tools\flash.ps1 -Execute -WorkflowLockHeld -FlashPackage -PackagePath <package-or-factory-manifest>"

function Show-OperatorPrompt {
    param(
        [Parameter(Mandatory = $true)][string] $Title,
        [Parameter(Mandatory = $true)][string] $Message
    )

    try {
        [System.Media.SystemSounds]::Exclamation.Play()
        [Console]::Beep(880, 220)
    } catch {
        Write-Warning "Could not play operator prompt sound: $($_.Exception.Message)"
    }

    try {
        Add-Type -AssemblyName System.Windows.Forms
        $result = [System.Windows.Forms.MessageBox]::Show(
            $Message,
            $Title,
            [System.Windows.Forms.MessageBoxButtons]::OKCancel,
            [System.Windows.Forms.MessageBoxIcon]::Warning
        )
        if ($result -ne [System.Windows.Forms.DialogResult]::OK) {
            throw "Operator cancelled flashing."
        }
    } catch {
        if ($_.Exception.Message -eq "Operator cancelled flashing.") { throw }
        Write-Warning "Could not show desktop prompt: $($_.Exception.Message)"
        Write-Output $Title
        Write-Output $Message
        $answer = Read-Host "输入 OK 继续刷机，其他内容取消"
        if ($answer -ne "OK") {
            throw "Operator cancelled flashing."
        }
    }
}

function Resolve-FactoryManifest {
    param([Parameter(Mandatory = $true)][string] $Path)

    $resolved = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($Path)
    if (Test-Path -LiteralPath $resolved -PathType Leaf) {
        if ([System.IO.Path]::GetExtension($resolved).Equals(".zip", [System.StringComparison]::OrdinalIgnoreCase)) {
            $extractRoot = Join-Path $repoRoot ".cache\wired_flash_packages"
            $extractDir = Join-Path $extractRoot ("{0}-{1}" -f [System.IO.Path]::GetFileNameWithoutExtension($resolved), (Get-Date -Format "yyyyMMdd-HHmmss"))
            New-Item -ItemType Directory -Force -Path $extractDir | Out-Null
            Expand-Archive -LiteralPath $resolved -DestinationPath $extractDir -Force
            return Resolve-FactoryManifest -Path $extractDir
        }
        return (Resolve-Path -LiteralPath $resolved).Path
    }

    if (-not (Test-Path -LiteralPath $resolved -PathType Container)) {
        throw "Package path not found: $Path"
    }

    $directManifest = Join-Path $resolved "manifest.json"
    if (Test-Path -LiteralPath $directManifest -PathType Leaf) {
        return (Resolve-Path -LiteralPath $directManifest).Path
    }

    $factoryManifests = @(Get-ChildItem -LiteralPath (Join-Path $resolved "factory") -Filter "manifest.json" -File -Recurse -ErrorAction SilentlyContinue)
    if ($factoryManifests.Count -ne 1) {
        throw "Expected exactly one factory manifest under package path, found $($factoryManifests.Count): $Path"
    }
    return $factoryManifests[0].FullName
}

function Get-WiredFactoryArtifacts {
    param([Parameter(Mandatory = $true)][string] $Path)

    $manifestPath = Resolve-FactoryManifest -Path $Path
    $manifestDir = Split-Path -Parent $manifestPath
    $manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
    if ([string]$manifest.package_type -ne "companion-wired-factory") {
        throw "Factory manifest package_type must be companion-wired-factory: $manifestPath"
    }

    $artifacts = @($manifest.artifacts)
    $ordered = @()
    foreach ($role in @("ota_loader", "app")) {
        $artifact = @($artifacts | Where-Object { [string]$_.role -eq $role }) | Select-Object -First 1
        if (-not $artifact) {
            throw "Factory manifest missing artifact role '$role': $manifestPath"
        }
        $fileName = [string]$artifact.file
        if ([System.IO.Path]::IsPathRooted($fileName) -or $fileName -like "*..*") {
            throw "Factory artifact file must be package-local: $fileName"
        }
        $artifactPath = Join-Path $manifestDir $fileName
        Assert-Path -Path $artifactPath -Label "factory artifact $role"
        $expectedSha = [string]$artifact.sha256
        if (-not [string]::IsNullOrWhiteSpace($expectedSha)) {
            $actualSha = (Get-FileHash -LiteralPath $artifactPath -Algorithm SHA256).Hash.ToLowerInvariant()
            if ($actualSha -ne $expectedSha.ToLowerInvariant()) {
                throw "Factory artifact hash mismatch for $role`: $fileName"
            }
        }
        $ordered += [pscustomobject]@{
            Role = $role
            Path = (Resolve-Path -LiteralPath $artifactPath).Path
            ManifestPath = $manifestPath
        }
    }
    return $ordered
}

function Invoke-ProgrammerWrite {
    param(
        [Parameter(Mandatory = $true)][string] $Image,
        [Parameter(Mandatory = $true)][string] $Label,
        [Parameter(Mandatory = $true)][string[]] $ConnectArgs,
        [switch] $ResetAfter
    )

    $programmerArgs = @("-c") + $ConnectArgs + @("-w", $Image, "-v")
    if ($ResetAfter) {
        $programmerArgs += "-rst"
    }

    Write-Output "Flashing $Label with $programmer"
    Write-Output "Image: $Image"
    & $programmer @programmerArgs
    if ($LASTEXITCODE -ne 0) {
        throw "STM32CubeProgrammer flash failed for $Label with exit code $LASTEXITCODE."
    }
}

if ($CheckOnly) {
    if ($programmer) {
        Write-Output "CHECK: STM32CubeProgrammer CLI found: $programmer"
    } else {
        Write-Output "CHECK: STM32CubeProgrammer CLI not found. Install STM32CubeProgrammer or set -ProgrammerPath/STM32CUBEPROGRAMMER_CLI before real flashing."
    }
    Write-Output "CHECK: Reference hex exists: $referenceHexRelative -> $((Test-Path -LiteralPath $referenceHex -PathType Leaf))"
    Write-Output "CHECK: BLE full stack binary exists: $bleStackRelative -> $((Test-Path -LiteralPath $bleStackBinary -PathType Leaf))"
    Write-Output "CHECK: CPU2 BLE stack provisioning is separate; run tools\provision_companion_wireless_stack.ps1 -CheckOnly and, on hardware, -Execute -ReadFusInfo/-InstallBleStack before expecting BLE advertising."
    Write-Output "CHECK: NUCLEO bring-up hex exists: $nucleoBringupHexRelative -> $((Test-Path -LiteralPath $nucleoBringupHex -PathType Leaf))"
    Write-Output "CHECK: BLE audio fixture hex exists: $audioFixtureHexRelative -> $((Test-Path -LiteralPath $audioFixtureHex -PathType Leaf))"
    Write-Output "CHECK: Real flash must run inside workflow lock:"
    Write-Output "  $referenceLockCommand"
    Write-Output "  $nucleoLockCommand"
    Write-Output "  $audioFixtureLockCommand"
    Write-Output "  $packageLockCommand"
    if (-not [string]::IsNullOrWhiteSpace($PackagePath)) {
        $checkArtifacts = @(Get-WiredFactoryArtifacts -Path $PackagePath)
        Write-Output "CHECK: Factory package manifest: $($checkArtifacts[0].ManifestPath)"
        foreach ($artifact in $checkArtifacts) {
            Write-Output "CHECK: Factory artifact $($artifact.Role): $($artifact.Path)"
        }
    }
    exit 0
}

if (-not $Execute) {
    throw "Refusing to flash without -Execute. For a dry check, use -CheckOnly."
}

if (-not $WorkflowLockHeld) {
    throw "Refusing to flash without workflow lock acknowledgement. Run under aiw with-lock -Resource Companion-WB55 and pass -WorkflowLockHeld inside the locked command."
}

$selectedFlashTargets = @(@($FlashReference, $FlashNucleoBringup, $FlashAudioFixture, $FlashPackage) | Where-Object { $_ })
if ($selectedFlashTargets.Count -gt 1) {
    throw "Select only one flash target: -FlashReference, -FlashNucleoBringup, -FlashAudioFixture, or -FlashPackage."
}

if (-not $FlashReference -and -not $FlashNucleoBringup -and -not $FlashAudioFixture -and -not $FlashPackage) {
    throw "No flash target selected. Pass -FlashReference, -FlashNucleoBringup, -FlashAudioFixture, or -FlashPackage."
}

if (-not $programmer) {
    throw "STM32CubeProgrammer CLI not found. Install STM32CubeProgrammer, add STM32_Programmer_CLI.exe to PATH, or pass -ProgrammerPath."
}

if ($FlashPackage) {
    if ([string]::IsNullOrWhiteSpace($PackagePath)) {
        throw "Pass -PackagePath <package directory, package zip, or factory manifest> with -FlashPackage."
    }
    $packageArtifacts = @(Get-WiredFactoryArtifacts -Path $PackagePath)
    $targetImage = $packageArtifacts[0].Path
    $targetLabel = "Companion wired factory package"
} elseif ($FlashReference) {
    Assert-Path -Path $referenceHex -Label "BLE_p2pServer reference hex"
    Assert-Path -Path $bleStackBinary -Label "WB55 BLE full stack binary"
    $targetImage = $referenceHex
    $targetLabel = "official BLE_p2pServer reference image"
} elseif ($FlashAudioFixture) {
    $targetImage = if ($ImagePath) {
        $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($ImagePath)
    } else {
        $audioFixtureHex
    }
    Assert-Path -Path $targetImage -Label "Companion BLE audio fixture image"
    $targetLabel = "Companion BLE audio fixture image"
} else {
    $targetImage = if ($ImagePath) {
        $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($ImagePath)
    } else {
        $nucleoBringupHex
    }
    Assert-Path -Path $targetImage -Label "Companion NUCLEO bring-up image"
    $targetLabel = "Companion NUCLEO bring-up image"
}

$connectArgs = @("port=$Port")
if ($FlashNucleoBringup -or $FlashAudioFixture -or $FlashPackage) {
    $connectArgs += @("mode=UR", "reset=HWrst", "freq=4000")
}

if ($FlashPackage) {
    $artifactLines = ($packageArtifacts | ForEach-Object { " - $($_.Role): $($_.Path)" }) -join [Environment]::NewLine
    Show-OperatorPrompt -Title "Companion WB55 有线刷机确认" -Message "请确认 Companion/NUCLEO-WB55 已通过板载 ST-LINK USB 接好，Type/串口监视器已停止占用设备。将从同一个 Companion package 顺序刷入 OTA loader 和 app：$([Environment]::NewLine)$artifactLines$([Environment]::NewLine)$([Environment]::NewLine)点击 OK 开始刷机；点击 Cancel 取消。"

    for ($index = 0; $index -lt $packageArtifacts.Count; $index++) {
        $artifact = $packageArtifacts[$index]
        Invoke-ProgrammerWrite -Image $artifact.Path -Label "factory artifact $($artifact.Role)" -ConnectArgs $connectArgs -ResetAfter:($index -eq ($packageArtifacts.Count - 1))
    }
} else {
    Show-OperatorPrompt -Title "Companion WB55 有线刷机确认" -Message "请确认 Companion/NUCLEO-WB55 已通过板载 ST-LINK USB 接好，Type/串口监视器已停止占用设备。将刷入：$targetLabel$([Environment]::NewLine)$targetImage$([Environment]::NewLine)$([Environment]::NewLine)点击 OK 开始刷机；点击 Cancel 取消。"
    Invoke-ProgrammerWrite -Image $targetImage -Label $targetLabel -ConnectArgs $connectArgs -ResetAfter
}

Write-Output "PASS: $targetLabel flashed."
