#ifndef COMPANION_V11_UPDATE_BOOT_TARGET_H
#define COMPANION_V11_UPDATE_BOOT_TARGET_H

#include "update_storage.h"

typedef struct {
    const uint8_t *public_key_xy;
    uint32_t key_id;
    uint32_t installed_version;
    uint32_t installed_image_size;
} comp_v11_update_boot_target_config_t;

/* Initializes real WBA55 SPI3/NOR, internal Flash, PKA and a ~32 s IWDG.
 * Returns only on an initialization/recovery failure. On success it resumes a
 * bounded install/rollback transaction and jumps to 0x08008000. */
bool comp_v11_update_boot_target_run(
    const comp_v11_update_boot_target_config_t *config);

#endif
