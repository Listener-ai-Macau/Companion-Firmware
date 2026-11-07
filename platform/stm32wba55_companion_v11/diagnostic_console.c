#include "diagnostic_console.h"

#include <stdio.h>
#include <stddef.h>
#include <string.h>

/* Cold guarded UART formatting; never runs in capture/playback deadlines. */
#if defined(__GNUC__)
#pragma GCC optimize ("Oz")
#endif

#if defined(COMPANION_WBA_BLE_LINKED) && COMPANION_WBA_EXPERIMENTAL_STOP1
enum { COMP_V11_DIAG_COMMAND_COUNT = 32u };
#else
enum { COMP_V11_DIAG_COMMAND_COUNT = 30u };
#endif
_Static_assert(COMP_V11_DIAG_COMMAND_COUNT<=32u,"diagnostic command mask overflow");
#define COMP_V11_DIAG_ALL_COMMANDS (UINT32_MAX >> (32u-COMP_V11_DIAG_COMMAND_COUNT))

static const char *reason_name(comp_v11_diag_reason_t reason)
{
    switch (reason) {
    case COMP_V11_DIAG_BOOT: return "boot";
    case COMP_V11_DIAG_QUERY: return "query";
    default: return "periodic";
    }
}

void comp_v11_diag_console_init(comp_v11_diag_console_t *console)
{
    if (console != NULL) {
        memset(console, 0, sizeof(*console));
        console->command_candidates = COMP_V11_DIAG_ALL_COMMANDS;
    }
}

static bool command_complete(uint8_t index,const char *text,uint8_t matched)
{ return index==12u ? matched==10u : text[matched]=='\0'; }
static int hex_digit(uint8_t byte)
{
    if(byte>='0' && byte<='9')return byte-'0';
    if(byte>='a' && byte<='f')return byte-'a'+10;
    if(byte>='A' && byte<='F')return byte-'A'+10;
    return -1;
}

