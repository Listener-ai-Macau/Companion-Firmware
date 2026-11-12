"""Check real compact-counter function envelopes, nesting and lifetime."""
from pathlib import Path
import ast,argparse,subprocess,json,re
from verify_wba_spi_nor_adapter import find_vsdevcmd
p=argparse.ArgumentParser();p.add_argument("--output",type=Path,required=True);args=p.parse_args()
root=Path(__file__).resolve().parents[1];out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
old=ast.parse((root/"tools/test_wba_cpu_duty.py").read_text())
pre=next(ast.literal_eval(n.value)for n in old.body if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id=="prelude"for t in n.targets))
pre=pre.replace('static void __WFI(void){assert(mask==1u||!timer_on);tim.CNT+=1000u;dwt.CYCCNT+=100u;}','static void __WFI(void){}')
extra=r"""
#include <string.h>
#include "companion_cpu_stage.h"
static struct {uint32_t APB1LFZR;} debug_registers;
#define DBGMCU (&debug_registers)
#define DBGMCU_APB1LFZR_DBG_TIM2_STOP 1u
static unsigned writes;static char output[4096];
bool comp_v11_hal_debug_write(const char *text){++writes;strncat(output,text,sizeof(output)-strlen(output)-1u);return true;}
"""
target=root/"platform/stm32wba55_companion_v11"
src=(target/"cpu_duty_target.c").read_text().replace('#include "stm32wbaxx_hal.h"','').replace('#include "clock_target.h"','')
tests=r"""
static void fixture_reset(void){
 memset(&observer,0,sizeof(observer));memset(function_stages,0,sizeof(function_stages));
 memset(&tim,0,sizeof(tim));memset(&rcc,0,sizeof(rcc));memset(&debug_registers,0,sizeof(debug_registers));
 RTC->SSR=UINT32_MAX;mask=ipsr=timer_on=sleep_on=timer_irq=resets=0;rtc_valid=true;
 writes=0;output[0]=0;function_report_pending=false;
}
int main(void){
 fixture_reset();assert(!comp_cpu_duty_span_begin().token);
 comp_cpu_duty_begin(7,false);assert(observer.active&&timer_on&&!sleep_on&&!mask);
 TIM2->CNT=10;comp_cpu_duty_span_t a=comp_cpu_duty_span_begin();
 TIM2->CNT=110;comp_cpu_duty_span_end(COMP_DUTY_INPUT_STATUS,a);
 assert(function_stages[COMP_DUTY_INPUT_STATUS].calls==1&&function_stages[COMP_DUTY_INPUT_STATUS].ticks==100);
 TIM2->CNT=120;a=comp_cpu_duty_span_begin();TIM2->CNT=130;comp_cpu_duty_span_t b=comp_cpu_duty_span_begin();
 TIM2->CNT=180;comp_cpu_duty_span_end(COMP_DUTY_BLE,b);TIM2->CNT=200;comp_cpu_duty_span_end(COMP_DUTY_PRODUCT,a);
 assert(function_stages[COMP_DUTY_PRODUCT].ticks==80&&function_stages[COMP_DUTY_BLE].ticks==50);
 TIM2->CNT=UINT32_MAX-5u;a=comp_cpu_duty_span_begin();TIM2->CNT=25;
 comp_cpu_duty_span_end(COMP_DUTY_FUSION,a);assert(function_stages[COMP_DUTY_FUSION].ticks==31);
 ipsr=16;assert(!comp_cpu_duty_span_begin().token);comp_cpu_duty_span_end(COMP_DUTY_FUSION,a);
 assert(function_stages[COMP_DUTY_FUSION].calls==1);ipsr=0;
 /* Compact audio uses only the existing PDM/Opus/NOR hooks, with no detailed
  * capture-checkpoint spans or changing the normal encoder/storage paths. */
 for(unsigned i=0u;i<3u;++i){
  comp_cpu_stage_span_t audio=comp_cpu_stage_begin();TIM2->CNT+=11u+i;
  comp_cpu_stage_end(i,audio,true);
  assert(function_stages[COMP_DUTY_PDM+i].calls==1u&&function_stages[COMP_DUTY_PDM+i].ticks==11u+i);
 }
 assert(!comp_cpu_detail_begin().token);
 comp_cpu_duty_poll();assert(function_stages[COMP_DUTY_OBSERVER].calls==1u);
 ipsr=16;TIM2->CNT=200;comp_cpu_duty_irq_enter();TIM2->CNT=210;comp_cpu_duty_irq_enter();
 TIM2->CNT=230;comp_cpu_duty_irq_exit();TIM2->CNT=240;comp_cpu_duty_irq_exit();ipsr=0;
 assert(irq_summary.ticks==40u&&irq_summary.calls==1u&&!irq_summary.depth&&!mask);
 irq_summary.waiting=true;ipsr=16;TIM2->CNT=250;comp_cpu_duty_irq_enter();TIM2->CNT=270;comp_cpu_duty_irq_exit();ipsr=0;irq_summary.waiting=false;
 assert(irq_summary.ticks==60u&&irq_summary.wfi_ticks==20u&&irq_summary.calls==2u);
 a=comp_cpu_duty_span_begin();comp_cpu_duty_emit();assert(!writes);
 TIM2->CNT=1000000;RTC->SSR=UINT32_MAX-1024u;comp_cpu_duty_end(0,false);
 assert(!observer.active&&!timer_on&&!observer.duty.invalid);
 comp_cpu_duty_span_end(COMP_DUTY_FUSION,a);assert(function_stages[COMP_DUTY_FUSION].calls==1);
 comp_cpu_duty_emit();assert(writes==COMP_DUTY_STAGE_COUNT+2u&&strstr(output,"nested_rows_overlap=1")&&strstr(output,"stage=2 calls=1")&&strstr(output,"CPU2 IRQ"));
 unsigned previous=writes;comp_cpu_duty_emit();assert(writes==previous);
 comp_cpu_duty_begin(8,false);TIM2->CNT=100;comp_cpu_duty_span_end(COMP_DUTY_INPUT_STATUS,a);
 assert(!function_stages[COMP_DUTY_INPUT_STATUS].calls);
 fixture_reset();timer_on=1;TIM2->CNT=444;comp_cpu_duty_begin(9,false);
 assert(observer.duty.invalid&&!observer.timer_owned&&!comp_cpu_duty_span_begin().token&&TIM2->CNT==444&&!resets);
 puts("PASS compact function-envelope exact source: raw counter/wrap, inclusive nesting, ISR exclusion, no active UART, same-scope stop/renewal, foreign timer retained. No physical qualification.");
}
"""
model=out/"model.c";model.write_text(re.sub(r"\bmask\b","fixture_mask",pre)+extra+src+re.sub(r"\bmask\b","fixture_mask",tests),encoding="utf-8")
cmd=["cl.exe","/nologo","/TC","/std:c11","/O2","/W4","/WX","/wd4100","/wd4505","/D_CRT_SECURE_NO_WARNINGS","/I"+str(target),"/I"+str(root/"app/companion_pendant/recording"),str(model),"/Fe:"+str(out/"test.exe")]
batch=out/"compile.cmd";batch.write_text('@echo off\ncall "'+str(find_vsdevcmd())+'" -arch=amd64 -host_arch=amd64 >nul\nif errorlevel 1 exit /b %errorlevel%\n'+subprocess.list2cmdline(cmd)+'\n')
for name,cmd in [("compile",["cmd","/d","/c",str(batch)]),("run",[str(out/"test.exe")])]:
 r=subprocess.run(cmd,cwd=out,capture_output=True,text=True,encoding="utf-8",errors="replace");(out/(name+".log")).write_text(r.stdout+r.stderr);print(name,r.returncode,r.stdout+r.stderr);r.check_returncode()
(out/"result.json").write_text(json.dumps({"result":"PASS_REAL_COMPACT_FUNCTION_ENVELOPE_MODEL","softwareOnly":True})+"\n")
