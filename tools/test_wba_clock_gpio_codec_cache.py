from pathlib import Path
import sys,subprocess,json,hashlib,argparse
p=argparse.ArgumentParser();p.add_argument('--source-root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--output',type=Path,required=True);a=p.parse_args();S=a.source_root.resolve();A=S/'platform/stm32wba55_companion_v11';sys.path.insert(0,str(S/'tools'))
from verify_wba_spi_nor_adapter import find_vsdevcmd
out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
text=(A/'cpu_profile_target.c').read_text();block=text.split('/* CODEC_CACHE_MODEL_BEGIN */',1)[1].split('/* CODEC_CACHE_MODEL_END */',1)[0]
pre=r'''
#include <stdint.h>
#include <stdbool.h>
#include <stdio.h>
#include <string.h>
#include "panel_gpio_timing.h"
#include "cpu_codec_irq.h"
static struct {uint32_t entered,max_us,max_at;uint16_t kind,max_kind;} outer_irq;
static bool transport_capture;
#define ICACHE_MONITOR_HIT_MISS 0x300u
static struct {uint32_t CR;} fake_cache;
#define ICACHE (&fake_cache)
static struct {bool active;} residence;
static uint32_t fake_hits,fake_misses,starts,stops,resets;
static bool cache_enabled=true;
static uint32_t HAL_ICACHE_IsEnabled(void){return cache_enabled;}
static int HAL_ICACHE_Monitor_Reset(uint32_t mask){if(mask!=ICACHE_MONITOR_HIT_MISS)return 1;++resets;fake_hits=fake_misses=0;return 0;}
static int HAL_ICACHE_Monitor_Start(uint32_t mask){++starts;ICACHE->CR|=mask;return 0;}
static int HAL_ICACHE_Monitor_Stop(uint32_t mask){++stops;ICACHE->CR&=~mask;return 0;}
static uint32_t HAL_ICACHE_Monitor_GetHitValue(void){return fake_hits;}
static uint32_t HAL_ICACHE_Monitor_GetMissValue(void){return fake_misses;}
#define CHECK(x) do{if(!(x)){fprintf(stderr,"FAIL line %d: %s\n",__LINE__,#x);return 1;}}while(0)
'''
post=r'''
int main(void){
 CHECK(comp_v11_panel_gpio_delay_loops(0u)==64u);
 CHECK(comp_v11_panel_gpio_delay_loops(98303712u)==64u);
 CHECK(comp_v11_panel_gpio_delay_loops(61439820u)==40u);
 CHECK(comp_v11_panel_gpio_delay_loops(64000000u)==42u);
 const uint32_t boundaries[]={1u,49152000u,65536000u,100000000u,UINT32_MAX};
 unsigned cases=0u;
 for(uint32_t hz=1u;hz<120000000u;hz+=78125u){uint32_t n=comp_v11_panel_gpio_delay_loops(hz);CHECK((uint64_t)n*98303712u>=(uint64_t)hz*64u);CHECK(n<=4096u && n>0u);++cases;}
 for(unsigned i=0;i<sizeof(boundaries)/sizeof(boundaries[0]);++i){uint32_t hz=boundaries[i],n=comp_v11_panel_gpio_delay_loops(hz);CHECK((uint64_t)n*98303712u>=(uint64_t)hz*64u);}
 ICACHE->CR=5u;comp_cpu_codec_cache_begin();CHECK(starts==0 && resets==0 && !codec_cache.owned);
 residence.active=true;ICACHE->CR=5u|0x100u;comp_cpu_codec_cache_begin();CHECK(starts==0 && stops==0 && resets==0 && codec_cache.foreign==1u && ICACHE->CR==(5u|0x100u));
 comp_cpu_codec_admission(0x00010303u,15000u);
 ICACHE->CR=5u;comp_cpu_codec_cache_begin();CHECK(codec_cache.owned && starts==1 && resets==1 && ICACHE->CR==(5u|ICACHE_MONITOR_HIT_MISS));fake_hits=200u;fake_misses=5u;codec_irq.current_us=180u;codec_irq.current_kind=39u;codec_cache_end(7000u,200u,true);
 CHECK(codec_cache.peak_admission_flags==0x00010303u && codec_cache.peak_admission_next_us==15000u);
 CHECK(!codec_cache.owned && stops==1u && ICACHE->CR==5u && codec_cache.calls==1u && codec_cache.hits==200u && codec_cache.misses==5u && codec_cache.peak_irq_us==200u && codec_irq.peak_us==180u && codec_irq.peak_kind==39u);
 comp_cpu_codec_admission(0x00030100u,0u);
 comp_cpu_codec_cache_begin();fake_hits=300u;fake_misses=UINT16_MAX;codec_cache_end(9000u,750u,true);CHECK(codec_cache.calls==2u && codec_cache.saturations==1u && codec_cache.peak_us==9000u && codec_cache.peak_hits==300u && codec_cache.peak_misses==UINT16_MAX && codec_cache.peak_irq_us==750u && ICACHE->CR==5u);
 CHECK(codec_cache.peak_admission_flags==0x00030100u && codec_cache.peak_admission_next_us==0u);
 comp_cpu_codec_admission(0x00010201u,0u);
 comp_cpu_codec_cache_begin();codec_cache_end(1u,0u,false);CHECK(!codec_cache.owned && codec_cache.calls==2u && codec_cache.begins==3u && ICACHE->CR==5u);
 comp_cpu_codec_cache_begin();codec_cache_stop_owned();CHECK(!codec_cache.owned && codec_cache.calls==2u && codec_cache.begins==4u && ICACHE->CR==5u);
 cache_enabled=false;uint32_t prior_starts=starts;comp_cpu_codec_cache_begin();CHECK(!codec_cache.owned&&starts==prior_starts);cache_enabled=true;
 comp_cpu_codec_cache_begin();codec_cache_end(2000u,50u,true);
 CHECK(codec_cache.peak_us==9000u && codec_cache.peak_admission_flags==0x00030100u && codec_cache.peak_admission_next_us==0u);
 printf("PASS_GPIO_CLOCK_MODEL cases=%u ceil_no_faster_nominal_reference low61=40 ref98=64; electrical edges NOT_QUALIFIED\n",cases);
 printf("PASS_CACHE_OBSERVATION real_source sizeof=%zu reset_counters_only/foreign-owner/saturation/paired-peak/abort-release; no cache invalidate or associativity change\n",sizeof(codec_cache));return 0;
}
'''
p=out/'test.c';p.write_text(pre+block+post,encoding='utf-8');args=['cl.exe','/nologo','/TC','/std:c11','/O2','/W4','/WX','/utf-8','/I'+str(A),str(p),'/Fe:'+str(out/'test.exe')]
cmd=out/'compile.cmd';cmd.write_text('@echo off\ncall "'+str(find_vsdevcmd())+'" -arch=amd64 -host_arch=amd64 >nul\nif errorlevel 1 exit /b %errorlevel%\n'+subprocess.list2cmdline(args)+'\n')
p=subprocess.run(['cmd.exe','/d','/c',str(cmd)],cwd=out,capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW);(out/'build.log').write_text(p.stdout+p.stderr);assert p.returncode==0,(p.stdout+p.stderr)[-4000:]
p=subprocess.run([str(out/'test.exe')],cwd=out,capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW);(out/'result.log').write_text(p.stdout+p.stderr);assert p.returncode==0,(p.stdout+p.stderr)[-4000:]
r={'result':'PASS_EXACT_SOURCE_MODEL_ONLY','output':p.stdout,'cpuCacheSourceSha256':hashlib.sha256((A/'cpu_profile_target.c').read_bytes()).hexdigest(),'gpioTimingSha256':hashlib.sha256((A/'panel_gpio_timing.h').read_bytes()).hexdigest(),'physicalBoard':False,'electricalTimingQualified':False};(out/'result.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
