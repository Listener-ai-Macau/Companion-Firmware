/* Compile the actual storage predicates, erase ownership, busy/bulk decisions
 * and poll-to-controller call together. Hardware/ACI and unrelated owners are
 * simulated; no installed firmware or throughput claim is made here. */
#define main original_bulk_handoff_main
#include "test_ble_bulk_handoff.c"
#undef main
#define COMPANION_WBA_EXTERNAL_BOND_STORE 1
#define COMPANION_WBA_DUAL_PAIR_CAPTURE 1
#define COMP_PIPE_IDLE 1u
#define COMP_PIPE_FINISHED 2u
#define COMP_WBA_RECORDING_TRANSFER_ACTIVE 3u
#define COMP_WBA_RECORDING_TRANSFER_BACKPRESSURED 4u
#define DENZIC_OTA_V1_STATE_RECEIVING 5u
#define COMP_WBA_NOR_RECORDING_BASE 1048576u
#define COMP_WBA_NOR_TOTAL_BYTES 16777216u
typedef struct {bool erase_active;uint32_t erase_address,erase_bytes;} companion_spi_nor_stm32wba_t;
typedef struct {unsigned phase;} catalog_t;
typedef struct {bool poisoned;} storage_t;
typedef struct {unsigned state,workspace_bytes;struct {catalog_t*catalog;storage_t*storage;} config;} comp_wba_recording_pipeline_t;
typedef struct {bool capture_active,prepare_pending,command_pending,start_pending,menu_pending;} comp_runtime_t;
typedef struct {struct {bool running;} microphone;bool playback_active;unsigned power_monitor;companion_spi_nor_stm32wba_t nor;} board_t;
typedef struct {bool media_ready,ready,boot_retry_owned;comp_wba_recording_pipeline_t pipeline;} recording_t;
typedef struct {board_t*board;comp_runtime_t runtime;recording_t recording;bool storage_layout_ready,recording_ready;struct{bool writing;} pet_profile;} product_t;
static product_t app,*product;
static board_t board;
static catalog_t catalog;
static storage_t storage;
typedef struct{bool consume_pending;} segmented_t;
static segmented_t segmented;
static struct{segmented_t*segmented;struct{unsigned state;} transfer;} product_link;
static bool local_clear_pending,nvm_busy,pair_owned,catalog_current=true;
static bool initializing,prepared,failed,update_ready;
static uint32_t claimed_base,claimed_bytes,erased_end,ahead_bytes;
static struct{unsigned state;} ota_transfer;
static unsigned power_blockers;
static bool comp_v11_ble_nvm_busy(void){return nvm_busy;}
static bool comp_wba_recording_product_recovering(const recording_t*r){return r->boot_retry_owned;}
static bool comp_wba_recording_product_boot_retry_owned(const recording_t*r){return r->boot_retry_owned;}
static bool comp_v11_dual_pair_owned(product_t*p){(void)p;return pair_owned;}
static bool comp_wba_recording_product_catalog_current(recording_t*r){(void)r;return catalog_current;}
static unsigned comp_wba_ota_admission_power_blockers(unsigned*p,uint32_t tick)
{(void)p;(void)tick;return power_blockers;}
static bool sealed_transfer_work(void){return false;}
static bool comp_v11_update_product_owns_erase(void);
static bool comp_v11_update_product_busy(void);
static bool comp_v11_update_product_reboot_pending(void);
static bool comp_v11_ble_can_continue_update(void);
#include "production_owner_gate.inc"

