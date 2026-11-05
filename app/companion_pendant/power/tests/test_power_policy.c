#include "power_policy.h"
#include "power_settings_store.h"

#include <stdio.h>
#include <string.h>

static int fail(const char *message)
{
    fprintf(stderr, "FAIL: %s\n", message);
    return 1;
}

typedef struct {
    comp_power_policy_t policy;
    bool idle_due;
    bool low_power_queued;
    bool queued_entry_cancelled;
    unsigned low_power_enters;
    unsigned recording_starts;
} idle_record_race_t;

static void race_try_enter_low_power(idle_record_race_t *race)
{
    if (race->idle_due && comp_power_policy_stop_allowed(&race->policy)) {
        race->idle_due = false;
        race->low_power_enters++;
    }
}

static void race_queue_low_power(idle_record_race_t *race)
{
    if (race->idle_due && comp_power_policy_stop_allowed(&race->policy)) {
        race->idle_due = false;
        race->low_power_queued = true;
    }
}

static void race_cancel_queued_low_power(idle_record_race_t *race)
{
    race->queued_entry_cancelled = true;
}

static void race_drain_low_power(idle_record_race_t *race)
{
    if (!race->low_power_queued) return;
    race->low_power_queued = false;
    if (race->queued_entry_cancelled) {
        race->queued_entry_cancelled = false;
        return;
    }
    race->low_power_enters++;
}

static void race_init_idle(idle_record_race_t *race)
{
    comp_power_policy_init(&race->policy);
    comp_power_policy_set_touch_wake_ready(&race->policy, true);
    comp_power_policy_set_blocker(
        &race->policy, COMP_POWER_BLOCKER_BOOT, false);
    race->idle_due = false;
    race->low_power_queued = false;
    race->queued_entry_cancelled = false;
    race->low_power_enters = 0u;
    race->recording_starts = 0u;
}

static int test_idle_deadline_double_tap_interleave(void)
{
    idle_record_race_t race;
    idle_record_race_t mutation;

    race_init_idle(&race);

    /* Worst real scheduler order: the RTC deadline posts ENTER_LOW_POWER,
     * then the physical first DOWN arrives before DisplayTask drains it.
     * Activity must invalidate the posted intent, not merely clear idle_due. */
    race.idle_due = true;
    race_queue_low_power(&race);
    comp_power_policy_set_blocker(
        &race.policy, COMP_POWER_BLOCKER_SCREEN_WAIT, true);
    race_cancel_queued_low_power(&race);
    race_drain_low_power(&race);
    if (race.low_power_enters != 0u || race.low_power_queued) {
        return fail("queued idle entry survived first-touch cancellation");
    }

    race_init_idle(&mutation);
    mutation.idle_due = true;
    race_queue_low_power(&mutation);
    race_drain_low_power(&mutation);
    if (mutation.low_power_enters != 1u) {
        return fail("queued-entry test does not reject missing cancellation");
    }

    race_init_idle(&race);

    /* Production order at the first physical DOWN:
     * 1. buffer_touch_sample_during_panel_wait marks SCREEN_WAIT;
     * 2. cancel_low_power_idle_pose_timer clears an armed/due deadline.
     * Force the worst RTC interleave by firing the deadline immediately after
     * cancel. SCREEN_WAIT must still prevent a sleepy commit. */
    comp_power_policy_set_blocker(
        &race.policy, COMP_POWER_BLOCKER_SCREEN_WAIT, true);
    race.idle_due = false;
    race.idle_due = true; /* late TimerServer callback */
    race_try_enter_low_power(&race);

    /* First release starts the bounded double-tap confirmation window. */
    comp_power_policy_set_blocker(
        &race.policy, COMP_POWER_BLOCKER_SCREEN_WAIT, false);
    comp_power_policy_set_blocker(
        &race.policy, COMP_POWER_BLOCKER_TOUCH_CONFIRMATION, true);
    race_try_enter_low_power(&race);

    /* Second DOWN is captured before replay and before recording dispatch. */
    comp_power_policy_set_blocker(
        &race.policy, COMP_POWER_BLOCKER_SCREEN_WAIT, true);
    comp_power_policy_set_blocker(
        &race.policy, COMP_POWER_BLOCKER_TOUCH_CONTACT, true);
    race_try_enter_low_power(&race);

    /* Recording commit takes ownership before the gesture blockers clear. */
    comp_power_policy_set_blocker(
        &race.policy, COMP_POWER_BLOCKER_MIC_CAPTURE, true);
    race.recording_starts++;
    comp_power_policy_set_blocker(
        &race.policy, COMP_POWER_BLOCKER_TOUCH_CONFIRMATION, false);
    comp_power_policy_set_blocker(
        &race.policy, COMP_POWER_BLOCKER_TOUCH_CONTACT, false);
    comp_power_policy_set_blocker(
        &race.policy, COMP_POWER_BLOCKER_SCREEN_WAIT, false);
    race_try_enter_low_power(&race);

    if (race.low_power_enters != 0u || race.recording_starts != 1u ||
        !race.idle_due) {
        return fail("idle deadline crossed double-tap/recording gate");
    }

    /* Sensitivity check: the rejected ordering (deadline callback before the
     * first-DOWN blocker) must actually enter low power. */
    race_init_idle(&mutation);
    mutation.idle_due = true;
    race_try_enter_low_power(&mutation);
    if (mutation.low_power_enters != 1u) {
        return fail("race test does not reject blocker-after-deadline mutation");
    }

    /* Normal idle remains reachable after all genuine activity is absent. */
    race_init_idle(&race);
    race.idle_due = true;
    race_try_enter_low_power(&race);
    if (race.low_power_enters != 1u || race.idle_due) {
        return fail("normal idle entry regressed");
    }

    return 0;
}

