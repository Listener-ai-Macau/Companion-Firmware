#ifndef COMPANION_SPI_NOR_STM32WBA_H
#define COMPANION_SPI_NOR_STM32WBA_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef enum {
    COMPANION_SPI_NOR_STM32WBA_TARGET_WB55 = 54,
    COMPANION_SPI_NOR_STM32WBA_TARGET_WBA55 = 55,
    COMPANION_SPI_NOR_STM32WBA_TARGET_WBA65 = 65,
} companion_spi_nor_stm32wba_target_t;

typedef enum {
    COMPANION_SPI_NOR_STM32WBA_OK = 0,
    COMPANION_SPI_NOR_STM32WBA_ERROR = -1,
    COMPANION_SPI_NOR_STM32WBA_TIMEOUT = -2,
    COMPANION_SPI_NOR_STM32WBA_UNSUPPORTED = -3,
    COMPANION_SPI_NOR_STM32WBA_BAD_PARAM = -4,
    COMPANION_SPI_NOR_STM32WBA_OUT_OF_RANGE = -5,
    COMPANION_SPI_NOR_STM32WBA_NOT_PROBED = -6,
} companion_spi_nor_stm32wba_status_t;

typedef bool (*companion_spi_nor_stm32wba_chip_select_fn_t)(
    void *context,
    bool active);

typedef bool (*companion_spi_nor_stm32wba_transfer_fn_t)(
    void *context,
    const uint8_t *transmit,
    uint8_t *receive,
    size_t length,
    uint32_t timeout_ms);

typedef uint32_t (*companion_spi_nor_stm32wba_now_ms_fn_t)(void *context);
typedef void (*companion_spi_nor_stm32wba_delay_ms_fn_t)(
    void *context,
    uint32_t delay_ms);

typedef struct {
    companion_spi_nor_stm32wba_target_t target;
    companion_spi_nor_stm32wba_chip_select_fn_t chip_select;
    companion_spi_nor_stm32wba_transfer_fn_t transfer;
    companion_spi_nor_stm32wba_now_ms_fn_t now_ms;
    companion_spi_nor_stm32wba_delay_ms_fn_t delay_ms;
    void *context;
    uint32_t transfer_timeout_ms;
    uint32_t page_program_timeout_ms;
    uint32_t sector_erase_timeout_ms;
} companion_spi_nor_stm32wba_config_t;

typedef struct {
    uint32_t jedec_id;
    uint8_t manufacturer_id;
    uint8_t memory_type;
    uint8_t capacity_code;
    uint8_t status1;
    uint32_t size_bytes;
    uint32_t page_size;
    uint32_t sector_size;
} companion_spi_nor_stm32wba_info_t;

typedef struct {
    companion_spi_nor_stm32wba_config_t config;
    companion_spi_nor_stm32wba_info_t info;
    bool probed;
    bool last_probe_id_transfer_completed;
    uint32_t last_probe_jedec_id;
} companion_spi_nor_stm32wba_t;

typedef struct {
    companion_spi_nor_stm32wba_t *nor;
    uint32_t base_address;
    uint32_t size_bytes;
} companion_spi_nor_stm32wba_partition_t;

bool companion_spi_nor_stm32wba_init(
    companion_spi_nor_stm32wba_t *nor,
    const companion_spi_nor_stm32wba_config_t *config);

bool companion_spi_nor_stm32wba_ready(
    const companion_spi_nor_stm32wba_t *nor);

const char *companion_spi_nor_stm32wba_status_name(
    companion_spi_nor_stm32wba_status_t status);

companion_spi_nor_stm32wba_status_t companion_spi_nor_stm32wba_probe(
    companion_spi_nor_stm32wba_t *nor,
    companion_spi_nor_stm32wba_info_t *out_info);

companion_spi_nor_stm32wba_status_t companion_spi_nor_stm32wba_wait_ready(
    companion_spi_nor_stm32wba_t *nor,
    uint32_t timeout_ms);

companion_spi_nor_stm32wba_status_t companion_spi_nor_stm32wba_read(
    companion_spi_nor_stm32wba_t *nor,
    uint32_t address,
    uint8_t *destination,
    size_t length);

companion_spi_nor_stm32wba_status_t companion_spi_nor_stm32wba_program(
    companion_spi_nor_stm32wba_t *nor,
    uint32_t address,
    const uint8_t *source,
    size_t length);

companion_spi_nor_stm32wba_status_t companion_spi_nor_stm32wba_erase_4k(
    companion_spi_nor_stm32wba_t *nor,
    uint32_t address);

companion_spi_nor_stm32wba_status_t companion_spi_nor_stm32wba_erase_64k(
    companion_spi_nor_stm32wba_t *nor,
    uint32_t address);

bool companion_spi_nor_stm32wba_partition_init(
    companion_spi_nor_stm32wba_partition_t *partition,
    companion_spi_nor_stm32wba_t *nor,
    uint32_t base_address,
    uint32_t size_bytes);

bool companion_spi_nor_stm32wba_partition_read(
    void *context,
    uint32_t partition_offset,
    uint8_t *destination,
    size_t length);

companion_spi_nor_stm32wba_status_t
companion_spi_nor_stm32wba_partition_program(
    companion_spi_nor_stm32wba_partition_t *partition,
    uint32_t partition_offset,
    const uint8_t *source,
    size_t length);

companion_spi_nor_stm32wba_status_t
companion_spi_nor_stm32wba_partition_erase_4k(
    companion_spi_nor_stm32wba_partition_t *partition,
    uint32_t partition_offset);

#ifdef __cplusplus
}
#endif

#endif /* COMPANION_SPI_NOR_STM32WBA_H */
