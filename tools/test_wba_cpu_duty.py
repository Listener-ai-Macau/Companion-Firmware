from pathlib import Path
import json,re,subprocess,sys
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'tools'))
from verify_wba_spi_nor_adapter import find_vsdevcmd
out=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else root/'.cache/cpu-duty-model';out.mkdir(parents=True,exist_ok=False)
target=root/'platform/stm32wba55_companion_v11'
prelude=r'''
#include <assert.h>
#include <stdio.h>
#include <stdbool.h>
#include <stdint.h>
#define COMPANION_WBA_CPU_DUTY_OBSERVER 1
static struct {uint32_t CR1,DIER,SMCR,PSC,ARR,CCER,EGR,SR,CNT;} tim;
static struct {uint32_t CTRL,CYCCNT;} dwt;
static struct {uint32_t DEMCR;} dcb;
static struct {uint32_t CFGR2;} rcc;
static struct {uint32_t SSR;} rtc;
#define TIM2 (&tim)
#define DWT (&dwt)
#define DCB (&dcb)
#define RCC (&rcc)
#define RTC (&rtc)
#define TIM_CR1_CEN 1u
#define TIM_EGR_UG 1u
#define TIM2_IRQn 1u
#define RCC_CFGR2_HPRE 0xFu
#define RCC_CFGR2_PPRE1 0x70u
#define RCC_HCLK_DIV1 0u
#define DWT_CTRL_NOCYCCNT_Msk 0x2000000u
#define DWT_CTRL_CYCCNTENA_Msk 1u
#define DCB_DEMCR_TRCENA_Msk 0x1000000u
#define SET_BIT(reg,bit) ((reg)|=(bit))
#define CLEAR_BIT(reg,bit) ((reg)&=~(bit))
static unsigned mask,ipsr,timer_on,sleep_on,timer_irq,resets;
static bool rtc_valid=true;
uint32_t SystemCoreClock=61439820u;
static uint32_t __get_PRIMASK(void){return mask;}
static uint32_t __get_IPSR(void){return ipsr;}
static void __disable_irq(void){mask=1u;}
static void __set_PRIMASK(uint32_t value){mask=value;}
static void __DSB(void){}
static void __ISB(void){}
static uint32_t HAL_RCC_GetPCLK1Freq(void){return 61439820u;}
static uint32_t NVIC_GetEnableIRQ(unsigned n){(void)n;return timer_irq;}
#define __HAL_RCC_TIM2_IS_CLK_ENABLED() timer_on
#define __HAL_RCC_TIM2_IS_CLK_SLEEP_ENABLED() sleep_on
#define __HAL_RCC_TIM2_CLK_SLEEP_DISABLE() (sleep_on=0u)
#define __HAL_RCC_TIM2_CLK_SLEEP_ENABLE() (sleep_on=1u)
#define __HAL_RCC_TIM2_CLK_ENABLE() (timer_on=1u)
#define __HAL_RCC_TIM2_CLK_DISABLE() (timer_on=0u)
#define __HAL_RCC_TIM2_FORCE_RESET() (++resets)
#define __HAL_RCC_TIM2_RELEASE_RESET() ((void)0)
bool comp_v11_clock_domain_continuous(void){return rtc_valid;}
'''
source=(target/'cpu_duty_target.c').read_text().replace('#include "stm32wbaxx_hal.h"','').replace('#include "clock_target.h"','')
tail=r'''
static void advance(uint32_t us,uint32_t awake_cycles){
    TIM2->CNT+=(uint32_t)(((uint64_t)us*observer.clock.timer_hz)/(observer.clock.divider*1000000u));
    DWT->CYCCNT+=awake_cycles;
    RTC->SSR-=(uint32_t)(((uint64_t)us*1024u)/1000000u);
}
static void fixture_reset(void){
    memset(&observer,0,sizeof(observer));memset(&tim,0,sizeof(tim));
    memset(&dwt,0,sizeof(dwt));memset(&dcb,0,sizeof(dcb));
    memset(&rcc,0,sizeof(rcc));RTC->SSR=UINT32_MAX;
    mask=ipsr=timer_on=sleep_on=timer_irq=resets=0u;rtc_valid=true;SystemCoreClock=61439820u;
}
int main(void){
    comp_cpu_duty_bound_t s={0};comp_cpu_duty_busy(&s,UINT32_MAX-10u,true);
    comp_cpu_duty_account(&s,9u,true,5u);assert(s.window_us==20u&&s.sleep_lower_us==15u);
    comp_cpu_duty_busy(&s,9u+999980u,true);assert(s.windows==1u&&s.peak_busy_upper_us==999985u);
    memset(&s,0,sizeof(s));comp_cpu_duty_busy(&s,0u,true);comp_cpu_duty_busy(&s,999990u,true);
    comp_cpu_duty_account(&s,1000010u,true,8u);
    assert(s.windows==1u&&s.peak_busy_upper_us==999998u&&s.sleep_lower_us==2u);
    comp_cpu_duty_account(&s,2000020u,false,0u);assert(s.invalid==1u&&s.windows==1u&&!s.have_stamp);
    assert(comp_cpu_duty_wait_busy_upper(61440u,61440000u)==1001u);
    assert(comp_cpu_duty_wait_busy_upper(1u,61440000u)==2u);
    assert(comp_cpu_duty_wait_busy_upper(0u,61440000u)==UINT32_MAX);
    /* Independent exact occupancy over100000 mixed busy/sleep spans. Model
     * only knows total possible busy per span, not where it occurs. */
    memset(&s,0,sizeof(s));comp_cpu_duty_busy(&s,0u,true);
    uint32_t seed=7u,time_us=0u,exact_window=0u,exact_busy=0u,exact_peak=0u,exact_windows=0u;
    for(unsigned trial=0;trial<100000u;trial++){
        seed=1664525u*seed+1013904223u;uint32_t length=1u+seed%20000u;
        seed=1664525u*seed+1013904223u;uint32_t busy=seed%(length+1u);
        seed=1664525u*seed+1013904223u;uint32_t prefix=seed%(length-busy+1u);
        uint32_t left=length,position=0u;
        while(left){
            uint32_t n=1000000u-exact_window;if(n>left)n=left;
            uint32_t a=position>prefix?position:prefix,b=position+n<prefix+busy?position+n:prefix+busy;
            if(b>a)exact_busy+=b-a;
            exact_window+=n;position+=n;left-=n;
            if(exact_window==1000000u){if(exact_busy>exact_peak)exact_peak=exact_busy;exact_windows++;exact_window=exact_busy=0u;}
        }
        time_us+=length;comp_cpu_duty_account(&s,time_us,true,busy);
        assert(s.windows==exact_windows&&s.peak_busy_upper_us>=exact_peak&&!s.invalid);
    }
    fixture_reset();comp_cpu_duty_begin(7u,true);assert(observer.active&&timer_on&&sleep_on&&resets==1u&&mask==0u);
    DWT->CTRL=0x100u;DCB->DEMCR=0x80u;DWT->CYCCNT=1234u;mask=1u;
    comp_cpu_duty_wait_enter();assert(observer.cycle_lease&&DWT->CYCCNT==1234u&&DWT->CTRL==0x101u&&DCB->DEMCR==0x1000080u);
    advance(10000u,61440u);uint32_t retained=DWT->CYCCNT;comp_cpu_duty_wait_exit();
    assert(!observer.cycle_lease&&DWT->CTRL==0x100u&&DCB->DEMCR==0x80u&&DWT->CYCCNT==retained&&observer.duty.proven_waits==1u&&mask==1u);
    for(unsigned i=0;i<101u;i++){comp_cpu_duty_wait_enter();advance(10000u,61440u);comp_cpu_duty_wait_exit();}
    assert(observer.duty.windows>=1u&&observer.duty.peak_busy_upper_us<110000u&&!observer.duty.invalid);
    comp_cpu_duty_snapshot_t shot=comp_cpu_duty_snapshot();assert(shot.enabled&&shot.active&&shot.recording&&shot.token==7u);
    comp_cpu_duty_begin(8u,false);assert(observer.token==7u&&observer.recording);
    comp_cpu_duty_end(8u,true);assert(observer.active);
    /* RTC was advanced with a truncated fixture tick per wait; set exact final reference. */
    RTC->SSR=UINT32_MAX-(uint32_t)(((uint64_t)observer.clock.us*1024u)/1000000u);
    comp_cpu_duty_end(7u,true);assert(!observer.active&&!timer_on&&!sleep_on&&!observer.duty.invalid);
    comp_cpu_duty_begin(9u,false);assert(!observer.active&&observer.token==7u);
    fixture_reset();comp_cpu_duty_begin(9u,false);mask=0u;
    for(unsigned i=0;i<102u;i++){comp_cpu_duty_wait_enter();assert(!observer.cycle_lease);advance(10000u,61440u);comp_cpu_duty_wait_exit();}
    assert(observer.duty.windows>=1u&&observer.duty.peak_busy_upper_us==1000000u&&!observer.duty.proven_waits&&!observer.duty.invalid&&mask==0u);
    fixture_reset();comp_cpu_duty_begin(10u,true);mask=1u;DWT->CTRL=0x101u;DCB->DEMCR=0x1000080u;
    comp_cpu_duty_wait_enter();advance(2000u,61440u);comp_cpu_duty_wait_exit();
    assert(DWT->CTRL==0x101u&&DCB->DEMCR==0x1000080u); /* foreign enable bits retained */
    comp_cpu_duty_wait_enter();advance(2000u,0u);comp_cpu_duty_wait_exit();assert(observer.duty.invalid);
    fixture_reset();timer_on=1u;TIM2->CNT=444u;comp_cpu_duty_begin(11u,true);
    assert(observer.duty.invalid&&!observer.timer_owned&&TIM2->CNT==444u&&!resets&&timer_on);
    comp_cpu_duty_wait_enter();comp_cpu_duty_wait_exit();comp_cpu_duty_end(11u,true);assert(timer_on&&!resets);
    fixture_reset();comp_cpu_duty_begin(12u,true);advance(2000001u,1u);comp_cpu_duty_poll();assert(observer.duty.invalid);
    fixture_reset();comp_cpu_duty_begin(13u,true);rtc_valid=false;advance(1000001u,1u);comp_cpu_duty_poll();assert(observer.duty.invalid);
    fixture_reset();comp_cpu_duty_begin(14u,true);mask=1u;comp_cpu_duty_wait_enter();DWT->CTRL=0u;advance(1000u,10u);comp_cpu_duty_wait_exit();assert(observer.duty.invalid);
    puts("PASS actual compact CPU observer source: upper-bound window splitting, quantisation, timer-wrap, disabled/unmasked no false idle, masked-only DWT enable-bit lease with zero counter resets, foreign bits/timer retained, lifecycle scope, clock/error rejection; SOFTWARE ONLY");
    return 0;
}
'''
p=out/'cpu-duty.c'
def fixture_names(text):
    for name in ['mask','rtc']:text=re.sub(r'\b'+name+r'\b','fixture_'+name,text)
    return text
