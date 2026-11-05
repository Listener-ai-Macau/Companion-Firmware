"""Exercise exact production OTA ownership and controller admission together."""
from pathlib import Path
import argparse,hashlib,json,subprocess
from build_wba_prehardware import run
from verify_wba_spi_nor_adapter import find_vsdevcmd
from test_wba_ota_stream_backpressure import function
ROOT=Path(__file__).resolve().parents[1]

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--baseline-ref',required=True);p.add_argument('--baseline-repo',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 out=a.output.resolve();out.mkdir(exist_ok=False,parents=True)
 rel='platform/stm32wba55_companion_v11/ble';ble=ROOT/rel
 original=subprocess.check_output(['git','show',a.baseline_ref+':'+rel+'/ble_product.c'],cwd=a.baseline_repo).decode().replace('\r\n','\n')
 current=(ble/'ble_product.c').read_text();update=(ble/'update_product.c').read_text();host=(ble/'app_ble.c').read_text()
 rows=[]
 for label,source,expected in [('baseline',original,0),('fixed',current,1)]:
  dest=out/label;dest.mkdir()
  body='\n'.join(function(source,s) for s in ['static bool can_update_storage_mount','bool comp_v11_ble_can_update_storage_mount','bool comp_v11_ble_can_continue_update','bool comp_v11_ble_can_update','static bool stack_writes_allowed'])
  # Alias two file-static names only: these are distinct objects in the real TUs.
  body+='\n#define ready update_ready\n#define transfer ota_transfer\n'
  body+='\n'.join(function(update,s) for s in ['bool comp_v11_update_product_owns_erase','bool comp_v11_update_product_busy','bool comp_v11_update_product_reboot_pending','static bool idle','static bool powered_idle','bool comp_v11_update_product_bulk_transfer'])
  body+='\n#undef ready\n#undef transfer\n'
  start=source.index('const bool update_busy=comp_v11_update_product_busy();');end=source.index('!product->board->microphone.running&&(!update_busy||update_idle));',start)+len('!product->board->microphone.running&&(!update_busy||update_idle));')
  body+='\nstatic void production_profile_turn(void){\n const bool interval_hint=false;const bool writes_allowed=stack_writes_allowed();\n'+source[start:end]+'\n}\n'
  (dest/'production_owner_gate.inc').write_text(body)
  (dest/'production_bulk_profile.inc').write_text(function(host,'void comp_v11_ble_bulk_profile')+'\n')
  fixture=ble/'tests/test_ota_bulk_owner.c';exe=dest/'ota-bulk-owner.exe'
  cmd=['cl.exe','/nologo','/TC','/std:c11','/Zc:preprocessor','/O2','/W4','/WX',f'/DEXPECT_OWNER_PROFILE={expected}',f'/I{dest}',str(fixture),f'/Fe:{exe}']
  script=dest/'build.cmd';script.write_text('@echo off\ncall "'+str(find_vsdevcmd())+'" -arch=amd64 -host_arch=amd64 >nul\nif errorlevel 1 exit /b %errorlevel%\n'+subprocess.list2cmdline(cmd)+'\n')
  log=dest/'build.log';run(['cmd.exe','/d','/c',str(script)],dest,log);output=run([str(exe)],dest,log)
  rows.append(dict(label=label,expectedOwnedEraseConfigCalls=expected,output=output,extractedSha256=hashlib.sha256(body.encode()).hexdigest()))
 report=dict(result='PRODUCTION_OTA_CONTROLLER_INITIAL_GATE_REPRODUCED_AND_CONTINUATION_FIXED',baseline=a.baseline_ref,rows=rows,hardwareOperations=0,installed=False,speedMeasured=False)
 (out/'result.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
