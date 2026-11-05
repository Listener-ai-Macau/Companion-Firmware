#include <assert.h>
#include <stdio.h>
#include <stdint.h>
#ifdef _MSC_VER
#include <stdlib.h>
#endif
#include "../../platform/stm32wba55_companion_v11/ble/ble_directional_budget_recovery.h"
int main(void) {
#ifdef _MSC_VER
 _set_error_mode(_OUT_TO_STDERR); _set_abort_behavior(0,_WRITE_ABORT_MSG|_CALL_REPORTFAULT);
#endif
 uint8_t s=0;uint32_t after=0;
 assert(!comp_ble_budget_recovery_observe(&s,true,true,0,0,340,340,100,&after));
 assert(!comp_ble_budget_recovery_observe(&s,true,true,340,340,965,965,100,&after));
 assert(!comp_ble_budget_recovery_observe(&s,true,false,340,340,340,965,100,&after));
 assert(!comp_ble_budget_recovery_observe(&s,false,true,340,340,340,965,100,&after));
 assert(comp_ble_budget_recovery_observe(&s,true,true,340,340,340,965,100,&after)&&s==1&&after==300);
 assert(!comp_ble_budget_recovery_take(&s,true,true,true,true,340,965,299,after));
 assert(!comp_ble_budget_recovery_take(&s,false,true,true,true,340,965,300,after));
 assert(!comp_ble_budget_recovery_take(&s,true,false,true,true,340,965,300,after));
 assert(!comp_ble_budget_recovery_take(&s,true,true,false,true,340,965,300,after));
 assert(comp_ble_budget_recovery_take(&s,true,true,true,true,340,965,300,after)&&s==2);
 assert(!comp_ble_budget_recovery_take(&s,true,true,true,true,340,965,301,after));
 assert(!comp_ble_budget_recovery_observe(&s,true,true,340,340,340,965,500,&after));
 s=0;assert(comp_ble_budget_recovery_observe(&s,true,true,340,340,340,965,UINT32_MAX-100,&after));
 assert(after==99 && !comp_ble_budget_recovery_take(&s,true,true,true,true,340,965,98,after));
 assert(comp_ble_budget_recovery_take(&s,true,true,true,true,340,965,99,after));
 s=0;assert(comp_ble_budget_recovery_observe(&s,true,true,340,340,340,965,100,&after));
 assert(!comp_ble_budget_recovery_observe(&s,true,true,340,965,965,965,110,&after)&&s==0);
 /* Captured574 regression: a previously valid negotiated link is cut to
  * symmetric340. ActualCI6/active-bulk admission is supplied by app_ble;
  * a finite CI timeout alone must never pass that gate. */
 s=0;assert(!comp_ble_budget_recovery_observe(&s,false,true,1590,1590,340,340,100,&after)&&s==0);
 assert(!comp_ble_budget_recovery_observe(&s,true,false,1590,1590,340,340,100,&after)&&s==0);
 assert(comp_ble_budget_recovery_observe(&s,true,true,1590,1590,340,340,100,&after)&&s==3&&after==300);
 assert(!comp_ble_budget_recovery_observe(&s,true,true,340,340,340,340,110,&after)&&s==3&&after==300);
 assert(!comp_ble_budget_recovery_take(&s,true,true,false,true,340,340,500,after)&&s==3);
 /* Production CI6 event rearms the settling deadline. */
 after=700;
 assert(!comp_ble_budget_recovery_take(&s,true,true,true,true,340,340,699,after));
 assert(!comp_ble_budget_recovery_take(&s,true,false,true,true,340,340,700,after));
 assert(!comp_ble_budget_recovery_take(&s,false,true,true,true,340,340,700,after));
 assert(comp_ble_budget_recovery_take(&s,true,true,true,true,340,340,700,after)&&s==2);
 assert(!comp_ble_budget_recovery_observe(&s,true,true,1590,1590,340,340,800,&after)&&s==2);
 assert(!comp_ble_budget_recovery_take(&s,true,true,true,true,340,340,900,after));
 s=0;assert(comp_ble_budget_recovery_observe(&s,true,true,965,965,340,340,UINT32_MAX-100,&after));
 assert(after==99 && !comp_ble_budget_recovery_take(&s,true,true,true,true,340,340,98,after));
 assert(comp_ble_budget_recovery_take(&s,true,true,true,true,340,340,99,after));
 s=0;assert(comp_ble_budget_recovery_observe(&s,true,true,1590,1590,340,340,100,&after));
 assert(!comp_ble_budget_recovery_observe(&s,true,true,340,340,1590,1590,110,&after)&&s==0);
 puts("PASS_DIRECTIONAL_RECOVERY no_initial_or_bulk_retry one_actual_transition one_foreground_attempt wrap_safe cancellation");
 return 0;
}
