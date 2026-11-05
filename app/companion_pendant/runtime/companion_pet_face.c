#include "companion_pet_face.h"

/* The renderer has already read an authored UI67 resource for the exact
 * family, gaze direction or reaction phase. Keep that complete face intact.
 * Timing, response choice, seed and ornaments remain owned by the runtime.
 * Procedural face replacement used one shared eye/curve recipe for distinct
 * authored expressions; keeping the anchors alone did not retain the style.
 * P21 removes the P17/P20 mouth overwrite: even an isolated replacement
 * changed the authored expression. Refined bitmap candidates must first be
 * reviewed as whole faces and phrases before entering the resource bank.
 * Gaze, wink, brow and mouth acting continue using the authored frame selected
 * above; this hook must not erase or redraw its anatomy. */

bool comp_pet_face_draw(uint8_t frame[5000], const comp_runtime_frame_t *f,
    bool (*progress)(void *), void *context)
{
    if (!frame || !f || (unsigned)f->family >= 10u) return false;
    return progress == NULL || progress(context);
}

/* Match the original UI67 authored reaction assets, including wink and
 * closed-eye poses. This is the resource renderer's existing closed-eye map,
 * rather than the P09 procedural expression policy. */
uint8_t comp_pet_face_closed(const comp_runtime_frame_t *f)
{
    if (f->family == COMP_BROWSER_FAMILY_SLEEPY) return 3u;
    if (f->kind != COMP_RUNTIME_FRAME_REACTION || !f->reaction_expression ||
        f->reaction_pose_phase != 1u) return 0u;
    /* Spatial attention uses the existing open directional whole face.
     * Affectionate warm/up/down eyelids otherwise replace a tilt's gaze
     * with a centred closed-eye pat, even when its coordinates are retained.
     * A genuinely sleepy family above still keeps its authored closed eyes. */
    if (f->pet_interaction == COMP_PET_TILT) return 0u;
    if (f->family == COMP_BROWSER_FAMILY_WARM &&
        (f->reaction_zone == COMP_BROWSER_TAP_ZONE_UP ||
         f->reaction_zone == COMP_BROWSER_TAP_ZONE_DOWN)) return 3u;
    if (f->family == COMP_BROWSER_FAMILY_DELIGHTED &&
        f->reaction_zone == COMP_BROWSER_TAP_ZONE_CENTER) return 3u;
    if (f->family == COMP_BROWSER_FAMILY_BASHFUL) {
        if (f->reaction_zone == COMP_BROWSER_TAP_ZONE_DOWN) return 3u;
        /* The UI64+ left reaction is authored with open eyes. */
        if (f->reaction_zone == COMP_BROWSER_TAP_ZONE_LEFT) return 0u;
    }
    if (f->family == COMP_BROWSER_FAMILY_PLAYFUL) {
        if (f->reaction_zone == COMP_BROWSER_TAP_ZONE_LEFT) return 1u;
        if (f->reaction_zone == COMP_BROWSER_TAP_ZONE_RIGHT) return 2u;
    }
    return 0u;
}
