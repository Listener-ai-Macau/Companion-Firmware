#include "audio_stream.h"

#include <string.h>

static uint16_t comp_audio_stream_select_gatt_value_max(uint16_t requested)
{
    if (requested < COMP_AUDIO_STREAM_MIN_GATT_VALUE_BYTES) {
        return COMP_AUDIO_STREAM_DEFAULT_GATT_VALUE_BYTES;
    }
    if (requested > COMP_AUDIO_STREAM_MAX_GATT_VALUE_BYTES) {
        return COMP_AUDIO_STREAM_MAX_GATT_VALUE_BYTES;
    }
    return requested;
}

static void comp_audio_stream_write_u16_le(uint8_t *out, uint16_t value)
{
    out[0] = (uint8_t)(value & 0xFFu);
    out[1] = (uint8_t)((value >> 8) & 0xFFu);
}

static void comp_audio_stream_write_u32_le(uint8_t *out, uint32_t value)
{
    out[0] = (uint8_t)(value & 0xFFu);
    out[1] = (uint8_t)((value >> 8) & 0xFFu);
    out[2] = (uint8_t)((value >> 16) & 0xFFu);
    out[3] = (uint8_t)((value >> 24) & 0xFFu);
}

static bool comp_audio_stream_is_trim_byte(uint8_t value)
{
    return value == '\r' || value == '\n' || value == ' ' || value == '\t';
}

static void comp_audio_stream_trim_command(const uint8_t **data, size_t *length)
{
    if (data == 0 || length == 0 || *data == 0) {
        return;
    }

    const uint8_t *start = *data;
    size_t remaining = *length;
    if (remaining > 0u && start[0] == '~') {
        start++;
        remaining--;
    }
    while (remaining > 0u && comp_audio_stream_is_trim_byte(start[0])) {
        start++;
        remaining--;
    }
    while (remaining > 0u && comp_audio_stream_is_trim_byte(start[remaining - 1u])) {
        remaining--;
    }

    *data = start;
    *length = remaining;
}

static bool comp_audio_stream_command_equals(const uint8_t *data,
                                             size_t length,
                                             const char *expected)
{
    size_t expected_len = strlen(expected);
    return length == expected_len && memcmp(data, expected, expected_len) == 0;
}

static comp_audio_control_t comp_audio_stream_classify_control(const uint8_t *data,
                                                               size_t length)
{
    if (data == 0 || length == 0u) {
        return COMP_AUDIO_CONTROL_NONE;
    }
    if (comp_audio_stream_command_equals(data, length, "TYPE:READY")) {
        return COMP_AUDIO_CONTROL_TYPE_READY;
    }
    if (comp_audio_stream_command_equals(data, length, "TYPE:READY:A1")) {
        return COMP_AUDIO_CONTROL_TYPE_READY_A1;
    }
    if (comp_audio_stream_command_equals(data, length, "TYPE:READY:A2")) {
        return COMP_AUDIO_CONTROL_TYPE_READY_A2;
    }
    if (comp_audio_stream_command_equals(data, length, "TYPE:HB")) {
        return COMP_AUDIO_CONTROL_TYPE_HEARTBEAT;
    }
    if (comp_audio_stream_command_equals(data, length, "TYPE:STOP") ||
        comp_audio_stream_command_equals(data, length, "TYPE:BYE")) {
        return COMP_AUDIO_CONTROL_TYPE_STOP;
    }
    if (comp_audio_stream_command_equals(data, length, "VREC:TOGGLE")) {
        return COMP_AUDIO_CONTROL_RECORDING_TOGGLE;
    }
    if (comp_audio_stream_command_equals(data, length, "VREC:STOP")) {
        return COMP_AUDIO_CONTROL_RECORDING_STOP;
    }
    if (comp_audio_stream_command_equals(data, length, "VREC:CANCEL")) {
        return COMP_AUDIO_CONTROL_RECORDING_CANCEL;
    }
    if (comp_audio_stream_command_equals(data, length, "VREC:PROCESSING:START")) {
        return COMP_AUDIO_CONTROL_RECORDING_PROCESSING_START;
    }
    if (comp_audio_stream_command_equals(data, length, "VREC:PROCESSING:STOP")) {
        return COMP_AUDIO_CONTROL_RECORDING_PROCESSING_STOP;
    }
    if (comp_audio_stream_command_equals(data, length, "VREC:PROCESSING:DONE")) {
        return COMP_AUDIO_CONTROL_RECORDING_PROCESSING_DONE;
    }
    if (comp_audio_stream_command_equals(data, length, "VREC:PROCESSING:WARN")) {
        return COMP_AUDIO_CONTROL_RECORDING_PROCESSING_WARN;
    }
    return COMP_AUDIO_CONTROL_UNSUPPORTED;
}

