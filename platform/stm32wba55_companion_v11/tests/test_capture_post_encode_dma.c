#include "product_app.h"
#include "capture_encode_window.h"
#include "companion_recording_wire.h"
#include "wba_storage_layout.h"
#include "wba_shared_pool.h"
#include "wba_flash_migration.h"
#include "wba_workspace_layout.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define FLASH_BYTES 0x01000000u
#define STEP_MS 10u

typedef struct {
    uint8_t *flash;
    uint32_t tick;
    uint32_t speaker_submits;
    uint32_t speaker_completions;
    uint32_t speaker_submits_while_recording;
    uint32_t mic_starts;
    uint32_t mic_stops;
    uint32_t first_mic_start_after_speaker_blocks;
    uint32_t pcm_sequence;
    bool key_pressed;
    bool amplifier_enabled;
    bool rng_unavailable;
    bool fail_identity_program;
    bool mic_before_durable_identity;
    uint32_t identity_writes_during_capture;
    uint32_t resource_read_ms,resource_reads,last_audio_tick,microphone_poll_ms;
    bool pending_pcm_before_resource;
    bool early_checkpoint_timing;
    bool dma_model;
    uint32_t next_ready, codec_ms;
    companion_screen_assets_stm32wba_config_t resources;
} fixture_t;

static fixture_t fixture;
static comp_v11_hal_t *active_board;
static comp_v11_product_app_t *active_app;

static int fail(const char *message)
{
    fprintf(stderr, "FAIL_WBA_PRODUCT_RECORDING_INTEGRATION %s\n", message);
    return 2;
}

#define REQUIRE(condition, message) \
    do { if (!(condition)) return fail(message); } while (0)

uint32_t HAL_GetTick(void)
{
    return fixture.tick;
}

bool comp_v11_hal_key_pressed(void)
{
    return fixture.key_pressed;
}

bool comp_v11_hal_random_u32(comp_v11_hal_t *board, uint32_t *value)
{
    (void)board;
    if (value == NULL || fixture.rng_unavailable) return false;
    *value = 0x94D049BBu ^ fixture.tick;
    return true;
}
bool comp_v11_hal_device_uid(uint8_t uid[12])
{
    if(!uid)return false;
    for(size_t i=0u;i<12u;i++)uid[i]=(uint8_t)(i+1u);
    return true;
}

bool comp_v11_hal_set_pcm_sink(comp_v11_hal_t *board,
                               comp_wba_pdm_pcm_frame_fn_t sink,
                               void *context)
{
    if (board == NULL) return false;
    board->pcm_sink = sink;
    board->pcm_sink_context = context;
    return true;
}

bool comp_v11_hal_microphone_profile(comp_v11_hal_t *board,uint8_t profile ,bool allow_directional)
{(void)allow_directional; return board!=NULL && !board->microphone.running && profile<=1u; }

bool comp_v11_hal_microphone_enable(comp_v11_hal_t *board, bool enabled)
{
    if (board == NULL || !board->microphone.initialized) return false;
    if (enabled && !board->microphone.running) {
        uint64_t session = 0u;
        if (active_app == NULL || !active_app->recording_identity.loaded ||
                !(session=active_app->recording.capture.engine.active.descriptor.session_id) ||
                session != active_app->recording_session_id ||
                session >= active_app->recording_identity.record.next_session_id)
            fixture.mic_before_durable_identity = true;
        if (active_app != NULL) for (uint32_t bank = 0u; bank < 2u; bank++) {
            const comp_rec_identity_t *identity = &active_app->recording_identity;
            if (!identity->next_slot[bank]) {
                fixture.mic_before_durable_identity = true;
                continue;
            }
            const uint8_t *p = fixture.flash + COMP_WBA_NOR_RECORDING_IDENTITY_BASE +
                bank * COMP_REC_IDENTITY_BANK_BYTES +
                ((uint32_t)identity->next_slot[bank] - 1u) * COMP_REC_IDENTITY_SLOT_BYTES;
            if (memcmp(p, "CSI1", 4u) || comp_rec_get64(p + 8u) != identity->record.sequence ||
                    comp_rec_get32(p + 156u) != comp_rec_crc(p, 156u))
                fixture.mic_before_durable_identity = true;
        }
        fixture.mic_starts++;
        if (fixture.mic_starts == 1u) {
            fixture.first_mic_start_after_speaker_blocks =
                fixture.speaker_completions;
        }
    }
    if (!enabled && board->microphone.running) fixture.mic_stops++;
    fixture.last_audio_tick=fixture.tick;
    fixture.next_ready=fixture.tick+10u;
    board->microphone.running = enabled;
    return true;
}

void comp_v11_microphone_hal_get_stats(
    comp_v11_microphone_hal_t *microphone,
    comp_v11_microphone_stats_t *stats)
{
    if (microphone == NULL || stats == NULL) return;
    memset(stats, 0, sizeof(*stats));
    stats->initialized = microphone->initialized;
    stats->running = microphone->running;
    stats->stale_dma_halves = microphone->stale_dma_halves;
    stats->event_queue_overflows = microphone->event_queue_overflows;
    stats->processing_rejections = microphone->processing_rejections;
    stats->error_irqs = microphone->error_irqs;
}

#include "microphone_capture_match_fake.h"

static bool amplifier(void *context, bool enabled)
{
    (void)context;
    fixture.amplifier_enabled = enabled;
    return true;
}

static bool submit_i2s(void *context, const int16_t *pcm, size_t frames)
{
    comp_v11_hal_t *board = context;
    if (board == NULL || pcm == NULL || frames != COMP_SPEAKER_BLOCK_FRAMES)
        return false;
    fixture.speaker_submits++;
    if (board->microphone.running) fixture.speaker_submits_while_recording++;
    return true;
}

