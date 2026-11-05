#ifndef COMPANION_V11_PANEL_BOOT_IDLE_H
#define COMPANION_V11_PANEL_BOOT_IDLE_H

#include "stm32wbaxx_hal.h"

#ifndef COMP_V11_PANEL_LOW_SLEW
#define COMP_V11_PANEL_LOW_SLEW 0
#endif
#ifndef COMP_V11_PANEL_OPEN_DRAIN
#define COMP_V11_PANEL_OPEN_DRAIN 0
#endif
#if COMP_V11_PANEL_OPEN_DRAIN
/* V1.1 schematic: U3 is TXB0104 (EPD D/C/BUSY/SCK/SDIN); U4 is
 * TXS0104E (EPD CS and touch). TXB0104 requires push-pull input drivers.
 * The withdrawn FW119 comparison assumed TXS on every EPD signal and failed.
 * A different fitted part requires an explicitly qualified board profile. */
#error "Companion V1.1 EPD TXB0104 does not support open-drain output drivers"
#endif

static inline void comp_v11_panel_gpio_slew(void)
{
#if COMP_V11_PANEL_LOW_SLEW
    /* Change only the translated EPD outputs. This changes edge slew, not
     * SPI bit periods, pin directions, pulls, or the IMU/NOR/audio clocks. */
    MODIFY_REG(GPIOA->OSPEEDR, GPIO_OSPEEDR_OSPEED11 | GPIO_OSPEEDR_OSPEED15, 0u);
    MODIFY_REG(GPIOB->OSPEEDR, GPIO_OSPEEDR_OSPEED0 | GPIO_OSPEEDR_OSPEED4, 0u);
#endif
}

/* The assembled board keeps the EPD rail on across MCU resets. Hold both
 * shared-SPI devices deselected throughout resident boot and clock startup,
 * before any pin can become a clock/data source. This does not reset the EPD;
 * the board has no MCU-connected EPD RESET pin or usable rail switch. */
static inline void comp_v11_panel_boot_idle(void)
{
    GPIO_InitTypeDef init = {0};
    __HAL_RCC_GPIOA_CLK_ENABLE();
    __HAL_RCC_GPIOB_CLK_ENABLE();

    HAL_GPIO_WritePin(GPIOB, GPIO_PIN_0 | GPIO_PIN_15, GPIO_PIN_SET);
    init.Pin = GPIO_PIN_0 | GPIO_PIN_15; /* EPD CS / IMU CS, active low */
    init.Mode = GPIO_MODE_OUTPUT_PP;
    init.Pull = GPIO_NOPULL;
    init.Speed = GPIO_SPEED_FREQ_HIGH;
    HAL_GPIO_Init(GPIOB, &init);

    HAL_GPIO_WritePin(GPIOA, GPIO_PIN_11, GPIO_PIN_SET);
    init.Pin = GPIO_PIN_11; /* EPD D/C idle is data, both CS remain high. */
    HAL_GPIO_Init(GPIOA, &init);

    HAL_GPIO_WritePin(GPIOB, GPIO_PIN_4, GPIO_PIN_RESET);
    init.Pin = GPIO_PIN_4; /* Shared SCK idle, SPI mode 0 */
    HAL_GPIO_Init(GPIOB, &init);
    HAL_GPIO_WritePin(GPIOA, GPIO_PIN_15, GPIO_PIN_RESET);
    init.Pin = GPIO_PIN_15; /* Shared MOSI idle */
    HAL_GPIO_Init(GPIOA, &init);
    comp_v11_panel_gpio_slew();
}

#endif
