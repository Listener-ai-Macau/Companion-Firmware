"""Compile real update_product against mock storage/radio; test its power gate."""
from pathlib import Path
import hashlib,json,subprocess
from build_wba_prehardware import run
from verify_wba_spi_nor_adapter import find_vsdevcmd

ROOT=Path(__file__).resolve().parents[1]
APP=ROOT/'app/companion_pendant'; PLATFORM=ROOT/'platform/stm32wba55_companion_v11'
OUT=ROOT/'.cache/host-tests/wba-update-product-power'
def main():
    OUT.mkdir(parents=True,exist_ok=True)
    result=OUT/'result.json'; result.unlink(missing_ok=True)
    sdk=OUT/'sdk'; sdk.mkdir(exist_ok=True)
    (sdk/'stm32wbaxx_hal.h').write_text('#ifndef POWER_TEST_HAL\n#define POWER_TEST_HAL\n#include <stdint.h>\ntypedef struct { void *Instance; } PKA_HandleTypeDef;\n#define PKA ((void*)0x1000)\nuint32_t HAL_GetTick(void);\nvoid NVIC_SystemReset(void);\n#endif\n')
    (sdk/'stm32wbaxx_hal_pka.h').write_text('#include "stm32wbaxx_hal.h"\n')
    (sdk/'ble_types.h').write_text('#ifndef POWER_TEST_BLE_TYPES\n#define POWER_TEST_BLE_TYPES\n#include <stdint.h>\ntypedef uint8_t tBleStatus;\n#endif\n')
    (sdk/'stm32_wpan_common.h').write_text('/* Mock SDK, no radio */\n')
    (sdk/'product_app.h').write_text('#ifndef POWER_TEST_APP\n#define POWER_TEST_APP\n#include "wba_power_monitor.h"\n#include "spi_nor_stm32wba.h"\n#include "screen_menu.h"\n#include "companion_preferences.h"\n#include "companion_runtime.h"\ntypedef struct { companion_spi_nor_stm32wba_t nor; comp_wba_power_monitor_t power_monitor; } comp_v11_hal_t;\ntypedef struct { comp_v11_hal_t *board; bool recording_ready,storage_layout_ready,assets_ready; struct { struct { struct { uint32_t generation; } root; } generation; } resources; } comp_v11_product_app_t;\n#endif\n')
    (sdk/'wba_update_trust_anchor.h').write_text('#include <stdint.h>\n#define COMP_WBA_UPDATE_KEY_ID 1u\nstatic const uint8_t comp_wba_update_public_key[64]={1}; /* MOCK, not a device trust anchor */\n')
    includes=[sdk,PLATFORM/'ble',PLATFORM,*(APP/n for n in ('power','board','update','storage','gatt','runtime','runtime/generated','recording','epaper','playback','touch','imu','v1_features','diag_log')),
        ROOT/'third_party/denzic-platform/audio/embedded/c/include',ROOT/'third_party/denzic-platform/ota/embedded/c/include']
    sources=[PLATFORM/'ble/update_product.c',PLATFORM/'tests/test_update_product_power.c',
        APP/'power/wba_power_monitor.c',APP/'board/companion_v11_board.c',APP/'board/tca6408.c']
    log=OUT/'build.log'; log.write_text('')
    exe=OUT/'test.exe'
    args=['cl.exe','/nologo','/std:c11','/W4','/WX','/wd4302','/wd4311','/wd4312',
        '/DCOMPANION_WBA_APP_VERSION=0x0001010D',
        *(f'/I{p}' for p in includes),*(str(p) for p in sources),f'/Fe:{exe}']
    script=OUT/'build.cmd'; script.write_text(f'@echo off\ncall "{find_vsdevcmd()}" -arch=amd64 -host_arch=amd64 >nul\nif errorlevel 1 exit /b %errorlevel%\n'+subprocess.list2cmdline(args)+'\n')
    run(['cmd.exe','/d','/c',str(script)],OUT,log)
    output=run([str(exe)],OUT,log)
    tracked=[*sources,PLATFORM/'ble/update_product.h',PLATFORM/'update_storage.h',
        APP/'power/wba_power_monitor.h',APP/'gatt/companion_gatt_stm32wb.h',Path(__file__),*sdk.glob('*.h')]
    result.write_text(json.dumps({'result':'PASS_PREHARDWARE_SOFTWARE_ONLY','hardwareAcceptance':'NOT_RUN',
        'fullChainAcceptance':'NOT_RUN','storageAndRadio':'MOCK','output':output,
        'source_sha256':{p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in tracked}},indent=2)+'\n')
    print(output,end=''); print(result); return 0
if __name__=='__main__': raise SystemExit(main())
