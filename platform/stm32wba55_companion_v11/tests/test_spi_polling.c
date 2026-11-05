#include "spi_polling.h"
#include <stdio.h>
#include <stdlib.h>

SPI_TypeDef test_spi1, test_spi3;
static unsigned calls, fail_call;
static size_t seen;
static bool dummy;
static uint8_t source[4100], destination[4100];
#define CHECK(x) do { if (!(x)) { fprintf(stderr,"failure at %d\n",__LINE__); exit(1); } } while (0)
static uint8_t value(size_t offset) { return (uint8_t)(offset * 17u + offset / 256u); }
HAL_StatusTypeDef HAL_SPI_TransmitReceive(SPI_HandleTypeDef *b, const uint8_t *tx,
    uint8_t *rx, uint16_t n, uint32_t timeout)
{
    ++calls;
    if (calls == fail_call) return HAL_ERROR;
    CHECK(timeout==23u && n!=0u);
    CHECK(b->Instance != SPI3 || n<=512u);
    CHECK(rx==destination+seen);
    CHECK(tx==(dummy?rx:source+seen));
    for (size_t i=0;i<n;++i) CHECK(tx[i]==(dummy?255u:value(seen+i)));
    for (size_t i=0;i<n;++i) rx[i]=value(seen+i);
    seen+=n;
    return HAL_OK;
}
HAL_StatusTypeDef HAL_SPI_Transmit(SPI_HandleTypeDef *b, const uint8_t *tx,
    uint16_t n, uint32_t timeout)
{
    ++calls;
    if (calls == fail_call) return HAL_ERROR;
    CHECK(timeout==23u && n!=0u && (b->Instance!=SPI3 || n<=512u));
    CHECK(tx==source+seen);
    for (size_t i=0;i<n;++i) CHECK(tx[i]==value(seen+i));
    seen+=n; return HAL_OK;
}
int main(void)
{
    SPI_HandleTypeDef bus={SPI3};
    for (size_t i=0;i<sizeof(source);++i) source[i]=value(i);
    const size_t lengths[]={1,511,512,513,1023,1024,4096,4100};
    for (unsigned mode=0;mode<3u;++mode) {
        for (unsigned j=0;j<sizeof(lengths)/sizeof(lengths[0]);++j) {
            memset(destination,0xA5,sizeof(destination)); calls=0;seen=0;dummy=mode==0u;
            CHECK(comp_v11_spi_polling_transfer(&bus,mode==0u?NULL:source,
                mode==2u?NULL:destination,lengths[j],23u));
            CHECK(seen==lengths[j] && calls==(lengths[j]+511u)/512u);
            if (mode!=2u) for (size_t i=0;i<seen;++i) CHECK(destination[i]==value(i));
            for (size_t i=seen;i<sizeof(destination);++i) CHECK(destination[i]==0xA5);
        }
    }
    calls=0;seen=0;dummy=false;fail_call=2;memset(destination,0xA5,sizeof(destination));
    CHECK(!comp_v11_spi_polling_transfer(&bus,source,destination,4096,23u));
    CHECK(calls==2u && seen==512u && destination[1024]==0xA5);
    fail_call=0;calls=0;seen=0;bus.Instance=SPI1;
    CHECK(comp_v11_spi_polling_transfer(&bus,source,destination,4096,23u));
    CHECK(calls==1u && seen==4096u);
    calls=0;
    CHECK(!comp_v11_spi_polling_transfer(NULL,source,destination,4,23u));
    CHECK(!comp_v11_spi_polling_transfer(&bus,source,destination,0,23u));
    CHECK(!comp_v11_spi_polling_transfer(&bus,source,destination,65536,23u));
    CHECK(!comp_v11_spi_polling_transfer(&bus,NULL,NULL,4,23u));
    CHECK(calls==0u);
    puts("PASS_SPI_POLLING_SOFTWARE_ONLY: SPI3 boundaries, dummy/full-duplex/TX, buffer integrity, failure stops, SPI1 preserved");
    return 0;
}
