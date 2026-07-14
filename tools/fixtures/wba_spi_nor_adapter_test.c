#include "asset_store.h"
#include "screen_assets_stm32wba.h"
#include "spi_nor_stm32wba.h"

#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#define FAKE_NOR_SIZE (1u << 20)
#define FAKE_NOR_SECTOR_SIZE 4096u
#define FAKE_NOR_BLOCK_SIZE 65536u

#define CMD_WRITE_ENABLE 0x06u
#define CMD_READ_STATUS1 0x05u
#define CMD_READ_JEDEC_ID 0x9Fu
#define CMD_RELEASE_POWERDOWN 0xABu
#define CMD_ENABLE_RESET 0x66u
#define CMD_RESET_DEVICE 0x99u
#define CMD_READ_DATA 0x03u
#define CMD_PAGE_PROGRAM 0x02u
#define CMD_SECTOR_ERASE_4K 0x20u
#define CMD_BLOCK_ERASE_64K 0xD8u

#define SR1_WIP 0x01u
#define SR1_WEL 0x02u

typedef struct {
    uint8_t bytes[FAKE_NOR_SIZE];
    uint8_t jedec[3];
    uint8_t status1;
    uint8_t command;
    uint32_t address;
    uint32_t now_ms;
    uint32_t busy_reads;
    uint32_t page_programs;
    uint32_t sector_erases;
    uint32_t block_erases;
    uint32_t software_resets;
    bool selected;
    bool force_busy;
    bool reset_enabled;
} fake_nor_t;

static fake_nor_t s_fake;

static bool check(bool condition, const char *message)
{
    if (!condition) {
        (void)fprintf(stderr, "FAIL: %s\n", message);
    }
    return condition;
}

static void fake_reset(uint8_t manufacturer, uint8_t memory_type, uint8_t capacity)
{
    (void)memset(&s_fake, 0, sizeof(s_fake));
    (void)memset(s_fake.bytes, 0xFF, sizeof(s_fake.bytes));
    s_fake.jedec[0] = manufacturer;
    s_fake.jedec[1] = memory_type;
    s_fake.jedec[2] = capacity;
}

static bool fake_chip_select(void *context, bool active)
{
    fake_nor_t *fake = (fake_nor_t *)context;
    if (fake == NULL || fake->selected == active) {
        return false;
    }
    fake->selected = active;
    if (active) {
        fake->command = 0u;
        fake->address = 0u;
    }
    return true;
}

static uint32_t decode_address(const uint8_t *header)
{
    return ((uint32_t)header[1] << 16) |
           ((uint32_t)header[2] << 8) |
           (uint32_t)header[3];
}

static bool fake_command_header(fake_nor_t *fake,
                                const uint8_t *transmit,
                                size_t length)
{
    if (length != 1u && length != 4u) {
        return false;
    }
    fake->command = transmit[0];
    if (length == 1u) {
        if (fake->command == CMD_WRITE_ENABLE) {
            fake->status1 |= SR1_WEL;
        } else if (fake->command == CMD_ENABLE_RESET) {
            fake->reset_enabled = true;
        } else if (fake->command == CMD_RESET_DEVICE) {
            if (!fake->reset_enabled) {
                return false;
            }
            fake->reset_enabled = false;
            fake->status1 = 0u;
            fake->software_resets++;
        }
        return fake->command == CMD_WRITE_ENABLE ||
               fake->command == CMD_READ_STATUS1 ||
               fake->command == CMD_READ_JEDEC_ID ||
               fake->command == CMD_RELEASE_POWERDOWN ||
               fake->command == CMD_ENABLE_RESET ||
               fake->command == CMD_RESET_DEVICE;
    }

    fake->address = decode_address(transmit);
    if (fake->address >= FAKE_NOR_SIZE) {
        return false;
    }
    if (fake->command == CMD_SECTOR_ERASE_4K ||
        fake->command == CMD_BLOCK_ERASE_64K) {
        const uint32_t erase_size =
            fake->command == CMD_SECTOR_ERASE_4K
                ? FAKE_NOR_SECTOR_SIZE
                : FAKE_NOR_BLOCK_SIZE;
        if ((fake->status1 & SR1_WEL) == 0u ||
            (fake->address % erase_size) != 0u ||
            fake->address > FAKE_NOR_SIZE - erase_size) {
            return false;
        }
        (void)memset(&fake->bytes[fake->address],
                     0xFF,
                     erase_size);
        if (fake->command == CMD_SECTOR_ERASE_4K) {
            fake->sector_erases++;
        } else {
            fake->block_erases++;
        }
        fake->busy_reads = 2u;
        fake->status1 |= SR1_WIP;
        return true;
    }
    return fake->command == CMD_READ_DATA ||
           fake->command == CMD_PAGE_PROGRAM;
}

