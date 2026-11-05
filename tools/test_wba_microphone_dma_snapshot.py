from pathlib import Path
import argparse,subprocess,json,hashlib
from verify_wba_spi_nor_adapter import find_vsdevcmd
p=argparse.ArgumentParser(description="Exact production stable-DMA snapshot ownership/PCM model; no physical timing proof")
p.add_argument('--output',type=Path,required=True);p.add_argument('--ce-shared',action='store_true');a=p.parse_args();O=a.output.resolve();O.mkdir(exist_ok=False)
S=Path(__file__).resolve().parents[1];P=S/'platform/stm32wba55_companion_v11';REC=S/'app/companion_pendant/recording'
raw=(P/'microphone_hal.c').read_text();start=raw.index('typedef struct { const uint8_t *bytes; } stable_read_context_t;');end=raw.index('bool comp_v11_microphone_hal_init(',start);helper=raw[start:end]
template=(P/'tests/test_microphone_dma_snapshot.c').read_text();assert template.count('/* @PRODUCTION_STABLE_HALF_HELPER@ */')==1
source=O/'model.c';source.write_text(template.replace('/* @PRODUCTION_STABLE_HALF_HELPER@ */',helper))
args=['cl.exe','/nologo','/TC','/std:c11','/O2','/W4','/WX','/utf-8','/DCOMPANION_WBA_CE_SHARED_CAPTURE='+str(int(a.ce_shared)),'/I'+str(P/'tests/fakes'),'/I'+str(P),'/I'+str(REC),str(source),str(REC/'wba_pdm_capture.c'),'/Fe:'+str(O/'test.exe')]
cmd=O/'compile.cmd';cmd.write_text('@echo off\ncall "'+str(find_vsdevcmd())+'" -arch=amd64 -host_arch=amd64 >nul\nif errorlevel 1 exit /b %errorlevel%\n'+subprocess.list2cmdline(args)+'\n')
r=subprocess.run(['cmd.exe','/d','/c',str(cmd)],cwd=O,capture_output=True,text=True);(O/'compile.txt').write_text(r.stdout+r.stderr);assert r.returncode==0,(r.stdout+r.stderr)[-3000:]
r=subprocess.run([str(O/'test.exe')],cwd=O,capture_output=True,text=True);proof={'result':'PASS_SOFTWARE_ONLY'if r.returncode==0 else'FAIL_SOFTWARE_ONLY','output':r.stdout+r.stderr,'ceShared':a.ce_shared,'productionHelperSha256':hashlib.sha256(helper.encode()).hexdigest(),'physicalBoard':False,'stackQualified':False};(O/'result.json').write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps(proof));assert r.returncode==0
