#include "spi_nor_stm32wba.h"
#include "companion_cpu_stage.h"

#include <string.h>

#define NOR_CMD_WRITE_ENABLE 0x06u
#define NOR_CMD_READ_STATUS1 0x05u
#define NOR_CMD_READ_STATUS2 0x35u
#define NOR_CMD_READ_SFDP 0x5Au
#define NOR_CMD_ERASE_SUSPEND 0x75u
#define NOR_CMD_ERASE_RESUME 0x7Au
#define NOR_CMD_READ_JEDEC_ID 0x9Fu
#define NOR_CMD_RELEASE_POWERDOWN 0xABu
#define NOR_CMD_ENABLE_RESET 0x66u
#define NOR_CMD_RESET_DEVICE 0x99u
#define NOR_CMD_READ_DATA 0x03u
#define NOR_CMD_PAGE_PROGRAM 0x02u
#define NOR_CMD_SECTOR_ERASE_4K 0x20u
#define NOR_CMD_BLOCK_ERASE_32K 0x52u
#define NOR_CMD_BLOCK_ERASE_64K 0xD8u

#define NOR_SR1_WIP 0x01u
#define NOR_SR1_WEL 0x02u
#define NOR_SR2_SUS 0x80u
#define NOR_ERASE_RUNNING 0u
#define NOR_ERASE_SUSPEND_WAIT 1u
#define NOR_ERASE_SUSPENDED 2u
#define NOR_ERASE_RESUME_WAIT 3u
#define NOR_ERASE_COMPLETE 4u
#define NOR_WINBOND_128_18V_ID 0xEF6018u

#define NOR_MANUFACTURER_XTX 0x0Bu
#define NOR_XTX_RESET_DELAY_MS 1u

#define NOR_DEFAULT_TRANSFER_TIMEOUT_MS 200u
#define NOR_DEFAULT_PROGRAM_TIMEOUT_MS 5000u
#define NOR_DEFAULT_ERASE_TIMEOUT_MS 30000u
#define NOR_PAGE_SIZE 256u
#define NOR_SECTOR_SIZE 4096u
#define NOR_BLOCK_SIZE 65536u
#define NOR_MAX_24BIT_SIZE 0x01000000u

/* rawpcm8 (2026-08-06, Drops=0 mandate): for the first SPIN_BUDGET_MS of a
 * wait, busy-spin the status poll (no vTaskDelay) so NOR page programs — which
 * clear WIP in <~1 ms — complete without yielding the caller. Previously every
 * poll did delay_ms(1)=vTaskDelay(1); on the WB55 the audio encode task is
 * prio 5 alongside rec/display/svc, so each "1 ms" yield cost ~10-20 ms
 * wall-clock as peer tasks ran, ballooning a 4 KB drain (16 page programs) to
 * ~343 ms. That is < 16 KB/s real-time capture -> PCM ring overflow (drops) +
 * SAI DMA starved (overruns). Waits longer than the budget (sector/block erase,
 * >= tens of ms) still fall back to a yielding delay so an erase never hog the
 * CPU/watchdog. */
/* 2026-08-06 (Drops=0 mandate) — DISPROVEN, reverted 5u -> 2u. Raising this 2->5
 * did NOT reduce drain_max_ms (stayed ~296 ms) on a real board-mic codec=2 capture
 * (capture_drain.txt id=3: drops=14, drain_max_ms=296, identical to the spin=2
 * baseline id=2 drops=13). That disproves the "per-page vTaskDelay(1) yield is the
 * stall" theory: the residual flush stall is genuine WIP > 5 ms per page on this
 * XTX part during a high-water stage flush, so no spin budget <= a few ms catches
 * it — 16 pages ~= 296 ms regardless. The actual drops fix is elsewhere: the
 * high-water flush page_budget was halved 16->8 in main.c
 * (recording_flash_append_bytes) so each flush ~= 148 ms < the 280 ms (28-slot) PCM
 * ring, regardless of per-page WIP time. Spin value left at the original 2. */
#define NOR_WAIT_READY_SPIN_BUDGET_MS 2u

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

/* On the qualified WBA55/1.8V128Mbit Winbond path, command and returned
 * status are one sixteen-clock exchange under the same CS. The first RX
 * byte belongs to the command clocks and is discarded. This removes a
 * second HAL transaction, not a WIP/SUS poll or an ownership check.
 * Other ports/parts and the initial unidentified probe keep their path. */
static companion_spi_nor_stm32wba_status_t read_status_byte(
    companion_spi_nor_stm32wba_t *nor,uint8_t command,uint8_t *value)
{
    if(value==NULL)return COMPANION_SPI_NOR_STM32WBA_BAD_PARAM;
    if(nor==NULL || nor->config.target!=COMPANION_SPI_NOR_STM32WBA_TARGET_WBA55 ||
       nor->info.jedec_id!=NOR_WINBOND_128_18V_ID)
        return read_command(nor,command,value,1u);
    uint8_t tx[2]={command,0xFFu},rx[2];
    companion_spi_nor_stm32wba_status_t status=begin_transaction(nor);
    if(status!=COMPANION_SPI_NOR_STM32WBA_OK)return status;
    status=transfer_bytes(nor,tx,rx,sizeof(tx));
    if(status==COMPANION_SPI_NOR_STM32WBA_OK)*value=rx[1];
    return finish_transaction(nor,status);
}

static companion_spi_nor_stm32wba_status_t read_status1(
    companion_spi_nor_stm32wba_t *nor,
    uint8_t *status1)
{
    return read_status_byte(nor, NOR_CMD_READ_STATUS1, status1);
}

static companion_spi_nor_stm32wba_status_t read_erase_status(
    companion_spi_nor_stm32wba_t *nor, uint8_t *sr1, uint8_t *sr2)
{
    companion_spi_nor_stm32wba_status_t s = read_status1(nor, sr1);
    if (s == COMPANION_SPI_NOR_STM32WBA_OK)
        s = read_status_byte(nor, NOR_CMD_READ_STATUS2, sr2);
    if (s == COMPANION_SPI_NOR_STM32WBA_OK) nor->info.status1 = *sr1;
    return s;
}

static uint32_t little32(const uint8_t *p)
{
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8u) |
           ((uint32_t)p[2] << 16u) | ((uint32_t)p[3] << 24u);
}

