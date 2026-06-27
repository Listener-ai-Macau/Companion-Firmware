TARGET := Companion_BLE_Ota_Loader
BUILD_DIR := build
ROOT := ../..
CUBE := $(ROOT)/third_party/STM32CubeWB
OTA := $(CUBE)/Projects/P-NUCLEO-WB55.Nucleo/Applications/BLE/BLE_Ota

TOOLCHAIN ?= C:/ST/STM32CubeIDE_2.1.1/STM32CubeIDE/plugins/com.st.stm32cube.ide.mcu.externaltools.gnu-tools-for-stm32.14.3.rel1.win32_1.0.100.202602081740/tools/bin
CC := $(TOOLCHAIN)/arm-none-eabi-gcc
AS := $(TOOLCHAIN)/arm-none-eabi-gcc
OBJCOPY := $(TOOLCHAIN)/arm-none-eabi-objcopy
SIZE := $(TOOLCHAIN)/arm-none-eabi-size

CPU := -mcpu=cortex-m4 -mthumb -mfpu=fpv4-sp-d16 -mfloat-abi=hard
DEFS := -DUSE_HAL_DRIVER -DUSE_STM32WBXX_NUCLEO -DCORE_CM4 -DSTM32WB55xx -DCOMPANION_OTA_LOADER_ALWAYS_ADVERTISE

INC_DIRS := \
	$(OTA)/Core/Inc \
	$(CUBE)/Utilities/lpm/tiny_lpm \
	$(CUBE)/Middlewares/ST/STM32_WPAN/interface/patterns/ble_thread/shci \
	$(CUBE)/Utilities/sequencer \
	$(CUBE)/Drivers/CMSIS/Device/ST/STM32WBxx/Include \
	$(CUBE)/Middlewares/ST/STM32_WPAN/interface/patterns/ble_thread \
	$(CUBE)/Middlewares/ST/STM32_WPAN/interface/patterns/ble_thread/tl \
	$(OTA)/STM32_WPAN/App \
	$(CUBE)/Middlewares/ST/STM32_WPAN/ble/core \
	$(CUBE)/Middlewares/ST/STM32_WPAN \
	$(CUBE)/Middlewares/ST/STM32_WPAN/ble/core/template \
	$(CUBE)/Drivers/BSP/P-NUCLEO-WB55.Nucleo \
	$(CUBE)/Drivers/STM32WBxx_HAL_Driver/Inc \
	$(CUBE)/Middlewares/ST/STM32_WPAN/ble/core/auto \
	$(CUBE)/Middlewares/ST/STM32_WPAN/ble/svc/Inc \
	$(CUBE)/Middlewares/ST/STM32_WPAN/ble/svc/Src \
	$(CUBE)/Middlewares/ST/STM32_WPAN/utilities \
	$(CUBE)/Middlewares/ST/STM32_WPAN/ble \
	$(CUBE)/Drivers/CMSIS/Include

INCLUDES := $(addprefix -I,$(INC_DIRS))

