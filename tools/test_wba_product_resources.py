#!/usr/bin/env python3
from pathlib import Path
import argparse,hashlib,json,shutil,subprocess
from build_wba_prehardware import run
from verify_wba_spi_nor_adapter import find_vsdevcmd

ROOT=Path(__file__).resolve().parents[1];APP=ROOT/'app/companion_pendant';OUT=ROOT/'.cache/wba-product-resources'
SRC=[APP/p for p in ('runtime/companion_resources.c','runtime/companion_renderer.c','epaper/asset_store.c','epaper/emote_asset_pack.c','epaper/emote_player.c','epaper/ui_asset_generation.c','epaper/screen_menu.c','epaper/screen_framebuffer.c','epaper/motion_coordinator.c','touch/browser_interaction_runtime.c','runtime/tests/test_wba_product_resources.c')]
INC=[APP/d for d in ('runtime','runtime/generated','epaper','touch','playback','power','imu')]
INC += [ROOT/'third_party/denzic-platform/audio/embedded/c/include']
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reuse-resource-build',action='store_true',
                        help='Reuse exact source-matched resource pixels; still rebuild and run the C decoder/renderer gate.')
    args=parser.parse_args()
    log=OUT/'test-build.log';log.write_text('');report={'result':'FAIL','hardwareAcceptance':'NOT_RUN'}
    try:
        if args.reuse_resource_build:
            profile=json.loads((OUT/'profile.json').read_text())
            if digest(OUT/'ui-partition.bin').upper()!=profile['uiPartitionSha256'].upper():
                raise RuntimeError('Reusable resource image does not match its profile')
            stale=[name for name,expected in profile['sourceSha256'].items()
                   if digest(ROOT/name).upper()!=expected.upper()]
            if stale:raise RuntimeError(f'Reusable resource source changed: {stale[:5]}')
        else:run(['python',str(ROOT/'tools/build_wba_product_resources.py')],ROOT,log,timeout=180)
        exe=OUT/'test_resources.exe';dev=find_vsdevcmd()
        args=['cl.exe','/nologo','/std:c11','/W4','/WX','/utf-8','/D_CRT_SECURE_NO_WARNINGS','/DCOMPANION_SCREEN_COMP_REQ_638_SOURCE_PACK=1','/DCOMPANION_WBA_RESOURCE_PROFILE=1',*(f'/I{p}' for p in INC),*(str(p) for p in SRC),f'/Fe:{exe}']
        cmd=OUT/'test-build.cmd';cmd.write_text(f'@echo off\ncall "{dev}" -arch=amd64 -host_arch=amd64 >nul\nif errorlevel 1 exit /b %errorlevel%\n'+subprocess.list2cmdline(args)+'\n')
        run(['cmd.exe','/d','/c',str(cmd)],OUT,log);text=run([str(exe),str(OUT/'ui-partition.bin'),str(OUT/'states.txt')],OUT,log)
        print(text,end='');
        if 'PASS_WBA_PRODUCT_RESOURCES' not in text:raise RuntimeError('completion missing')
        cc=shutil.which('arm-none-eabi-gcc');
        if not cc:raise RuntimeError('Cortex-M33 compiler missing')
        run([cc,'-std=c11','-mcpu=cortex-m33','-mthumb','-Os','-Wall','-Wextra','-Werror','-DCOMPANION_WBA_RESOURCE_PROFILE=1',*(f'-I{p}' for p in INC),'-c',str(APP/'runtime/companion_resources.c'),'-o',str(OUT/'companion_resources.o')],OUT,log)
        profile=json.loads((OUT/'profile.json').read_text())
        states=profile['states'];checks={
          'all_ten_family_rest_bootstrap':all(f'life_{family}_e0_s0_rest_hold' in states for family in ('calm','curious','delighted','warm','playful','sleepy','bashful','thoughtful','focused','alert')),
          'directional_life_is_distinct':states['life_calm_e0_s2_notice_left_accent']['sha256']!=states['life_calm_e0_s2_notice_right_accent']['sha256'],
          'all_menu_screens_locales':all(any(k.startswith(f'menu_ui_{locale}_s{screen}_') for k in states) for locale in ('en','zh_cn','zh_tw') for screen in range(13)),
          'all_menu_rows_have_three_phases':all(any(f'_{phase}_i{item}' in k and f'_s{screen}_' in k for k in states) for screen,n in enumerate((8,7,4,7,4,2,3,5,6,7,5,3,3)) for item in range(n) for phase in ('ack','processing','result')),
          'menu_setting_variants_are_visible':states['menu_ui_zh_cn_s1_o4_normal']['sha256']!=states['menu_ui_zh_cn_s1_o4_normal_v1']['sha256'],
          'pointer_grid_complete':sum(v['kind']=='pointer_follow' for v in states.values())==250,
          'recording_timeline_complete':sum(v['kind']=='recording_timeline' for v in states.values())==64,
          'pointer_changes_only_registered_eyes':profile['artQualityChecks']['pointerChangedPixelsRestrictedToRegisteredEyes'],
          'life_preserves_fixed_anatomy':profile['artQualityChecks']['lifeFixedCheekNosePixelsPreserved'],
          'life_rest_equals_default':profile['artQualityChecks']['lifeRestEqualsExpressionDefault'],
          'life_excludes_blink_closed':profile['artQualityChecks']['lifeExcludesNaturalBlinkClosedCue'],
          'recording_restores_verified_original_keyframe':profile['artQualityChecks']['recordingArt']['referenceFrameExact'] and profile['artQualityChecks']['recordingArt']['microphoneBlackPixels']==108,
          'recording_has_continuous_motion':profile['artQualityChecks']['recordingArt']['uniqueFrames']>20,
        }
        if not all(checks.values()):raise RuntimeError(f'profile coverage failed: {checks}')
        report.update(result='PASS_SOFTWARE_RESOURCE_PROFILE',profileRevision=profile['profileRevision'],generation=profile['generation'],resourceId=profile['resourceId'],stateCount=profile['stateCount'],canonicalFrameCount=profile['canonicalFrameCount'],uiPartitionSha256=profile['uiPartitionSha256'],sleepyDistinctFromCalm=profile['sleepyDistinctFromCalm'],hostOutput=text.strip(),sourceSha256={str(p.relative_to(ROOT)):digest(p) for p in [*SRC,ROOT/'tools/build_wba_product_resources.py',Path(__file__),ROOT/'tools/build_wba_prehardware.py',APP/'runtime/generated/companion_wba_resource_contract.h',APP/'epaper/ssd1681_wba.h',APP/'runtime/generated/companion_wba_live_menu_values.h',APP/'runtime/generated/companion_wba_menu_feedback.h',APP/'runtime/generated/companion_wba_menu_geometry.h']})
        report['checks']=checks
    except Exception as e:report['error']=str(e);print(e)
    (OUT/'test-result.json').write_text(json.dumps(report,indent=2)+'\n');return int(report['result']=='FAIL')
if __name__=='__main__':raise SystemExit(main())
