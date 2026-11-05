from pathlib import Path
import sys,subprocess,json,hashlib,shutil,argparse
p=argparse.ArgumentParser();p.add_argument('--reference-source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--source-root',type=Path,default=Path(__file__).resolve().parents[1]);a=p.parse_args();S=a.source_root.resolve();E=S/'app/companion_pendant/epaper';sys.path.insert(0,str(S/'tools'))
from verify_wba_spi_nor_adapter import find_vsdevcmd
out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
frames=[]
for pattern in range(8):
 data=bytearray([255]*5000)
 for y in range(200):
  for x in range(25):
   if (x+pattern)%11==0 and (y+pattern)%7==0:data[y*25+x]=((x*17+y*3+pattern)&255)
 frames.append(bytes(data))
(out/'frames-a.bin').write_bytes(b''.join(frames[:4]));(out/'frames-b.bin').write_bytes(b''.join(frames[4:]))
base=['cl.exe','/nologo','/TC','/std:c11','/O2','/W4','/WX','/wd4127','/wd4505','/D_CRT_SECURE_NO_WARNINGS','/DCOMP_WBA_PACKED_OLD_FRAME=1',*['/I'+str(S/'app/companion_pendant'/n)for n in ['epaper','runtime','playback','touch','power','imu','recording','storage','v1_features']],'/I'+str(S/'third_party/denzic-platform/audio/embedded/c/include')]
commands=[base+['/c','/Dcomp_wba_frame_store_size=reference_frame_size','/Dcomp_wba_frame_store_write=reference_frame_write','/Dcomp_wba_frame_store_read=reference_frame_read',str(a.reference_source.resolve()),'/Fo:'+str(out/'reference.obj')],base+['/c','/Dcomp_wba_frame_store_read=timed_frame_read',str(E/'screen_presenter_wba.c'),'/Fo:'+str(out/'presenter.obj')],base+[str(E/'tests/test_wba_frame_store.c'),str(E/'wba_frame_store.c'),str(E/'ssd1681_wba.c'),str(E/'refresh_policy.c'),'/Fe:'+str(out/'test.exe'),'/link',str(out/'presenter.obj'),str(out/'reference.obj')]]
cmd=out/'compile.cmd';cmd.write_text('@echo off\ncall "'+str(find_vsdevcmd())+'" -arch=amd64 -host_arch=amd64 >nul\nif errorlevel 1 exit /b %errorlevel%\n'+'\nif errorlevel 1 exit /b %errorlevel%\n'.join(subprocess.list2cmdline(x)for x in commands)+'\n')
p=subprocess.run(['cmd.exe','/d','/c',str(cmd)],cwd=out,capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW);(out/'build.log').write_text(p.stdout+p.stderr);assert p.returncode==0,(p.stdout+p.stderr)[-5000:]
a=[str(out/'test.exe'),str(out/'frames-a.bin'),str(out/'frames-b.bin'),str(out/'raw.trace'),str(out/'packed.trace')];p=subprocess.run(a,cwd=out,capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW);(out/'result.log').write_text(p.stdout+p.stderr);assert p.returncode==0,(p.stdout+p.stderr)[-5000:]
assert (out/'raw.trace').read_bytes()==(out/'packed.trace').read_bytes(),'raw/packed panel commands, bytes and timing differ'
result={'result':'PASS_PRODUCTION_C_SOFTWARE_ONLY','output':p.stdout,'rawPackedWireParity':True,'injectedTimingNotArmMeasurement':True,'noVisualAssetChange':True,'referenceSource':str(a.reference_source.resolve()),'referenceSourceSha256':hashlib.sha256(a.reference_source.read_bytes()).hexdigest(),'inputSha256':{str(p.relative_to(S)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [E/'tests/test_wba_frame_store.c',E/'wba_frame_store.c',E/'wba_frame_store.h',E/'screen_presenter_wba.c',E/'screen_presenter_wba.h',E/'ssd1681_wba.c',E/'refresh_policy.c']}};(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