void comp_v11_diag_console_accept(comp_v11_diag_console_t *console, uint8_t byte)
{
    static const char *const commands[] = {
        "PAIR", "EPD HOLD", "EPD RUN", "EPD SNAP", "EPD TRACE", "EPD STATUS", "BATTERY", "EPD KEY", "EPD SAME", "EPD BASE", "EPD CATCH", "EPD PINS", "IMU MAP ", "IMU CLEAR", "SOUND", "REC START", "REC STOP", "BLE RECONNECT", "REC PAUSE", "REC RESUME", "REC MARK", "SOUND 4", "SOUND 5", "SOUND 6", "SOUND 7", "SOUND REF 1", "SOUND REF 2", "SOUND REF 3", "REC RECOVER", "REC CACHE OFF ONCE"
#if defined(COMPANION_WBA_BLE_LINKED) && COMPANION_WBA_EXPERIMENTAL_STOP1
        , "POWER STOP1 ONCE", "POWER STOP1 WINDOW"
#endif
    };
    _Static_assert(sizeof(commands)/sizeof(commands[0])==COMP_V11_DIAG_COMMAND_COUNT,"diagnostic command mask/table mismatch");
    if (console == NULL) return;
    if (byte == (uint8_t)'?') {
        console->query_pending = true;
        /* The one-byte query is a complete service command at a line
         * boundary. Do not poison the next EPD/PAIR/BATTERY line when the
         * host sends it without a newline. A '?' inside an unfinished or
         * malformed line still invalidates that line as before. */
        if (console->command_match == 0u && !console->command_invalid) return;
    }
    if (byte == (uint8_t)'\n') {
        for (uint8_t i=0u; i<sizeof(commands)/sizeof(commands[0]); ++i) {
            if (!console->command_invalid &&
                (console->command_candidates & (1u<<i)) != 0u &&
                command_complete(i,commands[i],console->command_match)) {
                if (i==0u) console->pair_pending=true;
                else if(i==17u) console->reconnect_pending=true;
#if defined(COMPANION_WBA_BLE_LINKED) && COMPANION_WBA_EXPERIMENTAL_STOP1
                else if(i==30u) console->record_command=COMP_V11_DIAG_RECORD_STOP1_ONCE;
                else if(i==31u) console->record_command=COMP_V11_DIAG_RECORD_STOP1_WINDOW;
#endif
                else if(i==29u) console->record_command=COMP_V11_DIAG_RECORD_CACHE_OFF_NEXT;
                else if(i==28u) console->record_command=COMP_V11_DIAG_RECORD_RECOVER;
                else if(i>=25u) console->panel_command=(uint8_t)(COMP_V11_DIAG_PANEL_SOUND_REFERENCE_1K+i-25u);
                else if(i>=21u) console->panel_command=(uint8_t)(COMP_V11_DIAG_PANEL_SOUND_GREETING+i-21u);
                else if(i>=18u) console->record_command=(uint8_t)(i-15u);
                else if(i==6u) console->battery_pending=true;
                else if(i>=15u) console->record_command=(uint8_t)(i-14u);
                else if(i==14u) console->panel_command=COMP_V11_DIAG_PANEL_SOUND;
                else if(i>=12u) {
                    console->imu_command=i==12u?1u:2u;
                    console->imu_axes=i==12u?console->imu_candidate_axes:0u;
                }
                else console->panel_command=i==11u?COMP_V11_DIAG_PANEL_PINS:i==10u?COMP_V11_DIAG_PANEL_CATCH:
                    i==9u?COMP_V11_DIAG_PANEL_BASE:
                    i==8u?COMP_V11_DIAG_PANEL_SAME:
                    i==7u?COMP_V11_DIAG_PANEL_KEY:i;
            }
        }
        console->command_invalid=false;
        console->command_match=0u;
        console->command_candidates=COMP_V11_DIAG_ALL_COMMANDS;
        console->imu_candidate_axes=0u;
    } else if (byte == (uint8_t)'\r') {
        /* CR is accepted only after an exact complete command. */
        uint32_t candidates=0u;
        for (uint8_t i=0u; i<sizeof(commands)/sizeof(commands[0]); ++i)
            if ((console->command_candidates & (1u<<i)) != 0u &&
                command_complete(i,commands[i],console->command_match)) candidates|=(uint32_t)(1u<<i);
        if (candidates==0u) console->command_invalid=true;
        console->command_candidates=candidates;
    } else if (!console->command_invalid) {
        uint32_t candidates=0u;
        for (uint8_t i=0u; i<sizeof(commands)/sizeof(commands[0]); ++i) {
            if ((console->command_candidates & (1u<<i)) == 0u)continue;
            if(i==12u && console->command_match>=8u) {
                const int digit=hex_digit(byte);
                if(console->command_match<10u && digit>=0) {
                    console->imu_candidate_axes=(uint8_t)((console->imu_candidate_axes<<4u)|(uint8_t)digit);
                    candidates|=(uint32_t)(1u<<i);
                }
            } else if(commands[i][console->command_match]!='\0' &&
                byte==(uint8_t)commands[i][console->command_match])candidates|=(uint32_t)(1u<<i);
        }
        console->command_candidates=candidates;
        if (candidates==0u) console->command_invalid=true;
        else console->command_match++;
    }
}

bool comp_v11_diag_console_take_imu(comp_v11_diag_console_t *c,uint8_t *command,uint8_t *axes)
{
    if(!c || !command || !axes || c->imu_command==0u)return false;
    *command=c->imu_command;*axes=c->imu_axes;c->imu_command=0u;return true;
}

comp_v11_diag_panel_command_t comp_v11_diag_console_take_panel(comp_v11_diag_console_t *console)
{
    if (console==NULL) return COMP_V11_DIAG_PANEL_NONE;
    comp_v11_diag_panel_command_t command=(comp_v11_diag_panel_command_t)console->panel_command;
    console->panel_command=COMP_V11_DIAG_PANEL_NONE;
    return command;
}

