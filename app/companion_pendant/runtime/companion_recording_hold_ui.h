#ifndef COMPANION_RECORDING_HOLD_UI_H
#define COMPANION_RECORDING_HOLD_UI_H
#include <stdbool.h>
#include <stdint.h>
/* Same existing16px status rail, between elapsed time and Bluetooth.
 * Deliberate stationary1s hold; no bottom button or extra progress frames. */
enum { COMP_RECORD_HOLD_ICON_X=136, COMP_RECORD_HOLD_ICON_Y=2,
       COMP_RECORD_HOLD_LEFT=126, COMP_RECORD_HOLD_RIGHT=151,
       COMP_RECORD_HOLD_TOP=0, COMP_RECORD_HOLD_BOTTOM=24,
       COMP_RECORD_HOLD_MIN_MS=1000, COMP_RECORD_HOLD_MAX_MS=2200,
       COMP_RECORD_HOLD_MOVE_PX=12 };
static inline bool comp_record_hold_contains(uint16_t x,uint16_t y)
{
    return x>=COMP_RECORD_HOLD_LEFT && x<COMP_RECORD_HOLD_RIGHT &&
        y<COMP_RECORD_HOLD_BOTTOM; /* Native coordinates are unsigned; top is0. */
}
#endif
