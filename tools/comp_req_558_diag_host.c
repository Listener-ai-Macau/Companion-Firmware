#include "companion_platform_adapters.h"
#include "denzic_diag_log_gatt_v1.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

typedef struct { uint16_t count; uint32_t mode; uint32_t reads; uint32_t stops; } diag_fixture_t;
static uint32_t crc32(const uint8_t *p,size_t n){uint32_t c=0xffffffffu;for(size_t i=0;i<n;i++){c^=p[i];for(unsigned b=0;b<8;b++)c=(c>>1)^(0xedb88320u&(uint32_t)-(int)(c&1u));}return ~c;}
static bool count(void *p,uint16_t *n){*n=((diag_fixture_t*)p)->count;return true;}
static bool start(void *p){(void)p;return true;}
static bool read_chunk(void *p,uint32_t expected,uint8_t *out,size_t cap,size_t *len){diag_fixture_t*f=p;uint16_t n=expected<f->count?1u:0u;uint32_t offset=expected;if(f->mode==1u&&expected==1u)offset=0u;if(f->mode==3u&&expected==1u)n=0u;if(f->mode==4u&&expected==1u)offset=99u;size_t bytes=DENZIC_OBSERVABILITY_V1_DIAG_LOG_CHUNK_HEADER_BYTES+(size_t)n*DENZIC_OBSERVABILITY_V1_DIAG_LOG_EVENT_WIRE_BYTES;if(bytes>cap)return false;uint8_t events[DENZIC_OBSERVABILITY_V1_DIAG_LOG_EVENT_WIRE_BYTES]={0};uint32_t wire_crc=crc32(events,(size_t)n*DENZIC_OBSERVABILITY_V1_DIAG_LOG_EVENT_WIRE_BYTES);if(f->mode==2u&&expected==1u)wire_crc^=1u;denzic_diag_log_gatt_v1_encode_chunk_header(out,n,offset,wire_crc);if(n)memcpy(out+DENZIC_OBSERVABILITY_V1_DIAG_LOG_CHUNK_HEADER_BYTES,events,sizeof(events));*len=bytes;f->reads++;return true;}
static bool stop(void *p){((diag_fixture_t*)p)->stops++;return true;}
int main(void){setvbuf(stdout,NULL,_IONBF,0);for(uint32_t mode=0;mode<6u;mode++){diag_fixture_t f={(uint16_t)(mode==5u?COMPANION_PLATFORM_DIAG_EVENT_CAPACITY+1u:2u),mode,0u,0u};companion_diag_transport_t t={&f,count,start,read_chunk,stop};companion_diag_result_t r;bool ok=companion_diag_log_pull(&t,&r);printf("diag mode=%u ok=%u reads=%u stop=%u observed=%u retained=%u dropped=%u crc=%u offset=%u overflow=%u\n",(unsigned)mode,ok?1u:0u,(unsigned)r.reads,(unsigned)r.stop_calls,(unsigned)r.observed_events,(unsigned)r.retained_events,(unsigned)r.dropped_events,(unsigned)r.crc_failures,(unsigned)r.offset_failures,r.overflow?1u:0u);assert(f.stops==1u);if(mode==0u)assert(ok);else assert(!ok);}printf("COMP-REQ-558 diagnostics PASS fixed_capacity=%u count/start/read/stop=1 crc=1 offset=1 overflow=1\n",COMPANION_PLATFORM_DIAG_EVENT_CAPACITY);return 0;}
