#include "companion_silk_live_fast.h"

/* Default quality (0): short/meeting capture ASR-viable until max_s policy enables FAST. */
static volatile int s_companion_silk_live_fast = 0;

void companion_silk_live_fast_set(int enabled)
{
    s_companion_silk_live_fast = enabled ? 1 : 0;
}

int companion_silk_live_fast_enabled(void)
{
#if defined(COMPANION_SILK_LIVE_FAST) && COMPANION_SILK_LIVE_FAST
    return s_companion_silk_live_fast;
#else
    (void)s_companion_silk_live_fast;
    return 0;
#endif
}

void companion_silk_live_fast_configure_max_s(uint32_t max_seconds)
{
    /*
     * LIVE_FAST encode for all live-mic lengths while quality path uses CIC3
     * (density→flat noise; CIC3+full SILK under-ran realtime, drops high).
     * Prefer clean CIC3 PCM + LIVE_FAST SILK over density + full SILK.
     * Soak (>=180s) unchanged (also LIVE_FAST).
     */
    (void)max_seconds;
    companion_silk_live_fast_set(1);
}
