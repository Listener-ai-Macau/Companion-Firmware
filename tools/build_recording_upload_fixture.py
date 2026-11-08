"""Wrap the fixed generated2MiB sample using production catalog/audio functions.

No board access. The explicit development fixture replaces only its catalog
banks and bounded audio extent. It is never embedded into production resources.
"""
from pathlib import Path
import argparse
import hashlib
import json
import re
import subprocess
from verify_wba_spi_nor_adapter import find_vsdevcmd

ROOT = Path(__file__).resolve().parents[1]


def build(sample, out, epoch='1f59b27acf4936e1',
          device_uid='180010000d50335754363720', static_bytes=905216):
    # This fixture is keyed to a physical board and its compiled resource bank.
    # Keep the payload unchanged when moving the experiment to a repaired board.
    if not re.fullmatch(r'[0-9a-fA-F]{24}', device_uid) or int(device_uid, 16) == 0:
        raise ValueError('An explicit nonzero 12-byte MCU UID is required')
    device_uid = device_uid.lower()
    if (type(static_bytes) is not int or static_bytes % 4096 or
            not 8192 <= static_bytes <= 16*1024*1024-0x20000-0x220000):
        raise ValueError('Static bank must be sector aligned and leave room for the 2MiB fixture')
    info = json.loads((sample / 'sample.json').read_text(encoding='utf-8-sig'))
    payload = sample / info['payload']['path']
    assert info['synthetic'] and info['payload']['bytes'] == 2097152
    assert hashlib.sha256(payload.read_bytes()).hexdigest() == info['payload']['sha256']
    if len(epoch)!=16 or not 0<int(epoch,16)<=0xffffffffffffffff:
        raise ValueError('Explicit live catalog epoch must be16 hexadecimal digits and nonzero')
    out.mkdir(parents=True, exist_ok=False)
    rec = ROOT / 'app/companion_pendant/recording'
    sources = [ROOT / 'tools/fixtures/recording_upload_fixture.c',
               rec / 'companion_segment_audio.c', rec / 'companion_segment_catalog.c', rec / 'companion_range_receipt.c', rec / 'companion_range_reclaim.c']
    includes = [rec, ROOT / 'app/companion_pendant/update']
    exe = out / 'fixture.exe'
    args = ['cl.exe', '/nologo', '/TC', '/std:c11', '/O2', '/W4', '/WX', '/MD',
            '/D_CRT_SECURE_NO_WARNINGS', f'/DCOMP_WBA_NOR_UI_BYTES={static_bytes}u',
            *['/I' + str(p) for p in includes], *[str(p) for p in sources], '/Fe:' + str(exe)]
    script = out / 'compile.cmd'
    script.write_text('@echo off\ncall "' + str(find_vsdevcmd()) + '" -arch=amd64 -host_arch=amd64 >nul\n'
                      'if errorlevel 1 exit /b %errorlevel%\n' + subprocess.list2cmdline(args) + '\n', encoding='utf-8')
    p = subprocess.run(['cmd.exe', '/d', '/c', str(script)], cwd=out, capture_output=True, text=True)
    (out / 'compile.log').write_text(p.stdout + p.stderr, encoding='utf-8')
    if p.returncode:
        raise RuntimeError(p.stdout + p.stderr)
    command = [str(exe), str(payload), str(out / 'catalog.bin'), str(out / 'audio-pages.bin'),
               epoch, device_uid, '65536', '7fff202610120001']
    p = subprocess.run(command, cwd=out, capture_output=True, text=True)
    (out / 'fixture.log').write_text(p.stdout + p.stderr, encoding='utf-8')
    if p.returncode:
        raise RuntimeError(p.stdout + p.stderr)
    result = json.loads(p.stdout)
    assert (result['catalogBase'], result['dataBase']) == (static_bytes+0x14000, static_bytes+0x20000)
    assert result['dataBase']+result['reservedBytes'] <= 16*1024*1024
    result.update(epoch=epoch, deviceUid=device_uid, staticBytes=static_bytes,
                  sessionId='7fff202610120001', synthetic=True, boardInstalled=False,
                  payloadSha256=info['payload']['sha256'],
                  sources={p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
                  files={name: dict(bytes=(out / name).stat().st_size,
                                    sha256=hashlib.sha256((out / name).read_bytes()).hexdigest())
                         for name in ('catalog.bin', 'audio-pages.bin', 'fixture.exe')})
    (out / 'result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({key: result[key] for key in ('result', 'recordingId', 'payloadBytes', 'reservedBytes', 'catalogBase', 'dataBase')}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sample', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--epoch',default='1f59b27acf4936e1',help='Live catalog namespace after an authorized development format; does not change fixed file/recording ID/SHA')
    parser.add_argument('--device-uid', default='180010000d50335754363720',
                        help='Actual UART/SWD MCU UID; never substitute the old board identity')
    parser.add_argument('--static-bytes', type=int, default=905216,
                        help='Exact compiled resource bank extent, not the old fixture geometry')
    args = parser.parse_args()
    build(args.sample.resolve(), args.output.resolve(), args.epoch, args.device_uid, args.static_bytes)
