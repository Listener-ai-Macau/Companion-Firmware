#include "power_settings_store.h"

#include <string.h>

#define COMP_POWER_SETTINGS_MAGIC 0x31535750u /* PWS1 */
#define COMP_POWER_SETTINGS_VERSION 2u
#define COMP_POWER_SETTINGS_VERSION_LEGACY 1u
#define COMP_POWER_SETTINGS_DEFAULT_MINUTES 3u

enum {
    SETTINGS_SILENT_AUTO_STOP = 1u << 0,
    SETTINGS_AUTO_RECONNECT = 1u << 1,
    SETTINGS_CLOCK_24_HOUR = 1u << 2,
    SETTINGS_GAZE_FOLLOW = 1u << 3,
    SETTINGS_NATURAL_BLINK = 1u << 4,
    SETTINGS_RECORDING_LIMIT_SHIFT = 5u,
    SETTINGS_RECORDER_PROFILE_SHIFT = 7u,
    SETTINGS_INTERACTION_LEVEL_SHIFT = 8u,
    SETTINGS_QUIET_HOURS_SHIFT = 10u,
    SETTINGS_RECORDING_GESTURE_SHIFT = 12u,
    SETTINGS_TIME_ZONE_SHIFT = 13u,
};

static uint32_t get_u32(const uint8_t *bytes)
{
    return (uint32_t)bytes[0] |
           ((uint32_t)bytes[1] << 8u) |
           ((uint32_t)bytes[2] << 16u) |
           ((uint32_t)bytes[3] << 24u);
}

static void put_u32(uint8_t *bytes, uint32_t value)
{
    bytes[0] = (uint8_t)value;
    bytes[1] = (uint8_t)(value >> 8u);
    bytes[2] = (uint8_t)(value >> 16u);
    bytes[3] = (uint8_t)(value >> 24u);
}

static uint16_t get_u16(const uint8_t *bytes)
{
    return (uint16_t)((uint16_t)bytes[0] | ((uint16_t)bytes[1] << 8u));
}

static void put_u16(uint8_t *bytes, uint16_t value)
{
    bytes[0] = (uint8_t)value;
    bytes[1] = (uint8_t)(value >> 8u);
}

static uint32_t record_crc32(const uint8_t *data, size_t length)
{
    uint32_t crc = 0u;
    size_t index;
    uint8_t bit;

    crc = ~crc;
    for (index = 0u; index < length; ++index) {
        crc ^= data[index];
        for (bit = 0u; bit < 8u; ++bit) {
            crc = (crc >> 1u) ^ (0xEDB88320u & (0u - (crc & 1u)));
        }
    }
    return ~crc;
}

static bool supported_minutes(uint8_t minutes)
{
    return minutes == 0u || minutes == 1u || minutes == 3u || minutes == 5u;
}

void comp_power_settings_values_default(comp_power_settings_values_t *values)
{
    if (values == NULL) {
        return;
    }
    *values = (comp_power_settings_values_t){
        .silent_auto_stop = true,
        .auto_reconnect = true,
        .clock_24_hour = true,
        .gaze_follow = true,
        .natural_blink = true,
        .idle_minutes = COMP_POWER_SETTINGS_DEFAULT_MINUTES,
        .recording_limit_minutes = 0u, /* No time limit by default; storage still bounds recording. */
        .recorder_profile = 0u,
        .interaction_level = 1u,
        .quiet_hours = 0u,
        .recording_gesture = 0u,
        .time_zone_offset_minutes = 480,
    };
}

bool comp_power_settings_values_valid(
    const comp_power_settings_values_t *values)
{
    return values != NULL && supported_minutes(values->idle_minutes) &&
           (values->recording_limit_minutes == 0u ||
            values->recording_limit_minutes == 15u ||
            values->recording_limit_minutes == 30u ||
            values->recording_limit_minutes == 60u) &&
           values->recorder_profile <= 1u &&
           values->interaction_level <= 2u && values->quiet_hours <= 2u &&
           values->recording_gesture <= 1u &&
           (values->time_zone_offset_minutes == 480 ||
            values->time_zone_offset_minutes == 0 ||
            values->time_zone_offset_minutes == -300);
}

