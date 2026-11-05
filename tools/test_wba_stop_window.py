"""Actual target admission/lifetime and console parser, declared sleep model.

No physical clock, deep-sleep dwell, current, or energy qualification.
"""
from pathlib import Path
import argparse,hashlib,json,os,subprocess

STUB=r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "diagnostic_console.h"
#ifndef COMPANION_WBA_AUTOMATIC_STOP1
#define COMPANION_WBA_AUTOMATIC_STOP1 0
#endif
typedef struct {unsigned marker;} comp_v11_product_app_t;
typedef struct {bool captured,entered_stop;} comp_v11_stop_wake_snapshot_t;
typedef struct {bool enabled;} comp_wba_stop_t;
typedef enum {COMP_WBA_STOP_SKIPPED,COMP_WBA_STOP_ABORTED,COMP_WBA_STOP_COMPLETED} comp_wba_stop_result_t;
static comp_v11_product_app_t fixture,*product=&fixture;
static comp_wba_stop_t stop;
static bool trial_armed,trial_window,app_stop_permission,eligible_now,pending_now,actual_entry,host_ready;
static uint16_t trial_entries_left;
static uint32_t trial_deadline,last_wake_flags,ticks,ipsr,primask,companion_stop1_entries,advance_ms;
static uint32_t run_calls,wfi_calls,vote_calls,last_vote;
static uint8_t stop_stage;
static comp_v11_stop_wake_snapshot_t last_wake;
#define __get_IPSR() ipsr
#define __get_PRIMASK() primask
#define HAL_GetTick() ticks
#define CFG_LPM_APP 0u
#define UTIL_LPM_STOP1_MODE 2u
#define UTIL_LPM_SLEEP_MODE 1u
static bool eligible(comp_v11_product_app_t *p){return p==product&&eligible_now;}
static bool foreground_pending(const comp_v11_product_app_t *p){assert(p==product);return pending_now;}
static bool comp_v11_ble_host_ready(void){return host_ready;}
static void UTIL_LPM_SetMaxMode(uint32_t owner,uint32_t mode){assert(owner==1u);++vote_calls;last_vote=mode;}
static void comp_v11_cpu_wait_enter(void){}
static void comp_v11_cpu_wait_exit(void){}
static void __WFI(void){++wfi_calls;}
static comp_wba_stop_result_t comp_wba_stop_run(comp_wba_stop_t *,bool);
'''

TEST=r'''
static comp_wba_stop_result_t comp_wba_stop_run(comp_wba_stop_t *s,bool allowed)
{
    ++run_calls;
    if(!s->enabled||!allowed)return COMP_WBA_STOP_SKIPPED;
    assert(eligible_now&&!pending_now&&(COMPANION_WBA_AUTOMATIC_STOP1||trial_armed));
    if(actual_entry)trial_entered();
    ticks+=advance_ms;
    return actual_entry?COMP_WBA_STOP_COMPLETED:COMP_WBA_STOP_ABORTED;
}
static void fresh(void)
{
    stop.enabled=eligible_now=actual_entry=host_ready=true;
    trial_armed=trial_window=app_stop_permission=pending_now=false;
    trial_entries_left=0;ticks=ipsr=primask=companion_stop1_entries=0;
    run_calls=wfi_calls=vote_calls=last_vote=0;advance_ms=20;product=&fixture;
}
static void feed(comp_v11_diag_console_t *c,const char *s)
{while(*s)comp_v11_diag_console_accept(c,(uint8_t)*s++);}
int main(void)
{
#if COMPANION_WBA_AUTOMATIC_STOP1
    fresh();assert(!strcmp(comp_v11_low_power_identity(),"STOP1_AUTOMATIC"));
    for(unsigned i=0;i<1000u;i++)comp_v11_low_power_idle(&fixture);
    assert(companion_stop1_entries==1000u&&app_stop_permission&&!trial_armed);
    pending_now=true;comp_v11_low_power_idle(&fixture);
    assert(companion_stop1_entries==1000u&&!app_stop_permission);
    pending_now=false;eligible_now=false;comp_v11_low_power_idle(&fixture);
    assert(companion_stop1_entries==1000u&&!app_stop_permission);
    eligible_now=true;comp_v11_low_power_idle(&fixture);
    assert(companion_stop1_entries==1001u&&app_stop_permission);
    stop.enabled=false;comp_v11_low_power_idle(&fixture);
    assert(!app_stop_permission&&!strcmp(comp_v11_low_power_identity(),"STOP1_UNAVAILABLE"));
    comp_v11_diag_console_t c;comp_v11_diag_console_init(&c);
    feed(&c,"REC STOP\n");assert(comp_v11_diag_console_take_record(&c)==COMP_V11_DIAG_RECORD_STOP);
    puts("PASS automatic Stop1: continuous eligible idle, pending/activity veto, automatic resume, disabled target; physical current/wake not qualified");
    return 0;
#else
    fresh();assert(!strcmp(comp_v11_low_power_identity(),"STOP1_ONCE_UNARMED"));
    comp_v11_low_power_idle(&fixture);assert(companion_stop1_entries==0&&wfi_calls==1);
    assert(comp_v11_low_power_arm_once(&fixture));
    assert(!comp_v11_low_power_arm_window(&fixture));
    comp_v11_low_power_idle(&fixture);
    assert(companion_stop1_entries==1&&!trial_armed&&!app_stop_permission&&last_vote==1);
    for(unsigned i=0;i<20;i++)comp_v11_low_power_idle(&fixture);
    assert(companion_stop1_entries==1);
    fresh();advance_ms=0;assert(comp_v11_low_power_arm_window(&fixture));
    for(unsigned i=0;i<256;i++)comp_v11_low_power_idle(&fixture);
    assert(companion_stop1_entries==256&&!trial_armed&&!trial_entries_left&&!app_stop_permission);
    comp_v11_low_power_idle(&fixture);assert(companion_stop1_entries==256);
    fresh();ticks=UINT32_MAX-2000u;assert(comp_v11_low_power_arm_window(&fixture));
    for(unsigned i=0;i<251;i++)comp_v11_low_power_idle(&fixture);
    assert(companion_stop1_entries==250&&!trial_armed&&!app_stop_permission);
    fresh();assert(comp_v11_low_power_arm_window(&fixture));pending_now=true;
    comp_v11_low_power_idle(&fixture);assert(companion_stop1_entries==0&&run_calls==0&&wfi_calls==0);
    pending_now=false;eligible_now=false;
    comp_v11_low_power_idle(&fixture);assert(companion_stop1_entries==0&&!app_stop_permission);
    eligible_now=true;comp_v11_low_power_idle(&fixture);assert(companion_stop1_entries==1&&trial_armed);
    actual_entry=false;ticks=5000;comp_v11_low_power_idle(&fixture);
    assert(!trial_armed&&!app_stop_permission&&companion_stop1_entries==1);
    for(unsigned fault=0;fault<5;fault++){
        fresh();if(fault==0)ipsr=1;if(fault==1)primask=1;if(fault==2)stop.enabled=false;
        if(fault==3)eligible_now=false;if(fault==4)pending_now=true;
        assert(!comp_v11_low_power_arm_window(&fixture)&&!trial_armed);
    }
    fresh();assert(comp_v11_low_power_arm_window(&fixture));actual_entry=false;
    comp_v11_low_power_idle(&fixture);assert(companion_stop1_entries==0&&trial_entries_left==256);
    stop.enabled=false;comp_v11_low_power_idle(&fixture);
    assert(!app_stop_permission&&!strcmp(comp_v11_low_power_identity(),"STOP1_UNAVAILABLE"));
    comp_v11_diag_console_t c;comp_v11_diag_console_init(&c);
    assert(c.command_candidates==UINT32_MAX);
    feed(&c,"POWER STOP1 WINDOW\r\n");
    assert(comp_v11_diag_console_take_record(&c)==COMP_V11_DIAG_RECORD_STOP1_WINDOW);
    assert(comp_v11_diag_console_take_record(&c)==COMP_V11_DIAG_RECORD_NONE);
    feed(&c,"POWER STOP1 ONCE\n");assert(comp_v11_diag_console_take_record(&c)==COMP_V11_DIAG_RECORD_STOP1_ONCE);
    feed(&c,"POWER STOP1 WINDO\n");assert(comp_v11_diag_console_take_record(&c)==COMP_V11_DIAG_RECORD_NONE);
    feed(&c,"POWER STOP1 WINDOW X\n");assert(comp_v11_diag_console_take_record(&c)==COMP_V11_DIAG_RECORD_NONE);
    feed(&c,"REC STOP\n");assert(comp_v11_diag_console_take_record(&c)==COMP_V11_DIAG_RECORD_STOP);
    feed(&c,"REC CACHE OFF ONCE\n");assert(comp_v11_diag_console_take_record(&c)==COMP_V11_DIAG_RECORD_CACHE_OFF_NEXT);
    feed(&c,"PAIR\n");assert(comp_v11_diag_console_take_pair(&c));
    puts("PASS actual target: reset remains WFI; one-shot one entry; window expires after5s or256 actual entries; wrap, admission, foreground precedence, abort/no entry, unavailable, exact32-command parser");
    puts("MODEL_ONLY: actual clocks/dwell/wake/recording/current/energy not qualified");
    return 0;
#endif
}
'''

def function(text,marker):
    a=text.index(marker);b=text.index('{',a)+1;level=1
    while level:level+=(text[b]=='{')-(text[b]=='}');b+=1
    return text[a:b]

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',required=True);a=ap.parse_args()
    root=Path(__file__).resolve().parents[1];target=root/'platform/stm32wba55_companion_v11'
    out=Path(a.output).resolve();out.mkdir(parents=True,exist_ok=False)
    src=(target/'low_power_target.c').read_text()
    marks=['static void trial_expire(','static void trial_entered(','void comp_v11_low_power_idle(','const char *comp_v11_low_power_identity(','static bool arm_trial(','bool comp_v11_low_power_arm_once(','bool comp_v11_low_power_arm_window(']
    body='\n'.join(function(src,m)for m in marks)
    (out/'window.c').write_text(STUB+body+TEST)
    vc=Path(r'C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat');runs=[]
    for label,cc,feature in [('window',out/'window.c',True),('automatic',out/'window.c',True),('normal-console',target/'tests/test_diagnostic_console.c',False)]:
        d=out/label;d.mkdir();cmd=['cl.exe','/nologo','/std:c11','/W4','/WX',f'/I{target}',str(cc),str(target/'diagnostic_console.c'),f'/Fe:{d/"test.exe"}']
        if feature:cmd+=['/DCOMPANION_WBA_BLE_LINKED=1','/DCOMPANION_WBA_EXPERIMENTAL_STOP1=1']
        if label=='automatic':cmd+=['/DCOMPANION_WBA_AUTOMATIC_STOP1=1']
        script=d/'build.cmd';script.write_text('@echo off\ncall "'+str(vc)+'" >nul\nif errorlevel 1 exit /b %errorlevel%\n'+subprocess.list2cmdline(cmd)+'\n')
        p=subprocess.run([os.environ.get('COMSPEC','cmd.exe'),'/d','/c',str(script)],cwd=d,capture_output=True)
        (d/'build.log').write_bytes(p.stdout+p.stderr);assert p.returncode==0,(p.stdout+p.stderr).decode(errors='replace')
        p=subprocess.run([str(d/'test.exe')],cwd=d,capture_output=True);(d/'run.log').write_bytes(p.stdout+p.stderr)
        assert p.returncode==0,(p.stdout+p.stderr).decode(errors='replace')
        runs.append(dict(name=label,stdout=p.stdout.decode()))
    result=dict(result='PASS_BOUNDED_STOP_WINDOW_SOFTWARE_ONLY',runs=runs,physicalSleepQualified=False,energyQualified=False,installed=False,targetSha256=hashlib.sha256((target/'low_power_target.c').read_bytes()).hexdigest())
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
