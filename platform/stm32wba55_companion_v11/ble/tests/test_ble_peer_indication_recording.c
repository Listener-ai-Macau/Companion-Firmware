/* Compile the actual recording/maintenance gates and actual control prefix.
 * Hardware clock/ACI and the unrelated advertising body are explicit stubs. */
#include "../ble_peer_indication.h"
#include <assert.h>
#include <stdio.h>
#define COMPANION_WBA_PEER_INDICATIONS 1
#define COMPANION_WBA_EXTERNAL_BOND_STORE 1
#define BLE_STATUS_BUSY 0x93u
#define BLE_STATUS_INSUFFICIENT_RESOURCES 0x64u
#define COMP_DIAG_EVT_BLE_TRANSPORT 0u
#define COMP_DIAG_SEV_WARN 1u
#define COMP_DIAG_SEV_INFO 2u
typedef uint8_t tBleStatus;
static comp_v11_peer_indication_t peer_indication;
static uint32_t clock_now,external_revision;
static bool ready,radio_enabled,connection_allowed,connection_secured,advertise_pending;
static bool ota_busy,nvm_busy,nvm_pending,encode_slot,hash_fault;
static uint16_t connection;
static unsigned confirm_calls,advertising_body_calls,disconnect_calls;
static uint8_t command_status;
struct mic {bool running;};
struct board {struct mic microphone;};
struct product {
    struct board *board;
    struct {bool command_pending,start_pending;} runtime;
    struct {bool recovering;} recording;
    uint32_t capture_cycle_started_ms;
};
static struct board board;
static struct product storage,*product=&storage;
static uint32_t HAL_GetTick(void){return clock_now;}
static bool comp_v11_update_product_busy(void){return ota_busy;}
static bool comp_wba_recording_product_recovering(const void *p)
{(void)p;return storage.recording.recovering;}
static bool comp_v11_update_product_reboot_pending(void){return false;}
static bool comp_v11_ble_nvm_busy(void){return nvm_pending || nvm_busy;}
static bool comp_v11_microphone_hal_encode_window(struct mic *m){assert(m==&board.microphone);return encode_slot;}
static bool comp_v11_ble_public_hash_fault(void){return hash_fault;}
static void comp_v11_ble_link(bool linked,bool secured){(void)linked;connection_secured=secured;}
static void record_error(uint8_t e){assert(e==0xfb);}
static uint8_t hci_disconnect(uint16_t h,uint8_t reason){assert(h==connection&&reason==0x13);++disconnect_calls;return 0;}
static tBleStatus aci_gatt_confirm_indication(uint16_t h){assert(h==connection);++confirm_calls;return command_status;}
static void comp_diag_log_record_code(unsigned a,unsigned b,uint32_t c,uint32_t d,uint32_t e,uint32_t f)
{(void)a;(void)b;(void)c;(void)d;(void)e;(void)f;}
#include "production_gates.inc"
#include "production_control_prefix.inc"
static void setup(void)
{
    ready=radio_enabled=connection_allowed=true;connection_secured=false;connection=1;clock_now=101;
    ota_busy=nvm_busy=nvm_pending=hash_fault=false;encode_slot=true;board.microphone.running=true;
    storage=(struct product){.board=&board,.capture_cycle_started_ms=100};product=&storage;
    confirm_calls=advertising_body_calls=disconnect_calls=0;command_status=0;
    comp_v11_peer_indication_reset(&peer_indication);
    const uint8_t indication[]={1,0,3,0,4,1,0,255,255};
    assert(comp_v11_peer_indication_receive(&peer_indication,connection,true,false,indication,sizeof indication,clock_now));
}
static void poll(void){comp_v11_ble_advertise_poll(clock_now,advertising_commands_allowed());}
int main(void)
{
    /* A disconnected active recorder must advertise even if a bond snapshot is
     * queued in RAM; NVM writes stay blocked, existing key security stays on. */
    setup();connection=0xffffu;advertise_pending=true;external_revision=0;
    APP_BLE_HostNvmStore();assert(external_revision==1u && nvm_pending);
    assert(!stack_writes_allowed() && comp_v11_ble_nvm_busy());
    assert(advertising_commands_allowed());poll();
    assert(advertising_body_calls==1 && nvm_pending && !nvm_busy);
    puts("PASS disconnected recording can re-advertise with pending NVM");
    nvm_busy=true;assert(!advertising_commands_allowed()); /* physical NVM owner */
    nvm_busy=false;connection=1;assert(advertising_commands_allowed()); /* public peer control only */
    connection=0xffffu;board.microphone.running=false;assert(!advertising_commands_allowed());
    board.microphone.running=true;encode_slot=false;assert(!advertising_commands_allowed());
    encode_slot=true;clock_now=103;assert(!advertising_commands_allowed());
    storage.capture_cycle_started_ms=clock_now;assert(advertising_commands_allowed());
    ota_busy=true;assert(!advertising_commands_allowed());
    puts("PASS actual NVM owner, idle, capture deadline and OTA gates remain");

    /* Reconnected phone may send Service Changed while a bond snapshot remains
     * queued. The public indication still needs its time-limited confirmation. */
    setup();APP_BLE_HostNvmStore();poll();
    assert(nvm_pending && !nvm_busy && confirm_calls==1 && !peer_indication.pending);
    puts("PASS pending NVM cannot starve connected peer confirmation");

    setup();assert(!stack_writes_allowed() && advertising_commands_allowed());
    /* This is precisely the old668 guard: both bulk allowances are false. */
    assert(!stack_writes_allowed() && !(!board.microphone.running));
    poll();assert(confirm_calls==1&&!peer_indication.pending&&!connection_secured);
    assert(board.microphone.running && advertising_body_calls==0 && disconnect_calls==0);
    puts("PASS active recording denies old bulk/NVM gate but confirms one peer indication in existing audio-safe control slot");

    setup();encode_slot=false;poll();assert(!confirm_calls&&peer_indication.pending);
    encode_slot=true;clock_now=103;poll();assert(!confirm_calls&&peer_indication.pending);
    storage.capture_cycle_started_ms=clock_now;poll();assert(confirm_calls==1);
    setup();ota_busy=true;poll();assert(!confirm_calls);ota_busy=false;nvm_busy=true;poll();assert(!confirm_calls);
    nvm_busy=false;storage.runtime.start_pending=true;poll();assert(!confirm_calls);
    storage.runtime.start_pending=false;storage.runtime.command_pending=true;poll();assert(!confirm_calls);
    storage.runtime.command_pending=false;poll();assert(confirm_calls==1);
    puts("PASS DMA/encode window, cycle age, maintenance, NVM and pending recording commands remain strict gates");

    setup();command_status=BLE_STATUS_BUSY;poll();assert(confirm_calls==1&&peer_indication.pending);
    poll();assert(confirm_calls==1);clock_now+=10;storage.capture_cycle_started_ms=clock_now;command_status=0;poll();assert(confirm_calls==2&&!peer_indication.pending);
    setup();radio_enabled=false;poll();assert(!confirm_calls&&!peer_indication.pending);
    setup();hash_fault=true;poll();assert(!confirm_calls&&disconnect_calls==1&&!ready);
    setup();board.microphone.running=false;assert(stack_writes_allowed());poll();assert(confirm_calls==1);
    storage.recording.recovering=true;assert(!stack_writes_allowed());
    storage.recording.recovering=false;assert(stack_writes_allowed());
    puts("PASS no tight retry, disabled radio/hash fault protection and original idle confirmation behavior");
    return 0;
}
