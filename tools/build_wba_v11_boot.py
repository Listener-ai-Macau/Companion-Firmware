#!/usr/bin/env python3
"""Build the selected resident WBA55 signed-update installer. Never flashes."""
from __future__ import annotations
import argparse, hashlib, json, shutil, subprocess, struct
from pathlib import Path
from wba_flash_geometry import MCUS, LAYOUTS, SOURCE as GEOMETRY_SOURCE, HEADER as GEOMETRY_HEADER, for_mcu, validate_generated_header
from wba_resource_geometry import geometry as resource_geometry, from_profile as resource_geometry_from_profile
from inspect_wba_ce_sram import inspect_elf as inspect_ce_elf

ROOT=Path(__file__).resolve().parents[1]
PLATFORM=ROOT/'platform/stm32wba55_companion_v11'
APP=ROOT/'app/companion_pendant'
SDK_COMMIT='e455b860ceb52aaa0332a98f1e7a10bbd7014fc9'

def digest(path:Path)->str:return hashlib.sha256(path.read_bytes()).hexdigest()
def run(argv:list[str],cwd:Path)->str:
    p=subprocess.run(argv,cwd=cwd,text=True,capture_output=True)
    if p.returncode:raise RuntimeError((p.stdout+p.stderr).strip())
    return p.stdout
def uint32(text:str)->int:
    value=int(text,0)
    if not 0<value<=0xffffffff:raise argparse.ArgumentTypeError('must be a nonzero uint32')
    return value

