#ifndef COMPANION_R7_RUNTIME_BRIDGE_STM32WB_H
#define COMPANION_R7_RUNTIME_BRIDGE_STM32WB_H

#if defined(COMPANION_R7_RUNTIME_HOST_TEST) && COMPANION_R7_RUNTIME_HOST_TEST
typedef struct {
    unsigned host_dry_run;
} comp_epaper_panel_adapter_t;
#else
#include "panel_adapter.h"
#endif

#include <stdbool.h>
#include <stdint.h>

typedef void (*companion_r7_runtime_wait_service_fn)(void *context,
                                                      uint32_t now_ms);

void companion_r7_runtime_bridge_init(comp_epaper_panel_adapter_t *adapter);
bool companion_r7_runtime_bridge_service(void);
bool companion_r7_runtime_bridge_visual_transport(void *context,
                                                   uint8_t command,
                                                   const uint8_t *data,
                                                   uint16_t length);
uint32_t companion_r7_runtime_bridge_last_busy_ms(void);
uint32_t companion_r7_runtime_bridge_last_transaction_ms(void);
bool companion_r7_runtime_bridge_visual_faulted(void);
uint32_t companion_r7_runtime_bridge_visual_activation_count(void);
bool companion_r7_runtime_bridge_visual_closed(void);
void companion_r7_runtime_bridge_visual_set_burst_active(bool active);
bool companion_r7_runtime_bridge_exit_cleanup(void);
void companion_r7_runtime_bridge_set_wait_service(
    companion_r7_runtime_wait_service_fn service,
    void *context,
    uint16_t period_ms);

#endif
