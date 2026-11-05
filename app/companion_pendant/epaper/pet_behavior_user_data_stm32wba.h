#ifndef COMPANION_EPAPER_PET_BEHAVIOR_USER_DATA_STM32WBA_H
#define COMPANION_EPAPER_PET_BEHAVIOR_USER_DATA_STM32WBA_H

#include "panel_target_stm32wba.h"
#include "pet_behavior.h"

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define COMP_PET_BEHAVIOR_USER_DATA_STM32WBA_MIN_SLOTS 2u

typedef bool (*comp_pet_behavior_user_data_stm32wba_read_fn_t)(
    void *context,
    uint8_t logical_slot,
    uint8_t *destination,
    size_t length);

typedef bool (*comp_pet_behavior_user_data_stm32wba_write_fn_t)(
    void *context,
    uint8_t logical_slot,
    const uint8_t *source,
    size_t length);

typedef bool (*comp_pet_behavior_user_data_stm32wba_erase_fn_t)(
    void *context);

typedef struct {
    companion_epaper_panel_stm32wba_target_t target;
    uint8_t logical_slot_count;
    uint32_t min_commit_interval_ms;
    comp_pet_behavior_user_data_stm32wba_read_fn_t read;
    comp_pet_behavior_user_data_stm32wba_write_fn_t write;
    comp_pet_behavior_user_data_stm32wba_erase_fn_t privacy_erase;
    void *context;
} comp_pet_behavior_user_data_stm32wba_config_t;

typedef struct {
    comp_pet_behavior_user_data_stm32wba_config_t config;
    uint8_t active_slot;
    uint32_t active_sequence;
    uint32_t last_commit_ms;
    bool has_active_record;
} comp_pet_behavior_user_data_stm32wba_t;

void comp_pet_behavior_user_data_stm32wba_init(
    comp_pet_behavior_user_data_stm32wba_t *adapter);

bool comp_pet_behavior_user_data_stm32wba_bind(
    comp_pet_behavior_user_data_stm32wba_t *adapter,
    const comp_pet_behavior_user_data_stm32wba_config_t *config);

bool comp_pet_behavior_user_data_stm32wba_ready(
    const comp_pet_behavior_user_data_stm32wba_t *adapter);

bool comp_pet_behavior_user_data_stm32wba_load_latest(
    comp_pet_behavior_user_data_stm32wba_t *adapter,
    comp_pet_behavior_memory_t *out_memory);

bool comp_pet_behavior_user_data_stm32wba_should_commit(
    const comp_pet_behavior_user_data_stm32wba_t *adapter,
    uint32_t now_ms,
    bool force);

bool comp_pet_behavior_user_data_stm32wba_save(
    comp_pet_behavior_user_data_stm32wba_t *adapter,
    const comp_pet_behavior_memory_t *memory,
    uint32_t now_ms,
    bool force);

bool comp_pet_behavior_user_data_stm32wba_privacy_erase(
    comp_pet_behavior_user_data_stm32wba_t *adapter);

#ifdef __cplusplus
}
#endif

#endif /* COMPANION_EPAPER_PET_BEHAVIOR_USER_DATA_STM32WBA_H */