comp_v11_diag_record_command_t comp_v11_diag_console_take_record(comp_v11_diag_console_t *c)
{
    if(!c)return COMP_V11_DIAG_RECORD_NONE;
    comp_v11_diag_record_command_t command=(comp_v11_diag_record_command_t)c->record_command;
    c->record_command=COMP_V11_DIAG_RECORD_NONE;return command;
}

bool comp_v11_diag_console_take_pair(comp_v11_diag_console_t *console)
{
    if (console == NULL || !console->pair_pending) return false;
    console->pair_pending = false;
    return true;
}

bool comp_v11_diag_console_take_pair_guarded(comp_v11_diag_console_t *console,uint32_t now,
                                             uint32_t blockers,uint32_t *battery_deadline)
{
    if(!battery_deadline)return false;
    if(!console || !console->pair_pending){*battery_deadline=0u;return false;}
    /* Query output needs ADC idle too. A PAIR arriving just after that output
     * can meet the next short sample. Finish that one sample without dropping
     * the explicit request; any other protected operation rejects it now. */
    if(blockers==4u) {
        if(!*battery_deadline)*battery_deadline=(now+250u)|1u;
        if((int32_t)(now-*battery_deadline)<0)return false;
    }
    *battery_deadline=0u;
    return comp_v11_diag_console_take_pair(console);
}

bool comp_v11_diag_console_take_reconnect(comp_v11_diag_console_t *console)
{
    if(console==NULL || !console->reconnect_pending)return false;
    console->reconnect_pending=false;return true;
}

bool comp_v11_diag_console_take_query(comp_v11_diag_console_t *console, bool output_safe)
{
    if (console == NULL || !console->query_pending || !output_safe) return false;
    console->query_pending = false;
    return true;
}
bool comp_v11_diag_console_take_battery(comp_v11_diag_console_t *console,bool output_safe)
{
    if(!console || !console->battery_pending || !output_safe)return false;
    console->battery_pending=false;
    return true;
}

bool comp_v11_diag_console_output_safe(const comp_v11_diag_activity_t *a)
{
    if (a == NULL) return false;
    return !a->microphone_capture && !a->screen_maintenance && !a->screen_wait &&
        !a->playback && !a->battery_sample && !a->recording_transfer && !a->storage &&
        !a->update && !a->bond_nvm && !a->playback_active && !a->microphone_running &&
        !a->runtime_prepare && !a->runtime_start && !a->runtime_command &&
        !a->runtime_capture && !a->runtime_stop;
}

bool comp_v11_diag_console_fault_output_safe(const comp_v11_diag_activity_t *a,bool stopped_fault)
{
    return a && stopped_fault && !a->microphone_capture && !a->microphone_running &&
        !a->playback && !a->playback_active && !a->battery_sample &&
        !a->recording_transfer && !a->storage && !a->update && !a->bond_nvm;
}

bool comp_v11_diag_console_pairing_safe(const comp_v11_diag_activity_t *a)
{
    return comp_v11_diag_console_pairing_blockers(a)==0u;
}

uint32_t comp_v11_diag_console_pairing_blockers(const comp_v11_diag_activity_t *a)
{
    if (a == NULL) return UINT32_C(0x80000000);
    /* The foreground has already submitted any bounded display SPI chunk.
     * The display's long BUSY interval does not consume the BLE/UART buses.
     * Keep all real product-operation guards and the normal encrypted window. */
    return (uint32_t)a->microphone_capture | (uint32_t)a->playback<<1u |
        (uint32_t)a->battery_sample<<2u | (uint32_t)a->recording_transfer<<3u |
        (uint32_t)a->storage<<4u | (uint32_t)a->update<<5u |
        (uint32_t)a->bond_nvm<<6u | (uint32_t)a->playback_active<<7u |
        (uint32_t)a->microphone_running<<8u | (uint32_t)a->runtime_prepare<<9u |
        (uint32_t)a->runtime_start<<10u | (uint32_t)a->runtime_command<<11u |
        (uint32_t)a->runtime_capture<<12u | (uint32_t)a->runtime_stop<<13u;
}

