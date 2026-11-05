#include "../ble_peer_indication.h"
#include <assert.h>
#include <stdio.h>

int main(void)
{
    comp_v11_peer_indication_t s={0};
    /* R85 phone ATT 1d03000100ffff -> official legacy event on handle 0x0202.
     * This is metadata only. No private value or pairing credential fixture. */
    const uint8_t legacy[]={2,2,3,0,4,1,0,255,255};
    const uint8_t extended[]={2,2,3,0,0,0,4,0,1,0,255,255};
    assert(!comp_v11_peer_indication_receive(&s,0x202,false,false,legacy,sizeof legacy,10));
    assert(!comp_v11_peer_indication_receive(&s,0x203,true,false,legacy,sizeof legacy,10));
    assert(!comp_v11_peer_indication_receive(&s,0x202,true,false,legacy,sizeof legacy-1,10));
    assert(!comp_v11_peer_indication_receive(&s,0x202,true,true,extended,7,10));
    assert(comp_v11_peer_indication_receive(&s,0x202,true,false,legacy,sizeof legacy,10));
    assert(s.attribute==3 && s.pending && s.attempts==0);
    assert(!comp_v11_peer_indication_due(&s,0x202,true,false,10));
    assert(comp_v11_peer_indication_due(&s,0x202,true,true,10));
    comp_v11_peer_indication_result(&s,0,false,10);
    assert(!s.pending && !comp_v11_peer_indication_due(&s,0x202,true,true,11));
    puts("PASS captured Service Changed event queues one foreground confirmation; no command in receive callback");

    assert(comp_v11_peer_indication_receive(&s,0x202,true,true,extended,sizeof extended,20));
    comp_v11_peer_indication_result(&s,0x64,true,20);
    assert(!comp_v11_peer_indication_receive(&s,0x202,true,true,extended,sizeof extended,21));
    assert(s.attempts==1 && s.deadline==1020);
    assert(!comp_v11_peer_indication_due(&s,0x202,true,true,29));
    assert(comp_v11_peer_indication_due(&s,0x202,true,true,30));
    for(unsigned i=1;i<8;++i)comp_v11_peer_indication_result(&s,0x93,true,30+i*10);
    assert(!s.pending && s.attempts==8);
    assert(comp_v11_peer_indication_receive(&s,0x202,true,false,legacy,sizeof legacy,100));
    assert(!comp_v11_peer_indication_due(&s,0x202,true,true,1100) && !s.pending);
    assert(comp_v11_peer_indication_receive(&s,0x202,true,false,legacy,sizeof legacy,1200));
    comp_v11_peer_indication_result(&s,0x0c,false,1200);assert(!s.pending);
    puts("PASS retries are paced and finite; duplicates cannot renew deadline; permanent failure stops");

    assert(comp_v11_peer_indication_receive(&s,0x202,true,false,legacy,sizeof legacy,UINT32_MAX-5));
    assert(comp_v11_peer_indication_due(&s,0x202,true,true,1));
    assert(!comp_v11_peer_indication_due(&s,0x203,true,true,1) && !s.pending);
    assert(comp_v11_peer_indication_receive(&s,0x202,true,false,legacy,sizeof legacy,1));
    comp_v11_peer_indication_reset(&s);
    assert(!comp_v11_peer_indication_due(&s,0x202,true,true,2));
    puts("PASS timer wrap, disconnect and recycled connection handle cannot confirm stale indication");
    return 0;
}
