param([string]$OutRoot = '.cache/validation/comp-req-501-raw-touch-trace',
      [ValidateSet('none','missing_raw','duplicate_raw','duplicate_sink','no_frame_hash','direct_injection','legacy_remap','drop_decision','duplicate_decision','altered_target','bypass_route_render')]
      [string]$Mutation = 'none')
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$out = Join-Path $root $OutRoot
New-Item -ItemType Directory -Force -Path $out | Out-Null
$epaper = Join-Path $root 'app/companion_pendant/epaper'
$touch = Join-Path $root 'app/companion_pendant/touch'
$fixture = Join-Path $root 'tools/comp_req_501_raw_touch_trace.c'
$exe = Join-Path $out 'comp-req-501-raw-touch-trace.exe'
$log = Join-Path $out 'compile.log'
$vcvars = $null
$where = Get-Command vswhere.exe -ErrorAction SilentlyContinue
if ($where) { $install = & $where.Source -latest -products '*' -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath 2>$null | Select-Object -First 1; if ($install) { $vcvars = Get-ChildItem (Join-Path $install 'VC/Auxiliary/Build') -Filter vcvars64.bat -File | Select-Object -First 1 -ExpandProperty FullName } }
if (-not $vcvars) { $vcvars = Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio/2022/BuildTools/VC/Auxiliary/Build/vcvars64.bat' }
if (-not (Test-Path $vcvars)) { throw 'MSVC vcvars64 unavailable' }
$cmd = 'call "' + $vcvars + '" >nul && cl.exe /nologo /TC /std:c11 /O2 /W4 /WX /DCOMPANION_VISUAL_ASSET_PACK_ENABLE=1 /I"' + $epaper + '" /I"' + $touch + '" "' + $fixture + '" "' + (Join-Path $touch 'touch_gesture.c') + '" "' + (Join-Path $touch 'touch_visual_decision.c') + '" "' + (Join-Path $touch 'touch_visual_board_dispatch.c') + '" "' + (Join-Path $epaper 'screen_menu.c') + '" "' + (Join-Path $epaper 'screen_framebuffer.c') + '" "' + (Join-Path $epaper 'companion_visual_asset_pack.c') + '" /Fe:"' + $exe + '"'
$build = cmd.exe /d /s /c $cmd 2>&1; $build | Set-Content -Encoding utf8 $log
if ($LASTEXITCODE -ne 0 -or -not (Test-Path $exe)) { throw 'COMP-REQ-501 raw trace build failed' }
$previousMutation = $env:COMP_REQ_501_MUTATION
$env:COMP_REQ_501_MUTATION = $Mutation
$stdout = & $exe 2>&1 | Out-String; $exit = $LASTEXITCODE
if ($null -eq $previousMutation) { Remove-Item Env:COMP_REQ_501_MUTATION -ErrorAction SilentlyContinue } else { $env:COMP_REQ_501_MUTATION = $previousMutation }
$result = [ordered]@{schema='companion.comp_req_501.raw_touch_trace.v1'; status=if($exit -eq 0){'PASS'}else{'NO_GO'}; exit_code=$exit; stdout=$stdout.Trim(); compiler='MSVC dynamically discovered'; optimization='O2'; checkonly=[ordered]@{hardware_contact=0;programmer=0;serial=0;write=0;reset=0;refresh=0;popup=0;retry=0}}
$result | ConvertTo-Json -Depth 8 | Set-Content -Encoding utf8 (Join-Path $out 'result.json')
$result | ConvertTo-Json -Compress
if ($exit -ne 0) { exit $exit }
