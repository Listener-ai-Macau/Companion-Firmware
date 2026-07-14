#include "spi_nor_stm32wba.h"

#include <string.h>

#define NOR_CMD_WRITE_ENABLE 0x06u
#define NOR_CMD_READ_STATUS1 0x05u
#define NOR_CMD_READ_JEDEC_ID 0x9Fu
#define NOR_CMD_RELEASE_POWERDOWN 0xABu
#define NOR_CMD_ENABLE_RESET 0x66u
#define NOR_CMD_RESET_DEVICE 0x99u
#define NOR_CMD_READ_DATA 0x03u
#define NOR_CMD_PAGE_PROGRAM 0x02u
#define NOR_CMD_SECTOR_ERASE_4K 0x20u
#define NOR_CMD_BLOCK_ERASE_64K 0xD8u

#define NOR_SR1_WIP 0x01u
#define NOR_SR1_WEL 0x02u

#define NOR_MANUFACTURER_XTX 0x0Bu
#define NOR_XTX_RESET_DELAY_MS 1u

#define NOR_DEFAULT_TRANSFER_TIMEOUT_MS 200u
#define NOR_DEFAULT_PROGRAM_TIMEOUT_MS 5000u
#define NOR_DEFAULT_ERASE_TIMEOUT_MS 30000u
#define NOR_PAGE_SIZE 256u
#define NOR_SECTOR_SIZE 4096u
#define NOR_BLOCK_SIZE 65536u
#define NOR_MAX_24BIT_SIZE 0x01000000u

static bool target_valid(companion_spi_nor_stm32wba_target_t target)
{
    return target == COMPANION_SPI_NOR_STM32WBA_TARGET_WB55 ||
           target == COMPANION_SPI_NOR_STM32WBA_TARGET_WBA55 ||
           target == COMPANION_SPI_NOR_STM32WBA_TARGET_WBA65;
}

static bool configured(const companion_spi_nor_stm32wba_t *nor)
{
    return nor != NULL && target_valid(nor->config.target) &&
           nor->config.chip_select != NULL && nor->config.transfer != NULL &&
           nor->config.now_ms != NULL && nor->config.delay_ms != NULL;
}

static companion_spi_nor_stm32wba_status_t finish_transaction(
    companion_spi_nor_stm32wba_t *nor,
    companion_spi_nor_stm32wba_status_t status)
{
    bool released = nor->config.chip_select(nor->config.context, false);
    if (status == COMPANION_SPI_NOR_STM32WBA_OK && !released) {
        return COMPANION_SPI_NOR_STM32WBA_ERROR;
    }
    return status;
}

static companion_spi_nor_stm32wba_status_t begin_transaction(
    companion_spi_nor_stm32wba_t *nor)
{
    if (!configured(nor)) {
        return COMPANION_SPI_NOR_STM32WBA_BAD_PARAM;
    }
    return nor->config.chip_select(nor->config.context, true)
               ? COMPANION_SPI_NOR_STM32WBA_OK
               : COMPANION_SPI_NOR_STM32WBA_ERROR;
}

static companion_spi_nor_stm32wba_status_t transfer_bytes(
    companion_spi_nor_stm32wba_t *nor,
    const uint8_t *transmit,
    uint8_t *receive,
    size_t length)
{
    if (length == 0u) {
        return COMPANION_SPI_NOR_STM32WBA_OK;
    }
    return nor->config.transfer(nor->config.context,
                                transmit,
                                receive,
                                length,
                                nor->config.transfer_timeout_ms)
               ? COMPANION_SPI_NOR_STM32WBA_OK
               : COMPANION_SPI_NOR_STM32WBA_ERROR;
}

static companion_spi_nor_stm32wba_status_t send_command(
    companion_spi_nor_stm32wba_t *nor,
    uint8_t command)
{
    companion_spi_nor_stm32wba_status_t status = begin_transaction(nor);
    if (status != COMPANION_SPI_NOR_STM32WBA_OK) {
        return status;
    }
    status = transfer_bytes(nor, &command, NULL, 1u);
    return finish_transaction(nor, status);
}

