#include "product_app.h"
#include "companion_recording_wire.h"
#include "wba_storage_layout.h"
#include "wba_shared_pool.h"
#include "wba_flash_migration.h"

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
        if (active_app == NULL || !comp_rec_identity_find(&active_app->recording_identity,
                active_app->recorder.entry.recording_id, &session) ||
                !session || session != active_app->recording_session_id)
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
    int16_t pcm[COMP_WBA_RECORDING_PCM_FRAME_SAMPLES];
    if (board == NULL) return;
    comp_v11_hal_speaker_poll(board);
    if (!board->microphone.running || board->pcm_sink == NULL) return;
    for (uint32_t i = 0u; i < COMP_WBA_RECORDING_PCM_FRAME_SAMPLES; ++i) {
        uint32_t phase = (fixture.pcm_sequence * 160u + i) % 160u;
        pcm[i] = phase < 80u ? (int16_t)(phase * 180u) :
                               (int16_t)((159u - phase) * 180u);
    }
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
            fixture.pending_pcm_before_resource=active_app->recorder.ring_count!=0u;
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

static void step(comp_v11_product_app_t *app, uint32_t count)
{
    for (uint32_t i = 0u; i < count; ++i) {
        fixture.tick += STEP_MS;
        comp_v11_product_app_poll(app);
    }
}

static bool wait_state(comp_v11_product_app_t *app,
                       comp_wba_recording_service_state_t wanted,
                       uint32_t max_steps)
{
    for (uint32_t i = 0u; i < max_steps; ++i) {
        if (app->recorder.state == wanted) return true;
        step(app, 1u);
    }
    return app->recorder.state == wanted;
}

static void key_release(comp_v11_product_app_t *app)
{
    fixture.key_pressed = false;
    step(app, 4u);
}

static void key_long_press(comp_v11_product_app_t *app)
{
    fixture.key_pressed = true;
    step(app, 75u);
}

static uint32_t count_entries(const comp_recording_journal_t *journal,
                              uint8_t state)
{
    uint32_t count = 0u;
    for (uint32_t i = 0u; i < COMP_RECORDING_JOURNAL_MAX_ENTRIES; ++i) {
        const comp_recording_journal_entry_t *entry = &journal->catalog.entries[i];
        if (entry->recording_id != 0u && entry->sync_state == state) count++;
    }
    return count;
}

