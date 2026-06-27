#include "comp_qspi_nor.h"

#include <string.h>

#define NOR_CMD_WRITE_ENABLE 0x06u
#define NOR_CMD_READ_STATUS1 0x05u
#define NOR_CMD_READ_STATUS2 0x35u
#define NOR_CMD_READ_JEDEC_ID 0x9Fu
#define NOR_CMD_RELEASE_POWERDOWN 0xABu
#define NOR_CMD_READ_SFDP 0x5Au
#define NOR_CMD_READ_DATA 0x03u
#define NOR_CMD_FAST_READ 0x0Bu
#define NOR_CMD_QUAD_OUT_FAST_READ 0x6Bu
#define NOR_CMD_PAGE_PROGRAM 0x02u
#define NOR_CMD_SECTOR_ERASE_4K 0x20u

#define NOR_SR1_WIP 0x01u
#define NOR_SR1_WEL 0x02u
#define NOR_SR2_QE_COMMON 0x02u

#define NOR_DEFAULT_TIMEOUT_MS 200u
#define NOR_READY_TIMEOUT_MS 5000u
#define NOR_PAGE_SIZE 256u
#define NOR_SECTOR_SIZE 4096u

static comp_qspi_nor_status_t map_hal_status(HAL_StatusTypeDef status)
{
    switch (status) {
    case HAL_OK:
        return COMP_QSPI_NOR_OK;
    case HAL_BUSY:
        return COMP_QSPI_NOR_BUSY;
    case HAL_TIMEOUT:
        return COMP_QSPI_NOR_TIMEOUT;
    case HAL_ERROR:
    default:
        return COMP_QSPI_NOR_ERROR;
    }
}

static void init_command(QSPI_CommandTypeDef *command)
{
    memset(command, 0, sizeof(*command));
    command->AlternateBytes = 0u;
    command->AddressSize = QSPI_ADDRESS_24_BITS;
    command->AlternateBytesSize = QSPI_ALTERNATE_BYTES_8_BITS;
    command->InstructionMode = QSPI_INSTRUCTION_1_LINE;
    command->AddressMode = QSPI_ADDRESS_NONE;
    command->AlternateByteMode = QSPI_ALTERNATE_BYTES_NONE;
    command->DataMode = QSPI_DATA_NONE;
    command->DdrMode = QSPI_DDR_MODE_DISABLE;
    command->SIOOMode = QSPI_SIOO_INST_EVERY_CMD;
}

static comp_qspi_nor_status_t send_no_data(comp_qspi_nor_t *nor, uint8_t instruction)
{
    QSPI_CommandTypeDef command;
    init_command(&command);
    command.Instruction = instruction;

    return map_hal_status(HAL_QSPI_Command(nor->hqspi, &command, nor->timeout_ms));
}

static comp_qspi_nor_status_t read_command(comp_qspi_nor_t *nor,
                                           uint8_t instruction,
                                           uint32_t address_mode,
                                           uint32_t address,
                                           uint32_t data_mode,
                                           uint32_t dummy_cycles,
                                           uint8_t *data,
                                           size_t length)
{
    if (data == NULL || length == 0u) {
        return COMP_QSPI_NOR_BAD_PARAM;
    }

    QSPI_CommandTypeDef command;
    init_command(&command);
    command.Instruction = instruction;
    command.AddressMode = address_mode;
    command.Address = address;
    command.DataMode = data_mode;
    command.DummyCycles = dummy_cycles;
    command.NbData = (uint32_t)length;

    HAL_StatusTypeDef status = HAL_QSPI_Command(nor->hqspi, &command, nor->timeout_ms);
    if (status != HAL_OK) {
        return map_hal_status(status);
    }

    return map_hal_status(HAL_QSPI_Receive(nor->hqspi, data, nor->timeout_ms));
}

