#include "clock_target.h"
#include "stm32wbaxx_hal.h"
#include <stdio.h>
#include <string.h>
#define CHECK(x) do { if (!(x)) {printf("FAIL target line %d: %s\n",__LINE__,#x);return 1;} } while (0)
fake_rtc_t fake_rtc={RTC_BINARY_ONLY,31u<<16,UINT32_MAX};
uint32_t fake_lse_ready=1,fake_rtc_source=RCC_RTCCLKSOURCE_LSE,fake_css;
RTC_HandleTypeDef hrtc;
static uint32_t backup[32],now,writes;
uint32_t HAL_GetTick(void){return now;}
uint32_t HAL_RTCEx_BKUPRead(const RTC_HandleTypeDef *h,uint32_t i){(void)h;return backup[i];}
void HAL_RTCEx_BKUPWrite(const RTC_HandleTypeDef *h,uint32_t i,uint32_t v){(void)h;backup[i]=v;++writes;}
int main(void)
{
    comp_clock_t c={0};backup[0]=123;backup[1]=456;backup[2]=789;backup[3]=333;backup[16]=999;
    CHECK(comp_v11_clock_domain_continuous());
    comp_v11_clock_restore(&c,false);CHECK(!c.valid);
    CHECK(comp_clock_sync(&c,23,59,59,now));comp_v11_clock_checkpoint(&c);
    /* Reset only the product/HAL tick while RTC and backup words survive. */
    memset(&c,0,sizeof(c));fake_rtc.SSR-=2048;
    comp_v11_clock_restore(&c,true);CHECK(c.valid && c.utc_seconds==1 && c.milliseconds==0);
    uint32_t before=writes;fake_rtc.SSR-=61u*1024u;now=20;
    comp_v11_clock_poll(&c,now,false);CHECK(c.valid && c.utc_seconds==62 && writes==before);
    comp_v11_clock_poll(&c,now,true);CHECK(writes>before);
    CHECK(backup[0]==123 && backup[1]==456 && backup[2]==789 && backup[3]==333 && backup[16]==999);
    fake_css=1;comp_v11_clock_poll(&c,now,false);CHECK(!c.valid);
    fake_css=0;comp_v11_clock_restore(&c,true);CHECK(!c.valid);
    CHECK(comp_clock_sync(&c,12,0,0,now));comp_v11_clock_checkpoint(&c);
    const uint32_t midnight=20001u*86400u;
    CHECK(comp_clock_sync_unix(&c,midnight-1u,now));comp_v11_clock_checkpoint(&c);
    memset(&c,0,sizeof(c));now=0;fake_rtc.SSR-=2048;
    comp_v11_clock_restore(&c,true);
    CHECK(c.valid && c.calendar_valid && comp_clock_unix(&c,now)==midnight+1u);
    before=writes;fake_rtc.SSR-=61u*1024u;
    comp_v11_clock_poll(&c,now,true);CHECK(writes>before && c.utc_seconds==midnight+62u);
    CHECK(backup[0]==123 && backup[1]==456 && backup[2]==789 && backup[3]==333 && backup[16]==999);
    comp_v11_clock_restore(&c,false);CHECK(!c.valid && !c.calendar_valid);
    fake_rtc.PRER=30u<<16;CHECK(!comp_v11_clock_domain_continuous());
    comp_v11_clock_poll(&c,now,false);CHECK(!c.valid);
    puts("PASS actual clock target / mocked RTC: restart, radio registers preserved, capture deferral, oscillator/config failure");
    puts("PASS full date retained across reset/midnight, minute checkpoint and lost RTC domain");return 0;
}