static void playback_active(void *context, bool active)
{
    comp_v11_hal_t *board = context;
    if (board != NULL) board->playback_active = active;
}

bool comp_v11_hal_set_idle_peripherals(comp_v11_hal_t *board, bool idle)
{
    board->idle_peripherals=idle;
    return true;
}
comp_ssd1681_wba_status_t comp_ssd1681_wba_status(const comp_ssd1681_wba_t *panel)
{ (void)panel; return COMP_SSD1681_WBA_IDLE; }

void comp_v11_hal_speaker_poll(comp_v11_hal_t *board)
{
    if (board == NULL) return;
    if (board->speaker.tx_pending) {
        comp_speaker_tx_complete(&board->speaker, true);
        fixture.speaker_completions++;
    }
    (void)comp_speaker_service(&board->speaker);
}
void comp_v11_hal_poll(comp_v11_hal_t *board)
{
    if(board==NULL)return;
    comp_v11_hal_speaker_poll(board);
    if(fixture.dma_model)(void)comp_v11_microphone_hal_poll(&board->microphone);
}
comp_v11_microphone_poll_result_t comp_v11_microphone_hal_poll(comp_v11_microphone_hal_t *microphone)
{
    if(!microphone || !microphone->running || !fixture.dma_model ||
       (int32_t)(fixture.tick-fixture.next_ready)<0)return COMP_V11_MIC_POLL_IDLE;
    uint32_t age=fixture.tick-fixture.next_ready;
    if(age+fixture.microphone_poll_ms>=10u) {
        microphone->stale_dma_halves++;
        return COMP_V11_MIC_POLL_DROPPED;
    }
    fixture.next_ready+=10u;
    fixture.tick+=fixture.microphone_poll_ms;
    int16_t pcm[160];for(unsigned i=0;i<160;i++)pcm[i]=(int16_t)(i*40u);
    if(!active_board->pcm_sink(active_board->pcm_sink_context,pcm,160u,16000u)) {
        microphone->processing_rejections++;
        return COMP_V11_MIC_POLL_DROPPED;
    }
    microphone->processed_dma_halves++;
    return COMP_V11_MIC_POLL_PROCESSED;
}


bool companion_spi_nor_stm32wba_partition_init(
    companion_spi_nor_stm32wba_partition_t *partition,
    companion_spi_nor_stm32wba_t *nor,
    uint32_t base_address,
    uint32_t size_bytes)
{
    if (partition == NULL || nor == NULL || base_address > FLASH_BYTES ||
        size_bytes > FLASH_BYTES - base_address) return false;
    partition->nor = nor;
    partition->base_address = base_address;
    partition->size_bytes = size_bytes;
    return true;
}

bool companion_spi_nor_stm32wba_partition_read(
    void *context, uint32_t offset, uint8_t *destination, size_t length)
{
    companion_spi_nor_stm32wba_partition_t *partition = context;
    if (partition == NULL || destination == NULL ||
        offset > partition->size_bytes || length > partition->size_bytes - offset)
        return false;
    memcpy(destination, fixture.flash + partition->base_address + offset, length);
    if(partition->base_address==0u && fixture.resource_read_ms) {
        if(fixture.resource_reads==0u)
            fixture.pending_pcm_before_resource=active_app->recording.capture.engine.ring_count!=0u;
        fixture.tick+=fixture.resource_read_ms;
        fixture.resource_reads++;
    }
    return true;
}

companion_spi_nor_stm32wba_status_t
companion_spi_nor_stm32wba_partition_program(
    companion_spi_nor_stm32wba_partition_t *partition,
    uint32_t offset, const uint8_t *source, size_t length)
{
    uint8_t *destination;
    if (partition == NULL || source == NULL || offset > partition->size_bytes ||
        length > partition->size_bytes - offset)
        return COMPANION_SPI_NOR_STM32WBA_OUT_OF_RANGE;
    if (partition->base_address == COMP_WBA_NOR_RECORDING_IDENTITY_BASE) {
        if (active_board->microphone.running) fixture.identity_writes_during_capture++;
        if (fixture.fail_identity_program) return COMPANION_SPI_NOR_STM32WBA_ERROR;
    }
    destination = fixture.flash + partition->base_address + offset;
    for (size_t i = 0u; i < length; ++i) {
        if ((destination[i] & source[i]) != source[i])
            return COMPANION_SPI_NOR_STM32WBA_ERROR;
        destination[i] &= source[i];
    }
    return COMPANION_SPI_NOR_STM32WBA_OK;
}

companion_spi_nor_stm32wba_status_t
companion_spi_nor_stm32wba_partition_erase_4k(
    companion_spi_nor_stm32wba_partition_t *partition, uint32_t offset)
{
    if (partition == NULL || (offset % 4096u) != 0u ||
        offset > partition->size_bytes || 4096u > partition->size_bytes - offset)
        return COMPANION_SPI_NOR_STM32WBA_OUT_OF_RANGE;
    if (partition->base_address == COMP_WBA_NOR_RECORDING_IDENTITY_BASE &&
            active_board->microphone.running) fixture.identity_writes_during_capture++;
    memset(fixture.flash + partition->base_address + offset, 0xFF, 4096u);
    return COMPANION_SPI_NOR_STM32WBA_OK;
}

/* Display resources are intentionally unavailable in this recording-only
 *
 * The NOR step below represents completed physical storage; byte-exact
 * command/pending/failure behavior is covered by the real NOR adapter fixture.
 */
