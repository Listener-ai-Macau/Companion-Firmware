"""Narrow portable menu/control-owner comparison requested by the pet Goal.

Uses real runtime/recognizer/menu with frozen input sources and fake I/O.
Does not contact hardware or claim optical/capture/acoustic qualification.
"""
from pathlib import Path
import argparse,hashlib,json,shutil,subprocess
from verify_wba_spi_nor_adapter import find_vsdevcmd

ROOT=Path(__file__).resolve().parents[1]
SOURCE_NAMES=['runtime/companion_runtime.c','runtime/companion_pet_behavior.c','runtime/companion_pet_chat.c',
 'playback/audio_feedback.c','playback/speaker_playback.c','touch/touch_gesture.c','touch/touch_tap_arbiter.c',
 'touch/browser_interaction_runtime.c','epaper/screen_menu.c','epaper/screen_framebuffer.c','epaper/motion_coordinator.c','power/power_settings_store.c']
FOLDERS=['runtime','runtime/generated','playback','touch','epaper','imu','power']
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--profile',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--fixture',type=Path);p.add_argument('--expect-old-rejection',action='store_true');a=p.parse_args()
 source=a.source.resolve();out=a.output.resolve();out.mkdir(parents=True,exist_ok=False);frozen=out/'source';project=source/'app/companion_pendant'
 sha=lambda b:hashlib.sha256(b).hexdigest();hashes={};sources=[]
 for name in SOURCE_NAMES:
  old=project/name;target=frozen/'app/companion_pendant'/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(old.read_bytes());hashes[old.relative_to(source).as_posix()]=sha(target.read_bytes());sources.append(target)
 includes=[]
 for folder in FOLDERS:
  includes.append(frozen/'app/companion_pendant'/folder)
  for old in (project/folder).glob('*.h'):
   target=frozen/old.relative_to(source);target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(old.read_bytes());hashes[old.relative_to(source).as_posix()]=sha(target.read_bytes())
 shared=Path('third_party/denzic-platform/audio/embedded/c/include');includes.append(frozen/shared)
 for old in (source/shared).glob('*.h'):
  target=frozen/old.relative_to(source);target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(old.read_bytes());hashes[old.relative_to(source).as_posix()]=sha(target.read_bytes())
 profile=out/'profile';profile.mkdir();profile_hashes={}
 for old in a.profile.resolve().glob('*.h'):
  target=profile/old.name;target.write_bytes(old.read_bytes());profile_hashes[old.name]=sha(target.read_bytes())
 fixture=a.fixture.resolve() if a.fixture else ROOT/'app/companion_pendant/runtime/tests/test_menu_control_continuity.c'
 test=out/'test_menu_control_continuity.c';test.write_bytes(fixture.read_bytes());exe=out/'menu_continuity.exe';devcmd=find_vsdevcmd()
 if not devcmd:raise RuntimeError('MSVC unavailable')
 args=['cl.exe','/nologo','/std:c11','/W4','/WX','/wd4127','/utf-8','/O1','/DCOMPANION_WBA_RESOURCE_PROFILE=1','/DCOMPANION_SCREEN_COMP_REQ_638_SOURCE_PACK=1',f'/I{profile}',*[f'/I{x}' for x in includes],*[str(x) for x in sources],str(test),f'/Fe:{exe}']
 script=out/'build.cmd';script.write_text('@echo off\ncall "'+str(devcmd)+'" -arch=amd64 -host_arch=amd64 >nul\nif errorlevel 1 exit /b %errorlevel%\n'+subprocess.list2cmdline(args)+'\n',encoding='utf-8')
 built=subprocess.run(['cmd.exe','/d','/c',str(script)],cwd=out,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);(out/'build.log').write_bytes(built.stdout)
 report=dict(result='COMPILE_FAILED',source=str(source),sourceSha256=hashes,profileSha256=profile_hashes,fixtureSha256=sha(test.read_bytes()),buildExitCode=built.returncode,hardwareOperations=0,physicalQualified=False,captureQualified=False,fullChainAcceptance='NOT_RUN')
 if built.returncode==0:
  ran=subprocess.run([str(exe)],cwd=out,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);(out/'run.log').write_bytes(ran.stdout);lines=ran.stdout.decode(errors='replace');print(lines,end='')
  report.update(runExitCode=ran.returncode,output=lines,exeSha256=sha(exe.read_bytes()))
  if a.expect_old_rejection:
   report['result']='OLD_REJECTION_REPRODUCED' if ran.returncode!=0 and 'io.menu_calls==1u&&r.menu.browser.clock_24_hour!=before' in lines else 'OLD_REJECTION_NOT_REPRODUCED'
  else:report['result']='PASS_MENU_CONTROL_CONTINUITY_SOFTWARE_ONLY' if ran.returncode==0 and 'PASS_MENU_CONTROL_CONTINUITY_SOFTWARE:' in lines else 'FAIL_MENU_CONTROL_CONTINUITY'
 (out/'result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(report['result']);return 0 if report['result'] in ('OLD_REJECTION_REPRODUCED','PASS_MENU_CONTROL_CONTINUITY_SOFTWARE_ONLY') else 1
if __name__=='__main__':raise SystemExit(main())
