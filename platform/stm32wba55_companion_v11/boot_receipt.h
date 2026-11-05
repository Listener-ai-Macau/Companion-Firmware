#ifndef COMP_V11_BOOT_RECEIPT_H
#define COMP_V11_BOOT_RECEIPT_H
#include <stdint.h>

/* Diagnostic handoff only, never an authentication or jump permission.
 * BKP16..18 are reserved for this receipt. ST timer owns 0..2 and the
 * product clock owns 4..15. Boot invalidates before work and publishes last.
 * Bind to the installed reset vector; App captures before RTC initialization
 * can reset the backup domain. No NOR journal or persistent App RAM buffer. */
#define COMP_V11_BOOT_RECEIPT_MAGIC UINT32_C(0x31525442) /* BTR1 */
enum {
    COMP_V11_BOOT_ROUTE_UNKNOWN=0,
    COMP_V11_BOOT_ROUTE_CURRENT=1,
    COMP_V11_BOOT_ROUTE_INSTALLED=2,
    /* Exact observed scope: both entry words were erased on this Boot entry,
     * then the retained package passed the ordinary full install checks.
     * This does not classify all possible interrupted installation points. */
    COMP_V11_BOOT_ROUTE_REINSTALLED_ERASED_ENTRY=3,
};
static inline uint32_t comp_v11_boot_receipt_check(uint32_t route,uint32_t reset_vector)
{return ~(COMP_V11_BOOT_RECEIPT_MAGIC^route^reset_vector);}
static inline void comp_v11_boot_receipt_publish(volatile uint32_t *words,
                                               uint32_t route,uint32_t reset_vector)
{
    words[0]=0u;
    words[1]=route;words[2]=comp_v11_boot_receipt_check(route,reset_vector);
    words[0]=COMP_V11_BOOT_RECEIPT_MAGIC;
}
static inline uint8_t comp_v11_boot_receipt_read(const volatile uint32_t *words,
                                               uint32_t reset_vector)
{
    uint32_t magic=words[0],route=words[1],check=words[2];
    return magic==COMP_V11_BOOT_RECEIPT_MAGIC &&
        route>=COMP_V11_BOOT_ROUTE_CURRENT && route<=COMP_V11_BOOT_ROUTE_REINSTALLED_ERASED_ENTRY &&
        check==comp_v11_boot_receipt_check(route,reset_vector)?(uint8_t)route:0u;
}
#endif