static bool send(comp_v11_diag_write_fn_t write, void *context, char *line, int length, size_t capacity)
{
    return write != NULL && length > 0 && (size_t)length < capacity && write(context, line);
}
bool comp_v11_diag_console_emit_record_fault(const comp_v11_diag_record_fault_t *s,
                                            comp_v11_diag_write_fn_t write,void *context)
{
    if(!s || !write)return false;
    char line[256];
    int n=snprintf(line,sizeof(line),
        "RFAIL1 CAUSE token=%lu core_hz=%lu pipeline=%u failure=%u record_fault=%u engine=%u engine_failure=%u\r\n",
        (unsigned long)s->token,(unsigned long)s->core_hz,(unsigned)s->pipeline,
        (unsigned)s->failure,(unsigned)s->record_fault,(unsigned)s->engine,(unsigned)s->engine_failure);
    if(!send(write,context,line,n,sizeof(line)))return false;
    n=snprintf(line,sizeof(line),
        "RFAIL1 BUDGET token=%lu deadline=%lu fg_ms=%lu poll_ms=%lu budget=%lu queue=%u pcm=%lu enc=%lu\r\n",
        (unsigned long)s->token,(unsigned long)s->deadline,(unsigned long)s->foreground_ms,
        (unsigned long)s->max_poll_ms,(unsigned long)s->budget_failures,(unsigned)s->queue_depth,
        (unsigned long)s->pcm_blocks,(unsigned long)s->encoded_packets);
    if(!send(write,context,line,n,sizeof(line)))return false;
    n=snprintf(line,sizeof(line),
        "RFAIL1 STATE token=%lu stale=%lu overflow=%lu reject=%lu irq=%lu runtime=%04x blocks=%08lx catalog=%u future=%u consume=%u\r\n",
        (unsigned long)s->token,(unsigned long)s->stale,(unsigned long)s->overflows,
        (unsigned long)s->rejections,(unsigned long)s->irq_errors,(unsigned)s->runtime_flags,
        (unsigned long)s->blockers,(unsigned)s->catalog_phase,(unsigned)s->future_phase,(unsigned)s->consume_phase);
    return send(write,context,line,n,sizeof(line));
}

bool comp_v11_diag_console_emit_record_queue(const comp_v11_diag_record_queue_t *s,
                                            comp_v11_diag_write_fn_t write,void *context)
{
    if(!s || !write)return false;
    char line[256];
    int n=snprintf(line,sizeof(line),
        "RECQ1 INPUT token=%lu bound=%u state=%u mic=%u block_samples=160 pcm_blocks=%lu encoded_packets=%lu\r\n",
        (unsigned long)s->token,(unsigned)s->engine_bound,(unsigned)s->state,
        (unsigned)s->microphone_active,(unsigned long)s->pcm_blocks,(unsigned long)s->encoded_packets);
    if(!send(write,context,line,n,sizeof(line)))return false;
    n=snprintf(line,sizeof(line),
        "RECQ1 PENDING token=%lu depth=%u peak=%lu slots=%u codec_pcm=%u stage_bytes=%u writer_phase=%u\r\n",
        (unsigned long)s->token,(unsigned)s->queue_depth,(unsigned long)s->queue_peak,
        (unsigned)s->queue_slots,(unsigned)s->pcm_fill,(unsigned)s->stage_bytes,(unsigned)s->writer_phase);
    if(!send(write,context,line,n,sizeof(line)))return false;
    n=snprintf(line,sizeof(line),
        "RECQ1 END token=%lu durable_bytes=%lu pcm_overflows=%lu budget_failures=%lu queue_age_measured=0\r\n",
        (unsigned long)s->token,(unsigned long)s->durable_bytes,
        (unsigned long)s->overflows,(unsigned long)s->budget_failures);
    return send(write,context,line,n,sizeof(line));
}

