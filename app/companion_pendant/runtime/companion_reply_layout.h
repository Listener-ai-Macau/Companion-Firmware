#ifndef COMPANION_REPLY_LAYOUT_H
#define COMPANION_REPLY_LAYOUT_H

/* Reserved home-face text area for future screen replies. No chat backend or
 * generated answer is implied by these layout constants. Native art stays
 * above y=172. One short line sits at the bottom and updates atomically;
 * no wrapping, scrolling or typewriter animation. Idle keeps this strip blank.
 * During capture, x=2..41/y=156..179 remains the existing recording overlay. */
#define COMP_REPLY_TEXT_X 12u
#define COMP_REPLY_TEXT_Y 185u
#define COMP_REPLY_TEXT_WIDTH 176u
#define COMP_REPLY_TEXT_HEIGHT 13u
#define COMP_REPLY_TEXT_LINE_HEIGHT 13u
#define COMP_REPLY_TEXT_LINE_PITCH 13u
#define COMP_REPLY_TEXT_LINES 1u
#define COMP_REPLY_TEXT_RECORDING_X 48u
#define COMP_REPLY_TEXT_RECORDING_WIDTH 140u

_Static_assert(COMP_REPLY_TEXT_Y+COMP_REPLY_TEXT_HEIGHT<=200u,"reply below display");
_Static_assert(COMP_REPLY_TEXT_X+COMP_REPLY_TEXT_WIDTH<=200u,"reply outside display");
_Static_assert((COMP_REPLY_TEXT_LINES-1u)*COMP_REPLY_TEXT_LINE_PITCH+COMP_REPLY_TEXT_LINE_HEIGHT<=COMP_REPLY_TEXT_HEIGHT,"reply line overlap");
#endif
