/* Behavioral replay only. No MCU, panel, radio or physical timing is emulated. */
#include "screen_scheduler_stm32wba.h"
#include "screen_assets_stm32wba.h"
#include "screen_composition.h"
#include "overlay_commit_scheduler.h"
#include "emote_asset_pack.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define CHECK(condition) do { if (!(condition)) { \
    fprintf(stderr, "FAIL line %d: %s\n", __LINE__, #condition); return false; \
} } while (0)
#define MASK(tick) COMPANION_WBA_SCREEN_TICK_MASK(COMPANION_WBA_SCREEN_TICK_##tick)

typedef struct {
    uint32_t now;
    uint32_t delay;
    unsigned starts;
    unsigned stops;
    unsigned wakes;
} fake_clock_t;

static void wake(void *context) { ((fake_clock_t *)context)->wakes++; }
static void start(void *context, uint32_t delay)
{
    fake_clock_t *clock = context;
    clock->starts++;
    clock->delay = delay;
}
static void stop(void *context) { ((fake_clock_t *)context)->stops++; }
static uint32_t now(void *context) { return ((fake_clock_t *)context)->now; }
static void init_scheduler(companion_epaper_stm32wba_scheduler_t *scheduler,
                            fake_clock_t *clock)
{
    const companion_epaper_stm32wba_scheduler_config_t config = {
        .schedule_display_task = wake, .start_expression_tick_timer = start,
        .stop_expression_tick_timer = stop, .now_ms = now, .context = clock,
    };
    companion_epaper_stm32wba_scheduler_init(scheduler, &config);
}

static bool test_deadlines(void)
{
    fake_clock_t clock = {0};
    companion_epaper_stm32wba_scheduler_t scheduler;
    unsigned starts;
    init_scheduler(&scheduler, &clock);
    CHECK(companion_epaper_stm32wba_schedule_tick(
        &scheduler, COMPANION_WBA_SCREEN_TICK_LIFE, 480u));
    CHECK(clock.delay == 480u);
    CHECK(companion_epaper_stm32wba_schedule_tick(
        &scheduler, COMPANION_WBA_SCREEN_TICK_BLINK, 120u));
    CHECK(clock.delay == 120u);
    starts = clock.starts;
    /* Later expression recovery/charging must not overwrite an earlier blink. */
    companion_epaper_stm32wba_schedule_expression_tick(&scheduler, 5000u);
    CHECK(companion_epaper_stm32wba_schedule_tick(
        &scheduler, COMPANION_WBA_SCREEN_TICK_CHARGING, 960u));
    CHECK(clock.starts == starts && clock.delay == 120u);
    CHECK(companion_epaper_stm32wba_schedule_tick(
        &scheduler, COMPANION_WBA_SCREEN_TICK_RECORDING, 0u));
    CHECK(companion_epaper_stm32wba_schedule_tick(
        &scheduler, COMPANION_WBA_SCREEN_TICK_RECORDING, 0u));
    CHECK(clock.wakes == 1u);
    CHECK(companion_epaper_stm32wba_take_due(&scheduler) == MASK(RECORDING));
    CHECK(clock.delay == 120u);
    clock.now = 119u; /* early/stale one-shot notification */
    CHECK(companion_epaper_stm32wba_take_due(&scheduler) == 0u);
    CHECK(clock.delay == 1u);
    clock.now = 120u;
    CHECK(companion_epaper_stm32wba_take_due(&scheduler) == MASK(BLINK));
    CHECK(clock.delay == 360u);
    companion_epaper_stm32wba_cancel_tick(&scheduler, COMPANION_WBA_SCREEN_TICK_EXPRESSION);
    CHECK(clock.delay == 360u);
    clock.now = 1400u; /* panel BUSY spans both deadlines */
    CHECK(companion_epaper_stm32wba_take_due(&scheduler) == (MASK(LIFE) | MASK(CHARGING)));
    CHECK(companion_epaper_stm32wba_take_due(&scheduler) == 0u);
    CHECK(!scheduler.timer_armed);
    CHECK(!companion_epaper_stm32wba_schedule_tick(
        &scheduler, COMPANION_WBA_SCREEN_TICK_COUNT, 1u));
    CHECK(!companion_epaper_stm32wba_schedule_tick(
        &scheduler, (companion_epaper_stm32wba_tick_t)-1, 1u));
    CHECK(!companion_epaper_stm32wba_schedule_tick(
        &scheduler, COMPANION_WBA_SCREEN_TICK_LIFE, UINT32_MAX));
    clock.now = UINT32_MAX - 10u;
    CHECK(companion_epaper_stm32wba_schedule_tick(
        &scheduler, COMPANION_WBA_SCREEN_TICK_LIFE, 20u));
    clock.now = 8u;
    CHECK(companion_epaper_stm32wba_take_due(&scheduler) == 0u && clock.delay == 1u);
    clock.now = 9u;
    CHECK(companion_epaper_stm32wba_take_due(&scheduler) == MASK(LIFE));
    companion_epaper_stm32wba_schedule_expression_tick(&scheduler, 0u);
    companion_epaper_stm32wba_cancel_all_ticks(&scheduler);
    CHECK(companion_epaper_stm32wba_take_due(&scheduler) == 0u);
    companion_epaper_stm32wba_scheduler_init(&scheduler, NULL);
    CHECK(!companion_epaper_stm32wba_schedule_tick(
        &scheduler, COMPANION_WBA_SCREEN_TICK_LIFE, 0u));
    puts("PASS scheduler: independent deadlines, BUSY catch-up, stale wake, wrap, cancel, invalid input");
    return true;
}

