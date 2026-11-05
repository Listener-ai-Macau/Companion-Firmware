param([string]$OutRoot='.cache/validation/comp-req-513-recording-trace', [string]$Mutation='none')
$ErrorActionPreference='Stop'
$root=(Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$out=Join-Path $root $OutRoot; New-Item -ItemType Directory -Force $out | Out-Null
$epaper=Join-Path $root 'app/companion_pendant/epaper'; $touch=Join-Path $root 'app/companion_pendant/touch'
$record=Join-Path $root 'app/companion_pendant/recording'; $diag=Join-Path $root 'app/companion_pendant/diag_log'
$fixture=Join-Path $PSScriptRoot 'comp_req_513_recording_trace.c'; $exe=Join-Path $out 'comp-req-513-recording-trace.exe'
$boundary=Join-Path $touch 'touch_recording_boundary.c'; $gesture=Join-Path $touch 'touch_gesture.c'
$mutantRoot=Join-Path $out 'mutant-source'
$edge=''
if($Mutation -ne 'none') {
    $mutantRoot=Join-Path $root ('.cache/validation/comp-req-525-mutant-build/'+$Mutation)
    $exe=Join-Path $mutantRoot 'comp-req-513-recording-trace.exe'
    New-Item -ItemType Directory -Force $mutantRoot | Out-Null
    $mutantBoundary=Join-Path $mutantRoot 'touch_recording_boundary.c'
    $mutantGesture=Join-Path $mutantRoot 'touch_gesture.c'
    $mutantFixture=Join-Path $mutantRoot 'comp_req_513_recording_trace.c'
    Copy-Item $boundary $mutantBoundary
    Copy-Item $gesture $mutantGesture
    Copy-Item $fixture $mutantFixture
    $fixtureText=Get-Content $mutantFixture -Raw
    if($Mutation -eq 'dispatcher_bypass') {
        $fixtureText=$fixtureText -replace 'if \(!comp_touch_recording_boundary_dispatch\(\s*&t->boundary,\s*&decision,\s*t->menu_visible,\s*t->menu_visible \? &t->menu : NULL,\s*t->fsm.state,\s*now\)\)', 'if (!comp_touch_recording_boundary_submit(&t->boundary, &decision.gesture, t->fsm.state, t->menu_visible, now))'
        $edge='fixture.feed:direct_submit_bypass'
    } elseif($Mutation -eq 'dispatcher_drop') {
        $fixtureText=$fixtureText.Replace('if (!comp_touch_recording_boundary_dispatch(', 'if (t->menu_visible && !comp_touch_recording_boundary_dispatch(')
        $edge='fixture.feed:discard_dispatch'
    } elseif($Mutation -eq 'direct_fsm') {
        $fixtureText=$fixtureText.Replace('if (!comp_touch_recording_boundary_dispatch(', 'if ((void)comp_recording_fsm_dispatch(&t->fsm, COMP_RECORDING_EVENT_START_REQUEST, COMP_RECORDING_SOURCE_USER_TOUCH), !comp_touch_recording_boundary_dispatch(')
        $edge='fixture.feed:direct_fsm_call'
    }
    Set-Content -Path $mutantFixture -Value $fixtureText -Encoding utf8
    $fixture=$mutantFixture
    $text=Get-Content $mutantBoundary -Raw
    switch($Mutation) {
        'dispatcher_duplicate' { $text=$text.Replace('if (boundary->queue[i] == COMP_TOUCH_RECORDING_ACTION_TOGGLE) {','if (false && boundary->queue[i] == COMP_TOUCH_RECORDING_ACTION_TOGGLE) {'); $edge='boundary.submit:disable_dedupe' }
        'menu_sink_noop' { $text=$text.Replace('return boundary->sinks.menu == NULL ||','return true ||'); $edge='boundary.dispatch:skip_menu_sink' }
        'deferred_drop' { $text=$text.Replace('boundary->queue[boundary->queue_count++] =','boundary->queue[boundary->queue_count] ='); $edge='boundary.submit:drop_enqueue' }
        'supersede' { $text=$text.Replace('boundary->deduplicated++;','boundary->deduplicated++; boundary->queue_count = 0u;'); $edge='boundary.submit:clear_retained' }
    }
    Set-Content -Path $mutantBoundary -Value $text -Encoding utf8
    $gtext=Get-Content $mutantGesture -Raw
    if($Mutation -eq 'threshold') { $gtext=$gtext.Replace('now_ms - state->last_tap_ms <= state->config.double_tap_max_gap_ms &&','false &&'); $edge='gesture.process:disable_window' }
    Set-Content -Path $mutantGesture -Value $gtext -Encoding utf8
    $gesture=$mutantGesture
    $boundary=$mutantBoundary
}
$vcvars=$null; $where=Get-Command vswhere.exe -ErrorAction SilentlyContinue
if($where){$install=& $where.Source -latest -products '*' -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath 2>$null|Select-Object -First 1;if($install){$vcvars=Get-ChildItem (Join-Path $install 'VC/Auxiliary/Build') -Filter vcvars64.bat -File|Select-Object -First 1 -ExpandProperty FullName}}
if(-not $vcvars){$vcvars=Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio/2022/BuildTools/VC/Auxiliary/Build/vcvars64.bat'}
if(-not(Test-Path $vcvars)){throw 'MSVC vcvars64 unavailable'}
$sources=@($fixture,(Join-Path $touch 'ft6336.c'),$gesture,(Join-Path $touch 'touch_visual_decision.c'),$boundary,(Join-Path $epaper 'screen_menu.c'),(Join-Path $epaper 'screen_framebuffer.c'),(Join-Path $epaper 'companion_visual_asset_pack.c'),(Join-Path $record 'recording_fsm.c'),(Join-Path $record 'microphone.c'),(Join-Path $diag 'diag_log.c'),(Join-Path $root 'third_party/denzic-platform/audio/embedded/c/src/denzic_audio_recording_v1.c'))
$args=($sources|%{('"'+$_+'"')}) -join ' '; $log=Join-Path $out 'compile.log'
$wx=if($Mutation -eq 'none'){'/WX'}else{'/WX-'}
$cmd='call "'+$vcvars+'" >nul && cl.exe /nologo /Brepro /TC /std:c11 /O2 /W4 '+$wx+' /DCOMPANION_VISUAL_ASSET_PACK_ENABLE=1 /I"'+$epaper+'" /I"'+$touch+'" /I"'+$record+'" /I"'+$diag+'" /I"'+(Join-Path $root 'third_party/denzic-platform/audio/embedded/c/include')+'" '+$args+' /Fe:"'+$exe+'"'
cmd.exe /d /s /c $cmd 2>&1|Set-Content -Encoding utf8 $log
if($LASTEXITCODE -ne 0){throw 'COMP-REQ-513 compile failed'}
$stdout=& $exe 2>&1|Out-String;$code=$LASTEXITCODE
$mutantHashes=[ordered]@{}
if(Test-Path $mutantRoot){Get-ChildItem $mutantRoot -File | ForEach-Object {$mutantHashes[$_.Name]=(Get-FileHash $_.FullName -Algorithm SHA256).Hash.ToUpper()}}
[ordered]@{status=if($code-eq0){'PASS'}else{'NO_GO'};exit_code=$code;mutation=$Mutation;changed_edge=$edge;stdout=$stdout.Trim();runner_sha256=(Get-FileHash $PSCommandPath -Algorithm SHA256).Hash.ToUpper();mutant_source_sha256=$mutantHashes;compile_command=$cmd;executable_sha256=(Get-FileHash $exe -Algorithm SHA256).Hash.ToUpper();checkonly=[ordered]@{hardware_contact=0;programmer=0;serial=0;write=0;reset=0;refresh=0;popup=0;retry=0}}|ConvertTo-Json -Depth 8|Set-Content -Encoding utf8 (Join-Path $out 'result.json')
if($code-ne0){exit $code}
