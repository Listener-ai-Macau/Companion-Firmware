#ifndef COMP_V11_UPDATE_PRODUCT_H
#define COMP_V11_UPDATE_PRODUCT_H
#include "product_app.h"
#include "companion_gatt_stm32wb.h"
bool comp_v11_update_product_init(comp_v11_product_app_t *);
void comp_v11_update_product_poll(void);
/* Exact live next-block owner, read-only. Generic storage mounting still
 * excludes every erase; only continuation of this OTA may use its own owner. */
bool comp_v11_update_product_owns_erase(void);
bool comp_v11_update_product_busy(void);
/* A retained full package may drain existing BLE NVM before its reset.
 * This does not admit Flash writes during receive or microphone capture. */
bool comp_v11_update_product_reboot_pending(void);
/* Receiving a verified manifest's bytes, not verification/install/trial work.
 * Read-only admission includes the existing power and recorder idle gates. */
bool comp_v11_update_product_bulk_transfer(void);
void comp_v11_update_product_readiness(companion_gatt_ota_readiness_v1_t *);
/* Read-only screen phase(low8)/percent(high8,255 unknown). Received progress
 * is quantized to5% for the physical e-paper budget; it is not install success. */
uint16_t comp_v11_update_product_screen_status(void);
typedef struct {
    /* Manifest0 accepted,1 not ready,2 busy/power,3 authorization,
     *4 existing transaction,5 layout admission,6 durable receive begin. */
    uint32_t manifest_attempts,manifest_stage;
    uint32_t pka_failure_stage,pka_failure_status,pka_failure_error,pka_failures;
    /* HAL-tick latency (1ms quantization): receive plus FINISH pending record.
     * Async64 erase latency includes its suspensions and overlaps program_ms.
     * IRQ/stack progress is included; never sum these into payload/RF wall. */
    uint32_t program_calls,program_ms,erase4_calls,erase4_ms,erase64_calls,erase64_ms,io_flags;
} comp_v11_update_diagnostics_t;
typedef struct {
    /* Same existing BLE microsecond observer. SPI callbacks and safe stack
     * progress are disjoint children of program_us, not pure wire/CPU time.
     * prepare includes erasing; suspend is the access guard before program.
     * Both are outside program_us but inside the enclosing DATA call.
     * Flags:1 counter overflow,2 unexpected recursive program owner. */
    uint32_t program_us,program_spi_us,program_progress_us;
    uint32_t program_spi_calls,program_progress_calls;
    uint32_t data_prepare_us,data_suspend_us,program_observe_flags;
} comp_v11_update_program_diagnostics_t;
/* Cached scalars only; no PKA/RNG/NOR read or formatting in the hot path. */
const comp_v11_update_diagnostics_t *comp_v11_update_product_diagnostics(void);
const comp_v11_update_program_diagnostics_t *comp_v11_update_program_diagnostics(void);
#endif