static bool test_composition_replay(void)
{
    fake_clock_t clock = {0};
    companion_epaper_stm32wba_scheduler_t scheduler;
    comp_screen_composition_t composition;
    comp_epaper_overlay_commit_scheduler_t recording;
    uint32_t life = 0u, wave = 0u, charging = 0u, blink = 0u, request = 0u;
    init_scheduler(&scheduler, &clock);
    comp_screen_composition_init(&composition);
    comp_epaper_overlay_commit_scheduler_init(&recording);
    CHECK(comp_epaper_overlay_commit_scheduler_activate(&recording));
    for (unsigned tick = 0u; tick < (unsigned)COMPANION_WBA_SCREEN_TICK_COUNT; ++tick) {
        CHECK(companion_epaper_stm32wba_schedule_tick(
            &scheduler, (companion_epaper_stm32wba_tick_t)tick,
            tick == (unsigned)COMPANION_WBA_SCREEN_TICK_BLINK ? 12000u : 0u));
    }
    while (clock.now < 90000u) {
        uint32_t due = companion_epaper_stm32wba_take_due(&scheduler);
        if (due == 0u) {
            CHECK(scheduler.timer_armed);
            clock.now += clock.delay;
            continue;
        }
        if ((due & MASK(LIFE)) != 0u) {
            life++;
            CHECK(comp_screen_composition_set_base(&composition, (uint16_t)life, life));
            CHECK(companion_epaper_stm32wba_schedule_tick(
                &scheduler, COMPANION_WBA_SCREEN_TICK_LIFE, 480u));
        }
        if ((due & MASK(BLINK)) != 0u) {
            blink++;
            CHECK(companion_epaper_stm32wba_schedule_tick(
                &scheduler, COMPANION_WBA_SCREEN_TICK_BLINK, 12000u));
        }
        if ((due & MASK(CHARGING)) != 0u) {
            charging++;
            CHECK(comp_screen_composition_set_charging(&composition, true, (uint8_t)(charging % 4u)));
            CHECK(companion_epaper_stm32wba_schedule_tick(
                &scheduler, COMPANION_WBA_SCREEN_TICK_CHARGING, 960u));
        }
        if ((due & MASK(RECORDING)) != 0u) {
            const uint32_t base_revision = composition.base.revision;
            const uint32_t charge_revision = composition.charging.revision;
            comp_screen_composition_snapshot_t snapshot;
            comp_epaper_overlay_commit_report_t report;
            CHECK(comp_epaper_overlay_commit_scheduler_prepare(&recording, true));
            request++;
            CHECK(comp_epaper_overlay_commit_scheduler_mark_dispatched(&recording, request, clock.now));
            /* Variable completion latency includes a slow display. Failure must
             * leave the visible composition intact and release only its owner. */
            clock.now += request % 7u == 0u ? 900u : 160u;
            CHECK(!comp_epaper_overlay_commit_scheduler_complete(
                &recording, request + 1u, true, clock.now, &report));
            CHECK(comp_epaper_overlay_commit_scheduler_complete(
                &recording, request, request % 11u != 0u, clock.now, &report));
            if (report.visible != 0u) {
                wave++;
                CHECK(comp_screen_composition_set_recording(&composition, true, (uint16_t)wave, wave));
            }
            CHECK(composition.base.revision == base_revision);
            CHECK(composition.charging.revision == charge_revision);
            comp_screen_composition_snapshot(&composition, COMP_SCREEN_SURFACE_MENU, &snapshot);
            CHECK(!snapshot.base_visible && !snapshot.recording_visible && !snapshot.charging_visible);
            comp_screen_composition_snapshot(&composition, COMP_SCREEN_SURFACE_HOME, &snapshot);
            CHECK(snapshot.base_visible && snapshot.recording_visible && snapshot.charging_visible);
            CHECK(companion_epaper_stm32wba_schedule_tick(
                &scheduler, COMPANION_WBA_SCREEN_TICK_RECORDING, 0u));
        }
    }
    CHECK(life > 50u && blink >= 5u && charging > 30u && wave > life);
    CHECK(recording.failed_commit_count > 0u);
    companion_epaper_stm32wba_cancel_tick(&scheduler, COMPANION_WBA_SCREEN_TICK_RECORDING);
    comp_epaper_overlay_commit_scheduler_stop(&recording);
    CHECK((scheduler.active_mask & MASK(RECORDING)) == 0u);
    CHECK((scheduler.active_mask & MASK(LIFE)) != 0u);
    printf("PASS 90s logical replay: life=%lu blink=%lu charging=%lu wave=%lu failed_transactions=%lu\n",
           (unsigned long)life, (unsigned long)blink, (unsigned long)charging,
           (unsigned long)wave, (unsigned long)recording.failed_commit_count);
    return true;
}

