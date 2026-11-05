#define main original_allocator_fixture_main
#include "test_companion_segment_reserve.c"
#undef main

static void rotated_short_sessions(void)
{
    comp_segment_catalog_t c,rebooted;setup(&c);
    comp_segment_entry_t protected=entry(&c,10,4096,4096);put(&c,&protected);
    memset(media+BASE+4096,0xA5,4096);
    unsigned seen=0u;
    for(unsigned i=0;i<12u;i++) {
        comp_segment_entry_t e=entry(&c,100u+i,0,0);e.descriptor.recording_id=0;
        comp_segment_reserve_t r={0};
        assert(comp_segment_reserve_begin_rotated(&r,&c,&e,8192)==COMP_SEG_PENDING);
        assert(finish_reserve(&r)==COMP_SEG_OK);
        assert(e.extent_offset>=8192 && (e.extent_offset-8192)%8192==0);
        assert(media[BASE+4096]==0xA5 && media[BASE+8191]==0xA5);
        seen |= 1u << ((e.extent_offset-8192)/8192);
        comp_segment_entry_t *owned=0;assert(comp_segment_reserve_take(&r,&owned)&&owned==&e);
        assert(comp_segment_catalog_cancel_unwritten_begin(&c,&e)==COMP_SEG_PENDING);
        assert(finish_catalog(&c)==COMP_SEG_OK);
        if(i==5u) { mount(&rebooted);assert(finish_catalog(&rebooted)==COMP_SEG_OK);c=rebooted; }
    }
    unsigned distinct=0u;for(unsigned x=seen;x;x>>=1)distinct+=x&1u;
    printf("ROTATION distinct=%u slots mask=%x; protected preserved; restart persists next_id\n",distinct,seen);
    assert(distinct>=4u);
}
static void fragmented_gap_slots(void)
{
    for(unsigned i=0;i<35u;i++) {
        comp_segment_catalog_t c;setup(&c);
        comp_segment_entry_t protected=entry(&c,10,4096,4096);put(&c,&protected);
        c.next_id=100u+i; /* vary selector; the test does not remount this fabricated identity */
        comp_segment_entry_t e=entry(&c,20,0,0);e.descriptor.recording_id=0;
        comp_segment_reserve_t r={0};
        assert(comp_segment_reserve_begin_rotated(&r,&c,&e,8192)==COMP_SEG_PENDING);
        assert(finish_reserve(&r)==COMP_SEG_OK);
        assert(e.extent_offset>=8192 && (e.extent_offset-8192)%8192==0);
        uint32_t before=(DATA-8192)/8192;
        uint32_t after=(e.extent_offset-8192)/8192+(DATA-e.extent_offset-8192)/8192;
        assert(before==after+1u);
    }
    puts("FRAGMENT_GAP: no whole extent lost in 35 selector positions");
}

static uint32_t rnd=0x5a17u;
static uint32_t next_random(void){rnd^=rnd<<13;rnd^=rnd>>17;rnd^=rnd<<5;return rnd;}
static void many_gap_arrangements(void)
{
    for(unsigned t=0;t<500u;t++) {
        comp_segment_catalog_t c;setup(&c);uint32_t occupied=0u;
        for(unsigned j=0;j<4u;j++) {
            unsigned slot=next_random()%16u;
            if(occupied & (1u<<slot))continue;
            occupied|=1u<<slot;comp_segment_entry_t old=entry(&c,30u+j,slot*4096u,4096u);put(&c,&old);
            memset(media+BASE+slot*4096u,0xA5,4096u);
        }
        const unsigned size=(next_random()%4u)+1u;
        unsigned before=0u,run=0u;
        for(unsigned j=0;j<=16u;j++) {
            if(j<16u && !(occupied&(1u<<j)))run++;
            else {before+=run/size;run=0u;}
        }
        c.next_id=1000u+t;
        comp_segment_entry_t e=entry(&c,100u+t,0,0);e.descriptor.recording_id=0;comp_segment_reserve_t r={0};
        assert(comp_segment_reserve_begin_rotated(&r,&c,&e,size*4096u)==COMP_SEG_PENDING);
        comp_segment_result_t result=finish_reserve(&r);
        if(!before){assert(result==COMP_SEG_FULL);continue;}
        if(result!=COMP_SEG_OK){printf("failed t=%u occupancy=%x size=%u before=%u result=%d hint=%u\n",t,occupied,size,before,(int)result,r.hint);assert(0);}
        unsigned start=e.extent_offset/4096u;
        for(unsigned j=0;j<size;j++){assert(!(occupied&(1u<<(start+j))));occupied|=1u<<(start+j);}
        unsigned after=0u;run=0u;
        for(unsigned j=0;j<=16u;j++) {
            if(j<16u && !(occupied&(1u<<j)))run++;
            else {after+=run/size;run=0u;}
        }
        if(before!=after+1u){printf("capacity failure t=%u before=%u after=%u size=%u start=%u hint=%u\n",t,before,after,size,start,r.hint);assert(0);}
        for(unsigned j=0;j<16u;j++)if(media[BASE+j*4096u]==0xA5)assert(media[BASE+j*4096u+4095u]==0xA5);
    }
    puts("500 layouts: occupancy protected and each allocation consumes exactly one whole available extent");
}

static void complete_ring_capacity(void)
{
    for(unsigned t=0;t<100u;t++) {
        comp_segment_catalog_t c;setup(&c);uint32_t occupied=0u;
        for(unsigned j=0;j<4u;j++) {
            unsigned slot=next_random()%16u;if(occupied&(1u<<slot))continue;
            occupied|=1u<<slot;comp_segment_entry_t old=entry(&c,30u+j,slot*4096u,4096u);put(&c,&old);
        }
        const unsigned size=(next_random()%3u)+1u;unsigned expected=0u,run=0u;
        for(unsigned j=0;j<=16u;j++){
            if(j<16u && !(occupied&(1u<<j)))run++;else{expected+=run/size;run=0u;}
        }
        if(!expected)continue;
        c.next_id=2000u+t;uint32_t hint=0u;
        for(unsigned j=0;j<expected;j++) {
            comp_segment_entry_t e=entry(&c,300u+j,0,0);e.descriptor.recording_id=0;comp_segment_reserve_t r={0};
            comp_segment_result_t begun=j==0u?comp_segment_reserve_begin_rotated(&r,&c,&e,size*4096u):comp_segment_reserve_begin(&r,&c,&e,size*4096u,hint);
            assert(begun==COMP_SEG_PENDING);
            comp_segment_result_t result=finish_reserve(&r);
            if(result!=COMP_SEG_OK){printf("RING incomplete t=%u step=%u/%u size=%u hint=%u result=%d\n",t,j,expected,size,hint,(int)result);assert(0);}
            hint=e.extent_offset+e.reserved_bytes;if(hint==DATA)hint=0u;
            comp_segment_entry_t *owned=0;assert(comp_segment_reserve_take(&r,&owned)&&owned==&e);
        }
    }
    puts("100 layouts: rotated first extent followed by normal successor allocates all preflight whole slots");
}
int main(void) { assert(original_allocator_fixture_main()==0); rotated_short_sessions();fragmented_gap_slots();many_gap_arrangements();complete_ring_capacity();return 0; }