static comp_audio_stream_status_t comp_audio_stream_notify_packet(comp_audio_stream_t *stream,
                                                                  comp_audio_packet_type_t packet_type,
                                                                  uint32_t session_id,
                                                                  uint16_t sequence_or_count,
                                                                  const uint8_t *payload,
                                                                  uint16_t payload_len,
                                                                  uint16_t packet_pcm_bytes)
{
    if (stream == 0 || stream->config.notify == 0) {
        return COMP_AUDIO_STREAM_BAD_ARGUMENT;
    }
    if (!comp_audio_stream_is_ready(stream)) {
        return COMP_AUDIO_STREAM_NOT_READY;
    }

    uint8_t packet[COMP_AUDIO_STREAM_MAX_GATT_VALUE_BYTES];
    uint16_t written = 0u;
    comp_audio_stream_status_t status = comp_audio_stream_build_vka1_packet(packet_type,
                                                                            session_id,
                                                                            sequence_or_count,
                                                                            payload,
                                                                            payload_len,
                                                                            packet_pcm_bytes,
                                                                            packet,
                                                                            sizeof(packet),
                                                                            &written);
    if (status != COMP_AUDIO_STREAM_OK) {
        return status;
    }

    status = stream->config.notify(stream->config.context, packet, written);
    if (status != COMP_AUDIO_STREAM_OK) {
        return COMP_AUDIO_STREAM_NOTIFY_FAILED;
    }
    return COMP_AUDIO_STREAM_OK;
}

void comp_audio_stream_init(comp_audio_stream_t *stream,
                            const comp_audio_stream_config_t *config)
{
    if (stream == 0) {
        return;
    }
    memset(stream, 0, sizeof(*stream));
    if (config != 0) {
        stream->config = *config;
    }
    stream->config.gatt_value_max_bytes =
        comp_audio_stream_select_gatt_value_max(stream->config.gatt_value_max_bytes);
}

void comp_audio_stream_set_notify_enabled(comp_audio_stream_t *stream, bool enabled)
{
    if (stream == 0) {
        return;
    }
    stream->notify_enabled = enabled;
    if (!enabled) {
        stream->type_link_ready = false;
        stream->session_active = false;
    }
}

bool comp_audio_stream_is_ready(const comp_audio_stream_t *stream)
{
    return stream != 0 && stream->notify_enabled && stream->type_link_ready;
}

bool comp_audio_stream_is_type_link_ready(const comp_audio_stream_t *stream)
{
    return stream != 0 && stream->type_link_ready;
}

uint16_t comp_audio_stream_gatt_value_max_bytes(const comp_audio_stream_t *stream)
{
    if (stream == 0) {
        return COMP_AUDIO_STREAM_DEFAULT_GATT_VALUE_BYTES;
    }
    return comp_audio_stream_select_gatt_value_max(stream->config.gatt_value_max_bytes);
}

uint16_t comp_audio_stream_payload_bytes(const comp_audio_stream_t *stream)
{
    uint16_t value_max = comp_audio_stream_gatt_value_max_bytes(stream);
    if (value_max <= COMP_AUDIO_STREAM_VKA1_HEADER_BYTES) {
        return 0u;
    }
    return (uint16_t)(value_max - COMP_AUDIO_STREAM_VKA1_HEADER_BYTES);
}

comp_audio_stream_status_t comp_audio_stream_handle_control_write(comp_audio_stream_t *stream,
                                                                  const uint8_t *data,
                                                                  size_t length)
{
    if (stream == 0 || data == 0 || length == 0u) {
        return COMP_AUDIO_STREAM_BAD_ARGUMENT;
    }

    const uint8_t *command = data;
    size_t command_len = length;
    comp_audio_stream_trim_command(&command, &command_len);
    comp_audio_control_t control = comp_audio_stream_classify_control(command, command_len);

    if (control == COMP_AUDIO_CONTROL_TYPE_READY ||
        control == COMP_AUDIO_CONTROL_TYPE_READY_A1 ||
        control == COMP_AUDIO_CONTROL_TYPE_READY_A2 ||
        control == COMP_AUDIO_CONTROL_TYPE_HEARTBEAT) {
        stream->type_link_ready = true;
        stream->type_heartbeat_count++;
    } else if (control == COMP_AUDIO_CONTROL_TYPE_STOP) {
        stream->type_link_ready = false;
    } else if (control == COMP_AUDIO_CONTROL_UNSUPPORTED ||
               control == COMP_AUDIO_CONTROL_NONE) {
        return COMP_AUDIO_STREAM_UNSUPPORTED_CONTROL;
    }

    if (stream->config.control != 0) {
        stream->config.control(stream->config.context, control, command, command_len);
    }
    return COMP_AUDIO_STREAM_OK;
}

