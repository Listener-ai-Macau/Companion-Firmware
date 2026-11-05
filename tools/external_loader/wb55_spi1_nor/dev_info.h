#ifndef COMPANION_WB55_SPI1_NOR_DEV_INFO_H
#define COMPANION_WB55_SPI1_NOR_DEV_INFO_H

#include <stdint.h>

#define NOR_FLASH 3u
#define DEVICE_SECTOR_TYPES 10u

struct DeviceSectors {
    uint32_t sector_count;
    uint32_t sector_size;
};

struct StorageInfo {
    char device_name[100];
    uint16_t device_type;
    uint32_t device_start_address;
    uint32_t device_size;
    uint32_t page_size;
    uint8_t erased_value;
    struct DeviceSectors sectors[DEVICE_SECTOR_TYPES];
};

extern const struct StorageInfo StorageInfo;

#endif