static companion_spi_nor_stm32wba_status_t read_sfdp(
    companion_spi_nor_stm32wba_t *nor, uint32_t address, uint8_t *out, size_t n)
{
    uint8_t header[5];
    encode_address(header, NOR_CMD_READ_SFDP, address);
    header[4] = 0u; /* SFDP always uses three address bytes and eight dummy clocks. */
    companion_spi_nor_stm32wba_status_t s = begin_transaction(nor);
    if (s != COMPANION_SPI_NOR_STM32WBA_OK) return s;
    s = transfer_bytes(nor, header, NULL, sizeof(header));
    if (s == COMPANION_SPI_NOR_STM32WBA_OK) s = transfer_bytes(nor, NULL, out, n);
    return finish_transaction(nor, s);
}

static bool overlaps_erase(const companion_spi_nor_stm32wba_t *nor,
                           uint32_t address, size_t length)
{
    return length != 0u && address < nor->erase_address + nor->erase_bytes &&
           nor->erase_address < address + (uint32_t)length;
}

static bool range_valid(uint32_t size_bytes,uint32_t offset,size_t length);

bool companion_spi_nor_stm32wba_erase_access_ready(const companion_spi_nor_stm32wba_t *nor,
    uint32_t address,size_t length)
{
    if(!nor||!nor->probed||!range_valid(nor->info.size_bytes,address,length))return false;
    if(!nor->erase_active)return true;
    return !nor->erase_command_failed&&!overlaps_erase(nor,address,length)&&
        (nor->erase_phase==NOR_ERASE_SUSPENDED||nor->erase_phase==NOR_ERASE_COMPLETE);
}

/* The owner stays active even if suspension observes natural completion.
 * Its worker must receive that completion once; an unrelated read/program
 * must not release it and cause erase_step to erase the same range again. */
