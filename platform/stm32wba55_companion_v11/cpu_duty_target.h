#ifndef COMP_CPU_DUTY_TARGET_H
#define COMP_CPU_DUTY_TARGET_H
#include <stdbool.h>
#include <stdint.h>
#ifndef COMPANION_WBA_CPU_DUTY_OBSERVER
#define COMPANION_WBA_CPU_DUTY_OBSERVER 0
#endif
typedef struct {
    uint32_t windows,peak_busy_upper_us,invalid,waits,token;
    bool enabled,active,recording;
    uint8_t invalid_reason;
} comp_cpu_duty_snapshot_t;
enum {COMP_DUTY_PRODUCT=0,COMP_DUTY_BLE,COMP_DUTY_INPUT_STATUS,
    COMP_DUTY_IMU_GPIO,COMP_DUTY_FUSION,COMP_DUTY_POINTER_SEND,COMP_DUTY_MAIN,
    COMP_DUTY_READY,COMP_DUTY_SEQ,COMP_DUTY_NVM,COMP_DUTY_HAL,COMP_DUTY_RUNTIME,COMP_DUTY_UPDATE,
    COMP_DUTY_STAGE_COUNT};
typedef struct {uint32_t raw,token;} comp_cpu_duty_span_t;
#if COMPANION_WBA_CPU_DUTY_OBSERVER
comp_cpu_duty_span_t comp_cpu_duty_span_begin(void);
void comp_cpu_duty_span_end(unsigned,comp_cpu_duty_span_t);
void comp_cpu_duty_emit(void);
void comp_cpu_duty_begin(uint32_t token,bool recording);
void comp_cpu_duty_end(uint32_t token,bool recording);
void comp_cpu_duty_wait_enter(void);
void comp_cpu_duty_wait_exit(void);
void comp_cpu_duty_wfi(void);
void comp_cpu_duty_poll(void);
bool comp_cpu_duty_counter_owned(void);
comp_cpu_duty_snapshot_t comp_cpu_duty_snapshot(void);
#else
static inline comp_cpu_duty_span_t comp_cpu_duty_span_begin(void){return (comp_cpu_duty_span_t){0};}
static inline void comp_cpu_duty_span_end(unsigned stage,comp_cpu_duty_span_t span){(void)stage;(void)span;}
static inline void comp_cpu_duty_emit(void){}
static inline comp_cpu_duty_snapshot_t comp_cpu_duty_snapshot(void)
{return (comp_cpu_duty_snapshot_t){0};}
#endif
#endif
