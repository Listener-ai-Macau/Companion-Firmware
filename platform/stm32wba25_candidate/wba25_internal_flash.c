#include "wba25_internal_flash.h"
#include "stm32wbaxx_hal.h"
#include <string.h>

#if !defined(STM32WBA25xx) || !defined(FLASH_DOUBLEWORD_SUPPORT)
#error "This experimental adapter requires the STM32WBA25 double-word Flash HAL"
#endif
_Static_assert(FLASH_PAGE_SIZE == 4096u, "WBA25 Flash erase page must be 4 KiB");

/* All calls are restricted to the eventual board's authenticated app extent;
 * the existing WBA55 layout and its update identity must never be reused. */
static bool valid_range(const comp_wba25_internal_flash_t *p)
{
    const uint32_t base = FLASH_BASE;
    const uint32_t size = FLASH_SIZE;
    return p && p->app_start >= base && p->app_end > p->app_start &&
        p->app_start % FLASH_PAGE_SIZE == 0u && p->app_end % FLASH_PAGE_SIZE == 0u &&
        p->app_end - base <= size;
}

bool comp_wba25_internal_flash_read(void *context, uint32_t address,
                                    uint8_t *data, size_t length)
{
    const comp_wba25_internal_flash_t *p = context;
    if (!valid_range(p) || !data || !length || address < p->app_start ||
        address >= p->app_end || length > p->app_end - address) return false;
    memcpy(data, (const void *)(uintptr_t)address, length);
    return true;
}

bool comp_wba25_internal_flash_erase(void *context, uint32_t address)
{
    const comp_wba25_internal_flash_t *p = context;
    FLASH_EraseInitTypeDef erase = {0};
    uint32_t error = 0u;
    if (!valid_range(p) || address < p->app_start || address >= p->app_end ||
        address % FLASH_PAGE_SIZE != 0u) return false;
    erase.TypeErase = FLASH_TYPEERASE_PAGES;
    erase.Page = (address - FLASH_BASE) / FLASH_PAGE_SIZE;
    erase.NbPages = 1u;
    if (HAL_FLASH_Unlock() != HAL_OK) return false;
    HAL_StatusTypeDef result = HAL_FLASHEx_Erase(&erase, &error);
    HAL_StatusTypeDef locked = HAL_FLASH_Lock();
    return result == HAL_OK && locked == HAL_OK;
}

bool comp_wba25_internal_flash_write(void *context, uint32_t address,
                                     const uint8_t *data, size_t length)
{
    const comp_wba25_internal_flash_t *p = context;
    uint32_t words[2];
    HAL_StatusTypeDef result = HAL_OK;
    if (!valid_range(p) || !data || !length || address < p->app_start ||
        address >= p->app_end || address % sizeof(words) != 0u ||
        length > p->app_end - address) return false;
    /* The end is page-aligned. An 8-byte-aligned address and a bounded length
     * ensure that padding the final unit cannot escape the app extent. */
    if (HAL_FLASH_Unlock() != HAL_OK) return false;
    for (size_t offset = 0u; offset < length; offset += sizeof(words)) {
        size_t n = length - offset < sizeof(words) ? length - offset : sizeof(words);
        memset(words, 0xff, sizeof(words));
        memcpy(words, data + offset, n);
        uint32_t destination = address + (uint32_t)offset;
        if (HAL_FLASH_Program(FLASH_TYPEPROGRAM_DOUBLEWORD, destination,
                              (uintptr_t)words) != HAL_OK ||
            memcmp((const void *)(uintptr_t)destination, words, sizeof(words)) != 0) {
            result = HAL_ERROR;
            break;
        }
    }
    HAL_StatusTypeDef locked = HAL_FLASH_Lock();
    return result == HAL_OK && locked == HAL_OK;
}