static companion_spi_nor_stm32wba_status_t read_command(
    companion_spi_nor_stm32wba_t *nor,
    uint8_t command,
    uint8_t *destination,
    size_t length)
{
    if (destination == NULL || length == 0u) {
        return COMPANION_SPI_NOR_STM32WBA_BAD_PARAM;
    }
    companion_spi_nor_stm32wba_status_t status = begin_transaction(nor);
    if (status != COMPANION_SPI_NOR_STM32WBA_OK) {
        return status;
    }
    status = transfer_bytes(nor, &command, NULL, 1u);
    if (status == COMPANION_SPI_NOR_STM32WBA_OK) {
        status = transfer_bytes(nor, NULL, destination, length);
    }
    return finish_transaction(nor, status);
}

static void encode_address(uint8_t header[4], uint8_t command, uint32_t address)
{
    header[0] = command;
    header[1] = (uint8_t)(address >> 16);
    header[2] = (uint8_t)(address >> 8);
    header[3] = (uint8_t)address;
}

static companion_spi_nor_stm32wba_status_t read_addressed(
    companion_spi_nor_stm32wba_t *nor,
    uint8_t command,
    uint32_t address,
    uint8_t *destination,
    size_t length)
{
    uint8_t header[4];
    encode_address(header, command, address);
    companion_spi_nor_stm32wba_status_t status = begin_transaction(nor);
    if (status != COMPANION_SPI_NOR_STM32WBA_OK) {
        return status;
    }
    status = transfer_bytes(nor, header, NULL, sizeof(header));
    if (status == COMPANION_SPI_NOR_STM32WBA_OK) {
        status = transfer_bytes(nor, NULL, destination, length);
    }
    return finish_transaction(nor, status);
}

static companion_spi_nor_stm32wba_status_t write_addressed(
    companion_spi_nor_stm32wba_t *nor,
    uint8_t command,
    uint32_t address,
    const uint8_t *source,
    size_t length)
{
    uint8_t header[4];
    encode_address(header, command, address);
    companion_spi_nor_stm32wba_status_t status = begin_transaction(nor);
    if (status != COMPANION_SPI_NOR_STM32WBA_OK) {
        return status;
    }
    status = transfer_bytes(nor, header, NULL, sizeof(header));
    if (status == COMPANION_SPI_NOR_STM32WBA_OK && length != 0u) {
        status = transfer_bytes(nor, source, NULL, length);
    }
    return finish_transaction(nor, status);
}

static companion_spi_nor_stm32wba_status_t read_status1(
    companion_spi_nor_stm32wba_t *nor,
    uint8_t *status1)
{
    return read_command(nor, NOR_CMD_READ_STATUS1, status1, 1u);
}

static companion_spi_nor_stm32wba_status_t read_jedec_id(
    companion_spi_nor_stm32wba_t *nor,
    uint8_t id[3])
{
    companion_spi_nor_stm32wba_status_t status =
        read_command(nor, NOR_CMD_READ_JEDEC_ID, id, 3u);
    if (status != COMPANION_SPI_NOR_STM32WBA_OK) {
        return status;
    }
    nor->last_probe_id_transfer_completed = true;
    nor->last_probe_jedec_id = ((uint32_t)id[0] << 16) |
                               ((uint32_t)id[1] << 8) |
                               (uint32_t)id[2];
    return COMPANION_SPI_NOR_STM32WBA_OK;
}

static companion_spi_nor_stm32wba_status_t normalize_xtx_after_mcu_reset(
    companion_spi_nor_stm32wba_t *nor)
{
    companion_spi_nor_stm32wba_status_t status =
        companion_spi_nor_stm32wba_wait_ready(
            nor,
            nor->config.page_program_timeout_ms);
    if (status != COMPANION_SPI_NOR_STM32WBA_OK) {
        return status;
    }
    status = send_command(nor, NOR_CMD_ENABLE_RESET);
    if (status != COMPANION_SPI_NOR_STM32WBA_OK) {
        return status;
    }
    status = send_command(nor, NOR_CMD_RESET_DEVICE);
    if (status != COMPANION_SPI_NOR_STM32WBA_OK) {
        return status;
    }
    nor->config.delay_ms(nor->config.context, NOR_XTX_RESET_DELAY_MS);
    return COMPANION_SPI_NOR_STM32WBA_OK;
}

