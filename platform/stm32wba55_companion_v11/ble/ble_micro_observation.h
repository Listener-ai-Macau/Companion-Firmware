#ifndef COMP_V11_BLE_MICRO_OBSERVATION_H
#define COMP_V11_BLE_MICRO_OBSERVATION_H
#include <stdbool.h>
#include <stdint.h>
/* Read-only SysTick/HAL projection. Do not touch DWT: ST's LL delay resets
 * and disables CYCCNT. Call durations include IRQ/preemption, not CPU time.
 * Arithmetic wraps modulo2^32us; each measured call/window must be<71min. */
typedef struct {
    uint32_t backend_us,backend_calls,backend_max_us;
    uint32_t prepare_us,prepare_calls,commit_us,commit_calls;
    uint32_t rejected_us,rejected_calls,publish_us,publish_calls;
    uint32_t window_start_us,window_us,clock_fallbacks;
} comp_v11_ble_micro_observation_t;
_Static_assert(sizeof(comp_v11_ble_micro_observation_t)==56u,"bounded micro observation");
static inline bool comp_v11_ble_micro_consistent(uint32_t before,uint32_t after,uint32_t load,uint32_t v1,uint32_t v2)
{return before==after && load>0u && load<UINT32_MAX/1000u && v1<=load && v2<=v1;}
static inline uint32_t comp_v11_ble_micro_stamp(uint32_t tick,uint32_t load,uint32_t value,bool pending)
{return (tick+(pending?1u:0u))*1000u+((load-value)*1000u)/(load+1u);}
static inline void comp_v11_ble_micro_aci(comp_v11_ble_micro_observation_t *m,uint32_t elapsed,bool final,bool success)
{
    if(!success){m->rejected_us+=elapsed;++m->rejected_calls;}
    else if(final){m->commit_us+=elapsed;++m->commit_calls;}
    else {m->prepare_us+=elapsed;++m->prepare_calls;}
}
#endif
