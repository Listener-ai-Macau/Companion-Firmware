#include "wba_frame_store.h"
#include "wba_frame_huffman.h"
#include <string.h>
static void put(uint8_t *out,size_t *bits,uint8_t symbol)
{
    if(!out){*bits+=frame_lengths[symbol];return;}
    for(unsigned i=frame_lengths[symbol];i!=0u;--i) {
        const size_t bit=(*bits)++;
        if(out) {
            if(!(bit&7u))out[bit/8u]=0u;
            if(frame_codes[symbol]&(1u<<(i-1u)))out[bit/8u]|=(uint8_t)(128u>>(bit&7u));
        }
    }
}
static uint8_t delta(const uint8_t *frame,size_t at)
{return frame[at]^(at<25u?255u:frame[at-25u]);}
static size_t encode(const uint8_t *frame,uint8_t *out,comp_wba_frame_store_progress_fn_t progress,void *context)
{
    size_t at=0u,size=0u,next_service=0u;
    while(at<5000u) {
        if(progress && at>=next_service) {
            if(!progress(context))return SIZE_MAX;
            next_service=at+128u;
        }
        uint8_t value=delta(frame,at);size_t n=1u;
        const size_t limit=value?65u:128u;
        while(at+n<5000u && n<limit && delta(frame,at+n)==value)++n;
        if(!value) {put(out,&size,(uint8_t)(n-1u));at+=n;}
        else if(n>=2u) {
            put(out,&size,(uint8_t)(128u+n-2u));put(out,&size,value);at+=n;
        } else {
            const size_t first=at++;
            while(at<5000u && at-first<64u && delta(frame,at) &&
                (at+1u==5000u || delta(frame,at)!=delta(frame,at+1u)))++at;
            n=at-first;
            put(out,&size,(uint8_t)(192u+n-1u));for(size_t i=0u;i<n;++i)put(out,&size,delta(frame,first+i));
        }
    }
    return size;
}
size_t comp_wba_frame_store_size_progress(const uint8_t frame[5000],comp_wba_frame_store_progress_fn_t progress,void *context)
{
    if(!frame)return 0u;
    size_t bits=encode(frame,NULL,progress,context);
    return bits==SIZE_MAX?0u:(bits+7u)/8u;
}
size_t comp_wba_frame_store_size(const uint8_t frame[5000])
{return comp_wba_frame_store_size_progress(frame,NULL,NULL);}
static void rewind_store(comp_wba_frame_store_t *store)
{
    store->input_bit=store->output=0u;store->remaining=0u;
    store->kind=store->value=0u;memset(store->row,255u,sizeof(store->row));
}
bool comp_wba_frame_store_write_progress(comp_wba_frame_store_t *store,const uint8_t frame[5000],comp_wba_frame_store_progress_fn_t progress,void *context)
{
    if(!store || !frame)return false;
    const size_t n=encode(frame,NULL,progress,context);
    /* Preflight before changing any committed byte. An unrepresentable
     * candidate is rejected BEFORE display activation by the presenter. */
    if(!n || n>sizeof(store->bytes)*8u)return false;
    store->valid=false;
    if(encode(frame,store->bytes,progress,context)!=n)return false;
    store->bit_length=(uint16_t)n;store->valid=true;rewind_store(store);return true;
}
bool comp_wba_frame_store_write(comp_wba_frame_store_t *store,const uint8_t frame[5000])
{return comp_wba_frame_store_write_progress(store,frame,NULL,NULL);}
static bool symbol(comp_wba_frame_store_t *store,uint8_t *value)
{
    uint16_t code=0u;
    for(unsigned n=1u;n<16u;++n) {
        if(store->input_bit>=store->bit_length)return false;
        const unsigned at=store->input_bit++;
        code=(uint16_t)((code<<1u)|((store->bytes[at/8u]>>(7u-(at&7u)))&1u));
        if(frame_counts[n] && code>=frame_first[n] && code-frame_first[n]<frame_counts[n]) {
            *value=frame_symbols[frame_indices[n]+code-frame_first[n]];return true;
        }
    }
    return false;
}
static bool next_row(comp_wba_frame_store_t *store)
{
    if(store->output>=5000u)return false;
    for(unsigned x=0u;x<25u;++x) {
        if(!store->remaining) {
            uint8_t code;if(!symbol(store,&code))return false;
            if(code<128u){store->kind=0u;store->value=0u;store->remaining=(uint8_t)(code+1u);}
            else if(code<192u) {
                if(!symbol(store,&store->value))return false;
                store->kind=1u;store->remaining=(uint8_t)(code-126u);
            } else {store->kind=2u;store->remaining=(uint8_t)(code-191u);}
        }
        uint8_t value=store->value;
        if(store->kind==2u && !symbol(store,&value))return false;
        store->row[x]^=value;--store->remaining;
    }
    store->output+=25u;
    return store->output!=5000u || (!store->remaining && store->input_bit==store->bit_length);
}
bool comp_wba_frame_store_read(comp_wba_frame_store_t *store,size_t offset,uint8_t *out,size_t count)
{
    if(!store || !store->valid || !out || offset>5000u || count>5000u-offset ||
        store->bit_length>sizeof(store->bytes)*8u || store->input_bit>store->bit_length ||
        store->output>5000u || store->output%25u || store->kind>2u)return false;
    while(count) {
        const size_t row_end=(offset/25u+1u)*25u;
        if(row_end<store->output)rewind_store(store);
        while(store->output<row_end)if(!next_row(store)){store->valid=false;return false;}
        size_t n=row_end-offset;if(n>count)n=count;
        memcpy(out,store->row+offset%25u,n);offset+=n;out+=n;count-=n;
    }
    return true;
}
