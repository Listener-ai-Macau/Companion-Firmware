#requires -Version 7.0
param([Parameter(Mandatory=$true)][string]$StepJsonPath)
$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$step = Get-Content -LiteralPath $StepJsonPath -Raw -Encoding UTF8 | ConvertFrom-Json
$op = "C:\Users\Billy\Desktop\Denzic\ai-collaboration-workflow\scripts\operator_prompt.ps1"
$out = [string]$step.output_path
$dir = Split-Path -Parent $out
if ($dir -and -not (Test-Path -LiteralPath $dir)) { New-Item -ItemType Directory -Force -Path $dir | Out-Null }
$notePath = $out
if ($notePath -notlike "*.txt") { $notePath = [IO.Path]::ChangeExtension($out, ".note.txt") }
$jsonPath = if ($out -like "*.json") { $out } else { $out + ".json" }

$arg = @(
  "-NoProfile","-STA","-File",$op,
  "-Title", [string]$step.title,
  "-ProgressText", [string]$step.progress,
  "-ScopeText", [string]$step.scope,
  "-Message", [string]$step.message,
  "-ExpectedText", [string]$step.expected,
  "-Buttons", $(if ($step.buttons) { [string]$step.buttons } else { "通过,失败,跳过,中止" }),
  "-OutputPath", $notePath,
  "-Width","820","-Height","480",
  "-Position","Center",
  "-ReviewStyle","-Input","-Json","-NoSound"
)
# IMPORTANT: invoke in-process so Chinese args stay Unicode (no cmd re-encode)
$psiOutput = & $op `
  -Title ([string]$step.title) `
  -ProgressText ([string]$step.progress) `
  -ScopeText ([string]$step.scope) `
  -Message ([string]$step.message) `
  -ExpectedText ([string]$step.expected) `
  -Buttons $(if ($step.buttons) { [string]$step.buttons } else { "通过,失败,跳过,中止" }) `
  -OutputPath $notePath `
  -Width 820 -Height 480 `
  -Position Center `
  -ReviewStyle -Input -Json -NoSound

# Save full JSON result
if ($psiOutput) {
  $text = if ($psiOutput -is [array]) { $psiOutput -join "`n" } else { [string]$psiOutput }
  [IO.File]::WriteAllText($jsonPath, $text, [Text.UTF8Encoding]::new($false))
  Write-Output $text
}