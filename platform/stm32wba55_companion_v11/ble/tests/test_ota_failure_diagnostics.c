/* Reuse the production GATT+DOV1+CE arena fixture. UART and radio/NOR are
 * shims; the report body and its caller are production code, not a model. */
#define main prior_durable_contract_main
#include "test_ota_durable_notifications.c"
#undef main
#include "failure_diagnostic_ports.h"
static char output[16384];static size_t output_bytes;static unsigned output_calls;
static bool in_security_callback;
bool comp_v11_hal_debug_write(const char *message)
{
 assert(!in_security_callback);
 size_t n=strlen(message);assert(n<sizeof(output)-output_bytes);
 memcpy(output+output_bytes,message,n+1u);output_bytes+=n;++output_calls;return true;
}
uint32_t comp_v11_ble_observe_us(void){return now*1000u;}
void comp_v11_ble_link_budget(uint8_t out[20]){memset(out,0,20);memcpy(out,"BLK1",4);}
void comp_v11_ble_rx_shape_trace(uint8_t stage,...){(void)stage;}
static const comp_v11_update_diagnostics_t io={0};
static const comp_v11_update_program_diagnostics_t program={0};
const comp_v11_update_diagnostics_t *comp_v11_update_product_diagnostics(void){return &io;}
const comp_v11_update_program_diagnostics_t *comp_v11_update_program_diagnostics(void){return &program;}
int main(void)
{
 denzic_ota_v1_storage_driver_t storage={begin,write_data,finish,abort_write};
 denzic_ota_v1_init(&transfer,storage,NULL,505,64);
 comp_v11_ota_gatt_ports_t ports={control,data,status,NULL,claim,release,clock_ms,NULL};
 assert(comp_v11_ota_gatt_init(&ports));comp_v11_ota_gatt_connection(true);
 start(215,430);now=1020;value(0,215,1);
 unsigned calls=output_calls;in_security_callback=true;
 now=1023;comp_v11_ota_gatt_connection(false);in_security_callback=false;
 assert(output_calls==calls&&!borrowed&&storage_calls==0);
 const comp_v11_ota_phase_timing_t *t=comp_v11_ota_gatt_phase_timing();
 assert(t->started&&!t->running&&t->invalid==2u&&t->span_us==3000);
 /* A new authenticated BEGIN can already be queued before foreground gets
  * another turn. Its reset must not silently erase the failed ledger. */
 comp_v11_ota_gatt_connection(true);
 uint8_t b[20]={'D','O','V','1',DENZIC_OTA_V1_OP_BEGIN,1};
 put32(b+8,430);b[12]=215;b[14]=64;packet(0,b,20,0);
 comp_v11_ota_gatt_poll();
 if(output_calls==calls || !strstr(output,"OTA2 rx=1 processed=0") ||
    !strstr(output,"span_us=3000") || !strstr(output,"invalid=2")) {
  puts("FAIL_OLD_LINK_LOSS_LEDGER_WAS_OVERWRITTEN_WITHOUT_REPORT");return 71;
 }
 calls=output_calls;assert(!t->started&&transfer.bytes_written==0);
 comp_v11_ota_gatt_poll();comp_v11_ota_gatt_poll();assert(output_calls==calls);
 /* The successor's normal durable completion is still reported once. */
 value(0,215,2);comp_v11_ota_gatt_poll();value(215,215,3);comp_v11_ota_gatt_poll();
 assert(t->started&&!t->running&&!t->invalid&&transfer.bytes_written==430&&!borrowed);
 b[4]=DENZIC_OTA_V1_OP_FINISH;packet(0,b,20,0);comp_v11_ota_gatt_poll();
 assert(output_calls>calls);calls=output_calls;
 comp_v11_ota_gatt_connection(false);comp_v11_ota_gatt_poll();assert(output_calls==calls);
 puts("PASS lost-link ledger emitted once in foreground before successor BEGIN; zero callback UART/old DATA writes, distinct successor success, no duplicate reports. Hardware/rate NOT_RUN.");return 0;
}
