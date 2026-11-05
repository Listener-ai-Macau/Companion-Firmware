#include "power_target_stm32wba.h"

#include <stdio.h>

int main(void)
{
    if (!comp_power_stm32wba_self_test()) {
        fputs("FAIL: WBA power target transition retry contract\n", stderr);
        return 1;
    }
    puts("PASS_HOST_ONLY: WBA power target retries failed transitions and "
         "keeps fail-closed state truthful");
    return 0;
}
