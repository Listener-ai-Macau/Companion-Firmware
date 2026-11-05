#ifndef COMP_V11_BLE_PRODUCT_H
#define COMP_V11_BLE_PRODUCT_H
#include <stdbool.h>
#include <stdint.h>
#include "product_app.h"
#if COMPANION_WBA_ACL_READINESS_PROFILE
void comp_v11_ble_acl_admission_begin(uint16_t h,const uint8_t *data,uint16_t bytes,uint8_t flags);
void comp_v11_ble_acl_admission_end(bool success);
#endif
/* Bind board media before APPE/host startup; default backend remains internal. */
void comp_v11_ble_bond_media_bind(companion_spi_nor_stm32wba_t *);
bool comp_v11_ble_init(comp_v11_product_app_t *app);
void comp_v11_ble_poll(void);
/* True only for runnable foreground work; a full TX pool still permits sleep. */
bool comp_v11_ble_foreground_pending(void);
/* Blocking UART must wait for the finite batch owner, including queued tails.
 * Read-only; no interval renewal or radio/Flash operation from this query. */
bool comp_v11_ble_blocking_diagnostic_busy(void);
/* Feed only a sealed transfer at renderer/NOR transaction boundaries.
 * No control dispatch, catalog mutation or erasure inside a rendered frame. */
void comp_v11_ble_transfer_progress(void);
void comp_v11_ble_idle_background_progress(void);
/* Bounded long-value receive metadata in the existing diagnostic ring.
 * No payload, address, key, additional resident buffer or callback UART. */
void comp_v11_ble_rx_shape_trace(uint8_t stage,uint8_t why,uint8_t type,uint8_t event,
    uint16_t primary,uint16_t extension,uint8_t plen,uint16_t attribute,
    uint16_t offset,uint16_t length);

uint32_t comp_v11_ble_transfer_backpressure(void);
uint32_t comp_v11_ble_tx_pool_events(void);
uint32_t comp_v11_ble_tx_timed_retries(void);
bool comp_v11_ble_entropy(uint32_t *value);
bool comp_v11_ble_host_ready(void);
/* Only service the existing entropy producer between idle console writes. */
void comp_v11_ble_console_idle_progress(void);
uint8_t comp_v11_ble_host_error(void);
uint16_t comp_v11_ble_connection(void);
uint16_t comp_v11_ble_connection_interval(void);
/* Current connection events only; encoded BLK1/20B, no controller commands. */
void comp_v11_ble_link_budget(uint8_t out[20]);
/* Actual ATT_MTU - 3, capped by the product characteristic; default 20. */
uint16_t comp_v11_ble_value_capacity(void);
bool comp_v11_ble_notifications_allowed(void);
uint16_t comp_v11_ble_recording_capacity(void);
typedef struct {
    uint32_t bond_lost_events, rebond_attempts;
    uint8_t pairing_status, pairing_reason;
} comp_v11_ble_security_stats_t;
const comp_v11_ble_security_stats_t *comp_v11_ble_security_stats(void);
void comp_v11_ble_advertise_poll(uint32_t now,bool commands_allowed);
void comp_v11_ble_nvm_poll(uint32_t now,bool writes_allowed);
bool comp_v11_ble_nvm_busy(void);
/* Foreground-only lifecycle operations. They never erase recording extents. */
bool comp_v11_ble_open_pairing_window(void);
bool comp_v11_ble_clear_bonds(void);
bool comp_v11_ble_bond_count(uint8_t *);
uint32_t comp_v11_ble_bond_generation(void);
uint32_t comp_v11_ble_bond_failures(void);
bool comp_v11_ble_nvm_control_blocked(bool microphone_running);
/* Snapshot live GATT/CCCD state into the existing host NVM cache before a
 * planned reset; caller must then wait for comp_v11_ble_nvm_busy()==false. */