p.write_text(fixture_names(prelude)+source+fixture_names(tail),encoding='utf-8')
command=['cl.exe','/nologo','/std:c11','/W4','/WX','/I'+str(target),'/I'+str(root/'app/companion_pendant/runtime'),str(p),'/Fe:'+str(out/'cpu-duty.exe')]
cmd=out/'build.cmd';cmd.write_text('@echo off\ncall "'+str(find_vsdevcmd())+'" -arch=amd64 -host_arch=amd64 >nul\nif errorlevel 1 exit /b %errorlevel%\n'+subprocess.list2cmdline(command)+'\n')
with(out/'build.log').open('xb')as f:r=subprocess.run(['cmd.exe','/d','/c',str(cmd)],cwd=out,stdout=f,stderr=subprocess.STDOUT)
assert r.returncode==0,(out/'build.log').read_text(errors='replace')[-4000:]
r=subprocess.run([str(out/'cpu-duty.exe')],cwd=out,capture_output=True,text=True);(out/'run.log').write_text(r.stdout+r.stderr,encoding='utf-8');assert r.returncode==0,r.stdout+r.stderr
result={'result':'PASS_COMPACT_CPU_OBSERVER_EXACT_SOURCE_MODEL_ONLY','output':r.stdout,'actualTargetInstalled':False,'cpuDutyPhysicalQualified':False};(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
