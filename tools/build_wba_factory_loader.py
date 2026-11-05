"""Build the SRAM-only WBA55/SPI3 initial UI programmer; never connect to a board."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import subprocess
from build_wba_v11 import prepare_sdk
from wba_resource_geometry import geometry as resource_geometry
from wba_flash_geometry import MCUS, for_mcu, validate_generated_header, SOURCE, HEADER

ROOT = Path(__file__).resolve().parents[1]
FACTORY = ROOT / 'platform/stm32wba55_companion_v11/factory'

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sdk', type=Path, default=ROOT / '.cache/deps/STM32CubeWBA')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--mcu', choices=MCUS, default='STM32WBA55CEU6')
    parser.add_argument('--ui-resource-bytes',type=lambda v:int(v,0),required=True,help='Exact static resource extent; bounds every write and locates protected bond pages')
    parser.add_argument('--development-format',action='store_true',
                        help='Explicit developer formatter: initialize NOR and discard board recordings')
    args = parser.parse_args()
    geometry = for_mcu(args.mcu)
    media=resource_geometry(args.ui_resource_bytes)
    validate_generated_header()
    out = (args.output or ROOT / ('.cache/wba-factory/loader-ce' if geometry.flash_kib == 512 else '.cache/wba-factory/loader')).resolve()
    sdk = args.sdk.resolve()
    out.mkdir(parents=True, exist_ok=True)
    log = out / 'build.log'
    log.write_text('', encoding='utf-8')
    def run(argv):
        result = subprocess.run([str(x) for x in argv], capture_output=True, text=True, cwd=out)
        with log.open('a', encoding='utf-8') as f:
            f.write(subprocess.list2cmdline([str(x) for x in argv]) + '\n' + result.stdout + result.stderr)
        if result.returncode:
            raise RuntimeError(result.stdout + result.stderr)
        return result.stdout
    prepare_sdk(sdk, False, out, log)
    cc = shutil.which('arm-none-eabi-gcc')
    if not cc:
        raise RuntimeError('Arm GNU toolchain missing')
    hal = sdk / 'Drivers/STM32WBAxx_HAL_Driver'
    cmsis = sdk / 'Drivers/CMSIS'
    device = cmsis / 'Device/ST/STM32WBAxx'
    conf = out / 'stm32wbaxx_hal_conf.h'
    modules = ('cortex', 'dma', 'gpio', 'rcc', 'pwr', 'flash', 'spi')
    conf.write_text('#ifndef STM32WBAXX_HAL_CONF_H\n#define STM32WBAXX_HAL_CONF_H\n'
        '#define HAL_MODULE_ENABLED\n' + ''.join(f'#define HAL_{m.upper()}_MODULE_ENABLED\n' for m in modules) +
        '#define HSE_VALUE 32000000UL\n#define HSI_VALUE 16000000UL\n#define LSI_VALUE 32000UL\n'
        '#define LSE_VALUE 32768UL\n#define HSE_STARTUP_TIMEOUT 100UL\n#define LSE_STARTUP_TIMEOUT 5000UL\n'
        '#define VDD_VALUE 1800UL\n#define TICK_INT_PRIORITY 15U\n#define USE_RTOS 0U\n#define USE_SPI_CRC 0U\n'
        + ''.join(f'#include "stm32wbaxx_hal_{m}.h"\n' for m in modules) +
        '#define assert_param(expr) ((void)0U)\n#endif\n', encoding='ascii')
    storage = ROOT / 'app/companion_pendant/storage'
    sources = [FACTORY / 'loader.c', FACTORY / 'loader_target.c', storage / 'spi_nor_stm32wba.c',
        device / 'Source/Templates/system_stm32wbaxx.c']
    for name in ('hal', 'hal_cortex', 'hal_dma', 'hal_dma_ex', 'hal_gpio', 'hal_rcc', 'hal_rcc_ex',
                 'hal_pwr', 'hal_pwr_ex', 'hal_flash', 'hal_flash_ex', 'hal_spi', 'hal_spi_ex'):
        sources.append(hal / f'Src/stm32wbaxx_{name}.c')
    includes = [out, FACTORY, storage, ROOT / 'app/companion_pendant/update',
                ROOT / 'app/companion_pendant/recording', hal / 'Inc', cmsis / 'Include', device / 'Include']
    flags = ['-mcpu=cortex-m33', '-mthumb', '-mfloat-abi=soft', '-std=c11', '-Os', '-g',
             '-ffunction-sections', '-fdata-sections', '-DSTM32WBA55xx', '-DUSE_HAL_DRIVER',
             f'-DCOMP_WBA_INTERNAL_FLASH_KIB={geometry.flash_kib}u',
             f'-DCOMP_WBA_NOR_UI_BYTES={media["staticBytes"]}u',
             *(['-DCOMP_FACTORY_DEVELOPMENT_FORMAT=1'] if args.development_format else []),
             *(f'-I{x}' for x in includes)]
    objects = []
    for index, source in enumerate(sources):
        obj = out / f'{index:02}-{source.stem}.o'
        warnings = ['-Wall', '-Wextra', '-Werror'] if source.is_relative_to(ROOT / 'platform') or source.is_relative_to(ROOT / 'app') else []
        run([cc, *flags, *warnings, '-c', source, '-o', obj]); objects.append(obj)
    loader = out / 'Companion_V11_WBA55_UI.stldr'
    run([cc, *flags[:3], '-nostartfiles', *objects, '-T', FACTORY / 'loader.ld', '-Wl,--gc-sections',
         f'-Wl,-Map={out / "loader.map"}', '--specs=nano.specs', '--specs=nosys.specs', '-o', loader])
    symbols = run([shutil.which('arm-none-eabi-nm'), '-S', loader])
    for name in ('Init', 'Read', 'Write', 'SectorErase', 'MassErase', 'StorageInfo'):
        if not any(line.endswith(' ' + name) for line in symbols.splitlines()):
            raise RuntimeError('Missing loader export ' + name)
    segments = run([shutil.which('arm-none-eabi-readelf'), '-l', loader])
    for line in segments.splitlines():
        fields = line.split()
        if fields and fields[0] == 'LOAD':
            start, size = int(fields[2], 16), int(fields[5], 16)
            if start < 0x20000004 or start + size > 0x20008000:
                raise RuntimeError('Loader escaped its reserved SRAM window')
    tracked = [*sources, FACTORY / 'loader.h', FACTORY / 'loader.ld', FACTORY.parent / 'spi_polling.h', storage / 'spi_nor_stm32wba.h',
               ROOT / 'app/companion_pendant/recording/companion_cpu_stage.h', Path(__file__), conf, SOURCE, HEADER]
    report = {'schema': 'companion.wba.factory-loader.v1', 'result': 'PASS_BUILD_ONLY',
        'mcu': geometry.mcu, 'internal_flash_geometry': geometry.receipt(),
        'hardwareAcceptance': 'NOT_RUN', 'flashed': False, 'loader': loader.name, 'loader_sha256': digest(loader),
        'read_base': 0x90000000, 'read_bytes': 0x1000000, 'write_bytes': 0x1000000 if args.development_format else media['staticBytes'],
        'development_format':args.development_format,
        'protected_bond_range':[media['dynamicBase']+0xc000,media['dynamicBase']+0xf000],
        'static_geometry':media,
        'mass_erase': 'REFUSED', 'compiler': run([cc, '--version']).splitlines()[0],
        'symbols': symbols, 'segments': segments,
        'sources': {str(p.relative_to(ROOT) if p.is_relative_to(ROOT) else p): digest(p) for p in tracked}}
    (out / 'result.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: report[k] for k in ('result', 'loader', 'loader_sha256', 'hardwareAcceptance')}))

if __name__ == '__main__':
    main()
