"""Capture one finite frozen WBA display scene over the physical UART.

Requires firmware exposing EPD HOLD/RUN/SNAP/TRACE/STATUS. No SWD, reset,
flash, extra refresh, recording command or controller register read is used.
Output is controller-order bytes plus a native-order image and raw transcript.
"""
from pathlib import Path
import argparse,hashlib,json,re,time,zlib


def fields(line):
    return dict(re.findall(r'([a-z][a-z0-9_]*)=([^\s]+)',line))


def parse_scene(raw):
    begin=None;rows={};end=None
    for line in raw.decode('ascii',errors='replace').splitlines():
        if line.startswith('EPDDBG FRAME BEGIN '):
            begin=fields(line);rows={};end=None
        elif begin and line.startswith('EPDDBG ROW '):
            row=fields(line)
            if row.get('id')!=begin.get('id'):continue
            y=int(row['y']);data=bytes.fromhex(row['data'])
            if not 0<=y<200 or len(data)!=25 or y in rows:
                raise ValueError('Invalid/duplicate scene row')
            rows[y]=data
        elif begin and line.startswith('EPDDBG FRAME ABORT'):
            raise RuntimeError('Device aborted changing/busy scene: '+line)
        elif begin and line.startswith('EPDDBG FRAME END '):
            end=fields(line)
            if end.get('id')!=begin.get('id'):continue
            break
    if not begin or not end or len(rows)!=200:
        raise ValueError(f'Incomplete scene ({len(rows)}/200 rows)')
    assert begin['width']==begin['height']=='200' and begin['stride']=='25'
    assert begin['order']=='controller_flip_y' and end['rows']=='200'
    image=b''.join(rows[y] for y in range(200))
    crc=f'{zlib.crc32(image):08x}'
    if crc!=begin['crc32'].lower() or crc!=end['crc32'].lower():
        raise ValueError('Scene CRC mismatch; no image accepted')
    return image,begin


