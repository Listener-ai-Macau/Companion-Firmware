"""Source-bound nested CPU partition and old/new-purpose late-return checks."""
from pathlib import Path
import argparse,hashlib,json,subprocess,sys
p=argparse.ArgumentParser();p.add_argument('--source-root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();S=a.source_root.resolve();A=S/'platform/stm32wba55_companion_v11';O=a.output.resolve();O.mkdir(parents=True,exist_ok=False)
sys.path.insert(0,str(S/'tools'));from verify_wba_spi_nor_adapter import find_vsdevcmd
t=(A/'cpu_profile_target.c').read_text();adapter=t.split('/* CPU_TRANSFER_STAGE_MODEL_BEGIN */',1)[1].split('/* CPU_TRANSFER_STAGE_MODEL_END */',1)[0]
def function(name,prefix):
 start=t.index(prefix+name+'(');end=t.index('{',start)+1;depth=1
 while depth:depth+=int(t[end]=='{')-int(t[end]=='}');end+=1
 return t[start:end]
adapter+='\n'+function('stage_end_bytes','static void ')+'\n'+function('comp_cpu_stage_end','void ')
pre=r'''
#define COMPANION_WBA_CPU_RESIDENCE_PROFILE 1
#define COMPANION_WBA_CPU_DETAILED_PROFILE 0
#include "cpu_residence.h"
#include "cpu_self_ledger.h"
#include "cpu_profile_target.h"
#include <stdio.h>
#include <limits.h>
#define CHECK(x) do{if(!(x)){fprintf(stderr,"FAIL line %d %s\n",__LINE__,#x);return 1;}}while(0)
typedef struct {uint64_t self_thread_us,thread_us,irq_us;uint32_t calls,max_wall_us,invalid;}stage_stats_t;
static comp_cpu_residence_t residence;
static comp_cpu_self_ledger_t stage_self;
static stage_stats_t stage_stats[3];
static bool transport_capture,valid_clock=true;
static uint32_t now_us,primask,ipsr,cache_ends,cache_stops;
static uint32_t opus_over_budget[3];
static struct{uint64_t all_bytes,wall,irq;uint32_t calls,min,max;uint16_t bytes;}panel_bytes;
static uint32_t __get_IPSR(void){return ipsr;}
static uint32_t __get_PRIMASK(void){return primask;}
static void __disable_irq(void){primask=1u;}
static void __set_PRIMASK(uint32_t v){primask=v;}
static bool stamp(bool entry,uint32_t*out){(void)entry;*out=now_us;return valid_clock;}
static void codec_cache_end(uint32_t wall,uint32_t irq,bool complete){(void)wall;(void)irq;(void)complete;++cache_ends;}
static void codec_cache_stop_owned(void){++cache_stops;}
static void reset(bool transfer,uint32_t token,uint32_t now){now_us=now;transport_capture=transfer;comp_cpu_residence_begin(&residence,token,61439820u,now,true);comp_cpu_self_reset(&stage_self);memset(stage_stats,0,sizeof(stage_stats));}
'''
post=r'''
int main(void){
 reset(true,7u,1000u);comp_cpu_stage_span_t seq=comp_v11_cpu_transfer_stage_begin();CHECK(seq.token==7u&&stage_self.depth==1u);
 CHECK(!comp_cpu_stage_begin().token); /* recording cannot join upload tree */
 now_us=1100u;comp_cpu_residence_irq_enter(&residence,now_us,true);now_us=1120u;comp_cpu_residence_irq_exit(&residence,now_us,true);
 now_us=1200u;comp_cpu_stage_span_t read=comp_v11_cpu_transfer_stage_begin();now_us=1500u;comp_v11_cpu_transfer_stage_end(COMP_BULK_CPU_READ,read);
 now_us=1600u;comp_cpu_stage_span_t publish=comp_v11_cpu_transfer_stage_begin();
 stage_stats_t saved[3];memcpy(saved,stage_stats,sizeof(saved));comp_cpu_self_ledger_t before=stage_self;
 comp_cpu_stage_end(COMP_CPU_STAGE_OPUS,publish,true);CHECK(!memcmp(saved,stage_stats,sizeof(saved))&&!memcmp(&before,&stage_self,sizeof(before))&&!cache_ends&&!cache_stops);
 now_us=1650u;comp_v11_cpu_transfer_stage_end(COMP_BULK_CPU_PUBLISH,publish);now_us=1700u;comp_v11_cpu_transfer_stage_end(COMP_BULK_CPU_SEQ,seq);
 CHECK(stage_stats[0].thread_us==680u&&stage_stats[0].irq_us==20u&&stage_stats[0].self_thread_us==330u);
 CHECK(stage_stats[1].thread_us==300u&&stage_stats[1].self_thread_us==300u&&stage_stats[2].self_thread_us==50u);
 CHECK(stage_stats[0].self_thread_us+stage_stats[1].self_thread_us+stage_stats[2].self_thread_us+stage_stats[0].irq_us==700u);
 CHECK(stage_self.depth==0u&&!stage_self.invalid&&primask==0u);
 reset(false,7u,2000u);CHECK(!comp_v11_cpu_transfer_stage_begin().token);comp_cpu_stage_span_t rec=comp_cpu_stage_begin();CHECK(rec.token==7u);
 before=stage_self;comp_v11_cpu_transfer_stage_end(COMP_BULK_CPU_SEQ,seq);CHECK(!memcmp(&before,&stage_self,sizeof(before)));
 now_us=2100u;comp_cpu_stage_end(COMP_CPU_STAGE_PDM,rec,true);CHECK(stage_stats[0].thread_us==100u&&stage_stats[0].self_thread_us==100u);
 reset(true,7u,3000u);comp_cpu_stage_span_t current=comp_v11_cpu_transfer_stage_begin();before=stage_self;
 comp_v11_cpu_transfer_stage_end(COMP_BULK_CPU_SEQ,seq);CHECK(!memcmp(&before,&stage_self,sizeof(before))&&!stage_stats[0].invalid); /* stale same token/different domain */
 now_us=3100u;comp_v11_cpu_transfer_stage_end(COMP_BULK_CPU_SEQ,current);CHECK(stage_stats[0].calls==1u&&!stage_self.invalid);
 reset(true,8u,4000u);seq=comp_v11_cpu_transfer_stage_begin();valid_clock=false;comp_v11_cpu_transfer_stage_end(0u,seq);CHECK(stage_stats[0].invalid==1u&&stage_self.invalid==1u);valid_clock=true;
 reset(true,9u,UINT32_MAX-30u);seq=comp_v11_cpu_transfer_stage_begin();now_us+=80u;comp_v11_cpu_transfer_stage_end(0u,seq);CHECK(stage_stats[0].thread_us==80u&&!stage_self.invalid);
 reset(true,10u,8000u);seq=comp_v11_cpu_transfer_stage_begin();now_us+=2000001u;comp_v11_cpu_transfer_stage_end(0u,seq);CHECK(stage_stats[0].invalid==1u&&stage_self.invalid==1u);
 printf("PASS actual 3-slot nested stages:700us=330seq-self+300read+50publish+20irq; recording/transfer and stale same-token domain isolated; invalid clocks/wrap/long spans explicit; no cache side effects\n");return 0;
}
'''
f=O/'test.c';f.write_text(pre+adapter+post,encoding='utf-8');args=['cl.exe','/nologo','/TC','/std:c11','/O2','/W4','/WX','/utf-8','/I'+str(A),'/I'+str(S/'app/companion_pendant/recording'),str(f),'/Fe:'+str(O/'test.exe')]
cmd=O/'compile.cmd';cmd.write_text('@echo off\ncall "'+str(find_vsdevcmd())+'" -arch=amd64 -host_arch=amd64 >nul\nif errorlevel 1 exit /b %errorlevel%\n'+subprocess.list2cmdline(args)+'\n');v=subprocess.run(['cmd.exe','/d','/c',str(cmd)],cwd=O,capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW);(O/'build.log').write_text(v.stdout+v.stderr);assert v.returncode==0,(v.stdout+v.stderr)[-4000:]
v=subprocess.run([str(O/'test.exe')],cwd=O,capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW);(O/'result.log').write_text(v.stdout+v.stderr);assert v.returncode==0,(v.stdout+v.stderr)[-4000:]
d=dict(result='PASS_SOURCE_BOUND_UPLOAD_CPU_NESTING_AND_PURPOSE',adapterSha256=hashlib.sha256(adapter.encode()).hexdigest(),output=v.stdout,hardwareTimingVerified=False,rateQualified=False);(O/'result.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d))