companion_spi_nor_stm32wba_status_t companion_spi_nor_stm32wba_partition_erase_step(
    companion_spi_nor_stm32wba_partition_t *partition,uint32_t offset,
    uint32_t remaining,uint32_t *erased)
{
    if(!erased)return COMPANION_SPI_NOR_STM32WBA_BAD_PARAM;
    *erased=0u;
    if(!partition || remaining<4096u || remaining%4096u || offset%4096u ||
       offset>partition->size_bytes || remaining>partition->size_bytes-offset)
        return COMPANION_SPI_NOR_STM32WBA_OUT_OF_RANGE;
    uint32_t bytes=(partition->base_address+offset)%65536u==0u && remaining>=65536u?65536u:4096u;
    memset(fixture.flash+partition->base_address+offset,255,bytes);*erased=bytes;
    return COMPANION_SPI_NOR_STM32WBA_OK;
}

/* Display resources are intentionally unavailable in this recording-only
 * board integration fixture.  Product recording, timing, and storage code is
 * real; these stubs keep the test independent of a 2 MiB authored asset pack. */
void comp_runtime_renderer_init(comp_runtime_renderer_t *renderer,
    comp_runtime_read_state_fn read_state, void *context)
{
    memset(renderer, 0, sizeof(*renderer));
    renderer->read_state = read_state;
    renderer->context = context;
}

bool comp_runtime_renderer_render(void *context,
    const comp_runtime_frame_t *request, uint8_t frame[5000])
{
    (void)context; (void)request; (void)frame;
    return false;
}

bool comp_runtime_renderer_complete(comp_runtime_renderer_t *renderer,
    uint32_t token, bool visible)
{
    (void)renderer; (void)token; (void)visible;
    return false;
}

bool comp_runtime_resources_mount(comp_runtime_resources_t *resources,
                                  const comp_asset_store_t *store)
{
    (void)resources; (void)store;
    return false;
}

bool comp_runtime_resources_read(void *context, const char *state_id,
                                 uint8_t frame[5000])
{
    (void)context; (void)state_id; (void)frame;
    return false;
}

void companion_screen_assets_stm32wba_init(
    companion_screen_assets_stm32wba_t *adapter)
{
    if (adapter != NULL) memset(adapter, 0, sizeof(*adapter));
}

bool companion_screen_assets_stm32wba_bind(
    companion_screen_assets_stm32wba_t *adapter, comp_asset_store_t *store,
    const companion_screen_assets_stm32wba_config_t *config)
{
    (void)adapter; (void)store;
    fixture.resources=*config;
    return false;
}

bool companion_screen_assets_stm32wba_set_cache(
    companion_screen_assets_stm32wba_t *adapter, uint8_t *buffer,
    size_t capacity)
{
    (void)adapter; (void)buffer; (void)capacity;
    return false;
}

bool comp_screen_presenter_wba_init(comp_screen_presenter_wba_t *presenter,
    const comp_screen_presenter_wba_config_t *config)
{
    if (presenter == NULL || config == NULL) return false;
    memset(presenter, 0, sizeof(*presenter));
    presenter->config = *config;
    presenter->status = COMP_SCREEN_PRESENTER_WBA_NOT_READY;
    return true;
}

comp_screen_presenter_wba_status_t comp_screen_presenter_wba_service(
    comp_screen_presenter_wba_t *presenter, uint32_t now_ms)
{
    (void)now_ms;
    if(fixture.early_checkpoint_timing&&active_board->microphone.running)fixture.tick+=3u;
    return presenter == NULL ? COMP_SCREEN_PRESENTER_WBA_NOT_READY :
                               presenter->status;
}

comp_screen_presenter_wba_submit_result_t comp_screen_presenter_wba_submit(
    comp_screen_presenter_wba_t *presenter,
    const comp_runtime_frame_t *request, uint32_t now_ms)
{
    (void)presenter; (void)request; (void)now_ms;
    return COMP_SCREEN_PRESENTER_WBA_SUBMIT_BAD_ARGUMENT;
}

/* Board/device/storage below are models. The app/runtime/continuous engine,
 * durable catalogs/session allocator, cue ordering and deadline are real code.
 * NOR suspension semantics are checked separately with the command model. */
bool companion_spi_nor_stm32wba_ready(const companion_spi_nor_stm32wba_t *nor)
{return nor!=NULL&&nor->info.size_bytes==FLASH_BYTES;}
companion_spi_nor_stm32wba_status_t companion_spi_nor_stm32wba_read(
    companion_spi_nor_stm32wba_t *nor,uint32_t address,uint8_t *p,size_t n)
{
    if(!nor||!p||address>FLASH_BYTES||n>FLASH_BYTES-address)return COMPANION_SPI_NOR_STM32WBA_BAD_PARAM;
    memcpy(p,fixture.flash+address,n);return COMPANION_SPI_NOR_STM32WBA_OK;
}
companion_spi_nor_stm32wba_status_t companion_spi_nor_stm32wba_program(
    companion_spi_nor_stm32wba_t *nor,uint32_t address,const uint8_t *p,size_t n)
{
    companion_spi_nor_stm32wba_partition_t whole={nor,0u,FLASH_BYTES};
    return companion_spi_nor_stm32wba_partition_program(&whole,address,p,n);
}
companion_spi_nor_stm32wba_status_t companion_spi_nor_stm32wba_erase_step(
    companion_spi_nor_stm32wba_t *nor,uint32_t at,uint32_t n)
{
    if(!nor||at%4096u||n%4096u||at>FLASH_BYTES||n>FLASH_BYTES-at)return COMPANION_SPI_NOR_STM32WBA_BAD_PARAM;
    memset(fixture.flash+at,255u,n);return COMPANION_SPI_NOR_STM32WBA_OK;
}
bool companion_spi_nor_stm32wba_erase_access_ready(const companion_spi_nor_stm32wba_t *nor,uint32_t at,size_t n)
{(void)at;(void)n;return nor&&!nor->erase_active;}
companion_spi_nor_stm32wba_status_t companion_spi_nor_stm32wba_erase_suspend_step(companion_spi_nor_stm32wba_t *nor)
{(void)nor;return COMPANION_SPI_NOR_STM32WBA_UNSUPPORTED;}
companion_spi_nor_stm32wba_status_t companion_spi_nor_stm32wba_erase_suspend_step_bounded(
    companion_spi_nor_stm32wba_t *nor,uint32_t budget_ms)
{(void)budget_ms;return companion_spi_nor_stm32wba_erase_suspend_step(nor);}
bool comp_v11_microphone_hal_encode_window(comp_v11_microphone_hal_t *mic)
{
    if(!mic || !mic->running)return false;
    if(!fixture.dma_model)return true;
    /* Same counter/IRQ publication contract: 10ms halves, >4ms guard. */
    uint32_t remaining=fixture.next_ready-fixture.tick;
    return (int32_t)remaining>0 && comp_v11_capture_encode_window_open(
        remaining*384u,3840u,1u,false);
}
void model_codec_elapsed(uint32_t frames)
{if(fixture.dma_model)fixture.tick+=frames*fixture.codec_ms;}

