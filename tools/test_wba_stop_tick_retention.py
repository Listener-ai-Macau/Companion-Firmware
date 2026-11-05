"""Check actual Stop1 target functions against a declared retained-register model.

Not a clock/peripheral emulator or board acceptance. Both the old and new
function bodies run, so the old phase-reset regression remains observable.
"""
from pathlib import Path
import argparse, hashlib, json, runpy, subprocess

STUB=r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include "wba_stop.h"
typedef struct {volatile uint32_t CTRL,LOAD,VAL;} systick_t;
typedef struct {volatile uint32_t CR,CFGR1;} rcc_t;
typedef struct {volatile uint32_t VOSR;} pwr_t;
typedef struct {volatile uint32_t ACR;} flash_t;
typedef struct {volatile uint32_t CR;} ram_t;
static systick_t tick;
static rcc_t rcc;
static pwr_t pwr;
static flash_t flash;
static ram_t ram1,ram2;
#define SysTick (&tick)
#define RCC (&rcc)
#define PWR (&pwr)
#define FLASH (&flash)
#define RAMCFG_SRAM1 (&ram1)
#define RAMCFG_SRAM2 (&ram2)
#define RCC_CR_HSIRDY 1u
#define RCC_CR_HSERDY 2u
#define RCC_CR_PLL1RDY 4u
#define PWR_VOSR_VOSRDY 1u
#define FLASH_ACR_LATENCY 7u
#define FLASH_LATENCY_3 3u
#define RAMCFG_CR_WSC 1u
#define RCC_CFGR1_SWS 3u
#define LL_RCC_SYS_CLKSOURCE_PLL1R 3u
#define LL_RCC_SYS_CLKSOURCE_STATUS_PLL1R 3u
#define LL_PWR_REGU_VOLTAGE_SCALE1 1u
#define RCC_SAI1CLKSOURCE_PLL1P 1u
#define MODIFY_REG(REG,MASK,VALUE) ((REG)=((REG)&~(MASK))|(VALUE))
#define LL_RCC_HSI_Enable() (rcc.CR|=1u)
#define LL_RCC_HSE_Enable() (rcc.CR|=2u)
#define LL_RCC_HSE_DisablePrescaler() ((void)0)
#define LL_PWR_SetRegulVoltageScaling(x) (pwr.VOSR=(x))
#define __HAL_FLASH_SET_LATENCY(x) (flash.ACR=(x))
#define LL_RCC_PLL1_EnableDomain_PLL1P() ((void)0)
#define LL_RCC_PLL1_EnableDomain_PLL1R() ((void)0)
#define LL_RCC_PLL1_Enable() (rcc.CR|=4u)
#define LL_RCC_SetSysClkSource(x) (rcc.CFGR1=(x))
#define __HAL_RCC_SAI1_CONFIG(x) ((void)(x))
static uint32_t SystemCoreClock=61439820u,uwTick,saved_systick;
static volatile uint8_t stop_stage;
static bool mismatch,pending,locked,abort_entry;
static uint32_t rtc_count,rtc_delta;
static void SystemCoreClockUpdate(void) {if(mismatch)SystemCoreClock=16000000u;}
static bool wait_bit(volatile uint32_t *reg,uint32_t mask,uint32_t expected)
{return (*reg&mask)==expected;}
'''

TEST=r'''
static void advance(uint32_t cycles)
{
    if(!(tick.CTRL&1u)) return;
    /* M33: zero reloads next clock; 1->0 pends. Bulk complete periods are
     * equivalent to stepping individual clocks, not an elapsed-time oracle. */
    uint32_t period=tick.LOAD+1u;
    uint32_t until=tick.VAL?tick.VAL:period;
    if(cycles<until) {if(!tick.VAL)tick.VAL=period;tick.VAL-=cycles;return;}
    cycles-=until;
    if(tick.CTRL&2u)uwTick+=1u+cycles/period;
    uint32_t rest=cycles%period;
    tick.VAL=rest?period-rest:0u;
}
static bool arm_model(void *p,uint32_t ms){(void)p;assert(ms==20u);return true;}
static bool disarm_model(void *p){(void)p;assert(!locked);return true;}
static bool lock_model(void *p){(void)p;locked=true;return !abort_entry;}
static void unlock_model(void *p)
{(void)p;locked=false;if(pending&&(tick.CTRL&2u)){++uwTick;pending=false;}}
static uint32_t rtc_model(void *p){(void)p;return rtc_count;}
static void feed_model(void *p){(void)p;assert(locked&&!(tick.CTRL&1u));}
static bool enter_model(void *p)
{(void)p;assert(locked&&!(tick.CTRL&1u));rtc_count+=rtc_delta;return restore_audio_clock(61439820u,1u,0u,2u);}
static void setup(comp_wba_stop_t *s)
{
    static const comp_wba_stop_ports_t ports={arm_model,disarm_model,lock_model,unlock_model,suspend,resume,rtc_model,enter_model,feed_model};
    tick.CTRL=7u;tick.LOAD=61438u;tick.VAL=0u;uwTick=0u;
    rtc_count=0u;rtc_delta=21u;pending=false;locked=false;abort_entry=false;mismatch=false;SystemCoreClock=61439820u;
    comp_wba_stop_init(s,&ports,NULL,true);
}
int main(void)
{
    uint32_t changed=0u;
    comp_wba_stop_t s;
    for(uint32_t val=0u;val<61439u;++val) {
        setup(&s);tick.VAL=val;uwTick=UINT32_MAX-3u;
        assert(comp_wba_stop_run(&s,true)==COMP_WBA_STOP_COMPLETED);
        changed+=(tick.VAL!=val);
        assert(tick.LOAD==61438u&&tick.CTRL==7u&&uwTick==16u&&!locked);
        assert(flash.ACR==2u&&ram1.CR==1u&&ram2.CR==0u&&SystemCoreClock==61439820u);
    }
    printf("PHASE_CHANGED=%u of61439 retained register values\n",changed);
#if EXPECT_RETAINED
    assert(changed==0u);
#else
    assert(changed==61438u);
#endif
    setup(&s);rtc_delta=1024u;const uint32_t cycles=46079u;
    for(unsigned i=0;i<10000u;++i){advance(cycles);assert(comp_wba_stop_run(&s,true)==COMP_WBA_STOP_COMPLETED);}
    uint32_t expected=10000000u+(uint32_t)(((uint64_t)cycles*10000u)/61439u);
    printf("REPEATED_MODEL actual_ms=%u expected_ms=%u discarded_awake_ms=%u\n",uwTick,expected,expected-uwTick);
#if EXPECT_RETAINED
    assert(uwTick==expected);
#else
    assert(expected-uwTick==7499u);
#endif
    setup(&s);tick.VAL=73u;abort_entry=true;
    assert(comp_wba_stop_run(&s,true)==COMP_WBA_STOP_ABORTED&&tick.VAL==73u&&uwTick==0u&&tick.CTRL==7u);
    setup(&s);tick.VAL=0u;pending=true;
    assert(comp_wba_stop_run(&s,true)==COMP_WBA_STOP_COMPLETED&&uwTick==21u&&!pending);
    setup(&s);tick.VAL=400u;rtc_count=UINT32_MAX-7u;rtc_delta=21u;
    assert(comp_wba_stop_run(&s,true)==COMP_WBA_STOP_COMPLETED&&uwTick==20u);
    setup(&s);rtc_delta=1u;
    for(unsigned i=0;i<1024u;++i)assert(comp_wba_stop_run(&s,true)==COMP_WBA_STOP_COMPLETED);
    assert(uwTick==1000u&&s.fraction==0u);
    setup(&s);mismatch=true;
    assert(comp_wba_stop_run(&s,true)==COMP_WBA_STOP_FAULT&&!s.enabled);
    /* Resume restores the caller's enable/interrupt bits, not always-on. */
    for(uint32_t ctrl=0u;ctrl<8u;++ctrl){tick.CTRL=ctrl;tick.VAL=29u;suspend(NULL);resume(NULL,0u);assert(tick.CTRL==ctrl);}
    puts("PASS modeled aborted entry, late pending tick once, RTC wrap/fraction, clock mismatch, original control ownership");
    puts("SOFTWARE_ONLY: RTC edge quantization, real Stop1 retention/wake/current NOT_QUALIFIED");return 0;
}
'''

def function(source, marker):
    start=source.index(marker);body=source.index('{',start);level=1;end=body+1
    while level:
        level+=(source[end]=='{')-(source[end]=='}');end+=1
    return source[start:end]

def main():
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--baseline',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
    baseline=a.baseline.resolve();candidate=a.source.resolve();power=baseline/'app/companion_pendant/power'
    vc=runpy.run_path(str(baseline/'tools/verify_wba_spi_nor_adapter.py'))['find_vsdevcmd']();assert vc
    results=[]
    for label,path,expected in [('baseline',baseline/'platform/stm32wba55_companion_v11/low_power_target.c',0),('candidate',candidate,1)]:
        text=path.read_text();bodies='\n'.join(function(text,x) for x in ['static bool restore_audio_clock(','static void suspend(','static void resume('])
        c=out/(label+'.c');c.write_text(STUB+bodies+TEST,encoding='utf-8');exe=out/(label+'.exe')
        args=['cl.exe','/nologo','/std:c11','/W4','/WX',f'/DEXPECT_RETAINED={expected}',f'/I{power}',str(c),str(power/'wba_stop.c'),f'/Fe:{exe}']
        script=out/(label+'.cmd');script.write_text('@echo off\ncall "'+str(vc)+'" -arch=amd64 -host_arch=amd64 >nul\nif errorlevel 1 exit /b %errorlevel%\n'+subprocess.list2cmdline(args)+'\n')
        result=subprocess.run(['cmd.exe','/d','/c',str(script)],cwd=out,capture_output=True);(out/(label+'-build.log')).write_bytes(result.stdout+result.stderr);assert result.returncode==0,(label,result.stdout[-2000:],result.stderr[-2000:])
        result=subprocess.run([str(exe)],cwd=out,capture_output=True);(out/(label+'-run.log')).write_bytes(result.stdout+result.stderr);assert result.returncode==0,(label,result.stdout,result.stderr)
        results.append(dict(label=label,source=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),output=result.stdout.decode()))
    report=dict(result='STOP1_RETAINED_SYSTICK_PHASE_MODEL_PASS',scope='Actual production restore/suspend/resume bodies and coordinator; modeled MMIO, not MCU emulation or board acceptance',runs=results,installed=False,continuousSleepQualified=False)
    (out/'result.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
