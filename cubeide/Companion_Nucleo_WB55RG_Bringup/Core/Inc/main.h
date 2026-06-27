#ifndef COMPANION_NUCLEO_BRINGUP_MAIN_H
#define COMPANION_NUCLEO_BRINGUP_MAIN_H

#include "audio_stream.h"
#include "stm32wbxx_hal.h"

#include <stdbool.h>
#include <stddef.h>

void Error_Handler(void);

void Companion_App_HandleBleControl(comp_audio_control_t control,
                                    const uint8_t *data,
                                    size_t length);
void Companion_App_HandleBleLinkReadyChanged(bool ready);

bool Companion_BleAudio_IsReady(void);
bool Companion_BleAudio_IsSessionActive(void);
uint32_t Companion_BleAudio_NextSessionId(void);
comp_audio_stream_status_t Companion_BleAudio_SendSessionStart(uint32_t session_id);
comp_audio_stream_status_t Companion_BleAudio_SendPcmBytes(const uint8_t *pcm,
                                                           uint16_t pcm_bytes);
comp_audio_stream_status_t Companion_BleAudio_SendSessionStop(void);
comp_audio_stream_status_t Companion_BleAudio_SendSessionCancel(void);
comp_audio_stream_status_t Companion_BleAudio_SendSessionError(comp_audio_session_error_t error_code);

#endif /* COMPANION_NUCLEO_BRINGUP_MAIN_H */
