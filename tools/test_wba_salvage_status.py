"""Exercise actual BLE status bit composition, without a device or BLE stack."""
from pathlib import Path
import argparse, hashlib, json, subprocess
from test_wba_ota_stream_backpressure import function
from verify_wba_spi_nor_adapter import find_vsdevcmd

root=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
ble=(root/'platform/stm32wba55_companion_v11/ble/ble_product.c').read_text()
header=(root/'app/companion_pendant/gatt/companion_gatt_stm32wb.h').read_text()
assert 'COMPANION_GATT_FAULT_RECORDING_TAIL_UNRESOLVED = 1u << 11' in header
body=function(ble,'static uint16_t device_fault_bitmap')
code='''#include <stdbool.h>\n#include <stdint.h>\n#include <assert.h>\n#include <stdio.h>\n
enum {COMPANION_GATT_FAULT_RECORDING_TAIL_UNRESOLVED=1u<<11};
typedef struct {bool salvage,retained;} recording_t;
typedef struct {uint32_t faults;} board_t;
typedef struct {board_t *board;recording_t recording;} comp_v11_product_app_t;
bool comp_wba_recording_product_salvaging(const recording_t *r){return r->salvage;}
bool comp_wba_recording_product_tail_retained(const recording_t *r){return r->retained;}
'''+body+'''
int main(void){
 board_t board={0};comp_v11_product_app_t app={&board,{false,false}};
 assert(device_fault_bitmap(&app)==0u);
 board.faults=0x102u;assert(device_fault_bitmap(&app)==0x102u);
 app.recording.salvage=true;app.recording.retained=true;assert(device_fault_bitmap(&app)==0x902u);
 /* A remount makes operations unavailable, but does not repair old audio. */
 app.recording.salvage=false;assert(device_fault_bitmap(&app)==0x902u);
 app.recording.retained=false;assert(device_fault_bitmap(&app)==0x102u);
 puts("PASS actual BLE status bitmap preserves other faults and identifies unresolved tail; software only");
}
'''
(out/'test.c').write_text(code,encoding='utf-8')
args=['cl.exe','/nologo','/TC','/std:c11','/O2','/W4','/WX',str(out/'test.c'),'/Fe:'+str(out/'test.exe')]
(out/'build.cmd').write_text('@echo off\ncall "'+str(find_vsdevcmd())+'" -arch=amd64 -host_arch=amd64 >nul\nif errorlevel 1 exit /b %errorlevel%\n'+subprocess.list2cmdline(args)+'\n')
for name,command in [('build',['cmd.exe','/d','/c',str(out/'build.cmd')]),('run',[str(out/'test.exe')])]:
 result=subprocess.run(command,cwd=out,capture_output=True);(out/(name+'.log')).write_bytes(result.stdout+result.stderr)
 if result.returncode:raise SystemExit(result.returncode)
print(json.dumps(dict(result='PASS_SALVAGE_STATUS_MODEL',functionSha256=hashlib.sha256(body.encode()).hexdigest(),hardwareOperations=0)))
