"""Exercise the production board shutdown, retry and speaker code with faulted HAL/TCA."""
from pathlib import Path
import os
import subprocess
from verify_wba_spi_nor_adapter import find_vsdevcmd

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(os.environ.get("SPEAKER_TEST_OUT", r"E:/CodexData/Companion/speaker-shutdown-fault-20261030/dma-recovery-r1"))
BOARD = Path(os.environ.get("SPEAKER_TEST_BOARD", str(ROOT / "platform/stm32wba55_companion_v11/board_hal.c")))
PLAYBACK = ROOT / "app/companion_pendant/playback"
BOARD_APP = ROOT / "app/companion_pendant/board"

def section(source, start, end):
    return source[source.index(start):source.index(end)]

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    source = BOARD.read_text(encoding="utf-8")
    amp = section(source, "static bool amp(", "static bool submit(")
    activity = section(source, "static void activity(", "static bool speaker_init(")
    poll = section(source, "void comp_v11_hal_speaker_poll(", "#if defined(__GNUC__)\n__attribute__((section(\".sram1.bss\")")
    fixture = r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include "speaker_playback.h"
#include "audio_feedback.h"
#include "tca6408.h"
#define COMP_V11_AMP_ENABLE 0x40u
#define COMP_V11_FAULT_AUDIO 1u
#define COMP_V11_FAULT_SPEAKER_SHUTDOWN 1024u
#define COMP_POWER_BLOCKER_PLAYBACK 1u
#define COMP_POWER_BLOCKER_MIC_CAPTURE 2u
#define COMP_POWER_BLOCKER_STORAGE 4u
#define COMP_POWER_BLOCKER_UPDATE 8u
#define COMP_POWER_BLOCKER_RECORDING_TRANSFER 16u
#define COMP_POWER_BLOCKER_BOND_NVM 32u
#define SAI_xCR1_SAIEN 1u
#define SAI_xCR1_DMAEN 2u
#define DMA_CCR_EN 1u
#define DMA_FLAG_TC 1u
#define DMA_FLAG_HT 2u
#define DMA_FLAG_DTE 4u
#define DMA_FLAG_ULE 8u
#define DMA_FLAG_USE 16u
#define DMA_FLAG_SUSP 32u
#define DMA_FLAG_TO 64u
#define GPDMA1_Channel0_IRQn 0
#define HAL_OK 0
#define SPEAKER_DMA_DEADLINE_MS 100u
#define SPEAKER_SHUTDOWN_RETRY_MS 1000u
typedef struct {uint32_t CR1;} sai_regs;
typedef struct {uint32_t CCR;} dma_regs;
typedef struct {sai_regs *Instance;} sai_t;
typedef struct {dma_regs *Instance;} dma_t;
typedef struct {uint32_t blockers;} power_t;
typedef struct {bool running;} mic_t;
typedef struct {comp_tca6408_t io; bool playback_active;
    uint32_t faults; power_t power; mic_t microphone; comp_speaker_t speaker;} comp_v11_hal_t;
static sai_regs sr; static dma_regs dr;
static sai_t sai_speaker={&sr}; static dma_t dma_speaker={&dr};
static uint8_t speaker_completion,speaker_prefilled,speaker_probe[8];
static uint32_t speaker_submit_started_ms,now;
static int hal_result,leave_sai,leave_dma,stop_calls,writes,failed_write,drop_write,deny_write,failed_read;
static int dma_init_result,dma_init_calls,irq_line_enabled,irq_clears,dma_clears;
static uint8_t registers[4];
static uint32_t HAL_GetTick(void){return now;}
static unsigned __get_IPSR(void){return 0u;}
static unsigned __get_PRIMASK(void){return 0u;}
static void __disable_irq(void){}
static void __set_PRIMASK(unsigned p){(void)p;}
static void __DMB(void){}
static int HAL_SAI_DMAStop(sai_t *s){stop_calls++; if(!leave_sai)s->Instance->CR1=0;
    if(!leave_dma)dr.CCR=0;return hal_result;}
static uint32_t NVIC_GetEnableIRQ(int irq){(void)irq;return (uint32_t)irq_line_enabled;}
static void HAL_NVIC_DisableIRQ(int irq){(void)irq;irq_line_enabled=0;}
static void HAL_NVIC_EnableIRQ(int irq){(void)irq;irq_line_enabled=1;}
static void HAL_NVIC_ClearPendingIRQ(int irq){(void)irq;irq_clears++;}
static void clear_dma(dma_t *d,uint32_t flags){(void)d;assert(flags==127u);dma_clears++;}
#define __HAL_DMA_CLEAR_FLAG(d, flags) clear_dma((d),(flags))
static int HAL_DMA_Init(dma_t *d){assert(!irq_line_enabled);dma_init_calls++;if(dma_init_result==0)d->Instance->CCR=0;
    return dma_init_result;}
