#!/usr/bin/env python3
"""Check the real C decoder and renderer against the unchanged UI67 pixels."""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess

from compact_wba_recording_ui import generate
from render_wba_menu_review import SOURCES, INCLUDES
from verify_wba_spi_nor_adapter import find_vsdevcmd

ROOT = Path(__file__).resolve().parents[1]
RENDERER = ROOT / 'app/companion_pendant/runtime/companion_renderer.c'


def build(output, sources, includes, defines):
    devcmd = find_vsdevcmd()
    if not devcmd:
        raise RuntimeError('Visual Studio C++ Build Tools not found')
    exe = output / 'verify.exe'
    arguments = ['cl.exe', '/nologo', '/std:c11', '/W4', '/WX', '/utf-8',
                 '/D_CRT_SECURE_NO_WARNINGS', *('/D' + d for d in defines),
                 *('/I' + str(p) for p in includes), *(str(p) for p in sources),
                 '/Fe:' + str(exe)]
    script = output / 'build.cmd'
    script.write_text(f'@echo off\ncall "{devcmd}" -arch=amd64 -host_arch=amd64 >nul\n'
                      'if errorlevel 1 exit /b %errorlevel%\n' +
                      subprocess.list2cmdline(arguments) + '\n', encoding='utf-8')
    process = subprocess.run(['cmd.exe', '/d', '/c', str(script)], cwd=output,
                             text=True, capture_output=True)
    (output / 'build.log').write_text(process.stdout + process.stderr, encoding='utf-8')
    if process.returncode:
        raise RuntimeError(f'C build failed; see {output / "build.log"}')
    return exe


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--resources', type=Path, required=True)
    parser.add_argument('--baseline-renderer', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    output, resources = args.out.resolve(), args.resources.resolve()
    if output.exists() and any(output.iterdir()):
        raise RuntimeError('Refuse to replace an existing result')
    output.mkdir(parents=True, exist_ok=True)
    packed = output / 'atlases'
    report = generate(resources, packed)
    glyph_dir = output / 'decoder'
    glyph_dir.mkdir()
    exporter = glyph_dir / 'decode.c'
    lines = ['#include <stdio.h>', '#include "companion_bitmap_stream.h"',
             '#include "companion_wba_recording_ui_packed.h"', 'int main(void) {']
    for atlas in report['atlases']:
        name, width = atlas['name'], atlas['glyphBytes']
        lines.append(f'for (unsigned l=0;l<sizeof({name})/sizeof({name}[0]);++l) {{')
        lines.append(f'for (unsigned i=0;i<sizeof({name}[0])/sizeof({name}[0][0]);++i) {{')
        lines.append(f'comp_bitmap_stream_t stream={{{name}[l][i],0,0}};')
        lines.append(f'for (unsigned b=0;b<{width}u;++b) if (putchar(comp_bitmap_stream_byte(&stream))==EOF) return 1;')
        lines.append('}}')
    lines.append('return 0; }')
    exporter.write_text('\n'.join(lines), encoding='utf-8')
    # Windows stdout in text mode would translate LF bytes. Decode to a file
    # with a binary C stream rather than let that translation alter the atlas.
    text = exporter.read_text(encoding='utf-8').replace('#include <stdio.h>',
          '#include <stdio.h>\n#include <fcntl.h>\n#include <io.h>').replace(
          'int main(void) {', 'int main(void) { if (_setmode(_fileno(stdout),_O_BINARY)==-1) return 1;')
    exporter.write_text(text, encoding='utf-8')
    exe = build(glyph_dir, [exporter], [packed, ROOT / 'app/companion_pendant/runtime'],
                ['COMPANION_WBA_RECORDING_UI_PACKED=1'])
    decoded = subprocess.run([str(exe)], check=True, capture_output=True).stdout
    digest = hashlib.sha256(decoded).hexdigest()
    if len(decoded) != report['originalBytes'] or digest != report['originalConcatSha256']:
        raise RuntimeError('The production C stream changed a bitmap byte')
    common = ['COMPANION_SCREEN_COMP_REQ_638_SOURCE_PACK=1', 'COMPANION_WBA_RESOURCE_PROFILE=1',
              f'COMP_WBA_NOR_UI_BYTES={(resources / "ui-partition.bin").stat().st_size}u',
              'COMP_WBA_NOR_TOTAL_BYTES=16777216u']
    frames = []
    for mode in ('baseline', 'packed'):
        directory = output / mode
        directory.mkdir()
        raw = directory / 'raw'
        raw.mkdir()
        sources = [args.baseline_renderer.resolve() if p == RENDERER and mode == 'baseline' else p for p in SOURCES]
        sources.append(ROOT / 'app/companion_pendant/runtime/companion_pet_face.c')
        includes = ([packed] if mode == 'packed' else []) + [resources, *INCLUDES]
        executable = build(directory, sources, includes, common +
                           (['COMPANION_WBA_RECORDING_UI_PACKED=1'] if mode == 'packed' else []))
        process = subprocess.run([str(executable), str(resources / 'ui-partition.bin'), str(raw)],
                                 text=True, capture_output=True)
        (directory / 'render.log').write_text(process.stdout + process.stderr, encoding='utf-8')
        process.check_returncode()
        if 'PASS_NATIVE_WBA_MENU_REVIEW' not in process.stdout:
            raise RuntimeError('Renderer did not finish')
        frames.append({p.name: p.read_bytes() for p in raw.glob('*.bin')})
    if not frames[0] or frames[0].keys() != frames[1].keys():
        raise RuntimeError('Renderer fixture set changed')
    changed = [name for name in frames[0] if frames[0][name] != frames[1][name]]
    result = dict(schema='companion.recording-ui.lossless-verify.v1',
                  cDecodedBytes=len(decoded), cDecodedSha256=digest,
                  glyphCount=sum(a['glyphs'] for a in report['atlases']),
                  framesCompared=len(frames[0]), changedFrames=changed,
                  bitmapByteExact=not changed, resourceBankChanged=False,
                  rawAtlasBytes=report['originalBytes'], packedDataBytesM33=report['packedBytes'])
    (output / 'result.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    if changed:
        raise RuntimeError(f'The production renderer changed {len(changed)} frames')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
