#ifndef COMP_SPI_NOR_STM32WB_SPI1_H
#define COMP_SPI_NOR_STM32WB_SPI1_H

#include "spi_nor_stm32wba.h"
#include "stm32wbxx_hal.h"

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

typedef companion_spi_nor_stm32wba_status_t comp_spi_nor_status_t;

#define COMP_SPI_NOR_OK COMPANION_SPI_NOR_STM32WBA_OK
#define COMP_SPI_NOR_ERROR COMPANION_SPI_NOR_STM32WBA_ERROR
#define COMP_SPI_NOR_TIMEOUT COMPANION_SPI_NOR_STM32WBA_TIMEOUT
#define COMP_SPI_NOR_UNSUPPORTED COMPANION_SPI_NOR_STM32WBA_UNSUPPORTED
#define COMP_SPI_NOR_BAD_PARAM COMPANION_SPI_NOR_STM32WBA_BAD_PARAM
#define COMP_SPI_NOR_OUT_OF_RANGE COMPANION_SPI_NOR_STM32WBA_OUT_OF_RANGE
#define COMP_SPI_NOR_NOT_PROBED COMPANION_SPI_NOR_STM32WBA_NOT_PROBED

typedef struct {
    uint32_t jedec_id;
    uint8_t manufacturer_id;
    uint8_t memory_type;
    uint8_t capacity_code;
    uint8_t status1;
    uint8_t status2;
    uint32_t size_bytes;
    uint32_t sector_size;
    uint32_t page_size;
    uint32_t block_size;
    bool quad_enabled;
    bool sfdp_present;
} comp_spi_nor_info_t;

typedef struct {
    companion_spi_nor_stm32wba_t core;
    comp_spi_nor_info_t info;
    SPI_HandleTypeDef *hspi;
    GPIO_TypeDef *cs_port;
    uint16_t cs_pin;
    uint32_t transaction_count;
    uint32_t transferred_bytes;
    HAL_StatusTypeDef last_hal_status;
    uint32_t last_hal_error;
} comp_spi_nor_t;

bool comp_spi_nor_init(comp_spi_nor_t *nor,
                       SPI_HandleTypeDef *hspi,
                       GPIO_TypeDef *cs_port,
                       uint16_t cs_pin);
const char *comp_spi_nor_status_name(comp_spi_nor_status_t status);
comp_spi_nor_status_t comp_spi_nor_probe(comp_spi_nor_t *nor,
                                         comp_spi_nor_info_t *out_info);
comp_spi_nor_status_t comp_spi_nor_wait_ready(comp_spi_nor_t *nor,
                                              uint32_t timeout_ms);
comp_spi_nor_status_t comp_spi_nor_read(comp_spi_nor_t *nor,
                                        uint32_t address,
                                        uint8_t *data,
                                        size_t length);
comp_spi_nor_status_t comp_spi_nor_write(comp_spi_nor_t *nor,
                                         uint32_t address,
                                         const uint8_t *data,
                                         size_t length);
comp_spi_nor_status_t comp_spi_nor_erase_4k(comp_spi_nor_t *nor,
                                            uint32_t address);
comp_spi_nor_status_t comp_spi_nor_erase_64k(comp_spi_nor_t *nor,
                                             uint32_t address);
uint32_t comp_spi_nor_last_probe_jedec_id(const comp_spi_nor_t *nor);
bool comp_spi_nor_last_probe_id_transfer_completed(const comp_spi_nor_t *nor);

#endif /* COMP_SPI_NOR_STM32WB_SPI1_H */
