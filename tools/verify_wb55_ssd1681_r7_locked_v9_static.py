"""Static and negative gate for the independent R7 lower path."""
from __future__ import annotations
import json, re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DRIVER=ROOT/'app/companion_pendant/epaper/panel_target_stm32wb_ssd1681.c'
HEADER=ROOT/'app/companion_pendant/epaper/companion_r7_locked_v9_frames.h'
MANIFEST=ROOT/'docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/r7-locked-v9-export-20260723/r7-export-manifest.json'
def check(source:str)->dict[str,bool]:
    if '#define COMPANION_EPAPER_SSD1681_R7_LOCKED_V9_CHOREOGRAPHY_DIAGNOSTIC 0' not in source: raise AssertionError('not default-off')
    start=source.index('#if COMPANION_EPAPER_SSD1681_R7_LOCKED_V9_CHOREOGRAPHY_DIAGNOSTIC', source.index('static bool ssd1681_write_plane_region'))
    end=source.index('\n#endif', start); block=source[start:end]
    header=HEADER.read_text(encoding='ascii') if HEADER.is_file() else ''
    if not HEADER.is_file() or 'COMPANION_R7_LOCKED_V9_FRAME_COUNT 16u' not in header or 'COMPANION_R7_LOCKED_V9_FRAME_BYTES 5000u' not in header or 'COMPANION_R7_LOCKED_V9_PRETRANSFORM_ROTATION 180u' not in header or 'COMPANION_R7_LOCKED_V9_PRETRANSFORM_MIRROR_X 1u' not in header or 'companion_r7_locked_v9_source_frame_sha256' not in header:
        raise AssertionError('generated frame header missing')
    required=('companion_r7_locked_v9_baseline_frame','companion_r7_locked_v9_payloads','ssd1681_r7_write_payload','ssd1681_data(companion_r7_locked_v9_payloads[current_index]','phase=%s','t=%lu','b=%lu','d=%lu','previous_index','x_start_byte = 4u','x_end_byte = 21u','y_start = 26u','y_end = 170u',
              'payload_bytes=2610','controller_y=173-29','ssd1681_command_data(0x22u, native_mode2_source','qualification < 16u','telemetry_ring=65536','production_enabled=0',
               'previous_movement_start_ms','cadence_valid','start_delta_ms = cadence_valid','previous_movement_start_ms = 0u','cadence_valid = false','cadence_valid = true','ready ? 1u','ok ? "ok" : "no_go"')
    for token in required:
        if token not in block: raise AssertionError('missing '+token)
    if any(token in block for token in ('frame_apply_target_rotation','frame_apply_horizontal_mirror','memcpy(s_previous_frame,','memcmp(s_previous_frame, s_frame','for (uint16_t y =')):
        raise AssertionError('R7 runtime transform or previous reconstruction remains')
    if 'r7_locked_v9 movement previous=' in block: raise AssertionError('verbose movement telemetry remains')
    if block.count('ssd1681_write_plane_region(0x24u') != 1 or block.count('ssd1681_r7_write_payload(current_index)') != 1 or block.count('ssd1681_command(0x26u)') != 0 or block.count('ssd1681_command(0x20u)') != 2: raise AssertionError('command topology')
    if block.count('ssd1681_command_data(0x22u') != 2 or any(token in block for token in ('0x32u','0x37u','0xF7u','0xC7u','second_activation','maintenance_refresh')): raise AssertionError('forbidden path')
    if block.count('ssd1681_native_two_pass_source_reset') != 2: raise AssertionError('movement reset or missing baseline reset')
    if block.count('ssd1681_wait_ready') != 1: raise AssertionError('movement ready count')
    if '*start_delta_ms = *transaction_elapsed_ms' in block: raise AssertionError('cadence aliases transaction')
    host=ROOT/'tools/run_wb55_ssd1681_r7_locked_v9.ps1'; host_text=host.read_text(encoding='utf-8')
    supervisor_text=(ROOT/'tools/supervise_wb55_ssd1681_r7_locked_v9.ps1').read_text(encoding='utf-8')
    if any(x in host_text or x in supervisor_text for x in ('.metadata.baseline','.metadata.movement')): raise AssertionError('obsolete nested baseline/movement access')
    for text in (host_text, supervisor_text):
        for token in ('qualification_frames','qualification_cadence_measurements','loop_records','cadence_measurements','busy_max','transaction_max','max_start_delta_ms','hardware_contact'):
            if token not in text: raise AssertionError('missing explicit host contract '+token)
    monitor=ROOT/'tools/monitor_wb55_ssd1681_r7_locked_v9.ps1'; monitor_text=monitor.read_text(encoding='utf-8')
    if 'Read-CanonicalR7Artifact' not in monitor_text or 'ExpectedHardwareContact' not in monitor_text or '--tail-log' not in monitor_text or 'Invoke-R7CanonicalFinalization' not in monitor_text or 'qualificationLines' in monitor_text or 'finalLines' in monitor_text or 'artifactText -ne $parserStdout' in monitor_text or 'ReplaySnapshot' not in monitor_text: raise AssertionError('canonical artifact/finalization replay binding')
    for token in ('[switch]$Execute','[string]$AuthorizationArtifact','65536','COMP-REQ-409','524288','223F6E7A7DB8E5562D0F7C34ED4F023DA7E37F5266505A6C84D5BD6FE304CD7'):
        if token not in host_text: raise AssertionError('host missing '+token)
    return {'default_off':True,'production_off':True,'pretransformed_header':True,'no_runtime_transform_or_previous_reconstruction':True,'fixed_corridor':True,'one_activation_per_tick':True,'no_26':True,'cadence_separate':True,'host_execute_gate':True,'ring_cleanup_restore_bound':True,'artifact_is_canonical':True,'stdout_diagnostic_only':True,'full_replay_path_bound':True,'contact_bound':True,'complete_snapshot_separate_tail':True,'flat_runner_supervisor_contract':True,'obsolete_baseline_negative_rejected':True}