static bool fake_receive(fake_nor_t *fake, uint8_t *receive, size_t length)
{
    if (fake->command == CMD_READ_JEDEC_ID && length == sizeof(fake->jedec)) {
        (void)memcpy(receive, fake->jedec, sizeof(fake->jedec));
        return true;
    }
    if (fake->command == CMD_READ_STATUS1 && length == 1u) {
        if (fake->force_busy) {
            receive[0] = (uint8_t)(fake->status1 | SR1_WIP);
            return true;
        }
        receive[0] = fake->status1;
        if (fake->busy_reads != 0u) {
            fake->busy_reads--;
            if (fake->busy_reads == 0u) {
                fake->status1 = (uint8_t)(fake->status1 & 0xFCu);
            }
        }
        return true;
    }
    if (fake->command == CMD_READ_DATA &&
        fake->address <= FAKE_NOR_SIZE &&
        length <= (size_t)(FAKE_NOR_SIZE - fake->address)) {
        (void)memcpy(receive, &fake->bytes[fake->address], length);
        fake->address += (uint32_t)length;
        return true;
    }
    return false;
}

static bool fake_transmit_payload(fake_nor_t *fake,
                                  const uint8_t *transmit,
                                  size_t length)
{
    if (fake->command != CMD_PAGE_PROGRAM ||
        (fake->status1 & SR1_WEL) == 0u ||
        fake->address >= FAKE_NOR_SIZE ||
        length > (size_t)(FAKE_NOR_SIZE - fake->address) ||
        length > 256u - (fake->address % 256u)) {
        return false;
    }
    for (size_t index = 0u; index < length; ++index) {
        fake->bytes[fake->address + (uint32_t)index] &= transmit[index];
    }
    fake->address += (uint32_t)length;
    fake->page_programs++;
    fake->busy_reads = 2u;
    fake->status1 |= SR1_WIP;
    return true;
}

static bool fake_transfer(void *context,
                          const uint8_t *transmit,
                          uint8_t *receive,
                          size_t length,
                          uint32_t timeout_ms)
{
    fake_nor_t *fake = (fake_nor_t *)context;
    if (fake == NULL || !fake->selected || length == 0u || timeout_ms == 0u ||
        (transmit == NULL) == (receive == NULL)) {
        return false;
    }
    if (transmit != NULL) {
        if (fake->command == 0u) {
            return fake_command_header(fake, transmit, length);
        }
        return fake_transmit_payload(fake, transmit, length);
    }
    return fake_receive(fake, receive, length);
}

static uint32_t fake_now_ms(void *context)
{
    const fake_nor_t *fake = (const fake_nor_t *)context;
    return fake != NULL ? fake->now_ms : 0u;
}

static void fake_delay_ms(void *context, uint32_t delay_ms)
{
    fake_nor_t *fake = (fake_nor_t *)context;
    if (fake != NULL) {
        fake->now_ms += delay_ms;
    }
}

static bool init_and_probe(companion_spi_nor_stm32wba_t *nor)
{
    const companion_spi_nor_stm32wba_config_t config = {
        .target = COMPANION_SPI_NOR_STM32WBA_TARGET_WBA55,
        .chip_select = fake_chip_select,
        .transfer = fake_transfer,
        .now_ms = fake_now_ms,
        .delay_ms = fake_delay_ms,
        .context = &s_fake,
        .transfer_timeout_ms = 20u,
        .page_program_timeout_ms = 20u,
        .sector_erase_timeout_ms = 20u,
    };
    return companion_spi_nor_stm32wba_init(nor, &config) &&
           companion_spi_nor_stm32wba_probe(nor, NULL) ==
               COMPANION_SPI_NOR_STM32WBA_OK;
}

