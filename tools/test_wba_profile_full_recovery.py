"""Current-schema full-arena storage qualification; never opens a device.

Use a delivered frozen firmware source, not an unrelated working-tree HEAD.
Portable Opus/command-level NOR do not qualify ARM timing, acoustics or energy.
"""
from pathlib import Path
import argparse, hashlib, json, subprocess
from test_wba_recording_product import NAMES
from verify_wba_spi_nor_adapter import find_vsdevcmd

ROOT=Path(__file__).resolve().parents[1]

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source',type=Path,required=True)
    ap.add_argument('--source-commit',required=True)
    ap.add_argument('--output',type=Path,required=True)
    a=ap.parse_args();source=a.source.resolve();out=a.output.resolve()
    assert len(a.source_commit)==40 and all(c in '0123456789abcdef'for c in a.source_commit)
    app=source/'app/companion_pendant';rec=app/'recording'
    test=ROOT/'app/companion_pendant/recording/tests/test_wba_profile_full_recovery.c'
    library=ROOT/'.cache/opus-host-fixed/opus.lib'
    sources=[app/'runtime/companion_link.c',*[rec/(n+'.c')for n in NAMES],app/'storage/spi_nor_stm32wba.c']
    # Included test fixtures and headers are compilation inputs too. Check
    # their availability before starting this one native model build.
    fixture=source/'tools/fixtures/wba_nor_suspend_test.c'
    required=[test,library,fixture,*sources,rec/'tests/test_wba_recording_product.c',
              rec/'tests/test_wba_recording_radio.c',rec/'tests/test_wba_recording_recovery.c',
              rec/'tests/test_wba_recording_pipeline.c',app/'runtime/tests/test_companion_link.c']
    missing=[str(p)for p in required if not p.is_file()]
    assert not missing,missing
    out.mkdir(parents=True,exist_ok=False);frozen=out/test.name;frozen.write_bytes(test.read_bytes())
    sdk=out/'sdk';sdk.mkdir()
    (sdk/'ble_types.h').write_text('#include <stdint.h>\ntypedef uint8_t tBleStatus;\n')
    (sdk/'stm32_wpan_common.h').write_text('/* native public-type model */\n')
    includes=[sdk,rec,rec/'tests',*[app/n for n in
        ['runtime','storage','gatt','v1_features','playback','touch','epaper','imu','power']],
        source/'third_party/denzic-platform/audio/embedded/c/include',source/'third_party/opus/include']
    inputs=set(required)|set(app.rglob('*.h'))|set((source/'third_party/denzic-platform/audio/embedded/c/include').rglob('*.h'))
    report=dict(result='PREPARING_MODEL',source=str(source),sourceCommit=a.source_commit,
        modelSha256=hashlib.sha256(frozen.read_bytes()).hexdigest(),hardwareOperations=0,
        firmwareChanged=False,physicalFullDiskQualified=False,physicalTimingQualified=False,
        ceMemoryLayoutQualified=False,realAcousticOrEnergyQualified=False,
        hostCodec='portable lowdelay Opus; not actual ARM CELT execution')
    (out/'inputs.json').write_text(json.dumps({str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in sorted(inputs)},indent=2)+'\n')
    command=['cl.exe','/nologo','/W4','/WX','/wd5287','/std:c11','/TC','/O2','/MD','/utf-8',
        '/D_CRT_SECURE_NO_WARNINGS','/DCOMP_WBA_INTERNAL_FLASH_KIB=0','/DCOMPANION_RECORDING_SEGMENTED_ONLY=1',
        '/DCOMPANION_OPUS16_WBA_LOWDELAY=1','/DCOMPANION_OPUS16_ENCODER_BYTES=65536',
        '/DCOMP_NOR_FIXTURE_BYTES=1048576',*['/I'+str(p)for p in includes],str(frozen),
        *map(str,sources),'/Fe:'+str(out/'test.exe'),'/link',str(library)]
    script=out/'build.cmd';script.write_text('@echo off\ncall "'+str(find_vsdevcmd())+
        '" -arch=amd64 -host_arch=amd64 >nul\nif errorlevel 1 exit /b %errorlevel%\n'+subprocess.list2cmdline(command)+'\n')
    for stage,cmd in [('build',['cmd.exe','/d','/c',str(script)]),('run',[str(out/'test.exe')])]:
        with(out/(stage+'.log')).open('xb')as log:
            process=subprocess.Popen(cmd,cwd=out,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
            try:code=process.wait(timeout=120)
            except subprocess.TimeoutExpired:process.kill();process.wait();code=124
        report.update(stage=stage,exitCode=code,result='FAILED_MODEL_PRESERVED'if code else
            'PASS_SCHEMA5_FULL_STORAGE_SOFTWARE_ONLY'if stage=='run'else'BUILT_MODEL_NOT_RUN')
        (out/'result.json').write_text(json.dumps(report,indent=2)+'\n')
        if code:raise RuntimeError(stage+' failed: '+(out/(stage+'.log')).read_text(errors='replace')[-3000:])
    report['output']=(out/'run.log').read_text(errors='replace')
    (out/'result.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))

if __name__=='__main__':main()
