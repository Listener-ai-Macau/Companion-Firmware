#ifndef COMP_SPI_TEST_HAL_H
#define COMP_SPI_TEST_HAL_H
#include <stdint.h>
typedef struct { uint32_t unused; } SPI_TypeDef;
typedef struct { SPI_TypeDef *Instance; } SPI_HandleTypeDef;
typedef enum { HAL_OK=0, HAL_ERROR=1 } HAL_StatusTypeDef;
extern SPI_TypeDef test_spi1, test_spi3;
#define SPI1 (&test_spi1)
#define SPI3 (&test_spi3)
HAL_StatusTypeDef HAL_SPI_Transmit(SPI_HandleTypeDef *, const uint8_t *, uint16_t, uint32_t);
HAL_StatusTypeDef HAL_SPI_TransmitReceive(SPI_HandleTypeDef *, const uint8_t *, uint8_t *, uint16_t, uint32_t);
#endif