void comp_v11_diag_console_emit_battery(const comp_v11_diag_snapshot_t *s,
                                       comp_v11_diag_write_fn_t write,void *context)
{
    char line[256];
    if(!s || !write)return;
    const char *cell=s->voltage_valid?"VALID":
        !s->battery_divider_verified?"DIVIDER_UNVERIFIED":
        !s->battery_divider_safe?"DIVIDER_RANGE":
        !s->battery_reference_verified && !s->battery_raw_mode?"REFERENCE_UNVERIFIED":
        !s->battery_adc_enabled?"SAMPLING_DISABLED":
        s->battery_saturated?"SATURATED":
        s->battery_adc_error?"ADC_ERROR":
        !s->battery_adc_samples?"NOT_SAMPLED":
        s->battery_sample_age_ms>=15000u?"STALE":
        s->battery_raw_mode?"RAW_ONLY":"INVALID";
    static const char *const charge[]={"UNKNOWN","CHARGING","POWERED_IDLE","DISCHARGING","FAULT"};
    bool supply=s->battery_reference_valid && s->battery_reference_age_ms<15000u;
    int length=snprintf(line,sizeof(line),
        "BATTERY1 cell=%s cell_mv=%u pct_valid=%u pct=%u supply_valid=%u supply_mv=%u supply_age_ms=%lu supply_min_mv=%u supply_max_mv=%u charge=%s adc_error=%u\r\n",
        cell,(unsigned)(s->voltage_valid?s->battery_mv:0u),
        (unsigned)(s->voltage_valid && s->percent_valid),
        (unsigned)(s->voltage_valid && s->percent_valid?s->battery_percent:255u),
        (unsigned)supply,(unsigned)(supply?s->battery_reference_mv:0u),
        (unsigned long)s->battery_reference_age_ms,
        (unsigned)s->battery_reference_min_mv,(unsigned)s->battery_reference_max_mv,
        s->charger_valid && s->charge_state<5u?charge[s->charge_state]:charge[0],
        (unsigned)s->battery_adc_error);
    (void)send(write,context,line,length,sizeof(line));
}


/* UART status is cold and excluded while capture/transfer owns the board.
 * Compact readonly field offsets replace repeated variadic argument setup.
 * Format tokens1=decimal,2/3/4=zero-padded hex4/8/6 and5=hex2 replace repeated printf
 * specifiers in readonly storage. Packed tokens also carry the adjacent
 * equals/space (bits4/5); no information is removed from the emitted line; they are expanded before any UART write.
 * Preserve every existing DIAG1 byte and one write per complete line. No
 * static RAM, audio/profile change, allocation or new UART command here. */
_Static_assert(sizeof(comp_v11_diag_snapshot_t)<=512u,"diagnostic offset width");
#define D_FIELD(member) ((uint16_t)(offsetof(comp_v11_diag_snapshot_t,member) | \
    ((sizeof(((comp_v11_diag_snapshot_t *)0)->member)==4u?2u: \
      sizeof(((comp_v11_diag_snapshot_t *)0)->member)==2u?1u:0u)<<9u)))