def export_scene(out,raw,expected_fw):
    image,meta=parse_scene(raw)
    if expected_fw and meta['fw'].lower()!=expected_fw.lower():
        raise ValueError('Unexpected scene firmware')
    (out/'controller-frame.bin').write_bytes(image)
    # Native UI y is the inverse of the accepted controller row mapping.
    native=b''.join(image[y*25:(y+1)*25] for y in reversed(range(200)))
    # Firmware white=1, PBM black=1. Only reconstruct the actual raw bitmap.
    (out/'native-frame.pbm').write_bytes(b'P4\n200 200\n'+bytes(x^255 for x in native))
    from PIL import Image
    Image.open(out/'native-frame.pbm').save(out/'native-frame.png')
    return dict(result='EXACT_FROZEN_UART_FRAME_CAPTURED',frame=meta,
                frameSha256=hashlib.sha256(image).hexdigest(),
                inkPixels=sum((x^255).bit_count() for x in image),
                physicalGlassQuality='NOT_EVALUATED',screenFixed=False)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    source=parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--port')
    source.add_argument('--input-log',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--expected-fw',required=True)
    parser.add_argument('--expected-uid',default='180010000d50335754363720')
    parser.add_argument('--hold-seconds',type=float,default=0,
                        help='Leave the frozen scene visible after capture (0..20s), then RUN')
    parser.add_argument('--observe-seconds',type=float,default=8,
                        help='Retain resumed trace for0..20s; not a visual acceptance')
    parser.add_argument('--single-query',action='store_true',
                        help='Query identity once; after the scene use passive trace only')
    args=parser.parse_args()
    if not 0<=args.hold_seconds<=20 or not 0<=args.observe_seconds<=20:
        parser.error('hold/observe seconds must be0..20')
    if not re.fullmatch('[0-9a-fA-F]{8}',args.expected_fw):parser.error('Bad expected firmware')
    out=args.output.resolve()
    if out.exists() and any(out.iterdir()):parser.error('Preserve previous evidence; output must be new/empty')
    out.mkdir(parents=True,exist_ok=True)
    raw=bytearray();port=None;held=False;commands=[]
    result=dict(result='PENDING',flashed=False,resetsRequested=False,
                controllerRegisterReads=False,fullRefreshRequested=False,
                recordingStarted=False,physicalGlassQuality='NOT_EVALUATED')
    try:
        if args.input_log:
            raw.extend(args.input_log.read_bytes())
            result.update(export_scene(out,raw,args.expected_fw))
        else:
            import serial
            from diagnose_wba_uart import parse_frames
            port=serial.Serial(port=None,baudrate=115200,timeout=.1,write_timeout=1)
            port.dtr=False;port.rts=False;port.port=args.port;port.open()
            with (out/'uart.log').open('wb') as log:
                def read_until(predicate,seconds):
                    start=time.monotonic();offset=len(raw)
                    while time.monotonic()-start<seconds:
                        chunk=port.read(min(max(port.in_waiting,1),4096))
                        if chunk:
                            raw.extend(chunk);log.write(chunk);log.flush()
                            if len(raw)>1024*1024:raise ValueError('Scene transcript exceeds bound')
                        if predicate(bytes(raw[offset:])):return bytes(raw[offset:])
                    raise TimeoutError('Scene UART response timed out')

                def send(line):
                    data=(line+'\n').encode('ascii')
                    result['lastCommand']=line
                    commands.append(dict(command=line,monotonic=time.monotonic(),bytes=len(data)))
                    # LPUART has an8-byte RX FIFO and foreground parsing.
                    # Pace service lines; do not paste an11-byte command
                    # into a UART still finishing the previous TX reply.
                    for byte in data:
                        if port.write(bytes([byte]))!=1:raise IOError('Incomplete UART command write')
                        time.sleep(.003)
                    port.flush()

                def drain(seconds):
                    start=time.monotonic()
                    while time.monotonic()-start<seconds:
                        chunk=port.read(min(max(port.in_waiting,1),4096))
                        if chunk:raw.extend(chunk);log.write(chunk);log.flush()

                send('?')
                identity=read_until(lambda b:bool(parse_frames(b)[0]),8)
                snapshots,_=parse_frames(identity);s=snapshots[-1]['sections']
                if s['ID']['fw']!=args.expected_fw.lower() or s['ID']['uid']!=args.expected_uid:
                    raise ValueError('Physical board identity mismatch')
                if (s['AUDIO']['mic_run'] or s['BLE']['linked'] or
                    s['STORAGE']['rec_state'] not in (1,6) or s['STORAGE']['rec_fault'] or
                    int(s['POWER']['sleep_block'],16)&sum(1<<bit for bit in (0,1,8,11,12,13,14))):
                    raise RuntimeError('Live product operation; scene hold refused')
                # Full DIAG1 has cached lines after END. Drain them before
                # commands so prior UART status cannot satisfy a new reply.
                drain(.6)
                send('EPD TRACE')
                read_until(lambda b:bool(re.search(rb'(?m)^EPDDBG TRACE [^\r\n]*\r?\n',b)),3)
                hold_started=time.monotonic()
                send('EPD HOLD');held=True
                read_until(lambda b:bool(re.search(rb'(?m)^EPDDBG HOLD ready=1 [^\r\n]*\r?\n',b)),7)
                send('EPD STATUS')
                read_until(lambda b:bool(re.search(rb'(?m)^EPDDBG STATUS [^\r\n]*\r?\n',b)),3)
                send('EPD SNAP')
                read_until(lambda b:bool(re.search(rb'(?m)^EPDDBG FRAME (?:END|ABORT)[^\r\n]*\r?\n',b)),8)
                result.update(export_scene(out,raw,args.expected_fw))
                hold_remaining=min(args.hold_seconds,max(0,28-(time.monotonic()-hold_started)))
                print(json.dumps({'result':result['result'],'frame':result['frame'],
                                  'frozenForOwnerSeconds':round(hold_remaining,1)}),flush=True)
                if hold_remaining:
                    until=time.monotonic()+hold_remaining
                    while time.monotonic()<until:
                        chunk=port.read(min(max(port.in_waiting,1),4096))
                        if chunk:raw.extend(chunk);log.write(chunk);log.flush()
                send('EPD RUN');held=False
                read_until(lambda b:bool(re.search(rb'(?m)^EPDDBG RUN\r?\n',b)),3)
                start=time.monotonic()
                while time.monotonic()-start<args.observe_seconds:
                    chunk=port.read(min(max(port.in_waiting,1),4096))
                    if chunk:raw.extend(chunk);log.write(chunk);log.flush()
                if not args.single_query:
                    send('?')
                    read_until(lambda b:bool(parse_frames(b)[0]),8)
                result['resumedTrace']=re.findall(r'(?m)^PANEL(?:15|19) [^\r\n]+',raw.decode('ascii',errors='replace'))
                result['resumeCommandAcknowledged']=True
    except Exception as exc:
        result.update(result='FAIL',error=str(exc))
        print(json.dumps({'result':'FAIL','error':str(exc)}),flush=True)
    finally:
        if port and port.is_open:
            if held:
                try:port.write(b'\nEPD RUN\n');port.flush()
                except Exception:pass
            port.close()
        result['portClosed']=port is None or not port.is_open
        result['hostCommands']=commands
        (out/'uart.log').write_bytes(raw)
        (out/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    return 0 if result['result']=='EXACT_FROZEN_UART_FRAME_CAPTURED' else 1


if __name__=='__main__':raise SystemExit(main())
