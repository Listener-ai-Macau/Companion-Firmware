#ifndef COMPANION_V11_MICROPHONE_HAL_H
#define COMPANION_V11_MICROPHONE_HAL_H

#include <stdbool.h>
#include <stdint.h>

#include "stm32wbaxx_hal.h"
#include "wba_pdm_capture.h"
#include "companion_duration_stats.h"

#ifdef __cplusplus
extern "C" {
#endif

/* SPH0655 normal mode starts at 1.1 MHz. 1.536 MHz / 96 retains 16 kHz
 * PCM and the existing 10 ms foreground deadline without changing speaker PLL. */
#define COMP_V11_MIC_DECIMATION 96u
#define COMP_V11_MIC_RAW_HALF_BYTES \
    (COMP_WBA_PDM_PCM_FRAME_SAMPLES * COMP_V11_MIC_DECIMATION * 2u / 8u)
#define COMP_V11_MIC_COPY_BYTES 256u
#define COMP_V11_MIC_RAW_DMA_BYTES (2u * COMP_V11_MIC_RAW_HALF_BYTES)
#define COMP_V11_MIC_DMA_TRANSFER_HALFWORDS \
    (COMP_V11_MIC_RAW_DMA_BYTES / sizeof(uint16_t))
#define COMP_V11_MIC_EVENT_QUEUE_CAPACITY 4u
#define COMP_V11_MIC_SAI_MCKDIV 16u
#define COMP_V11_MIC_NOMINAL_KERNEL_HZ 49151855u
#define COMP_V11_MIC_NOMINAL_SAI_BIT_CLOCK_HZ \
    (COMP_V11_MIC_NOMINAL_KERNEL_HZ / COMP_V11_MIC_SAI_MCKDIV)
#define COMP_V11_MIC_NOMINAL_PDM_HZ \
    (COMP_V11_MIC_NOMINAL_SAI_BIT_CLOCK_HZ / 2u)

typedef enum {
    COMP_V11_MIC_POLL_IDLE = 0,
    COMP_V11_MIC_POLL_PROCESSED,
    COMP_V11_MIC_POLL_DROPPED,
    COMP_V11_MIC_POLL_ERROR,
} comp_v11_microphone_poll_result_t;

typedef struct {
    uint32_t sequence;
    uint8_t half;
} comp_v11_microphone_event_t;

typedef struct {
    uint32_t starts;
    uint32_t stops;
    uint32_t rx_half_irqs;
    uint32_t rx_complete_irqs;
    uint32_t error_irqs;
    uint32_t ignored_callbacks;
    uint32_t event_queue_overflows;
    uint32_t startup_halves_discarded;
    uint32_t stale_dma_halves;
    uint32_t processed_dma_halves;
    uint32_t processing_rejections;
    uint32_t last_hal_error;
    uint32_t configured_pdm_clock_hz;
    bool initialized;
    bool running;
    comp_wba_pdm_stats_t processing;
} comp_v11_microphone_stats_t;

/* Capture fault baseline stores exactly the counters compared by the live
 * recording guard. The full diagnostic statistics remain available separately. */
typedef struct {
    uint32_t error_irqs, event_queue_overflows, stale_dma_halves, processing_rejections;
} comp_v11_microphone_fault_baseline_t;

typedef struct {
    SAI_HandleTypeDef sai;
    DMA_HandleTypeDef dma;
    DMA_NodeTypeDef dma_node;
    DMA_QListTypeDef dma_queue;
    comp_wba_pdm_capture_t processing;

    /* Word storage guarantees the halfword DMA alignment required by SAI. */
#if COMPANION_WBA_CE_SHARED_CAPTURE
    uint32_t *raw_dma_words;
#else
    uint32_t raw_dma_words[COMP_V11_MIC_RAW_DMA_BYTES / sizeof(uint32_t)];
#endif
    /* A noinline foreground frame snapshots one half on the existing stack.
     * It returns before Opus, so no permanent duplicate raw buffer is held. */

    volatile comp_v11_microphone_event_t events[COMP_V11_MIC_EVENT_QUEUE_CAPACITY];
    volatile uint32_t latest_half_sequence[2];
    volatile uint32_t next_sequence;
    volatile uint32_t last_hal_error;
    volatile uint32_t rx_half_irqs;
    volatile uint32_t rx_complete_irqs;
    volatile uint32_t error_irqs;
    volatile uint32_t ignored_callbacks;
    volatile uint32_t event_queue_overflows;
    volatile uint8_t event_head;
    volatile uint8_t event_tail;
    volatile uint8_t writing_half;
    uint8_t startup_halves_remaining;
    volatile bool error_pending;
    volatile bool running;

    uint32_t starts;
    uint32_t stops;
    uint32_t stale_dma_halves;
    uint32_t startup_halves_discarded;
    uint32_t processed_dma_halves;
    uint32_t processing_rejections;
    uint32_t configured_pdm_clock_hz;
    bool initialized;
    /* Only a failed partial start owns this bounded foreground cleanup. */
    bool partial_start_cleanup;
    uint8_t partial_stop_attempts;
    uint32_t partial_stop_due_ms;
    comp_duration_stats_t pdm_duration;
    /* Optional cooperative board policy. NULL preserves standalone behavior;
     * a false result retains the pending DMA event, never discards samples. */
    bool (*conversion_window)(uint32_t dma_remaining_bytes,uint32_t half_bytes);
} comp_v11_microphone_hal_t;

/* Configures only SAI1 Block A and GPDMA1 Channel 1. The caller must already
 * configure PA9/SAI1_CK1 and PA10/SAI1_D1 AF3 and the shared SAI kernel clock.
 * The PDM config must use decimation 96 because each DMA half is sized for
 * exactly one 160-sample frame at a nominal 1.536 MHz PDM clock. */
bool comp_v11_microphone_hal_init(
    comp_v11_microphone_hal_t *microphone,
    const comp_wba_pdm_config_t *processing_config);
bool comp_v11_microphone_hal_start(comp_v11_microphone_hal_t *microphone);
bool comp_v11_microphone_hal_stop(comp_v11_microphone_hal_t *microphone);

/* Processes at most one completed 10 ms half and invokes the configured PCM
 * callback only from foreground/task context. */
comp_v11_microphone_poll_result_t comp_v11_microphone_hal_poll(
    comp_v11_microphone_hal_t *microphone);
/* Read-only DMA phase admission. Pending capture/error or an imminent
 * half boundary takes priority over one non-preemptible encoder call. */
bool comp_v11_microphone_hal_encode_window(comp_v11_microphone_hal_t *microphone);
bool comp_v11_microphone_hal_io_window(comp_v11_microphone_hal_t *microphone);
/* Capture hot path: compare only liveness/fault counters atomically. Full
 * diagnostic/filter statistics remain available through get_stats(). */
void comp_v11_microphone_hal_fault_baseline(const comp_v11_microphone_hal_t *,
                                             comp_v11_microphone_fault_baseline_t *);
bool comp_v11_microphone_hal_fault_baseline_matches(const comp_v11_microphone_hal_t *,
                                             const comp_v11_microphone_fault_baseline_t *);
bool comp_v11_microphone_hal_capture_matches(
    const comp_v11_microphone_hal_t *microphone,
    const comp_v11_microphone_stats_t *baseline);
void comp_v11_microphone_hal_get_stats(
    comp_v11_microphone_hal_t *microphone,
    comp_v11_microphone_stats_t *stats);

SAI_HandleTypeDef *comp_v11_microphone_hal_sai_handle(
    comp_v11_microphone_hal_t *microphone);
DMA_HandleTypeDef *comp_v11_microphone_hal_dma_handle(
    comp_v11_microphone_hal_t *microphone);

/* Forwarders for the board's existing aggregate IRQ and HAL callbacks. They
 * never run PDM conversion or invoke the PCM callback. The callback forwarders
 * return false when hsai belongs to another SAI block. */
void comp_v11_microphone_hal_dma_irq(comp_v11_microphone_hal_t *microphone);
void comp_v11_microphone_hal_sai_irq(comp_v11_microphone_hal_t *microphone);
bool comp_v11_microphone_hal_on_rx_half(
    comp_v11_microphone_hal_t *microphone, SAI_HandleTypeDef *hsai);
bool comp_v11_microphone_hal_on_rx_complete(
    comp_v11_microphone_hal_t *microphone, SAI_HandleTypeDef *hsai);
bool comp_v11_microphone_hal_on_error(
    comp_v11_microphone_hal_t *microphone, SAI_HandleTypeDef *hsai);

#ifdef __cplusplus
}
#endif

#endif /* COMPANION_V11_MICROPHONE_HAL_H */
