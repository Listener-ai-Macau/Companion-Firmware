#ifndef COMPANION_AUDIO_STREAM_H
#define COMPANION_AUDIO_STREAM_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define COMP_AUDIO_STREAM_SERVICE_UUID_TEXT "710af845-6d9f-6583-0c4d-9e5b3bc3091a"
#define COMP_AUDIO_STREAM_NOTIFY_UUID_TEXT "710af845-6d9f-6583-0c4d-9e5b3bc3091b"
#define COMP_AUDIO_STREAM_READINESS_UUID_TEXT "710af845-6d9f-6583-0c4d-9e5b3bc3091c"
#define COMP_AUDIO_STREAM_CAPABILITIES_UUID_TEXT "710af845-6d9f-6583-0c4d-9e5b3bc3091d"
#define COMP_AUDIO_STREAM_CONTROL_UUID_TEXT "710af845-6d9f-6583-0c4d-9e5b3bc3091e"

#define COMP_AUDIO_STREAM_VKA1_MAGIC "VKA1"
#define COMP_AUDIO_STREAM_VKA1_HEADER_BYTES 20u
#define COMP_AUDIO_STREAM_VKA1_VERSION 1u
#define COMP_AUDIO_STREAM_PCM_SAMPLE_RATE_HZ 16000u
#define COMP_AUDIO_STREAM_PCM_CHANNELS 1u
#define COMP_AUDIO_STREAM_PCM_SAMPLE_WIDTH_BITS 16u
#define COMP_AUDIO_STREAM_DEFAULT_GATT_VALUE_BYTES 244u
#define COMP_AUDIO_STREAM_MAX_GATT_VALUE_BYTES 500u
#define COMP_AUDIO_STREAM_MIN_GATT_VALUE_BYTES COMP_AUDIO_STREAM_VKA1_HEADER_BYTES

typedef enum {
    COMP_AUDIO_PACKET_SESSION_START = 1,
    COMP_AUDIO_PACKET_AUDIO_DATA = 2,
    COMP_AUDIO_PACKET_SESSION_STOP = 3,
    COMP_AUDIO_PACKET_SESSION_CANCEL = 4,
    COMP_AUDIO_PACKET_SESSION_ERROR = 5,
} comp_audio_packet_type_t;

typedef enum {
    COMP_AUDIO_SESSION_ERROR_NONE = 0,
    COMP_AUDIO_SESSION_ERROR_QUEUE_FULL = 1,
    COMP_AUDIO_SESSION_ERROR_NOTIFY_TIMEOUT = 2,
    COMP_AUDIO_SESSION_ERROR_LINK_LOST = 3,
    COMP_AUDIO_SESSION_ERROR_SEQUENCE_OVERFLOW = 4,
    COMP_AUDIO_SESSION_ERROR_INVALID_STATE = 5,
    COMP_AUDIO_SESSION_ERROR_NO_MEMORY = 6,
    COMP_AUDIO_SESSION_ERROR_PACKET_TOO_LARGE = 7,
    COMP_AUDIO_SESSION_ERROR_TRANSPORT = 8,
} comp_audio_session_error_t;

typedef enum {
    COMP_AUDIO_CONTROL_NONE = 0,
    COMP_AUDIO_CONTROL_TYPE_READY,
    COMP_AUDIO_CONTROL_TYPE_READY_A1,
    COMP_AUDIO_CONTROL_TYPE_READY_A2,
    COMP_AUDIO_CONTROL_TYPE_HEARTBEAT,
    COMP_AUDIO_CONTROL_TYPE_STOP,
    COMP_AUDIO_CONTROL_RECORDING_TOGGLE,
    COMP_AUDIO_CONTROL_RECORDING_STOP,
    COMP_AUDIO_CONTROL_RECORDING_CANCEL,
    COMP_AUDIO_CONTROL_RECORDING_PROCESSING_START,
    COMP_AUDIO_CONTROL_RECORDING_PROCESSING_STOP,
    COMP_AUDIO_CONTROL_RECORDING_PROCESSING_DONE,
    COMP_AUDIO_CONTROL_RECORDING_PROCESSING_WARN,
    COMP_AUDIO_CONTROL_UNSUPPORTED,
} comp_audio_control_t;

