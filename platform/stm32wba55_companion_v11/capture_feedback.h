#ifndef COMP_V11_CAPTURE_FEEDBACK_H
#define COMP_V11_CAPTURE_FEEDBACK_H

#include <stdint.h>

typedef enum {
    COMP_CAPTURE_UNKNOWN=0, COMP_CAPTURE_IDLE, COMP_CAPTURE_PREPARING,
    COMP_CAPTURE_RECORDING, COMP_CAPTURE_PAUSED, COMP_CAPTURE_SAVING,
    COMP_CAPTURE_SAVED, COMP_CAPTURE_FULL, COMP_CAPTURE_ERROR, COMP_CAPTURE_UPDATING,
    COMP_CAPTURE_PAUSING, COMP_CAPTURE_RESUMING
} comp_capture_feedback_state_t;

enum {
    COMP_CAPTURE_MIC_RUNNING=1u,
    COMP_CAPTURE_MARK_PENDING=2u,
    COMP_CAPTURE_MARK_CONFIRMED=4u,
    COMP_CAPTURE_CAPACITY_KNOWN=8u,
    COMP_CAPTURE_UNSYNCED=16u,
    COMP_CAPTURE_ORIGINAL_SAVED=32u
};
enum {
    COMP_CAPTURE_FULL_SLOTS=1u,
    COMP_CAPTURE_FULL_EXTENT=2u,
    COMP_CAPTURE_FULL_STOP=4u,
    COMP_CAPTURE_FULL_NO_SEGMENTS=8u,
    COMP_CAPTURE_FULL_ALLOCATION=16u
};

/* A read-only projection of the existing owners, with no retained state or
 * GPIO/color assumption. MARK_CONFIRMED applies only to bookmark_request;
 * accepted requests are pending until the existing NOR owner reports OK.
 * CAPACITY_KNOWN excludes busy/stale snapshots. FULL may coexist with
 * ORIGINAL_SAVED: the last capture is safe but another cannot fit now.
 * FULL_STOP alone is a historical end cause, not proof that space is still full.
 * A future indicator adapter can detect edges in this view. It must not treat
 * a request, a stale count or a canceled prepared writer as a success pulse. */
typedef struct {
    uint32_t bookmark_request;
    uint8_t state,flags,full_reason,reserved;
} comp_capture_feedback_t;
_Static_assert(sizeof(comp_capture_feedback_t)==8u,"bounded Capture feedback view");

#endif