static comp_qspi_nor_status_t write_data_command(comp_qspi_nor_t *nor,
                                                 uint8_t instruction,
                                                 uint32_t address,
                                                 uint32_t data_mode,
                                                 const uint8_t *data,
                                                 size_t length)
{
    if (data == NULL || length == 0u || length > NOR_PAGE_SIZE) {
        return COMP_QSPI_NOR_BAD_PARAM;
    }

    QSPI_CommandTypeDef command;
    init_command(&command);
    command.Instruction = instruction;
    command.AddressMode = QSPI_ADDRESS_1_LINE;
    command.Address = address;
    command.DataMode = data_mode;
    command.NbData = (uint32_t)length;

    HAL_StatusTypeDef status = HAL_QSPI_Command(nor->hqspi, &command, nor->timeout_ms);
    if (status != HAL_OK) {
        return map_hal_status(status);
    }

    return map_hal_status(HAL_QSPI_Transmit(nor->hqspi, (uint8_t *)data, nor->timeout_ms));
}

static comp_qspi_nor_status_t address_command(comp_qspi_nor_t *nor,
                                              uint8_t instruction,
                                              uint32_t address)
{
    QSPI_CommandTypeDef command;
    init_command(&command);
    command.Instruction = instruction;
    command.AddressMode = QSPI_ADDRESS_1_LINE;
    command.Address = address;

    return map_hal_status(HAL_QSPI_Command(nor->hqspi, &command, nor->timeout_ms));
}

static comp_qspi_nor_status_t poll_status1(comp_qspi_nor_t *nor,
                                           uint32_t match,
                                           uint32_t mask,
                                           uint32_t timeout_ms)
{
    QSPI_CommandTypeDef command;
    QSPI_AutoPollingTypeDef config;

    init_command(&command);
    command.Instruction = NOR_CMD_READ_STATUS1;
    command.DataMode = QSPI_DATA_1_LINE;

    memset(&config, 0, sizeof(config));
    config.Match = match;
    config.Mask = mask;
    config.MatchMode = QSPI_MATCH_MODE_AND;
    config.StatusBytesSize = 1u;
    config.Interval = 0x10u;
    config.AutomaticStop = QSPI_AUTOMATIC_STOP_ENABLE;

    return map_hal_status(HAL_QSPI_AutoPolling(nor->hqspi, &command, &config, timeout_ms));
}

static comp_qspi_nor_status_t write_enable(comp_qspi_nor_t *nor)
{
    comp_qspi_nor_status_t status = send_no_data(nor, NOR_CMD_WRITE_ENABLE);
    if (status != COMP_QSPI_NOR_OK) {
        return status;
    }
    return poll_status1(nor, NOR_SR1_WEL, NOR_SR1_WEL, nor->timeout_ms);
}

static uint32_t size_from_jedec_capacity(uint8_t capacity_code)
{
    if (capacity_code < 20u || capacity_code >= 31u) {
        return 0u;
    }
    return 1u << capacity_code;
}

void comp_qspi_nor_init(comp_qspi_nor_t *nor, QSPI_HandleTypeDef *hqspi)
{
    if (nor == NULL) {
        return;
    }

    memset(nor, 0, sizeof(*nor));
    nor->hqspi = hqspi;
    nor->timeout_ms = NOR_DEFAULT_TIMEOUT_MS;
    nor->info.page_size = NOR_PAGE_SIZE;
    nor->info.sector_size = NOR_SECTOR_SIZE;
}

const char *comp_qspi_nor_status_name(comp_qspi_nor_status_t status)
{
    switch (status) {
    case COMP_QSPI_NOR_OK:
        return "ok";
    case COMP_QSPI_NOR_BUSY:
        return "busy";
    case COMP_QSPI_NOR_TIMEOUT:
        return "timeout";
    case COMP_QSPI_NOR_UNSUPPORTED:
        return "unsupported";
    case COMP_QSPI_NOR_BAD_PARAM:
        return "bad_param";
    case COMP_QSPI_NOR_ERROR:
    default:
        return "error";
    }
}

comp_qspi_nor_status_t comp_qspi_nor_release_powerdown(comp_qspi_nor_t *nor)
{
    if (nor == NULL || nor->hqspi == NULL) {
        return COMP_QSPI_NOR_BAD_PARAM;
    }

    comp_qspi_nor_status_t status = send_no_data(nor, NOR_CMD_RELEASE_POWERDOWN);
    HAL_Delay(1u);
    return status;
}