bool comp_v11_hal_take_key_wake(comp_v11_hal_t *board)
{(void)board;return false;}
comp_wba_button_edges_t comp_v11_hal_take_key_edges(comp_v11_hal_t *board)
{
    comp_wba_button_edges_t edge={board->wake_events.key_down_ms,board->wake_events.key_up_ms,
        (uint8_t)(board->wake_events.key_pending>>1u),comp_v11_hal_key_pressed()};
    board->wake_events.key_pending=0u;return edge;
}
void comp_runtime_renderer_set_progress(comp_runtime_renderer_t *renderer,
    comp_runtime_render_progress_fn callback,void *context)
{(void)renderer;(void)callback;(void)context;}
void comp_v11_hal_log(const char *message)
{(void)message;}
void comp_v11_hal_panel_failure_diagnostic(comp_v11_hal_t *board)
{(void)board;}
bool comp_screen_presenter_wba_ready_for_frame(const comp_screen_presenter_wba_t *presenter,
    uint32_t now_ms)
{(void)presenter;(void)now_ms;return false;} /* Display is outside this fixture. */

/* Keep excluded display/service ports explicit as the product evolves. None
 * of these fakes advances/qualifies an optical frame or a pet/chat outcome. */
bool comp_v11_hal_panel_busy(void){return false;}
bool comp_v11_hal_touch_pending(void){return false;}
bool comp_ssd1681_wba_read_frame(comp_ssd1681_wba_t *panel,const uint8_t *frame,
    size_t offset,uint8_t *out,size_t size)
{(void)panel;(void)frame;(void)offset;(void)out;(void)size;return false;}
void comp_runtime_renderer_set_ui_reader(comp_runtime_renderer_t *r,comp_runtime_read_ui_fn reader)
{(void)r;(void)reader;}
bool comp_runtime_resources_read_ui(void *context,uint32_t offset,uint8_t *out,size_t size)
{(void)context;(void)offset;(void)out;(void)size;return false;}
bool comp_screen_presenter_wba_debug_replay_baseline(comp_screen_presenter_wba_t *p,uint32_t now)
{(void)p;(void)now;return false;}
bool comp_screen_presenter_wba_debug_replay_quick_full(comp_screen_presenter_wba_t *p,uint32_t now)
{(void)p;(void)now;return false;}
bool comp_screen_presenter_wba_debug_replay_flashing_full(comp_screen_presenter_wba_t *p,uint32_t now)
{(void)p;(void)now;return false;}
bool comp_screen_presenter_wba_debug_replay_same_partial(comp_screen_presenter_wba_t *p,uint32_t now)
{(void)p;(void)now;return false;}
bool comp_v11_product_render_pet_caption(comp_v11_product_app_t *app,const comp_runtime_frame_t *f,uint8_t frame[5000])
{(void)app;return comp_runtime_renderer_render(NULL,f,frame);}

