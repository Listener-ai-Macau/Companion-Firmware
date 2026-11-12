#!/usr/bin/env python3
"""Exercise the WBA product button/audio/recording chain on a fake board.

This is host-only integration evidence.  It uses the real product runtime,
continuous recording core, segmented catalog, and fixed-point Opus encoder while replacing the
physical board, NOR transport, and display assets with deterministic fakes.
"""

from __future__ import annotations

import hashlib
import argparse
import json
import os
import pathlib
import struct
import subprocess
import sys
import wave


REPO = pathlib.Path(__file__).resolve().parents[1]
# Verify an immutable candidate without changing the shared working tree.
# Keep artifacts under the short repository path for Windows MAX_PATH callers.
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('artifact_name')
parser.add_argument('source_root',type=pathlib.Path,nargs='?')
parser.add_argument('--power-guard-only',action='store_true')
parser.add_argument('--resource-timeout-only',action='store_true')
parser.add_argument('--resource-uncertain-only',action='store_true')
parser.add_argument('--idle-display-failure-only',action='store_true')
parser.add_argument('--screen-disabled',action='store_true')
parser.add_argument('--late-button-release-only',action='store_true')
parser.add_argument('--capture-controls-only',action='store_true')
parser.add_argument('--imu-highlight-only',action='store_true')
parser.add_argument('--input-interaction-only',action='store_true')
parser.add_argument('--pointer-single-tap-only',action='store_true')
parser.add_argument('--idle-prime-only',action='store_true')
parser.add_argument('--auto-fault-recovery-only',action='store_true')
parser.add_argument('--opus-lib',type=pathlib.Path)
options=parser.parse_args()
ROOT = options.source_root.resolve() if options.source_root else REPO
OUT = REPO / ".cache/recording-core-20261011" / options.artifact_name
POWER_GUARD_ONLY = options.power_guard_only
APP = ROOT / "app" / "companion_pendant"
PLATFORM = ROOT / "platform" / "stm32wba55_companion_v11"
WIRE = ROOT / "third_party" / "denzic-platform" / "audio" / "embedded" / "c" / "include"
OPUS = ROOT / "third_party" / "opus"


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(command, cwd=OUT, text=True, capture_output=True, check=False)
    if result.returncode:
        raise RuntimeError(
            f"command failed ({result.returncode}): {' '.join(command)}\n"
            f"{result.stdout}\n{result.stderr}"
        )
    return result


def run_vc(command: str) -> subprocess.CompletedProcess[str]:
    vcvars = pathlib.Path(os.environ.get("ProgramFiles(x86)", "")) / (
        "Microsoft Visual Studio/2022/BuildTools/VC/Auxiliary/Build/vcvars64.bat"
    )
    if not vcvars.exists():
        raise RuntimeError(f"MSVC environment not found: {vcvars}")
    script = OUT / "vc-command.cmd"
    script.parent.mkdir(parents=True, exist_ok=True)
    script.write_text(
        f'@call "{vcvars}" >nul\n@if errorlevel 1 exit /b %errorlevel%\n@{command}\n',
        encoding="utf-8",
    )
    return run(["cmd", "/d", "/c", str(script)])


