/* Command-driven diagnostic booted from internal Flash after a core reset.
 * The installer restores the exact previously installed product afterwards.
 * No BLE stack, other peripheral task, resource decoder, ADC, NOR or low-power
 * scheduler is linked. EPD power/reset are NOT controlled by this program.
 * Generated functions preserve the product's GPIO SPI ordering and delay loop;
 * the same SSD1681 source and build switches drive both fixed frames. */
#include "stm32wbaxx_hal.h"
#include "ssd1681_wba.h"
#include "panel_boot_idle.h"
#include "otp.h"
#include <stdarg.h>
#include <stdio.h>
#include <string.h>

#ifndef COMP_SCREEN_FIXED_GPIO_MONITOR
#define COMP_SCREEN_FIXED_GPIO_MONITOR 0
#endif
#ifndef COMP_SCREEN_BUS_ISOLATION
#define COMP_SCREEN_BUS_ISOLATION 0
#endif
#ifndef COMP_SCREEN_STATUS_PHASE
#define COMP_SCREEN_STATUS_PHASE 0
#endif
#ifndef COMP_SCREEN_SELECTED_QUIET_MS
#define COMP_SCREEN_SELECTED_QUIET_MS 0
#endif
#ifndef COMP_SCREEN_HELD_CONTROL
#define COMP_SCREEN_HELD_CONTROL 0
#endif
#if COMP_SCREEN_HELD_CONTROL
#define DIAG_ID "COMP_SCREEN_HELD_CONTROL_V6"
#elif COMP_SCREEN_STATUS_PHASE && COMP_SCREEN_SELECTED_QUIET_MS == 20
#define DIAG_ID "COMP_SCREEN_SELECTED_QUIET_V5"
#elif COMP_SCREEN_STATUS_PHASE
#define DIAG_ID "COMP_SCREEN_STATUS_PHASE_V4"
#elif COMP_SCREEN_BUS_ISOLATION
#define DIAG_ID "COMP_SCREEN_BUS_ISOLATION_V3"
#elif COMP_SCREEN_FIXED_GPIO_MONITOR
#define DIAG_ID "COMP_SCREEN_FIXED_GPIO_V2"
#else
#define DIAG_ID "COMP_SCREEN_FIXED_V1"
#endif
#define EVENT_LIMIT 1600u
static UART_HandleTypeDef uart;
static SPI_HandleTypeDef spi_shared;
static comp_ssd1681_wba_t panel;
static bool uart_ok, qualified_target, ran, spi_owned;
static bool panel_gpio_active = true, panel_gpio_reading;
static uint8_t previous_frame[5000], current_frame[5000];
static volatile uint32_t rx_faults, rx_head, rx_tail;
static volatile uint8_t rx_ring[128];
static uint32_t event_count, event_overflow;
typedef struct {
    uint32_t tick, fnv;
    uint16_t bytes;
    uint8_t data, stage, sequence, ram_phase, head[4];
} bus_event_t;
static bus_event_t events[EVENT_LIMIT];
#if COMP_SCREEN_FIXED_GPIO_MONITOR
/* MCU-side digital checks only. These extra reads extend GPIO bit periods;
 * they are not an electrical waveform capture or the production transport. */
static uint32_t gpio_samples, gpio_idr_mismatch[5], gpio_odr_mismatch[5];
static uint32_t gpio_busy_high, gpio_command_bytes;
typedef struct { uint32_t tick; uint8_t phase, expected, idr, odr; } gpio_sample_t;
static gpio_sample_t gpio_first_mismatch[16];
static unsigned gpio_retained;
static bool gpio_data;
static uint8_t packed_outputs(uint32_t a, uint32_t b)
{
    return (uint8_t)(((b >> 0u)&1u) | (((a >> 11u)&1u)<<1u) |
        (((b >> 4u)&1u)<<2u) | (((a >> 15u)&1u)<<3u) | (((b >> 15u)&1u)<<4u));
}
static void gpio_check(uint8_t phase, bool clock, bool output, bool selected)
{
    const uint32_t a=GPIOA->IDR, b=GPIOB->IDR;
    const uint8_t idr=packed_outputs(a,b), odr=packed_outputs(GPIOA->ODR,GPIOB->ODR);
    const uint8_t expected=(uint8_t)(16u | (selected ? 0u : 1u) |
        ((selected ? gpio_data : true) ? 2u : 0u) | (clock ? 4u : 0u) | (output ? 8u : 0u));
    ++gpio_samples;
    if ((a & GPIO_PIN_12)!=0u) ++gpio_busy_high;
    for (unsigned i=0u;i<5u;++i) {
        if (((idr^expected)&(1u<<i))!=0u) ++gpio_idr_mismatch[i];
        if (((odr^expected)&(1u<<i))!=0u) ++gpio_odr_mismatch[i];
    }
    if ((idr!=expected || odr!=expected) && gpio_retained<16u)
        gpio_first_mismatch[gpio_retained++]=(gpio_sample_t){HAL_GetTick(),phase,expected,idr,odr};
}
#endif
static inline void panel_busy_trace(bool during_bus) { (void)during_bus; }
/* Verbatim functions extracted from the frozen product HAL by the builder. */
#include "product_transport.inc"
#if COMP_SCREEN_FIXED_GPIO_MONITOR
static void monitored_command_send(uint8_t byte)
{
    ++gpio_command_bytes;
    for (uint8_t bit=0u;bit<8u;++bit) {
        HAL_GPIO_WritePin(GPIOB,GPIO_PIN_4,GPIO_PIN_RESET);
        bool output=(byte&0x80u)!=0u;
        HAL_GPIO_WritePin(GPIOA,GPIO_PIN_15,output ? GPIO_PIN_SET : GPIO_PIN_RESET);
        panel_gpio_delay();
        gpio_check(1u,false,output,true);
        HAL_GPIO_WritePin(GPIOB,GPIO_PIN_4,GPIO_PIN_SET);
        panel_gpio_delay();
        gpio_check(2u,true,output,true);
        byte<<=1u;
    }
}
#endif

