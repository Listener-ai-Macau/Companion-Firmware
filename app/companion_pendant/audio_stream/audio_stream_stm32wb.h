#ifndef COMPANION_AUDIO_STREAM_STM32WB_H
#define COMPANION_AUDIO_STREAM_STM32WB_H

#include "audio_stream.h"
#include "stm32_wpan_common.h"
#include "ble_types.h"

#ifdef __cplusplus
extern "C" {
#endif

#define COMP_AUDIO_STREAM_STM32WB_GATT_VALUE_BYTES 248u
#define COMP_AUDIO_STREAM_STM32WB_CONTROL_VALUE_BYTES 64u
#define COMP_AUDIO_STREAM_STM32WB_READINESS_VALUE_BYTES 96u
#define COMP_AUDIO_STREAM_STM32WB_CAPABILITIES_VALUE_BYTES 96u

typedef enum {
    COMP_AUDIO_STREAM_STM32WB_NOTIFY_ENABLED = 0,
    COMP_AUDIO_STREAM_STM32WB_NOTIFY_DISABLED,
    COMP_AUDIO_STREAM_STM32WB_CONTROL_WRITE,
} comp_audio_stream_stm32wb_event_t;

typedef struct {
    comp_audio_stream_stm32wb_event_t event;
    comp_audio_stream_status_t control_status;
    const uint8_t *payload;
    uint8_t length;
} comp_audio_stream_stm32wb_notification_t;

comp_audio_stream_config_t comp_audio_stream_stm32wb_default_config(
    comp_audio_stream_control_fn_t control,
    void *context);

tBleStatus comp_audio_stream_stm32wb_init(comp_audio_stream_t *stream);
comp_audio_stream_status_t comp_audio_stream_stm32wb_notify(void *context,
                                                            const uint8_t *data,
                                                            uint16_t length);
tBleStatus comp_audio_stream_stm32wb_last_notify_status(void);
void comp_audio_stream_stm32wb_notify_pump(void);
tBleStatus comp_audio_stream_stm32wb_update_readiness(const uint8_t *data,
                                                      uint8_t length);
tBleStatus comp_audio_stream_stm32wb_update_capabilities(const uint8_t *data,
                                                         uint8_t length);

void comp_audio_stream_stm32wb_app_notification(
    const comp_audio_stream_stm32wb_notification_t *notification);

#ifdef __cplusplus
}
#endif

#endif /* COMPANION_AUDIO_STREAM_STM32WB_H */
