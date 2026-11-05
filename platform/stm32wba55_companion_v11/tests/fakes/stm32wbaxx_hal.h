#ifndef TEST_WBA_PRODUCT_STM32WBAXX_HAL_H
#define TEST_WBA_PRODUCT_STM32WBAXX_HAL_H

#include <stdint.h>

/* Host-layout placeholders only.  The integration fixture never calls the
 * STM32 HAL; it needs the public board state layout used by product_app. */
typedef struct { uintptr_t instance; uint32_t error_code; } SAI_HandleTypeDef;
typedef struct { uintptr_t instance; uint32_t counter; } DMA_HandleTypeDef;
typedef struct { uint32_t words[16]; } DMA_NodeTypeDef;
typedef struct { uint32_t words[8]; } DMA_QListTypeDef;

uint32_t HAL_GetTick(void);

#endif
