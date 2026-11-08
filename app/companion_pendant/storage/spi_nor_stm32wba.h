#ifndef COMPANION_SPI_NOR_STM32WBA_H
#define COMPANION_SPI_NOR_STM32WBA_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include "spi_nor_blank_cache.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef enum {
    COMPANION_SPI_NOR_STM32WBA_TARGET_WB55 = 54,
    COMPANION_SPI_NOR_STM32WBA_TARGET_WBA55 = 55,
    COMPANION_SPI_NOR_STM32WBA_TARGET_WBA65 = 65,
} companion_spi_nor_stm32wba_target_t;

typedef enum {
    COMPANION_SPI_NOR_STM32WBA_OK = 0,
    COMPANION_SPI_NOR_STM32WBA_PENDING = 1,
    COMPANION_SPI_NOR_STM32WBA_ERROR = -1,
    COMPANION_SPI_NOR_STM32WBA_TIMEOUT = -2,
    COMPANION_SPI_NOR_STM32WBA_UNSUPPORTED = -3,
    COMPANION_SPI_NOR_STM32WBA_BAD_PARAM = -4,
    COMPANION_SPI_NOR_STM32WBA_OUT_OF_RANGE = -5,
    COMPANION_SPI_NOR_STM32WBA_NOT_PROBED = -6,
} companion_spi_nor_stm32wba_status_t;

typedef bool (*companion_spi_nor_stm32wba_chip_select_fn_t)(
    void *context,
    bool active);

typedef bool (*companion_spi_nor_stm32wba_transfer_fn_t)(
    void *context,
    const uint8_t *transmit,
    uint8_t *receive,
    size_t length,
    uint32_t timeout_ms);

typedef uint32_t (*companion_spi_nor_stm32wba_now_ms_fn_t)(void *context);
typedef void (*companion_spi_nor_stm32wba_delay_ms_fn_t)(
    void *context,
    uint32_t delay_ms);

#ifndef COMPANION_WBA_RECLAIM_TIMING
#define COMPANION_WBA_RECLAIM_TIMING 0
#endif
#if COMPANION_WBA_RECLAIM_TIMING
/* Temporary consume-scoped observation. No NOR logging, policy or completion
 * change. WIP sample brackets use the driver's millisecond clock; elapsed
 * includes polling latency and is not a silicon minimum. Absent in release. */
typedef struct {
    uint32_t issued,completed,bytes,erase_elapsed_ms,busy_lower_ms,max_poll_gap_ms;
    uint32_t last_poll_ms,last_busy_lower_ms,program_calls,program_ms,interrupted;
    bool active;
} companion_spi_nor_reclaim_timing_t;
#endif

typedef struct {
    companion_spi_nor_stm32wba_target_t target;
    companion_spi_nor_stm32wba_chip_select_fn_t chip_select;
    companion_spi_nor_stm32wba_transfer_fn_t transfer;
    companion_spi_nor_stm32wba_now_ms_fn_t now_ms;
    companion_spi_nor_stm32wba_delay_ms_fn_t delay_ms;
    void *context;
    uint32_t transfer_timeout_ms;
    uint32_t page_program_timeout_ms;
    uint32_t sector_erase_timeout_ms;
    /* Optional owner-scoped progress after a BUSY status transaction has
     * deselected NOR, including the initial sub-2ms spin. No sleeping,
     * re-entering this NOR, storage mutation or premature completion. */
    void (*wait_progress)(void *context);
} companion_spi_nor_stm32wba_config_t;

typedef struct {
    uint32_t jedec_id;
    uint8_t manufacturer_id;
    uint8_t memory_type;
    uint8_t capacity_code;
    uint8_t status1;
    uint32_t size_bytes;
    uint32_t page_size;
    uint32_t sector_size;
    uint32_t sfdp_suspend_parameters, sfdp_suspend_instructions;
    uint8_t sfdp_bfp_dwords;
    bool erase_32k_supported;
} companion_spi_nor_stm32wba_info_t;