typedef enum {
    COMP_AUDIO_STREAM_OK = 0,
    COMP_AUDIO_STREAM_BAD_ARGUMENT,
    COMP_AUDIO_STREAM_NOT_READY,
    COMP_AUDIO_STREAM_NOT_ACTIVE,
    COMP_AUDIO_STREAM_PACKET_TOO_LARGE,
    COMP_AUDIO_STREAM_SEQUENCE_OVERFLOW,
    COMP_AUDIO_STREAM_NOTIFY_FAILED,
    COMP_AUDIO_STREAM_UNSUPPORTED_CONTROL,
} comp_audio_stream_status_t;

typedef comp_audio_stream_status_t (*comp_audio_stream_notify_fn_t)(
    void *context,
    const uint8_t *data,
    uint16_t length);

typedef void (*comp_audio_stream_control_fn_t)(
    void *context,
    comp_audio_control_t control,
    const uint8_t *data,
    size_t length);

typedef struct {
    comp_audio_stream_notify_fn_t notify;
    comp_audio_stream_control_fn_t control;
    void *context;
    uint16_t gatt_value_max_bytes;
} comp_audio_stream_config_t;

typedef struct {
    comp_audio_stream_config_t config;
    uint32_t session_id;
    uint16_t next_packet_sequence;
    uint16_t expected_packet_count;
    uint32_t type_heartbeat_count;
    bool notify_enabled;
    bool type_link_ready;
    bool session_active;
} comp_audio_stream_t;

void comp_audio_stream_init(comp_audio_stream_t *stream,
                            const comp_audio_stream_config_t *config);
void comp_audio_stream_set_notify_enabled(comp_audio_stream_t *stream, bool enabled);
bool comp_audio_stream_is_ready(const comp_audio_stream_t *stream);
bool comp_audio_stream_is_type_link_ready(const comp_audio_stream_t *stream);
uint16_t comp_audio_stream_gatt_value_max_bytes(const comp_audio_stream_t *stream);
uint16_t comp_audio_stream_payload_bytes(const comp_audio_stream_t *stream);

comp_audio_stream_status_t comp_audio_stream_handle_control_write(comp_audio_stream_t *stream,
                                                                  const uint8_t *data,
                                                                  size_t length);
comp_audio_stream_status_t comp_audio_stream_send_session_start(comp_audio_stream_t *stream,
                                                                uint32_t session_id);
comp_audio_stream_status_t comp_audio_stream_send_session_audio(comp_audio_stream_t *stream,
                                                                const uint8_t *pcm,
                                                                uint16_t pcm_bytes);
comp_audio_stream_status_t comp_audio_stream_send_session_audio_frame(
    comp_audio_stream_t *stream,
    const uint8_t *pcm,
    uint16_t payload_bytes,
    uint16_t packet_pcm_bytes);
comp_audio_stream_status_t comp_audio_stream_send_session_stop(comp_audio_stream_t *stream);
comp_audio_stream_status_t comp_audio_stream_send_session_cancel(comp_audio_stream_t *stream);
comp_audio_stream_status_t comp_audio_stream_send_session_error(comp_audio_stream_t *stream,
                                                                comp_audio_session_error_t error_code);

comp_audio_stream_status_t comp_audio_stream_build_vka1_packet(comp_audio_packet_type_t packet_type,
                                                               uint32_t session_id,
                                                               uint16_t sequence_or_count,
                                                               const uint8_t *payload,
                                                               uint16_t payload_len,
                                                               uint16_t packet_pcm_bytes,
                                                               uint8_t *out,
                                                               uint16_t out_capacity,
                                                               uint16_t *written);

const char *comp_audio_stream_status_name(comp_audio_stream_status_t status);
const char *comp_audio_stream_control_name(comp_audio_control_t control);

#ifdef __cplusplus
}
#endif

#endif /* COMPANION_AUDIO_STREAM_H */
