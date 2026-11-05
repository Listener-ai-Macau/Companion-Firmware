ROOT := ../../..
BUILD := build
TARGET := $(BUILD)/Companion_WB55_SPI1_NOR_UI_2MiB.stldr
TOOLCHAIN ?= C:/ST/STM32CubeIDE_2.1.1/STM32CubeIDE/plugins/com.st.stm32cube.ide.mcu.externaltools.gnu-tools-for-stm32.14.3.rel1.win32_1.0.100.202602081740/tools/bin
CC := $(TOOLCHAIN)/arm-none-eabi-gcc
READELF := $(TOOLCHAIN)/arm-none-eabi-readelf
SIZE := $(TOOLCHAIN)/arm-none-eabi-size

CMSIS_DEVICE := $(ROOT)/third_party/STM32CubeWB/Drivers/CMSIS/Device/ST/STM32WBxx/Include
CMSIS_CORE := $(ROOT)/third_party/STM32CubeWB/Drivers/CMSIS/Include
CFLAGS := -mcpu=cortex-m4 -mthumb -mfloat-abi=soft -Os -g0 \
	-ffreestanding -fno-builtin -ffunction-sections -fdata-sections \
	-Wall -Wextra -Werror -DCORE_CM4 -DSTM32WB55xx \
	-I$(CMSIS_DEVICE) -I$(CMSIS_CORE)
LDFLAGS := -nostdlib -Wl,--gc-sections -Wl,--build-id=none \
	-Tloader.ld

SOURCES := loader.c dev_info.c
OBJECTS := $(SOURCES:%.c=$(BUILD)/%.o)

.PHONY: all clean inspect verify

all: $(TARGET)

$(BUILD):
	@powershell -NoProfile -Command "New-Item -ItemType Directory -Force '$(BUILD)' | Out-Null"

$(BUILD)/%.o: %.c | $(BUILD)
	$(CC) $(CFLAGS) -c $< -o $@

$(TARGET): $(OBJECTS) loader.ld
	$(CC) $(CFLAGS) $(OBJECTS) $(LDFLAGS) -o $@
	$(SIZE) $@

inspect: $(TARGET)
	$(READELF) -S -s $(TARGET)

verify: $(TARGET)
	python verify_loader.py $(TARGET)

clean:
	@powershell -NoProfile -Command "if (Test-Path '$(BUILD)') { Remove-Item -Recurse -Force '$(BUILD)' }"