typedef struct {
    uint8_t bytes[COMP_POWER_SETTINGS_SECTOR_BYTES];
    size_t write_limit;
    unsigned erase_count;
    unsigned write_count;
    size_t programmed_bytes;
    size_t maximum_write_length;
    uint32_t last_write_offset;
    bool erase_fails;
} fake_settings_flash_t;

static bool fake_settings_read(void *context,
                               uint32_t offset,
                               uint8_t *destination,
                               size_t length)
{
    fake_settings_flash_t *flash = context;
    if (flash == NULL || destination == NULL ||
        offset > sizeof(flash->bytes) || length > sizeof(flash->bytes) - offset) {
        return false;
    }
    memcpy(destination, &flash->bytes[offset], length);
    return true;
}

static bool fake_settings_write(void *context,
                                uint32_t offset,
                                const uint8_t *source,
                                size_t length)
{
    fake_settings_flash_t *flash = context;
    size_t written;
    size_t index;
    if (flash == NULL || source == NULL ||
        offset > sizeof(flash->bytes) || length > sizeof(flash->bytes) - offset) {
        return false;
    }
    written = flash->write_limit < length ? flash->write_limit : length;
    flash->write_count++;
    flash->programmed_bytes += written;
    if (length > flash->maximum_write_length) {
        flash->maximum_write_length = length;
    }
    flash->last_write_offset = offset;
    for (index = 0u; index < written; ++index) {
        flash->bytes[offset + index] &= source[index];
    }
    return written == length;
}

static bool fake_settings_erase(void *context)
{
    fake_settings_flash_t *flash = context;
    if (flash == NULL || flash->erase_fails) {
        return false;
    }
    memset(flash->bytes, 0xFF, sizeof(flash->bytes));
    flash->erase_count++;
    return true;
}

static uint32_t test_crc32(const uint8_t *data, size_t length)
{
    uint32_t crc = ~0u;
    for (size_t index = 0u; index < length; ++index) {
        crc ^= data[index];
        for (uint8_t bit = 0u; bit < 8u; ++bit)
            crc = (crc >> 1u) ^ (0xEDB88320u & (0u - (crc & 1u)));
    }
    return ~crc;
}

static void test_put_u32(uint8_t *bytes, uint32_t value)
{
    bytes[0] = (uint8_t)value;
    bytes[1] = (uint8_t)(value >> 8u);
    bytes[2] = (uint8_t)(value >> 16u);
    bytes[3] = (uint8_t)(value >> 24u);
}

static void test_put_u16(uint8_t *bytes, uint16_t value)
{
    bytes[0] = (uint8_t)value;
    bytes[1] = (uint8_t)(value >> 8u);
}

