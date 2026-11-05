/* Real product + real NOR driver, existing command-level SPI model. No radio,
 * signature or physical timing qualification. 16MiB below is host-only media. */
#define COMP_NOR_FIXTURE_BYTES 16777216u
#define main original_nor_driver_fixture_main
#include "../../../tools/fixtures/wba_nor_suspend_test.c"
#undef main
/* The existing bus model also names its callback transfer. Rename only the
 * product's file-static DOV context for this single-TU native inclusion. */
#define transfer ota_engine
#include "../ble/update_product.c"
#undef transfer

static comp_v11_hal_t board;
static comp_v11_product_app_t app;
static bool queued,workspace_held;
static unsigned releases;
uint32_t HAL_GetTick(void){return f.now;}
void NVIC_SystemReset(void){assert(!"not used in erase behavior test");}
bool comp_v11_ble_can_update(void){return !board.nor.erase_active;}
bool comp_v11_ble_can_continue_update(void)
{return comp_v11_ble_can_update()||comp_v11_update_product_owns_erase();}
bool comp_v11_ble_can_update_storage_mount(void){return !board.nor.erase_active;}
void comp_v11_ble_idle_background_progress(void){++f.now;}
bool comp_v11_ble_store_gatt_for_reboot(void){return true;}
bool comp_v11_ble_nvm_busy(void){return false;}
bool comp_v11_ota_gatt_init(const comp_v11_ota_gatt_ports_t *p){(void)p;return true;}
void comp_v11_ota_gatt_poll_slice(void){}
bool comp_v11_ota_gatt_foreground_pending(void){return queued;}
void comp_v11_ota_gatt_identity(const uint8_t b[56]){(void)b;}
size_t comp_v11_ota_gatt_copy_following_data(uint32_t a,uint32_t b,uint16_t c,uint8_t*d,size_t n)
{(void)a;(void)b;(void)c;(void)d;(void)n;return 0;}
void *companion_opus16_rt_workspace_borrow(size_t n){(void)n;return NULL;}
void companion_opus16_rt_workspace_release(void*p){(void)p;}
bool comp_wba_recording_product_space_current(const void*p){(void)p;return true;}
void comp_v11_product_recording_lease_result(comp_v11_product_app_t*p,bool ok){(void)p;(void)ok;}
bool comp_v11_product_update_workspace(comp_v11_product_app_t*p,uint32_t bytes,uint32_t*base)
{
    (void)p;
    if(bytes){assert(!workspace_held);workspace_held=true;*base=COMP_WBA_NOR_TOTAL_BYTES-bytes;}
    else {
        assert(!board.nor.erase_active && !(f.sr1&1) && !(f.sr2&128));
        workspace_held=false;++releases;*base=0;
    }
    return true;
}
comp_wba_power_snapshot_t comp_wba_power_monitor_snapshot(const comp_wba_power_monitor_t*m,uint32_t t)
{(void)m;(void)t;comp_wba_power_snapshot_t s={0};return s;}
bool comp_wba_simple_package_open(comp_wba_simple_package_t*p,const uint8_t*h,size_t n,const comp_wba_simple_limits_t*l)
{(void)p;(void)h;(void)n;(void)l;assert(!board.nor.erase_active);return false;}
bool comp_wba_simple_package_newer(const comp_wba_simple_package_t*p,uint32_t a,uint32_t b)
{(void)p;(void)a;(void)b;return false;}
bool comp_wba_simple_pending_record(uint8_t p[COMP_SIMPLE_PENDING_BYTES],uint32_t a,uint32_t b,const uint8_t h[COMP_WBA_SIMPLE_HEADER_BYTES])
{(void)p;(void)a;(void)b;(void)h;assert(!"no publication from a fake manifest");return false;}
uint32_t comp_wba_update_wire_crc32(const uint8_t*p,size_t n)
{return comp_wba_recording_crc32(0,p,(uint32_t)n);}

