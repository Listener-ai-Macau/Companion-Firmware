#include "ble_event_copy.h"

#include <stdio.h>
#include <string.h>

static int fail_line(int line, const char *message)
{
    fprintf(stderr,"FAIL line=%d %s\n",line,message);
    return line;
}
#define CHECK(expression,message) \
    do { if(!(expression)) return fail_line(__LINE__,message); } while(0)

int main(void)
{
    uint8_t contiguous[]={0x04u,0xFFu,4u,0x01u,0x02u,0x03u,0x04u};
    uint8_t primary[]={0x04u,0xFFu,6u,0x10u,0x11u};
    uint8_t extension[]={0x12u,0x13u,0x14u,0x15u};
    uint8_t output[COMP_V11_BLE_HCI_EVENT_MAX_BYTES];
    uint8_t maximum[COMP_V11_BLE_HCI_EVENT_MAX_BYTES];
    uint16_t total=0u;

    CHECK(comp_v11_ble_event_plan(contiguous,(uint16_t)sizeof(contiguous),
                                  NULL,0u,&total)==
              COMP_V11_BLE_EVENT_COPY_OK && total==sizeof(contiguous),
          "contiguous event validates");
    CHECK(comp_v11_ble_event_flatten(contiguous,(uint16_t)sizeof(contiguous),
                                     NULL,0u,output,sizeof(output),&total)==
              COMP_V11_BLE_EVENT_COPY_OK && total==sizeof(contiguous) &&
          memcmp(output,contiguous,sizeof(contiguous))==0,
          "contiguous event remains byte exact");

    CHECK(comp_v11_ble_event_plan(primary,(uint16_t)sizeof(primary),extension,
                                  (uint16_t)sizeof(extension),&total)==
              COMP_V11_BLE_EVENT_COPY_OK && total==9u,
          "payload split validates against plen");
    CHECK(comp_v11_ble_event_flatten(primary,(uint16_t)sizeof(primary),
                                     extension,(uint16_t)sizeof(extension),
                                     output,sizeof(output),&total)==
              COMP_V11_BLE_EVENT_COPY_OK && total==9u &&
          memcmp(output,primary,sizeof(primary))==0 &&
          memcmp(&output[sizeof(primary)],extension,sizeof(extension))==0,
          "split payload is reassembled in order");

    memset(maximum,0,sizeof(maximum));
    maximum[0]=COMP_V11_BLE_HCI_EVENT_PACKET_TYPE;
    maximum[1]=0xFFu; maximum[2]=255u;
    for(uint32_t i=3u;i<sizeof(maximum);++i)maximum[i]=(uint8_t)i;
    CHECK(comp_v11_ble_event_flatten(maximum,200u,&maximum[200],58u,
                                     output,sizeof(output),&total)==
              COMP_V11_BLE_EVENT_COPY_OK && total==sizeof(maximum) &&
          memcmp(output,maximum,sizeof(maximum))==0,
          "maximum standard HCI event supports an ext segment");

    CHECK(comp_v11_ble_event_plan(NULL,3u,NULL,0u,&total)==
              COMP_V11_BLE_EVENT_COPY_BAD_ARGUMENT,
          "null primary rejected");
    CHECK(comp_v11_ble_event_plan(contiguous,2u,NULL,0u,&total)==
              COMP_V11_BLE_EVENT_COPY_BAD_LENGTH,
          "short standard header rejected");
    CHECK(comp_v11_ble_event_plan(primary,(uint16_t)sizeof(primary),NULL,4u,
                                  &total)==
              COMP_V11_BLE_EVENT_COPY_BAD_ARGUMENT,
          "missing extension pointer rejected");
    uint8_t bad_type[]={0x02u,0u,0u};
    CHECK(comp_v11_ble_event_plan(bad_type,sizeof(bad_type),NULL,0u,&total)==
              COMP_V11_BLE_EVENT_COPY_BAD_TYPE,
          "non-event packet rejected by event helper");
    uint8_t too_short[]={0x04u,0xFFu,5u,1u,2u};
    CHECK(comp_v11_ble_event_plan(too_short,sizeof(too_short),NULL,0u,&total)==
              COMP_V11_BLE_EVENT_COPY_BAD_LENGTH,
          "truncated plen rejected");
    uint8_t too_long[]={0x04u,0xFFu,1u,1u,2u};
    CHECK(comp_v11_ble_event_plan(too_long,sizeof(too_long),NULL,0u,&total)==
              COMP_V11_BLE_EVENT_COPY_BAD_LENGTH,
          "bytes beyond plen rejected");
    CHECK(comp_v11_ble_event_plan(contiguous,UINT16_MAX,extension,1u,&total)==
              COMP_V11_BLE_EVENT_COPY_BAD_LENGTH,
          "length addition overflow rejected before copying");
    CHECK(comp_v11_ble_event_flatten(contiguous,sizeof(contiguous),NULL,0u,
                                     output,6u,&total)==
              COMP_V11_BLE_EVENT_COPY_OUTPUT_TOO_SMALL && total==0u,
          "short destination rejected without reported output");
    CHECK(comp_v11_ble_event_flatten(contiguous,sizeof(contiguous),NULL,0u,
                                     NULL,sizeof(output),&total)==
              COMP_V11_BLE_EVENT_COPY_BAD_ARGUMENT && total==0u,
          "null destination rejected");

    printf("PASS_WBA_BLE_EVENT_COPY_HOST_ONLY max=%u\n",
           COMP_V11_BLE_HCI_EVENT_MAX_BYTES);
    return 0;
}
