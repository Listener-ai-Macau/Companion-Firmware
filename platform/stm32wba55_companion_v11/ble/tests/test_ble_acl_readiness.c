#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "../ble_acl_readiness_profile.h"
static uint8_t data[251];
static void packet(uint32_t offset){
 memset(data,0,sizeof(data));data[0]=0xf2;data[1]=1;data[2]=4;data[4]=0x1b;data[7]=1;data[8]=8;
 data[9]=0xdb;data[10]=1;data[13]=2;
 for(unsigned i=0;i<4;++i)data[19+i]=(uint8_t)(offset>>(8*i));
}
static void start(comp_acl_ready_t *v,uint32_t offset,uint32_t epoch,bool idle){
 packet(offset);comp_acl_ready_begin(v,1,1,131072,data,251,1,epoch,idle);
 comp_acl_ready_end(v,true,epoch,idle);
}
static void tail(comp_acl_ready_t *v,uint32_t epoch,bool idle,bool success){
 comp_acl_ready_begin(v,1,1,131072,data,251,0,epoch,idle);
 comp_acl_ready_end(v,success,epoch,idle);
}
int main(void){
 /* Match the real official allocator: memset(header,0,16), raw packet
  * allocation, then offset4/size251/flags1. total_len remains zero. */
 assert(comp_acl_ready_slice_valid(data,4,251,0));
 assert(comp_acl_ready_slice_valid(data,4,251,255));
 assert(!comp_acl_ready_slice_valid(data,4,251,254));
 assert(!comp_acl_ready_slice_valid(data,4,252,0));
 assert(!comp_acl_ready_slice_valid(data,0,251,0));
 assert(!comp_acl_ready_slice_valid(NULL,4,251,0));
 comp_acl_ready_t v={0};start(&v,524400,7,true);tail(&v,7,true,true);
 if(!(v.count==1 && v.flags[0]==3 && v.parts[0]==2)){printf("PUBLIC_TYPED_ACL_CONTRACT_REJECTED rows=%u parts=%u flags=%u\n",v.count,v.parts[0],v.flags[0]);return 3;}
 v=(comp_acl_ready_t){0};start(&v,524400,7,true);tail(&v,8,true,true);assert(v.flags[0]==1);
 v=(comp_acl_ready_t){0};start(&v,524400,7,false);tail(&v,7,false,true);assert(v.flags[0]==1);
 v=(comp_acl_ready_t){0};start(&v,524400,7,true);tail(&v,7,true,false);assert(v.flags[0]==4 && !v.tracking);
 v=(comp_acl_ready_t){0};start(&v,100,7,true);tail(&v,7,true,true);assert(!v.count);
 v=(comp_acl_ready_t){0};packet(524400);comp_acl_ready_begin(&v,1,1,131072,data,251,1,7,true);
 comp_acl_ready_end(&v,true,8,true);tail(&v,8,true,true);assert(v.flags[0]==1);
 v=(comp_acl_ready_t){0};start(&v,524400,7,true);
 comp_acl_ready_begin(&v,2,1,131072,data,251,0,7,true);comp_acl_ready_end(&v,true,7,true);
 assert(v.remaining==251 && !v.pending);tail(&v,7,true,true);assert(v.flags[0]==3);
 v=(comp_acl_ready_t){0};start(&v,524400,7,true);start(&v,524875,7,true);tail(&v,7,true,true);
 assert(v.flags[0]&ACL_READY_INTERRUPTED);assert(v.flags[1]==3);
 v=(comp_acl_ready_t){0};for(unsigned n=0;n<20;++n){start(&v,524400+475*n,7,true);tail(&v,7,true,true);}
 assert(v.count==16 && !v.tracking && v.errors==0);
 v=(comp_acl_ready_t){0};packet(524400);comp_acl_ready_begin(&v,1,1,131072,NULL,251,1,7,true);assert(!v.count);
 comp_acl_ready_begin(&v,1,1,131072,data,20,1,7,true);assert(!v.count);
 data[0]=0;comp_acl_ready_begin(&v,1,1,131072,data,251,1,7,true);assert(!v.count);
 v=(comp_acl_ready_t){0};packet(524400);
 comp_acl_ready_begin(&v,1,1,131072,data,251,17,7,true);
 assert(!v.count && v.errors==1); /* A different flag contract is never accepted. */
 v=(comp_acl_ready_t){0};comp_acl_ready_begin(&v,1,1,131072,NULL,251,1,7,true);
 assert(!v.count && v.starts==1 && v.unbounded==1);
 /* 199-byte single-LL values use parts as epoch delta only in schema4. */
 v=(comp_acl_ready_t){0};packet(524400);data[0]=222u;data[1]=0u;data[9]=199u;data[10]=0u;
 comp_acl_ready_begin(&v,1,1,131072,data,226u,1,100u,true);comp_acl_ready_end(&v,true,100u,true);
 assert(v.count==1 && v.flags[0]==(ACL_READY_SINGLE_EPOCH|ACL_READY_COMPLETE|ACL_READY_SAME_IDLE_EPOCH) && v.parts[0]==0);
 packet(524599);data[0]=222u;data[1]=0u;data[9]=199u;data[10]=0u;
 comp_acl_ready_begin(&v,1,1,131072,data,226u,1,102u,true);comp_acl_ready_end(&v,true,102u,true);
 assert(v.count==2 && v.parts[1]==2 && v.flags[1]==(ACL_READY_SINGLE_EPOCH|ACL_READY_COMPLETE|ACL_READY_SAME_IDLE_EPOCH));
 packet(524798);data[0]=222u;data[1]=0u;data[9]=199u;data[10]=0u;
 comp_acl_ready_begin(&v,1,1,131072,data,226u,1,102u,true);comp_acl_ready_end(&v,true,103u,false);
 assert(v.count==3 && v.parts[2]==2 && v.flags[2]==(ACL_READY_SINGLE_EPOCH|ACL_READY_COMPLETE));
 packet(524997);data[0]=222u;data[1]=0u;data[9]=199u;data[10]=0u;
 comp_acl_ready_begin(&v,1,1,131072,data,226u,1,400u,true);comp_acl_ready_end(&v,true,400u,true);
 assert(v.count==4 && v.parts[3]==255u && (v.flags[3]&ACL_READY_EPOCH_OVERFLOW));
 /* Geometry transitions never compare a split row with the single baseline. */
 start(&v,525196,400u,true);tail(&v,400u,true,true);assert(v.count==4);
 v=(comp_acl_ready_t){0};packet(524400);data[0]=222u;data[1]=0u;data[9]=199u;data[10]=0u;
 comp_acl_ready_begin(&v,1,1,131072,data,226u,1,0xffffffffu,true);comp_acl_ready_end(&v,true,0xffffffffu,true);
 comp_acl_ready_begin(&v,1,1,131072,data,226u,1,0u,true);comp_acl_ready_end(&v,true,0u,true);
 assert(v.parts[0]==0u && v.parts[1]==1u && !(v.flags[1]&ACL_READY_EPOCH_OVERFLOW));
 v=(comp_acl_ready_t){0};packet(524400);data[0]=222u;data[1]=0u;data[9]=199u;data[10]=0u;
 comp_acl_ready_begin(&v,1,1,131072,data,226u,1,7u,true);comp_acl_ready_end(&v,false,7u,true);
 assert(v.flags[0]==(ACL_READY_SINGLE_EPOCH|ACL_READY_REJECTED));
 puts("PASS_PUBLIC_ACL_SAME_IDLE_EPOCH_RADIO_RACE_REJECT_OTHER_HANDLE_INTERRUPTION_BOUNDS_FIXED_SAMPLE");
}
