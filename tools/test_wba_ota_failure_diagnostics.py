"""Check real OTA failed-ledger output, including an old-source negative control."""
from pathlib import Path
import argparse,hashlib,json,re,subprocess
from build_wba_prehardware import run
from verify_wba_spi_nor_adapter import find_vsdevcmd
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
 p.add_argument('--opus-lib',type=Path,required=True);p.add_argument('--baseline',default='d1d34e2')
 a=p.parse_args();out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
 ble=ROOT/'platform/stm32wba55_companion_v11/ble';ota=ROOT/'third_party/denzic-platform/ota/embedded/c'
 source=ble/'wba_ota_gatt.c';relative=source.relative_to(ROOT).as_posix()
 prior=subprocess.check_output(['git','show',a.baseline+':'+relative],cwd=ROOT).decode('utf-8').replace('\r\n','\n')
 # Only the platform include block is replaced by host ports. The entire
 # report/queue/connection/poll code is otherwise compiled byte-for-byte.
 hardware='#ifdef COMPANION_WBA_BLE_LINKED\n#include "app_common.h"\n#include "board_hal.h"\n#include "ble_product.h"\n#include "update_product.h"\n#include <stdio.h>\n#endif'
 types=re.findall(r'typedef struct \{.*?\} comp_v11_update_\w+_t;', (ble/'update_product.h').read_text(),re.S)
 assert len(types)==2
 fake='''#ifndef FAILURE_DIAGNOSTIC_PORTS_H
#define FAILURE_DIAGNOSTIC_PORTS_H
#include <stdint.h>
#include <stdbool.h>
#include <stdio.h>
'''+ '\n'.join(types)+'''
uint32_t comp_v11_ble_observe_us(void);
bool comp_v11_hal_debug_write(const char *);
void comp_v11_ble_link_budget(uint8_t out[20]);
void comp_v11_ble_rx_shape_trace(uint8_t stage,...);
const comp_v11_update_diagnostics_t *comp_v11_update_product_diagnostics(void);
const comp_v11_update_program_diagnostics_t *comp_v11_update_program_diagnostics(void);
#endif
'''
 (out/'failure_diagnostic_ports.h').write_text(fake)
 includes=[out,ble/'tests/ota_fakes',ble/'tests',ble,ROOT/'app/companion_pendant/update',ota/'include',ROOT/'app/companion_pendant/recording',ROOT/'third_party/opus/include']
 reports={}
 for case,text in [('prior',prior),('fixed',source.read_text())]:
  assert text.count(hardware)==1
  generated=out/(case+'-gatt.c');generated.write_text(text.replace(hardware,'#include "failure_diagnostic_ports.h"'))
  exe=out/(case+'.exe');cmd=['cl.exe','/nologo','/std:c11','/W4','/WX','/wd4295','/O2','/Gy','/MD','/DCOMP_WBA_INTERNAL_FLASH_KIB=512u','/DCOMPANION_WBA_BLE_LINKED=1','/DCOMPANION_WBA_CE_SHARED_CAPTURE=1','/DCOMPANION_OPUS16_ENCODER_BYTES=8744u',*(f'/I{x}'for x in includes),str(generated),str(ble/'tests/test_ota_failure_diagnostics.c'),str(ota/'src/denzic_ota_v1.c'),str(ROOT/'app/companion_pendant/recording/companion_opus16_rt.c'),f'/Fe:{exe}','/link','/OPT:REF',str(a.opus_lib.resolve())]
  script=out/(case+'.cmd');script.write_text('@echo off\ncall "'+str(find_vsdevcmd())+'" -arch=amd64 -host_arch=amd64 >nul\nif errorlevel 1 exit /b %errorlevel%\n'+subprocess.list2cmdline(cmd)+'\n')
  run(['cmd.exe','/d','/c',str(script)],out,out/(case+'-build.log'))
  q=subprocess.run([str(exe)],capture_output=True,text=True,timeout=20)
  (out/(case+'-result.txt')).write_text(q.stdout+q.stderr)
  assert q.returncode==(71 if case=='prior' else 0),(case,q.returncode,q.stdout,q.stderr)
  reports[case]={'exitCode':q.returncode,'output':q.stdout,'sourceSha256':hashlib.sha256(text.encode()).hexdigest()}
 result={'result':'PASS_NATIVE_PRODUCTION_FAILURE_DIAGNOSTICS','baseline':a.baseline,'cases':reports,'hardwareOrRateQualified':False,'sourceSha256':{str(x.relative_to(ROOT)):hashlib.sha256(x.read_bytes()).hexdigest()for x in [source,ble/'tests/test_ota_failure_diagnostics.c',Path(__file__)]}}
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
