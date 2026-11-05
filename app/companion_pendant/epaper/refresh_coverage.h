#ifndef COMPANION_EPAPER_REFRESH_COVERAGE_H
#define COMPANION_EPAPER_REFRESH_COVERAGE_H

#include <stdbool.h>
#include <stdint.h>

typedef struct {
    uint8_t x_start_byte;
    uint8_t x_end_byte;
    uint16_t y_start;
    uint16_t y_end;
    bool valid;
} comp_epaper_refresh_coverage_t;

static inline void comp_epaper_refresh_coverage_reset(
    comp_epaper_refresh_coverage_t *coverage)
{
    if (coverage != NULL) {
        *coverage = (comp_epaper_refresh_coverage_t){0};
    }
}

static inline bool comp_epaper_refresh_coverage_expand(
    const comp_epaper_refresh_coverage_t *current,
    uint8_t x_start_byte,
    uint8_t x_end_byte,
    uint16_t y_start,
    uint16_t y_end,
    comp_epaper_refresh_coverage_t *expanded)
{
    if (current == NULL || expanded == NULL || x_start_byte > x_end_byte ||
        y_start > y_end) {
        return false;
    }
    if (!current->valid) {
        *expanded = (comp_epaper_refresh_coverage_t){
            .x_start_byte = x_start_byte,
            .x_end_byte = x_end_byte,
            .y_start = y_start,
            .y_end = y_end,
            .valid = true,
        };
        return true;
    }
    *expanded = *current;
    if (x_start_byte < expanded->x_start_byte) {
        expanded->x_start_byte = x_start_byte;
    }
    if (x_end_byte > expanded->x_end_byte) {
        expanded->x_end_byte = x_end_byte;
    }
    if (y_start < expanded->y_start) {
        expanded->y_start = y_start;
    }
    if (y_end > expanded->y_end) {
        expanded->y_end = y_end;
    }
    return true;
}

#endif /* COMPANION_EPAPER_REFRESH_COVERAGE_H */