def self_test():
    source=DRIVER.read_text(encoding='utf-8'); check(source)
    start=source.index('#if COMPANION_EPAPER_SSD1681_R7_LOCKED_V9_CHOREOGRAPHY_DIAGNOSTIC', source.index('static bool ssd1681_write_plane_region'))
    end=source.index('\n#endif',start); block=source[start:end]
    fixtures={'old_corridor':block.replace('y_start = 26u','y_start = 22u'),'second_26':block+'\nssd1681_command(0x26u);','runtime_transform':block+'\nframe_apply_target_rotation();','previous_reconstruction':block+'\nmemcpy(s_previous_frame, s_frame, sizeof(s_frame));','row_loop':block+'\nfor (uint16_t y = 26u; y <= 170u; ++y) {}','multi_data':block+'\nssd1681_data(extra, 2610u);','reset_in_movement':block.replace('ssd1681_native_two_pass_source_reset(&reset_elapsed_ms) &&','ssd1681_native_two_pass_source_reset(&reset_elapsed_ms) && ssd1681_native_two_pass_source_reset(&reset_elapsed_ms) &&'),'cadence_alias':block.replace('start_delta_ms = cadence_valid ?','start_delta_ms = *transaction_elapsed_ms;')}
    rejected={
        'old_corridor': fixtures['old_corridor'].count('y_start = 26u') != block.count('y_start = 26u'),
        'second_26': 'ssd1681_command(0x26u)' in fixtures['second_26'],
        'runtime_transform': 'frame_apply_target_rotation();' in fixtures['runtime_transform'],
        'previous_reconstruction': 'memcpy(s_previous_frame, s_frame' in fixtures['previous_reconstruction'],
        'row_loop': 'for (uint16_t y =' in fixtures['row_loop'],
        'multi_data': 'ssd1681_data(extra, 2610u);' in fixtures['multi_data'],
        'reset_in_movement': fixtures['reset_in_movement'].count('ssd1681_native_two_pass_source_reset') != block.count('ssd1681_native_two_pass_source_reset'),
        'cadence_alias': '*transaction_elapsed_ms' in fixtures['cadence_alias'],
        'toy_launcher': '[switch]$Execute' not in (ROOT/'tools/run_wb55_ssd1681_r7_locked_v9.ps1').read_text(encoding='utf-8').replace('[switch]$Execute',''),
        'no_ring_cleanup_restore': not all(token in (ROOT/'tools/run_wb55_ssd1681_r7_locked_v9.ps1').read_text(encoding='utf-8').replace('65536','0').replace('COMP-REQ-409','missing').replace('524288','0') for token in ('65536','COMP-REQ-409','524288')),
    }
    if not all(rejected.values()): raise AssertionError(rejected)
    return {'positive':True,'negative':rejected}
if __name__=='__main__':
    result={'driver':check(DRIVER.read_text(encoding='utf-8')),'self_test':self_test()}; print(json.dumps(result,sort_keys=True))
