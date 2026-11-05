#include "../ble_route_observation.h"
#include <assert.h>
#include <stdio.h>
int main(void) {
 comp_v11_ble_route_observation_t m={0};comp_v11_ble_route_slot_t *s=&m.job[0];
 comp_v11_ble_route_ready(s,100u);comp_v11_ble_route_ready(s,300u);comp_v11_ble_route_run(s,500u);
 assert(s->total_us==400u&&s->max_us==400u&&(s->word&ROUTE_COUNT)==1u);
 comp_v11_ble_route_ready(s,UINT32_MAX-9u);comp_v11_ble_route_run(s,10u);
 assert(s->total_us==420u&&(s->word&ROUTE_COUNT)==2u);
 /* A new ISR marker published before an atomic count increment survives. */
 comp_v11_ble_route_ready(s,700u);(void)route_add(&s->word,1u);
 assert((s->word&ROUTE_PENDING)&&s->since_us==700u);comp_v11_ble_route_run(s,710u);
 comp_v11_ble_route_run(s,800u);assert((s->word&ROUTE_UNMARKED)&&(s->word&ROUTE_COUNT)==4u);
 uint8_t e[9]={4,255,6,0x12,0x34,0,0,1,0};
 assert(comp_v11_ble_route_pool_packet(e,9,0x3412));
 assert(!comp_v11_ble_route_pool_packet(e,8,0x3412));
 assert(!comp_v11_ble_route_pool_packet(e,9,0x3512));e[7]=0;
 assert(!comp_v11_ble_route_pool_packet(e,9,0x3412));
 puts("PASS earliest event marker, ISR pending-bit preservation, wraparound, partial flags and exact pool event framing");return 0;
}