int main(int argc, char **argv)
{
    comp_v11_hal_t board;
    comp_v11_product_app_t app;
    comp_speaker_config_t speaker_config;
    const comp_recording_journal_entry_t *entry;
    comp_wba_recording_service_stats_t stats;
    comp_recording_journal_catalog_t full_catalog;
    FILE *artifact;

    REQUIRE(argc == 2, "output path required");
    memset(&fixture, 0, sizeof(fixture));
    fixture.flash = malloc(FLASH_BYTES);
    REQUIRE(fixture.flash != NULL, "flash allocation");
    memset(fixture.flash, 0xFF, FLASH_BYTES);
    memset(&board, 0, sizeof(board));
    active_board = &board;
    board.microphone.initialized = true;
    speaker_config = (comp_speaker_config_t){
        amplifier, submit_i2s, playback_active, &board
    };
    comp_speaker_init(&board.speaker, &speaker_config);
    board.speaker_ready = true;

    comp_v11_product_app_init(&app, &board, NULL);
    active_app = &app;
    REQUIRE(app.recording_ready, "product recorder did not mount");
    {
        companion_recording_capacity_v1_t capacity;
        uint8_t status[84]={1u};char name[1024];
        _Static_assert(sizeof(companion_recording_capacity_v1_t)==48u,"capacity wire size");
        REQUIRE(comp_v11_product_recording_capacity(&app,&capacity),"initial capacity");
        uint32_t board_id=0x57424155u;memcpy(status+12,&board_id,4u);
        memcpy(status+36,&capacity,sizeof(capacity));
        REQUIRE(snprintf(name,sizeof(name),"%s.capacity.bin",argv[1])>0,"capacity fixture path");
        FILE *wire=fopen(name,"wb");REQUIRE(wire!=NULL,"capacity fixture open");
        REQUIRE(fwrite(status,1u,sizeof(status),wire)==sizeof(status) && fclose(wire)==0,
                "capacity fixture write");
    }
    comp_power_policy_init(&board.power);
    comp_power_policy_set_blocker(&board.power,COMP_POWER_BLOCKER_BOOT,false);
    comp_power_policy_set_button_wake_ready(&board.power,true);
    app.runtime.surface=COMP_SCREEN_SURFACE_LOW_POWER;
    app.runtime.visible_surface=COMP_SCREEN_SURFACE_HOME;
    REQUIRE(!comp_v11_product_update_idle_policy(&app),"uncommitted sleep screen allowed idle");
    app.runtime.visible_surface=COMP_SCREEN_SURFACE_LOW_POWER;
    app.runtime.visible_revision=app.runtime.revision;
    REQUIRE(comp_v11_product_update_idle_policy(&app),"button-only wake cannot idle without touch");
    const comp_power_blocker_t external[]={COMP_POWER_BLOCKER_RECORDING_TRANSFER,
        COMP_POWER_BLOCKER_STORAGE,COMP_POWER_BLOCKER_UPDATE,COMP_POWER_BLOCKER_BOND_NVM};
    for (uint32_t i=0;i<sizeof(external)/sizeof(external[0]);++i) {
        comp_power_policy_set_blocker(&board.power,external[i],true);
        REQUIRE(!comp_v11_product_update_idle_policy(&app),"product discarded module sleep blocker");
        comp_power_policy_set_blocker(&board.power,external[i],false);
    }
    app.runtime.prepare_pending=true;
    REQUIRE(!comp_v11_product_update_idle_policy(&app),"storage preparation allowed idle");
    app.runtime.prepare_pending=false;
    app.recorder.state=COMP_WBA_RECORDING_STOPPING;
    REQUIRE(!comp_v11_product_update_idle_policy(&app),"finalizing audio allowed idle");
    app.recorder.state=COMP_WBA_RECORDING_IDLE;
    board.power_monitor.phase=COMP_WBA_BAT_CLEANUP;
    REQUIRE(!comp_v11_product_update_idle_policy(&app),"unclosed ADC gate allowed idle");
    board.power_monitor.phase=COMP_WBA_BAT_IDLE;
    /* A sleeping press is wholly consumed even after the runtime wakes. */
    key_long_press(&app); step(&app,75u);
    REQUIRE(app.runtime.surface==COMP_SCREEN_SURFACE_HOME && fixture.mic_starts==0u &&
        !app.runtime.prepare_pending && !app.runtime.start_pending,"sleep press accidentally requested recording");
    key_release(&app);
    board.power_monitor.sampling_enabled=true;
    board.power_monitor.value=(comp_wba_power_snapshot_t){.millivolts=3800,.percent=55,
        .voltage_valid=true,.percent_valid=true};
    board.power_monitor.voltage_ms=fixture.tick;
    step(&app,1u);
    REQUIRE(app.runtime.menu.browser.battery_percent==55u &&
        (app.runtime.status_packed>>24)==55u && (app.runtime.status_packed&(1u<<17)),
        "qualified battery did not reach status/menu");
    board.power_monitor.sampling_enabled=false;
    step(&app,1u);
    REQUIRE(app.runtime.menu.browser.battery_percent==255u && !(app.runtime.status_packed&(1u<<17)),
        "unavailable battery retained fabricated percentage");
    uint8_t echoed_settings[13];
    comp_clock_t saved_clock=app.clock;
    app.clock.valid=false;
    comp_v11_product_settings(&app,echoed_settings);
    REQUIRE(echoed_settings[10]==255u && echoed_settings[11]==255u && echoed_settings[12]==255u,
            "unknown clock fabricated valid UTC readback");
    app.clock=saved_clock;
    uint8_t settings[13]={1,1,0,0,0x59,1,0,0,0,1,10,30,45};
    REQUIRE(comp_v11_product_apply_settings(&app,settings,sizeof(settings)),"Type settings and UTC clock");
    REQUIRE(app.preferences.values.policy.time_zone_offset_minutes==345 && app.clock.valid,
            "quarter-hour timezone retained");
    uint32_t saved_generation=app.preferences.generation;
    comp_v11_product_settings(&app,echoed_settings);
    REQUIRE(memcmp(echoed_settings,settings,sizeof(settings))==0,
            "accepted clock extension was omitted from settings readback");
    saved_clock=app.clock;
    fixture.tick+=2500u;
    comp_v11_product_settings(&app,echoed_settings);
    REQUIRE(echoed_settings[10]==10u && echoed_settings[11]==30u && echoed_settings[12]==47u &&
            app.preferences.generation==saved_generation && memcmp(&saved_clock,&app.clock,sizeof(saved_clock))==0,
            "clock readback must sample elapsed UTC without mutation or NOR writes");
    REQUIRE(comp_v11_product_apply_settings(&app,settings,10u) && app.clock.valid,
            "legacy 10-byte settings invalidated a synchronized clock");
    settings[10]=24;
    REQUIRE(!comp_v11_product_apply_settings(&app,settings,sizeof(settings)) &&
            app.preferences.generation==saved_generation,"bad clock changed persistent preferences");
    settings[10]=10;
    settings[2]=1;
    REQUIRE(comp_v11_product_apply_settings(&app,settings,sizeof(settings)) && app.runtime.quiet,
            "Type manual quiet is applied and persisted");
    comp_v11_product_settings(&app,echoed_settings);
    REQUIRE(echoed_settings[2]==1u,"settings echoes manual preference rather than transient quiet hours");
    settings[1]=2u;
    REQUIRE(comp_v11_product_apply_settings(&app,settings,sizeof(settings)) &&
        app.runtime.menu.language==COMP_SCREEN_MENU_LANGUAGE_ZH_TW,"Traditional Chinese applies through device settings");
    comp_v11_product_settings(&app,echoed_settings);
    REQUIRE(echoed_settings[1]==2u,"Traditional Chinese round-trips through settings readback");
    settings[1]=3u;
    REQUIRE(!comp_v11_product_apply_settings(&app,settings,sizeof(settings)) &&
        app.runtime.menu.language==COMP_SCREEN_MENU_LANGUAGE_ZH_TW,"unknown locale preserves current settings");
    settings[1]=1u;
    settings[2]=0;
    REQUIRE(comp_v11_product_apply_settings(&app,settings,sizeof(settings)) && !app.runtime.quiet,
            "Type manual quiet can be disabled");
    saved_generation=app.preferences.generation;
    REQUIRE(app.runtime.recording == DENZIC_AUDIO_RECORDING_STATE_IDLE,
            "initial runtime recording state");
    /* A production-supported value; it also exercises the large pre-erase
     * preparation phase before the cue. */
    app.runtime.menu.browser.recording_limit_minutes = 15u;

    key_long_press(&app);
    REQUIRE(app.runtime.prepare_pending || app.runtime.start_pending ||
            app.runtime.capture_active, "button did not request recording");
    REQUIRE(wait_state(&app, COMP_WBA_RECORDING_CAPTURING, 900u),
            "prepare/cue/start did not reach capture");
    REQUIRE(app.runtime.capture_active && board.microphone.running,
            "runtime/backend capture state diverged at start");
    const uint64_t first_session = app.recording_session_id;
    REQUIRE(first_session != 0u && !fixture.mic_before_durable_identity,
            "microphone enabled before both session snapshots were durable");
    settings[12]=46;
    REQUIRE(comp_v11_product_apply_settings(&app,settings,sizeof(settings)) &&
            app.preferences.generation==saved_generation && board.microphone.running,
            "clock-only sync interrupted recording or wrote NOR");
    comp_v11_product_settings(&app,echoed_settings);
    REQUIRE(echoed_settings[12]==46u && board.microphone.running && app.preferences.generation==saved_generation,
            "capture clock readback interrupted microphone or wrote preferences");
    REQUIRE(fixture.first_mic_start_after_speaker_blocks >= 30u,
            "microphone started before recording-start cue completed");
    REQUIRE(!fixture.amplifier_enabled && !comp_speaker_active(&board.speaker),
            "speaker remained active when microphone started");
    key_release(&app);
    step(&app, 40u);

    key_long_press(&app);
    REQUIRE(wait_state(&app, COMP_WBA_RECORDING_TRANSFER_READY, 256u),
            "first stop did not finalize");
    REQUIRE(!app.runtime.capture_active && !board.microphone.running,
            "first stop left capture active");
    REQUIRE(app.runtime.recording == DENZIC_AUDIO_RECORDING_STATE_TRANSFER_READY,
            "first finalize report did not reach runtime");
    REQUIRE(count_entries(&app.recording_journal,
                          COMP_RECORDING_JOURNAL_UNSYNCED) == 1u,
            "first recording is not unsynced");
    key_release(&app);

    key_long_press(&app);
    REQUIRE(wait_state(&app, COMP_WBA_RECORDING_CAPTURING, 900u),
            "fault scenario did not start");
    REQUIRE(app.runtime.capture_active, "fault scenario runtime not active");
    REQUIRE(app.recording_session_id > first_session, "new capture reused a session");
    step(&app, 8u);
    board.microphone.error_irqs++;
    step(&app, 1u);
    REQUIRE(app.recorder.state == COMP_WBA_RECORDING_FAULT,
            "microphone HAL counter change did not fault recorder");
    REQUIRE(app.recorder.last_fault_reason ==
                COMP_WBA_RECORDING_FAULT_PLATFORM_CAPTURE,
            "wrong external capture fault reason");
    REQUIRE(!board.microphone.running && !app.runtime.capture_active &&
            app.runtime.recording == DENZIC_AUDIO_RECORDING_STATE_ERROR_RECOVERY,
            "fault report/microphone/runtime state diverged");
    REQUIRE(count_entries(&app.recording_journal,
                          COMP_RECORDING_JOURNAL_WRITING) == 1u,
            "faulted partial was not retained explicitly");
    key_release(&app);

    key_long_press(&app);
    REQUIRE(wait_state(&app, COMP_WBA_RECORDING_CAPTURING, 900u),
            "retry did not recover and start");
    REQUIRE(app.runtime.capture_active && app.recorder.token == app.runtime.record_token,
            "retry token/report lifecycle diverged");
    key_release(&app);
    step(&app, 40u);
    key_long_press(&app);
    REQUIRE(wait_state(&app, COMP_WBA_RECORDING_TRANSFER_READY, 256u),
            "retry stop did not finalize");
    REQUIRE(app.runtime.recording == DENZIC_AUDIO_RECORDING_STATE_TRANSFER_READY &&
            !app.runtime.capture_active, "retry final report diverged");

    entry = comp_wba_recording_service_entry(&app.recorder);
    REQUIRE(entry != NULL && entry->codec == COMP_WBA_RECORDING_CODEC_OPUS16 &&
            entry->sync_state == COMP_RECORDING_JOURNAL_UNSYNCED &&
            entry->duration_ms >= 400u && entry->total_length > 12u,
            "retry recording metadata");
    REQUIRE(memcmp(fixture.flash + 0x00200000u + entry->payload_offset,
                   "COP1", 4u) == 0, "retry payload is not COP1");
    REQUIRE(count_entries(&app.recording_journal,
                          COMP_RECORDING_JOURNAL_UNSYNCED) == 2u &&
            count_entries(&app.recording_journal,
                          COMP_RECORDING_JOURNAL_WRITING) == 1u,
            "completed/partial journal lifecycle");
    REQUIRE(fixture.speaker_submits_while_recording == 0u,
            "speaker submitted audio while microphone active");
    REQUIRE(app.capture_deadline_faults == 0u,
            "host foreground path raised a false deadline fault");

    comp_wba_recording_service_get_stats(&app.recorder, &stats);
    REQUIRE(stats.starts == 3u && stats.finalized == 2u &&
            stats.external_capture_faults == 1u && stats.failures == 1u,
            "recording aggregate statistics");
    REQUIRE(stats.dropped_pcm_frames == 0u && stats.budget_violations == 0u,
            "unexpected PCM drop or budget violation");

    /* One additional reservation leaves bytes for a short recording, but
     * not the entire local 30-minute request. Never silently shorten it. */
    {
        companion_recording_capacity_v1_t capacity;
        comp_recording_journal_space_t space;
        comp_recording_journal_entry_t occupied;
        REQUIRE(comp_recording_journal_space(&app.recording_journal,&space),"capacity snapshot");
        REQUIRE(space.largest_free_extent>1024u*1024u,"capacity fixture needs free extent");
        REQUIRE(comp_recording_journal_begin(&app.recording_journal,
                space.largest_free_extent-1024u*1024u,0u,fixture.tick,3u,1u,&occupied)==
                COMP_RECORDING_JOURNAL_OK,"leave one MiB for short requests");
        full_catalog=app.recording_journal.catalog;
        app.runtime.menu.browser.recording_limit_minutes=30u;
        REQUIRE(comp_v11_product_recording_capacity(&app,&capacity) &&
                capacity.tag==COMPANION_RECORDING_CAPACITY_TAG &&
                capacity.data_bytes==8u*1024u*1024u-8192u &&
                capacity.largest_free_extent==1024u*1024u &&
                capacity.protected_bytes>0u,"product reports V1 geometry and live reservations");
        uint32_t speaker_before=fixture.speaker_completions;
        REQUIRE(comp_runtime_record(&app.runtime,true,fixture.tick)==COMP_RUNTIME_UNAVAILABLE &&
                !app.runtime.prepare_pending && !app.runtime.capture_active &&
                !board.microphone.running && fixture.speaker_completions==speaker_before &&
                memcmp(&full_catalog,&app.recording_journal.catalog,sizeof(full_catalog))==0,
                "insufficient fixed duration changed catalog, microphone or cue");
    }
    /* Fill the remaining directory slots without consuming the large free
     * byte extent left by trimming. Product prepare and the journal must both
     * reject this state while every completed entry is still UNSYNCED. */
    while (comp_recording_journal_count(&app.recording_journal) <
           COMP_RECORDING_JOURNAL_MAX_ENTRIES) {
        comp_recording_journal_entry_t added;
        uint8_t digest[COMP_RECORDING_JOURNAL_SHA256_BYTES] = {0};
        REQUIRE(comp_recording_journal_begin(
                    &app.recording_journal, 4096u, 0u, fixture.tick, 3u, 1u,
                    &added) == COMP_RECORDING_JOURNAL_OK,
                "fixture directory fill begin");
        digest[0] = (uint8_t)added.recording_id;
        REQUIRE(comp_recording_journal_finalize(
                    &app.recording_journal, added.recording_id, 1u, 20u,
                    added.recording_id, digest, 3u) ==
                    COMP_RECORDING_JOURNAL_OK,
                "fixture directory fill finalize");
    }
    full_catalog = app.recording_journal.catalog;
    /* Catalog mutations can come from transfer/erase work without a recorder
     * state callback. The next foreground poll must refresh menu values, and
     * the incomplete faulted recording must not be counted as transferable. */
    uint32_t catalog_bytes = 0u;
    uint16_t catalog_count = 0u;
    for (uint32_t i = 0u; i < COMP_RECORDING_JOURNAL_MAX_ENTRIES; ++i) {
        const comp_recording_journal_entry_t *item = &full_catalog.entries[i];
        if (item->recording_id != 0u &&
            (item->sync_state == COMP_RECORDING_JOURNAL_UNSYNCED ||
             item->sync_state == COMP_RECORDING_JOURNAL_ACKED)) {
            catalog_count++;
            catalog_bytes += item->total_length;
        }
    }
    REQUIRE(app.runtime.menu.browser.recording_count != catalog_count,
            "fixture did not exercise a catalog change outside recorder reports");
    step(&app, 1u);
    REQUIRE(app.runtime.menu.browser.recording_count == catalog_count &&
            app.runtime.menu.browser.recording_storage_kb ==
                (catalog_bytes + 1023u) / 1024u,
            "menu did not refresh completed catalog count and rounded-up KiB");
    key_release(&app);
    key_long_press(&app);
    REQUIRE(app.recorder.state == COMP_WBA_RECORDING_TRANSFER_READY &&
            !app.runtime.capture_active && !board.microphone.running,
            "full directory unexpectedly started recording");
    REQUIRE(app.runtime.last_result == COMP_RUNTIME_UNAVAILABLE,
            "full directory refusal was not visible to runtime");
    REQUIRE(app.recorder.last_fault_reason ==
                COMP_WBA_RECORDING_FAULT_STORAGE_FULL,
            "full directory refusal was not identified as protected storage");
    REQUIRE(memcmp(&full_catalog, &app.recording_journal.catalog,
                   sizeof(full_catalog)) == 0,
            "full directory refusal evicted or mutated stored recordings");

    artifact = fopen(argv[1], "wb");
    REQUIRE(artifact != NULL, "artifact open");
    REQUIRE(fwrite(fixture.flash + 0x00200000u + entry->payload_offset, 1u,
                   entry->total_length, artifact) == entry->total_length,
            "artifact write");
    REQUIRE(fclose(artifact) == 0, "artifact close");
    REQUIRE(!fixture.mic_before_durable_identity && fixture.identity_writes_during_capture == 0u,
            "namespace writes overlapped capture or lacked readback");
    {
        uint8_t saved_namespace[COMP_REC_IDENTITY_BYTES];
        const uint64_t epoch = app.recording_identity.record.format_epoch;
        const uint64_t next_session = app.recording_identity.record.next_session_id;
        memcpy(saved_namespace, fixture.flash + COMP_WBA_NOR_RECORDING_IDENTITY_BASE,
               sizeof(saved_namespace));
        comp_v11_product_app_t rebooted;
        comp_v11_product_app_init(&rebooted, &board, NULL);
        REQUIRE(rebooted.recording_identity.loaded && rebooted.recording_identity.ready &&
                rebooted.recording_identity.record.format_epoch == epoch &&
                rebooted.recording_identity.record.next_session_id == next_session &&
                memcmp(saved_namespace, fixture.flash + COMP_WBA_NOR_RECORDING_IDENTITY_BASE,
                       sizeof(saved_namespace)) == 0,
                "reboot reset or rewrote the durable namespace");
    }

    printf("PASS_WBA_PRODUCT_RECORDING_INTEGRATION_HOST_ONLY "
           "codec=3 bytes=%lu duration_ms=%lu starts=%lu finalized=%lu "
           "faults=%lu speaker_blocks=%lu pollution_blocks=%lu\n",
           (unsigned long)entry->total_length,
           (unsigned long)entry->duration_ms,
           (unsigned long)stats.starts,
           (unsigned long)stats.finalized,
           (unsigned long)stats.external_capture_faults,
           (unsigned long)fixture.speaker_completions,
           (unsigned long)fixture.speaker_submits_while_recording);
    /* A long authored resource read must continue to drain PCM in bounded
     * foreground slices. An indivisible read over the deadline still fails. */
    memset(fixture.flash,255,FLASH_BYTES);
    comp_v11_product_app_init(&app,&board,NULL);
    step(&app,2u);
    app.runtime.record_limit_seconds=5u;
    REQUIRE(app.runtime.config.recording_prepare(&app,201u),"resource capture prepare");
    REQUIRE(wait_state(&app,COMP_WBA_RECORDING_READY,16u),"resource capture ready");
    REQUIRE(app.runtime.config.recording_control(&app,true,201u),"resource capture start");
    fixture.resource_read_ms=2u;fixture.resource_reads=0u;fixture.microphone_poll_ms=6u;
    fixture.tick+=STEP_MS;
    uint32_t before_frames=app.recorder.stats.pcm_frames;
    uint8_t resource_bytes[5000];
    REQUIRE(fixture.resources.read(fixture.resources.context,0u,resource_bytes,sizeof(resource_bytes)),
            "bounded resource read failed");
    REQUIRE(fixture.resource_reads==20u && app.recorder.microphone_active &&
            app.capture_deadline_faults==0u && app.recorder.stats.pcm_frames>=before_frames+3u &&
            app.max_capture_foreground_ms<=10u && fixture.pending_pcm_before_resource,
            "long resource read starved capture or combined cold conversion and codec");
    fixture.resource_read_ms=11u;
    REQUIRE(!fixture.resources.read(fixture.resources.context,0u,resource_bytes,256u) &&
            app.capture_deadline_faults==1u && !board.microphone.running &&
            app.recorder.last_fault_reason==COMP_WBA_RECORDING_FAULT_DEADLINE,
            "unbounded resource read escaped the capture deadline");
    fixture.resource_read_ms=0u;fixture.microphone_poll_ms=0u;
    printf("PASS_WBA_RESOURCE_AUDIO_PROGRESS_HOST_ONLY bounded_resource_read=1 cold_conversion_defers_codec=1 late_read_rejected=1\n");
    /* A previous prehardware 14 MiB layout must remain untouched. */
    memset(fixture.flash,255,FLASH_BYTES);memcpy(fixture.flash+0xFFE000u,"CRJ1",4);
    fixture.flash[0xE00000u]=0x5Au;
    comp_v11_product_app_init(&app,&board,NULL);
    REQUIRE(!app.storage_layout_ready && !app.recording_ready && !app.settings_ready &&
            fixture.flash[0xE00000u]==0x5Au,"legacy geometry was reformatted");
    memset(fixture.flash,255,FLASH_BYTES);memcpy(fixture.flash+0xFFF000u,"CRJ2",4);
    fixture.flash[0xE00000u]=0x6Bu;
    comp_v11_product_app_init(&app,&board,NULL);
    REQUIRE(!app.storage_layout_ready && !app.recording_ready && !app.settings_ready &&
            fixture.flash[0xE00000u]==0x6Bu,"legacy CRJ2 geometry was reformatted");
    /* Unknown namespace is rejected before current journal/preferences can write. */
    memset(fixture.flash,255,FLASH_BYTES);
    fixture.flash[COMP_WBA_NOR_RECORDING_IDENTITY_BASE]=0x5Au;
    uint32_t flash_crc=comp_rec_crc(fixture.flash,FLASH_BYTES);
    comp_v11_product_app_init(&app,&board,NULL);
    REQUIRE(!app.storage_layout_ready && !app.recording_ready && !app.settings_ready &&
            comp_rec_crc(fixture.flash,FLASH_BYTES)==flash_crc,
            "unknown namespace initialization changed retained media");
    /* Entropy and namespace I/O failures refuse recording before journal allocation. */
    memset(fixture.flash,255,FLASH_BYTES);
    comp_v11_product_app_init(&app,&board,NULL);
    REQUIRE(app.recording_ready && !app.recording_identity.loaded,"fresh namespace mount");
    const uint32_t starts_before=fixture.mic_starts;
    flash_crc=comp_rec_crc(fixture.flash,FLASH_BYTES);
    fixture.rng_unavailable=true;
    step(&app,2u);
    REQUIRE(!app.runtime.config.recording_prepare(&app,101u) && !board.microphone.running &&
            fixture.mic_starts==starts_before && comp_rec_crc(fixture.flash,FLASH_BYTES)==flash_crc,
            "missing hardware entropy fabricated epoch or touched journal");
    fixture.rng_unavailable=false;step(&app,2u);
    fixture.fail_identity_program=true;
    REQUIRE(!app.runtime.config.recording_prepare(&app,102u) && !board.microphone.running &&
            fixture.mic_starts==starts_before && !app.recording_identity.ready &&
            comp_rec_crc(fixture.flash,FLASH_BYTES)==flash_crc,
            "namespace write failure opened microphone or allocated payload");
    fixture.fail_identity_program=false;
    REQUIRE(app.runtime.config.recording_prepare(&app,103u) && app.recording_session_id==1u &&
            app.recording_identity.loaded && !board.microphone.running,
            "explicit remount did not recover failed blank-media reservation");
    /* Missing roots cannot turn retained audio into apparently empty media. */
    memset(fixture.flash,255,FLASH_BYTES);memcpy(fixture.flash+COMP_WBA_V2_LAYOUT_A,"CFL2",4u);
    flash_crc=comp_rec_crc(fixture.flash,FLASH_BYTES);
    comp_v11_product_app_init(&app,&board,NULL);
    REQUIRE(!app.storage_layout_ready && !app.recording_ready && !app.settings_ready &&
            comp_rec_crc(fixture.flash,FLASH_BYTES)==flash_crc,
            "V1 initialization wrote into an announced V2 layout");
    memset(fixture.flash,255,FLASH_BYTES);memcpy(fixture.flash+COMP_WBA_MIGRATION_ROOT_B,"CLM2",4u);
    flash_crc=comp_rec_crc(fixture.flash,FLASH_BYTES);comp_v11_product_app_init(&app,&board,NULL);
    REQUIRE(!app.storage_layout_ready && !app.recording_ready && !app.settings_ready &&
            comp_rec_crc(fixture.flash,FLASH_BYTES)==flash_crc,
            "prepared migration allowed a V1 writer before front layout publication");
    memset(fixture.flash,255,FLASH_BYTES);fixture.flash[0x200000u]=0xCAu;
    comp_v11_product_app_init(&app,&board,NULL);
    REQUIRE(!app.recording_ready && !app.settings_ready && fixture.flash[0x200000u]==0xCAu,
            "lost catalogs caused silent payload format");
    free(fixture.flash);
    printf("PASS_WBA_SESSION_IDENTITY_PRODUCT_GATES_HOST_ONLY dual_copy_before_mic=1 "
           "reboot_persist=1 no_namespace_write_during_capture=1 entropy_fail_closed=1 "
           "io_fail_closed=1 unknown_media_read_only=1 legacy_crj2_read_only=1\n");
    (void)active_board;
    return 0;
}

bool comp_v11_hal_microphone_audio_profile(const comp_v11_hal_t *b,uint8_t profile,comp_rec_audio_profile_t *out)
{(void)b;(void)profile;(void)out;return false;}
