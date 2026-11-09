#include "product_app.h"
#ifdef COMPANION_TEST_SEALED_PULL_RECOVERY
#include "wba_segment_pull.h"
#endif
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
    bool level_fixture;
    int16_t level_pcm;
    uint8_t level_saturation_per_frame;
    bool key_pressed;
    bool amplifier_enabled;
    bool rng_unavailable;
    bool fail_identity_program;
    bool fail_microphone_profile;
    bool mic_before_durable_identity;
    uint32_t identity_writes_during_capture;
    uint32_t resource_read_ms,resource_reads,resource_bounded_calls,last_audio_tick,microphone_poll_ms;
    bool pending_pcm_before_resource;
    companion_screen_assets_stm32wba_config_t resources;
} fixture_t;

static fixture_t fixture;
static bool profile_failure_test, normal_recovery_test;
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
{(void)allow_directional; return board!=NULL && !board->microphone.running && profile<=1u && !fixture.fail_microphone_profile; }

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
{ return panel ? panel->status : COMP_SSD1681_WBA_NOT_READY; }

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
    int16_t pcm[COMP_WBA_RECORDING_PCM_FRAME_SAMPLES];
    if (board == NULL) return;
    comp_v11_hal_speaker_poll(board);
    if (!board->microphone.running || board->pcm_sink == NULL) return;
    for (uint32_t i = 0u; i < COMP_WBA_RECORDING_PCM_FRAME_SAMPLES; ++i) {
        uint32_t phase = (fixture.pcm_sequence * 160u + i) % 160u;
        pcm[i] = fixture.level_fixture?fixture.level_pcm:
                 phase < 80u ? (int16_t)(phase * 180u) :
                               (int16_t)((159u - phase) * 180u);
    }
    board->microphone.processing.stats.saturated_samples+=fixture.level_saturation_per_frame;
    fixture.pcm_sequence++;
    fixture.last_audio_tick=fixture.tick;
    if (!board->pcm_sink(board->pcm_sink_context, pcm,
                         COMP_WBA_RECORDING_PCM_FRAME_SAMPLES, 16000u)) {
        board->microphone.processing_rejections++;
    }
}

