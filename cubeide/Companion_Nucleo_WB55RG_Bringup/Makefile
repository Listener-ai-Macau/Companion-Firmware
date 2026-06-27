TARGET := Companion_Nucleo_WB55RG_Bringup
BUILD_DIR := build
ROOT := ../..
CUBE := $(ROOT)/third_party/STM32CubeWB

TOOLCHAIN ?= C:/ST/STM32CubeIDE_2.1.1/STM32CubeIDE/plugins/com.st.stm32cube.ide.mcu.externaltools.gnu-tools-for-stm32.14.3.rel1.win32_1.0.100.202602081740/tools/bin
CC := $(TOOLCHAIN)/arm-none-eabi-gcc
AS := $(TOOLCHAIN)/arm-none-eabi-gcc
OBJCOPY := $(TOOLCHAIN)/arm-none-eabi-objcopy
SIZE := $(TOOLCHAIN)/arm-none-eabi-size

CPU := -mcpu=cortex-m4 -mthumb -mfpu=fpv4-sp-d16 -mfloat-abi=hard
DEFS := -DUSE_HAL_DRIVER -DSTM32WB55xx -DDEBUG
ifeq ($(OTA_APP),1)
DEFS += -DCOMPANION_STM32WB_OTA_APP
endif

INC_DIRS := \
	Core/Inc \
	$(CUBE)/Drivers/STM32WBxx_HAL_Driver/Inc \
	$(CUBE)/Drivers/STM32WBxx_HAL_Driver/Inc/Legacy \
	$(CUBE)/Drivers/CMSIS/Device/ST/STM32WBxx/Include \
	$(CUBE)/Drivers/CMSIS/Include \
	$(ROOT)/app/companion_pendant/audio_stream \
	$(ROOT)/app/companion_pendant/diag_log \
	$(ROOT)/app/companion_pendant/recording

INCLUDES := $(addprefix -I,$(INC_DIRS))

C_SOURCES := \
	Core/Src/comp_qspi_nor.c \
	Core/Src/main.c \
	$(CUBE)/Drivers/STM32WBxx_HAL_Driver/Src/stm32wbxx_hal.c \
	$(CUBE)/Drivers/STM32WBxx_HAL_Driver/Src/stm32wbxx_hal_cortex.c \
	$(CUBE)/Drivers/STM32WBxx_HAL_Driver/Src/stm32wbxx_hal_dma.c \
	$(CUBE)/Drivers/STM32WBxx_HAL_Driver/Src/stm32wbxx_hal_dma_ex.c \
	$(CUBE)/Drivers/STM32WBxx_HAL_Driver/Src/stm32wbxx_hal_exti.c \
	$(CUBE)/Drivers/STM32WBxx_HAL_Driver/Src/stm32wbxx_hal_gpio.c \
	$(CUBE)/Drivers/STM32WBxx_HAL_Driver/Src/stm32wbxx_hal_pwr.c \
	$(CUBE)/Drivers/STM32WBxx_HAL_Driver/Src/stm32wbxx_hal_pwr_ex.c \
	$(CUBE)/Drivers/STM32WBxx_HAL_Driver/Src/stm32wbxx_hal_qspi.c \
	$(CUBE)/Drivers/STM32WBxx_HAL_Driver/Src/stm32wbxx_hal_rcc.c \
	$(CUBE)/Drivers/STM32WBxx_HAL_Driver/Src/stm32wbxx_hal_rcc_ex.c \
	$(CUBE)/Drivers/STM32WBxx_HAL_Driver/Src/stm32wbxx_hal_sai.c \
	$(CUBE)/Drivers/STM32WBxx_HAL_Driver/Src/stm32wbxx_hal_sai_ex.c \
	$(CUBE)/Drivers/STM32WBxx_HAL_Driver/Src/stm32wbxx_hal_spi.c \
	$(CUBE)/Drivers/STM32WBxx_HAL_Driver/Src/stm32wbxx_hal_spi_ex.c \
	$(CUBE)/Drivers/STM32WBxx_HAL_Driver/Src/stm32wbxx_hal_uart.c \
	$(CUBE)/Drivers/STM32WBxx_HAL_Driver/Src/stm32wbxx_hal_uart_ex.c \
	$(CUBE)/Projects/P-NUCLEO-WB55.Nucleo/Applications/BLE/BLE_p2pServer/STM32CubeIDE/Application/User/Core/syscalls.c \
	$(CUBE)/Projects/P-NUCLEO-WB55.Nucleo/Applications/BLE/BLE_p2pServer/STM32CubeIDE/Application/User/Core/sysmem.c \
	$(ROOT)/app/companion_pendant/audio_stream/audio_stream.c \
	$(ROOT)/app/companion_pendant/diag_log/diag_log.c \
	$(ROOT)/app/companion_pendant/recording/microphone.c \
	$(ROOT)/app/companion_pendant/recording/recording_fsm.c

ASM_SOURCE := $(CUBE)/Projects/P-NUCLEO-WB55.Nucleo/Applications/BLE/BLE_p2pServer/STM32CubeIDE/Application/User/Startup/startup_stm32wb55rgvx.s
ifeq ($(OTA_APP),1)
SYSTEM_SOURCE := $(CUBE)/Projects/P-NUCLEO-WB55.Nucleo/Applications/BLE/BLE_p2pServer_ota/Core/Src/system_stm32wbxx.c
LD_SCRIPT := $(CUBE)/Projects/P-NUCLEO-WB55.Nucleo/Applications/BLE/BLE_p2pServer_ota/STM32CubeIDE/STM32WB55RGVX_FLASH.ld
else
SYSTEM_SOURCE := $(CUBE)/Projects/P-NUCLEO-WB55.Nucleo/Applications/BLE/BLE_p2pServer/Core/Src/system_stm32wbxx.c
LD_SCRIPT := $(CUBE)/Projects/P-NUCLEO-WB55.Nucleo/Applications/BLE/BLE_p2pServer/STM32CubeIDE/STM32WB55RGVX_FLASH.ld
endif
C_SOURCES += $(SYSTEM_SOURCE)

OBJECTS := $(addprefix $(BUILD_DIR)/,$(notdir $(C_SOURCES:.c=.o)))
ASM_OBJECT := $(BUILD_DIR)/$(notdir $(ASM_SOURCE:.s=.o))
DEPS := $(OBJECTS:.o=.d)

vpath %.c $(sort $(dir $(C_SOURCES)))

CFLAGS := $(CPU) $(DEFS) $(INCLUDES) -Og -g3 -Wall -Wextra -ffunction-sections -fdata-sections -std=gnu11 -MMD -MP
ASFLAGS := $(CPU) $(DEFS) $(INCLUDES) -x assembler-with-cpp -MMD -MP
LDFLAGS := $(CPU) -T$(LD_SCRIPT) --specs=nano.specs --specs=nosys.specs -Wl,-Map=$(BUILD_DIR)/$(TARGET).map -Wl,--gc-sections -static -Wl,--start-group -lc -lm -Wl,--end-group

.PHONY: all
all: $(BUILD_DIR)/$(TARGET).elf $(BUILD_DIR)/$(TARGET).hex $(BUILD_DIR)/$(TARGET).bin
	$(SIZE) $(BUILD_DIR)/$(TARGET).elf

$(BUILD_DIR):
	@if not exist "$(BUILD_DIR)" mkdir "$(BUILD_DIR)"

$(BUILD_DIR)/main.o: Core/Src/main.c | $(BUILD_DIR)
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
