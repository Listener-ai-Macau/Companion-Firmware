/* Independent SRAM checks requested by the owner. No external ADC sampling,
 * NOR/Flash writes, or calendar/backup-domain reset. TCA_RESET explicitly
 * resets all expander ports, then restores the captured latch/polarity/direction.
 * STOP observations prove wake functionality, never physical power/current.
 * STM32WBA5x ES0592: enter Stop using HSE; wait after WFI before clock changes. */
#include "battery_adc.h"
static volatile uint32_t electrical_rtc_irqs,electrical_io_irqs,electrical_rtc_flags;
static RTC_HandleTypeDef electrical_rtc={.Instance=RTC,.State=HAL_RTC_STATE_READY};
void RTC_IRQHandler(void)
{
    uint32_t flags=RTC->MISR;electrical_rtc_flags|=flags;
    if(flags&RTC_MISR_WUTMF){RTC->SCR=RTC_SCR_CWUTF;++electrical_rtc_irqs;}
}
void EXTI13_IRQHandler(void)
{
    if(__HAL_GPIO_EXTI_GET_IT(GPIO_PIN_13)){
        __HAL_GPIO_EXTI_CLEAR_IT(GPIO_PIN_13);++electrical_io_irqs;
    }
}
static bool electrical_hse(void)
{
    RCC_OscInitTypeDef osc={0};RCC_ClkInitTypeDef clk={0};
    osc.OscillatorType=RCC_OSCILLATORTYPE_HSE|RCC_OSCILLATORTYPE_HSI;
    osc.HSEState=RCC_HSE_ON;osc.HSIState=RCC_HSI_ON;
    osc.HSICalibrationValue=RCC_HSICALIBRATION_DEFAULT;osc.PLL1.PLLState=RCC_PLL_NONE;
    if(HAL_RCC_OscConfig(&osc)!=HAL_OK)return false;
    clk.ClockType=RCC_CLOCKTYPE_SYSCLK;clk.SYSCLKSource=RCC_SYSCLKSOURCE_HSE;
    return HAL_RCC_ClockConfig(&clk,FLASH_LATENCY_1)==HAL_OK&&HAL_RCC_GetHCLKFreq()==32000000u;
}
static bool electrical_hsi(void)
{
    RCC_ClkInitTypeDef clk={0};clk.ClockType=RCC_CLOCKTYPE_SYSCLK;clk.SYSCLKSource=RCC_SYSCLKSOURCE_HSI;
    return HAL_RCC_ClockConfig(&clk,FLASH_LATENCY_0)==HAL_OK&&HAL_RCC_GetHCLKFreq()==16000000u;
}
static void tca_reset_path(void)
{
    say("BEGIN test=TCA_RESET_PATH all_ports_temporarily_inputs=1 restore_original_registers=1\r\n");
    uint8_t before[4]={0},defaults[4]={0},after[4]={0},value=0u;
    bool saved=io_snapshot(before);unsigned nack=0u;
    bool nondefault=saved&&(before[1]!=0xffu||before[2]!=0u||before[3]!=0xffu);
    if(saved){
        HAL_GPIO_WritePin(GPIOB,GPIO_PIN_12,GPIO_PIN_RESET);HAL_Delay(2u);
        bool ack=i2c_read(&io_bus,0x20u,1u,&value,1u);uint32_t error=HAL_I2C_GetError(&io_bus);
        nack=!ack&&error==HAL_I2C_ERROR_AF;
        say("TCA_RESET_HELD ack=%u hal_error=%08lx reset_pin=%u\r\n",ack,(unsigned long)error,HAL_GPIO_ReadPin(GPIOB,GPIO_PIN_12));
    }
    HAL_GPIO_WritePin(GPIOB,GPIO_PIN_12,GPIO_PIN_SET);HAL_Delay(2u);
    bool read=saved&&io_snapshot(defaults),reset=read&&defaults[1]==0xffu&&defaults[2]==0u&&defaults[3]==0xffu;
    bool restored=saved&&i2c_write(&io_bus,0x20u,1u,before[1])&&i2c_write(&io_bus,0x20u,2u,before[2])&&
        i2c_write(&io_bus,0x20u,3u,before[3])&&io_snapshot(after)&&after[1]==before[1]&&after[2]==before[2]&&after[3]==before[3];
    /* TI specifies register reset, not the I2C acknowledgement while held. */
    say("TCA_RESET_SUMMARY saved=%u initial_nondefault=%u held_nack=%u default_out=%02x default_pol=%02x default_dir=%02x defaults_ok=%u before_out=%02x before_dir=%02x after_out=%02x after_dir=%02x restored=%u\r\n",
        saved,nondefault,nack,defaults[1],defaults[2],defaults[3],reset,before[1],before[3],after[1],after[3],restored);
    finish("TCA_RESET_PATH",saved&&nondefault&&reset&&restored?"HARDWARE_RESET_DEFAULTS_AND_RESTORE_PASSED":"RESET_DEFAULTS_OR_RESTORE_FAILED");
}
static void internal_reference_measure(void)
{
    say("BEGIN test=INTERNAL_REFERENCE external_adc=0 p7_not_enabled=1 absolute_calibrated_by_meter=0\r\n");
    uint8_t before[4]={0},after[4]={0};bool safe=io_snapshot(before)&&(before[1]&0x80u)==0u&&(before[3]&0x80u)==0u;
    bool ok=safe;unsigned count=0u;uint32_t sum=0u;uint16_t low=UINT16_MAX,high=0u;
    for(unsigned n=0u;n<32u&&ok;++n){
        uint16_t raw=0u;ok=comp_v11_battery_adc_begin(NULL,false,HAL_GetTick());
        comp_wba_adc_result_t state=COMP_WBA_ADC_PENDING;uint32_t start=HAL_GetTick();
        while(ok&&state==COMP_WBA_ADC_PENDING&&HAL_GetTick()-start<25u){state=comp_v11_battery_adc_read(&raw,HAL_GetTick());HAL_Delay(1u);}
        const comp_v11_battery_adc_stats_t *s=comp_v11_battery_adc_stats();
        ok=ok&&state==COMP_WBA_ADC_READY&&s->reference_valid&&s->error==0u;
        say("VREF_SAMPLE index=%u raw=%u factory_raw=%u vdda_mv=%u valid=%u adc_error=%u ms=%lu\r\n",n,raw,s->factory_raw,s->reference_mv,ok,s->error,(unsigned long)HAL_GetTick());
        if(ok){++count;sum+=s->reference_mv;if(s->reference_mv<low)low=s->reference_mv;if(s->reference_mv>high)high=s->reference_mv;}
        comp_v11_battery_adc_cancel();HAL_Delay(20u);
    }
    bool unchanged=io_snapshot(after)&&before[1]==after[1]&&before[2]==after[2]&&before[3]==after[3];
    say("VREF_SUMMARY samples=%u minimum_mv=%u maximum_mv=%u mean_mv=%lu p7_off=%u registers_unchanged=%u adc_busy=%u calibrated_by_meter=0\r\n",
        count,count?low:0u,high,(unsigned long)(count?sum/count:0u),safe,unchanged,comp_v11_battery_adc_busy());
    finish("INTERNAL_REFERENCE",ok&&count==32u&&unchanged&&!comp_v11_battery_adc_busy()?"INTERNAL_REFERENCE_OBSERVED_EXTERNAL_ADC_UNTESTED":"INTERNAL_REFERENCE_CAPTURE_FAILED");
}
static void relative_clock_measure(void)
{
    say("BEGIN test=RELATIVE_CLOCKS hse_vs_lse=1 calibrated_frequency_instrument=0\r\n");
    bool had_apb=__HAL_RCC_RTCAPB_IS_CLK_ENABLED();__HAL_RCC_RTCAPB_CLK_ENABLE();
    bool ok=electrical_hse()&&__HAL_RCC_GET_FLAG(RCC_FLAG_LSERDY)&&
        (RTC->ICSR&RTC_ICSR_BIN)==RTC_ICSR_BIN_0&&((RTC->PRER&RTC_PRER_PREDIV_A)>>RTC_PRER_PREDIV_A_Pos)==31u;
    CoreDebug->DEMCR|=CoreDebug_DEMCR_TRCENA_Msk;DWT->CTRL|=DWT_CTRL_CYCCNTENA_Msk;
    unsigned count=0u;
    for(unsigned n=0u;n<3u&&ok;++n){
        uint32_t begin=0u,end=0u;ok=rtc_ssr(&begin);
        uint32_t align_start=HAL_GetTick();
        do{if(!rtc_ssr(&end)){ok=false;break;}}while(end==begin&&HAL_GetTick()-align_start<5u);
        ok=ok&&end!=begin;begin=end;uint32_t cycles0=DWT->CYCCNT;
        uint32_t start=HAL_GetTick();
        do{if(!rtc_ssr(&end)){ok=false;break;}}while(begin-end<512u&&HAL_GetTick()-start<700u);
        uint32_t cycles=DWT->CYCCNT-cycles0,delta=begin-end;
        ok=ok&&delta>=512u&&delta<520u&&cycles>0u;
        uint32_t relative_hz=delta?(uint32_t)((uint64_t)cycles*1024u/delta):0u;
        say("CLOCK_RATIO index=%u rtc_ticks=%lu hse_cycles=%lu hse_hz_if_lse_nominal=%lu observed=%u aligned_to_rtc_edges=1 absolute_calibrated=0\r\n",
            n,(unsigned long)delta,(unsigned long)cycles,(unsigned long)relative_hz,ok);
        if(ok)++count;
    }
    bool restored=electrical_hsi();if(!had_apb)__HAL_RCC_RTCAPB_CLK_DISABLE();
    finish("RELATIVE_CLOCKS",ok&&count==3u&&restored?"RELATIVE_COUNTS_CAPTURED_ABSOLUTE_PRECISION_UNTESTED":"RELATIVE_CLOCK_CAPTURE_FAILED");
}
static bool rtc_guard_arm(uint32_t counter)
{
    electrical_rtc.Lock=HAL_UNLOCKED;electrical_rtc.State=HAL_RTC_STATE_READY;
    HAL_NVIC_ClearPendingIRQ(RTC_IRQn);RTC->SCR=RTC_SCR_CWUTF;
    return HAL_RTCEx_SetWakeUpTimer_IT(&electrical_rtc,counter,RTC_WAKEUPCLOCK_RTCCLK_DIV16,0u)==HAL_OK;
}
static void wake_measure(bool imu_source)
{
    const char *test=imu_source?"IMU_STOP_WAKE":"RTC_STOP_WAKE";
    say("BEGIN test=%s isolated_sram=1 stop1=1 chip_revision=%04lx power_current_measured=0\r\n",test,(unsigned long)(DBGMCU->IDCODE>>16));
    bool had_apb=__HAL_RCC_RTCAPB_IS_CLK_ENABLED();__HAL_RCC_RTCAPB_CLK_ENABLE();
    bool had_dbp=(PWR->DBPR&PWR_DBPR_DBP)!=0u;HAL_PWR_EnableBkUpAccess();
    uint32_t old_cr=RTC->CR,old_wutr=RTC->WUTR,old_debug=DBGMCU->SCR;
    bool prepared=electrical_hse()&&__HAL_RCC_GET_FLAG(RCC_FLAG_LSERDY)&&
        __HAL_RCC_GET_RTC_SOURCE()==RCC_RTCCLKSOURCE_LSE&&
        (RTC->ICSR&RTC_ICSR_BIN)==RTC_ICSR_BIN_0&&((RTC->PRER&RTC_PRER_PREDIV_A)>>RTC_PRER_PREDIV_A_Pos)==31u;
    HAL_NVIC_DisableIRQ(EXTI13_IRQn);
    CLEAR_BIT(RTC->CR,RTC_CR_ALRAIE|RTC_CR_ALRBIE|RTC_CR_SSRUIE);
    HAL_NVIC_SetPriority(RTC_IRQn,2u,0u);HAL_NVIC_EnableIRQ(RTC_IRQn);
    uint8_t base[4]={0},after[4]={0},data[6]={0},status=0u;
    if(imu_source&&prepared){
        prepared=shared_spi()&&comp_lsm6dso_start(&imu,imu_read,imu_write,NULL,HAL_GetTick());
        uint32_t start=HAL_GetTick();
        while(prepared&&imu.state!=COMP_IMU_READY&&HAL_GetTick()-start<150u){
            comp_imu_sample_t sample;prepared=comp_lsm6dso_poll(&imu,HAL_GetTick(),&sample)!=COMP_IMU_IO_ERROR;HAL_Delay(1u);
        }
        prepared=prepared&&imu.state==COMP_IMU_READY&&comp_lsm6dso_set_idle(&imu,true)&&imu_reg8(0x0Du,0u);
        HAL_Delay(100u);
        prepared=prepared&&imu_read(NULL,0x28u,data,sizeof(data))&&io_snapshot(base);
        gpio(GPIOC,GPIO_PIN_13,GPIO_MODE_IT_FALLING,GPIO_PULLUP,0u);
        __HAL_GPIO_EXTI_CLEAR_IT(GPIO_PIN_13);HAL_NVIC_ClearPendingIRQ(EXTI13_IRQn);
        HAL_NVIC_SetPriority(EXTI13_IRQn,2u,0u);HAL_NVIC_EnableIRQ(EXTI13_IRQn);
    }
    unsigned count=0u;bool passed=prepared;
    for(unsigned n=0u;n<3u&&passed;++n){
        HAL_NVIC_DisableIRQ(EXTI13_IRQn);
        (void)HAL_RTCEx_DeactivateWakeUpTimer(&electrical_rtc);RTC->SCR=RTC_SCR_CWUTF;
        if(imu_source){
            passed=imu_reg8(0x0Du,0u)&&imu_read(NULL,0x28u,data,sizeof(data))&&io_snapshot(base)&&imu_read(NULL,0x1Eu,&status,1u)&&(status&1u)==0u;
            __HAL_GPIO_EXTI_CLEAR_IT(GPIO_PIN_13);HAL_NVIC_ClearPendingIRQ(EXTI13_IRQn);
        }
        electrical_rtc_irqs=electrical_io_irqs=electrical_rtc_flags=0u;
        passed=passed&&rtc_guard_arm(2047u);
        if(imu_source)passed=passed&&imu_reg8(0x0Du,1u)&&HAL_GPIO_ReadPin(GPIOC,GPIO_PIN_13)==GPIO_PIN_SET;
        uint32_t ssr_before=0u,ssr_after=0u;passed=passed&&rtc_ssr(&ssr_before);
        if(!passed)break;
        HAL_NVIC_ClearPendingIRQ(RTC_IRQn);
        if(imu_source)HAL_NVIC_EnableIRQ(EXTI13_IRQn);
        CLEAR_BIT(DBGMCU->SCR,DBGMCU_SCR_DBG_STOP);__HAL_PWR_CLEAR_FLAG(PWR_FLAG_STOPF);
        HAL_SuspendTick();CLEAR_BIT(SysTick->CTRL,SysTick_CTRL_ENABLE_Msk);SCB->ICSR=SCB_ICSR_PENDSTCLR_Msk;
        __disable_irq();IWDG->KR=0xAAAAu;
        HAL_PWR_EnterSTOPMode(PWR_LOWPOWERMODE_STOP1,PWR_STOPENTRY_WFI);
        for(volatile unsigned delay=0u;delay<32u;++delay)__NOP();
        bool stopped=__HAL_PWR_GET_FLAG(PWR_FLAG_STOPF)!=0u;uint32_t source=__HAL_RCC_GET_SYSCLK_SOURCE();
        bool stamp=rtc_ssr(&ssr_after);DBGMCU->SCR=old_debug;
        SystemCoreClockUpdate();(void)HAL_InitTick(15u);HAL_ResumeTick();__enable_irq();
        HAL_NVIC_DisableIRQ(EXTI13_IRQn);
        (void)HAL_RTCEx_DeactivateWakeUpTimer(&electrical_rtc);RTC->SCR=RTC_SCR_CWUTF;
        bool inputs=true;
        if(imu_source)inputs=io_snapshot(after)&&((after[0]^base[0])&0x2Du)==8u&&imu_reg8(0x0Du,0u);
        uint32_t ticks=ssr_before-ssr_after;
        bool irq=imu_source?(electrical_io_irqs==1u&&electrical_rtc_irqs==0u):(electrical_rtc_irqs==1u&&electrical_io_irqs==0u);
        bool duration=imu_source?(ticks>0u&&ticks<205u):(ticks>=850u&&ticks<=1300u);
        bool hse_restored=electrical_hse();
        bool ok=stopped&&stamp&&source==RCC_SYSCLKSOURCE_STATUS_HSI&&irq&&duration&&inputs&&hse_restored;
        say("STOP_WAKE index=%u source=%s stop_flag=%u sysclk_after=%08lx rtc_ticks=%lu rtc_irq=%lu io_irq=%lu rtc_flags=%08lx inputs_before=%02x inputs_after=%02x inputs_expected=%u hse_restored=%u ok=%u power_measured=0\r\n",
            n,imu_source?"imu":"rtc",stopped,(unsigned long)source,(unsigned long)ticks,
            (unsigned long)electrical_rtc_irqs,(unsigned long)electrical_io_irqs,(unsigned long)electrical_rtc_flags,base[0],after[0],inputs,hse_restored,ok);
        passed=passed&&ok;if(ok)++count;
    }
    HAL_NVIC_DisableIRQ(EXTI13_IRQn);HAL_NVIC_DisableIRQ(RTC_IRQn);
    bool imu_stopped=!imu_source||(imu.write!=NULL&&comp_lsm6dso_stop(&imu));
    bool timer_off=HAL_RTCEx_DeactivateWakeUpTimer(&electrical_rtc)==HAL_OK;
    uint32_t restore_start=HAL_GetTick();while((RTC->ICSR&RTC_ICSR_WUTWF)==0u&&HAL_GetTick()-restore_start<100u)HAL_Delay(1u);
    bool writable=(RTC->ICSR&RTC_ICSR_WUTWF)!=0u;
    if(writable){RTC->WUTR=old_wutr;RTC->CR=old_cr;}
    bool rtc_restored=writable&&RTC->CR==old_cr&&RTC->WUTR==old_wutr;
    DBGMCU->SCR=old_debug;bool hsi=electrical_hsi();
    /* Compare the writable debug controls, not the hardware low-power status. */
    const uint32_t debug_controls=DBGMCU_SCR_DBG_STOP|DBGMCU_SCR_DBG_STANDBY;
    uint32_t final_debug=DBGMCU->SCR;
    bool debug_restored=((final_debug^old_debug)&debug_controls)==0u;
    if(!had_dbp)HAL_PWR_DisableBkUpAccess();
    if(!had_apb)__HAL_RCC_RTCAPB_CLK_DISABLE();
    say("STOP_WAKE_SUMMARY cycles=%u imu_stopped=%u timer_disabled=%u rtc_configuration_restored=%u hsi_restored=%u debug_restored=%u debug_before=%08lx debug_after=%08lx debug_control_mask=%08lx power_current_measured=0\r\n",
        count,imu_stopped,timer_off,rtc_restored,hsi,debug_restored,(unsigned long)old_debug,(unsigned long)final_debug,(unsigned long)debug_controls);
    finish(test,passed&&count==3u&&imu_stopped&&timer_off&&rtc_restored&&hsi&&debug_restored?"STOP1_SOURCE_AND_CLOCK_RECOVERY_OBSERVED_CURRENT_UNMEASURED":"STOP1_WAKE_OR_RESTORE_NOT_QUALIFIED");
}
