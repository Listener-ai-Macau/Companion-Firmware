#ifndef COMP_V11_BLE_GATE_OBSERVATION_H
#define COMP_V11_BLE_GATE_OBSERVATION_H
#include <stdbool.h>
#include <stdint.h>
#include <limits.h>

/* Per sealed transfer. Only elapsed time AFTER a failed ACI returns is
 * measured here, until the first real wake or fallback attempt. These
 * disjoint gate intervals overlap radio/NOR work: never add to those sums.
 * The caller serializes ISR snapshots with its existing short IRQ guard.
 * No additional stack command, packet, polling, log ring or UART output. */
typedef struct {
    uint32_t since_us, wait_us[3], origins, radio_ends;
    uint16_t wakes[3];
    uint8_t flags, reserved;
} comp_v11_ble_gate_observation_t;
_Static_assert(sizeof(comp_v11_ble_gate_observation_t)==32u,"bounded gate observation");
#define GATE_OBS_ACTIVE 1u
#define GATE_OBS_OVERFLOW 2u
#define GATE_OBS_BACKWARD 4u
#define GATE_OBS_CENSORED 8u
#define GATE_OBS_RADIO_API_CENSORED 16u
#define GATE_OBS_MEASURED 128u

static inline void comp_gate_observation_start(comp_v11_ble_gate_observation_t *p)
{
    *p=(comp_v11_ble_gate_observation_t){0};
    p->flags=GATE_OBS_MEASURED;
}
static inline void comp_gate_observation_packed_increment(
    comp_v11_ble_gate_observation_t *p,uint32_t *counts,unsigned shift)
{
    if(((*counts>>shift)&UINT32_C(65535))==UINT32_C(65535))
        p->flags|=GATE_OBS_OVERFLOW;
    else *counts+=UINT32_C(1)<<shift;
}
static inline void comp_gate_observation_origin(
    comp_v11_ble_gate_observation_t *p,bool notification_commit)
{
    comp_gate_observation_packed_increment(p,&p->origins,notification_commit?16u:0u);
}
static inline void comp_gate_observation_open(
    comp_v11_ble_gate_observation_t *p,uint32_t now)
{
    if(p->flags&GATE_OBS_ACTIVE){p->flags|=GATE_OBS_CENSORED;return;}
    p->since_us=now;p->flags|=GATE_OBS_ACTIVE;
}
static inline void comp_gate_observation_close(
    comp_v11_ble_gate_observation_t *p,unsigned reason,uint32_t now)
{
    if(!(p->flags&GATE_OBS_ACTIVE))return;
    p->flags=(uint8_t)(p->flags&~GATE_OBS_ACTIVE);
    if(reason<1u || reason>3u){p->flags|=GATE_OBS_CENSORED;return;}
    uint32_t elapsed=now-p->since_us;
    unsigned i=reason-1u;
    if(elapsed>INT32_MAX){p->flags|=GATE_OBS_BACKWARD;return;}
    if(elapsed>UINT32_MAX-p->wait_us[i] || p->wakes[i]==UINT16_MAX){
        p->flags|=GATE_OBS_OVERFLOW;return;
    }
    p->wait_us[i]+=elapsed;++p->wakes[i];
}
static inline void comp_gate_observation_radio_end(
    comp_v11_ble_gate_observation_t *p,unsigned pending,bool provisional_api)
{
    /* The public LL admission counter is NOT a view of the physical radio
     * FIFO. An API whose original return is pending cannot qualify emptiness.
     * Count only boundaries with no such provisional owner; retain censoring.
     * Low16=end with accepted/uncompleted ACL; high16=no outstanding ACL. */
    if(provisional_api){p->flags|=GATE_OBS_RADIO_API_CENSORED;return;}
    comp_gate_observation_packed_increment(p,&p->radio_ends,pending?0u:16u);
}
#endif