static bool settings_equal(const comp_power_settings_values_t *left,
                           const comp_power_settings_values_t *right)
{
    return left != NULL && right != NULL &&
           left->silent_auto_stop == right->silent_auto_stop &&
           left->auto_reconnect == right->auto_reconnect &&
           left->clock_24_hour == right->clock_24_hour &&
           left->gaze_follow == right->gaze_follow &&
           left->natural_blink == right->natural_blink &&
           left->idle_minutes == right->idle_minutes &&
           left->recording_limit_minutes == right->recording_limit_minutes &&
           left->recorder_profile == right->recorder_profile &&
           left->interaction_level == right->interaction_level &&
           left->quiet_hours == right->quiet_hours &&
           left->recording_gesture == right->recording_gesture &&
           left->time_zone_offset_minutes == right->time_zone_offset_minutes;
}

static int save_remount_exactly_once(
    fake_settings_flash_t *flash,
    const comp_power_settings_port_t *port,
    comp_power_settings_store_t *store,
    const comp_power_settings_values_t *expected,
    const char *label)
{
    comp_power_settings_store_t remounted;
    unsigned writes_before = flash->write_count;
    size_t bytes_before = flash->programmed_bytes;
    uint16_t slot_before = store->next_slot;

    if (comp_power_settings_store_save_values(store, expected) !=
            COMP_POWER_SETTINGS_OK ||
        flash->write_count != writes_before + 1u ||
        flash->programmed_bytes != bytes_before +
                                       COMP_POWER_SETTINGS_RECORD_BYTES ||
        flash->maximum_write_length != COMP_POWER_SETTINGS_RECORD_BYTES ||
        flash->last_write_offset !=
            (uint32_t)slot_before * COMP_POWER_SETTINGS_RECORD_BYTES ||
        comp_power_settings_store_mount(&remounted, port) !=
            COMP_POWER_SETTINGS_OK ||
        !settings_equal(comp_power_settings_store_values(&remounted),
                        expected)) {
        return fail(label);
    }
    *store = remounted;
    writes_before = flash->write_count;
    bytes_before = flash->programmed_bytes;
    if (comp_power_settings_store_save_values(store, expected) !=
            COMP_POWER_SETTINGS_OK ||
        flash->write_count != writes_before ||
        flash->programmed_bytes != bytes_before) {
        return fail("unchanged settings write amplification");
    }
    return 0;
}

static int test_all_settings_round_trip(
    fake_settings_flash_t *flash,
    const comp_power_settings_port_t *port,
    comp_power_settings_store_t *store)
{
    comp_power_settings_values_t values;
    uint8_t index;
    static const uint8_t idle_values[] = {0u, 1u, 5u, 3u};
    static const uint8_t limit_values[] = {15u, 60u, 30u, 0u};
    static const uint8_t interaction_values[] = {0u, 2u, 1u};
    static const uint8_t quiet_values[] = {1u, 2u, 0u};
    static const int16_t time_zones[] = {0, -300, 480};

#define SAVE_ONE(label) \
    do { if (save_remount_exactly_once(flash, port, store, &values, label)) \
             return 1; } while (0)
#define RESET_VALUES() comp_power_settings_values_default(&values)

    RESET_VALUES(); values.silent_auto_stop = false;
    SAVE_ONE("silent_auto_stop round trip");
    RESET_VALUES(); values.auto_reconnect = false;
    SAVE_ONE("auto_reconnect round trip");
    RESET_VALUES(); values.clock_24_hour = false;
    SAVE_ONE("clock_24_hour round trip");
    RESET_VALUES(); values.gaze_follow = false;
    SAVE_ONE("gaze_follow round trip");
    RESET_VALUES(); values.natural_blink = false;
    SAVE_ONE("natural_blink round trip");
    for (index = 0u; index < sizeof(idle_values); ++index) {
        RESET_VALUES(); values.idle_minutes = idle_values[index];
        SAVE_ONE("idle_minutes boundary round trip");
    }
    for (index = 0u; index < sizeof(limit_values); ++index) {
        RESET_VALUES(); values.recording_limit_minutes = limit_values[index];
        SAVE_ONE("recording_limit_minutes boundary round trip");
    }
    RESET_VALUES(); values.recorder_profile = 1u;
    SAVE_ONE("recorder_profile round trip");
    for (index = 0u; index < 3u; ++index) {
        RESET_VALUES(); values.interaction_level = interaction_values[index];
        SAVE_ONE("interaction_level boundary round trip");
    }
    for (index = 0u; index < 3u; ++index) {
        RESET_VALUES(); values.quiet_hours = quiet_values[index];
        SAVE_ONE("quiet_hours boundary round trip");
    }
    for (index = 0u; index < 3u; ++index) {
        RESET_VALUES(); values.time_zone_offset_minutes = time_zones[index];
        SAVE_ONE("time_zone_offset_minutes boundary round trip");
    }
    RESET_VALUES(); values.recording_gesture = 1u;
    SAVE_ONE("recording_gesture round trip");

#undef RESET_VALUES
#undef SAVE_ONE
    return 0;
}

