#include "diagnostic_console.h"
#include <assert.h>
#include <stdio.h>
int main(void)
{
    assert(comp_v11_diag_periodic_allowed(0u,0u));
    assert(comp_v11_diag_periodic_allowed(100u,0u));
    assert(!comp_v11_diag_periodic_allowed(100u,500u));
    assert(!comp_v11_diag_periodic_allowed(499u,500u));
    assert(comp_v11_diag_periodic_allowed(500u,500u));
    assert(comp_v11_diag_periodic_allowed(501u,500u));
    assert(!comp_v11_diag_periodic_allowed(UINT32_MAX-20u,9u));
    assert(!comp_v11_diag_periodic_allowed(8u,9u));
    assert(comp_v11_diag_periodic_allowed(10u,9u));
    assert(comp_v11_diag_periodic_allowed(20u,UINT32_MAX-20u));
    /* Explicit query parsing/safety is unchanged; main applies this predicate
     * only to the implicit periodic branch. No old framing suite is rerun. */
    puts("PASS: finite trace defers periodic bulk logs, restores at expiry and handles tick wrap. Software timing policy only; query branch unchanged by inspection.");
    return 0;
}
