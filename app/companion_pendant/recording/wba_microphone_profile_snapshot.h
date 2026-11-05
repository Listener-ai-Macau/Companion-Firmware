#ifndef COMP_WBA_MICROPHONE_PROFILE_SNAPSHOT_H
#define COMP_WBA_MICROPHONE_PROFILE_SNAPSHOT_H
#include "wba_pdm_capture.h"
#include "companion_recording_audio_profile.h"

/* Pure description of the actual selected filter configuration. No callbacks,
 * allocation or I/O. Capture remains mono; mask3 only means both were filtered. */
static inline bool comp_wba_microphone_profile_snapshot(const comp_wba_pdm_capture_t *c,
    uint8_t profile,uint32_t version,const uint8_t source[20],const uint8_t calibration[32],comp_rec_audio_profile_t *out)
{
    if(!out || !source || !calibration || !comp_wba_pdm_capture_ready(c))return false;
    comp_rec_audio_profile_t p={0};p.output=(uint8_t)c->config.output;p.recorder_profile=profile;
    p.filtered_mask=comp_wba_pdm_capture_channel_mask(c);p.gain_q15=c->config.gain_q15;
    p.inversion_flags=(uint8_t)((c->config.invert_left?1u:0u)|(c->config.invert_right?2u:0u));
    p.right_gain_q15=32768u;p.firmware_version=version;p.decimation=c->config.decimation;
    p.layout=(uint8_t)c->config.layout;p.bit_order=(uint8_t)c->config.bit_order;memcpy(p.firmware_source,source,20u);
    if(c->config.output==COMP_WBA_PDM_OUTPUT_BEAMFORM){
        p.delay_q8=c->dual_mic.config.delay_q8;p.right_gain_q15=c->dual_mic.config.right_gain_q15;
        if(c->dual_mic.config.invert_right)p.inversion_flags|=4u;
        memcpy(p.calibration_sha256,calibration,32u);
    }
    if(!comp_rec_audio_profile_valid(&p))return false;
    *out=p;return true;
}
#endif
