"""Exercise production ADC/power sequencing with asynchronous register/port models."""
from pathlib import Path
import argparse,hashlib,json,shutil,subprocess
from verify_wba_spi_nor_adapter import find_vsdevcmd
ROOT=Path(__file__).resolve().parents[1]
STUB=r'''
#ifndef FAKE_ADC_HAL_H
#define FAKE_ADC_HAL_H
#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>
#include <assert.h>
typedef struct {uint32_t CFGR1,PWRR;} ADC_TypeDef;
typedef struct {uint32_t CFGR1;} SYSCFG_TypeDef;
extern ADC_TypeDef fake_adc;extern SYSCFG_TypeDef fake_syscfg;extern uint8_t fake_factory[3];
extern uint32_t fake_ldo,fake_ldo_ready,fake_calibrating,fake_ready,fake_eoc,fake_overrun;
extern uint32_t fake_init,fake_cal_starts,fake_enables,fake_starts,fake_reset,fake_clock,fake_channel,fake_external;
extern uint16_t fake_data;
extern uint32_t fake_enabled;
#define ADC4 (&fake_adc)
#define SYSCFG (&fake_syscfg)
#define VREFINT_CAL_ADDR ((uintptr_t)&fake_factory[1])
#define VREFINT_CAL_VREF 3000u
#define SYSCFG_CFGR1_BOOSTEN 2u
#define SYSCFG_CFGR1_ANASWVDD 4u
#define ADC_CFGR1_DMAEN 1u
#define ADC_CFGR1_DMACFG 2u
#define ADC_PWRR_AUTOFF 1u
#define ADC_CHANNEL_VREFINT 17u
#define ADC_CHANNEL_4 4u
#define ADC_FLAG_OVR 1u
#define ADC_FLAG_EOC 2u
#define HAL_OK 0
#define MODIFY_REG(r,c,s) ((r)=((r)&~(c))|(s))
#define CLEAR_BIT(r,c) ((r)&=~(c))
#define __get_IPSR() 0u
#define __HAL_RCC_SYSCFG_CLK_ENABLE() ((void)0)
#define __HAL_RCC_ADC_CONFIG(c) ((void)(c))
#define __HAL_RCC_ADC4_CLK_ENABLE() (fake_clock=1u)
#define __HAL_RCC_ADC4_CLK_DISABLE() (fake_clock=0u)
#define __HAL_RCC_ADC4_FORCE_RESET() do {fake_reset++;fake_ldo=0;fake_ldo_ready=0;fake_calibrating=0;fake_ready=0;fake_eoc=0;fake_overrun=0;fake_enabled=0;}while(0)
#define __HAL_RCC_ADC4_RELEASE_RESET() ((void)0)
#define HAL_SYSCFG_EnableIOAnalogSwitchBooster() (fake_syscfg.CFGR1|=SYSCFG_CFGR1_BOOSTEN)
#define HAL_RCC_GetSysClockFreq() 98304000u
#define __HAL_ADC_GET_FLAG(p,f) ((void)(p),(f)==ADC_FLAG_OVR?fake_overrun:fake_eoc)
typedef struct {uint32_t ClockPrescaler,Resolution,DataAlign,ScanConvMode,EOCSelection,NbrOfConversion,ExternalTrigConv,Overrun,SamplingTimeCommon1,SamplingTimeCommon2,TriggerFrequencyMode;} ADC_InitTypeDef;
typedef struct {ADC_TypeDef *Instance;ADC_InitTypeDef Init;} ADC_HandleTypeDef;
typedef struct {uint32_t Channel,Rank,SamplingTime;} ADC_ChannelConfTypeDef;
static inline int HAL_ADC_Init(ADC_HandleTypeDef *p){assert(p->Instance==ADC4 && fake_ldo && fake_ldo_ready);fake_init++;return HAL_OK;}
static inline int HAL_ADC_ConfigChannel(ADC_HandleTypeDef *p,const ADC_ChannelConfTypeDef *c){(void)p;assert(!fake_calibrating&&!fake_enabled);fake_channel=c->Channel;if(c->Channel==ADC_CHANNEL_4)fake_external++;return HAL_OK;}
#define LL_ADC_ClearFlag_LDORDY(p) ((void)(p),fake_ldo_ready=0u)
#define LL_ADC_EnableInternalRegulator(p) ((void)(p),fake_ldo=1u)
#define LL_ADC_IsActiveFlag_LDORDY(p) ((void)(p),fake_ldo_ready)
#define LL_ADC_IsInternalRegulatorEnabled(p) ((void)(p),fake_ldo)
#define LL_ADC_StartCalibration(p) ((void)(p),fake_calibrating=1u,fake_cal_starts++)
#define LL_ADC_IsCalibrationOnGoing(p) ((void)(p),fake_calibrating)
#define LL_ADC_ClearFlag_ADRDY(p) ((void)(p),fake_ready=0u)
#define LL_ADC_Enable(p) ((void)(p),fake_enables++,fake_enabled=1u)
#define LL_ADC_Disable(p) ((void)(p),fake_enabled=0u)
#define LL_ADC_IsEnabled(p) ((void)(p),fake_enabled)

#define LL_ADC_IsActiveFlag_ADRDY(p) ((void)(p),fake_ready)
#define LL_ADC_ClearFlag_EOC(p) ((void)(p),fake_eoc=0u)
#define LL_ADC_ClearFlag_EOS(p) ((void)(p))
#define LL_ADC_ClearFlag_OVR(p) ((void)(p),fake_overrun=0u)
#define LL_ADC_REG_StartConversion(p) ((void)(p),fake_starts++)
#define LL_ADC_REG_ReadConversionData12(p) ((void)(p),fake_data)
#endif
'''
def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args();out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    platform=ROOT/'platform/stm32wba55_companion_v11';power=ROOT/'app/companion_pendant/power'
    files=[platform/'battery_adc.c',platform/'battery_adc.h',platform/'tests/test_battery_adc_async.c',power/'wba_power_monitor.c',power/'wba_power_monitor.h']
    for p in files:shutil.copyfile(p,out/p.name)
    constants=['ADC_REGULAR_RANK_1','ADC_SAMPLINGTIME_COMMON_1','RCC_ADCCLKSOURCE_SYSCLK','ADC_CLOCK_ASYNC_DIV4','ADC_RESOLUTION_12B','ADC_DATAALIGN_RIGHT','ADC_SCAN_DISABLE','ADC_EOC_SINGLE_CONV','ADC_SOFTWARE_START','ADC_OVR_DATA_PRESERVED','ADC_SAMPLETIME_814CYCLES_5','ADC_TRIGGER_FREQ_LOW']
    (out/'fake_adc_hal.h').write_text(STUB+'\n'+''.join(f'#define {name} 0u\n'for name in constants))
    for name in ['stm32wbaxx_hal.h','stm32wbaxx_ll_adc.h']:(out/name).write_text('#include "fake_adc_hal.h"\n')
    (out/'companion_v11_board.h').write_text('#include <stdbool.h>\n#include <stdint.h>\nstatic inline bool comp_v11_battery_divider_safe(uint32_t top,uint32_t bottom,uint32_t reference,uint32_t maximum){return top && bottom && reference>100u && (uint64_t)maximum*bottom<=(uint64_t)(reference-100u)*(top+bottom);}\n')
    cmd=['cl.exe','/nologo','/std:c11','/W4','/WX','/DCOMPANION_WBA_BATTERY_LINEAR_ESTIMATE=1','battery_adc.c','wba_power_monitor.c','test_battery_adc_async.c','/Fe:test.exe']
    vc=find_vsdevcmd();assert vc
    script=out/'build.cmd';script.write_text('@echo off\ncall "'+str(vc)+'" -arch=amd64 -host_arch=amd64 >nul\nif errorlevel 1 exit /b %errorlevel%\n'+subprocess.list2cmdline(cmd)+'\n')
    with (out/'build.log').open('wb')as log:r=subprocess.run(['cmd.exe','/d','/c',str(script)],cwd=out,stdout=log,stderr=subprocess.STDOUT)
    if r.returncode:print((out/'build.log').read_text(errors='replace'));r.check_returncode()
    r=subprocess.run([str(out/'test.exe')],cwd=out,capture_output=True,timeout=10);(out/'test.log').write_bytes(r.stdout+r.stderr);print(r.stdout.decode(errors='replace'));r.check_returncode()
    (out/'result.json').write_text(json.dumps(dict(result='PRODUCTION_ADC_AND_CAPTURE_LEASE_SOFTWARE_ONLY',hardwareAcceptance='NOT_RUN',fullChainAcceptance='NOT_QUALIFIED',sourceSha256={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()for p in files}),indent=2)+'\n')
if __name__=='__main__':main()
