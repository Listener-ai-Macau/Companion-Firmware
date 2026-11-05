#include "motion_events.h"
#include <string.h>
/* Compact flags preserve the existing board SRAM allocation. */
_Static_assert(sizeof(comp_motion_events_t) <= 32u, "motion event state grew");
#define CARRY_ENTER_MS 2400u
#define CARRY_QUIET_MS 1200u
#define TILT_STABLE_MS 350u
static int32_t magnitude(int32_t value) { return value < 0 ? -value : value; }
/* Provisional tuning for a deliberate short reciprocal motion. Three lobes
 * on one axis, each qualified for >=40ms, distinguish it from a single tilt
 * and its return. The compact clock rounds upward, so pauses expire early
 * rather than extending a gesture. Physical sensitivity remains to be tuned. */
static bool reciprocal_shake(comp_motion_events_t *m,
    const comp_imu_sample_t *s, uint32_t elapsed)
{
    int32_t spin = 0, linear = 0;
    uint8_t spin_axis = 0u, linear_axis = 0u;
    for (uint8_t axis = 0u; axis < 3u; ++axis) {
        const int32_t g = s->gyro_mdps[axis];
        const int32_t a = (int32_t)s->accel_mg[axis] - m->gravity_mg[axis];
        if (magnitude(g) > magnitude(spin)) { spin = g; spin_axis = axis; }
        if (magnitude(a) > magnitude(linear)) { linear = a; linear_axis = axis; }
    }
    /* Retain the signal source through a gyro zero crossing; mixing a
     * gravity-filter residual into that same gesture would invent turns. */
    const bool gyro = magnitude(spin) >= 60000 ||
        (m->shake_history != 0u && m->shake_gyro);
    const int32_t value = gyro ? spin : linear;
    const uint8_t axis = gyro ? spin_axis : linear_axis;
    const uint8_t direction = (gyro ? magnitude(spin) >= 60000 : magnitude(linear) >= 250) ?
        (uint8_t)(1u + axis * 2u + (value < 0)) : 0u;
    uint16_t h = m->shake_history;
    unsigned age = ((h >> 5u) & 127u) + (elapsed + 9u) / 10u;
    unsigned dwell = h >> 12u, turns = (h >> 3u) & 3u;
    uint8_t previous = h & 7u;
    if (age > 90u) { previous = 0u; turns = dwell = age = 0u; }
    if (direction) {
        if (!previous || m->shake_gyro != gyro ||
            (direction - 1u) / 2u != (previous - 1u) / 2u) {
            previous = direction; turns = dwell = age = 0u;
            m->shake_gyro = gyro;
        } else if (direction != previous) {
            /* An unqualified spike breaks the sequence, not another turn. */
            turns = dwell >= 4u && turns < 3u ? turns + 1u : 0u;
            previous = direction; dwell = 0u;
        }
        const unsigned step = (elapsed + 9u) / 10u;
        dwell = dwell + step > 15u ? 15u : dwell + step;
    }
    /* Below threshold, retain the prior qualified lobe without adding dwell.
     * A natural zero crossing neither erases a turn nor supplies a new one. */
    m->shake_history = (uint16_t)(previous | (turns << 3u) |
        (age << 5u) | (dwell << 12u));
    return direction && turns >= 2u && dwell >= 4u && age >= 16u;
}
void comp_motion_events_init(comp_motion_events_t *motion)
{
    if (motion != NULL) {
        memset(motion, 0, sizeof(*motion));
        motion->tilt = motion->candidate_tilt = COMP_MOTION_TILT_UNKNOWN;
    }
}
bool comp_motion_events_set_screen_axes(comp_motion_events_t *m,
    uint8_t right, uint8_t up, uint8_t front)
{
    const uint8_t packed = comp_imu_screen_axes_pack(right, up, front);
    return packed != 0u && comp_motion_events_set_packed_axes(m, packed);
}
bool comp_motion_events_set_packed_axes(comp_motion_events_t *m, uint8_t packed)
{
    if (!m || !comp_imu_screen_axes_valid(packed)) return false;
    if (m->screen_axes == packed) return true;
    m->screen_axes = packed;
    m->tilt_initialized = false;
    m->tilt = m->candidate_tilt = COMP_MOTION_TILT_UNKNOWN;
    m->orientation_since_ms = m->sample_ms;
    return true;
}
static int32_t axis_value(const comp_imu_sample_t *s, uint8_t code)
{
    const int32_t value = s->accel_mg[(code - 1u) / 2u];
    return (code & 1u) ? value : -value;
}
static uint8_t tilt_candidate(const comp_motion_events_t *m, const comp_imu_sample_t *s)
{
    if (!(m->screen_axes & 0x80u)) return COMP_MOTION_TILT_UNKNOWN;
    const uint8_t right = m->screen_axes & 7u, up = (m->screen_axes >> 3u) & 7u;
    const unsigned front_axis = 3u - (right - 1u) / 2u - (up - 1u) / 2u;
    const int32_t front = s->accel_mg[front_axis] *
        ((m->screen_axes & 0x40u) ? -1 : 1);
    const int32_t x = axis_value(s, right), y = axis_value(s, up);
    if (front < -750 || (m->tilt == COMP_MOTION_TILT_INVERTED && front < -550))
        return COMP_MOTION_TILT_INVERTED;
    /* Two thresholds keep noisy samples from exchanging adjacent looks.
     * These are gravity projections, not measured roll/pitch angles. */
    if (m->tilt == COMP_MOTION_TILT_LEFT && x < -300 && magnitude(x) + 120 >= magnitude(y))
        return COMP_MOTION_TILT_LEFT;
    if (m->tilt == COMP_MOTION_TILT_RIGHT && x > 300 && magnitude(x) + 120 >= magnitude(y))
        return COMP_MOTION_TILT_RIGHT;
    if (m->tilt == COMP_MOTION_TILT_UP && y > 300 && magnitude(y) + 120 >= magnitude(x))
        return COMP_MOTION_TILT_UP;
    if (m->tilt == COMP_MOTION_TILT_DOWN && y < -300 && magnitude(y) + 120 >= magnitude(x))
        return COMP_MOTION_TILT_DOWN;
    if (magnitude(x) < 450 && magnitude(y) < 450) return COMP_MOTION_TILT_CENTER;
    if (magnitude(x) >= magnitude(y))
        return x < 0 ? COMP_MOTION_TILT_LEFT : COMP_MOTION_TILT_RIGHT;
    return y < 0 ? COMP_MOTION_TILT_DOWN : COMP_MOTION_TILT_UP;
}
uint8_t comp_motion_events_update(comp_motion_events_t *motion, const comp_imu_sample_t *sample)
{
    int64_t energy = 0;
    int32_t delta = 0, largest = 0;
    unsigned dominant = 0u;
    uint8_t events = 0u, orientation, tilt;
    bool still, cooled;
    if (motion == NULL || sample == NULL) { return 0u; }
    if (motion->initialized && sample->timestamp_ms == motion->sample_ms) { return 0u; }
    uint32_t elapsed = sample->timestamp_ms - motion->sample_ms;
    if (!motion->initialized || elapsed > 500u) {
        if (motion->carried) events |= COMP_MOTION_CARRY_ENDED;
        elapsed = 0u;
        memcpy(motion->gravity_mg, sample->accel_mg, sizeof(motion->gravity_mg));
        motion->still_since_ms = sample->timestamp_ms;
        motion->stationary = false;
        motion->initialized = true;
        /* A shared-bus/sleep gap is unknown motion, never a quiet interval.
         * Do not emit a landing from samples taken before the interruption. */
        motion->settle_pending = false;
        motion->carried = false;
        motion->movement_ms = 0u;
        motion->shake_history = 0u;
        /* Keep only the last qualified posture for comparison. A display
         * bus gap cannot prove pickup/landing, but a held new tilt can be
         * qualified from fresh post-gap samples. Reset its candidate/dwell;
         * startup or a mounting-profile change still has no prior baseline
         * and must not synthesize a first tilt event. */
        motion->candidate_tilt = COMP_MOTION_TILT_UNKNOWN;
        motion->candidate_orientation = 0u;
        motion->orientation_since_ms = sample->timestamp_ms;
    }
    motion->sample_ms = sample->timestamp_ms;
    for (unsigned axis = 0u; axis < 3u; ++axis) {
        int32_t a = sample->accel_mg[axis];
        energy += (int64_t)a * a;
        delta += magnitude(a - motion->gravity_mg[axis]);
        if (magnitude(a) > largest) { largest = magnitude(a); dominant = axis; }
    }
    cooled = !motion->has_event || sample->timestamp_ms - motion->event_ms >= 1000u;
    const bool rotating = magnitude(sample->gyro_mdps[0]) >= 15000 ||
        magnitude(sample->gyro_mdps[1]) >= 15000 ||
        magnitude(sample->gyro_mdps[2]) >= 15000;
    still = energy >= 810000 && energy <= 1210000 && delta < 120 && !rotating;
    const bool reciprocal = elapsed && !motion->carried &&
        reciprocal_shake(motion, sample, elapsed);
    if (!still) {
        const uint32_t movement = motion->movement_ms + elapsed;
        motion->movement_ms = (uint16_t)(movement > CARRY_ENTER_MS ? CARRY_ENTER_MS : movement);
    } else {
        const uint32_t decay = elapsed / 4u;
        motion->movement_ms = motion->movement_ms > decay ?
            (uint16_t)(motion->movement_ms - decay) : 0u;
    }
    if (!motion->carried && motion->movement_ms >= CARRY_ENTER_MS) {
        motion->carried = true;
        motion->settle_pending = false;
        events |= COMP_MOTION_CARRIED;
    }
    if (!motion->carried) {
        /* A qualified shake may follow a pickup, but repeated shakes wait
         * two seconds. No initial/post-gap sample manufactures a shake. */
        const bool shake_ready = !motion->has_event || motion->last_was_pickup ||
            sample->timestamp_ms - motion->event_ms >= 2000u;
        if (elapsed && shake_ready && (energy > 4000000 || reciprocal)) {
            events |= COMP_MOTION_SHAKE; motion->shake_history = 0u;
        } else if (cooled && motion->stationary && !still && delta > 250 &&
                 sample->timestamp_ms - motion->still_since_ms >= 1000u) { events |= COMP_MOTION_PICKUP; }
    }
    if (!still || !motion->stationary) { motion->still_since_ms = sample->timestamp_ms; }
    motion->stationary = still;
    if (motion->carried && still &&
        sample->timestamp_ms - motion->still_since_ms >= CARRY_QUIET_MS) {
        motion->carried = false;
        motion->movement_ms = 0u;
        motion->settle_pending = true;
        events |= COMP_MOTION_CARRY_ENDED;
    } else if (motion->carried && !still && cooled) {
        /* Keep the runtime's bounded suppression lease fresh, at most1Hz. */
        events |= COMP_MOTION_CARRIED;
    }
    if (still && motion->settle_pending && cooled &&
        sample->timestamp_ms - motion->still_since_ms >= 600u) {
        events |= COMP_MOTION_SETTLED;
        motion->settle_pending = false;
    }
    for (unsigned axis = 0u; axis < 3u; ++axis) {
        motion->gravity_mg[axis] = (int16_t)(motion->gravity_mg[axis] +
            ((int32_t)sample->accel_mg[axis] - motion->gravity_mg[axis]) / 8);
    }
    orientation = largest >= 750 && still ?
        (uint8_t)(1u + dominant * 2u + (sample->accel_mg[dominant] < 0 ? 1u : 0u)) : 0u;
    tilt = still ? tilt_candidate(motion, sample) : COMP_MOTION_TILT_UNKNOWN;
    if (orientation != motion->candidate_orientation || tilt != motion->candidate_tilt) {
        motion->candidate_orientation = orientation;
        motion->candidate_tilt = tilt;
        motion->orientation_since_ms = sample->timestamp_ms;
    } else {
        if (orientation != 0u && orientation != motion->orientation &&
            sample->timestamp_ms - motion->orientation_since_ms >= 200u) {
            motion->orientation = orientation; events |= COMP_MOTION_ORIENTATION_CHANGED;
        }
        if (tilt != COMP_MOTION_TILT_UNKNOWN &&
            sample->timestamp_ms - motion->orientation_since_ms >= TILT_STABLE_MS) {
            if (motion->tilt_initialized && tilt != motion->tilt)
                events |= COMP_MOTION_TILT_CHANGED;
            motion->tilt = tilt;
            motion->tilt_initialized = true;
        }
    }
    if (events & (COMP_MOTION_PICKUP | COMP_MOTION_SHAKE | COMP_MOTION_CARRIED)) {
        motion->event_ms = sample->timestamp_ms; motion->has_event = true;
        motion->last_was_pickup = (events & COMP_MOTION_PICKUP) != 0u;
        if (!motion->carried) motion->settle_pending = true;
    }
    if (motion->carried) motion->shake_history = 0u;
    return events;
}