static companion_spi_nor_stm32wba_status_t access_during_erase(
    companion_spi_nor_stm32wba_t *nor, uint32_t address, size_t length)
{
    if (!nor->erase_active) return COMPANION_SPI_NOR_STM32WBA_OK;
    if (overlaps_erase(nor, address, length)) return COMPANION_SPI_NOR_STM32WBA_PENDING;
    if (nor->erase_phase == NOR_ERASE_COMPLETE && !nor->erase_command_failed)
        return COMPANION_SPI_NOR_STM32WBA_OK;
    if (nor->erase_phase != NOR_ERASE_SUSPENDED)
        return COMPANION_SPI_NOR_STM32WBA_PENDING;
    uint8_t sr1 = 0u, sr2 = 0u;
    companion_spi_nor_stm32wba_status_t s = read_erase_status(nor, &sr1, &sr2);
    if (s != COMPANION_SPI_NOR_STM32WBA_OK) return s;
    /* A prior page program may have failed/timed out while the erase was
     * suspended. Never read through that BUSY or issue a second program. */
    return (sr1 & NOR_SR1_WIP) == 0u && (sr2 & NOR_SR2_SUS) != 0u
        ? COMPANION_SPI_NOR_STM32WBA_OK : COMPANION_SPI_NOR_STM32WBA_PENDING;
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

companion_spi_nor_stm32wba_status_t companion_spi_nor_stm32wba_recovery_observe(
    companion_spi_nor_stm32wba_t *nor)
{
    if (!companion_spi_nor_stm32wba_ready(nor))
        return configured(nor) ? COMPANION_SPI_NOR_STM32WBA_NOT_PROBED
                               : COMPANION_SPI_NOR_STM32WBA_BAD_PARAM;
    if (nor->info.jedec_id != NOR_WINBOND_128_18V_ID || !nor->erase_suspend_supported)
        return COMPANION_SPI_NOR_STM32WBA_UNSUPPORTED;
    if (nor->erase_active) return COMPANION_SPI_NOR_STM32WBA_PENDING;
    uint8_t id[3], sr1, sr2;
    companion_spi_nor_stm32wba_status_t r = read_command(nor, NOR_CMD_READ_JEDEC_ID, id, sizeof(id));
    if (r != COMPANION_SPI_NOR_STM32WBA_OK) return r;
    uint32_t observed = ((uint32_t)id[0] << 16u) | ((uint32_t)id[1] << 8u) | id[2];
    if (observed != nor->info.jedec_id) return COMPANION_SPI_NOR_STM32WBA_ERROR;
    r = read_status1(nor, &sr1);
    if (r != COMPANION_SPI_NOR_STM32WBA_OK) return r;
    if (sr1 & (NOR_SR1_WIP | NOR_SR1_WEL)) return COMPANION_SPI_NOR_STM32WBA_PENDING;
    r = read_status_byte(nor, NOR_CMD_READ_STATUS2, &sr2);
    if (r != COMPANION_SPI_NOR_STM32WBA_OK) return r;
    if (sr2 & NOR_SR2_SUS) return COMPANION_SPI_NOR_STM32WBA_PENDING;
    /* Status registers are separate transactions. Recheck BUSY and WEL after
     * SR2, even though exclusivity is still a caller obligation. */
    r = read_status1(nor, &sr1);
    if (r != COMPANION_SPI_NOR_STM32WBA_OK) return r;
    return (sr1 & (NOR_SR1_WIP | NOR_SR1_WEL)) ?
        COMPANION_SPI_NOR_STM32WBA_PENDING : COMPANION_SPI_NOR_STM32WBA_OK;
}

const char *companion_spi_nor_stm32wba_status_name(
    companion_spi_nor_stm32wba_status_t status)
{
    switch (status) {
    case COMPANION_SPI_NOR_STM32WBA_OK:
        return "ok";
    case COMPANION_SPI_NOR_STM32WBA_PENDING:
        return "pending";
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
    if (nor->erase_active) return COMPANION_SPI_NOR_STM32WBA_PENDING;
    nor->probed = false;
    nor->erase_suspend_supported = false;
    nor->info.erase_32k_supported = false;
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
    if (jedec_id == NOR_WINBOND_128_18V_ID) {
        status = companion_spi_nor_stm32wba_probe_erase_suspend(nor);
        if (status != COMPANION_SPI_NOR_STM32WBA_OK &&
            status != COMPANION_SPI_NOR_STM32WBA_UNSUPPORTED) {
            nor->probed = false;
            return status;
        }
    }
    if (out_info != NULL) {
        *out_info = nor->info;
    }
    return COMPANION_SPI_NOR_STM32WBA_OK;
}

companion_spi_nor_stm32wba_status_t companion_spi_nor_stm32wba_probe_erase_suspend(
    companion_spi_nor_stm32wba_t *nor)
{
    if (!companion_spi_nor_stm32wba_ready(nor))
        return configured(nor) ? COMPANION_SPI_NOR_STM32WBA_NOT_PROBED
                               : COMPANION_SPI_NOR_STM32WBA_BAD_PARAM;
    if (nor->erase_active) return COMPANION_SPI_NOR_STM32WBA_PENDING;
    nor->erase_suspend_supported = false;
    nor->suspend_wait_ms = 0u; nor->resume_guard_ms = 0u;
    nor->info.sfdp_suspend_parameters = 0u; nor->info.sfdp_suspend_instructions = 0u;
    nor->info.sfdp_bfp_dwords = 0u;
    nor->info.erase_32k_supported = false;
    if (nor->info.jedec_id != NOR_WINBOND_128_18V_ID)
        return COMPANION_SPI_NOR_STM32WBA_UNSUPPORTED;
    uint8_t sr1 = 0u, sr2 = 0u;
    companion_spi_nor_stm32wba_status_t s = read_erase_status(nor, &sr1, &sr2);
    if (s != COMPANION_SPI_NOR_STM32WBA_OK) return s;
    const bool interrupted = (sr2 & NOR_SR2_SUS) != 0u;
    /* Unqualified clean media may use the exclusive path. An unknown paused
     * operation cannot: mounting and reading its target would be unsafe. */
    const companion_spi_nor_stm32wba_status_t unsupported = interrupted
        ? COMPANION_SPI_NOR_STM32WBA_ERROR : COMPANION_SPI_NOR_STM32WBA_UNSUPPORTED;
    if ((sr1 & NOR_SR1_WIP) != 0u) {
        s = companion_spi_nor_stm32wba_wait_ready(nor,
            interrupted ? nor->config.page_program_timeout_ms : nor->config.sector_erase_timeout_ms);
        if (s != COMPANION_SPI_NOR_STM32WBA_OK) return s;
    }
    uint8_t header[16], bfp[52];
    s = read_sfdp(nor, 0u, header, 8u);
    if (s != COMPANION_SPI_NOR_STM32WBA_OK) return s;
    if (memcmp(header, "SFDP", 4u) != 0 || header[5] != 1u || header[6] > 7u)
        return unsupported;
    const uint8_t parameters = (uint8_t)(header[6] + 1u);
    bool found = false;
    for (uint8_t i = 0u; i < parameters; ++i) {
        s = read_sfdp(nor, 8u + (uint32_t)i * 8u, header, 8u);
        if (s != COMPANION_SPI_NOR_STM32WBA_OK) return s;
        if (header[0] == 0u && header[7] == 0xFFu && header[2] == 1u) {
            nor->info.sfdp_bfp_dwords = header[3];found = true; break;
        }
    }
    if (!found || header[3] < 13u) return unsupported;
    const uint32_t address = (uint32_t)header[4] | ((uint32_t)header[5] << 8u) |
                             ((uint32_t)header[6] << 16u);
    if (address > NOR_MAX_24BIT_SIZE - sizeof(bfp) || address % 4u != 0u)
        return unsupported;
    s = read_sfdp(nor, address, bfp, sizeof(bfp));
    if (s != COMPANION_SPI_NOR_STM32WBA_OK) return s;
    const uint32_t density = little32(bfp + 4u), dw11 = little32(bfp + 40u);
    const uint32_t dw12 = little32(bfp + 44u), dw13 = little32(bfp + 48u);
    nor->info.sfdp_suspend_parameters = dw12; nor->info.sfdp_suspend_instructions = dw13;
    bool sector = false, block = false, half_block = false;
    for (size_t i = 28u; i < 36u; i += 2u) {
        if (bfp[i] == 12u && bfp[i + 1u] == NOR_CMD_SECTOR_ERASE_4K) sector = true;
        if (bfp[i] == 16u && bfp[i + 1u] == NOR_CMD_BLOCK_ERASE_64K) block = true;
        if (bfp[i] == 15u && bfp[i + 1u] == NOR_CMD_BLOCK_ERASE_32K) half_block = true;
    }
    /* JESD216 DWORD12 bit31=0 means supported (it is NOT a positive flag).
     * Restriction nibble E permits other-sector reads/programs, forbids new
     * erases, and says those restrictions are sufficient. More restrictive or
     * unknown definitions stay on the exclusive path; no universal 75/7A guess. */
    if (density != nor->info.size_bytes * 8u - 1u ||
        ((dw11 >> 4u) & 15u) != 8u || !sector || !block ||
        (dw12 & UINT32_C(0x80000000)) != 0u || ((dw12 >> 4u) & 15u) != 14u ||
        (uint8_t)(dw13 >> 24u) != NOR_CMD_ERASE_SUSPEND ||
        (uint8_t)(dw13 >> 16u) != NOR_CMD_ERASE_RESUME)
        return unsupported;
    const uint32_t units_ns[4] = {128u, 1000u, 8000u, 64000u};
    const uint32_t latency_ns = units_ns[(dw12 >> 29u) & 3u] *
                                (((dw12 >> 24u) & 31u) + 1u);
    nor->suspend_wait_ms = (uint8_t)((latency_ns + 999999u) / 1000000u + 1u);
    nor->resume_guard_ms = (uint8_t)(((((dw12 >> 20u) & 15u) + 1u) * 64u + 999u) /
                                    1000u + 1u);
    s = read_erase_status(nor, &sr1, &sr2);
    if (s != COMPANION_SPI_NOR_STM32WBA_OK) return s;
    if ((sr2 & NOR_SR2_SUS) != 0u) {
        /* An MCU reset does not reset NOR. Finish the previously suspended
         * operation before mounting catalogs; never silently discard it using
         * 66/99. This only runs at startup, with sampling not started. */
        s = companion_spi_nor_stm32wba_wait_ready(nor, nor->config.page_program_timeout_ms);
        if (s != COMPANION_SPI_NOR_STM32WBA_OK) return s;
        s = send_command(nor, NOR_CMD_ERASE_RESUME);
        if (s != COMPANION_SPI_NOR_STM32WBA_OK) return s;
        nor->config.delay_ms(nor->config.context, nor->resume_guard_ms);
        s = companion_spi_nor_stm32wba_wait_ready(nor, nor->config.sector_erase_timeout_ms);
        if (s != COMPANION_SPI_NOR_STM32WBA_OK) return s;
        s = read_erase_status(nor, &sr1, &sr2);
        if (s != COMPANION_SPI_NOR_STM32WBA_OK) return s;
        if ((sr2 & NOR_SR2_SUS) != 0u) return COMPANION_SPI_NOR_STM32WBA_ERROR;
    }
    nor->erase_suspend_supported = true;
    nor->info.erase_32k_supported = half_block;
    return COMPANION_SPI_NOR_STM32WBA_OK;
}

companion_spi_nor_stm32wba_status_t companion_spi_nor_stm32wba_wait_ready(
    companion_spi_nor_stm32wba_t *nor,
    uint32_t timeout_ms)
{
    if (nor && nor->erase_active && nor->erase_phase != NOR_ERASE_SUSPENDED &&
        nor->erase_phase != NOR_ERASE_COMPLETE)
        return COMPANION_SPI_NOR_STM32WBA_PENDING;
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
        /* A normal page program can finish inside the initial spin budget,
         * so delay_ms alone cannot service its owner's cooperative work.
         * The status transaction has fully deasserted CS at this point. */
        if (nor->config.wait_progress) {
            nor->config.wait_progress(nor->config.context);
        }
        if (elapsed < NOR_WAIT_READY_SPIN_BUDGET_MS) {
            /* Busy-spin: jump back to the loop top and re-read status without
             * yielding. now_ms is 1 ms-resolution, so this tight-loops
             * read_status1 (~us each) until WIP clears or the tick advances. */
            continue;
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
    companion_spi_nor_stm32wba_status_t access = access_during_erase(nor, address, length);
    if (access != COMPANION_SPI_NOR_STM32WBA_OK) return access;
    if (length == 0u) {
        return COMPANION_SPI_NOR_STM32WBA_OK;
    }
    if (destination == NULL) {
        return COMPANION_SPI_NOR_STM32WBA_BAD_PARAM;
    }
    return read_addressed(nor, NOR_CMD_READ_DATA, address, destination, length);
}

/* Status probes for a suspended-erase radio read share its tick budget.
 * An incomplete/failed status probe is never marked as a released payload
 * failure: the erase owner keeps control and the existing fault path applies. */
static companion_spi_nor_stm32wba_status_t transient_status_bounded(
    companion_spi_nor_stm32wba_t *nor,uint8_t command,uint8_t *value,
    uint32_t started,uint32_t budget)
{
    uint32_t elapsed=nor->config.now_ms(nor->config.context)-started;
    if(elapsed>=budget)return COMPANION_SPI_NOR_STM32WBA_PENDING;
    companion_spi_nor_stm32wba_status_t result=begin_transaction(nor);
    if(result!=COMPANION_SPI_NOR_STM32WBA_OK)return result;
    elapsed=nor->config.now_ms(nor->config.context)-started;
    if(elapsed>=budget)return nor->config.chip_select(nor->config.context,false)?
        COMPANION_SPI_NOR_STM32WBA_PENDING:COMPANION_SPI_NOR_STM32WBA_ERROR;
    const uint8_t tx[2]={command,0xffu};uint8_t rx[2]={0u,0u};
    result=nor->config.transfer(nor->config.context,tx,rx,sizeof(tx),budget-elapsed)?
        COMPANION_SPI_NOR_STM32WBA_OK:COMPANION_SPI_NOR_STM32WBA_ERROR;
    result=finish_transaction(nor,result);
    if(result==COMPANION_SPI_NOR_STM32WBA_OK)*value=rx[1];
    return result;
}

companion_spi_nor_stm32wba_status_t companion_spi_nor_stm32wba_read_transient(
    companion_spi_nor_stm32wba_t *nor,uint32_t address,uint8_t *destination,
    size_t length,bool *released_read_failure)
{
    if(!released_read_failure)return COMPANION_SPI_NOR_STM32WBA_BAD_PARAM;
    *released_read_failure=false;
    if(!companion_spi_nor_stm32wba_ready(nor))return COMPANION_SPI_NOR_STM32WBA_NOT_PROBED;
    if(!destination||!length)return COMPANION_SPI_NOR_STM32WBA_BAD_PARAM;
    if(!range_valid(nor->info.size_bytes,address,length))return COMPANION_SPI_NOR_STM32WBA_OUT_OF_RANGE;
    /* A single budget covers both status transactions and the data read.
     * Tick/interrupt latency means this is not a hard wall-clock guarantee. */
    const bool bounded=nor->config.target==COMPANION_SPI_NOR_STM32WBA_TARGET_WBA55 &&
        nor->info.jedec_id==NOR_WINBOND_128_18V_ID && length<=NOR_PAGE_SIZE &&
        nor->config.transfer_timeout_ms>0u;
    const uint32_t budget=bounded && nor->config.transfer_timeout_ms>8u ?
        8u : nor->config.transfer_timeout_ms;
    const uint32_t started=bounded?nor->config.now_ms(nor->config.context):0u;
    if(nor->erase_active) {
        if(!bounded||nor->erase_command_failed||overlaps_erase(nor,address,length))
            return COMPANION_SPI_NOR_STM32WBA_PENDING;
        if(nor->erase_phase==NOR_ERASE_SUSPENDED) {
            uint8_t sr1=0u,sr2=0u;
            companion_spi_nor_stm32wba_status_t check=transient_status_bounded(nor,NOR_CMD_READ_STATUS1,&sr1,started,budget);
            if(check!=COMPANION_SPI_NOR_STM32WBA_OK)return check;
            check=transient_status_bounded(nor,NOR_CMD_READ_STATUS2,&sr2,started,budget);
            if(check!=COMPANION_SPI_NOR_STM32WBA_OK)return check;
            nor->info.status1=sr1;
            if((sr1&NOR_SR1_WIP)!=0u||(sr2&NOR_SR2_SUS)==0u)
                return COMPANION_SPI_NOR_STM32WBA_PENDING;
        } else if(nor->erase_phase!=NOR_ERASE_COMPLETE) {
            return COMPANION_SPI_NOR_STM32WBA_PENDING;
        }
    }
    if(bounded && nor->config.now_ms(nor->config.context)-started>=budget)
        return COMPANION_SPI_NOR_STM32WBA_PENDING;
    uint8_t header[4];encode_address(header,NOR_CMD_READ_DATA,address);
    companion_spi_nor_stm32wba_status_t result=begin_transaction(nor);
    if(result!=COMPANION_SPI_NOR_STM32WBA_OK)return result;
    uint32_t header_elapsed=bounded?nor->config.now_ms(nor->config.context)-started:0u;
    if(bounded && header_elapsed>=budget)
        return nor->config.chip_select(nor->config.context,false)?
            COMPANION_SPI_NOR_STM32WBA_PENDING:COMPANION_SPI_NOR_STM32WBA_ERROR;
    if(bounded)result=nor->config.transfer(nor->config.context,header,NULL,sizeof(header),budget-header_elapsed)?
        COMPANION_SPI_NOR_STM32WBA_OK:COMPANION_SPI_NOR_STM32WBA_ERROR;
    else result=transfer_bytes(nor,header,NULL,sizeof(header));
    const bool read_header_complete=result==COMPANION_SPI_NOR_STM32WBA_OK;
    if(read_header_complete) {
        if(bounded) {
            const uint32_t elapsed=nor->config.now_ms(nor->config.context)-started;
            if(elapsed>=budget)result=COMPANION_SPI_NOR_STM32WBA_ERROR;
            else result=nor->config.transfer(nor->config.context,NULL,destination,length,budget-elapsed)?
                COMPANION_SPI_NOR_STM32WBA_OK:COMPANION_SPI_NOR_STM32WBA_ERROR;
        } else result=transfer_bytes(nor,NULL,destination,length);
    }
    bool released=nor->config.chip_select(nor->config.context,false);
    if(!released)return COMPANION_SPI_NOR_STM32WBA_ERROR;
    if(read_header_complete&&result!=COMPANION_SPI_NOR_STM32WBA_OK)*released_read_failure=true;
    return result;
}

static companion_spi_nor_stm32wba_status_t program_page_body(
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
    companion_spi_nor_stm32wba_status_t access = access_during_erase(nor, address, length);
    if (access != COMPANION_SPI_NOR_STM32WBA_OK) return access;
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
    if (nor->erase_active) return COMPANION_SPI_NOR_STM32WBA_PENDING;
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
    if (nor->erase_active) return COMPANION_SPI_NOR_STM32WBA_PENDING;
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

bool companion_spi_nor_stm32wba_erase_is_suspended(
    const companion_spi_nor_stm32wba_t *nor)
{
    return nor && nor->erase_active && nor->erase_phase == NOR_ERASE_SUSPENDED;
}

/* Foreground capture has a shared budget for the erase owner's status and
 * suspend/resume qualification. PENDING before a command means no command
 * was issued; an attempted command failure remains ERROR and keeps ownership.
 * This is a HAL-tick bound, not a physical wall-clock guarantee. */
companion_spi_nor_stm32wba_status_t companion_spi_nor_stm32wba_erase_suspend_step_bounded(
    companion_spi_nor_stm32wba_t *nor, uint32_t budget)
{
    if (!companion_spi_nor_stm32wba_ready(nor) || !budget)
        return COMPANION_SPI_NOR_STM32WBA_BAD_PARAM;
    if (!nor->erase_active) return COMPANION_SPI_NOR_STM32WBA_OK;
    if (!nor->erase_suspend_supported) return COMPANION_SPI_NOR_STM32WBA_UNSUPPORTED;
    if (nor->erase_command_failed) return COMPANION_SPI_NOR_STM32WBA_ERROR;
    if (nor->erase_phase == NOR_ERASE_COMPLETE) return COMPANION_SPI_NOR_STM32WBA_OK;
    if (nor->config.target != COMPANION_SPI_NOR_STM32WBA_TARGET_WBA55 ||
        nor->info.jedec_id != NOR_WINBOND_128_18V_ID)
        return companion_spi_nor_stm32wba_erase_suspend_step(nor);
    if (budget > nor->config.transfer_timeout_ms) budget = nor->config.transfer_timeout_ms;
    if (!budget) return COMPANION_SPI_NOR_STM32WBA_BAD_PARAM;
    uint32_t start = nor->config.now_ms(nor->config.context);
    if ((nor->erase_phase == NOR_ERASE_RUNNING && start - nor->erase_run_since_ms < nor->resume_guard_ms) ||
        (nor->erase_phase == NOR_ERASE_SUSPEND_WAIT && start - nor->erase_phase_started_ms < nor->suspend_wait_ms) ||
        (nor->erase_phase == NOR_ERASE_RESUME_WAIT && start - nor->erase_phase_started_ms < nor->resume_guard_ms))
        return COMPANION_SPI_NOR_STM32WBA_PENDING;
    uint8_t sr1=0u, sr2=0u;
    companion_spi_nor_stm32wba_status_t result = transient_status_bounded(nor,NOR_CMD_READ_STATUS1,&sr1,start,budget);
    if (result != COMPANION_SPI_NOR_STM32WBA_OK) return result;
    result = transient_status_bounded(nor,NOR_CMD_READ_STATUS2,&sr2,start,budget);
    if (result != COMPANION_SPI_NOR_STM32WBA_OK) return result;
    nor->info.status1 = sr1;
    const uint32_t now = nor->config.now_ms(nor->config.context);
    if (nor->erase_phase == NOR_ERASE_RESUME_WAIT) {
        if (sr2 & NOR_SR2_SUS) { nor->erase_phase=NOR_ERASE_SUSPENDED; return COMPANION_SPI_NOR_STM32WBA_ERROR; }
        nor->erase_started_ms += now - nor->erase_pause_started_ms;
        nor->erase_phase = (sr1 & NOR_SR1_WIP) ? NOR_ERASE_RUNNING : NOR_ERASE_COMPLETE;
        return COMPANION_SPI_NOR_STM32WBA_PENDING;
    }
    if (sr2 & NOR_SR2_SUS) {
        if (sr1 & NOR_SR1_WIP) return COMPANION_SPI_NOR_STM32WBA_PENDING;
        if (nor->erase_phase != NOR_ERASE_SUSPENDED) nor->erase_pause_started_ms=now;
        nor->erase_phase=NOR_ERASE_SUSPENDED;return COMPANION_SPI_NOR_STM32WBA_OK;
    }
    if (!(sr1 & NOR_SR1_WIP)) {
        nor->erase_phase=NOR_ERASE_COMPLETE;
        if (sr1 & NOR_SR1_WEL) {nor->erase_command_failed=true;return COMPANION_SPI_NOR_STM32WBA_ERROR;}
        return COMPANION_SPI_NOR_STM32WBA_OK;
    }
    if (nor->erase_phase == NOR_ERASE_SUSPEND_WAIT || nor->erase_phase == NOR_ERASE_SUSPENDED) {
        nor->erase_phase=NOR_ERASE_RUNNING;nor->erase_run_since_ms=now;return COMPANION_SPI_NOR_STM32WBA_ERROR;
    }
    uint32_t elapsed=now-start;
    if (elapsed >= budget) return COMPANION_SPI_NOR_STM32WBA_PENDING;
    result=begin_transaction(nor);
    if (result != COMPANION_SPI_NOR_STM32WBA_OK) return result;
    elapsed=nor->config.now_ms(nor->config.context)-start;
    if (elapsed >= budget) return nor->config.chip_select(nor->config.context,false) ?
        COMPANION_SPI_NOR_STM32WBA_PENDING : COMPANION_SPI_NOR_STM32WBA_ERROR;
    const uint8_t command=NOR_CMD_ERASE_SUSPEND;
    nor->erase_phase_started_ms=now;nor->erase_phase=NOR_ERASE_SUSPEND_WAIT;
    result=nor->config.transfer(nor->config.context,&command,NULL,1u,budget-elapsed) ?
        COMPANION_SPI_NOR_STM32WBA_OK : COMPANION_SPI_NOR_STM32WBA_ERROR;
    result=finish_transaction(nor,result);
    /* An interrupt may delay CS assertion or command transfer. Do not
     * count that delay toward the device's post-command suspend guard. */
    nor->erase_phase_started_ms=nor->config.now_ms(nor->config.context);
    return result==COMPANION_SPI_NOR_STM32WBA_OK ? COMPANION_SPI_NOR_STM32WBA_PENDING : result;
}

companion_spi_nor_stm32wba_status_t companion_spi_nor_stm32wba_erase_suspend_step(
    companion_spi_nor_stm32wba_t *nor)
{
    if (!companion_spi_nor_stm32wba_ready(nor))
        return configured(nor) ? COMPANION_SPI_NOR_STM32WBA_NOT_PROBED
                               : COMPANION_SPI_NOR_STM32WBA_BAD_PARAM;
    if (!nor->erase_active) return COMPANION_SPI_NOR_STM32WBA_OK;
    if (!nor->erase_suspend_supported) return COMPANION_SPI_NOR_STM32WBA_UNSUPPORTED;
    if (nor->erase_command_failed) return COMPANION_SPI_NOR_STM32WBA_ERROR;
    if (nor->erase_phase == NOR_ERASE_COMPLETE) return COMPANION_SPI_NOR_STM32WBA_OK;
    if (nor->erase_phase == NOR_ERASE_RESUME_WAIT) {
        /* A foreground page can preempt the erase owner after RESUME. It
         * must qualify that pending command itself: otherwise the page waits
         * for the owner, while capture's pending writer prevents the owner
         * from running. Yield after qualification; never issue SUSPEND in
         * this same slice or release the original owner's completion. */
        companion_spi_nor_stm32wba_status_t resumed =
            companion_spi_nor_stm32wba_erase_resume_step(nor);
        return resumed == COMPANION_SPI_NOR_STM32WBA_OK
            ? COMPANION_SPI_NOR_STM32WBA_PENDING : resumed;
    }
    const uint32_t now = nor->config.now_ms(nor->config.context);
    if (nor->erase_phase == NOR_ERASE_RUNNING &&
        now - nor->erase_run_since_ms < nor->resume_guard_ms)
        return COMPANION_SPI_NOR_STM32WBA_PENDING;
    if (nor->erase_phase == NOR_ERASE_SUSPEND_WAIT &&
        now - nor->erase_phase_started_ms < nor->suspend_wait_ms)
        return COMPANION_SPI_NOR_STM32WBA_PENDING;
    uint8_t sr1 = 0u, sr2 = 0u;
    companion_spi_nor_stm32wba_status_t s = read_erase_status(nor, &sr1, &sr2);
    if (s != COMPANION_SPI_NOR_STM32WBA_OK) return s;
    if ((sr2 & NOR_SR2_SUS) != 0u) {
        if ((sr1 & NOR_SR1_WIP) != 0u) return COMPANION_SPI_NOR_STM32WBA_PENDING;
        if (nor->erase_phase != NOR_ERASE_SUSPENDED) nor->erase_pause_started_ms = now;
        nor->erase_phase = NOR_ERASE_SUSPENDED;
        return COMPANION_SPI_NOR_STM32WBA_OK;
    }
    if ((sr1 & NOR_SR1_WIP) == 0u) {
        nor->erase_phase = NOR_ERASE_COMPLETE;
        if ((sr1 & NOR_SR1_WEL) != 0u) {
            nor->erase_command_failed = true;
            return COMPANION_SPI_NOR_STM32WBA_ERROR;
        }
        return COMPANION_SPI_NOR_STM32WBA_OK;
    }
    if (nor->erase_phase == NOR_ERASE_SUSPEND_WAIT ||
        nor->erase_phase == NOR_ERASE_SUSPENDED) {
        /* A suspend that was ignored/unconfirmed may not unlock storage.
         * Leave the erase running and report the specific qualification failure. */
        nor->erase_phase = NOR_ERASE_RUNNING;
        nor->erase_run_since_ms = now;
        return COMPANION_SPI_NOR_STM32WBA_ERROR;
    }
    nor->erase_phase_started_ms = now;
    nor->erase_phase = NOR_ERASE_SUSPEND_WAIT;
    s = send_command(nor, NOR_CMD_ERASE_SUSPEND);
    /* Guard from command completion, including on uncertain transfer. */
    nor->erase_phase_started_ms = nor->config.now_ms(nor->config.context);
    return s == COMPANION_SPI_NOR_STM32WBA_OK ? COMPANION_SPI_NOR_STM32WBA_PENDING : s;
}

companion_spi_nor_stm32wba_status_t companion_spi_nor_stm32wba_erase_resume_step(
    companion_spi_nor_stm32wba_t *nor)
{
    if (!companion_spi_nor_stm32wba_ready(nor))
        return configured(nor) ? COMPANION_SPI_NOR_STM32WBA_NOT_PROBED
                               : COMPANION_SPI_NOR_STM32WBA_BAD_PARAM;
    if (!nor->erase_active || nor->erase_phase == NOR_ERASE_RUNNING ||
        nor->erase_phase == NOR_ERASE_COMPLETE) return COMPANION_SPI_NOR_STM32WBA_OK;
    if (!nor->erase_suspend_supported) return COMPANION_SPI_NOR_STM32WBA_UNSUPPORTED;
    if (nor->erase_phase == NOR_ERASE_SUSPEND_WAIT) {
        companion_spi_nor_stm32wba_status_t s = companion_spi_nor_stm32wba_erase_suspend_step(nor);
        if (s != COMPANION_SPI_NOR_STM32WBA_OK || nor->erase_phase == NOR_ERASE_COMPLETE)
            return s;
    }
    const uint32_t now = nor->config.now_ms(nor->config.context);
    if (nor->erase_phase == NOR_ERASE_RESUME_WAIT &&
        now - nor->erase_phase_started_ms < nor->resume_guard_ms)
        return COMPANION_SPI_NOR_STM32WBA_PENDING;
    uint8_t sr1 = 0u, sr2 = 0u;
    companion_spi_nor_stm32wba_status_t s = read_erase_status(nor, &sr1, &sr2);
    if (s != COMPANION_SPI_NOR_STM32WBA_OK) return s;
    if (nor->erase_phase == NOR_ERASE_RESUME_WAIT) {
        if ((sr2 & NOR_SR2_SUS) != 0u) {
            /* The command did not take effect. Preserve ownership and permit
             * an explicit next resume attempt, never issue a new erase. */
            nor->erase_phase = NOR_ERASE_SUSPENDED;
            return COMPANION_SPI_NOR_STM32WBA_ERROR;
        }
        nor->erase_started_ms += now - nor->erase_pause_started_ms;
        nor->erase_phase = (sr1 & NOR_SR1_WIP) != 0u ? NOR_ERASE_RUNNING : NOR_ERASE_COMPLETE;
        return COMPANION_SPI_NOR_STM32WBA_OK;
    }
    if ((sr1 & NOR_SR1_WIP) != 0u) return COMPANION_SPI_NOR_STM32WBA_PENDING;
    if ((sr2 & NOR_SR2_SUS) == 0u) return COMPANION_SPI_NOR_STM32WBA_ERROR;
    nor->erase_phase = NOR_ERASE_RESUME_WAIT;
    nor->erase_phase_started_ms = now;
    nor->erase_run_since_ms = now;
    s = send_command(nor, NOR_CMD_ERASE_RESUME);
    /* A delayed command must not consume its post-resume guard. */
    nor->erase_phase_started_ms = nor->config.now_ms(nor->config.context);
    nor->erase_run_since_ms = nor->erase_phase_started_ms;
    return s == COMPANION_SPI_NOR_STM32WBA_OK ? COMPANION_SPI_NOR_STM32WBA_PENDING : s;
}

companion_spi_nor_stm32wba_status_t companion_spi_nor_stm32wba_erase_finish_poll(
    companion_spi_nor_stm32wba_t *nor, uint32_t address, uint32_t bytes)
{
    if(!companion_spi_nor_stm32wba_ready(nor))
        return COMPANION_SPI_NOR_STM32WBA_NOT_PROBED;
    if(!nor->erase_active || nor->erase_address!=address || nor->erase_bytes!=bytes)
        return COMPANION_SPI_NOR_STM32WBA_BAD_PARAM;
    uint32_t elapsed=nor->config.now_ms(nor->config.context)-nor->erase_phase_started_ms;
    if((nor->erase_phase==NOR_ERASE_SUSPEND_WAIT && elapsed<nor->suspend_wait_ms) ||
       (nor->erase_phase==NOR_ERASE_RESUME_WAIT && elapsed<nor->resume_guard_ms) ||
       (nor->erase_phase==NOR_ERASE_RUNNING &&
        nor->config.now_ms(nor->config.context)-nor->erase_run_since_ms<nor->resume_guard_ms))
        return COMPANION_SPI_NOR_STM32WBA_PENDING;
    uint8_t sr1=0u,sr2=0u;
    companion_spi_nor_stm32wba_status_t status=read_erase_status(nor,&sr1,&sr2);
    if(status!=COMPANION_SPI_NOR_STM32WBA_OK)return status;
    if((sr1&NOR_SR1_WIP) || (sr2&NOR_SR2_SUS))return COMPANION_SPI_NOR_STM32WBA_PENDING;
    /* Read-only proof of physical quiescence retires just this owner. A
     * failed command remains an error, rather than a successful erase. */
    bool failed=nor->erase_command_failed || (sr1&NOR_SR1_WEL)!=0u;
    nor->erase_phase=NOR_ERASE_COMPLETE;nor->erase_active=false;
    return failed?COMPANION_SPI_NOR_STM32WBA_ERROR:COMPANION_SPI_NOR_STM32WBA_OK;
}

uint32_t companion_spi_nor_stm32wba_erase_chunk(
    const companion_spi_nor_stm32wba_t *nor, uint32_t address, uint32_t remaining)
{
    if(address%NOR_BLOCK_SIZE==0u && remaining>=NOR_BLOCK_SIZE)return NOR_BLOCK_SIZE;
    if(nor && nor->info.erase_32k_supported && address%32768u==0u && remaining>=32768u)return 32768u;
    return NOR_SECTOR_SIZE;
}

companion_spi_nor_stm32wba_status_t companion_spi_nor_stm32wba_erase_step(
    companion_spi_nor_stm32wba_t *nor, uint32_t address, uint32_t bytes)
{
    if (!companion_spi_nor_stm32wba_ready(nor))
        return configured(nor) ? COMPANION_SPI_NOR_STM32WBA_NOT_PROBED
                               : COMPANION_SPI_NOR_STM32WBA_BAD_PARAM;
    if ((bytes != NOR_SECTOR_SIZE && bytes != NOR_BLOCK_SIZE &&
         !(bytes==32768u && nor->info.erase_32k_supported)) || address % bytes)
        return COMPANION_SPI_NOR_STM32WBA_BAD_PARAM;
    if (!range_valid(nor->info.size_bytes, address, bytes))
        return COMPANION_SPI_NOR_STM32WBA_OUT_OF_RANGE;
    if (nor->erase_active &&
        (address != nor->erase_address || bytes != nor->erase_bytes))
        return COMPANION_SPI_NOR_STM32WBA_BAD_PARAM;

    if (nor->erase_active && nor->erase_phase != NOR_ERASE_RUNNING &&
        nor->erase_phase != NOR_ERASE_COMPLETE) {
        companion_spi_nor_stm32wba_status_t resumed = companion_spi_nor_stm32wba_erase_resume_step(nor);
        return resumed == COMPANION_SPI_NOR_STM32WBA_OK
            ? COMPANION_SPI_NOR_STM32WBA_PENDING : resumed;
    }
    uint8_t status1 = 0u;
    companion_spi_nor_stm32wba_status_t status = read_status1(nor, &status1);
    if (status != COMPANION_SPI_NOR_STM32WBA_OK) return status;
    if (nor->erase_active) {
        if (nor->erase_phase == NOR_ERASE_COMPLETE) {
            nor->erase_active = false;
            return nor->erase_command_failed ? COMPANION_SPI_NOR_STM32WBA_ERROR
                                             : COMPANION_SPI_NOR_STM32WBA_OK;
        }
        if (status1 & NOR_SR1_WIP) {
            return nor->config.now_ms(nor->config.context) - nor->erase_started_ms >=
                       nor->config.sector_erase_timeout_ms
                ? COMPANION_SPI_NOR_STM32WBA_TIMEOUT : COMPANION_SPI_NOR_STM32WBA_PENDING;
        }
        if (nor->erase_suspend_supported) {
            uint8_t sr2 = 0u;
            status = read_command(nor, NOR_CMD_READ_STATUS2, &sr2, 1u);
            if (status != COMPANION_SPI_NOR_STM32WBA_OK) return status;
            if ((sr2 & NOR_SR2_SUS) != 0u) {
                nor->erase_phase = NOR_ERASE_SUSPENDED;
                nor->erase_pause_started_ms = nor->config.now_ms(nor->config.context);
                return COMPANION_SPI_NOR_STM32WBA_PENDING;
            }
        }
        nor->erase_active = false;
        /* A failed command may or may not have reached the chip. Retry the
         * same range after readiness; never credit that uncertain erase. */
        return nor->erase_command_failed || (status1 & NOR_SR1_WEL)
            ? COMPANION_SPI_NOR_STM32WBA_ERROR : COMPANION_SPI_NOR_STM32WBA_OK;
    }
    if (status1 & NOR_SR1_WIP) return COMPANION_SPI_NOR_STM32WBA_PENDING;
    status = write_enable(nor);
    if (status != COMPANION_SPI_NOR_STM32WBA_OK) return status;
    nor->erase_address = address;
    nor->erase_bytes = bytes;
    nor->erase_started_ms = nor->config.now_ms(nor->config.context);
    nor->erase_run_since_ms = nor->erase_started_ms;
    nor->erase_phase = NOR_ERASE_RUNNING;
    nor->erase_command_failed = false;
    nor->erase_active = true;
    status = write_addressed(nor, bytes == NOR_BLOCK_SIZE ? NOR_CMD_BLOCK_ERASE_64K :
                             bytes == 32768u ? NOR_CMD_BLOCK_ERASE_32K : NOR_CMD_SECTOR_ERASE_4K,
                             address, NULL, 0u);
    /* The erase begins on the command's CS release. IRQ or SPI delay must
     * not spend its timeout or suspend guard before that point. Keep the
     * attempted owner even when command completion is uncertain. */
    nor->erase_started_ms = nor->config.now_ms(nor->config.context);
    nor->erase_run_since_ms = nor->erase_started_ms;
    if (status != COMPANION_SPI_NOR_STM32WBA_OK) {
        nor->erase_command_failed = true;
        return status;
    }
    return COMPANION_SPI_NOR_STM32WBA_PENDING;
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

companion_spi_nor_stm32wba_status_t companion_spi_nor_stm32wba_partition_erase_step(
    companion_spi_nor_stm32wba_partition_t *partition, uint32_t offset,
    uint32_t remaining_bytes, uint32_t *erased_bytes)
{
    if (!erased_bytes) return COMPANION_SPI_NOR_STM32WBA_BAD_PARAM;
    *erased_bytes = 0u;
    if (!partition || !partition->nor || offset % NOR_SECTOR_SIZE ||
        remaining_bytes < NOR_SECTOR_SIZE || remaining_bytes % NOR_SECTOR_SIZE)
        return COMPANION_SPI_NOR_STM32WBA_BAD_PARAM;
    if (!range_valid(partition->size_bytes, offset, remaining_bytes))
        return COMPANION_SPI_NOR_STM32WBA_OUT_OF_RANGE;
    uint32_t address = partition->base_address + offset;
    uint32_t bytes = companion_spi_nor_stm32wba_erase_chunk(partition->nor,address,remaining_bytes);
    companion_spi_nor_stm32wba_status_t status =
        companion_spi_nor_stm32wba_erase_step(partition->nor, address, bytes);
    if (status == COMPANION_SPI_NOR_STM32WBA_OK) *erased_bytes = bytes;
    return status;
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

companion_spi_nor_stm32wba_status_t companion_spi_nor_stm32wba_program(
    companion_spi_nor_stm32wba_t *nor,uint32_t address,const uint8_t *data,size_t length)
{
    comp_cpu_stage_span_t span=comp_cpu_stage_begin();
    companion_spi_nor_stm32wba_status_t result=program_page_body(nor,address,data,length);
    comp_cpu_stage_end(COMP_CPU_STAGE_NOR_PROGRAM,span,result==COMPANION_SPI_NOR_STM32WBA_OK);
    return result;
}
