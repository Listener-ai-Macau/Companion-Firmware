#include "../ble_gate_observation.h"
#include <assert.h>
int main(void)
{
 comp_v11_ble_gate_observation_t v={.flags=COMP_RADIO_KNOWN};
 comp_spi_page(&v,10u,true);comp_v11_ble_gate_observe_radio(&v,20u,true);
 comp_v11_ble_gate_observe_radio(&v,60u,false);comp_spi_page(&v,90u,false);
 assert(v.spi_radio_us==40u && !(v.flags&(COMP_SPI_INVALID|COMP_SPI_ACTIVE)));
 v=(comp_v11_ble_gate_observation_t){.flags=COMP_RADIO_ON|COMP_RADIO_KNOWN};
 comp_spi_page(&v,10u,true);comp_spi_page(&v,110u,false);assert(v.spi_radio_us==100u);
 v=(comp_v11_ble_gate_observation_t){.flags=COMP_RADIO_ON|COMP_RADIO_KNOWN};
 comp_spi_page(&v,UINT32_MAX-10u,true);comp_spi_page(&v,9u,false);
 assert(v.spi_radio_us==20u && !(v.flags&COMP_SPI_INVALID));
 v=(comp_v11_ble_gate_observation_t){0};comp_spi_page(&v,10u,true);assert(v.flags&COMP_SPI_INVALID);
 v=(comp_v11_ble_gate_observation_t){.flags=COMP_RADIO_KNOWN};
 comp_spi_page(&v,10u,true);comp_v11_ble_gate_observe_radio(&v,20u,true);
 comp_v11_ble_gate_observe_radio(&v,30u,true);assert(v.flags&COMP_SPI_INVALID);
 v=(comp_v11_ble_gate_observation_t){.flags=COMP_RADIO_ON|COMP_RADIO_KNOWN};
 comp_spi_page(&v,10u,true);comp_spi_page(&v,9u,false);assert(v.flags&COMP_SPI_INVALID);
 v=(comp_v11_ble_gate_observation_t){.flags=COMP_RADIO_KNOWN};
 comp_v11_ble_gate_observe_origin(&v,true);comp_v11_ble_gate_observe_open(&v,10u);
 comp_spi_page(&v,20u,true);comp_v11_ble_gate_observe_radio(&v,30u,true);
 comp_spi_page(&v,70u,false);comp_v11_ble_gate_observe_radio(&v,90u,false);
 comp_v11_ble_gate_observe_close(&v,110u,1u);
 assert(v.total_us==100u && v.radio_on_us==60u && v.spi_radio_us==40u && !comp_radio_invalid(&v));
 return 0;
}
