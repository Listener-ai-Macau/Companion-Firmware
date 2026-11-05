#ifndef COMPANION_CPU_CODEC_IRQ_H
#define COMPANION_CPU_CODEC_IRQ_H
#include <stdbool.h>
#include <stdint.h>

/* The WBA radio uses RADIO and the software HASH vector. Classify only the
 * completed outer envelope, never charge a nested IRQ for a second time.
 * Exception numbers fit uint16_t; the packed identity fields make room for
 * the split within the original combined outer/codec observation storage. */
typedef struct {
    uint32_t current_us,peak_us,current_radio_us,peak_radio_us;
    uint16_t current_kind,peak_kind;
} comp_cpu_codec_irq_t;

static inline void comp_cpu_codec_irq_frame_begin(comp_cpu_codec_irq_t *s)
{
    s->current_us=0u;s->current_kind=0u;s->current_radio_us=0u;
}
static inline void comp_cpu_codec_irq_note_outer(comp_cpu_codec_irq_t *s,
    uint32_t elapsed,uint16_t kind,bool radio)
{
    if(elapsed>s->current_us){s->current_us=elapsed;s->current_kind=kind;}
    /* Saturate explicitly on an invalid/oversized accumulation. The report
     * refuses to derive a complement when this exceeds the measured IRQ sum. */
    if(radio)s->current_radio_us=elapsed>UINT32_MAX-s->current_radio_us?
        UINT32_MAX:s->current_radio_us+elapsed;
}
static inline void comp_cpu_codec_irq_peak(comp_cpu_codec_irq_t *s)
{
    s->peak_us=s->current_us;s->peak_kind=s->current_kind;
    s->peak_radio_us=s->current_radio_us;
}
#endif
