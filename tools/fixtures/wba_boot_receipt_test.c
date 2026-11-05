#include "boot_receipt.h"
#include <assert.h>
#include <stdio.h>

int main(void)
{
    volatile uint32_t words[3]={0u};
    const uint32_t reset=0x08008101u;
    assert(comp_v11_boot_receipt_read(words,reset)==0u);
    for(uint32_t route=1u;route<=3u;++route) {
        comp_v11_boot_receipt_publish(words,route,reset);
        assert(comp_v11_boot_receipt_read(words,reset)==route);
        assert(comp_v11_boot_receipt_read(words,reset+2u)==0u);
        words[0]=0u; /* power cut before publication */
        assert(comp_v11_boot_receipt_read(words,reset)==0u);
        comp_v11_boot_receipt_publish(words,route,reset);
        words[2]^=1u;
        assert(comp_v11_boot_receipt_read(words,reset)==0u);
    }
    comp_v11_boot_receipt_publish(words,4u,reset);
    assert(comp_v11_boot_receipt_read(words,reset)==0u);
    puts("BOOT_RECEIPT_TORN_CORRUPT_VECTOR_MISMATCH_REJECTED_HOST_ONLY");
    return 0;
}
