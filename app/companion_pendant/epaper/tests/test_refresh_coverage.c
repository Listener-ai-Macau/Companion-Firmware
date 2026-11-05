#include "refresh_coverage.h"

#include <stdio.h>
#include <stdlib.h>

static void require_true(bool condition, const char *message)
{
    if (!condition) {
        fprintf(stderr, "FAIL: %s\n", message);
        exit(1);
    }
}

int main(void)
{
    comp_epaper_refresh_coverage_t coverage = {0};
    comp_epaper_refresh_coverage_t next = {0};

    require_true(comp_epaper_refresh_coverage_expand(
                     &coverage, 9u, 12u, 72u, 108u, &next),
                 "first source change establishes coverage");
    require_true(next.valid && next.x_start_byte == 9u &&
                     next.x_end_byte == 12u && next.y_start == 72u &&
                     next.y_end == 108u,
                 "first coverage matches the source change");
    coverage = next;

    require_true(comp_epaper_refresh_coverage_expand(
                     &coverage, 4u, 21u, 26u, 179u, &next),
                 "later source change expands coverage");
    require_true(next.x_start_byte == 4u && next.x_end_byte == 21u &&
                     next.y_start == 26u && next.y_end == 179u,
                 "coverage is the stable union, not the latest XOR");
    coverage = next;

    require_true(comp_epaper_refresh_coverage_expand(
                     &coverage, 10u, 11u, 80u, 90u, &next),
                 "contained change is accepted");
    require_true(next.x_start_byte == coverage.x_start_byte &&
                     next.x_end_byte == coverage.x_end_byte &&
                     next.y_start == coverage.y_start &&
                     next.y_end == coverage.y_end,
                 "contained change cannot shrink physical coverage");

    comp_epaper_refresh_coverage_reset(&coverage);
    require_true(!coverage.valid,
                 "a lifecycle full-refresh boundary starts a new epoch");
    require_true(!comp_epaper_refresh_coverage_expand(
                     &coverage, 12u, 4u, 20u, 30u, &next),
                 "invalid source geometry is rejected");

    puts("MACHINE_READY: source-driven stable refresh coverage");
    return 0;
}