static companion_spi_nor_stm32wba_status_t write_enable(
    companion_spi_nor_stm32wba_t *nor)
{
    companion_spi_nor_stm32wba_status_t status =
        send_command(nor, NOR_CMD_WRITE_ENABLE);
    if (status != COMPANION_SPI_NOR_STM32WBA_OK) {
        return status;
    }
    uint8_t status1 = 0u;
    status = read_status1(nor, &status1);
    if (status != COMPANION_SPI_NOR_STM32WBA_OK) {
        return status;
    }
    return (status1 & NOR_SR1_WEL) != 0u
               ? COMPANION_SPI_NOR_STM32WBA_OK
               : COMPANION_SPI_NOR_STM32WBA_ERROR;
}

static uint32_t size_from_capacity_code(uint8_t capacity_code)
{
    if (capacity_code < 20u || capacity_code > 24u) {
        return 0u;
    }
    return 1u << capacity_code;
}

static bool range_valid(uint32_t size_bytes, uint32_t offset, size_t length)
{
    if (offset > size_bytes || length > (size_t)(size_bytes - offset)) {
        return false;
    }
    return true;
}

bool companion_spi_nor_stm32wba_init(
    companion_spi_nor_stm32wba_t *nor,
    const companion_spi_nor_stm32wba_config_t *config)
{
    if (nor == NULL || config == NULL) {
        return false;
    }
    memset(nor, 0, sizeof(*nor));
    nor->config = *config;
    if (nor->config.transfer_timeout_ms == 0u) {
        nor->config.transfer_timeout_ms = NOR_DEFAULT_TRANSFER_TIMEOUT_MS;
    }
    if (nor->config.page_program_timeout_ms == 0u) {
        nor->config.page_program_timeout_ms = NOR_DEFAULT_PROGRAM_TIMEOUT_MS;
    }
    if (nor->config.sector_erase_timeout_ms == 0u) {
        nor->config.sector_erase_timeout_ms = NOR_DEFAULT_ERASE_TIMEOUT_MS;
    }
    nor->info.page_size = NOR_PAGE_SIZE;
    nor->info.sector_size = NOR_SECTOR_SIZE;
    return configured(nor);
}

bool companion_spi_nor_stm32wba_ready(
    const companion_spi_nor_stm32wba_t *nor)
{
    return configured(nor) && nor->probed && nor->info.size_bytes != 0u;
}

const char *companion_spi_nor_stm32wba_status_name(
    companion_spi_nor_stm32wba_status_t status)
{
    switch (status) {
    case COMPANION_SPI_NOR_STM32WBA_OK:
        return "ok";
    case COMPANION_SPI_NOR_STM32WBA_TIMEOUT:
        return "timeout";
    case COMPANION_SPI_NOR_STM32WBA_UNSUPPORTED:
        return "unsupported";
    case COMPANION_SPI_NOR_STM32WBA_BAD_PARAM:
        return "bad_param";
    case COMPANION_SPI_NOR_STM32WBA_OUT_OF_RANGE:
        return "out_of_range";
    case COMPANION_SPI_NOR_STM32WBA_NOT_PROBED:
        return "not_probed";
    case COMPANION_SPI_NOR_STM32WBA_ERROR:
    default:
        return "error";
    }
}