C_SOURCES := \
	Src/app_ble.c \
	$(OTA)/Core/Src/app_debug.c \
	$(OTA)/Core/Src/app_entry.c \
	$(OTA)/Core/Src/flash_driver.c \
	$(OTA)/Core/Src/hw_timerserver.c \
	$(OTA)/Core/Src/hw_uart.c \
	$(OTA)/Core/Src/main.c \
	$(OTA)/Core/Src/stm32_lpm_if.c \
	$(OTA)/Core/Src/stm32wbxx_it.c \
	Src/system_stm32wbxx.c \
	Src/otas_app.c \
	$(OTA)/STM32_WPAN/Target/hw_ipcc.c \
	$(OTA)/STM32CubeIDE/Application/Core/syscalls.c \
	$(OTA)/STM32CubeIDE/Application/Core/sysmem.c \
	$(CUBE)/Utilities/lpm/tiny_lpm/stm32_lpm.c \
	$(CUBE)/Utilities/sequencer/stm32_seq.c \
	$(CUBE)/Drivers/STM32WBxx_HAL_Driver/Src/stm32wbxx_hal.c \
	$(CUBE)/Drivers/STM32WBxx_HAL_Driver/Src/stm32wbxx_hal_adc.c \
	$(CUBE)/Drivers/STM32WBxx_HAL_Driver/Src/stm32wbxx_hal_adc_ex.c \
	$(CUBE)/Drivers/STM32WBxx_HAL_Driver/Src/stm32wbxx_hal_cortex.c \
	$(CUBE)/Drivers/STM32WBxx_HAL_Driver/Src/stm32wbxx_hal_dma.c \
	$(CUBE)/Drivers/STM32WBxx_HAL_Driver/Src/stm32wbxx_hal_flash.c \
	$(CUBE)/Drivers/STM32WBxx_HAL_Driver/Src/stm32wbxx_hal_flash_ex.c \
	$(CUBE)/Drivers/STM32WBxx_HAL_Driver/Src/stm32wbxx_hal_gpio.c \
	$(CUBE)/Drivers/STM32WBxx_HAL_Driver/Src/stm32wbxx_hal_pwr.c \
	$(CUBE)/Drivers/STM32WBxx_HAL_Driver/Src/stm32wbxx_hal_pwr_ex.c \
	$(CUBE)/Drivers/STM32WBxx_HAL_Driver/Src/stm32wbxx_hal_rcc.c \
	$(CUBE)/Drivers/STM32WBxx_HAL_Driver/Src/stm32wbxx_hal_rcc_ex.c \
	$(CUBE)/Drivers/STM32WBxx_HAL_Driver/Src/stm32wbxx_hal_rtc.c \
	$(CUBE)/Drivers/STM32WBxx_HAL_Driver/Src/stm32wbxx_hal_rtc_ex.c \
	$(CUBE)/Drivers/STM32WBxx_HAL_Driver/Src/stm32wbxx_hal_spi.c \
	$(CUBE)/Drivers/STM32WBxx_HAL_Driver/Src/stm32wbxx_hal_spi_ex.c \
	$(CUBE)/Drivers/STM32WBxx_HAL_Driver/Src/stm32wbxx_hal_uart.c \
	$(CUBE)/Drivers/STM32WBxx_HAL_Driver/Src/stm32wbxx_hal_uart_ex.c \
	$(CUBE)/Drivers/BSP/P-NUCLEO-WB55.Nucleo/stm32wbxx_nucleo.c \
	$(CUBE)/Middlewares/ST/STM32_WPAN/utilities/dbg_trace.c \
	$(CUBE)/Middlewares/ST/STM32_WPAN/utilities/otp.c \
	$(CUBE)/Middlewares/ST/STM32_WPAN/utilities/stm_list.c \
	$(CUBE)/Middlewares/ST/STM32_WPAN/utilities/stm_queue.c \
	Src/otas_stm.c \
	$(CUBE)/Middlewares/ST/STM32_WPAN/ble/svc/Src/svc_ctl.c \
	$(CUBE)/Middlewares/ST/STM32_WPAN/ble/core/auto/ble_gap_aci.c \
	$(CUBE)/Middlewares/ST/STM32_WPAN/ble/core/auto/ble_gatt_aci.c \
	$(CUBE)/Middlewares/ST/STM32_WPAN/ble/core/auto/ble_hal_aci.c \
	$(CUBE)/Middlewares/ST/STM32_WPAN/ble/core/auto/ble_hci_le.c \
	$(CUBE)/Middlewares/ST/STM32_WPAN/ble/core/auto/ble_l2cap_aci.c \
	$(CUBE)/Middlewares/ST/STM32_WPAN/ble/core/template/osal.c \
	$(CUBE)/Middlewares/ST/STM32_WPAN/interface/patterns/ble_thread/shci/shci.c \
	$(CUBE)/Middlewares/ST/STM32_WPAN/interface/patterns/ble_thread/tl/hci_tl.c \
	$(CUBE)/Middlewares/ST/STM32_WPAN/interface/patterns/ble_thread/tl/hci_tl_if.c \
	$(CUBE)/Middlewares/ST/STM32_WPAN/interface/patterns/ble_thread/tl/shci_tl.c \
	$(CUBE)/Middlewares/ST/STM32_WPAN/interface/patterns/ble_thread/tl/shci_tl_if.c \
	$(CUBE)/Middlewares/ST/STM32_WPAN/interface/patterns/ble_thread/tl/tl_mbox.c

