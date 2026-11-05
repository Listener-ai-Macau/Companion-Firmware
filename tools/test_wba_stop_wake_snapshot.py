"""Run the actual target snapshot function against a read-only IRQ model.

Checks the missing radio/EXTI evidence, not real sleep, clocks or current.
"""
from pathlib import Path
import argparse
import hashlib
import json
import runpy
import subprocess


def function(text, marker):
    start = text.index(marker)
    end = text.index('{', start) + 1
    depth = 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    return text[start:end]


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--baseline', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    root = Path(__file__).resolve().parents[1]
    target = root / 'platform/stm32wba55_companion_v11'
    source = (target / 'low_power_target.c').read_text()
    header = (target / 'low_power_target.h').read_text()
    declarations = header[header.index('#define COMP_V11_STOP_IRQ_WORDS'):header.index('const comp_v11_stop_wake_snapshot_t *')]
    body = function(source, 'static void capture_pending_irqs(')
    c = r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
typedef struct {volatile uint32_t ISPR[3],ISER[3];} nvic_t;
typedef struct {volatile uint32_t ICSR;} scb_t;
typedef struct {volatile uint32_t RPR1,FPR1;} exti_t;
static nvic_t nvic;
static scb_t scb;
static exti_t exti;
#define NVIC (&nvic)
#define SCB (&scb)
#define EXTI (&exti)
''' + declarations + body + r'''
int main(void)
{
    comp_v11_stop_wake_snapshot_t sample={0};
    capture_pending_irqs(&sample.before);
    /* A radio IRQ with neither UART RX nor RTC alarm explains why the old
     * two-bit observation can be zero despite a real pending interrupt. */
    nvic.ISPR[2]=1u<<2; nvic.ISER[2]=1u<<2;
    nvic.ISPR[0]=(1u<<25)|(1u<<24); nvic.ISER[0]=1u<<25;
    nvic.ISPR[1]=1u<<24; nvic.ISER[1]=1u<<24;
    scb.ICSR=1u<<26; exti.FPR1=1u<<14; exti.RPR1=1u<<13;
    const nvic_t saved_nvic=nvic; const scb_t saved_scb=scb; const exti_t saved_exti=exti;
    capture_pending_irqs(&sample.after);
    assert(sample.before.pending_enabled[2]==0u);
    assert(sample.after.pending_enabled[0]==(1u<<25));
    assert(sample.after.pending_enabled[1]==(1u<<24));
    assert(sample.after.pending_enabled[2]==(1u<<2));
    assert(sample.after.icsr==(1u<<26));
    assert(sample.after.exti_falling==(1u<<14)&&sample.after.exti_rising==(1u<<13));
    assert(memcmp(&saved_nvic,&nvic,sizeof(nvic))==0);
    assert(memcmp(&saved_scb,&scb,sizeof(scb))==0);
    assert(memcmp(&saved_exti,&exti,sizeof(exti))==0);
    /* IRQ dispatch may clear hardware later; the retained observation stays. */
    memset(&nvic,0,sizeof(nvic)); memset(&exti,0,sizeof(exti)); scb.ICSR=0;
    assert(sample.after.pending_enabled[2]==(1u<<2));
    /* Every supported external IRQ is represented; disabled IRQs are not. */
    for(unsigned irq=0;irq<72u;++irq) {
        nvic.ISPR[irq/32u]=1u<<(irq%32u); nvic.ISER[irq/32u]=0;
        capture_pending_irqs(&sample.after); assert(sample.after.pending_enabled[irq/32u]==0u);
        nvic.ISER[irq/32u]=nvic.ISPR[irq/32u]; capture_pending_irqs(&sample.after);
        assert(sample.after.pending_enabled[irq/32u]==(1u<<(irq%32u)));
        nvic.ISPR[irq/32u]=0; nvic.ISER[irq/32u]=0;
    }
    puts("PASS actual target snapshot: radio/EXTI/multiple pending IRQs, disabled masking, no register mutation, retained after dispatch");
    puts("SOFTWARE_ONLY: historical wake cause, physical STOP1 and current remain unqualified");
    return 0;
}
'''
    out = a.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    cc = out / 'snapshot.c'
    cc.write_text(c, encoding='utf-8')
    vc = runpy.run_path(str(a.baseline.resolve() / 'tools/verify_wba_spi_nor_adapter.py'))['find_vsdevcmd']()
    assert vc
    exe = out / 'snapshot.exe'
    cmd = ['cl.exe', '/nologo', '/std:c11', '/W4', '/WX', str(cc), f'/Fe:{exe}']
    script = out / 'build.cmd'
    script.write_text('@echo off\ncall "'+str(vc)+'" -arch=amd64 -host_arch=amd64 >nul\nif errorlevel 1 exit /b %errorlevel%\n'+subprocess.list2cmdline(cmd)+'\n')
    build = subprocess.run(['cmd.exe', '/d', '/c', str(script)], cwd=out, capture_output=True)
    (out / 'build.log').write_bytes(build.stdout+build.stderr)
    assert build.returncode == 0, build.stdout[-3000:]
    run = subprocess.run([str(exe)], cwd=out, capture_output=True)
    (out / 'run.log').write_bytes(run.stdout+run.stderr)
    assert run.returncode == 0, run.stdout+run.stderr
    report = dict(result='PASS_SOFTWARE_ONLY', source_sha256=hashlib.sha256((target/'low_power_target.c').read_bytes()).hexdigest(), output=run.stdout.decode(), installed=False)
    (out/'result.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__ == '__main__':
    main()
