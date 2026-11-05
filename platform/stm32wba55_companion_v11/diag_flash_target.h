#ifndef COMP_V11_DIAG_FLASH_TARGET_H
#define COMP_V11_DIAG_FLASH_TARGET_H
#include "product_app.h"
#include "diag_flash_journal.h"
#ifndef COMP_V11_DIAG_FLASH_ENABLED
#define COMP_V11_DIAG_FLASH_ENABLED 0
#endif
#if COMP_V11_DIAG_FLASH_ENABLED
comp_diag_flash_data_t comp_v11_diag_flash_snapshot(void);
void comp_v11_diag_flash_boot(comp_v11_hal_t *,uint32_t,const comp_diag_flash_data_t *);
void comp_v11_diag_flash_replay(comp_v11_hal_t *);
void comp_v11_diag_flash_dump(comp_v11_hal_t *);
void comp_v11_diag_flash_heartbeat(const comp_v11_product_app_t *,uint32_t,uint32_t);
#endif
#endif
