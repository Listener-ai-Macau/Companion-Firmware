#include "dev_info.h"

#define COMPANION_EXTERNAL_ALIAS_BASE 0x90000000u
#define COMPANION_UI_PARTITION_BYTES 0x00200000u
#define COMPANION_NOR_PAGE_BYTES 256u
#define COMPANION_NOR_SECTOR_BYTES 4096u

__attribute__((used, section(".DevInfo")))
const struct StorageInfo StorageInfo = {
    "Companion WB55 SPI1 NOR UI assets only",
    NOR_FLASH,
    COMPANION_EXTERNAL_ALIAS_BASE,
    COMPANION_UI_PARTITION_BYTES,
    COMPANION_NOR_PAGE_BYTES,
    0xFFu,
    {
        {COMPANION_UI_PARTITION_BYTES / COMPANION_NOR_SECTOR_BYTES,
         COMPANION_NOR_SECTOR_BYTES},
        {0u, 0u},
    },
};