comp_qspi_nor_status_t comp_qspi_nor_read_id(comp_qspi_nor_t *nor, uint8_t id[3])
{
    if (nor == NULL || nor->hqspi == NULL || id == NULL) {
        return COMP_QSPI_NOR_BAD_PARAM;
    }

    return read_command(nor,
                        NOR_CMD_READ_JEDEC_ID,
                        QSPI_ADDRESS_NONE,
                        0u,
                        QSPI_DATA_1_LINE,
                        0u,
                        id,
                        3u);
}

comp_qspi_nor_status_t comp_qspi_nor_read_status(comp_qspi_nor_t *nor, uint8_t *status1, uint8_t *status2)
{
    if (nor == NULL || nor->hqspi == NULL || status1 == NULL || status2 == NULL) {
        return COMP_QSPI_NOR_BAD_PARAM;
    }

    comp_qspi_nor_status_t status = read_command(nor,
                                                 NOR_CMD_READ_STATUS1,
                                                 QSPI_ADDRESS_NONE,
                                                 0u,
                                                 QSPI_DATA_1_LINE,
                                                 0u,
                                                 status1,
                                                 1u);
    if (status != COMP_QSPI_NOR_OK) {
        return status;
    }

    return read_command(nor,
                        NOR_CMD_READ_STATUS2,
                        QSPI_ADDRESS_NONE,
                        0u,
                        QSPI_DATA_1_LINE,
                        0u,
                        status2,
                        1u);
}

comp_qspi_nor_status_t comp_qspi_nor_read_sfdp(comp_qspi_nor_t *nor,
                                               uint32_t address,
                                               uint8_t *data,
                                               size_t length)
{
    if (nor == NULL || nor->hqspi == NULL) {
        return COMP_QSPI_NOR_BAD_PARAM;
    }

    return read_command(nor,
                        NOR_CMD_READ_SFDP,
                        QSPI_ADDRESS_1_LINE,
                        address,
                        QSPI_DATA_1_LINE,
                        8u,
                        data,
                        length);
}

comp_qspi_nor_status_t comp_qspi_nor_probe(comp_qspi_nor_t *nor, comp_qspi_nor_info_t *out_info)
{
    if (nor == NULL || nor->hqspi == NULL) {
        return COMP_QSPI_NOR_BAD_PARAM;
    }

    uint8_t id[3] = {0};
    uint8_t status1 = 0u;
    uint8_t status2 = 0u;
    uint8_t sfdp_signature[4] = {0};

    (void)comp_qspi_nor_release_powerdown(nor);

    comp_qspi_nor_status_t status = comp_qspi_nor_read_id(nor, id);
    if (status != COMP_QSPI_NOR_OK) {
        return status;
    }

    uint32_t jedec = ((uint32_t)id[0] << 16) | ((uint32_t)id[1] << 8) | id[2];
    if (jedec == 0u || jedec == 0xFFFFFFu) {
        return COMP_QSPI_NOR_ERROR;
    }

    status = comp_qspi_nor_read_status(nor, &status1, &status2);
    if (status != COMP_QSPI_NOR_OK) {
        return status;
    }

    comp_qspi_nor_status_t sfdp_status = comp_qspi_nor_read_sfdp(nor, 0u, sfdp_signature, sizeof(sfdp_signature));
    bool sfdp_present = sfdp_status == COMP_QSPI_NOR_OK &&
                        sfdp_signature[0] == 'S' &&
                        sfdp_signature[1] == 'F' &&
                        sfdp_signature[2] == 'D' &&
                        sfdp_signature[3] == 'P';

    comp_qspi_nor_info_t info;
    memset(&info, 0, sizeof(info));
    info.jedec_id = jedec;
    info.manufacturer_id = id[0];
    info.memory_type = id[1];
    info.capacity_code = id[2];
    info.status1 = status1;
    info.status2 = status2;
    info.size_bytes = size_from_jedec_capacity(id[2]);
    info.sector_size = NOR_SECTOR_SIZE;
    info.page_size = NOR_PAGE_SIZE;
    info.quad_enabled = (status2 & NOR_SR2_QE_COMMON) != 0u;
    info.sfdp_present = sfdp_present;

    nor->info = info;
    nor->prefer_quad_read = false;

    if (out_info != NULL) {
        *out_info = info;
    }

    return COMP_QSPI_NOR_OK;
}

