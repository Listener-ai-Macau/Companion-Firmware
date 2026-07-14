#include "comp_spi_nor_stm32wb_spi1.h"

#include <limits.h>
#include <string.h>

#define COMP_SPI_NOR_TRANSFER_TIMEOUT_MS 200u
#define COMP_SPI_NOR_PROGRAM_TIMEOUT_MS 5000u
#define COMP_SPI_NOR_ERASE_TIMEOUT_MS 30000u
#define COMP_SPI_NOR_BLOCK_SIZE 65536u

static bool spi1_chip_select(void *context, bool active)
{
    comp_spi_nor_t *nor = (comp_spi_nor_t *)context;
    if (nor == NULL || nor->cs_port == NULL || nor->cs_pin == 0u) {
        return false;
    }
    HAL_GPIO_WritePin(nor->cs_port,
                      nor->cs_pin,
                      active ? GPIO_PIN_RESET : GPIO_PIN_SET);
    if (active) {
        nor->transaction_count++;
    }
    return true;
}

static bool spi1_transfer(void *context,
                          const uint8_t *transmit,
                          uint8_t *receive,
                          size_t length,
                          uint32_t timeout_ms)
{
    comp_spi_nor_t *nor = (comp_spi_nor_t *)context;
    if (nor == NULL || nor->hspi == NULL || length == 0u || timeout_ms == 0u ||
        (transmit == NULL && receive == NULL)) {
        return false;
    }

    size_t offset = 0u;
    while (offset < length) {
        size_t remaining = length - offset;
        uint16_t chunk = remaining > UINT16_MAX ? UINT16_MAX : (uint16_t)remaining;
        HAL_StatusTypeDef status;
        if (transmit != NULL && receive != NULL) {
            status = HAL_SPI_TransmitReceive(nor->hspi,
                                             (uint8_t *)&transmit[offset],
                                             &receive[offset],
                                             chunk,
                                             timeout_ms);
        } else if (transmit != NULL) {
            status = HAL_SPI_Transmit(nor->hspi,
                                      (uint8_t *)&transmit[offset],
                                      chunk,
                                      timeout_ms);
        } else {
            status = HAL_SPI_Receive(nor->hspi,
                                     &receive[offset],
                                     chunk,
                                     timeout_ms);
        }
        nor->last_hal_status = status;
        nor->last_hal_error = HAL_SPI_GetError(nor->hspi);
        if (status != HAL_OK) {
            return false;
        }
        nor->transferred_bytes += chunk;
        offset += chunk;
    }
    return true;
}

static uint32_t spi1_now_ms(void *context)
{
    (void)context;
    return HAL_GetTick();
}

static void spi1_delay_ms(void *context, uint32_t delay_ms)
{
    (void)context;
    HAL_Delay(delay_ms);
}

bool comp_spi_nor_init(comp_spi_nor_t *nor,
                       SPI_HandleTypeDef *hspi,
                       GPIO_TypeDef *cs_port,
                       uint16_t cs_pin)
{
    if (nor == NULL || hspi == NULL || hspi->Instance != SPI1 ||
        cs_port == NULL || cs_pin == 0u) {
        return false;
    }
    memset(nor, 0, sizeof(*nor));
    nor->hspi = hspi;
    nor->cs_port = cs_port;
    nor->cs_pin = cs_pin;
    nor->last_hal_status = HAL_OK;
    nor->last_hal_error = HAL_SPI_ERROR_NONE;
    HAL_GPIO_WritePin(nor->cs_port, nor->cs_pin, GPIO_PIN_SET);

    const companion_spi_nor_stm32wba_config_t config = {
        .target = COMPANION_SPI_NOR_STM32WBA_TARGET_WB55,
        .chip_select = spi1_chip_select,
        .transfer = spi1_transfer,
        .now_ms = spi1_now_ms,
        .delay_ms = spi1_delay_ms,
        .context = nor,
        .transfer_timeout_ms = COMP_SPI_NOR_TRANSFER_TIMEOUT_MS,
        .page_program_timeout_ms = COMP_SPI_NOR_PROGRAM_TIMEOUT_MS,
        .sector_erase_timeout_ms = COMP_SPI_NOR_ERASE_TIMEOUT_MS,
    };
    return companion_spi_nor_stm32wba_init(&nor->core, &config);
}

const char *comp_spi_nor_status_name(comp_spi_nor_status_t status)
{
    return companion_spi_nor_stm32wba_status_name(status);
}

comp_spi_nor_status_t comp_spi_nor_probe(comp_spi_nor_t *nor,
                                         comp_spi_nor_info_t *out_info)
{
    if (nor == NULL) {
        return COMP_SPI_NOR_BAD_PARAM;
    }
    companion_spi_nor_stm32wba_info_t info;
    comp_spi_nor_status_t status =
        companion_spi_nor_stm32wba_probe(&nor->core, &info);
    if (status != COMP_SPI_NOR_OK) {
        memset(&nor->info, 0, sizeof(nor->info));
        return status;
    }
    nor->info = (comp_spi_nor_info_t){
        .jedec_id = info.jedec_id,
        .manufacturer_id = info.manufacturer_id,
        .memory_type = info.memory_type,
        .capacity_code = info.capacity_code,
        .status1 = info.status1,
        .status2 = 0u,
        .size_bytes = info.size_bytes,
        .sector_size = info.sector_size,
        .page_size = info.page_size,
        .block_size = COMP_SPI_NOR_BLOCK_SIZE,
        .quad_enabled = false,
        .sfdp_present = false,
    };
    if (out_info != NULL) {
        *out_info = nor->info;
    }
    return COMP_SPI_NOR_OK;
}

comp_spi_nor_status_t comp_spi_nor_wait_ready(comp_spi_nor_t *nor,
                                              uint32_t timeout_ms)
{
    return nor == NULL
               ? COMP_SPI_NOR_BAD_PARAM
               : companion_spi_nor_stm32wba_wait_ready(&nor->core, timeout_ms);
}

comp_spi_nor_status_t comp_spi_nor_read(comp_spi_nor_t *nor,
                                        uint32_t address,
                                        uint8_t *data,
                                        size_t length)
{
    return nor == NULL
               ? COMP_SPI_NOR_BAD_PARAM
               : companion_spi_nor_stm32wba_read(
                     &nor->core, address, data, length);
}

comp_spi_nor_status_t comp_spi_nor_write(comp_spi_nor_t *nor,
                                         uint32_t address,
                                         const uint8_t *data,
                                         size_t length)
{
    return nor == NULL
               ? COMP_SPI_NOR_BAD_PARAM
               : companion_spi_nor_stm32wba_program(
                     &nor->core, address, data, length);
}

comp_spi_nor_status_t comp_spi_nor_erase_4k(comp_spi_nor_t *nor,
                                            uint32_t address)
{
    return nor == NULL
               ? COMP_SPI_NOR_BAD_PARAM
               : companion_spi_nor_stm32wba_erase_4k(&nor->core, address);
}

comp_spi_nor_status_t comp_spi_nor_erase_64k(comp_spi_nor_t *nor,
                                             uint32_t address)
{
    return nor == NULL
               ? COMP_SPI_NOR_BAD_PARAM
               : companion_spi_nor_stm32wba_erase_64k(&nor->core, address);
}

uint32_t comp_spi_nor_last_probe_jedec_id(const comp_spi_nor_t *nor)
{
    return nor == NULL ? 0u : nor->core.last_probe_jedec_id;
}

bool comp_spi_nor_last_probe_id_transfer_completed(const comp_spi_nor_t *nor)
{
    return nor != NULL && nor->core.last_probe_id_transfer_completed;
}