comp_v11_microphone_poll_result_t comp_v11_microphone_hal_poll(comp_v11_microphone_hal_t *microphone)
{
    if(!microphone || !microphone->running || !fixture.resource_read_ms ||
       fixture.tick-fixture.last_audio_tick<STEP_MS)return COMP_V11_MIC_POLL_IDLE;
    /* Only synthesize a DMA half when simulated real time has advanced. */
    comp_v11_hal_poll(active_board);
    fixture.tick+=fixture.microphone_poll_ms;
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
        if(partition->nor->erase_active)return COMPANION_SPI_NOR_STM32WBA_ERROR;
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

void comp_screen_presenter_wba_set_progress(comp_screen_presenter_wba_t *p,bool (*fn)(void *))
{p->progress=fn;}
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
/* This fake has no JEDEC/SR1/SR2; explicit opt-in models a qualified result,
 * never a claim about physical recovery. */
static bool fake_recovery_quiescent;
static unsigned fake_recovery_observations;
static bool fake_fail_recording_root_once;
static bool fake_fail_idle_read_once;
static bool fake_fail_stream_payload_once;
static bool fake_resource_bounded;
static bool fake_resource_uncertain;
static bool fake_resource_pending;
companion_spi_nor_stm32wba_status_t companion_spi_nor_stm32wba_recovery_observe(companion_spi_nor_stm32wba_t *nor)
{++fake_recovery_observations;return nor&&fake_recovery_quiescent&&!nor->erase_active?COMPANION_SPI_NOR_STM32WBA_OK:COMPANION_SPI_NOR_STM32WBA_UNSUPPORTED;}
companion_spi_nor_stm32wba_status_t companion_spi_nor_stm32wba_read(
    companion_spi_nor_stm32wba_t *nor,uint32_t address,uint8_t *p,size_t n)
{
    if(!nor||!p||address>FLASH_BYTES||n>FLASH_BYTES-address)return COMPANION_SPI_NOR_STM32WBA_BAD_PARAM;
    if(fake_fail_idle_read_once) { fake_fail_idle_read_once=false; return COMPANION_SPI_NOR_STM32WBA_ERROR; }
    if(fake_fail_recording_root_once&&address==COMP_WBA_NOR_SEGMENT_CATALOG_A&&n==256u) {
        fake_fail_recording_root_once=false;return COMPANION_SPI_NOR_STM32WBA_ERROR;
    }
    memcpy(p,fixture.flash+address,n);return COMPANION_SPI_NOR_STM32WBA_OK;
}
/* This fixture cannot observe CS; failed reads remain conservatively uncertain. */
companion_spi_nor_stm32wba_status_t companion_spi_nor_stm32wba_read_transient(
    companion_spi_nor_stm32wba_t *nor,uint32_t address,uint8_t *p,size_t n,bool *released)
{
    if(!released)return COMPANION_SPI_NOR_STM32WBA_BAD_PARAM;*released=false;
    if(fake_resource_bounded&&address<COMP_WBA_NOR_RECORDING_IDENTITY_BASE) {
        fixture.resource_bounded_calls++;
        if(fixture.resource_reads==0u)
            fixture.pending_pcm_before_resource=active_app->recording.capture.engine.ring_count!=0u;
        fixture.resource_reads++;
        if(fake_resource_pending)return COMPANION_SPI_NOR_STM32WBA_PENDING;
        if(fake_resource_uncertain){fixture.tick++;return COMPANION_SPI_NOR_STM32WBA_ERROR;}
        if(fixture.resource_read_ms>=8u) {
            fixture.tick+=8u;*released=true;return COMPANION_SPI_NOR_STM32WBA_ERROR;
        }
        fixture.tick+=fixture.resource_read_ms;
    }
    if(fake_fail_stream_payload_once){fake_fail_stream_payload_once=false;*released=true;return COMPANION_SPI_NOR_STM32WBA_ERROR;}
    return companion_spi_nor_stm32wba_read(nor,address,p,n);
}
companion_spi_nor_stm32wba_status_t companion_spi_nor_stm32wba_program(
    companion_spi_nor_stm32wba_t *nor,uint32_t address,const uint8_t *p,size_t n)
{
    companion_spi_nor_stm32wba_partition_t whole={nor,0u,FLASH_BYTES};
    return companion_spi_nor_stm32wba_partition_program(&whole,address,p,n);
}
static bool fake_hold_erase,fake_finish_erase;
uint32_t companion_spi_nor_stm32wba_erase_chunk(const companion_spi_nor_stm32wba_t *nor,uint32_t at,uint32_t remaining)
{
    if(at%65536u==0u&&remaining>=65536u)return 65536u;
    if(nor&&nor->info.erase_32k_supported&&at%32768u==0u&&remaining>=32768u)return 32768u;
    return 4096u;
}
companion_spi_nor_stm32wba_status_t companion_spi_nor_stm32wba_erase_step(
    companion_spi_nor_stm32wba_t *nor,uint32_t at,uint32_t n)
{
    if(!nor||at%4096u||n%4096u||at>FLASH_BYTES||n>FLASH_BYTES-at)return COMPANION_SPI_NOR_STM32WBA_BAD_PARAM;
    if(fake_hold_erase) {
        if(!nor->erase_active){nor->erase_active=true;nor->erase_address=at;nor->erase_bytes=n;}
        if(!fake_finish_erase)return COMPANION_SPI_NOR_STM32WBA_PENDING;
        fake_finish_erase=false;fake_hold_erase=false;nor->erase_active=false;
    }
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
{return mic&&mic->running;}
bool comp_v11_hal_take_key_wake(comp_v11_hal_t *board)
{(void)board;return false;}
comp_wba_button_edges_t comp_v11_hal_take_key_edges(comp_v11_hal_t *board)
{
    comp_wba_button_edges_t edges={board->wake_events.key_down_ms,board->wake_events.key_up_ms,
        (uint8_t)(board->wake_events.key_pending>>1u),fixture.key_pressed};
    board->wake_events.key_pending=0u;return edges;
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
static bool feedback_watch;
static uint32_t feedback_observed;
static void step(comp_v11_product_app_t *app,uint32_t count)
{
    for(uint32_t i=0u;i<count;i++) {
        fixture.tick+=STEP_MS;comp_v11_product_app_poll(app);
        if(feedback_watch) {
            comp_capture_feedback_t feedback=comp_v11_product_capture_feedback(app,false);
            feedback_observed|=(1u<<feedback.state)|((uint32_t)feedback.flags<<16u);
        }
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
{
    if(fixture.key_pressed!=pressed)
        comp_v11_wake_events_note_key_isr(&app->board->wake_events,
            pressed?COMP_V11_WAKE_KEY_FALLING:COMP_V11_WAKE_KEY_RISING,fixture.tick);
    fixture.key_pressed=pressed;step(app,count);
}
static bool settled_space(comp_v11_product_app_t *app)
{
    for(uint32_t i=0u;i<20000u&&!comp_wba_recording_product_space_current(&app->recording);i++)step(app,1u);
    return comp_wba_recording_product_space_current(&app->recording);
}
static uint32_t fake_nor_now(void *context) { (void)context; return fixture.tick; }
static void init_board(comp_v11_product_app_t *app,comp_v11_hal_t *board)
{
    memset(board,0,sizeof(*board));active_board=board;active_app=app;
    board->panel.status=COMP_SSD1681_WBA_IDLE;
    board->microphone.initialized=true;board->nor.info.size_bytes=FLASH_BYTES;board->nor.erase_suspend_supported=true;
    board->nor.config.now_ms=fake_nor_now;
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
    if(profile_failure_test) {
        uint64_t initial_next=app.recording_identity.record.next_session_id;
        fixture.fail_microphone_profile=true;
        REQUIRE(comp_runtime_record(&app.runtime,true,fixture.tick)!=COMP_RUNTIME_OK &&
            app.recording_identity.record.next_session_id==initial_next && !board.microphone.running,
            "direct profile rejection allocated identity or started microphone");
        fixture.fail_microphone_profile=false;
    }
    REQUIRE(comp_runtime_record(&app.runtime,true,fixture.tick)==COMP_RUNTIME_OK,"first START");
    REQUIRE(wait_state(&app,COMP_WBA_RECORDING_CAPTURING,20000u),"first MIC");
    step(&app,60u);uint64_t old=app.recording_session_id;
    comp_wba_recording_product_fault(&app.recording,COMP_WBA_RECORDING_FAULT_DEADLINE);
    REQUIRE(!board.microphone.running&&!app.runtime.capture_active&&
        app.runtime.recording==DENZIC_AUDIO_RECORDING_STATE_ERROR_RECOVERY,"fault must really stop MIC");
    unsigned starts=fixture.mic_starts;
    uint8_t *saved_fault_extent=NULL, saved_fault_sha[32]={0};
    uint32_t saved_fault_offset=0,saved_fault_bytes=0;
    for(unsigned i=0u;i<40u;i++)step(&app,1u);
    REQUIRE(app.recording.pipeline.state==COMP_PIPE_FAILED&&fixture.mic_starts==starts,"idle poll silently retried fault");
    REQUIRE(comp_runtime_record(&app.runtime,true,fixture.tick)==COMP_RUNTIME_OK&&
        app.runtime.prepare_pending&&!app.recording.media_ready&&!board.microphone.running,"retry must defer START to bounded recovery");
    REQUIRE(app.recording_identity.record.next_session_id==old+1u,"recovery allocated premature identity");
    if (profile_failure_test) {
    /* Once recovery starts, an unavailable microphone profile must fail this
     * request once. It must not allocate persistent session IDs in every poll. */
    fixture.fail_microphone_profile=true;
    for (unsigned n=0;n<11500u && app.runtime.prepare_pending;n++) step(&app,1u);
    fprintf(stderr,"POST_RECOVERY_STATE prepare=%u command=%u state=%u mic=%u starts=%u next_before=%llu next_after=%llu boot=%u ready=%u pipe=%u fault=%u tick=%u\n",(unsigned)app.runtime.prepare_pending,(unsigned)app.runtime.command_pending,(unsigned)app.runtime.recording,(unsigned)board.microphone.running,fixture.mic_starts,(unsigned long long)(old+1u),(unsigned long long)app.recording_identity.record.next_session_id,(unsigned)app.recording.boot_phase,(unsigned)app.recording.ready,(unsigned)app.recording.pipeline.state,(unsigned)app.recording.last_fault,(unsigned)fixture.tick);
    REQUIRE(!app.runtime.prepare_pending && !app.runtime.command_pending &&
        app.runtime.recording==DENZIC_AUDIO_RECORDING_STATE_ERROR_RECOVERY &&
        !board.microphone.running && fixture.mic_starts==starts &&
        app.recording_identity.record.next_session_id==old+1u,
        "post-recovery profile failure must stop, retain audio and not burn identities");
    for(unsigned n=0;n<300u;n++)step(&app,1u);
    REQUIRE(!app.runtime.prepare_pending && fixture.mic_starts==starts &&
        app.recording_identity.record.next_session_id==old+1u,
        "idle polling restarted or allocated after failed prepare");
    comp_segment_entry_t recovered={0};bool found_fault=false;
    for(uint8_t index=0;index<64u;index++) if(app.recording.catalog.slots[index]!=255u) {
        REQUIRE(comp_wba_segment_storage_entry(&app.recording.storage,&app.recording.catalog,index,&recovered)==COMP_SEG_OK,
            "read recovered original");
        if(recovered.descriptor.session_id==old){found_fault=true;break;}
    }
    REQUIRE(found_fault&&recovered.state==COMP_SEG_UNSYNCED,"fault original not recovered");
    saved_fault_offset=COMP_WBA_NOR_RECORDING_BASE+recovered.extent_offset;
    saved_fault_bytes=recovered.reserved_bytes;
    saved_fault_extent=malloc(saved_fault_bytes);REQUIRE(saved_fault_extent,"original snapshot allocation");
    memcpy(saved_fault_extent,fixture.flash+saved_fault_offset,saved_fault_bytes);
    memcpy(saved_fault_sha,recovered.descriptor.sha256,32u);
    fixture.fail_microphone_profile=false;
    REQUIRE(comp_runtime_record(&app.runtime,true,fixture.tick)==COMP_RUNTIME_OK,
        "explicit retry after profile restored rejected");
    }
    REQUIRE(wait_state(&app,COMP_WBA_RECORDING_CAPTURING,30000u),"runtime retry did not resume through ordinary prepare");
    REQUIRE(app.recording_session_id==old+1u&&fixture.mic_starts==starts+1u&&
        app.recording_identity.record.format_epoch==epoch&&!fixture.mic_before_durable_identity&&
        !fixture.identity_writes_during_capture,"retry identity/one-start/namespace violated");
    step(&app,60u);
    REQUIRE(comp_runtime_record(&app.runtime,false,fixture.tick)==COMP_RUNTIME_OK,"normal STOP after retry");
    REQUIRE(wait_state(&app,COMP_WBA_RECORDING_TRANSFER_READY,30000u)&&!board.microphone.running,"retry capture did not save/STOP");
    REQUIRE(settled_space(&app)&&app.recording.space.logical==2u,"fault prefix or new recording missing");
    if (profile_failure_test) {
        comp_segment_entry_t recovered={0};bool found=false;
        for(uint8_t index=0;index<64u;index++) if(app.recording.catalog.slots[index]!=255u) {
            REQUIRE(comp_wba_segment_storage_entry(&app.recording.storage,&app.recording.catalog,index,&recovered)==COMP_SEG_OK,
                "reread recovered original");
            if(recovered.descriptor.session_id==old){found=true;break;}
        }
        REQUIRE(found&&!memcmp(saved_fault_sha,recovered.descriptor.sha256,32u)&&
            !memcmp(saved_fault_extent,fixture.flash+saved_fault_offset,saved_fault_bytes),
            "failed prepare or retry modified recovered original");
        free(saved_fault_extent);
        puts("PASS_PROFILE_FAILURE_RECOVERY_REAL_APP_SOFTWARE_ONLY: one explicit retry, no extra identity, original retained and new recording saved");
        free(fixture.flash);return 0;
    }
    if (normal_recovery_test) {
        puts("PASS_NORMAL_RECOVERY_REAL_APP_SOFTWARE_ONLY: explicit recovery and one new recording saved");
        free(fixture.flash);return 0;
    }
    REQUIRE(comp_runtime_record(&app.runtime,true,fixture.tick)==COMP_RUNTIME_OK,"cancellation source START");
    REQUIRE(wait_state(&app,COMP_WBA_RECORDING_CAPTURING,20000u),"cancellation source MIC");
    step(&app,40u);comp_wba_recording_product_fault(&app.recording,COMP_WBA_RECORDING_FAULT_DEADLINE);
    starts=fixture.mic_starts;uint64_t next=app.recording_identity.record.next_session_id;
    /* Wired recovery repairs storage only and never invents a new START. */
    REQUIRE(!comp_v11_product_recording_recover(NULL),"null recovery admitted");
#define REJECT_RECOVERY(field) do {field=true;REQUIRE(!comp_v11_product_recording_recover(&app),#field);field=false;}while(0)
    REJECT_RECOVERY(board.microphone.running);REJECT_RECOVERY(board.playback_active);REJECT_RECOVERY(app.pet_profile.writing);
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
    REQUIRE(comp_runtime_record(&app.runtime,true,fixture.tick)==COMP_RUNTIME_OK,"poison recovery capture START");
    REQUIRE(wait_state(&app,COMP_WBA_RECORDING_CAPTURING,30000u),"poison recovery capture MIC");
    step(&app,40u);comp_wba_recording_product_fault(&app.recording,COMP_WBA_RECORDING_FAULT_STORAGE_IO);
    starts=fixture.mic_starts;next=app.recording_identity.record.next_session_id;
    app.recording.storage.poisoned=true;
    REQUIRE(!comp_v11_product_recording_recover(&app),"unqualified physical observation accepted");
    fake_recovery_quiescent=true;
    REQUIRE(comp_v11_product_recording_recover(&app)&&comp_wba_recording_product_recovering(&app.recording),"qualified explicit remount refused");
    comp_preferences_values_t prefs=app.preferences.values;
    REQUIRE(!comp_v11_product_save_preferences(&app,&prefs),"settings writer entered recovery");
    uint32_t during_recovery=0u;
    REQUIRE(!comp_v11_product_update_workspace(&app,4096u,&during_recovery),"OTA claimed recovery workspace");
    for(unsigned i=0u;i<30000u&&comp_wba_recording_product_recovering(&app.recording);i++)step(&app,1u);
    REQUIRE(app.recording.ready&&app.recording.pipeline.state==COMP_PIPE_IDLE&&!board.microphone.running&&
        fixture.mic_starts==starts&&app.recording_identity.record.next_session_id==next,
        "remount started audio, allocated identity or failed");
    REQUIRE(comp_runtime_record(&app.runtime,true,fixture.tick)==COMP_RUNTIME_OK,"post-remount START");
    REQUIRE(wait_state(&app,COMP_WBA_RECORDING_CAPTURING,30000u),"post-remount MIC");
    step(&app,40u);comp_wba_recording_product_fault(&app.recording,COMP_WBA_RECORDING_FAULT_STORAGE_IO);
    app.recording.storage.poisoned=true;starts=fixture.mic_starts;next=app.recording_identity.record.next_session_id;
    REQUIRE(comp_runtime_record(&app.runtime,true,fixture.tick)==COMP_RUNTIME_OK,"poisoned ordinary START not queued");
    REQUIRE(wait_state(&app,COMP_WBA_RECORDING_CAPTURING,30000u),"ordinary START did not remount and capture");
    REQUIRE(fixture.mic_starts==starts+1u&&app.recording_identity.record.next_session_id==next+1u,
        "ordinary START did not allocate exactly one new durable session");
    REQUIRE(comp_runtime_record(&app.runtime,false,fixture.tick)==COMP_RUNTIME_OK,"post-poison STOP");
    REQUIRE(wait_state(&app,COMP_WBA_RECORDING_TRANSFER_READY,30000u),"post-poison STOP failed");
    REQUIRE(settled_space(&app),"post-poison capacity scan did not finish");
    fake_recovery_quiescent=false;
    uint32_t physical;
    /* A stopped retained microphone original must survive an OTA workspace
     * claim and release. Only a genuinely overlapping tail is refused. */
    REQUIRE(app.recording.space.microphone_owned,"OTA preservation fixture needs retained microphone audio");
    uint8_t *ota_original=malloc(FLASH_BYTES);REQUIRE(ota_original,"OTA original snapshot");
    memcpy(ota_original,fixture.flash,FLASH_BYTES);
    REQUIRE(comp_v11_product_update_workspace(&app,4096u,&physical)&&physical>0u,
        "OTA refused disjoint workspace while microphone originals are retained");
    REQUIRE(comp_v11_product_update_workspace(&app,0u,&physical),"OTA cannot release its own workspace");
    REQUIRE(!comp_v11_product_update_workspace(&app,app.recording.catalog.data_bytes,&physical),
        "OTA workspace overlapped retained microphone audio");
    REQUIRE(!memcmp(ota_original,fixture.flash,FLASH_BYTES),"OTA workspace modified original NOR bytes");
    free(ota_original);
    REQUIRE(comp_wba_recording_product_workspace(&app.recording,4096u,&physical)&&physical>0u,
        "recovered idle cannot claim a disjoint temporary workspace");
    REQUIRE(comp_wba_recording_product_workspace(&app.recording,0u,&physical),"recovered idle cannot release temporary workspace");
    /* Reproduce the physical board: a retained tail owner leaves a large
     * middle gap, so a full CUP cannot use the old tail-only allocator. */
    comp_segment_entry_t ota_tail={0};ota_tail.state=COMP_SEG_WRITING;
    ota_tail.extent_offset=app.recording.catalog.data_bytes-4096u;ota_tail.reserved_bytes=4096u;
    ota_tail.descriptor.recording_id=app.recording.catalog.next_id;
    ota_tail.descriptor.session_id=UINT64_C(0x7777);ota_tail.descriptor.codec=3u;
    ota_tail.descriptor.format_epoch=app.recording.catalog.epoch;
    ota_tail.descriptor.source_mode=1u;memcpy(ota_tail.descriptor.device_uid,app.recording.catalog.uid,12u);
    REQUIRE(comp_segment_catalog_put_begin(&app.recording.catalog,&ota_tail)==COMP_SEG_PENDING,"tail owner reservation");
    comp_segment_result_t ota_tail_result=COMP_SEG_PENDING;
    while(ota_tail_result==COMP_SEG_PENDING)ota_tail_result=comp_wba_segment_storage_catalog_poll(&app.recording.storage,&app.recording.catalog);
    REQUIRE(ota_tail_result==COMP_SEG_OK,"tail owner commit");
    REQUIRE(!comp_v11_product_update_workspace(&app,1429504u,&physical),"stale gap inventory allowed OTA");
    REQUIRE(settled_space(&app),"fragmented gap inventory");
    ota_original=malloc(FLASH_BYTES);REQUIRE(ota_original,"fragmented OTA original snapshot");
    memcpy(ota_original,fixture.flash,FLASH_BYTES);
    REQUIRE(comp_v11_product_update_workspace(&app,1429504u,&physical),"full CUP refused a free middle gap");
    uint32_t ota_middle=physical;
    REQUIRE(ota_middle>=app.recording.catalog.data_base&&
        ota_middle+1429504u<=app.recording.catalog.data_base+ota_tail.extent_offset,"middle OTA overlaps retained tail");
    for(unsigned i=0u;i<100u;i++)comp_wba_recording_product_poll(&app.recording);
    REQUIRE(app.recording.ready&&app.recording.pipeline.state!=COMP_PIPE_FAILED,"interior OTA broke capacity poll");
    REQUIRE(!comp_v11_product_update_workspace(&app,1433600u,&physical),"live OTA claim silently resized");
    REQUIRE(comp_v11_product_update_workspace(&app,1429504u,&physical)&&physical==ota_middle,"live middle claim moved");
    REQUIRE(comp_v11_product_update_workspace(&app,0u,&physical)&&physical==0u,"middle OTA release failed");
    REQUIRE(settled_space(&app),"capacity unavailable after middle OTA release");
    REQUIRE(!memcmp(ota_original,fixture.flash,FLASH_BYTES),"fragmented OTA lease modified original NOR");free(ota_original);
    REQUIRE(comp_segment_catalog_cancel_unwritten_begin(&app.recording.catalog,&ota_tail)==COMP_SEG_PENDING,"test tail cleanup");
    ota_tail_result=COMP_SEG_PENDING;
    while(ota_tail_result==COMP_SEG_PENDING)ota_tail_result=comp_wba_segment_storage_catalog_poll(&app.recording.storage,&app.recording.catalog);
    REQUIRE(ota_tail_result==COMP_SEG_OK&&settled_space(&app),"test tail cleanup commit");
    /* A failed read in the idle capacity walk must not strand the recorder.
     * This test uses the production product poll and fake NOR, with existing
     * sealed entries; the failure occurs before any erase or write. */
    REQUIRE(settled_space(&app)&&app.recording.space.used>0u,"idle fault requires existing audio");
    uint8_t old_used=app.recording.space.used; unsigned starts_before_idle=fixture.mic_starts;
    uint8_t *idle_original=malloc(FLASH_BYTES);REQUIRE(idle_original,"idle original snapshot");memcpy(idle_original,fixture.flash,FLASH_BYTES);
    memset(&app.recording.space,0,sizeof(app.recording.space));
    fake_recovery_quiescent=true;fake_fail_idle_read_once=true;
    for(unsigned i=0u;i<100u&&fake_fail_idle_read_once;i++)comp_wba_recording_product_poll(&app.recording);
    REQUIRE(!fake_fail_idle_read_once&&app.recording.storage.poisoned,"idle read error not injected");
    for(unsigned i=0u;i<30000u&&!app.recording.ready;i++)step(&app,1u);
    REQUIRE(app.recording.ready,"idle transient read error left recorder permanently unavailable");
    REQUIRE(app.recording_identity.record.format_epoch==epoch&&!board.microphone.running&&fixture.mic_starts==starts_before_idle&&app.recording.space.used==old_used,"idle recovery changed namespace, contents, or started MIC");
    REQUIRE(!memcmp(idle_original,fixture.flash,FLASH_BYTES),"idle read recovery modified durable NOR contents");free(idle_original);
    REQUIRE(comp_runtime_record(&app.runtime,true,fixture.tick)==COMP_RUNTIME_OK,"idle recovery ordinary start rejected");
    REQUIRE(wait_state(&app,COMP_WBA_RECORDING_CAPTURING,30000u),"idle recovery did not permit new capture");
    step(&app,40u);REQUIRE(comp_runtime_record(&app.runtime,false,fixture.tick)==COMP_RUNTIME_OK,"idle recovery ordinary stop rejected");
    REQUIRE(wait_state(&app,COMP_WBA_RECORDING_TRANSFER_READY,30000u)&&settled_space(&app),"idle recovery new recording did not seal");
    /* An existing OTA workspace must not be silently discarded by retry. */
    app.recording.pipeline.workspace_bytes=4096u;
    memset(&app.recording.space,0,sizeof(app.recording.space));
    fake_fail_idle_read_once=true;
    for(unsigned i=0u;i<100u&&fake_fail_idle_read_once;i++)comp_wba_recording_product_poll(&app.recording);
    REQUIRE(!fake_fail_idle_read_once&&app.recording.storage.poisoned&&
        !comp_wba_recording_product_boot_retry_pending(&app.recording)&&
        app.recording.pipeline.workspace_bytes==4096u,"fault retried over active workspace");
    fake_recovery_quiescent=false;
    /* Fresh boot from existing data, one transient root-read failure; the
     * app's real poll must retry once and still run its boot-lease gate. */
    fake_recovery_quiescent=true;fake_fail_recording_root_once=true;init_board(&app,&board);
    REQUIRE(wait_state(&app,COMP_WBA_RECORDING_IDLE,30000u),"automatic boot read retry did not recover");
    REQUIRE(!fake_fail_recording_root_once&&!comp_wba_recording_product_boot_retry_pending(&app.recording)&&app.recording.ready&&
        app.recording_identity.record.format_epoch==epoch,"boot retry skipped failure/lease or changed namespace");
    fake_recovery_quiescent=false;
    puts("PASS_RUNTIME_RECOVERY_REAL_APP_SOFTWARE_ONLY idle-read-auto-remount/whole-NOR-unchanged/new-capture/OTA-owner-denial/boot-retry; no board timing/power proof");
    free(fixture.flash);return 0;
}
static int damaged_tail_continuity_journey(bool reboot)
{
    comp_v11_hal_t board;comp_v11_product_app_t app;
    memset(&fixture,0,sizeof(fixture));fixture.flash=malloc(FLASH_BYTES);
    REQUIRE(fixture.flash,"continuity fixture NOR allocation");
    memset(fixture.flash,255u,FLASH_BYTES);layout_root();init_board(&app,&board);
    REQUIRE(wait_state(&app,COMP_WBA_RECORDING_IDLE,20000u),"continuity initial mount");
    REQUIRE(comp_runtime_record(&app.runtime,true,fixture.tick)==COMP_RUNTIME_OK,"first START");
    REQUIRE(wait_state(&app,COMP_WBA_RECORDING_CAPTURING,20000u),"first MIC");
    step(&app,60u);
    comp_segment_entry_t damaged={0};bool found=false;
    for(uint8_t i=0u;i<64u;i++)if(app.recording.catalog.slots[i]!=255u) {
        REQUIRE(comp_wba_segment_storage_entry(&app.recording.storage,&app.recording.catalog,i,&damaged)==COMP_SEG_OK,
                "read original entry");
        if(damaged.state==COMP_SEG_WRITING){found=true;break;}
    }
    REQUIRE(found,"no writing extent");
    uint32_t offset=COMP_WBA_NOR_RECORDING_BASE+damaged.extent_offset;
    fixture.flash[offset+37u]^=1u;
    uint8_t *copy=malloc(damaged.reserved_bytes);REQUIRE(copy,"saved corrupt extent");
    memcpy(copy,fixture.flash+offset,damaged.reserved_bytes);
    comp_wba_recording_product_fault(&app.recording,COMP_WBA_RECORDING_FAULT_DEADLINE);
    REQUIRE(!board.microphone.running,"fault did not stop mic");
    if(reboot) {
        init_board(&app,&board);
        REQUIRE(wait_state(&app,COMP_WBA_RECORDING_FAULT,30000u),"corrupt tail reboot did not reach salvage");
    }
    REQUIRE(comp_runtime_record(&app.runtime,true,fixture.tick)==COMP_RUNTIME_OK,"retry START");
    REQUIRE(wait_state(&app,COMP_WBA_RECORDING_CAPTURING,30000u),"new capture after retained tail");
    REQUIRE(app.recording_session_id!=damaged.descriptor.session_id,"new identity reused old session");
    step(&app,60u);
    REQUIRE(comp_runtime_record(&app.runtime,false,fixture.tick)==COMP_RUNTIME_OK,"new STOP");
    REQUIRE(wait_state(&app,COMP_WBA_RECORDING_TRANSFER_READY,20000u),"new recording not sealed");
    REQUIRE(!memcmp(copy,fixture.flash+offset,damaged.reserved_bytes),"damaged extent changed");
    REQUIRE(!app.recording.ready&&app.recording.last_fault!=COMP_WBA_RECORDING_FAULT_NONE,
            "degraded status erased");
    uint32_t physical=0u;
    REQUIRE(!comp_v11_product_update_workspace(&app,4096u,&physical),"new OTA admitted in salvage");
    REQUIRE(settled_space(&app),"space did not settle after new recording");
    /* Production app polling, after a second read-only error while an old
     * damaged extent is retained. No user request or new session is needed
     * for bounded remount, and no retained media may change in that remount. */
    uint8_t *before=malloc(FLASH_BYTES);REQUIRE(before,"idle salvage flash snapshot");
    memcpy(before,fixture.flash,FLASH_BYTES);
    unsigned idle_starts=fixture.mic_starts;
    memset(&app.recording.space,0,sizeof(app.recording.space));
    fake_recovery_quiescent=true;fake_fail_idle_read_once=true;
    for(unsigned i=0u;i<100u&&fake_fail_idle_read_once;i++)comp_wba_recording_product_poll(&app.recording);
    REQUIRE(!fake_fail_idle_read_once&&app.recording.storage.poisoned&&
        comp_wba_recording_product_boot_retry_pending(&app.recording),"salvage idle fault did not arm retry");
    for(unsigned i=0u;i<30000u&&!comp_wba_recording_product_salvaging(&app.recording);i++)step(&app,1u);
    REQUIRE(comp_wba_recording_product_salvaging(&app.recording)&&
        comp_wba_recording_product_capture_prepare_available(&app.recording)&&
        !board.microphone.running&&fixture.mic_starts==idle_starts,
        "salvage idle retry failed or started microphone");
    REQUIRE(!memcmp(before,fixture.flash,FLASH_BYTES),"salvage idle retry changed durable media");
    free(before);fake_recovery_quiescent=false;
    /* If the two bounded automatic observations fail, a new explicit START
     * must retry after the transient condition clears without changing the
     * old damaged extent or inventing an automatic recording. */
    unsigned exhausted_starts=fixture.mic_starts;
    memset(&app.recording.space,0,sizeof(app.recording.space));
    fake_fail_idle_read_once=true;
    for(unsigned i=0u;i<100u&&fake_fail_idle_read_once;i++)comp_wba_recording_product_poll(&app.recording);
    REQUIRE(!fake_fail_idle_read_once&&comp_wba_recording_product_boot_retry_pending(&app.recording),
        "salvage explicit-retry fault did not arm");
    step(&app,2000u);
    REQUIRE(!comp_wba_recording_product_boot_retry_pending(&app.recording)&&
        comp_wba_recording_product_tail_retained(&app.recording)&&fixture.mic_starts==exhausted_starts&&
        !memcmp(copy,fixture.flash+offset,damaged.reserved_bytes),"salvage retry exhaustion changed old audio");
    fake_recovery_quiescent=true;
    REQUIRE(comp_runtime_record(&app.runtime,true,fixture.tick)==COMP_RUNTIME_OK,"second START");
    REQUIRE(wait_state(&app,COMP_WBA_RECORDING_CAPTURING,20000u),"second MIC");
    fake_recovery_quiescent=false;
    step(&app,60u);
    comp_wba_recording_product_fault(&app.recording,COMP_WBA_RECORDING_FAULT_DEADLINE);
    REQUIRE(!board.microphone.running,"second fault did not stop mic");
    REQUIRE(comp_runtime_record(&app.runtime,true,fixture.tick)==COMP_RUNTIME_OK,"second fault retry START");
    REQUIRE(wait_state(&app,COMP_WBA_RECORDING_CAPTURING,30000u),"second fault recovery stuck");
    step(&app,60u);
    REQUIRE(comp_runtime_record(&app.runtime,false,fixture.tick)==COMP_RUNTIME_OK,"recovered STOP");
    REQUIRE(wait_state(&app,COMP_WBA_RECORDING_TRANSFER_READY,20000u),"recovered session not sealed");
    REQUIRE(!memcmp(copy,fixture.flash+offset,damaged.reserved_bytes),"original damaged extent changed after second recovery");
    free(copy);free(fixture.flash);
    puts("PASS_DAMAGED_TAIL_PRODUCT_CONTINUITY_SOFTWARE_ONLY");return 0;
}
static int explicit_idle_retry_journey(void)
{
    comp_v11_hal_t board;comp_v11_product_app_t app;
    memset(&fixture,0,sizeof(fixture));fixture.flash=malloc(FLASH_BYTES);
    REQUIRE(fixture.flash,"retry fixture NOR allocation");
    memset(fixture.flash,255u,FLASH_BYTES);layout_root();init_board(&app,&board);
    REQUIRE(wait_state(&app,COMP_WBA_RECORDING_IDLE,20000u),"retry initial mount");
    REQUIRE(comp_runtime_record(&app.runtime,true,fixture.tick)==COMP_RUNTIME_OK,"original START");
    REQUIRE(wait_state(&app,COMP_WBA_RECORDING_CAPTURING,20000u),"original MIC");
    step(&app,60u);
    REQUIRE(comp_runtime_record(&app.runtime,false,fixture.tick)==COMP_RUNTIME_OK,"original STOP");
    REQUIRE(wait_state(&app,COMP_WBA_RECORDING_TRANSFER_READY,20000u)&&settled_space(&app),"original seal");
    comp_segment_entry_t original={0};bool found=false;
    for(uint8_t i=0u;i<64u;i++)if(app.recording.catalog.slots[i]!=255u) {
        REQUIRE(comp_wba_segment_storage_entry(&app.recording.storage,&app.recording.catalog,i,&original)==COMP_SEG_OK,"original descriptor");
        if(original.state==COMP_SEG_UNSYNCED){found=true;break;}
    }
    REQUIRE(found,"missing original");
    uint32_t at=COMP_WBA_NOR_RECORDING_BASE+original.extent_offset;
    uint8_t *saved=malloc(original.reserved_bytes);REQUIRE(saved,"original extent snapshot");
    memcpy(saved,fixture.flash+at,original.reserved_bytes);
    unsigned starts=fixture.mic_starts;
    memset(&app.recording.space,0,sizeof(app.recording.space));
    fake_recovery_quiescent=false;fake_fail_idle_read_once=true;
    for(unsigned i=0u;i<100u&&fake_fail_idle_read_once;i++)comp_wba_recording_product_poll(&app.recording);
    REQUIRE(!fake_fail_idle_read_once&&comp_wba_recording_product_boot_retry_pending(&app.recording),"transient error not injected");
    step(&app,2000u);
    REQUIRE(!comp_wba_recording_product_boot_retry_pending(&app.recording)&&!app.recording.ready&&
        fixture.mic_starts==starts&&!board.microphone.running,"automatic attempts did not stop safely");
    REQUIRE(!memcmp(saved,fixture.flash+at,original.reserved_bytes),"old audio changed during retries");
    /* A newly secured phone/PC link queues one background retry. While the
     * media is still unavailable it must exhaust once, then remain quiet. */
    unsigned observed=fake_recovery_observations;
    comp_v11_product_recording_link_change(&app,true,true);
    comp_v11_product_recording_link_change(&app,false,false);step(&app,20u);
    REQUIRE(fake_recovery_observations==observed&&!app.recording_link_retry,
        "disconnected link left an unstarted recovery request");
    comp_v11_product_recording_link_change(&app,true,true);step(&app,2000u);
    REQUIRE(fake_recovery_observations==observed+2u&&!app.recording_link_retry&&
        comp_wba_recording_product_idle_retry_exhausted(&app.recording),"secured-link retry was not bounded");
    observed=fake_recovery_observations;step(&app,2000u);
    REQUIRE(fake_recovery_observations==observed&&!board.microphone.running&&fixture.mic_starts==starts,
        "same connection repeatedly retried or started microphone");
    /* A later fresh secured link after media recovers remounts without a
     * START; the existing client can then re-read the real capability. */
    fake_recovery_quiescent=true;
    comp_v11_product_recording_link_change(&app,false,false);
    comp_v11_product_recording_link_change(&app,true,true);
    for(unsigned i=0u;i<30000u&&!app.recording.ready;i++)step(&app,1u);
    REQUIRE(app.recording.ready&&!board.microphone.running&&fixture.mic_starts==starts&&
        !memcmp(saved,fixture.flash+at,original.reserved_bytes),"secured-link recovery altered original or auto-started");
    /* Repeat the synthetic idle failure to exercise a separate local START. */
    memset(&app.recording.space,0,sizeof(app.recording.space));
    fake_recovery_quiescent=false;fake_fail_idle_read_once=true;
    for(unsigned i=0u;i<100u&&fake_fail_idle_read_once;i++)comp_wba_recording_product_poll(&app.recording);
    REQUIRE(!fake_fail_idle_read_once&&comp_wba_recording_product_boot_retry_pending(&app.recording),"second idle error missing");
    step(&app,2000u);
    REQUIRE(comp_wba_recording_product_idle_retry_exhausted(&app.recording),"second idle retry did not exhaust");
    fake_recovery_quiescent=true;
    app.recording.pipeline.workspace_bytes=4096u;
    REQUIRE(comp_runtime_record(&app.runtime,true,fixture.tick)!=COMP_RUNTIME_OK&&
        app.recording.pipeline.workspace_bytes==4096u&&!board.microphone.running,
        "explicit retry stole an update workspace");
    app.recording.pipeline.workspace_bytes=0u;
    uint64_t next=app.recording_identity.record.next_session_id;
    REQUIRE(comp_runtime_record(&app.runtime,true,fixture.tick)==COMP_RUNTIME_OK,
        "explicit START could not begin a retry to cancel");
    REQUIRE(comp_runtime_record(&app.runtime,false,fixture.tick)==COMP_RUNTIME_OK,
        "cancel during explicit retry was rejected");
    for(unsigned i=0u;i<30000u&&comp_wba_recording_product_recovering(&app.recording);++i)step(&app,1u);
    step(&app,20u);
    REQUIRE(app.recording.ready&&fixture.mic_starts==starts&&!board.microphone.running&&
        app.recording_identity.record.next_session_id==next&&!memcmp(saved,fixture.flash+at,original.reserved_bytes),
        "cancelled retry started capture, allocated session or altered old audio");
    REQUIRE(comp_runtime_record(&app.runtime,true,fixture.tick)==COMP_RUNTIME_OK,
        "explicit START after media recovered could not initiate recovery");
    REQUIRE(wait_state(&app,COMP_WBA_RECORDING_CAPTURING,30000u),"explicit retry did not start new capture");
    REQUIRE(fixture.mic_starts==starts+1u&&!memcmp(saved,fixture.flash+at,original.reserved_bytes),
        "explicit retry altered old audio or duplicated start");
    REQUIRE(comp_runtime_record(&app.runtime,false,fixture.tick)==COMP_RUNTIME_OK,"retry STOP");
    REQUIRE(wait_state(&app,COMP_WBA_RECORDING_TRANSFER_READY,20000u),"retry not sealed");
    free(saved);free(fixture.flash);fake_recovery_quiescent=false;
    puts("PASS_EXPLICIT_IDLE_RETRY_REAL_APP_SOFTWARE_ONLY");return 0;
}

static int salvage_to_healthy_journey(void)
{
    comp_v11_hal_t board;comp_v11_product_app_t app;
    memset(&fixture,0,sizeof(fixture));fixture.flash=malloc(FLASH_BYTES);
    REQUIRE(fixture.flash,"ready state fixture NOR allocation");
    memset(fixture.flash,255u,FLASH_BYTES);layout_root();init_board(&app,&board);
    REQUIRE(wait_state(&app,COMP_WBA_RECORDING_IDLE,20000u),"ready state initial mount");
    REQUIRE(comp_runtime_record(&app.runtime,true,fixture.tick)==COMP_RUNTIME_OK,"ready state first START");
    REQUIRE(wait_state(&app,COMP_WBA_RECORDING_CAPTURING,20000u),"ready state first MIC");step(&app,60u);
    comp_segment_entry_t old={0};bool found=false;
    for(uint8_t i=0u;i<64u;i++)if(app.recording.catalog.slots[i]!=255u) {
        REQUIRE(comp_wba_segment_storage_entry(&app.recording.storage,&app.recording.catalog,i,&old)==COMP_SEG_OK,"ready state original");
        if(old.state==COMP_SEG_WRITING){found=true;break;}
    }
    REQUIRE(found,"ready state missing writing segment");
    uint32_t at=COMP_WBA_NOR_RECORDING_BASE+old.extent_offset;
    fixture.flash[at+37u]^=1u;comp_wba_recording_product_fault(&app.recording,COMP_WBA_RECORDING_FAULT_DEADLINE);
    init_board(&app,&board);REQUIRE(wait_state(&app,COMP_WBA_RECORDING_FAULT,30000u),"ready state salvage boot");
    REQUIRE(comp_wba_recording_product_salvaging(&app.recording)&&!app.recording_ready,"ready state not in salvage");
    /* Only synthetic media: undo the injected corruption before remount. */
    fixture.flash[at+37u]^=1u;
    memset(&app.recording.space,0,sizeof(app.recording.space));
    fake_recovery_quiescent=true;fake_fail_idle_read_once=true;
    for(unsigned i=0u;i<100u&&fake_fail_idle_read_once;i++)comp_wba_recording_product_poll(&app.recording);
    REQUIRE(!fake_fail_idle_read_once&&comp_wba_recording_product_boot_retry_pending(&app.recording),"ready state retry not armed");
    /* Deliberately bypass step()'s fake initial lease callback: runtime
     * remount already owns the verified lease and must update its own cache. */
    for(unsigned i=0u;i<30000u&&!app.recording.ready;i++) {
        fixture.tick+=STEP_MS;comp_v11_product_app_poll(&app);
    }
    REQUIRE(app.recording.ready&&app.recording_ready&&!board.microphone.running,
        "successful runtime recovery left product readiness stale");
    REQUIRE(!comp_wba_recording_product_tail_retained(&app.recording),"resolved synthetic tail still flagged");
    free(fixture.flash);fake_recovery_quiescent=false;
    puts("PASS_SALVAGE_TO_HEALTHY_READY_REAL_APP_SOFTWARE_ONLY");return 0;
}

static int consume_read_recovery_journey(bool reboot,bool commit_failure)
{
    comp_v11_hal_t board;comp_v11_product_app_t app;
    memset(&fixture,0,sizeof(fixture));fixture.flash=malloc(FLASH_BYTES);
    REQUIRE(fixture.flash,"consume read fixture allocation");
    memset(fixture.flash,255u,FLASH_BYTES);layout_root();init_board(&app,&board);
    REQUIRE(wait_state(&app,COMP_WBA_RECORDING_IDLE,20000u),"initial mount");
    REQUIRE(comp_runtime_record(&app.runtime,true,fixture.tick)==COMP_RUNTIME_OK &&
        wait_state(&app,COMP_WBA_RECORDING_CAPTURING,20000u),"original START");
    step(&app,60u);
    REQUIRE(comp_runtime_record(&app.runtime,false,fixture.tick)==COMP_RUNTIME_OK &&
        wait_state(&app,COMP_WBA_RECORDING_TRANSFER_READY,30000u) && settled_space(&app),"original STOP");
    if(reboot) {
        init_board(&app,&board);
        REQUIRE(wait_state(&app,COMP_WBA_RECORDING_IDLE,30000u) && settled_space(&app),"reboot mount");
    }
    comp_segment_entry_t original={0};bool found=false;
    for(uint8_t i=0u;i<64u&&!found;i++)if(app.recording.catalog.slots[i]!=255u) {
        REQUIRE(comp_wba_segment_storage_entry(&app.recording.storage,&app.recording.catalog,i,&original)==COMP_SEG_OK,
            "original lookup");
        found=original.state==COMP_SEG_UNSYNCED;
    }
    REQUIRE(found && (reboot?!app.recording.pipeline.engine_bound:app.recording.pipeline.engine_bound),
        "original not sealed or recorder ownership unexpected");
    uint8_t *before=malloc(FLASH_BYTES);REQUIRE(before,"NOR snapshot allocation");
    memcpy(before,fixture.flash,FLASH_BYTES);unsigned starts=fixture.mic_starts;
    REQUIRE(comp_wba_recording_pipeline_consume(&app.recording.pipeline,&original.descriptor)==COMP_SEG_PENDING,
        "consume proof was not queued");
    fake_recovery_quiescent=true;
    if(commit_failure) {
        for(unsigned i=0u;i<1000u && !app.recording.catalog.phase;i++)comp_wba_recording_product_poll(&app.recording);
        REQUIRE(app.recording.catalog.phase && app.recording.catalog.pending==&app.recording.pipeline.consume,
            "consume ACK owner not retained");
    }
    fake_fail_idle_read_once=true;
    for(unsigned i=0u;i<100u&&fake_fail_idle_read_once;i++)comp_wba_recording_product_poll(&app.recording);
    REQUIRE(!fake_fail_idle_read_once && app.recording.storage.poisoned &&
        comp_wba_recording_pipeline_consume_result(&app.recording.pipeline)==COMP_SEG_IO_ERROR,
        "consume directory read failure not observed");
    if(commit_failure) {
        REQUIRE(!comp_wba_recording_pipeline_consume_idle_read_failed(&app.recording.pipeline) &&
            !comp_wba_recording_product_boot_retry_pending(&app.recording),
            "uncertain ACK incorrectly qualified as read-only");
        /* The catalog may terminate its RAM transaction on IO failure; the
         * poisoned medium and failed result must remain, with no replay. */
        memcpy(before,fixture.flash,FLASH_BYTES);
        step(&app,200u);
        REQUIRE(app.recording.storage.poisoned && app.recording.pipeline.state==COMP_PIPE_FAILED &&
            comp_wba_recording_pipeline_consume_result(&app.recording.pipeline)==COMP_SEG_IO_ERROR &&
            !comp_wba_recording_product_boot_retry_pending(&app.recording) &&
            !memcmp(before,fixture.flash,FLASH_BYTES) && !board.microphone.running && fixture.mic_starts==starts,
            "uncertain ACK was retried, modified, or auto-started");
        puts("PASS_CONSUME_ACK_UNCERTAIN_REMAINS_BLOCKED_SOFTWARE_ONLY");free(before);free(fixture.flash);return 0;
    }
    for(unsigned i=0u;i<30000u &&
        (!app.recording.ready || app.recording.pipeline.state!=COMP_PIPE_IDLE || app.recording.storage.poisoned);i++)step(&app,1u);
    REQUIRE(app.recording.ready && app.recording.pipeline.state==COMP_PIPE_IDLE && !app.recording.storage.poisoned,
        "read-only consume failure stranded recorder");
    REQUIRE(!memcmp(before,fixture.flash,FLASH_BYTES)&&fixture.mic_starts==starts&&!board.microphone.running,
        "read-only failure recovery modified media or started microphone");
    REQUIRE(comp_runtime_record(&app.runtime,true,fixture.tick)==COMP_RUNTIME_OK &&
        wait_state(&app,COMP_WBA_RECORDING_CAPTURING,30000u),"new START after consume read failure");
    step(&app,40u);
    REQUIRE(comp_runtime_record(&app.runtime,false,fixture.tick)==COMP_RUNTIME_OK &&
        wait_state(&app,COMP_WBA_RECORDING_TRANSFER_READY,30000u),"new STOP after consume read failure");
    REQUIRE(!memcmp(before+COMP_WBA_NOR_RECORDING_BASE+original.extent_offset,
        fixture.flash+COMP_WBA_NOR_RECORDING_BASE+original.extent_offset,original.reserved_bytes),
        "original extent changed after new recording");
    puts("PASS_CONSUME_READ_RECOVERY_REAL_APP_SOFTWARE_ONLY");free(before);free(fixture.flash);return 0;
}
static int recording_level_journey(void)
{
    comp_v11_hal_t board;comp_v11_product_app_t app;comp_wba_recording_level_snapshot_t level;
    memset(&fixture,0,sizeof(fixture));fixture.flash=malloc(FLASH_BYTES);
    REQUIRE(fixture.flash,"level fixture allocation");
    memset(fixture.flash,255u,FLASH_BYTES);layout_root();init_board(&app,&board);
    REQUIRE(wait_state(&app,COMP_WBA_RECORDING_IDLE,20000u),"level boot");
    REQUIRE(!comp_v11_product_recording_level(&app,fixture.tick,&level),"idle reported a live level");
    fixture.level_fixture=true;fixture.level_pcm=INT16_MIN;fixture.level_saturation_per_frame=3u;
    REQUIRE(comp_runtime_record(&app.runtime,true,fixture.tick)==COMP_RUNTIME_OK &&
        wait_state(&app,COMP_WBA_RECORDING_CAPTURING,20000u),"level start");
    REQUIRE(app.recording_level_enabled,"level did not follow microphone start");
    REQUIRE(!comp_v11_product_recording_level(&app,fixture.tick,&level),"partial window reported valid");
    step(&app,100u);
    REQUIRE(comp_v11_product_recording_level(&app,fixture.tick,&level) &&
        level.sampled_mean==32768u && level.sampled_peak==32768u && level.saturated_samples==300u,
        "final mono level or saturation count incorrect");
    REQUIRE(!comp_v11_product_recording_level(&app,fixture.tick+2000u,&level),"stale level remained valid");
    fixture.level_pcm=0;fixture.level_saturation_per_frame=0u;step(&app,100u);
    REQUIRE(comp_v11_product_recording_level(&app,fixture.tick,&level) &&
        !level.sampled_mean && !level.sampled_peak && !level.saturated_samples,
        "quiet output not measured or previous window persisted");
    comp_v11_product_recording_level_enable(&app,false);
    REQUIRE(!comp_v11_product_recording_level(&app,fixture.tick,&level),"disabled level remained visible");
    comp_v11_product_recording_level_enable(&app,true);
    REQUIRE(!comp_v11_product_recording_level(&app,fixture.tick,&level),"re-enable exposed old output window");
    REQUIRE(comp_runtime_record(&app.runtime,false,fixture.tick)==COMP_RUNTIME_OK &&
        wait_state(&app,COMP_WBA_RECORDING_TRANSFER_READY,30000u),"level stop");
    REQUIRE(!app.recording_level_enabled,"level did not follow microphone stop");
    REQUIRE(!comp_v11_product_recording_level(&app,fixture.tick,&level),"stopped capture reported a live level");
    puts("PASS_RECORDING_OUTPUT_LEVEL_REAL_APP_SOFTWARE_ONLY");free(fixture.flash);return 0;
}
static int external_read_recovery_journey(void)
{
    comp_v11_hal_t board;comp_v11_product_app_t app;
    memset(&fixture,0,sizeof(fixture));fixture.flash=malloc(FLASH_BYTES);
    REQUIRE(fixture.flash,"external read fixture allocation");
    memset(fixture.flash,255u,FLASH_BYTES);layout_root();init_board(&app,&board);
    REQUIRE(wait_state(&app,COMP_WBA_RECORDING_IDLE,20000u),"initial mount");
    REQUIRE(comp_runtime_record(&app.runtime,true,fixture.tick)==COMP_RUNTIME_OK &&
        wait_state(&app,COMP_WBA_RECORDING_CAPTURING,20000u),"original START");
    step(&app,60u);
    REQUIRE(comp_runtime_record(&app.runtime,false,fixture.tick)==COMP_RUNTIME_OK &&
        wait_state(&app,COMP_WBA_RECORDING_TRANSFER_READY,30000u),"original STOP");
    init_board(&app,&board);
    REQUIRE(wait_state(&app,COMP_WBA_RECORDING_IDLE,30000u)&&settled_space(&app),"reboot mount");
    uint8_t slot=255u;for(uint8_t i=0u;i<64u;i++)if(app.recording.catalog.slots[i]!=255u){slot=i;break;}
    REQUIRE(slot!=255u && app.recording.space.valid,"expected existing original and cached capacity");
    uint8_t *before=malloc(FLASH_BYTES);REQUIRE(before,"NOR snapshot allocation");
    memcpy(before,fixture.flash,FLASH_BYTES);unsigned starts=fixture.mic_starts;
    comp_segment_entry_t entry={0};fake_recovery_quiescent=true;fake_fail_idle_read_once=true;
    REQUIRE(comp_wba_segment_storage_entry(&app.recording.storage,&app.recording.catalog,slot,&entry)==COMP_SEG_IO_ERROR &&
        !fake_fail_idle_read_once && app.recording.storage.poisoned,"directory read failure not injected");
    REQUIRE(!comp_wba_recording_product_space_current(&app.recording),"poisoned cache still advertised current");
    for(unsigned i=0u;i<30000u &&
        (!app.recording.ready || app.recording.storage.poisoned);i++)step(&app,1u);
    REQUIRE(app.recording.ready&&!app.recording.storage.poisoned && app.recording.pipeline.state==COMP_PIPE_IDLE,
        "external read error left stale ready and poisoned storage");
    REQUIRE(!memcmp(before,fixture.flash,FLASH_BYTES)&&!board.microphone.running&&fixture.mic_starts==starts,
        "external read recovery modified media or started microphone");
    REQUIRE(comp_runtime_record(&app.runtime,true,fixture.tick)==COMP_RUNTIME_OK &&
        wait_state(&app,COMP_WBA_RECORDING_CAPTURING,30000u),"new capture after read recovery");
    REQUIRE(comp_runtime_record(&app.runtime,false,fixture.tick)==COMP_RUNTIME_OK &&
        wait_state(&app,COMP_WBA_RECORDING_TRANSFER_READY,30000u),"new stop after read recovery");
    puts("PASS_EXTERNAL_READ_RECOVERY_REAL_APP_SOFTWARE_ONLY");free(before);free(fixture.flash);return 0;
}
#ifdef COMPANION_TEST_SEALED_PULL_RECOVERY
static bool recovery_allow(void *ctx) {(void)ctx;return true;}
static bool recovery_notify(void *ctx,const uint8_t *value,uint16_t n) {(void)ctx;(void)value;(void)n;return true;}
static int sealed_payload_read_recovery_journey(void)
{
    comp_v11_hal_t board;comp_v11_product_app_t app;
    memset(&fixture,0,sizeof(fixture));fixture.flash=malloc(FLASH_BYTES);
    REQUIRE(fixture.flash,"external read fixture allocation");
    memset(fixture.flash,255u,FLASH_BYTES);layout_root();init_board(&app,&board);
    REQUIRE(wait_state(&app,COMP_WBA_RECORDING_IDLE,20000u),"initial mount");
    REQUIRE(comp_runtime_record(&app.runtime,true,fixture.tick)==COMP_RUNTIME_OK &&
        wait_state(&app,COMP_WBA_RECORDING_CAPTURING,20000u),"original START");
    step(&app,60u);
    REQUIRE(comp_runtime_record(&app.runtime,false,fixture.tick)==COMP_RUNTIME_OK &&
        wait_state(&app,COMP_WBA_RECORDING_TRANSFER_READY,30000u),"original STOP");
    init_board(&app,&board);
    REQUIRE(wait_state(&app,COMP_WBA_RECORDING_IDLE,30000u)&&settled_space(&app),"reboot mount");
    uint8_t slot=255u;for(uint8_t i=0u;i<64u;i++)if(app.recording.catalog.slots[i]!=255u){slot=i;break;}
    REQUIRE(slot!=255u && app.recording.space.valid,"expected existing original and cached capacity");
    uint8_t *before=malloc(FLASH_BYTES);REQUIRE(before,"NOR snapshot allocation");
    memcpy(before,fixture.flash,FLASH_BYTES);unsigned starts=fixture.mic_starts;
    comp_segment_entry_t entry={0},selected={0};
    REQUIRE(comp_wba_segment_storage_entry(&app.recording.storage,&app.recording.catalog,slot,&entry)==COMP_SEG_OK,"sealed entry");
    comp_wba_segment_pull_t pull;comp_wba_recording_transfer_t transfer;uint8_t page[256],request[32]={0};
    comp_wba_segment_pull_config_t cfg={&app.recording.storage,&app.recording.catalog,&transfer,&selected,page,
        recovery_allow,recovery_allow,recovery_notify,NULL};
    REQUIRE(comp_wba_segment_pull_init(&pull,&cfg),"pull init");
    REQUIRE(comp_wba_segment_pull_peer(&pull,app.recording.catalog.uid,app.recording.catalog.epoch,true),"pull peer");
    request[0]=2u;request[1]=0x21u;request[2]=4u;
    comp_rec_put32(request+4u,entry.descriptor.recording_id);comp_rec_put64(request+8u,entry.descriptor.format_epoch);
    comp_rec_put64(request+16u,entry.descriptor.session_id);comp_rec_put32(request+24u,entry.descriptor.segment_index);
    REQUIRE(comp_wba_segment_pull_begin(&pull,request)==COMP_SEG_PENDING,"pull begin");
    for(unsigned i=0u;i<1000u&&transfer.state==COMP_WBA_RECORDING_TRANSFER_IDLE;i++) {
        comp_segment_result_t selected_result=comp_wba_segment_pull_select_poll(&pull);
        REQUIRE(selected_result==COMP_SEG_PENDING||selected_result==COMP_SEG_OK,"pull selection");
    }
    REQUIRE(transfer.state==COMP_WBA_RECORDING_TRANSFER_ACTIVE,"pull active");
    fake_recovery_quiescent=true;fake_fail_idle_read_once=true;
    comp_segment_result_t result=COMP_SEG_PENDING;
    for(unsigned i=0u;i<1000u&&result==COMP_SEG_PENDING;i++)result=comp_wba_segment_pull_poll(&pull);
    REQUIRE(result==COMP_SEG_IO_ERROR && !fake_fail_idle_read_once && app.recording.storage.poisoned &&
        app.recording.storage.idle_lookup_read_failed,"sealed audio read failure not recoverable");
    comp_wba_segment_pull_cancel(&pull); /* release transfer owner before remount */
    REQUIRE(!comp_wba_recording_product_space_current(&app.recording),"poisoned cache still advertised current");
    for(unsigned i=0u;i<30000u &&
        (!app.recording.ready || app.recording.storage.poisoned);i++)step(&app,1u);
    REQUIRE(app.recording.ready&&!app.recording.storage.poisoned && app.recording.pipeline.state==COMP_PIPE_IDLE,
        "external read error left stale ready and poisoned storage");
    REQUIRE(!memcmp(before,fixture.flash,FLASH_BYTES)&&!board.microphone.running&&fixture.mic_starts==starts,
        "external read recovery modified media or started microphone");
    REQUIRE(comp_runtime_record(&app.runtime,true,fixture.tick)==COMP_RUNTIME_OK &&
        wait_state(&app,COMP_WBA_RECORDING_CAPTURING,30000u),"new capture after read recovery");
    REQUIRE(comp_runtime_record(&app.runtime,false,fixture.tick)==COMP_RUNTIME_OK &&
        wait_state(&app,COMP_WBA_RECORDING_TRANSFER_READY,30000u),"new stop after read recovery");
    puts("PASS_SEALED_PAYLOAD_READ_RECOVERY_REAL_APP_SOFTWARE_ONLY");free(before);free(fixture.flash);return 0;
}
static int sealed_read_fault_active_app_journey(void)
{
    comp_v11_hal_t board;comp_v11_product_app_t app;
    memset(&fixture,0,sizeof(fixture));fixture.flash=malloc(FLASH_BYTES);
    REQUIRE(fixture.flash,"active read fixture allocation");memset(fixture.flash,255u,FLASH_BYTES);layout_root();init_board(&app,&board);
    REQUIRE(wait_state(&app,COMP_WBA_RECORDING_IDLE,20000u),"initial mount");
    REQUIRE(comp_runtime_record(&app.runtime,true,fixture.tick)==COMP_RUNTIME_OK &&
        wait_state(&app,COMP_WBA_RECORDING_CAPTURING,20000u),"original START");
    step(&app,60u);
    REQUIRE(comp_runtime_record(&app.runtime,false,fixture.tick)==COMP_RUNTIME_OK &&
        wait_state(&app,COMP_WBA_RECORDING_TRANSFER_READY,30000u),"original STOP");
    init_board(&app,&board);REQUIRE(wait_state(&app,COMP_WBA_RECORDING_IDLE,30000u)&&settled_space(&app),"reboot mount");
    uint8_t slot=255u;for(uint8_t i=0u;i<64u;i++)if(app.recording.catalog.slots[i]!=255u){slot=i;break;}
    comp_segment_entry_t entry={0},selected={0};
    REQUIRE(slot!=255u&&comp_wba_segment_storage_entry(&app.recording.storage,&app.recording.catalog,slot,&entry)==COMP_SEG_OK,"saved original");
    uint8_t *before=malloc(entry.reserved_bytes);REQUIRE(before,"original snapshot");
    memcpy(before,fixture.flash+COMP_WBA_NOR_RECORDING_BASE+entry.extent_offset,entry.reserved_bytes);
    REQUIRE(comp_runtime_record(&app.runtime,true,fixture.tick)==COMP_RUNTIME_OK &&
        wait_state(&app,COMP_WBA_RECORDING_CAPTURING,20000u),"second START");
    uint32_t accepted=app.recording.capture.engine.stats.accepted_pcm_blocks;
    comp_wba_segment_pull_t pull;comp_wba_recording_transfer_t transfer;uint8_t page[256],request[32]={0};
    comp_wba_segment_pull_config_t cfg={&app.recording.storage,&app.recording.catalog,&transfer,&selected,page,
        recovery_allow,recovery_allow,recovery_notify,NULL};
    REQUIRE(comp_wba_segment_pull_init(&pull,&cfg) && comp_wba_segment_pull_peer(&pull,app.recording.catalog.uid,app.recording.catalog.epoch,true),"pull init/peer");
    request[0]=2u;request[1]=0x21u;request[2]=4u;
    comp_rec_put32(request+4u,entry.descriptor.recording_id);comp_rec_put64(request+8u,entry.descriptor.format_epoch);
    comp_rec_put64(request+16u,entry.descriptor.session_id);comp_rec_put32(request+24u,entry.descriptor.segment_index);
    REQUIRE(comp_wba_segment_pull_begin(&pull,request)==COMP_SEG_PENDING,"pull begin");
    for(unsigned i=0u;i<1000u&&transfer.state==COMP_WBA_RECORDING_TRANSFER_IDLE;i++) {
        comp_segment_result_t r=comp_wba_segment_pull_select_poll(&pull);
        REQUIRE(r==COMP_SEG_PENDING||r==COMP_SEG_OK,"pull selection");
    }
    REQUIRE(transfer.state==COMP_WBA_RECORDING_TRANSFER_ACTIVE,"pull active");
    fake_fail_stream_payload_once=true;comp_segment_result_t r=COMP_SEG_PENDING;
    for(unsigned i=0u;i<1000u&&r==COMP_SEG_PENDING;i++)r=comp_wba_segment_pull_poll(&pull);
    REQUIRE(r==COMP_SEG_OK&&!fake_fail_stream_payload_once&&!app.recording.storage.poisoned&&board.microphone.running,
        "radio read did not recover or poisoned active capture");
    comp_wba_segment_pull_cancel(&pull);step(&app,100u);
    REQUIRE(board.microphone.running&&app.recording.capture.engine.stats.accepted_pcm_blocks>accepted&&
        comp_wba_recording_product_state(&app.recording)==COMP_WBA_RECORDING_CAPTURING,"capture did not continue");
    REQUIRE(comp_runtime_record(&app.runtime,false,fixture.tick)==COMP_RUNTIME_OK &&
        wait_state(&app,COMP_WBA_RECORDING_TRANSFER_READY,30000u),"second STOP");
    REQUIRE(!memcmp(before,fixture.flash+COMP_WBA_NOR_RECORDING_BASE+entry.extent_offset,entry.reserved_bytes),"original changed");
    puts("PASS_ACTIVE_APP_SURVIVES_RADIO_PAYLOAD_FAULT_SOFTWARE_ONLY");free(before);free(fixture.flash);return 0;
}

#endif
static int resource_timeout_journey(unsigned mode)
{
    comp_v11_hal_t board;comp_v11_product_app_t app;
    memset(&fixture,0,sizeof(fixture));fixture.flash=malloc(FLASH_BYTES);
    REQUIRE(fixture.flash,"model NOR allocation");memset(fixture.flash,255u,FLASH_BYTES);layout_root();
    init_board(&app,&board);REQUIRE(wait_state(&app,COMP_WBA_RECORDING_IDLE,20000u),"boot");
    comp_power_policy_init(&board.power);comp_power_policy_set_blocker(&board.power,COMP_POWER_BLOCKER_BOOT,false);
    comp_power_policy_set_button_wake_ready(&board.power,true);
    key(&app,true,COMPANION_WBA_SCREEN_ENABLED?75u:110u);key(&app,false,4u);
    REQUIRE(wait_state(&app,COMP_WBA_RECORDING_CAPTURING,20000u),"capture start");
    board.nor.config.target=COMPANION_SPI_NOR_STM32WBA_TARGET_WBA55;
    board.nor.info.jedec_id=0xef6018u;board.nor.config.transfer_timeout_ms=200u;
    fake_resource_bounded=true;fixture.resource_read_ms=50u;fixture.resource_reads=0u;
    fake_resource_uncertain=mode==1u;fake_resource_pending=mode==2u;
    uint8_t resource[256];uint32_t started=fixture.tick;
    if(mode==3u) {
        /* A non-recorder microphone owner keeps its existing resource path. */
        app.recording.capture.engine.microphone_active=false;fixture.resource_read_ms=1u;
        REQUIRE(fixture.resources.read(fixture.resources.context,0u,resource,sizeof(resource))&&
            fixture.resource_reads==1u&&fixture.resource_bounded_calls==0u&&
            !memcmp(resource,fixture.flash,sizeof(resource)),"non-recorder resource path changed");
        puts("PASS non-recorder microphone owner keeps original resource path; software only");
        free(fixture.flash);return 0;
    }
    REQUIRE(!fixture.resources.read(fixture.resources.context,0u,resource,sizeof(resource)),"failed resource read must not succeed");
    if(mode==1u) {
        REQUIRE(!board.microphone.running&&app.recording.storage.poisoned&&
            app.recording.last_fault==COMP_WBA_RECORDING_FAULT_STORAGE_IO,
            "uncertain resource bus failure did not stop capture and retain fault");
        unsigned reads=fixture.resource_reads;
        REQUIRE(!fixture.resources.read(fixture.resources.context,0u,resource,sizeof(resource))&&
            fixture.resource_reads==reads,"resource path reused uncertain shared bus");
        puts("PASS uncertain resource bus failure stops capture and retains storage fault; software only");
        free(fixture.flash);return 0;
    }
    REQUIRE(fixture.tick-started<=8u&&board.microphone.running&&app.capture_deadline_faults==0u,
        "resource read stalled or stopped the recording");
    fake_resource_pending=false;fixture.resource_read_ms=1u;uint8_t normal[512];unsigned reads=fixture.resource_reads;
    REQUIRE(fixture.resources.read(fixture.resources.context,0u,normal,sizeof(normal))&&
        fixture.resource_reads==reads+2u&&!memcmp(normal,fixture.flash,sizeof(normal)),
        "normal two-page resource read did not recover");
    REQUIRE(board.microphone.running&&app.capture_deadline_faults==0u,"audio did not survive resource recovery");
    board.nor.info.jedec_id=0x0b6018u;reads=fixture.resource_reads;
    REQUIRE(fixture.resources.read(fixture.resources.context,0u,resource,sizeof(resource))&&
        fixture.resource_reads==reads+1u&&!memcmp(resource,fixture.flash,sizeof(resource)),
        "unqualified NOR did not keep original resource path");
    board.nor.info.jedec_id=0xef6018u;
    fake_resource_bounded=false;fixture.resource_read_ms=0u;
    key(&app,true,COMPANION_WBA_SCREEN_ENABLED?75u:110u);key(&app,false,4u);
    REQUIRE(wait_state(&app,COMP_WBA_RECORDING_TRANSFER_READY,20000u),"STOP after resource read fault");
    puts("PASS recording survives bounded resource read failure and normal resource access resumes; software only");
    free(fixture.flash);return 0;
}
static int full_stop_notice_journey(void)
{
    comp_v11_hal_t board;comp_v11_product_app_t app;
    memset(&fixture,0,sizeof(fixture));fixture.flash=malloc(FLASH_BYTES);
    REQUIRE(fixture.flash,"full notice fixture allocation");
    memset(fixture.flash,255u,FLASH_BYTES);layout_root();init_board(&app,&board);
    REQUIRE(wait_state(&app,COMP_WBA_RECORDING_IDLE,20000u),"full notice boot");
    REQUIRE(comp_runtime_record(&app.runtime,true,fixture.tick)==COMP_RUNTIME_OK &&
        wait_state(&app,COMP_WBA_RECORDING_CAPTURING,20000u),"full notice start");
    REQUIRE(app.recording.report && app.recording.pipeline.engine_bound,"actual callback not bound");
    uint32_t token=app.runtime.record_token;
    app.recording.capture.engine.stop_reason=COMP_CONT_STOP_FULL;
    app.recording.report(app.recording.pipeline.config.context,token+1u,DENZIC_AUDIO_RECORDING_STATE_TRANSFER_READY,false);
    REQUIRE(app.runtime.record_stop_reason!=COMP_RECORD_STOP_STORAGE_FULL,"stale token reported full");
    app.recording.report(app.recording.pipeline.config.context,token,DENZIC_AUDIO_RECORDING_STATE_STOPPING,false);
    REQUIRE(app.runtime.record_stop_reason!=COMP_RECORD_STOP_STORAGE_FULL,"unsealed recording reported saved full");
    app.recording.report(app.recording.pipeline.config.context,token,DENZIC_AUDIO_RECORDING_STATE_TRANSFER_READY,false);
    REQUIRE(app.runtime.record_stop_reason==COMP_RECORD_STOP_STORAGE_FULL &&
        app.runtime.recording==DENZIC_AUDIO_RECORDING_STATE_TRANSFER_READY && app.runtime.record_saved_state,
        "sealed full recording not visibly distinguished or no longer available");
    app.runtime.record_stop_reason=COMP_RECORD_STOP_NONE;
    app.runtime.recording=DENZIC_AUDIO_RECORDING_STATE_RECORDING;
    app.recording.capture.engine.stop_reason=COMP_CONT_STOP_USER;
    app.recording.report(app.recording.pipeline.config.context,token,DENZIC_AUDIO_RECORDING_STATE_TRANSFER_READY,false);
    REQUIRE(app.runtime.record_stop_reason!=COMP_RECORD_STOP_STORAGE_FULL,"normal stop reported full");
    puts("PASS full stop actual product callback: only current sealed full recording; normal and stale reports unchanged");
    free(fixture.flash);return 0;
}
static int idle_display_failure_journey(void)
{
    comp_v11_hal_t board={0};comp_v11_product_app_t app={0};app.board=&board;
    comp_power_policy_init(&board.power);
    comp_power_policy_set_blocker(&board.power,COMP_POWER_BLOCKER_BOOT,false);
    comp_power_policy_set_button_wake_ready(&board.power,true);
    app.runtime.menu.browser.auto_sleep_minutes=1u;
    app.runtime.frame_outstanding=true;app.runtime.revision=2u;
    board.panel.status=COMP_SSD1681_WBA_ERROR;
    fixture.tick=59999u;
    REQUIRE(!comp_v11_product_update_idle_policy(&app),"failed screen ignored inactivity timer");
    fixture.tick=60000u;
    REQUIRE(comp_v11_product_update_idle_policy(&app),"failed screen retained impossible visible-frame vote");
    board.microphone.running=true;
    REQUIRE(!comp_v11_product_update_idle_policy(&app),"failed screen bypassed microphone");
    board.microphone.running=false;
    comp_power_policy_set_blocker(&board.power,COMP_POWER_BLOCKER_UPDATE,true);
    REQUIRE(!comp_v11_product_update_idle_policy(&app),"failed screen bypassed OTA");
    comp_power_policy_set_blocker(&board.power,COMP_POWER_BLOCKER_UPDATE,false);
    app.runtime.last_activity_ms=fixture.tick;
    REQUIRE(!comp_v11_product_update_idle_policy(&app),"new activity did not wake idle policy");
    app.runtime.last_activity_ms=0u;app.runtime.menu.browser.auto_sleep_minutes=0u;
    REQUIRE(!comp_v11_product_update_idle_policy(&app),"disabled sleep ignored");
    app.runtime.menu.browser.auto_sleep_minutes=1u;app.assets_ready=true;
    board.panel.status=COMP_SSD1681_WBA_IDLE;
    REQUIRE(!comp_v11_product_update_idle_policy(&app),"healthy screen bypassed visible completion");
    board.panel.status=COMP_SSD1681_WBA_ACTIVE;app.assets_ready=false;
    REQUIRE(!comp_v11_product_update_idle_policy(&app),"active panel transaction bypassed");
    puts("PASS failed display idle policy: real inactivity, microphone/OTA/activity/disabled timer and active panel retained; healthy display completion unchanged");
    return 0;
}
static int idle_prime_handoff_journey(void)
{
    for(unsigned cancel=0u;cancel<2u;++cancel) {
        comp_v11_hal_t board;comp_v11_product_app_t app;
        memset(&fixture,0,sizeof(fixture));fixture.flash=malloc(FLASH_BYTES);
        REQUIRE(fixture.flash,"idle prime NOR allocation");memset(fixture.flash,255u,FLASH_BYTES);layout_root();
        init_board(&app,&board);REQUIRE(wait_state(&app,COMP_WBA_RECORDING_IDLE,20000u),"idle prime boot");
        (void)comp_wba_recording_pipeline_prime(&app.recording.pipeline,false);
        memset(fixture.flash+app.recording.catalog.data_base,0x5au,app.recording.catalog.data_bytes);
        fake_hold_erase=true;fake_finish_erase=false;
        for(unsigned i=0u;i<20000u&&!board.nor.erase_active;++i)step(&app,1u);
        REQUIRE(board.nor.erase_active&&comp_wba_recording_pipeline_primed(&app.recording.pipeline),"no owned idle erase");
        uint64_t next=app.recording_identity.record.next_session_id;
        REQUIRE(comp_runtime_record(&app.runtime,true,fixture.tick)==COMP_RUNTIME_OK,"START while idle erase refused");
        step(&app,3u);
        REQUIRE(app.runtime.prepare_pending&&!board.microphone.running&&
            app.recording_identity.record.next_session_id==next,"identity persisted before erase retired");
        if(cancel)REQUIRE(comp_runtime_record(&app.runtime,false,fixture.tick)==COMP_RUNTIME_OK,"pending idle handoff cancel failed");
        fake_finish_erase=true;step(&app,2u);
        if(cancel) {
            step(&app,200u);
            REQUIRE(!app.runtime.prepare_pending&&!fixture.mic_starts&&app.recording_identity.record.next_session_id==next,
                "canceled idle handoff auto-started or burned session");
        } else {
            REQUIRE(wait_state(&app,COMP_WBA_RECORDING_CAPTURING,20000u),"handoff did not start after quiescence");
            REQUIRE(fixture.mic_starts==1u&&app.recording_identity.record.next_session_id==next+1u&&
                !fixture.mic_before_durable_identity,"handoff identity/one-start ordering");
            step(&app,60u);
            REQUIRE(comp_runtime_record(&app.runtime,false,fixture.tick)==COMP_RUNTIME_OK,"handoff STOP");
            REQUIRE(wait_state(&app,COMP_WBA_RECORDING_TRANSFER_READY,20000u),"handoff seal");
        }
        free(fixture.flash);
    }
    puts("PASS real product idle erase handoff: explicit START waits before CSI1 persistence, one MIC start after durable identity; cancel allocates nothing and never auto-starts");
    return 0;
}
static int late_release_button_journey(void)
{
    comp_v11_hal_t board;comp_v11_product_app_t app;
    memset(&fixture,0,sizeof(fixture));fixture.flash=malloc(FLASH_BYTES);
    REQUIRE(fixture.flash,"late release NOR allocation");memset(fixture.flash,255u,FLASH_BYTES);layout_root();
    init_board(&app,&board);REQUIRE(wait_state(&app,COMP_WBA_RECORDING_IDLE,20000u),"late release boot");
    fixture.tick+=200000u;step(&app,5u);
    /* DOWN was sampled/debounced. A foreground gap crosses the threshold;
     * the next physical level is already UP. This is still one long hold. */
    key(&app,true,4u);key(&app,true,60u);fixture.tick+=500u;key(&app,false,4u);
    REQUIRE(wait_state(&app,COMP_WBA_RECORDING_CAPTURING,20000u),"released long press lost across foreground gap");
    step(&app,100u);
    /* Release exactly at the product threshold without a prior held poll. */
    key(&app,true,4u);key(&app,true,COMPANION_WBA_SCREEN_ENABLED?66u:96u);key(&app,false,4u);
    REQUIRE(wait_state(&app,COMP_WBA_RECORDING_TRANSFER_READY,20000u),"threshold release did not STOP");
    REQUIRE(fixture.mic_starts==1u&&!board.microphone.running&&app.recording.last_fault==0u,
        "late release repeated toggle or recording fault");
    puts("PASS Capture real product long press: late release across idle foreground gap starts once; threshold release stops and seals without a wired recording command");
    free(fixture.flash);return 0;
}
static int feedback_saved_checks(comp_v11_product_app_t *app)
{
    comp_wba_recording_product_t *product=&app->recording;
    comp_cont_recording_t *engine=&product->capture.engine;
    comp_capture_feedback_t view=comp_v11_product_capture_feedback(app,false);
    REQUIRE(view.state==COMP_CAPTURE_SAVED&&(view.flags&COMP_CAPTURE_ORIGINAL_SAVED),
        "saved feedback before sealed/catalog durability");
    REQUIRE((view.flags&COMP_CAPTURE_MARK_CONFIRMED)&&view.bookmark_request==engine->bookmark_request,
        "latest durable mark missing from feedback");
    /* Sealing invalidates the generation-qualified free-space walk. Its busy
     * interval is unknown capacity, even though this recording is saved. */
    for(uint32_t i=0u;i<20000u&&!(view.flags&COMP_CAPTURE_CAPACITY_KNOWN);++i) {
        REQUIRE(view.state!=COMP_CAPTURE_FULL,"busy capacity reported full");
        step(app,1u);view=comp_v11_product_capture_feedback(app,false);
    }
    REQUIRE(view.flags&COMP_CAPTURE_CAPACITY_KNOWN,"idle capacity walk did not complete");
    const uint32_t generation=product->catalog.generation;
    const uint32_t preferences=app->preferences.generation;
    const comp_wba_recording_space_t space=product->space;
    product->space.generation^=1u;
    view=comp_v11_product_capture_feedback(app,false);
    REQUIRE(!(view.flags&COMP_CAPTURE_CAPACITY_KNOWN)&&view.state!=COMP_CAPTURE_FULL,
        "stale capacity claimed full/known");
    product->space=space;
    REQUIRE((view=comp_v11_product_capture_feedback(app,true)).state==COMP_CAPTURE_UPDATING,
        "actual update owner has no feedback priority");
    product->space.used=COMP_SEGMENT_CAPACITY;product->space.allocatable_segments=0u;
    product->space.largest_gap=product->pipeline.config.extent_bytes*4u;
    view=comp_v11_product_capture_feedback(app,false);
    REQUIRE(view.state==COMP_CAPTURE_FULL&&(view.full_reason&COMP_CAPTURE_FULL_SLOTS)&&
        (view.flags&COMP_CAPTURE_ORIGINAL_SAVED),"catalog slots/full preserved-original distinction");
    product->space.used=0u;product->space.largest_gap=product->pipeline.config.extent_bytes-1u;
    view=comp_v11_product_capture_feedback(app,false);
    REQUIRE(view.state==COMP_CAPTURE_FULL&&(view.full_reason&COMP_CAPTURE_FULL_EXTENT)&&
        !(view.full_reason&COMP_CAPTURE_FULL_SLOTS),"fragmented bytes mistaken for usable extent");
    product->space=space;
    const comp_cont_stop_t stop=engine->stop_reason;
    engine->stop_reason=COMP_CONT_STOP_FULL;
    view=comp_v11_product_capture_feedback(app,false);
    REQUIRE(view.state==COMP_CAPTURE_SAVED&&(view.full_reason&COMP_CAPTURE_FULL_STOP),
        "historical full stop hid currently available capacity");
    engine->stop_reason=stop;
    product->catalog.phase=1u;view=comp_v11_product_capture_feedback(app,false);
    REQUIRE(view.state==COMP_CAPTURE_SAVING&&!(view.flags&COMP_CAPTURE_ORIGINAL_SAVED),
        "uncommitted catalog reported saved");
    product->catalog.phase=0u;
    const comp_cont_state_t state=engine->state;
    const comp_segment_result_t failure=engine->failure;
    engine->state=COMP_CONT_FAULT;engine->failure=COMP_SEG_IO_ERROR;
    view=comp_v11_product_capture_feedback(app,false);
    REQUIRE(view.state==COMP_CAPTURE_ERROR&&!(view.flags&COMP_CAPTURE_MARK_CONFIRMED),
        "failed writer reported successful mark");
    engine->state=COMP_CONT_CANCELED;
    view=comp_v11_product_capture_feedback(app,false);
    REQUIRE(view.state==COMP_CAPTURE_IDLE&&!(view.flags&(COMP_CAPTURE_ORIGINAL_SAVED|COMP_CAPTURE_MARK_CONFIRMED)),
        "canceled prepared writer reported saved original");
    engine->state=state;engine->failure=failure;
    const comp_wba_pipeline_state_t phase=product->pipeline.state;
    const comp_segment_result_t pipeline_failure=product->pipeline.failure;
    product->pipeline.state=COMP_PIPE_FAILED;product->pipeline.failure=COMP_SEG_FULL;
    view=comp_v11_product_capture_feedback(app,false);
    REQUIRE(view.state==COMP_CAPTURE_FULL&&(view.full_reason&COMP_CAPTURE_FULL_ALLOCATION)&&
        !(view.flags&COMP_CAPTURE_ORIGINAL_SAVED),"failed full allocation reported saved or generic error");
    product->pipeline.state=phase;product->pipeline.failure=pipeline_failure;
    REQUIRE(product->catalog.generation==generation&&app->preferences.generation==preferences,
        "feedback changed storage or preferences");
    return 0;
}
static int capture_controls_journey(const char *path)
{
    comp_v11_hal_t board;comp_v11_product_app_t app;
    REQUIRE(!COMPANION_WBA_SCREEN_ENABLED,"Capture journey requires no-screen build");
    memset(&fixture,0,sizeof(fixture));fixture.flash=malloc(FLASH_BYTES);
    REQUIRE(fixture.flash,"Capture control NOR allocation");memset(fixture.flash,255u,FLASH_BYTES);layout_root();
    init_board(&app,&board);REQUIRE(wait_state(&app,COMP_WBA_RECORDING_IDLE,20000u),"Capture control boot");
    feedback_observed=0u;feedback_watch=true;
    uint8_t calendar_settings[17];comp_v11_product_calendar_settings(&app,calendar_settings);
    REQUIRE(comp_rec_get32(calendar_settings+13u)==0u,"unsynchronized date fabricated");
    key(&app,true,80u);key(&app,false,4u);
    REQUIRE(fixture.mic_starts==0u,"sub-second press started recording");
    fixture.tick+=200000u;step(&app,5u);
    const uint32_t calendar_anchor=20001u*86400u-1u;
    calendar_settings[10]=23u;calendar_settings[11]=59u;calendar_settings[12]=59u;
    comp_rec_put32(calendar_settings+13u,calendar_anchor);
    uint32_t saved_preferences=app.preferences.generation;
    REQUIRE(comp_v11_product_apply_settings(&app,calendar_settings,sizeof(calendar_settings)) &&
        app.clock.calendar_valid && app.preferences.generation==saved_preferences,"calendar-only sync wrote NOR or failed");
    comp_clock_t date_before=app.clock;
    calendar_settings[10]=22u;
    REQUIRE(!comp_v11_product_apply_settings(&app,calendar_settings,sizeof(calendar_settings)) &&
        !memcmp(&date_before,&app.clock,sizeof(date_before)),"inconsistent date/time changed clock");
    calendar_settings[10]=23u;
    app.runtime.surface=COMP_SCREEN_SURFACE_LOW_POWER;
    app.button.last_event=0u;
    /* An idle input/storage pass can span a complete80ms short press. */
    fixture.key_pressed=true;
    comp_v11_wake_events_note_key_isr(&board.wake_events,COMP_V11_WAKE_KEY_FALLING,fixture.tick);
    fixture.tick+=80u;fixture.key_pressed=false;
    comp_v11_wake_events_note_key_isr(&board.wake_events,COMP_V11_WAKE_KEY_RISING,fixture.tick);
    step(&app,4u);
    REQUIRE((app.button.last_event&COMP_WBA_BUTTON_CONFIRM)!=0u,
        "idle short press lost between foreground polls");
    app.runtime.surface=COMP_SCREEN_SURFACE_LOW_POWER;
    key(&app,true,110u);key(&app,false,4u);
    REQUIRE(wait_state(&app,COMP_WBA_RECORDING_CAPTURING,20000u),"single held wake did not start Capture");
    step(&app,30u);
    comp_cont_recording_t *engine=&app.recording.capture.engine;
    REQUIRE(engine->state==COMP_CONT_RUNNING&&fixture.mic_starts==1u,"Capture start not stable");
    comp_capture_feedback_t feedback=comp_v11_product_capture_feedback(&app,false);
    REQUIRE(feedback.state==COMP_CAPTURE_RECORDING&&(feedback.flags&COMP_CAPTURE_MIC_RUNNING),
        "feedback missed actual microphone capture");
    const uint32_t first_blocks=engine->stats.accepted_pcm_blocks;
    engine->stats.accepted_pcm_blocks=0u;
    REQUIRE(comp_v11_product_capture_feedback(&app,false).state==COMP_CAPTURE_PREPARING,
        "microphone request reported recording before first PCM");
    engine->stats.accepted_pcm_blocks=first_blocks;
    const comp_cont_state_t running=engine->state;
    engine->state=COMP_CONT_PAUSE_PENDING;
    REQUIRE(comp_v11_product_capture_feedback(&app,false).state==COMP_CAPTURE_PAUSING,"pending pause claimed paused");
    engine->state=COMP_CONT_RESUMING;
    REQUIRE(comp_v11_product_capture_feedback(&app,false).state==COMP_CAPTURE_RESUMING,"pending resume claimed recording");
    engine->state=running;
    app.recording.media_ready=false;
    REQUIRE(comp_v11_product_capture_feedback(&app,false).state==COMP_CAPTURE_PREPARING,
        "recovery union mistaken for active engine");
    app.recording.media_ready=true;
    REQUIRE(comp_v11_product_capture_feedback(NULL,false).state==COMP_CAPTURE_UNKNOWN,
        "missing product reported a known state");
    uint32_t recorded_date=engine->active.started_unix_s;
    REQUIRE(recorded_date>=calendar_anchor && recorded_date<=calendar_anchor+5u,"Capture date not persisted from synchronized clock");
    REQUIRE(comp_clock_sync_unix(&app.clock,calendar_anchor-1000u,fixture.tick),"host clock backstep fixture");
    comp_v11_product_calendar_settings(&app,calendar_settings);
    REQUIRE(comp_v11_product_apply_settings(&app,calendar_settings,sizeof(calendar_settings)) &&
        engine->active.started_unix_s==recorded_date && fixture.mic_starts==1u,
        "in-recording sync changed original date or restarted microphone");
    REQUIRE(comp_v11_product_apply_settings(&app,calendar_settings,10u) && app.clock.calendar_valid,
        "legacy preference-only write discarded complete date");
    const uint32_t preferences_during_capture=app.preferences.generation;
    REQUIRE(!comp_v11_product_restore_defaults(&app)&&board.microphone.running&&
        app.preferences.generation==preferences_during_capture&&engine->active.started_unix_s==recorded_date,
        "restore preferences interrupted capture or changed the original");
    for(uint32_t i=1u;i<=2u;i++) {
        uint32_t blocks=engine->stats.accepted_pcm_blocks;
        key(&app,true,10u);key(&app,false,4u);step(&app,60u);
        REQUIRE(board.microphone.running&&engine->state==COMP_CONT_RUNNING&&fixture.mic_starts==1u&&
            engine->stats.accepted_pcm_blocks>blocks,"short mark paused or restarted microphone");
        REQUIRE(engine->bookmark_sequence==i&&engine->bookmark_phase==0u&&
            comp_v11_product_recording_bookmark_result(&app,app.runtime.record_token,engine->bookmark_request)==COMP_SEG_OK,
            "short press bookmark not durable");
    }
    /* Exactly one hardware second. DOWN is first polled10ms late while
     * UP is polled at its actual edge; all capture service gaps stay<=10ms. */
    fixture.key_pressed=true;
    comp_v11_wake_events_note_key_isr(&board.wake_events,COMP_V11_WAKE_KEY_FALLING,fixture.tick);
    step(&app,99u);fixture.tick+=10u;fixture.key_pressed=false;
    comp_v11_wake_events_note_key_isr(&board.wake_events,COMP_V11_WAKE_KEY_RISING,fixture.tick);
    comp_v11_product_app_poll(&app);step(&app,4u);
    REQUIRE(wait_state(&app,COMP_WBA_RECORDING_TRANSFER_READY,20000u),"one-second stop not saved");
    REQUIRE(feedback_saved_checks(&app)==0,"saved feedback checks");
    const uint32_t expected_states=(1u<<COMP_CAPTURE_PREPARING)|(1u<<COMP_CAPTURE_RECORDING)|
        (1u<<COMP_CAPTURE_SAVING)|(1u<<COMP_CAPTURE_SAVED);
    REQUIRE((feedback_observed&expected_states)==expected_states&&
        (feedback_observed&((uint32_t)COMP_CAPTURE_MARK_PENDING<<16u))&&
        (feedback_observed&((uint32_t)COMP_CAPTURE_MARK_CONFIRMED<<16u)),
        "real recorder/NOR journey missed preparing/recording/saving/saved or pending/durable mark feedback");
    feedback_watch=false;
    REQUIRE(fixture.mic_starts==1u&&!board.microphone.running&&!app.recording.last_fault&&
        engine->bookmark_sequence==2u,"long stop added a mark or repeated start");
    comp_segment_entry_t entry={0};bool found=false;
    for(uint8_t i=0u;i<COMP_SEGMENT_CAPACITY;i++)if(app.recording.catalog.slots[i]!=255u) {
        REQUIRE(comp_wba_segment_storage_entry(&app.recording.storage,&app.recording.catalog,i,&entry)==COMP_SEG_OK,
            "Capture saved metadata");found=true;
    }
    REQUIRE(found&&entry.state==COMP_SEG_UNSYNCED&&entry.started_unix_s==recorded_date,"Capture original/date not retained");
    comp_preferences_values_t custom=app.preferences.values;
    custom.locale=2u;custom.volume=75u;custom.quiet_enabled=true;custom.policy.time_zone_offset_minutes=480;
    custom.imu_screen_axes=0x99u;custom.name_length=5u;memcpy(custom.name,"Owner",5u);
    REQUIRE(comp_v11_product_save_preferences(&app,&custom)&&!comp_preferences_are_defaults(&app.preferences.values),
        "custom preferences fixture did not save");
    const uint32_t date_before_restore=comp_clock_unix(&app.clock,fixture.tick);
    const uint32_t catalog_before_restore=app.recording.catalog.generation;
    REQUIRE(comp_v11_product_restore_defaults(&app)&&comp_preferences_are_defaults(&app.preferences.values)&&
        app.preferences.values.imu_screen_axes==0x99u&&app.clock.calendar_valid&&
        comp_clock_unix(&app.clock,fixture.tick)==date_before_restore&&
        app.recording.catalog.generation==catalog_before_restore,"restore preferences touched date, calibration or recordings");
    const uint32_t default_generation=app.preferences.generation;
    REQUIRE(comp_v11_product_restore_defaults(&app)&&app.preferences.generation==default_generation,
        "repeated restore appended needless NOR writes");
    FILE *artifact=fopen(path,"wb");REQUIRE(artifact,"Capture artifact open");
    comp_segment_audio_port_t audio=comp_wba_segment_storage_audio_port(&app.recording.storage);
    uint32_t offset=0u,index=0u;
    while(offset<entry.descriptor.encoded_length) {
        uint8_t page[256],n;
        REQUIRE(comp_segment_audio_read_page(&audio,&entry,COMP_WBA_NOR_RECORDING_BASE,index++,page,&n)==COMP_SEG_OK,
            "Capture original read");
        REQUIRE(fwrite(page,1u,n,artifact)==n,"Capture artifact write");offset+=n;
    }
    REQUIRE(fclose(artifact)==0&&offset==entry.descriptor.encoded_length,"Capture original incomplete");
    init_board(&app,&board);REQUIRE(wait_state(&app,COMP_WBA_RECORDING_IDLE,20000u)&&
        app.recording.space.logical==1u,"Capture original lost on normal reboot");
    REQUIRE(comp_preferences_are_defaults(&app.preferences.values)&&app.preferences.values.imu_screen_axes==0x99u,
        "restored preferences or calibration not durable");
    puts("PASS Capture recorder-card controls: one-second start from sleep, two durable short-press marks without pause, one-second stop, original survives reboot");
    puts("PASS Capture feedback: real prepare/capture/save/mark durability; stale capacity, catalog slots, fragmented extents, cancellation and failure never invent success");
    puts("PASS Capture calendar settings: unknown/midnight/invalid echo/NOR-free sync; active date immutable across host backstep");
    puts("PASS restore preferences: refuses live capture, preserves saved original/date/calibration, no-op repeat and reboot durability");
    free(fixture.flash);return 0;
}
int main(int argc,char **argv)
{
    if(argc==3&&!strcmp(argv[2],"--idle-prime-only"))return idle_prime_handoff_journey();
    if(argc==3&&!strcmp(argv[2],"--capture-controls-only"))return capture_controls_journey(argv[1]);
    if(argc==3&&!strcmp(argv[2],"--late-button-release-only"))return late_release_button_journey();
    if(argc==3&&!strcmp(argv[2],"--idle-display-failure-only"))return idle_display_failure_journey();
    if(argc==3&&!strcmp(argv[2],"--full-stop-notice"))return full_stop_notice_journey();
    if(argc==3&&!strcmp(argv[2],"--resource-timeout-only"))return resource_timeout_journey(0u);
    if(argc==3&&!strcmp(argv[2],"--resource-uncertain-only"))return resource_timeout_journey(1u);
    if(argc==3&&!strcmp(argv[2],"--resource-pending-only"))return resource_timeout_journey(2u);
    if(argc==3&&!strcmp(argv[2],"--resource-other-mic-only"))return resource_timeout_journey(3u);
    #ifdef COMPANION_TEST_SEALED_PULL_RECOVERY
    if(argc==3&&!strcmp(argv[2],"--sealed-read-active-app"))return sealed_read_fault_active_app_journey();
    if(argc==3&&!strcmp(argv[2],"--sealed-payload-read-recovery"))return sealed_payload_read_recovery_journey();
    #endif
    if(argc==3&&!strcmp(argv[2],"--external-read-recovery"))return external_read_recovery_journey();
    if(argc==3&&!strcmp(argv[2],"--recording-level"))return recording_level_journey();
    if(argc==3&&!strcmp(argv[2],"--consume-read-recovery"))return consume_read_recovery_journey(true,false);
    if(argc==3&&!strcmp(argv[2],"--consume-read-after-stop"))return consume_read_recovery_journey(false,false);
    if(argc==3&&!strcmp(argv[2],"--consume-ack-uncertain"))return consume_read_recovery_journey(true,true);
    if(argc==3&&!strcmp(argv[2],"--salvage-to-healthy"))return salvage_to_healthy_journey();
    if(argc==3&&!strcmp(argv[2],"--explicit-idle-retry"))return explicit_idle_retry_journey();
    if(argc==3&&!strcmp(argv[2],"--damaged-tail-continuity"))return damaged_tail_continuity_journey(false);
    if(argc==3&&!strcmp(argv[2],"--damaged-tail-reboot"))return damaged_tail_continuity_journey(true);
    if(argc==3&&!strcmp(argv[2],"--runtime-profile-failure-only")) {profile_failure_test=true;return runtime_recovery_journey();}
    if(argc==3&&!strcmp(argv[2],"--runtime-normal-recovery-only")) {normal_recovery_test=true;return runtime_recovery_journey();}
    if(argc==3&&!strcmp(argv[2],"--runtime-recovery-only"))return runtime_recovery_journey();
    if(argc==3 && !strcmp(argv[2],"--power-guard-only"))return power_guard_journey(argv[1]);
    _Static_assert(offsetof(companion_opus16_rt_t,sample_rate_hz)==
        offsetof(companion_opus16_rt_t,last_encode_error)+sizeof(int16_t),
        "Opus error occupies alignment padding, no audio RAM growth");
    companion_opus16_rt_t bad_codec;int16_t bad_pcm=0;uint8_t bad_packet[402];
    REQUIRE(companion_opus16_rt_init_rate_frame(&bad_codec,16000u,20u),"error observation encoder init");
    bad_codec.frame_samples=1u; /* Real Opus refuses this unsupported duration. */
    REQUIRE(companion_opus16_rt_encode(&bad_codec,&bad_pcm,1u,bad_packet,sizeof(bad_packet),false)==0u&&
        bad_codec.last_encode_error<0&&bad_codec.frames_encoded==0u&&bad_codec.bytes_out==0u,
        "actual codec failure lost or counted as saved audio");
    companion_opus16_rt_destroy(&bad_codec);
    comp_v11_hal_t board;comp_v11_product_app_t app;
    REQUIRE(argc==2,"artifact path required");
    memset(&fixture,0,sizeof(fixture));fixture.flash=malloc(FLASH_BYTES);
    REQUIRE(fixture.flash,"model NOR allocation");memset(fixture.flash,255u,FLASH_BYTES);layout_root();
    init_board(&app,&board);REQUIRE(!app.recording_ready,"recorder advertised before boot recovery/lease");
    REQUIRE(wait_state(&app,COMP_WBA_RECORDING_IDLE,20000u),"cooperative product boot");
    REQUIRE(app.recording_identity.loaded&&app.recording_identity.ready,"CSI1 namespace bootstrap");
    uint64_t epoch=app.recording_identity.record.format_epoch;
    /* Existing saved timer is obsolete for the WBA segmented product. */
    app.runtime.menu.browser.recording_limit_minutes=30u;
    companion_recording_capacity_v1_t local_capacity;
    REQUIRE(comp_v11_product_recording_capacity(&app,&local_capacity) &&
        local_capacity.local_limit_seconds==0u,"capacity must report actual unlimited local timer");
    comp_power_policy_init(&board.power);comp_power_policy_set_blocker(&board.power,COMP_POWER_BLOCKER_BOOT,false);
    comp_power_policy_set_button_wake_ready(&board.power,true);
    key(&app,true,COMPANION_WBA_SCREEN_ENABLED?75u:110u);key(&app,false,4u);
    REQUIRE(wait_state(&app,COMP_WBA_RECORDING_CAPTURING,20000u),"physical long-press/cue/MIC start ports");
    REQUIRE(app.runtime.record_limit_seconds==0u,"legacy timer stopped product local recording");
    REQUIRE(fixture.mic_starts==1u&&fixture.first_mic_start_after_speaker_blocks>0u&&
        !fixture.mic_before_durable_identity&&!fixture.identity_writes_during_capture,"cue or durable identity order");
    REQUIRE(!comp_v11_product_update_idle_policy(&app),"capture allowed idle");
    step(&app,140u);key(&app,true,COMPANION_WBA_SCREEN_ENABLED?75u:110u);key(&app,false,4u);
    REQUIRE(wait_state(&app,COMP_WBA_RECORDING_TRANSFER_READY,20000u)&&!board.microphone.running,
        "same app STOP/seal/unused reservation cancel");
    REQUIRE(app.runtime.recording==DENZIC_AUDIO_RECORDING_STATE_TRANSFER_READY&&!app.runtime.capture_active&&
        fixture.speaker_submits_while_recording==0u,"runtime saved state/cue pollution");
    REQUIRE(settled_space(&app)&&app.recording.space.logical==1u&&app.recording.space.used==1u,
        "logical catalog and physical segment capacity");
    comp_segment_entry_t entry={0};bool found=false;
    for(uint8_t i=0u;i<64u&&!found;i++)if(app.recording.catalog.slots[i]!=255u) {
        REQUIRE(comp_wba_segment_storage_entry(&app.recording.storage,&app.recording.catalog,i,&entry)==COMP_SEG_OK,
            "sealed physical metadata");found=true;
    }
    REQUIRE(found&&entry.state==COMP_SEG_UNSYNCED&&entry.descriptor.session_id==app.recording_session_id&&
        entry.descriptor.format_epoch==epoch,"saved segment/session identity");
    FILE *artifact=fopen(argv[1],"wb");REQUIRE(artifact,"artifact open");
    comp_segment_audio_port_t audio=comp_wba_segment_storage_audio_port(&app.recording.storage);
    companion_sha256_t hash;uint8_t digest[32];companion_sha256_init(&hash);
    uint32_t offset=0u,index=0u;
    while(offset<entry.descriptor.encoded_length) {
        uint8_t page[256],n;
        REQUIRE(comp_segment_audio_read_page(&audio,&entry,COMP_WBA_NOR_RECORDING_BASE,index++,page,&n)==COMP_SEG_OK,
            "CSP2 raw page read");
        REQUIRE(fwrite(page,1u,n,artifact)==n,"raw COP1 write");
        companion_sha256_update(&hash,page,n);offset+=n;
    }
    REQUIRE(fclose(artifact)==0,"artifact close");companion_sha256_final(&hash,digest);
    REQUIRE(offset==entry.descriptor.encoded_length&&!memcmp(digest,entry.descriptor.sha256,32u),"raw SHA matches sealed descriptor");
    uint64_t next_session=app.recording_identity.record.next_session_id;
    init_board(&app,&board);REQUIRE(wait_state(&app,COMP_WBA_RECORDING_IDLE,20000u),"normal app reboot");
    REQUIRE(app.recording_identity.record.format_epoch==epoch&&app.recording_identity.record.next_session_id==next_session&&
        app.recording.space.logical==1u,"reboot namespace/segment retention");
    /* A normal read longer than a sampling interval still has to yield. */
    key(&app,true,COMPANION_WBA_SCREEN_ENABLED?75u:110u);key(&app,false,4u);
    REQUIRE(wait_state(&app,COMP_WBA_RECORDING_CAPTURING,20000u),"resource capture start");
    fixture.resource_read_ms=2u;fixture.resource_reads=0u;fixture.microphone_poll_ms=6u;
    fixture.tick+=STEP_MS;uint32_t before=app.recording.capture.engine.stats.accepted_pcm_blocks;
    uint8_t resource[5000];
    REQUIRE(fixture.resources.read(fixture.resources.context,0u,resource,sizeof(resource)),"bounded authored resource read");
    REQUIRE(fixture.resource_reads==20u&&board.microphone.running&&app.capture_deadline_faults==0u&&
        app.recording.capture.engine.stats.accepted_pcm_blocks>=before+3u&&app.max_capture_foreground_ms<=10u&&
        fixture.pending_pcm_before_resource,"resource progress starved or stacked conversion/codec");
    fixture.resource_read_ms=11u;
    REQUIRE(!fixture.resources.read(fixture.resources.context,0u,resource,256u)&&app.capture_deadline_faults==1u&&
        !board.microphone.running&&app.recording.last_fault==COMP_WBA_RECORDING_FAULT_DEADLINE&&
        app.runtime.recording==DENZIC_AUDIO_RECORDING_STATE_ERROR_RECOVERY,"deadline fault was hidden or reported saved");
    REQUIRE(!fixture.mic_before_durable_identity&&!fixture.identity_writes_during_capture,"namespace mutated in capture");
    printf("PASS_WBA_PRODUCT_RECORDING_SEGMENTED_HOST_ONLY codec=3 bytes=%lu PCM/cue/STOP/reboot/resource-yield/deadline\n",
        (unsigned long)entry.descriptor.encoded_length);
    free(fixture.flash);return 0;
}


bool comp_v11_hal_microphone_audio_profile(const comp_v11_hal_t *b,uint8_t profile,comp_rec_audio_profile_t *out)
{(void)b;(void)profile;(void)out;return false;}
