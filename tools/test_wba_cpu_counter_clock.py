from pathlib import Path
import sys,argparse,subprocess,json,hashlib
p=argparse.ArgumentParser();p.add_argument('--source-root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--output',type=Path,required=True);a=p.parse_args();S=a.source_root.resolve();A=S/'platform/stm32wba55_companion_v11';sys.path.insert(0,str(S/'tools'))
from verify_wba_spi_nor_adapter import find_vsdevcmd
out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
target=(A/'cpu_profile_target.c').read_text();adapter=target.split('/* CPU_TIMER_MODEL_BEGIN */',1)[1].split('/* CPU_TIMER_MODEL_END */',1)[0]
pre=r"""
#include "cpu_counter_clock.h"
#include "ble/ble_micro_observation.h"
#include <stdio.h>
#include <string.h>
#define CHECK(x) do{if(!(x)){fprintf(stderr,"FAIL line %d %s\n",__LINE__,#x);return 1;}}while(0)
typedef struct {uint32_t CR1,DIER,SMCR,CCER,PSC,ARR,EGR,SR,CNT;} tim_t;
typedef struct {uint32_t CFGR2;} rcc_t;
static tim_t tim;static rcc_t rcc;static bool clock_on,sleep_on,nvic_on;
static uint32_t SystemCoreClock=61439820u,pclk=61439820u;
#define TIM2 (&tim)
#define RCC (&rcc)
#define TIM2_IRQn 41
#define TIM_CR1_CEN 1u
#define TIM_EGR_UG 1u
#define RCC_CFGR2_PPRE1 0x70u
#define RCC_CFGR2_HPRE 0xfu
#define RCC_HCLK_DIV1 0u
#define NVIC_GetEnableIRQ(x) ((void)(x),nvic_on)
#define HAL_RCC_GetPCLK1Freq() pclk
#define __HAL_RCC_TIM2_IS_CLK_ENABLED() clock_on
#define __HAL_RCC_TIM2_IS_CLK_SLEEP_ENABLED() sleep_on
#define __HAL_RCC_TIM2_CLK_ENABLE() (clock_on=true)
#define __HAL_RCC_TIM2_CLK_DISABLE() (clock_on=false)
#define __HAL_RCC_TIM2_CLK_SLEEP_ENABLE() (sleep_on=true)
#define __HAL_RCC_TIM2_CLK_SLEEP_DISABLE() (sleep_on=false)
#define __HAL_RCC_TIM2_FORCE_RESET() memset(&tim,0,sizeof(tim))
#define __HAL_RCC_TIM2_RELEASE_RESET() ((void)0)
"""
post=r"""
int main(void){
 uint32_t before=comp_v11_ble_micro_stamp(108960u,61438u,43928u,false);
 uint32_t after=comp_v11_ble_micro_stamp(108960u,61438u,61347u,false);
 CHECK(before==108960284u&&after==108960001u&&before-after==283u);
 CHECK(timer_start()&&clock_on&&sleep_on&&timer_config_owned());
 CHECK(TIM2->DIER==0u&&TIM2->CCER==0u&&TIM2->SMCR==0u&&TIM2->PSC==60u);
 uint32_t old=0u,now=0u;CHECK(stamp(false,&old));TIM2->CNT+=722u;CHECK(stamp(false,&now)&&now>old);old=now;
 TIM2->CNT+=100u;CHECK(stamp(true,&now)&&now>old); /* phase flag has no effect */
 timer_stop();CHECK(!clock_on&&!sleep_on&&!cpu_timer.owned&&!cpu_timer.release_refused);
 sleep_on=true;CHECK(timer_start());timer_stop();CHECK(!clock_on&&sleep_on);sleep_on=false;
 clock_on=true;TIM2->CNT=12345u;TIM2->PSC=99u;tim_t saved=tim;CHECK(!timer_start()&&!memcmp(&saved,&tim,sizeof(tim))&&clock_on);clock_on=false;
 nvic_on=true;CHECK(!timer_start()&&!clock_on);nvic_on=false;
 CHECK(timer_start());SystemCoreClock--;CHECK(!stamp(false,&now)&&cpu_timer.rejected==1u);SystemCoreClock++;timer_stop();CHECK(!clock_on);
 CHECK(timer_start());TIM2->DIER=1u;saved=tim;timer_stop();CHECK(cpu_timer.release_refused&&clock_on&&!memcmp(&saved,&tim,sizeof(tim)));clock_on=false;
 memset(&cpu_timer,0,sizeof(cpu_timer));memset(&tim,0,sizeof(tim));rcc.CFGR2=0x10u;pclk=30719910u;CHECK(timer_start()&&cpu_timer.clock.timer_hz==61439820u);timer_stop();rcc.CFGR2=0u;pclk=61439820u;
 const uint32_t frequencies[]={1000000u,16000000u,32768000u,49151856u,61439820u,64000000u,65535808u,98303712u,200000000u};
 uint32_t checks=0u,max_error=0u;
 for(unsigned f=0u;f<sizeof(frequencies)/sizeof(frequencies[0]);++f){
  comp_cpu_counter_clock_t c;CHECK(comp_cpu_counter_clock_init(&c,frequencies[f],UINT32_MAX-500u));
  uint64_t ticks=0u;uint32_t raw=UINT32_MAX-500u;
  uint64_t target_ticks=((uint64_t)frequencies[f]*7200u)/c.divider;
  while(ticks<target_ticks){uint32_t delta=12345u;if(target_ticks-ticks<delta)delta=(uint32_t)(target_ticks-ticks);ticks+=delta;raw+=delta;CHECK(comp_cpu_counter_clock_read(&c,raw,&now));
   uint32_t exact=(uint32_t)((ticks*c.divider*1000000u)/frequencies[f]);int32_t difference=(int32_t)(now-exact);uint32_t error=(uint32_t)(difference<0?-difference:difference);CHECK(error<=3u);if(error>max_error)max_error=error;++checks;
  }
  CHECK(comp_cpu_counter_clock_read(&c,raw,&now));CHECK(!comp_cpu_counter_clock_read(&c,raw+c.max_delta+1u,&now));
 }
 comp_cpu_counter_clock_t c;CHECK(!comp_cpu_counter_clock_init(&c,0u,0u)&&!comp_cpu_counter_clock_init(&c,999999u,0u)&&!comp_cpu_counter_clock_init(&c,200000001u,0u));
 CHECK(timer_start());TIM2->ARR=5u;CHECK(!stamp(false,&now));TIM2->ARR=UINT32_MAX;timer_stop();
 printf("PASS_ACTUAL_TIMER_ADAPTER checks=%lu max_q31_error_us=%lu clock_state=%zu adapter=%zu old283us_reproduced; two-hour-counter-and-us-wrap; ownership/IRQ/WFI-clock/clock-change/release\n",(unsigned long)checks,(unsigned long)max_error,sizeof(c),sizeof(cpu_timer));return 0;
}
"""
f=out/'test.c';f.write_text(pre+adapter+post,encoding='utf-8');args=['cl.exe','/nologo','/TC','/std:c11','/O2','/W4','/WX','/utf-8','/I'+str(A),str(f),'/Fe:'+str(out/'test.exe')];cmd=out/'compile.cmd';cmd.write_text('@echo off\ncall "'+str(find_vsdevcmd())+'" -arch=amd64 -host_arch=amd64 >nul\nif errorlevel 1 exit /b %errorlevel%\n'+subprocess.list2cmdline(args)+'\n');r=subprocess.run(['cmd.exe','/d','/c',str(cmd)],cwd=out,capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW);(out/'build.log').write_text(r.stdout+r.stderr);assert r.returncode==0,(r.stdout+r.stderr)[-4000:]
r=subprocess.run([str(out/'test.exe')],cwd=out,capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW);(out/'result.log').write_text(r.stdout+r.stderr);assert r.returncode==0,(r.stdout+r.stderr)[-4000:];record={'result':'PASS_SOURCE_BOUND_TIMER_MODEL_ONLY','output':r.stdout,'headerSha256':hashlib.sha256((A/'cpu_counter_clock.h').read_bytes()).hexdigest(),'adapterSha256':hashlib.sha256(adapter.encode()).hexdigest(),'systickOldWindowReproduced':True,'hardwareTimerVerified':False,'hardwareRecordingQualified':False};(out/'result.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record))