typedef struct {
    uint8_t *bytes;
    size_t size;
    unsigned reads;
    bool fail;
} fake_store_t;
static bool read_bytes(void *context, uint32_t offset, uint8_t *out, size_t length)
{
    fake_store_t *store = context;
    store->reads++;
    if (store->fail || offset > store->size || length > store->size - offset) {
        return false;
    }
    memcpy(out, store->bytes + offset, length);
    return true;
}
static bool bind_store(companion_screen_assets_stm32wba_t *adapter,
                       comp_asset_store_t *store, fake_store_t *fake,
                       companion_epaper_panel_stm32wba_target_t target)
{
    const companion_screen_assets_stm32wba_config_t config = {
        .target = target, .partition_size = (uint32_t)fake->size,
        .read = read_bytes, .context = fake,
    };
    return companion_screen_assets_stm32wba_bind(adapter, store, &config);
}

static bool test_asset_boundaries(void)
{
    uint8_t bytes[777], cache[256], output[512];
    fake_store_t fake = {.bytes = bytes, .size = sizeof(bytes)};
    companion_screen_assets_stm32wba_t adapter;
    comp_asset_store_t store;
    for (size_t i = 0u; i < sizeof(bytes); ++i) { bytes[i] = (uint8_t)i; }
    CHECK(bind_store(&adapter, &store, &fake, COMPANION_EPAPER_PANEL_STM32WBA_TARGET_WBA55));
    CHECK(companion_screen_assets_stm32wba_set_cache(&adapter, cache, sizeof(cache)));
    for (uint32_t i = 0u; i < 256u; ++i) {
        CHECK(comp_asset_store_read(&store, i, output, 1u) && output[0] == (uint8_t)i);
    }
    CHECK(fake.reads == 1u);
    printf("PASS tiny-read cache: 256 logical reads / %u backing read (256-byte buffer)\n", fake.reads);
    CHECK(comp_asset_store_read(&store, 250u, output, 20u));
    CHECK(memcmp(output, bytes + 250u, 20u) == 0);
    CHECK(comp_asset_store_read(&store, 770u, output, 7u));
    CHECK(memcmp(output, bytes + 770u, 7u) == 0);
    CHECK(comp_asset_store_read(&store, 0u, output, sizeof(output)));
    CHECK(memcmp(output, bytes, sizeof(output)) == 0);
    CHECK(!comp_asset_store_read(&store, 777u, output, 1u));
    CHECK(!comp_asset_store_read(&store, UINT32_MAX, output, 1u));
    CHECK(!comp_asset_store_read(&store, 0u, output, SIZE_MAX));
    CHECK(comp_asset_store_read(&store, 777u, output, 0u));
    CHECK(!companion_screen_assets_stm32wba_set_cache(&adapter, NULL, 256u));
    CHECK(!companion_screen_assets_stm32wba_set_cache(&adapter, cache, 0u));
    fake.fail = true;
    companion_screen_assets_stm32wba_invalidate(&adapter);
    CHECK(!comp_asset_store_read(&store, 0u, output, 1u));
    CHECK(adapter.cache_length == 0u);
    fake.fail = false;
    bytes[0] = 93u;
    CHECK(comp_asset_store_read(&store, 0u, output, 1u) && output[0] == 93u);
    bytes[0] = 94u;
    companion_screen_assets_stm32wba_invalidate(&adapter);
    CHECK(comp_asset_store_read(&store, 0u, output, 1u) && output[0] == 94u);
    fake.fail = true;
    CHECK(!comp_asset_store_read(&store, 0u, output, sizeof(output)));
    CHECK(adapter.cache_length == 0u);
    fake.fail = false;
    CHECK(companion_screen_assets_stm32wba_bind(&adapter, &store, &adapter.config));
    CHECK(adapter.cache == NULL);
    CHECK(comp_asset_store_read(&store, 0u, output, 1u) && output[0] == 94u);
    CHECK(!companion_screen_assets_stm32wba_bind(&adapter, &store, NULL));
    CHECK(!companion_screen_assets_stm32wba_ready(&adapter));
    CHECK(!comp_asset_store_read(&store, 0u, output, 1u));
    CHECK(bind_store(&adapter, &store, &fake, COMPANION_EPAPER_PANEL_STM32WBA_TARGET_WBA65));
    CHECK(!bind_store(&adapter, &store, &fake, (companion_epaper_panel_stm32wba_target_t)99));
    CHECK(store.read == NULL && adapter.config.read == NULL);
    puts("PASS assets: cross-page, tail, overflow, failed I/O, invalidation and failed rebind");
    return true;
}

