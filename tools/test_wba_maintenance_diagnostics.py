"""Compile the actual read-only snapshot and existing CRM1 framing; no device I/O."""
from pathlib import Path
import hashlib,json,subprocess,sys
from verify_wba_spi_nor_adapter import find_vsdevcmd
from test_wba_ota_stream_backpressure import function
ROOT=Path(__file__).resolve().parents[1]
out=Path(sys.argv[1]).resolve();out.mkdir(parents=True,exist_ok=False)
source=ROOT/'platform/stm32wba55_companion_v11/ble/app_ble.c';text=source.read_text()
(out/'snapshot.inc').write_text(function(text,'static bool pairing_open')+'\n'+function(text,'static void pairing_result')+'\n'+function(text,'void comp_v11_ble_maintenance_diagnostics')+'\n')
fixture=r'''
#include "maintenance_protocol.h"
#include <assert.h>
#include <stdio.h>
static uint32_t tick,pairing_until;
static uint32_t HAL_GetTick(void){return tick;}
static bool radio_enabled,advertising,connection_secured,connection_allowed;
static uint16_t connection;
static uint8_t last_error;
static struct {uint32_t bond_lost_events,rebond_attempts;uint8_t pairing_status,pairing_reason,pairing_failure_status,pairing_failure_reason;} security_stats;
_Static_assert(sizeof(security_stats)==12u,"unchanged security allocation");
static struct {uint8_t unsecured_reason,unsecured_allowed,encryption_status;} link_history;
static struct {uint16_t seen,failed;} initial_link_observation;
#include "snapshot.inc"
int main(void){
 uint8_t p[32];memset(p,0xa5,sizeof(p));tick=1000u;pairing_until=121000u;
 radio_enabled=advertising=connection_allowed=connection_secured=true;connection=3u;last_error=7u;
 security_stats.pairing_failure_status=security_stats.pairing_failure_reason=0xffu;
 pairing_result(0u,0u);
 security_stats.bond_lost_events=0xffffffffu;security_stats.rebond_attempts=70000u;
 link_history.unsecured_reason=5u;link_history.unsecured_allowed=1u;link_history.encryption_status=6u;
 initial_link_observation.seen=63u;initial_link_observation.failed=2u;
 comp_v11_ble_maintenance_diagnostics(p);
 assert(p[6]==191u&&p[7]==7u&&p[12]==0u&&p[13]==0u&&p[14]==5u&&p[15]==6u);
 pairing_result(2u,9u);pairing_result(0u,0u);
 comp_v11_ble_maintenance_diagnostics(p);
 assert(p[6]==255u&&p[12]==2u&&p[13]==9u);
 assert(security_stats.pairing_status==0u&&security_stats.pairing_reason==0u);
 pairing_result(1u,8u);comp_v11_ble_maintenance_diagnostics(p);
 assert(p[12]==1u&&p[13]==8u);
 assert(comp_maint_get32(p+16u)==120000u&&comp_maint_get32(p+20u)==(63u|(2u<<16u)));
 assert(comp_maint_get32(p+24u)==0xffffffffu&&pairing_until==121000u&&security_stats.rebond_attempts==70000u);
 for(unsigned i=0u;i<32u;++i)if(i<6u||(i>=8u&&i<12u)||i>=28u)assert(p[i]==0xa5u);
 tick=121000u;comp_v11_ble_maintenance_diagnostics(p);assert(!(p[6]&4u)&&!comp_maint_get32(p+16u));
 tick=0xfffffffau;pairing_until=4u;comp_v11_ble_maintenance_diagnostics(p);assert((p[6]&4u)&&comp_maint_get32(p+16u)==10u);
 pairing_until=0u;comp_v11_ble_maintenance_diagnostics(p);assert(!(p[6]&4u)&&!comp_maint_get32(p+16u));
 puts("PASS exact production cached BLE diagnostic snapshot: deadline/wrap, cause/count encoding, saturation, no mutation or header/nonce writes; software only");return 0;
}'''
(out/'snapshot.c').write_text(fixture)
logs=[]
for label,test in [('framing',ROOT/'platform/stm32wba55_companion_v11/tests/test_maintenance_protocol.c'),('snapshot',out/'snapshot.c')]:
 exe=out/(label+'.exe');cmd=['cl.exe','/nologo','/W4','/WX','/std:c11','/TC','/I'+str(ROOT/'platform/stm32wba55_companion_v11/ble'),'/I'+str(ROOT/'app/companion_pendant/storage'),str(test),'/Fe:'+str(exe)]
 script=out/(label+'.cmd');script.write_text('@echo off\ncall "'+str(find_vsdevcmd())+'" -arch=amd64 -host_arch=amd64 >nul\nif errorlevel 1 exit /b %errorlevel%\n'+subprocess.list2cmdline(cmd)+'\n')
 for stage,args in [('compile',['cmd.exe','/d','/c',str(script)]),('run',[str(exe)])]:
  p=subprocess.run(args,cwd=out,capture_output=True,text=True,encoding='utf-8',errors='replace',creationflags=subprocess.CREATE_NO_WINDOW)
  log=p.stdout+p.stderr;(out/(label+'-'+stage+'.log')).write_text(log,encoding='utf-8');assert p.returncode==0,log
  if stage=='run':logs.append(log)
report={'result':'PASS_CACHED_DIAGNOSTIC_SOFTWARE_ONLY','output':logs,'sourceSha256':hashlib.sha256(source.read_bytes()).hexdigest(),'noHardwareOperations':True,'noFirmwareInstallation':True}
(out/'result.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
