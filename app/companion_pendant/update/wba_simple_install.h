#ifndef COMPANION_WBA_SIMPLE_INSTALL_H
#define COMPANION_WBA_SIMPLE_INSTALL_H
#include "wba_simple_package.h"

/* Small records inside EXISTING dynamic metadata; no backup image, snapshot,
 * per-page progress journal or dedicated OTA partition. Current A/B is only
 * atomic metadata publication. It never selects an old image for rollback. */
#define COMP_SIMPLE_CURRENT_BYTES 192u
#define COMP_SIMPLE_PENDING_BYTES 196u

typedef struct {
    bool (*nor_read)(void *,uint32_t,uint8_t *,size_t);
    bool (*nor_erase)(void *,uint32_t);
    bool (*nor_write)(void *,uint32_t,const uint8_t *,size_t);
    bool (*flash_read)(void *,uint32_t,uint8_t *,size_t);
    bool (*flash_erase)(void *,uint32_t);
    bool (*flash_write)(void *,uint32_t,const uint8_t *,size_t);
    void (*keep_alive)(void *);
    void *context;
} comp_wba_simple_install_ports_t;

typedef struct {
    comp_wba_simple_limits_t limits;
    comp_wba_update_p256_trust_t trust;
    comp_wba_simple_install_ports_t ports;
    uint32_t current[2],pending,flash_page_bytes;
    uint32_t minimum_app,minimum_resources;
} comp_wba_simple_install_config_t;

typedef enum {
    COMP_SIMPLE_BOOT_RECOVERY=0,
    COMP_SIMPLE_BOOT_CURRENT=1,
    COMP_SIMPLE_BOOT_INSTALLED=2,
} comp_wba_simple_boot_result_t;
typedef enum {
    COMP_SIMPLE_ERROR_NONE=0,COMP_SIMPLE_ERROR_CONFIG=1,
    COMP_SIMPLE_ERROR_CURRENT=2,COMP_SIMPLE_ERROR_PENDING=3,
    COMP_SIMPLE_ERROR_AUTH=4,COMP_SIMPLE_ERROR_FLASH=5,
    COMP_SIMPLE_ERROR_RESOURCES=6,COMP_SIMPLE_ERROR_DESTINATION=7,
    COMP_SIMPLE_ERROR_PUBLICATION=8,
} comp_wba_simple_boot_error_t;

/* Factory initial provisioning supplies the signed current package header
 * AFTER checking installed destinations. App only publishes pending after a
 * complete DOV1 download; an incomplete/torn pending write never starts copy. */
bool comp_wba_simple_current_record(uint8_t out[COMP_SIMPLE_CURRENT_BYTES],
    const uint8_t header[COMP_WBA_SIMPLE_HEADER_BYTES]);
bool comp_wba_simple_pending_record(uint8_t out[COMP_SIMPLE_PENDING_BYTES],
    uint32_t file_base,uint32_t file_bytes,
    const uint8_t header[COMP_WBA_SIMPLE_HEADER_BYTES]);

/* Synchronous resident Boot, no receive/resume protocol. Fully verifies the
 * candidate BEFORE any destination erase. Power loss retains the complete
 * candidate+pending record; next entry repeats installation from the start.
 * scratch>=512; caller feeds IWDG through keep_alive. Only CURRENT/INSTALLED
 * permit a jump. Error never erases the pending full package.
 * COMP_WBA_SIMPLE_ALLOW_4K_INTERNAL_FLASH is an opt-in geometry preparation,
 * not a target port. A 4 KiB target still requires its own correctly bounded
 * flash_erase/flash_write implementation, target identity and memory layout;
 * enabling this switch must not be used to flash the WBA55 image on WBA25. */
comp_wba_simple_boot_result_t comp_wba_simple_boot_run(
    const comp_wba_simple_install_config_t *,uint8_t *scratch,size_t,
    comp_wba_simple_boot_error_t *);
#endif
