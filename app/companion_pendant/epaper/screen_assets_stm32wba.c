#include "screen_assets_stm32wba.h"

#include <string.h>

static bool read_partition(void *context,
                           uint32_t partition_offset,
                           uint8_t *destination,
                           size_t length)
{
    companion_screen_assets_stm32wba_t *adapter =
        (companion_screen_assets_stm32wba_t *)context;
    size_t consumed = 0u;

    if (!companion_screen_assets_stm32wba_ready(adapter) || destination == NULL ||
        partition_offset > adapter->config.partition_size ||
        length > adapter->config.partition_size - partition_offset) {
        return false;
    }
    if (length == 0u) {
        return true;
    }
    if (adapter->cache == NULL || length >= adapter->cache_capacity) {
        bool result = adapter->config.read(adapter->config.context,
                                            partition_offset, destination, length);
        if (!result) {
            companion_screen_assets_stm32wba_invalidate(adapter);
        }
        return result;
    }
    while (consumed < length) {
        uint32_t offset = partition_offset + (uint32_t)consumed;
        size_t available;
        size_t count;
        if (adapter->cache_length == 0u || offset < adapter->cache_offset ||
            offset - adapter->cache_offset >= adapter->cache_length) {
            uint32_t capacity = (uint32_t)adapter->cache_capacity;
            uint32_t start = offset - offset % capacity;
            size_t fill = adapter->config.partition_size - start;
            if (fill > adapter->cache_capacity) {
                fill = adapter->cache_capacity;
            }
            /* Invalidate before I/O: a failed transfer must never become a hit. */
            companion_screen_assets_stm32wba_invalidate(adapter);
            if (!adapter->config.read(adapter->config.context, start,
                                      adapter->cache, fill)) {
                return false;
            }
            adapter->cache_offset = start;
            adapter->cache_length = fill;
        }
        available = adapter->cache_length - (offset - adapter->cache_offset);
        count = length - consumed;
        if (count > available) {
            count = available;
        }
        memcpy(destination + consumed,
               adapter->cache + (offset - adapter->cache_offset), count);
        consumed += count;
    }
    return true;
}

void companion_screen_assets_stm32wba_init(
    companion_screen_assets_stm32wba_t *adapter)
{
    if (adapter != NULL) {
        memset(adapter, 0, sizeof(*adapter));
    }
}

bool companion_screen_assets_stm32wba_ready(
    const companion_screen_assets_stm32wba_t *adapter)
{
    return adapter != NULL &&
           (adapter->config.target == COMPANION_EPAPER_PANEL_STM32WBA_TARGET_WBA55 ||
            adapter->config.target == COMPANION_EPAPER_PANEL_STM32WBA_TARGET_WBA65) &&
           adapter->config.partition_size != 0u && adapter->config.read != NULL;
}

bool companion_screen_assets_stm32wba_bind(
    companion_screen_assets_stm32wba_t *adapter,
    comp_asset_store_t *store,
    const companion_screen_assets_stm32wba_config_t *config)
{
    /* Copy first so rebinding with &adapter->config is well-defined. Clear both
     * outputs on any failure; a stale reader must not continue an old OTA slot. */
    companion_screen_assets_stm32wba_config_t value = {0};
    if (config != NULL) {
        value = *config;
    }
    companion_screen_assets_stm32wba_init(adapter);
    if (store != NULL) {
        memset(store, 0, sizeof(*store));
    }
    if (adapter == NULL || store == NULL || config == NULL) {
        return false;
    }
    adapter->config = value;
    if (!companion_screen_assets_stm32wba_ready(adapter)) {
        companion_screen_assets_stm32wba_init(adapter);
        return false;
    }
    return comp_asset_store_init_reader(store, COMP_ASSET_STORAGE_EXTERNAL_NOR,
                                        adapter->config.partition_size,
                                        read_partition, adapter);
}

bool companion_screen_assets_stm32wba_set_cache(
    companion_screen_assets_stm32wba_t *adapter,
    uint8_t *buffer,
    size_t capacity)
{
    if (!companion_screen_assets_stm32wba_ready(adapter) ||
        (buffer == NULL) != (capacity == 0u) || capacity > UINT32_MAX) {
        return false;
    }
    adapter->cache = buffer;
    adapter->cache_capacity = capacity;
    companion_screen_assets_stm32wba_invalidate(adapter);
    return true;
}

void companion_screen_assets_stm32wba_invalidate(
    companion_screen_assets_stm32wba_t *adapter)
{
    if (adapter != NULL) {
        adapter->cache_length = 0u;
    }
}
