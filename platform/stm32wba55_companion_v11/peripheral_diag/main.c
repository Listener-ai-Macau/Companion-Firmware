/* Independent peripheral qualification, loaded into SRAM by an identity-gated
 * debugger. No product application, radio stack, SMPS/VOS change or internal
 * Flash write. A reset returns to the installed product. Results describe
 * transactions; physical hearing/vision/stimulus is still required. */
#include "stm32wbaxx_hal.h"
#include "spi_polling.h"
#include "spi_nor_stm32wba.h"
#include "wba_workspace_layout.h"
#include "lsm6dso.h"
#include "ft6336.h"
#include "wba_pdm_capture.h"
#include "ssd1681_wba.h"
#ifdef COMP_PERIPHERAL_VOICE_ONLY
#include "speaker_phrase_hq.h"
#else
#include "speaker_phrase.h"
#endif
#include <stdarg.h>
#include <stdio.h>
#include <string.h>

#define DIAG_ID "COMP_PERIPH_RAM_V1"
#define RAW_FRAME_BYTES 3840u
#define RAW_FRAMES 8u
#define NOR_SCRATCH 0xFFF000u
#define NOR_SECTOR 4096u
#define AUDIO_KERNEL_HZ 49151855u

static UART_HandleTypeDef uart;
static I2C_HandleTypeDef io_bus, touch_bus;
static SPI_HandleTypeDef spi1, spi3;
static SAI_HandleTypeDef sai_tx, sai_rx;
static DMA_HandleTypeDef dma_tx, dma_rx;
static companion_spi_nor_stm32wba_t nor;
static comp_lsm6dso_t imu;
static comp_ssd1681_wba_t panel;
static comp_wba_pdm_capture_t decoder;
static bool uart_ok, io_ok, spi1_ok, nor_ok, audio_ok, qualified_target;
static uint32_t audio_saved_hse_cr;
static uint8_t nor_backup[NOR_SECTOR], page[256];
static uint8_t before_frame[5000], after_frame[5000];
static uint32_t raw_words[RAW_FRAME_BYTES * RAW_FRAMES / 4u];
static int16_t tx_pcm[512u * 2u];
static volatile bool tx_done, rx_done, audio_error;
static uint32_t pcm_channel, pcm_sequence;
static bool key_armed;
static GPIO_PinState key_initial,key_stable,key_candidate;
static uint32_t key_candidate_ms,key_arm_ms,key_presses,key_releases,key_event_count;
static struct {uint32_t ms;uint8_t pressed;} key_events[12];
static bool imu_armed,imu_live_io_ok;
static uint32_t imu_arm_ms,imu_live_samples,imu_live_high,imu_live_low,imu_live_io_errors;
static bool touch_armed;
static uint32_t touch_arm_ms,touch_poll_ms,touch_live_reads,touch_live_contacts,touch_live_errors;
static uint32_t touch_live_io_errors,touch_irq_low,touch_irq_high;
/* Keep receiving commands while the foreground exports status/key events. */
static volatile uint8_t uart_rx[128];
static volatile uint32_t uart_rx_head,uart_rx_tail,uart_rx_faults;
void LPUART1_IRQHandler(void)
{
    uint32_t errors=LPUART1->ISR&(USART_ISR_ORE|USART_ISR_FE|USART_ISR_NE|USART_ISR_PE);
    if(errors){LPUART1->ICR=USART_ICR_ORECF|USART_ICR_FECF|USART_ICR_NECF|USART_ICR_PECF;++uart_rx_faults;}
    while(LPUART1->ISR&USART_ISR_RXNE_RXFNE) {
        uint8_t byte=(uint8_t)LPUART1->RDR;
        uint32_t next=(uart_rx_head+1u)&127u;
        if(next==uart_rx_tail){++uart_rx_faults;continue;}
        uart_rx[uart_rx_head]=byte;__DMB();uart_rx_head=next;
    }
}

extern void __real_SystemInit(void);
void __wrap_SystemInit(void)
{
    /* The original app was halted before SRAM loading. Suppress its pending
     * interrupts until our vectors, BSS, UART and HAL tick are ready. */
    __disable_irq();
    SysTick->CTRL = 0u;
    for (unsigned i = 0u; i < sizeof(NVIC->ICER) / sizeof(NVIC->ICER[0]); ++i) {
        NVIC->ICER[i] = UINT32_MAX;
        NVIC->ICPR[i] = UINT32_MAX;
    }
    SCB->ICSR = SCB_ICSR_PENDSTCLR_Msk | SCB_ICSR_PENDSVCLR_Msk;
    __real_SystemInit();
}

