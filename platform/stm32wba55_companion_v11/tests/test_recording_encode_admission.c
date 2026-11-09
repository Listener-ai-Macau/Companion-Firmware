#include <assert.h>
#include <stdint.h>
#include <stdbool.h>
#include <stdio.h>
#include "capture_radio_window.h"
#define COMPANION_WBA_BLE_LINKED 1
typedef struct { bool dma_window; } microphone_t;
typedef struct { microphone_t microphone; } board_t;
typedef struct { board_t *board; } comp_v11_product_app_t;
static comp_capture_radio_window_t radio;
static uint32_t tick,ble_calls;
static bool valid=true,busy=true;
static uint32_t next_us=0u;
static bool comp_v11_microphone_hal_encode_window(microphone_t *m){return m->dma_window;}
static bool comp_v11_ble_capture_encode_window(bool pending)
{++ble_calls;return comp_capture_radio_window_open(&radio,tick,pending,valid,busy,next_us);}
/* @PRODUCTION_ENCODE_ADMISSION@ */
int main(void)
{
    board_t b={{true}};comp_v11_product_app_t app={&b};
    /* Active capture preserves the original urgency and DMA-safety order. */
    assert(!recording_encode_window(&app,true,2u));tick=11u;
    assert(!recording_encode_window(&app,true,2u));tick=12u;
    assert(recording_encode_window(&app,true,2u));
    tick=13u;assert(recording_encode_window(&app,true,3u));
    b.microphone.dma_window=false;uint32_t before=ble_calls;
    assert(!recording_encode_window(&app,true,3u) && ble_calls==before);
    /* STOP/PAUSE no longer bypass the policy even with a full PCM queue;
     * a stopped DMA has no future capture slot to wait for. */
    tick=20u;assert(!recording_encode_window(&app,false,8u));tick=31u;
    assert(!recording_encode_window(&app,false,8u));tick=32u;
    assert(recording_encode_window(&app,false,8u));
    /* The final empty-queue padding frame has the same bounded courtesy. */
    tick=40u;assert(!recording_encode_window(&app,false,0u));tick=52u;
    assert(recording_encode_window(&app,false,0u));
    tick=60u;busy=false;next_us=7001u;
    assert(recording_encode_window(&app,false,0u));
    valid=false;busy=true;next_us=0u;
    assert(recording_encode_window(&app,false,0u));
    puts("PASS exact production admission: active DMA safety,30ms urgent queue,STOP/PAUSE drain and final padding12ms bounded courtesy,quiet gap,missing query; software only");
    return 0;
}