void SysTick_Handler(void) { HAL_IncTick(); IWDG->KR = 0xAAAAu; }
/* At 115200 a character takes about 87us. A foreground loop sleeping 1ms
 * cannot safely receive a whole command through a one-byte polled RDR.
 * Use the same bounded FIFO/IRQ ring as the existing peripheral diagnostic;
 * no screen work or UART output runs in this handler. */
void LPUART1_IRQHandler(void)
{
    uint32_t errors=LPUART1->ISR & (USART_ISR_ORE|USART_ISR_FE|USART_ISR_NE|USART_ISR_PE);
    if (errors) {
        LPUART1->ICR=USART_ICR_ORECF|USART_ICR_FECF|USART_ICR_NECF|USART_ICR_PECF;
        ++rx_faults;
    }
    while ((LPUART1->ISR & USART_ISR_RXNE_RXFNE)!=0u) {
        uint8_t byte=(uint8_t)LPUART1->RDR;
        uint32_t next=(rx_head+1u)&127u;
        if (next==rx_tail) { ++rx_faults; continue; }
        rx_ring[rx_head]=byte; __DMB(); rx_head=next;
    }
}
static uint32_t now(void *context) { (void)context; return HAL_GetTick(); }
static bool busy(void *context)
{ (void)context; return HAL_GPIO_ReadPin(GPIOA, GPIO_PIN_12) == GPIO_PIN_SET; }
static bool allow_recovery(void *context)
{ (void)context; return qualified_target && __get_IPSR() == 0u && !spi_owned; }
static void say(const char *format, ...)
{
    char line[420]; va_list args; va_start(args, format);
    int n = vsnprintf(line, sizeof(line), format, args); va_end(args);
    if (n < 0 || !uart_ok) return;
    uint16_t count = (uint16_t)((size_t)n < sizeof(line) ? (size_t)n : sizeof(line)-1u);
    (void)HAL_UART_Transmit(&uart, (const uint8_t *)line, count, 100u);
}
static bool identity(void)
{
    const uint8_t expected[12] = {0x18,0,0x10,0,0x0d,0x50,0x33,0x57,0x54,0x36,0x37,0x20};
    return (DBGMCU->IDCODE & 0xFFFu) == 0x492u &&
        *(const uint16_t *)FLASHSIZE_BASE == 512u &&
        (FLASH->OPTR & FLASH_OPTR_TZEN) == 0u &&
        !memcmp((const void *)UID_BASE, expected, sizeof(expected));
}
static void hello(void)
{
    const uint8_t *u = (const uint8_t *)UID_BASE;
    say("HELLO id=" DIAG_ID " uid=%02x%02x%02x%02x%02x%02x%02x%02x%02x%02x%02x%02x device=%03lx flash_kib=%u hclk=%lu target_ok=%u ran=%u rx_faults=%lu\r\n",
        u[0],u[1],u[2],u[3],u[4],u[5],u[6],u[7],u[8],u[9],u[10],u[11],
        (unsigned long)(DBGMCU->IDCODE & 0xFFFu), *(const uint16_t *)FLASHSIZE_BASE,
        (unsigned long)SystemCoreClock, qualified_target, ran, (unsigned long)rx_faults);
}
static bool transfer(void *context, bool data, const uint8_t *bytes, uint16_t n)
{
    (void)context;
    if (!qualified_target || !bytes || n == 0u || spi_owned || __get_IPSR() != 0u)
        return false;
    spi_owned = true;
    /* Exact software-SPI branch of comp_v11_hal_panel_transfer(). There is
     * no caller scheduling, display-rail controller or alternate slave here. */
    panel_gpio_begin();
    HAL_GPIO_WritePin(GPIOB, GPIO_PIN_15, GPIO_PIN_SET);
    HAL_GPIO_WritePin(GPIOA, GPIO_PIN_11, data ? GPIO_PIN_SET : GPIO_PIN_RESET);
    HAL_GPIO_WritePin(GPIOB, GPIO_PIN_0, GPIO_PIN_RESET);
    panel_gpio_delay();
#if COMP_SCREEN_FIXED_GPIO_MONITOR
    gpio_data=data;
    gpio_check(0u,false,false,true);
    const bool register_packet=!(data && panel.stage==11u);
    for (uint16_t i=0u;i<n;++i) {
        if (register_packet) monitored_command_send(bytes[i]);
        else panel_gpio_send(bytes[i]);
    }
#else
    for (uint16_t i = 0u; i < n; ++i) panel_gpio_send(bytes[i]);
#endif
    panel_gpio_end();
    HAL_GPIO_WritePin(GPIOB, GPIO_PIN_0, GPIO_PIN_SET);
#if COMP_SCREEN_FIXED_GPIO_MONITOR
    gpio_check(3u,false,(bytes[n-1u]&1u)!=0u,false);
#endif
    spi_owned = false;
    /* Record after CS is released. UART stays silent throughout ACTIVE. */
    if (event_count < EVENT_LIMIT) {
        bus_event_t *e = &events[event_count++];
        e->tick = HAL_GetTick(); e->bytes = n; e->data = data;
        e->stage = panel.stage; e->sequence = panel.sequence;
        e->ram_phase = panel.recording_phase; e->fnv = 2166136261u;
        for (uint16_t i = 0u; i < n; ++i) {
            e->fnv = (e->fnv ^ bytes[i]) * 16777619u;
            if (i < sizeof(e->head)) e->head[i] = bytes[i];
        }
    } else ++event_overflow;
    return true;
}
static void frame(unsigned variant)
{
    memset(current_frame, 0xFF, sizeof(current_frame));
    /* Two simple eye rectangles; B moves them eight pixels. All coordinates
     * are controller-buffer coordinates, without a resource renderer. */
    for (unsigned y = 72u; y < 96u; ++y) {
        for (unsigned x = 6u + variant; x < 9u + variant; ++x)
            current_frame[y * 25u + x] = 0u;
        for (unsigned x = 15u + variant; x < 18u + variant; ++x)
            current_frame[y * 25u + x] = 0u;
    }
}
static bool run_frame(unsigned variant)
{
    frame(variant);
    const comp_ssd1681_wba_window_t w = {6u,18u,72u,95u};
    const uint32_t started = HAL_GetTick();
    bool accepted = variant == 0u ?
        comp_ssd1681_wba_start_full(&panel, previous_frame, current_frame, 5000u) :
        comp_ssd1681_wba_start_partial_pair(&panel, previous_frame, current_frame, 5000u, &w);
    uint32_t polls = 0u, high = 0u, max_gap = 0u, last = started;
    while (accepted && comp_ssd1681_wba_status(&panel) == COMP_SSD1681_WBA_ACTIVE &&
           HAL_GetTick() - started < 12000u) {
        uint32_t tick = HAL_GetTick(), gap = tick-last; last=tick;
        if (gap > max_gap) max_gap = gap;
        ++polls; if (busy(NULL)) ++high;
        comp_ssd1681_wba_poll(&panel);
        HAL_Delay(1u);
    }
    bool completed = accepted && comp_ssd1681_wba_status(&panel) == COMP_SSD1681_WBA_COMPLETE;
    if (comp_ssd1681_wba_status(&panel) == COMP_SSD1681_WBA_ACTIVE)
        comp_ssd1681_wba_cancel(&panel);
    const comp_ssd1681_wba_stats_t *s = &panel.stats;
    say("FRAME variant=%u accepted=%u complete=%u elapsed_ms=%lu polls=%lu high=%lu max_gap_ms=%lu status=%u error=%u stage=%u transfers=%lu bytes=%lu baseline=%u\r\n",
        variant, accepted, completed, (unsigned long)(HAL_GetTick()-started),
        (unsigned long)polls, (unsigned long)high, (unsigned long)max_gap,
        panel.status, panel.error, panel.stage, (unsigned long)s->transfer_calls,
        (unsigned long)s->transferred_bytes, panel.baseline_valid);
    say("VISIBLE variant=%u activations=%lu start_ms=%lu polls=%lu high=%lu max_gap_ms=%lu edges=%u miss_start_ms=%lu miss_ms=%lu miss_polls=%lu miss_high=%lu miss_edges=%u recoveries=%lu retries=%lu first_stage=%u first_error=%u first_ms=%lu\r\n",
        variant,(unsigned long)s->visible_activation_count,(unsigned long)s->visible_started_ms,
        (unsigned long)s->visible_poll_samples,(unsigned long)s->visible_high_samples,
        (unsigned long)s->visible_max_poll_gap_ms,s->visible_edge_flags,
        (unsigned long)s->missed_started_ms,(unsigned long)s->missed_at_ms,
        (unsigned long)s->missed_poll_samples,(unsigned long)s->missed_high_samples,
        s->missed_edge_flags,(unsigned long)s->activation_recoveries,
        (unsigned long)s->activation_retries,s->first_failure_stage,
        s->first_failure_error,(unsigned long)s->first_failure_ms);
    if (completed) memcpy(previous_frame, current_frame, sizeof(previous_frame));
    return completed;
}
static void ready_status(void)
{
    /* The manual does not require CLKEN for 0x2F. Do not issue extra 0x20,
     * VCI/HV detection or LUT commands to manufacture such a prerequisite.
     * Only try this after the fixed-frame result has already been recorded. */
    const uint32_t start = HAL_GetTick(); uint32_t quiet = start, highs = 0u, rises = 0u;
    (void)panel_take_busy_edges(NULL, COMP_SSD1681_WBA_BUSY_EDGES_ARM);
    bool ready = false;
    while (HAL_GetTick()-start < 250u) {
        uint32_t tick = HAL_GetTick(); bool level = busy(NULL);
        uint8_t edges = panel_take_busy_edges(NULL, COMP_SSD1681_WBA_BUSY_EDGES_SAMPLE);
        if (level) ++highs;
        if ((edges & 1u) != 0u) ++rises;
        if (level || (edges & 1u) != 0u) quiet = tick;
        else if (tick-quiet >= 20u) { ready=true; break; }
        HAL_Delay(1u);
    }
    if (!ready) {
        (void)panel_take_busy_edges(NULL, COMP_SSD1681_WBA_BUSY_EDGES_STOP);
        say("READ_STATUS sent=0 reason=READY_NOT_QUALIFIED elapsed_ms=%lu high_samples=%lu rising_intervals=%lu\r\n",
            (unsigned long)(HAL_GetTick()-start),(unsigned long)highs,(unsigned long)rises);
        return;
    }
    uint8_t value[2]={0u,0u}; unsigned reads=0u; bool edge_seen=false;
    for (; reads < 2u; ++reads) {
        if (busy(NULL) || (panel_take_busy_edges(NULL, COMP_SSD1681_WBA_BUSY_EDGES_SAMPLE)&1u)!=0u)
            break;
        panel_gpio_read_begin(0x2Fu);
        value[reads] = panel_gpio_receive(); panel_gpio_end();
        edge_seen |= (panel_take_busy_edges(NULL, COMP_SSD1681_WBA_BUSY_EDGES_SAMPLE)&1u)!=0u;
        if (edge_seen) { ++reads; break; }
    }
    (void)panel_take_busy_edges(NULL, COMP_SSD1681_WBA_BUSY_EDGES_STOP);
    /* High status bits include power flags whose sense commands were NOT
     * issued; report raw bytes and only the documented ID/reserved/busy bits. */
    bool id_valid = reads==2u && !edge_seen && value[0]==value[1] &&
        (value[0]&0xCFu)==0x01u;
    say("READ_STATUS sent=%u raw=%02X,%02X id_ready_valid=%u rising_seen=%u\r\n",
        reads,value[0],value[1],id_valid,edge_seen);
}
#if COMP_SCREEN_BUS_ISOLATION || COMP_SCREEN_HELD_CONTROL
/* Distinguish autonomous BUSY activity from coupling to a particular MCU
 * output. No command byte or panel activation is sent. Clock/data/DC move
 * only with BOTH CS high; CS alone moves only while SCK stays low. Digital
 * samples do not prove the voltages or reception on the panel side. */
