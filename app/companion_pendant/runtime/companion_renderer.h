#ifndef COMPANION_RUNTIME_RENDERER_H
#define COMPANION_RUNTIME_RENDERER_H
#include "companion_runtime.h"
#include "companion_reply_layout.h"
typedef bool (*comp_runtime_read_state_fn)(void *, const char *state_id, uint8_t frame[5000]);
typedef bool (*comp_runtime_render_progress_fn)(void *);
typedef bool (*comp_runtime_read_ui_fn)(void *, uint32_t, uint8_t *, size_t);
#define COMP_RUNTIME_WBA_FACE_CACHE_BYTES 1664u
#ifndef COMP_RUNTIME_WBA_FACE_REFERENCES
#define COMP_RUNTIME_WBA_FACE_REFERENCES 0
#endif
#define COMP_RUNTIME_FACE_REFERENCE_BYTES 112u
#define COMP_RUNTIME_BLINK_GLYPH_BYTES 256u
#if COMP_RUNTIME_WBA_FACE_REFERENCES && (!COMPANION_WBA_RESOURCE_PROFILE || !COMPANION_WBA_UI_EXTERNAL)
#error "Face references require the immutable external authored WBA70+ bank"
#endif
#if COMPANION_WBA_RESOURCE_PROFILE
/* The bitmap-cache fallback uses the complete UI70 bank's1583-byte maximum.
 * Keep visible and pending identities distinct; controller OLD/CURRENT
 * remain separate full5000-byte buffers in the presenter owner. */
#define COMP_RUNTIME_FACE_CACHE_BYTES COMP_RUNTIME_WBA_FACE_CACHE_BYTES
#else
#define COMP_RUNTIME_FACE_CACHE_BYTES 5000u
#endif
typedef struct {
    comp_runtime_read_state_fn read_state;
    void *context;
#if COMPANION_WBA_UI_EXTERNAL
    comp_runtime_read_ui_fn read_ui;
#endif
    /* Bounded CPU-only drawing must yield too: a NOR cache hit is not an
     * audio checkpoint. Returning false aborts this uncommitted frame. */
    comp_runtime_render_progress_fn progress;
    void *progress_context;
    /* Face caches/references contain authored base only. Status/recording/blink never
     * become the next emotion's source and cannot reset its life clock. */
#if COMP_RUNTIME_WBA_FACE_REFERENCES
    /* Authored resources are immutable until paired OTA reboot. A bounded
     * attention-placement prefix belongs to the same cached face identity.
     * Pending/visible identities remain separate even when render fails. */
    uint8_t base[COMP_RUNTIME_FACE_REFERENCE_BYTES], pending_base[COMP_RUNTIME_FACE_REFERENCE_BYTES];
#else
    uint8_t base[COMP_RUNTIME_FACE_CACHE_BYTES], pending_base[COMP_RUNTIME_FACE_CACHE_BYTES];
#endif
    uint16_t base_bytes, pending_base_bytes;
    uint32_t token;
    comp_browser_family_t base_family;
    comp_browser_family_t pending_family;
    bool base_valid, pending_base_valid, pending;
    /* Track authored eyelids separately from temporary natural blinks. Only
     * a successful visible commit changes these masks (left=1, right=2). */
    uint8_t base_eye_closed_mask, pending_base_eye_closed_mask;
    uint8_t visible_eye_closed_mask, pending_eye_closed_mask;
    bool pending_opens_eyes;
    uint32_t base_pet_seed, pending_pet_seed;
    /* Ornament metadata: low2 bits original variation, next3 bits the actual
     * authored face accent; committed with the clean face, never status RNG. */
    uint8_t base_pet_variant, pending_pet_variant;
    int8_t base_pet_float, pending_pet_float;
} comp_runtime_renderer_t;
void comp_runtime_renderer_init(comp_runtime_renderer_t *, comp_runtime_read_state_fn, void *);
void comp_runtime_renderer_set_progress(comp_runtime_renderer_t *, comp_runtime_render_progress_fn, void *);
void comp_runtime_renderer_set_ui_reader(comp_runtime_renderer_t *, comp_runtime_read_ui_fn);
bool comp_runtime_renderer_render(void *, const comp_runtime_frame_t *, uint8_t frame[5000]);
bool comp_runtime_renderer_complete(comp_runtime_renderer_t *, uint32_t token, bool visible);
#endif
