#!/usr/bin/env python3
"""Fault-injected product NOR recovery model, no real board or timing claim."""
from pathlib import Path
import hashlib,json,subprocess,sys
from test_wba_recording_product import NAMES
from verify_wba_spi_nor_adapter import find_vsdevcmd
root=Path(__file__).resolve().parents[1];out=root/'.cache/recording-core-20261011'/sys.argv[1]
out.mkdir(parents=True,exist_ok=False);sdk=out/'sdk';sdk.mkdir()
(sdk/'ble_types.h').write_text('#include <stdint.h>\ntypedef uint8_t tBleStatus;\n')
(sdk/'stm32_wpan_common.h').write_text('/* public type model */\n')
app=root/'app/companion_pendant';rec=app/'recording'
sources=[rec/'tests/test_wba_reserve_fault_product.c',app/'runtime/companion_link.c',*[rec/(n+'.c') for n in NAMES],*[rec/('wba_segment_discard_'+n+'.c') for n in ('preview','worker','control','wire')],app/'storage/spi_nor_stm32wba.c']
includes=[sdk,rec,rec/'tests',*[app/n for n in ('runtime','storage','gatt','v1_features','playback','touch','epaper','imu','power')],root/'third_party/denzic-platform/audio/embedded/c/include',root/'third_party/opus/include']
lib=root/'.cache/opus-host-fixed/opus.lib'
args=['cl.exe','/nologo','/W4','/WX','/wd5287','/std:c11','/TC','/O2','/MD','/DCOMP_WBA_INTERNAL_FLASH_KIB=0','/DCOMPANION_RECORDING_SEGMENTED_ONLY=1','/DCOMPANION_OPUS16_WBA_LOWDELAY=1','/DCOMPANION_OPUS16_ENCODER_BYTES=65536','/DCOMP_NOR_FIXTURE_BYTES=1048576','/DTEST_FIXED='+('1' if '--fixed' in sys.argv else '0'),*['/I'+str(p) for p in includes],*map(str,sources),'/Fe:'+str(out/'test.exe'),'/link',str(lib)]
inputs=sources+[rec/'tests/test_wba_recording_product.c',rec/'tests/test_wba_recording_radio.c',rec/'tests/test_wba_recording_recovery.c',rec/'tests/test_wba_recording_pipeline.c',root/'tools/fixtures/wba_nor_suspend_test.c',Path(__file__).resolve()]
(out/'inputs.json').write_text(json.dumps({str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs},indent=2))
cmd=out/'build.cmd';cmd.write_text('@echo off\ncall "'+str(find_vsdevcmd())+'" -arch=amd64 -host_arch=amd64 >nul\nif errorlevel 1 exit /b %errorlevel%\n'+subprocess.list2cmdline(args)+'\n',encoding='ascii')
for name,command in [('compile',['cmd.exe','/d','/c',str(cmd)]),('run',[str(out/'test.exe')])]:
    p=subprocess.run(command,cwd=out,capture_output=True,text=True,timeout=120)
    (out/(name+'.log')).write_text(p.stdout+p.stderr,encoding='utf8')
    if p.returncode:raise RuntimeError(name+': '+str(p.returncode)+'\n'+p.stdout+p.stderr)
print((out/'run.log').read_text(encoding='utf8'))
