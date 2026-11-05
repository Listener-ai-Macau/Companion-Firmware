#ifndef COMP_MOTION_EVENTS_H
#define COMP_MOTION_EVENTS_H
#include "lsm6dso.h"
#include "imu_screen_axes.h"
#define COMP_MOTION_PICKUP 1u
#define COMP_MOTION_SHAKE 2u
#define COMP_MOTION_ORIENTATION_CHANGED 4u
/* Activity followed by stable acceleration; not proof of being on a table. */
#define COMP_MOTION_SETTLED 8u
/* Sustained movement, not a claim that a pocket/person was identified. */
#define COMP_MOTION_CARRIED 16u
#define COMP_MOTION_CARRY_ENDED 32u
#define COMP_MOTION_TILT_CHANGED 64u
typedef enum {
    COMP_MOTION_TILT_CENTER, COMP_MOTION_TILT_LEFT, COMP_MOTION_TILT_RIGHT,
    COMP_MOTION_TILT_UP, COMP_MOTION_TILT_DOWN, COMP_MOTION_TILT_INVERTED,
    COMP_MOTION_TILT_UNKNOWN = 255u
} comp_motion_tilt_t;
typedef struct {
    int16_t gravity_mg[3];
    uint8_t orientation;
    uint8_t candidate_orientation;
    uint32_t still_since_ms;
    uint32_t event_ms;
    uint32_t orientation_since_ms;
    uint32_t sample_ms;
    bool initialized : 1;
    bool stationary : 1;
    bool has_event : 1;
    bool settle_pending : 1;
    bool carried : 1;
    bool tilt_initialized : 1;
    bool last_was_pickup : 1;
    bool shake_gyro : 1;
    uint8_t tilt, candidate_tilt;
    /* Signed axis codes for screen-right/up, front sign, verified bit. */
    uint8_t screen_axes;
    uint16_t movement_ms;
    /* Direction/reversals and bounded 10ms age/dwell, in the former padding.
     * Never replay a gesture across a shared-bus or sleep sampling gap. */
    uint16_t shake_history;
} comp_motion_events_t;
void comp_motion_events_init(comp_motion_events_t *motion);
/* Signed sensor axis = axis*2+sign+1 (1=+X,2=-X,...6=-Z).
 * All three must refer to different axes. Only call with a verified board
 * mounting profile; init leaves tilt UNKNOWN instead of guessing directions.
 * This maps coordinates, not bias calibration or persistent settings. */
bool comp_motion_events_set_screen_axes(comp_motion_events_t *motion,
    uint8_t screen_right, uint8_t screen_up, uint8_t screen_front);
/* Restore explicit packed profile from durable settings; zero clears it.
 * Changing a profile rebaselines tilt, without synthesizing an input event. */
bool comp_motion_events_set_packed_axes(comp_motion_events_t *, uint8_t packed);
/* Orientation = dominant axis * 2 + sign, 0 unknown, 1..6.
 * Thresholds are provisional product tuning, not a calibrated IMU frame.
 * Events never directly change recording/emotion state. Consumer owns policy. */
uint8_t comp_motion_events_update(comp_motion_events_t *motion, const comp_imu_sample_t *sample);
#endif