ASM_SOURCE := $(OTA)/STM32CubeIDE/Application/Startup/startup_stm32wb55rgvx.s
LD_SCRIPT := $(OTA)/STM32CubeIDE/STM32WB55RGVX_FLASH.ld

OBJECTS := $(addprefix $(BUILD_DIR)/,$(notdir $(C_SOURCES:.c=.o)))
ASM_OBJECT := $(BUILD_DIR)/$(notdir $(ASM_SOURCE:.s=.o))
DEPS := $(OBJECTS:.o=.d)

vpath %.c $(sort $(dir $(C_SOURCES)))

CFLAGS := $(CPU) $(DEFS) $(INCLUDES) -Os -g0 -Wall -ffunction-sections -fdata-sections -std=gnu11 -MMD -MP
ASFLAGS := $(CPU) $(DEFS) $(INCLUDES) -x assembler-with-cpp -MMD -MP
LDFLAGS := $(CPU) -T$(LD_SCRIPT) --specs=nano.specs --specs=nosys.specs -Wl,-Map=$(BUILD_DIR)/$(TARGET).map -Wl,--gc-sections -static -Wl,--start-group -lc -lm -Wl,--end-group

.PHONY: all
all: $(BUILD_DIR)/$(TARGET).elf $(BUILD_DIR)/$(TARGET).hex $(BUILD_DIR)/$(TARGET).bin
	$(SIZE) $(BUILD_DIR)/$(TARGET).elf

$(BUILD_DIR):
	@if not exist "$(BUILD_DIR)" mkdir "$(BUILD_DIR)"

$(BUILD_DIR)/app_ble.o: Src/app_ble.c | $(BUILD_DIR)
	$(CC) $(CFLAGS) -c "$<" -o "$@"

$(BUILD_DIR)/otas_app.o: Src/otas_app.c | $(BUILD_DIR)
	$(CC) $(CFLAGS) -c "$<" -o "$@"

$(BUILD_DIR)/otas_stm.o: Src/otas_stm.c | $(BUILD_DIR)
	$(CC) $(CFLAGS) -c "$<" -o "$@"

$(BUILD_DIR)/system_stm32wbxx.o: Src/system_stm32wbxx.c | $(BUILD_DIR)
	$(CC) $(CFLAGS) -c "$<" -o "$@"

$(BUILD_DIR)/%.o: %.c | $(BUILD_DIR)
	$(CC) $(CFLAGS) -c "$<" -o "$@"

$(ASM_OBJECT): $(ASM_SOURCE) | $(BUILD_DIR)
	$(AS) $(ASFLAGS) -c "$<" -o "$@"

$(BUILD_DIR)/$(TARGET).elf: $(OBJECTS) $(ASM_OBJECT)
	$(CC) $(OBJECTS) $(ASM_OBJECT) $(LDFLAGS) -o "$@"

$(BUILD_DIR)/$(TARGET).hex: $(BUILD_DIR)/$(TARGET).elf
	$(OBJCOPY) -O ihex "$<" "$@"

$(BUILD_DIR)/$(TARGET).bin: $(BUILD_DIR)/$(TARGET).elf
	$(OBJCOPY) -O binary "$<" "$@"

-include $(DEPS)
