"""Run the actual APP_BLE_Init against separate GAP/controller identity stores."""
from pathlib import Path
import argparse,hashlib,json,subprocess
from verify_wba_spi_nor_adapter import find_vsdevcmd
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'platform/stm32wba55_companion_v11/ble/app_ble.c'
PRELUDE=r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
/* Pinned SDK ble_defs.h offsets; GAP and controller have independent stores. */
#define CONFIG_DATA_GAP_ADD_REC_NBR_OFFSET 0x34
#define CONFIG_DATA_GAP_ADD_REC_NBR_LEN 1
#define CONFIG_DATA_IR_OFFSET 0x18
#define CONFIG_DATA_ER_OFFSET 0x08
#define CONFIG_DATA_IR_LEN 16
#define CONFIG_DATA_ER_LEN 16
#define CONFIG_DATA_RANDOM_ADDRESS_OFFSET 0x2E
#define CONFIG_DATA_RANDOM_ADDRESS_LEN 6
#define COMP_PREFS_NAME_BYTES 20
#define SNVMA_ERROR_OK 0
#define APP_BLE_Host_SNVMA_BufferId_1_1 0
#define dummy_SNVMA_BufferId_1_2 1
#define CFG_TX_POWER 0
#define GAP_PERIPHERAL_ROLE 1
#define PRIVACY_DISABLED 0
#define IO_CAP_NO_INPUT_NO_OUTPUT 3
#define MITM_PROTECTION_NOT_REQUIRED 0
#define SC_PAIRING_OPTIONAL 1
#define KEYPRESS_NOT_SUPPORTED 0
#define USE_FIXED_PIN_FOR_PAIRING_FORBIDDEN 1
#define GAP_STATIC_RANDOM_ADDR 1
typedef struct { uint8_t address[6]; } Bonded_Device_Entry_t;
static struct { uint32_t magic; uint32_t keys[8]; uint8_t address[6]; uint8_t reserved[6]; } identity;
static bool identity_ready,ready,advertise_pending,radio_enabled=true,missing_identity;
static uint8_t local_name[20]="Companion",local_name_length=9,last_error;
static uint16_t gap_service,gap_name;
static uint32_t pairing_until;
static uint8_t host_address[6],controller_address[6];
static unsigned gap_calls,random_writes,nvm_writes;
static bool reject_config;
static uint8_t success(void){return 0;}
static void record_error(uint8_t error){last_error=error;}
static bool check(uint8_t error){if(error)record_error(error);return error==0;}
static int restore(int id){return id==1 && missing_identity?1:0;}
static int persist(void){++nvm_writes;identity_ready=true;return 0;}
static bool entropy(uint32_t *word){static uint32_t n=0x12345600;*word=++n;return true;}
#define LST_init_head(...) ((void)0)
#define UTIL_SEQ_RegTask(...) ((void)0)
#define SNVMA_Register(...) success()
#define SNVMA_Restore(id) restore(id)
#define SNVMA_Write(...) persist()
#define comp_v11_ble_entropy entropy
#define BAES_Reset() ((void)0)
#define PKACTRL_Reset() ((void)0)
#define BLE_TIMER_Init() ((void)0)
#define HOST_BLE_Init() success()
static uint8_t aci_hal_write_config_data(uint8_t offset,uint8_t n,const uint8_t *value)
{
    assert(value);
    if(offset==CONFIG_DATA_RANDOM_ADDRESS_OFFSET){
        assert(n==6 && (value[5]&0xC0)==0xC0);++random_writes;
        if(reject_config)return 0x12;
        memcpy(host_address,value,6);
    }
    return 0;
}
static uint8_t gap_init(uint16_t *gap,uint16_t *name,uint16_t *appearance)
{++gap_calls;*gap=1;*name=2;*appearance=3;return 0;}
static uint8_t hci_le_set_random_address(const uint8_t *address)
{memcpy(controller_address,address,6);return 0;}
static uint8_t bonded(uint8_t *count,Bonded_Device_Entry_t *peers)
{(void)peers;*count=0;return 0;}
#define aci_hal_set_tx_power_level(...) success()
#define aci_gatt_init() success()
#define aci_gap_init(role,privacy,len,gap,name,appearance) gap_init(gap,name,appearance)
#define aci_gatt_update_char_value(...) success()
#define aci_gap_set_io_capability(...) success()
#define aci_gap_set_authentication_requirement(...) success()
#define SVCCTL_Init() ((void)0)
#define companion_gatt_stm32wb_init() success()
#define comp_diag_log_record_code(...) ((void)0)
#define hci_le_set_default_phy(...) success()
#define aci_gap_get_bonded_devices bonded
static uint32_t HAL_GetTick(void){return 123;}
/* GAP refreshes the controller from its own config before every advertisement.
 * An unset host identity reproduces status 0x12, irrespective of an HCI write. */