def main()->int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sdk',type=Path,default=ROOT/'.cache/deps/STM32CubeWBA')
    parser.add_argument('--output',type=Path,default=ROOT/'.cache/wba-v11-boot')
    parser.add_argument('--mcu', choices=MCUS, default='STM32WBA55CEU6')
    parser.add_argument('--flash-layout', choices=LAYOUTS, default='legacy32', help='compact24 requires a matched SWD boot+app migration; cannot be sent to legacy32 over app OTA')
    parser.add_argument('--lto',action='store_true',help='Whole-program size optimization; keeps signed install/recovery features, physical qualification remains separate')
    parser.add_argument('--simple-ota',action='store_true',help='One signed full App+UI file; download restarts at zero, Boot restarts interrupted installation')
    parser.add_argument('--development-install-cut-window-ms',type=int,default=0,
                        help='DEV key only: bounded physical power-cut window after the authenticated first App page is erased; default disabled')
    parser.add_argument('--update-public-key',type=Path,help='raw 64-byte big-endian P-256 X||Y')
    parser.add_argument('--update-key-id',type=uint32)
    parser.add_argument('--firmware-version',type=uint32,required=True)
    parser.add_argument('--installed-image-size',type=uint32,required=True)
    parser.add_argument('--panel-low-slew',action='store_true',
                        help='Match the application EPD SCK/MOSI/DC/CS low-slew GPIO candidate during resident boot')
    parser.add_argument('--panel-open-drain',action='store_true',
                        help='Withdrawn comparison; rejected because the V1.1 EPD U3 TXB0104 requires push-pull drivers')
    resource_args=parser.add_mutually_exclusive_group()
    resource_args.add_argument('--ui-resources',type=Path,help='Bind boot geometry to this resource bank/profile')
    resource_args.add_argument('--ui-resource-bytes',type=uint32,help='Explicit static-bank extent; default 1 MiB')
    args=parser.parse_args()
    if not args.simple_ota or args.mcu!='STM32WBA55CEU6' or args.flash_layout not in ('legacy32','compact24','compact24-nor'):
        parser.error('Minimal OTA requires --simple-ota, WBA55CE and legacy32; initial provisioning must match the new App/UI and signed current header')
    if args.panel_open_drain:
        parser.error('--panel-open-drain is unsupported on Companion V1.1: EPD U3 is TXB0104, not TXS0104E; FW119 failed and was withdrawn')
    if not args.update_public_key or not args.update_key_id:
        parser.error('The product boot requires its existing OTA trust anchor: --update-public-key and --update-key-id; refusing an update-disabled replacement')
    if args.development_install_cut_window_ms and (args.update_key_id!=0x44455631 or not 5000<=args.development_install_cut_window_ms<=60000):
        parser.error('The physical cut window requires the explicit DEV key and 5000..60000ms; production builds keep it disabled')
    out=args.output.resolve();sdk=args.sdk.resolve();out.mkdir(parents=True,exist_ok=True)
    geometry=for_mcu(args.mcu,args.flash_layout);validate_generated_header()
    if not geometry.nvm_bytes and args.update_key_id!=0x44455631:
        parser.error('NVM0 is DEV only until external pairing persistence security and migration are qualified')
    resource_sources=[]
    if args.ui_resources:
        profile_file=args.ui_resources.resolve()/'profile.json'
        bank=profile_file.parent/'ui-partition.bin'
        profile=json.loads(profile_file.read_text())
        if digest(bank).upper()!=profile['uiPartitionSha256'].upper():
            parser.error('Resource bank/profile identity differs')
        nor_geometry=resource_geometry_from_profile(profile,bank.stat().st_size)
        resource_sources=[profile_file,bank]
    else:
        nor_geometry=resource_geometry(args.ui_resource_bytes or 0x100000)
    if args.installed_image_size>geometry.app_bytes:parser.error('--installed-image-size exceeds selected MCU relocated app capacity')
    linker=geometry.linker(PLATFORM,boot=True);geometry.validate_linker(linker,boot=True)
    if (args.update_public_key is None)!=(args.update_key_id is None):parser.error('public key and key id must be provided together')
    key=bytes(64);key_id=0
    if args.update_public_key:
        key=args.update_public_key.read_bytes();key_id=args.update_key_id
        if len(key)!=64 or not any(key):parser.error('--update-public-key must be nonzero raw64 X||Y')
        try:
            from cryptography.hazmat.primitives.asymmetric import ec
            ec.EllipticCurvePublicNumbers(int.from_bytes(key[:32],'big'),int.from_bytes(key[32:],'big'),ec.SECP256R1()).public_key()
        except Exception as exc:parser.error(f'invalid P-256 public point: {exc}')
    cc=shutil.which('arm-none-eabi-gcc');objcopy=shutil.which('arm-none-eabi-objcopy');size_tool=shutil.which('arm-none-eabi-size')
    if not cc or not objcopy or not size_tool:raise RuntimeError('Arm GNU toolchain missing')
    if run(['git','rev-parse','HEAD'],sdk).strip()!=SDK_COMMIT:raise RuntimeError('pinned CubeWBA SDK identity mismatch')
    hal=sdk/'Drivers/STM32WBAxx_HAL_Driver';cmsis=sdk/'Drivers/CMSIS';device=cmsis/'Device/ST/STM32WBAxx'
    trust=out/'wba_update_trust_anchor.h'
    trust.write_text('#ifndef COMPANION_WBA_UPDATE_TRUST_ANCHOR_H\n#define COMPANION_WBA_UPDATE_TRUST_ANCHOR_H\n#include <stdint.h>\n'
        f'#define COMP_WBA_UPDATE_KEY_ID UINT32_C(0x{key_id:08X})\n'
        'static const uint8_t comp_wba_update_public_key[64]={'
        +','.join(f'0x{x:02X}' for x in key)+'};\n#endif\n',encoding='ascii')
    hal_conf=out/'stm32wbaxx_hal_conf.h'
    hal_conf.write_text('''#ifndef STM32WBAXX_HAL_CONF_H
#define STM32WBAXX_HAL_CONF_H
#define HAL_MODULE_ENABLED
#define HAL_CORTEX_MODULE_ENABLED
#define HAL_DMA_MODULE_ENABLED
#define HAL_GPIO_MODULE_ENABLED
#define HAL_RCC_MODULE_ENABLED
#define HAL_PWR_MODULE_ENABLED
#define HAL_FLASH_MODULE_ENABLED
#define HAL_SPI_MODULE_ENABLED
#define HAL_PKA_MODULE_ENABLED
#define HAL_RNG_MODULE_ENABLED
#define HAL_UART_MODULE_ENABLED
#define HSE_VALUE 32000000UL
#define HSI_VALUE 16000000UL
#define LSI_VALUE 32000UL
#define LSE_VALUE 32768UL
#define HSE_STARTUP_TIMEOUT 100UL
#define LSE_STARTUP_TIMEOUT 5000UL
#define VDD_VALUE 1800UL
#define TICK_INT_PRIORITY 0x0FUL
#define USE_RTOS 0U
#define PREFETCH_ENABLE 0U
#define USE_SPI_CRC 0U
#include "stm32wbaxx_hal_rcc.h"
#include "stm32wbaxx_hal_gpio.h"
#include "stm32wbaxx_hal_cortex.h"
#include "stm32wbaxx_hal_dma.h"
#include "stm32wbaxx_hal_flash.h"
#include "stm32wbaxx_hal_pwr.h"
#include "stm32wbaxx_hal_spi.h"
#include "stm32wbaxx_hal_pka.h"
#include "stm32wbaxx_hal_rng.h"
#include "stm32wbaxx_hal_uart.h"
#define assert_param(expr) ((void)0U)
#endif
''',encoding='ascii')
    update=APP/'update';storage=APP/'storage';ota=ROOT/'third_party/denzic-platform/ota/embedded/c'
    recording=APP/'recording'
    sources=[PLATFORM/'update_boot_main.c',PLATFORM/'update_boot_target.c',
        update/'wba_update_manifest_wire.c',update/'wba_update_p256.c',
        update/'wba_update_p256_hal.c',update/'wba_simple_package.c',update/'wba_simple_install.c',
        storage/'spi_nor_stm32wba.c',
        device/'Source/Templates/system_stm32wbaxx.c',device/'Source/Templates/gcc/startup_stm32wba55xx.s']
    for name in ('hal','hal_cortex','hal_dma','hal_dma_ex','hal_gpio','hal_rcc','hal_rcc_ex','hal_pwr','hal_pwr_ex',
                 'hal_flash','hal_flash_ex','hal_spi','hal_spi_ex','hal_pka','hal_rng','hal_uart','hal_uart_ex'):
        sources.append(hal/f'Src/stm32wbaxx_{name}.c')
    if geometry.flash_kib == 512:
        sources.append(PLATFORM/'ce_reset.S')
    includes=[out,PLATFORM,update,recording,storage,ota/'include',hal/'Inc',cmsis/'Include',device/'Include']
    flags=['-mcpu=cortex-m33','-mthumb','-mfpu=fpv5-sp-d16','-mfloat-abi=hard','-std=c11','-Os','-g3',
        '-ffunction-sections','-fdata-sections','-DSTM32WBA55xx','-DUSE_HAL_DRIVER',
        f'-DCOMP_WBA_INTERNAL_FLASH_KIB={geometry.flash_kib}u',
        f'-DCOMP_WBA_BOOT_FLASH_KIB={geometry.boot_bytes // 1024}u',
        f'-DCOMP_WBA_INTERNAL_NVM_KIB={geometry.nvm_bytes // 1024}u',
        f'-DCOMPANION_WBA_APP_VERSION={args.firmware_version}u',
        f'-DCOMP_V11_PANEL_LOW_SLEW={int(args.panel_low_slew)}',
        f'-DCOMP_V11_PANEL_OPEN_DRAIN={int(args.panel_open_drain)}',
        f'-DCOMPANION_WBA_INSTALLED_IMAGE_SIZE={args.installed_image_size}u',*(f'-I{x}' for x in includes)]
    flags += [f'-DCOMP_WBA_DEV_INSTALL_CUT_WINDOW_MS={args.development_install_cut_window_ms}u']
    flags += [f'-DCOMP_WBA_NOR_UI_BYTES={nor_geometry["staticBytes"]}u',
              f'-DCOMP_WBA_NOR_TOTAL_BYTES={nor_geometry["norBytes"]}u']
    if args.lto:flags+=['-flto']
    objects=[]
    for index,source in enumerate(sources):
        obj=out/f'{index:02d}-{source.stem}.o';warnings=['-Wall','-Wextra','-Werror'] if source.is_relative_to(APP) or source.is_relative_to(PLATFORM) else []
        run([cc,*flags,*warnings,'-c',str(source),'-o',str(obj)],out);objects.append(obj)
    elf=out/'companion_wba55_v11_boot.elf';binary=out/'companion_wba55_v11_boot.bin';mapfile=out/'companion_wba55_v11_boot.map'
    run([cc,'-mcpu=cortex-m33','-mthumb','-mfpu=fpv5-sp-d16','-mfloat-abi=hard',*(['-flto'] if args.lto else []),*(str(x) for x in objects),
         '-T',str(linker),'-Wl,--gc-sections',f'-Wl,-Map={mapfile}',
         '--specs=nano.specs','--specs=nosys.specs','-o',str(elf)],out)
    run([objcopy,'-O','binary',str(elf),str(binary)],out)
    sram_inspection=inspect_ce_elf(elf) if geometry.flash_kib == 512 else None
    if sram_inspection and not sram_inspection['writableSectionAddressesValid']:
        raise RuntimeError('CE resident Boot uses unsupported SRAM addresses')
    initial_sp,reset_vector=struct.unpack_from('<II',binary.read_bytes())
    if not geometry.valid_stack_pointer(initial_sp) or not reset_vector&1 or not geometry.flash_base <= (reset_vector&~1) < geometry.flash_base+geometry.boot_bytes:
        raise RuntimeError('Resident Boot vector differs from selected physical geometry')
    size_text=run([size_tool,str(elf)],out);bin_bytes=binary.stat().st_size
    if bin_bytes>geometry.boot_bytes:raise RuntimeError(f'boot BIN exceeds selected capacity {geometry.boot_bytes}: {bin_bytes}')
    tracked=[*sources,PLATFORM/'update_boot_target.h',PLATFORM/'panel_boot_idle.h',PLATFORM/'boot_receipt.h',
             linker,Path(__file__),GEOMETRY_SOURCE,GEOMETRY_HEADER,
             Path(__file__).with_name('wba_flash_geometry.py'),Path(__file__).with_name('wba_resource_geometry.py'),
             update/'wba_storage_layout.h',update/'wba_simple_layout.h',update/'wba_simple_install.h',update/'wba_simple_package.h',trust,hal_conf,*resource_sources]
    result={'schema':'companion.wba.v11.resident-boot.v1','result':'PASS','flashed':False,
        'system_pair_protocol':'companion_simple_ota_v3',
        'requires_matched_simple_receiver_app':True,'requires_initial_signed_package_header':True,
        'download_resume':False,'interrupted_install_restarts_full_package':True,'old_image_backup':False,
        'development_install_cut_window_ms':args.development_install_cut_window_ms,
        'development_only_instrumentation':bool(args.development_install_cut_window_ms),
        'physical_qualified':False,
        'sram_inspection':sram_inspection,
        'mcu':geometry.mcu,'internal_flash_geometry':geometry.receipt(),
        'load_address':'0x08000000','capacity_bytes':geometry.boot_bytes,'binary_bytes':bin_bytes,
        'firmware_version':args.firmware_version,'installed_image_size':args.installed_image_size,
        'lto':args.lto,
        'panel_low_slew_enabled':args.panel_low_slew,
        'panel_open_drain_enabled':args.panel_open_drain,
        'flash_geometry':nor_geometry,
        'trust_configured':bool(key_id),'key_id':key_id,'public_key_sha256':hashlib.sha256(key).hexdigest(),
        'sdk_commit':SDK_COMMIT,'compiler':run([cc,'--version'],out).splitlines()[0],
        'elf':str(elf),'bin':str(binary),'elf_sha256':digest(elf),'bin_sha256':digest(binary),
        'size':size_text.strip(),'sources':{str(x.relative_to(ROOT) if x.is_relative_to(ROOT) else x):digest(x) for x in tracked}}
    (out/'result.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print(f"PASS_WBA_V11_BOOT bytes={bin_bytes} sha256={result['bin_sha256']} trust={int(bool(key_id))}")
    print(out/'result.json');return 0

if __name__=='__main__':raise SystemExit(main())
