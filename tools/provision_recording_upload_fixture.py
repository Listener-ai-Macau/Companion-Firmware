"""Install an explicit synthetic2MiB developer recording, without changing app.

Uses the already verified CE/SPI3 development loader via official ST tooling.
Owner permits clearing development recordings. Only V2 catalog banks and this
bounded payload extent are erased; resources, settings, identity allocator,
layout, OTA roots and pairing NVM stay intact. No audio output or real capture.
This preparation period ends before ordinary BLE timing starts.
"""
from datetime import datetime
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import time
import tempfile
import zlib

import serial
from serial.tools import list_ports
from diagnose_wba_uart import parse_frames
from provision_wba_v11 import probe_lock, validate_identity
from cube_programmer_api_session import Session
from migrate_wba_static_ui import open_loader,remove_loader,external_read
from build_recording_upload_fixture import build as build_fixture
from wba_flash_geometry import for_mcu

ROOT = Path(__file__).resolve().parents[1]
BOARD = ROOT.parent / 'docs/board_operations.md'
SN = '004400403532510B31333430'
OWNER = '01a105e0-7fe5-7cc0-b712-46de75337261'
NOR = 0x90000000
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
load = lambda p: json.loads(p.read_text(encoding='utf-8-sig'))


def replace_board_row(before, after):
    """Change one lease row without translating the other chat's line endings."""
    raw = BOARD.read_bytes()
    old, new = before.encode('utf-8'), after.encode('utf-8')
    assert raw.count(old) == 1, 'Exact shared board row unavailable'
    fd, temporary = tempfile.mkstemp(prefix=BOARD.name + '.', dir=BOARD.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(raw.replace(old, new, 1))
            stream.flush()
            os.fsync(stream.fileno())
        assert BOARD.read_bytes() == raw, 'Shared board changed; preserve newer owner'
        os.replace(temporary, BOARD)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)