comp_qspi_nor_status_t comp_qspi_nor_wait_ready(comp_qspi_nor_t *nor, uint32_t timeout_ms)
{
    if (nor == NULL || nor->hqspi == NULL) {
        return COMP_QSPI_NOR_BAD_PARAM;
    }
    return poll_status1(nor, 0u, NOR_SR1_WIP, timeout_ms);
}

comp_qspi_nor_status_t comp_qspi_nor_read(comp_qspi_nor_t *nor,
                                          uint32_t address,
                                          uint8_t *data,
                                          size_t length)
{
    if (nor == NULL || nor->hqspi == NULL || data == NULL) {
        return COMP_QSPI_NOR_BAD_PARAM;
    }
    if (length == 0u) {
        return COMP_QSPI_NOR_OK;
    }

    if (nor->prefer_quad_read) {
        comp_qspi_nor_status_t status = read_command(nor,
                                                     NOR_CMD_QUAD_OUT_FAST_READ,
                                                     QSPI_ADDRESS_1_LINE,
                                                     address,
                                                     QSPI_DATA_4_LINES,
                                                     8u,
                                                     data,
                                                     length);
        if (status == COMP_QSPI_NOR_OK) {
            return status;
        }
    }

    return read_command(nor,
                        NOR_CMD_READ_DATA,
                        QSPI_ADDRESS_1_LINE,
                        address,
                        QSPI_DATA_1_LINE,
                        0u,
                        data,
                        length);
}

comp_qspi_nor_status_t comp_qspi_nor_write(comp_qspi_nor_t *nor,
                                           uint32_t address,
                                           const uint8_t *data,
                                           size_t length)
{
    if (nor == NULL || nor->hqspi == NULL || data == NULL) {
        return COMP_QSPI_NOR_BAD_PARAM;
    }

    size_t offset = 0u;
    while (offset < length) {
        uint32_t page_offset = (address + (uint32_t)offset) % NOR_PAGE_SIZE;
        size_t chunk = NOR_PAGE_SIZE - page_offset;
        if (chunk > (length - offset)) {
            chunk = length - offset;
        }

        comp_qspi_nor_status_t status = comp_qspi_nor_wait_ready(nor, NOR_READY_TIMEOUT_MS);
        if (status != COMP_QSPI_NOR_OK) {
            return status;
        }

        status = write_enable(nor);
        if (status != COMP_QSPI_NOR_OK) {
            return status;
        }

        status = write_data_command(nor,
                                    NOR_CMD_PAGE_PROGRAM,
                                    address + (uint32_t)offset,
                                    QSPI_DATA_1_LINE,
                                    &data[offset],
                                    chunk);
        if (status != COMP_QSPI_NOR_OK) {
            return status;
        }

        status = comp_qspi_nor_wait_ready(nor, NOR_READY_TIMEOUT_MS);
        if (status != COMP_QSPI_NOR_OK) {
            return status;
        }

        offset += chunk;
    }

    return COMP_QSPI_NOR_OK;
}

comp_qspi_nor_status_t comp_qspi_nor_erase_4k(comp_qspi_nor_t *nor, uint32_t address)
{
    if (nor == NULL || nor->hqspi == NULL) {
        return COMP_QSPI_NOR_BAD_PARAM;
    }
    if ((address % NOR_SECTOR_SIZE) != 0u) {
        return COMP_QSPI_NOR_BAD_PARAM;
    }

    comp_qspi_nor_status_t status = comp_qspi_nor_wait_ready(nor, NOR_READY_TIMEOUT_MS);
    if (status != COMP_QSPI_NOR_OK) {
        return status;
    }

    status = write_enable(nor);
    if (status != COMP_QSPI_NOR_OK) {
        return status;
    }

    status = address_command(nor, NOR_CMD_SECTOR_ERASE_4K, address);
    if (status != COMP_QSPI_NOR_OK) {
        return status;
    }

    return comp_qspi_nor_wait_ready(nor, NOR_READY_TIMEOUT_MS);
}
