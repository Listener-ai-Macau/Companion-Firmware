"""Freeze/build current production screen runtime against the preserved UI68.

Only explicitly simulated peripherals are linked. No board access or tests.
"""
from pathlib import Path
from datetime import datetime
import hashlib, json, shutil, subprocess
import wba_runtime_preview as preview

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / '.cache/screen-art-polish-20261011'
OUT = BASE / 'preview-build-p16-final'
SOURCE = BASE / 'source-p16-final'
UI = ROOT / '.cache/flash-external-20261011/source205/.cache/external-ui68'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    SOURCE.mkdir(parents=True, exist_ok=True)
    if (OUT/'build-result.json').exists(): raise RuntimeError('Immutable successful candidate exists')
    sources = [*preview.SOURCES, *preview.EXTRA]
    originals = {p.relative_to(ROOT).as_posix(): sha(p) for p in sources}
    headers = set()
    for directory in preview.INCLUDES:
        for p in directory.glob('*.h'):
            headers.add(p)
    headers.update((ROOT/'app/companion_pendant/update').glob('*.h'))
    for p in [*sources, *sorted(headers)]:
        dest = SOURCE / p.relative_to(ROOT)
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists():
            if sha(dest)!=sha(p): raise RuntimeError('Frozen input changed: '+str(p))
        else: shutil.copy2(p, dest)
    bank = SOURCE / '.cache/external-ui68'
    if not bank.exists(): shutil.copytree(UI, bank)
    includes = [bank, *[SOURCE / p.relative_to(ROOT) for p in preview.INCLUDES]]
    dll = OUT / 'wba-runtime-preview.dll'
    args = ['cl.exe', '/nologo', '/std:c11', '/W4', '/WX', '/wd4127', '/utf-8', '/LD',
        '/DCOMPANION_SCREEN_COMP_REQ_638_SOURCE_PACK=1', '/DCOMPANION_WBA_RESOURCE_PROFILE=1',
        '/DCOMPANION_WBA_BATTERY_LINEAR_ESTIMATE=1', '/DCOMPANION_WBA_UI_EXTERNAL=1',
        '/DCOMPANION_WBA_RECORDING_UI_PACKED=1', '/DCOMP_WBA_NOR_UI_BYTES=905216u',
        '/DCOMP_WBA_NOR_TOTAL_BYTES=16777216u', *(f'/I{p}' for p in includes),
        *(str(SOURCE / p.relative_to(ROOT)) for p in sources), f'/Fe:{dll}']
    command = OUT / 'build.cmd'
    for name in ('build.cmd','build.log'):
        path=OUT/name
        if path.exists(): path.rename(OUT/(name+'.first-missing-update-header'))
    command.write_text('@echo off\ncall "'+str(preview.find_vsdevcmd())+
        '" -arch=amd64 -host_arch=amd64 >nul\nif errorlevel 1 exit /b %errorlevel%\n'+
        subprocess.list2cmdline(args)+'\n', encoding='utf-8')
    result = subprocess.run(['cmd.exe', '/d', '/c', str(command)], cwd=OUT, capture_output=True)
    (OUT / 'build.log').write_bytes(result.stdout+result.stderr)
    if result.returncode:
        raise RuntimeError((result.stdout+result.stderr).decode(errors='replace'))
    frozen = [*sources, *sorted(headers)]
    inputs = [SOURCE / p.relative_to(ROOT) for p in frozen]
    inputs += list(bank.glob('*.h'))
    receipt = dict(result='BUILT_PRODUCTION_SCREEN_RUNTIME_NATIVE_P16_UI68', design='P16',
        createdAtLocal=datetime.now().isoformat(), baseFirmware='1.1.209',
        dllSha256=sha(dll), resourceImageSha256=sha(bank/'ui-partition.bin'),
        sources={str(p): sha(p) for p in inputs}, productionSources=originals,
        productionSourcesChanged=True, originalArtworkRedrawn=False,
        armFirmwareBuilt=False, installed=False, testsRun=False, boardAccess=False,
        audioPlayback=False, physicalAcceptance='NOT_RUN')
    (OUT/'build-result.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:receipt[k] for k in ('result','dllSha256','resourceImageSha256')},ensure_ascii=False))

if __name__ == '__main__': main()
