#ifndef COMPANION_PREFERENCES_H
#define COMPANION_PREFERENCES_H
#include "power_settings_store.h"
#define COMP_PREFS_BANK_BYTES 4096u
#define COMP_PREFS_RECORD_BYTES 64u
#define COMP_PREFS_NAME_BYTES 24u
#if defined(COMPANION_PRODUCT_CAPTURE) && COMPANION_PRODUCT_CAPTURE
#define COMP_PREFS_DEFAULT_NAME "Capture"
#else
#define COMP_PREFS_DEFAULT_NAME "Companion"
#endif
#define COMP_PREFS_DEFAULT_NAME_BYTES (sizeof(COMP_PREFS_DEFAULT_NAME)-1u)
typedef struct {
    comp_power_settings_values_t policy;
    uint8_t locale,volume,name_length;
    /* Pack existing booleans so a mounting byte fits the old RAM envelope. */
    bool radio_enabled : 1;
    bool quiet_enabled : 1;
    bool battery_fill : 1;
    bool pet_discovery_seen : 1;
    uint8_t imu_screen_axes;
    uint8_t name[COMP_PREFS_NAME_BYTES];
} comp_preferences_values_t;
typedef struct {
    bool (*read)(void *,uint32_t,uint8_t *,size_t);
    bool (*write)(void *,uint32_t,const uint8_t *,size_t);
    bool (*erase)(void *,uint32_t);
    void *context;
} comp_preferences_port_t;
typedef struct {
    comp_preferences_port_t port;
    comp_preferences_values_t values;
    /* Append sequence, including uncertain attempts. Only values/persisted
     * describe the last verified settings; failed writes may consume numbers. */
    uint32_t generation;
    uint8_t bank,next_slot;
    bool mounted : 1;
    bool persisted : 1;
    bool append_uncertain : 1;
} comp_preferences_t;
/* utc_seconds is Unix time only when calendar_valid; legacy h:m:s sync keeps
 * an explicitly date-unknown UTC-of-day. The extra flag fits existing padding. */
typedef struct { uint32_t tick,utc_seconds;uint16_t milliseconds;bool valid,calendar_valid; } comp_clock_t;
void comp_preferences_defaults(comp_preferences_values_t *);
bool comp_preferences_valid(const comp_preferences_values_t *);
/* Stable serialized values only, independent of RAM padding or save sequence. */
uint32_t comp_preferences_fingerprint(const comp_preferences_values_t *);
bool comp_preferences_are_defaults(const comp_preferences_values_t *);
bool comp_preferences_mount(comp_preferences_t *,const comp_preferences_port_t *);
bool comp_preferences_save(comp_preferences_t *,const comp_preferences_values_t *);
void comp_clock_poll(comp_clock_t *,uint32_t now);
bool comp_clock_sync(comp_clock_t *,uint8_t h,uint8_t m,uint8_t s,uint32_t now);
bool comp_clock_sync_unix(comp_clock_t *,uint32_t unix_seconds,uint32_t now);
uint32_t comp_clock_unix(const comp_clock_t *,uint32_t now);
uint32_t comp_clock_status(comp_clock_t *,int16_t zone,bool clock24,uint32_t now);
uint8_t comp_clock_local_hour(comp_clock_t *,int16_t zone,uint32_t now);
#endif
