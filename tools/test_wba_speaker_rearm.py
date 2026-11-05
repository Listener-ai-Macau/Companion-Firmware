"""Host-only checks of the actual board's SAI DMA re-arm boundary."""
from pathlib import Path
import hashlib,json,subprocess
from verify_wba_spi_nor_adapter import find_vsdevcmd

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'platform/stm32wba55_companion_v11/board_hal.c'
OUT=ROOT/'.cache/hardware-bringup-20261006/speaker-rearm-host'

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    text=SOURCE.read_text()
    body=text[text.index('static bool submit('):text.index('static void activity(')]
    fixture=r'''
#include <assert.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#define COMP_SPEAKER_BLOCK_FRAMES 64u
#define HAL_SAI_STATE_READY 1u
#define HAL_SAI_STATE_BUSY_TX 2u
#define HAL_SAI_ERROR_NONE 0u
#define SAI_xCR1_DMAEN 1u
#define SAI_FLAG_OVRUDR 2u
#define HAL_OK 0
typedef struct { uint32_t CR1,SR; } instance_t;
typedef struct { instance_t *Instance; uint32_t State,ErrorCode; } sai_t;
typedef struct { bool speaker_ready; } comp_v11_hal_t;
static instance_t instance;
static sai_t sai_speaker={&instance,HAL_SAI_STATE_READY,0u};
static unsigned clears,submits;
static int next_hal_result;
static void clear(sai_t *s,uint32_t flag) {
    assert(s->State==HAL_SAI_STATE_READY && s->ErrorCode==0u && !(s->Instance->CR1&SAI_xCR1_DMAEN));
    assert(flag==SAI_FLAG_OVRUDR);s->Instance->SR&=~flag;clears++;
}
#define __HAL_SAI_CLEAR_FLAG(s,f) clear((s),(f))
static int HAL_SAI_Transmit_DMA(sai_t *s,uint8_t *pcm,uint16_t size) {
    assert(pcm && size==128u && !(s->Instance->SR&SAI_FLAG_OVRUDR));submits++;
    return next_hal_result;
}
'''
    checks=r'''
int main(void) {
    comp_v11_hal_t board={true};int16_t pcm[128]={0};
    instance.SR=SAI_FLAG_OVRUDR|16u;
    assert(submit(&board,pcm,64u) && clears==1u && submits==1u && instance.SR==16u);
    sai_speaker.State=HAL_SAI_STATE_BUSY_TX;instance.SR=SAI_FLAG_OVRUDR;
    assert(!submit(&board,pcm,64u) && clears==1u && instance.SR==SAI_FLAG_OVRUDR);
    sai_speaker.State=HAL_SAI_STATE_READY;instance.CR1=SAI_xCR1_DMAEN;
    assert(!submit(&board,pcm,64u) && clears==1u);
    instance.CR1=0u;sai_speaker.ErrorCode=2u;
    assert(!submit(&board,pcm,64u) && clears==1u && sai_speaker.ErrorCode==2u);
    sai_speaker.ErrorCode=0u;next_hal_result=1;
    assert(!submit(&board,pcm,64u) && clears==2u && submits==2u);
    assert(!submit(NULL,pcm,64u) && !submit(&board,NULL,64u) && !submit(&board,pcm,0u));
    puts("PASS_HOST_ONLY actual speaker re-arm clears only idle UDR; active and reported faults retained");
    return 0;
}
'''
    source=OUT/'test.c';source.write_text(fixture+body+checks)
    exe=OUT/'test.exe'
    script=OUT/'build.cmd'
    args=['cl.exe','/nologo','/std:c11','/W4','/WX',str(source),f'/Fe:{exe}']
    script.write_text(f'@call "{find_vsdevcmd()}" -arch=amd64 -host_arch=amd64 >nul\n@if errorlevel 1 exit /b %errorlevel%\n@'+subprocess.list2cmdline(args)+'\n')
    logs=[]
    for command in (['cmd.exe','/d','/c',str(script)],[str(exe)]):
        result=subprocess.run(command,cwd=OUT,text=True,capture_output=True)
        logs.append(result.stdout+result.stderr)
        (OUT/'test.log').write_text('\n'.join(logs))
        if result.returncode:raise RuntimeError('speaker re-arm test failed: '+str(OUT/'test.log'))
    receipt={'result':'PASS_HOST_ONLY','hardwareAcceptance':'NOT_RUN',
        'source_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),'output':logs[-1].strip()}
    (OUT/'result.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(receipt['output'])

if __name__=='__main__':main()
