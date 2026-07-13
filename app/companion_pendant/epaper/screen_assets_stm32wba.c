#include "screen_assets_stm32wba.h"

#include <string.h>

static bool read_partition(void *context,
                           uint32_t partition_offset,
                           uint8_t *destination,
                           size_t length)
{
    companion_screen_assets_stm32wba_t *adapter =
        (companion_screen_assets_stm32wba_t *)context;

    if (!companion_screen_assets_stm32wba_ready(adapter) ||
        destination == NULL ||
        partition_offset > adapter->config.partition_size ||
        length > adapter->config.partition_size - partition_offset) {
        return false;
    }
    return adapter->config.read(adapter->config.context,
                                partition_offset,
                                destination,
                                length);
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
           (adapter->config.target ==
                COMPANION_EPAPER_PANEL_STM32WBA_TARGET_WBA55 ||
            adapter->config.target ==
                COMPANION_EPAPER_PANEL_STM32WBA_TARGET_WBA65) &&
           adapter->config.partition_size != 0u &&
           adapter->config.read != NULL;
}

bool companion_screen_assets_stm32wba_bind(
    companion_screen_assets_stm32wba_t *adapter,
    comp_asset_store_t *store,
    const companion_screen_assets_stm32wba_config_t *config)
{
    if (adapter == NULL || store == NULL || config == NULL) {
        return false;
    }
    companion_screen_assets_stm32wba_init(adapter);
    adapter->config = *config;
    if (!companion_screen_assets_stm32wba_ready(adapter)) {
        return false;
    }
    return comp_asset_store_init_reader(store,
                                        COMP_ASSET_STORAGE_EXTERNAL_NOR,
                                        adapter->config.partition_size,
                                        read_partition,
                                        adapter);
}
