#ifndef COMPANION_V11_SERVICES_H
#define COMPANION_V11_SERVICES_H
#include "companion_v1_features.h"
#include "lsm6dso.h"
#include "speaker_playback.h"
enum { COMP_V11_SPEAKER_ERROR_IO = 1u, COMP_V11_SPEAKER_ERROR_BUSY = 3u };
typedef struct {
    comp_speaker_t *speaker;
    comp_lsm6dso_t *imu;
    const comp_imu_sample_t *sample;
    companion_gatt_speaker_status_v1_t speaker_status;
    /* One bounded, explicit find owner. Never reuse this ID for another run. */
    uint32_t find_request_id, find_started_ms, find_next_cue_ms, find_cue_generation;
    bool find_active, find_cue_inflight;
    uint8_t motion_flags;
    bool speaker_available, prompt_inflight, playback_inhibited;
} comp_v11_services_t;
/* Bind once from the foreground owner. Refresh with the existing V1 product
 * task; this adapter does not initialize a radio or publish GATT itself. */
void comp_v11_services_bind(comp_v11_services_t *services, companion_v1_features_t *features,
                            comp_speaker_t *speaker, bool speaker_available,
                            comp_lsm6dso_t *imu, const comp_imu_sample_t *sample);
#endif
