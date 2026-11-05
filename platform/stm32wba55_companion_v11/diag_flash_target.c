#include "diag_flash_target.h"
#include "wba_storage_layout.h"
#include "diag_log.h"
#include "stm32wbaxx_ll_iwdg.h"
#include <stdio.h>
#include <string.h>
#if !COMP_V11_DIAG_FLASH_ENABLED || COMPANION_WBA_CPU_RESIDENCE_PROFILE
#error "Flash crash journal uses its own bounded fault handler, without CPU residence tracing"
#endif
#define HEARTBEAT_MAGIC UINT32_C(0x43484232)
#define FAULT_MAGIC UINT32_C(0x43484632)
/* 0..2 ST timer, 3/19 old reset witness, 4..15 product clock,
 * 16..18 resident Boot receipt. Only 20..31 belong to this optional journal. */
static void backup_access(void)
{HAL_PWR_EnableBkUpAccess();__HAL_RCC_RTCAPB_CLK_ENABLE();}
comp_diag_flash_data_t comp_v11_diag_flash_snapshot(void)
{
    comp_diag_flash_data_t d={{0}};
    if(TAMP->BKP20R==HEARTBEAT_MAGIC) {
        d.word[COMP_DJ_TICK]=TAMP->BKP21R;d.word[COMP_DJ_PHASE]=TAMP->BKP22R;
        d.word[COMP_DJ_STATE]=TAMP->BKP23R;
    }
    if(TAMP->BKP24R==FAULT_MAGIC) {
        d.word[COMP_DJ_PC]=TAMP->BKP25R;d.word[COMP_DJ_LR]=TAMP->BKP26R;
        d.word[COMP_DJ_CFSR]=TAMP->BKP27R;d.word[COMP_DJ_HFSR]=TAMP->BKP28R;
        d.word[COMP_DJ_BFAR]=TAMP->BKP29R;d.word[COMP_DJ_EXC_RETURN]=TAMP->BKP30R;
        d.word[COMP_DJ_FAULT]=TAMP->BKP31R;
    }
    return d;
}
static bool read_nor(void *ctx,uint32_t at,uint8_t *p,size_t n)
{return companion_spi_nor_stm32wba_read(ctx,at,p,n)==COMPANION_SPI_NOR_STM32WBA_OK;}
static bool program_nor(void *ctx,uint32_t at,const uint8_t *p,size_t n)
{return companion_spi_nor_stm32wba_program(ctx,at,p,n)==COMPANION_SPI_NOR_STM32WBA_OK;}
static comp_diag_flash_ports_t ports(comp_v11_hal_t *b)
{
    return(comp_diag_flash_ports_t){read_nor,program_nor,&b->nor,
        COMP_WBA_NOR_DIAGNOSTIC_BASE,COMP_WBA_NOR_DIAGNOSTIC_BYTES};
}
void comp_v11_diag_flash_boot(comp_v11_hal_t *b,uint32_t reset,const comp_diag_flash_data_t *previous)
{
    backup_access();
    comp_diag_flash_result_t r={0};comp_diag_flash_data_t d=*previous;
    d.word[COMP_DJ_FW]=COMPANION_WBA_APP_VERSION;d.word[COMP_DJ_RESET]=reset;
    if(companion_spi_nor_stm32wba_ready(&b->nor)&&!b->nor.erase_active) {
        const comp_diag_flash_ports_t p=ports(b);r=comp_diag_flash_journal(&p,&d,NULL,NULL);
        if(r.appended){TAMP->BKP20R=0u;TAMP->BKP24R=0u;__DSB();}
    }
    char line[160];
    (void)snprintf(line,sizeof(line),
        "DIAGFLASH1 scan=%u append=%u records=%lu seq=%lu reset=%08lX prev_ms=%lu phase=%lu fault=%lu\r\n",
        (unsigned)r.scanned,(unsigned)r.appended,(unsigned long)r.valid,(unsigned long)r.sequence,
        (unsigned long)reset,(unsigned long)d.word[COMP_DJ_TICK],
        (unsigned long)d.word[COMP_DJ_PHASE],(unsigned long)d.word[COMP_DJ_FAULT]);
    (void)comp_v11_hal_debug_write(line);
}
static void replay(void *ctx,uint32_t seq,const comp_diag_flash_data_t *d)
{
    (void)ctx;
    comp_diag_log_record_code(COMP_DIAG_EVT_BOOT_START,COMP_DIAG_SEV_INFO,
        d->word[COMP_DJ_FW],d->word[COMP_DJ_RESET],d->word[COMP_DJ_TICK],d->word[COMP_DJ_PHASE]);
    if(d->word[COMP_DJ_FAULT]) {
        comp_diag_log_record_code(COMP_DIAG_EVT_ERRORS_FAULT,COMP_DIAG_SEV_ERROR,
            d->word[COMP_DJ_PC],d->word[COMP_DJ_LR],d->word[COMP_DJ_CFSR],d->word[COMP_DJ_HFSR]);
        comp_diag_log_record_code(COMP_DIAG_EVT_ERRORS_FAULT_CONTEXT,COMP_DIAG_SEV_ERROR,
            d->word[COMP_DJ_BFAR],d->word[COMP_DJ_EXC_RETURN],d->word[COMP_DJ_FAULT],seq);
    }
}
void comp_v11_diag_flash_replay(comp_v11_hal_t *b)
{
    if(!companion_spi_nor_stm32wba_ready(&b->nor)||b->nor.erase_active)return;
    const comp_diag_flash_ports_t p=ports(b);(void)comp_diag_flash_journal(&p,NULL,replay,NULL);
}
static void dump_record(void *ctx,uint32_t seq,const comp_diag_flash_data_t *d)
{
    (void)ctx;char line[256];
    LL_IWDG_ReloadCounter(IWDG);
    (void)snprintf(line,sizeof(line),
        "DJ1 seq=%lu fw=%08lX reset=%08lX ms=%lu phase=%lu state=%08lX fault=%lu pc=%08lX lr=%08lX cfsr=%08lX hfsr=%08lX bfar=%08lX exc=%08lX\r\n",
        (unsigned long)seq,(unsigned long)d->word[COMP_DJ_FW],(unsigned long)d->word[COMP_DJ_RESET],
        (unsigned long)d->word[COMP_DJ_TICK],(unsigned long)d->word[COMP_DJ_PHASE],
        (unsigned long)d->word[COMP_DJ_STATE],(unsigned long)d->word[COMP_DJ_FAULT],
        (unsigned long)d->word[COMP_DJ_PC],(unsigned long)d->word[COMP_DJ_LR],
        (unsigned long)d->word[COMP_DJ_CFSR],(unsigned long)d->word[COMP_DJ_HFSR],
        (unsigned long)d->word[COMP_DJ_BFAR],(unsigned long)d->word[COMP_DJ_EXC_RETURN]);
    (void)comp_v11_hal_debug_write(line);
}
void comp_v11_diag_flash_dump(comp_v11_hal_t *b)
{
    if(!companion_spi_nor_stm32wba_ready(&b->nor)||b->nor.erase_active)return;
    const comp_diag_flash_ports_t p=ports(b);(void)comp_diag_flash_journal(&p,NULL,dump_record,NULL);
}
void comp_v11_diag_flash_heartbeat(const comp_v11_product_app_t *app,uint32_t tick,uint32_t phase)
{
    static uint32_t last;
    if(!last||(uint32_t)(tick-last)>=100u){TAMP->BKP21R=tick;last=tick;}
    TAMP->BKP22R=phase;
    TAMP->BKP23R=((uint32_t)app->runtime.recording&15u)|
        (((uint32_t)app->recording.pipeline.state&15u)<<4u)|
        ((app->board->microphone.running?1u:0u)<<8u)|
        ((app->board->nor.erase_active?1u:0u)<<9u)|
        ((app->board->key_wake_events&UINT32_C(0x003FFFFF))<<10u);
    TAMP->BKP20R=HEARTBEAT_MAGIC;
}
/* Independent fault-only stack; no NOR/UART/heap operations in an exception.
 * The already-running watchdog performs the original fail-stop reset. */
