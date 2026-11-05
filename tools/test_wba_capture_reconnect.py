"""Exercise real admission and GAP recovery functions for the failed recording."""
from pathlib import Path
import argparse,hashlib,json,subprocess
from verify_wba_spi_nor_adapter import find_vsdevcmd
ROOT=Path(__file__).resolve().parents[1];BLE=ROOT/'platform/stm32wba55_companion_v11/ble'
PRELUDE=r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <string.h>
#include <stdio.h>
typedef uint8_t tBleStatus;
#define COMPANION_WBA_EXTERNAL_BOND_STORE 1
#define COMP_PREFS_NAME_BYTES 20u
#define AD_TYPE_COMPLETE_LOCAL_NAME 9u
#define BLE_STATUS_SUCCESS 0u
#define HCI_COMMAND_DISALLOWED_ERR_CODE 12u
#define ADV_IND 0u
#define GAP_STATIC_RANDOM_ADDR 1u
#define NO_WHITE_LIST_USE 0u
#define comp_diag_log_record_code(...) ((void)0)
typedef struct { bool running; } microphone_t;
typedef struct { microphone_t microphone; } board_t;
typedef struct { bool command_pending,start_pending; } runtime_t;
typedef struct { board_t *board; runtime_t runtime; struct {bool recovering;} recording; uint32_t capture_cycle_started_ms; } product_t;
static board_t board;static product_t app={.board=&board};static product_t *product=&app;
static uint32_t tick,external_revision;static bool update_busy,nvm_busy,nvm_pending,window_open;
static uint32_t HAL_GetTick(void){return tick;}
static bool comp_v11_update_product_busy(void){return update_busy;}
static bool comp_v11_update_product_reboot_pending(void){return false;}
static bool comp_wba_recording_product_recovering(const void *p){(void)p;return app.recording.recovering;}
static bool comp_v11_ble_nvm_busy(void){return nvm_pending || nvm_busy;}
static bool comp_v11_microphone_hal_encode_window(microphone_t *m){assert(m==&board.microphone);return window_open;}
static bool ready,advertise_pending,identity_ready,radio_enabled,advertising,connection_secured;
static uint8_t advertise_stop_pending,local_name_length,local_name[COMP_PREFS_NAME_BYTES];
static uint16_t connection,advertising_rearms,advertising_recoveries;
static uint32_t advertising_retry,pairing_until;
static uint8_t advertising_link_status,advertising_link_mask,advertising_stop_status,advertising_disable_status;
static unsigned commands,stops,disables,starts;static tBleStatus gap_result,disable_result,start_result;
static bool comp_v11_ble_public_hash_fault(void){return false;}
static void comp_v11_ble_link(bool a,bool b){(void)a;(void)b;}
static void record_error(uint8_t e){(void)e;}
static bool pairing_open(void){return true;}
static bool check(tBleStatus value){return value==0;}
static tBleStatus hci_disconnect(uint16_t h,uint8_t r){(void)h;(void)r;++commands;return 0;}
static tBleStatus aci_hal_get_link_status_v2(uint8_t *links,uint16_t *handles){(void)handles;memset(links,0,22);++commands;return 0;}
static tBleStatus aci_gap_set_non_discoverable(void){++commands;++stops;return gap_result;}
static tBleStatus hci_le_set_advertising_enable(uint8_t e){assert(e==0);++commands;++disables;return disable_result;}
static tBleStatus aci_gap_set_discoverable(uint8_t a,uint16_t b,uint16_t c,uint8_t d,uint8_t e,
 uint8_t f,uint8_t *g,uint8_t h,uint8_t *i,uint16_t j,uint16_t k){
 (void)a;(void)b;(void)c;(void)d;(void)e;(void)f;(void)g;(void)h;(void)i;(void)j;(void)k;++commands;++starts;return start_result;}
