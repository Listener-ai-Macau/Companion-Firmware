#include "stm32wbxx.h"

#include <stddef.h>
#include <stdint.h>

#define LOADER_API __attribute__((used, section(".loader_api")))

#define EXTERNAL_ALIAS_BASE 0x90000000u
#define UI_PARTITION_BYTES 0x00200000u
#define NOR_PAGE_BYTES 256u
#define NOR_SECTOR_BYTES 4096u

#define NOR_CMD_WRITE_ENABLE 0x06u
#define NOR_CMD_READ_STATUS 0x05u
#define NOR_CMD_READ_DATA 0x03u
#define NOR_CMD_PAGE_PROGRAM 0x02u
#define NOR_CMD_ERASE_4K 0x20u
#define NOR_CMD_RELEASE_POWER_DOWN 0xABu
#define NOR_CMD_READ_JEDEC 0x9Fu

#define NOR_STATUS_BUSY 0x01u
#define NOR_STATUS_WRITE_ENABLE_LATCH 0x02u

#define EXPECTED_JEDEC_MANUFACTURER 0x0Bu
#define EXPECTED_JEDEC_MEMORY_TYPE 0x40u
#define EXPECTED_JEDEC_CAPACITY 0x18u

#define WAIT_LIMIT 0x02000000u

static void cs_high(void)
{
    GPIOA->BSRR = GPIO_BSRR_BS2;
}

static void cs_low(void)
{
    GPIOA->BSRR = GPIO_BSRR_BR2;
}

static int wait_flag_set(volatile uint32_t *reg, uint32_t flag)
{
    uint32_t remaining = WAIT_LIMIT;
    while ((*reg & flag) == 0u) {
        if (--remaining == 0u) {
            return 0;
        }
    }
    return 1;
}

static int wait_flag_clear(volatile uint32_t *reg, uint32_t flag)
{
    uint32_t remaining = WAIT_LIMIT;
    while ((*reg & flag) != 0u) {
        if (--remaining == 0u) {
            return 0;
        }
    }
    return 1;
}

static uint8_t spi_transfer(uint8_t value, int *ok)
{
    if (!wait_flag_set(&SPI1->SR, SPI_SR_TXE)) {
        *ok = 0;
        return 0u;
    }
    *(__IO uint8_t *)&SPI1->DR = value;
    if (!wait_flag_set(&SPI1->SR, SPI_SR_RXNE)) {
        *ok = 0;
        return 0u;
    }
    return *(__IO uint8_t *)&SPI1->DR;
}

static int spi_finish(void)
{
    return wait_flag_set(&SPI1->SR, SPI_SR_TXE) &&
           wait_flag_clear(&SPI1->SR, SPI_SR_BSY);
}

static int range_to_offset(uint32_t address, uint32_t size,
                           uint32_t *offset)
{
    if (offset == NULL || address < EXTERNAL_ALIAS_BASE) {
        return 0;
    }
    *offset = address - EXTERNAL_ALIAS_BASE;
    return *offset <= UI_PARTITION_BYTES &&
           size <= UI_PARTITION_BYTES - *offset;
}

static int send_command_address(uint8_t command, uint32_t offset)
{
    int ok = 1;
    cs_low();
    (void)spi_transfer(command, &ok);
    (void)spi_transfer((uint8_t)(offset >> 16u), &ok);
    (void)spi_transfer((uint8_t)(offset >> 8u), &ok);
    (void)spi_transfer((uint8_t)offset, &ok);
    return ok;
}

static int read_status(uint8_t *status)
{
    int ok = 1;
    if (status == NULL) {
        return 0;
    }
    cs_low();
    (void)spi_transfer(NOR_CMD_READ_STATUS, &ok);
    *status = spi_transfer(0xFFu, &ok);
    ok = spi_finish() && ok;
    cs_high();
    return ok;
}

static int wait_nor_ready(void)
{
    uint32_t remaining = WAIT_LIMIT;
    uint8_t status;
    do {
        if (!read_status(&status)) {
            return 0;
        }
        if ((status & NOR_STATUS_BUSY) == 0u) {
            return 1;
        }
    } while (--remaining != 0u);
    return 0;
}

static int write_enable(void)
{
    int ok = 1;
    uint8_t status;
    cs_low();
    (void)spi_transfer(NOR_CMD_WRITE_ENABLE, &ok);
    ok = spi_finish() && ok;
    cs_high();
    return ok && read_status(&status) &&
           (status & NOR_STATUS_WRITE_ENABLE_LATCH) != 0u;
}

static int nor_read(uint32_t offset, uint8_t *destination, uint32_t size)
{
    int ok;
    uint32_t index;
    if (destination == NULL || offset > UI_PARTITION_BYTES ||
        size > UI_PARTITION_BYTES - offset || !wait_nor_ready()) {
        return 0;
    }
    ok = send_command_address(NOR_CMD_READ_DATA, offset);
    for (index = 0u; ok && index < size; ++index) {
        destination[index] = spi_transfer(0xFFu, &ok);
    }
    ok = spi_finish() && ok;
    cs_high();
    return ok;
}

