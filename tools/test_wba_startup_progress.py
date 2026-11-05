"""Fault-inject production power preparation and startup NOR watchdog calls.

Uses the real C routines, isolated from hardware; no physical clock, storage,
audio or product acceptance is claimed.
"""
from pathlib import Path
import argparse, hashlib, json, shutil, subprocess
from verify_wba_spi_nor_adapter import find_vsdevcmd

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'platform/stm32wba55_companion_v11/board_hal.c'
FAKE = r'''
#include <assert.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#define HAL_OK 0
#define PWR_SMPS_SUPPLY 2u
#define PWR_REGULATOR_VOLTAGE_SCALE1 1u
#define IWDG ((void *)1)
#define COMPANION_WBA_BLE_LINKED 1
#define __HAL_RCC_PWR_CLK_ENABLE() (power_enabled=true)
static bool power_enabled, supply_failure, voltage_failure;
static unsigned supply_calls, voltage_calls;
static int HAL_PWREx_ConfigSupply(uint32_t source) {
    assert(power_enabled && source==PWR_SMPS_SUPPLY); ++supply_calls;
    return supply_failure ? 1 : HAL_OK;
}
static int HAL_PWREx_ControlVoltageScaling(uint32_t scale) {
    assert(power_enabled && supply_calls==1u && !supply_failure);
    assert(scale==PWR_REGULATOR_VOLTAGE_SCALE1); ++voltage_calls;
    return voltage_failure ? 1 : HAL_OK;
}
static int spi_flash, owner;
static void *active_board=&owner;
static bool startup_storage_active, transfer_ok;
static uint32_t startup_storage_started, tick, irq, reloads, transfer_calls;
static bool transfer(void *bus, const uint8_t *tx, uint8_t *rx, size_t n, uint32_t timeout) {
    assert(bus==&spi_flash && timeout==10u); (void)tx; (void)rx; (void)n;
    ++transfer_calls; return transfer_ok;
}
static uint32_t HAL_GetTick(void) { return tick; }
static uint32_t __get_IPSR(void) { return irq; }
static void LL_IWDG_ReloadCounter(void *p) { assert(p==IWDG); ++reloads; }
static void reset_model(void) {
    power_enabled=supply_failure=voltage_failure=false;
    supply_calls=voltage_calls=0u;
    startup_storage_active=transfer_ok=true;
    startup_storage_started=tick=irq=reloads=transfer_calls=0u;
}
'''
CASES = r'''
int main(void) {
    reset_model(); assert(power_clock_prepare());
    assert(power_enabled && supply_calls==1u && voltage_calls==1u);
    reset_model(); supply_failure=true; assert(!power_clock_prepare());
    assert(supply_calls==1u && voltage_calls==0u);
    reset_model(); voltage_failure=true; assert(!power_clock_prepare());
    assert(voltage_calls==1u);

    reset_model(); tick=179999u; assert(flash_transfer(&owner,NULL,NULL,128u,10u));
    assert(reloads==1u && transfer_calls==1u);
    reset_model(); transfer_ok=false; assert(!flash_transfer(&owner,NULL,NULL,128u,10u));
    assert(reloads==0u);
    reset_model(); assert(flash_transfer(&owner,NULL,NULL,0u,10u)); assert(reloads==0u);
    reset_model(); assert(flash_transfer(NULL,NULL,NULL,128u,10u)); assert(reloads==0u);
    reset_model(); irq=16u; assert(flash_transfer(&owner,NULL,NULL,128u,10u)); assert(reloads==0u);
    reset_model(); tick=180000u; assert(flash_transfer(&owner,NULL,NULL,128u,10u)); assert(reloads==0u);
    reset_model(); comp_v11_hal_storage_init_complete();
    assert(flash_transfer(&owner,NULL,NULL,128u,10u)); assert(reloads==0u);
    reset_model(); startup_storage_started=UINT32_MAX-100u; tick=50u;
    assert(flash_transfer(&owner,NULL,NULL,128u,10u)); assert(reloads==1u);
    reset_model(); startup_storage_started=UINT32_MAX-100u; tick=179900u;
    assert(flash_transfer(&owner,NULL,NULL,128u,10u)); assert(reloads==0u);
    puts("12 startup power/progress software cases passed; hardware acceptance NOT_RUN");
    return 0;
}
'''

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    out = parser.parse_args().output.resolve(); out.mkdir(parents=True, exist_ok=False)
    text = SOURCE.read_text(encoding='utf-8')
    power = text[text.index('static bool power_clock_prepare(void)'):text.index('static bool clocks(void)')]
    progress = text[text.index('static bool flash_transfer('):text.index('static uint32_t now(')]
    source = out / 'startup.c'; source.write_text(FAKE+power+progress+CASES, encoding='utf-8')
    exe = out / 'test.exe'
    command = ['cl.exe','/nologo','/std:c11','/W4','/WX',str(source),f'/Fe:{exe}']
    batch = out / 'build.cmd'
    batch.write_text('@echo off\ncall "'+str(find_vsdevcmd())+'" -arch=amd64 -host_arch=amd64 >nul\nif errorlevel 1 exit /b %errorlevel%\n'+subprocess.list2cmdline(command)+'\n')
    logs = []
    for command in (['cmd.exe','/d','/c',str(batch)], [str(exe)],
                    [shutil.which('arm-none-eabi-gcc'),'-std=c11','-mcpu=cortex-m33','-mthumb','-Os','-Wall','-Wextra','-Werror','-c',str(source),'-o',str(out/'test.o')]):
        result = subprocess.run(command,cwd=out,capture_output=True,text=True)
        logs.append(result.stdout+result.stderr)
        (out/'test.log').write_text('\n'.join(logs),encoding='utf-8')
        if result.returncode: raise RuntimeError('startup regression failed: '+str(out/'test.log'))
    report = {'result':'PASS_STARTUP_PROGRESS_SOFTWARE_ONLY','cases':12,'hardwareAcceptance':'NOT_RUN',
              'sources':{p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in (SOURCE,Path(__file__))}}
    (out/'result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(logs[1].strip())

if __name__ == '__main__': main()
