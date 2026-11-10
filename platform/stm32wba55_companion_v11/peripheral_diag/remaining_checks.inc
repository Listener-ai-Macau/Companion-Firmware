/* Focused remaining hardware checks. No Flash/NOR/NVM writes or P4/P7 toggle.
 * MEMS procedure and limits: ST LSM6DSO DS12140 Table 2, CTRL5_C, and
 * STMicroelectronics/STMems_Standard_C_drivers lsm6dso_self_test.c.
 * Internal self-test does not certify mounting axes or gesture thresholds. */
static bool imu_reg8(uint8_t reg,uint8_t value)
{
    uint8_t actual=0u;
    return imu_write(NULL,reg,&value,1u)&&imu_read(NULL,reg,&actual,1u)&&actual==value;
}
static int32_t imu_signed16(const uint8_t *p)
{
    uint32_t v=(uint32_t)p[0]|((uint32_t)p[1]<<8);
    return v>=32768u?(int32_t)v-65536:(int32_t)v;
}
static bool imu_st_average(uint8_t mask,uint8_t reg,bool gyro,const char *phase,int32_t mean[3],bool *quiet)
{
    int32_t sum[3]={0},low[3]={32767,32767,32767},high[3]={-32768,-32768,-32768};
    for(unsigned n=0u;n<6u;++n) {
        uint8_t status=0u,raw[6];uint32_t start=HAL_GetTick();
        do {
            if(!imu_read(NULL,0x1Eu,&status,1u))return false;
            if((status&mask)!=0u)break;
            HAL_Delay(1u);
        }while(HAL_GetTick()-start<150u);
        if((status&mask)==0u||!imu_read(NULL,reg,raw,sizeof(raw)))return false;
        int32_t a[3];
        for(unsigned k=0u;k<3u;++k) {
            a[k]=imu_signed16(raw+2u*k);
            if(n) {sum[k]+=a[k];if(a[k]<low[k])low[k]=a[k];if(a[k]>high[k])high[k]=a[k];}
        }
        say("IMU_ST_SAMPLE phase=%s index=%u dummy=%u x=%ld y=%ld z=%ld ms=%lu\r\n",
            phase,n,n==0u,(long)a[0],(long)a[1],(long)a[2],(unsigned long)HAL_GetTick());
    }
    *quiet=true;
    for(unsigned k=0u;k<3u;++k) {
        mean[k]=gyro?sum[k]*70/5:sum[k]*122/5000;
        int32_t span=gyro?(high[k]-low[k])*70:(high[k]-low[k])*122/1000;
        if(span>(gyro?5000:50))*quiet=false;
    }
    say("IMU_ST_AVERAGE phase=%s x=%ld y=%ld z=%ld stationary_window=%u units=%s\r\n",
        phase,(long)mean[0],(long)mean[1],(long)mean[2],*quiet,gyro?"mdps":"mg");
    return true;
}
static bool imu_mode_samples(const char *phase,bool idle)
{
    uint32_t start=HAL_GetTick(),first=0u,last=0u,count=0u;
    int32_t minimum=INT32_MAX,maximum=0;
    while(HAL_GetTick()-start<1800u&&count<6u) {
        comp_imu_sample_t s;comp_imu_poll_t p=comp_lsm6dso_poll(&imu,HAL_GetTick(),&s);
        if(p==COMP_IMU_IO_ERROR)return false;
        if(p==COMP_IMU_SAMPLE) {
            if(!count)first=s.timestamp_ms;
            else {int32_t interval=(int32_t)(s.timestamp_ms-last);if(interval<minimum)minimum=interval;if(interval>maximum)maximum=interval;}
            last=s.timestamp_ms;++count;
        }
        HAL_Delay(1u);
    }
    uint8_t ctrl[2]={0},ctrl6=0u,status=0u;
    bool ok=imu_read(NULL,0x10u,ctrl,2u)&&imu_read(NULL,0x15u,&ctrl6,1u)&&count==6u;
    if(idle) {
        uint8_t discard[6];
        ok=ok&&imu_read(NULL,0x22u,discard,sizeof(discard));
        HAL_Delay(100u);
        ok=ok&&imu_read(NULL,0x1Eu,&status,1u)&&(status&2u)==0u&&ctrl[0]==0x18u&&ctrl[1]==0u&&ctrl6==0x10u;
    }else ok=ok&&ctrl[0]==0x38u&&ctrl[1]==0x30u;
    ok=ok&&minimum>=(idle?60:12)&&maximum<=(idle?110:30);
    say("IMU_MODE phase=%s idle=%u samples=%lu span_ms=%lu interval_min_ms=%ld interval_max_ms=%ld ctrl1=%02x ctrl2=%02x ctrl6=%02x gyro_drdy_after_clear=%u ok=%u\r\n",
        phase,idle,(unsigned long)count,(unsigned long)(last-first),(long)minimum,(long)maximum,
        ctrl[0],ctrl[1],ctrl6,(status>>1)&1u,ok);
    return ok;
}
static void imu_self_test(void)
{
    say("BEGIN test=IMU_SELF_TEST owner_keep_still=1 internal_stimulus=1 calibrated_accuracy=0\r\n");
    uint8_t id=0u;bool io=shared_spi()&&imu_read(NULL,0x0Fu,&id,1u)&&id==0x6Cu;
    const char *failure="IO_OR_CONFIGURATION_FAILED";
    int32_t off[3],on[3],again[3];bool quiet_off=false,quiet_on=false,quiet_again=false,limits=true,quiet=true;
    bool xl_limits=false,gy_limits=false;
    /* Reset only this MEMS device, with a finite reset wait. */
    uint8_t reset=1u;
    io=io&&imu_write(NULL,0x12u,&reset,1u);
    uint32_t reset_start=HAL_GetTick();
    while(io&&(reset&1u)&&HAL_GetTick()-reset_start<100u){HAL_Delay(1u);io=imu_read(NULL,0x12u,&reset,1u);}
    io=io&&(reset&1u)==0u&&imu_reg8(0x12u,0x44u)&&imu_reg8(0x18u,0x02u)&&imu_reg8(0x10u,0x38u)&&imu_reg8(0x11u,0u);
    if(io) {
        HAL_Delay(100u);
        io=imu_st_average(1u,0x28u,false,"xl_off",off,&quiet_off)&&imu_reg8(0x14u,0x02u);
        HAL_Delay(100u);
        io=io&&imu_st_average(1u,0x28u,false,"xl_negative",on,&quiet_on)&&imu_reg8(0x14u,0u);
        HAL_Delay(100u);
        io=io&&imu_st_average(1u,0x28u,false,"xl_return",again,&quiet_again);
        if(io) {
            xl_limits=true;quiet=quiet_off&&quiet_on&&quiet_again;
            for(unsigned k=0u;k<3u;++k) {
                int32_t d=on[k]-off[k];if(d<0)d=-d;
                int32_t returned=again[k]-off[k];if(returned<0)returned=-returned;
                if(d<50||d>1700)xl_limits=false;
                if(returned>50)quiet=false;
                say("IMU_ST_AXIS sensor=xl axis=%u off=%ld on=%ld return=%ld delta=%ld min=50 max=1700 units=mg\r\n",
                    k,(long)off[k],(long)on[k],(long)again[k],(long)d);
            }
        }
    }
    io=io&&imu_reg8(0x10u,0u)&&imu_reg8(0x11u,0x5Cu); /* 208Hz, +/-2000dps */
    if(io) {
        HAL_Delay(100u);
        io=imu_st_average(2u,0x22u,true,"gy_off",off,&quiet_off)&&imu_reg8(0x14u,0x04u);
        HAL_Delay(100u);
        io=io&&imu_st_average(2u,0x22u,true,"gy_positive",on,&quiet_on)&&imu_reg8(0x14u,0u);
        HAL_Delay(100u);
        io=io&&imu_st_average(2u,0x22u,true,"gy_return",again,&quiet_again);
        if(io) {
            gy_limits=true;quiet=quiet&&quiet_off&&quiet_on&&quiet_again;
            for(unsigned k=0u;k<3u;++k) {
                int32_t d=on[k]-off[k];if(d<0)d=-d;
                int32_t returned=again[k]-off[k];if(returned<0)returned=-returned;
                if(d<150000||d>700000)gy_limits=false;
                if(returned>5000)quiet=false;
                say("IMU_ST_AXIS sensor=gy axis=%u off=%ld on=%ld return=%ld delta=%ld min=150000 max=700000 units=mdps\r\n",
                    k,(long)off[k],(long)on[k],(long)again[k],(long)d);
            }
        }
    }
    /* Always revoke electrostatic stimulus, including after an I/O error. */
    bool stimulus_off=imu_reg8(0x14u,0u);
    bool powered_down=imu_reg8(0x10u,0u)&&imu_reg8(0x11u,0u);
    bool modes=false;
    if(io&&stimulus_off&&powered_down) {
        modes=comp_lsm6dso_start(&imu,imu_read,imu_write,NULL,HAL_GetTick())&&imu_mode_samples("run52",false)&&
            comp_lsm6dso_set_idle(&imu,true,HAL_GetTick())&&imu_mode_samples("idle12_5",true)&&
            comp_lsm6dso_set_idle(&imu,false,HAL_GetTick())&&imu_mode_samples("resume52",false);
    }
    bool stopped=comp_lsm6dso_stop(&imu);
    limits=xl_limits&&gy_limits;
    say("IMU_ST_SUMMARY id=%02x io=%u xl_limits=%u gy_limits=%u stationary=%u stimulus_disabled=%u modes_restored=%u stopped=%u\r\n",
        id,io,xl_limits,gy_limits,quiet,stimulus_off,modes,stopped);
    if(io&&stimulus_off&&modes&&stopped)failure=!quiet?"MOTION_CONTAMINATED":!limits?"SELF_TEST_OUT_OF_SPEC":"SIX_AXES_SELF_TEST_AND_MODES_PASSED";
    finish("IMU_SELF_TEST",failure);
}
static void imu_interrupt_path(void)
{
    say("BEGIN test=IMU_INTERRUPT_PATH route=LSM6DSO_INT1_TCA_P3_PC13 digital_path_only=1 no_p4_p7=1\r\n");
    uint8_t original[4]={0},base[4]={0},up[4]={0},down[4]={0},status=0u;
    bool io=shared_spi()&&io_snapshot(original)&&original[2]==0u&&(original[3]&8u)!=0u&&
        comp_lsm6dso_start(&imu,imu_read,imu_write,NULL,HAL_GetTick());
    uint32_t start=HAL_GetTick();
    while(io&&imu.state!=COMP_IMU_READY&&HAL_GetTick()-start<150u) {
        comp_imu_sample_t sample;
        io=comp_lsm6dso_poll(&imu,HAL_GetTick(),&sample)!=COMP_IMU_IO_ERROR;
        HAL_Delay(1u);
    }
    io=io&&imu.state==COMP_IMU_READY&&imu_reg8(0x0Du,0u);
    HAL_Delay(50u);
    io=io&&imu_read(NULL,0x1Eu,&status,1u)&&(status&3u)==3u&&io_snapshot(base);
    HAL_Delay(1u);
    bool baseline=io&&(base[0]&8u)==0u&&HAL_GPIO_ReadPin(GPIOC,GPIO_PIN_13)==GPIO_PIN_SET;
    bool path=baseline;unsigned cycles=0u;
    say("IMU_IRQ_BASELINE status=%02x inputs=%02x direction=%02x polarity=%02x pc13=%u ok=%u\r\n",
        status,base[0],base[3],base[2],HAL_GPIO_ReadPin(GPIOC,GPIO_PIN_13),baseline);
    for(unsigned n=0u;n<3u&&path;++n) {
        io=imu_reg8(0x0Du,0x01u);HAL_Delay(25u);
        unsigned assert_before=HAL_GPIO_ReadPin(GPIOC,GPIO_PIN_13);
        io=io&&io_snapshot(up);HAL_Delay(1u);
        unsigned assert_after=HAL_GPIO_ReadPin(GPIOC,GPIO_PIN_13);
        io=io&&imu_reg8(0x0Du,0u);HAL_Delay(1u);
        unsigned release_before=HAL_GPIO_ReadPin(GPIOC,GPIO_PIN_13);
        io=io&&io_snapshot(down);HAL_Delay(1u);
        unsigned release_after=HAL_GPIO_ReadPin(GPIOC,GPIO_PIN_13);
        bool isolated=io&&((up[0]^base[0])&0x2Du)==8u&&((down[0]^base[0])&0x2Du)==0u;
        bool unchanged=io&&up[1]==original[1]&&down[1]==original[1]&&up[2]==original[2]&&
            down[2]==original[2]&&up[3]==original[3]&&down[3]==original[3];
        bool ok=isolated&&unchanged&&assert_before==0u&&assert_after==1u&&release_before==0u&&release_after==1u;
        say("IMU_IRQ_CYCLE index=%u baseline_inputs=%02x high_inputs=%02x low_inputs=%02x assert_before_read=%u assert_after_read=%u release_before_read=%u release_after_read=%u only_p3_input_changed=%u io_registers_unchanged=%u ok=%u\r\n",
            n,base[0],up[0],down[0],assert_before,assert_after,release_before,release_after,isolated,unchanged,ok);
        path=path&&ok;if(ok)++cycles;
    }
    bool stopped=imu.write!=NULL&&comp_lsm6dso_stop(&imu);
    uint8_t final[4]={0};bool final_read=io_snapshot(final);
    HAL_Delay(1u);
    bool restored=final_read&&final[1]==original[1]&&final[2]==original[2]&&final[3]==original[3]&&
        (final[0]&8u)==0u&&HAL_GPIO_ReadPin(GPIOC,GPIO_PIN_13)==GPIO_PIN_SET;
    say("IMU_IRQ_SUMMARY cycles=%u isolated_path=%u stopped=%u final_registers_unchanged=%u final_inputs=%02x final_pc13=%u\r\n",
        cycles,path,stopped,restored,final[0],HAL_GPIO_ReadPin(GPIOC,GPIO_PIN_13));
    finish("IMU_INTERRUPT_PATH",path&&cycles==3u&&stopped&&restored?
        "IMU_P3_EXPANDER_PC13_INTERRUPT_PATH_PASSED":"INTERRUPT_PATH_NOT_QUALIFIED");
}
static bool touch_ids(const char *phase)
{
    uint8_t a3=0u,a6=0u,a8=0u;
    bool ok=touch_read_mode(0xA3u,&a3,1u,false)&&touch_read_mode(0xA6u,&a6,1u,false)&&touch_read_mode(0xA8u,&a8,1u,false);
    ok=ok&&a3==0x64u&&a6==0x01u&&a8==0x11u;
    say("TOUCH_RESET_IDS phase=%s a3=%02x a6=%02x a8=%02x ok=%u\r\n",phase,a3,a6,a8,ok);
    return ok;
}
static void touch_reset_path(void)
{
    say("BEGIN test=TOUCH_RESET_PATH rate_hz=10000 only_tca_mask=02 no_p4_p7=1\r\n");
    uint8_t saved[4]={0},low[4]={0},high[4]={0},restored[4]={0};
    bool saved_ok=io_snapshot(saved),baseline=saved_ok&&touch_prepare(10000u,false)&&touch_ids("released_before");
    bool asserted=baseline&&io_bit(0x02u,false);HAL_Delay(20u);
    bool low_read=asserted&&io_snapshot(low),negative=true;unsigned nacks=0u;
    if(asserted)for(unsigned n=0u;n<3u;++n) {
        uint8_t id=0u;bool ack=touch_read_mode(0xA3u,&id,1u,false);uint32_t error=HAL_I2C_GetError(&touch_bus);
        if(!ack&&error==HAL_I2C_ERROR_AF)++nacks;else negative=false;
        say("TOUCH_RESET_HELD_LOW index=%u ack=%u id=%02x hal_error=%08lx\r\n",n,ack,id,(unsigned long)error);HAL_Delay(10u);
    }
    bool released=io_bit(0x02u,true);HAL_Delay(350u);
    bool high_read=released&&io_snapshot(high),recovered=released&&touch_ids("released_after");
    bool other_bits=saved_ok&&low_read&&high_read&&
        (((saved[1]^low[1])|(saved[1]^high[1])|(saved[3]^low[3])|(saved[3]^high[3]))&0xFDu)==0u;
    bool physical_level=low_read&&high_read&&(low[0]&2u)==0u&&(high[0]&2u)!=0u;
    bool restore_latch=saved_ok&&io_bit(0x02u,(saved[1]&2u)!=0u)&&io_snapshot(restored)&&restored[1]==saved[1]&&restored[3]==saved[3];
    say("TOUCH_RESET_SUMMARY baseline=%u asserted=%u nack_count=%u released=%u recovered=%u p1_levels=%u other_bits_unchanged=%u latch_restored=%u before_latch=%02x low_latch=%02x high_latch=%02x restored_latch=%02x\r\n",
        baseline,asserted,nacks,released,recovered,physical_level,other_bits,restore_latch,saved[1],low[1],high[1],restored[1]);
    finish("TOUCH_RESET_PATH",baseline&&asserted&&negative&&nacks==3u&&recovered&&physical_level&&other_bits&&restore_latch?
        "RESET_CONTROL_REACHED_TOUCH_AND_RECOVERED":"RESET_PATH_NOT_QUALIFIED");
}
static bool rtc_ssr(uint32_t *value)
{
    for(unsigned n=0u;n<8u;++n){uint32_t a=RTC->SSR,b=RTC->SSR;if(a==b){*value=a;return true;}}
    return false;
}
static void clock_observation(void)
{
    /* Observe inherited LSE/RTC without resetting or writing backup state,
     * calendar, prescaler, alarms or oscillator configuration. */
    bool had_apb=__HAL_RCC_RTCAPB_IS_CLK_ENABLED();__HAL_RCC_RTCAPB_CLK_ENABLE();
    bool lse=__HAL_RCC_GET_FLAG(RCC_FLAG_LSERDY),css=__HAL_RCC_GET_FLAG(RCC_FLAG_LSECSSD);
    uint32_t source=__HAL_RCC_GET_RTC_SOURCE(),icsr=RTC->ICSR,pre=RTC->PRER;
    bool binary=(icsr&RTC_ICSR_BIN)==RTC_ICSR_BIN_0&&(icsr&RTC_ICSR_INIT)==0u;
    bool configured=lse&&!css&&source==RCC_RTCCLKSOURCE_LSE&&binary&&((pre&RTC_PRER_PREDIV_A)>>RTC_PRER_PREDIV_A_Pos)==31u;
    say("CLOCK_OBSERVE hse_ready=%u lse_ready=%u lse_css_fault=%u rtc_source=%08lx icsr=%08lx prer=%08lx configured=%u precision_calibrated=0\r\n",
        __HAL_RCC_GET_FLAG(RCC_FLAG_HSERDY),lse,css,(unsigned long)source,(unsigned long)icsr,(unsigned long)pre,configured);
    bool advances=configured;uint32_t previous=0u,start=HAL_GetTick();
    if(configured)advances=rtc_ssr(&previous);
    for(unsigned n=0u;n<3u&&advances;++n) {
        HAL_Delay(500u);uint32_t current=0u,ms=HAL_GetTick(),delta;
        bool read=rtc_ssr(&current);delta=previous-current;
        bool valid=read&&delta>0u&&delta<2048u;
        say("CLOCK_RTC_STEP index=%u host_tick_ms=%lu rtc_delta=%lu ssr=%08lx valid=%u\r\n",
            n,(unsigned long)(ms-start),(unsigned long)delta,(unsigned long)current,valid);
        advances=advances&&valid;previous=current;start=ms;
    }
    if(!had_apb)__HAL_RCC_RTCAPB_CLK_DISABLE();
    finish("CLOCKS",advances?"LSE_RTC_BINARY_ADVANCE_OBSERVED":"LSE_RTC_NOT_QUALIFIED");
}
