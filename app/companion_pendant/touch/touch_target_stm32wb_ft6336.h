#ifndef COMPANION_TOUCH_TARGET_STM32WB_FT6336_H
#define COMPANION_TOUCH_TARGET_STM32WB_FT6336_H

#include "ft6336.h"

#include "stm32wbxx_hal.h"

#include <stdbool.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef enum {
    COMPANION_TOUCH_FT6336_STM32WB_OK = 0,
    COMPANION_TOUCH_FT6336_STM32WB_NOT_DETECTED,
    COMPANION_TOUCH_FT6336_STM32WB_I2C_ERROR,
    COMPANION_TOUCH_FT6336_STM32WB_BAD_REPORT,
    COMPANION_TOUCH_FT6336_STM32WB_BAD_ARGUMENT,
} companion_touch_ft6336_stm32wb_result_t;

typedef struct {
    I2C_HandleTypeDef *i2c;
    uint16_t address_8bit;
    comp_ft6336_identity_t identity;
    bool detected;
    bool identity_attempted;
    bool identity_valid;
    bool operating_mode_attempted;
    bool operating_mode_valid;
    uint8_t operating_mode;
    bool power_mode_valid;
    uint8_t power_mode;
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
    uint32_t operating_mode_config_count;
    uint32_t operating_mode_config_error_count;
    uint32_t interrupt_config_count;
    uint32_t interrupt_config_error_count;
    uint32_t runtime_tuning_config_count;
    uint32_t runtime_tuning_error_count;
    uint32_t read_count;
    uint32_t error_count;
} companion_touch_ft6336_stm32wb_t;

void companion_touch_ft6336_stm32wb_init(companion_touch_ft6336_stm32wb_t *touch,
                                         I2C_HandleTypeDef *i2c);
bool companion_touch_ft6336_stm32wb_probe(companion_touch_ft6336_stm32wb_t *touch);
bool companion_touch_ft6336_stm32wb_read_identity(
    companion_touch_ft6336_stm32wb_t *touch);
bool companion_touch_ft6336_stm32wb_configure_working_mode(
    companion_touch_ft6336_stm32wb_t *touch);
bool companion_touch_ft6336_stm32wb_configure_interrupt(
    companion_touch_ft6336_stm32wb_t *touch);
bool companion_touch_ft6336_stm32wb_configure_runtime_tuning(
    companion_touch_ft6336_stm32wb_t *touch);
companion_touch_ft6336_stm32wb_result_t companion_touch_ft6336_stm32wb_poll(
    companion_touch_ft6336_stm32wb_t *touch,
    comp_ft6336_touch_sample_t *sample);
const char *companion_touch_ft6336_stm32wb_result_name(
    companion_touch_ft6336_stm32wb_result_t result);

#ifdef __cplusplus
}
#endif

#endif /* COMPANION_TOUCH_TARGET_STM32WB_FT6336_H */
