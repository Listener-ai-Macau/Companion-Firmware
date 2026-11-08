"""Run actual connection admission and deadline clauses across successive links."""
from pathlib import Path
import argparse,hashlib,json,subprocess
from verify_wba_spi_nor_adapter import find_vsdevcmd
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'platform/stm32wba55_companion_v11/ble/app_ble.c'
PRELUDE=r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#define COMPANION_WBA_PEER_INDICATIONS 0
#define BLE_STATUS_SUCCESS 0
static uint32_t now,pairing_until,dle_ready_after,bulk_ci_ready_after,bulk_dle_ready_after;
static uint16_t connection,bulk_ci_previous_interval,dle_aligned_octets;
static bool radio_enabled,advertising,connection_secured,connection_allowed;
static bool bulk_ci_requested,bulk_ci_wait_update,bulk_dle_issued,bulk_dle_waiting;
static bool dle_alignment_attempted,dle_restore_attempted;
static uint8_t bulk_ci_attempts,dle_attempts,dle_status,directional_budget_recovery;
static uint8_t dle_alignment_status,dle_restore_status;
static unsigned att,transport,disconnects,securities,bond_checks;
static uint8_t bond_result;
static uint32_t HAL_GetTick(void){return now;}
static void comp_v11_ble_mtu_open(unsigned *p,uint32_t t){*p=t;}
static void comp_v11_ble_link(bool linked,bool secured){assert(linked&&!secured);}
static uint8_t check(uint8_t s){assert(s==0);return s;}
static uint8_t aci_gap_check_bonded_device(uint8_t type,const uint8_t *a,uint8_t *it,uint8_t *ia)
{assert(type==1&&a&&it&&ia);++bond_checks;return bond_result;}
static uint8_t hci_disconnect(uint16_t h,uint8_t reason)
{assert(h==connection&&reason==0x13);++disconnects;return 0;}
static uint8_t aci_gap_peripheral_security_req(uint16_t h)
{assert(h==connection);++securities;return 0;}
'''
TEST=r'''
static void reset_case(uint32_t tick,uint32_t deadline,uint8_t bond)
{now=tick;pairing_until=deadline;bond_result=bond;radio_enabled=true;disconnects=securities=bond_checks=0;}
int main(void){
 const uint8_t address[6]={1,2,3,4,5,6};
 /* The field failure: prior window ended while disconnected; a known
  * phone reconnects later. Encryption has not finished at the first poll. */
 reset_case(130000,120000,0);connection_opened(7,1,address);expire_connection();
 assert(connection_allowed&&securities==1&&bond_checks==1&&disconnects==0&&pairing_until==0);
 reset_case(130000,120000,1);connection_opened(7,1,address);
 assert(!connection_allowed&&securities==0&&disconnects==1);
 reset_case(100000,120000,1);connection_opened(7,1,address);expire_connection();
 assert(connection_allowed&&securities==1&&!bond_checks&&!disconnects&&pairing_until==120000);
 now=120001;expire_connection();assert(disconnects==1&&pairing_until==0);
 reset_case(100000,120000,0);connection_opened(7,1,address);connection_secured=true;
 now=120001;expire_connection();assert(disconnects==0);
 reset_case(0xfffffff0u,0x100u,1);connection_opened(7,1,address);expire_connection();
 assert(connection_allowed&&!disconnects&&pairing_until==0x100u);
 now=0x101u;expire_connection();assert(disconnects==1);
 reset_case(0x200u,0x100u,0);connection_opened(7,1,address);expire_connection();
 assert(connection_allowed&&!disconnects&&pairing_until==0);
 reset_case(130000,120000,0);radio_enabled=false;connection_opened(7,1,address);
 assert(!connection_allowed&&disconnects==1&&securities==0);
 puts("PASS_PRODUCTION_PAIRING_DEADLINE_SUCCESSIVE_LINKS_SOFTWARE_ONLY");return 0;
}
'''
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);p.add_argument('--source',type=Path,default=SOURCE);a=p.parse_args()
 out=a.output.resolve();out.mkdir(parents=True,exist_ok=False);text=a.source.read_text(encoding='utf-8')
 start=text.index('static bool pairing_open(');window=text[start:text.index('}',start)+1]
 opened=text[text.index('static void connection_opened('):text.index('void comp_v11_ble_apply_preferences(')]
 start=text.index('    if(connection!=0xFFFFu && !connection_secured && pairing_until && !pairing_open())')
 expiry=text[start:text.index('\n    }',start)+6]
 harness=out/'deadline.c';harness.write_text(PRELUDE+window+'\n'+opened+'\nstatic void expire_connection(void){\n'+expiry+'\n}\n'+TEST,encoding='utf-8')
 exe=out/'deadline.exe';script=out/'build.cmd'
 cmd=['cl.exe','/nologo','/std:c11','/W4','/WX',str(harness),'/Fe:'+str(exe)]
 script.write_text('@echo off\ncall "'+str(find_vsdevcmd())+'" -arch=amd64 -host_arch=amd64 >nul\nif errorlevel 1 exit /b %errorlevel%\n'+subprocess.list2cmdline(cmd)+'\n',encoding='utf-8')
 logs=[]
 for command in (['cmd.exe','/d','/c',str(script)],[str(exe)]):
  r=subprocess.run(command,cwd=out,capture_output=True,text=True,encoding='utf-8',errors='replace');logs.append(r.stdout+r.stderr)
  (out/'test.log').write_text('\n'.join(logs),encoding='utf-8')
  if r.returncode:raise RuntimeError('Production deadline regression: '+str(out/'test.log'))
 result={'result':logs[-1].strip(),'hardwareAcceptance':'NOT_RUN','sourceSha256':hashlib.sha256(a.source.read_bytes()).hexdigest()}
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(result['result'])
if __name__=='__main__':main()