companion_spi_nor_stm32wba_status_t companion_spi_nor_stm32wba_probe(
    companion_spi_nor_stm32wba_t *nor,
    companion_spi_nor_stm32wba_info_t *out_info)
{
    if (!configured(nor)) {
        return COMPANION_SPI_NOR_STM32WBA_BAD_PARAM;
    }
    nor->probed = false;
    nor->last_probe_id_transfer_completed = false;
    nor->last_probe_jedec_id = 0u;
    companion_spi_nor_stm32wba_status_t status =
        send_command(nor, NOR_CMD_RELEASE_POWERDOWN);
    if (status != COMPANION_SPI_NOR_STM32WBA_OK) {
        return status;
    }
    nor->config.delay_ms(nor->config.context, 1u);

    uint8_t id[3] = {0u, 0u, 0u};
    status = read_jedec_id(nor, id);
    if (status != COMPANION_SPI_NOR_STM32WBA_OK) {
        return status;
    }
    uint32_t jedec_id = nor->last_probe_jedec_id;
    if (jedec_id == 0u || jedec_id == 0x00FFFFFFu) {
        return COMPANION_SPI_NOR_STM32WBA_ERROR;
    }
    uint32_t size_bytes = size_from_capacity_code(id[2]);
    if (size_bytes == 0u || size_bytes > NOR_MAX_24BIT_SIZE) {
        return COMPANION_SPI_NOR_STM32WBA_UNSUPPORTED;
    }

    uint8_t status1 = 0u;
    status = read_status1(nor, &status1);
    if (status != COMPANION_SPI_NOR_STM32WBA_OK) {
        return status;
    }

    if (id[0] == NOR_MANUFACTURER_XTX) {
        status = normalize_xtx_after_mcu_reset(nor);
        if (status != COMPANION_SPI_NOR_STM32WBA_OK) {
            return status;
        }
        memset(id, 0, sizeof(id));
        status = read_jedec_id(nor, id);
        if (status != COMPANION_SPI_NOR_STM32WBA_OK) {
            return status;
        }
        jedec_id = nor->last_probe_jedec_id;
        if (jedec_id == 0u || jedec_id == 0x00FFFFFFu ||
            id[0] != NOR_MANUFACTURER_XTX ||
            size_from_capacity_code(id[2]) != size_bytes) {
            return COMPANION_SPI_NOR_STM32WBA_ERROR;
        }
        status = read_status1(nor, &status1);
        if (status != COMPANION_SPI_NOR_STM32WBA_OK) {
            return status;
        }
    }

    nor->info.jedec_id = jedec_id;
    nor->info.manufacturer_id = id[0];
    nor->info.memory_type = id[1];
    nor->info.capacity_code = id[2];
    nor->info.status1 = status1;
    nor->info.size_bytes = size_bytes;
    nor->info.page_size = NOR_PAGE_SIZE;
    nor->info.sector_size = NOR_SECTOR_SIZE;
    nor->probed = true;
    if (out_info != NULL) {
        *out_info = nor->info;
    }
    return COMPANION_SPI_NOR_STM32WBA_OK;
}

companion_spi_nor_stm32wba_status_t companion_spi_nor_stm32wba_wait_ready(
    companion_spi_nor_stm32wba_t *nor,
    uint32_t timeout_ms)
{
    if (!configured(nor) || timeout_ms == 0u) {
        return COMPANION_SPI_NOR_STM32WBA_BAD_PARAM;
    }
    uint32_t started_at = nor->config.now_ms(nor->config.context);
    for (;;) {
        uint8_t status1 = 0u;
        companion_spi_nor_stm32wba_status_t status =
            read_status1(nor, &status1);
        if (status != COMPANION_SPI_NOR_STM32WBA_OK) {
            return status;
        }
        if ((status1 & NOR_SR1_WIP) == 0u) {
            return COMPANION_SPI_NOR_STM32WBA_OK;
        }
        uint32_t elapsed =
            nor->config.now_ms(nor->config.context) - started_at;
        if (elapsed >= timeout_ms) {
            return COMPANION_SPI_NOR_STM32WBA_TIMEOUT;
        }
        nor->config.delay_ms(nor->config.context, 1u);
    }
}

companion_spi_nor_stm32wba_status_t companion_spi_nor_stm32wba_read(
    companion_spi_nor_stm32wba_t *nor,
    uint32_t address,
    uint8_t *destination,
    size_t length)
{
    if (!companion_spi_nor_stm32wba_ready(nor)) {
        return configured(nor) ? COMPANION_SPI_NOR_STM32WBA_NOT_PROBED
                               : COMPANION_SPI_NOR_STM32WBA_BAD_PARAM;
    }
    if (!range_valid(nor->info.size_bytes, address, length)) {
        return COMPANION_SPI_NOR_STM32WBA_OUT_OF_RANGE;
    }
    if (length == 0u) {
        return COMPANION_SPI_NOR_STM32WBA_OK;
    }
    if (destination == NULL) {
        return COMPANION_SPI_NOR_STM32WBA_BAD_PARAM;
    }
    return read_addressed(nor, NOR_CMD_READ_DATA, address, destination, length);
}

