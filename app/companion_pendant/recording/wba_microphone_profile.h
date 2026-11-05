#ifndef COMPANION_WBA_MICROPHONE_PROFILE_H
#define COMPANION_WBA_MICROPHONE_PROFILE_H
#include "wba_pdm_capture.h"

/* Existing recorder setting: 0=voice, 1=meeting. Calibration is a fixed
 * directional candidate, not speaker identification or meeting denoising.
 * Caller owns the microphone; running must be its actual DMA liveness.
 * No allocation, new frame, clock, storage or callback work. START's existing
 * discarded startup interval resets/warms both filters and delay history. */
static inline bool comp_wba_microphone_profile_select(comp_wba_pdm_capture_t *c,
    bool running,uint8_t profile,const comp_wba_dual_mic_config_t *calibration)
{
    if(running || profile>1u || !comp_wba_pdm_capture_ready(c) ||
       (calibration && !comp_wba_dual_mic_config_valid(calibration)))return false;
    if(profile==0u && calibration) {
        c->config.output=COMP_WBA_PDM_OUTPUT_BEAMFORM;
        c->config.selected_only=false;
        c->config.dual_mic=*calibration;
        c->dual_mic.config=*calibration;
    } else {
        c->config.output=COMP_WBA_PDM_OUTPUT_LEFT;
        c->config.selected_only=c->config.observe_pair_frame==NULL;
    }
    return true;
}
#endif