typedef struct {
    companion_spi_nor_stm32wba_config_t config;
    companion_spi_nor_stm32wba_info_t info;
    bool probed;
    bool last_probe_id_transfer_completed;
    uint32_t last_probe_jedec_id;
    /* One cooperative erase owns NOR until a status poll proves completion.
     * A command/transport error retains ownership until WIP is clear. */
    uint32_t erase_address;
    uint32_t erase_bytes;
    uint32_t erase_started_ms;
    uint32_t erase_phase_started_ms, erase_pause_started_ms, erase_run_since_ms;
    /* SFDP and the supported vendor status layout must BOTH qualify. These
     * timings include one extra tick because now_ms may cross a tick boundary
     * immediately after a command; an elapsed 1 ms is not a 1 ms minimum. */
    uint8_t suspend_wait_ms, resume_guard_ms, erase_phase;
    bool erase_suspend_supported;
    bool erase_active;
    bool erase_command_failed;
    companion_nor_blank_cache_t blank_cache;
#if COMPANION_WBA_RECLAIM_TIMING
    companion_spi_nor_reclaim_timing_t reclaim_timing;
#endif
} companion_spi_nor_stm32wba_t;

typedef struct {
    companion_spi_nor_stm32wba_t *nor;
    uint32_t base_address;
    uint32_t size_bytes;
} companion_spi_nor_stm32wba_partition_t;

bool companion_spi_nor_stm32wba_init(
    companion_spi_nor_stm32wba_t *nor,
    const companion_spi_nor_stm32wba_config_t *config);

bool companion_spi_nor_stm32wba_ready(
    const companion_spi_nor_stm32wba_t *nor);

/* Recovery preflight only. The caller must first hold exclusive access to
 * the whole NOR and stop all producers, update and radio storage users. This
 * observes the supported Winbond part without reset, resume, write or erase;
 * OK proves only the sampled ID/status, not that a failed write committed or
 * that the on-media catalogue is valid. An existing erase owner is retained. */
companion_spi_nor_stm32wba_status_t companion_spi_nor_stm32wba_recovery_observe(
    companion_spi_nor_stm32wba_t *nor);

const char *companion_spi_nor_stm32wba_status_name(
    companion_spi_nor_stm32wba_status_t status);

companion_spi_nor_stm32wba_status_t companion_spi_nor_stm32wba_probe(
    companion_spi_nor_stm32wba_t *nor,
    companion_spi_nor_stm32wba_info_t *out_info);

companion_spi_nor_stm32wba_status_t companion_spi_nor_stm32wba_wait_ready(
    companion_spi_nor_stm32wba_t *nor,
    uint32_t timeout_ms);

companion_spi_nor_stm32wba_status_t companion_spi_nor_stm32wba_read(
    companion_spi_nor_stm32wba_t *nor,
    uint32_t address,
    uint8_t *destination,
    size_t length);

/* Only a read-only radio stream may use this distinction. A transport
 * payload error is isolated only after the complete read header and a
 * successful CS release; no bytes from the failed read are valid. An active
 * erase, failed select/header/release or invalid state remains uncertain. */
companion_spi_nor_stm32wba_status_t companion_spi_nor_stm32wba_read_transient(
    companion_spi_nor_stm32wba_t *nor,uint32_t address,uint8_t *destination,
    size_t length,bool *released_read_failure);

companion_spi_nor_stm32wba_status_t companion_spi_nor_stm32wba_program(
    companion_spi_nor_stm32wba_t *nor,
    uint32_t address,
    const uint8_t *source,
    size_t length);

companion_spi_nor_stm32wba_status_t companion_spi_nor_stm32wba_erase_4k(
    companion_spi_nor_stm32wba_t *nor,
    uint32_t address);

companion_spi_nor_stm32wba_status_t companion_spi_nor_stm32wba_erase_64k(
    companion_spi_nor_stm32wba_t *nor,
    uint32_t address);

/* Start once, then perform one status poll per call. Repeat the exact address
 * and size (4 KiB, qualified 32 KiB, or 64 KiB); PENDING never means erased. Other
 * NOR reads/programs/probes/erases defer while this owner is active. */
companion_spi_nor_stm32wba_status_t companion_spi_nor_stm32wba_erase_step(
    companion_spi_nor_stm32wba_t *, uint32_t address, uint32_t bytes);