companion_spi_nor_stm32wba_status_t companion_spi_nor_stm32wba_program(
    companion_spi_nor_stm32wba_t *nor,
    uint32_t address,
    const uint8_t *source,
    size_t length)
{
    if (!companion_spi_nor_stm32wba_ready(nor)) {
        return configured(nor) ? COMPANION_SPI_NOR_STM32WBA_NOT_PROBED
                               : COMPANION_SPI_NOR_STM32WBA_BAD_PARAM;
    }
    if (!range_valid(nor->info.size_bytes, address, length)) {
        return COMPANION_SPI_NOR_STM32WBA_OUT_OF_RANGE;
    }
    if (length == 0u) {
        return COMPANION_SPI_NOR_STM32WBA_OK;
    }
    if (source == NULL) {
        return COMPANION_SPI_NOR_STM32WBA_BAD_PARAM;
    }

    size_t offset = 0u;
    while (offset < length) {
        uint32_t current_address = address + (uint32_t)offset;
        size_t page_remaining =
            (size_t)(NOR_PAGE_SIZE - (current_address % NOR_PAGE_SIZE));
        size_t chunk = length - offset;
        if (chunk > page_remaining) {
            chunk = page_remaining;
        }
        companion_spi_nor_stm32wba_status_t status =
            companion_spi_nor_stm32wba_wait_ready(
                nor,
                nor->config.page_program_timeout_ms);
        if (status != COMPANION_SPI_NOR_STM32WBA_OK) {
            return status;
        }
        status = write_enable(nor);
        if (status != COMPANION_SPI_NOR_STM32WBA_OK) {
            return status;
        }
        status = write_addressed(nor,
                                 NOR_CMD_PAGE_PROGRAM,
                                 current_address,
                                 &source[offset],
                                 chunk);
        if (status != COMPANION_SPI_NOR_STM32WBA_OK) {
            return status;
        }
        status = companion_spi_nor_stm32wba_wait_ready(
            nor,
            nor->config.page_program_timeout_ms);
        if (status != COMPANION_SPI_NOR_STM32WBA_OK) {
            return status;
        }
        offset += chunk;
    }
    return COMPANION_SPI_NOR_STM32WBA_OK;
}

companion_spi_nor_stm32wba_status_t companion_spi_nor_stm32wba_erase_4k(
    companion_spi_nor_stm32wba_t *nor,
    uint32_t address)
{
    if (!companion_spi_nor_stm32wba_ready(nor)) {
        return configured(nor) ? COMPANION_SPI_NOR_STM32WBA_NOT_PROBED
                               : COMPANION_SPI_NOR_STM32WBA_BAD_PARAM;
    }
    if ((address % NOR_SECTOR_SIZE) != 0u) {
        return COMPANION_SPI_NOR_STM32WBA_BAD_PARAM;
    }
    if (!range_valid(nor->info.size_bytes, address, NOR_SECTOR_SIZE)) {
        return COMPANION_SPI_NOR_STM32WBA_OUT_OF_RANGE;
    }
    companion_spi_nor_stm32wba_status_t status =
        companion_spi_nor_stm32wba_wait_ready(
            nor,
            nor->config.sector_erase_timeout_ms);
    if (status != COMPANION_SPI_NOR_STM32WBA_OK) {
        return status;
    }
    status = write_enable(nor);
    if (status != COMPANION_SPI_NOR_STM32WBA_OK) {
        return status;
    }
    status = write_addressed(nor,
                             NOR_CMD_SECTOR_ERASE_4K,
                             address,
                             NULL,
                             0u);
    if (status != COMPANION_SPI_NOR_STM32WBA_OK) {
        return status;
    }
    return companion_spi_nor_stm32wba_wait_ready(
        nor,
        nor->config.sector_erase_timeout_ms);
}

