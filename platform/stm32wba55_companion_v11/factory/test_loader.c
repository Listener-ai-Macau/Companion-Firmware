#include "loader.h"
#include <stdio.h>
#include <string.h>
static unsigned calls, erases;
static uint32_t last_offset, last_size;
static bool hw_ok = true;
bool factory_hw_init(void) { return hw_ok; }
bool factory_hw_read(uint32_t offset, uint8_t *data, uint32_t size)
{ ++calls; last_offset = offset; last_size = size; data[0] = 0x5a; return hw_ok; }
bool factory_hw_write(uint32_t offset, const uint8_t *data, uint32_t size)
{ (void)data; ++calls; last_offset = offset; last_size = size; return hw_ok; }
bool factory_hw_erase(uint32_t offset) { ++erases; last_offset = offset; return hw_ok; }
#define CHECK(x) do { if (!(x)) { printf("FAIL line %d: %s\n", __LINE__, #x); return 1; } } while (0)
int main(void)
{
    uint8_t b[8] = {0};
    CHECK(!Read(COMP_FACTORY_BASE, 1, b));
    CHECK(!Write(COMP_FACTORY_BASE, 1, b));
    CHECK(Init());
    CHECK(Read(COMP_FACTORY_BASE + COMP_FACTORY_NOR_BYTES - 1, 1, b));
    CHECK(last_offset == COMP_FACTORY_NOR_BYTES - 1 && last_size == 1 && b[0] == 0x5a);
    unsigned before = calls;
    CHECK(!Read(COMP_FACTORY_BASE - 1, 1, b));
    CHECK(!Read(COMP_FACTORY_BASE + COMP_FACTORY_NOR_BYTES - 1, 2, b));
    CHECK(!Read(COMP_FACTORY_BASE, UINT32_MAX, b));
    CHECK(!Read(COMP_FACTORY_BASE, 1, NULL));
    CHECK(calls == before);
    CHECK(Write(COMP_FACTORY_BASE + COMP_FACTORY_UI_BYTES - 1, 1, b));
    before = calls;
    CHECK(!Write(COMP_FACTORY_BASE + COMP_FACTORY_UI_BYTES - 1, 2, b));
    CHECK(!Write(COMP_FACTORY_BASE + COMP_FACTORY_UI_BYTES, 1, b));
    CHECK(!Write(COMP_FACTORY_BASE, UINT32_MAX, b));
    CHECK(!Write(COMP_FACTORY_BASE, 0, b));
    CHECK(calls == before);
    CHECK(SectorErase(COMP_FACTORY_BASE + 2, COMP_FACTORY_BASE + 4096));
    CHECK(erases == 2 && last_offset == 4096);
    CHECK(!SectorErase(COMP_FACTORY_BASE, COMP_FACTORY_BASE + COMP_FACTORY_UI_BYTES));
    CHECK(!SectorErase(COMP_FACTORY_BASE, UINT32_MAX));
    CHECK(!SectorErase(COMP_FACTORY_BASE + 1, COMP_FACTORY_BASE));
    CHECK(!MassErase() && erases == 2);
    hw_ok = false;
    CHECK(!Write(COMP_FACTORY_BASE, 1, b));
    CHECK(!Read(COMP_FACTORY_BASE, 1, b));
    CHECK(!SectorErase(COMP_FACTORY_BASE, COMP_FACTORY_BASE + 8191));
    CHECK(erases == 3); /* first failed sector stops the transaction */
    CHECK(!Init()); before = calls;
    hw_ok = true;
    CHECK(!Read(COMP_FACTORY_BASE, 1, b) && calls == before);
    CHECK(Init()); CHECK(Read(COMP_FACTORY_BASE, 1, b));
    puts("PASS_HOST_FACTORY_LOADER: guarded ranges, inclusive sectors, failures, init lifecycle");
    return 0;
}
