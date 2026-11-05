"""Run actual OTA admission predicates with a declared mount-ready port."""
from pathlib import Path
import argparse,hashlib,json,os,subprocess
from test_wba_ota_stream_backpressure import function
from verify_wba_spi_nor_adapter import find_vsdevcmd

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
 root=Path(__file__).resolve().parents[1];out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
 src=(root/'platform/stm32wba55_companion_v11/ble/ble_product.c').read_text()
 body='\n'.join(function(src,n)for n in ['bool comp_v11_ble_can_continue_update','bool comp_v11_ble_can_update'])
 code='''#include <stdbool.h>
#include <assert.h>
#include <stdio.h>
static struct {bool recording_ready;struct{bool ready,salvage,update_available;} recording;} app,*product;
static bool mounted=true;
static bool can_update_storage_mount(bool owned){(void)owned;return mounted;}
static bool comp_v11_ble_can_update_storage_mount(void){return mounted;}
static bool comp_wba_recording_product_salvaging(const void *p){(void)p;return app.recording.salvage;}
static bool comp_wba_recording_product_update_available(const void *p){(void)p;return app.recording.update_available;}
'''+body+'''
int main(void){
 product=&app;app.recording_ready=app.recording.ready=true;
 assert(comp_v11_ble_can_update()&&comp_v11_ble_can_continue_update());
 /* A retained old app-ready flag never opens a non-salvage failed owner. */
 app.recording.ready=false;
 assert(!comp_v11_ble_can_update()&&!comp_v11_ble_can_continue_update());
 /* Only the product's separate qualified, isolated update predicate may
  * open salvage.  This fixture models the predicate; the actual ownership
  * checks and exact restored lease are exercised in the NOR product model. */
 app.recording.salvage=true;app.recording.update_available=false;
 assert(!comp_v11_ble_can_update()&&!comp_v11_ble_can_continue_update());
 app.recording.update_available=true;app.recording_ready=false;
 assert(comp_v11_ble_can_update()&&comp_v11_ble_can_continue_update());
 mounted=false;assert(!comp_v11_ble_can_update()&&!comp_v11_ble_can_continue_update());
 mounted=true;app.recording.salvage=false;
 app.recording.ready=true;app.recording_ready=false;
 assert(!comp_v11_ble_can_update()&&!comp_v11_ble_can_continue_update());
 app.recording_ready=true;mounted=false;
 assert(!comp_v11_ble_can_update()&&!comp_v11_ble_can_continue_update());
 product=NULL;
 assert(!comp_v11_ble_can_update()&&!comp_v11_ble_can_continue_update());
 puts("PASS: OTA initial/continuation predicates require normal app readiness or separately qualified salvage; mount/app/null exclusions retained");
}
'''
 (out/'test.c').write_text(code);cmd=['cl.exe','/nologo','/std:c11','/W4','/WX',str(out/'test.c'),f'/Fe:{out/"test.exe"}']
 script=out/'build.cmd';script.write_text('@echo off\ncall "'+str(find_vsdevcmd())+'" -arch=amd64 -host_arch=amd64 >nul\nif errorlevel 1 exit /b %errorlevel%\n'+subprocess.list2cmdline(cmd)+'\n')
 for stage,command in [('build',[os.environ.get('COMSPEC','cmd.exe'),'/d','/c',str(script)]),('run',[str(out/'test.exe')])]:
  run=subprocess.run(command,cwd=out,capture_output=True);(out/(stage+'.log')).write_bytes(run.stdout+run.stderr);assert run.returncode==0,(run.stdout+run.stderr).decode(errors='replace')
 result=dict(result='PASS_QUALIFIED_SALVAGE_OTA_ADMISSION_MODEL',sourceFunctionsSha256=hashlib.sha256(body.encode()).hexdigest(),stdout=(out/'run.log').read_text(),hardwareOperations=0,speedExperiments=0)
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
