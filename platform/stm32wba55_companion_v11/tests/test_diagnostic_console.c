#include "diagnostic_console.h"

#include <stdio.h>
#include <string.h>

#define CHECK(x) do { if (!(x)) { printf("FAIL line=%d %s\n", __LINE__, #x); return 1; } } while (0)

typedef struct {
    char text[4096];
    size_t length;
    unsigned calls, fail_call;
} sink_t;

static bool capture(void *context,const char *line)
{
    sink_t *sink=context;
    size_t n=strlen(line);
    ++sink->calls;
    if(sink->calls==sink->fail_call)return false;
    if(n>=sizeof(sink->text)-sink->length)return false;
    memcpy(sink->text+sink->length,line,n+1u);sink->length+=n;
    return true;
}

static unsigned lines(const char *text)
{
    unsigned result=0;
    for(;*text;++text)if(*text=='\n')++result;
    return result;
}

int main(void)
{
    _Static_assert(sizeof(comp_v11_diag_console_t)==20u,"Reconnect reuses existing console padding");
    comp_v11_diag_console_t console;
    comp_v11_diag_activity_t activity={0};
    comp_v11_diag_snapshot_t s={0};
    sink_t sink={0},failed={.fail_call=4u};
    comp_v11_diag_console_init(&console);
    CHECK(console.sequence==0u&&!console.query_pending);
    comp_v11_diag_console_accept(&console,(uint8_t)'s');
    CHECK(!console.query_pending);
    comp_v11_diag_console_accept(&console,(uint8_t)'\n');
    const char *battery="BATTERY\r\n";
    for(const char *p=battery;*p;++p)comp_v11_diag_console_accept(&console,(uint8_t)*p);
    CHECK(console.battery_pending && !comp_v11_diag_console_take_battery(&console,false));
    CHECK(comp_v11_diag_console_take_battery(&console,true));
    CHECK(!comp_v11_diag_console_take_battery(&console,true));
    CHECK(!comp_v11_diag_console_take_pair(&console));
    for(const char *p="BLE RECONNECT\r\n";*p;++p) {
        comp_v11_diag_console_accept(&console,(uint8_t)*p);
        if(*p!='\n')CHECK(!console.reconnect_pending);
    }
    CHECK(!comp_v11_diag_console_take_pair(&console));
    CHECK(comp_v11_diag_console_take_reconnect(&console));
    CHECK(!comp_v11_diag_console_take_reconnect(&console));
    CHECK(!comp_v11_diag_console_take_reconnect(NULL));
    CHECK(comp_v11_diag_console_take_record(&console)==COMP_V11_DIAG_RECORD_NONE);
    const char *invalid_reconnect[]={"BLE RECONNEC\n","BLE RECONNECTX\n","ble reconnect\n","BLE RECON\rNECT\n","BLE RECONNECT ?\n"};
    for(unsigned i=0;i<sizeof(invalid_reconnect)/sizeof(invalid_reconnect[0]);++i) {
        for(const char *p=invalid_reconnect[i];*p;++p)comp_v11_diag_console_accept(&console,(uint8_t)*p);
        CHECK(!comp_v11_diag_console_take_reconnect(&console));
        CHECK(!comp_v11_diag_console_take_pair(&console));
        CHECK(comp_v11_diag_console_take_record(&console)==COMP_V11_DIAG_RECORD_NONE);
    }
    CHECK(comp_v11_diag_console_take_panel(&console)==COMP_V11_DIAG_PANEL_NONE);
    const char *bad_battery[]={"battery\n","BATTERY X\n","XBATTERY\n","BATT\n","BAT\rTERY\n"};
    for(unsigned i=0;i<sizeof(bad_battery)/sizeof(bad_battery[0]);++i) {
        for(const char *p=bad_battery[i];*p;++p)comp_v11_diag_console_accept(&console,(uint8_t)*p);
        CHECK(!comp_v11_diag_console_take_battery(&console,true));
    }
    CHECK(!comp_v11_diag_console_take_pair(&console));
    comp_v11_diag_console_accept(&console,(uint8_t)'\n');
    const char *pair="PAIR\r\n";
    for(const char *p=pair;*p;++p) {
        comp_v11_diag_console_accept(&console,(uint8_t)*p);
        if(*p!='\n')CHECK(!console.pair_pending);
    }
    CHECK(comp_v11_diag_console_take_pair(&console));
    CHECK(!comp_v11_diag_console_take_pair(&console));
    const char *invalid[]={"XPAIR\n","PAI\n","PAIRX\n","pair\n","PA\rIR\n","PAIR ?\n"};
    for(unsigned i=0;i<sizeof(invalid)/sizeof(invalid[0]);++i) {
        for(const char *p=invalid[i];*p;++p)
            comp_v11_diag_console_accept(&console,(uint8_t)*p);
        CHECK(!comp_v11_diag_console_take_pair(&console));
    }
    const char *rec_commands[]={"REC START\r\n","REC STOP\n","REC PAUSE\n","REC RESUME\r\n","REC MARK\n","REC RECOVER\r\n","REC CACHE OFF ONCE\n"};
    for(unsigned i=0;i<sizeof(rec_commands)/sizeof(rec_commands[0]);++i) {
        for(const char *command_byte=rec_commands[i];*command_byte;++command_byte) {
            comp_v11_diag_console_accept(&console,(uint8_t)*command_byte);
            if(*command_byte!='\n')CHECK(comp_v11_diag_console_take_record(&console)==COMP_V11_DIAG_RECORD_NONE);
        }
        CHECK(comp_v11_diag_console_take_record(&console)==(comp_v11_diag_record_command_t)(i+1u));
        CHECK(comp_v11_diag_console_take_record(&console)==COMP_V11_DIAG_RECORD_NONE);
    }
    const char *bad_rec[]={"REC\n","REC START X\n","XREC STOP\n","REC STA\rRT\n","REC STOP?\n","REC START\rX\n","rec start\n","REC RECOVE\n","REC RECOVERX\n","REC RECO\rVER\n","REC RECOVER ?\n"};
    for(unsigned i=0;i<sizeof(bad_rec)/sizeof(bad_rec[0]);++i) {
        for(const char *command_byte=bad_rec[i];*command_byte;++command_byte)comp_v11_diag_console_accept(&console,(uint8_t)*command_byte);
        CHECK(comp_v11_diag_console_take_record(&console)==COMP_V11_DIAG_RECORD_NONE);
    }
    /* Noise invalidates the whole line; a busy consumer cannot leave a start
     * pending until a different product owner has finished. */
    for(const char *command_byte="REC ST";*command_byte;++command_byte)comp_v11_diag_console_accept(&console,(uint8_t)*command_byte);
    comp_v11_diag_console_accept(&console,0u);
    for(const char *command_byte="ART\n";*command_byte;++command_byte)comp_v11_diag_console_accept(&console,(uint8_t)*command_byte);
    CHECK(comp_v11_diag_console_take_record(&console)==COMP_V11_DIAG_RECORD_NONE);
    for(const char *command_byte="?REC START\n";*command_byte;++command_byte)comp_v11_diag_console_accept(&console,(uint8_t)*command_byte);
    CHECK(comp_v11_diag_console_take_record(&console)==COMP_V11_DIAG_RECORD_START);
    CHECK(comp_v11_diag_console_take_record(&console)==COMP_V11_DIAG_RECORD_NONE);
    CHECK(comp_v11_diag_console_take_record(NULL)==COMP_V11_DIAG_RECORD_NONE);
    CHECK(!comp_v11_diag_console_take_pair(NULL));
    /* A consumed busy request cannot silently reopen a window later. */
    for(const char *p="PAIR\nPAIR\n";*p;++p)
        comp_v11_diag_console_accept(&console,(uint8_t)*p);
    CHECK(comp_v11_diag_console_take_pair(&console));
    CHECK(!comp_v11_diag_console_take_pair(&console));
    console.query_pending=false;

    CHECK(comp_v11_diag_console_output_safe(&activity));
    activity.ui_pending=true;
    CHECK(comp_v11_diag_console_output_safe(&activity));
    activity.microphone_capture=true;
    CHECK(!comp_v11_diag_console_output_safe(&activity));
    activity.microphone_capture=false;activity.update=true;
    CHECK(!comp_v11_diag_console_output_safe(&activity));
    activity.update=false;activity.recording_transfer=true;
    CHECK(!comp_v11_diag_console_output_safe(&activity));
    activity.recording_transfer=false;activity.runtime_capture=true;
    CHECK(!comp_v11_diag_console_output_safe(&activity));
    CHECK(!comp_v11_diag_console_output_safe(NULL));
    activity=(comp_v11_diag_activity_t){.ui_pending=true,.screen_wait=true,.screen_maintenance=true};
    CHECK(!comp_v11_diag_console_output_safe(&activity));
    CHECK(comp_v11_diag_console_pairing_safe(&activity));
    CHECK(comp_v11_diag_console_pairing_blockers(&activity)==0u);
    CHECK(!comp_v11_diag_console_pairing_safe(NULL));
    CHECK(comp_v11_diag_console_pairing_blockers(NULL)==UINT32_C(0x80000000));
#define BLOCKS_PAIR(member,bit) do { activity.member=true; CHECK(!comp_v11_diag_console_pairing_safe(&activity)); CHECK(comp_v11_diag_console_pairing_blockers(&activity)==(1u<<(bit))); activity.member=false; } while(0)
    BLOCKS_PAIR(microphone_capture,0); BLOCKS_PAIR(playback,1); BLOCKS_PAIR(battery_sample,2);
    BLOCKS_PAIR(recording_transfer,3); BLOCKS_PAIR(storage,4); BLOCKS_PAIR(update,5); BLOCKS_PAIR(bond_nvm,6);
    BLOCKS_PAIR(playback_active,7); BLOCKS_PAIR(microphone_running,8); BLOCKS_PAIR(runtime_prepare,9);
    BLOCKS_PAIR(runtime_start,10); BLOCKS_PAIR(runtime_command,11); BLOCKS_PAIR(runtime_capture,12); BLOCKS_PAIR(runtime_stop,13);
#undef BLOCKS_PAIR
    activity.battery_sample=true;activity.update=true;
    const uint32_t rejected_guards=comp_v11_diag_console_pairing_blockers(&activity);
    activity.battery_sample=false;activity.update=false;
    CHECK(rejected_guards==0x24u && comp_v11_diag_console_pairing_safe(&activity));
    /* Actual445 refusal was battery-only. Finishing that bounded sample must
     * not lose PAIR, grant while ADC is active, or queue behind new capture. */
    uint32_t pair_deadline=0u;
    console.pair_pending=true;
    CHECK(!comp_v11_diag_console_take_pair_guarded(&console,100u,4u,&pair_deadline));
    CHECK(console.pair_pending && pair_deadline>=350u && pair_deadline<=351u);
    CHECK(comp_v11_diag_console_take_pair_guarded(&console,102u,0u,&pair_deadline));
    CHECK(!console.pair_pending && pair_deadline==0u);
    console.pair_pending=true;
    CHECK(!comp_v11_diag_console_take_pair_guarded(&console,200u,4u,&pair_deadline));
    CHECK(comp_v11_diag_console_take_pair_guarded(&console,201u,1u|4u,&pair_deadline));
    CHECK(!console.pair_pending && pair_deadline==0u); /* Caller rejects mic guard. */
    CHECK(!comp_v11_diag_console_take_pair_guarded(&console,202u,0u,&pair_deadline));
    console.pair_pending=true;
    CHECK(!comp_v11_diag_console_take_pair_guarded(&console,UINT32_MAX-100u,4u,&pair_deadline));
    CHECK(!comp_v11_diag_console_take_pair_guarded(&console,100u,4u,&pair_deadline));
    CHECK(comp_v11_diag_console_take_pair_guarded(&console,151u,4u,&pair_deadline));
    CHECK(!console.pair_pending && pair_deadline==0u); /* Caller rejects timeout, no late open. */
    activity=(comp_v11_diag_activity_t){0};
    comp_v11_diag_console_accept(&console,(uint8_t)'?');
    CHECK(console.query_pending&&!comp_v11_diag_console_take_query(&console,false));
    CHECK(console.query_pending&&comp_v11_diag_console_take_query(&console,true));
    CHECK(!console.query_pending);

    s.firmware_version=0x00010128u;s.build_id=0x20261004u;s.board_id=0x57424155u;
    { const uint8_t uid[12]={0x67,0x45,0x23,0x01,0xef,0xcd,0xab,0x89,0x40,0x30,0x20,0x10};
      memcpy(s.uid,uid,sizeof(uid)); }
    s.ui_generation=58u;s.uptime_ms=1234u;s.reset_flags=0x28000000u;s.iwdg_reset=true;
    s.faults=1u|8u|128u;s.ram_gap=1160u;s.stack_min_free=704u;s.stack_low=true;
    s.panel_status=4u;s.panel_error=3u;s.presenter_status=2u;s.assets_ready=true;
    s.panel_rendered=9u;s.panel_failed=2u;s.nor_jedec=0xef4018u;s.nor_size=16777216u;
    s.panel_stage=3u;s.panel_busy=true;s.panel_transfer_calls=19u;s.panel_busy_timeouts=2u;
    s.storage_layout_ready=true;s.recording_ready=true;s.recording_state=3u;
    s.recording_fault=4u;s.recording_committed=8192u;s.microphone_initialized=true;
    s.nor_suspend_qualified=true;s.nor_erase_active=true;s.nor_erase_suspended=true;
    s.nor_suspend_wait_ms=2u;s.nor_resume_guard_ms=2u;s.nor_sfdp_bfp_dwords=16u;
    s.nor_sfdp_dw12=0x330001ecu;s.nor_sfdp_dw13=0x757a757au;
    s.microphone_hal_error=7u;s.microphone_error_irqs=2u;s.microphone_stale=3u;
    s.microphone_overflows=4u;s.microphone_rejections=5u;s.microphone_frames=600u;
    s.capture_deadline_faults=1u;s.speaker_ready=true;s.ble_compiled=true;
    s.capture_foreground_ms=UINT32_MAX;s.capture_hal_ms=UINT32_MAX;s.capture_recorder_ms=UINT32_MAX;
    s.capture_ble_ms=UINT32_MAX;s.capture_runtime_ms=UINT32_MAX;s.capture_presenter_ms=UINT32_MAX;
    s.capture_render_ms=UINT32_MAX;s.microphone_poll_ms=UINT32_MAX;
    s.timing_recording_id=UINT32_MAX;s.timing_microphone_starts=UINT32_MAX;
    s.encode_timing_samples=UINT32_MAX;s.encode_p95_upper_ms=UINT32_MAX;s.encode_peak_upper_ms=UINT32_MAX;
    s.pdm_timing_samples=UINT32_MAX;s.pdm_p95_upper_ms=UINT32_MAX;s.pdm_peak_upper_ms=UINT32_MAX;
    s.encode_timing_valid=true;s.pdm_timing_valid=true;
    s.ble_initialized=true;s.ble_host_ready=true;s.ble_host_error=9u;
    s.ble_connection=0x0042u;s.ble_linked=true;s.ble_secured=true;
    s.battery_adc_enabled=true;s.voltage_valid=true;s.percent_valid=true;
    s.charger_valid=true;s.charger_present=true;s.battery_mv=3890u;
    s.battery_percent=76u;s.charge_state=1u;s.ota_power_blockers=0x12u;
    s.sleep_blockers=0xa5u;
    s.battery_reference_raw=2730u;s.battery_factory_raw=1638u;s.battery_reference_mv=1800u;
    s.battery_reference_valid=true;s.battery_reference_age_ms=UINT32_MAX;
    s.battery_reference_samples=UINT32_MAX;s.battery_adc_samples=UINT32_MAX;
    s.battery_adc_failures=UINT32_MAX;s.battery_sample_errors=UINT32_MAX;s.battery_gate_errors=UINT32_MAX;
    s.battery_raw_mode=true;s.battery_input_mv=1793u;s.battery_input_valid=true;
    s.battery_sample_age_ms=UINT32_MAX;
    s.battery_reference_min_mv=1750u;s.battery_reference_max_mv=1810u;
    comp_v11_diag_console_emit(&console,&s,COMP_V11_DIAG_QUERY,capture,&sink);
    CHECK(lines(sink.text)==12u);
    CHECK(strstr(sink.text,"DIAG1 BEGIN seq=1 reason=query\r\n")!=NULL);
    CHECK(strstr(sink.text,"fw=00010128 build=20261004 board=57424155 uid=67452301efcdab8940302010 ui=58")!=NULL);
    CHECK(strstr(sink.text,"reset=28000000 iwdg_reset=1 faults=00000089 clock=1 lse=0 io=0 imu=0 touch=0 audio=0 mic=1 nor=1 panel=0 battery=0")!=NULL);
    CHECK(strstr(sink.text,"jedec=ef4018 size=16777216")!=NULL);
    CHECK(strstr(sink.text,"suspend_ok=1 erase_active=1 erase_sus=1 sus_ms=2 resume_ms=2 bfp_dw=16 dw12=330001ec dw13=757a757a")!=NULL);
    CHECK(strstr(sink.text,"stage=3 busy=1 transfer_calls=19 busy_timeouts=2")!=NULL);
    CHECK(strstr(sink.text,"mic_reject=5 frames=600 deadline=1 speaker_ready=1")!=NULL);
    CHECK(strstr(sink.text,"fg_ms=4294967295 hal_ms=4294967295 rec_ms=4294967295")!=NULL);
    CHECK(strstr(sink.text,"render_ms=4294967295 pdm_ms=4294967295")!=NULL);
    CHECK(strstr(sink.text,"DIAG1 TIMING seq=1 rec_id=4294967295 mic_starts=4294967295 tick_us=1000 min_samples=20")!=NULL);
    CHECK(strstr(sink.text,"enc_n=4294967295 enc_valid=1 enc_p95_upper_ms=4294967295 enc_peak_upper_ms=4294967295")!=NULL);
    CHECK(strstr(sink.text,"pdm_n=4294967295 pdm_valid=1 pdm_p95_upper_ms=4294967295 pdm_peak_upper_ms=4294967295")!=NULL);
    CHECK(strstr(sink.text,"connection=0042 linked=1 secured=1")!=NULL);
    CHECK(strstr(sink.text,"ota_block=0012 sleep_block=000000a5")!=NULL);
    CHECK(strstr(sink.text,"DIAG1 BATTERY seq=1 vref_raw=2730 vref_cal=1638 vdda_mv=1800 vref_valid=1")!=NULL);
    CHECK(strstr(sink.text,"divider_safe=0 divider_verified=0 reference_verified=0 sample_errors=4294967295 gate_errors=4294967295 raw_mode=1 input_mv=1793 input_valid=1 saturated=0 sample_age_ms=4294967295 vdda_min_mv=1750 vdda_max_mv=1810\r\n")!=NULL);
    CHECK(strstr(sink.text,"DIAG1 END seq=1\r\n")!=NULL);

    comp_v11_diag_console_emit(&console,&s,COMP_V11_DIAG_PERIODIC,capture,&failed);
    CHECK(failed.calls==4u);
    CHECK(strstr(failed.text,"DIAG1 END")==NULL);
    CHECK(console.sequence==2u);
    {
        sink_t power={0};
        comp_v11_diag_console_emit_battery(&s,capture,&power);
        CHECK(lines(power.text)==1u && power.length<256u);
        CHECK(strstr(power.text,"cell=VALID cell_mv=3890 pct_valid=1 pct=76")!=NULL);
        CHECK(strstr(power.text,"supply_valid=0 supply_mv=0")!=NULL); /* Old VREF is not current supply. */
        s.voltage_valid=false;s.percent_valid=false;s.battery_reference_age_ms=12u;
        power=(sink_t){0};comp_v11_diag_console_emit_battery(&s,capture,&power);
        CHECK(strstr(power.text,"cell=DIVIDER_UNVERIFIED cell_mv=0 pct_valid=0 pct=255")!=NULL);
        CHECK(strstr(power.text,"supply_valid=1 supply_mv=1800")!=NULL);
        s.battery_divider_verified=true;
        power=(sink_t){0};comp_v11_diag_console_emit_battery(&s,capture,&power);
        CHECK(strstr(power.text,"cell=DIVIDER_RANGE")!=NULL);
        s.battery_divider_safe=true;s.battery_saturated=true;
        power=(sink_t){0};comp_v11_diag_console_emit_battery(&s,capture,&power);
        CHECK(strstr(power.text,"cell=SATURATED")!=NULL);
        s.battery_saturated=false;s.battery_adc_error=5u;
        power=(sink_t){0};comp_v11_diag_console_emit_battery(&s,capture,&power);
        CHECK(strstr(power.text,"cell=ADC_ERROR")!=NULL);
        s.battery_adc_error=0u;s.charger_valid=false;
        power=(sink_t){0};comp_v11_diag_console_emit_battery(&s,capture,&power);
        CHECK(strstr(power.text,"cell=STALE")!=NULL && strstr(power.text,"charge=UNKNOWN")!=NULL);
        s.battery_sample_age_ms=10u;
        power=(sink_t){0};comp_v11_diag_console_emit_battery(&s,capture,&power);
        CHECK(strstr(power.text,"cell=RAW_ONLY")!=NULL);
    }
    {
        comp_v11_diag_activity_t fault={.screen_wait=true,.screen_maintenance=true,
            .runtime_prepare=true,.runtime_start=true,.runtime_command=true,.runtime_capture=true,.runtime_stop=true};
        CHECK(!comp_v11_diag_console_output_safe(&fault));
        CHECK(!comp_v11_diag_console_pairing_safe(&fault));
        CHECK(!comp_v11_diag_console_fault_output_safe(&fault,false));
        CHECK(comp_v11_diag_console_fault_output_safe(&fault,true));
        CHECK(!comp_v11_diag_console_fault_output_safe(NULL,true));
        bool *physical[]={&fault.microphone_capture,&fault.microphone_running,&fault.playback,
            &fault.playback_active,&fault.battery_sample,&fault.recording_transfer,&fault.storage,&fault.update,&fault.bond_nvm};
        for(unsigned i=0u;i<sizeof(physical)/sizeof(physical[0]);++i) {
            *physical[i]=true;CHECK(!comp_v11_diag_console_fault_output_safe(&fault,true));*physical[i]=false;
        }
        comp_v11_diag_record_fault_t evidence={.token=3139075243u,.core_hz=65535808u,.pipeline=8u,
            .failure=3u,.record_fault=3u,.engine=9u,.engine_failure=3u,.budget_failures=1u,
            .max_poll_ms=11u,.pcm_blocks=24u,.encoded_packets=12u,.runtime_flags=31u};
        sink_t compact={0};
        CHECK(comp_v11_diag_console_emit_record_fault(&evidence,capture,&compact));
        CHECK(lines(compact.text)==3u && compact.length<768u);
        CHECK(strstr(compact.text,"RFAIL1 CAUSE token=3139075243 core_hz=65535808")!=NULL);
        CHECK(strstr(compact.text,"pipeline=8 failure=3 record_fault=3")!=NULL);
        CHECK(strstr(compact.text,"poll_ms=11 budget=1 queue=0 pcm=24 enc=12")!=NULL);
        CHECK(strstr(compact.text,"runtime=001f")!=NULL);
        CHECK(strstr(compact.text,"DIAG1 END")==NULL); /* Never a healthy/full snapshot. */
        compact=(sink_t){.fail_call=2u};
        CHECK(!comp_v11_diag_console_emit_record_fault(&evidence,capture,&compact));
        CHECK(compact.calls==2u && lines(compact.text)==1u);
        CHECK(!comp_v11_diag_console_emit_record_fault(NULL,capture,&compact));
        CHECK(!comp_v11_diag_console_emit_record_fault(&evidence,NULL,&compact));
        puts("PASS_WBA_STOPPED_FAULT_QUERY exact_failure_and_budget=1 active_io_rejected=1 no_controls_or_normal_pass=1");
    }
    {
        comp_v11_diag_record_queue_t q={.token=UINT32_MAX,.pcm_blocks=UINT32_MAX,
            .encoded_packets=UINT32_MAX,.durable_bytes=UINT32_MAX,.queue_peak=8u,
            .queue_depth=8u,.queue_slots=8u,.pcm_fill=160u,.stage_bytes=320u,
            .writer_phase=1u,.state=5u,.engine_bound=true,.microphone_active=false,
            .overflows=UINT32_MAX,.budget_failures=UINT32_MAX};
        sink_t queue={0};
        CHECK(comp_v11_diag_console_emit_record_queue(&q,capture,&queue));
        CHECK(lines(queue.text)==3u);
        CHECK(strstr(queue.text,"pcm_blocks=4294967295 encoded_packets=4294967295")!=NULL);
        CHECK(strstr(queue.text,"depth=8 peak=8 slots=8 codec_pcm=160 stage_bytes=320 writer_phase=1")!=NULL);
        CHECK(strstr(queue.text,"queue_age_measured=0")!=NULL);
        for(unsigned fail=1u;fail<=3u;++fail){
            queue=(sink_t){.fail_call=fail};
            CHECK(!comp_v11_diag_console_emit_record_queue(&q,capture,&queue));
            CHECK(queue.calls==fail && strstr(queue.text,"RECQ1 END")==NULL);
        }
        q=(comp_v11_diag_record_queue_t){.queue_slots=8u};queue=(sink_t){0};
        CHECK(comp_v11_diag_console_emit_record_queue(&q,capture,&queue));
        CHECK(strstr(queue.text,"bound=0")!=NULL); /* not silently a valid empty recording */
        CHECK(!comp_v11_diag_console_emit_record_queue(NULL,capture,&queue));
        CHECK(!comp_v11_diag_console_emit_record_queue(&q,NULL,&queue));
        puts("PASS_RECORD_QUEUE_SUMMARY bounded_records=1 partial_no_end=1 unavailable_explicit=1 queue_age_not_invented=1");
    }
    fputs(sink.text,stdout);
    puts("PASS_WBA_DIAG_CONSOLE sections=10 framed_lines=12 query_deferred=1 exact_wired_pair_command=1 partial_has_no_end=1");
    puts("PASS_WBA_DIAG_BUSY_POLICY ordinary_visible_ui_allowed=1 active_io_and_update_deferred=1");
    puts("PASS_WBA_BATTERY_QUERY exact_read_only_command=1 deferred_for_audio=1 one_bounded_line=1 cell_supply_separate=1 stale_and_unqualified_unknown=1");
    return 0;
}
