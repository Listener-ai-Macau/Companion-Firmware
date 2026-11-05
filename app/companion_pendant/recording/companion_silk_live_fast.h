#pragma once

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/**
 * Runtime SILK LIVE_FAST gate (compile still needs COMPANION_SILK_LIVE_FAST=1
 * for the code paths to exist).
 *
 * Policy:
 * - max_seconds >= 180: enable LIVE_FAST for long continuous soak realtime.
 * - max_seconds < 180: full SILK (pitch + multi-iter NSQ + LBRR) for meeting ASR.
 */
void companion_silk_live_fast_configure_max_s(uint32_t max_seconds);
void companion_silk_live_fast_set(int enabled);
int companion_silk_live_fast_enabled(void);

#ifdef __cplusplus
}
#endif
