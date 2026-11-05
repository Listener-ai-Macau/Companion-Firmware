#include "ft6336.h"

#include <string.h>

bool comp_ft6336_decode_touch_report(const uint8_t report[COMP_FT6336_TOUCH_REPORT_BYTES],
                                     comp_ft6336_touch_sample_t *out)
{
    if (report == NULL || out == NULL) {
        return false;
    }

    const uint8_t touch_count = report[0] & 0x0Fu;
    if (touch_count > 2u) {
        return false;
    }

    memset(out, 0, sizeof(*out));
    out->touch_count = touch_count;
    if (touch_count == 0u) {
        out->event = COMP_FT6336_TOUCH_EVENT_NONE;
        return true;
    }

    out->event = (comp_ft6336_touch_event_t)((report[1] >> 6) & 0x03u);
    out->x = (uint16_t)(((uint16_t)(report[1] & 0x0Fu) << 8) | report[2]);
    out->touch_id = (report[3] >> 4) & 0x0Fu;
    out->y = (uint16_t)(((uint16_t)(report[3] & 0x0Fu) << 8) | report[4]);
    return true;
}

const char *comp_ft6336_touch_event_name(comp_ft6336_touch_event_t event)
{
    switch (event) {
    case COMP_FT6336_TOUCH_EVENT_DOWN:
        return "down";
    case COMP_FT6336_TOUCH_EVENT_UP:
        return "up";
    case COMP_FT6336_TOUCH_EVENT_CONTACT:
        return "contact";
    case COMP_FT6336_TOUCH_EVENT_NONE:
        return "none";
    default:
        return "reserved";
    }
}

bool comp_ft6336_decoder_self_test(void)
{
    static const uint8_t down_report[COMP_FT6336_TOUCH_REPORT_BYTES] = {
        0x01u, 0x00u, 0xC7u, 0x10u, 0x63u,
    };
    static const uint8_t idle_report[COMP_FT6336_TOUCH_REPORT_BYTES] = {
        0x00u, 0x00u, 0x00u, 0x00u, 0x00u,
    };
    comp_ft6336_touch_sample_t sample;

    return comp_ft6336_decode_touch_report(down_report, &sample) &&
           sample.touch_count == 1u &&
           sample.event == COMP_FT6336_TOUCH_EVENT_DOWN &&
           sample.touch_id == 1u &&
           sample.x == 199u &&
           sample.y == 99u &&
           comp_ft6336_decode_touch_report(idle_report, &sample) &&
           sample.touch_count == 0u &&
           sample.event == COMP_FT6336_TOUCH_EVENT_NONE;
}