'''
TEST=r'''
int main(void){
 tick=100;app.capture_cycle_started_ms=100;board.microphone.running=true;window_open=true;
 assert(!stack_writes_allowed());assert(advertising_commands_allowed());
 window_open=false;assert(!advertising_commands_allowed());window_open=true;
 tick=103;assert(!advertising_commands_allowed());tick=101;
 app.runtime.start_pending=true;assert(!advertising_commands_allowed());app.runtime.start_pending=false;
 app.runtime.command_pending=true;assert(!advertising_commands_allowed());app.runtime.command_pending=false;
 update_busy=true;assert(!advertising_commands_allowed());update_busy=false;
 nvm_busy=true;assert(!advertising_commands_allowed());nvm_busy=false;
 product=NULL;assert(!advertising_commands_allowed());product=&app;
 ready=identity_ready=radio_enabled=advertise_pending=true;connection=0xffffu;advertise_stop_pending=1;
 gap_result=12;disable_result=0;start_result=0;
 /* Pending bond snapshot after disconnect is not an active flash owner. */
 advertise_stop_pending=0;APP_BLE_HostNvmStore();assert(nvm_pending && external_revision==1u);
 assert(!stack_writes_allowed() && comp_v11_ble_nvm_busy());
 comp_v11_ble_advertise_poll(tick,advertising_commands_allowed());
 assert(commands==1 && starts==1 && advertising && !advertise_pending && nvm_pending);
 puts("PASS_ACTUAL_GAP_RESTART_WHEN_BOND_SAVE_QUEUED");
 nvm_pending=false;advertising=false;advertise_pending=true;advertise_stop_pending=1;advertising_retry=0;commands=stops=disables=starts=0;
 window_open=false;comp_v11_ble_advertise_poll(tick,advertising_commands_allowed());assert(commands==0);
 window_open=true;comp_v11_ble_advertise_poll(tick,advertising_commands_allowed());
 assert(commands==1 && stops==1 && disables==0 && advertise_stop_pending==2 && !advertising);
 comp_v11_ble_advertise_poll(tick,advertising_commands_allowed());assert(commands==1);
 tick=102;app.capture_cycle_started_ms=tick;
 disable_result=12;comp_v11_ble_advertise_poll(tick,advertising_commands_allowed());
 assert(commands==2 && disables==1 && advertise_stop_pending==2 && advertising_retry==1102);
 tick=1101;app.capture_cycle_started_ms=tick;comp_v11_ble_advertise_poll(tick,advertising_commands_allowed());assert(commands==2);
 tick=1102;app.capture_cycle_started_ms=tick;disable_result=0;
 comp_v11_ble_advertise_poll(tick,advertising_commands_allowed());assert(commands==3 && advertise_stop_pending==0 && advertising_rearms==1);
 comp_v11_ble_advertise_poll(tick,advertising_commands_allowed());assert(commands==4 && starts==1 && advertising && !advertise_pending);
 connection=1;connection_secured=true;advertise_pending=true;
 comp_v11_ble_advertise_poll(tick,advertising_commands_allowed());assert(commands==4);
 board.microphone.running=false;assert(stack_writes_allowed() && advertising_commands_allowed());
 puts("PASS_ACTUAL_CAPTURE_GAP_ADMISSION_AND_SINGLE_COMMAND_RETRY_SOFTWARE_ONLY");return 0;
}
'''
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
 out=p.parse_args().output.resolve();out.mkdir(parents=True,exist_ok=False)
 product_source=(BLE/'ble_product.c').read_text(encoding='utf-8');gap_source=(BLE/'app_ble.c').read_text(encoding='utf-8')
 gate=product_source[product_source.index('static bool stack_writes_allowed('):product_source.index('bool comp_v11_ble_foreground_pending(')]
 start=gap_source.index('void comp_v11_ble_advertise_poll(');end=gap_source.index('\n}',start)+2;gap=gap_source[start:end]+'\n'
 store=gap_source[gap_source.index('void APP_BLE_HostNvmStore('):gap_source.index('bool comp_v11_ble_store_gatt_for_reboot(')]
 nvm=gap_source[gap_source.index('bool comp_v11_ble_nvm_control_blocked('):gap_source.index('tBleStatus BLECB_Indication(')]
 source=out/'actual-functions.c';source.write_text(PRELUDE+store+nvm+gate+gap+TEST,encoding='utf-8')
 exe=out/'test.exe';args=['cl.exe','/nologo','/TC','/std:c11','/O2','/W4','/WX',str(source),'/Fe:'+str(exe)]
 cmd=out/'build.cmd';cmd.write_text('@echo off\ncall "'+str(find_vsdevcmd())+'" -arch=amd64 -host_arch=amd64 >nul\nif errorlevel 1 exit /b %errorlevel%\n'+subprocess.list2cmdline(args)+'\n')
 logs=[]
 for command in (['cmd.exe','/d','/c',str(cmd)],[str(exe)]):
  run=subprocess.run(command,cwd=out,capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW)
  logs.append(run.stdout+run.stderr);(out/'test.log').write_text('\n'.join(logs),encoding='utf-8')
  assert run.returncode==0, str(out/'test.log')
 result=dict(result=logs[-1].strip(),physicalBoard=False,sourceSha256={name:hashlib.sha256((BLE/name).read_bytes()).hexdigest() for name in ('ble_product.c','app_ble.c')})
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(result['result'])
if __name__=='__main__':main()
