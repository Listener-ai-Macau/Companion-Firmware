#include "pet_behavior_user_data_stm32wba.h"

#include <string.h>

#define COMP_PET_BEHAVIOR_USER_DATA_MAGIC 0x43505544u /* CPUD */
#define COMP_PET_BEHAVIOR_USER_DATA_RECORD_VERSION 1u
#define COMP_PET_BEHAVIOR_USER_DATA_DEFAULT_COMMIT_MS 60000u

typedef struct {
    uint32_t magic;
    uint16_t record_version;
    uint16_t payload_size;
    uint32_t sequence;
    comp_pet_behavior_memory_t memory;
    uint32_t crc32;
} comp_pet_behavior_user_data_record_t;

static uint32_t crc32_update(uint32_t crc, const uint8_t *data, size_t length)
{
    size_t i;
    uint8_t bit;

    crc = ~crc;
    for (i = 0u; i < length; ++i) {
        crc ^= data[i];
        for (bit = 0u; bit < 8u; ++bit) {
            crc = (crc >> 1u) ^ (0xEDB88320u & (0u - (crc & 1u)));
        }
    }
    return ~crc;
}

static uint32_t record_crc32(const comp_pet_behavior_user_data_record_t *record)
{
    uint32_t crc = 0u;

    crc = crc32_update(crc, (const uint8_t *)&record->magic, sizeof(record->magic));
    crc = crc32_update(crc,
                       (const uint8_t *)&record->record_version,
                       sizeof(record->record_version));
    crc = crc32_update(crc,
                       (const uint8_t *)&record->payload_size,
                       sizeof(record->payload_size));
    crc = crc32_update(crc,
                       (const uint8_t *)&record->sequence,
                       sizeof(record->sequence));
    crc = crc32_update(crc,
                       (const uint8_t *)&record->memory,
                       sizeof(record->memory));
    return crc;
}

static bool target_is_valid(companion_epaper_panel_stm32wba_target_t target)
{
    return target == COMPANION_EPAPER_PANEL_STM32WBA_TARGET_WBA55 ||
           target == COMPANION_EPAPER_PANEL_STM32WBA_TARGET_WBA65;
}

static bool record_is_valid(const comp_pet_behavior_user_data_record_t *record)
{
    if (record == NULL ||
        record->magic != COMP_PET_BEHAVIOR_USER_DATA_MAGIC ||
        record->record_version != COMP_PET_BEHAVIOR_USER_DATA_RECORD_VERSION ||
        record->payload_size != sizeof(record->memory)) {
        return false;
    }
    return record->crc32 == record_crc32(record);
}

void comp_pet_behavior_user_data_stm32wba_init(
    comp_pet_behavior_user_data_stm32wba_t *adapter)
{
    if (adapter != NULL) {
        memset(adapter, 0, sizeof(*adapter));
    }
}

bool comp_pet_behavior_user_data_stm32wba_ready(
    const comp_pet_behavior_user_data_stm32wba_t *adapter)
{
    return adapter != NULL &&
           target_is_valid(adapter->config.target) &&
           adapter->config.logical_slot_count >=
               COMP_PET_BEHAVIOR_USER_DATA_STM32WBA_MIN_SLOTS &&
           adapter->config.read != NULL &&
           adapter->config.write != NULL &&
           adapter->config.privacy_erase != NULL;
}

bool comp_pet_behavior_user_data_stm32wba_bind(
    comp_pet_behavior_user_data_stm32wba_t *adapter,
    const comp_pet_behavior_user_data_stm32wba_config_t *config)
{
    if (adapter == NULL || config == NULL) {
        return false;
    }
    comp_pet_behavior_user_data_stm32wba_init(adapter);
    adapter->config = *config;
    if (adapter->config.min_commit_interval_ms == 0u) {
        adapter->config.min_commit_interval_ms =
            COMP_PET_BEHAVIOR_USER_DATA_DEFAULT_COMMIT_MS;
    }
    return comp_pet_behavior_user_data_stm32wba_ready(adapter);
}