static bool test_probe(void)
{
    companion_spi_nor_stm32wba_t nor;
    fake_reset(0xFFu, 0xFFu, 0xFFu);
    const companion_spi_nor_stm32wba_config_t invalid_config = {
        .target = COMPANION_SPI_NOR_STM32WBA_TARGET_WBA55,
        .chip_select = fake_chip_select,
        .transfer = fake_transfer,
        .now_ms = fake_now_ms,
        .delay_ms = fake_delay_ms,
        .context = &s_fake,
    };
    if (!check(companion_spi_nor_stm32wba_init(&nor, &invalid_config),
               "invalid-JEDEC adapter initialization") ||
        !check(companion_spi_nor_stm32wba_probe(&nor, NULL) ==
                   COMPANION_SPI_NOR_STM32WBA_ERROR,
               "all-FF JEDEC must be rejected") ||
        !check(nor.last_probe_id_transfer_completed,
               "failed probe must preserve completed transfer state") ||
        !check(nor.last_probe_jedec_id == 0x00FFFFFFu,
               "failed probe must preserve raw JEDEC bytes")) {
        return false;
    }
    (void)printf("PASS probe_diagnostics raw_jedec=0x%06lX transfer=1\n",
                 (unsigned long)nor.last_probe_jedec_id);

    fake_reset(0xEFu, 0x40u, 0x14u);
    if (!check(init_and_probe(&nor), "valid JEDEC probe") ||
        !check(nor.info.jedec_id == 0x00EF4014u,
               "JEDEC bytes must be preserved") ||
        !check(nor.info.size_bytes == FAKE_NOR_SIZE,
               "JEDEC capacity must map to one MiB")) {
        return false;
    }
    (void)printf("PASS probe jedec=0x%06lX size=%lu\n",
                 (unsigned long)nor.info.jedec_id,
                 (unsigned long)nor.info.size_bytes);

    fake_reset(0x0Bu, 0x40u, 0x14u);
    if (!check(init_and_probe(&nor), "XTX normalized JEDEC probe") ||
        !check(s_fake.software_resets == 1u,
               "XTX probe must issue one 66h/99h reset sequence") ||
        !check(nor.info.jedec_id == 0x000B4014u,
               "XTX JEDEC must survive normalization")) {
        return false;
    }
    (void)printf("PASS xtx_reset normalization=%lu\n",
                 (unsigned long)s_fake.software_resets);
    return true;
}

static bool test_program_read_erase_and_timeout(void)
{
    companion_spi_nor_stm32wba_t nor;
    uint8_t source[300];
    uint8_t destination[300];
    const uint32_t block_address = FAKE_NOR_BLOCK_SIZE;
    for (size_t index = 0u; index < sizeof(source); ++index) {
        source[index] = (uint8_t)(index * 29u + 7u);
    }

    fake_reset(0xEFu, 0x40u, 0x14u);
    if (!check(init_and_probe(&nor), "program test probe") ||
        !check(companion_spi_nor_stm32wba_program(
                   &nor, 250u, source, sizeof(source)) ==
                   COMPANION_SPI_NOR_STM32WBA_OK,
               "cross-page program") ||
        !check(s_fake.page_programs == 3u,
               "300 bytes at offset 250 must split into three pages") ||
        !check(companion_spi_nor_stm32wba_read(
                   &nor, 250u, destination, sizeof(destination)) ==
                   COMPANION_SPI_NOR_STM32WBA_OK,
               "program readback") ||
        !check(memcmp(source, destination, sizeof(source)) == 0,
               "program readback bytes") ||
        !check(companion_spi_nor_stm32wba_read(
                   &nor, FAKE_NOR_SIZE - 4u, destination, 5u) ==
                   COMPANION_SPI_NOR_STM32WBA_OUT_OF_RANGE,
               "out-of-range read rejection") ||
        !check(companion_spi_nor_stm32wba_erase_4k(&nor, 1u) ==
                   COMPANION_SPI_NOR_STM32WBA_BAD_PARAM,
               "unaligned erase rejection") ||
        !check(companion_spi_nor_stm32wba_erase_4k(&nor, 0u) ==
                   COMPANION_SPI_NOR_STM32WBA_OK,
               "aligned erase") ||
        !check(s_fake.sector_erases == 1u && s_fake.bytes[250] == 0xFFu,
               "4 KiB erase result")) {
        return false;
    }
    (void)printf("PASS page_program splits=%lu\n",
                 (unsigned long)s_fake.page_programs);
    (void)printf("PASS bounds_and_erase\n");

    if (!check(companion_spi_nor_stm32wba_program(
                   &nor, block_address + 250u, source, sizeof(source)) ==
                   COMPANION_SPI_NOR_STM32WBA_OK,
               "64 KiB block test program") ||
        !check(companion_spi_nor_stm32wba_erase_64k(
                   &nor, block_address + 1u) ==
                   COMPANION_SPI_NOR_STM32WBA_BAD_PARAM,
               "unaligned 64 KiB erase rejection") ||
        !check(companion_spi_nor_stm32wba_erase_64k(
                   &nor, FAKE_NOR_SIZE) ==
                   COMPANION_SPI_NOR_STM32WBA_OUT_OF_RANGE,
               "out-of-range 64 KiB erase rejection") ||
        !check(companion_spi_nor_stm32wba_erase_64k(
                   &nor, block_address) ==
                   COMPANION_SPI_NOR_STM32WBA_OK,
               "aligned 64 KiB erase") ||
        !check(s_fake.block_erases == 1u &&
                   s_fake.bytes[block_address + 250u] == 0xFFu,
               "64 KiB erase result")) {
        return false;
    }
    (void)printf("PASS erase_64k blocks=%lu\n",
                 (unsigned long)s_fake.block_erases);

    s_fake.force_busy = true;
    if (!check(companion_spi_nor_stm32wba_wait_ready(&nor, 3u) ==
                   COMPANION_SPI_NOR_STM32WBA_TIMEOUT,
               "forced busy timeout")) {
        return false;
    }
    s_fake.force_busy = false;
    (void)printf("PASS timeout\n");
    return true;
}