#define D_BYTE_ARRAY(member,index) ((uint16_t)(offsetof(comp_v11_diag_snapshot_t,member)+(index)))
#define D_MASK24(member) ((uint16_t)(offsetof(comp_v11_diag_snapshot_t,member)|(3u<<9u)))
#define D_FAULT(bit) ((uint16_t)(D_FIELD(faults)|0x8000u|((bit)<<11u)))
/* Group formats omit the common DIAG1 prefix and first seq label. */
typedef struct {const char *format;const uint16_t *fields;uint16_t count;} diag_fields_t;
static const uint16_t diag_id[]={
    D_FIELD(firmware_version),D_FIELD(build_id),D_FIELD(board_id),
    D_BYTE_ARRAY(uid,0u),D_BYTE_ARRAY(uid,1u),D_BYTE_ARRAY(uid,2u),D_BYTE_ARRAY(uid,3u),
    D_BYTE_ARRAY(uid,4u),D_BYTE_ARRAY(uid,5u),D_BYTE_ARRAY(uid,6u),D_BYTE_ARRAY(uid,7u),
    D_BYTE_ARRAY(uid,8u),D_BYTE_ARRAY(uid,9u),D_BYTE_ARRAY(uid,10u),D_BYTE_ARRAY(uid,11u),
    D_FIELD(ui_generation),D_FIELD(uptime_ms),
};
static const uint16_t diag_core[]={
    D_FIELD(reset_flags),D_FIELD(iwdg_reset),D_FIELD(faults),D_FAULT(0u),
    D_FAULT(6u),D_FAULT(1u),D_FAULT(2u),D_FAULT(5u),
    D_FAULT(4u),D_FAULT(7u),D_FAULT(3u),D_FAULT(8u),
    D_FAULT(9u),D_FIELD(ram_gap),D_FIELD(stack_min_free),D_FIELD(stack_low),
    D_FIELD(stack_guard),
};
#if !defined(COMPANION_WBA_SCREEN_ENABLED) || COMPANION_WBA_SCREEN_ENABLED
static const uint16_t diag_display[]={
    D_FIELD(panel_bound),D_FIELD(panel_status),D_FIELD(panel_error),D_FIELD(presenter_status),
    D_FIELD(assets_ready),D_FIELD(panel_rendered),D_FIELD(panel_failed),D_FIELD(panel_stage),
    D_FIELD(panel_busy),D_FIELD(panel_transfer_calls),D_FIELD(panel_busy_timeouts),
};
#endif
static const uint16_t diag_storage[]={
    D_MASK24(nor_jedec),D_FIELD(nor_size),D_FIELD(storage_layout_ready),D_FIELD(recording_ready),
    D_FIELD(recording_state),D_FIELD(recording_fault),D_FIELD(recording_committed),D_FIELD(nor_suspend_qualified),
    D_FIELD(nor_erase_active),D_FIELD(nor_erase_suspended),D_FIELD(nor_suspend_wait_ms),D_FIELD(nor_resume_guard_ms),
    D_FIELD(nor_sfdp_bfp_dwords),D_FIELD(nor_sfdp_dw12),D_FIELD(nor_sfdp_dw13),
};
static const uint16_t diag_audio[]={
    D_FIELD(microphone_initialized),D_FIELD(microphone_running),D_FIELD(microphone_hal_error),D_FIELD(microphone_error_irqs),
    D_FIELD(microphone_stale),D_FIELD(microphone_overflows),D_FIELD(microphone_rejections),D_FIELD(microphone_frames),
    D_FIELD(capture_deadline_faults),D_FIELD(speaker_ready),D_FIELD(capture_foreground_ms),D_FIELD(capture_hal_ms),
    D_FIELD(capture_recorder_ms),D_FIELD(capture_ble_ms),D_FIELD(capture_runtime_ms),D_FIELD(capture_presenter_ms),
    D_FIELD(capture_render_ms),D_FIELD(microphone_poll_ms),
};
static const uint16_t diag_timing[]={
    D_FIELD(timing_recording_id),D_FIELD(timing_microphone_starts),D_FIELD(encode_timing_samples),D_FIELD(encode_timing_valid),
    D_FIELD(encode_p95_upper_ms),D_FIELD(encode_peak_upper_ms),D_FIELD(pdm_timing_samples),D_FIELD(pdm_timing_valid),
    D_FIELD(pdm_p95_upper_ms),D_FIELD(pdm_peak_upper_ms),
};
static const uint16_t diag_ble[]={
    D_FIELD(ble_compiled),D_FIELD(ble_initialized),D_FIELD(ble_host_ready),D_FIELD(ble_host_error),
    D_FIELD(ble_connection),D_FIELD(ble_linked),D_FIELD(ble_secured),D_FIELD(ble_fatal),
    D_FIELD(ble_bond_lost),D_FIELD(ble_rebond_attempts),D_FIELD(ble_pairing_status),D_FIELD(ble_pairing_reason),
};
static const uint16_t diag_power[]={
    D_FIELD(battery_adc_enabled),D_FIELD(voltage_valid),D_FIELD(percent_valid),D_FIELD(charger_valid),
    D_FIELD(charger_present),D_FIELD(battery_mv),D_FIELD(battery_percent),D_FIELD(charge_state),
    D_FIELD(ota_power_blockers),D_FIELD(sleep_blockers),
};
static const uint16_t diag_battery[]={
    D_FIELD(battery_reference_raw),D_FIELD(battery_factory_raw),D_FIELD(battery_reference_mv),D_FIELD(battery_reference_valid),
    D_FIELD(battery_reference_age_ms),D_FIELD(battery_reference_samples),D_FIELD(battery_adc_raw),D_FIELD(battery_adc_samples),
    D_FIELD(battery_adc_error),D_FIELD(battery_adc_failures),D_FIELD(battery_divider_safe),D_FIELD(battery_divider_verified),
    D_FIELD(battery_reference_verified),D_FIELD(battery_sample_errors),D_FIELD(battery_gate_errors),D_FIELD(battery_raw_mode),
    D_FIELD(battery_input_mv),D_FIELD(battery_input_valid),D_FIELD(battery_saturated),D_FIELD(battery_sample_age_ms),
    D_FIELD(battery_reference_min_mv),D_FIELD(battery_reference_max_mv),
};
static const uint16_t diag_powercfg[]={
    D_FIELD(battery_top_ohm),D_FIELD(battery_bottom_ohm),D_FIELD(battery_maximum_mv),D_FIELD(battery_reference_floor_mv),
    D_FIELD(charger_pullups_verified),D_FIELD(battery_soc_curve_verified),
};
static const diag_fields_t diag_groups[]={
    {"ID\261fw\263build\263board\263uid\225\005\005\005\005\005\005\005\005\005\005\005 ui\261uptime_ms\221\r\n",diag_id,17u},
    {"CORE\261reset\263iwdg_reset\261faults\263clock\261lse\261io\261imu\261touch\261audio\261mic\261nor\261panel\261battery\261ram_gap\261stack_min\261stack_low\261stack_guard\221\r\n",diag_core,17u},
#if !defined(COMPANION_WBA_SCREEN_ENABLED) || COMPANION_WBA_SCREEN_ENABLED
    {"DISPLAY\261bound\261driver\261error\261presenter\261assets\261rendered\261failed\261stage\261busy\261transfer_calls\261busy_timeouts\221\r\n",diag_display,11u},
#endif
    {"STORAGE\261jedec\264size\261layout\261recording_ready\261rec_state\261rec_fault\261committed\261suspend_ok\261erase_active\261erase_sus\261sus_ms\261resume_ms\261bfp_dw\261dw12\263dw13\223\r\n",diag_storage,15u},
    {"AUDIO\261mic_init\261mic_run\261mic_hal\261mic_irq_err\261mic_stale\261mic_overflow\261mic_reject\261frames\261deadline\261speaker_ready\261fg_ms\261hal_ms\261rec_ms\261ble_ms\261runtime_ms\261present_ms\261render_ms\261pdm_ms\221\r\n",diag_audio,18u},
    {"TIMING\261rec_id\261mic_starts\261tick_us=1000 min_samples=20 enc_n\261enc_valid\261enc_p95_upper_ms\261enc_peak_upper_ms\261pdm_n\261pdm_valid\261pdm_p95_upper_ms\261pdm_peak_upper_ms\221\r\n",diag_timing,10u},
    {"BLE\261compiled\261init\261host\261host_error\261connection\262linked\261secured\261fatal\261bond_lost\261rebond\261pair_status\261pair_reason\221\r\n",diag_ble,12u},
    {"POWER\261adc\261voltage_valid\261percent_valid\261charger_valid\261charger_present\261mv\261pct\261charge\261ota_block\262sleep_block\223\r\n",diag_power,10u},
    {"BATTERY\261vref_raw\261vref_cal\261vdda_mv\261vref_valid\261vref_age_ms\261vref_n\261raw\261samples\261adc_error\261adc_failures\261divider_safe\261divider_verified\261reference_verified\261sample_errors\261gate_errors\261raw_mode\261input_mv\261input_valid\261saturated\261sample_age_ms\261vdda_min_mv\261vdda_max_mv\221\r\n",diag_battery,22u},
    {"POWERCFG\261top_ohm\261bottom_ohm\261max_cell_mv\261reference_floor_mv\261charger_pullups_verified\261soc_curve_verified\221\r\n",diag_powercfg,6u},
};
#undef D_FIELD
#undef D_MASK24
#undef D_FAULT

