"""Verify actual product erase-ahead lifecycle with actual NOR and SPI model."""
from pathlib import Path
import argparse,hashlib,json,subprocess
from build_wba_prehardware import run
from verify_wba_spi_nor_adapter import find_vsdevcmd
R=Path(__file__).resolve().parents[1];A=R/'app/companion_pendant';P=R/'platform/stm32wba55_companion_v11'
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 o=a.output.resolve();o.mkdir(parents=True,exist_ok=False);sdk=o/'sdk';sdk.mkdir()
 (sdk/'ble_types.h').write_text('#ifndef ERASE_TEST_BLE\n#define ERASE_TEST_BLE\n#include <stdint.h>\ntypedef uint8_t tBleStatus;\n#endif\n')
 (sdk/'stm32_wpan_common.h').write_text('/* Host fixture, no radio SDK */\n')
 (sdk/'product_app.h').write_text('''#ifndef ERASE_TEST_APP
#define ERASE_TEST_APP
#include "wba_power_monitor.h"
#include "spi_nor_stm32wba.h"
#include "screen_menu.h"
#include "companion_preferences.h"
#include "companion_runtime.h"
typedef struct { companion_spi_nor_stm32wba_t nor; comp_wba_power_monitor_t power_monitor; } comp_v11_hal_t;
typedef struct { comp_v11_hal_t *board; bool recording_ready; struct {bool media_ready;} recording; struct {struct {struct {uint32_t generation;} root;} generation;} resources;} comp_v11_product_app_t;
static struct {uint32_t KR;} test_iwdg;
#define IWDG (&test_iwdg)
uint32_t HAL_GetTick(void);
void NVIC_SystemReset(void);
bool comp_v11_product_update_workspace(comp_v11_product_app_t*,uint32_t,uint32_t*);
void comp_v11_product_recording_lease_result(comp_v11_product_app_t*,bool);
bool comp_wba_recording_product_space_current(const void*);
#endif
''')
 includes=[sdk,P/'ble',P,*(A/n for n in ('power','board','update','storage','gatt','runtime','runtime/generated','recording','epaper','playback','touch','imu','v1_features','diag_log')),R/'third_party/denzic-platform/ota/embedded/c/include',R/'third_party/denzic-platform/audio/embedded/c/include']
 sources=[P/'tests/test_ota_erase_ahead.c',A/'storage/spi_nor_stm32wba.c',R/'third_party/denzic-platform/ota/embedded/c/src/denzic_ota_v1.c']
 # Existing SPI fixture's global f shares the TU with a SHA helper local f.
 # Suppress only that host inclusion shadow warning; keep other warnings fatal.
 exe=o/'test.exe';cmd=['cl.exe','/nologo','/std:c11','/W4','/WX','/wd4295','/wd4459','/O2','/Gy','/MD','/DCOMPANION_WBA_APP_VERSION=66324','/DCOMPANION_WBA_OTA_DEV_IGNORE_POWER=1','/DCOMP_WBA_NOR_UI_BYTES=950272u',*(f'/I{x}' for x in includes),*(str(x) for x in sources),f'/Fe:{exe}','/link','/OPT:REF']
 script=o/'build.cmd';script.write_text('@echo off\ncall "'+str(find_vsdevcmd())+'" -arch=amd64 -host_arch=amd64 >nul\nif errorlevel 1 exit /b %errorlevel%\n'+subprocess.list2cmdline(cmd)+'\n')
 log=o/'build.log';run(['cmd.exe','/d','/c',str(script)],o,log);output=run([str(exe)],o,log)
 inputs=[*sources,P/'ble/update_product.c',P/'ble/update_product.h',P/'ble/ota_page_stream.h',R/'tools/fixtures/wba_nor_suspend_test.c',Path(__file__),sdk/'product_app.h']
 (o/'result.json').write_text(json.dumps(dict(result='PASS_ACTUAL_OTA_PRODUCT_ERASE_AHEAD_HOST_ONLY',output=output,hardware=False,newSpeedMeasurements=0,sourceSha256={str(x):hashlib.sha256(x.read_bytes()).hexdigest() for x in inputs}),indent=2)+'\n');print(output,end='')
if __name__=='__main__':main()
