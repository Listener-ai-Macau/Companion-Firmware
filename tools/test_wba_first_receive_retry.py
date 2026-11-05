from pathlib import Path
import sys,os,json,subprocess,hashlib,struct,zlib,shutil,copy
fw=Path(__file__).resolve().parents[1]
from argparse import ArgumentParser
p=ArgumentParser(description='Verify first paired OTA intent recovery with actual SPI NOR command handling; no board or real PKA claims')
p.add_argument('--output',required=True,type=Path);out=p.parse_args().output.resolve();out.mkdir(parents=True,exist_ok=False)
sys.path.insert(0,str(fw/'tools'))
from test_wba_system_bundle import BundleTests
from wba_system_bundle import sign_device_wire,public_key
from sign_wba_update_manifest import signed_prefix
from argparse import Namespace
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature,encode_dss_signature
f=BundleTests();f.setUp()
try:
 candidate=(f.root/'system-transaction.wsb').read_bytes();d=copy.deepcopy(f.d)
 for name,target,version in [('firmware','firmware',314),('resources','ui-assets',68)]:
  p=(f.root/d['components'][name]['file']).read_bytes()
  args=Namespace(target=target,format_version=1 if target=='firmware' else 2,target_family=0x41425743,board_target=f.g.board_target,component_version=version,minimum_app_version=314 if name=='resources' else 0,maximum_app_version=314 if name=='resources' else 0,key_id=1)
  body=signed_prefix(args,p);r,s=decode_dss_signature(f.key.sign(body,ec.ECDSA(hashes.SHA256())))
  body+=r.to_bytes(32,'big')+s.to_bytes(32,'big');d['components'][name].update(version=version,wba_manifest_hex=(body+struct.pack('<I',zlib.crc32(body))).hex())
 d['resource_contract']['generation']=68;current=sign_device_wire(d,f.key)
 for wire,name in [(candidate,'candidate'),(current,'current')]:
  dig=[]
  for body,at in [(wire[:384],384),(wire[96:172],172),(wire[240:316],316)]:
   sig=wire[at:at+64];public_key(f.xy).verify(encode_dss_signature(int.from_bytes(sig[:32],'big'),int.from_bytes(sig[32:],'big')),body,ec.ECDSA(hashes.SHA256()));dig.append(hashlib.sha256(body).digest())
  (out/(name+'.wsb')).write_bytes(wire);(out/(name+'-digests.bin')).write_bytes(b''.join(dig))
 (out/'public.xy').write_bytes(f.xy)
finally:f.tearDown()
harness=(fw/'platform/stm32wba55_companion_v11/tests/test_system_first_retry.c').read_text(encoding='utf-8').replace('#include \"test_system_storage.c\"','#include \"'+(fw/'platform/stm32wba55_companion_v11/tests/test_system_storage.c').as_posix()+'\"')

(out/'test-repair.c').write_text(harness,encoding='utf-8')
sources=[out/'test-repair.c',fw/'platform/stm32wba55_companion_v11/system_storage.c']
sources += [fw/'app/companion_pendant/update'/n for n in ['wba_system_anchor.c','wba_system_confirmed.c','wba_system_journal.c','wba_system_receive.c','wba_system_wire.c','wba_update_manifest_wire.c','wba_update_p256.c','wba_update_service.c']]
sources += [fw/'app/companion_pendant/storage/spi_nor_stm32wba.c',fw/'app/companion_pendant/storage/wba_workspace_layout.c',fw/'third_party/denzic-platform/ota/embedded/c/src/denzic_ota_v1.c']
includes=[fw/'platform/stm32wba55_companion_v11',fw/'app/companion_pendant/update',fw/'app/companion_pendant/storage',fw/'third_party/denzic-platform/ota/embedded/c/include']
vc=Path(r'C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat');exe=out/'repair.exe';command=out/'build.cmd'
command.write_text('@call "'+str(vc)+'" >nul\ncl.exe /nologo /TC /std:c11 /O2 /W4 /WX /wd4295 /DCOMP_WBA_BOOT_FLASH_KIB=24 /DCOMP_WBA_NOR_UI_BYTES=8192 '+' '.join('/I"'+str(p)+'"' for p in includes)+' '+' '.join('"'+str(p)+'"' for p in sources)+' /Fe"'+str(exe)+'" /link /INCREMENTAL:NO\n')
p=subprocess.run([os.environ['ComSpec'],'/d','/c',str(command)],cwd=out,capture_output=True,text=True);(out/'build.log').write_text(p.stdout+p.stderr);assert p.returncode==0,p.stdout+p.stderr
p=subprocess.run([str(exe),str(out/'candidate.wsb'),str(out/'public.xy'),str(out/'candidate-digests.bin'),str(out/'current.wsb'),str(out/'current-digests.bin')],cwd=out,capture_output=True,text=True);(out/'run.log').write_text(p.stdout+p.stderr)
result=dict(result='FIRST_TORN_RECEIVE_RETRY_SOFTWARE_VALID' if p.returncode==0 else 'FAILED',output=p.stdout+p.stderr,hardwareOperations=0,installed=False,signatureFixturesVerified=True,hardwareSignatureAndDestinationCoordinatorFake=True,sourceSha256={p.relative_to(fw).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sources if p.is_relative_to(fw)})
(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result));sys.exit(p.returncode)
