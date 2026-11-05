#!/usr/bin/env python3
"""One explicit two-second engineering PCM-pair window, fixed V3 UART.

Requires an installed matching signed image. No BLE central, playback, cloud,
SWD, reset, baud change or retry. The paired source is separate from normal
product recordings and is never declared calibrated/denoised. Normal UART
admission is queried once; a post-operation query only checks actual release.
"""
from pathlib import Path
from datetime import datetime
import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
import time

SN='004400403532510B31333430'
UID='120011000d50335754363720'
MAX_WIRE=2_000_000


def fields(line):
    return dict(item.split('=',1)for item in line.split()if '='in item)


class PairRows:
    """Pure incremental parser; no hardware or manufacture of missing data."""
    def __init__(self):
        self.pending=bytearray();self.stream=bytearray();self.states=[];self.faults=[]
        self.dump_started=False;self.end=None;self.released=False;self.rejected=False

    def feed(self,chunk):
        self.pending.extend(chunk)
        if len(self.pending)>16384:raise ValueError('Unterminated UART row exceeds limit')
        while b'\n'in self.pending:
            raw,_,rest=self.pending.partition(b'\n');self.pending=bytearray(rest)
            line=raw.rstrip(b'\r').decode('ascii','replace')
            if line.startswith('DPAIR STATE '):
                self.states.append(fields(line));self.states=self.states[-16:];self.faults=[]
            elif line.startswith('DPAIR FAULTS '):
                self.faults.append(fields(line));self.faults=self.faults[-16:]
            elif line.startswith('DPAIR DATA '):
                if not self.dump_started or self.end is not None:raise ValueError('Unexpected pair payload')
                m=re.fullmatch(r'DPAIR DATA offset=(\d+) hex=([0-9a-f]{2,64})',line)
                if not m or len(m[2])%2 or int(m[1])!=len(self.stream):raise ValueError('Pair payload missing/repeated/reordered')
                self.stream.extend(bytes.fromhex(m[2]))
                if len(self.stream)>132928:raise ValueError('Pair payload exceeds finite target window')
            elif line.startswith('DPAIR END '):
                if not self.dump_started or self.end is not None:raise ValueError('Unexpected terminal row')
                self.end=fields(line)
                if int(self.end.get('bytes','-1'))!=len(self.stream):raise ValueError('Pair terminal byte count mismatch')
            elif line=='DPAIR RELEASED mic=0 workspace=0':self.released=True
            elif line.startswith('DPAIR REJECTED'):self.rejected=True


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--project-root',type=Path,required=True)
    p.add_argument('--expected-version',type=int,required=True)
    p.add_argument('--expected-source',required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--known-source-setup',type=Path,
        help='Optional explicit current known-source setup, validated and bound before any device access')
    a=p.parse_args();root=a.project_root.resolve();out=a.output.resolve()
    assert re.fullmatch(r'[0-9a-f]{40}',a.expected_source)and 1<=a.expected_version<=0xffffffff
    assert (root/'docs/board_operations.md').is_file()
    setup_raw=None;setup=None
    if a.known_source_setup is not None:
        from calibrate_wba_dual_mic_pair import validate_setup
        assert a.known_source_setup.stat().st_size<=2_000_000,'Setup exceeds finite limit'
        setup_raw=a.known_source_setup.read_bytes()
        setup=validate_setup(setup_raw,UID,a.expected_source)
    out.mkdir(parents=True,exist_ok=False)
    if setup_raw is not None:(out/'known-source-setup.json').write_bytes(setup_raw)
    sys.path.insert(0,str(root/'tools'))
    from atomic_artifact_write import write_bytes_atomic
    from select_companion_transport_endpoint import select_next,register_stage
    sys.path.insert(0,str(root/'Companion-Firmware/tools'))
    from diagnose_wba_uart import parse_frames
    import serial
    from serial.tools import list_ports
    sys.path.insert(0,str(Path(__file__).resolve().parent))
    import decode_wba_dual_mic_stream as decoder
    now=lambda:datetime.now().astimezone().isoformat(timespec='seconds')
    selection=select_next()
    (out/'endpoint-selection.json').write_text(json.dumps(selection,ensure_ascii=False,indent=2)+'\n')
    obs=selection['observation']
    assert selection['stageBoundary']=='closed_and_physical_idle_observed','Previous physical owner unresolved'
    assert obs.get('serviceActive')is not True and not(obs.get('adbOnline')and obs.get('serviceActive')is None),'Phone owner unresolved'
    # This operation has no BLE-central equivalent in the current diagnostic
    # App: it is the firmware's wired service command. Observe phone policy,
    # keep any active phone job, and open only the fixed V3 UART.
    state=dict(result='PREPARING_WIRED_FINITE_PAIR_WINDOW',startedAtLocal=now(),
        expectedFirmwareWireVersion=a.expected_version,expectedSource=a.expected_source,
        endpointSelection=selection,executionEndpoint='fixed_v3_wired_service_no_central',
        endpointReason='Current Android upload/OTA App does not expose DPAIR UART service; no BLE central is started',
        finiteEngineeringWindow=True,normalProductRecording=False,knownFrontSourceConfirmed=setup is not None,
        knownSourceSetupSha256=hashlib.sha256(setup_raw).hexdigest()if setup_raw is not None else None,
        knownSourceIsCallerDeclaration=True,
        recordings=0,cloudCalls=0,playback=False,hostMicrophone=False,reset=False,swd=False,
        physicalNoiseReductionQualified=False,ownHandlesClosed=False,availabilityQueries=0)
    def save():write_bytes_atomic(out/'result.json',(json.dumps(state,ensure_ascii=False,indent=2)+'\n').encode())
    board=root/'docs/board_operations.md'
    def owners(raw):return [x for x in raw.decode('utf-8-sig').split('## 当前占用',1)[1].split('## 交接方式',1)[0].splitlines()if '**占用中**'in x]
    lease=f'- **占用中**：上层P645固定V3有限双麦工程窗，{state["startedAtLocal"]}，当前正常应用一次准入后只采2秒独立PCM、停麦后读回及实际释放；无BLE中央/播放/云/SWD/复位，失败不重开。依据{out/"result.json"}。'
    def replace(old,new):
        raw=board.read_bytes();needle=old.encode();assert raw.count(needle)==1
        assert board.read_bytes()==raw;write_bytes_atomic(board,raw.replace(needle,new.encode(),1))
    def guard():assert owners(board.read_bytes())==[lease],'Shared board owner changed'
    held=False;port=None;log=None;wire=bytearray();rows=PairRows();last_rx=time.monotonic();started=False
    def pump():
        nonlocal last_rx
        guard();chunk=port.read(min(max(port.in_waiting,1),4096))
        if chunk:
            if len(wire)+len(chunk)>MAX_WIRE:raise RuntimeError('UART evidence exceeded finite limit')
            wire.extend(chunk);log.write(chunk);log.flush();rows.feed(chunk);last_rx=time.monotonic()
        return chunk
    def quiet():
        deadline=time.monotonic()+2
        while time.monotonic()<deadline:
            pump()
            if time.monotonic()-last_rx>=.250:return
        raise RuntimeError('Target output did not become idle; no command queued')
    def send(command):
        quiet()
        for byte in b'\n'+command.encode()+b'\n':
            guard();port.write(bytes([byte]));port.flush();time.sleep(.020)
        state.setdefault('commands',[]).append(dict(command=command,atLocal=now()));save()
    try:
        assert not owners(board.read_bytes()),'Another chat owns the board'
        replace('## 当前占用','## 当前占用\n\n'+lease);held=True;save();register_stage(out/'result.json','uart-service')
        ports=[x.device for x in list_ports.comports()if x.serial_number==SN];assert len(ports)==1,'Fixed V3 UART mapping unavailable or ambiguous'
        port=serial.Serial(port=None,baudrate=115200,timeout=.05,write_timeout=1,rtscts=False,dsrdtr=False,xonxoff=False)
        port.dtr=port.rts=False;port.port=ports[0];guard();port.open()
        log=(out/'live-uart.log').open('xb');state['uartPort']=ports[0]
        port.write(b'?');port.flush();state['availabilityQueries']=1;save();deadline=time.monotonic()+12;before=None
        while time.monotonic()<deadline:
            pump();frames,_=parse_frames(bytes(wire));fresh=[f for f in frames if f['reason']=='query']
            if fresh:before=fresh[-1];break
        assert before,'No complete normal application reply; stop without START/reconnect/reset'
        state['beforeSnapshot']=before;s=before['sections']
        assert int(s['ID']['fw'],16)==a.expected_version and s['ID']['uid']==UID and s['ID']['ui']==84,'Actual image/UID mismatch'
        assert not s['AUDIO']['mic_run']and s['BLE']['linked']==0 and s['STORAGE']['recording_ready']==1 and not s['STORAGE']['rec_fault'],'Application is not idle'
        send('DPAIR START');started=True;state['result']='ACTUAL_FINITE_PAIR_WINDOW_STARTED';state['captureAttempts']=1;save();deadline=time.monotonic()+30
        while time.monotonic()<deadline:
            pump()
            assert not rows.rejected,'Target rejected START; do not retry'
            if rows.states and rows.states[-1]['state']in ('6','8','9')and rows.faults:break
        if rows.states:state['captureStatus']=rows.states[-1]
        if rows.faults:state['captureFaults']=rows.faults[-1]
        save()
        assert rows.states and rows.states[-1]['state']=='6'and rows.states[-1]['error']=='0','Capture did not complete cleanly'
        assert rows.faults,'No actual capture counter row'
        state['recordings']=1
        state['normalProductRecordings']=0
        state['actualCaptureKind']='ONE_FINITE_ENGINEERING_PCM_PAIR_WINDOW'
        state['captureFaults']=rows.faults[-1]
        assert set(rows.faults[-1])=={'missing','reordered','invalid','rejected','stale','overflow','irq','deadline'}
        assert all(int(v)==0 for v in rows.faults[-1].values()),'Actual capture counters failed'
        rows.dump_started=True;send('DPAIR DUMP');deadline=time.monotonic()+60
        while time.monotonic()<deadline and rows.end is None:pump()
        (out/'original-pair.dmp').write_bytes(rows.stream)
        assert rows.end and rows.end['error']=='0','No complete clean dump'
        pcm,identity=decoder.decode(bytes(rows.stream));assert len(pcm)==128000
        assert identity['deviceUid']==UID and identity['firmwareSource']==a.expected_source and identity['synthetic']is False
        assert identity['sampleCount']==32000 and identity['recordingToken']==int(rows.states[-1]['token'])and identity['recordingId']==int(rows.states[-1]['capture'])
        state['sourceIdentity']=identity;state['sourceBytes']=len(rows.stream);state['result']='PAIR_BYTES_COMPLETE_RELEASE_PENDING';save()
        send('DPAIR RELEASE');deadline=time.monotonic()+8
        while time.monotonic()<deadline and not rows.released:pump()
        assert rows.released,'Actual microphone/workspace release not confirmed'
        # One post-operation snapshot, not a failed-admission retry. Same port.
        quiet();offset=len(wire);port.write(b'?');port.flush();deadline=time.monotonic()+12;after=None
        while time.monotonic()<deadline:
            pump();frames,_=parse_frames(bytes(wire[offset:]));fresh=[f for f in frames if f['reason']=='query']
            if fresh:after=fresh[-1];break
        assert after,'No complete post-operation identity/idle reply'
        s=after['sections'];assert int(s['ID']['fw'],16)==a.expected_version and s['ID']['uid']==UID
        assert s['BLE']['linked']==0 and not s['AUDIO']['mic_run']and not s['STORAGE']['erase_active']
        state['postPhysicalIdle']=after
        evidence=dict(schema='companion.dual-mic-pair-capture.v1',streamSha256=decoder.sha(bytes(rows.stream)),**identity,
            processedChannelMask=3,sourcePositionFromCapture=True,captureKind='BOARD_SAI_PDM',
            captureIdentityKind='FINITE_ENGINEERING_WINDOW_NOT_PRODUCT_CATALOG',
            processingStage='POST_CHANNEL_GAIN_DC_PRE_BEAMFORM_PCM16',completed=True,
            captureFaultCounters=dict(zip(decoder.FAULT_COUNTERS,[int(rows.faults[-1][key])for key in ['missing','reordered','invalid','rejected','stale','overflow','irq','deadline']])),
            originalUartLogSha256=hashlib.sha256(bytes(wire)).hexdigest(),
            exactSourceIdentitySelfReportedNotAuthentication=True,knownFrontSourceConfirmed=setup is not None,
            knownSourceSetupSha256=hashlib.sha256(setup_raw).hexdigest()if setup_raw is not None else None,
            knownSourceIsCallerDeclaration=True)
        (out/'capture-evidence.json').write_text(json.dumps(evidence,indent=2)+'\n')
        decoder.create_bundle(out/'original-pair.dmp',out/'capture-evidence.json',out/'independent-source',
            use_case=setup['useCase']if setup is not None else 'GENERAL_DUAL_MIC_CAPTURE')
        state['result']='ACTUAL_INDEPENDENT_PAIR_SOURCE_READBACK_AND_RELEASE_CONFIRMED';save()
    except BaseException as error:
        state.update(result='ACTUAL_PAIR_OPERATION_FAILED_OR_UNCONFIRMED',error=repr(error));save()
        if rows.stream and not(out/'original-pair.dmp').exists():(out/'original-pair.dmp').write_bytes(rows.stream)
        raise
    finally:
        if started and not rows.released and port is not None and port.is_open:
            try:
                send('DPAIR RELEASE');deadline=time.monotonic()+8
                while time.monotonic()<deadline and not rows.released:pump()
                state['cleanupReleaseConfirmed']=rows.released
            except Exception as error:state['cleanupError']=repr(error)
        if port is not None:port.close()
        if log is not None:log.close()
        state.update(ownHandlesClosed=port is None or not port.is_open,finishedAtLocal=now(),targetReleaseConfirmed=rows.released)
        save()
        if held:
            assert state['ownHandlesClosed'],'Actual UART remains open; retain shared lease'
            replace(lease,lease.replace('**占用中**','**已释放**',1)+'；实际UART已关闭，结果'+state['result']+'；目标释放='+str(rows.released)+'，无确认时不得当作物理idle。')
    print(json.dumps({key:state.get(key)for key in ['result','sourceBytes','ownHandlesClosed','targetReleaseConfirmed','physicalNoiseReductionQualified']}))


if __name__=='__main__':main()
