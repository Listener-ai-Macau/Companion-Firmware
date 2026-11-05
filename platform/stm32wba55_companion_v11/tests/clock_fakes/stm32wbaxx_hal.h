#ifndef CLOCK_FAKE_HAL_H
#define CLOCK_FAKE_HAL_H
#include <stdint.h>
typedef struct {uint32_t unused;} RTC_HandleTypeDef;
typedef struct {uint32_t ICSR,PRER,SSR;} fake_rtc_t;
extern fake_rtc_t fake_rtc;
extern uint32_t fake_lse_ready,fake_rtc_source,fake_css;
#define RTC (&fake_rtc)
#define RTC_BKP_DR4 4u
#define RCC_FLAG_LSERDY 1u
#define RCC_FLAG_LSECSSD 2u
#define RCC_RTCCLKSOURCE_LSE 1u
#define RTC_ICSR_BIN 3u
#define RTC_BINARY_ONLY 1u
#define RTC_ICSR_INITS 16u
#define RTC_ICSR_INIT 128u
#define RTC_PRER_PREDIV_A 0x007F0000u
#define RTC_PRER_PREDIV_A_Pos 16u
#define __HAL_RCC_GET_FLAG(f) ((f)==RCC_FLAG_LSERDY?fake_lse_ready:fake_css)
#define __HAL_RCC_GET_RTC_SOURCE() (fake_rtc_source)
uint32_t HAL_GetTick(void);
uint32_t HAL_RTCEx_BKUPRead(const RTC_HandleTypeDef *,uint32_t);
void HAL_RTCEx_BKUPWrite(const RTC_HandleTypeDef *,uint32_t,uint32_t);
#endif
