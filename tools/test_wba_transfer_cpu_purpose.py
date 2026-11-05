"""Exercise actual target ownership functions with an independent time ledger."""
from pathlib import Path
import argparse,hashlib,json,subprocess,sys
p=argparse.ArgumentParser();p.add_argument('--source-root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
S=a.source_root.resolve();A=S/'platform/stm32wba55_companion_v11';O=a.output.resolve();O.mkdir(parents=True,exist_ok=False)
sys.path.insert(0,str(S/'tools'));from verify_wba_spi_nor_adapter import find_vsdevcmd
t=(A/'cpu_profile_target.c').read_text()
adapter=t.split('/* CPU_TRANSFER_MODEL_BEGIN */',1)[1].split('/* CPU_TRANSFER_MODEL_END */',1)[0]
def function(name):
    start=t.index('void '+name+'(');end=t.index('{',start);depth=1;end+=1
    while depth:
        depth+=int(t[end]=='{')-int(t[end]=='}');end+=1
    return t[start:end]
adapter+='\n'+function('comp_v11_cpu_capture_begin')+'\n'+function('comp_v11_cpu_capture_end')
pre=r'''
#include "cpu_residence.h"
#include <stdio.h>
#include <string.h>
#define CHECK(x) do{if(!(x)){fprintf(stderr,"FAIL line %d %s\n",__LINE__,#x);return 1;}}while(0)
#define COMPANION_WBA_EXPERIMENTAL_STOP1 0
static comp_cpu_residence_t residence;
static bool transport_capture;
static struct{bool owned_off,armed;}cache_trial;
static uint32_t panel_bytes,outer_irq,codec_irq,codec_cache,stage_stats[2],opus_over_budget[3],stage_self;
static uint32_t ipsr,primask,now_us,SystemCoreClock=61439820u;
static uint32_t starts,stops,cache_begins,cache_restores,self_finishes;
static bool timer_ok=true,clock_ok=true,timer_owned;
static uint32_t __get_IPSR(void){return ipsr;}
static uint32_t __get_PRIMASK(void){return primask;}
static void __disable_irq(void){primask=1u;}
static void __set_PRIMASK(uint32_t v){primask=v;}
static bool timer_start(void){++starts;timer_owned=timer_ok;return timer_ok;}
static void timer_stop(void){++stops;timer_owned=false;}
static bool stamp(bool systick,uint32_t*out){(void)systick;*out=now_us;return timer_owned&&clock_ok;}
static void reference(uint32_t now){comp_cpu_residence_reference(&residence,now,now/1000u,true);}
static void cache_trial_begin(uint32_t token){(void)token;++cache_begins;cache_trial.armed=false;}
static void cache_trial_restore(void){++cache_restores;cache_trial.owned_off=false;}
static void codec_cache_stop_owned(void){}
static void comp_cpu_self_reset(uint32_t*p){*p=0u;}
static void comp_cpu_self_finish(uint32_t*p){(void)p;++self_finishes;}
'''
post=r'''
int main(void){
 stage_stats[0]=77u;cache_trial.armed=true;
 comp_v11_cpu_transfer_begin(0u);CHECK(!starts&&!residence.active);
 ipsr=16u;comp_v11_cpu_transfer_begin(7u);CHECK(!starts);ipsr=0u;
 cache_trial.owned_off=true;comp_v11_cpu_transfer_begin(7u);CHECK(!starts&&cache_trial.armed);cache_trial.owned_off=false;
 comp_v11_cpu_capture_begin(42u);CHECK(residence.active&&!transport_capture&&cache_begins==1u);
 comp_cpu_residence_t before=residence;uint32_t count=starts;
 comp_v11_cpu_transfer_begin(7u);CHECK(!memcmp(&before,&residence,sizeof(before))&&starts==count);
 comp_v11_cpu_transfer_end();CHECK(residence.active&&residence.stats.token==42u);
 comp_v11_cpu_capture_end(41u);CHECK(residence.active);
 comp_v11_cpu_capture_end(42u);CHECK(!residence.active&&!timer_owned&&cache_restores==1u&&self_finishes==1u);
 cache_trial.armed=true;stage_stats[0]=77u;now_us=1000u;
 comp_v11_cpu_transfer_begin(7u);CHECK(residence.active&&transport_capture&&residence.stats.token==7u&&cache_trial.armed);
 CHECK(stage_stats[0]==77u&&cache_begins==1u&&cache_restores==1u);
 comp_v11_cpu_capture_end(7u);CHECK(residence.active&&timer_owned); /* same numeric token, different owner */
 now_us=1030u;comp_cpu_residence_wait(&residence,now_us,true,true);
 now_us=1070u;comp_cpu_residence_irq_enter(&residence,now_us,true);
 now_us=1090u;comp_cpu_residence_irq_exit(&residence,now_us,true);
 now_us=1110u;comp_cpu_residence_wait(&residence,now_us,true,false);
 now_us=1130u;comp_v11_cpu_transfer_end();
 CHECK(!residence.active&&!timer_owned&&transport_capture&&primask==0u);
 CHECK(residence.stats.total_us[0]==50u&&residence.stats.total_us[1]==20u&&residence.stats.total_us[2]==60u);
 CHECK(!residence.stats.clock_errors&&!residence.stats.order_errors&&cache_trial.armed&&cache_begins==1u&&cache_restores==1u);
 count=stops;comp_v11_cpu_transfer_end();CHECK(stops==count);
 now_us=2000u;comp_v11_cpu_transfer_begin(8u);CHECK(residence.active&&transport_capture);
 now_us=2020u;comp_v11_cpu_capture_begin(99u);CHECK(residence.active&&!transport_capture&&residence.stats.token==99u&&cache_begins==2u);
 before=residence;comp_v11_cpu_transfer_end();CHECK(!memcmp(&before,&residence,sizeof(before)));
 comp_v11_cpu_capture_end(99u);CHECK(!residence.active&&self_finishes==2u);
 timer_ok=false;now_us=3000u;comp_v11_cpu_transfer_begin(9u);CHECK(residence.active&&transport_capture&&!timer_owned&&residence.stats.clock_errors==1u);
 comp_v11_cpu_transfer_end();CHECK(!residence.active&&residence.stats.clock_errors>=1u);timer_ok=true;
 now_us=UINT32_MAX-40u;comp_v11_cpu_transfer_begin(10u);now_us+=80u;comp_v11_cpu_transfer_end();CHECK(residence.stats.total_us[0]==80u&&!residence.stats.clock_errors);
 now_us=4000u;comp_v11_cpu_transfer_begin(11u);clock_ok=false;now_us+=100u;comp_v11_cpu_transfer_end();CHECK(residence.stats.clock_errors>0u&&!residence.active);clock_ok=true;
 printf("PASS actual transfer/capture purpose ownership; 130us exclusive partition=50thread+20irq+60wfi; cache trial retained; no stage mutation; capture preempts; refused timer/invalid clock/wrap explicit\n");return 0;
}
'''
f=O/'test.c';f.write_text(pre+adapter+post,encoding='utf-8')
args=['cl.exe','/nologo','/TC','/std:c11','/O2','/W4','/WX','/utf-8','/I'+str(A),str(f),'/Fe:'+str(O/'test.exe')]
cmd=O/'compile.cmd';cmd.write_text('@echo off\ncall "'+str(find_vsdevcmd())+'" -arch=amd64 -host_arch=amd64 >nul\nif errorlevel 1 exit /b %errorlevel%\n'+subprocess.list2cmdline(args)+'\n')
v=subprocess.run(['cmd.exe','/d','/c',str(cmd)],cwd=O,capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW);(O/'build.log').write_text(v.stdout+v.stderr);assert v.returncode==0,(v.stdout+v.stderr)[-4000:]
v=subprocess.run([str(O/'test.exe')],cwd=O,capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW);(O/'result.log').write_text(v.stdout+v.stderr);assert v.returncode==0,(v.stdout+v.stderr)[-4000:]
result=dict(result='PASS_ACTUAL_TRANSFER_CPU_PURPOSE_SOURCE_MODEL',adapterSha256=hashlib.sha256(adapter.encode()).hexdigest(),output=v.stdout,hardwareTimingVerified=False,rateQualified=False)
(O/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
