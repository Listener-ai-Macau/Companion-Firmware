#include "touch_target_stm32wba_ft6336.h"

#include <string.h>

const char *companion_touch_ft6336_stm32wba_target_name(
    companion_touch_ft6336_stm32wba_target_t target)
{
    switch (target) {
    case COMPANION_TOUCH_FT6336_STM32WBA_TARGET_WBA55:
        return "WBA55";
    case COMPANION_TOUCH_FT6336_STM32WBA_TARGET_WBA65:
        return "WBA65";
    default:
        return "WBA";
    }
}

void companion_touch_ft6336_stm32wba_init(
    companion_touch_ft6336_stm32wba_t *touch,
    const companion_touch_ft6336_stm32wba_config_t *config)
{
    if (touch == NULL) {
        return;
    }

    memset(touch, 0, sizeof(*touch));
    touch->address_7bit = COMP_FT6336_I2C_ADDRESS_7BIT;
    if (config != NULL) {
        touch->config = *config;
    }
    if (companion_touch_ft6336_stm32wba_ready(touch) &&
        companion_touch_ft6336_stm32wba_probe(touch)) {
        (void)companion_touch_ft6336_stm32wba_read_identity(touch);
        (void)companion_touch_ft6336_stm32wba_configure_interrupt(touch);
        (void)companion_touch_ft6336_stm32wba_configure_runtime_tuning(touch);
    }
}

bool companion_touch_ft6336_stm32wba_ready(
    const companion_touch_ft6336_stm32wba_t *touch)
{
    return touch != NULL &&
           (touch->config.target == COMPANION_TOUCH_FT6336_STM32WBA_TARGET_WBA55 ||
            touch->config.target == COMPANION_TOUCH_FT6336_STM32WBA_TARGET_WBA65) &&
           touch->config.probe != NULL &&
           touch->config.read != NULL &&
           touch->config.write != NULL;
}

bool companion_touch_ft6336_stm32wba_probe(
    companion_touch_ft6336_stm32wba_t *touch)
{
    if (!companion_touch_ft6336_stm32wba_ready(touch)) {
        return false;
    }

    touch->probe_count++;
    touch->detected = touch->config.probe(touch->config.context,
                                          touch->address_7bit);
    return touch->detected;
}

