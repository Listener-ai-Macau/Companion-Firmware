#include "touch_target_stm32wb_ft6336.h"

#define COMPANION_TOUCH_FT6336_I2C_TRIALS 2u
#define COMPANION_TOUCH_FT6336_I2C_TIMEOUT_MS 20u

void companion_touch_ft6336_stm32wb_init(companion_touch_ft6336_stm32wb_t *touch,
                                         I2C_HandleTypeDef *i2c)
{
    if (touch == NULL) {
        return;
    }

    *touch = (companion_touch_ft6336_stm32wb_t){0};
    touch->i2c = i2c;
    touch->address_8bit = (uint16_t)(COMP_FT6336_I2C_ADDRESS_7BIT << 1);
    if (companion_touch_ft6336_stm32wb_probe(touch)) {
        (void)companion_touch_ft6336_stm32wb_read_identity(touch);
        (void)companion_touch_ft6336_stm32wb_configure_interrupt(touch);
        (void)companion_touch_ft6336_stm32wb_configure_runtime_tuning(touch);
    }
}

bool companion_touch_ft6336_stm32wb_probe(companion_touch_ft6336_stm32wb_t *touch)
{
    if (touch == NULL || touch->i2c == NULL) {
        return false;
    }

    touch->probe_count++;
    touch->detected = HAL_I2C_IsDeviceReady(touch->i2c,
                                            touch->address_8bit,
                                            COMPANION_TOUCH_FT6336_I2C_TRIALS,
                                            COMPANION_TOUCH_FT6336_I2C_TIMEOUT_MS) == HAL_OK;
    return touch->detected;
}

bool companion_touch_ft6336_stm32wb_read_identity(
    companion_touch_ft6336_stm32wb_t *touch)
{
    uint8_t registers[COMP_FT6336_IDENTITY_BYTES];

    if (touch == NULL || touch->i2c == NULL || !touch->detected) {
        return false;
    }
    touch->identity_attempted = true;
    touch->identity_read_count++;
    if (HAL_I2C_Mem_Read(touch->i2c,
                         touch->address_8bit,
                         COMP_FT6336_IDENTITY_REGISTER,
                         I2C_MEMADD_SIZE_8BIT,
                         registers,
                         sizeof(registers),
                         COMPANION_TOUCH_FT6336_I2C_TIMEOUT_MS) != HAL_OK) {
        touch->error_count++;
        touch->identity_valid = false;
        return false;
    }
    touch->identity = (comp_ft6336_identity_t){
        .cipher = registers[0],
        .firmware_id = registers[3],
        .chip_id = registers[5],
    };
    touch->identity_valid = true;
    return true;
}

bool companion_touch_ft6336_stm32wb_configure_interrupt(
    companion_touch_ft6336_stm32wb_t *touch)
{
    uint8_t requested = COMP_FT6336_G_MODE_TRIGGER;
    uint8_t actual = UINT8_MAX;

    if (touch == NULL || touch->i2c == NULL || !touch->detected) {
        return false;
    }
    touch->interrupt_mode_attempted = true;
    touch->interrupt_config_count++;
    if (HAL_I2C_Mem_Write(touch->i2c,
                          touch->address_8bit,
                          COMP_FT6336_G_MODE_REGISTER,
                          I2C_MEMADD_SIZE_8BIT,
                          &requested,
                          sizeof(requested),
                          COMPANION_TOUCH_FT6336_I2C_TIMEOUT_MS) != HAL_OK ||
        HAL_I2C_Mem_Read(touch->i2c,
                         touch->address_8bit,
                         COMP_FT6336_G_MODE_REGISTER,
                         I2C_MEMADD_SIZE_8BIT,
                         &actual,
                         sizeof(actual),
                         COMPANION_TOUCH_FT6336_I2C_TIMEOUT_MS) != HAL_OK) {
        touch->interrupt_config_error_count++;
        touch->interrupt_mode_valid = false;
        return false;
    }
    touch->interrupt_mode = actual;
    touch->interrupt_mode_valid = actual == COMP_FT6336_G_MODE_TRIGGER;
    if (!touch->interrupt_mode_valid) {
        touch->interrupt_config_error_count++;
    }
    return touch->interrupt_mode_valid;
}

