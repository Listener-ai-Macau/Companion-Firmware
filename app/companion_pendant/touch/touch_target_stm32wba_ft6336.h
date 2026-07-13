#ifndef COMPANION_TOUCH_TARGET_STM32WBA_FT6336_H
#define COMPANION_TOUCH_TARGET_STM32WBA_FT6336_H

#include "ft6336.h"

#include <stdbool.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef enum {
    COMPANION_TOUCH_FT6336_STM32WBA_TARGET_WBA55 = 0,
    COMPANION_TOUCH_FT6336_STM32WBA_TARGET_WBA65 = 1,
} companion_touch_ft6336_stm32wba_target_t;

typedef enum {
    COMPANION_TOUCH_FT6336_STM32WBA_OK = 0,
    COMPANION_TOUCH_FT6336_STM32WBA_NOT_DETECTED,
    COMPANION_TOUCH_FT6336_STM32WBA_I2C_ERROR,
    COMPANION_TOUCH_FT6336_STM32WBA_BAD_REPORT,
    COMPANION_TOUCH_FT6336_STM32WBA_BAD_ARGUMENT,
} companion_touch_ft6336_stm32wba_result_t;

typedef bool (*companion_touch_ft6336_stm32wba_probe_fn_t)(
    void *context,
    uint8_t address_7bit);

typedef bool (*companion_touch_ft6336_stm32wba_read_fn_t)(
    void *context,
    uint8_t address_7bit,
    uint8_t register_address,
    uint8_t *data,
    uint16_t length);

typedef bool (*companion_touch_ft6336_stm32wba_write_fn_t)(
    void *context,
    uint8_t address_7bit,
    uint8_t register_address,
    const uint8_t *data,
    uint16_t length);

typedef struct {
    companion_touch_ft6336_stm32wba_target_t target;
    companion_touch_ft6336_stm32wba_probe_fn_t probe;
    companion_touch_ft6336_stm32wba_read_fn_t read;
    companion_touch_ft6336_stm32wba_write_fn_t write;
    void *context;
} companion_touch_ft6336_stm32wba_config_t;

typedef struct {
    companion_touch_ft6336_stm32wba_config_t config;
    comp_ft6336_identity_t identity;
    uint8_t address_7bit;
    bool detected;
    bool identity_attempted;
    bool identity_valid;
    bool interrupt_mode_attempted;
    bool interrupt_mode_valid;
    uint8_t interrupt_mode;
    bool runtime_tuning_attempted;
    bool runtime_tuning_valid;
    uint8_t touch_threshold;
    uint8_t active_period;
    uint8_t monitor_period;
    uint32_t probe_count;
    uint32_t identity_read_count;
    uint32_t interrupt_config_count;
    uint32_t interrupt_config_error_count;
    uint32_t runtime_tuning_config_count;
    uint32_t runtime_tuning_error_count;
    uint32_t read_count;
    uint32_t error_count;
} companion_touch_ft6336_stm32wba_t;

const char *companion_touch_ft6336_stm32wba_target_name(
    companion_touch_ft6336_stm32wba_target_t target);

void companion_touch_ft6336_stm32wba_init(
    companion_touch_ft6336_stm32wba_t *touch,
    const companion_touch_ft6336_stm32wba_config_t *config);

bool companion_touch_ft6336_stm32wba_ready(
    const companion_touch_ft6336_stm32wba_t *touch);

bool companion_touch_ft6336_stm32wba_probe(
    companion_touch_ft6336_stm32wba_t *touch);

bool companion_touch_ft6336_stm32wba_read_identity(
    companion_touch_ft6336_stm32wba_t *touch);

bool companion_touch_ft6336_stm32wba_configure_interrupt(
    companion_touch_ft6336_stm32wba_t *touch);

bool companion_touch_ft6336_stm32wba_configure_runtime_tuning(
    companion_touch_ft6336_stm32wba_t *touch);

companion_touch_ft6336_stm32wba_result_t companion_touch_ft6336_stm32wba_poll(
    companion_touch_ft6336_stm32wba_t *touch,
    comp_ft6336_touch_sample_t *sample);

const char *companion_touch_ft6336_stm32wba_result_name(
    companion_touch_ft6336_stm32wba_result_t result);

#ifdef __cplusplus
}
#endif

#endif /* COMPANION_TOUCH_TARGET_STM32WBA_FT6336_H */