#define ISO_CYCLES 2048u
#if COMP_SCREEN_HELD_CONTROL
#define ISO_PHASES 5u
#else
#define ISO_PHASES 9u
#endif
typedef struct {
    uint32_t samples, high[4], rises[4], falls[4];
    uint32_t elapsed, last_cycle, max_gap, last_change, longest_high, longest_low;
    uint8_t signal, idr_mismatch, odr_mismatch, first_expected, first_idr, first_odr;
    bool last_busy, aborted;
} isolation_phase_t;
static isolation_phase_t isolation[ISO_PHASES];
static uint8_t isolation_outputs(uint32_t a, uint32_t b)
{
    return (uint8_t)(((b >> 0u)&1u) | (((a >> 11u)&1u)<<1u) |
        (((b >> 4u)&1u)<<2u) | (((a >> 15u)&1u)<<3u) | (((b >> 15u)&1u)<<4u));
}
static void isolation_park(void)
{
    /* Deselect first; no clock edge is produced with CS low. */
    HAL_GPIO_WritePin(GPIOB,GPIO_PIN_0|GPIO_PIN_15,GPIO_PIN_SET);
    HAL_GPIO_WritePin(GPIOB,GPIO_PIN_4,GPIO_PIN_RESET);
    HAL_GPIO_WritePin(GPIOA,GPIO_PIN_11,GPIO_PIN_SET);
    HAL_GPIO_WritePin(GPIOA,GPIO_PIN_15,GPIO_PIN_RESET);
}
static bool isolation_sample(isolation_phase_t *p, unsigned offset, uint8_t expected)
{
    uint32_t cycle=DWT->CYCCNT, a=GPIOA->IDR, b=GPIOB->IDR;
    uint8_t idr=isolation_outputs(a,b), odr=isolation_outputs(GPIOA->ODR,GPIOB->ODR);
    bool level=(a&GPIO_PIN_12)!=0u;
    uint32_t gap=cycle-p->last_cycle; p->last_cycle=cycle;
    if (gap>p->max_gap) p->max_gap=gap;
    if (level!=p->last_busy) {
        uint32_t span=cycle-p->last_change;
        if (p->last_busy && span>p->longest_high) p->longest_high=span;
        if (!p->last_busy && span>p->longest_low) p->longest_low=span;
        p->last_busy=level; p->last_change=cycle;
    }
    ++p->samples; if (level) ++p->high[offset];
    uint8_t edges=panel_take_busy_edges(NULL,COMP_SSD1681_WBA_BUSY_EDGES_SAMPLE);
    if ((edges&1u)!=0u) ++p->rises[offset];
    if ((edges&2u)!=0u) ++p->falls[offset];
    if (idr!=expected || odr!=expected) {
        p->first_expected=expected; p->first_idr=idr; p->first_odr=odr;
        p->idr_mismatch|=(uint8_t)(idr^expected); p->odr_mismatch|=(uint8_t)(odr^expected);
        p->aborted=true; return false;
    }
    return true;
}
static void run_bus_isolation(void)
{
    /* Interleave quiet controls with SCK, SDIN, DC, then CS-only stimulus.
     * Each cycle samples immediately after the write and after the original
     * 64-NOP delay, for requested low and high. Quiet controls make no writes. */
#if COMP_SCREEN_HELD_CONTROL
    static const uint8_t signals[ISO_PHASES]={255u,1u,255u,0u,255u};
    static const char *const names[ISO_PHASES]={"QUIET0","DC_LOW_CS_HIGH","QUIET1","CS_LOW_DC_HIGH","QUIET2"};
#else
    static const uint8_t signals[ISO_PHASES]={255u,2u,255u,3u,255u,1u,255u,0u,255u};
    static const char *const names[ISO_PHASES]={"QUIET0","SCK","QUIET1","SDIN","QUIET2","DC","QUIET3","CS_NO_CLOCK","QUIET4"};
#endif
    isolation_park();
    CoreDebug->DEMCR|=CoreDebug_DEMCR_TRCENA_Msk;
    DWT->CTRL|=DWT_CTRL_CYCCNTENA_Msk;
    uint32_t check=DWT->CYCCNT; panel_gpio_delay();
    if (DWT->CYCCNT==check) {
        say("END id=" DIAG_ID " result=CYCLE_COUNTER_UNAVAILABLE panel_commands=0 screen_fixed=0\r\n"); return;
    }
    say("BEGIN id=" DIAG_ID " panel_commands=0 phases=%u cycles=2048 held_control=%u delay_nops=64 mcu_digital_only=1\r\n",ISO_PHASES,COMP_SCREEN_HELD_CONTROL);
    HAL_Delay(20u);
    bool ok=true; unsigned count=0u;
    (void)panel_take_busy_edges(NULL,COMP_SSD1681_WBA_BUSY_EDGES_ARM);
    for (; count<ISO_PHASES; ++count) {
        isolation_phase_t *p=&isolation[count]; p->signal=signals[count];
        isolation_park(); panel_gpio_delay();
        (void)panel_take_busy_edges(NULL,COMP_SSD1681_WBA_BUSY_EDGES_SAMPLE);
        uint32_t start=DWT->CYCCNT;
        p->last_cycle=p->last_change=start; p->last_busy=busy(NULL);
        uint8_t mask=p->signal==255u ? 0u : (uint8_t)(1u<<p->signal);
        GPIO_TypeDef *port=(p->signal==0u || p->signal==2u) ? GPIOB : GPIOA;
        uint16_t pin=p->signal==0u ? GPIO_PIN_0 : p->signal==1u ? GPIO_PIN_11 :
            p->signal==2u ? GPIO_PIN_4 : GPIO_PIN_15;
#if COMP_SCREEN_HELD_CONTROL
        if (mask) HAL_GPIO_WritePin(port,pin,GPIO_PIN_RESET);
        const uint8_t held=(uint8_t)(19u&~mask);
#endif
        for (unsigned i=0u; i<ISO_CYCLES; ++i) {
#if COMP_SCREEN_HELD_CONTROL
            if (!isolation_sample(p,0u,held)) break;
            panel_gpio_delay(); if (!isolation_sample(p,1u,held)) break;
            if (!isolation_sample(p,2u,held)) break;
            panel_gpio_delay(); if (!isolation_sample(p,3u,held)) break;
#else
            if (mask) HAL_GPIO_WritePin(port,pin,GPIO_PIN_RESET);
            uint8_t low=(uint8_t)(19u&~mask);
            if (!isolation_sample(p,0u,low)) break;
            panel_gpio_delay(); if (!isolation_sample(p,1u,low)) break;
            if (mask) HAL_GPIO_WritePin(port,pin,GPIO_PIN_SET);
            uint8_t high=(uint8_t)(19u|mask);
            if (!isolation_sample(p,2u,high)) break;
            panel_gpio_delay(); if (!isolation_sample(p,3u,high)) break;
#endif
        }
        p->elapsed=DWT->CYCCNT-start;
        uint32_t span=DWT->CYCCNT-p->last_change;
        if (p->last_busy && span>p->longest_high) p->longest_high=span;
        if (!p->last_busy && span>p->longest_low) p->longest_low=span;
        if (p->aborted) { ok=false; ++count; break; }
#if COMP_SCREEN_HELD_CONTROL
        if (!mask && (p->elapsed<SystemCoreClock/50u || p->high[0] || p->high[1] || p->high[2] || p->high[3] ||
                      p->rises[0] || p->rises[1] || p->rises[2] || p->rises[3])) {
            ok=false; ++count; break; /* No next stimulus without20ms quiet. */
        }
#endif
    }
    isolation_park();
    (void)panel_take_busy_edges(NULL,COMP_SSD1681_WBA_BUSY_EDGES_STOP);
    for (unsigned i=0u;i<count;++i) {
        const isolation_phase_t *p=&isolation[i];
        say("PIN_PHASE i=%u name=%s samples=%lu high=%lu,%lu,%lu,%lu rises=%lu,%lu,%lu,%lu falls=%lu,%lu,%lu,%lu elapsed_cycles=%lu max_gap_cycles=%lu high_run_cycles=%lu low_run_cycles=%lu idr_xor=%02X odr_xor=%02X aborted=%u\r\n",
            i,names[i],(unsigned long)p->samples,(unsigned long)p->high[0],(unsigned long)p->high[1],(unsigned long)p->high[2],(unsigned long)p->high[3],
            (unsigned long)p->rises[0],(unsigned long)p->rises[1],(unsigned long)p->rises[2],(unsigned long)p->rises[3],
            (unsigned long)p->falls[0],(unsigned long)p->falls[1],(unsigned long)p->falls[2],(unsigned long)p->falls[3],
            (unsigned long)p->elapsed,(unsigned long)p->max_gap,(unsigned long)p->longest_high,(unsigned long)p->longest_low,
            p->idr_mismatch,p->odr_mismatch,p->aborted);
        if (p->aborted) say("PIN_ABORT expected=%02X idr=%02X odr=%02X\r\n",p->first_expected,p->first_idr,p->first_odr);
    }
    say("END id=" DIAG_ID " result=%s phases=%u panel_commands=0 cs_clocked_bytes=0 transfers=%lu screen_fixed=0 physical_ghosting=NOT_VERIFIED\r\n",
        ok ? "BUS_ISOLATION_CAPTURED" : "OUTPUT_OR_QUIET_QUALIFICATION_STOPPED",count,(unsigned long)event_count);
}
#endif
#if COMP_SCREEN_STATUS_PHASE
/* One documented read-only command after qualified quiet, with per-bit MCU
 * digital observations. This is not a repeated full-refresh/profile trial.
 * Stop further clocks at the first high BUSY or rising latch; never substitute
 * an edge for a visible activation, or enable clock/analog rails for a read. */
