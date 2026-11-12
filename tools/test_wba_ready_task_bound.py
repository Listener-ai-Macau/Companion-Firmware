"""Compare exact old/new ready-query functions over configured task masks."""
from pathlib import Path
import argparse,subprocess,json
from verify_wba_spi_nor_adapter import find_vsdevcmd
a=argparse.ArgumentParser();a.add_argument("--output",type=Path,required=True);opt=a.parse_args()
root=Path(__file__).resolve().parents[1];out=opt.output.resolve();out.mkdir(parents=True,exist_ok=False)
p=root/"platform/stm32wba55_companion_v11/ble/ble_product.c"
def body(s,signature):
 start=s.index("{",s.index(signature));level=0
 for i in range(start,len(s)):
  if s[i]=="{":level+=1
  elif s[i]=="}":
   level-=1
   if not level:return s[start:i+1]
old=subprocess.check_output(["git","show","04a7f86:platform/stm32wba55_companion_v11/ble/ble_product.c"],cwd=root).decode()
new=p.read_text()
config=(p.parent/"app_conf.h").read_text();end=config.index("} CFG_Task_Id_t;")+len("} CFG_Task_Id_t;");begin=config.rfind("typedef enum",0,end);enum=config[begin:end]
pre=r"""
#include <stdint.h>
#include <stdbool.h>
#include <assert.h>
#include <stdio.h>
#define UTIL_SEQ_DEFAULT UINT32_MAX
static uint32_t pending;static unsigned calls;
static bool fatal_error,sequencer_yielded,writes_allowed,sealed,nvm,io,tx;
static int holder,*product=&holder,product_link,notify_gate;
static uint32_t UTIL_SEQ_IsSchedulableTask(uint32_t task){++calls;return (pending&task)==task;}
static bool stack_writes_allowed(void){return writes_allowed;}
static bool sealed_transfer_work(void){return sealed;}
static bool comp_v11_ble_nvm_busy(void){return nvm;}
static bool comp_link_heavy_io_allowed(void*p){(void)p;return io;}
static bool comp_v11_ble_tx_gate_ready(void*p,uint32_t now){(void)p;(void)now;return tx;}
static uint32_t HAL_GetTick(void){return 100;}
"""
tests=r"""
int main(void){
 uint32_t seed=7;
 for(unsigned i=0;i<20000;++i){
  seed=seed*1664525u+1013904223u;pending=seed&((1u<<CFG_TASK_NBR)-1u);
  fatal_error=(seed&0x80000000u)!=0;sequencer_yielded=(seed&0x40000000u)!=0;
  writes_allowed=(seed&0x20000000u)!=0;sealed=(seed&0x10000000u)!=0;
  nvm=(seed&0x08000000u)!=0;io=(seed&0x04000000u)!=0;tx=(seed&0x02000000u)!=0;
  assert(before()==after());
 }
 fatal_error=sequencer_yielded=false;writes_allowed=true;sealed=false;pending=0;calls=0;
 assert(!before());unsigned old_calls=calls;calls=0;assert(!after());
 assert(old_calls==32u&&calls==CFG_TASK_NBR);
 pending=1u<<(CFG_TASK_NBR-1u);assert(after());pending=1u<<CFG_TASK_FLASH_MANAGER;
 writes_allowed=false;assert(!after());writes_allowed=true;assert(after());
 sequencer_yielded=true;pending=0;assert(after());
 printf("PASS exact old/new sequencer readiness20000 configured masks and gate combinations; empty query SDK calls32 -> %u, highest task/Flash gating/yield preserved. Software only.\n",CFG_TASK_NBR);
}
"""
src=pre+enum+"static bool before(void)"+body(old,"bool comp_v11_ble_foreground_pending")+"\nstatic bool after(void)"+body(new,"static bool foreground_pending_body")+"\n"+tests
model=out/"model.c";model.write_text(src)
cmd=["cl.exe","/nologo","/TC","/std:c11","/O2","/W4","/WX",str(model),"/Fe:"+str(out/"test.exe")]
batch=out/"compile.cmd";batch.write_text('@echo off\ncall "'+str(find_vsdevcmd())+'" -arch=amd64 -host_arch=amd64 >nul\nif errorlevel 1 exit /b %errorlevel%\n'+subprocess.list2cmdline(cmd)+'\n')
for name,cmd in [("compile",["cmd","/d","/c",str(batch)]),("run",[str(out/"test.exe")])]:
 r=subprocess.run(cmd,cwd=out,capture_output=True,text=True,encoding="utf-8",errors="replace");(out/(name+".log")).write_text(r.stdout+r.stderr);print(name,r.returncode,r.stdout+r.stderr);r.check_returncode()
(out/"result.json").write_text(json.dumps({"result":"PASS_CONFIGURED_TASK_BOUND_EQUIVALENCE","softwareOnly":True})+"\n")