static void layout_root(void)
{
    uint8_t p[64]={0};memcpy(p,"CFL3",4u);comp_rec_put32(p+4u,3u);comp_rec_put32(p+8u,64u);
    comp_rec_put32(p+12u,COMP_WBA_NOR_UI_BYTES);comp_rec_put32(p+16u,COMP_WBA_NOR_DYNAMIC_BASE);
    comp_rec_put32(p+20u,COMP_WBA_NOR_RECORDING_CATALOG);comp_rec_put32(p+24u,COMP_WBA_NOR_RECORDING_BASE);
    comp_rec_put32(p+28u,COMP_WBA_NOR_RECORDING_DATA_BYTES);comp_rec_put32(p+60u,comp_rec_crc(p,60u));
    memcpy(fixture.flash+COMP_WBA_NOR_LAYOUT_A,p,64u);memcpy(fixture.flash+COMP_WBA_NOR_LAYOUT_B,p,64u);
}
static void step(comp_v11_product_app_t *app,uint32_t count)
{
    for(uint32_t i=0u;i<count;i++) {
        fixture.tick+=STEP_MS;comp_v11_product_app_poll(app);
        if(!app->recording_ready&&comp_wba_recording_product_space_current(&app->recording)) {
            /* No BLE/PKA in this fixture. Simulate only the external boot
             * lease result; this cannot qualify actual WUS2 or signed OTA. */
            comp_v11_product_recording_lease_result(app,true);
        }
    }
}
static bool wait_state(comp_v11_product_app_t *app,uint8_t wanted,uint32_t limit)
{
    for(uint32_t i=0u;i<limit;i++) {
        if(comp_wba_recording_product_state(&app->recording)==wanted)return true;
        step(app,1u);
    }
    return comp_wba_recording_product_state(&app->recording)==wanted;
}
static void key(comp_v11_product_app_t *app,bool pressed,uint32_t count)
{fixture.key_pressed=pressed;step(app,count);}
static bool settled_space(comp_v11_product_app_t *app)
{
    for(uint32_t i=0u;i<20000u&&!comp_wba_recording_product_space_current(&app->recording);i++)step(app,1u);
    return comp_wba_recording_product_space_current(&app->recording);
}
static void init_board(comp_v11_product_app_t *app,comp_v11_hal_t *board)
{
    memset(board,0,sizeof(*board));active_board=board;active_app=app;
    board->microphone.initialized=true;board->nor.info.size_bytes=FLASH_BYTES;board->nor.erase_suspend_supported=true;
    comp_speaker_config_t speaker={amplifier,submit_i2s,playback_active,board};
    comp_speaker_init(&board->speaker,&speaker);board->speaker_ready=true;
    comp_v11_product_app_init(app,board,NULL);
}
static void measured_cell(comp_wba_power_monitor_t *m,uint16_t mv)
{
    m->value.voltage_valid=true;m->value.millivolts=mv;
    m->voltage_ms=fixture.tick;
}
static int power_guard_journey(const char *artifact_path)
{
    comp_v11_hal_t board;comp_v11_product_app_t app;
    memset(&fixture,0,sizeof(fixture));fixture.flash=malloc(FLASH_BYTES);
    REQUIRE(fixture.flash,"power fixture NOR allocation");
    memset(fixture.flash,255u,FLASH_BYTES);layout_root();init_board(&app,&board);
    REQUIRE(wait_state(&app,COMP_WBA_RECORDING_IDLE,20000u),"power fixture boot/lease");
    comp_wba_power_monitor_t *m=&board.power_monitor;
    m->profile=(comp_wba_power_profile_t){.top_ohm=150000u,.bottom_ohm=68000u,
        .reference_mv=1800u,.reference_min_mv=1700u,.minimum_battery_mv=2800u,
        .maximum_battery_mv=4350u,.minimum_update_mv=3600u,.adc_full_scale=4095u,
        .divider_verified=true,.reference_verified=true,.recording_stop_mv=3200u,
        .recording_resume_mv=3450u,.recording_limits_verified=true};
    m->sampling_enabled=true;
    REQUIRE(comp_wba_power_recording_limits_safe(&m->profile),"synthetic qualified limits rejected");
    REQUIRE(comp_runtime_record(&app.runtime,true,fixture.tick)==COMP_RUNTIME_UNAVAILABLE &&
        app.runtime.record_stop_reason==COMP_RECORD_STOP_POWER_UNKNOWN && !fixture.mic_starts,
        "unknown qualified voltage invented low battery or started capture");
    measured_cell(m,4000u);
    REQUIRE(comp_runtime_record(&app.runtime,true,fixture.tick)==COMP_RUNTIME_OK,"prepare power candidate");
    REQUIRE(wait_state(&app,COMP_WBA_RECORDING_READY,20000u),"prepare writer not ready");
    measured_cell(m,3100u); /* Voltage changed after admission, before actual MIC. */
    REQUIRE(wait_state(&app,COMP_WBA_RECORDING_TRANSFER_READY,20000u) && !fixture.mic_starts &&
        app.recording.capture.engine.state==COMP_CONT_CANCELED &&
        app.runtime.record_stop_reason==COMP_RECORD_STOP_LOW_BATTERY,
        "late denied MIC left an open reservation or fabricated saved audio");
    REQUIRE(settled_space(&app) && !app.recording.space.used,"denied prepared writer not reclaimed");
    measured_cell(m,4000u);comp_wba_power_monitor_recording_guard(m,fixture.tick);
    REQUIRE(comp_runtime_record(&app.runtime,true,fixture.tick)==COMP_RUNTIME_OK,"qualified normal start");
    REQUIRE(wait_state(&app,COMP_WBA_RECORDING_CAPTURING,20000u),"qualified MIC did not start");
    step(&app,60u);
    measured_cell(m,3100u);step(&app,1u);
    REQUIRE(board.microphone.running && m->recording_low_samples==1u,"single low sample stopped capture");
    step(&app,300u);
    REQUIRE(board.microphone.running && m->recording_low_samples==1u,"cached low sample counted twice");
    m->value.voltage_valid=false;step(&app,1u);
    REQUIRE(board.microphone.running && !m->recording_low_samples,"unknown gap confirmed a low sample");
    measured_cell(m,3100u);step(&app,1u);
    step(&app,500u); /* Same real source timestamp through many foreground polls. */
    REQUIRE(board.microphone.running && m->recording_low_samples==1u,"poll count replaced sample count");
    measured_cell(m,3100u);step(&app,1u);
    REQUIRE(m->recording_power_blocked && !board.microphone.running &&
        app.runtime.record_stop_reason==COMP_RECORD_STOP_LOW_BATTERY,"second fresh low sample did not stop");
    REQUIRE(wait_state(&app,COMP_WBA_RECORDING_TRANSFER_READY,20000u) &&
        app.runtime.recording==DENZIC_AUDIO_RECORDING_STATE_TRANSFER_READY && !app.runtime.capture_active,
        "low power stop bypassed ordinary asynchronous seal/drain");
    REQUIRE(comp_runtime_record_stop(&app.runtime,COMP_RECORD_STOP_REQUESTED,fixture.tick)==COMP_RUNTIME_OK &&
        app.runtime.record_stop_reason==COMP_RECORD_STOP_LOW_BATTERY,"late user STOP erased power cause");
    REQUIRE(settled_space(&app) && app.recording.space.logical==1u,"low stop lost logical recording");
    comp_segment_entry_t entry={0};bool found=false;
    for(uint8_t i=0u;i<64u&&!found;i++)if(app.recording.catalog.slots[i]!=255u) {
        REQUIRE(comp_wba_segment_storage_entry(&app.recording.storage,&app.recording.catalog,i,&entry)==COMP_SEG_OK,
            "low stop physical metadata");found=entry.state==COMP_SEG_UNSYNCED;
    }
    REQUIRE(found && (entry.descriptor.flags&COMP_REC_V2_LAST) &&
        (entry.descriptor.flags>>COMP_REC_V2_END_SHIFT)==COMP_REC_END_LOW_BATTERY &&
        entry.descriptor.sample_count && entry.descriptor.sample_count%320u==0u,
        "low stop not a complete sealed original");
    uint32_t starts=fixture.mic_starts;
    REQUIRE(comp_runtime_record(&app.runtime,true,fixture.tick)!=COMP_RUNTIME_OK &&
        fixture.mic_starts==starts,"critical latch permitted a new original");
    m->value.voltage_valid=false;step(&app,1u);
    REQUIRE(m->recording_power_blocked && !comp_wba_power_monitor_recording_allowed(m,fixture.tick),
        "unknown voltage cleared established protection");
    measured_cell(m,3350u);step(&app,1u);
    REQUIRE(m->recording_power_blocked,"voltage rebound below recovery cleared latch");
    measured_cell(m,3500u);step(&app,1u);step(&app,500u);
    REQUIRE(m->recording_power_blocked && m->recording_recovery_samples==1u,"cached recovery counted twice");
    measured_cell(m,3500u);step(&app,1u);
    REQUIRE(!m->recording_power_blocked && comp_wba_power_monitor_recording_allowed(m,fixture.tick) &&
        fixture.mic_starts==starts,"recovery failed or automatically reopened recording");
    comp_wba_power_monitor_t wrap={0};wrap.profile=m->profile;wrap.sampling_enabled=true;
    wrap.value.voltage_valid=true;wrap.value.millivolts=3100u;
    wrap.voltage_ms=UINT32_MAX-20u;comp_wba_power_monitor_recording_guard(&wrap,UINT32_MAX-10u);
    wrap.voltage_ms=0u;comp_wba_power_monitor_recording_guard(&wrap,1u);
    REQUIRE(wrap.recording_power_blocked,"fresh zero timestamp after wrap discarded");
    wrap.raw_diagnostic=true;comp_wba_power_monitor_recording_guard(&wrap,2u);
    REQUIRE(wrap.recording_power_blocked && !comp_wba_power_monitor_recording_allowed(&wrap,2u),
        "raw mode erased an established qualified latch");
    memset(&wrap,0,sizeof(wrap));wrap.profile=m->profile;wrap.raw_diagnostic=true;wrap.sampling_enabled=true;
    wrap.value.voltage_valid=true;wrap.value.millivolts=3100u;
    wrap.voltage_ms=1u;comp_wba_power_monitor_recording_guard(&wrap,1u);
    wrap.voltage_ms=2u;comp_wba_power_monitor_recording_guard(&wrap,2u);
    REQUIRE(!wrap.recording_power_blocked,"engineering raw data became protection evidence");
    wrap.raw_diagnostic=false;wrap.value.millivolts=4000u;wrap.profile.reference_verified=false;
    REQUIRE(!comp_wba_power_monitor_recording_allowed(&wrap,2u),
        "requested protection losing qualification silently became permissive engineering mode");
    wrap.profile.recording_limits_verified=false;
    REQUIRE(comp_wba_power_monitor_recording_allowed(&wrap,2u),
        "explicit no-protection default was confused with failed requested protection");
    memset(&wrap,0,sizeof(wrap));
    REQUIRE(comp_wba_power_monitor_recording_allowed(&wrap,0u),"unqualified production default regressed normal recording");
    FILE *artifact=fopen(artifact_path,"wb");REQUIRE(artifact,"power original artifact open");
    comp_segment_audio_port_t audio=comp_wba_segment_storage_audio_port(&app.recording.storage);
    companion_sha256_t hash;uint8_t digest[32];companion_sha256_init(&hash);
    uint32_t offset=0u,index=0u;
    while(offset<entry.descriptor.encoded_length) {
        uint8_t page[256],n;
        REQUIRE(comp_segment_audio_read_page(&audio,&entry,COMP_WBA_NOR_RECORDING_BASE,index++,page,&n)==COMP_SEG_OK,
            "power sealed page read");
        REQUIRE(fwrite(page,1u,n,artifact)==n,"power artifact write");
        companion_sha256_update(&hash,page,n);offset+=n;
    }
    REQUIRE(fclose(artifact)==0,"power artifact close");companion_sha256_final(&hash,digest);
    REQUIRE(offset==entry.descriptor.encoded_length && !memcmp(digest,entry.descriptor.sha256,32u),
        "low stop bytes did not match sealed SHA after blocked/recovery requests");
    uint8_t wire[COMP_REC_V2_DESCRIPTOR_BYTES];char metadata_path[512];
    REQUIRE(comp_rec_v2_encode(&entry.descriptor,wire,sizeof(wire)),"terminal cause descriptor encode");
    (void)snprintf(metadata_path,sizeof(metadata_path),"%s.descriptor",artifact_path);
    artifact=fopen(metadata_path,"wb");REQUIRE(artifact,"terminal cause metadata open");
    REQUIRE(fwrite(wire,1u,sizeof(wire),artifact)==sizeof(wire) && fclose(artifact)==0,"terminal cause metadata save");
    uint64_t original=entry.descriptor.session_id;uint8_t expected_flags=entry.descriptor.flags;
    init_board(&app,&board);REQUIRE(wait_state(&app,COMP_WBA_RECORDING_IDLE,20000u),"terminal cause normal remount");
    found=false;
    for(uint8_t i=0u;i<64u&&!found;i++)if(app.recording.catalog.slots[i]!=255u) {
        REQUIRE(comp_wba_segment_storage_entry(&app.recording.storage,&app.recording.catalog,i,&entry)==COMP_SEG_OK,
            "terminal cause remounted metadata");found=entry.descriptor.session_id==original;
    }
    REQUIRE(found && entry.descriptor.flags==expected_flags &&
        !memcmp(digest,entry.descriptor.sha256,32u),"normal remount lost reason or changed original SHA");
    puts("PASS_WBA_POWER_GUARD_PRODUCT_SOFTWARE_ONLY fresh-samples/unknown-gap/late-start-cancel/ordinary-seal/retained-SHA/critical-admission/hysteresis/no-auto-restart/wrap/raw-rejected");
    free(fixture.flash);return 0;
}
static int runtime_recovery_journey(void)
{
    comp_v11_hal_t board;comp_v11_product_app_t app;
    memset(&fixture,0,sizeof(fixture));fixture.flash=malloc(FLASH_BYTES);
    REQUIRE(fixture.flash,"recovery NOR allocation");
    memset(fixture.flash,255u,FLASH_BYTES);layout_root();init_board(&app,&board);
    REQUIRE(wait_state(&app,COMP_WBA_RECORDING_IDLE,20000u),"recovery boot lease");
    uint64_t epoch=app.recording_identity.record.format_epoch;
    REQUIRE(comp_runtime_record(&app.runtime,true,fixture.tick)==COMP_RUNTIME_OK,"first START");
    REQUIRE(wait_state(&app,COMP_WBA_RECORDING_CAPTURING,20000u),"first MIC");
    step(&app,60u);uint64_t old=app.recording_session_id;
    comp_wba_recording_product_fault(&app.recording,COMP_WBA_RECORDING_FAULT_DEADLINE);
    REQUIRE(!board.microphone.running&&!app.runtime.capture_active&&
        app.runtime.recording==DENZIC_AUDIO_RECORDING_STATE_ERROR_RECOVERY,"fault must really stop MIC");
    unsigned starts=fixture.mic_starts;
    for(unsigned i=0u;i<40u;i++)step(&app,1u);
    REQUIRE(app.recording.pipeline.state==COMP_PIPE_FAILED&&fixture.mic_starts==starts,"idle poll silently retried fault");
    REQUIRE(comp_runtime_record(&app.runtime,true,fixture.tick)==COMP_RUNTIME_OK&&
        app.runtime.prepare_pending&&!app.recording.media_ready&&!board.microphone.running,"retry must defer START to bounded recovery");
    REQUIRE(app.recording_identity.record.next_session_id==old+1u,"recovery allocated premature identity");
    REQUIRE(wait_state(&app,COMP_WBA_RECORDING_CAPTURING,30000u),"runtime retry did not resume through ordinary prepare");
    REQUIRE(app.recording_session_id==old+1u&&fixture.mic_starts==starts+1u&&
        app.recording_identity.record.format_epoch==epoch&&!fixture.mic_before_durable_identity&&
        !fixture.identity_writes_during_capture,"retry identity/one-start/namespace violated");
    step(&app,60u);
    REQUIRE(comp_runtime_record(&app.runtime,false,fixture.tick)==COMP_RUNTIME_OK,"normal STOP after retry");
    REQUIRE(wait_state(&app,COMP_WBA_RECORDING_TRANSFER_READY,30000u)&&!board.microphone.running,"retry capture did not save/STOP");
    REQUIRE(settled_space(&app)&&app.recording.space.logical==2u,"fault prefix or new recording missing");
    REQUIRE(comp_runtime_record(&app.runtime,true,fixture.tick)==COMP_RUNTIME_OK,"cancellation source START");
    REQUIRE(wait_state(&app,COMP_WBA_RECORDING_CAPTURING,20000u),"cancellation source MIC");
    step(&app,40u);comp_wba_recording_product_fault(&app.recording,COMP_WBA_RECORDING_FAULT_DEADLINE);
    starts=fixture.mic_starts;uint64_t next=app.recording_identity.record.next_session_id;
    /* Wired recovery repairs storage only and never invents a new START. */
    REQUIRE(!comp_v11_product_recording_recover(NULL),"null recovery admitted");
#define REJECT_RECOVERY(field) do {field=true;REQUIRE(!comp_v11_product_recording_recover(&app),#field);field=false;}while(0)
    REJECT_RECOVERY(board.microphone.running);REJECT_RECOVERY(board.playback_active);
    REJECT_RECOVERY(app.runtime.menu_pending);REJECT_RECOVERY(app.runtime.prepare_pending);
    REJECT_RECOVERY(app.runtime.command_pending);REJECT_RECOVERY(app.runtime.start_pending);
    REJECT_RECOVERY(app.runtime.capture_active);REJECT_RECOVERY(app.runtime.stop_pending);
#undef REJECT_RECOVERY
    REQUIRE(comp_v11_product_recording_recover(&app),"explicit wired recovery rejected stopped fault");
    REQUIRE(!comp_v11_product_recording_recover(&app),"recovery started twice");
    for(unsigned i=0u;i<30000u&&!app.recording.ready;i++)step(&app,1u);
    REQUIRE(app.recording.ready&&app.recording.pipeline.state==COMP_PIPE_IDLE&&!board.microphone.running&&
        fixture.mic_starts==starts&&app.recording_identity.record.next_session_id==next&&
        app.runtime.recording==DENZIC_AUDIO_RECORDING_STATE_ERROR_RECOVERY,
        "wired recovery started audio, allocated identity or pretended fault was a normal save");
    REQUIRE(!comp_v11_product_recording_recover(&app),"idle recovery implicitly retried");
    REQUIRE(comp_runtime_record(&app.runtime,true,fixture.tick)==COMP_RUNTIME_OK,"after wired recovery START");
    REQUIRE(wait_state(&app,COMP_WBA_RECORDING_CAPTURING,30000u),"after wired recovery MIC");
    step(&app,40u);comp_wba_recording_product_fault(&app.recording,COMP_WBA_RECORDING_FAULT_DEADLINE);
    starts=fixture.mic_starts;next=app.recording_identity.record.next_session_id;
    REQUIRE(comp_runtime_record(&app.runtime,true,fixture.tick)==COMP_RUNTIME_OK,"second retry");
    REQUIRE(comp_runtime_record(&app.runtime,false,fixture.tick)==COMP_RUNTIME_OK,"cancel pending retry");
    for(unsigned i=0u;i<30000u&&!app.recording.ready;i++)step(&app,1u);
    step(&app,20u);
    REQUIRE(app.recording.ready&&app.recording.pipeline.state==COMP_PIPE_IDLE&&!board.microphone.running&&
        fixture.mic_starts==starts&&app.recording_identity.record.next_session_id==next,
        "canceled recovery auto-started or allocated identity");
    uint32_t physical;
    REQUIRE(comp_v11_product_update_workspace(&app,4096u,&physical)&&physical>0u,"recovered idle cannot claim OTA workspace");
    REQUIRE(comp_v11_product_update_workspace(&app,0u,&physical),"recovered idle cannot release workspace");
    puts("PASS_RUNTIME_RECOVERY_REAL_APP_SOFTWARE_ONLY explicit-retry/real-runtime/CSI1/retained-prefix/ordinary-STOP/cancel-no-start/OTA-workspace; no board timing/power proof");
    free(fixture.flash);return 0;
}
#include "capture_encode_window.h"
#include "product_app.c"
int main(void)
{
    comp_v11_hal_t board;comp_v11_product_app_t app;
    memset(&fixture,0,sizeof(fixture));fixture.flash=malloc(FLASH_BYTES);
    REQUIRE(fixture.flash,"NOR allocation");memset(fixture.flash,255u,FLASH_BYTES);layout_root();init_board(&app,&board);
    REQUIRE(wait_state(&app,COMP_WBA_RECORDING_IDLE,20000u),"boot");
    REQUIRE(comp_runtime_record(&app.runtime,true,fixture.tick)==COMP_RUNTIME_OK,"START");
    REQUIRE(wait_state(&app,COMP_WBA_RECORDING_CAPTURING,20000u),"MIC");
    int16_t pcm[160];for(unsigned i=0;i<160;i++)pcm[i]=(int16_t)(i*40u);
    REQUIRE(board.pcm_sink(board.pcm_sink_context,pcm,160u,16000u),"first PCM");
    REQUIRE(comp_wba_recording_product_stage_pcm_half(&app.recording),"bounded first-half staging");
    REQUIRE(board.pcm_sink(board.pcm_sink_context,pcm,160u,16000u),"second PCM");
    fixture.dma_model=true;fixture.codec_ms=8u;fixture.microphone_poll_ms=2u;
    fixture.resource_read_ms=6u;fixture.next_ready=fixture.tick+10u;
    fixture.tick+=5u;app.capture_cycle_started_ms=fixture.tick;
    uint8_t page[256];bool read=resource_read(&app,0u,page,sizeof(page));
    if(app.recording.last_fault) {
        printf("BASELINE_LATE_DMA fault=%u stale=%lu deadline=%lu packets=%lu read=%u\n",(unsigned)app.recording.last_fault,
            (unsigned long)board.microphone.stale_dma_halves,(unsigned long)app.capture_deadline_faults,
            (unsigned long)app.recording.capture.engine.stats.encoded_packets,(unsigned)read);
        free(fixture.flash);return 3;
    }
    REQUIRE(read&&board.microphone.running&&app.recording.capture.engine.stats.encoded_packets==1u,"real encode/resource path");
    REQUIRE(board.microphone.processed_dma_halves==2u&&board.microphone.stale_dma_halves==0u&&app.capture_deadline_faults==0u,"post-encode DMA not serviced before next bounded IO");
    fixture.tick+=11u;REQUIRE(!capture_progress(&app,25u)&&app.capture_deadline_faults==1u&&!board.microphone.running,"11ms deadline weakened");
    puts("PASS_PRODUCTION_SCHEDULER_MODEL real Opus8ms/PCM2ms/next IO6ms; old stale DMA reproduced, post-codec priority repairs this schedule; 11ms protection remains. SOFTWARE ONLY, not actual61 qualification");
    free(fixture.flash);return 0;
}

bool comp_v11_hal_microphone_audio_profile(const comp_v11_hal_t *b,uint8_t profile,comp_rec_audio_profile_t *out)
{(void)b;(void)profile;(void)out;return false;}
