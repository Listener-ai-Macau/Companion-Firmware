#ifndef COMPANION_WBA_BLE_EVENT_COPY_H
#define COMPANION_WBA_BLE_EVENT_COPY_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define COMP_V11_BLE_HCI_EVENT_PACKET_TYPE 0x04u
#define COMP_V11_BLE_HCI_EVENT_HEADER_BYTES 3u
#define COMP_V11_BLE_HCI_EVENT_MAX_BYTES 258u

typedef enum {
    COMP_V11_BLE_EVENT_COPY_OK = 0,
    COMP_V11_BLE_EVENT_COPY_BAD_ARGUMENT,
    COMP_V11_BLE_EVENT_COPY_BAD_TYPE,
    COMP_V11_BLE_EVENT_COPY_BAD_LENGTH,
    COMP_V11_BLE_EVENT_COPY_OUTPUT_TOO_SMALL,
} comp_v11_ble_event_copy_result_t;

/* BLECB_Indication can split one standard HCI event across data/ext_data.
 * The three-byte packet header must remain in data; the HCI plen byte remains
 * authoritative for the total event size. */
comp_v11_ble_event_copy_result_t comp_v11_ble_event_plan(
    const uint8_t *data, uint16_t length,
    const uint8_t *ext_data, uint16_t ext_length,
    uint16_t *total_length);

comp_v11_ble_event_copy_result_t comp_v11_ble_event_flatten(
    const uint8_t *data, uint16_t length,
    const uint8_t *ext_data, uint16_t ext_length,
    uint8_t *output, uint16_t output_capacity,
    uint16_t *output_length);

#ifdef __cplusplus
}
#endif

#endif /* COMPANION_WBA_BLE_EVENT_COPY_H */
