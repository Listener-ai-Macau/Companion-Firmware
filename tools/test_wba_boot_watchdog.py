"""Exercise the production boot watchdog routine with clock/register faults.

The C routine is extracted unchanged to isolate it from Flash and boot-jump IO.
Native models are regression evidence, not oscillator or hardware acceptance.
"""
from pathlib import Path
import argparse, hashlib, json, shutil, subprocess
from verify_wba_spi_nor_adapter import find_vsdevcmd

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'platform/stm32wba55_companion_v11/update_boot_target.c'
FAKE = r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#define HAL_OK 0
#define RCC_OSCILLATORTYPE_LSI 1u
#define RCC_LSI1_ON 2u
#define RCC_LSI_DIV1 0u
#define LL_IWDG_PRESCALER_256 6u
#define IWDG ((void *)1)
typedef struct { uint32_t OscillatorType, LSIState, LSIDiv; } RCC_OscInitTypeDef;
static uint32_t tick, busy, reloads, prescaler, counter;
static bool oscillator_failure, register_failure, clock_on, enabled, unlocked;
static int HAL_RCC_OscConfig(const RCC_OscInitTypeDef *config) {
    if (oscillator_failure) return 1;
    clock_on = config->OscillatorType == RCC_OSCILLATORTYPE_LSI &&
        config->LSIState == RCC_LSI1_ON && config->LSIDiv == RCC_LSI_DIV1;
    return clock_on ? HAL_OK : 1;
}
static uint32_t HAL_GetTick(void) { return tick++; }
static void LL_IWDG_Enable(void *p) { (void)p; assert(clock_on); enabled = true; }
static void LL_IWDG_EnableWriteAccess(void *p) { (void)p; unlocked = true; }
static void LL_IWDG_SetPrescaler(void *p, uint32_t n) {
    (void)p; assert(enabled && unlocked); prescaler=n;
}
static void LL_IWDG_SetReloadCounter(void *p, uint32_t n) {
    (void)p; assert(enabled && unlocked); counter=n;
}
static uint32_t LL_IWDG_IsReady(void *p) {
    (void)p; if (register_failure) return 0u;
    if (busy) { --busy; return 0u; } return enabled ? 1u : 0u;
}
static void LL_IWDG_ReloadCounter(void *p) { (void)p; assert(enabled); ++reloads; }
static void reset_model(void) {
    tick=busy=reloads=prescaler=counter=0u;
    oscillator_failure=register_failure=clock_on=enabled=unlocked=false;
}
'''
CASES = r'''
int main(void) {
    reset_model(); busy=4u;
    assert(watchdog_start()); assert(reloads==1u && prescaler==6u && counter==4095u);
    reset_model(); oscillator_failure=true;
    assert(!watchdog_start()); assert(!enabled && !unlocked && reloads==0u);
    reset_model(); register_failure=true;
    assert(!watchdog_start()); assert(enabled && reloads==0u && tick<=104u);
    reset_model(); tick=UINT32_MAX-2u; busy=8u;
    assert(watchdog_start()); assert(reloads==1u && tick<20u);
    reset_model(); tick=UINT32_MAX-2u; register_failure=true;
    assert(!watchdog_start()); assert(reloads==0u && tick<104u);
    puts("5 boot watchdog software cases passed; hardware acceptance NOT_RUN");
    return 0;
}
'''

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    out=parser.parse_args().output.resolve(); out.mkdir(parents=True,exist_ok=False)
    text=SOURCE.read_text(encoding='utf-8')
    start=text.index('static bool watchdog_start(void)')
    end=text.index('static void watchdog_feed(void)',start)
    source=out/'watchdog.c'; source.write_text(FAKE+text[start:end]+CASES,encoding='utf-8')
    exe=out/'test.exe'
    command=['cl.exe','/nologo','/std:c11','/W4','/WX',str(source),f'/Fe:{exe}']
    batch=out/'build.cmd'; batch.write_text('@echo off\ncall "'+str(find_vsdevcmd())+'" -arch=amd64 -host_arch=amd64 >nul\nif errorlevel 1 exit /b %errorlevel%\n'+subprocess.list2cmdline(command)+'\n')
    logs=[]
    for command in (['cmd.exe','/d','/c',str(batch)],[str(exe)],
                    [shutil.which('arm-none-eabi-gcc'),'-std=c11','-mcpu=cortex-m33','-mthumb','-Os','-Wall','-Wextra','-Werror','-c',str(source),'-o',str(out/'test.o')]):
        result=subprocess.run(command,cwd=out,capture_output=True,text=True)
        logs.append(result.stdout+result.stderr)
        (out/'test.log').write_text('\n'.join(logs),encoding='utf-8')
        if result.returncode: raise RuntimeError('boot watchdog regression failed: '+str(out/'test.log'))
    report={'result':'PASS_BOOT_WATCHDOG_SOFTWARE_ONLY','cases':5,'hardwareAcceptance':'NOT_RUN',
            'sources':{p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in (SOURCE,Path(__file__))}}
    (out/'result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(logs[1].strip())

if __name__=='__main__': main()
