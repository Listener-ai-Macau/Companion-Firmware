#include "update_product.h"
#include "wba_simple_install.h"
#include "wba_simple_layout.h"
#include "wba_ota_gatt.h"
#include "ble_product.h"
#include "companion_opus16_rt.h"
#include "wba_recording_crc.h"
#include "wba_ota_power_gate.h"
#include "ota_page_stream.h"
#include <string.h>

#if COMPANION_WBA_CE_SHARED_CAPTURE && defined(__GNUC__)
#define OTA_SRAM1 __attribute__((section(".sram1.bss"),aligned(8)))
#else
#define OTA_SRAM1
#endif
static comp_v11_product_app_t *product;
static denzic_ota_v1_context_t transfer OTA_SRAM1;
static comp_v11_update_diagnostics_t diagnostics OTA_SRAM1;
/* Keep the new32B observation in SRAM2. The original SRAM1 receipt is
 * unchanged; its existing CE arena is not lent or enlarged for profiling. */
static comp_v11_update_program_diagnostics_t program_diagnostics;
const comp_v11_update_program_diagnostics_t *comp_v11_update_program_diagnostics(void)
{return &program_diagnostics;}
static uint8_t installed_hash[32] OTA_SRAM1;
static uint32_t claimed_base,claimed_bytes,erased_end,activity_ms,prepared_ms,physical_prefix;
/* One next-block owner inside the existing OTA lease. Its frontier advances
 * only after the driver proves completion; a suspended erase is never free. */
