"""Actual compact upload phase adapter: nesting, clipping, ownership and overflow."""
from pathlib import Path
import argparse,hashlib,json,subprocess,sys
p=argparse.ArgumentParser();p.add_argument('--source-root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();S=a.source_root.resolve();A=S/'platform/stm32wba55_companion_v11';O=a.output.resolve();O.mkdir(parents=True,exist_ok=False);sys.path.insert(0,str(S/'tools'));from verify_wba_spi_nor_adapter import find_vsdevcmd
t=(A/'cpu_profile_target.c').read_text();storage=t[t.index('typedef struct {uint64_t self_thread_us'):t.index('static comp_cpu_self_ledger_t stage_self;')]
adapter=t.split('/* CPU_TRANSFER_STAGE_MODEL_BEGIN */',1)[1].split('/* CPU_TRANSFER_STAGE_MODEL_END */',1)[0]
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
'''
support=r'''
static comp_cpu_residence_t residence;
static comp_cpu_self_ledger_t stage_self;
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
static void reset(bool transfer,uint32_t token,uint32_t now){now_us=now;transport_capture=transfer;comp_cpu_residence_begin(&residence,token,61439820u,now,true);comp_cpu_self_reset(&stage_self);memset(&observation_stages,0,sizeof(observation_stages));}
'''
post=r'''
int main(void){
 _Static_assert(sizeof(bulk_phase_stats_t)<=sizeof(stage_stats)&&sizeof(observation_stages)==120u,"existing120B observation storage");
 reset(true,7u,1000u);comp_cpu_stage_span_t product=comp_v11_cpu_transfer_stage_begin();
 now_us=1100u;comp_cpu_stage_span_t hal=comp_v11_cpu_transfer_stage_begin();
 now_us=1200u;comp_cpu_stage_span_t inputs=comp_cpu_detail_begin();
 now_us=1210u;comp_cpu_residence_irq_enter(&residence,now_us,true);now_us=1230u;comp_cpu_residence_irq_exit(&residence,now_us,true);
 now_us=1300u;comp_cpu_detail_end(COMP_CPU_STAGE_HAL_INPUTS,inputs,true);
 now_us=1400u;comp_v11_cpu_transfer_stage_end(COMP_BULK_CPU_HAL,hal);
 now_us=1500u;comp_cpu_stage_span_t seq=comp_cpu_detail_begin();
 now_us=1600u;comp_cpu_stage_span_t read=comp_v11_cpu_transfer_stage_begin();now_us=1700u;comp_v11_cpu_transfer_stage_end(COMP_BULK_CPU_READ,read);
 now_us=1750u;comp_cpu_stage_span_t pub=comp_v11_cpu_transfer_stage_begin();
 unsigned char before[sizeof(observation_stages)];memcpy(before,&observation_stages,sizeof(before));comp_cpu_self_ledger_t saved=stage_self;
 comp_cpu_stage_end(COMP_CPU_STAGE_OPUS,pub,true);CHECK(!memcmp(before,&observation_stages,sizeof(before))&&!memcmp(&saved,&stage_self,sizeof(saved))&&!cache_ends&&!cache_stops);
 now_us=1800u;comp_v11_cpu_transfer_stage_end(COMP_BULK_CPU_PUBLISH,pub);
 now_us=1850u;comp_cpu_detail_end(COMP_CPU_STAGE_BLE_SEQUENCER,seq,true);
 now_us=1900u;comp_cpu_stage_span_t runtime=comp_cpu_detail_begin();now_us=1950u;comp_cpu_detail_end(COMP_CPU_STAGE_RUNTIME_SERVICE,runtime,true);
 now_us=2000u;comp_cpu_stage_span_t render=comp_cpu_detail_begin();now_us=2100u;comp_cpu_detail_end(COMP_CPU_STAGE_RENDER_SERVICE,render,true);
 now_us=2200u;comp_cpu_residence_end(&residence,now_us,true);
 now_us=900000u;comp_v11_cpu_transfer_stage_end(COMP_BULK_CPU_PRODUCT,product); /* exact2200us closed edge, no live timer */
 CHECK(bulk_phase.cropped==1u&&!bulk_phase.flags&&!stage_self.depth&&!stage_self.invalid);
 CHECK(bulk_phase.self_us[0]==400u&&bulk_phase.self_us[1]==200u&&bulk_phase.self_us[4]==80u);
 CHECK(bulk_phase.self_us[14]==200u&&bulk_phase.self_us[17]==100u&&bulk_phase.self_us[18]==50u&&bulk_phase.self_us[11]==50u&&bulk_phase.self_us[13]==100u);
 uint32_t total=0u;for(unsigned i=0;i<19u;++i)total+=bulk_phase.self_us[i];CHECK(total==1180u&&residence.stats.total_us[0]==1180u&&residence.stats.total_us[1]==20u);
 reset(false,7u,3000u);CHECK(!comp_cpu_detail_begin().token);comp_cpu_stage_span_t rec=comp_cpu_stage_begin();CHECK(rec.token==7u);now_us=3100u;comp_cpu_stage_end(COMP_CPU_STAGE_PDM,rec,true);CHECK(stage_stats[0].thread_us==100u);
 saved=stage_self;comp_v11_cpu_transfer_stage_end(0u,product);CHECK(!memcmp(&saved,&stage_self,sizeof(saved)));
 reset(true,7u,4000u);comp_cpu_stage_span_t current=comp_cpu_detail_begin();saved=stage_self;comp_v11_cpu_transfer_stage_end(0u,product);CHECK(!memcmp(&saved,&stage_self,sizeof(saved)));
 now_us=4100u;comp_cpu_detail_panel_end(current,false,25u);CHECK(bulk_phase.self_us[3]==100u&&!bulk_phase.flags&&!stage_self.depth); /* actual failed work still costs100us, no I/O success inferred */
 reset(true,8u,5000u);seq=comp_cpu_detail_begin();valid_clock=false;comp_cpu_detail_end(14u,seq,true);CHECK(bulk_phase.flags==4u&&stage_self.invalid);valid_clock=true;
 reset(true,9u,UINT32_MAX-30u);seq=comp_cpu_detail_begin();now_us+=80u;comp_cpu_detail_end(14u,seq,true);CHECK(bulk_phase.self_us[14]==80u&&!bulk_phase.flags);
 reset(true,10u,8000u);seq=comp_cpu_detail_begin();bulk_phase.calls[14]=UINT16_MAX;now_us+=100u;comp_cpu_detail_end(14u,seq,true);CHECK(bulk_phase.calls[14]==UINT16_MAX&&bulk_phase.flags==8u&&bulk_phase.self_us[14]==100u&&!stage_self.invalid);
 reset(true,11u,9000u);seq=comp_cpu_detail_begin();bulk_phase.self_us[14]=UINT32_MAX-5u;now_us+=100u;comp_cpu_detail_end(14u,seq,true);CHECK(bulk_phase.self_us[14]==UINT32_MAX-5u&&(bulk_phase.flags&2u));
 reset(true,12u,10000u);seq=comp_cpu_detail_begin();now_us+=2000001u;comp_cpu_detail_end(14u,seq,true);CHECK(bulk_phase.flags&1u);
 reset(true,13u,20000u);product=comp_v11_cpu_transfer_stage_begin();
 for(unsigned i=0u;i<100000u;++i){now_us+=1u;comp_cpu_stage_span_t cheap=comp_cpu_detail_begin();now_us+=1u;comp_cpu_detail_end(COMP_CPU_STAGE_CAPTURE_PROGRESS,cheap,true);}
 comp_v11_cpu_transfer_stage_end(COMP_BULK_CPU_PRODUCT,product);comp_cpu_residence_end(&residence,now_us,true);
 CHECK(bulk_phase.calls[8]==UINT16_MAX&&bulk_phase.flags==8u&&!stage_self.invalid&&!stage_self.depth);
 CHECK(bulk_phase.self_us[8]==100000u&&bulk_phase.self_us[0]==100000u&&residence.stats.total_us[0]==200000u);
 printf("PASS count metadata saturation at100000 calls preserves200000us exact nesting and total; ");
 printf("PASS actual19-phase adapter and actualdetail hooks; storage120B unchanged; 1200us=1180self+20irq; closed-edge crop excludes late return; recording/domain/cache isolation; failed-I/O duration; wrap and count/sum/clock/long-window overflow explicit\n");return 0;
}
'''
f=O/'test.c';f.write_text(pre+storage+support+adapter+post,encoding='utf-8');args=['cl.exe','/nologo','/TC','/std:c11','/O2','/W4','/WX','/utf-8','/I'+str(A),'/I'+str(S/'app/companion_pendant/recording'),str(f),'/Fe:'+str(O/'test.exe')]
cmd=O/'compile.cmd';cmd.write_text('@echo off\ncall "'+str(find_vsdevcmd())+'" -arch=amd64 -host_arch=amd64 >nul\nif errorlevel 1 exit /b %errorlevel%\n'+subprocess.list2cmdline(args)+'\n');v=subprocess.run(['cmd.exe','/d','/c',str(cmd)],cwd=O,capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW);(O/'build.log').write_text(v.stdout+v.stderr);assert v.returncode==0,(v.stdout+v.stderr)[-4000:]
v=subprocess.run([str(O/'test.exe')],cwd=O,capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW);(O/'result.log').write_text(v.stdout+v.stderr);assert v.returncode==0,(v.stdout+v.stderr)[-4000:]
d=dict(result='PASS_SOURCE_BOUND_COMPACT_UPLOAD_PHASES_AND_REAL_DETAIL_HOOKS',adapterSha256=hashlib.sha256((storage+adapter).encode()).hexdigest(),output=v.stdout,hardwareTimingVerified=False,rateQualified=False);(O/'result.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d))
