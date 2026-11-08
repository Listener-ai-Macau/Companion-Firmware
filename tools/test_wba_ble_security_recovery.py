"""Exercise the actual WBA approved-rebond handler and its privacy guards."""
from pathlib import Path
import argparse, hashlib, json, subprocess
from verify_wba_spi_nor_adapter import find_vsdevcmd

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'platform/stm32wba55_companion_v11/ble/app_ble.c'
PRELUDE = r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "diag_log.h"
#define ACI_GAP_BOND_LOST_VSEVT_CODE 0x0405u
#define ACI_GAP_PAIRING_COMPLETE_VSEVT_CODE 0x0401u
typedef struct { uint16_t Connection_Handle; } aci_gap_bond_lost_event_rp0;
typedef struct { uint16_t Connection_Handle; uint8_t Status,Reason; } aci_gap_pairing_complete_event_rp0;
static bool ready,radio_enabled,connection_allowed,connection_secured,advertising;
static bool reconnect_requested,advertise_pending,advertise_stop_pending,window;
static struct {uint32_t first_bond_lost_ms;} link_history;
static uint16_t connection;
static uint32_t pairing_until,advertising_retry;
static unsigned rebonds,disconnects;
static uint8_t reply,last_error;
static uint32_t HAL_GetTick(void) { return 4000u; }
static bool pairing_open(void) { return window; }
static bool check(uint8_t value) { last_error=value; return value==0u; }
static uint8_t aci_gap_allow_rebond(uint16_t handle) { assert(handle==connection); ++rebonds; return reply; }
static uint8_t hci_disconnect(uint16_t handle,uint8_t reason) { assert(handle==connection && (reason==5u||reason==0x13u)); ++disconnects; return 0; }
static void comp_v11_ble_link(bool linked,bool secured) { assert(linked && !secured); }
void comp_diag_log_record_code(uint16_t code,uint8_t severity,uint32_t a,uint32_t b,uint32_t c,uint32_t d)
{ assert(code==COMP_DIAG_EVT_BLE_SECURITY); (void)severity;(void)a;(void)b;(void)c;(void)d; }
'''
TEST = r'''
static void reset_case(void) {
    ready=radio_enabled=connection_allowed=window=true;
    connection_secured=advertising=reconnect_requested=advertise_pending=false;
    connection=7u;reply=last_error=0u;rebonds=disconnects=0u;
    memset(&security_stats,0,sizeof(security_stats));
    security_stats.pairing_status=security_stats.pairing_reason=255u;
}
int main(void) {
    const uint8_t lost[]={7,0},wrong[]={8,0},good[]={7,0,0,0},failed[]={7,0,2,3};
    reset_case();
    gap_security_event(ACI_GAP_BOND_LOST_VSEVT_CODE,lost,sizeof(lost));
    assert(rebonds==1 && disconnects==0 && security_stats.rebond_attempts==1 && !connection_secured);
    reset_case();window=false;
    gap_security_event(ACI_GAP_BOND_LOST_VSEVT_CODE,lost,sizeof(lost));
    assert(rebonds==0 && disconnects==1 && !connection_secured);
    reset_case();connection_allowed=false;
    gap_security_event(ACI_GAP_BOND_LOST_VSEVT_CODE,lost,sizeof(lost));
    assert(rebonds==0 && disconnects==1);
    reset_case();radio_enabled=false;
    gap_security_event(ACI_GAP_BOND_LOST_VSEVT_CODE,lost,sizeof(lost));
    assert(rebonds==0 && disconnects==1);
    reset_case();
    gap_security_event(ACI_GAP_BOND_LOST_VSEVT_CODE,wrong,sizeof(wrong));
    gap_security_event(ACI_GAP_BOND_LOST_VSEVT_CODE,lost,1u);
    gap_security_event(ACI_GAP_PAIRING_COMPLETE_VSEVT_CODE,failed,3u);
    assert(rebonds==0 && disconnects==0 && security_stats.bond_lost_events==0 && security_stats.pairing_status==255);
    reset_case();reply=0x12u;
    gap_security_event(ACI_GAP_BOND_LOST_VSEVT_CODE,lost,sizeof(lost));
    assert(rebonds==1 && disconnects==1 && !connection_secured);
    reset_case();
    gap_security_event(ACI_GAP_PAIRING_COMPLETE_VSEVT_CODE,good,sizeof(good));
    assert(security_stats.pairing_status==0 && disconnects==0 && !connection_secured);
    reset_case();connection_secured=true;
    gap_security_event(ACI_GAP_PAIRING_COMPLETE_VSEVT_CODE,failed,sizeof(failed));
    assert(security_stats.pairing_status==2 && security_stats.pairing_reason==3 && !connection_secured && disconnects==1);
    reset_case();connection=0xffffu;advertising=true;
    assert(comp_v11_ble_reconnect(true) && advertising && advertise_pending && advertise_stop_pending && pairing_until==124000u && disconnects==0);
    puts("PASS_BLE_APPROVED_REBOND_AND_PRIVACY_GUARDS_SOFTWARE_ONLY");
    return 0;
}
'''

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    out=parser.parse_args().output.resolve();out.mkdir(parents=True,exist_ok=False)
    source=SOURCE.read_text(encoding='utf-8')
    header=(SOURCE.parent/'ble_product.h').read_text(encoding='utf-8')
    start=header.index('typedef struct {\n    uint32_t bond_lost_events')
    definition=header[start:header.index('comp_v11_ble_security_stats_t;',start)+len('comp_v11_ble_security_stats_t;')]
    security=source[source.index('static void gap_security_event('):source.index('SVCCTL_UserEvtFlowStatus_t SVCCTL_App_Notification')]
    start=source.index('bool comp_v11_ble_reconnect(')
    reconnect=source[start:source.index('\n}',start)+2]
    stats='\nstatic comp_v11_ble_security_stats_t security_stats;\nstatic void pairing_result(uint8_t status,uint8_t reason){security_stats.pairing_status=status;security_stats.pairing_reason=reason;}\n'
    harness=out/'security.c';harness.write_text(PRELUDE+definition+stats+security+reconnect+TEST,encoding='utf-8')
    exe=out/'test.exe';build=out/'build.cmd'
    args=['cl.exe','/nologo','/std:c11','/W4','/WX',f'/I{ROOT / "app/companion_pendant/diag_log"}',str(harness),'/Fe:'+str(exe)]
    build.write_text('@echo off\ncall "'+str(find_vsdevcmd())+'" -arch=amd64 -host_arch=amd64 >nul\nif errorlevel 1 exit /b %errorlevel%\n'+subprocess.list2cmdline(args)+'\n',encoding='utf-8')
    logs=[]
    for command in (['cmd.exe','/d','/c',str(build)],[str(exe)]):
        p=subprocess.run(command,cwd=out,capture_output=True,text=True,encoding='utf-8',errors='replace')
        logs.append(p.stdout+p.stderr);(out/'test.log').write_text('\n'.join(logs),encoding='utf-8')
        if p.returncode:raise RuntimeError('BLE recovery test failed: '+str(out/'test.log'))
    r={'result':logs[-1].strip(),'hardwareAcceptance':'NOT_RUN','sourceSha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest()}
    (out/'result.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8');print(r['result'])

if __name__=='__main__':main()