static uint8_t speaker_probe_io(comp_v11_hal_t *b,uint8_t *p){(void)b;(void)p;return 0u;}
static void comp_power_policy_set_blocker(power_t *p,uint32_t bit,bool on)
{if(on)p->blockers|=bit;else p->blockers&=~bit;}
static bool read_io(void *p,uint8_t a,uint8_t r,uint8_t *v)
{(void)p;(void)a;if(failed_read)return false;*v=registers[r];return true;}
static bool write_io(void *p,uint8_t a,uint8_t r,uint8_t v)
{(void)p;(void)a;writes++;if(!drop_write)registers[r]=v;return !failed_write;}
static bool admit(void *p){(void)p;return !deny_write;}
static bool submit(void *p,const int16_t *pcm,size_t n)
{(void)p;(void)pcm;(void)n;sr.CR1=3u;dr.CCR=1u;return true;}
'''
    checks = r'''
static void setup(comp_v11_hal_t *b){
    (void)HAL_DMA_Init;
    *b=(comp_v11_hal_t){0}; for(unsigned i=0;i<4;i++)registers[i]=0;
    now=0;hal_result=0;leave_sai=leave_dma=failed_write=drop_write=deny_write=failed_read=stop_calls=writes=0;
    dma_init_result=dma_init_calls=irq_clears=dma_clears=0;irq_line_enabled=1;
    sr.CR1=dr.CCR=speaker_completion=speaker_prefilled=0;
    assert(comp_tca6408_init(&b->io,read_io,write_io,b,0x20u,0x03u,0u));
    b->io.admit_write=admit;
    comp_speaker_config_t cfg={amp,submit,activity,b};comp_speaker_init(&b->speaker,&cfg);
    assert(comp_speaker_play_cue(&b->speaker,COMP_SPEAKER_CUE_CONFIRM)==COMP_SPEAKER_OK);
    assert(comp_speaker_service(&b->speaker));
}
int main(void){
    comp_v11_hal_t b;setup(&b);deny_write=1;
    comp_speaker_tx_complete(&b.speaker,false);
    assert(b.speaker.state==COMP_SPEAKER_STATE_FAULT && !comp_speaker_active(&b.speaker));
    assert((b.faults&COMP_V11_FAULT_SPEAKER_SHUTDOWN) && b.playback_active && (b.power.blockers&1u));
    assert(registers[1]&COMP_V11_AMP_ENABLE);int previous=stop_calls;
    now=999;comp_v11_hal_speaker_poll(&b);assert(stop_calls==previous);
    deny_write=0;now=1000;b.power.blockers|=COMP_POWER_BLOCKER_STORAGE;
    comp_v11_hal_speaker_poll(&b);assert(stop_calls==previous);
    b.power.blockers&=~COMP_POWER_BLOCKER_STORAGE;comp_v11_hal_speaker_poll(&b);
    assert(!(b.faults&COMP_V11_FAULT_SPEAKER_SHUTDOWN) && !b.playback_active && !(b.power.blockers&1u));
    assert(!(registers[1]&COMP_V11_AMP_ENABLE) && b.speaker.state==COMP_SPEAKER_STATE_FAULT);
    setup(&b);failed_write=1;comp_speaker_tx_complete(&b.speaker,false);
    assert(!b.io.ready && (b.faults&COMP_V11_FAULT_SPEAKER_SHUTDOWN) && b.playback_active);
    previous=stop_calls;int oldwrites=writes;failed_read=1;now=2000;comp_v11_hal_speaker_poll(&b);
    assert(stop_calls==previous && writes==oldwrites && (b.faults&COMP_V11_FAULT_SPEAKER_SHUTDOWN));
    failed_read=0;registers[3]^=0x04u;now=3000;comp_v11_hal_speaker_poll(&b);
    assert(!b.io.ready && stop_calls==previous && writes==oldwrites);
    registers[3]^=0x04u;registers[1]^=0x04u;now=4000;comp_v11_hal_speaker_poll(&b);
    assert(!b.io.ready && stop_calls==previous && writes==oldwrites);
    registers[1]^=0x04u;registers[2]=1u;now=5000;comp_v11_hal_speaker_poll(&b);
    assert(!b.io.ready && stop_calls==previous && writes==oldwrites);
    registers[2]=0u;failed_write=0;now=6000;comp_v11_hal_speaker_poll(&b);
    assert(b.io.ready && !(b.faults&COMP_V11_FAULT_SPEAKER_SHUTDOWN) && !b.playback_active);
    setup(&b);failed_write=1;drop_write=1;comp_speaker_tx_complete(&b.speaker,false);
    assert(!b.io.ready && (registers[1]&COMP_V11_AMP_ENABLE));
    failed_write=drop_write=0;now=1000;comp_v11_hal_speaker_poll(&b);
    assert(b.io.ready && !(registers[1]&COMP_V11_AMP_ENABLE) && !b.playback_active);
    setup(&b);hal_result=1;leave_dma=1;comp_speaker_tx_complete(&b.speaker,false);
    assert((b.faults&COMP_V11_FAULT_SPEAKER_SHUTDOWN) && b.playback_active);
    hal_result=0;dma_init_result=1;now=1000;comp_v11_hal_speaker_poll(&b);
    assert(dma_init_calls==1 && (b.faults&COMP_V11_FAULT_SPEAKER_SHUTDOWN) &&
           b.playback_active && (dr.CCR&1u) && irq_line_enabled && !dma_clears && !irq_clears);
    now=1500;comp_v11_hal_speaker_poll(&b);assert(dma_init_calls==1);
    dma_init_result=0;now=2000;comp_v11_hal_speaker_poll(&b);
    assert(dma_init_calls==2 && !(b.faults&COMP_V11_FAULT_SPEAKER_SHUTDOWN) &&
           !b.playback_active && irq_line_enabled && dma_clears==1 && irq_clears==1);
    setup(&b);hal_result=1;leave_sai=1;leave_dma=1;comp_speaker_tx_complete(&b.speaker,false);
    now=1000;comp_v11_hal_speaker_poll(&b);
    assert(dma_init_calls==0 && (b.faults&COMP_V11_FAULT_SPEAKER_SHUTDOWN));
    /* Real cue gate must complete as FAILED, so the caller can explicitly
     * reject/cancel capture instead of waiting for a permanently bad amp. */
    setup(&b);comp_speaker_tx_complete(&b.speaker,false);
    comp_speaker_config_t sc={amp,submit,activity,&b};comp_speaker_init(&b.speaker,&sc);
    comp_audio_feedback_t feedback;comp_audio_feedback_config_t fc={&b.speaker,NULL,&b,150u,1500u};
    comp_audio_feedback_init(&feedback,&fc);
    assert(comp_audio_feedback_submit(&feedback,COMP_AUDIO_FEEDBACK_RECORDING_START_REQUEST,0u)==
           COMP_AUDIO_FEEDBACK_SUBMIT_ACCEPTED);
    comp_audio_feedback_service(&feedback,0u);comp_audio_feedback_service(&feedback,1u);
    assert(b.speaker.tx_pending);deny_write=1;comp_speaker_tx_complete(&b.speaker,false);
    comp_audio_feedback_service(&feedback,2u);comp_audio_feedback_outcome_t outcome;
    assert(comp_audio_feedback_take_recording_start_gate(&feedback,&outcome));
    assert(outcome==COMP_AUDIO_FEEDBACK_OUTCOME_FAILED && (b.faults&COMP_V11_FAULT_SPEAKER_SHUTDOWN));
    assert(b.playback_active && (b.power.blockers&COMP_POWER_BLOCKER_PLAYBACK));
    puts("PASS production speaker + board shutdown model: no false release, bounded retry, ACK loss and DMA safety");
    return 0;
}
'''
    test = OUT / "test.c"
    test.write_text(fixture + amp + activity + poll + checks, encoding="utf-8")
    exe = OUT / "test.exe"
    cmd = OUT / "build.cmd"
    args = ["cl.exe", "/nologo", "/std:c11", "/W4", "/WX", f"/I{PLAYBACK}",
            f"/I{BOARD_APP}", str(test), str(PLAYBACK / "speaker_playback.c"), str(PLAYBACK / "audio_feedback.c"),
            str(BOARD_APP / "tca6408.c"), f"/Fe:{exe}"]
    cmd.write_text(f'@call "{find_vsdevcmd()}" -arch=amd64 -host_arch=amd64 >nul\n'
                   '@if errorlevel 1 exit /b %errorlevel%\n@' + subprocess.list2cmdline(args) + '\n')
    logs=[]
    for command in (["cmd.exe", "/d", "/c", str(cmd)], [str(exe)]):
        result=subprocess.run(command,cwd=OUT,text=True,capture_output=True)
        logs.append(result.stdout+result.stderr)
        (OUT/"test.log").write_text("\n".join(logs),encoding="utf-8")
        if result.returncode:
            raise RuntimeError(f"exit {result.returncode}: {OUT/'test.log'}")
    print(logs[-1].strip())

if __name__ == "__main__":
    main()
