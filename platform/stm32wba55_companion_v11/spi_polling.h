#ifndef COMPANION_V11_SPI_POLLING_H
#define COMPANION_V11_SPI_POLLING_H

#include "stm32wbaxx_hal.h"
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <string.h>

/* SPI3 is the limited-feature instance. RM0493 limits its TSIZE counter;
 * the generic HAL/CMSIS mask is shared with full-feature SPI1 and does not
 * enforce that limit. Keep SPI3 calls at 512 bytes, including factory reads.
 * The caller owns CS for the entire command: chunk boundaries never pulse it.
 */
static inline bool comp_v11_spi_polling_transfer(SPI_HandleTypeDef *bus,
    const uint8_t *tx, uint8_t *rx, size_t size, uint32_t timeout)
{
    if (bus == NULL || size == 0u || size > UINT16_MAX || (tx == NULL && rx == NULL) ||
        (bus->Instance != SPI1 && bus->Instance != SPI3)) return false;
    const size_t limit = bus->Instance == SPI3 ? 512u : UINT16_MAX;
    while (size != 0u) {
        uint16_t count = (uint16_t)(size > limit ? limit : size);
        HAL_StatusTypeDef result;
        if (tx != NULL && rx != NULL) {
            result = HAL_SPI_TransmitReceive(bus, tx, rx, count, timeout);
        } else if (tx != NULL) {
            result = HAL_SPI_Transmit(bus, tx, count, timeout);
        } else {
            memset(rx, 0xFF, count);
            result = HAL_SPI_TransmitReceive(bus, rx, rx, count, timeout);
        }
        if (result != HAL_OK) return false;
        if (tx != NULL) tx += count;
        if (rx != NULL) rx += count;
        size -= count;
    }
    return true;
}
#endif
