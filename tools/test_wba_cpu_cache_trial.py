from pathlib import Path
import sys,argparse,subprocess,json,hashlib
p=argparse.ArgumentParser();p.add_argument('--source-root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--output',type=Path,required=True);a=p.parse_args();S=a.source_root.resolve();A=S/'platform/stm32wba55_companion_v11';sys.path.insert(0,str(S/'tools'))
from verify_wba_spi_nor_adapter import find_vsdevcmd
out=a.output.resolve();out.mkdir(parents=True,exist_ok=False);target=(A/'cpu_profile_target.c').read_text();adapter=target.split('/* CPU_CACHE_TRIAL_MODEL_BEGIN */',1)[1].split('/* CPU_CACHE_TRIAL_MODEL_END */',1)[0]
pre=r"""
#include <stdint.h>
#include <stdbool.h>
#include <stdio.h>
#include <string.h>
#define CHECK(x) do{if(!(x)){fprintf(stderr,"FAIL line %d %s\n",__LINE__,#x);return 1;}}while(0)
static struct{bool active;}residence;
static struct{uint32_t CR;}icache;
#define ICACHE (&icache)
#define ICACHE_MONITOR_HIT_MISS 0x30000u
#define HAL_OK 0
static uint32_t ipsr,disable_calls,enable_calls,tick;
static uint32_t HAL_GetTick(void){return tick;}static bool enabled=true,disable_fails,enable_fails;
typedef int HAL_StatusTypeDef;
static uint32_t __get_IPSR(void){return ipsr;}
static uint32_t HAL_ICACHE_IsEnabled(void){return enabled;}
static int HAL_ICACHE_Disable(void){++disable_calls;if(disable_fails)return 1;enabled=false;return HAL_OK;}
static int HAL_ICACHE_Enable(void){++enable_calls;if(enable_fails)return 1;enabled=true;return HAL_OK;}
"""
post=r"""
int main(void){
 cache_trial_begin(1u);CHECK(enabled&&!cache_trial.used&&disable_calls==0u);cache_trial_restore();CHECK(enable_calls==0u);
 residence.active=true;CHECK(!comp_v11_cpu_arm_cache_off_trial());residence.active=false;
 ipsr=46u;CHECK(!comp_v11_cpu_arm_cache_off_trial());ipsr=0u;
 ICACHE->CR=ICACHE_MONITOR_HIT_MISS;CHECK(!comp_v11_cpu_arm_cache_off_trial());ICACHE->CR=0u;
 enabled=false;CHECK(!comp_v11_cpu_arm_cache_off_trial());enabled=true;
 CHECK(comp_v11_cpu_arm_cache_off_trial());CHECK(!comp_v11_cpu_arm_cache_off_trial());CHECK(enabled&&disable_calls==0u);
 cache_trial_begin(2u);CHECK(!enabled&&cache_trial.used&&cache_trial.owned_off&&cache_trial.token==2u&&!cache_trial.armed&&!cache_trial.error);
 cache_trial_restore();CHECK(enabled&&!cache_trial.owned_off&&cache_trial.restored);uint32_t calls=enable_calls;cache_trial_restore();CHECK(enable_calls==calls);
 cache_trial_begin(3u);CHECK(enabled&&!cache_trial.used&&!cache_trial.armed); /* not inherited */
 CHECK(comp_v11_cpu_arm_cache_off_trial());disable_fails=true;cache_trial_begin(4u);CHECK(enabled&&cache_trial.error&&!cache_trial.owned_off);disable_fails=false;
 CHECK(comp_v11_cpu_arm_cache_off_trial());cache_trial_begin(5u);enable_fails=true;cache_trial_restore();CHECK(!enabled&&cache_trial.owned_off&&cache_trial.error&&!cache_trial.restored&&!comp_v11_cpu_arm_cache_off_trial());enable_fails=false;cache_trial_restore();CHECK(enabled&&cache_trial.restored&&cache_trial.error); /* never erase a restore failure */
 CHECK(comp_v11_cpu_arm_cache_off_trial());cache_trial_begin(6u);CHECK(!enabled);cache_trial_restore();CHECK(enabled&&cache_trial.restored&&!cache_trial.error);
 CHECK(comp_v11_cpu_arm_cache_off_trial());tick+=30000u;cache_trial_begin(7u);CHECK(enabled&&!cache_trial.used&&!cache_trial.armed);
 tick=UINT32_MAX-500u;CHECK(comp_v11_cpu_arm_cache_off_trial());tick+=1000u;cache_trial_begin(8u);CHECK(!enabled&&cache_trial.used);cache_trial_restore();CHECK(enabled);
 printf("PASS_CACHE_OFF_ONCE_SOURCE_MODEL state_bytes=%zu default-untouched/busy-IRQ-monitor-refuse/one-capture/end-and-fault-restore/failure-retained/30s-expiry-and-wrap/no-capacity-emulation\n",sizeof(cache_trial));return 0;
}
"""
f=out/'test.c';f.write_text(pre+adapter+post,encoding='utf-8');args=['cl.exe','/nologo','/TC','/std:c11','/O2','/W4','/WX','/utf-8',str(f),'/Fe:'+str(out/'test.exe')];cmd=out/'compile.cmd';cmd.write_text('@echo off\ncall "'+str(find_vsdevcmd())+'" -arch=amd64 -host_arch=amd64 >nul\nif errorlevel 1 exit /b %errorlevel%\n'+subprocess.list2cmdline(args)+'\n');r=subprocess.run(['cmd.exe','/d','/c',str(cmd)],cwd=out,capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW);(out/'build.log').write_text(r.stdout+r.stderr);assert r.returncode==0,(r.stdout+r.stderr)[-4000:]
r=subprocess.run([str(out/'test.exe')],cwd=out,capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW);(out/'result.log').write_text(r.stdout+r.stderr);assert r.returncode==0,(r.stdout+r.stderr)[-4000:];record={'result':'PASS_SOURCE_BOUND_CACHE_TRIAL_MODEL_ONLY','output':r.stdout,'adapterSha256':hashlib.sha256(adapter.encode()).hexdigest(),'hardwareCacheOffVerified':False,'hardwareRecordingQualified':False};(out/'result.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record))
