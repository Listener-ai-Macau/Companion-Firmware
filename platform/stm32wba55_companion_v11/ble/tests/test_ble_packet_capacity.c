#include "ble_packet_capacity.h"
#include <assert.h>
#include <stdio.h>

int main(void)
{
    /* The observed effective251/965/2M can carry226, not251 bytes. */
    assert(comp_v11_ble_ll_payload_capacity(251u,965u,2u)==226u);
    assert(comp_v11_ble_bulk_aligned_octets(251u,965u,2u,6u)==226u);
    assert(comp_v11_ble_bulk_aligned_octets(226u,965u,2u,6u)==0u);
    /* Exact encrypted airtime boundary; historical1590 already permits251. */
    assert(comp_v11_ble_ll_payload_capacity(251u,1063u,2u)==250u);
    assert(comp_v11_ble_ll_payload_capacity(251u,1064u,2u)==251u);
    assert(comp_v11_ble_bulk_aligned_octets(251u,1590u,2u,6u)==0u);
    assert(comp_v11_ble_ll_payload_capacity(251u,2120u,1u)==251u);
    /* A small peer/time, or a different connection/PHY, is not enlarged. */
    assert(comp_v11_ble_ll_payload_capacity(70u,965u,2u)==70u);
    assert(comp_v11_ble_ll_payload_capacity(251u,340u,2u)==70u);
    assert(comp_v11_ble_bulk_aligned_octets(251u,965u,2u,12u)==226u);
    assert(comp_v11_ble_bulk_aligned_octets(251u,965u,2u,24u)==226u);
    assert(comp_v11_ble_bulk_aligned_octets(251u,965u,2u,0u)==0u);
    assert(comp_v11_ble_bulk_aligned_octets(251u,965u,2u,3201u)==0u);
    assert(comp_v11_ble_bulk_aligned_octets(251u,965u,1u,6u)==0u);
    assert(comp_v11_ble_ll_payload_capacity(251u,0u,2u)==0u);
    assert(comp_v11_ble_ll_payload_capacity(0u,965u,2u)==0u);
    assert(comp_v11_ble_ll_payload_capacity(252u,965u,2u)==0u);
    assert(comp_v11_ble_ll_payload_capacity(251u,965u,3u)==0u);
    assert(comp_v11_ble_ll_payload_capacity(27u,328u,1u)==27u);
    assert(comp_v11_ble_ll_payload_capacity(27u,327u,1u)==0u);
    /* Existing compact notification capacity remains maximum489 payload. */
    assert(comp_v11_ble_compact_capacity(509u)==489u);
    assert(comp_v11_ble_compact_capacity(244u)==224u);
    assert(comp_v11_ble_single_ll_compact_capacity(251u,965u,2u)==199u);
    assert(comp_v11_ble_single_ll_compact_capacity(251u,1590u,2u)==224u);
    /* Preserve512ATT/509value negotiation; pack sealed data into twoPDUs. */
    assert(comp_v11_ble_bulk_compact_capacity(509u,251u,1590u,2u,6u,1u)==475u);
    assert(comp_v11_ble_bulk_compact_capacity(509u,251u,1064u,2u,6u,1u)==475u);
    assert(comp_v11_ble_bulk_compact_capacity(495u,251u,1590u,2u,6u,1u)==475u);
    assert(comp_v11_ble_bulk_compact_capacity(244u,251u,1590u,2u,6u,1u)==224u);
    /* Do not shrink unqualified links or live/ordinary traffic. */
    assert(comp_v11_ble_bulk_compact_capacity(509u,251u,965u,2u,6u,1u)==199u);
    assert(comp_v11_ble_bulk_compact_capacity(509u,226u,965u,2u,6u,1u)==450u);
    assert(comp_v11_ble_bulk_compact_capacity(470u,226u,965u,2u,6u,1u)==450u);
    assert(comp_v11_ble_bulk_compact_capacity(244u,226u,965u,2u,6u,1u)==224u);
    assert(20u+450u+7u==251u+226u);
    /* Captured340us link: retain max509 negotiation, remove the two tails
     * after the host stack's nominal251-byte prefragment. Smaller peer and
     * live/unknown budgets remain independent; this is not a speed test. */
    assert(comp_v11_ble_bulk_compact_capacity(509u,251u,340u,2u,6u,1u)==434u);
    assert(comp_v11_ble_bulk_compact_capacity(509u,70u,340u,2u,12u,1u)==434u);
    assert(comp_v11_ble_bulk_compact_capacity(454u,70u,340u,2u,6u,1u)==434u);
    assert(comp_v11_ble_bulk_compact_capacity(244u,70u,340u,2u,6u,1u)==224u);
    assert(comp_v11_ble_bulk_compact_capacity(509u,251u,340u,2u,6u,0u)==489u);
    assert(comp_v11_ble_bulk_compact_capacity(509u,251u,340u,1u,6u,1u)==489u);
    assert(comp_v11_ble_bulk_compact_capacity(509u,251u,340u,2u,0u,1u)==489u);
    assert(comp_v11_ble_bulk_compact_capacity(509u,251u,0u,2u,6u,1u)==489u);
    assert(20u+434u+7u==251u+3u*70u);
    assert(comp_v11_ble_bulk_compact_capacity(509u,251u,1063u,2u,6u,1u)==474u);
    assert(comp_v11_ble_bulk_compact_capacity(509u,226u,1590u,2u,6u,1u)==450u);
    assert(comp_v11_ble_bulk_compact_capacity(509u,251u,1590u,1u,6u,1u)==489u);
    assert(comp_v11_ble_bulk_compact_capacity(509u,251u,1590u,2u,12u,1u)==475u);
    assert(comp_v11_ble_bulk_compact_capacity(509u,251u,965u,2u,12u,1u)==450u);
    assert(comp_v11_ble_bulk_compact_capacity(244u,251u,965u,2u,12u,1u)==224u);
    assert(comp_v11_ble_bulk_compact_capacity(509u,251u,965u,2u,12u,0u)==489u);
    assert(comp_v11_ble_bulk_compact_capacity(509u,251u,965u,2u,0u,1u)==489u);
    assert(comp_v11_ble_bulk_compact_capacity(509u,251u,1590u,2u,6u,0u)==489u);
    assert(comp_v11_ble_bulk_compact_capacity(244u,251u,965u,2u,6u,1u)==199u);
    assert(comp_v11_ble_bulk_compact_capacity(219u,251u,965u,2u,6u,1u)==199u);
    assert(comp_v11_ble_bulk_compact_capacity(180u,251u,965u,2u,6u,1u)==160u);
    assert(comp_v11_ble_bulk_compact_capacity(509u,251u,965u,2u,6u,0u)==489u);
    assert(199u+20u+7u==226u);
    puts("PASS_WBA_BLE_EFFECTIVE_PACKET_CAPACITY_SOFTWARE_ONLY");
    return 0;
}
