"""Build an isolated fixed-frame diagnostic from the current production driver.

Never opens hardware. HAL transport functions are extracted verbatim, rather
than substituting the older hardware-SPI peripheral diagnostic.
"""
from __future__ import annotations
import argparse, hashlib, json, re, shutil, struct, subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PLATFORM=ROOT/'platform/stm32wba55_companion_v11'
DIAG=PLATFORM/'screen_fixed_diag'

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--installed-build',type=Path,required=True)
    ap.add_argument('--gpio-monitor',action='store_true',help='Add MCU digital GPIO checks; instrumented bit timing is not production timing')
    ap.add_argument('--bus-isolation',action='store_true',help='No panel commands: interleave quiet BUSY samples with individually toggled MCU outputs')
    ap.add_argument('--held-control',action='store_true',help='No clocks/commands: hold DC low with CS high, then CS low with DC high, bracketed by qualified quiet')
    ap.add_argument('--status-phase',action='store_true',help='One read-only0x2F command with per-bit samples after qualified20ms quiet')
    ap.add_argument('--selected-quiet-ms',type=int,choices=(0,20),default=0,help='One-variable status-phase comparison: hold CS/DC low before clocking')
    ap.add_argument('--sdk',type=Path,default=ROOT/'.cache/deps/STM32CubeWBA')
    a=ap.parse_args(); out=a.output.resolve(); out.mkdir(parents=True,exist_ok=False)
    assert sum((a.gpio_monitor,a.bus_isolation,a.status_phase,a.held_control))<=1,'Choose one diagnostic mode'
    assert not a.selected_quiet_ms or a.status_phase
    sdk=a.sdk.resolve(); installed=json.loads(a.installed_build.read_bytes())
    assert installed['panel_idle_clock_divider']==1 and installed['panel_passive_trace_enabled']
    assert installed['panel_bus']=='SOFTWARE_SPI_ENGINEERING_AUDIT' and installed['shared_spi_gpio_enabled']
    assert not any(installed.get(k,False) for k in ('panel_startup_readback_enabled','panel_low_slew_enabled','panel_open_drain_enabled'))
    for name in ('app/companion_pendant/epaper/ssd1681_wba.c','app/companion_pendant/epaper/ssd1681_wba.h','platform/stm32wba55_companion_v11/board_hal.c'):
        assert sha(ROOT/name)==installed['source_sha256'][name],('Installed driver differs',name)
    board=(PLATFORM/'board_hal.c').read_text(encoding='utf-8')
    names=('gpio','power_clock_prepare','clocks','panel_gpio_delay','panel_gpio_begin','panel_gpio_end',
           'panel_gpio_send','panel_gpio_receive','panel_gpio_read_begin','panel_take_busy_edges')
    functions=[]
    for name in names:
        found=re.search(r'^static (?:\w+\s+)+'+name+r'\([^;]*?\)\n\{',board,re.M)
        if not found: raise RuntimeError('Cannot extract '+name)
        start=found.start(); end=found.end(); level=1
        # These known functions do not contain braces in strings/comments.
        while level:
            if board[end]=='{': level+=1
            elif board[end]=='}': level-=1
            end+=1
        functions.append(board[start:end])
    include=out/'product_transport.inc'
    include.write_text('\n\n'.join(functions)+'\n',encoding='utf-8')
    conf=out/'stm32wbaxx_hal_conf.h'
    modules=('cortex','gpio','rcc','pwr','flash','dma','uart','spi')
    conf.write_text('#ifndef STM32WBAXX_HAL_CONF_H\n#define STM32WBAXX_HAL_CONF_H\n#define HAL_MODULE_ENABLED\n'+
        ''.join(f'#define HAL_{x.upper()}_MODULE_ENABLED\n' for x in modules)+
        '#define HSE_VALUE 32000000UL\n#define HSI_VALUE 16000000UL\n#define LSI_VALUE 32000UL\n#define LSE_VALUE 32768UL\n'
        '#define HSE_STARTUP_TIMEOUT 100UL\n#define LSE_STARTUP_TIMEOUT 5000UL\n#define VDD_VALUE 1800UL\n#define TICK_INT_PRIORITY 15U\n#define USE_RTOS 0U\n#define USE_SPI_CRC 0U\n'+
        ''.join(f'#include "stm32wbaxx_hal_{x}.h"\n' for x in modules)+
        '#define assert_param(expr) ((void)0U)\n#endif\n',encoding='ascii')
    hal=sdk/'Drivers/STM32WBAxx_HAL_Driver'; cmsis=sdk/'Drivers/CMSIS'
    device=cmsis/'Device/ST/STM32WBAxx'; otp=sdk/'Projects/Common/WPAN/Modules'
    sources=[DIAG/'main.c',PLATFORM/'syscalls.c',ROOT/'app/companion_pendant/epaper/ssd1681_wba.c',otp/'otp.c',
        device/'Source/Templates/system_stm32wbaxx.c',device/'Source/Templates/gcc/startup_stm32wba55xx.s']
    sources += [hal/f'Src/stm32wbaxx_{x}.c' for x in ('hal','hal_cortex','hal_gpio','hal_rcc','hal_rcc_ex','hal_pwr','hal_pwr_ex','hal_flash','hal_flash_ex','hal_dma','hal_dma_ex','hal_uart','hal_uart_ex')]
    cc=shutil.which('arm-none-eabi-gcc')
    if not cc: raise RuntimeError('ARM compiler not found')
    flags=['-mcpu=cortex-m33','-mthumb','-mfpu=fpv5-sp-d16','-mfloat-abi=hard','-std=c11','-Os','-g3','-flto',
        '-ffunction-sections','-fdata-sections','-fstack-usage','-DSTM32WBA55xx','-DUSE_HAL_DRIVER',
        '-DCOMP_V11_PANEL_PASSIVE_TRACE=1','-DCOMP_V11_PANEL_IDLE_CLOCK_DIVIDER=1',
        f'-DCOMP_SCREEN_FIXED_GPIO_MONITOR={int(a.gpio_monitor)}',
        f'-DCOMP_SCREEN_BUS_ISOLATION={int(a.bus_isolation)}',
        f'-DCOMP_SCREEN_STATUS_PHASE={int(a.status_phase)}',
        f'-DCOMP_SCREEN_SELECTED_QUIET_MS={a.selected_quiet_ms}',
        f'-DCOMP_SCREEN_HELD_CONTROL={int(a.held_control)}',
        *(f'-I{p}' for p in (out,DIAG,PLATFORM,ROOT/'app/companion_pendant/epaper',otp,hal/'Inc',cmsis/'Include',device/'Include'))]
    log=out/'build.log'
    def run(argv):
        p=subprocess.run([str(x) for x in argv],cwd=out,text=True,capture_output=True)
        with log.open('a',encoding='utf-8') as f: f.write(subprocess.list2cmdline([str(x) for x in argv])+'\n'+p.stdout+p.stderr)
        if p.returncode: raise RuntimeError(p.stdout+p.stderr)
        return p.stdout
    objects=[]
    for i,s in enumerate(sources):
        o=out/f'{i:02}-{s.stem}.o'
        warn=['-Wall','-Wextra','-Werror'] if not s.is_relative_to(sdk) else []
        run([cc,*flags,*warn,'-c',s,'-o',o]); objects.append(o)
    elf=out/'companion-screen-fixed.elf'; image=elf.with_suffix('.bin')
    run([cc,*flags,*objects,'-T',DIAG/'flash.ld','--specs=nano.specs','--specs=nosys.specs',
        '-Wl,--gc-sections',f'-Wl,-Map={elf.with_suffix(".map")}', '-o',elf])
    run([shutil.which('arm-none-eabi-objcopy'),'-O','binary',elf,image])
    sp,pc=struct.unpack_from('<II',image.read_bytes())
    assert sp==0x20020000 and 0x08000000<=pc&~1<0x08010000 and pc&1 and image.stat().st_size<=65536
    nm=run([shutil.which('arm-none-eabi-nm'),'-S',elf])
    assert not any(line.endswith(' '+name) for line in nm.splitlines()
        for name in ('HAL_FLASH_Program','HAL_FLASHEx_Erase','HAL_FLASH_OB_Launch','OTP_Write','MX_APPE_Init'))
    repo_sources=[p for p in sources if p.is_relative_to(ROOT)]+[DIAG/'flash.ld',Path(__file__),PLATFORM/'board_hal.c',
        PLATFORM/'panel_boot_idle.h',ROOT/'app/companion_pendant/epaper/ssd1681_wba.h',include,conf]
    result={'schema':'companion.screen-fixed-diagnostic.v1','result':'BUILT_NOT_INSTALLED','diagnosticId':'COMP_SCREEN_HELD_CONTROL_V6' if a.held_control else 'COMP_SCREEN_SELECTED_QUIET_V5' if a.selected_quiet_ms else 'COMP_SCREEN_STATUS_PHASE_V4' if a.status_phase else 'COMP_SCREEN_BUS_ISOLATION_V3' if a.bus_isolation else 'COMP_SCREEN_FIXED_GPIO_V2' if a.gpio_monitor else 'COMP_SCREEN_FIXED_V1',
        'image':image.name,'imageSha256':sha(image),'imageBytes':image.stat().st_size,'elfSha256':sha(elf),
        'installedFirmwareReference':installed['firmware_version'],'installedAppSha256':installed['bin_sha256'],
        'source_sha256':{p.relative_to(ROOT).as_posix():sha(p) for p in repo_sources},
        'generatedTransportFunctions':list(names),'generatedTransportSha256':sha(include),
        'compileFlags':flags,'loadAddress':0x08000000,'entryAddress':pc,'stackBytes':24576,
        'size':run([shutil.which('arm-none-eabi-size'),elf]).strip(),
        'bleStackLinked':False,'otherPeripheralTasksLinked':False,'readStatusAfterFixedFramesOnly':not (a.bus_isolation or a.status_phase or a.held_control),
        'gpioMonitor':a.gpio_monitor,'instrumentedBitTiming':a.gpio_monitor or a.bus_isolation or a.status_phase or a.held_control,
        'busIsolation':a.bus_isolation or a.held_control,'panelCommands':not (a.bus_isolation or a.held_control),
        'statusPhase':a.status_phase,'displayActivation':not (a.bus_isolation or a.status_phase or a.held_control),
        'selectedQuietMs':a.selected_quiet_ms,
        'heldControl':a.held_control,
        'resetPanel':False,'norCommands':False,'physicalGhosting':'NOT_VERIFIED','hardwareAccess':False}
    (out/'build.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:result[k] for k in ('result','imageBytes','imageSha256','size')},ensure_ascii=False))

if __name__=='__main__': main()