bool comp_pet_behavior_user_data_stm32wba_load_latest(
    comp_pet_behavior_user_data_stm32wba_t *adapter,
    comp_pet_behavior_memory_t *out_memory)
{
    comp_pet_behavior_user_data_record_t record;
    comp_pet_behavior_user_data_record_t best;
    bool have_best = false;
    uint8_t slot;

    if (!comp_pet_behavior_user_data_stm32wba_ready(adapter) ||
        out_memory == NULL) {
        return false;
    }
    memset(&best, 0, sizeof(best));
    for (slot = 0u; slot < adapter->config.logical_slot_count; ++slot) {
        memset(&record, 0, sizeof(record));
        if (!adapter->config.read(adapter->config.context,
                                  slot,
                                  (uint8_t *)&record,
                                  sizeof(record))) {
            continue;
        }
        if (!record_is_valid(&record)) {
            continue;
        }
        if (!have_best || record.sequence > best.sequence) {
            best = record;
            adapter->active_slot = slot;
            have_best = true;
        }
    }
    if (!have_best) {
        adapter->has_active_record = false;
        return false;
    }
    *out_memory = best.memory;
    adapter->active_sequence = best.sequence;
    adapter->has_active_record = true;
    return true;
}

bool comp_pet_behavior_user_data_stm32wba_should_commit(
    const comp_pet_behavior_user_data_stm32wba_t *adapter,
    uint32_t now_ms,
    bool force)
{
    if (!comp_pet_behavior_user_data_stm32wba_ready(adapter)) {
        return false;
    }
    if (force || !adapter->has_active_record) {
        return true;
    }
    return (uint32_t)(now_ms - adapter->last_commit_ms) >=
           adapter->config.min_commit_interval_ms;
}

bool comp_pet_behavior_user_data_stm32wba_save(
    comp_pet_behavior_user_data_stm32wba_t *adapter,
    const comp_pet_behavior_memory_t *memory,
    uint32_t now_ms,
    bool force)
{
    comp_pet_behavior_user_data_record_t record;
    uint8_t next_slot;

    if (!comp_pet_behavior_user_data_stm32wba_ready(adapter) ||
        memory == NULL ||
        !comp_pet_behavior_user_data_stm32wba_should_commit(adapter, now_ms, force)) {
        return false;
    }
    memset(&record, 0, sizeof(record));
    record.magic = COMP_PET_BEHAVIOR_USER_DATA_MAGIC;
    record.record_version = COMP_PET_BEHAVIOR_USER_DATA_RECORD_VERSION;
    record.payload_size = sizeof(record.memory);
    record.sequence = adapter->has_active_record ? adapter->active_sequence + 1u : 1u;
    record.memory = *memory;
    record.crc32 = record_crc32(&record);

    next_slot = adapter->has_active_record
                    ? (uint8_t)((adapter->active_slot + 1u) %
                                adapter->config.logical_slot_count)
                    : 0u;
    if (!adapter->config.write(adapter->config.context,
                               next_slot,
                               (const uint8_t *)&record,
                               sizeof(record))) {
        return false;
    }
    adapter->active_slot = next_slot;
    adapter->active_sequence = record.sequence;
    adapter->last_commit_ms = now_ms;
    adapter->has_active_record = true;
    return true;
}

bool comp_pet_behavior_user_data_stm32wba_privacy_erase(
    comp_pet_behavior_user_data_stm32wba_t *adapter)
{
    if (!comp_pet_behavior_user_data_stm32wba_ready(adapter)) {
        return false;
    }
    if (!adapter->config.privacy_erase(adapter->config.context)) {
        return false;
    }
    adapter->active_slot = 0u;
    adapter->active_sequence = 0u;
    adapter->last_commit_ms = 0u;
    adapter->has_active_record = false;
    return true;
}