/* Largest supported aligned chunk wholly contained in an admitted range.
 * The caller still checks partition/recording ownership before erase_step. */
uint32_t companion_spi_nor_stm32wba_erase_chunk(
    const companion_spi_nor_stm32wba_t *, uint32_t address, uint32_t remaining_bytes);

/* Only poll/retire this exact existing erase owner. Never start, resume or
 * suspend an erase. A client whose write admission was revoked can finish
 * an already-completed operation without resuming it during capture. */
companion_spi_nor_stm32wba_status_t companion_spi_nor_stm32wba_erase_finish_poll(
    companion_spi_nor_stm32wba_t *, uint32_t address, uint32_t bytes);

/* Optional read-only qualification of the Winbond EF6018 status layout and
 * SFDP density/geometry/erase-suspend instructions/restrictions. Unsupported
 * devices retain the exclusive erase path. probe() calls this for EF6018;
 * an interrupted qualified suspend is resumed at startup, never reset away.
 * No guessed capability or JEDEC ID alone enables concurrent recording. */
companion_spi_nor_stm32wba_status_t companion_spi_nor_stm32wba_probe_erase_suspend(
    companion_spi_nor_stm32wba_t *);

/* Foreground, no waits/spin: request suspension, then poll to prove BUSY=0
 * AND SUS=1. PENDING/transport error retains the exact original erase owner.
 * Only after OK may normal read/program access OTHER sectors/blocks. Reads
 * and programs reject ANY overlap with the full owned erase range. No second
 * erase is allowed while suspended. The original erase_step automatically
 * resumes; BUSY=0 while SUS=1 is NEVER reported as an erase completion.
 * Callers with bool storage callbacks must preflight this API before invoking
 * them, rather than turn healthy PENDING into a recording I/O fault. */
companion_spi_nor_stm32wba_status_t companion_spi_nor_stm32wba_erase_suspend_step_bounded(
    companion_spi_nor_stm32wba_t *nor, uint32_t budget_ms);

companion_spi_nor_stm32wba_status_t companion_spi_nor_stm32wba_erase_suspend_step(
    companion_spi_nor_stm32wba_t *);
companion_spi_nor_stm32wba_status_t companion_spi_nor_stm32wba_erase_resume_step(
    companion_spi_nor_stm32wba_t *);
bool companion_spi_nor_stm32wba_erase_is_suspended(
    const companion_spi_nor_stm32wba_t *);
/* Cached range eligibility for a cooperative adapter, not a fresh hardware
 * status qualification. Normal read/program still validate SR1/SR2. The exact
 * erase owner remains retained even after natural completion is latched. */
bool companion_spi_nor_stm32wba_erase_access_ready(const companion_spi_nor_stm32wba_t *,
    uint32_t address,size_t length);

bool companion_spi_nor_stm32wba_partition_init(
    companion_spi_nor_stm32wba_partition_t *partition,
    companion_spi_nor_stm32wba_t *nor,
    uint32_t base_address,
    uint32_t size_bytes);

bool companion_spi_nor_stm32wba_partition_read(
    void *context,
    uint32_t partition_offset,
    uint8_t *destination,
    size_t length);

companion_spi_nor_stm32wba_status_t
companion_spi_nor_stm32wba_partition_program(
    companion_spi_nor_stm32wba_partition_t *partition,
    uint32_t partition_offset,
    const uint8_t *source,
    size_t length);

companion_spi_nor_stm32wba_status_t
companion_spi_nor_stm32wba_partition_erase_4k(
    companion_spi_nor_stm32wba_partition_t *partition,
    uint32_t partition_offset);

/* Erase only within the caller-owned range and partition. Uses a physically
 * aligned 64 KiB block when it fits, otherwise a 4 KiB sector. erased_bytes is
 * zero until WIP clears successfully; pending/error never advances a cursor. */
companion_spi_nor_stm32wba_status_t
companion_spi_nor_stm32wba_partition_erase_step(
    companion_spi_nor_stm32wba_partition_t *, uint32_t offset,
    uint32_t remaining_bytes, uint32_t *erased_bytes);

#ifdef __cplusplus
}
#endif

#endif /* COMPANION_SPI_NOR_STM32WBA_H */
