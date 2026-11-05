#ifndef COMPANION_BITMAP_STREAM_H
#define COMPANION_BITMAP_STREAM_H
#include <stdint.h>

/* Trusted build-generated bitmap. Decode a byte once before painting its bits;
 * no heap, frame scratch, NOR read or persistence work in the renderer. */
typedef struct {
    const uint8_t *next;
    uint8_t remaining, white;
} comp_bitmap_stream_t;

static inline uint8_t comp_bitmap_stream_byte(comp_bitmap_stream_t *s)
{
#if COMPANION_WBA_RECORDING_UI_PACKED
    if (!s->remaining) {
        const uint8_t token = *s->next++;
        s->remaining = (uint8_t)((token & 127u) + 1u);
        s->white = (uint8_t)(token & 128u);
    }
    --s->remaining;
    return s->white ? 255u : *s->next++;
#else
    return *s->next++;
#endif
}
#endif
