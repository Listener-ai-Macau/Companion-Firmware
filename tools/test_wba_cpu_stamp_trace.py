from pathlib import Path
import sys,argparse,subprocess,json,hashlib
p=argparse.ArgumentParser();p.add_argument('--source-root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--output',type=Path,required=True);a=p.parse_args();S=a.source_root.resolve();A=S/'platform/stm32wba55_companion_v11';sys.path.insert(0,str(S/'tools'))
from verify_wba_spi_nor_adapter import find_vsdevcmd
out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
code=r'''
#include "cpu_stamp_trace.h"
#include <stdio.h>
#include <string.h>
#define CHECK(x) do{if(!(x)){fprintf(stderr,"FAIL line %d %s\n",__LINE__,#x);return 1;}}while(0)
int main(void){comp_cpu_stamp_trace_t t={0};comp_cpu_stamp_sample_t a={1u,61438u,1000u,900u,2u,61439820u},b={2u,61438u,1100u,1000u,0x2400u,61439820u};
 comp_cpu_stamp_trace_note(&t,&a,10000u);CHECK(t.have&&!t.captured&&t.events==0u);
 comp_cpu_stamp_trace_note(&t,&b,9992u);CHECK(t.captured&&t.events==1u&&t.before_us==10000u&&t.after_us==9992u&&!memcmp(&t.before,&a,sizeof(a))&&!memcmp(&t.after,&b,sizeof(b)));
 b.v1=123u;CHECK(t.after.v1==1100u);comp_cpu_stamp_trace_note(&t,&b,9980u);CHECK(t.events==2u&&t.after_us==9992u);
 t.events=UINT32_MAX;comp_cpu_stamp_trace_note(&t,&b,9970u);CHECK(t.events==UINT32_MAX);
 memset(&t,0,sizeof(t));comp_cpu_stamp_trace_note(&t,&a,UINT32_MAX-4u);comp_cpu_stamp_trace_note(&t,&b,10u);CHECK(t.events==0u&&!t.captured&&t.last_us==10u);
 comp_cpu_stamp_trace_note(&t,&a,10u);CHECK(t.events==0u&&t.last_us==10u);
 printf("PASS_RAW_CLOCK_TRACE sizeof=%zu first-pair-retained/no-clamp/no-counter-or-clock-write/wrap/saturation\n",sizeof(t));return 0;}
'''
f=out/'test.c';f.write_text(code,encoding='utf-8');args=['cl.exe','/nologo','/TC','/std:c11','/O2','/W4','/WX','/utf-8','/I'+str(A),str(f),'/Fe:'+str(out/'test.exe')];cmd=out/'compile.cmd';cmd.write_text('@echo off\ncall "'+str(find_vsdevcmd())+'" -arch=amd64 -host_arch=amd64 >nul\nif errorlevel 1 exit /b %errorlevel%\n'+subprocess.list2cmdline(args)+'\n');r=subprocess.run(['cmd.exe','/d','/c',str(cmd)],cwd=out,capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW);(out/'build.log').write_text(r.stdout+r.stderr);assert r.returncode==0,(r.stdout+r.stderr)[-3000:]
r=subprocess.run([str(out/'test.exe')],cwd=out,capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW);(out/'result.log').write_text(r.stdout+r.stderr);assert r.returncode==0,(r.stdout+r.stderr)[-3000:];record={'result':'PASS_SOURCE_HEADER_MODEL_ONLY','output':r.stdout,'sourceSha256':hashlib.sha256((A/'cpu_stamp_trace.h').read_bytes()).hexdigest(),'hardwareClockRepair':False};(out/'result.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record))
