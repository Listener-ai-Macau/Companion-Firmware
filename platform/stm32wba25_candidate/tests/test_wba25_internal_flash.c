/* Host execution of the real adapter with a fake HAL and mapped NOR bytes.
 * It does not claim WBA25 hardware, ECC or power-loss qualification. */
#include <windows.h>
#include <stdio.h>
#include <string.h>
#include "stm32wbaxx_hal.h"
#include "wba25_internal_flash.h"
#include "wba25_memory_geometry.h"

#define CHECK(x) do { if (!(x)) { fprintf(stderr, "failed line %d: %s\n", __LINE__, #x); return 1; } } while (0)
static unsigned unlocks, locks, writes, erases;
static int fail_unlock, fail_lock, fail_program, fail_erase, corrupt_write;
HAL_StatusTypeDef HAL_FLASH_Unlock(void) { ++unlocks; return fail_unlock ? HAL_ERROR : HAL_OK; }
HAL_StatusTypeDef HAL_FLASH_Lock(void) { ++locks; return fail_lock ? HAL_ERROR : HAL_OK; }
HAL_StatusTypeDef HAL_FLASHEx_Erase(FLASH_EraseInitTypeDef *e, uint32_t *error)
{
    ++erases; (void)error;
    if (fail_erase || e->TypeErase != FLASH_TYPEERASE_PAGES || e->NbPages != 1u || e->Page >= 128u) return HAL_ERROR;
    memset((void *)(uintptr_t)(FLASH_BASE + e->Page * FLASH_PAGE_SIZE), 0xff, FLASH_PAGE_SIZE);
    return HAL_OK;
}
HAL_StatusTypeDef HAL_FLASH_Program(uint32_t type, uint32_t address, uintptr_t data)
{
    ++writes;
    if (fail_program || type != FLASH_TYPEPROGRAM_DOUBLEWORD || (address & 7u)) return HAL_ERROR;
    memcpy((void *)(uintptr_t)address, (const void *)data, 8u);
    if (corrupt_write) *(uint8_t *)(uintptr_t)address ^= 1u;
    return HAL_OK;
}
int main(void)
{
    CHECK(comp_wba25_stack_pointer_valid(0x20010000u, false));
    CHECK(comp_wba25_stack_pointer_valid(0x20018000u, false));
    CHECK(!comp_wba25_stack_pointer_valid(0x20018008u, false));
    CHECK(!comp_wba25_stack_pointer_valid(0x20020000u, false)); /* WBA55CE upper end */
    CHECK(!comp_wba25_stack_pointer_valid(0x20000000u, false));
    CHECK(!comp_wba25_stack_pointer_valid(0x20010001u, false));
    CHECK(comp_wba25_stack_pointer_valid(0x30018000u, true));
    CHECK(!comp_wba25_stack_pointer_valid(0x30018000u, false));
    uint8_t *mem = VirtualAlloc((void *)(uintptr_t)FLASH_BASE, FLASH_SIZE, MEM_RESERVE | MEM_COMMIT, PAGE_READWRITE);
    CHECK(mem == (uint8_t *)(uintptr_t)FLASH_BASE);
    memset(mem, 0xff, FLASH_SIZE);
    comp_wba25_internal_flash_t app = { FLASH_BASE + 0x6000u, FLASH_BASE + 0x7e000u };
    uint8_t input[13] = { 0,1,2,3,4,5,6,7,8,9,10,11,12 }, out[13];
    CHECK(comp_wba25_internal_flash_write(&app, app.app_start, input, sizeof(input)));
    CHECK(writes == 2u && locks == 1u && memcmp(mem + 0x6000u, input, sizeof(input)) == 0);
    CHECK(mem[0x600d] == 0xff && mem[0x600f] == 0xff);
    CHECK(comp_wba25_internal_flash_read(&app, app.app_start, out, sizeof(out)) && memcmp(input, out, sizeof(out)) == 0);
    CHECK(!comp_wba25_internal_flash_write(&app, app.app_end - 8u, input, 9u));
    CHECK(!comp_wba25_internal_flash_write(&app, app.app_start + 1u, input, 1u));
    CHECK(!comp_wba25_internal_flash_erase(&app, app.app_start - FLASH_PAGE_SIZE));
    CHECK(!comp_wba25_internal_flash_erase(&app, app.app_end));
    CHECK(!comp_wba25_internal_flash_read(&app, app.app_end - 8u, out, 9u));
    CHECK(writes == 2u && erases == 0u);
    fail_unlock = 1; CHECK(!comp_wba25_internal_flash_erase(&app, app.app_start));
    CHECK(locks == 1u && erases == 0u); fail_unlock = 0;
    fail_erase = 1; CHECK(!comp_wba25_internal_flash_erase(&app, app.app_start));
    CHECK(locks == 2u); fail_erase = 0;
    CHECK(comp_wba25_internal_flash_erase(&app, app.app_start));
    CHECK(mem[0x6000] == 0xff && locks == 3u);
    fail_program = 1; CHECK(!comp_wba25_internal_flash_write(&app, app.app_start, input, sizeof(input)));
    CHECK(locks == 4u); fail_program = 0;
    corrupt_write = 1; CHECK(!comp_wba25_internal_flash_write(&app, app.app_start, input, sizeof(input)));
    CHECK(locks == 5u); corrupt_write = 0;
    fail_lock = 1; CHECK(!comp_wba25_internal_flash_erase(&app, app.app_start)); fail_lock = 0;
    comp_wba25_internal_flash_t invalid = { app.app_start, FLASH_BASE + FLASH_SIZE + FLASH_PAGE_SIZE };
    CHECK(!comp_wba25_internal_flash_erase(&invalid, invalid.app_start));
    CHECK(VirtualFree(mem, 0, MEM_RELEASE));
    puts("WBA25_FLASH_AND_SRAM_HOST_MODEL_ONLY: 64+32KiB stack bounds, 4KiB erase, 8-byte writes, readback and HAL failures passed");
    return 0;
}
