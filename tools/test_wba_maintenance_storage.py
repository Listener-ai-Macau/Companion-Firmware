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
#include "wba_recording_pipeline.h"
#include <assert.h>
#include <stdio.h>
#include "snapshot.inc"
int main(void){
 companion_spi_nor_stm32wba_t n={0},before;uint8_t p[32];
 comp_segment_catalog_t catalog={0};comp_wba_recording_pipeline_t pipeline={0},saved;
 pipeline.config.catalog=&catalog;catalog.data_base=0xfd000;
 for(unsigned bits=0;bits<128;bits++){
  n.probed=(bits&1u)!=0;n.erase_suspend_supported=(bits&2u)!=0;
  n.info.erase_32k_supported=(bits&4u)!=0;n.erase_active=(bits&8u)!=0;n.erase_command_failed=(bits&16u)!=0;
  n.info.jedec_id=0xef6018;n.erase_address=98304;n.erase_bytes=32768;
  n.erase_phase=3;n.info.sfdp_bfp_dwords=16;n.resume_guard_ms=2;n.suspend_wait_ms=1;
  pipeline.consume.reserved_bytes=(bits&32u)?270336u:0u;
  pipeline.consume.extent_offset=4096;pipeline.consume.descriptor.recording_id=132208;
  pipeline.consume.descriptor.flags=11;pipeline.consume_phase=7;
  catalog.reclaim_block_sectors=(bits&64u)?8u:0u;
  memcpy(&before,&n,sizeof(n));memcpy(&saved,&pipeline,sizeof(pipeline));
  memset(p,0xa5,sizeof(p));maintenance_storage_fields(&n,&pipeline,p);
  assert(!memcmp(&before,&n,sizeof(n))&&!memcmp(&saved,&pipeline,sizeof(pipeline))&&p[6]==bits&&p[7]==2);
  assert(comp_maint_get32(p+12)==((bits&32u)?0xfe000u:0u)&&comp_maint_get32(p+16)==98304&&comp_maint_get32(p+20)==((bits&32u)?270336u:0u));
  assert(p[24]==8&&p[25]==7&&p[26]==3&&p[27]==((bits&32u)?11:0));
  for(unsigned i=0;i<32;i++)if(i<6||(i>=8&&i<12)||i>=28)assert(p[i]==0xa5);
 }
 pipeline.consume.descriptor.recording_id=0;
 maintenance_storage_fields(&n,&pipeline,p);
 assert(!(p[6]&32u)&&comp_maint_get32(p+12)==0&&comp_maint_get32(p+20)==0);
 puts("PASS actual storage/target serializer128 combinations; unknown target explicit; owner preserved; no I/O, mutation, payload or header/nonce/CRC writes");return 0;
}''')
files=[source,*[r/p for p in ['platform/stm32wba55_companion_v11/ble/maintenance_protocol.h','app/companion_pendant/storage/spi_nor_stm32wba.h','app/companion_pendant/recording/wba_recording_pipeline.h','app/companion_pendant/recording/companion_segment_catalog.h']]]
(out/'source.json').write_text(json.dumps({p.relative_to(r).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()for p in files},indent=2)+'\n')
args=['cl.exe','/nologo','/W4','/WX','/std:c11','/TC',*[str('/I'+str(r/n))for n in ['platform/stm32wba55_companion_v11/ble','app/companion_pendant/storage','app/companion_pendant/recording']],str(out/'snapshot.c'),'/Fe:'+str(out/'snapshot.exe')]
cmd=out/'build.cmd';cmd.write_text('@echo off\ncall "'+str(find_vsdevcmd())+'" -arch=amd64 -host_arch=amd64 >nul\nif errorlevel 1 exit /b %errorlevel%\n'+subprocess.list2cmdline(args)+'\n',encoding='ascii')
for name,args in [('compile',['cmd.exe','/d','/c',str(cmd)]),('run',[str(out/'snapshot.exe')])]:
    p=subprocess.run(args,cwd=out,capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW);(out/(name+'.log')).write_text(p.stdout+p.stderr);assert p.returncode==0,p.stdout+p.stderr
(out/'result.json').write_text(json.dumps({'result':'PASS_ACTUAL_CACHED_STORAGE_SCALAR_SERIALIZER','noDeviceIO':True,'source':hashlib.sha256(source.read_bytes()).hexdigest()})+'\n');print('PASS storage diagnostic serializer')
