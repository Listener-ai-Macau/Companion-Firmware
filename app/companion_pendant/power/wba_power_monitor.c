#include "wba_power_monitor.h"
#include "companion_v11_board.h"
#include <stddef.h>
#include <string.h>

#define SAMPLE_MS 5000u
#define VOLTAGE_STALE_MS 15000u
#define INPUT_STALE_MS 100u
#define PG_DEBOUNCE_MS 120u
#define STAT_STABLE_MS 2000u

bool comp_wba_power_profile_safe(const comp_wba_power_profile_t *p)
{
    if (!p || !p->divider_verified || !p->reference_verified ||
        p->reference_mv < p->reference_min_mv || p->reference_mv > 3600u ||
        p->minimum_battery_mv < 1000u || p->minimum_battery_mv >= p->maximum_battery_mv ||
        p->minimum_update_mv < p->minimum_battery_mv || p->minimum_update_mv > p->maximum_battery_mv ||
        p->adc_full_scale < 16u ||
        !comp_v11_battery_divider_safe(p->top_ohm, p->bottom_ohm,
                                       p->reference_min_mv, p->maximum_battery_mv)) return false;
    if (p->soc_point_count != 0u) {
        if (!p->soc_points || p->soc_point_count < 2u || p->soc_point_count > 16u) return false;
        for (uint8_t i=0; i<p->soc_point_count; ++i) {
            const comp_wba_soc_point_t *point=&p->soc_points[i];
            if (point->millivolts < p->minimum_battery_mv || point->millivolts > p->maximum_battery_mv ||
                point->percent > 100u || (i && (point->millivolts <= p->soc_points[i-1u].millivolts ||
                point->percent <= p->soc_points[i-1u].percent))) return false;
        }
    }
    return true;
}
static void unknown_charger(comp_wba_power_monitor_t *m)
{
    m->value.charger_valid=false; m->value.charger_present=false;
    m->value.charge_state=COMP_WBA_CHARGE_UNKNOWN;
    m->input_seen=false; m->blink_edges=0;
}
void comp_wba_power_monitor_init(comp_wba_power_monitor_t *m, const comp_wba_power_profile_t *p,
                                 const comp_wba_power_ports_t *ports, uint32_t now)
{
    if (!m) return;
    memset(m,0,sizeof(*m)); m->value.percent=255u; m->next_sample_ms=now;
    if (p) m->profile=*p;
    if (ports) m->ports=*ports;
    m->sampling_enabled=comp_wba_power_profile_safe(p) && ports && ports->gate &&
        ports->start && ports->read && ports->cancel;
    /* Even an invalid profile must make a best effort to keep P7 low. An
     * ambiguous write remains a sleep blocker until the owner can retry. */
    if (m->ports.gate && !m->ports.gate(m->ports.context,false)) {
        m->gate_may_be_on=true; m->gate_fault=true; m->gate_sample_verified=false; m->phase=COMP_WBA_BAT_CLEANUP; ++m->gate_errors;
    }
}
void comp_wba_power_monitor_inputs(comp_wba_power_monitor_t *m, bool valid,
                                   bool pg_high, bool stat_high, uint32_t now)
{
    if (!m) return;
    if (!valid || !m->profile.charger_pullups_verified) { unknown_charger(m); return; }
    if (!m->input_seen || now-m->input_ms > INPUT_STALE_MS) {
        unknown_charger(m); m->input_seen=true;
        m->pg_high=pg_high; m->stat_high=stat_high;
        m->pg_since_ms=m->stat_since_ms=m->stat_edge_ms=now;
    }
    m->input_ms=now;
    if (m->pg_high != pg_high) {
        m->pg_high=pg_high; m->pg_since_ms=now; m->blink_edges=0;
        m->stat_since_ms=m->stat_edge_ms=now;
        m->value.charger_valid=false; m->value.charge_state=COMP_WBA_CHARGE_UNKNOWN;
    }
    if (m->stat_high != stat_high) {
        uint32_t half_period=now-m->stat_edge_ms;
        /* Three successive half periods near 500ms reject insertion and
         * contact chatter. Stable STATUS cannot masquerade as fault blink. */
        m->blink_edges=(half_period >= 350u && half_period <= 700u && !pg_high) ?
            (uint8_t)(m->blink_edges < 3u ? m->blink_edges+1u : 3u) : 0u;
        m->stat_high=stat_high; m->stat_since_ms=m->stat_edge_ms=now;
        if (m->value.charge_state != COMP_WBA_CHARGE_FAULT)
            m->value.charge_state=COMP_WBA_CHARGE_UNKNOWN;
    }
    if (now-m->pg_since_ms < PG_DEBOUNCE_MS) return;
    m->value.charger_valid=true; m->value.charger_present=!pg_high;
    if (pg_high) m->value.charge_state=COMP_WBA_CHARGE_DISCHARGING;
    else if (m->blink_edges >= 3u) m->value.charge_state=COMP_WBA_CHARGE_FAULT;
    else if (now-m->stat_since_ms >= STAT_STABLE_MS)
        m->value.charge_state=stat_high ? COMP_WBA_CHARGE_POWERED_IDLE : COMP_WBA_CHARGE_CHARGING;
    /* After a detected fault, retain it through a stable two-second recovery
     * window, then clear the blink history along with the fault. */
    if (now-m->stat_since_ms >= STAT_STABLE_MS) {
        m->blink_edges=0;
        if (!pg_high) m->value.charge_state=stat_high ?
            COMP_WBA_CHARGE_POWERED_IDLE : COMP_WBA_CHARGE_CHARGING;
    }
}
bool comp_wba_power_monitor_enable_raw(comp_wba_power_monitor_t *m)
{
    if (!m || m->sampling_enabled || m->phase != COMP_WBA_BAT_IDLE ||
        m->gate_may_be_on || !m->ports.gate || !m->ports.start ||
        !m->ports.read || !m->ports.cancel || m->profile.adc_full_scale != 4095u ||
#if COMPANION_WBA_BATTERY_LINEAR_ESTIMATE
        /* Explicit Owner opt-in uses the confirmed nominal board divider.
         * HAL checks a fresh VREF before P7, then rejects saturation. This
         * raw path never changes production voltage/SOC/OTA qualification. */
        m->profile.top_ohm!=100000u || m->profile.bottom_ohm!=68000u ||
        m->profile.maximum_battery_mv!=4350u) return false;
#else
        !m->profile.divider_verified ||
        !comp_v11_battery_divider_safe(m->profile.top_ohm,m->profile.bottom_ohm,
            m->profile.reference_min_mv,m->profile.maximum_battery_mv)) return false;
