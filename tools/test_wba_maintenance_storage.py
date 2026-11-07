from pathlib import Path
import hashlib,json,subprocess,sys
r=Path(__file__).resolve().parents[1]
from test_wba_ota_stream_backpressure import function
from verify_wba_spi_nor_adapter import find_vsdevcmd
out=Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=False);source=r/'platform/stm32wba55_companion_v11/ble/ble_product.c'
(out/'snapshot.inc').write_text(function(source.read_text(),'static void maintenance_storage_fields')+'\n')
(out/'snapshot.c').write_text(r'''
#include "maintenance_protocol.h"
#include "spi_nor_stm32wba.h"
#include <assert.h>
#include <stdio.h>
#include "snapshot.inc"
int main(void){
 companion_spi_nor_stm32wba_t n={0},before;uint8_t p[32];
 for(unsigned bits=0;bits<32;bits++){
  n.probed=(bits&1u)!=0;n.erase_suspend_supported=(bits&2u)!=0;
  n.info.erase_32k_supported=(bits&4u)!=0;n.erase_active=(bits&8u)!=0;n.erase_command_failed=(bits&16u)!=0;
  n.info.jedec_id=0xef6018;n.erase_address=98304;n.erase_bytes=32768;
  n.erase_phase=3;n.info.sfdp_bfp_dwords=16;n.resume_guard_ms=2;n.suspend_wait_ms=1;
  memcpy(&before,&n,sizeof(n));memset(p,0xa5,sizeof(p));maintenance_storage_fields(&n,p);
  assert(!memcmp(&before,&n,sizeof(n))&&p[6]==bits);
  assert(comp_maint_get32(p+12)==0xef6018&&comp_maint_get32(p+16)==98304&&comp_maint_get32(p+20)==32768);
  assert(p[24]==3&&p[25]==16&&p[26]==2&&p[27]==1);
  for(unsigned i=0;i<32;i++)if(i<6||(i>=7&&i<12)||i>=28)assert(p[i]==0xa5);
 }
 puts("PASS actual storage scalar serializer32 combinations; owner preserved; no I/O, mutation, payload or header/nonce/CRC writes");return 0;
}''')
files=[source,r/'platform/stm32wba55_companion_v11/ble/maintenance_protocol.h',r/'app/companion_pendant/storage/spi_nor_stm32wba.h']
(out/'source.json').write_text(json.dumps({p.relative_to(r).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()for p in files},indent=2)+'\n')
args=['cl.exe','/nologo','/W4','/WX','/std:c11','/TC',*[str('/I'+str(r/n))for n in ['platform/stm32wba55_companion_v11/ble','app/companion_pendant/storage']],str(out/'snapshot.c'),'/Fe:'+str(out/'snapshot.exe')]
cmd=out/'build.cmd';cmd.write_text('@echo off\ncall "'+str(find_vsdevcmd())+'" -arch=amd64 -host_arch=amd64 >nul\nif errorlevel 1 exit /b %errorlevel%\n'+subprocess.list2cmdline(args)+'\n',encoding='ascii')
for name,args in [('compile',['cmd.exe','/d','/c',str(cmd)]),('run',[str(out/'snapshot.exe')])]:
    p=subprocess.run(args,cwd=out,capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW);(out/(name+'.log')).write_text(p.stdout+p.stderr);assert p.returncode==0,p.stdout+p.stderr
(out/'result.json').write_text(json.dumps({'result':'PASS_ACTUAL_CACHED_STORAGE_SCALAR_SERIALIZER','noDeviceIO':True,'source':hashlib.sha256(source.read_bytes()).hexdigest()})+'\n');print('PASS storage diagnostic serializer')