static uint8_t recording_limit_index(uint8_t minutes)
{
    return minutes == 15u ? 0u : minutes == 30u ? 1u :
           minutes == 60u ? 2u : 3u;
}

static uint8_t time_zone_index(int16_t minutes)
{
    return minutes == 480 ? 0u : minutes == 0 ? 1u : 2u;
}

static uint16_t pack_values(const comp_power_settings_values_t *values)
{
    return (uint16_t)((values->silent_auto_stop ? SETTINGS_SILENT_AUTO_STOP : 0u) |
        (values->auto_reconnect ? SETTINGS_AUTO_RECONNECT : 0u) |
        (values->clock_24_hour ? SETTINGS_CLOCK_24_HOUR : 0u) |
        (values->gaze_follow ? SETTINGS_GAZE_FOLLOW : 0u) |
        (values->natural_blink ? SETTINGS_NATURAL_BLINK : 0u) |
        ((uint16_t)recording_limit_index(values->recording_limit_minutes) <<
         SETTINGS_RECORDING_LIMIT_SHIFT) |
        ((uint16_t)values->recorder_profile << SETTINGS_RECORDER_PROFILE_SHIFT) |
        ((uint16_t)values->interaction_level << SETTINGS_INTERACTION_LEVEL_SHIFT) |
        ((uint16_t)values->quiet_hours << SETTINGS_QUIET_HOURS_SHIFT) |
        ((uint16_t)values->recording_gesture << SETTINGS_RECORDING_GESTURE_SHIFT) |
        ((uint16_t)time_zone_index(values->time_zone_offset_minutes) <<
         SETTINGS_TIME_ZONE_SHIFT));
}

static void unpack_values(uint8_t idle_minutes,
                          uint16_t packed,
                          comp_power_settings_values_t *values)
{
    static const uint8_t limits[4] = {15u, 30u, 60u, 0u};
    static const int16_t time_zones[3] = {480, 0, -300};
    uint8_t time_zone = (uint8_t)((packed >> SETTINGS_TIME_ZONE_SHIFT) & 3u);

    comp_power_settings_values_default(values);
    values->silent_auto_stop = (packed & SETTINGS_SILENT_AUTO_STOP) != 0u;
    values->auto_reconnect = (packed & SETTINGS_AUTO_RECONNECT) != 0u;
    values->clock_24_hour = (packed & SETTINGS_CLOCK_24_HOUR) != 0u;
    values->gaze_follow = (packed & SETTINGS_GAZE_FOLLOW) != 0u;
    values->natural_blink = (packed & SETTINGS_NATURAL_BLINK) != 0u;
    values->idle_minutes = idle_minutes;
    values->recording_limit_minutes =
        limits[(packed >> SETTINGS_RECORDING_LIMIT_SHIFT) & 3u];
    values->recorder_profile =
        (uint8_t)((packed >> SETTINGS_RECORDER_PROFILE_SHIFT) & 1u);
    values->interaction_level =
        (uint8_t)((packed >> SETTINGS_INTERACTION_LEVEL_SHIFT) & 3u);
    values->quiet_hours =
        (uint8_t)((packed >> SETTINGS_QUIET_HOURS_SHIFT) & 3u);
    values->recording_gesture =
        (uint8_t)((packed >> SETTINGS_RECORDING_GESTURE_SHIFT) & 1u);
    values->time_zone_offset_minutes = time_zones[time_zone];
}

static bool erased_record(const uint8_t record[COMP_POWER_SETTINGS_RECORD_BYTES])
{
    uint8_t index;
    for (index = 0u; index < COMP_POWER_SETTINGS_RECORD_BYTES; ++index) {
        if (record[index] != 0xFFu) {
            return false;
        }
    }
    return true;
}

