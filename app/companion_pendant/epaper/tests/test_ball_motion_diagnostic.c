#include "ball_motion_diagnostic.h"

#include <stdio.h>
#include <string.h>

typedef struct {
    uint16_t x;
    uint16_t y;
    const char *name;
} expected_position_t;

static int require_true(int condition, const char *message)
{
    if (!condition) {
        fprintf(stderr, "FAIL: %s\n", message);
        return 1;
    }
    return 0;
}

int main(void)
{
    static const expected_position_t k_expected[] = {
        {100u, 100u, "baseline_center"},
        {100u, 58u, "up"},
        {142u, 100u, "right"},
        {100u, 142u, "down"},
        {58u, 100u, "left"},
        {100u, 100u, "return_center"},
        {100u, 100u, "settle_center"},
    };

    for (uint8_t step = 0u; step <= COMP_EPAPER_BALL_MOTION_DIAGNOSTIC_PARTIAL_STEPS;
         ++step) {
        if (require_true(comp_epaper_ball_motion_diagnostic_center_x(step) ==
                             k_expected[step].x &&
                             comp_epaper_ball_motion_diagnostic_center_y(step) ==
                             k_expected[step].y &&
                             strcmp(comp_epaper_ball_motion_diagnostic_position_name(step),
                                    k_expected[step].name) == 0,
                         "orbit position contract")) {
            return 1;
        }
    }
    if (require_true(comp_epaper_ball_motion_diagnostic_center_x(99u) == 100u &&
                         comp_epaper_ball_motion_diagnostic_center_y(99u) == 100u &&
                         strcmp(comp_epaper_ball_motion_diagnostic_position_name(99u),
                                "settle_center") == 0,
                     "out-of-range steps clamp to settle")) {
        return 1;
    }

    puts("PASS: ball motion center-up-right-down-left-center");
    return 0;
}