static int nor_program_page(uint32_t offset, const uint8_t *source,
                            uint32_t size)
{
    int ok;
    uint32_t index;
    if (source == NULL || size == 0u || size > NOR_PAGE_BYTES ||
        (offset & (NOR_PAGE_BYTES - 1u)) + size > NOR_PAGE_BYTES ||
        offset > UI_PARTITION_BYTES ||
        size > UI_PARTITION_BYTES - offset ||
        !wait_nor_ready() || !write_enable()) {
        return 0;
    }
    ok = send_command_address(NOR_CMD_PAGE_PROGRAM, offset);
    for (index = 0u; ok && index < size; ++index) {
        (void)spi_transfer(source[index], &ok);
    }
    ok = spi_finish() && ok;
    cs_high();
    return ok && wait_nor_ready();
}

static int nor_erase_sector(uint32_t offset)
{
    int ok;
    if ((offset & (NOR_SECTOR_BYTES - 1u)) != 0u ||
        offset >= UI_PARTITION_BYTES ||
        !wait_nor_ready() || !write_enable()) {
        return 0;
    }
    ok = send_command_address(NOR_CMD_ERASE_4K, offset);
    ok = spi_finish() && ok;
    cs_high();
    return ok && wait_nor_ready();
}

static int configure_hsi16(void)
{
    uint32_t remaining = WAIT_LIMIT;
    RCC->CR |= RCC_CR_HSION;
    while ((RCC->CR & RCC_CR_HSIRDY) == 0u) {
        if (--remaining == 0u) {
            return 0;
        }
    }
    RCC->CFGR = (RCC->CFGR & ~RCC_CFGR_SW) | RCC_CFGR_SW_0;
    remaining = WAIT_LIMIT;
    while ((RCC->CFGR & RCC_CFGR_SWS) != RCC_CFGR_SWS_0) {
        if (--remaining == 0u) {
            return 0;
        }
    }
    return 1;
}

static void configure_gpio_spi1(void)
{
    uint32_t value;

    RCC->AHB2ENR |= RCC_AHB2ENR_GPIOAEN | RCC_AHB2ENR_GPIOBEN;
    RCC->APB2ENR |= RCC_APB2ENR_SPI1EN;
    (void)RCC->AHB2ENR;
    (void)RCC->APB2ENR;

    value = GPIOA->MODER;
    value &= ~((3u << GPIO_MODER_MODE1_Pos) |
               (3u << GPIO_MODER_MODE2_Pos) |
               (3u << GPIO_MODER_MODE7_Pos));
    value |= (2u << GPIO_MODER_MODE1_Pos) |
             (1u << GPIO_MODER_MODE2_Pos) |
             (2u << GPIO_MODER_MODE7_Pos);
    GPIOA->MODER = value;
    GPIOA->OTYPER &= ~(GPIO_OTYPER_OT1 | GPIO_OTYPER_OT2 | GPIO_OTYPER_OT7);
    GPIOA->PUPDR &= ~((3u << GPIO_PUPDR_PUPD1_Pos) |
                      (3u << GPIO_PUPDR_PUPD2_Pos) |
                      (3u << GPIO_PUPDR_PUPD7_Pos));
    GPIOA->OSPEEDR |= (3u << GPIO_OSPEEDR_OSPEED1_Pos) |
                      (3u << GPIO_OSPEEDR_OSPEED2_Pos) |
                      (3u << GPIO_OSPEEDR_OSPEED7_Pos);
    value = GPIOA->AFR[0];
    value &= ~((0xFu << GPIO_AFRL_AFSEL1_Pos) |
               (0xFu << GPIO_AFRL_AFSEL7_Pos));
    value |= (5u << GPIO_AFRL_AFSEL1_Pos) |
             (5u << GPIO_AFRL_AFSEL7_Pos);
    GPIOA->AFR[0] = value;

    value = GPIOB->MODER;
    value &= ~(3u << GPIO_MODER_MODE4_Pos);
    value |= 2u << GPIO_MODER_MODE4_Pos;
    GPIOB->MODER = value;
    GPIOB->OTYPER &= ~GPIO_OTYPER_OT4;
    GPIOB->PUPDR &= ~(3u << GPIO_PUPDR_PUPD4_Pos);
    GPIOB->OSPEEDR |= 3u << GPIO_OSPEEDR_OSPEED4_Pos;
    value = GPIOB->AFR[0];
    value &= ~(0xFu << GPIO_AFRL_AFSEL4_Pos);
    value |= 5u << GPIO_AFRL_AFSEL4_Pos;
    GPIOB->AFR[0] = value;

    cs_high();
    RCC->APB2RSTR |= RCC_APB2RSTR_SPI1RST;
    RCC->APB2RSTR &= ~RCC_APB2RSTR_SPI1RST;
    SPI1->CR1 = 0u;
    SPI1->CR2 = (7u << SPI_CR2_DS_Pos) | SPI_CR2_FRXTH;
    SPI1->CR1 = SPI_CR1_MSTR | SPI_CR1_SSM | SPI_CR1_SSI |
                SPI_CR1_BR_1 | SPI_CR1_SPE;
}

