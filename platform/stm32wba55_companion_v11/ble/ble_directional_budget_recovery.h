#ifndef COMP_BLE_DIRECTIONAL_BUDGET_RECOVERY_H
#define COMP_BLE_DIRECTIONAL_BUDGET_RECOVERY_H
#include <stdbool.h>
#include <stdint.h>
/* Product recovery candidate for an OBSERVED 2M budget transition:
 * state1: both340 -> local RX recovers while local TX remains340;
 * state3: previously both>340 -> both340 after initial DLE accepted.
 * State3 is admitted only by active bulk, ACTUAL CI6 and a200ms settle
 * after that CI event. Starting slow or starting bulk alone never arms it.
 * State0 idle,1/3 pending,2 attempted. At most ONE attempt per connection.
 * The current event values stay authoritative; no synthetic capacity.
 */
static inline bool comp_ble_budget_recovery_observe(uint8_t *state,
    bool initial_accepted,bool phy2,uint16_t old_tx,uint16_t old_rx,
    uint16_t tx,uint16_t rx,uint32_t now,uint32_t *ready_after)
{
    if(*state==2u)return false;
    if(initial_accepted && phy2 && old_tx>340u && old_rx>340u &&
       tx==340u && rx==340u) {
        *state=3u;*ready_after=now+200u;return true;
    }
    if(*state==3u && tx==340u && rx==340u)return false;
    if(tx!=340u || rx<=340u){*state=0u;return false;}
    if(!initial_accepted || !phy2 || old_tx!=340u || old_rx!=340u)return false;
    *state=1u;*ready_after=now+200u;return true;
}
static inline bool comp_ble_budget_recovery_take(uint8_t *state,
    bool commands_allowed,bool secured,bool ci_ready,bool phy2,
    uint16_t tx,uint16_t rx,uint32_t now,uint32_t ready_after)
{
    if((*state!=1u && *state!=3u) || !commands_allowed || !secured || !ci_ready || !phy2 ||
       tx!=340u || (*state==1u ? rx<=340u : rx!=340u) ||
       (int32_t)(now-ready_after)<0)return false;
    *state=2u;return true;
}
#endif
