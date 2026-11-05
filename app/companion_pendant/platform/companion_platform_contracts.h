#ifndef COMPANION_PLATFORM_CONTRACTS_H
#define COMPANION_PLATFORM_CONTRACTS_H

#include <stdbool.h>
#include "denzic_audio_transport_v1.h"

#ifdef __cplusplus
extern "C" {
#endif

bool companion_platform_contract_probe(void);
void companion_platform_audio_transport_init(
    denzic_audio_transport_v1_pacing_t *pacing);
uint32_t companion_platform_audio_transport_note_pcm_sent(
    denzic_audio_transport_v1_pacing_t *pacing,
    uint32_t packet_pcm_bytes);

#ifdef __cplusplus
}
#endif

#endif
