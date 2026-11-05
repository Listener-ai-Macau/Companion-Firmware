"""Exercise production IRQ hooks and ledger with an explicit clock/NVIC port.

This verifies envelope attribution, not physical IRQ timing or CPU margin.
"""
from pathlib import Path
import argparse, hashlib, json, os, re, subprocess

HARNESS=r'''
#include <assert.h>
#include <stdio.h>
#include "cpu_residence.h"
#include "cpu_codec_irq.h"
#define CPU_HOOK
enum {HASH_IRQn=61,RADIO_IRQn=66};
static comp_cpu_residence_t residence;
static struct {bool owned;} codec_cache;
static uint32_t clock_us,exception;
static bool clock_valid=true;
static unsigned witnesses;
static uint32_t __get_PRIMASK(void){return 0u;}
static void __disable_irq(void){}
static void __set_PRIMASK(uint32_t mask){assert(mask==0u);}
static uint32_t __get_IPSR(void){return exception;}
static bool stamp(bool tick,uint32_t*now){(void)tick;*now=clock_us;return clock_valid;}
static void comp_v11_reset_witness_irq_enter(void){++witnesses;}
static void comp_v11_reset_witness_irq_exit(void){++witnesses;}
#include "actual_hooks.inc"
static void enter(uint32_t at,uint32_t kind){clock_us=at;exception=kind;comp_v11_cpu_irq_enter(false);}
static void leave(uint32_t at){clock_us=at;comp_v11_cpu_irq_exit();}
int main(void){
    assert(sizeof(outer_irq)+sizeof(codec_irq)==36u);
    comp_cpu_residence_begin(&residence,1u,61440000u,0u,true);
    codec_cache.owned=true;comp_cpu_codec_irq_frame_begin(&codec_irq);
    /* A tick nested inside the radio's software IRQ is included once. */
    enter(10u,77u);enter(50u,15u);leave(80u);leave(110u);
    /* A radio nested inside a non-radio outer belongs to that outer
     * envelope. The diagnostic explicitly says exclusive=0. */
    enter(120u,45u);enter(121u,82u);leave(125u);leave(140u);
    enter(144u,82u);leave(184u);
    assert(residence.stats.total_us[COMP_CPU_IRQ]==160u);
    assert(codec_irq.current_radio_us==140u);
    assert(codec_irq.current_us==100u&&codec_irq.current_kind==77u);
    comp_cpu_codec_irq_peak(&codec_irq);
    assert(codec_irq.peak_radio_us==140u&&codec_irq.peak_us==100u);
    assert(residence.stats.total_us[COMP_CPU_IRQ]-codec_irq.peak_radio_us==20u);
    assert(residence.stats.nested_entries==2u&&residence.stats.order_errors==0u);
    /* A subsequent short frame cannot erase the saved peak. */
    comp_cpu_codec_irq_frame_begin(&codec_irq);
    enter(200u,45u);leave(220u);
    assert(codec_irq.current_radio_us==0u&&codec_irq.peak_radio_us==140u);
    /* An equal/new peak snapshots this frame alone, including a zero split. */
    comp_cpu_codec_irq_peak(&codec_irq);
    assert(codec_irq.peak_radio_us==0u&&codec_irq.peak_us==20u&&codec_irq.peak_kind==45u);
    codec_cache.owned=false;enter(230u,77u);leave(290u);
    assert(codec_irq.current_radio_us==0u&&codec_irq.current_us==20u);
    /* An invalid outer timestamp is not added to the attribution. */
    codec_cache.owned=true;enter(300u,77u);clock_valid=false;leave(330u);
    assert(codec_irq.current_radio_us==0u&&residence.stats.clock_errors==1u);
    clock_valid=true;
    /* Unsuitable accumulations stay visibly invalid, never wrap to fast. */
    codec_irq.current_radio_us=UINT32_MAX-2u;
    comp_cpu_codec_irq_note_outer(&codec_irq,4u,77u,true);
    assert(codec_irq.current_radio_us==UINT32_MAX);
    assert(witnesses==16u);
    puts("PASS: real IRQ hooks/ledger; nested envelopes counted once, same-frame radio/complement, retained peak, non-owned/invalid clocks, saturating invalid accumulation");
}
'''

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
    root=Path(__file__).resolve().parents[1];out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
    platform=root/'platform/stm32wba55_companion_v11';src=(platform/'cpu_profile_target.c').read_text()
    outer=re.search(r'static struct \{uint32_t entered,max_us,max_at;uint16_t kind,max_kind;\} outer_irq;',src).group(0)
    begin=src.index('CPU_HOOK void comp_v11_cpu_irq_enter(');end=src.index('CPU_HOOK void comp_v11_cpu_wait_enter(',begin)
    actual=outer+'\nstatic comp_cpu_codec_irq_t codec_irq;\n'+src[begin:end]
    assert 'residence.irq_depth==1u && valid'in actual
    assert 'RADIO_IRQn+16u'in actual and 'HASH_IRQn+16u'in actual
    assert '"OCACHE3 token='in src and 'exclusive=0'in src
    assert 'comp_cpu_codec_irq_peak(&codec_irq);'in src and 'comp_cpu_codec_irq_frame_begin(&codec_irq);'in src
    (out/'actual_hooks.inc').write_text(actual);(out/'test.c').write_text(HARNESS)
    vc=Path(r'C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat')
    cmd=['cl.exe','/nologo','/std:c11','/W4','/WX',f'/I{platform}',str(out/'test.c'),f'/Fe:{out/"test.exe"}']
    script=out/'build.cmd';script.write_text('@echo off\ncall "'+str(vc)+'" >nul\nif errorlevel 1 exit /b %errorlevel%\n'+subprocess.list2cmdline(cmd)+'\n')
    build=subprocess.run([os.environ.get('COMSPEC','cmd.exe'),'/d','/c',str(script)],cwd=out,capture_output=True)
    (out/'build.log').write_bytes(build.stdout+build.stderr);assert build.returncode==0,(build.stdout+build.stderr).decode(errors='replace')
    run=subprocess.run([str(out/'test.exe')],cwd=out,capture_output=True);(out/'run.log').write_bytes(run.stdout+run.stderr)
    assert run.returncode==0,(run.stdout+run.stderr).decode(errors='replace')
    result=dict(result='PASS_CODEC_RADIO_OUTER_IRQ_SPLIT_MODEL',sourceSha256=hashlib.sha256(src.encode()).hexdigest(),productionHooksSha256=hashlib.sha256(actual.encode()).hexdigest(),stdout=run.stdout.decode(),deviceOperations=0,physicalTimingQualified=False)
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