static int test_browser_policy_matrix(void)
{
    comp_power_settings_values_t values;
    static const uint8_t recording_limits[] = {0u, 15u, 30u, 60u};
    static const uint16_t recording_seconds[] = {2700u, 900u, 1800u, 3600u};
    static const uint16_t interaction_ms[] = {1920u, 960u, 480u};
    uint8_t index;
    uint16_t tracker;
    uint16_t blocks;

    comp_power_settings_values_default(&values);
    for (index = 0u; index < 4u; ++index) {
        values.recording_limit_minutes = recording_limits[index];
        if (comp_power_settings_recording_max_seconds(&values) !=
            recording_seconds[index]) {
            return fail("recording limit policy matrix");
        }
    }
    values.recording_limit_minutes = 30u;
    values.silent_auto_stop = false;
    for (index = 0u; index < 2u; ++index) {
        values.recorder_profile = index;
        if (comp_power_settings_silence_stop_blocks(&values) != 0u) {
            return fail("disabled silent auto-stop policy");
        }
    }
    values.silent_auto_stop = true;
    values.recorder_profile = 0u;
    if (comp_power_settings_silence_stop_blocks(&values) != 500u) {
        return fail("voice silent auto-stop policy");
    }
    tracker = 0u;
    for (blocks = 0u; blocks < 700u; ++blocks) {
        if (comp_power_settings_silence_tracker_step(
                &values, false, &tracker) || tracker != 0u) {
            return fail("silence before voice never auto-stops");
        }
    }
    if (comp_power_settings_silence_tracker_step(
            &values, true, &tracker) || tracker != 0x8000u) {
        return fail("voice arms silence tracker");
    }
    for (blocks = 1u; blocks < 500u; ++blocks) {
        if (comp_power_settings_silence_tracker_step(
                &values, false, &tracker)) {
            return fail("voice silence threshold fires early");
        }
    }
    if (!comp_power_settings_silence_tracker_step(
            &values, false, &tracker) ||
        (tracker & 0x7FFFu) != 500u) {
        return fail("voice silence threshold exact boundary");
    }
    if (comp_power_settings_silence_tracker_step(
            &values, true, &tracker) || tracker != 0x8000u) {
        return fail("new voice resets silence tracker");
    }
    values.recorder_profile = 1u;
    if (comp_power_settings_silence_stop_blocks(&values) != 1500u) {
        return fail("meeting silent auto-stop policy");
    }
    tracker = 0x8000u;
    for (blocks = 1u; blocks < 1500u; ++blocks) {
        if (comp_power_settings_silence_tracker_step(
                &values, false, &tracker)) {
            return fail("meeting silence threshold fires early");
        }
    }
    if (!comp_power_settings_silence_tracker_step(
            &values, false, &tracker) ||
        (tracker & 0x7FFFu) != 1500u) {
        return fail("meeting silence threshold exact boundary");
    }
    values.silent_auto_stop = false;
    if (comp_power_settings_silence_tracker_step(
            &values, false, &tracker) || tracker != 0u) {
        return fail("disabled silence policy clears tracker");
    }
    values.silent_auto_stop = true;
    for (index = 0u; index < 3u; ++index) {
        values.interaction_level = index;
        if (comp_power_settings_interaction_interval_ms(&values) !=
            interaction_ms[index]) {
            return fail("interaction level cadence matrix");
        }
    }

    values.interaction_level = 1u;
    values.quiet_hours = 0u;
    if (comp_power_settings_quiet_hours_active(&values, 1379u) ||
        !comp_power_settings_quiet_hours_active(&values, 1380u) ||
        !comp_power_settings_quiet_hours_active(&values, 1439u) ||
        !comp_power_settings_quiet_hours_active(&values, 0u) ||
        !comp_power_settings_quiet_hours_active(&values, 419u) ||
        comp_power_settings_quiet_hours_active(&values, 420u)) {
        return fail("quiet hours 23:00-07:00 boundaries");
    }
    values.quiet_hours = 1u;
    if (comp_power_settings_quiet_hours_active(&values, 1319u) ||
        !comp_power_settings_quiet_hours_active(&values, 1320u) ||
        !comp_power_settings_quiet_hours_active(&values, 479u) ||
        comp_power_settings_quiet_hours_active(&values, 480u)) {
        return fail("quiet hours 22:00-08:00 boundaries");
    }
    values.quiet_hours = 2u;
    if (comp_power_settings_quiet_hours_active(&values, 0u) ||
        comp_power_settings_quiet_hours_active(&values, 1439u)) {
        return fail("quiet hours disabled boundaries");
    }

    values.quiet_hours = 0u;
    values.clock_24_hour = false;
    if (comp_power_settings_display_hour(&values, 0u) != 12u ||
        comp_power_settings_display_hour(&values, 12u) != 12u ||
        comp_power_settings_display_hour(&values, 13u) != 1u ||
        comp_power_settings_display_hour(&values, 23u) != 11u) {
        return fail("12-hour clock boundary matrix");
    }
    values.clock_24_hour = true;
    for (index = 0u; index < 24u; ++index) {
        if (comp_power_settings_display_hour(&values, index) != index) {
            return fail("24-hour clock identity matrix");
        }
    }

    values.recording_gesture = 0u;
    if (!comp_power_settings_recording_entry_allowed(&values, true, false) ||
        comp_power_settings_recording_entry_allowed(&values, false, true) ||
        comp_power_settings_recording_entry_allowed(&values, false, false)) {
        return fail("corner recording gesture matrix");
    }
    values.recording_gesture = 1u;
    if (comp_power_settings_recording_entry_allowed(&values, true, false) ||
        !comp_power_settings_recording_entry_allowed(&values, false, true) ||
        comp_power_settings_recording_entry_allowed(&values, false, false)) {
        return fail("edge-pull recording gesture matrix");
    }

    values.interaction_level = 3u;
    if (comp_power_settings_recording_max_seconds(&values) != 180u ||
        comp_power_settings_silence_stop_blocks(&values) != 0u ||
        comp_power_settings_interaction_interval_ms(&values) != 960u ||
        comp_power_settings_quiet_hours_active(&values, 0u) ||
        comp_power_settings_recording_entry_allowed(&values, true, true)) {
        return fail("invalid policy uses safe outputs");
    }
    return 0;
}

