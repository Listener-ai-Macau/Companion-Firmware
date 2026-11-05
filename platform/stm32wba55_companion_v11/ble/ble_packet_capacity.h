#ifndef COMP_V11_BLE_PACKET_CAPACITY_H
#define COMP_V11_BLE_PACKET_CAPACITY_H

#include <stdint.h>

/* Application notification size is bounded by the actual ATT value capacity,
 * not by one radio PDU. L2CAP/controller fragmentation is valid even when DLE
 * octets/time become smaller. Forcing 43B audio notifications on a short 2M
 * PDU repeats the 20B product header and host callbacks for every fragment.
 * Retain negotiated bounds, queue backpressure and unchanged wire format. */
static inline uint16_t comp_v11_ble_compact_capacity(uint16_t value_bytes)
{
    if(value_bytes<=20u)return 0u;
    uint16_t audio_bytes=(uint16_t)(value_bytes-20u);
    return audio_bytes>489u ? 489u : audio_bytes;
}

/* Diagnostic estimate ONLY: encrypted airtime with no CTE is 112+8*N on 1M
 * or 60+4*N on 2M. N includes 20 product+3 ATT+4 L2CAP bytes. Both negotiated
 * octets and time constrain one LL PDU; they do not constrain an ATT message
 * reassembled from multiple PDUs. Zero means unknown or no single-PDU audio.
 * Core Vol6 PartB2.1/2.4.1; Vol3 PartA7.2. */
static inline uint16_t comp_v11_ble_ll_payload_capacity(
    uint16_t octets,uint16_t time_us,uint8_t phy)
{
    if((phy!=1u && phy!=2u) || octets<27u || octets>251u)return 0u;
    uint16_t overhead=phy==2u?60u:112u;
    uint16_t bit_time=phy==2u?4u:8u;
    if(time_us<=overhead)return 0u;
    uint16_t timed=(uint16_t)((time_us-overhead)/bit_time);
    if(octets>timed)octets=timed;
    return octets>=27u?octets:0u;
}

static inline uint16_t comp_v11_ble_single_ll_compact_capacity(
    uint16_t octets,uint16_t time_us,uint8_t phy)
{
    octets=comp_v11_ble_ll_payload_capacity(octets,time_us,phy);
    if(octets<=27u)return 0u;
    uint16_t audio_bytes=(uint16_t)(octets-27u);
    return audio_bytes>224u ? 224u : audio_bytes;
}

/* A short effective airtime can split each nominal251-byte host fragment
 * again. After bulk's actual2M negotiation, suggest that same physical
 * capacity explicitly to the official controller interface. This changes no
 * ATT value, audio framing or preferred2120us budget. Zero means no change;
 * unknown/invalid intervals, other PHYs and the already matching/full251-byte case stay intact.
 * The caller owns one attempt per explicit batch and a scoped251-byte restore.
 * This is a scheduling hypothesis, not evidence of radio packet counts. */
static inline uint16_t comp_v11_ble_bulk_aligned_octets(
    uint16_t octets,uint16_t time_us,uint8_t phy,uint16_t interval_units)
{
    if(phy!=2u || interval_units<6u || interval_units>3200u)return 0u;
    uint16_t timed=comp_v11_ble_ll_payload_capacity(octets,time_us,phy);
    return timed && timed<octets?timed:0u;
}

/* Same-original measurements with251/1590/2M/CI6 gave88.13KiB/s for
 *495-byte values versus61.82 for509:495+ATT3+L2CAP4 is exactly2*251.
 * Keep the negotiated509-byte ceiling, and only change normal sealed bulk
 * packet packing under that observed link. A measured226-byte radio budget
 * still prefragments at251 in the host stack:470+7=251+226, so its first host
 * fragment becomes226+25 and its second stays226, avoiding two extra tails.
 * The complete340us captures expose another concrete case: physical70 still
 * uses nominal251-byte host fragments.509+7 becomes251+251+14, observed as
 * 70,70,70,41,70,70,70,41,14.454+7 is251+3*70: the model removes two tails
 * and reduces the existing240-byte long-value staging from three calls to
 * two. This is a packing hypothesis, not measured radio/speed qualification.
 * Do not repeat the rejected CI12 adjustment or force single70-byte ATT
 * notifications with their many repeated product headers.
 * The physical packet ceiling is independent of connection interval: the
 * same actual251/965/2M budget at CI12 must not silently switch back to five
 * fragments. Unknown/invalid CI, other PHYs/budgets and recording/live mode
 * retain their capacity. Already prepared
 * packets are immutable; the transfer applies this ceiling on its next build.
 * A peer's smaller selected value remains a separate transfer bound. */
static inline uint16_t comp_v11_ble_bulk_compact_capacity(
    uint16_t value_bytes,uint16_t octets,uint16_t time_us,uint8_t phy,
    uint16_t interval_units,uint8_t sealed_bulk)
{
    uint16_t capacity=comp_v11_ble_compact_capacity(value_bytes);
    if(sealed_bulk && phy==2u && interval_units>=6u && interval_units<=3200u) {
        uint16_t physical=comp_v11_ble_ll_payload_capacity(octets,time_us,phy);
        /* Preserve the actually measured CI6/965 single-PDU policy. */
        if(octets==251u && time_us==965u && interval_units==6u && capacity>199u)return 199u;
        /* The configured controller ACL boundary remains251 bytes even when
         * the effective radio limit shrinks. R105 independently reassembled
         * 489-byte file payload as223/28/223/28/14 at953us. Keep one nominal
         * ACL prefix and fit the largest whole physical suffix into the
         * remaining negotiated value. This retains the known251->475,
         * 226->450 and70->434 policies and also handles actual223->447,
         * without a new magic time/phone entry or a DLE renegotiation.
         * No claim is made about the radio scheduling or measured throughput.
         * Smaller values within one nominal ACL, invalid/unknown budgets,
         * live recording and the wire protocol remain unchanged. */
        if(physical>=27u && capacity>224u) {
            uint16_t suffix=(uint16_t)(((capacity+27u-251u)/physical)*physical);
            if(suffix) {
                uint16_t packed=(uint16_t)(251u+suffix-27u);
                if(packed<capacity)return packed;
            }
        }
    }
    return capacity;
}

#endif