comp_audio_stream_status_t comp_audio_stream_send_session_start(comp_audio_stream_t *stream,
                                                                uint32_t session_id)
{
    if (stream == 0) {
        return COMP_AUDIO_STREAM_BAD_ARGUMENT;
    }
    comp_audio_stream_status_t status = comp_audio_stream_notify_packet(stream,
                                                                        COMP_AUDIO_PACKET_SESSION_START,
                                                                        session_id,
                                                                        0u,
                                                                        0,
                                                                        0u,
                                                                        0u);
    if (status == COMP_AUDIO_STREAM_OK) {
        stream->session_id = session_id;
        stream->next_packet_sequence = 0u;
        stream->expected_packet_count = 0u;
        stream->session_active = true;
    }
    return status;
}

comp_audio_stream_status_t comp_audio_stream_send_session_audio(comp_audio_stream_t *stream,
                                                                const uint8_t *pcm,
                                                                uint16_t pcm_bytes)
{
    if (stream == 0 || pcm == 0 || pcm_bytes == 0u) {
        return COMP_AUDIO_STREAM_BAD_ARGUMENT;
    }
    if (!stream->session_active) {
        return COMP_AUDIO_STREAM_NOT_ACTIVE;
    }

    uint16_t payload_bytes = comp_audio_stream_payload_bytes(stream);
    if (payload_bytes == 0u) {
        return COMP_AUDIO_STREAM_PACKET_TOO_LARGE;
    }

    uint16_t offset = 0u;
    while (offset < pcm_bytes) {
        if (stream->next_packet_sequence == UINT16_MAX) {
            return COMP_AUDIO_STREAM_SEQUENCE_OVERFLOW;
        }
        uint16_t remaining = (uint16_t)(pcm_bytes - offset);
        uint16_t chunk = remaining > payload_bytes ? payload_bytes : remaining;
        comp_audio_stream_status_t status = comp_audio_stream_notify_packet(stream,
                                                                            COMP_AUDIO_PACKET_AUDIO_DATA,
                                                                            stream->session_id,
                                                                            stream->next_packet_sequence,
                                                                            pcm + offset,
                                                                            chunk,
                                                                            chunk);
        if (status != COMP_AUDIO_STREAM_OK) {
            return status;
        }
        offset = (uint16_t)(offset + chunk);
        stream->next_packet_sequence++;
        stream->expected_packet_count = stream->next_packet_sequence;
    }
    return COMP_AUDIO_STREAM_OK;
}

comp_audio_stream_status_t comp_audio_stream_send_session_stop(comp_audio_stream_t *stream)
{
    if (stream == 0) {
        return COMP_AUDIO_STREAM_BAD_ARGUMENT;
    }
    if (!stream->session_active) {
        return COMP_AUDIO_STREAM_NOT_ACTIVE;
    }
    comp_audio_stream_status_t status = comp_audio_stream_notify_packet(stream,
                                                                        COMP_AUDIO_PACKET_SESSION_STOP,
                                                                        stream->session_id,
                                                                        stream->expected_packet_count,
                                                                        0,
                                                                        0u,
                                                                        0u);
    if (status == COMP_AUDIO_STREAM_OK) {
        stream->session_active = false;
    }
    return status;
}

comp_audio_stream_status_t comp_audio_stream_send_session_cancel(comp_audio_stream_t *stream)
{
    if (stream == 0) {
        return COMP_AUDIO_STREAM_BAD_ARGUMENT;
    }
    if (!stream->session_active) {
        return COMP_AUDIO_STREAM_NOT_ACTIVE;
    }
    comp_audio_stream_status_t status = comp_audio_stream_notify_packet(stream,
                                                                        COMP_AUDIO_PACKET_SESSION_CANCEL,
                                                                        stream->session_id,
                                                                        stream->expected_packet_count,
                                                                        0,
                                                                        0u,
                                                                        0u);
    if (status == COMP_AUDIO_STREAM_OK) {
        stream->session_active = false;
    }
    return status;
}

comp_audio_stream_status_t comp_audio_stream_send_session_error(comp_audio_stream_t *stream,
                                                                comp_audio_session_error_t error_code)
{
    if (stream == 0) {
        return COMP_AUDIO_STREAM_BAD_ARGUMENT;
    }
    if (!stream->session_active) {
        return COMP_AUDIO_STREAM_NOT_ACTIVE;
    }
    comp_audio_stream_status_t status = comp_audio_stream_notify_packet(stream,
                                                                        COMP_AUDIO_PACKET_SESSION_ERROR,
                                                                        stream->session_id,
                                                                        stream->expected_packet_count,
                                                                        0,
                                                                        0u,
                                                                        (uint16_t)error_code);
    if (status == COMP_AUDIO_STREAM_OK) {
        stream->session_active = false;
    }
    return status;
}

