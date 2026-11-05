#ifndef COMP_V11_RESET_WITNESS_H
#define COMP_V11_RESET_WITNESS_H
#include <stdint.h>
#if defined(__arm__) && COMPANION_WBA_CPU_RESIDENCE_PROFILE
typedef struct {uint32_t marker,detail;} comp_v11_reset_witness_t;
comp_v11_reset_witness_t comp_v11_reset_witness_read(void);
void comp_v11_reset_witness_emit(comp_v11_reset_witness_t,uint32_t);
void comp_v11_reset_witness_begin(unsigned);
void comp_v11_reset_witness_end(void);
void comp_v11_reset_witness_failure(unsigned,uint32_t,unsigned);
void comp_v11_reset_witness_uart_begin(const char *);
void comp_v11_reset_witness_uart_end(void);
void comp_v11_reset_witness_irq_enter(void);
void comp_v11_reset_witness_irq_exit(void);
#else
typedef struct {uint32_t marker,detail;} comp_v11_reset_witness_t;
static inline comp_v11_reset_witness_t comp_v11_reset_witness_read(void){return(comp_v11_reset_witness_t){0};}
static inline void comp_v11_reset_witness_emit(comp_v11_reset_witness_t w,uint32_t r){(void)w;(void)r;}
static inline void comp_v11_reset_witness_begin(unsigned s){(void)s;}
static inline void comp_v11_reset_witness_end(void){}
static inline void comp_v11_reset_witness_failure(unsigned k,uint32_t d,unsigned p){(void)k;(void)d;(void)p;}
static inline void comp_v11_reset_witness_uart_begin(const char *s){(void)s;}
static inline void comp_v11_reset_witness_uart_end(void){}
static inline void comp_v11_reset_witness_irq_enter(void){}
static inline void comp_v11_reset_witness_irq_exit(void){}
#endif
#endif
