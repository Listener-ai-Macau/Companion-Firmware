#ifndef COMPANION_NUCLEO_BRINGUP_MAIN_H
#define COMPANION_NUCLEO_BRINGUP_MAIN_H

#include "audio_stream.h"
#include "stm32wbxx_hal.h"

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#define COMPANION_RECORDING_FLASH_SHA256_BYTES 32u

typedef enum {
    COMPANION_RECORDING_FLASH_SOURCE_NONE = 0,
    COMPANION_RECORDING_FLASH_SOURCE_MIC_SAI = 1,
} companion_recording_flash_source_t;

typedef enum {
    COMPANION_RECORDING_FLASH_READ_OK = 0,
    COMPANION_RECORDING_FLASH_READ_BAD_ARGUMENT = 1,
    COMPANION_RECORDING_FLASH_READ_NOT_READY = 2,
    COMPANION_RECORDING_FLASH_READ_NO_STORED_RECORDING = 3,
    COMPANION_RECORDING_FLASH_READ_ID_MISMATCH = 4,
    COMPANION_RECORDING_FLASH_READ_OFFSET_OUT_OF_RANGE = 5,
    COMPANION_RECORDING_FLASH_READ_QSPI_BASE = 0x1000,
} companion_recording_flash_read_error_t;

typedef struct {
    uint32_t recording_id;
    uint32_t started_unix_s;
    uint32_t started_tick_ms;
    uint32_t duration_ms;
    uint32_t total_length;
    uint32_t content_crc32;
    uint8_t sha256[COMPANION_RECORDING_FLASH_SHA256_BYTES];
    uint8_t codec;
    uint8_t sync_state;
    uint8_t source_mode;
} companion_recording_flash_metadata_t;

typedef struct {
    uint32_t recording_id;
    uint32_t packet_sequence;
    uint32_t byte_offset;
    uint32_t total_length;
    uint32_t packet_crc32;
    uint32_t error_code;
    uint16_t payload_length;
    bool final_packet;
    uint8_t final_sha256[COMPANION_RECORDING_FLASH_SHA256_BYTES];
} companion_recording_flash_chunk_t;

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
comp_audio_stream_status_t Companion_BleAudio_SendPcmFrame(const uint8_t *pcm,
                                                           uint16_t payload_bytes,
                                                           uint16_t packet_pcm_bytes);
comp_audio_stream_status_t Companion_BleAudio_SendSessionStop(void);
comp_audio_stream_status_t Companion_BleAudio_SendSessionCancel(void);
comp_audio_stream_status_t Companion_BleAudio_SendSessionError(comp_audio_session_error_t error_code);
void Companion_BleAudio_RequestActiveLink(const char *reason);
void Companion_BleAudio_RequestIdleLink(const char *reason);
void Companion_Gatt_PublishRecordingList(void);

bool Companion_RecordingFlash_HandleControl(uint8_t command,
                                            uint16_t max_seconds);
bool Companion_RecordingFlash_GetMetadata(companion_recording_flash_metadata_t *out);
bool Companion_RecordingFlash_ReadChunk(uint32_t recording_id,
                                        uint32_t byte_offset,
                                        uint16_t requested_length,
                                        uint8_t *payload,
                                        uint16_t payload_capacity,
                                        companion_recording_flash_chunk_t *out);
bool Companion_RecordingFlash_Delete(uint8_t operation,
                                     uint32_t recording_id,
                                     uint32_t validated_total_length,
                                     const uint8_t validated_sha256[COMPANION_RECORDING_FLASH_SHA256_BYTES]);

#endif /* COMPANION_NUCLEO_BRINGUP_MAIN_H */