static uint16_t le16(const uint8_t *bytes)
{
    return (uint16_t)((uint16_t)bytes[0] | (uint16_t)((uint16_t)bytes[1] << 8));
}
static bool test_cemp(fake_store_t *fake,
                      companion_epaper_panel_stm32wba_target_t target)
{
    const comp_screen_asset_profile_t profile = {
        .width = 200u, .height = 200u, .stride_bytes = 25u,
        .pixel_format = COMP_SCREEN_PIXEL_FORMAT_MONO_1BPP_WHITE_IS_ONE_MSB,
    };
    companion_screen_assets_stm32wba_t adapter;
    comp_asset_store_t store;
    comp_emote_asset_mount_t mount;
    /* Host-only catalog allocation; production provides bounded target buffers. */
    size_t clip_count = le16(fake->bytes + 28u);
    size_t frame_count = le16(fake->bytes + 30u);
    comp_emote_clip_t *clips = calloc(clip_count, sizeof(*clips));
    comp_emote_frame_t *frames = calloc(frame_count, sizeof(*frames));
    char *strings = calloc(fake->size, 1u);
    uint8_t scratch[256], cache[256], plain[5000], cached[5000];
    unsigned direct_reads = 0u, cached_reads = 0u;
    CHECK(clips != NULL && frames != NULL && strings != NULL);
    CHECK(bind_store(&adapter, &store, fake, target));
    CHECK(comp_emote_asset_pack_mount(&mount, &store, &profile,
        clips, clip_count, frames, frame_count, strings, fake->size,
        scratch, sizeof(scratch)) == COMP_EMOTE_ASSET_MOUNT_OK);
    CHECK(comp_emote_asset_pack_verify_payload(&mount.pack, scratch, sizeof(scratch)));
    for (size_t i = 0u; i < frame_count; ++i) {
        unsigned before;
        CHECK(companion_screen_assets_stm32wba_set_cache(&adapter, NULL, 0u));
        before = fake->reads;
        CHECK(comp_emote_asset_pack_read_frame(&mount.pack, frames + i, plain, sizeof(plain)));
        direct_reads += fake->reads - before;
        CHECK(companion_screen_assets_stm32wba_set_cache(&adapter, cache, sizeof(cache)));
        before = fake->reads;
        CHECK(comp_emote_asset_pack_read_frame(&mount.pack, frames + i, cached, sizeof(cached)));
        cached_reads += fake->reads - before;
        CHECK(memcmp(plain, cached, sizeof(plain)) == 0);
    }
    CHECK(cached_reads <= direct_reads);
    /* Invalidating after changed backing bytes must expose CRC corruption. */
    fake->bytes[fake->size - 1u] ^= 1u;
    companion_screen_assets_stm32wba_invalidate(&adapter);
    CHECK(!comp_emote_asset_pack_verify_payload(&mount.pack, scratch, sizeof(scratch)));
    fake->bytes[fake->size - 1u] ^= 1u;
    companion_screen_assets_stm32wba_invalidate(&adapter);
    CHECK(comp_emote_asset_pack_verify_payload(&mount.pack, scratch, sizeof(scratch)));
    printf("PASS CEMP %s: %lu frames pixel-identical, callback_reads=%u cached=%u; corrupt payload rejected\n",
        target == COMPANION_EPAPER_PANEL_STM32WBA_TARGET_WBA55 ? "WBA55" : "WBA65",
        (unsigned long)frame_count, direct_reads, cached_reads);
    free(strings);
    free(frames);
    free(clips);
    return true;
}

int main(int argc, char **argv)
{
    FILE *file;
    long length;
    fake_store_t fake = {0};
    bool ok;
    if (!test_deadlines() || !test_composition_replay() || !test_asset_boundaries()) {
        return 1;
    }
    if (argc != 2 || (file = fopen(argv[1], "rb")) == NULL) { return 2; }
    if (fseek(file, 0, SEEK_END) != 0 || (length = ftell(file)) < 80 ||
        fseek(file, 0, SEEK_SET) != 0) { fclose(file); return 2; }
    fake.size = (size_t)length;
    fake.bytes = malloc(fake.size);
    if (fake.bytes == NULL) { fclose(file); return 2; }
    if (fread(fake.bytes, 1u, fake.size, file) != fake.size) {
        fclose(file); free(fake.bytes); return 2;
    }
    fclose(file);
    ok = test_cemp(&fake, COMPANION_EPAPER_PANEL_STM32WBA_TARGET_WBA55) &&
         test_cemp(&fake, COMPANION_EPAPER_PANEL_STM32WBA_TARGET_WBA65);
    free(fake.bytes);
    if (!ok) { return 1; }
    puts("PASS_PREHARDWARE: host behavior only; hardware acceptance pending");
    return 0;
}
