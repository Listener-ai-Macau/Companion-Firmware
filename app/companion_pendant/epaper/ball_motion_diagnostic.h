#ifndef COMPANION_BALL_MOTION_DIAGNOSTIC_H
#define COMPANION_BALL_MOTION_DIAGNOSTIC_H

#include <stdint.h>

#define COMP_EPAPER_BALL_MOTION_DIAGNOSTIC_PARTIAL_STEPS 6u
#define COMP_EPAPER_BALL_MOTION_DIAGNOSTIC_CENTER_X 100u
#define COMP_EPAPER_BALL_MOTION_DIAGNOSTIC_CENTER_Y 100u
#define COMP_EPAPER_BALL_MOTION_DIAGNOSTIC_ORBIT_OFFSET 42u
#define COMP_EPAPER_BALL_MOTION_DIAGNOSTIC_RADIUS 10u

static inline uint8_t comp_epaper_ball_motion_diagnostic_clamp_step(uint8_t step)
{
    return step > COMP_EPAPER_BALL_MOTION_DIAGNOSTIC_PARTIAL_STEPS
               ? COMP_EPAPER_BALL_MOTION_DIAGNOSTIC_PARTIAL_STEPS
               : step;
}

static inline uint16_t comp_epaper_ball_motion_diagnostic_center_x(uint8_t step)
{
    switch (comp_epaper_ball_motion_diagnostic_clamp_step(step)) {
    case 2u:
        return COMP_EPAPER_BALL_MOTION_DIAGNOSTIC_CENTER_X +
               COMP_EPAPER_BALL_MOTION_DIAGNOSTIC_ORBIT_OFFSET;
    case 4u:
        return COMP_EPAPER_BALL_MOTION_DIAGNOSTIC_CENTER_X -
               COMP_EPAPER_BALL_MOTION_DIAGNOSTIC_ORBIT_OFFSET;
    default:
        return COMP_EPAPER_BALL_MOTION_DIAGNOSTIC_CENTER_X;
    }
}

static inline uint16_t comp_epaper_ball_motion_diagnostic_center_y(uint8_t step)
{
    switch (comp_epaper_ball_motion_diagnostic_clamp_step(step)) {
    case 1u:
        return COMP_EPAPER_BALL_MOTION_DIAGNOSTIC_CENTER_Y -
               COMP_EPAPER_BALL_MOTION_DIAGNOSTIC_ORBIT_OFFSET;
    case 3u:
        return COMP_EPAPER_BALL_MOTION_DIAGNOSTIC_CENTER_Y +
               COMP_EPAPER_BALL_MOTION_DIAGNOSTIC_ORBIT_OFFSET;
    default:
        return COMP_EPAPER_BALL_MOTION_DIAGNOSTIC_CENTER_Y;
    }
}

static inline const char *comp_epaper_ball_motion_diagnostic_position_name(uint8_t step)
{
    switch (comp_epaper_ball_motion_diagnostic_clamp_step(step)) {
    case 0u:
        return "baseline_center";
    case 1u:
        return "up";
    case 2u:
        return "right";
    case 3u:
        return "down";
    case 4u:
        return "left";
    case 5u:
        return "return_center";
    default:
        return "settle_center";
    }
}

#endif /* COMPANION_BALL_MOTION_DIAGNOSTIC_H */