static int release_power_down(void)
{
    int ok = 1;
    uint32_t delay;
    cs_low();
    (void)spi_transfer(NOR_CMD_RELEASE_POWER_DOWN, &ok);
    ok = spi_finish() && ok;
    cs_high();
    for (delay = 0u; delay < 4096u; ++delay) {
        __NOP();
    }
    return ok;
}

static int jedec_matches(void)
{
    int ok = 1;
    uint8_t manufacturer;
    uint8_t memory_type;
    uint8_t capacity;
    cs_low();
    (void)spi_transfer(NOR_CMD_READ_JEDEC, &ok);
    manufacturer = spi_transfer(0xFFu, &ok);
    memory_type = spi_transfer(0xFFu, &ok);
    capacity = spi_transfer(0xFFu, &ok);
    ok = spi_finish() && ok;
    cs_high();
    return ok && manufacturer == EXPECTED_JEDEC_MANUFACTURER &&
           memory_type == EXPECTED_JEDEC_MEMORY_TYPE &&
           capacity == EXPECTED_JEDEC_CAPACITY;
}

LOADER_API int Init(void)
{
    if (!configure_hsi16()) {
        return 0;
    }
    configure_gpio_spi1();
    return release_power_down() && jedec_matches();
}

LOADER_API int Read(uint32_t address, uint32_t size, uint16_t *buffer)
{
    uint32_t offset;
    if (!range_to_offset(address, size, &offset)) {
        return 0;
    }
    return nor_read(offset, (uint8_t *)buffer, size);
}

LOADER_API int Write(uint32_t address, uint32_t size, uint8_t *buffer)
{
    uint32_t offset;
    uint32_t consumed = 0u;
    if (buffer == NULL || size == 0u ||
        !range_to_offset(address, size, &offset)) {
        return 0;
    }
    while (consumed < size) {
        uint32_t page_remaining =
            NOR_PAGE_BYTES - ((offset + consumed) & (NOR_PAGE_BYTES - 1u));
        uint32_t chunk = size - consumed;
        if (chunk > page_remaining) {
            chunk = page_remaining;
        }
        if (!nor_program_page(offset + consumed, buffer + consumed, chunk)) {
            return 0;
        }
        consumed += chunk;
    }
    return 1;
}

LOADER_API int SectorErase(uint32_t start_address, uint32_t end_address)
{
    uint32_t start_offset;
    uint32_t end_offset;
    uint32_t offset;
    if (end_address < start_address ||
        !range_to_offset(start_address, 1u, &start_offset) ||
        !range_to_offset(end_address, 1u, &end_offset)) {
        return 0;
    }
    start_offset &= ~(NOR_SECTOR_BYTES - 1u);
    end_offset &= ~(NOR_SECTOR_BYTES - 1u);
    for (offset = start_offset; offset <= end_offset;
         offset += NOR_SECTOR_BYTES) {
        if (!nor_erase_sector(offset)) {
            return 0;
        }
    }
    return 1;
}

LOADER_API int MassErase(uint32_t parallelism)
{
    uint32_t offset;
    (void)parallelism;
    for (offset = 0u; offset < UI_PARTITION_BYTES;
         offset += NOR_SECTOR_BYTES) {
        if (!nor_erase_sector(offset)) {
            return 0;
        }
    }
    return 1;
}

LOADER_API uint64_t Verify(uint32_t memory_address,
                           uint32_t ram_buffer_address,
                           uint32_t size_words,
                           uint32_t missalignment)
{
    uint8_t scratch[256];
    const uint8_t *expected = (const uint8_t *)ram_buffer_address;
    uint32_t size = size_words * 4u;
    uint32_t leading = missalignment & 0xFu;
    uint32_t trailing = (missalignment >> 16u) & 0xFu;
    uint32_t offset;
    uint32_t consumed = 0u;
    uint32_t checksum = 0u;

    if (size < leading + trailing) {
        return 1u;
    }
    memory_address += leading;
    expected += leading;
    size -= leading + trailing;
    if (!range_to_offset(memory_address, size, &offset)) {
        return 1u;
    }
    while (consumed < size) {
        uint32_t chunk = size - consumed;
        uint32_t index;
        if (chunk > sizeof(scratch)) {
            chunk = sizeof(scratch);
        }
        if (!nor_read(offset + consumed, scratch, chunk)) {
            return 1u;
        }
        for (index = 0u; index < chunk; ++index) {
            checksum += scratch[index];
            if (scratch[index] != expected[consumed + index]) {
                return ((uint64_t)checksum << 32u) |
                       (uint64_t)(memory_address + consumed + index);
            }
        }
        consumed += chunk;
    }
    return (uint64_t)checksum << 32u;
}