bool companion_touch_ft6336_stm32wba_read_identity(
    companion_touch_ft6336_stm32wba_t *touch)
{
    uint8_t registers[COMP_FT6336_IDENTITY_BYTES];

    if (!companion_touch_ft6336_stm32wba_ready(touch) || !touch->detected) {
        return false;
    }

    touch->identity_attempted = true;
    touch->identity_read_count++;
    if (!touch->config.read(touch->config.context,
                            touch->address_7bit,
                            COMP_FT6336_IDENTITY_REGISTER,
                            registers,
                            sizeof(registers))) {
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

bool companion_touch_ft6336_stm32wba_configure_working_mode(
    companion_touch_ft6336_stm32wba_t *touch)
{
    static const uint8_t registers[] = {
        COMP_FT6336_DEVICE_MODE_REGISTER,
        COMP_FT6336_POWER_MODE_REGISTER,
    };
    static const uint8_t requested[] = {
        COMP_FT6336_DEVICE_MODE_WORKING,
        COMP_FT6336_POWER_MODE_ACTIVE,
    };

    if (!companion_touch_ft6336_stm32wba_ready(touch) || !touch->detected) {
        return false;
    }
    /* Match the original WB acquisition setup. This runs only during the
     * existing initialization/recovery path, never on a contact, display
     * completion or each poll. Keep trigger mode, report rate and bus timing.
     * Any failed write/readback keeps the board's touch-ready gate closed. */
    for (size_t index = 0u; index < sizeof(requested); ++index) {
        uint8_t actual = UINT8_MAX;
        if (!touch->config.write(touch->config.context,
                                  touch->address_7bit, registers[index],
                                  &requested[index], 1u) ||
            !touch->config.read(touch->config.context,
                                 touch->address_7bit, registers[index],
                                 &actual, 1u) || actual != requested[index]) {
            return false;
        }
    }
    return true;
}

bool companion_touch_ft6336_stm32wba_configure_interrupt(
    companion_touch_ft6336_stm32wba_t *touch)
{
    const uint8_t requested = COMP_FT6336_G_MODE_TRIGGER;
    uint8_t actual = UINT8_MAX;

    if (!companion_touch_ft6336_stm32wba_ready(touch) || !touch->detected) {
        return false;
    }
    touch->interrupt_mode_attempted = true;
    touch->interrupt_config_count++;
    if (!companion_touch_ft6336_stm32wba_configure_working_mode(touch) ||
        !touch->config.write(touch->config.context,
                             touch->address_7bit,
                             COMP_FT6336_G_MODE_REGISTER,
                             &requested,
                             sizeof(requested)) ||
        !touch->config.read(touch->config.context,
                            touch->address_7bit,
                            COMP_FT6336_G_MODE_REGISTER,
                            &actual,
                            sizeof(actual))) {
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

bool companion_touch_ft6336_stm32wba_configure_runtime_tuning(
    companion_touch_ft6336_stm32wba_t *touch)
{
    static const uint8_t registers[] = {
        COMP_FT6336_TOUCH_THRESHOLD_REGISTER,
        COMP_FT6336_PERIOD_ACTIVE_REGISTER,
        COMP_FT6336_PERIOD_MONITOR_REGISTER,
    };
    static const uint8_t requested[] = {
        COMP_FT6336_COMPANION_TOUCH_THRESHOLD,
        COMP_FT6336_COMPANION_ACTIVE_PERIOD,
        COMP_FT6336_COMPANION_MONITOR_PERIOD,
    };
    uint8_t actual[sizeof(requested)];

    if (!companion_touch_ft6336_stm32wba_ready(touch) || !touch->detected) {
        return false;
    }
    touch->runtime_tuning_attempted = true;
    touch->runtime_tuning_config_count++;
    for (size_t index = 0u; index < sizeof(requested); ++index) {
        if (!touch->config.write(touch->config.context,
                                 touch->address_7bit,
                                 registers[index],
                                 &requested[index],
                                 1u) ||
            !touch->config.read(touch->config.context,
                                touch->address_7bit,
                                registers[index],
                                &actual[index],
                                1u)) {
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

companion_touch_ft6336_stm32wba_result_t companion_touch_ft6336_stm32wba_poll(
    companion_touch_ft6336_stm32wba_t *touch,
    comp_ft6336_touch_sample_t *sample)
{
    uint8_t report[COMP_FT6336_TOUCH_REPORT_BYTES];

    if (touch == NULL || sample == NULL ||
        !companion_touch_ft6336_stm32wba_ready(touch)) {
        return COMPANION_TOUCH_FT6336_STM32WBA_BAD_ARGUMENT;
    }
    if (!touch->detected && !companion_touch_ft6336_stm32wba_probe(touch)) {
        return COMPANION_TOUCH_FT6336_STM32WBA_NOT_DETECTED;
    }
    if (!touch->identity_valid && !touch->identity_attempted) {
        (void)companion_touch_ft6336_stm32wba_read_identity(touch);
    }
    if (!touch->interrupt_mode_attempted) {
        (void)companion_touch_ft6336_stm32wba_configure_interrupt(touch);
    }
    if (!touch->runtime_tuning_attempted) {
        (void)companion_touch_ft6336_stm32wba_configure_runtime_tuning(touch);
    }
    if (!touch->config.read(touch->config.context,
                            touch->address_7bit,
                            COMP_FT6336_TOUCH_REPORT_REGISTER,
                            report,
                            sizeof(report))) {
        touch->error_count++;
        touch->detected = false;
        touch->identity_attempted = false;
        touch->identity_valid = false;
        touch->interrupt_mode_attempted = false;
        touch->interrupt_mode_valid = false;
        touch->runtime_tuning_attempted = false;
        touch->runtime_tuning_valid = false;
        return COMPANION_TOUCH_FT6336_STM32WBA_I2C_ERROR;
    }
    if (!comp_ft6336_decode_touch_report(report, sample)) {
        touch->error_count++;
        return COMPANION_TOUCH_FT6336_STM32WBA_BAD_REPORT;
    }

    touch->read_count++;
    return COMPANION_TOUCH_FT6336_STM32WBA_OK;
}

const char *companion_touch_ft6336_stm32wba_result_name(
    companion_touch_ft6336_stm32wba_result_t result)
{
    switch (result) {
    case COMPANION_TOUCH_FT6336_STM32WBA_OK:
        return "ok";
    case COMPANION_TOUCH_FT6336_STM32WBA_NOT_DETECTED:
        return "not_detected";
    case COMPANION_TOUCH_FT6336_STM32WBA_I2C_ERROR:
        return "i2c_error";
    case COMPANION_TOUCH_FT6336_STM32WBA_BAD_REPORT:
        return "bad_report";
    default:
        return "bad_argument";
    }
}