#endif
    m->raw_diagnostic=true;
    m->sampling_enabled=true;
    return true;
}
static void cleanup(comp_wba_power_monitor_t *m, uint32_t now)
{
    if (!m->capture_gate && (!m->ports.gate || !m->ports.gate(m->ports.context,false))) {
        ++m->gate_errors; m->gate_fault=true; m->gate_sample_verified=false; m->gate_may_be_on=true; return;
    }
    if (!m->capture_gate) {
        if (m->gate_sample_verified) m->gate_fault=false;
        m->gate_sample_verified=false;
    }
    m->gate_may_be_on=false; m->phase=COMP_WBA_BAT_IDLE;
    m->next_sample_ms=now+SAMPLE_MS;
}
bool comp_wba_power_monitor_prepare_capture(comp_wba_power_monitor_t *m,uint32_t now)
{
    if(!m)return false;
    if(!m->ports.cancel)return !comp_wba_power_monitor_busy(m)&&!m->sampling_enabled;
    if(m->capture_gate)return true;
    m->ports.cancel(m->ports.context);
    if(m->sampling_enabled && !m->raw_diagnostic && comp_wba_power_profile_safe(&m->profile)) {
        if(!m->ports.gate || !m->ports.gate(m->ports.context,true)) {
            ++m->gate_errors;m->gate_fault=true;m->gate_sample_verified=false;m->phase=COMP_WBA_BAT_CLEANUP;m->gate_may_be_on=true;return false;
        }
        m->capture_gate=true;m->gate_sample_verified=false;m->gate_may_be_on=false;m->phase=COMP_WBA_BAT_IDLE;
        m->next_sample_ms=now;
    } else if(m->phase!=COMP_WBA_BAT_IDLE || m->gate_may_be_on) {
        m->phase=COMP_WBA_BAT_CLEANUP;cleanup(m,now);
    }
    return m->phase==COMP_WBA_BAT_IDLE && !m->gate_may_be_on;
}
void comp_wba_power_monitor_release_capture(comp_wba_power_monitor_t *m,uint32_t now)
{
    if(!m || !m->capture_gate)return;
    m->capture_gate=false;
    m->ports.cancel(m->ports.context);
    m->phase=COMP_WBA_BAT_CLEANUP;m->gate_may_be_on=true;
    cleanup(m,now);
}
static bool voltage(comp_wba_power_monitor_t *m, uint16_t raw, uint32_t now)
{
    /* Raw engineering samples are available through the board ADC port;
     * they never satisfy the production cell-voltage or SOC contract. */
    if (m->raw_diagnostic) {
        const comp_wba_power_profile_t *p=&m->profile;
        if (p->adc_full_scale<16u || !p->bottom_ohm || raw>=p->adc_full_scale-2u) {
            ++m->sample_errors;return false;
        }
        /* This is only an engineering plausibility check. A raw conversion
         * close to zero cannot establish recovery of the cell-sampling path;
         * it is not a qualified cell voltage or a low-battery decision. */
        uint32_t input_mv=((uint32_t)raw*p->reference_mv+p->adc_full_scale/2u)/p->adc_full_scale;
        uint64_t nominal_mv=((uint64_t)input_mv*((uint64_t)p->top_ohm+p->bottom_ohm)+p->bottom_ohm/2u)/p->bottom_ohm;
        if(nominal_mv<p->minimum_battery_mv || nominal_mv>p->maximum_battery_mv) {
            ++m->sample_errors;return false;
        }
        return true;
    }
    const comp_wba_power_profile_t *p=&m->profile;
    uint64_t mv=(uint64_t)raw*p->reference_mv*((uint64_t)p->top_ohm+p->bottom_ohm)/
        ((uint64_t)p->adc_full_scale*p->bottom_ohm);
    m->value.voltage_valid=false; m->value.percent_valid=false; m->value.percent=255u;
    if (raw >= p->adc_full_scale-2u || mv < p->minimum_battery_mv || mv > p->maximum_battery_mv) {
        ++m->sample_errors; return false;
    }
    m->value.millivolts=(uint16_t)mv; m->voltage_ms=now; m->value.voltage_valid=true;
    if (!p->soc_point_count) return true;
    uint8_t percent=p->soc_points[0].percent;
    for (uint8_t i=1u; i<p->soc_point_count; ++i) {
        const comp_wba_soc_point_t *a=&p->soc_points[i-1u], *b=&p->soc_points[i];
        if (mv >= b->millivolts) { percent=b->percent; continue; }
        if (mv > a->millivolts) percent=(uint8_t)(a->percent+
            (mv-a->millivolts)*(b->percent-a->percent)/(b->millivolts-a->millivolts));
        break;
    }
    m->value.percent=percent; m->value.percent_valid=true;
    return true;
}
void comp_wba_power_monitor_poll(comp_wba_power_monitor_t *m, bool allowed, uint32_t now)
{
    uint16_t raw=0;
    if (!m) return;
    if (m->phase == COMP_WBA_BAT_CLEANUP) { cleanup(m,now); return; }
    if (!allowed && m->phase != COMP_WBA_BAT_IDLE) {
        m->ports.cancel(m->ports.context); m->phase=COMP_WBA_BAT_CLEANUP;
        return;
    }
    if (m->phase == COMP_WBA_BAT_IDLE) {
        if (!allowed || !m->sampling_enabled || (int32_t)(now-m->next_sample_ms)<0) return;
        m->gate_may_be_on=true;
        if (!m->capture_gate && !m->ports.gate(m->ports.context,true)) { ++m->gate_errors; m->gate_fault=true; m->gate_sample_verified=false; m->phase=COMP_WBA_BAT_CLEANUP; return; }
        m->gate_sample_verified=false;
        m->adc_since_ms=now; m->phase=COMP_WBA_BAT_SETTLE; return;
    }
    if (m->phase == COMP_WBA_BAT_SETTLE) {
        if (now-m->adc_since_ms < 2u) return;
        if (!m->ports.start(m->ports.context)) {
            ++m->sample_errors; m->sample_fault=true; m->value.voltage_valid=false; m->value.percent_valid=false;
            m->ports.cancel(m->ports.context); m->phase=COMP_WBA_BAT_CLEANUP; return;
        }
        m->adc_since_ms=now; m->phase=COMP_WBA_BAT_CONVERT; return;
    }
    comp_wba_adc_result_t result=m->ports.read(m->ports.context,&raw);
    if (result == COMP_WBA_ADC_PENDING && now-m->adc_since_ms < COMP_WBA_BATTERY_TRANSACTION_MS) return;
    if (result == COMP_WBA_ADC_READY) {
        m->sample_fault=!voltage(m,raw,now);
        /* Engineering raw observations do not establish the physical
         * divider/voltage contract and cannot clear a gate fault. */
        m->gate_sample_verified=!m->sample_fault && !m->raw_diagnostic;
    }
    else { ++m->sample_errors; m->sample_fault=true; m->gate_sample_verified=false; m->value.voltage_valid=false; m->value.percent_valid=false; }
    m->ports.cancel(m->ports.context); m->phase=COMP_WBA_BAT_CLEANUP;
}
comp_wba_power_snapshot_t comp_wba_power_monitor_snapshot(const comp_wba_power_monitor_t *m, uint32_t now)
{
    comp_wba_power_snapshot_t v={.percent=255u};
    if (!m) return v;
    v=m->value;
    if (!m->sampling_enabled || now-m->voltage_ms >= VOLTAGE_STALE_MS) {
        v.voltage_valid=false; v.percent_valid=false;
    }
    if (!v.voltage_valid) v.millivolts=0u;
    if (!v.percent_valid) v.percent=255u;
    if (!m->input_seen || now-m->input_ms > INPUT_STALE_MS) {
        v.charger_valid=false; v.charger_present=false; v.charge_state=COMP_WBA_CHARGE_UNKNOWN;
    }
    return v;
}
bool comp_wba_power_monitor_busy(const comp_wba_power_monitor_t *m)
{ return m && (m->phase != COMP_WBA_BAT_IDLE || m->gate_may_be_on || m->capture_gate); }
bool comp_wba_power_recording_limits_safe(const comp_wba_power_profile_t *p)
{
    return comp_wba_power_profile_safe(p) && p->recording_limits_verified &&
        p->recording_stop_mv>p->minimum_battery_mv &&
        p->recording_stop_mv<p->recording_resume_mv &&
        p->recording_resume_mv<=p->maximum_battery_mv;
}
void comp_wba_power_monitor_recording_guard(comp_wba_power_monitor_t *m,uint32_t now)
{
    if(!m)return;
    comp_wba_power_snapshot_t v=comp_wba_power_monitor_snapshot(m,now);
    if(!comp_wba_power_recording_limits_safe(&m->profile) || m->raw_diagnostic || !v.voltage_valid) {
        m->recording_low_samples=0u;m->recording_recovery_samples=0u;
        return;
    }
    if(m->recording_sample_seen && m->recording_sample_ms==m->voltage_ms)return;
    m->recording_sample_ms=m->voltage_ms;m->recording_sample_seen=true;
    if(v.millivolts<=m->profile.recording_stop_mv) {
        m->recording_recovery_samples=0u;
        if(m->recording_low_samples<2u)++m->recording_low_samples;
        if(m->recording_low_samples==2u)m->recording_power_blocked=true;
    } else {
        m->recording_low_samples=0u;
        if(v.millivolts>=m->profile.recording_resume_mv) {
            if(m->recording_recovery_samples<2u)++m->recording_recovery_samples;
            if(m->recording_recovery_samples==2u)m->recording_power_blocked=false;
        } else m->recording_recovery_samples=0u;
    }
}
bool comp_wba_power_monitor_recording_allowed(const comp_wba_power_monitor_t *m,uint32_t now)
{
    if(!m)return false;
    /* The current unqualified engineering build keeps normal capture. A
     * previously established block cannot be cleared by losing qualification. */
    if(m->recording_power_blocked)return false;
    if(!m->profile.recording_limits_verified)return true;
    if(!comp_wba_power_recording_limits_safe(&m->profile))return false;
    comp_wba_power_snapshot_t v=comp_wba_power_monitor_snapshot(m,now);
    return !m->raw_diagnostic && v.voltage_valid &&
        v.millivolts>m->profile.recording_stop_mv;
}
uint16_t comp_wba_power_monitor_ota_blockers(const comp_wba_power_monitor_t *m, uint32_t now)
{
    comp_wba_power_snapshot_t v=comp_wba_power_monitor_snapshot(m,now);
    if (v.charger_valid && v.charge_state == COMP_WBA_CHARGE_FAULT) return COMP_WBA_OTA_CHARGER_FAULT;
    if (v.charger_valid && v.charger_present &&
        (v.charge_state == COMP_WBA_CHARGE_CHARGING || v.charge_state == COMP_WBA_CHARGE_POWERED_IDLE)) return 0u;
    if (!v.voltage_valid || !m) return COMP_WBA_OTA_POWER_UNKNOWN;
    return v.millivolts < m->profile.minimum_update_mv || (v.percent_valid && v.percent < 30u) ?
        COMP_WBA_OTA_POWER_LOW : 0u;
}
