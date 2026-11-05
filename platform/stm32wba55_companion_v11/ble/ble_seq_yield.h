#ifndef COMP_V11_BLE_SEQ_YIELD_H
#define COMP_V11_BLE_SEQ_YIELD_H
#include <stdbool.h>
#include "stm32_seq.h"
/* Called only after the existing outer-turn deadline. A stopped-file owner
 * may finish ONE already-ready LL task before yielding to product work.
 * Its self-reschedule is paused after that one turn. Live capture/NVM/OTA
 * use the original all-task pause. No task callback is invoked directly. */
static inline void comp_v11_ble_seq_yield(bool *yielded,bool permit_ll_tail,
    uint32_t current_task,uint32_t ll_task)
{
    if(permit_ll_tail && !*yielded && current_task!=ll_task &&
       UTIL_SEQ_IsSchedulableTask(ll_task))
        UTIL_SEQ_PauseTask(UTIL_SEQ_DEFAULT & ~ll_task);
    else UTIL_SEQ_PauseTask(UTIL_SEQ_DEFAULT);
    *yielded=true;
}
#endif
