#ifndef COMP_CPU_DUTY_TARGET_H
#define COMP_CPU_DUTY_TARGET_H
#include <stdbool.h>
#include <stdint.h>
#ifndef COMPANION_WBA_CPU_DUTY_OBSERVER
#define COMPANION_WBA_CPU_DUTY_OBSERVER 0
#endif
typedef struct {
    uint32_t windows,peak_busy_upper_us,invalid,waits,proven_waits,token;
    bool enabled,active,recording;
} comp_cpu_duty_snapshot_t;
#if COMPANION_WBA_CPU_DUTY_OBSERVER
void comp_cpu_duty_begin(uint32_t token,bool recording);
void comp_cpu_duty_end(uint32_t token,bool recording);
void comp_cpu_duty_wait_enter(void);
void comp_cpu_duty_wait_exit(void);
void comp_cpu_duty_poll(void);
bool comp_cpu_duty_counter_owned(void);
comp_cpu_duty_snapshot_t comp_cpu_duty_snapshot(void);
#else
static inline comp_cpu_duty_snapshot_t comp_cpu_duty_snapshot(void)
{return (comp_cpu_duty_snapshot_t){0};}
#endif
#endif
