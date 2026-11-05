#ifndef COMPANION_TOUCH_FT6336_H
#define COMPANION_TOUCH_FT6336_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define COMP_FT6336_I2C_ADDRESS_7BIT 0x38u
#define COMP_FT6336_DEVICE_MODE_REGISTER 0x00u
#define COMP_FT6336_DEVICE_MODE_WORKING 0x00u
#define COMP_FT6336_POWER_MODE_REGISTER 0xA5u
#define COMP_FT6336_POWER_MODE_ACTIVE 0x00u
#define COMP_FT6336_TOUCH_REPORT_REGISTER 0x02u
#define COMP_FT6336_TOUCH_REPORT_BYTES 5u
#define COMP_FT6336_IDENTITY_REGISTER 0xA3u
#define COMP_FT6336_IDENTITY_BYTES 6u
#define COMP_FT6336_G_MODE_REGISTER 0xA4u
#define COMP_FT6336_G_MODE_POLLING 0x00u
#define COMP_FT6336_G_MODE_TRIGGER 0x01u
/* Runtime tuning registers are shared by FT6236/FT6336-family controllers.
 * These values retain the controller's own filtering while reducing initial
 * contact latency on the small Companion touch panel. */
#define COMP_FT6336_TOUCH_THRESHOLD_REGISTER 0x80u
#define COMP_FT6336_PERIOD_ACTIVE_REGISTER 0x88u
#define COMP_FT6336_PERIOD_MONITOR_REGISTER 0x89u
/* TH_GROUP is a board-calibration value, not a gesture policy.  Keep it
 * overridable for a verified panel-specific tuning build while WB55 and WBA
 * share the same portable baseline. */
#ifndef COMP_FT6336_COMPANION_TOUCH_THRESHOLD
#define COMP_FT6336_COMPANION_TOUCH_THRESHOLD 0x16u
#endif
#define COMP_FT6336_COMPANION_ACTIVE_PERIOD 0x04u
#define COMP_FT6336_COMPANION_MONITOR_PERIOD 0x04u

typedef enum {
    COMP_FT6336_TOUCH_EVENT_DOWN = 0u,
    COMP_FT6336_TOUCH_EVENT_UP = 1u,
    COMP_FT6336_TOUCH_EVENT_CONTACT = 2u,
    COMP_FT6336_TOUCH_EVENT_RESERVED = 3u,
    COMP_FT6336_TOUCH_EVENT_NONE = 4u,
} comp_ft6336_touch_event_t;

typedef struct {
    uint8_t touch_count;
    comp_ft6336_touch_event_t event;
    uint8_t touch_id;
    uint16_t x;
    uint16_t y;
} comp_ft6336_touch_sample_t;

typedef struct {
    uint8_t cipher;
    uint8_t firmware_id;
    uint8_t chip_id;
} comp_ft6336_identity_t;

bool comp_ft6336_decode_touch_report(const uint8_t report[COMP_FT6336_TOUCH_REPORT_BYTES],
                                     comp_ft6336_touch_sample_t *out);
const char *comp_ft6336_touch_event_name(comp_ft6336_touch_event_t event);
bool comp_ft6336_decoder_self_test(void);

#ifdef __cplusplus
}
#endif

#endif /* COMPANION_TOUCH_FT6336_H */