static void setup_owner(void)
{
    setup();memset(&app,0,sizeof(app));memset(&board,0,sizeof(board));
    memset(&catalog,0,sizeof(catalog));memset(&storage,0,sizeof(storage));
    memset(&product_link,0,sizeof(product_link));memset(&segmented,0,sizeof(segmented));
    product=&app;app.board=&board;app.storage_layout_ready=app.recording_ready=true;
    app.recording.media_ready=app.recording.ready=true;app.recording.pipeline.state=COMP_PIPE_IDLE;
    app.recording.pipeline.config.catalog=&catalog;app.recording.pipeline.config.storage=&storage;
    product_link.segmented=&segmented;catalog_current=update_ready=true;
    local_clear_pending=nvm_busy=pair_owned=initializing=prepared=failed=false;power_blockers=0u;
    ota_transfer.state=DENZIC_OTA_V1_STATE_RECEIVING;
    claimed_base=2097152u;claimed_bytes=1048576u;erased_end=0u;ahead_bytes=65536u;
    board.nor.erase_address=claimed_base;board.nor.erase_bytes=ahead_bytes;
}
static void assert_controller_blocked(void)
{
    assert(!comp_v11_ble_can_continue_update());
    production_profile_turn();assert(config_calls==0u && ci_calls==0u && dle_calls==0u);
}
int main(void)
{
    assert(original_bulk_handoff_main()==0);
    setup_owner();board.nor.erase_active=true;
    assert(comp_v11_update_product_owns_erase());
    assert(!comp_v11_ble_can_update() && comp_v11_ble_can_continue_update());
    assert(comp_v11_update_product_bulk_transfer() && !stack_writes_allowed());
    production_profile_turn();assert(config_calls==EXPECT_OWNER_PROFILE);
    if(EXPECT_OWNER_PROFILE){
        assert(applied[0]==7u && applied[1]==251u);
        production_profile_turn();assert(ci_calls==1u && last_ci==6u);
        transport.interval=6u;unsigned prior=config_calls;
        for(unsigned i=0;i<100u;++i)production_profile_turn();
        assert(config_calls==prior && ci_calls==1u);
    }
    puts("PASS actual owned-erase continuation versus strict initial admission, exact poll-to-ACI behavior");
    setup_owner();nvm_busy=true;
    assert(!comp_v11_ble_can_update() && comp_v11_ble_can_continue_update());
    production_profile_turn();assert(config_calls==EXPECT_OWNER_PROFILE);
    puts("PASS deferred NVM cannot steal existing OTA, initial NVM exclusion retained");
    setup_owner();nvm_busy=true;app.recording.boot_retry_owned=true;app.recording.ready=false;app.recording_ready=false;
    assert(!stack_writes_allowed()&&comp_v11_ble_can_update_storage_mount()&&!comp_v11_ble_can_update());
    app.recording.boot_retry_owned=false;
    assert(!comp_v11_ble_can_update_storage_mount());
    puts("PASS boot retry can reconcile existing OTA lease while NVM remains deferred; no new OTA admitted");

    setup_owner();board.nor.erase_active=true;++board.nor.erase_address;assert_controller_blocked();
    setup_owner();board.nor.erase_active=true;++board.nor.erase_bytes;assert_controller_blocked();
    setup_owner();board.nor.erase_active=true;ahead_bytes=0u;assert_controller_blocked();
    setup_owner();board.nor.erase_active=true;claimed_base=COMP_WBA_NOR_TOTAL_BYTES;assert_controller_blocked();
    /* The enclosing production poll returns before this call site without
     * product. Exercise the predicate, not an unreachable null poll turn. */
    setup_owner();product=NULL;assert(!comp_v11_ble_can_continue_update());
    setup_owner();app.storage_layout_ready=false;assert_controller_blocked();
    setup_owner();app.recording_ready=false;assert_controller_blocked();
    setup_owner();app.recording.media_ready=false;assert_controller_blocked();
    setup_owner();app.pet_profile.writing=true;assert_controller_blocked();
    setup_owner();pair_owned=true;assert_controller_blocked();
    setup_owner();board.microphone.running=true;assert_controller_blocked();
    setup_owner();board.playback_active=true;assert_controller_blocked();
    setup_owner();app.runtime.capture_active=true;assert_controller_blocked();
    setup_owner();app.runtime.prepare_pending=true;assert_controller_blocked();
    setup_owner();app.runtime.command_pending=true;assert_controller_blocked();
    setup_owner();app.runtime.start_pending=true;assert_controller_blocked();
    setup_owner();app.runtime.menu_pending=true;assert_controller_blocked();
    setup_owner();segmented.consume_pending=true;assert_controller_blocked();
    setup_owner();local_clear_pending=true;assert_controller_blocked();
    setup_owner();product_link.transfer.state=COMP_WBA_RECORDING_TRANSFER_ACTIVE;assert_controller_blocked();
    setup_owner();product_link.transfer.state=COMP_WBA_RECORDING_TRANSFER_BACKPRESSURED;assert_controller_blocked();
    setup_owner();app.recording.pipeline.state=99u;assert_controller_blocked();
    setup_owner();catalog.phase=1u;assert_controller_blocked();
    setup_owner();storage.poisoned=true;assert_controller_blocked();
    setup_owner();catalog_current=false;assert_controller_blocked();
    puts("PASS unrelated owners/invalid ranges/state guards still suppress controller operations");

    setup_owner();power_blockers=1u;production_profile_turn();assert(config_calls==0u);
    setup_owner();update_ready=false;production_profile_turn();assert(config_calls==0u);
    setup_owner();initializing=true;board.nor.erase_active=true;production_profile_turn();assert(config_calls==0u);
    setup_owner();production_profile_turn();assert(config_calls==1u && applied[1]==251u);
    failed=true;production_profile_turn();assert(!bulk_profile && applied[0]==0u && applied[1]==32u);
    setup_owner();production_profile_turn();prepared=true;production_profile_turn();
    assert(!bulk_profile && applied[0]==0u && applied[1]==32u);
    puts("PASS power/not-ready/initialization cannot activate; failure and prepared phase restore normal RX");
    return 0;
}