static int test_power_settings_store(void)
{
    fake_settings_flash_t flash;
    comp_power_settings_store_t store;
    comp_power_settings_store_t remounted;
    comp_power_settings_values_t values;
    const comp_power_settings_port_t port = {
        .read = fake_settings_read,
        .write = fake_settings_write,
        .erase = fake_settings_erase,
        .context = &flash,
    };

    memset(&flash, 0xFF, sizeof(flash));
    flash.write_limit = COMP_POWER_SETTINGS_RECORD_BYTES;
    flash.erase_count = 0u;
    flash.write_count = 0u;
    flash.programmed_bytes = 0u;
    flash.maximum_write_length = 0u;
    flash.last_write_offset = 0u;
    flash.erase_fails = false;
    if (comp_power_settings_store_mount(&store, &port) !=
            COMP_POWER_SETTINGS_OK ||
        comp_power_settings_store_idle_minutes(&store) != 3u ||
        store.next_slot != 0u) {
        return fail("blank settings store default");
    }
    if (comp_power_settings_store_save(&store, 1u) !=
            COMP_POWER_SETTINGS_OK || flash.write_count != 1u ||
        flash.programmed_bytes != COMP_POWER_SETTINGS_RECORD_BYTES) {
        return fail("settings first append");
    }
    if (comp_power_settings_store_save(&store, 1u) !=
            COMP_POWER_SETTINGS_OK || flash.write_count != 1u) {
        return fail("unchanged settings append suppressed");
    }

    /* A torn append must leave the prior CRC-valid record authoritative. */
    flash.write_limit = 8u;
    if (comp_power_settings_store_save(&store, 5u) !=
        COMP_POWER_SETTINGS_IO_ERROR) {
        return fail("torn settings append rejected");
    }
    flash.write_limit = COMP_POWER_SETTINGS_RECORD_BYTES;
    if (comp_power_settings_store_mount(&remounted, &port) !=
            COMP_POWER_SETTINGS_OK ||
        comp_power_settings_store_idle_minutes(&remounted) != 1u ||
        remounted.next_slot != 2u) {
        return fail("torn append preserves prior value");
    }
    if (comp_power_settings_store_save(&remounted, 5u) !=
        COMP_POWER_SETTINGS_OK) {
        return fail("append after torn record");
    }

    /* Direct corruption of the newest CRC falls back to the prior record. */
    flash.bytes[2u * COMP_POWER_SETTINGS_RECORD_BYTES + 12u] ^= 0x01u;
    if (comp_power_settings_store_mount(&store, &port) !=
            COMP_POWER_SETTINGS_OK ||
        comp_power_settings_store_idle_minutes(&store) != 1u ||
        comp_power_settings_store_save(&store, 2u) !=
            COMP_POWER_SETTINGS_INVALID_VALUE) {
        return fail("corrupt/unsupported setting fallback");
    }

    /* Every browser setting shares one atomic generation. */
    comp_power_settings_values_default(&values);
    values.silent_auto_stop = false;
    values.auto_reconnect = false;
    values.clock_24_hour = false;
    values.gaze_follow = false;
    values.natural_blink = false;
    values.idle_minutes = 5u;
    values.recording_limit_minutes = 60u;
    values.recorder_profile = 1u;
    values.interaction_level = 2u;
    values.quiet_hours = 2u;
    values.recording_gesture = 1u;
    values.time_zone_offset_minutes = -300;
    if (comp_power_settings_store_save_values(&store, &values) !=
            COMP_POWER_SETTINGS_OK ||
        comp_power_settings_store_mount(&remounted, &port) !=
            COMP_POWER_SETTINGS_OK ||
        !settings_equal(comp_power_settings_store_values(&remounted), &values)) {
        return fail("complete browser settings atomic round trip");
    }

    if (test_all_settings_round_trip(&flash, &port, &remounted) != 0) {
        return 1;
    }
    values.interaction_level = 3u;
    if (comp_power_settings_store_save_values(&remounted, &values) !=
        COMP_POWER_SETTINGS_INVALID_VALUE) {
        return fail("invalid browser setting rejected");
    }

    values.interaction_level = 2u;
    if (comp_power_settings_recording_max_seconds(&values) != 3600u ||
        comp_power_settings_silence_stop_blocks(&values) != 0u ||
        comp_power_settings_interaction_interval_ms(&values) != 480u ||
        comp_power_settings_quiet_hours_active(&values, 30u) ||
        comp_power_settings_display_hour(&values, 13u) != 1u ||
        !comp_power_settings_recording_entry_allowed(
            &values, false, true) ||
        comp_power_settings_recording_entry_allowed(
            &values, true, false)) {
        return fail("complete browser runtime policy");
    }
    values.silent_auto_stop = true;
    values.recorder_profile = 0u;
    values.quiet_hours = 0u;
    values.clock_24_hour = true;
    if (comp_power_settings_silence_stop_blocks(&values) != 500u ||
        !comp_power_settings_quiet_hours_active(&values, 30u) ||
        comp_power_settings_quiet_hours_active(&values, 720u) ||
        comp_power_settings_display_hour(&values, 13u) != 13u) {
        return fail("voice/quiet-hours/24-hour runtime policy");
    }

    /* A CRC-correct v2 record with the reserved time-zone code must not be
     * normalized into UTC+8.  Treat it as corrupt and retain the prior valid
     * atomic generation. */
    values = *comp_power_settings_store_values(&remounted);
    {
        uint32_t offset =
            (uint32_t)remounted.next_slot * COMP_POWER_SETTINGS_RECORD_BYTES;
        uint8_t *record = &flash.bytes[offset];
        memset(record, 0, COMP_POWER_SETTINGS_RECORD_BYTES);
        test_put_u32(&record[0], 0x31535750u);
        test_put_u32(&record[4], remounted.generation + 1u);
        record[8] = 2u;
        record[9] = 3u;
        test_put_u16(&record[10], 0x6000u);
        test_put_u32(&record[12], test_crc32(record, 12u));
        if (comp_power_settings_store_mount(&store, &port) !=
                COMP_POWER_SETTINGS_OK ||
            !settings_equal(comp_power_settings_store_values(&store),
                            &values) ||
            store.generation != remounted.generation) {
            return fail("reserved v2 encoding falls back to prior generation");
        }
    }

    /* A PWS1/version-1 record migrates in memory: legacy idle survives while
     * every newly introduced field receives its safe product default. */
    memset(flash.bytes, 0xFF, sizeof(flash.bytes));
    test_put_u32(&flash.bytes[0], 0x31535750u);
    test_put_u32(&flash.bytes[4], 7u);
    flash.bytes[8] = 1u;
    flash.bytes[9] = 5u;
    flash.bytes[10] = 0u;
    flash.bytes[11] = 0u;
    test_put_u32(&flash.bytes[12], test_crc32(flash.bytes, 12u));
    comp_power_settings_values_default(&values);
    values.idle_minutes = 5u;
    if (comp_power_settings_store_mount(&store, &port) !=
            COMP_POWER_SETTINGS_OK || store.generation != 7u ||
        !settings_equal(comp_power_settings_store_values(&store), &values)) {
        return fail("legacy v1 settings migration");
    }
    values.silent_auto_stop = false;
    if (comp_power_settings_store_save_values(&store, &values) !=
            COMP_POWER_SETTINGS_OK || flash.bytes[16u + 8u] != 2u ||
        comp_power_settings_store_mount(&remounted, &port) !=
            COMP_POWER_SETTINGS_OK ||
        !settings_equal(comp_power_settings_store_values(&remounted),
                        &values)) {
        return fail("legacy v1 persists as v2 after first change");
    }

    /* A completely consumed invalid sector is recycled once, then verified. */
    memset(flash.bytes, 0x00, sizeof(flash.bytes));
    flash.erase_count = 0u;
    if (comp_power_settings_store_mount(&store, &port) !=
            COMP_POWER_SETTINGS_OK ||
        store.next_slot != COMP_POWER_SETTINGS_SLOT_COUNT ||
        comp_power_settings_store_save(&store, 0u) !=
            COMP_POWER_SETTINGS_OK ||
        flash.erase_count != 1u ||
        comp_power_settings_store_mount(&remounted, &port) !=
            COMP_POWER_SETTINGS_OK ||
        comp_power_settings_store_idle_minutes(&remounted) != 0u) {
        return fail("full-sector recycle and disabled persistence");
    }
    return 0;
}