typedef struct {
    uint32_t cycle, tick;
    uint8_t phase, bit, idr, odr, expected, mask, edges, level;
} status_sample_t;
static status_sample_t status_samples[64];
static unsigned status_sample_count;
static bool status_observe(uint8_t phase, uint8_t bit, uint8_t expected, uint8_t mask)
{
    if (status_sample_count>=64u) return false;
    status_sample_t *s=&status_samples[status_sample_count++];
    s->cycle=DWT->CYCCNT; s->tick=HAL_GetTick(); s->phase=phase; s->bit=bit;
    uint32_t a=GPIOA->IDR,b=GPIOB->IDR;
    s->idr=(uint8_t)(((b>>0u)&1u)|(((a>>11u)&1u)<<1u)|(((b>>4u)&1u)<<2u)|(((a>>15u)&1u)<<3u)|(((b>>15u)&1u)<<4u));
    a=GPIOA->ODR;b=GPIOB->ODR;
    s->odr=(uint8_t)(((b>>0u)&1u)|(((a>>11u)&1u)<<1u)|(((b>>4u)&1u)<<2u)|(((a>>15u)&1u)<<3u)|(((b>>15u)&1u)<<4u));
    s->expected=expected; s->mask=mask;
    s->level=(uint8_t)((GPIOA->IDR&GPIO_PIN_12)!=0u);
    s->edges=panel_take_busy_edges(NULL,COMP_SSD1681_WBA_BUSY_EDGES_SAMPLE);
    return !s->level && (s->edges&1u)==0u &&
        ((s->idr^expected)&mask)==0u && ((s->odr^expected)&mask)==0u;
}
static void run_status_phase(void)
{
    CoreDebug->DEMCR|=CoreDebug_DEMCR_TRCENA_Msk; DWT->CTRL|=DWT_CTRL_CYCCNTENA_Msk;
    (void)panel_take_busy_edges(NULL,COMP_SSD1681_WBA_BUSY_EDGES_ARM);
    uint32_t start=HAL_GetTick(),quiet=start,highs=0u,rises=0u;
    bool ready=false;
    while (HAL_GetTick()-start<250u) {
        uint32_t tick=HAL_GetTick(); bool level=busy(NULL);
        uint8_t edges=panel_take_busy_edges(NULL,COMP_SSD1681_WBA_BUSY_EDGES_SAMPLE);
        if (level) ++highs;
        if ((edges&1u)!=0u) ++rises;
        if (level || (edges&1u)!=0u) quiet=tick;
        else if (tick-quiet>=20u) { ready=true; break; }
        HAL_Delay(1u);
    }
    uint32_t elapsed=HAL_GetTick()-start;
    unsigned command_bits=0u,read_bits=0u; uint8_t raw_low=0u,raw_high=0u;
    uint32_t selected_elapsed=0u;
    bool ok=ready;
    if (ok) {
        panel_gpio_begin(); ok=status_observe(0u,255u,19u,31u);
        if (ok) {
            HAL_GPIO_WritePin(GPIOA,GPIO_PIN_11,GPIO_PIN_RESET);
            ok=status_observe(1u,255u,17u,31u);
        }
        if (ok) {
            HAL_GPIO_WritePin(GPIOB,GPIO_PIN_0,GPIO_PIN_RESET); panel_gpio_delay();
            ok=status_observe(2u,255u,16u,31u);
        }
#if COMP_SCREEN_SELECTED_QUIET_MS == 20
        /* Exactly one changed factor versus V4: both CS-low and DC-low are
         * held for20ms before any clock. A rising latch still vetoes the run;
         * waiting must not hide/forgive BUSY activity during selection. */
        uint32_t selected_start=HAL_GetTick();
        while (ok) {
            ok=status_observe(9u,255u,16u,31u);
            selected_elapsed=HAL_GetTick()-selected_start;
            if (!ok || selected_elapsed>=COMP_SCREEN_SELECTED_QUIET_MS) break;
            HAL_Delay(1u);
        }
#endif
        uint8_t command=0x2Fu;
        for (unsigned i=0u;ok && i<8u;++i) {
            bool output=(command&0x80u)!=0u;
            HAL_GPIO_WritePin(GPIOB,GPIO_PIN_4,GPIO_PIN_RESET);
            HAL_GPIO_WritePin(GPIOA,GPIO_PIN_15,output ? GPIO_PIN_SET : GPIO_PIN_RESET);
            panel_gpio_delay(); ok=status_observe(3u,(uint8_t)i,(uint8_t)(16u|(output ? 8u : 0u)),31u);
            if (!ok) break;
            HAL_GPIO_WritePin(GPIOB,GPIO_PIN_4,GPIO_PIN_SET); panel_gpio_delay();
            ++command_bits;
            ok=status_observe(4u,(uint8_t)i,(uint8_t)(20u|(output ? 8u : 0u)),31u);
            command<<=1u;
        }
        if (ok) {
            /* Same handoff order as panel_gpio_read_begin(), after the last
             * command rising edge. Added observations extend bit periods. */
            HAL_GPIO_WritePin(GPIOA,GPIO_PIN_11,GPIO_PIN_SET); panel_gpio_delay();
            ok=status_observe(5u,255u,30u,31u);
        }
        if (ok) {
            gpio(GPIOA,GPIO_PIN_15,GPIO_MODE_INPUT,GPIO_NOPULL,0u);
            panel_gpio_reading=true; panel_gpio_delay();
            ok=status_observe(6u,255u,22u,23u); /* SDA is now a target output. */
        }
        for (unsigned i=0u;ok && i<8u;++i) {
            HAL_GPIO_WritePin(GPIOB,GPIO_PIN_4,GPIO_PIN_RESET); panel_gpio_delay();
            ok=status_observe(7u,(uint8_t)i,18u,23u);
            if (!ok) break;
            raw_low=(uint8_t)((raw_low<<1u)|((status_samples[status_sample_count-1u].idr>>3u)&1u));
            HAL_GPIO_WritePin(GPIOB,GPIO_PIN_4,GPIO_PIN_SET); panel_gpio_delay();
            ok=status_observe(8u,(uint8_t)i,22u,23u);
            raw_high=(uint8_t)((raw_high<<1u)|((status_samples[status_sample_count-1u].idr>>3u)&1u));
            ++read_bits;
        }
        panel_gpio_end();
    }
    (void)panel_take_busy_edges(NULL,COMP_SSD1681_WBA_BUSY_EDGES_STOP);
    say("STATUS_READY qualified=%u elapsed_ms=%lu high=%lu rising_intervals=%lu timeout_ms=250 stable_ms=20\r\n",
        ready,(unsigned long)elapsed,(unsigned long)highs,(unsigned long)rises);
    for (unsigned i=0u;i<status_sample_count;++i) {
        const status_sample_t *s=&status_samples[i];
        say("STATUS_PHASE i=%u cycle=%lu ms=%lu phase=%u bit=%u idr=%02X odr=%02X expected=%02X mask=%02X busy=%u edges=%u\r\n",
            i,(unsigned long)s->cycle,(unsigned long)s->tick,s->phase,s->bit,s->idr,s->odr,s->expected,s->mask,s->level,s->edges);
    }
    bool documented=ok && read_bits==8u && raw_low==raw_high && (raw_high&0xCFu)==0x01u;
    say("END id=" DIAG_ID " result=%s ready=%u selected_quiet_ms=%u selected_elapsed_ms=%lu command_bits=%u read_bits=%u raw_low=%02X raw_high=%02X documented_bits_match=%u activations=0 screen_fixed=0 physical_ghosting=NOT_VERIFIED\r\n",
        ok ? "READ_ONLY_PHASE_CAPTURED" : ready ? "BUSY_OR_GPIO_CHANGED_STOPPED" : "READY_NOT_QUALIFIED",ready,
        COMP_SCREEN_SELECTED_QUIET_MS,(unsigned long)selected_elapsed,command_bits,read_bits,raw_low,raw_high,documented);
}
#endif
static void run(void)
{
    if (ran || !qualified_target) { say("ERROR reason=RUN_ALREADY_USED_OR_TARGET_INVALID\r\n"); return; }
    ran=true;
    gpio(GPIOA,GPIO_PIN_12,GPIO_MODE_IT_RISING_FALLING,GPIO_NOPULL,0u);
    HAL_NVIC_DisableIRQ(EXTI12_IRQn);
    CLEAR_BIT(EXTI->IMR1,GPIO_PIN_12); CLEAR_BIT(EXTI->EMR1,GPIO_PIN_12);
#if COMP_SCREEN_BUS_ISOLATION || COMP_SCREEN_HELD_CONTROL
    run_bus_isolation(); return;
#endif
#if COMP_SCREEN_STATUS_PHASE
    run_status_phase(); return;
#endif
    comp_ssd1681_wba_config_t cfg={0};
    cfg.transfer=transfer; cfg.is_busy=busy; cfg.now_ms=now;
    cfg.payload_chunk_bytes=128u; cfg.busy_timeout_ms=5000u; cfg.partial_limit=255u;
    cfg.reset_mode=COMP_SSD1681_WBA_RESET_SOFTWARE_ONLY;
    cfg.allow_mode2_recovery=allow_recovery; cfg.take_busy_edges=panel_take_busy_edges;
    bool initialized=comp_ssd1681_wba_init(&panel,&cfg);
    memset(previous_frame,0xFF,sizeof(previous_frame));
    say("BEGIN id=" DIAG_ID " driver=FW172_SOURCE spi=PRODUCT_GPIO_ORDER gpio_monitor=%u delay_nops=64 timeout_ms=5000 poll_delay_ms=1 reset=SOFTWARE_ONLY panel_power_retained=1\r\n",COMP_SCREEN_FIXED_GPIO_MONITOR);
    bool a=initialized && run_frame(0u), b=false;
    if (a) { HAL_Delay(1500u); b=run_frame(1u); }
    else say("FRAME variant=1 accepted=0 reason=NO_QUALIFIED_BASELINE\r\n");
    ready_status();
#if COMP_SCREEN_FIXED_GPIO_MONITOR
    say("GPIO_CHECK samples=%lu command_bytes=%lu busy_high=%lu idr_mismatch=%lu,%lu,%lu,%lu,%lu odr_mismatch=%lu,%lu,%lu,%lu,%lu map=CS,DC,SCK,SDIN,IMU_CS timing=INSTRUMENTED_MCU_DIGITAL_ONLY\r\n",
        (unsigned long)gpio_samples,(unsigned long)gpio_command_bytes,(unsigned long)gpio_busy_high,
        (unsigned long)gpio_idr_mismatch[0],(unsigned long)gpio_idr_mismatch[1],(unsigned long)gpio_idr_mismatch[2],(unsigned long)gpio_idr_mismatch[3],(unsigned long)gpio_idr_mismatch[4],
        (unsigned long)gpio_odr_mismatch[0],(unsigned long)gpio_odr_mismatch[1],(unsigned long)gpio_odr_mismatch[2],(unsigned long)gpio_odr_mismatch[3],(unsigned long)gpio_odr_mismatch[4]);
    for (unsigned i=0u;i<gpio_retained;++i) {
        const gpio_sample_t *g=&gpio_first_mismatch[i];
        say("GPIO_MISMATCH i=%u ms=%lu phase=%u expected=%02X idr=%02X odr=%02X\r\n",
            i,(unsigned long)g->tick,g->phase,g->expected,g->idr,g->odr);
    }
#endif
    say("BUS_BEGIN count=%lu overflow=%lu\r\n",(unsigned long)event_count,(unsigned long)event_overflow);
    for (uint32_t i=0u; i<event_count; ++i) {
        const bus_event_t *e=&events[i];
        say("BUS i=%lu ms=%lu dc=%u n=%u head=%02X%02X%02X%02X fnv=%08lx stage=%u seq=%u ram_phase=%u\r\n",
            (unsigned long)i,(unsigned long)e->tick,e->data,e->bytes,
            e->head[0],e->head[1],e->head[2],e->head[3],(unsigned long)e->fnv,
            e->stage,e->sequence,e->ram_phase);
    }
    say("END id=" DIAG_ID " result=%s a=%u b=%u screen_fixed=0 physical_ghosting=NOT_VERIFIED\r\n",
        a && b ? "TWO_FIXED_FRAMES_COMPLETED" : "FIXED_FRAME_REFRESH_FAILED",a,b);
}
int main(void)
{
    SCB->VTOR=0x08000000u;
    comp_v11_panel_boot_idle();
    __enable_irq(); if (HAL_Init()!=HAL_OK) for(;;)__NOP();
    OTP_Data_s *otp=NULL;
    HAL_RCCEx_HSESetTrimming(OTP_Read(DEFAULT_OTP_IDX,&otp)==HAL_OK ? otp->hsetune : 0x0Cu);
    bool clock_ok=clocks();
    SystemCoreClockUpdate(); (void)HAL_InitTick(15u);
    gpio(GPIOA,GPIO_PIN_1|GPIO_PIN_2,GPIO_MODE_AF_PP,GPIO_PULLUP,GPIO_AF8_LPUART1);
    __HAL_RCC_LPUART1_CONFIG(RCC_LPUART1CLKSOURCE_HSI); __HAL_RCC_LPUART1_CLK_ENABLE();
    uart.Instance=LPUART1; uart.Init.BaudRate=115200u; uart.Init.WordLength=UART_WORDLENGTH_8B;
    uart.Init.StopBits=UART_STOPBITS_1; uart.Init.Parity=UART_PARITY_NONE;
    uart.Init.Mode=UART_MODE_TX_RX; uart.Init.HwFlowCtl=UART_HWCONTROL_NONE;
    uart.Init.ClockPrescaler=UART_PRESCALER_DIV1;
    uart_ok=HAL_UART_Init(&uart)==HAL_OK && HAL_UARTEx_EnableFifoMode(&uart)==HAL_OK;
    if (uart_ok) {
        HAL_NVIC_SetPriority(LPUART1_IRQn,3u,0u); HAL_NVIC_EnableIRQ(LPUART1_IRQn);
        SET_BIT(LPUART1->CR1,USART_CR1_RXNEIE_RXFNEIE); SET_BIT(LPUART1->CR3,USART_CR3_EIE);
    }
    /* SystemCoreClock is the vendor's floating-point calculation; permit
     * its rounding while retaining the same PLL/dividers as production. */
    qualified_target=identity() && clock_ok && SystemCoreClock>98303000u && SystemCoreClock<98305000u;
    hello(); say("READY id=" DIAG_ID " clock_ok=%u commands=HELLO,RUN_ONCE\r\n",clock_ok);
    char line[24]; unsigned used=0u; bool overflow=false; uint32_t seen_faults=0u;
    for (;;) {
        IWDG->KR=0xAAAAu;
        if (seen_faults!=rx_faults) {
            __disable_irq(); seen_faults=rx_faults; rx_tail=rx_head; __enable_irq();
            used=0u; overflow=true;
        }
        if (rx_tail!=rx_head) {
            uint8_t byte=rx_ring[rx_tail]; __DMB(); rx_tail=(rx_tail+1u)&127u;
            if (byte=='\n' || byte=='\r') {
                line[used]='\0';
                if (!overflow && used) {
                    if (!strcmp(line,"HELLO")) hello();
                    else if (!strcmp(line,"RUN_ONCE")) run();
                    else say("ERROR reason=UNKNOWN_COMMAND\r\n");
                }
                used=0u; overflow=false;
            } else if (used+1u < sizeof(line)) line[used++]=(char)byte;
            else overflow=true;
        } else HAL_Delay(1u);
    }
}
