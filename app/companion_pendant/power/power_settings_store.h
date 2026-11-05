#ifndef COMPANION_POWER_SETTINGS_STORE_H
#define COMPANION_POWER_SETTINGS_STORE_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define COMP_POWER_SETTINGS_SECTOR_BYTES 4096u
#define COMP_POWER_SETTINGS_RECORD_BYTES 16u
#define COMP_POWER_SETTINGS_SLOT_COUNT \
    (COMP_POWER_SETTINGS_SECTOR_BYTES / COMP_POWER_SETTINGS_RECORD_BYTES)

typedef bool (*comp_power_settings_read_fn)(
    void *context, uint32_t offset, uint8_t *destination, size_t length);
typedef bool (*comp_power_settings_write_fn)(
    void *context, uint32_t offset, const uint8_t *source, size_t length);
typedef bool (*comp_power_settings_erase_fn)(void *context);

typedef struct {
    comp_power_settings_read_fn read;
    comp_power_settings_write_fn write;
    comp_power_settings_erase_fn erase;
    void *context;
} comp_power_settings_port_t;

/* Keep the complete browser policy in the existing 16-byte append-only
 * record.  The implementation packs the finite-choice fields into 15 bits;
 * this public form stays explicit so callers cannot depend on the wire bits. */
typedef struct {
    bool silent_auto_stop;
    bool auto_reconnect;
    bool clock_24_hour;
    bool gaze_follow;
    bool natural_blink;
    uint8_t idle_minutes;
    uint8_t recording_limit_minutes;
    uint8_t recorder_profile;
    uint8_t interaction_level;
    uint8_t quiet_hours;
    uint8_t recording_gesture;
    int16_t time_zone_offset_minutes;
} comp_power_settings_values_t;

typedef struct {
    comp_power_settings_port_t port;
    uint32_t generation;
    uint16_t next_slot;
    comp_power_settings_values_t values;
    bool mounted;
} comp_power_settings_store_t;

typedef enum {
    COMP_POWER_SETTINGS_OK = 0u,
    COMP_POWER_SETTINGS_BAD_ARGUMENT,
    COMP_POWER_SETTINGS_IO_ERROR,
    COMP_POWER_SETTINGS_INVALID_VALUE,
} comp_power_settings_result_t;

void comp_power_settings_store_init(comp_power_settings_store_t *store);
comp_power_settings_result_t comp_power_settings_store_mount(
    comp_power_settings_store_t *store,
    const comp_power_settings_port_t *port);
comp_power_settings_result_t comp_power_settings_store_save(
    comp_power_settings_store_t *store,
    uint8_t idle_minutes);
comp_power_settings_result_t comp_power_settings_store_save_values(
    comp_power_settings_store_t *store,
    const comp_power_settings_values_t *values);
void comp_power_settings_values_default(comp_power_settings_values_t *values);
bool comp_power_settings_values_valid(
    const comp_power_settings_values_t *values);
const comp_power_settings_values_t *comp_power_settings_store_values(
    const comp_power_settings_store_t *store);
uint8_t comp_power_settings_store_idle_minutes(
    const comp_power_settings_store_t *store);
uint16_t comp_power_settings_recording_max_seconds(
    const comp_power_settings_values_t *values);
uint16_t comp_power_settings_silence_stop_blocks(
    const comp_power_settings_values_t *values);
static inline bool comp_power_settings_silence_tracker_step(
    const comp_power_settings_values_t *values,
    bool voice_present,
    uint16_t *tracker)
{
    const uint16_t limit = comp_power_settings_silence_stop_blocks(values);
    uint16_t blocks;

    if (limit == 0u) {
        *tracker = 0u;
        return false;
    }
    if (voice_present) {
        *tracker = 0x8000u;
        return false;
    }
    if ((*tracker & 0x8000u) == 0u) return false;
    blocks = (uint16_t)((*tracker & 0x7FFFu) + 1u);
    *tracker = (uint16_t)(0x8000u | blocks);
    return blocks >= limit;
}
uint16_t comp_power_settings_interaction_interval_ms(
    const comp_power_settings_values_t *values);
bool comp_power_settings_quiet_hours_active(
    const comp_power_settings_values_t *values,
    uint16_t local_minute);
uint8_t comp_power_settings_display_hour(
    const comp_power_settings_values_t *values,
    uint8_t hour_24);
bool comp_power_settings_recording_entry_allowed(
    const comp_power_settings_values_t *values,
    bool corner_double_tap,
    bool edge_pull);

#ifdef __cplusplus
}
#endif

#endif /* COMPANION_POWER_SETTINGS_STORE_H */