bool comp_v11_ble_store_gatt_for_reboot(void);
void comp_v11_ble_link(bool connected,bool encrypted);
/* Observation only, called by valid owned HCI complete events, never by host UI state. */
void comp_v11_ble_observe_capture_radio(bool connected,uint16_t handle,uint8_t reason);
bool comp_v11_ble_menu(comp_screen_menu_action_t action);
comp_runtime_menu_dispatch_t comp_v11_ble_menu_begin(comp_screen_menu_action_t action,uint32_t token);
bool comp_v11_ble_storage_busy(void);
/* Physical/transient owners only; a stopped FAILED pipeline is not itself
 * a reason to deadlock its explicit recording retry. Internal guards remain. */
bool comp_v11_ble_recording_recovery_idle(void);
/* Read-only local-menu rejection reasons: product/host/link not ready,
 * local clear, update, exact segment consumption (bits0..5). */
uint8_t comp_v11_ble_menu_blockers(void);
bool comp_v11_ble_recording_timeline_requested(uint32_t token);
bool comp_v11_ble_can_update(void);
/* Same capture/playback/recording/catalog gates as ordinary update admission;
 * only the exact current OTA-owned asynchronous erase may remain active. */
bool comp_v11_ble_can_continue_update(void);
bool comp_v11_ble_can_update_storage_mount(void);
void comp_v11_ble_apply_preferences(const comp_preferences_values_t *);
/* Publish current verified local preferences to the existing SettingsV1
 * value. A later host clock sync preserves that prefix, so it must be fresh. */
void comp_v11_ble_settings_changed(void);
void comp_v11_ble_pet_caption_changed(void);
bool comp_v11_ble_reconnect(bool pairing);
bool comp_v11_ble_linked(void);
bool comp_v11_ble_secured(void);
void comp_v11_ble_tx_pool_available(void);
void comp_v11_ble_controller_progress_hint(void);
void comp_v11_ble_host_cycle_completed(void);
/* A local stack completion is a retry hint, never durable consumer ACK. */
void comp_v11_ble_recording_notification_complete(void);
typedef enum {
    COMP_V11_BLE_BULK_NONE,
    COMP_V11_BLE_BULK_DEVICE_TO_HOST,
    COMP_V11_BLE_BULK_HOST_TO_DEVICE
} comp_v11_ble_bulk_direction_t;
/* One scoped controller owner for recorder notifications and OTA reception.
 * Direction-specific packet alignment must never restrict OTA receive data. */
void comp_v11_ble_bulk_profile(comp_v11_ble_bulk_direction_t direction,bool interval_hint,
    bool commands_allowed,bool restore_allowed);
void comp_v11_ble_transport_diagnostic(void);
void comp_v11_ble_download_timing_diagnostic(void);
uint32_t comp_v11_ble_fatal_error(void);
#endif

/* Foreground backend page-read observation only, no extra I/O or UART. */
uint32_t comp_v11_ble_observe_us(void);
bool comp_v11_ble_observe_backend_read_active(void);
void comp_v11_ble_observe_nor_read(uint32_t elapsed);
void comp_v11_ble_observe_pool_callback(uint32_t entered_ms);
void comp_v11_ble_observe_radio_state(bool active);
void comp_v11_ble_observe_completion_enqueued(uint16_t handle);
void comp_v11_ble_observe_completion_dispatched(uint16_t handle);
void comp_v11_ble_observe_route_ready(uint8_t job);
void comp_v11_ble_observe_route_run(uint8_t job);

void comp_v11_ble_observe_ll_send(uint16_t h,bool begin,bool success);
uint16_t comp_v11_ble_observe_ll_handle(void);
void comp_v11_ble_observe_ll_completed(uint32_t packets,bool valid);
void comp_v11_ble_observe_ll_disconnect(uint16_t h);
uint32_t comp_v11_ble_observe_spi_page(bool begin);
uint8_t comp_v11_ble_controller_buffer_size(uint16_t *bytes,uint8_t *packets);
bool comp_v11_ble_report_callback_bound(void);
/* count, first, last; each metadata word is bytes[31:16]/flags[15:8]/status[7:0]. */
void comp_v11_ble_ll_failure_snapshot(uint32_t values[3]);
uint32_t comp_v11_ble_pending_acl_released(void);