class BoundedProgrammer:
    """Same official API session as matched CE installation, bounded SRAM1 I/O.

    One reset/halt is confined to sample preparation before any BLE measurement.
    Internal Flash/NVM are read-only. Only the authorized developer catalog and
    this exact fixed audio extent can be programmed. Each loader call <=16KiB.
    """
    def __init__(self,loader,out,guard,catalog,data,size,expected_uid):
        self.loader_path,self.output,self.guard=loader,out,guard
        self.catalog,self.data,self.size=catalog,data,size
        self.expected_uid=expected_uid
        self.session=None;self.loader=None;self.freeze=None;self.number=0
        self.compared_bytes=0;self.reused_bytes=0;self.programmed_bytes=0
        self.reset_attempted=False;self.reset_succeeded=False;self.restore_errors=[]
        self.recovery_events=[]
    def connect(self):
        if self.session:return
        self.session=Session(SN,self.output,self.guard,access_port=1).__enter__()
        self.freeze=int.from_bytes(self.session.read(0xE0044008,4,'debug-freeze-before.bin'),'little')
        self.session.word(0xE0044008,self.freeze|(1<<12))
        assert int.from_bytes(self.session.read(0xE000EDF0,4,'debug-halted.bin'),'little')&(1<<17)
    def recover_loader_session(self,error,operation):
        # An observed official memory-I/O failure is the only recovery trigger.
        # Keep the same exclusive preparation lease and already-read bytes; no
        # product reset, capture, BLE session or full-sample restart is inserted.
        message=str(error)
        if (len(self.recovery_events)>=2 or self.loader is None or
            not any(token in message for token in ('CUBEPROGRAMMER_ERROR_READ_MEM',
                                                    'CUBEPROGRAMMER_ERROR_WRITE_MEM'))):
            raise error
        elf=self.loader_path.read_bytes()
        assert elf[:6]==b'\x7fELF\x01\x01', 'Pinned loader must be ELF32 little-endian'
        offset=struct.unpack_from('<I',elf,28)[0]
        stride,count=struct.unpack_from('<HH',elf,42)
        segments=[struct.unpack_from('<8I',elf,offset+n*stride) for n in range(count)]
        segment=next(x for x in segments if x[0]==1 and x[2]==0x20000004)
        fingerprint=elf[segment[1]:segment[1]+32]
        event={'operation':operation,'error':repr(error),'reset':False,
               'startedAtLocal':datetime.now().isoformat(),'recovered':False}
        self.recovery_events.append(event)
        directory=self.output/f'connection-recovery-{len(self.recovery_events):02d}'
        directory.mkdir(exist_ok=False)
        try:
            self.close() # Native handle must actually close before re-opening.
            self.guard()
            self.session=Session(SN,directory,self.guard,connection_mode=1,access_port=1).__enter__()
            uid=self.session.read(0x0BF90700,12,'uid.bin').hex()
            halted=int.from_bytes(self.session.read(0xE000EDF0,4,'halted.bin'),'little')
            assert uid==self.expected_uid and halted&(1<<17), 'Only the same halted loader context may resume'
            pc=self.session.core_register(15)
            assert 0x20000000 <= (pc&~1) < segment[2]+segment[4], 'Core is outside the pinned SRAM loader'
            assert self.session.read(segment[2],32,'loader-prefix.bin')==fingerprint, 'SRAM loader identity differs'
            self.session.word(0xE0044008,self.freeze|(1<<12))
            self.loader=open_loader(self.session,directory,self.loader_path)
            event.update(recovered=True,uid=uid,dhcsr=f'{halted:08x}',pc=f'{pc:08x}',
                         loaderPrefixSha256=hashlib.sha256(fingerprint).hexdigest())
            print('Recovered official loader session; continue current block',len(self.recovery_events),flush=True)
        except BaseException as recovery_error:
            event['recoveryError']=repr(recovery_error)
            # Unknown UID/running core must not receive a cleanup reset.
            self.close()
            raise
        finally:
            (directory/'result.json').write_text(json.dumps(event,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    def read_external_chunk(self,address,size,name):
        while True:
            try:return self.session.read(address,size,name)
            except RuntimeError as error:self.recover_loader_session(error,'read '+name)
    def prepare_external(self):
        self.connect()
        if self.loader is None:self.loader=open_loader(self.session,self.output,self.loader_path)
    def read(self,address,size,name,external=False):
        if external:
            self.prepare_external()
            # Assemble exactly once across bounded physical reads, including a
            # recovered native API context. No successful chunk is reread and
            # no cached/expected bytes are substituted for actual NOR bytes.
            target=self.output/name
            if target.exists():raise RuntimeError('Refuse to overwrite external read '+name)
            actual=bytearray()
            for at in range(0,size,16384):
                actual.extend(self.read_external_chunk(address+at,min(16384,size-at),name+f'.part-{at:x}'))
            target.write_bytes(actual);return bytes(actual)
        self.connect();return self.session.read(address,size,name)
    def write(self,image,address,external=False):
        value=Path(image).read_bytes();offset=address-NOR
        if not external or offset%4096 or len(value)%4096 or not value:
            raise ValueError('Only aligned explicit developer NOR sectors may be written')
        allowed=any(offset>=base and len(value)<=length and offset-base<=length-len(value)
                    for base,length in [(self.catalog,49152),(self.data,self.size)])
        if not allowed:raise ValueError('Outside developer catalog/fixed sample extent')
        self.prepare_external()
        for at in range(0,len(value),16384):
            self.guard();self.number+=1;p=self.output/f'developer-write-{self.number:04d}-{offset+at:x}.bin'
            block=value[at:at+16384]
            # Resume the same fixed sample after an interrupted preparation.
            # Physical byte equality is required; a prior command/result is
            # never evidence that a block actually reached NOR. Skip only this
            # exact bounded extent. Full framed-file/catalog readback still
            # precedes publishing the recording and any BLE measurement.
            before=self.read(address+at,len(block),f'developer-compare-{self.number:04d}.bin',external=True)
            self.compared_bytes+=len(block)
            if before==block:
                self.reused_bytes+=len(block)
            else:
                assert not p.exists();p.write_bytes(block)
                while True:
                    try:
                        self.session.checked(self.session.api.downloadFile(str(p),address+at,0,1,None),'bounded developer sample NOR write')
                        break
                    except RuntimeError as error:self.recover_loader_session(error,'write '+p.name)
                self.programmed_bytes+=len(block)
            if self.number%16==0:
                print('Developer sample compared blocks',self.number,'reused bytes',self.reused_bytes,
                      'programmed bytes',self.programmed_bytes,flush=True)
    def reset(self):
        if not self.session:return
        errors=[]
        try:
            if self.loader is not None:
                try:remove_loader(self.session,self.loader)
                except BaseException as error:errors.append('remove_loader: '+repr(error))
                finally:self.loader=None
            if self.freeze is not None:
                try:self.session.word(0xE0044008,self.freeze)
                except BaseException as error:errors.append('restore_debug_freeze: '+repr(error))
            # A preceding cleanup error must not suppress the actual official
            # reset attempt and leave our own loader/halt context in place.
            self.reset_attempted=True
            try:self.session.reset();self.reset_succeeded=True
            except BaseException as error:errors.append('software_reset: '+repr(error))
        finally:
            try:self.close()
            except BaseException as error:errors.append('close: '+repr(error))
            self.restore_errors.extend(errors)
        if errors:raise RuntimeError('Loader context restore: '+'; '.join(errors))
    def close(self):
        if self.session:
            try:
                if self.loader is not None:remove_loader(self.session,self.loader);self.loader=None
            finally:self.session.close();self.session=None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixture', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--firmware', default='00010275')
    parser.add_argument('--expected-uid', default='180010000d50335754363720',
                        help='Expected physical MCU, checked independently against fixture, UART and SWD')
    parser.add_argument('--sample',type=Path,help='Fixed original sample directory; permits wrapping identical bytes in a newly initialized live catalog epoch')
    args = parser.parse_args()
    fixture = args.fixture.resolve()
    build = load(fixture / 'result.json')
    uid = args.expected_uid.lower()
    assert re.fullmatch(r'[0-9a-f]{24}',uid) and int(uid,16), 'Explicit physical MCU UID required'
    assert build['deviceUid'] == uid, 'Fixture belongs to another board; no hardware interface opened'
    static = build.get('staticBytes',905216)  # Legacy g2 has this exact extent.
    assert type(static) is int and 8192 <= static < 16777216-0x20000 and static%4096==0
    assert build['result'] == 'SYNTHETIC_PRODUCTION_MEDIA_IMAGE_BUILT_HOST_ONLY'
    assert build['synthetic'] and build['payloadBytes'] == 2097152
    assert (build['catalogBase'], build['dataBase']) == (static + 0x14000, static + 0x20000)
    assert build['dataBase'] + build['reservedBytes'] <= 16777216
    for name in ('catalog.bin', 'audio-pages.bin'):
        assert sha(fixture / name) == build['files'][name]['sha256']
    loader_dir = ROOT / '.cache/ble-mtu-20261011/next/formatter-ce'
    loader_build = load(loader_dir / 'result.json')
    loader = loader_dir / loader_build['loader']
    assert loader_build['mcu'] == 'STM32WBA55CEU6' and loader_build['development_format']
    assert sha(loader) == loader_build['loader_sha256'] == 'bf8a6b7014844a5ed036b6ea1b7b2bd9c96564adc1e58a58a2e660a74a23b641'
    assert load(loader_dir / 'st-parse-result.json')['loader_sha256'] == sha(loader)
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    stage = 'provision-synthetic-2mib-' + datetime.now().strftime('%H%M%S')
    line = (f'- **占用中**：Companion 录音及非屏幕功能（{OWNER}，{datetime.now().isoformat()}，{stage}）。'
            '准备固定2MiB合成上传样本；正常UART确认空闲后，用已校验CE/SPI3外部loader只替换开发V2目录和有限音频extent，'
            '不改内部固件/配对NVM/静态资源/设置/身份分配/OTA根，不外放/开录/云端。准备结束恢复原应用，关闭SWD/UART再释放；BLE计时另阶段。')
    state = dict(result='NOT_STARTED', startedAtLocal=datetime.now().isoformat(),
                 fixture=str(fixture), synthetic=True, firmware=args.firmware,
                 samples=[dict(recordingId=build['recordingId'], totalLength=build['payloadBytes'], sha256=build['payloadSha256'])],
                 deviceRecordingKey=dict(deviceUid=uid, formatEpoch=build['epoch'], sessionId=build['sessionId']),
                 playback=False, captureCommands=0, cloudCalls=0, internalFlashWrites=0,
                 optionByteWrites=0, massErases=0, norWritesStarted=False, officialDebugAccessPort=1,
                 boardInstalled=False, uploadMeasured=False, ownedHandlesClosed=False)
    held = False
    touched = False
    programmer = None

    def owners(text):
        return [s for s in text.split('## 当前占用', 1)[1].split('## 交接方式', 1)[0].splitlines() if '**占用中**' in s]

    def guard():
        assert owners(BOARD.read_text(encoding='utf-8-sig')) == [line], 'Board ownership changed'

    def save():
        (out / 'result.json').write_text(json.dumps(state, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    def uart(name, ready=False):
        ports = [p.device for p in list_ports.comports() if p.serial_number == SN]
        assert len(ports) == 1, 'Fixed V3 UART mapping unavailable'
        port = serial.Serial(port=None, baudrate=115200, timeout=.1, write_timeout=1)
        port.dtr = port.rts = False
        port.port = ports[0]
        value = bytearray()
        guard()
        with port:
            port.write(b'\n?\n')
            port.flush()
            until = time.monotonic() + (30 if ready else 8)
            while time.monotonic() < until:
                value.extend(port.read(8192))
                frames, _ = parse_frames(bytes(value))
                if any(f['sections']['ID']['fw'] == args.firmware and
                       (not ready or f['sections']['STORAGE']['recording_ready'] == 1 or
                        f['sections']['STORAGE']['rec_fault'] != 0) for f in frames):
                    break
        (out / name).write_bytes(value)
        frames, rejected = parse_frames(bytes(value))
        valid = [f for f in frames if f['sections']['ID']['uid'] == uid and f['sections']['ID']['fw'] == args.firmware]
        assert valid, 'Expected normal firmware/UID unavailable; no unchanged retry or power diagnosis'
        return valid[-1]

    try:
        text = BOARD.read_text(encoding='utf-8-sig')
        assert not owners(text), 'Screen chat still owns board; no hardware interface opened'
        replace_board_row('## 当前占用', '## 当前占用\n\n' + line)
        held = True
        before = uart('before-uart.log')
        s = before['sections']
        assert s['AUDIO']['mic_run'] == 0 and s['BLE']['linked'] == 0
        assert s['STORAGE']['recording_ready'] == 1 and s['STORAGE']['rec_fault'] == 0
        assert s['STORAGE']['jedec'] == 'ef6018' and s['STORAGE']['size'] == 16777216
        state['beforeSnapshot'] = before
        save()
        g = for_mcu('STM32WBA55CEU6')
        programmer = BoundedProgrammer(loader,out,guard,build['catalogBase'],build['dataBase'],build['reservedBytes'],uid)
        with probe_lock(SN):
            guard()
            assert validate_identity(programmer.read(0xE0044000, 4, 'device-id.bin'),
                                     programmer.read(0x0BF907A0, 2, 'flash-size.bin'),
                                     programmer.read(0x40022040, 4, 'option-bytes.bin'),
                                     programmer.read(0x0BF90700, 12, 'uid.bin'), g) == uid
            nvm = programmer.read(g.flash_base + g.nvm_offset, g.nvm_bytes, 'private-nvm-before.bin')
            guard()
            touched = True  # External SRAM loader requires restoring normal app afterwards.
            metadata = programmer.read(NOR + static, 131072, 'private-metadata-before.bin', external=True)
            roots = [metadata[at:at+256] for at in (0x14000, 0x1a000)]
            roots = [p for p in roots if p[:4] == b'CSC2' and p[252:256] == bytes(4)
                     and struct.unpack_from('<I', p, 60)[0] == zlib.crc32(p[:60])]
            assert roots and all(p[32:44].hex()==uid for p in roots), 'Actual catalog UID differs'
            live_epochs={struct.unpack_from('<Q',p,24)[0] for p in roots};assert len(live_epochs)==1
            live_epoch=f'{next(iter(live_epochs)):016x}'
            if live_epoch!=build['epoch']:
                assert args.sample,'Freshly formatted namespace: original fixed sample required, no guessed epoch'
                original_sha=build['payloadSha256'];original_id=build['recordingId']
                build_fixture(args.sample.resolve(),out/'live-fixture',live_epoch,uid,static)
                fixture=out/'live-fixture';build=load(fixture/'result.json')
                assert build['payloadSha256']==original_sha and build['recordingId']==original_id and build['payloadBytes']==2097152
                state.update(fixture=str(fixture),previousFormatEpoch=state['deviceRecordingKey']['formatEpoch'])
                state['deviceRecordingKey']['formatEpoch']=live_epoch
            assert max(struct.unpack_from('<I', p, 16)[0] for p in roots) < build['recordingId'], 'Synthetic ID is not fresh'
            assert metadata[0x2000:0x4000] == b'\xff' * 8192, 'Pending OTA state; fixture refused'
            layouts = [metadata[at:at+64] for at in (0x8000, 0x9000)]
            assert any(p[:4] == b'CFL3' and struct.unpack_from('<5I', p, 12) ==
                       (static, static, static + 0x10000, build['dataBase'], 16777216 - build['dataBase'])
                       and struct.unpack_from('<I', p, 60)[0] == zlib.crc32(p[:60]) for p in layouts), 'Actual geometry differs'
            state.update(actualGeometryVerified=True, developerCatalogClearAuthorized=True,
                         beforeMetadataSha256=hashlib.sha256(metadata).hexdigest(),
                         beforeNvmSha256=hashlib.sha256(nvm).hexdigest())
            blank = out / 'blank-developer-catalog.bin'
            blank.write_bytes(b'\xff' * 49152)
            guard()
            state['norWritesStarted'] = True
            save()
            # Clear catalog before overwriting its developer data. A preparation
            # failure cannot advertise the old entries against changed payload.
            programmer.write(blank, NOR + build['catalogBase'], external=True)
            assert programmer.read(NOR + build['catalogBase'], 49152, 'blank-catalog-readback.bin', external=True) == blank.read_bytes()
            guard()
            print('Developer catalog cleared; writing fixed2MiB framed payload', flush=True)
            programmer.write(fixture / 'audio-pages.bin', NOR + build['dataBase'], external=True)
            actual = programmer.read(NOR + build['dataBase'], build['reservedBytes'], 'audio-pages-readback.bin', external=True)
            assert hashlib.sha256(actual).hexdigest() == build['files']['audio-pages.bin']['sha256']
            guard()
            programmer.write(fixture / 'catalog.bin', NOR + build['catalogBase'], external=True)
            assert programmer.read(NOR + build['catalogBase'], 49152, 'catalog-readback.bin', external=True) == (fixture / 'catalog.bin').read_bytes()
            after = programmer.read(NOR + static, 131072, 'private-metadata-after.bin', external=True)
            assert after[:0x14000] == metadata[:0x14000], 'Protected settings/identity/layout/OTA metadata changed'
            assert programmer.read(g.flash_base + g.nvm_offset, g.nvm_bytes, 'private-nvm-after.bin') == nvm
            state.update(boardMediaReadback=True, protectedDynamicMetadataPreserved=True,
                         pairingNvmPreserved=True, staticResourcesWritten=False)
            save()
            guard()
            programmer.reset()
            state['normalAppResetAfterExternalLoader'] = True
            touched = False
        after = uart('after-uart.log', ready=True)
        state['afterSnapshot'] = after
        assert after['sections']['STORAGE']['recording_ready'] == 1 and after['sections']['STORAGE']['rec_fault'] == 0
        state.update(result='SYNTHETIC_2MIB_BOARD_SAMPLE_INSTALLED_READBACK_VERIFIED', boardInstalled=True,
                     afterSnapshot=after)
    except Exception as error:
        state.update(result='SYNTHETIC_BOARD_SAMPLE_NOT_COMPLETED', error=repr(error))
    finally:
        if touched and programmer is not None:
            try:
                guard()
                programmer.reset()
                state['normalAppResetAfterExternalLoader'] = True
            except Exception as error:
                state['normalAppRestoreError'] = repr(error)
        closed=True
        if programmer is not None:
            state['samplePreparationIo']={
                'comparedBytes':programmer.compared_bytes,
                'identicalNorBytesReused':programmer.reused_bytes,
                'programmedAndApiVerifiedBytes':programmer.programmed_bytes,
                'failedWriteMayBePartial':bool(state.get('error')),
                'notBleReceivedBytes':True}
            state['loaderRestore']={'resetAttempted':programmer.reset_attempted,
                'resetSucceeded':programmer.reset_succeeded,'errors':programmer.restore_errors,
                'boundedSameLeaseApiRecovery':programmer.recovery_events}
            if programmer.reset_succeeded:state['normalAppResetAfterExternalLoader']=True
            try:programmer.close()
            except BaseException as error:state['closeError']=repr(error);closed=False
        state.update(ownedHandlesClosed=closed, finishedAtLocal=datetime.now().isoformat())
        save()
        if held and closed:
            text = BOARD.read_text(encoding='utf-8-sig')
            assert line in text
            release = (f'- **已释放**：Companion 录音及非屏幕功能（{OWNER}，{state["finishedAtLocal"]}，{stage}）。'
                       f'{state["result"]}；实际CLI/SWD/UART句柄全部关闭，准备调试上下文结束；'
                       f'仅开发V2目录/有限音频区，固件/资源/设置/身份/配对保持结果见{out / "result.json"}；'
                       '无外放/开录/消费/云端。后续普通BLE收取另占连续时段，不将本次SWD准备算正常重连证据。')
            replace_board_row(line, release)
        print(json.dumps({k: state.get(k) for k in ('result', 'error', 'boardInstalled', 'boardMediaReadback', 'normalAppRestoreError')}, ensure_ascii=False), flush=True)
    return 0 if state['boardInstalled'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
