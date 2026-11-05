#ifndef COMPANION_WBA25_MEMORY_GEOMETRY_H
#define COMPANION_WBA25_MEMORY_GEOMETRY_H

#include <stdbool.h>
#include <stdint.h>

/* STM32WBA25xx physical SRAM: 64 KiB SRAM1 then 32 KiB SRAM2. The
 * application must still configure its security/retention and linker regions;
 * this range check does not establish either. Descending MSP may equal the
 * exclusive upper boundary. Do not use the WBA55CE 32+64 KiB bank sizes. */
#define COMP_WBA25_SRAM1_BYTES UINT32_C(0x10000)
#define COMP_WBA25_SRAM2_BYTES UINT32_C(0x08000)
#define COMP_WBA25_SRAM_NS_BASE UINT32_C(0x20000000)
#define COMP_WBA25_SRAM_S_BASE UINT32_C(0x30000000)

static inline bool comp_wba25_stack_pointer_valid(uint32_t sp, bool secure_alias)
{
    const uint32_t base = secure_alias ? COMP_WBA25_SRAM_S_BASE : COMP_WBA25_SRAM_NS_BASE;
    return (sp & 7u) == 0u && sp > base &&
        sp <= base + COMP_WBA25_SRAM1_BYTES + COMP_WBA25_SRAM2_BYTES;
}

#endif
