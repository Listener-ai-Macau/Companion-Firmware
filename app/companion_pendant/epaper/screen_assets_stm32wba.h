#ifndef COMPANION_EPAPER_SCREEN_ASSETS_STM32WBA_H
#define COMPANION_EPAPER_SCREEN_ASSETS_STM32WBA_H

#include "asset_store.h"
#include "panel_target_stm32wba.h"

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef bool (*companion_screen_assets_stm32wba_read_fn_t)(
    void *context,
    uint32_t partition_offset,
    uint8_t *destination,
    size_t length);

typedef struct {
    companion_epaper_panel_stm32wba_target_t target;
    uint32_t partition_size;
    companion_screen_assets_stm32wba_read_fn_t read;
    void *context;
} companion_screen_assets_stm32wba_config_t;

typedef struct {
    companion_screen_assets_stm32wba_config_t config;
    uint8_t *cache;
    size_t cache_capacity;
    uint32_t cache_offset;
    size_t cache_length;
} companion_screen_assets_stm32wba_t;

void companion_screen_assets_stm32wba_init(
    companion_screen_assets_stm32wba_t *adapter);

bool companion_screen_assets_stm32wba_ready(
    const companion_screen_assets_stm32wba_t *adapter);

bool companion_screen_assets_stm32wba_bind(
    companion_screen_assets_stm32wba_t *adapter,
    comp_asset_store_t *store,
    const companion_screen_assets_stm32wba_config_t *config);

/* Optional caller-owned read-ahead buffer (typically 256 bytes). Set after
 * bind; NULL/0 disables it. The adapter/store/buffer share one display-actor
 * lifetime. Bound resource partitions are immutable while being rendered.
 * Rebind on active-slot changes; invalidate before verifying in-place writes
 * or recovery. Neither cache nor adapter owns NOR/OTA partition geometry. */
bool companion_screen_assets_stm32wba_set_cache(
    companion_screen_assets_stm32wba_t *adapter,
    uint8_t *buffer,
    size_t capacity);
void companion_screen_assets_stm32wba_invalidate(
    companion_screen_assets_stm32wba_t *adapter);

#ifdef __cplusplus
}
#endif

#endif /* COMPANION_EPAPER_SCREEN_ASSETS_STM32WBA_H */