static bool test_screen_assets_partition(void)
{
    companion_spi_nor_stm32wba_t nor;
    companion_spi_nor_stm32wba_partition_t partition;
    companion_screen_assets_stm32wba_t adapter;
    comp_asset_store_t store;
    static const uint8_t expected[] = {0x43u, 0x45u, 0x4Du, 0x50u, 0x35u, 0x35u};
    uint8_t actual[sizeof(expected)] = {0u};
    const uint32_t partition_base = 0x00020000u;

    fake_reset(0xEFu, 0x40u, 0x14u);
    if (!check(init_and_probe(&nor), "partition test probe") ||
        !check(companion_spi_nor_stm32wba_partition_init(
                   &partition, &nor, partition_base, 0x00010000u),
               "logical partition init") ||
        !check(companion_spi_nor_stm32wba_partition_program(
                   &partition, 32u, expected, sizeof(expected)) ==
                   COMPANION_SPI_NOR_STM32WBA_OK,
               "logical partition program")) {
        return false;
    }

    const companion_screen_assets_stm32wba_config_t config = {
        .target = COMPANION_EPAPER_PANEL_STM32WBA_TARGET_WBA55,
        .partition_size = partition.size_bytes,
        .read = companion_spi_nor_stm32wba_partition_read,
        .context = &partition,
    };
    companion_screen_assets_stm32wba_init(&adapter);
    if (!check(companion_screen_assets_stm32wba_bind(
                   &adapter, &store, &config),
               "screen-assets binding") ||
        !check(comp_asset_store_read(&store, 32u, actual, sizeof(actual)),
               "screen-assets partition read") ||
        !check(memcmp(expected, actual, sizeof(expected)) == 0,
               "screen-assets partition bytes") ||
        !check(!comp_asset_store_read(
                   &store, partition.size_bytes - 2u, actual, sizeof(actual)),
               "screen-assets logical bounds")) {
        return false;
    }
    (void)printf("PASS screen_assets_partition transport=spi_nor_1_1_1\n");
    return true;
}

int main(int argc, char **argv)
{
    if (argc == 2 && strcmp(argv[1], "--force-fail") == 0) {
        (void)fprintf(stderr, "INTENTIONAL_WBA_SPI_NOR_SELF_TEST_FAILURE\n");
        return 9;
    }
    if (!test_probe() ||
        !test_program_read_erase_and_timeout() ||
        !test_screen_assets_partition()) {
        return 1;
    }
    (void)printf("PASS: WBA SPI NOR adapter native behavior\n");
    return 0;
}
