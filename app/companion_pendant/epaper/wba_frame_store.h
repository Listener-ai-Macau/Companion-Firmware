#ifndef COMPANION_WBA_FRAME_STORE_H
#define COMPANION_WBA_FRAME_STORE_H
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#ifndef COMP_WBA_PACKED_OLD_FRAME
#define COMP_WBA_PACKED_OLD_FRAME 0
#endif
#define COMP_WBA_FRAME_STORE_BYTES 1280u
/* Complete200x200 controller-order image. Row-XOR plus zero/repeat/literal
 * runs is lossless. No NOR I/O, heap, altered image or partial old baseline.
 * Cursor only caches decoding; encoded bytes stay immutable in flight. */
typedef struct {
    uint8_t bytes[COMP_WBA_FRAME_STORE_BYTES];
    uint16_t bit_length,input_bit,output;
    uint8_t remaining,kind,value,row[25];
    bool valid;
} comp_wba_frame_store_t;
typedef bool (*comp_wba_frame_store_progress_fn_t)(void *context);
/* Cooperative variants retain the exact bitstream and capacity preflight.
 * A rejected preflight leaves the old image unchanged. An interrupted write
 * marks its partially replaced stream invalid; it must never become a baseline. */
size_t comp_wba_frame_store_size_progress(const uint8_t frame[5000],comp_wba_frame_store_progress_fn_t,void *);
bool comp_wba_frame_store_write_progress(comp_wba_frame_store_t *,const uint8_t frame[5000],comp_wba_frame_store_progress_fn_t,void *);
size_t comp_wba_frame_store_size(const uint8_t frame[5000]);
bool comp_wba_frame_store_write(comp_wba_frame_store_t *,const uint8_t frame[5000]);
bool comp_wba_frame_store_read(comp_wba_frame_store_t *,size_t offset,uint8_t *,size_t count);
#endif
