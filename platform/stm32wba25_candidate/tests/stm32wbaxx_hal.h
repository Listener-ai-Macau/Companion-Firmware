#ifndef TEST_STM32WBAXX_HAL_H
#define TEST_STM32WBAXX_HAL_H
#include <stdint.h>
#define FLASH_BASE 0x08000000u
#define FLASH_SIZE 0x00080000u
#define FLASH_PAGE_SIZE 4096u
#define FLASH_DOUBLEWORD_SUPPORT 1
#define FLASH_TYPEERASE_PAGES 1u
#define FLASH_TYPEPROGRAM_DOUBLEWORD 2u
typedef enum { HAL_OK = 0, HAL_ERROR = 1 } HAL_StatusTypeDef;
typedef struct { uint32_t TypeErase, Page, NbPages; } FLASH_EraseInitTypeDef;
HAL_StatusTypeDef HAL_FLASH_Unlock(void);
HAL_StatusTypeDef HAL_FLASH_Lock(void);
HAL_StatusTypeDef HAL_FLASHEx_Erase(FLASH_EraseInitTypeDef *, uint32_t *);
HAL_StatusTypeDef HAL_FLASH_Program(uint32_t, uint32_t, uintptr_t);
#endif