uint8_t comp_v11_journal_fault_stack[128] __attribute__((section(".sram1.bss"),aligned(8),used));
static bool frame_range(uintptr_t p,unsigned words)
{
    const uintptr_t n=(uintptr_t)words*4u;
    return !(p&3u)&&((p>=UINT32_C(0x20000000)&&p<=UINT32_C(0x20008000)-n)||
        (p>=UINT32_C(0x20010000)&&p<=UINT32_C(0x20020000)-n));
}
__attribute__((noreturn,used)) void comp_v11_journal_fault(const uint32_t *frame,uint32_t exc,unsigned kind)
{
    uint32_t pc=0u,lr=0u;
    const bool supported=exc==UINT32_C(0xfffffff1)||exc==UINT32_C(0xfffffff9)||exc==UINT32_C(0xfffffffd)||
        exc==UINT32_C(0xffffffe1)||exc==UINT32_C(0xffffffe9)||exc==UINT32_C(0xffffffed);
    const uint32_t bad=SCB_CFSR_STKERR_Msk|SCB_CFSR_UNSTKERR_Msk|SCB_CFSR_MSTKERR_Msk|
        SCB_CFSR_MUNSTKERR_Msk|SCB_CFSR_LSPERR_Msk|SCB_CFSR_MLSPERR_Msk;
    const unsigned skip=(exc&16u)?0u:18u;
    if(supported&&!(SCB->CFSR&bad)&&frame_range((uintptr_t)frame,skip+8u)) {
        const uint32_t *basic=frame+skip;
        if(basic[7]&(1u<<24u)){pc=basic[6];lr=basic[5];}
    }
    backup_access();TAMP->BKP24R=0u;TAMP->BKP25R=pc;TAMP->BKP26R=lr;
    TAMP->BKP27R=SCB->CFSR;TAMP->BKP28R=SCB->HFSR;TAMP->BKP29R=SCB->BFAR;
    TAMP->BKP30R=exc;TAMP->BKP31R=kind;__DSB();TAMP->BKP24R=FAULT_MAGIC;__DSB();
    for(;;){__NOP();}
}
#define JOURNAL_FAULT(name,kind) \
__attribute__((naked,used)) void name(void){__asm volatile( \
    "cpsid i\n" "tst lr,#4\n" "ite eq\n" "mrseq r0,msp\n" "mrsne r0,psp\n" \
    "mov r1,lr\n" "movs r2,#" #kind "\n" \
    "ldr r3,=comp_v11_journal_fault_stack+128\n" "msr msp,r3\n" "b comp_v11_journal_fault\n");}
JOURNAL_FAULT(HardFault_Handler,1)
JOURNAL_FAULT(MemManage_Handler,2)
JOURNAL_FAULT(BusFault_Handler,3)
JOURNAL_FAULT(UsageFault_Handler,4)
JOURNAL_FAULT(NMI_Handler,5)
