#ifndef COMP_V11_OTA_PAGE_STREAM_H
#define COMP_V11_OTA_PAGE_STREAM_H
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <string.h>

typedef struct {
    void *context;
    bool (*prepare)(void *,uint32_t);
    bool (*program)(void *,uint32_t,const uint8_t *,size_t);
    /* Copy only the next COMPLETE, pinned, sequential DATA command. Stop at
     * controls, partial/malformed commands, changed owner or disconnect. */
    size_t (*following)(void *,uint32_t,uint8_t *,size_t);
} comp_ota_page_ports_t;

/* physical_prefix can lead the core's acknowledged prefix by at most255B.
 * It records only successful physical writes, never a volatile page buffer.
 * The following queue command remains immutable until the core consumes it;
 * its prewritten prefix is skipped then, without programming those bits twice.
 * No future command is acknowledged or removed here. Whole-file retry erases
 * its newly claimed range and resets physical_prefix, including after reboot.
 * The256B scratch is bounded stack, not resident RAM or a new queue slot. */
static inline bool comp_ota_page_stream_write(const comp_ota_page_ports_t *p,
    uint32_t *physical_prefix,uint32_t at,const uint8_t *bytes,size_t length,
    uint32_t expected)
{
    if(!p||!p->prepare||!p->program||!physical_prefix||!bytes||!length||
       at>expected||length>expected-at||*physical_prefix<at||
       *physical_prefix>expected||*physical_prefix-at>255u)return false;
    size_t skip=*physical_prefix-at;if(skip>length)skip=length;
    at+=(uint32_t)skip;bytes+=skip;length-=skip;
    uint8_t page[256];
    while(length) {
        if(!p->prepare(p->context,at))return false;
        size_t room=256u-(at&255u),current=length<room?length:room,extra=0u;
        const uint8_t *source=bytes;
        if(current==length&&room>current&&p->following) {
            size_t capacity=room-current;
            if(capacity>expected-at-current)capacity=expected-at-current;
            if(capacity) {
                memcpy(page,bytes,current);
                extra=p->following(p->context,at+(uint32_t)current,page+current,capacity);
                if(extra>capacity)return false;
                if(extra)source=page;
            }
        }
        if(!p->program(p->context,at,source,current+extra))return false;
        *physical_prefix=at+(uint32_t)(current+extra);
        at+=(uint32_t)current;bytes+=current;length-=current;
    }
    return true;
}
#endif