bool companion_touch_ft6336_stm32wb_configure_runtime_tuning(
    companion_touch_ft6336_stm32wb_t *touch)
{
    static const uint8_t registers[] = {
        COMP_FT6336_TOUCH_THRESHOLD_REGISTER,
        COMP_FT6336_PERIOD_ACTIVE_REGISTER,
        COMP_FT6336_PERIOD_MONITOR_REGISTER,
    };
    static uint8_t requested[] = {
        COMP_FT6336_COMPANION_TOUCH_THRESHOLD,
        COMP_FT6336_COMPANION_ACTIVE_PERIOD,
        COMP_FT6336_COMPANION_MONITOR_PERIOD,
    };
    uint8_t actual[sizeof(requested)];

    if (touch == NULL || touch->i2c == NULL || !touch->detected) {
        return false;
    }
    touch->runtime_tuning_attempted = true;
    touch->runtime_tuning_config_count++;
    for (size_t index = 0u; index < sizeof(requested); ++index) {
        if (HAL_I2C_Mem_Write(touch->i2c,
                              touch->address_8bit,
                              registers[index],
                              I2C_MEMADD_SIZE_8BIT,
                              &requested[index],
                              1u,
                              COMPANION_TOUCH_FT6336_I2C_TIMEOUT_MS) != HAL_OK ||
            HAL_I2C_Mem_Read(touch->i2c,
                             touch->address_8bit,
                             registers[index],
                             I2C_MEMADD_SIZE_8BIT,
                             &actual[index],
                             1u,
                             COMPANION_TOUCH_FT6336_I2C_TIMEOUT_MS) != HAL_OK) {
            touch->runtime_tuning_error_count++;
            touch->runtime_tuning_valid = false;
            return false;
        }
    }
    touch->touch_threshold = actual[0];
    touch->active_period = actual[1];
    touch->monitor_period = actual[2];
    touch->runtime_tuning_valid =
        actual[0] == requested[0] && actual[1] == requested[1] &&
        actual[2] == requested[2];
    if (!touch->runtime_tuning_valid) {
        touch->runtime_tuning_error_count++;
    }
    return touch->runtime_tuning_valid;
}

companion_touch_ft6336_stm32wb_result_t companion_touch_ft6336_stm32wb_poll(
    companion_touch_ft6336_stm32wb_t *touch,
    comp_ft6336_touch_sample_t *sample)
{
    uint8_t report[COMP_FT6336_TOUCH_REPORT_BYTES];

    if (touch == NULL || sample == NULL || touch->i2c == NULL) {
        return COMPANION_TOUCH_FT6336_STM32WB_BAD_ARGUMENT;
    }
    if (!touch->detected && !companion_touch_ft6336_stm32wb_probe(touch)) {
        return COMPANION_TOUCH_FT6336_STM32WB_NOT_DETECTED;
    }
    if (!touch->identity_valid && !touch->identity_attempted) {
        (void)companion_touch_ft6336_stm32wb_read_identity(touch);
    }
    if (!touch->interrupt_mode_attempted) {
        (void)companion_touch_ft6336_stm32wb_configure_interrupt(touch);
    }
    if (!touch->runtime_tuning_attempted) {
        (void)companion_touch_ft6336_stm32wb_configure_runtime_tuning(touch);
    }

    if (HAL_I2C_Mem_Read(touch->i2c,
                         touch->address_8bit,
                         COMP_FT6336_TOUCH_REPORT_REGISTER,
                         I2C_MEMADD_SIZE_8BIT,
                         report,
                         sizeof(report),
                         COMPANION_TOUCH_FT6336_I2C_TIMEOUT_MS) != HAL_OK) {
        touch->error_count++;
        touch->detected = false;
        touch->identity_attempted = false;
        touch->identity_valid = false;
        touch->interrupt_mode_attempted = false;
        touch->interrupt_mode_valid = false;
        touch->runtime_tuning_attempted = false;
        touch->runtime_tuning_valid = false;
        return COMPANION_TOUCH_FT6336_STM32WB_I2C_ERROR;
    }
    if (!comp_ft6336_decode_touch_report(report, sample)) {
        touch->error_count++;
        return COMPANION_TOUCH_FT6336_STM32WB_BAD_REPORT;
    }

    touch->read_count++;
    return COMPANION_TOUCH_FT6336_STM32WB_OK;
}

const char *companion_touch_ft6336_stm32wb_result_name(
    companion_touch_ft6336_stm32wb_result_t result)
{
    switch (result) {
    case COMPANION_TOUCH_FT6336_STM32WB_OK:
        return "ok";
    case COMPANION_TOUCH_FT6336_STM32WB_NOT_DETECTED:
        return "not_detected";
    case COMPANION_TOUCH_FT6336_STM32WB_I2C_ERROR:
        return "i2c_error";
    case COMPANION_TOUCH_FT6336_STM32WB_BAD_REPORT:
        return "bad_report";
    default:
        return "bad_argument";
    }
}
