#ifndef COMPANION_WBA25_INTERNAL_FLASH_H
#define COMPANION_WBA25_INTERNAL_FLASH_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

/* Experimental adapter for the simple installer's Flash callbacks.  The
 * eventual WBA25 board target must supply its authenticated application range;
 * this file neither chooses a layout nor grants a package target identity. */
typedef struct {
    uint32_t app_start;
    uint32_t app_end; /* exclusive; both ends must be 4 KiB aligned */
} comp_wba25_internal_flash_t;

bool comp_wba25_internal_flash_read(void *context, uint32_t address,
                                    uint8_t *data, size_t length);
bool comp_wba25_internal_flash_erase(void *context, uint32_t address);
bool comp_wba25_internal_flash_write(void *context, uint32_t address,
                                     const uint8_t *data, size_t length);

#endif