companion_spi_nor_stm32wba_status_t companion_spi_nor_stm32wba_erase_64k(
    companion_spi_nor_stm32wba_t *nor,
    uint32_t address)
{
    if (!companion_spi_nor_stm32wba_ready(nor)) {
        return configured(nor) ? COMPANION_SPI_NOR_STM32WBA_NOT_PROBED
                               : COMPANION_SPI_NOR_STM32WBA_BAD_PARAM;
    }
    if ((address % NOR_BLOCK_SIZE) != 0u) {
        return COMPANION_SPI_NOR_STM32WBA_BAD_PARAM;
    }
    if (!range_valid(nor->info.size_bytes, address, NOR_BLOCK_SIZE)) {
        return COMPANION_SPI_NOR_STM32WBA_OUT_OF_RANGE;
    }
    companion_spi_nor_stm32wba_status_t status =
        companion_spi_nor_stm32wba_wait_ready(
            nor,
            nor->config.sector_erase_timeout_ms);
    if (status != COMPANION_SPI_NOR_STM32WBA_OK) {
        return status;
    }
    status = write_enable(nor);
    if (status != COMPANION_SPI_NOR_STM32WBA_OK) {
        return status;
    }
    status = write_addressed(nor,
                             NOR_CMD_BLOCK_ERASE_64K,
                             address,
                             NULL,
                             0u);
    if (status != COMPANION_SPI_NOR_STM32WBA_OK) {
        return status;
    }
    return companion_spi_nor_stm32wba_wait_ready(
        nor,
        nor->config.sector_erase_timeout_ms);
}

bool companion_spi_nor_stm32wba_partition_init(
    companion_spi_nor_stm32wba_partition_t *partition,
    companion_spi_nor_stm32wba_t *nor,
    uint32_t base_address,
    uint32_t size_bytes)
{
    if (partition == NULL || !companion_spi_nor_stm32wba_ready(nor) ||
        size_bytes == 0u ||
        !range_valid(nor->info.size_bytes, base_address, size_bytes)) {
        return false;
    }
    partition->nor = nor;
    partition->base_address = base_address;
    partition->size_bytes = size_bytes;
    return true;
}

bool companion_spi_nor_stm32wba_partition_read(
    void *context,
    uint32_t partition_offset,
    uint8_t *destination,
    size_t length)
{
    companion_spi_nor_stm32wba_partition_t *partition =
        (companion_spi_nor_stm32wba_partition_t *)context;
    if (partition == NULL || partition->nor == NULL ||
        !range_valid(partition->size_bytes, partition_offset, length)) {
        return false;
    }
    return companion_spi_nor_stm32wba_read(
               partition->nor,
               partition->base_address + partition_offset,
               destination,
               length) == COMPANION_SPI_NOR_STM32WBA_OK;
}

companion_spi_nor_stm32wba_status_t
companion_spi_nor_stm32wba_partition_program(
    companion_spi_nor_stm32wba_partition_t *partition,
    uint32_t partition_offset,
    const uint8_t *source,
    size_t length)
{
    if (partition == NULL || partition->nor == NULL) {
        return COMPANION_SPI_NOR_STM32WBA_BAD_PARAM;
    }
    if (!range_valid(partition->size_bytes, partition_offset, length)) {
        return COMPANION_SPI_NOR_STM32WBA_OUT_OF_RANGE;
    }
    return companion_spi_nor_stm32wba_program(
        partition->nor,
        partition->base_address + partition_offset,
        source,
        length);
}

companion_spi_nor_stm32wba_status_t
companion_spi_nor_stm32wba_partition_erase_4k(
    companion_spi_nor_stm32wba_partition_t *partition,
    uint32_t partition_offset)
{
    if (partition == NULL || partition->nor == NULL) {
        return COMPANION_SPI_NOR_STM32WBA_BAD_PARAM;
    }
    if (!range_valid(partition->size_bytes,
                     partition_offset,
                     NOR_SECTOR_SIZE)) {
        return COMPANION_SPI_NOR_STM32WBA_OUT_OF_RANGE;
    }
    return companion_spi_nor_stm32wba_erase_4k(
        partition->nor,
        partition->base_address + partition_offset);
}