comp_audio_stream_status_t comp_audio_stream_build_vka1_packet(comp_audio_packet_type_t packet_type,
                                                               uint32_t session_id,
                                                               uint16_t sequence_or_count,
                                                               const uint8_t *payload,
                                                               uint16_t payload_len,
                                                               uint16_t packet_pcm_bytes,
                                                               uint8_t *out,
                                                               uint16_t out_capacity,
                                                               uint16_t *written)
{
    if (out == 0 || written == 0 || (payload_len != 0u && payload == 0)) {
        return COMP_AUDIO_STREAM_BAD_ARGUMENT;
    }
    uint16_t packet_len = (uint16_t)(COMP_AUDIO_STREAM_VKA1_HEADER_BYTES + payload_len);
    if (packet_len < COMP_AUDIO_STREAM_VKA1_HEADER_BYTES || packet_len > out_capacity) {
        return COMP_AUDIO_STREAM_PACKET_TOO_LARGE;
    }

    out[0] = 'V';
    out[1] = 'K';
    out[2] = 'A';
    out[3] = '1';
    out[4] = (uint8_t)packet_type;
    out[5] = 0u;
    comp_audio_stream_write_u16_le(out + 6u, COMP_AUDIO_STREAM_VKA1_HEADER_BYTES);
    comp_audio_stream_write_u32_le(out + 8u, session_id);
    comp_audio_stream_write_u16_le(out + 12u, sequence_or_count);
    out[14] = 0u;
    out[15] = 1u;
    comp_audio_stream_write_u16_le(out + 16u, payload_len);
    comp_audio_stream_write_u16_le(out + 18u, packet_pcm_bytes);
    if (payload_len != 0u) {
        memcpy(out + COMP_AUDIO_STREAM_VKA1_HEADER_BYTES, payload, payload_len);
    }
    *written = packet_len;
    return COMP_AUDIO_STREAM_OK;
}

const char *comp_audio_stream_status_name(comp_audio_stream_status_t status)
{
    switch (status) {
    case COMP_AUDIO_STREAM_OK:
        return "ok";
    case COMP_AUDIO_STREAM_BAD_ARGUMENT:
        return "bad_argument";
    case COMP_AUDIO_STREAM_NOT_READY:
        return "not_ready";
    case COMP_AUDIO_STREAM_NOT_ACTIVE:
        return "not_active";
    case COMP_AUDIO_STREAM_PACKET_TOO_LARGE:
        return "packet_too_large";
    case COMP_AUDIO_STREAM_SEQUENCE_OVERFLOW:
        return "sequence_overflow";
    case COMP_AUDIO_STREAM_NOTIFY_FAILED:
        return "notify_failed";
    case COMP_AUDIO_STREAM_UNSUPPORTED_CONTROL:
        return "unsupported_control";
    default:
        return "unknown";
    }
}

const char *comp_audio_stream_control_name(comp_audio_control_t control)
{
    switch (control) {
    case COMP_AUDIO_CONTROL_NONE:
        return "none";
    case COMP_AUDIO_CONTROL_TYPE_READY:
        return "type_ready";
    case COMP_AUDIO_CONTROL_TYPE_READY_A1:
        return "type_ready_a1";
    case COMP_AUDIO_CONTROL_TYPE_READY_A2:
        return "type_ready_a2";
    case COMP_AUDIO_CONTROL_TYPE_HEARTBEAT:
        return "type_heartbeat";
    case COMP_AUDIO_CONTROL_TYPE_STOP:
        return "type_stop";
    case COMP_AUDIO_CONTROL_RECORDING_TOGGLE:
        return "recording_toggle";
    case COMP_AUDIO_CONTROL_RECORDING_STOP:
        return "recording_stop";
    case COMP_AUDIO_CONTROL_RECORDING_CANCEL:
        return "recording_cancel";
    case COMP_AUDIO_CONTROL_RECORDING_PROCESSING_START:
        return "recording_processing_start";
    case COMP_AUDIO_CONTROL_RECORDING_PROCESSING_STOP:
        return "recording_processing_stop";
    case COMP_AUDIO_CONTROL_RECORDING_PROCESSING_DONE:
        return "recording_processing_done";
    case COMP_AUDIO_CONTROL_RECORDING_PROCESSING_WARN:
        return "recording_processing_warn";
    case COMP_AUDIO_CONTROL_UNSUPPORTED:
        return "unsupported";
    default:
        return "unknown";
    }
}