static uint32_t diagnostic_field(const comp_v11_diag_snapshot_t *s,uint16_t tag)
{
    const uint8_t *p=(const uint8_t *)s+(tag&511u);
    unsigned width=(tag>>9u)&3u;uint32_t value=0u;
    if(width==0u)value=*p;
    else if(width==1u){uint16_t v;memcpy(&v,p,sizeof(v));value=v;}
    else memcpy(&value,p,sizeof(value));
    if(tag&0x8000u)value=(value>>((tag>>11u)&15u))&1u;
    else if(width==3u)value&=0xFFFFFFu;
    return value;
}
static int diagnostic_fields_line(char *line,size_t capacity,
    const comp_v11_diag_snapshot_t *s,uint32_t seq,const diag_fields_t *group)
{
    const char *fmt=group->format;size_t at=6u;uint16_t argument=0u;
    if(capacity<=at)return -1;
    memcpy(line,"DIAG1 ",at);
    while(*fmt) {
        const unsigned token=(unsigned char)*fmt++;
        const unsigned type=(token&128u)?token&7u:token;
        if(type>5u){if(at+1u>=capacity)return -1;line[at++]=(char)token;continue;}
        if(argument==0u){if(at+4u>=capacity)return -1;memcpy(line+at," seq",4u);at+=4u;}
        const unsigned base=type==1u?10u:16u;
        unsigned width=type==2u?4u:type==3u?8u:type==4u?6u:type==5u?2u:0u;
        if((token&144u)==144u){if(at+1u>=capacity)return -1;line[at++]='=';}
        if(argument>group->count)return -1;
        uint32_t value=argument?diagnostic_field(s,group->fields[argument-1u]):seq;
        argument++;char digits[10];unsigned count=0u;
        do {unsigned d=(unsigned)(value%base);digits[count++]=(char)(d<10u?'0'+d:'a'+d-10u);value/=base;}while(value);
        if(width<count)width=count;
        if(at+width>=capacity)return -1;
        while(width>count){line[at++]='0';width--;}
        while(count)line[at++]=digits[--count];
        if((token&160u)==160u){if(at+1u>=capacity)return -1;line[at++]=' ';}
    }
    if(argument!=group->count+1u)return -1;
    line[at]='\0';return (int)at;
}

void comp_v11_diag_console_emit(comp_v11_diag_console_t *console,
                                const comp_v11_diag_snapshot_t *s,
                                comp_v11_diag_reason_t reason,
                                comp_v11_diag_write_fn_t write,
                                void *context)
{
    char line[512];
    uint32_t seq;
    if (console == NULL || s == NULL || write == NULL) return;
    seq = ++console->sequence;
    int length=snprintf(line, sizeof(line), "DIAG1 BEGIN seq=%lu reason=%s\r\n",
        (unsigned long)seq, reason_name(reason));
    if(!send(write, context, line, length, sizeof(line))) return;
    for(size_t i=0u;i<sizeof(diag_groups)/sizeof(diag_groups[0]);i++) {
        length=diagnostic_fields_line(line,sizeof(line),s,seq,&diag_groups[i]);
        if(!send(write,context,line,length,sizeof(line)))return;
    }
    length=snprintf(line, sizeof(line), "DIAG1 END seq=%lu\r\n", (unsigned long)seq);
    (void)send(write, context, line, length, sizeof(line));
}