static bool valid_record(const uint8_t record[COMP_POWER_SETTINGS_RECORD_BYTES])
{
    comp_power_settings_values_t values;

    if (get_u32(&record[0]) != COMP_POWER_SETTINGS_MAGIC ||
        !supported_minutes(record[9]) ||
        get_u32(&record[12]) != record_crc32(record, 12u)) {
        return false;
    }
    if (record[8] == COMP_POWER_SETTINGS_VERSION_LEGACY) {
        return true;
    }
    if (record[8] != COMP_POWER_SETTINGS_VERSION ||
        (get_u16(&record[10]) & 0x8000u) != 0u ||
        (get_u16(&record[10]) & 0x6000u) == 0x6000u) {
        return false;
    }
    unpack_values(record[9], get_u16(&record[10]), &values);
    return comp_power_settings_values_valid(&values);
}

static void encode_record(uint8_t record[COMP_POWER_SETTINGS_RECORD_BYTES],
                          uint32_t generation,
                          const comp_power_settings_values_t *values)
{
    memset(record, 0, COMP_POWER_SETTINGS_RECORD_BYTES);
    put_u32(&record[0], COMP_POWER_SETTINGS_MAGIC);
    put_u32(&record[4], generation);
    record[8] = COMP_POWER_SETTINGS_VERSION;
    record[9] = values->idle_minutes;
    put_u16(&record[10], pack_values(values));
    put_u32(&record[12], record_crc32(record, 12u));
}

void comp_power_settings_store_init(comp_power_settings_store_t *store)
{
    if (store != NULL) {
        memset(store, 0, sizeof(*store));
        comp_power_settings_values_default(&store->values);
    }
}

comp_power_settings_result_t comp_power_settings_store_mount(
    comp_power_settings_store_t *store,
    const comp_power_settings_port_t *port)
{
    uint8_t record[COMP_POWER_SETTINGS_RECORD_BYTES];
    uint16_t slot;
    bool have_valid = false;

    if (store == NULL || port == NULL || port->read == NULL ||
        port->write == NULL || port->erase == NULL) {
        return COMP_POWER_SETTINGS_BAD_ARGUMENT;
    }
    comp_power_settings_store_init(store);
    store->port = *port;
    store->next_slot = COMP_POWER_SETTINGS_SLOT_COUNT;
    for (slot = 0u; slot < COMP_POWER_SETTINGS_SLOT_COUNT; ++slot) {
        if (!store->port.read(store->port.context,
                              (uint32_t)slot * COMP_POWER_SETTINGS_RECORD_BYTES,
                              record,
                              sizeof(record))) {
            return COMP_POWER_SETTINGS_IO_ERROR;
        }
        if (erased_record(record)) {
            store->next_slot = slot;
            break;
        }
        if (valid_record(record) &&
            (!have_valid || (int32_t)(get_u32(&record[4]) -
                                      store->generation) > 0)) {
            store->generation = get_u32(&record[4]);
            if (record[8] == COMP_POWER_SETTINGS_VERSION_LEGACY) {
                comp_power_settings_values_default(&store->values);
                store->values.idle_minutes = record[9];
            } else {
                unpack_values(record[9], get_u16(&record[10]),
                              &store->values);
            }
            have_valid = true;
        }
    }
    store->mounted = true;
    return COMP_POWER_SETTINGS_OK;
}

comp_power_settings_result_t comp_power_settings_store_save(
    comp_power_settings_store_t *store,
    uint8_t idle_minutes)
{
    comp_power_settings_values_t values;

    if (store == NULL || !store->mounted) {
        return COMP_POWER_SETTINGS_BAD_ARGUMENT;
    }
    values = store->values;
    values.idle_minutes = idle_minutes;
    return comp_power_settings_store_save_values(store, &values);
}

