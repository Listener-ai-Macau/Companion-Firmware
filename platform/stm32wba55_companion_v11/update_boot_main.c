#include "update_boot_target.h"
#include "wba_update_trust_anchor.h"

#ifndef COMPANION_WBA_APP_VERSION
#define COMPANION_WBA_APP_VERSION UINT32_C(0)
#endif
#ifndef COMPANION_WBA_INSTALLED_IMAGE_SIZE
#define COMPANION_WBA_INSTALLED_IMAGE_SIZE UINT32_C(0)
#endif

void SysTick_Handler(void){HAL_IncTick();}

int main(void)
{
    const comp_v11_update_boot_target_config_t config={
        comp_wba_update_public_key,COMP_WBA_UPDATE_KEY_ID,
        COMPANION_WBA_APP_VERSION,COMPANION_WBA_INSTALLED_IMAGE_SIZE};
    (void)comp_v11_update_boot_target_run(&config);
    /* If initialization or recovery fails, do not jump around fail-closed state.
     * IWDG resets us when it was already started; otherwise an operator/debugger
     * can inspect the fault without an unauthenticated application launch. */
    __disable_irq();for(;;)__WFI();
}