def quote(path: pathlib.Path) -> str:
    return f'"{path}"'


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def decode_cop1(source: pathlib.Path, wav_path: pathlib.Path) -> dict[str, int]:
    import av
    import numpy as np
    import zlib

    raw = source.read_bytes()
    if len(raw) < 12 or raw[:4] != b"COP1" or raw[4:8] not in (bytes((1, 1, 20, 0)), bytes((4, 1, 20, 7))):
        raise RuntimeError("product artifact has an invalid COP1 header")
    if struct.unpack_from("<I", raw, 8)[0] != 16000:
        raise RuntimeError("product artifact sample rate is not 16 kHz")
    decoder = av.CodecContext.create("opus", "r")
    offset = 12
    packets = 0
    samples = []
    sample_rate = 0
    config = end = None
    while offset + 2 <= len(raw):
        if raw[4] >= 2 and raw[offset] == 255:
            offset += 1
            continue
        begin = offset
        length = struct.unpack_from("<H", raw, offset)[0]
        offset += 2
        if length == 0 and raw[4] == 4 and raw[begin+2:begin+6] == b'CPG1':
            wire=raw[begin:begin+32]
            if len(wire)!=32 or wire[6]!=4 or wire[7] or zlib.crc32(wire[:28])!=struct.unpack_from('<I',wire,28)[0]:
                raise RuntimeError(f'invalid bookmark at {begin}')
            offset=begin+32
            continue
        if length == 0 and raw[4] == 4:
            wire = raw[begin:begin + 32]
            if len(wire) != 32 or wire[2:6] != b"CDB1" or wire[7] != 0 or zlib.crc32(wire[:28]) != struct.unpack_from('<I', wire, 28)[0]:
                raise RuntimeError(f"invalid codec boundary at {begin}")
            delay, encoded, valid = struct.unpack_from('<IQQ', wire, 8)
            if wire[6] == 1 and begin == 12 and config is None and encoded == 0 and valid == (1 << 64) - 1 and delay <= 160:
                config = delay
            elif wire[6] == 2 and begin % 248 == 0 and config == delay and end is None and encoded == (packets + 1) * 320 and valid in (packets * 320, packets * 320 + 160) and encoded - valid >= delay:
                end = (encoded, valid)
            else:
                raise RuntimeError(f"inconsistent codec boundary at {begin}")
            offset = begin + 32
            continue
        if length == 0 or length > 400 or offset + length > len(raw):
            raise RuntimeError(f"invalid packet at offset {offset - 2}")
        if raw[4] == 4 and (config is None or length != 40 or (end is not None and (packets + 1) * 320 > end[0])):
            raise RuntimeError("invalid schema 4 audio order or length")
        frames = decoder.decode(av.Packet(raw[offset : offset + length]))
        offset += length
        packets += 1
        for frame in frames:
            sample_rate = frame.sample_rate
            array = frame.to_ndarray()
            if array.ndim == 2:
                array = array.mean(axis=0)
            samples.append(array)
    if offset != len(raw) or packets == 0 or not samples:
        raise RuntimeError("independent decoder did not consume product artifact")
    pcm = np.concatenate(samples)
    if raw[4] == 4:
        if config is None or end is None or packets * 320 != end[0] or sample_rate % 16000:
            raise RuntimeError("incomplete schema 4 audio")
        scale = sample_rate // 16000
        pcm = pcm[config * scale:(config + end[1]) * scale]
        if len(pcm) != end[1] * scale:
            raise RuntimeError("decoded samples do not cover declared source")
    if np.issubdtype(pcm.dtype, np.floating):
        pcm16 = (pcm * 32767.0).clip(-32768, 32767).astype("<i2")
    else:
        pcm16 = pcm.clip(-32768, 32767).astype("<i2")
    with wave.open(str(wav_path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(pcm16.tobytes())
    return {
        "packets": packets,
        "samples": int(len(pcm16)),
        "sample_rate_hz": sample_rate,
        "duration_ms": int(round(len(pcm16) * 1000 / sample_rate)),
    }


def main() -> int:
    import shutil
    from verify_wba_spi_nor_adapter import find_vsdevcmd
    OUT.mkdir(parents=True,exist_ok=False)
    if POWER_GUARD_ONLY:
        from wba_power_profile import DEFAULT,validate,write_header
        import copy
        assert DEFAULT['recordingStopMv']==DEFAULT['recordingResumeMv']==0 and not DEFAULT['recordingLimitsVerified']
        for change in ({'recordingLimitsVerified':True}, {'recordingStopMv':True},
                       {'recordingStopMv':3300,'recordingResumeMv':3200},
                       {'recordingStopMv':3200,'recordingResumeMv':3400,'recordingLimitsVerified':True}):
            candidate=copy.deepcopy(DEFAULT);candidate.update(change)
            try:validate(candidate)
            except ValueError:pass
            else:raise AssertionError('Unqualified/ambiguous recording limits accepted: '+repr(change))
        assert not write_header(OUT)['recording_protection_qualified']
        candidate=copy.deepcopy(DEFAULT);candidate.update(topOhm=150000,dividerVerified=True,referenceVerified=True,
            recordingStopMv=3200,recordingResumeMv=3450,recordingLimitsVerified=True,
            qualificationEvidence='HOST_ONLY_RESERVE_FIXTURE_NOT_BOARD_APPROVAL')
        assert validate(candidate)
    names = ['wba_recording_product','wba_recording_recovery','wba_recording_pipeline','wba_segment_storage',
        'companion_continuous_recording','companion_segment_audio','companion_range_receipt','companion_range_reclaim','companion_segment_catalog',
        'companion_segment_reserve','companion_recording_identity','companion_opus16_rt','wba_silence_stop','wba_segment_discard_preview','wba_segment_discard_worker','wba_segment_discard_control','wba_segment_discard_wire']
    sources=[PLATFORM/'tests/test_product_recording_segmented.c',PLATFORM/'product_app.c',
        *[APP/'recording'/(n+'.c') for n in names],
        APP/'runtime/companion_runtime.c',APP/'runtime/companion_preferences.c',APP/'runtime/companion_pet_profile_store.c',APP/'runtime/companion_pet_profile.c',APP/'runtime/companion_pet_profile_wire.c',
        APP/'runtime/companion_pet_chat.c',APP/'imu/motion_events.c',
        APP/'playback/audio_feedback.c',APP/'playback/speaker_playback.c',APP/'touch/touch_gesture.c',
        APP/'touch/touch_tap_arbiter.c',APP/'touch/browser_interaction_runtime.c',APP/'epaper/screen_menu.c',
        APP/'epaper/screen_framebuffer.c',APP/'epaper/motion_coordinator.c',APP/'power/power_settings_store.c',
        APP/'power/power_policy.c',APP/'power/wba_power_monitor.c',APP/'power/wba_button.c',
        APP/'board/companion_v11_board.c',APP/'board/tca6408.c',APP/'storage/wba_workspace_layout.c']
    files=set(sources)|set(APP.rglob('*.h'))|set(PLATFORM.glob('*.h'))|set((PLATFORM/'tests').glob('*.h'))|set((PLATFORM/'tests/fakes').glob('*.h'))|set(WIRE.rglob('*.h'))
    hashes={};frozen=OUT/'source'
    for p in sorted(files):
        target=frozen/p.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(p.read_bytes());hashes[p.relative_to(ROOT).as_posix()]=sha256(target)
    (OUT/'source.json').write_text(json.dumps(hashes,indent=2)+'\n',encoding='utf-8')
    exe=OUT/'product.exe';cop1=OUT/'product.cop1';wav=OUT/'product.wav'
    lib=options.opus_lib.resolve() if options.opus_lib else REPO/'.cache/opus-host-fixed/opus.lib'
    includes=[PLATFORM/'tests/fakes',PLATFORM,*[APP/n for n in ['board','imu','playback','storage','v1_features','power','touch','recording','epaper','runtime','runtime/generated','update']],WIRE]
    args=['cl.exe','/nologo','/TC','/std:c11','/O2','/W4','/WX','/wd4127','/wd5287','/wd4100','/utf-8','/MD','/D_CRT_SECURE_NO_WARNINGS',
        '/DCOMPANION_WBA_RESOURCE_PROFILE=1','/DCOMP_V11_PANEL_PASSIVE_TRACE=1',
        '/DCOMPANION_RECORDING_SEGMENTED_ONLY=1',
        '/DCOMPANION_SCREEN_COMP_REQ_638_SOURCE_PACK=1',
        '/DCOMPANION_OPUS16_WBA_LOWDELAY=1','/DCOMPANION_OPUS16_ENCODER_BYTES=65536','/DCOMPANION_OPUS16_STDIO_ERRORS=0',
        *['/I'+str(frozen/p.relative_to(ROOT)) for p in includes],'/I'+str(OPUS/'include'),
        *[str(frozen/p.relative_to(ROOT)) for p in sources],'/Fe:'+str(exe),'/link',str(lib)]
    if options.screen_disabled:args.insert(1,'/DCOMPANION_WBA_SCREEN_ENABLED=0')
    script=OUT/'compile.cmd';script.write_text('@echo off\ncall "'+str(find_vsdevcmd())+'" -arch=amd64 -host_arch=amd64 >nul\nif errorlevel 1 exit /b %errorlevel%\n'+subprocess.list2cmdline(args)+'\n',encoding='utf-8')
    def stage(command,name):
        result=subprocess.run(command,cwd=OUT,capture_output=True,text=True)
        (OUT/name).write_text(result.stdout+result.stderr,encoding='utf-8')
        if result.returncode:raise RuntimeError(f'{name}: exit{result.returncode}: '+result.stdout+result.stderr)
        return result.stdout
    try:
        stage(['cmd.exe','/d','/c',str(script)],'compile.txt')
        if options.pointer_single_tap_only:
            output=stage([str(exe),str(cop1),'--pointer-single-tap-only'],'result.txt')
            assert output.startswith('PASS_POINTER_SINGLE_TAP_PRODUCT_ONLY'),output
            result=dict(result='PASS_POINTER_SINGLE_TAP_PRODUCT_ONLY',output=output,physicalBoard=False,installed=False)
            (OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result));return 0
        output=stage([str(exe),str(cop1),*(['--input-interaction-only'] if options.input_interaction_only else ['--imu-highlight-only'] if options.imu_highlight_only else ['--auto-fault-recovery-only'] if options.auto_fault_recovery_only else ['--idle-prime-only'] if options.idle_prime_only else ['--capture-controls-only'] if options.capture_controls_only else (['--late-button-release-only'] if options.late_button_release_only else (['--idle-display-failure-only'] if options.idle_display_failure_only else (['--resource-uncertain-only'] if options.resource_uncertain_only else (['--resource-timeout-only'] if options.resource_timeout_only else (['--power-guard-only'] if POWER_GUARD_ONLY else []))))))],'result.txt')
        if options.auto_fault_recovery_only:
            assert output.startswith('PASS_AUTOMATIC_FAILED_ORIGINAL_SOFTWARE_ONLY'),output
            result=dict(result='PASS_AUTOMATIC_FAILED_ORIGINAL_SOFTWARE_ONLY',output=output,physicalBoard=False,installed=False)
            (OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result));return 0
        if options.idle_prime_only:
            assert output.startswith('PASS real product idle erase handoff'),output
            result=dict(result='PASS_IDLE_PRIME_PRODUCT_HANDOFF_SOFTWARE_ONLY',output=output,physicalBoard=False,installed=False)
            (OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result));return 0
        if options.capture_controls_only or options.imu_highlight_only or options.input_interaction_only:
            assert output.startswith('PASS recorder/desktop input' if options.input_interaction_only else 'PASS IMU highlight' if options.imu_highlight_only else 'PASS Capture recorder-card controls'),output
            decoded=decode_cop1(cop1,wav)
            raw=cop1.read_bytes()
            marks=[]
            for i in range(2,len(raw)-29):
                if raw[i:i+4]==b'CPG1' and raw[i-2:i]==b'\0\0':
                    wire=raw[i-2:i+30]
                    import zlib
                    assert wire[6]==4 and zlib.crc32(wire[:28])==struct.unpack_from('<I',wire,28)[0]
                    marks.append(dict(sequence=struct.unpack_from('<I',wire,8)[0],sampleOffset=struct.unpack_from('<Q',wire,12)[0],elapsedMs=struct.unpack_from('<Q',wire,20)[0]))
            expected_marks=1 if options.imu_highlight_only or options.input_interaction_only else 2
            assert len(marks)==expected_marks and [m['sequence'] for m in marks]==list(range(1,expected_marks+1))
            assert all(m['sampleOffset']>0 for m in marks)
            if expected_marks==2:assert marks[0]['sampleOffset']<marks[1]['sampleOffset']
            result=dict(result='PASS_RECORDER_DESKTOP_INPUT_SOFTWARE_ONLY' if options.input_interaction_only else 'PASS_IMU_OFFLINE_HIGHLIGHT_SOFTWARE_ONLY' if options.imu_highlight_only else 'PASS_CAPTURE_RECORDER_CONTROLS_SOFTWARE_ONLY',output=output,physicalBoard=False,installed=False,
                sourceSha256=hashes,decoded=decoded,marks=marks,cop1=dict(bytes=len(raw),sha256=sha256(cop1)))
            (OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:v for k,v in result.items() if k!='sourceSha256'}));return 0
        if options.late_button_release_only:
            assert output.startswith('PASS Capture real product long press'),output
            result=dict(result='PASS_CAPTURE_LATE_RELEASE_SOFTWARE_ONLY',output=output,physicalBoard=False,installed=False)
            (OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result));return 0
        if options.idle_display_failure_only:
            assert output.startswith('PASS failed display idle policy'),output
            result=dict(result='PASS_FAILED_DISPLAY_IDLE_POLICY_SOFTWARE_ONLY',output=output,physicalBoard=False,installed=False)
            (OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result));return 0
        if options.resource_uncertain_only:
            assert output.startswith('PASS uncertain resource bus failure'),output
            result=dict(result='PASS_RESOURCE_UNCERTAIN_FAULT_SOFTWARE_ONLY',output=output,physicalBoard=False,installed=False)
            (OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result));return 0
        if options.resource_timeout_only:
            assert output.startswith('PASS recording survives bounded resource read failure'),output
            result=dict(result='PASS_RESOURCE_READ_AUDIO_SOFTWARE_ONLY',output=output,physicalBoard=False,timingQualified=False,installed=False)
            (OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result));return 0
        if POWER_GUARD_ONLY:
            assert output.startswith('PASS_WBA_POWER_GUARD_PRODUCT_SOFTWARE_ONLY'),output
            result=dict(result='PASS_POWER_GUARD_PRODUCT_SOFTWARE_ONLY',sourceSha256=hashes,output=output,
                cop1=dict(bytes=cop1.stat().st_size,sha256=sha256(cop1)),libOpusSha256=sha256(lib),
                physicalBoard=False,physicalMicrophone=False,physicalNor=False,physicalSpeaker=False,
                realBle=False,otaLeaseResultSimulated=True,timingQualified=False,installed=False,
                actualBoardProtection='NOT_QUALIFIED',wireStopReason='DESCRIPTOR_EXPORTED_CMS3_NOT_RUN',
                descriptor=dict(bytes=pathlib.Path(str(cop1)+'.descriptor').stat().st_size,
                    sha256=sha256(pathlib.Path(str(cop1)+'.descriptor')),terminalCause='lowBattery',
                    normalRemountPreserved=True))
            (OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
            print(json.dumps({k:v for k,v in result.items() if k!='sourceSha256'}));return 0
        assert output.startswith('PASS_WBA_PRODUCT_RECORDING_SEGMENTED_HOST_ONLY'),output
        decoded=decode_cop1(cop1,wav)
        assert decoded['duration_ms']>=400 and decoded['sample_rate_hz']==48000
        result=dict(result='PASS_REAL_PRODUCT_APP_SOFTWARE_ONLY',sourceSha256=hashes,output=output,
            independentDecode=decoded,cop1=dict(bytes=cop1.stat().st_size,sha256=sha256(cop1)),
            libOpusSha256=sha256(lib),physicalBoard=False,physicalMicrophone=False,physicalNor=False,
            physicalSpeaker=False,realBle=False,otaLeaseResultSimulated=True,timingQualified=False,installed=False)
    except Exception as error:
        result=dict(result='FAILED_REAL_PRODUCT_APP_SOFTWARE',error=str(error),installed=False)
        (OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result));raise
    (OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='sourceSha256'}));return 0

if __name__=='__main__':
    raise SystemExit(main())