comp_power_settings_result_t comp_power_settings_store_save_values(
    comp_power_settings_store_t *store,
    const comp_power_settings_values_t *values)
{
    uint8_t record[COMP_POWER_SETTINGS_RECORD_BYTES];
    uint8_t verify[COMP_POWER_SETTINGS_RECORD_BYTES];
    uint32_t next_generation;
    uint32_t offset;

    if (store == NULL || !store->mounted || values == NULL) {
        return COMP_POWER_SETTINGS_BAD_ARGUMENT;
    }
    if (!comp_power_settings_values_valid(values)) {
        return COMP_POWER_SETTINGS_INVALID_VALUE;
    }
    if (values->idle_minutes == store->values.idle_minutes &&
        pack_values(values) == pack_values(&store->values)) {
        return COMP_POWER_SETTINGS_OK;
    }
    next_generation = store->generation + 1u;
    if (store->next_slot >= COMP_POWER_SETTINGS_SLOT_COUNT) {
        if (!store->port.erase(store->port.context)) {
            return COMP_POWER_SETTINGS_IO_ERROR;
        }
        store->next_slot = 0u;
    }
    offset = (uint32_t)store->next_slot * COMP_POWER_SETTINGS_RECORD_BYTES;
    encode_record(record, next_generation, values);
    if (!store->port.write(store->port.context, offset, record, sizeof(record)) ||
        !store->port.read(store->port.context, offset, verify, sizeof(verify)) ||
        memcmp(record, verify, sizeof(record)) != 0 || !valid_record(verify)) {
        return COMP_POWER_SETTINGS_IO_ERROR;
    }
    store->generation = next_generation;
    store->values = *values;
    store->next_slot++;
    return COMP_POWER_SETTINGS_OK;
}

const comp_power_settings_values_t *comp_power_settings_store_values(
    const comp_power_settings_store_t *store)
{
    return store == NULL || !store->mounted ? NULL : &store->values;
}

uint8_t comp_power_settings_store_idle_minutes(
    const comp_power_settings_store_t *store)
{
    return store == NULL || !store->mounted
               ? COMP_POWER_SETTINGS_DEFAULT_MINUTES
               : store->values.idle_minutes;
}

uint16_t comp_power_settings_recording_max_seconds(
    const comp_power_settings_values_t *values)
{
    if (!comp_power_settings_values_valid(values)) {
        return 180u;
    }
    /* "Unlimited" is bounded by the 14 MiB product recording region. */
    return values->recording_limit_minutes == 0u
               ? 2700u
               : (uint16_t)((uint16_t)values->recording_limit_minutes * 60u);
}

uint16_t comp_power_settings_silence_stop_blocks(
    const comp_power_settings_values_t *values)
{
    if (!comp_power_settings_values_valid(values) ||
        !values->silent_auto_stop) {
        return 0u;
    }
    /* Capture produces one 10 ms block. Voice ends promptly; a meeting keeps
     * longer pauses so participants can think without splitting the clip. */
    return values->recorder_profile == 0u ? 500u : 1500u;
}

uint16_t comp_power_settings_interaction_interval_ms(
    const comp_power_settings_values_t *values)
{
    static const uint16_t intervals[3] = {1920u, 960u, 480u};
    return !comp_power_settings_values_valid(values)
               ? intervals[1]
               : intervals[values->interaction_level];
}

bool comp_power_settings_quiet_hours_active(
    const comp_power_settings_values_t *values,
    uint16_t local_minute)
{
    uint16_t start;
    uint16_t end;

    if (!comp_power_settings_values_valid(values) || local_minute >= 1440u ||
        values->quiet_hours == 2u) {
        return false;
    }
    start = values->quiet_hours == 0u ? 1380u : 1320u;
    end = values->quiet_hours == 0u ? 420u : 480u;
    return local_minute >= start || local_minute < end;
}

uint8_t comp_power_settings_display_hour(
    const comp_power_settings_values_t *values,
    uint8_t hour_24)
{
    if (hour_24 > 23u || !comp_power_settings_values_valid(values) ||
        values->clock_24_hour) {
        return hour_24;
    }
    hour_24 = (uint8_t)(hour_24 % 12u);
    return hour_24 == 0u ? 12u : hour_24;
}

bool comp_power_settings_recording_entry_allowed(
    const comp_power_settings_values_t *values,
    bool corner_double_tap,
    bool edge_pull)
{
    return comp_power_settings_values_valid(values) &&
           (values->recording_gesture == 0u ? corner_double_tap : edge_pull);
}
