#ifndef COMP_V11_BLE_LINK_BUDGET_H
#define COMP_V11_BLE_LINK_BUDGET_H
#include <stdint.h>
#define COMP_V11_LINK_BUDGET_BYTES 20u
/* Metadata from real controller events, never requested/supported maxima.
 * An absent DLE/PHY event remains unknown. Not an authorization or RF proof. */
typedef struct {
    uint8_t flags,tx_phy,rx_phy;
    uint16_t tx_octets,tx_time,rx_octets,rx_time,interval,mtu;
} comp_v11_ble_link_budget_t;
static inline void comp_v11_ble_link_budget_encode(uint8_t out[20],const comp_v11_ble_link_budget_t *s)
{
    for(unsigned i=0;i<20u;++i)out[i]=0u;
    out[0]='B';out[1]='L';out[2]='K';out[3]='1';
    if(!s)return;
    out[4]=s->flags;out[5]=s->tx_phy;out[6]=s->rx_phy;
    const uint16_t fields[6]={s->tx_octets,s->tx_time,s->rx_octets,s->rx_time,s->interval,s->mtu};
    for(unsigned i=0;i<6u;++i){out[8u+2u*i]=(uint8_t)fields[i];out[9u+2u*i]=(uint8_t)(fields[i]>>8);}
}
#endif
