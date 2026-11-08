#ifndef COMPANION_V11_CAPTURE_ENCODE_WINDOW_H
#define COMPANION_V11_CAPTURE_ENCODE_WINDOW_H

#include <stdbool.h>
#include <stdint.h>

/* A DMA half contains 10 ms of unchanged 16 kHz PCM. A foreground poll's
 * duration does not say when the next half becomes ready: do not begin a
 * non-preemptible encoder immediately before that boundary. These admission
 * budgets include the measured encoder/PDM upper bounds and 1 ms headroom;
 * they do not change the separate 10 ms hard service deadline. */
#define COMP_V11_CAPTURE_HALF_MS 10u
#define COMP_V11_CAPTURE_ENCODE_BUDGET_MS 7u
#define COMP_V11_CAPTURE_CONVERT_BUDGET_MS 4u
#define COMP_V11_CAPTURE_DISPATCH_HEADROOM_MS 1u
/* Peripheral/GAP work retains its original independent4ms DMA headroom. */
#define COMP_V11_CAPTURE_IO_GUARD_MS 4u
#define COMP_V11_CAPTURE_ENCODE_GUARD_MS \
    (COMP_V11_CAPTURE_ENCODE_BUDGET_MS + COMP_V11_CAPTURE_CONVERT_BUDGET_MS + \
     COMP_V11_CAPTURE_DISPATCH_HEADROOM_MS - COMP_V11_CAPTURE_HALF_MS)

/* A first10ms PCM half is a bounded RAM staging step, not opus_encode().
 * It may follow the measured PDM conversion without waiting for an8ms codec
 * window. The product still performs its unchanged10ms deadline check after
 * the work; actual packet encoding retains the original stricter admission. */
static inline bool comp_v11_capture_work_window_open(uint32_t elapsed_ms,
    bool pcm_staging_pending,bool encode_window_open)
{
    return pcm_staging_pending ? elapsed_ms<=5u : elapsed_ms<=2u && encode_window_open;
}

static inline bool comp_v11_capture_guarded_window_open(
    uint32_t dma_remaining_bytes, uint32_t half_bytes,
    uint8_t published_writing_half, bool dma_event_pending,uint32_t guard_ms)
{
    if (dma_event_pending || half_bytes == 0u ||
        half_bytes > UINT32_MAX / 2u || dma_remaining_bytes == 0u ||
        dma_remaining_bytes > 2u * half_bytes || published_writing_half > 1u ||
        guard_ms>COMP_V11_CAPTURE_HALF_MS)
        return false;
    const uint8_t hardware_writing_half =
        (uint8_t)(dma_remaining_bytes > half_bytes ? 0u : 1u);
    /* The counter can cross a boundary before its IRQ publishes the half.
     * Give that interrupt/capture work priority over an encode too. */
    if (hardware_writing_half != published_writing_half) return false;
    const uint32_t bytes_to_boundary = hardware_writing_half == 0u ?
        dma_remaining_bytes - half_bytes : dma_remaining_bytes;
    const uint32_t guard_bytes = (uint32_t)(
        ((uint64_t)half_bytes * guard_ms +
         COMP_V11_CAPTURE_HALF_MS - 1u) / COMP_V11_CAPTURE_HALF_MS);
    return bytes_to_boundary > guard_bytes;
}
static inline bool comp_v11_capture_encode_window_open(
    uint32_t remaining,uint32_t half,uint8_t writing_half,bool pending)
{
    return comp_v11_capture_guarded_window_open(remaining,half,writing_half,pending,
        COMP_V11_CAPTURE_ENCODE_GUARD_MS);
}

#endif
