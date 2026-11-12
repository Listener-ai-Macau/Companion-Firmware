#ifndef COMP_V11_CPU_PROFILE_TARGET_H
#define COMP_V11_CPU_PROFILE_TARGET_H
#include <stdbool.h>
#include <stdint.h>
#include "companion_cpu_stage.h"
#include "cpu_duty_target.h"
/* Audio-only slots0/1 are reused as product/HAL only for sealed upload. */
enum {COMP_BULK_CPU_PRODUCT=0,COMP_BULK_CPU_HAL=1,COMP_BULK_CPU_SEQ=14,COMP_BULK_CPU_READ=17,COMP_BULK_CPU_PUBLISH=18,COMP_BULK_CPU_STAGES=19};
#ifndef COMPANION_WBA_CPU_RESIDENCE_PROFILE
#define COMPANION_WBA_CPU_RESIDENCE_PROFILE 0
#endif
#if COMPANION_WBA_CPU_RESIDENCE_PROFILE && COMPANION_WBA_CPU_DUTY_OBSERVER
#error "Select one CPU observer; no competing timer or counter owner"
#endif
#if COMPANION_WBA_CPU_RESIDENCE_PROFILE
#if defined(COMPANION_WBA_EXPERIMENTAL_STOP1) && COMPANION_WBA_EXPERIMENTAL_STOP1
/* A live owned TIM2 must never cross a Stop1 clock discontinuity. */
bool comp_v11_cpu_counter_owned(void);
#endif
bool comp_v11_cpu_arm_cache_off_trial(void);
void comp_v11_cpu_capture_begin(uint32_t);
void comp_v11_cpu_capture_end(uint32_t);
/* Sealed-file upload observer only; never starts a recording/cache trial. */
void comp_v11_cpu_transfer_begin(uint32_t);
void comp_v11_cpu_transfer_end(void);
comp_cpu_stage_span_t comp_v11_cpu_transfer_stage_begin(void);
void comp_v11_cpu_transfer_stage_end(unsigned,comp_cpu_stage_span_t);
void comp_v11_cpu_irq_enter(bool systick_entry);
void comp_v11_cpu_irq_exit(void);
void comp_v11_cpu_wait_enter(void);
void comp_v11_cpu_wait_exit(void);
void comp_v11_cpu_poll(void);
void comp_v11_cpu_emit(void);
/* Read stopped capture caches only, without UART, timer reads or clearing.
 * Every page repeats the same capture token; live/transport owners yield. */
bool comp_v11_cpu_codec_read(uint8_t page,uint32_t values[4],uint8_t *flags);
#else
#if COMPANION_WBA_CPU_DUTY_OBSERVER
#if defined(COMPANION_WBA_EXPERIMENTAL_STOP1) && COMPANION_WBA_EXPERIMENTAL_STOP1
static inline bool comp_v11_cpu_counter_owned(void){return comp_cpu_duty_counter_owned();}
#endif
static inline void comp_v11_cpu_capture_begin(uint32_t token){comp_cpu_duty_begin(token,true);}
static inline void comp_v11_cpu_capture_end(uint32_t token){comp_cpu_duty_end(token,true);}
static inline void comp_v11_cpu_transfer_begin(uint32_t token){comp_cpu_duty_begin(token,false);}
static inline void comp_v11_cpu_transfer_end(void){comp_cpu_duty_end(0u,false);}
static inline void comp_v11_cpu_wait_enter(void){comp_cpu_duty_wait_enter();}
static inline void comp_v11_cpu_wait_exit(void){comp_cpu_duty_wait_exit();}
static inline void comp_v11_cpu_poll(void){comp_cpu_duty_poll();}
#else
#if defined(COMPANION_WBA_EXPERIMENTAL_STOP1) && COMPANION_WBA_EXPERIMENTAL_STOP1
static inline bool comp_v11_cpu_counter_owned(void){return false;}
#endif
static inline void comp_v11_cpu_capture_begin(uint32_t token){(void)token;}
static inline void comp_v11_cpu_capture_end(uint32_t token){(void)token;}
static inline void comp_v11_cpu_transfer_begin(uint32_t generation){(void)generation;}
static inline void comp_v11_cpu_transfer_end(void){}
static inline void comp_v11_cpu_wait_enter(void){}
static inline void comp_v11_cpu_wait_exit(void){}
static inline void comp_v11_cpu_poll(void){}
#endif
static inline bool comp_v11_cpu_arm_cache_off_trial(void){return false;}
static inline comp_cpu_stage_span_t comp_v11_cpu_transfer_stage_begin(void){return (comp_cpu_stage_span_t){0};}
static inline void comp_v11_cpu_transfer_stage_end(unsigned stage,comp_cpu_stage_span_t span){(void)stage;(void)span;}
static inline void comp_v11_cpu_irq_enter(bool systick_entry){(void)systick_entry;}
static inline void comp_v11_cpu_irq_exit(void){}
static inline void comp_v11_cpu_emit(void){comp_cpu_duty_emit();}
#endif
#endif
