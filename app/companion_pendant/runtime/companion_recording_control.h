#ifndef COMPANION_RECORDING_CONTROL_H
#define COMPANION_RECORDING_CONTROL_H
#include <stdbool.h>
#include <stdint.h>
/* Shared visible/hit geometry. Below the original wave (ends at y179),
 * one native text line; no menu entry or capture-time full-page redraw. */
/* Keep the original x<=48 double-tap corner outside this single-tap button. */
enum { COMP_RECORD_STOP_LEFT=56, COMP_RECORD_STOP_RIGHT=184,
       COMP_RECORD_STOP_TOP=180, COMP_RECORD_STOP_BOTTOM=200 };
static inline bool comp_record_stop_contains(uint16_t x,uint16_t y)
{
    return x>=COMP_RECORD_STOP_LEFT && x<COMP_RECORD_STOP_RIGHT &&
        y>=COMP_RECORD_STOP_TOP && y<COMP_RECORD_STOP_BOTTOM;
}
#endif
