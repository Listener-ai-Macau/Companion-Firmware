from pathlib import Path
import subprocess,sys
root=Path(__file__).resolve().parents[1];src=root/'platform/stm32wba55_companion_v11/microphone_hal.c'; raw=src.read_text(encoding='utf8');out=Path(sys.argv[1]).resolve();out.mkdir(parents=True,exist_ok=False)
clear=raw[raw.index('static void clear_events('):raw.index('static void publish_event(')]
start=raw[raw.index('bool comp_v11_microphone_hal_start('):raw.index('static comp_v11_microphone_poll_result_t microphone_hal_poll_body(')]
a=raw.index('static comp_v11_microphone_poll_result_t microphone_hal_poll_body(');b=raw.index('    if (!pop_event(',a);poll=raw[a:b]+'    return COMP_V11_MIC_POLL_IDLE;\n}\n'
a=raw.index('bool comp_v11_microphone_hal_on_error(');b=raw.index('\n}',a)+2;irq=raw[a:b]
header=r"""#include <stdint.h>
#include <stdbool.h>
#include <string.h>
#include <stdio.h>
#include <assert.h>
#define COMPANION_WBA_CE_SHARED_CAPTURE 1
#define COMP_V11_MIC_DMA_TRANSFER_HALFWORDS 1920u
#define HAL_OK 0
#define DMA_CCR_EN 1u
#define SAI_xCR1_SAIEN 0x10000u
#define SAI_xCR1_DMAEN 0x20000u
#define __DMB() ((void)0)
typedef struct {uint32_t CCR;} DMA_Channel_TypeDef;typedef struct {uint32_t CR1;} SAI_Block_TypeDef;typedef struct {uint32_t ErrorCode;SAI_Block_TypeDef *Instance;} SAI_HandleTypeDef;typedef struct {DMA_Channel_TypeDef *Instance;} DMA_HandleTypeDef;
typedef struct {uint32_t samples;} duration_t;
typedef struct {int placeholder;} processing_t;
typedef struct {SAI_HandleTypeDef sai;DMA_HandleTypeDef dma;uint32_t raw[1];processing_t processing;duration_t pdm_duration;uint32_t next_sequence,latest_half_sequence[2],last_hal_error,error_irqs,starts,stops;uint8_t event_head,event_tail,writing_half,startup_halves_remaining;bool initialized,running,error_pending,partial_start_cleanup;uint8_t partial_stop_attempts;uint32_t partial_stop_due_ms;} comp_v11_microphone_hal_t;
typedef enum {COMP_V11_MIC_POLL_IDLE,COMP_V11_MIC_POLL_PROCESSED,COMP_V11_MIC_POLL_DROPPED,COMP_V11_MIC_POLL_ERROR} comp_v11_microphone_poll_result_t;
typedef struct{uint32_t sequence;uint8_t half;} comp_v11_microphone_event_t;
static unsigned stop_fail,stop_calls,claims,releases;static uint32_t tick;static bool start_fail,stuck_dma,stuck_sai;static DMA_Channel_TypeDef dma_reg;static SAI_Block_TypeDef sai_reg;
static uint32_t HAL_GetTick(void){return tick;}static uint32_t __get_PRIMASK(void){return 0;}static void __disable_irq(void){}static void __set_PRIMASK(uint32_t x){(void)x;}
static void comp_wba_pdm_capture_reset_stream(processing_t *p){(void)p;}static bool companion_opus16_rt_dma_claim(void*p){(void)p;claims++;return true;}static void companion_opus16_rt_dma_release(void*p){(void)p;releases++;}
bool comp_v11_microphone_hal_stop(comp_v11_microphone_hal_t*);
static uint8_t* raw_dma_bytes(comp_v11_microphone_hal_t*m){return (uint8_t*)m->raw;}
static int HAL_SAI_Receive_DMA(SAI_HandleTypeDef*s,uint8_t*b,uint16_t n){(void)s;(void)b;(void)n;dma_reg.CCR|=DMA_CCR_EN;sai_reg.CR1|=SAI_xCR1_SAIEN|SAI_xCR1_DMAEN;return start_fail?1:0;}
static int HAL_SAI_DMAStop(SAI_HandleTypeDef*s){(void)s;stop_calls++;if(!stuck_sai)sai_reg.CR1=0;if(stop_fail){stop_fail--;return 1;}if(!stuck_dma)dma_reg.CCR=0;return 0;}
"""
main=r"""int main(int argc,char**argv){comp_v11_microphone_hal_t m={0};m.initialized=true;m.dma.Instance=&dma_reg;m.sai.Instance=&sai_reg;setvbuf(stdout,NULL,_IONBF,0);
 if(argc!=2)return 2;
 if(!strcmp(argv[1],"partial")){start_fail=true;stop_fail=2;assert(!comp_v11_microphone_hal_start(&m));assert(m.running&&m.error_pending&&claims==1&&releases==0);for(unsigned i=0;i<8;i++){tick+=100;microphone_hal_poll_body(&m);}printf("partial running=%u stops=%u releases=%u\\n",m.running,stop_calls,releases);assert(!m.running&&releases==1&&stop_calls==3);}
 else if(!strcmp(argv[1],"irq")){assert(comp_v11_microphone_hal_start(&m));stop_fail=2;assert(comp_v11_microphone_hal_on_error(&m,&m.sai));printf("irq-after-error running=%u pending=%u\\n",m.running,m.error_pending);assert(m.running);microphone_hal_poll_body(&m);assert(m.running&&releases==0);assert(!comp_v11_microphone_hal_stop(&m));assert(m.running&&releases==0);assert(comp_v11_microphone_hal_stop(&m));assert(!m.running&&releases==1);}
 else if(!strcmp(argv[1],"persistent")){start_fail=true;stop_fail=100;tick=UINT32_MAX-50u;assert(!comp_v11_microphone_hal_start(&m));microphone_hal_poll_body(&m);assert(stop_calls==2);for(unsigned i=0;i<20;i++)microphone_hal_poll_body(&m);assert(stop_calls==2);for(unsigned i=0;i<20;i++){tick+=100;microphone_hal_poll_body(&m);}printf("persistent running=%u attempts=%u stops=%u releases=%u\\n",m.running,m.partial_stop_attempts,stop_calls,releases);assert(m.running&&m.partial_start_cleanup&&m.partial_stop_attempts==3&&stop_calls==4&&releases==0);}
 else if(!strcmp(argv[1],"stuck-sai")){start_fail=true;stuck_sai=true;assert(!comp_v11_microphone_hal_start(&m));for(unsigned i=0;i<8;i++){tick+=100;microphone_hal_poll_body(&m);}assert(m.running&&(sai_reg.CR1&SAI_xCR1_SAIEN)&&stop_calls==4&&releases==0);}
 else if(!strcmp(argv[1],"stuck-initial")){start_fail=true;stuck_dma=true;assert(!comp_v11_microphone_hal_start(&m));assert(m.running&&m.partial_start_cleanup&&releases==0);for(unsigned i=0;i<8;i++){tick+=100;microphone_hal_poll_body(&m);}assert(m.running&&stop_calls==4&&releases==0);}
 else if(!strcmp(argv[1],"stuck")){start_fail=true;stop_fail=1;stuck_dma=true;assert(!comp_v11_microphone_hal_start(&m));for(unsigned i=0;i<8;i++){tick+=100;microphone_hal_poll_body(&m);}printf("stuck running=%u dma_en=%u stops=%u releases=%u\\n",m.running,(dma_reg.CCR&DMA_CCR_EN)!=0,stop_calls,releases);assert(m.running&&(dma_reg.CCR&DMA_CCR_EN)&&releases==0);}
 else return 3;puts("PASS_MIC_START_OR_IRQ_CLEANUP_SOFTWARE_ONLY");return 0;}
"""
model=out/'model.c';model.write_text(header+clear+start+poll+irq+main,encoding='utf8');sys.path.insert(0,str(root/'tools'));from verify_wba_spi_nor_adapter import find_vsdevcmd
cmd=out/'compile.cmd';cmd.write_text('@echo off\ncall "'+str(find_vsdevcmd())+'" -arch=amd64 -host_arch=amd64 >nul\ncl.exe /nologo /TC /std:c11 /O2 /W4 /WX /wd4101 /wd4505 "'+str(model)+'" /Fe:"'+str(out/'test.exe')+'"\n',encoding='utf8');r=subprocess.run(['cmd.exe','/d','/c',str(cmd)],cwd=out,capture_output=True,text=True);(out/'compile.txt').write_text(r.stdout+r.stderr,encoding='utf8');print('compile',r.returncode);print(r.stdout[-1500:],r.stderr[-500:]);
if r.returncode:sys.exit(r.returncode)
failed=[]
for case in ('partial','irq','persistent','stuck','stuck-initial','stuck-sai'):
 r=subprocess.run([str(out/'test.exe'),case],cwd=out,capture_output=True,text=True);(out/(case+'.txt')).write_text(r.stdout+r.stderr,encoding='utf8');print(case,'exit',r.returncode,r.stdout[-800:],r.stderr[-500:]);
 if r.returncode:failed.append(case)
if failed:raise SystemExit('failed cases: '+','.join(failed))
