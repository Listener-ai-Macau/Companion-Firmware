#include "board_hal.h"
#include "reset_witness.h"
#if defined(__arm__) && COMPANION_WBA_CPU_RESIDENCE_PROFILE
#include <stdio.h>
/* Diagnostic-only words, never a boot permission, clock, pairing or audio
 * receipt. BKP0..2 are ST timer,4..15 product clock,16..18 Boot575 receipt.
 * Reserve the previously unused BKP3/19 without modifying that resident Boot.
 * No flash writes, logger in an IRQ, watchdog reload or timeout change. */
#define WITNESS_MAGIC UINT32_C(0xA7000000)
static uint32_t irq_parents;
static volatile uint8_t scope;
static uint8_t depth;
/* Fault-only stack. The normal24KiB stack/guard remains untouched. */
uint8_t comp_v11_fault_stack[128] __attribute__((section(".sram1.bss"),aligned(8),used));
_Static_assert(sizeof(comp_v11_fault_stack)==128u,"bounded fault-only stack");
static bool available(void)
{return __HAL_RCC_RTCAPB_IS_CLK_ENABLED();}
static uint32_t marker(unsigned phase,unsigned irq,unsigned kind)
{return WITNESS_MAGIC|((phase&255u)<<16u)|((irq&255u)<<8u)|(kind&255u);}
static void context(unsigned phase,unsigned irq,unsigned kind)
{if(available())TAMP->BKP3R=marker(phase,irq,kind);}
comp_v11_reset_witness_t comp_v11_reset_witness_read(void)
{return(comp_v11_reset_witness_t){TAMP->BKP3R,TAMP->BKP19R};}
void comp_v11_reset_witness_emit(comp_v11_reset_witness_t previous,uint32_t reset)
{
    char line[192];const bool valid=(previous.marker&UINT32_C(0xff000000))==WITNESS_MAGIC;
    (void)snprintf(line,sizeof(line),"RESETW1 schema=1 marker=%08lX detail=%08lX reset=%08lX valid=%u bkp3_19=1 watchdog_changed=0\r\n",
        (unsigned long)previous.marker,(unsigned long)previous.detail,(unsigned long)reset,(unsigned)valid);
    (void)comp_v11_hal_debug_write(line);
    bool writable=false;
    if(available()) {
        TAMP->BKP19R=UINT32_C(0x634A19C3);TAMP->BKP3R=marker(0u,0u,0u);
        writable=TAMP->BKP19R==UINT32_C(0x634A19C3)&&TAMP->BKP3R==marker(0u,0u,0u);
        TAMP->BKP3R=0u;TAMP->BKP19R=0u;
    }
    (void)snprintf(line,sizeof(line),"RESETW2 bkp_available=%u bkp_writable=%u scope=diagnostic_or_fault no_capture_bus_writes=1\r\n",
        (unsigned)available(),(unsigned)writable);
    (void)comp_v11_hal_debug_write(line);
}
void comp_v11_reset_witness_begin(unsigned phase)
{
    if(__get_IPSR()||!available())return;
    scope=(uint8_t)phase;depth=0u;irq_parents=0u;TAMP->BKP19R=0u;context(scope,0u,0u);
}
void comp_v11_reset_witness_end(void)
{
    if(__get_IPSR()||!scope)return;
    scope=0u;context(0u,0u,0u);
}
void comp_v11_reset_witness_uart_begin(const char *text)
{
    if(!scope||__get_IPSR()||!available())return;
    uint32_t tag=2166136261u;
    for(unsigned i=0;i<32u && text[i] && text[i]!=' ' && text[i]!='\r' && text[i]!='\n';++i)
        tag=(tag^(uint8_t)text[i])*16777619u;
    TAMP->BKP19R=tag;context(3u,0u,0u);
}
void comp_v11_reset_witness_uart_end(void)
{if(scope&&!__get_IPSR())context(scope,0u,0u);}
void comp_v11_reset_witness_failure(unsigned kind,uint32_t detail,unsigned pc)
{
    if(!available())return;
    /* Preserve a specific entropy-underflow witness when generic Error_Handler
     * immediately follows it. A later CPU fault still has its own handler. */
    if(kind==6u&&(TAMP->BKP3R&UINT32_C(0xff00007f))==(WITNESS_MAGIC|7u))return;
    TAMP->BKP19R=detail;
    context(scope,(unsigned)__get_IPSR(),kind|(pc?128u:0u));__DSB();
}
void comp_v11_reset_witness_irq_enter(void)
{
    /* Inactive throughout capture: just the scope byte/branch, no backup bus. */
    if(!scope||!available())return;
    unsigned parent=(TAMP->BKP3R>>8u)&255u;
    if(depth<4u)irq_parents=(irq_parents<<8u)|parent;
    if(depth!=255u)++depth;
    context((TAMP->BKP3R>>16u)&255u,depth<=4u?__get_IPSR():255u,0u);
}
void comp_v11_reset_witness_irq_exit(void)
{
    if(!scope||!depth||!available())return;
    unsigned parent=255u;
    if(depth<=4u){parent=irq_parents&255u;irq_parents>>=8u;}
    --depth;context((TAMP->BKP3R>>16u)&255u,parent,0u);
}
static bool frame_range(uintptr_t p,unsigned words)
{
    uintptr_t n=(uintptr_t)words*4u;
    return !(p&3u) && ((p>=UINT32_C(0x20000000)&&p<=UINT32_C(0x20008000)-n)||
        (p>=UINT32_C(0x20010000)&&p<=UINT32_C(0x20020000)-n));
}
__attribute__((noreturn,used)) void comp_v11_fault_observe(const uint32_t *frame,uint32_t exc_return,unsigned kind)
{
    uint32_t detail=exc_return;bool pc_valid=false;
    /* Only the known same-security basic/FP frames are read. Other ARMv8-M
     * exception layouts remain explicit LR evidence instead of guessed PCs. */
    bool supported=exc_return==UINT32_C(0xfffffff1)||exc_return==UINT32_C(0xfffffff9)||
        exc_return==UINT32_C(0xfffffffd)||exc_return==UINT32_C(0xffffffe1)||
        exc_return==UINT32_C(0xffffffe9)||exc_return==UINT32_C(0xffffffed);
    const uint32_t stacking=SCB_CFSR_STKERR_Msk|SCB_CFSR_UNSTKERR_Msk|SCB_CFSR_MSTKERR_Msk|
        SCB_CFSR_MUNSTKERR_Msk|SCB_CFSR_LSPERR_Msk|SCB_CFSR_MLSPERR_Msk;
    unsigned skip=(exc_return&16u)?0u:18u;
    if(supported&&!(SCB->CFSR&stacking)&&frame_range((uintptr_t)frame,skip+8u)) {
        const uint32_t *basic=frame+skip;
        if(basic[7]&(1u<<24u)){detail=basic[6];pc_valid=true;}
    }
    if(available()) {TAMP->BKP19R=detail;context(scope,(unsigned)__get_IPSR(),kind|(pc_valid?128u:0u));__DSB();}
    for(;;){__NOP();} /* original fail-stop; existing watchdog restarts it. */
}
/* Read the original exception SP/LR before using a small independent stack.
 * Never return into the fault, issue UART, clear fault state or feed IWDG. */
#define FAULT_HANDLER(name,kind) \
__attribute__((naked,used)) void name(void) {__asm volatile( \
    "cpsid i\n" "tst lr,#4\n" "ite eq\n" "mrseq r0,msp\n" "mrsne r0,psp\n" \
    "mov r1,lr\n" "movs r2,#" #kind "\n" \
    "ldr r3,=comp_v11_fault_stack+128\n" "msr msp,r3\n" "b comp_v11_fault_observe\n");}
FAULT_HANDLER(HardFault_Handler,1)
FAULT_HANDLER(MemManage_Handler,2)
FAULT_HANDLER(BusFault_Handler,3)
FAULT_HANDLER(UsageFault_Handler,4)
FAULT_HANDLER(NMI_Handler,5)
#endif
