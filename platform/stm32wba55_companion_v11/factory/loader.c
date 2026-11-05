#include "loader.h"
#include <stddef.h>

static bool initialized;
bool factory_mutation_allowed(uint32_t offset,uint32_t bytes)
{
    return bytes && offset<COMP_FACTORY_WRITE_BYTES && bytes<=COMP_FACTORY_WRITE_BYTES-offset &&
        (offset+bytes<=COMP_FACTORY_BOND_A || offset>=COMP_FACTORY_BOND_END);
}
static bool range(uint32_t address, uint32_t size, uint32_t limit)
{
    return address >= COMP_FACTORY_BASE && size != 0u &&
        address - COMP_FACTORY_BASE < limit && size <= limit - (address - COMP_FACTORY_BASE);
}
int Init(void)
{
    initialized = false;
    initialized = factory_hw_init();
    return initialized ? 1 : 0;
}
int Read(uint32_t address, uint32_t size, uint8_t *buffer)
{
    return initialized && buffer != NULL && range(address, size, COMP_FACTORY_NOR_BYTES) &&
        factory_hw_read(address - COMP_FACTORY_BASE, buffer, size) ? 1 : 0;
}
int Write(uint32_t address, uint32_t size, uint8_t *buffer)
{
    /* The separate developer formatter can initialize the entire NOR. */
    return initialized && buffer != NULL && range(address, size, COMP_FACTORY_WRITE_BYTES) &&
        factory_mutation_allowed(address-COMP_FACTORY_BASE,size) &&
        factory_hw_write(address - COMP_FACTORY_BASE, buffer, size) ? 1 : 0;
}
int SectorErase(uint32_t start, uint32_t end)
{
    /* ST passes inclusive endpoints. Validate the entire range BEFORE any erase. */
    if (!initialized || end < start || end - start == UINT32_MAX ||
        !range(start, end - start + 1u, COMP_FACTORY_WRITE_BYTES)) return 0;
    uint32_t offset = (start - COMP_FACTORY_BASE) & ~UINT32_C(4095);
    uint32_t last = (end - COMP_FACTORY_BASE) & ~UINT32_C(4095);
    if(!factory_mutation_allowed(offset,last-offset+4096u))return 0;
    for (;;) {
        if (!factory_hw_erase(offset)) return 0;
        if (offset == last) return 1;
        offset += 4096u;
    }
}
int MassErase(void) { return 0; }

/* UM2237 StorageInfo ABI: exactly 200 bytes with ten sector descriptors. */
typedef struct {
    char name[100]; uint16_t type; uint32_t start, size, page; uint8_t erased;
    struct { uint32_t count, size; } sectors[10];
} storage_info_t;
_Static_assert(sizeof(storage_info_t) == 200, "CubeProgrammer StorageInfo ABI");
#if defined(__GNUC__)
__attribute__((used, section(".Dev_info")))
#endif
const storage_info_t StorageInfo = {
#if defined(COMP_FACTORY_DEVELOPMENT_FORMAT) && COMP_FACTORY_DEVELOPMENT_FORMAT
    "Companion_V11_WBA55_SPI3_DEV_FORMAT_v3", 7, COMP_FACTORY_BASE,
#else
    "Companion_V11_WBA55_SPI3_UI_ONLY_v1", 7, COMP_FACTORY_BASE,
#endif
    COMP_FACTORY_NOR_BYTES, 256, 0xff, {{4096, 4096}}
};