void SysTick_Handler(void) { HAL_IncTick(); IWDG->KR = 0xAAAAu; }
static void gpio(GPIO_TypeDef *port, uint32_t pins, uint32_t mode, uint32_t pull, uint32_t af)
{
    GPIO_InitTypeDef g = {0};
    g.Pin = pins; g.Mode = mode; g.Pull = pull;
    g.Speed = GPIO_SPEED_FREQ_HIGH; g.Alternate = af;
    HAL_GPIO_Init(port, &g);
}
static void say(const char *format, ...)
{
    char line[320];
    va_list args; va_start(args, format);
    int n = vsnprintf(line, sizeof(line), format, args); va_end(args);
    if (n < 0 || !uart_ok) return;
    size_t bytes = (size_t)n >= sizeof(line) ? sizeof(line) - 1u : (size_t)n;
    (void)HAL_UART_Transmit(&uart, (const uint8_t *)line, (uint16_t)bytes, 100u);
}
static uint32_t now(void *context) { (void)context; return HAL_GetTick(); }
static void delay(void *context, uint32_t ms) { (void)context; HAL_Delay(ms); }
static void finish(const char *name, const char *result)
{ say("END test=%s result=%s ms=%lu\r\n", name, result, (unsigned long)HAL_GetTick()); }
static bool identity(void)
{
    const uint8_t expected[12] = {0x18,0x00,0x10,0x00,0x0d,0x50,0x33,0x57,0x54,0x36,0x37,0x20};
    const uint8_t *uid = (const uint8_t *)UID_BASE;
    return (DBGMCU->IDCODE & 0xFFFu) == 0x492u &&
        *(const uint16_t *)FLASHSIZE_BASE == 512u &&
        (FLASH->OPTR & FLASH_OPTR_TZEN) == 0u && !memcmp(uid, expected, sizeof(expected));
}
static void hello(void)
{
    const uint8_t *u = (const uint8_t *)UID_BASE;
    say("HELLO id=" DIAG_ID " uid=%02x%02x%02x%02x%02x%02x%02x%02x%02x%02x%02x%02x device=%03lx flash_kib=%u hclk=%lu target_ok=%u rx_irq=1 rx_faults=%lu\r\n",
        u[0],u[1],u[2],u[3],u[4],u[5],u[6],u[7],u[8],u[9],u[10],u[11],
        (unsigned long)(DBGMCU->IDCODE & 0xFFFu), *(const uint16_t *)FLASHSIZE_BASE,
        (unsigned long)SystemCoreClock, qualified_target,(unsigned long)uart_rx_faults);
}
static bool i2c_init(I2C_HandleTypeDef *bus, I2C_TypeDef *instance, uint32_t timing)
{
    memset(bus, 0, sizeof(*bus)); bus->Instance = instance;
    bus->Init.Timing = timing; bus->Init.AddressingMode = I2C_ADDRESSINGMODE_7BIT;
    bus->Init.DualAddressMode = I2C_DUALADDRESS_DISABLE;
    bus->Init.OwnAddress2Masks = I2C_OA2_NOMASK;
    bus->Init.GeneralCallMode = I2C_GENERALCALL_DISABLE; bus->Init.NoStretchMode = I2C_NOSTRETCH_DISABLE;
    return HAL_I2C_Init(bus) == HAL_OK &&
        HAL_I2CEx_ConfigAnalogFilter(bus, I2C_ANALOGFILTER_ENABLE) == HAL_OK &&
        HAL_I2CEx_ConfigDigitalFilter(bus, 0u) == HAL_OK;
}
static bool i2c_read(I2C_HandleTypeDef *b, uint8_t address, uint8_t reg, uint8_t *p, uint16_t n)
{ return HAL_I2C_Mem_Read(b, (uint16_t)(address << 1), reg, I2C_MEMADD_SIZE_8BIT, p, n, 30u) == HAL_OK; }
static bool i2c_write(I2C_HandleTypeDef *b, uint8_t address, uint8_t reg, uint8_t value)
{ return HAL_I2C_Mem_Write(b, (uint16_t)(address << 1), reg, I2C_MEMADD_SIZE_8BIT, &value, 1u, 30u) == HAL_OK; }
static bool io_prepare(void)
{
    if (io_ok) return true;
    /* Release RESET without an asserted pulse. Never cycle the expander or
     * overwrite all its output bits: P4 is the assembled always-on EPD rail. */
    HAL_GPIO_WritePin(GPIOB, GPIO_PIN_12, GPIO_PIN_SET);
    gpio(GPIOB, GPIO_PIN_12, GPIO_MODE_OUTPUT_PP, GPIO_NOPULL, 0u);
    gpio(GPIOC, GPIO_PIN_13, GPIO_MODE_INPUT, GPIO_PULLUP, 0u);
    gpio(GPIOA, GPIO_PIN_6 | GPIO_PIN_7, GPIO_MODE_AF_OD, GPIO_NOPULL, GPIO_AF4_I2C3);
    __HAL_RCC_I2C3_CONFIG(RCC_I2C3CLKSOURCE_HSI); __HAL_RCC_I2C3_CLK_ENABLE();
    io_ok = i2c_init(&io_bus, I2C3, 0x10422529u);
    return io_ok;
}
static bool io_snapshot(uint8_t regs[4])
{
    if (!io_prepare()) return false;
    for (uint8_t r = 0u; r < 4u; ++r) if (!i2c_read(&io_bus, 0x20u, r, regs+r, 1u)) return false;
    return true;
}
static bool io_bit(uint8_t mask, bool high)
{
    uint8_t regs[4];
    if ((mask != 0x02u && mask != 0x40u) || !io_snapshot(regs)) return false;
    uint8_t latch = high ? (uint8_t)(regs[1] | mask) : (uint8_t)(regs[1] & ~mask);
    /* Update the selected latch before enabling that one output. Other
     * directions, including P4/P7, retain their actual hardware state. */
    return i2c_write(&io_bus, 0x20u, 1u, latch) &&
        i2c_write(&io_bus, 0x20u, 3u, (uint8_t)(regs[3] & ~mask));
}
static void io_test(void)
{
    uint8_t r[4]; bool ok = io_snapshot(r);
    if (ok) say("IO input=%02x output=%02x polarity=%02x direction=%02x int_pin=%u\r\n",
        r[0],r[1],r[2],r[3],HAL_GPIO_ReadPin(GPIOC,GPIO_PIN_13));
    else say("IO error=%08lx\r\n", (unsigned long)HAL_I2C_GetError(&io_bus));
    finish("IO", ok ? "REGISTERS_READ_PHYSICAL_IO_PENDING" : "IO_ERROR");
}
static void key_test(void)
{
    gpio(GPIOB, GPIO_PIN_14, GPIO_MODE_INPUT, GPIO_PULLUP, 0u);
    say("BEGIN test=KEY duration_ms=60000 stop_after_transitions=6 initial=%u\r\n",HAL_GPIO_ReadPin(GPIOB,GPIO_PIN_14));
    uint32_t start = HAL_GetTick(), changes = 0u;
    GPIO_PinState last = HAL_GPIO_ReadPin(GPIOB, GPIO_PIN_14);
    while (HAL_GetTick()-start < 60000u) {
        GPIO_PinState v = HAL_GPIO_ReadPin(GPIOB, GPIO_PIN_14);
        if (v != last) {
            HAL_Delay(15u);
            if (HAL_GPIO_ReadPin(GPIOB, GPIO_PIN_14) == v) {
                last=v; ++changes; say("KEY ms=%lu pressed=%u\r\n",(unsigned long)HAL_GetTick(),v==GPIO_PIN_RESET);
            }
        }
        if(changes>=6u&&last==GPIO_PIN_SET)break;
        HAL_Delay(1u);
    }
    say("KEY transitions=%lu\r\n", (unsigned long)changes);
    finish("KEY", changes >= 2u && last==GPIO_PIN_SET ? "PRESS_RELEASE_OBSERVED" : "NO_COMPLETE_PRESS_RELEASE");
}
static void key_arm(void)
{
    gpio(GPIOB,GPIO_PIN_14,GPIO_MODE_INPUT,GPIO_PULLUP,0u);
    key_initial=key_stable=key_candidate=HAL_GPIO_ReadPin(GPIOB,GPIO_PIN_14);
    key_candidate_ms=key_arm_ms=HAL_GetTick();key_presses=key_releases=key_event_count=0u;
    memset(key_events,0,sizeof(key_events));key_armed=true;
    say("KEY_STATUS armed=1 initial=%u stable=%u presses=0 releases=0 elapsed_ms=0 no_operator_deadline=1\r\n",key_initial,key_stable);
    finish("KEY_ARM","ARMED_AWAITING_OPERATOR");
}
static void key_poll(void)
{
    if(!key_armed)return;
    uint32_t tick=HAL_GetTick();GPIO_PinState input=HAL_GPIO_ReadPin(GPIOB,GPIO_PIN_14);
    if(input!=key_candidate){key_candidate=input;key_candidate_ms=tick;}
    if(input!=key_stable&&tick-key_candidate_ms>=15u) {
        key_stable=input;bool pressed=input==GPIO_PIN_RESET;
        if(pressed)++key_presses;else ++key_releases;
        if(key_event_count<12u){key_events[key_event_count].ms=tick;key_events[key_event_count].pressed=pressed;}
        say("KEY_EVENT index=%lu ms=%lu pressed=%u\r\n",(unsigned long)key_event_count,(unsigned long)tick,pressed);
        ++key_event_count;
    }
}
static void key_status(void)
{
    key_poll();
    say("KEY_STATUS armed=%u initial=%u stable=%u live=%u presses=%lu releases=%lu events=%lu elapsed_ms=%lu no_operator_deadline=1\r\n",
        key_armed,key_initial,key_stable,HAL_GPIO_ReadPin(GPIOB,GPIO_PIN_14),(unsigned long)key_presses,
        (unsigned long)key_releases,(unsigned long)key_event_count,(unsigned long)(HAL_GetTick()-key_arm_ms));
    for(uint32_t i=0u;i<key_event_count&&i<12u;++i)say("KEY_EVENT index=%lu ms=%lu pressed=%u\r\n",
        (unsigned long)i,(unsigned long)key_events[i].ms,key_events[i].pressed);
    finish("KEY_STATUS",key_initial==GPIO_PIN_SET&&key_presses>=3u&&key_releases>=3u&&key_stable==GPIO_PIN_SET?
        "THREE_PRESS_RELEASE_OBSERVED":"AWAITING_OPERATOR");
}
static bool shared_spi(void)
{
    if (spi1_ok) return true;
    HAL_GPIO_WritePin(GPIOB, GPIO_PIN_0 | GPIO_PIN_15, GPIO_PIN_SET);
    gpio(GPIOB, GPIO_PIN_0 | GPIO_PIN_15, GPIO_MODE_OUTPUT_PP, GPIO_NOPULL, 0u);
    HAL_GPIO_WritePin(GPIOA, GPIO_PIN_11, GPIO_PIN_SET);
    gpio(GPIOA, GPIO_PIN_11, GPIO_MODE_OUTPUT_PP, GPIO_NOPULL, 0u);
    gpio(GPIOA, GPIO_PIN_12, GPIO_MODE_INPUT, GPIO_NOPULL, 0u);
    gpio(GPIOA, GPIO_PIN_15, GPIO_MODE_AF_PP, GPIO_NOPULL, GPIO_AF5_SPI1);
    gpio(GPIOB, GPIO_PIN_3 | GPIO_PIN_4, GPIO_MODE_AF_PP, GPIO_NOPULL, GPIO_AF5_SPI1);
    __HAL_RCC_SPI1_CLK_ENABLE();
    memset(&spi1,0,sizeof(spi1)); spi1.Instance=SPI1;
    spi1.Init.Mode=SPI_MODE_MASTER; spi1.Init.Direction=SPI_DIRECTION_2LINES;
    spi1.Init.DataSize=SPI_DATASIZE_8BIT; spi1.Init.CLKPolarity=SPI_POLARITY_LOW;
    spi1.Init.CLKPhase=SPI_PHASE_1EDGE; spi1.Init.NSS=SPI_NSS_SOFT;
    spi1.Init.BaudRatePrescaler=SPI_BAUDRATEPRESCALER_16;
    spi1.Init.FirstBit=SPI_FIRSTBIT_MSB; spi1.Init.TIMode=SPI_TIMODE_DISABLE;
    spi1.Init.CRCCalculation=SPI_CRCCALCULATION_DISABLE; spi1.Init.NSSPMode=SPI_NSS_PULSE_DISABLE;
    spi1.Init.NSSPolarity=SPI_NSS_POLARITY_LOW; spi1.Init.FifoThreshold=SPI_FIFO_THRESHOLD_01DATA;
    spi1.Init.MasterKeepIOState=SPI_MASTER_KEEP_IO_STATE_ENABLE;
    spi1_ok=HAL_SPI_Init(&spi1)==HAL_OK; return spi1_ok;
}
static bool imu_xfer(uint8_t reg, uint8_t *rx, const uint8_t *tx, size_t n)
{
    HAL_GPIO_WritePin(GPIOB,GPIO_PIN_0,GPIO_PIN_SET);
    HAL_GPIO_WritePin(GPIOB,GPIO_PIN_15,GPIO_PIN_RESET);
    uint8_t command = rx ? (uint8_t)(reg | 0x80u) : reg;
    bool ok=comp_v11_spi_polling_transfer(&spi1,&command,NULL,1u,30u) &&
        comp_v11_spi_polling_transfer(&spi1,tx,rx,n,30u);
    HAL_GPIO_WritePin(GPIOB,GPIO_PIN_15,GPIO_PIN_SET); return ok;
}
static bool imu_read(void *c,uint8_t r,uint8_t *p,size_t n) { (void)c;return imu_xfer(r,p,NULL,n); }
static bool imu_write(void *c,uint8_t r,const uint8_t *p,size_t n) { (void)c;return imu_xfer(r,NULL,p,n); }
static void imu_live_arm(void)
{
    if(imu_armed){finish("IMU_ARM","ALREADY_ARMED");return;}
    if(!shared_spi()||!comp_lsm6dso_start(&imu,imu_read,imu_write,NULL,HAL_GetTick())) {
        finish("IMU_ARM","START_FAILED");return;
    }
    imu_arm_ms=HAL_GetTick();imu_live_samples=imu_live_high=imu_live_low=imu_live_io_errors=0u;
    imu_live_io_ok=io_prepare();imu_armed=true;
    say("IMU_STATUS armed=1 samples=0 errors=0 elapsed_ms=0 no_operator_deadline=1\r\n");
    finish("IMU_ARM","ARMED_AWAITING_OPERATOR");
}
static void imu_live_poll(void)
{
    if(!imu_armed)return;
    comp_imu_sample_t s;comp_imu_poll_t p=comp_lsm6dso_poll(&imu,HAL_GetTick(),&s);
    if(p==COMP_IMU_IO_ERROR){imu_armed=false;(void)comp_lsm6dso_stop(&imu);finish("IMU_LIVE","IO_ERROR");return;}
    if(p!=COMP_IMU_SAMPLE)return;
    uint8_t pins=0u;
    if(imu_live_io_ok) {
        if(i2c_read(&io_bus,0x20u,0u,&pins,1u)){if(pins&8u)++imu_live_high;else ++imu_live_low;}
        else {++imu_live_io_errors;imu_live_io_ok=false;}
    }
    ++imu_live_samples;
    say("IMU_LIVE ms=%lu ax=%d ay=%d az=%d gx=%ld gy=%ld gz=%ld temp_x10=%d io=%02x int=%u\r\n",
        (unsigned long)s.timestamp_ms,s.accel_mg[0],s.accel_mg[1],s.accel_mg[2],
        (long)s.gyro_mdps[0],(long)s.gyro_mdps[1],(long)s.gyro_mdps[2],s.temperature_c_x10,
        pins,HAL_GPIO_ReadPin(GPIOC,GPIO_PIN_13));
}
static void imu_live_status(void)
{
    say("IMU_STATUS armed=%u samples=%lu errors=%lu io_errors=%lu int1_high=%lu int1_low=%lu elapsed_ms=%lu no_operator_deadline=1\r\n",
        imu_armed,(unsigned long)imu_live_samples,(unsigned long)imu.errors,(unsigned long)imu_live_io_errors,
        (unsigned long)imu_live_high,(unsigned long)imu_live_low,(unsigned long)(HAL_GetTick()-imu_arm_ms));
    finish("IMU_STATUS",imu_armed?"CAPTURE_RUNNING":"NOT_RUNNING");
}
static void imu_live_stop(void)
{
    bool was_armed=imu_armed;imu_armed=false;
    bool stopped=!was_armed||comp_lsm6dso_stop(&imu);
    imu_live_status();finish("IMU_STOP",stopped?"STOPPED":"STOP_FAILED");
}
static void imu_test(void)
{
    say("BEGIN test=IMU duration_ms=45000 sample_rate_nominal=52\r\n");
    if (!shared_spi() || !comp_lsm6dso_start(&imu,imu_read,imu_write,NULL,HAL_GetTick())) {
        finish("IMU","START_FAILED"); return;
    }
    uint32_t start=HAL_GetTick(), samples=0u, int_high=0u, int_low=0u;
    bool ok=true; comp_imu_sample_t s;
    uint8_t first_pins=0u;
    bool expander_available=io_prepare()&&i2c_read(&io_bus,0x20u,0u,&first_pins,1u);
    while (HAL_GetTick()-start<45000u) {
        uint8_t pins=0u;
        if (expander_available) {
            expander_available=i2c_read(&io_bus,0x20u,0u,&pins,1u);
            if (expander_available) {if (pins&8u) ++int_high; else ++int_low;}
        }
        comp_imu_poll_t p=comp_lsm6dso_poll(&imu,HAL_GetTick(),&s);
        if (p==COMP_IMU_IO_ERROR) { ok=false;break; }
        if (p==COMP_IMU_SAMPLE) {
            ++samples;
            say("IMU ms=%lu ax=%d ay=%d az=%d gx=%ld gy=%ld gz=%ld temp_x10=%d io=%02x int=%u\r\n",
                (unsigned long)s.timestamp_ms,s.accel_mg[0],s.accel_mg[1],s.accel_mg[2],
                (long)s.gyro_mdps[0],(long)s.gyro_mdps[1],(long)s.gyro_mdps[2],s.temperature_c_x10,
                pins,HAL_GPIO_ReadPin(GPIOC,GPIO_PIN_13));
        }
        HAL_Delay(1u);
    }
    ok=comp_lsm6dso_stop(&imu)&&ok;
    say("IMU samples=%lu int1_high=%lu int1_low=%lu errors=%lu\r\n",
        (unsigned long)samples,(unsigned long)int_high,(unsigned long)int_low,(unsigned long)imu.errors);
    finish("IMU",ok&&samples>=100u ? "DATA_CAPTURED_STIMULUS_REVIEW_REQUIRED":"IO_OR_SAMPLE_FAILURE");
}
static uint32_t touch_timing(uint32_t hz)
{
    /* HSI16 kernel, analog filter on, digital filter off. Targets are nominal:
     * physical rise/fall and synchronizer delays still need a scope. */
    switch(hz) {
    case 100000u:return 0x10422529u;
    case 50000u:return 0x10A24B53u;
    case 25000u:return 0x30A24B53u;
    case 10000u:return 0x70A25F67u;
    default:return 0u;
    }
}
static bool touch_prepare(uint32_t hz,bool reset)
{
    if(!touch_timing(hz)||!io_prepare())return false;
    if (reset && !io_bit(0x02u,false))return false;
    if (reset) HAL_Delay(10u);
    if (!io_bit(0x02u,true))return false;
    /* Match the product's >=300ms FT6336U reset-release qualification. */
    HAL_Delay(350u);
    gpio(GPIOB,GPIO_PIN_1|GPIO_PIN_2,GPIO_MODE_AF_OD,GPIO_NOPULL,GPIO_AF4_I2C1);
    __HAL_RCC_I2C1_CONFIG(RCC_I2C1CLKSOURCE_HSI);__HAL_RCC_I2C1_CLK_ENABLE();
    __HAL_RCC_I2C1_FORCE_RESET();__HAL_RCC_I2C1_RELEASE_RESET();
    bool ok=i2c_init(&touch_bus,I2C1,touch_timing(hz));
    say("TOUCH_BUS target_hz=%lu timing=%08lx kernel_hz=16000000 scl=%u sda=%u reset=%u init=%u\r\n",
        (unsigned long)hz,(unsigned long)touch_bus.Instance->TIMINGR,
        HAL_GPIO_ReadPin(GPIOB,GPIO_PIN_2),HAL_GPIO_ReadPin(GPIOB,GPIO_PIN_1),reset,ok);
    return ok;
}
static bool touch_read_mode(uint8_t reg,uint8_t *p,uint16_t n,bool stop)
{
    HAL_StatusTypeDef status;
    const char *stage=stop?"register_pointer":"memory_read";
    if(stop) {
        status=HAL_I2C_Master_Transmit(&touch_bus,0x70u,&reg,1u,30u);
        if(status==HAL_OK){stage="read_after_stop";status=HAL_I2C_Master_Receive(&touch_bus,0x70u,p,n,30u);}
    } else status=HAL_I2C_Mem_Read(&touch_bus,0x70u,reg,I2C_MEMADD_SIZE_8BIT,p,n,30u);
    if(status!=HAL_OK)say("TOUCH_IO mode=%s stage=%s reg=%02x bytes=%u hal=%u error=%08lx isr=%08lx scl=%u sda=%u\r\n",
        stop?"stop":"restart",stage,reg,n,status,(unsigned long)HAL_I2C_GetError(&touch_bus),
        (unsigned long)touch_bus.Instance->ISR,HAL_GPIO_ReadPin(GPIOB,GPIO_PIN_2),HAL_GPIO_ReadPin(GPIOB,GPIO_PIN_1));
    return status==HAL_OK;
}
static bool touch_write_register(uint8_t reg,uint8_t value)
{
    HAL_StatusTypeDef status=HAL_I2C_Mem_Write(&touch_bus,0x70u,reg,I2C_MEMADD_SIZE_8BIT,&value,1u,30u);
    if(status!=HAL_OK)say("TOUCH_IO mode=write stage=register_write reg=%02x hal=%u error=%08lx isr=%08lx scl=%u sda=%u\r\n",
        reg,status,(unsigned long)HAL_I2C_GetError(&touch_bus),(unsigned long)touch_bus.Instance->ISR,
        HAL_GPIO_ReadPin(GPIOB,GPIO_PIN_2),HAL_GPIO_ReadPin(GPIOB,GPIO_PIN_1));
    return status==HAL_OK;
}
static void touch_matrix(bool reset)
{
    say("BEGIN test=TOUCH matrix=1 rounds_per_mode=32 reset_once=%u\r\n",reset);
    const uint32_t rates[]={100000u,50000u,25000u,10000u};
    for(unsigned f=0u;f<4u;++f) {
        if(!touch_prepare(rates[f],reset&&f==0u)){finish("TOUCH","BUS_INIT_FAILED");return;}
        HAL_StatusTypeDef address=HAL_I2C_IsDeviceReady(&touch_bus,0x70u,1u,30u);
        say("TOUCH_ADDRESS hz=%lu hal=%u error=%08lx\r\n",(unsigned long)rates[f],address,(unsigned long)HAL_I2C_GetError(&touch_bus));
        uint32_t good[2]={0u,0u},bad[2]={0u,0u};uint8_t id[2][3]={{0}};
        for(unsigned r=0u;r<32u;++r)for(unsigned mode=0u;mode<2u;++mode) {
            uint8_t report[5];
            bool ok=touch_read_mode(0xA3u,&id[mode][0],1u,mode!=0u)&&
                touch_read_mode(0xA6u,&id[mode][1],1u,mode!=0u)&&
                touch_read_mode(0xA8u,&id[mode][2],1u,mode!=0u)&&
                touch_read_mode(0x02u,report,sizeof(report),mode!=0u);
            if(ok)++good[mode];else ++bad[mode];HAL_Delay(10u);
        }
        for(unsigned mode=0u;mode<2u;++mode)say("TOUCH_MATRIX hz=%lu mode=%s rounds=32 ok=%lu failed=%lu id_a3=%02x fw_a6=%02x id_a8=%02x\r\n",
            (unsigned long)rates[f],mode?"stop":"restart",(unsigned long)good[mode],(unsigned long)bad[mode],id[mode][0],id[mode][1],id[mode][2]);
    }
    finish("TOUCH","BUS_MATRIX_CAPTURED");
}
static void touch_test(uint32_t hz,bool reset,bool stop)
{
    say("BEGIN test=TOUCH scl_target_hz=%lu mode=%s reset=%u duration_ms=40000\r\n",(unsigned long)hz,stop?"stop":"restart",reset);
    if(!touch_prepare(hz,reset)){finish("TOUCH","BUS_INIT_FAILED");return;}
    uint8_t id[3];
    bool ok=touch_read_mode(0xA3u,&id[0],1u,stop)&&touch_read_mode(0xA6u,&id[1],1u,stop)&&touch_read_mode(0xA8u,&id[2],1u,stop);
    if (ok) say("TOUCH id_a3=%02x fw_a6=%02x id_a8=%02x\r\n",id[0],id[1],id[2]);
    ok=ok&&touch_write_register(0x00u,0x00u)&&touch_write_register(0xA5u,0x00u)&&
        touch_write_register(0xA4u,0x00u)&&
        touch_write_register(0x80u,COMP_FT6336_COMPANION_TOUCH_THRESHOLD)&&
        touch_write_register(0x88u,COMP_FT6336_COMPANION_ACTIVE_PERIOD);
    uint32_t start=HAL_GetTick(), reads=0u, touches=0u, errors=0u; uint8_t previous[5]={255,255,255,255,255};
    while (ok&&HAL_GetTick()-start<40000u) {
        uint8_t report[5],pins=0u; comp_ft6336_touch_sample_t s;
        if (!touch_read_mode(0x02u,report,sizeof(report),stop)) {++errors;ok=false;break;}
        ++reads;
        if (!comp_ft6336_decode_touch_report(report,&s)) {++errors;ok=false;break;}
        if (s.touch_count) ++touches;
        if (memcmp(report,previous,sizeof(report))) {
            (void)i2c_read(&io_bus,0x20u,0u,&pins,1u);
            say("TOUCH ms=%lu count=%u event=%u x=%u y=%u io=%02x int=%u\r\n",
                (unsigned long)HAL_GetTick(),s.touch_count,s.event,s.x,s.y,pins,HAL_GPIO_ReadPin(GPIOC,GPIO_PIN_13));
            memcpy(previous,report,sizeof(report));
        }
        HAL_Delay(10u);
    }
    say("TOUCH reads=%lu contact_reads=%lu errors=%lu hal_error=%08lx\r\n",
        (unsigned long)reads,(unsigned long)touches,(unsigned long)errors,(unsigned long)HAL_I2C_GetError(&touch_bus));
    finish("TOUCH",ok&&touches ? "CONTACTS_CAPTURED_COVERAGE_REVIEW_REQUIRED":(ok?"NO_CONTACT_OBSERVED":"IO_ERROR"));
}
static void touch_live_status(void)
{
    say("TOUCH_STATUS armed=%u reads=%lu contacts=%lu errors=%lu io_errors=%lu irq_low=%lu irq_high=%lu elapsed_ms=%lu no_operator_deadline=1\r\n",
        touch_armed,(unsigned long)touch_live_reads,(unsigned long)touch_live_contacts,(unsigned long)touch_live_errors,
        (unsigned long)touch_live_io_errors,(unsigned long)touch_irq_low,(unsigned long)touch_irq_high,
        (unsigned long)(HAL_GetTick()-touch_arm_ms));
    finish("TOUCH_STATUS",touch_live_errors||touch_live_io_errors?"IO_ERROR":"STATUS_CAPTURED");
}
static void touch_live_arm(void)
{
    if(touch_armed){finish("TOUCH_ARM","ALREADY_ARMED");return;}
    /* Control the matrix's descending-order/startup-time confound: low, higher,
     * then low again, without a touch reset. This is not another full matrix. */
    const uint32_t rates[]={10000u,25000u,10000u};
    bool low_rates_ok=true;
    for(unsigned f=0u;f<3u;++f) {
        if(!touch_prepare(rates[f],false)){finish("TOUCH_ARM","BUS_INIT_FAILED");return;}
        unsigned good=0u;uint8_t id[3]={0};
        for(unsigned r=0u;r<8u;++r) {
            bool ok=touch_read_mode(0xA3u,&id[0],1u,false)&&touch_read_mode(0xA6u,&id[1],1u,false)&&
                touch_read_mode(0xA8u,&id[2],1u,false)&&id[0]==0x64u&&id[1]==0x01u&&id[2]==0x11u;
            if(ok)++good;
        }
        say("TOUCH_READY_COMPARE index=%u hz=%lu rounds=8 ok=%u id_a3=%02x fw_a6=%02x id_a8=%02x reset=0\r\n",
            f,(unsigned long)rates[f],good,id[0],id[1],id[2]);
        if(rates[f]==10000u&&good!=8u)low_rates_ok=false;
    }
    if(!low_rates_ok){finish("TOUCH_ARM","LOW_RATE_ID_UNSTABLE");return;}
    bool ok=touch_write_register(0x00u,0x00u)&&touch_write_register(0xA5u,0x00u)&&
        touch_write_register(0xA4u,0x00u)&&touch_write_register(0x80u,COMP_FT6336_COMPANION_TOUCH_THRESHOLD)&&
        touch_write_register(0x88u,COMP_FT6336_COMPANION_ACTIVE_PERIOD);
    if(!ok){finish("TOUCH_ARM","CONFIG_WRITE_FAILED");return;}
    touch_arm_ms=HAL_GetTick();touch_poll_ms=touch_arm_ms;
    touch_live_reads=touch_live_contacts=touch_live_errors=touch_live_io_errors=touch_irq_low=touch_irq_high=0u;
    touch_armed=true;touch_live_status();finish("TOUCH_ARM","ARMED_AWAITING_OPERATOR");
}
static void touch_live_poll(void)
{
    if(!touch_armed||HAL_GetTick()-touch_poll_ms<20u)return;
    touch_poll_ms=HAL_GetTick();
    uint8_t report[5],before=0u,after=0u;comp_ft6336_touch_sample_t s;
    bool before_ok=i2c_read(&io_bus,0x20u,0u,&before,1u);
    bool read_ok=touch_read_mode(0x02u,report,sizeof(report),false);
    bool after_ok=i2c_read(&io_bus,0x20u,0u,&after,1u);
    if(!before_ok||!after_ok)++touch_live_io_errors;
    if(!read_ok||!comp_ft6336_decode_touch_report(report,&s)) {
        ++touch_live_errors;touch_armed=false;touch_live_status();finish("TOUCH_LIVE","IO_OR_DECODE_ERROR");return;
    }
    ++touch_live_reads;if(s.touch_count)++touch_live_contacts;
    if(before_ok){if(before&1u)++touch_irq_high;else ++touch_irq_low;}
    if(after_ok){if(after&1u)++touch_irq_high;else ++touch_irq_low;}
    say("TOUCH_LIVE ms=%lu count=%u event=%u x=%u y=%u io_before=%02x io_after=%02x io_ok=%u pc13=%u\r\n",
        (unsigned long)HAL_GetTick(),s.touch_count,s.event,s.x,s.y,before,after,before_ok&&after_ok,
        HAL_GPIO_ReadPin(GPIOC,GPIO_PIN_13));
    if(!before_ok||!after_ok){touch_armed=false;touch_live_status();finish("TOUCH_LIVE","EXPANDER_IO_ERROR");}
}
static void touch_live_stop(void)
{
    touch_armed=false;touch_live_status();finish("TOUCH_STOP","STOPPED");
}
#ifdef COMP_PERIPHERAL_REMAINING_ONLY
#include "remaining_checks.inc"
#include "electrical_checks.inc"
#endif
static bool nor_select(void *c,bool active)
{(void)c;HAL_GPIO_WritePin(GPIOA,GPIO_PIN_8,active?GPIO_PIN_RESET:GPIO_PIN_SET);return true;}
static bool nor_transfer(void *c,const uint8_t *tx,uint8_t *rx,size_t n,uint32_t ms)
{(void)c;return comp_v11_spi_polling_transfer(&spi3,tx,rx,n,ms);}
static bool nor_read(void *c,uint32_t addr,uint8_t *p,size_t n)
{(void)c;return companion_spi_nor_stm32wba_read(&nor,addr,p,n)==COMPANION_SPI_NOR_STM32WBA_OK;}
static bool nor_prepare(void)
{
    if (nor_ok) return true;
    HAL_GPIO_WritePin(GPIOA,GPIO_PIN_8,GPIO_PIN_SET);gpio(GPIOA,GPIO_PIN_8,GPIO_MODE_OUTPUT_PP,GPIO_NOPULL,0u);
    gpio(GPIOA,GPIO_PIN_0,GPIO_MODE_AF_PP,GPIO_NOPULL,GPIO_AF6_SPI3);
    gpio(GPIOB,GPIO_PIN_8|GPIO_PIN_9,GPIO_MODE_AF_PP,GPIO_NOPULL,GPIO_AF6_SPI3);
    __HAL_RCC_SPI3_CONFIG(RCC_SPI3CLKSOURCE_HSI);__HAL_RCC_SPI3_CLK_ENABLE();
    memset(&spi3,0,sizeof(spi3));spi3.Instance=SPI3;
    spi3.Init.Mode=SPI_MODE_MASTER;spi3.Init.Direction=SPI_DIRECTION_2LINES;spi3.Init.DataSize=SPI_DATASIZE_8BIT;
    spi3.Init.CLKPolarity=SPI_POLARITY_LOW;spi3.Init.CLKPhase=SPI_PHASE_1EDGE;spi3.Init.NSS=SPI_NSS_SOFT;
    spi3.Init.BaudRatePrescaler=SPI_BAUDRATEPRESCALER_4;spi3.Init.FirstBit=SPI_FIRSTBIT_MSB;
    spi3.Init.TIMode=SPI_TIMODE_DISABLE;spi3.Init.CRCCalculation=SPI_CRCCALCULATION_DISABLE;
    spi3.Init.NSSPMode=SPI_NSS_PULSE_DISABLE;spi3.Init.NSSPolarity=SPI_NSS_POLARITY_LOW;
    spi3.Init.FifoThreshold=SPI_FIFO_THRESHOLD_01DATA;spi3.Init.MasterKeepIOState=SPI_MASTER_KEEP_IO_STATE_ENABLE;
    companion_spi_nor_stm32wba_config_t cfg={0};
    cfg.target=COMPANION_SPI_NOR_STM32WBA_TARGET_WBA55;cfg.chip_select=nor_select;cfg.transfer=nor_transfer;
    cfg.now_ms=now;cfg.delay_ms=delay;cfg.transfer_timeout_ms=100u;cfg.page_program_timeout_ms=100u;
    cfg.sector_erase_timeout_ms=5000u;
    nor_ok=HAL_SPI_Init(&spi3)==HAL_OK&&companion_spi_nor_stm32wba_init(&nor,&cfg)&&
        companion_spi_nor_stm32wba_probe(&nor,NULL)==COMPANION_SPI_NOR_STM32WBA_OK&&
        nor.info.jedec_id==0xEF6018u&&nor.info.size_bytes==0x1000000u;
    say("NOR jedec=%06lx bytes=%lu ready=%u\r\n",(unsigned long)nor.info.jedec_id,(unsigned long)nor.info.size_bytes,nor_ok);
    return nor_ok;
}
static uint32_t crc_add(uint32_t crc,const uint8_t *p,size_t n)
{
    while (n--) {crc^=*p++;for(unsigned k=0u;k<8u;++k)crc=(crc>>1)^((crc&1u)?0xEDB88320u:0u);}
    return crc;
}
static void nor_test(bool destructive)
{
    say("BEGIN test=NOR write_requested=%u\r\n",destructive);
    if (!nor_prepare()) {finish(destructive?"NOR_RW":"NOR","PROBE_FAILED");return;}
    bool layout=comp_wba_workspace_layout_valid(nor_read,NULL);
    say("NOR layout_valid=%u static_bytes=%lu dynamic_base=%lu\r\n",layout,
        (unsigned long)COMP_WBA_NOR_UI_BYTES,(unsigned long)COMP_WBA_NOR_DYNAMIC_BASE);
    const uint32_t offsets[]={0u,COMP_WBA_NOR_UI_BYTES-4096u,COMP_WBA_NOR_DYNAMIC_BASE,
        COMP_WBA_NOR_RECORDING_BASE,0x800000u,0xFFE000u,0xFFF000u};
    bool ok=true;
    for (unsigned i=0u;i<sizeof(offsets)/sizeof(offsets[0]);++i) {
        uint32_t crc=UINT32_MAX;
        for(uint32_t n=0u;n<NOR_SECTOR;n+=sizeof(page)) {
            if(!nor_read(NULL,offsets[i]+n,page,sizeof(page))) {ok=false;break;}
            crc=crc_add(crc,page,sizeof(page));
        }
        say("NOR address=%08lx bytes=4096 crc32=%08lx ok=%u\r\n",(unsigned long)offsets[i],(unsigned long)(crc^UINT32_MAX),ok);
        if(!ok)break;
    }
    bool update_erased[2]={true,true};
    const uint32_t meta[2]={COMP_WBA_NOR_UPDATE_META_A,COMP_WBA_NOR_UPDATE_META_B};
    for(unsigned slot=0u;slot<2u;++slot) {
        for(uint32_t n=0u;n<NOR_SECTOR;n+=sizeof(page)) {
            if(!nor_read(NULL,meta[slot]+n,page,sizeof(page))){ok=false;update_erased[slot]=false;break;}
            for(size_t k=0u;k<sizeof(page);++k)if(page[k]!=0xFFu)update_erased[slot]=false;
        }
        say("NOR update_meta=%08lx erased=%u\r\n",(unsigned long)meta[slot],update_erased[slot]);
    }
    if (!destructive) {finish("NOR",ok?"READS_CAPTURED_WRITE_UNTESTED":"READ_FAILED");return;}
    /* This explicit developer command borrows only the final dynamic sector,
     * after layout validation. Save and restore it; no static resource/root,
     * metadata, pairing NVM or internal Flash address is writable here. The
     * host must establish no active update before loading this diagnostic. */
    if (!ok||!layout||!update_erased[0]||!update_erased[1]||NOR_SCRATCH<COMP_WBA_NOR_RECORDING_BASE||
        !nor_read(NULL,NOR_SCRATCH,nor_backup,sizeof(nor_backup))) {finish("NOR_RW","GUARD_OR_BACKUP_FAILED");return;}
    uint32_t prior_crc=crc_add(UINT32_MAX,nor_backup,sizeof(nor_backup))^UINT32_MAX;
    bool touched=false;
    for(unsigned pass=0u;pass<2u&&ok;++pass) {
        touched=true;
        ok=companion_spi_nor_stm32wba_erase_4k(&nor,NOR_SCRATCH)==COMPANION_SPI_NOR_STM32WBA_OK;
        for(uint32_t n=0u;n<NOR_SECTOR&&ok;n+=sizeof(page)) {
            ok=nor_read(NULL,NOR_SCRATCH+n,page,sizeof(page));
            for(size_t k=0u;k<sizeof(page)&&ok;++k)if(page[k]!=0xFFu)ok=false;
        }
        for(uint32_t n=0u;n<NOR_SECTOR&&ok;n+=sizeof(page)) {
            for(size_t k=0u;k<sizeof(page);++k)page[k]=(uint8_t)(((n+k)*73u+((n+k)>>8)*19u)^(pass?0xA5u:0x5Au));
            ok=companion_spi_nor_stm32wba_program(&nor,NOR_SCRATCH+n,page,sizeof(page))==COMPANION_SPI_NOR_STM32WBA_OK;
        }
        for(uint32_t n=0u;n<NOR_SECTOR&&ok;n+=sizeof(page)) {
            ok=nor_read(NULL,NOR_SCRATCH+n,page,sizeof(page));
            for(size_t k=0u;k<sizeof(page)&&ok;++k)
                if(page[k]!=(uint8_t)(((n+k)*73u+((n+k)>>8)*19u)^(pass?0xA5u:0x5Au)))ok=false;
        }
        say("NOR_RW pass=%u pattern_verified=%u\r\n",pass,ok);
    }
    bool restored=!touched;
    if(touched) {
        restored=companion_spi_nor_stm32wba_erase_4k(&nor,NOR_SCRATCH)==COMPANION_SPI_NOR_STM32WBA_OK&&
            companion_spi_nor_stm32wba_program(&nor,NOR_SCRATCH,nor_backup,sizeof(nor_backup))==COMPANION_SPI_NOR_STM32WBA_OK;
        for(uint32_t n=0u;n<NOR_SECTOR&&restored;n+=sizeof(page))
            restored=nor_read(NULL,NOR_SCRATCH+n,page,sizeof(page))&&!memcmp(page,nor_backup+n,sizeof(page));
    }
    say("NOR_RW address=%08lx bytes=4096 prior_crc32=%08lx restored=%u\r\n",(unsigned long)NOR_SCRATCH,(unsigned long)prior_crc,restored);
    finish("NOR_RW",ok&&restored?"TWO_PATTERNS_VERIFIED_RESTORED":(restored?"PATTERN_FAILED_RESTORED":"RESTORE_FAILED"));
}
static bool panel_transfer(void *c,bool data,const uint8_t *p,uint16_t n)
{
    (void)c;HAL_GPIO_WritePin(GPIOB,GPIO_PIN_15,GPIO_PIN_SET);
    HAL_GPIO_WritePin(GPIOA,GPIO_PIN_11,data?GPIO_PIN_SET:GPIO_PIN_RESET);
    HAL_GPIO_WritePin(GPIOB,GPIO_PIN_0,GPIO_PIN_RESET);
    bool ok=comp_v11_spi_polling_transfer(&spi1,p,NULL,n,30u);
    HAL_GPIO_WritePin(GPIOB,GPIO_PIN_0,GPIO_PIN_SET);HAL_GPIO_WritePin(GPIOA,GPIO_PIN_11,GPIO_PIN_SET);return ok;
}
static bool panel_busy(void *c) {(void)c;return HAL_GPIO_ReadPin(GPIOA,GPIO_PIN_12)==GPIO_PIN_SET;}
static void panel_test(void)
{
    say("BEGIN test=EPD pattern=checkerboard_then_inverse sequence=full_then_mode2 reset=software_only\r\n");
    if(!shared_spi()) {finish("EPD","BUS_INIT_FAILED");return;}
    comp_ssd1681_wba_config_t cfg={0};cfg.transfer=panel_transfer;cfg.is_busy=panel_busy;
    cfg.now_ms=now;cfg.payload_chunk_bytes=25u;cfg.busy_timeout_ms=8000u;cfg.partial_limit=64u;
    cfg.reset_mode=COMP_SSD1681_WBA_RESET_SOFTWARE_ONLY;
    bool ok=comp_ssd1681_wba_init(&panel,&cfg);
    memset(before_frame,0xFF,sizeof(before_frame));
    for(unsigned pattern=0u;pattern<2u&&ok;++pattern) {
        for(unsigned y=0u;y<200u;++y)for(unsigned x=0u;x<25u;++x)
            after_frame[y*25u+x]=((y/25u+x/3u+pattern)&1u)?0x00u:0xFFu;
        if(pattern==0u)ok=comp_ssd1681_wba_start_full(&panel,before_frame,after_frame,sizeof(after_frame));
        else {
            const comp_ssd1681_wba_window_t window={0u,24u,0u,199u};
            ok=comp_ssd1681_wba_start_partial_pair(&panel,before_frame,after_frame,sizeof(after_frame),&window);
        }
        uint32_t start=HAL_GetTick(),high=0u,low=0u;
        while(ok&&comp_ssd1681_wba_status(&panel)==COMP_SSD1681_WBA_ACTIVE&&HAL_GetTick()-start<20000u) {
            if(panel_busy(NULL))++high;else ++low;
            (void)comp_ssd1681_wba_poll(&panel);HAL_Delay(1u);
        }
        ok=ok&&comp_ssd1681_wba_status(&panel)==COMP_SSD1681_WBA_COMPLETE&&high>0u;
        say("EPD pattern=%u status=%u error=%u high_samples=%lu low_samples=%lu elapsed_ms=%lu\r\n",
            pattern,comp_ssd1681_wba_status(&panel),comp_ssd1681_wba_error(&panel),
            (unsigned long)high,(unsigned long)low,(unsigned long)(HAL_GetTick()-start));
        if(ok){memcpy(before_frame,after_frame,sizeof(before_frame));HAL_Delay(2500u);}
    }
    if(comp_ssd1681_wba_status(&panel)==COMP_SSD1681_WBA_ACTIVE)comp_ssd1681_wba_cancel(&panel);
    finish("EPD",ok?"TWO_ACTIVATIONS_COMPLETED_VISUAL_REVIEW_REQUIRED":"REFRESH_FAILED");
}
static bool audio_prepare(void)
{
    if(audio_ok)return true;
    /* Configure the accepted 49.151855 MHz SAI kernel only on an audio
     * command. CPU remains HSI16; do not switch regulator supply or VOS. */
    audio_saved_hse_cr=RCC->CR;
    say("AUDIO before_cr=%08lx cfgr=%08lx\r\n",(unsigned long)audio_saved_hse_cr,(unsigned long)RCC->CFGR1);
    RCC_OscInitTypeDef osc={0};
    osc.OscillatorType=RCC_OSCILLATORTYPE_HSI|RCC_OSCILLATORTYPE_HSE;
    osc.HSIState=RCC_HSI_ON;osc.HSICalibrationValue=RCC_HSICALIBRATION_DEFAULT;
    osc.HSEState=RCC_HSE_ON;osc.HSEDiv=RCC_HSE_DIV1;
    osc.PLL1.PLLState=RCC_PLL_ON;osc.PLL1.PLLSource=RCC_PLLSOURCE_HSE;
    osc.PLL1.PLLM=2u;osc.PLL1.PLLN=12u;osc.PLL1.PLLP=4u;
    osc.PLL1.PLLQ=4u;osc.PLL1.PLLR=2u;osc.PLL1.PLLFractional=2359u;
    if(HAL_RCC_OscConfig(&osc)!=HAL_OK)return false;
    __HAL_RCC_PLL1CLKOUT_ENABLE(RCC_PLL1_PCLK);__HAL_RCC_SAI1_CONFIG(RCC_SAI1CLKSOURCE_PLL1P);
    __HAL_RCC_SAI1_CLK_ENABLE();__HAL_RCC_GPDMA1_CLK_ENABLE();
    audio_ok=true;say("AUDIO kernel_nominal_hz=%lu hclk=%lu\r\n",(unsigned long)AUDIO_KERNEL_HZ,(unsigned long)SystemCoreClock);
    return true;
}
static bool dma_init(DMA_HandleTypeDef *d,bool tx)
{
    memset(d,0,sizeof(*d));d->Instance=tx?GPDMA1_Channel0:GPDMA1_Channel1;
    d->Init.Request=tx?GPDMA1_REQUEST_SAI1_B:GPDMA1_REQUEST_SAI1_A;
    d->Init.BlkHWRequest=DMA_BREQ_SINGLE_BURST;d->Init.Direction=tx?DMA_MEMORY_TO_PERIPH:DMA_PERIPH_TO_MEMORY;
    d->Init.SrcInc=tx?DMA_SINC_INCREMENTED:DMA_SINC_FIXED;
    d->Init.DestInc=tx?DMA_DINC_FIXED:DMA_DINC_INCREMENTED;
    d->Init.SrcDataWidth=DMA_SRC_DATAWIDTH_HALFWORD;d->Init.DestDataWidth=DMA_DEST_DATAWIDTH_HALFWORD;
    d->Init.Priority=DMA_HIGH_PRIORITY;d->Init.SrcBurstLength=1u;d->Init.DestBurstLength=1u;
    d->Init.TransferAllocatedPort=DMA_SRC_ALLOCATED_PORT0|DMA_DEST_ALLOCATED_PORT0;
    d->Init.TransferEventMode=DMA_TCEM_BLOCK_TRANSFER;d->Init.Mode=DMA_NORMAL;
    return HAL_DMA_Init(d)==HAL_OK;
}
static bool audio_release(void)
{
    /* No other command owns SAI or this PLL. Keep CPU/UART on HSI16. */
    RCC_OscInitTypeDef osc={0};osc.PLL1.PLLState=RCC_PLL_OFF;
    __HAL_RCC_SAI1_CLK_DISABLE();
    HAL_StatusTypeDef pll=HAL_RCC_OscConfig(&osc);
    HAL_StatusTypeDef hse;
    const uint32_t saved_hse=audio_saved_hse_cr&(RCC_CR_HSEON|RCC_CR_HSEPRE);
    const bool retained_request=(audio_saved_hse_cr&(RCC_CR_HSEON|RCC_CR_HSERDY))==RCC_CR_HSERDY;
    if((saved_hse&RCC_CR_HSEON)!=0u||retained_request) {
        /* The inherited radio can hold HSERDY with HSEON already clear. The
         * pre-command state was 0x00020500 on this board. Restore our software
         * request, rather than waiting for another block's clock to disappear.
         * This is no measurement or claim of product low-power behavior. */
        __HAL_RCC_HSE_CONFIG(saved_hse);
        hse=(RCC->CR&(RCC_CR_HSEON|RCC_CR_HSEPRE))==saved_hse?HAL_OK:HAL_ERROR;
    } else {
        osc.OscillatorType=RCC_OSCILLATORTYPE_HSE;osc.HSEState=RCC_HSE_OFF;
        osc.HSEDiv=saved_hse&RCC_CR_HSEPRE;osc.PLL1.PLLState=RCC_PLL_NONE;
        hse=HAL_RCC_OscConfig(&osc);
    }
    audio_ok=false;
    bool ok=pll==HAL_OK&&hse==HAL_OK;
    say("AUDIO released=%u pll_hal=%u hse_hal=%u inherited_hse_ready=%u cr=%08lx cfgr=%08lx hclk=%lu\r\n",ok,pll,hse,retained_request,
        (unsigned long)RCC->CR,(unsigned long)RCC->CFGR1,(unsigned long)SystemCoreClock);return ok;
}
void GPDMA1_Channel0_IRQHandler(void){HAL_DMA_IRQHandler(&dma_tx);}
void GPDMA1_Channel1_IRQHandler(void){HAL_DMA_IRQHandler(&dma_rx);}
void SAI1_IRQHandler(void)
{if(sai_tx.Instance)HAL_SAI_IRQHandler(&sai_tx);if(sai_rx.Instance)HAL_SAI_IRQHandler(&sai_rx);}
void HAL_SAI_TxCpltCallback(SAI_HandleTypeDef *h){if(h==&sai_tx)tx_done=true;}
void HAL_SAI_RxCpltCallback(SAI_HandleTypeDef *h){if(h==&sai_rx)rx_done=true;}
void HAL_SAI_ErrorCallback(SAI_HandleTypeDef *h){(void)h;audio_error=true;}
#ifndef COMP_PERIPHERAL_VOICE_ONLY
static void speaker_voice_fill(int16_t *buffer,uint32_t first_frame,uint32_t gain)
{
    for(uint32_t i=0u;i<512u;++i) {
        uint32_t frame=first_frame+i,index=frame/2u;int value=0;
        if(index<SPEAKER_PHRASE_BYTES) {
            int a=(int)speaker_phrase_pcm[index]-128;
            int b=index+1u<SPEAKER_PHRASE_BYTES?(int)speaker_phrase_pcm[index+1u]-128:a;
            value=(frame&1u)?(a+b)*(int)gain/2:a*(int)gain;
            if(value>28000)value=28000;
            if(value< -28000)value= -28000;
        }
        buffer[2u*i]=(int16_t)value;buffer[2u*i+1u]=(int16_t)value;
    }
}
#endif
static void speaker_test(bool speech,uint32_t voice_gain)
{
#ifdef COMP_PERIPHERAL_VOICE_ONLY
    (void)voice_gain;
    if(speech)say("BEGIN test=SPEAKER speech=1 source_hz=16000 source_bits=16 source_samples=%lu source_crc32=%08lx native_pcm=1 single_dma=1 sample_hz=16000 physical_hearing_required=1\r\n",
        (unsigned long)SPEAKER_HQ_SAMPLES,(unsigned long)SPEAKER_HQ_CRC32);
#else
    if(speech)say("BEGIN test=SPEAKER speech=1 source_hz=8000 source_bits=8 source_bytes=%lu source_crc32=%08lx source_pcm_gain=%lu sample_hz=16000 physical_hearing_required=1\r\n",
        (unsigned long)SPEAKER_PHRASE_BYTES,(unsigned long)SPEAKER_PHRASE_CRC32,(unsigned long)voice_gain);
#endif
    else say("BEGIN test=SPEAKER tones_hz=500,1000,1500 sample_hz=16000 physical_hearing_required=1\r\n");
    uint8_t saved[4];
    if(!audio_prepare()||!io_snapshot(saved)||!dma_init(&dma_tx,true)){
        (void)audio_release();
        finish("SPEAKER","PREPARE_FAILED");return;
    }
    gpio(GPIOB,GPIO_PIN_5|GPIO_PIN_6|GPIO_PIN_7,GPIO_MODE_AF_PP,GPIO_NOPULL,GPIO_AF13_SAI1);
    memset(&sai_tx,0,sizeof(sai_tx));sai_tx.Instance=SAI1_Block_B;
    sai_tx.Init.AudioMode=SAI_MODEMASTER_TX;sai_tx.Init.Synchro=SAI_ASYNCHRONOUS;
    sai_tx.Init.SynchroExt=SAI_SYNCEXT_DISABLE;sai_tx.Init.OutputDrive=SAI_OUTPUTDRIVE_ENABLE;
    sai_tx.Init.NoDivider=SAI_MASTERDIVIDER_ENABLE;sai_tx.Init.FIFOThreshold=SAI_FIFOTHRESHOLD_HF;
    sai_tx.Init.AudioFrequency=SAI_AUDIO_FREQUENCY_MCKDIV;sai_tx.Init.Mckdiv=12u;
    sai_tx.Init.MckOverSampling=SAI_MCK_OVERSAMPLING_DISABLE;sai_tx.Init.MonoStereoMode=SAI_STEREOMODE;
#ifdef COMP_PERIPHERAL_VOICE_ONLY
    if(speech)sai_tx.Init.MonoStereoMode=SAI_MONOMODE;
#endif
    sai_tx.Init.CompandingMode=SAI_NOCOMPANDING;sai_tx.Init.TriState=SAI_OUTPUT_NOTRELEASED;
    sai_tx.Init.MckOutput=SAI_MCK_OUTPUT_DISABLE;__HAL_LINKDMA(&sai_tx,hdmatx,dma_tx);
    bool ok=HAL_SAI_InitProtocol(&sai_tx,SAI_I2S_STANDARD,SAI_PROTOCOL_DATASIZE_16BIT,2u)==HAL_OK;
    HAL_NVIC_SetPriority(GPDMA1_Channel0_IRQn,2u,0u);HAL_NVIC_EnableIRQ(GPDMA1_Channel0_IRQn);
    HAL_NVIC_SetPriority(SAI1_IRQn,2u,0u);HAL_NVIC_EnableIRQ(SAI1_IRQn);
    ok=ok&&io_bit(0x40u,false);audio_error=false;uint32_t completed=0u;
    say("SPEAKER sai_cr1=%08lx frcr=%08lx slotr=%08lx frame_bits=%lu expected_fs_hz=16000 expected_bclk_hz=512000\r\n",
        (unsigned long)sai_tx.Instance->CR1,(unsigned long)sai_tx.Instance->FRCR,
        (unsigned long)sai_tx.Instance->SLOTR,(unsigned long)sai_tx.FrameInit.FrameLength);
    uint8_t enabled[4];bool enabled_read=io_snapshot(enabled);
    if(enabled_read)say("SPEAKER amp_input=%02x amp_output=%02x amp_direction=%02x\r\n",enabled[0],enabled[1],enabled[3]);
    uint32_t edge_fs=0u,edge_sck=0u,edge_sd=0u,fs_rising=0u,sample_ms=0u,previous_pins=GPIOB->IDR;
    if(speech&&ok) {
#ifdef COMP_PERIPHERAL_VOICE_ONLY
        /* SAI mono mode duplicates each native PCM sample into the two I2S
         * slots. One <=65534-byte GPDMA block keeps the whole phrase continuous. */
        _Static_assert(SPEAKER_HQ_SAMPLES*2u<=65534u,"Native voice exceeds a GPDMA block");
        ok=io_bit(0x40u,true);HAL_Delay(8u);
        if(io_snapshot(enabled))say("SPEAKER speech=1 amp_input=%02x amp_output=%02x amp_direction=%02x\r\n",enabled[0],enabled[1],enabled[3]);
        tx_done=false;__HAL_SAI_CLEAR_FLAG(&sai_tx,SAI_FLAG_OVRUDR);
        uint32_t start=HAL_GetTick(),duration_ms=SPEAKER_HQ_SAMPLES*1000u/16000u;
        ok=ok&&HAL_SAI_Transmit_DMA(&sai_tx,(uint8_t *)speaker_phrase_hq_pcm,SPEAKER_HQ_SAMPLES)==HAL_OK;
        while(ok&&!tx_done&&!audio_error&&HAL_GetTick()-start<duration_ms+500u) {
            uint32_t elapsed=HAL_GetTick()-start;
            if(elapsed>=80u&&elapsed<95u) {
                uint32_t pins=GPIOB->IDR,changed=pins^previous_pins;previous_pins=pins;
                if(changed&GPIO_PIN_5){++edge_fs;if(pins&GPIO_PIN_5)++fs_rising;}
                if(changed&GPIO_PIN_6)++edge_sck;
                if(changed&GPIO_PIN_7)++edge_sd;
                sample_ms=elapsed-80u;
            } else __WFI();
        }
        ok=ok&&tx_done&&!audio_error;completed=ok?1u:0u;
        say("SPEAKER speech=1 dma_blocks=%lu expected_blocks=1 ok=%u elapsed_ms=%lu nominal_frames=%lu dma_remaining=%lu sai_error=%08lx mono_duplicate=1\r\n",
            (unsigned long)completed,ok,(unsigned long)(HAL_GetTick()-start),
            (unsigned long)SPEAKER_HQ_SAMPLES,(unsigned long)__HAL_DMA_GET_COUNTER(&dma_tx),(unsigned long)HAL_SAI_GetError(&sai_tx));
#else
        /* Pre-fill the next DMA buffer during playback. Reuse the inactive mic
         * raw storage; the speech sample lives only in this SRAM diagnostic. */
        int16_t *buffers=(int16_t *)raw_words;
        uint32_t blocks=(SPEAKER_PHRASE_BYTES*2u+511u)/512u,start=HAL_GetTick();
        ok=io_bit(0x40u,true);HAL_Delay(8u);
        if(io_snapshot(enabled))say("SPEAKER speech=1 amp_input=%02x amp_output=%02x amp_direction=%02x\r\n",enabled[0],enabled[1],enabled[3]);
        speaker_voice_fill(buffers,0u,voice_gain);
        for(uint32_t block=0u;block<blocks&&ok;++block) {
            int16_t *playing=buffers+(block&1u)*1024u;
            tx_done=false;__HAL_SAI_CLEAR_FLAG(&sai_tx,SAI_FLAG_OVRUDR);
            ok=HAL_SAI_Transmit_DMA(&sai_tx,(uint8_t *)playing,1024u)==HAL_OK;
            uint32_t block_start=HAL_GetTick();
            if(block+1u<blocks)speaker_voice_fill(buffers+((block+1u)&1u)*1024u,(block+1u)*512u,voice_gain);
            uint32_t gpio_sample_start=HAL_GetTick();
            while(ok&&!tx_done&&!audio_error&&HAL_GetTick()-block_start<200u) {
                /* Sample after the known 40ms leading silence, and exclude
                 * next-buffer generation from this coarse GPIO time window. */
                if(block==2u&&HAL_GetTick()-gpio_sample_start<15u) {
                    uint32_t pins=GPIOB->IDR,changed=pins^previous_pins;previous_pins=pins;
                    if(changed&GPIO_PIN_5){++edge_fs;if(pins&GPIO_PIN_5)++fs_rising;}
                    if(changed&GPIO_PIN_6)++edge_sck;
                    if(changed&GPIO_PIN_7)++edge_sd;
                    sample_ms=HAL_GetTick()-gpio_sample_start;
                } else __WFI();
            }
            ok=ok&&tx_done&&!audio_error;if(ok)++completed;
        }
        say("SPEAKER speech=1 dma_blocks=%lu expected_blocks=%lu ok=%u elapsed_ms=%lu nominal_frames=%lu sai_error=%08lx\r\n",
            (unsigned long)completed,(unsigned long)blocks,ok,(unsigned long)(HAL_GetTick()-start),
            (unsigned long)(SPEAKER_PHRASE_BYTES*2u),(unsigned long)HAL_SAI_GetError(&sai_tx));
#endif
    }
    for(unsigned tone=0u;!speech&&tone<3u&&ok;++tone) {
        unsigned frequency=500u*(tone+1u);
        ok=io_bit(0x40u,true);HAL_Delay(1u);
        enabled_read=io_snapshot(enabled);
        if(enabled_read)say("SPEAKER tone=%u amp_input=%02x amp_output=%02x amp_direction=%02x\r\n",tone,enabled[0],enabled[1],enabled[3]);
        uint32_t sampled_this_tone=0u;
        for(unsigned block=0u;block<16u&&ok;++block) {
            for(unsigned i=0u;i<512u;++i) {
                unsigned absolute=block*512u+i;
                int16_t v=((absolute*frequency*2u/16000u)&1u)?2500:-2500;
                if(absolute<64u)v=(int16_t)(v*(int)absolute/64);
                if(absolute>=8128u)v=(int16_t)(v*(int)(8191u-absolute)/64);
                tx_pcm[2u*i]=v;tx_pcm[2u*i+1u]=v;
            }
            tx_done=false;__HAL_SAI_CLEAR_FLAG(&sai_tx,SAI_FLAG_OVRUDR);
            ok=HAL_SAI_Transmit_DMA(&sai_tx,(uint8_t*)tx_pcm,1024u)==HAL_OK;
            uint32_t start=HAL_GetTick();
            while(ok&&!tx_done&&!audio_error&&HAL_GetTick()-start<200u) {
                if(block==0u&&HAL_GetTick()-start<15u) {
                    uint32_t pins=GPIOB->IDR,changed=pins^previous_pins;previous_pins=pins;
                    if(changed&GPIO_PIN_5){++edge_fs;if(pins&GPIO_PIN_5)++fs_rising;}
                    if(changed&GPIO_PIN_6)++edge_sck;
                    if(changed&GPIO_PIN_7)++edge_sd;
                    sampled_this_tone=HAL_GetTick()-start;
                } else __WFI();
            }
            ok=ok&&tx_done&&!audio_error;if(ok)++completed;
        }
        say("SPEAKER tone=%u dma_blocks=%lu ok=%u sai_error=%08lx\r\n",tone,
            (unsigned long)completed,ok,(unsigned long)HAL_SAI_GetError(&sai_tx));
        sample_ms+=sampled_this_tone;
        bool muted=io_bit(0x40u,false);ok=ok&&muted;
        (void)HAL_SAI_DMAStop(&sai_tx);HAL_Delay(180u);
    }
    say("SPEAKER sampled_edges_fs=%lu sampled_edges_sck=%lu sampled_edges_sd=%lu no_frequency_measurement=1\r\n",
        (unsigned long)edge_fs,(unsigned long)edge_sck,(unsigned long)edge_sd);
    say("SPEAKER fs_rising=%lu sampled_ms=%lu gpio_fs_estimate_hz=%lu scope_measurement=0\r\n",
        (unsigned long)fs_rising,(unsigned long)sample_ms,(unsigned long)(sample_ms?fs_rising*1000u/sample_ms:0u));
    (void)io_bit(0x40u,false);
    (void)HAL_SAI_DMAStop(&sai_tx);(void)HAL_SAI_DeInit(&sai_tx);
    (void)HAL_DMA_DeInit(&dma_tx);HAL_NVIC_DisableIRQ(GPDMA1_Channel0_IRQn);
    /* Restore only the borrowed P6 latch/direction, including failure exits. */
    uint8_t regs[4];bool restored=io_snapshot(regs);
    restored=restored&&i2c_write(&io_bus,0x20u,1u,(uint8_t)((regs[1]&~0x40u)|(saved[1]&0x40u)));
    restored=restored&&i2c_write(&io_bus,0x20u,3u,(uint8_t)((regs[3]&~0x40u)|(saved[3]&0x40u)));
    say("SPEAKER amp_restored=%u\r\n",restored);
    restored=audio_release()&&restored;
    finish("SPEAKER",ok&&restored?"DMA_COMPLETED_HEARING_UNCONFIRMED":"AUDIO_OR_RESTORE_FAILED");
}
static bool emit_pcm(void *c,const int16_t *pcm,size_t n,uint32_t hz)
{
    (void)c;if(n!=160u||hz!=16000u)return false;
    /* DMA is already stopped. UART export cannot disturb captured samples. */
    for(unsigned offset=0u;offset<160u;offset+=32u) {
        char hex[129];
        for(unsigned i=0u;i<32u;++i) {
            uint16_t v=(uint16_t)pcm[offset+i];
            (void)snprintf(hex+4u*i,5u,"%02x%02x",v&255u,v>>8);
        }
        say("PCM channel=%lu frame=%lu sample=%u hex=%s\r\n",(unsigned long)pcm_channel,
            (unsigned long)pcm_sequence,offset,hex);
    }
    ++pcm_sequence;return true;
}
static void mic_test(void)
{
    say("BEGIN test=MIC capture_ms=80 pdm_nominal_hz=1535995 decimation=96 no_realtime_claim=1\r\n");
    if(!audio_prepare()||!dma_init(&dma_rx,false)){
        (void)audio_release();
        finish("MIC","PREPARE_FAILED");return;
    }
    gpio(GPIOA,GPIO_PIN_9|GPIO_PIN_10,GPIO_MODE_AF_PP,GPIO_NOPULL,GPIO_AF3_SAI1);
    memset(&sai_rx,0,sizeof(sai_rx));sai_rx.Instance=SAI1_Block_A;
    sai_rx.Init.AudioMode=SAI_MODEMASTER_RX;sai_rx.Init.Synchro=SAI_ASYNCHRONOUS;sai_rx.Init.SynchroExt=SAI_SYNCEXT_DISABLE;
    sai_rx.Init.MckOutput=SAI_MCK_OUTPUT_DISABLE;sai_rx.Init.OutputDrive=SAI_OUTPUTDRIVE_ENABLE;
    sai_rx.Init.NoDivider=SAI_MASTERDIVIDER_DISABLE;sai_rx.Init.FIFOThreshold=SAI_FIFOTHRESHOLD_HF;
    sai_rx.Init.AudioFrequency=SAI_AUDIO_FREQUENCY_MCKDIV;sai_rx.Init.Mckdiv=16u;
    sai_rx.Init.MckOverSampling=SAI_MCK_OVERSAMPLING_DISABLE;sai_rx.Init.MonoStereoMode=SAI_STEREOMODE;
    sai_rx.Init.CompandingMode=SAI_NOCOMPANDING;sai_rx.Init.TriState=SAI_OUTPUT_NOTRELEASED;
    sai_rx.Init.Protocol=SAI_FREE_PROTOCOL;sai_rx.Init.DataSize=SAI_DATASIZE_16;sai_rx.Init.FirstBit=SAI_FIRSTBIT_MSB;
    sai_rx.Init.ClockStrobing=SAI_CLOCKSTROBING_FALLINGEDGE;
    sai_rx.Init.PdmInit.Activation=ENABLE;sai_rx.Init.PdmInit.MicPairsNbr=1u;sai_rx.Init.PdmInit.ClockEnable=SAI_PDM_CLOCK1_ENABLE;
    sai_rx.FrameInit.FrameLength=16u;sai_rx.FrameInit.ActiveFrameLength=1u;sai_rx.FrameInit.FSDefinition=SAI_FS_STARTFRAME;
    sai_rx.FrameInit.FSPolarity=SAI_FS_ACTIVE_HIGH;sai_rx.FrameInit.FSOffset=SAI_FS_FIRSTBIT;
    sai_rx.SlotInit.FirstBitOffset=0u;sai_rx.SlotInit.SlotSize=SAI_SLOTSIZE_DATASIZE;
    sai_rx.SlotInit.SlotNumber=1u;sai_rx.SlotInit.SlotActive=SAI_SLOTACTIVE_0;
    __HAL_LINKDMA(&sai_rx,hdmarx,dma_rx);
    bool ok=HAL_SAI_Init(&sai_rx)==HAL_OK;rx_done=false;audio_error=false;
    HAL_NVIC_SetPriority(GPDMA1_Channel1_IRQn,2u,0u);HAL_NVIC_EnableIRQ(GPDMA1_Channel1_IRQn);
    HAL_NVIC_SetPriority(SAI1_IRQn,2u,0u);HAL_NVIC_EnableIRQ(SAI1_IRQn);
    memset(raw_words,0,sizeof(raw_words));uint32_t start=HAL_GetTick();
    ok=ok&&HAL_SAI_Receive_DMA(&sai_rx,(uint8_t*)raw_words,sizeof(raw_words)/2u)==HAL_OK;
    while(ok&&!rx_done&&!audio_error&&HAL_GetTick()-start<250u)__WFI();
    ok=ok&&rx_done&&!audio_error;
    uint32_t elapsed=HAL_GetTick()-start,remaining=__HAL_DMA_GET_COUNTER(&dma_rx);
    bool stopped=HAL_SAI_DMAStop(&sai_rx)==HAL_OK;
    say("MIC complete=%u dma_remaining=%lu elapsed_ms=%lu sai_error=%08lx dma_error=%08lx stopped=%u raw_crc32=%08lx\r\n",
        rx_done,(unsigned long)remaining,(unsigned long)elapsed,(unsigned long)HAL_SAI_GetError(&sai_rx),
        (unsigned long)HAL_DMA_GetError(&dma_rx),stopped,(unsigned long)(crc_add(UINT32_MAX,(uint8_t*)raw_words,sizeof(raw_words))^UINT32_MAX));
    ok=ok&&stopped;
    if(ok)for(pcm_channel=0u;pcm_channel<2u;++pcm_channel) {
        comp_wba_pdm_config_t cfg={0};cfg.layout=COMP_WBA_PDM_LAYOUT_LEFT_RIGHT_BYTES;
        cfg.bit_order=COMP_WBA_PDM_MSB_FIRST;cfg.output=pcm_channel?COMP_WBA_PDM_OUTPUT_RIGHT:COMP_WBA_PDM_OUTPUT_LEFT;
        cfg.decimation=96u;cfg.gain_q15=32768u;cfg.emit_pcm_frame=emit_pcm;
        comp_wba_pdm_capture_init(&decoder,&cfg);pcm_sequence=0u;
        ok=comp_wba_pdm_capture_prime(&decoder,(uint8_t*)raw_words,RAW_FRAME_BYTES,0u);
        for(unsigned frame=1u;frame<RAW_FRAMES&&ok;++frame)
            ok=comp_wba_pdm_capture_ingest(&decoder,(uint8_t*)raw_words+frame*RAW_FRAME_BYTES,RAW_FRAME_BYTES,frame);
        say("MIC channel=%lu pcm_frames=%lu peak_left=%d peak_right=%d saturated=%lu ok=%u\r\n",
            (unsigned long)pcm_channel,(unsigned long)pcm_sequence,decoder.stats.left_peak,
            decoder.stats.right_peak,(unsigned long)decoder.stats.saturated_samples,ok);
        if(!ok)break;
    }
    (void)HAL_SAI_DeInit(&sai_rx);(void)HAL_DMA_DeInit(&dma_rx);HAL_NVIC_DisableIRQ(GPDMA1_Channel1_IRQn);
    ok=audio_release()&&ok;
    finish("MIC",ok?"TWO_CHANNEL_PCM_EXPORTED_STIMULUS_REVIEW_REQUIRED":"CAPTURE_OR_DECODE_FAILED");
}
static void command(const char *line)
{
    if(!strcmp(line,"HELLO")){hello();return;}
    if(!qualified_target){finish("GUARD","WRONG_TARGET");return;}
#ifndef COMP_PERIPHERAL_VOICE_ONLY
    if(imu_armed&&strcmp(line,"IMU_STATUS")&&strcmp(line,"IMU_STOP")&&strcmp(line,"RESET")) {
        finish("GUARD","IMU_CAPTURE_ACTIVE");return;
    }
    if(touch_armed&&strcmp(line,"TOUCH_STATUS")&&strcmp(line,"TOUCH_STOP")&&strcmp(line,"RESET")) {
        finish("GUARD","TOUCH_CAPTURE_ACTIVE");return;
    }
#endif
    #ifdef COMP_PERIPHERAL_REMAINING_ONLY
    if(!strcmp(line,"IMU_SELF_TEST"))imu_self_test();
    else if(!strcmp(line,"IMU_INTERRUPT_PATH"))imu_interrupt_path();
    else if(!strcmp(line,"TOUCH_RESET_PATH"))touch_reset_path();
    else if(!strcmp(line,"CLOCKS"))clock_observation();
    else if(!strcmp(line,"TCA_RESET_PATH"))tca_reset_path();
    else if(!strcmp(line,"INTERNAL_REFERENCE"))internal_reference_measure();
    else if(!strcmp(line,"RELATIVE_CLOCKS"))relative_clock_measure();
    else if(!strcmp(line,"RTC_STOP_WAKE"))wake_measure(false);
    else if(!strcmp(line,"IMU_STOP_WAKE"))wake_measure(true);
    else if(!strcmp(line,"IMU_ARM"))imu_live_arm();
    else if(!strcmp(line,"IMU_STATUS"))imu_live_status();
    else if(!strcmp(line,"IMU_STOP"))imu_live_stop();
    #else
    if(!strcmp(line,"IO"))io_test();
#ifndef COMP_PERIPHERAL_VOICE_ONLY
    else if(!strcmp(line,"KEY"))key_test();
    else if(!strcmp(line,"KEY_ARM"))key_arm();
    else if(!strcmp(line,"KEY_STATUS"))key_status();
    else if(!strcmp(line,"KEY_STOP")){key_poll();key_armed=false;finish("KEY_STOP","DISARMED");}
    else if(!strcmp(line,"IMU"))imu_test();
    else if(!strcmp(line,"IMU_ARM"))imu_live_arm();
    else if(!strcmp(line,"IMU_STATUS"))imu_live_status();
    else if(!strcmp(line,"IMU_STOP"))imu_live_stop();
    else if(!strcmp(line,"TOUCH_MATRIX"))touch_matrix(false);
    else if(!strcmp(line,"TOUCH_MATRIX_RESET"))touch_matrix(true);
    else if(!strcmp(line,"TOUCH_ARM"))touch_live_arm();
    else if(!strcmp(line,"TOUCH_STATUS"))touch_live_status();
    else if(!strcmp(line,"TOUCH_STOP"))touch_live_stop();
    else if(!strcmp(line,"TOUCH100"))touch_test(100000u,false,false);
    else if(!strcmp(line,"TOUCH50"))touch_test(50000u,false,false);
    else if(!strcmp(line,"TOUCH25"))touch_test(25000u,false,false);
    else if(!strcmp(line,"TOUCH10"))touch_test(10000u,false,false);
    else if(!strcmp(line,"TOUCH100_STOP"))touch_test(100000u,false,true);
    else if(!strcmp(line,"TOUCH50_STOP"))touch_test(50000u,false,true);
    else if(!strcmp(line,"TOUCH25_STOP"))touch_test(25000u,false,true);
    else if(!strcmp(line,"TOUCH10_STOP"))touch_test(10000u,false,true);
    else if(!strcmp(line,"TOUCH50_RESET"))touch_test(50000u,true,false);
    else if(!strcmp(line,"NOR"))nor_test(false);
    else if(!strcmp(line,"NOR_RW_LAST_DEV_SECTOR"))nor_test(true);
    else if(!strcmp(line,"EPD"))panel_test();
#endif
    else if(!strcmp(line,"SPEAKER"))speaker_test(false,0u);
    else if(!strcmp(line,"SPEAKER_SPEECH"))speaker_test(true,256u);
    else if(!strcmp(line,"SPEAKER_SPEECH_G64"))speaker_test(true,64u);
    else if(!strcmp(line,"SPEAKER_SPEECH_G128"))speaker_test(true,128u);
    else if(!strcmp(line,"SPEAKER_SPEECH_G256"))speaker_test(true,256u);
    else if(!strcmp(line,"SPEAKER_SPEECH_G512"))speaker_test(true,512u);
#ifndef COMP_PERIPHERAL_VOICE_ONLY
    else if(!strcmp(line,"MIC"))mic_test();
#endif
    #endif
    else if(!strcmp(line,"RESET")){say("RESET returning_to_installed_product=1\r\n");HAL_Delay(30u);NVIC_SystemReset();}
    else say("ERROR unknown_command=1\r\n");
    say("READY id=" DIAG_ID "\r\n");
}
int main(void)
{
    /* No high-speed clock or external-peripheral setup before a usable UART. */
    __HAL_RCC_GPIOA_CLK_ENABLE();__HAL_RCC_GPIOB_CLK_ENABLE();__HAL_RCC_GPIOC_CLK_ENABLE();
    __HAL_RCC_GPDMA1_FORCE_RESET();__HAL_RCC_GPDMA1_RELEASE_RESET();
    __HAL_RCC_SAI1_FORCE_RESET();__HAL_RCC_SAI1_RELEASE_RESET();
    __enable_irq();
    if(HAL_Init()!=HAL_OK)for(;;)__NOP();
    if(HAL_RCC_DeInit()!=HAL_OK)for(;;)IWDG->KR=0xAAAAu;
    SystemCoreClockUpdate();(void)HAL_InitTick(15u);
    gpio(GPIOA,GPIO_PIN_1|GPIO_PIN_2,GPIO_MODE_AF_PP,GPIO_PULLUP,GPIO_AF8_LPUART1);
    __HAL_RCC_LPUART1_CONFIG(RCC_LPUART1CLKSOURCE_HSI);__HAL_RCC_LPUART1_CLK_ENABLE();
    __HAL_RCC_LPUART1_FORCE_RESET();__HAL_RCC_LPUART1_RELEASE_RESET();
    uart.Instance=LPUART1;uart.Init.BaudRate=115200u;uart.Init.WordLength=UART_WORDLENGTH_8B;
    uart.Init.StopBits=UART_STOPBITS_1;uart.Init.Parity=UART_PARITY_NONE;uart.Init.Mode=UART_MODE_TX_RX;
    uart.Init.HwFlowCtl=UART_HWCONTROL_NONE;uart.Init.ClockPrescaler=UART_PRESCALER_DIV1;
    uart_ok=HAL_UART_Init(&uart)==HAL_OK&&HAL_UARTEx_EnableFifoMode(&uart)==HAL_OK;
    if(uart_ok){HAL_NVIC_SetPriority(LPUART1_IRQn,3u,0u);HAL_NVIC_EnableIRQ(LPUART1_IRQn);
        SET_BIT(LPUART1->CR1,USART_CR1_RXNEIE_RXFNEIE);SET_BIT(LPUART1->CR3,USART_CR3_EIE);}
    qualified_target=identity();hello();say("READY id=" DIAG_ID "\r\n");
    char line[64];unsigned used=0u;bool overflow=false;uint32_t seen_rx_faults=0u;
    for(;;) {
#if !defined(COMP_PERIPHERAL_VOICE_ONLY) && !defined(COMP_PERIPHERAL_REMAINING_ONLY)
        key_poll();
        imu_live_poll();
        touch_live_poll();
#endif
        #ifdef COMP_PERIPHERAL_REMAINING_ONLY
        imu_live_poll();
        #endif
        if(seen_rx_faults!=uart_rx_faults) {
            __disable_irq();seen_rx_faults=uart_rx_faults;uart_rx_tail=uart_rx_head;__enable_irq();
            used=0u;overflow=true;say("ERROR uart_rx_faults=%lu command_discarded=1\r\n",(unsigned long)seen_rx_faults);
        }
        if(uart_rx_tail!=uart_rx_head) {
            uint8_t byte=uart_rx[uart_rx_tail];__DMB();uart_rx_tail=(uart_rx_tail+1u)&127u;
            if(byte=='\r'||byte=='\n') {
                if(used&&!overflow){line[used]=0;command(line);}
                else if(overflow)say("ERROR command_too_long=1\r\n");
                used=0u;overflow=false;
            }else if(used+1u<sizeof(line)){line[used++]=(char)byte;}else overflow=true;
        }else HAL_Delay(1u);
        IWDG->KR=0xAAAAu;
    }
}
