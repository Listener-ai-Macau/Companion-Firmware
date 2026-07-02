#ifndef COMP_QSPI_NOR_H
#define COMP_QSPI_NOR_H

#include "stm32wbxx_hal.h"

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

typedef enum {
    COMP_QSPI_NOR_OK = 0,
    COMP_QSPI_NOR_ERROR = -1,
    COMP_QSPI_NOR_BUSY = -2,
    COMP_QSPI_NOR_TIMEOUT = -3,
    COMP_QSPI_NOR_UNSUPPORTED = -4,
    COMP_QSPI_NOR_BAD_PARAM = -5,
} comp_qspi_nor_status_t;

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
    bool quad_enabled;
    bool sfdp_present;
} comp_qspi_nor_info_t;

typedef struct {
    QSPI_HandleTypeDef *hqspi;
    comp_qspi_nor_info_t info;
    uint32_t timeout_ms;
    bool prefer_quad_read;
} comp_qspi_nor_t;

void comp_qspi_nor_init(comp_qspi_nor_t *nor, QSPI_HandleTypeDef *hqspi);
const char *comp_qspi_nor_status_name(comp_qspi_nor_status_t status);

comp_qspi_nor_status_t comp_qspi_nor_probe(comp_qspi_nor_t *nor, comp_qspi_nor_info_t *out_info);
comp_qspi_nor_status_t comp_qspi_nor_read_id(comp_qspi_nor_t *nor, uint8_t id[3]);
comp_qspi_nor_status_t comp_qspi_nor_read_status(comp_qspi_nor_t *nor, uint8_t *status1, uint8_t *status2);
comp_qspi_nor_status_t comp_qspi_nor_read_sfdp(comp_qspi_nor_t *nor,
                                               uint32_t address,
                                               uint8_t *data,
                                               size_t length);
comp_qspi_nor_status_t comp_qspi_nor_read(comp_qspi_nor_t *nor,
                                          uint32_t address,
                                          uint8_t *data,
                                          size_t length);
comp_qspi_nor_status_t comp_qspi_nor_write(comp_qspi_nor_t *nor,
                                           uint32_t address,
                                           const uint8_t *data,
                                           size_t length);
comp_qspi_nor_status_t comp_qspi_nor_erase_4k(comp_qspi_nor_t *nor, uint32_t address);
comp_qspi_nor_status_t comp_qspi_nor_erase_64k(comp_qspi_nor_t *nor, uint32_t address);
comp_qspi_nor_status_t comp_qspi_nor_wait_ready(comp_qspi_nor_t *nor, uint32_t timeout_ms);
comp_qspi_nor_status_t comp_qspi_nor_release_powerdown(comp_qspi_nor_t *nor);

#endif /* COMP_QSPI_NOR_H */