static void session(void)
{
    reset();board.nor=make();memset(&app,0,sizeof(app));app.board=&board;
    workspace_held=false;releases=0;queued=false;
    assert(comp_v11_update_product_init(&app));ready=true;
    assert(begin_stream(NULL,1420544u));
    ota_engine.state=DENZIC_OTA_V1_STATE_RECEIVING;
    ota_engine.expected_size=1420544u;ota_engine.chunk_payload_bytes=466u;
    /* Exactly the production base; model an already durable current block. */
    assert(claimed_base==0xea5000u);
    erased_end=110592u;physical_prefix=45056u;ota_engine.bytes_written=45056u;
}
static void overlap_and_frontier(void)
{
    session();uint8_t bytes[466];memset(bytes,0xA5,sizeof(bytes));
    uint32_t before=erased_end;
    ahead_background();assert(ahead_bytes==65536u&&board.nor.erase_active);
    assert(f.erase_address==claimed_base+before&&f.erases==1u&&erased_end==before);
    assert(!comp_v11_ble_can_update_storage_mount()&&!comp_v11_ble_can_update());
    assert(comp_v11_update_product_owns_erase()&&comp_v11_ble_can_continue_update());
    ++board.nor.erase_address;
    assert(!comp_v11_update_product_owns_erase()&&!comp_v11_ble_can_continue_update());
    --board.nor.erase_address;
    assert(write_stream(NULL,bytes,sizeof(bytes)));
    assert(companion_spi_nor_stm32wba_erase_is_suspended(&board.nor));
    assert(physical_prefix==45056u+466u&&erased_end==before&&!f.erased);
    assert(!memcmp(f.bytes+claimed_base+45056u,bytes,sizeof(bytes)));
    assert(!ahead_program_access(before,1u)); /* never write the erasing block */
    queued=true;ahead_background();assert(f.resumes==0u);
    queued=false;ahead_background();assert(f.resumes==1u&&ahead_bytes);
    f.now+=board.nor.resume_guard_ms;ahead_background();
    complete();ahead_background();
    assert(!ahead_bytes&&!board.nor.erase_active&&erased_end==before+65536u);
    assert(f.erases==1u&&diagnostics.erase64_calls==1u);
    assert(!memcmp(f.bytes+claimed_base+45056u,bytes,sizeof(bytes)));
    assert(release_claim()&&!workspace_held&&releases==1u);
    puts("PASS actual product: next owned block overlaps current DATA; no advance on SUS; queued burst stays suspended; one completion");
}
static void abort_finish_and_failure(void)
{
    session();ahead_background();assert(ahead_program_access(45056u,1u));
    f.automatic_erase=true;disconnected=true;abort_stream(NULL);
    assert(!workspace_held&&!ahead_bytes&&!board.nor.erase_active&&releases==1u);
    session();ahead_background();assert(ahead_program_access(45056u,1u));
    f.automatic_erase=true;assert(!finish_stream(NULL));
    assert(!ahead_bytes&&!board.nor.erase_active&&workspace_held&&!prepared);
    assert(release_claim());
    session();ahead_background();f.ignored_suspend=true;
    assert(!ahead_program_access(45056u,1u)&&failed&&workspace_held&&board.nor.erase_active);
    assert(erased_end==110592u);
    f.ignored_suspend=false;f.automatic_erase=true;abort_stream(NULL);
    assert(!workspace_held&&!board.nor.erase_active&&releases==1u);
    session();f.fail_command=0xD8;ahead_background();
    assert(failed&&ahead_bytes&&workspace_held&&board.nor.erase_active);
    complete();abort_stream(NULL); /* uncertain erase is retired, not credited */
    assert(!ahead_bytes&&!board.nor.erase_active&&workspace_held&&erased_end==110592u);
    abort_stream(NULL);assert(!workspace_held&&releases==1u&&f.erases==1u);
    puts("PASS actual product: ABORT/disconnect and FINISH settle SUS before release/read; errors retain claim, uncertain completion never advances");
}
static void gates_and_fallback(void)
{
    session();physical_prefix=0;ahead_background();assert(!f.erases); /* no pre-timer erase */
    physical_prefix=1;queued=true;ahead_background();assert(!f.erases);
    queued=false;board.nor.erase_suspend_supported=false;ahead_background();assert(!f.erases);
    f.automatic_erase=true;assert(page_prepare(NULL,110592u));
    assert(erased_end==176128u&&!ahead_bytes&&f.erases==1u);
    assert(release_claim());
    session();erased_end=claimed_bytes;ahead_background();assert(!f.erases);
    erased_end=4096u;ahead_background();assert(!f.erases); /* no misaligned block */
    failed=true;ahead_background();assert(!f.erases);
    puts("PASS actual product: first-DATA/queued/failed/range/alignment/capability gates; unsupported chip uses existing synchronous erase");
}
int main(void)
{
    overlap_and_frontier();abort_finish_and_failure();gates_and_fallback();
    puts("PASS OTA_ERASE_AHEAD_PRODUCT_AND_DRIVER_HOST_ONLY; no real timing/radio/signature claim");return 0;
}