int main(void)
{
    comp_power_idle_settings_t settings;

    if (!comp_power_policy_self_test() || !comp_power_idle_settings_self_test()) {
        return fail("portable policy self-test");
    }

    comp_power_idle_settings_init(&settings);
    if (comp_power_idle_settings_minutes(&settings) !=
            COMP_POWER_IDLE_MINUTES_DEFAULT ||
        comp_power_idle_settings_timeout_ms(&settings) != 180000u) {
        return fail("three-minute default");
    }

    if (!comp_power_idle_settings_set_minutes(&settings, 5u) ||
        comp_power_idle_settings_timeout_ms(&settings) != 300000u) {
        return fail("five-minute selection");
    }

    if (comp_power_idle_settings_set_minutes(
            &settings, (uint8_t)(COMP_POWER_IDLE_MINUTES_MAX + 1u)) ||
        comp_power_idle_settings_minutes(&settings) != 5u) {
        return fail("invalid selection preserves setting");
    }

    if (!comp_power_idle_settings_set_minutes(
            &settings, COMP_POWER_IDLE_MINUTES_DISABLED) ||
        comp_power_idle_settings_timeout_ms(&settings) != 0u) {
        return fail("disabled selection");
    }

    if (test_idle_deadline_double_tap_interleave() != 0) {
        return 1;
    }

    if (test_power_settings_store() != 0) {
        return 1;
    }

    if (test_browser_policy_matrix() != 0) {
        return 1;
    }

    printf("PASS: power idle default=3m configurable=0..%um; "
           "deadline/double-tap interleave gated; settings all-field/boundary/"
           "v1-migration/CRC/torn/write-amplification and behavior matrix pass\n",
           (unsigned)COMP_POWER_IDLE_MINUTES_MAX);
    return 0;
}