static uint8_t advertise_model(void)
{
    static const uint8_t zero[6]={0};
    memcpy(controller_address,host_address,6);
    return memcmp(controller_address,zero,6)==0?0x12:0;
}
'''
TEST=r'''
static void reset(void)
{
    memset(&identity,0,sizeof(identity));identity.magic=0x31494243;
    const uint8_t stored[6]={1,2,3,4,5,0xC6};memcpy(identity.address,stored,6);
    memset(host_address,0,6);memset(controller_address,0,6);
    identity_ready=ready=advertise_pending=missing_identity=reject_config=false;
    gap_calls=random_writes=nvm_writes=0;last_error=0;pairing_until=0;
}
int main(void)
{
    reset();
    assert(hci_le_set_random_address(identity.address)==0);
    assert(advertise_model()==0x12); /* Reproduce the original host/controller mismatch. */
    reset();APP_BLE_Init();
    assert(ready && advertise_pending && identity_ready && random_writes==1 && gap_calls==1);
    assert(advertise_model()==0 && memcmp(controller_address,identity.address,6)==0);
    assert(nvm_writes==0 && last_error==0 && pairing_until==120123);
    reset();reject_config=true;APP_BLE_Init();
    assert(!ready && !advertise_pending && gap_calls==0 && last_error==0x12 && nvm_writes==0);
    reset();missing_identity=true;APP_BLE_Init();
    assert(ready && identity_ready && nvm_writes==1 && advertise_model()==0);
    assert(memcmp(host_address,identity.address,6)==0);
    puts("PASS_SOFTWARE_ONLY: actual BLE init configures both identity stores, preserves restored identity and fails closed on config rejection");
    return 0;
}
'''
def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    out=parser.parse_args().output.resolve();out.mkdir(parents=True,exist_ok=False)
    source=SOURCE.read_text(encoding='utf-8')
    actual=source[source.index('void APP_BLE_Init(void)'):source.index('void comp_v11_ble_advertise_poll')]
    harness=out/'binding.c';harness.write_text(PRELUDE+actual+TEST,encoding='utf-8')
    exe=out/'test.exe';build=out/'build.cmd'
    command=['cl.exe','/nologo','/std:c11','/W4','/WX',str(harness),'/Fe:'+str(exe)]
    build.write_text('@echo off\ncall "'+str(find_vsdevcmd())+'" -arch=amd64 -host_arch=amd64 >nul\nif errorlevel 1 exit /b %errorlevel%\n'+subprocess.list2cmdline(command)+'\n')
    logs=[]
    for argv in (['cmd.exe','/d','/c',str(build)],[str(exe)]):
        result=subprocess.run(argv,cwd=out,text=True,capture_output=True);logs.append(result.stdout+result.stderr)
        (out/'test.log').write_text('\n'.join(logs),encoding='utf-8')
        if result.returncode:raise RuntimeError('BLE init test failed: '+str(out/'test.log'))
    receipt={'result':'PASS_BLE_IDENTITY_INIT_SOFTWARE_ONLY','hardwareAcceptance':'NOT_RUN',
             'source_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),'output':logs[-1].strip()}
    (out/'result.json').write_text(json.dumps(receipt,indent=2)+'\n');print(receipt['output'])
if __name__=='__main__':main()