static uint32_t ahead_bytes,ahead_started_ms;
static bool ready,initialization_done,initializing,prepared,disconnected,failed,reboot_gatt_stored;
static uint32_t u32(const uint8_t*p)
{return (uint32_t)p[0]|((uint32_t)p[1]<<8)|((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24);}
static void put32(uint8_t*p,uint32_t v)
{for(unsigned i=0;i<4;i++)p[i]=(uint8_t)(v>>(8*i));}
static comp_wba_simple_limits_t limits(void)
{return (comp_wba_simple_limits_t){COMP_WBA_UPDATE_BOARD_COMPANION_V11,
    COMP_WBA_APP_ADDRESS,COMP_WBA_BOOT_APP_CAPACITY,COMP_WBA_NOR_UI_BYTES,
    COMP_WBA_NOR_TOTAL_BYTES,COMP_WBA_NOR_SYSTEM_BYTES};}
static bool idle(void)
{return initializing?comp_v11_ble_can_update_storage_mount():comp_v11_ble_can_continue_update();}
static bool powered_idle(void)
{return idle()&&product&&comp_wba_ota_admission_power_blockers(&product->board->power_monitor,HAL_GetTick())==0u;}
static void keep_alive(void)
{IWDG->KR=0xAAAAu;comp_v11_ble_idle_background_progress();}
static bool read_nor(uint32_t at,uint8_t*p,size_t n)
{return product&&companion_spi_nor_stm32wba_read(&product->board->nor,at,p,n)==COMPANION_SPI_NOR_STM32WBA_OK;}
/* Only the existing synchronous program owner lends this callback. Safe
 * stack progress excludes NOR writers; restore the exact port on every
 * driver return. No payload copy, timer, polling policy or hot UART added. */
static companion_spi_nor_stm32wba_transfer_fn_t program_transfer;
static uint32_t ota_clock_us(void)
{
#ifdef COMPANION_WBA_BLE_LINKED
    return comp_v11_ble_observe_us();
#else
    return HAL_GetTick()*1000u;
#endif
}
static void program_observe_add(uint32_t *sum,uint32_t value)
{
    if(value>UINT32_MAX-*sum)program_diagnostics.program_observe_flags|=1u;
    else *sum+=value;
}
static bool program_transfer_observed(void *context,const uint8_t *tx,
    uint8_t *rx,size_t n,uint32_t timeout)
{
    if(!program_transfer){program_diagnostics.program_observe_flags|=2u;return false;}
    uint32_t start=ota_clock_us();
    bool ok=program_transfer(context,tx,rx,n,timeout);
    program_observe_add(&program_diagnostics.program_spi_us,ota_clock_us()-start);
    program_observe_add(&program_diagnostics.program_spi_calls,1u);return ok;
}
static void ota_wait_progress(void *context)
{
    (void)context;
    if(!program_transfer){comp_v11_ble_idle_background_progress();return;}
    uint32_t start=ota_clock_us();comp_v11_ble_idle_background_progress();
    program_observe_add(&program_diagnostics.program_progress_us,ota_clock_us()-start);
    program_observe_add(&program_diagnostics.program_progress_calls,1u);
}
static void ota_wait_delay(void *context,uint32_t ms)
{
    (void)context;uint32_t started=HAL_GetTick();
    /* The NOR driver calls delay only after its status transaction ends.
     * HAL_Delay does not yield to WBA's cooperative LL/host tasks. While
     * this OTA owner waits for physical WIP, service only the existing
     * safe stack subset (no Flash manager, file pump or app dispatch). */
    do {ota_wait_progress(context);}
    while((uint32_t)(HAL_GetTick()-started)<ms);
}
static void io_result(uint32_t *calls,uint32_t *elapsed,uint32_t start,bool ok)
{
    uint32_t ms=HAL_GetTick()-start;
    if(*calls==UINT32_MAX || ms>UINT32_MAX-*elapsed)diagnostics.io_flags|=1u;
    else {++*calls;*elapsed+=ms;}
    if(!ok)diagnostics.io_flags|=2u;
}
static bool program(uint32_t at,const uint8_t*p,size_t n)
{
    if(!powered_idle())return false;
    companion_spi_nor_stm32wba_t *nor=&product->board->nor;
    void (*wait)(void *,uint32_t)=nor->config.delay_ms;if(!wait)return false;
    void (*progress)(void *)=nor->config.wait_progress;
    companion_spi_nor_stm32wba_transfer_fn_t original_transfer=nor->config.transfer;
    if(!original_transfer||program_transfer) {
        program_diagnostics.program_observe_flags|=2u;return false;
    }
    nor->config.delay_ms=ota_wait_delay;nor->config.wait_progress=ota_wait_progress;
    program_transfer=original_transfer;nor->config.transfer=program_transfer_observed;
    uint32_t start=HAL_GetTick();
    uint32_t precise_start=ota_clock_us();
    companion_spi_nor_stm32wba_status_t result=companion_spi_nor_stm32wba_program(nor,at,p,n);
    program_observe_add(&program_diagnostics.program_us,ota_clock_us()-precise_start);
    nor->config.transfer=original_transfer;program_transfer=NULL;
    nor->config.delay_ms=wait;nor->config.wait_progress=progress;
    bool ok=result==COMPANION_SPI_NOR_STM32WBA_OK;
    io_result(&diagnostics.program_calls,&diagnostics.program_ms,start,ok);return ok;
}
static bool erase(uint32_t at,uint32_t bytes)
{
    if(!powered_idle() || (bytes!=4096u&&bytes!=65536u))return false;
    companion_spi_nor_stm32wba_t *nor=&product->board->nor;
    void (*wait)(void *,uint32_t)=nor->config.delay_ms;if(!wait)return false;
    void (*progress)(void *)=nor->config.wait_progress;
    nor->config.delay_ms=ota_wait_delay;nor->config.wait_progress=ota_wait_progress;
    uint32_t start=HAL_GetTick();
    companion_spi_nor_stm32wba_status_t result=bytes==65536u?
        companion_spi_nor_stm32wba_erase_64k(nor,at):companion_spi_nor_stm32wba_erase_4k(nor,at);
    nor->config.delay_ms=wait;nor->config.wait_progress=progress;
    bool ok=result==COMPANION_SPI_NOR_STM32WBA_OK;
    io_result(bytes==65536u?&diagnostics.erase64_calls:&diagnostics.erase4_calls,
              bytes==65536u?&diagnostics.erase64_ms:&diagnostics.erase4_ms,start,ok);return ok;
}
/* Background erase time includes its program/read suspensions. It is a wall
 * latency, may overlap program_ms, and must not be added to the DATA ledger. */
static companion_spi_nor_stm32wba_status_t ahead_step(void)
{
    if(!ahead_bytes)return COMPANION_SPI_NOR_STM32WBA_OK;
    companion_spi_nor_stm32wba_t *nor=&product->board->nor;
    if(!nor->erase_active || nor->erase_address!=claimed_base+erased_end ||
       nor->erase_bytes!=ahead_bytes)return COMPANION_SPI_NOR_STM32WBA_ERROR;
    companion_spi_nor_stm32wba_status_t r=companion_spi_nor_stm32wba_erase_step(
        nor,claimed_base+erased_end,ahead_bytes);
    if(r==COMPANION_SPI_NOR_STM32WBA_OK) {
        io_result(&diagnostics.erase64_calls,&diagnostics.erase64_ms,ahead_started_ms,true);
        erased_end+=ahead_bytes;ahead_bytes=0u;
    } else if(r!=COMPANION_SPI_NOR_STM32WBA_PENDING) {
        diagnostics.io_flags|=2u;
        /* Driver can retire an uncertain command only after physical WIP
         * clears. Do not credit its range, but allow a later explicit ABORT
         * to release that now-idle failed claim rather than erase it again. */
        if(!nor->erase_active)ahead_bytes=0u;
    }
    return r;
}
static bool ahead_drain(void)
{
    /* ABORT/timeout/FINISH must settle the original physical owner before
     * releasing the claim, mounting metadata or publishing a pending image.
     * Transport errors retain both owner and claim; never reset NOR away. */
    while(ahead_bytes) {
        companion_spi_nor_stm32wba_status_t r=ahead_step();
        if(r==COMPANION_SPI_NOR_STM32WBA_OK)break;
        if(r!=COMPANION_SPI_NOR_STM32WBA_PENDING){failed=true;return false;}
        keep_alive();ota_wait_delay(NULL,1u);
    }
    return true;
}
static bool ahead_program_access_body(uint32_t at,size_t n)
{
    if(!ahead_bytes)return true;
    companion_spi_nor_stm32wba_t *nor=&product->board->nor;
    if(at>erased_end || n>erased_end-at)return false;
    uint32_t start=HAL_GetTick();
    for(;;) {
        if(disconnected||failed)return false;
        companion_spi_nor_stm32wba_status_t r=companion_spi_nor_stm32wba_erase_suspend_step(nor);
        if(r==COMPANION_SPI_NOR_STM32WBA_OK) {
            if(!companion_spi_nor_stm32wba_erase_is_suspended(nor))
                return ahead_step()==COMPANION_SPI_NOR_STM32WBA_OK; /* natural completion */
            return true; /* driver also validates SR1/SR2 and non-overlap at program */
        }
        if(r!=COMPANION_SPI_NOR_STM32WBA_PENDING ||
           HAL_GetTick()-start>=nor->config.sector_erase_timeout_ms) {
            failed=true;diagnostics.io_flags|=2u;return false;
        }
        keep_alive();ota_wait_delay(NULL,1u);
    }
}
static bool ahead_program_access(uint32_t at,size_t n)
{
    uint32_t start=ota_clock_us();bool ok=ahead_program_access_body(at,n);
    program_observe_add(&program_diagnostics.data_suspend_us,ota_clock_us()-start);return ok;
}
static void ahead_background(void)
{
    /* Only a gap in complete foreground commands lends time to the next
     * erase. Keep SUS across a queued DATA burst, not one resume per page.
     * First DATA must already have physically written: no pre-timer erases. */
    if(!ready||prepared||failed||disconnected||!claimed_bytes||!physical_prefix||
       transfer.state!=DENZIC_OTA_V1_STATE_RECEIVING||!powered_idle()||
       comp_v11_ota_gatt_foreground_pending())return;
    if(ahead_bytes) {
        companion_spi_nor_stm32wba_status_t r=ahead_step();
        if(r!=COMPANION_SPI_NOR_STM32WBA_OK&&r!=COMPANION_SPI_NOR_STM32WBA_PENDING)failed=true;
        return;
    }
    companion_spi_nor_stm32wba_t *nor=&product->board->nor;
    if(!nor->erase_suspend_supported||nor->erase_active||erased_end>=claimed_bytes||
       comp_wba_simple_payload_erase_bytes(claimed_base,claimed_bytes,erased_end)!=65536u)return;
    ahead_started_ms=HAL_GetTick();
    companion_spi_nor_stm32wba_status_t r=companion_spi_nor_stm32wba_erase_step(
        nor,claimed_base+erased_end,65536u);
    if(r==COMPANION_SPI_NOR_STM32WBA_PENDING&&nor->erase_active)ahead_bytes=65536u;
    else if(r!=COMPANION_SPI_NOR_STM32WBA_PENDING) {
        failed=true;diagnostics.io_flags|=2u;
        if(nor->erase_active)ahead_bytes=65536u;
    }
}
static bool release_claim(void)
{
    if(!ahead_drain())return false;
    uint32_t base=0;
    if(!comp_v11_product_update_workspace(product,0u,&base))return false;
    claimed_base=claimed_bytes=erased_end=physical_prefix=0u;return true;
}
static void abort_stream(void*c)
{
    (void)c;if(prepared)return;
    failed=claimed_bytes&&!release_claim();
}
static bool begin_stream(void*c,uint32_t size)
{
    (void)c;uint32_t minimum=COMP_WBA_SIMPLE_HEADER_BYTES+8u+COMP_WBA_NOR_UI_BYTES;
    uint32_t maximum=COMP_WBA_SIMPLE_HEADER_BYTES+COMP_WBA_BOOT_APP_CAPACITY+COMP_WBA_NOR_UI_BYTES;
    if(!ready||prepared||disconnected||!powered_idle()||size<minimum||size>maximum)return false;
    if(claimed_bytes&&!release_claim())return false;
    uint32_t bytes=(size+4095u)&~4095u,base;
    if(!comp_v11_product_update_workspace(product,bytes,&base))return false;
    claimed_base=base;claimed_bytes=bytes;erased_end=physical_prefix=0u;failed=false;
    diagnostics.program_calls=diagnostics.program_ms=diagnostics.erase4_calls=diagnostics.erase4_ms=0u;
    diagnostics.erase64_calls=diagnostics.erase64_ms=diagnostics.io_flags=0u;
    memset(&program_diagnostics,0,sizeof(program_diagnostics));
    /* No progress journal. Only FINISH may publish the pending record. */
    return !(base%4096u)&&base>=COMP_WBA_NOR_RECORDING_BASE&&
        base<=COMP_WBA_NOR_TOTAL_BYTES&&bytes<=COMP_WBA_NOR_TOTAL_BYTES-base;
}
static bool page_prepare_body(void*c,uint32_t at)
{
    (void)c;if(disconnected||failed||!claimed_bytes||at>=claimed_bytes)return false;
    uint32_t sector=at&~4095u;
    if(sector>=erased_end) {
        if(!ahead_drain()||disconnected)return false;
        if(sector<erased_end)return true;
        uint32_t bytes=comp_wba_simple_payload_erase_bytes(claimed_base,claimed_bytes,sector);
        if(!bytes||!erase(claimed_base+sector,bytes))return false;
        erased_end=sector+bytes;keep_alive();
    }
    return !disconnected;
}
static bool page_prepare(void*c,uint32_t at)
{
    uint32_t start=ota_clock_us();bool ok=page_prepare_body(c,at);
    program_observe_add(&program_diagnostics.data_prepare_us,ota_clock_us()-start);return ok;
}
static bool page_program(void*c,uint32_t at,const uint8_t*p,size_t n)
{
    (void)c;return !disconnected&&!failed&&ahead_program_access(at,n)&&
        program(claimed_base+at,p,n)&&!disconnected;
}
static size_t page_following(void*c,uint32_t at,uint8_t*p,size_t n)
{
    (void)c;return comp_v11_ota_gatt_copy_following_data(at,transfer.expected_size,
        transfer.chunk_payload_bytes,p,n);
}
static bool write_stream(void*c,const uint8_t*p,size_t n)
{
    (void)c;uint32_t at=transfer.bytes_written;
    if(!claimed_bytes||at>claimed_bytes||n>claimed_bytes-at||disconnected)return false;
    const comp_ota_page_ports_t ports={NULL,page_prepare,page_program,page_following};
    return comp_ota_page_stream_write(&ports,&physical_prefix,at,p,n,transfer.expected_size);
}
static bool finish_stream(void*c)
{
    (void)c;uint8_t h[COMP_WBA_SIMPLE_HEADER_BYTES],scratch[512];
    comp_wba_simple_package_t package;comp_wba_simple_limits_t g=limits();
    if(disconnected||failed||!powered_idle()||!ahead_drain()||!read_nor(claimed_base,h,sizeof(h))||
       !comp_wba_simple_package_open(&package,h,sizeof(h),&g)||
       !comp_wba_simple_package_newer(&package,COMPANION_WBA_APP_VERSION,product->resources.generation.root.generation)||
       144u+package.signed_manifest.manifest.size_bytes!=transfer.expected_size)return false;
    uint32_t crc=0;
    for(uint32_t at=0;at<transfer.expected_size;) {
        size_t n=transfer.expected_size-at;if(n>sizeof(scratch))n=sizeof(scratch);
        if(disconnected||!read_nor(claimed_base+at,scratch,n))return false;
        crc=comp_wba_recording_crc32(crc,scratch,(uint32_t)n);at+=(uint32_t)n;keep_alive();
    }
    if(disconnected||crc!=transfer.image_crc32)return false;
    uint8_t pending[COMP_SIMPLE_PENDING_BYTES];
    if(!comp_wba_simple_pending_record(pending,claimed_base,transfer.expected_size,h))return false;
    /* From the first publication write, an I/O failure may still have left
     * a valid pending record. Keep the package claim through reboot; ABORT
     * must not lend those bytes back to recording under a pending install. */
    prepared=true;prepared_ms=HAL_GetTick();
    if(!erase(COMP_SIMPLE_PENDING,4096u)||!program(COMP_SIMPLE_PENDING,pending,sizeof(pending))||
       !read_nor(COMP_SIMPLE_PENDING,scratch,sizeof(pending))||memcmp(pending,scratch,sizeof(pending)))return false;
    /* Receipt means fully retained, not authenticated/installed. Boot alone
     * verifies P-256 + whole-payload SHA before destination erasure. */
    return true;
}
static void connection(void*c,bool encrypted)
{(void)c;if(!encrypted)disconnected=true;}
static void *queue_workspace(void*c,size_t n)
{(void)c;return idle()?companion_opus16_rt_workspace_borrow(n):NULL;}
static void queue_release(void*c,void*p)
{(void)c;companion_opus16_rt_workspace_release(p);}
static uint32_t queue_clock(void*c){(void)c;return HAL_GetTick();}
static bool control(void*c,const uint8_t*b,size_t n)
{
    (void)c;if(!ready||!b||n<20u||memcmp(b,"DOV1",4u)||b[6]||b[7]||prepared)return false;
    if(b[4]!=DENZIC_OTA_V1_OP_ABORT&&!powered_idle())return false;
    if(b[4]==DENZIC_OTA_V1_OP_BEGIN) {
        /* Every BEGIN is a fresh file, including same-package retries. */
        /* Retire an older disconnect before cleanup. The physical erase can
         * yield to BLE; a new disconnect during that wait must remain latched
         * and must prevent this stale BEGIN from claiming a new workspace. */
        disconnected=false;
        abort_stream(NULL);denzic_ota_v1_reset(&transfer);
        if(failed||disconnected)return false;
    }
    bool ok=denzic_ota_v1_handle_control(&transfer,b,n);
    /* begin_stream can itself yield while releasing or claiming storage. A
     * lost owner must not publish a successfully confirmed new session. */
    if(b[4]==DENZIC_OTA_V1_OP_BEGIN && disconnected) {
        /* Do not expose a receiving state from the disconnected owner if a
         * replacement connection arrives before the next foreground turn. */
        abort_stream(NULL);denzic_ota_v1_reset(&transfer);return false;
    }
    if(ok&&b[4]==DENZIC_OTA_V1_OP_BEGIN)
        denzic_ota_v1_set_status_flags(&transfer,DENZIC_OTA_V1_STATUS_FLAG_ACTIVE_LINK_CONFIRMED);
    if(ok)activity_ms=HAL_GetTick();
    return ok;
}
static bool data(void*c,const uint8_t*b,size_t n)
{
    (void)c;if(!ready||!b||n<=4u||n>COMP_V11_OTA_VALUE_BYTES||!powered_idle()||disconnected||prepared)return false;
    bool ok=denzic_ota_v1_handle_data(&transfer,b,n);
    if(ok)activity_ms=HAL_GetTick();
    return ok;
}
static size_t status(void*c,uint8_t*b,size_t n)
{
    (void)c;denzic_ota_v1_context_t copy=transfer;copy.status_flags|=0x80u;
    if(!ready||failed){copy.state=DENZIC_OTA_V1_STATE_ERROR;copy.last_error=DENZIC_OTA_V1_ERROR_STORAGE_BEGIN;}
    return denzic_ota_v1_encode_status(&copy,b,n);
}
static bool mount_current(void)
{
    uint8_t record[COMP_SIMPLE_PENDING_BYTES];bool found=false;
    comp_wba_simple_package_t p;comp_wba_simple_limits_t g=limits();
    for(unsigned i=0;i<2;i++) {
        if(!read_nor(i?COMP_SIMPLE_CURRENT_B:COMP_SIMPLE_CURRENT_A,record,COMP_SIMPLE_CURRENT_BYTES))return false;
        if(memcmp(record,"SCU3",4u)||record[4]!=3u||record[5]||record[6]!=192u||record[7]||u32(record+8)||
           u32(record+188)!=comp_wba_update_wire_crc32(record,188u))continue;
        if(!comp_wba_simple_package_open(&p,record+12u,176u,&g)||
           p.signed_manifest.manifest.component_version!=COMPANION_WBA_APP_VERSION||
           p.resource_version!=product->resources.generation.root.generation)continue;
        if(found&&memcmp(installed_hash,p.signed_manifest.manifest.sha256,32u))return false;
        memcpy(installed_hash,p.signed_manifest.manifest.sha256,32u);found=true;
    }
    if(!found||!read_nor(COMP_SIMPLE_PENDING,record,sizeof(record)))return false;
    for(size_t i=0;i<sizeof(record);i++)if(record[i]!=255u)return false;
    return release_claim();
}
const comp_v11_update_diagnostics_t *comp_v11_update_product_diagnostics(void){return &diagnostics;}
bool comp_v11_update_product_init(comp_v11_product_app_t*app)
{
    if(!app)return false;
    product=app;ready=initialization_done=initializing=prepared=disconnected=failed=reboot_gatt_stored=false;
    claimed_base=claimed_bytes=erased_end=prepared_ms=physical_prefix=ahead_bytes=ahead_started_ms=0u;activity_ms=HAL_GetTick();
    memset(&diagnostics,0,sizeof(diagnostics));memset(installed_hash,0,sizeof(installed_hash));
    denzic_ota_v1_storage_driver_t d={begin_stream,write_stream,finish_stream,abort_stream};
    denzic_ota_v1_init(&transfer,d,NULL,COMP_V11_OTA_FILE_BYTES,COMP_V11_OTA_WINDOW_CHUNKS);
    const comp_v11_ota_gatt_ports_t p={control,data,status,NULL,queue_workspace,queue_release,queue_clock,connection};
    return comp_v11_ota_gatt_init(&p);
}
bool comp_v11_update_product_owns_erase(void)
{
    if(!product||!ahead_bytes||claimed_base<COMP_WBA_NOR_RECORDING_BASE||
       claimed_base>COMP_WBA_NOR_TOTAL_BYTES||claimed_bytes>COMP_WBA_NOR_TOTAL_BYTES-claimed_base||
       ahead_bytes>claimed_bytes||erased_end>claimed_bytes-ahead_bytes)return false;
    const companion_spi_nor_stm32wba_t *n=&product->board->nor;
    return n->erase_active&&n->erase_address==claimed_base+erased_end&&n->erase_bytes==ahead_bytes;
}
bool comp_v11_update_product_busy(void)
{return initializing||prepared||claimed_bytes||transfer.state==DENZIC_OTA_V1_STATE_RECEIVING;}
bool comp_v11_update_product_reboot_pending(void)
{return prepared;}
bool comp_v11_update_product_bulk_transfer(void)
{return ready&&!prepared&&!failed&&powered_idle()&&transfer.state==DENZIC_OTA_V1_STATE_RECEIVING;}
uint16_t comp_v11_update_product_screen_status(void)
{
    uint8_t phase=COMP_RUNTIME_UPDATE_NONE,pct=255;
    if(failed)phase=COMP_RUNTIME_UPDATE_FAILED;
    else if(prepared)phase=COMP_RUNTIME_UPDATE_RESTARTING;
    else if(transfer.state==DENZIC_OTA_V1_STATE_RECEIVING) {
        phase=COMP_RUNTIME_UPDATE_RECEIVING;
        if(transfer.expected_size)pct=(uint8_t)((transfer.bytes_written*100u/transfer.expected_size)/5u*5u);
    }
    return phase?(uint16_t)(phase|((uint16_t)pct<<8)):0u;
}
void comp_v11_update_product_readiness(companion_gatt_ota_readiness_v1_t*out)
{
    memset(out,0,sizeof(*out));out->schema_version=1;out->battery_percent=255;out->blocker_bitmap=ready?0u:1u;
    comp_wba_power_snapshot_t power=comp_wba_power_monitor_snapshot(product?&product->board->power_monitor:NULL,HAL_GetTick());
    out->battery_percent=power.percent;out->minimum_required_mv=product?product->board->power_monitor.profile.minimum_update_mv:0u;
    out->blocker_bitmap|=comp_wba_ota_admission_power_blockers(product?&product->board->power_monitor:NULL,HAL_GetTick());
    if(!idle()||prepared)out->blocker_bitmap|=2u;
    out->ready_state=out->blocker_bitmap?0u:1u;
    out->manifest_version=COMPANION_WBA_APP_VERSION;out->image_size=0u;
    if(ready)memcpy(out->image_sha256_prefix,installed_hash,sizeof(out->image_sha256_prefix));
}
static void reboot_when_nvm_durable(uint32_t now)
{
    if(!prepared || failed || now-prepared_ms<2000u || !powered_idle())return;
    if(!reboot_gatt_stored) {
        /* A successful snapshot starts the existing asynchronous NVM owner.
         * Yield one foreground turn; never reset on command success alone. */
        reboot_gatt_stored=comp_v11_ble_store_gatt_for_reboot();
        return;
    }
    if(!comp_v11_ble_nvm_busy())NVIC_SystemReset();
}
static void update_product_poll_owned(void)
{
    uint32_t now=HAL_GetTick();if(!product)return;
    if(disconnected&&!prepared) {
        abort_stream(NULL);denzic_ota_v1_reset(&transfer);disconnected=false;
        comp_v11_ota_gatt_status_changed();
    }
    if(!initialization_done&&product->recording.media_ready&&comp_wba_recording_product_space_current(&product->recording)) {
        initialization_done=true;initializing=true;ready=mount_current();initializing=false;
        comp_v11_ota_gatt_status_changed();
        comp_v11_product_recording_lease_result(product,ready);
    }
    comp_v11_ota_gatt_poll_slice();
    bool failed_before=failed;
    ahead_background();
    if(failed!=failed_before)comp_v11_ota_gatt_status_changed();
    /* Control/DATA callbacks update activity_ms (and FINISH prepared_ms).
     * NOR work can advance the tick during that poll. The earlier sample
     * minus a later callback timestamp wraps to ~UINT32_MAX and falsely
     * expires a brand-new receive/reboot delay. Sample AFTER callbacks. */
    now=HAL_GetTick();
    if(!ready)return;
    if(!prepared&&transfer.state==DENZIC_OTA_V1_STATE_RECEIVING&&now-activity_ms>120000u) {
        abort_stream(NULL);denzic_ota_v1_reset(&transfer);
        comp_v11_ota_gatt_status_changed();
    }
    uint8_t identity[COMP_V11_OTA_IDENTITY_BYTES];
#if COMP_V11_OTA_TARGET_BOUND_IDENTITY
    memcpy(identity,"WSI4",4);put32(identity+56,COMP_WBA_UPDATE_BOARD_COMPANION_V11);
#else
    memcpy(identity,"WSI3",4);
#endif
    put32(identity+4,COMPANION_WBA_APP_VERSION);
    put32(identity+8,product->resources.generation.root.generation);put32(identity+12,COMP_WBA_NOR_UI_BYTES);
    put32(identity+16,claimed_bytes);put32(identity+20,
        (product->recording_ready||(comp_wba_recording_product_salvaging(&product->recording)&&
        comp_wba_recording_product_readable(&product->recording)))&&!failed&&!prepared?1u:0u);
    memcpy(identity+24,installed_hash,32);comp_v11_ota_gatt_identity(identity);
    reboot_when_nvm_durable(now);
}

void comp_v11_update_product_poll(void)
{
    if(!product)return;
    uint8_t previous=comp_v11_ota_gatt_wall_context(COMP_OTA_WALL_UPDATE_OTHER);
    update_product_poll_owned();
    (void)comp_v11_ota_gatt_wall_context(previous);
}
