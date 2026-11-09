#ifndef COMPANION_CPU_STAGE_H
#define COMPANION_CPU_STAGE_H
#include <stdbool.h>
#include <stdint.h>
enum {COMP_CPU_STAGE_PDM=0,COMP_CPU_STAGE_OPUS,COMP_CPU_STAGE_NOR_PROGRAM,
    COMP_CPU_STAGE_PANEL_TX,COMP_CPU_STAGE_HAL_INPUTS,COMP_CPU_STAGE_MIC_POLL,
    COMP_CPU_STAGE_VALIDATE,COMP_CPU_STAGE_PIPELINE,COMP_CPU_STAGE_CAPTURE_PROGRESS,COMP_CPU_STAGE_MAIN_SERVICES,COMP_CPU_STAGE_BLE_SERVICE,COMP_CPU_STAGE_RUNTIME_SERVICE,COMP_CPU_STAGE_PRESENTER_SERVICE,COMP_CPU_STAGE_RENDER_SERVICE,COMP_CPU_STAGE_BLE_SEQUENCER,COMP_CPU_STAGE_BLE_LINK,COMP_CPU_STAGE_MEETING_ACI,COMP_CPU_STAGE_COUNT};
/* Detailed profiling remains available for a source-bound engineering build.
 * Normal builds keep true total residence plus PDM/Opus/NOR observations. */
#ifndef COMPANION_WBA_CPU_DETAILED_PROFILE
#define COMPANION_WBA_CPU_DETAILED_PROFILE 1
#endif
#define COMP_CPU_STAGE_STORAGE_COUNT (COMPANION_WBA_CPU_DETAILED_PROFILE?COMP_CPU_STAGE_COUNT:3u)
typedef struct {uint64_t irq_us;uint32_t at_us,token,sequence,domain;} comp_cpu_stage_span_t;
#if COMPANION_WBA_CPU_RESIDENCE_PROFILE
/* Optional observation only. No timer/IRQ priority or product admission changes. */
comp_cpu_stage_span_t comp_cpu_stage_begin(void);
/* Upload-only use of existing detail hooks; no record/capture activation. */
bool comp_cpu_bulk_owned(void);
comp_cpu_stage_span_t comp_cpu_bulk_stage_begin(void);
void comp_cpu_bulk_stage_end(unsigned,comp_cpu_stage_span_t);
void comp_cpu_stage_end(unsigned,comp_cpu_stage_span_t,bool completed);
void comp_cpu_codec_cache_begin(void);
/* Optional metadata paired with the same observed worst-wall codec frame. */
void comp_cpu_codec_admission(uint32_t flags,uint32_t next_radio_us);
void comp_cpu_panel_stage_end(comp_cpu_stage_span_t,bool completed,uint16_t bytes);
#else
static inline bool comp_cpu_bulk_owned(void){return false;}
static inline void comp_cpu_codec_cache_begin(void){}
static inline void comp_cpu_panel_stage_end(comp_cpu_stage_span_t s,bool completed,uint16_t bytes)
{(void)s;(void)completed;(void)bytes;}
static inline comp_cpu_stage_span_t comp_cpu_stage_begin(void)
{return (comp_cpu_stage_span_t){0};}
static inline void comp_cpu_stage_end(unsigned stage,comp_cpu_stage_span_t span,bool completed)
{(void)stage;(void)span;(void)completed;}
#endif

static inline comp_cpu_stage_span_t comp_cpu_detail_begin(void)
{
#if COMPANION_WBA_CPU_RESIDENCE_PROFILE
    if(comp_cpu_bulk_owned())return comp_cpu_bulk_stage_begin();
#endif
#if COMPANION_WBA_CPU_DETAILED_PROFILE
    return comp_cpu_stage_begin();
#else
    return (comp_cpu_stage_span_t){0};
#endif
}
static inline void comp_cpu_detail_end(unsigned stage,comp_cpu_stage_span_t span,bool completed)
{
#if COMPANION_WBA_CPU_RESIDENCE_PROFILE
    if(comp_cpu_bulk_owned()){comp_cpu_bulk_stage_end(stage,span);return;}
#endif
#if COMPANION_WBA_CPU_DETAILED_PROFILE
    comp_cpu_stage_end(stage,span,completed);
#else
    (void)stage;(void)span;(void)completed;
#endif
}
static inline void comp_cpu_detail_panel_end(comp_cpu_stage_span_t span,bool completed,uint16_t bytes)
{
#if COMPANION_WBA_CPU_RESIDENCE_PROFILE
    if(comp_cpu_bulk_owned()){comp_cpu_bulk_stage_end(COMP_CPU_STAGE_PANEL_TX,span);return;}
#endif
#if COMPANION_WBA_CPU_DETAILED_PROFILE
    comp_cpu_panel_stage_end(span,completed,bytes);
#else
    (void)span;(void)completed;(void)bytes;
#endif
}
#endif
