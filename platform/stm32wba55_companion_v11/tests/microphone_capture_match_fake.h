#ifndef COMP_V11_MICROPHONE_CAPTURE_MATCH_FAKE_H
#define COMP_V11_MICROPHONE_CAPTURE_MATCH_FAKE_H
/* Board integration fixtures do not link the STM32 HAL. Preserve the new
 * capture liveness contract through their existing statistics port. The exact
 * production atomic implementation has its own PRIMASK/fault-counter model. */
bool comp_v11_microphone_hal_capture_matches(
    const comp_v11_microphone_hal_t *microphone,
    const comp_v11_microphone_stats_t *baseline)
{
    if(microphone==NULL || baseline==NULL)return false;
    comp_v11_microphone_stats_t current;
    comp_v11_microphone_hal_get_stats((comp_v11_microphone_hal_t *)microphone,&current);
    return current.running && current.stale_dma_halves==baseline->stale_dma_halves &&
        current.event_queue_overflows==baseline->event_queue_overflows &&
        current.processing_rejections==baseline->processing_rejections &&
        current.error_irqs==baseline->error_irqs;
}
void comp_v11_microphone_hal_fault_baseline(const comp_v11_microphone_hal_t *microphone,
                                             comp_v11_microphone_fault_baseline_t *out)
{
    if (!microphone || !out) return;
    comp_v11_microphone_stats_t stats;
    comp_v11_microphone_hal_get_stats((comp_v11_microphone_hal_t *)microphone,&stats);
    out->error_irqs=stats.error_irqs;out->event_queue_overflows=stats.event_queue_overflows;
    out->stale_dma_halves=stats.stale_dma_halves;out->processing_rejections=stats.processing_rejections;
}
bool comp_v11_microphone_hal_fault_baseline_matches(const comp_v11_microphone_hal_t *microphone,
                                             const comp_v11_microphone_fault_baseline_t *baseline)
{
    if (!microphone || !baseline) return false;
    comp_v11_microphone_stats_t stats;
    comp_v11_microphone_hal_get_stats((comp_v11_microphone_hal_t *)microphone,&stats);
    return stats.running && stats.error_irqs==baseline->error_irqs &&
        stats.event_queue_overflows==baseline->event_queue_overflows &&
        stats.stale_dma_halves==baseline->stale_dma_halves &&
        stats.processing_rejections==baseline->processing_rejections;
}
#endif
