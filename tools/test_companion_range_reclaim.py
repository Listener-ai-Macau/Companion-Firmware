"""Focused refactor-core verification. No firmware build/install or device I/O."""
from pathlib import Path
import hashlib,json,subprocess,sys
from verify_wba_spi_nor_adapter import find_vsdevcmd

root=Path(__file__).resolve().parents[1]
out=Path(sys.argv[1]).resolve();out.mkdir(parents=True,exist_ok=False)
rec=root/'app/companion_pendant/recording'
sources=[rec/(n+'.c') for n in ['companion_range_receipt','companion_range_reclaim','companion_segment_audio','companion_segment_catalog']]
test=rec/'tests/test_companion_range_reclaim.c'
args=['cl.exe','/nologo','/W4','/WX','/std:c11','/TC','/O2','/MD','/I'+str(rec),str(test),*[str(p) for p in sources],'/Fe:'+str(out/'range_reclaim.exe')]
cmd=out/'compile.cmd'
cmd.write_text('@echo off\ncall "'+str(find_vsdevcmd())+'" -arch=amd64 -host_arch=amd64 >nul\nif errorlevel 1 exit /b %errorlevel%\n'+subprocess.list2cmdline(args)+'\n',encoding='ascii')
for name,command in [('compile',['cmd.exe','/d','/c',str(cmd)]),('range_reclaim',[str(out/'range_reclaim.exe')])]:
    p=subprocess.run(command,cwd=out,capture_output=True,text=True,encoding='utf-8',errors='replace',creationflags=subprocess.CREATE_NO_WINDOW)
    (out/(name+'.log')).write_text(p.stdout+p.stderr,encoding='utf-8');print(name,p.returncode,p.stdout,p.stderr,flush=True);p.check_returncode()
for source in sources:
    command=['arm-none-eabi-gcc','-std=c11','-mcpu=cortex-m33','-mthumb','-Os','-Wall','-Wextra','-Werror','-Wconversion','-Wshadow','-pedantic','-I'+str(rec),'-c',str(source),'-o',str(out/(source.stem+'.o'))]
    p=subprocess.run(command,cwd=out,capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW)
    (out/(source.stem+'-m33.log')).write_text(p.stdout+p.stderr,encoding='utf-8');print(source.stem,p.returncode,p.stdout,p.stderr,flush=True);p.check_returncode()
legacy=out/'resident-reader';legacy.mkdir()
for name in ['companion_segment_catalog.c','companion_segment_catalog.h','companion_recording_wire.h']:
    content=subprocess.check_output(['git','show','c802756:app/companion_pendant/recording/'+name],cwd=root)
    (legacy/name).write_bytes(content)
(legacy/'verify.c').write_text(r'''
#include "companion_segment_catalog.h"
#include <stdio.h>
static uint8_t media[69632];static unsigned mutations;
static bool rd(void *v,uint32_t at,uint8_t *p,uint32_t n){(void)v;if(at>sizeof(media)||n>sizeof(media)-at)return false;memcpy(p,media+at,n);return true;}
static bool wr(void *v,uint32_t at,const uint8_t *p,uint32_t n){(void)v;(void)at;(void)p;(void)n;mutations++;return false;}
static bool erase(void *v,uint32_t at,uint32_t n,uint32_t *done){(void)v;(void)at;(void)n;(void)done;mutations++;return false;}
int main(int argc,char **argv){
 if(argc!=2)return 1;FILE *f=fopen(argv[1],"rb");if(!f||fread(media,1,sizeof(media),f)!=sizeof(media))return 2;fclose(f);
 uint8_t uid[12];for(unsigned i=0;i<12;i++)uid[i]=(uint8_t)(i+1);
 comp_segment_port_t port={rd,wr,erase,NULL};comp_segment_catalog_t c;comp_segment_entry_t e;
 comp_segment_result_t r=comp_segment_catalog_mount_begin(&c,&port,0,24576,49152,20480,uid,7);
 for(unsigned i=0;i<20000&&r==COMP_SEG_PENDING;i++)r=comp_segment_catalog_mount_poll(&c);
 if(r!=COMP_SEG_OK||mutations||comp_segment_catalog_read(&c,0,&e)!=COMP_SEG_OK||e.state!=COMP_SEG_UNSYNCED||e.descriptor.recording_id!=1)return 3;
 puts("PASS_ACTUAL_RESIDENT_READER original_CSG2_identity_generation_and_extent_mount=1 CRR_extension_safely_skipped=1 no_mutations=1");return 0;
}
''',encoding='utf-8')
args=['cl.exe','/nologo','/W4','/WX','/std:c11','/TC','/O2','/MD','/I'+str(legacy),str(legacy/'verify.c'),str(legacy/'companion_segment_catalog.c'),'/Fe:'+str(out/'resident_reader.exe')]
cmd=out/'resident-compile.cmd';cmd.write_text('@echo off\ncall "'+str(find_vsdevcmd())+'" -arch=amd64 -host_arch=amd64 >nul\nif errorlevel 1 exit /b %errorlevel%\n'+subprocess.list2cmdline(args)+'\n',encoding='ascii')
for name,command in [('resident-compile',['cmd.exe','/d','/c',str(cmd)]),('resident-after-range',[str(out/'resident_reader.exe'),str(out/'range-catalog-after-range.bin')]),('resident-after-rebase',[str(out/'resident_reader.exe'),str(out/'range-catalog-after-rebase.bin')])]:
    p=subprocess.run(command,cwd=out,capture_output=True,text=True,encoding='utf-8',errors='replace',creationflags=subprocess.CREATE_NO_WINDOW)
    (out/(name+'.log')).write_text(p.stdout+p.stderr,encoding='utf-8');print(name,p.returncode,p.stdout,p.stderr,flush=True);p.check_returncode()
(out/'result.json').write_text(json.dumps({'result':'PASS_RANGE_RECLAIM_TRANSACTION_CORE','sourceSha256':{str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [*sources,test,Path(__file__)]},'deviceAccessed':False,'installed':False,'physicalSpeedQualified':False,'catalogAndHostIntegrated':False},indent=2)+'\n')
