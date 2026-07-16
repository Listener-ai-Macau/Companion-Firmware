TARGET := Companion_Nucleo_WB55RG_Bringup
BUILD_DIR := build
ROOT := ../..
CUBE := $(ROOT)/third_party/STM32CubeWB
P2P := $(CUBE)/Projects/P-NUCLEO-WB55.Nucleo/Applications/BLE/BLE_p2pServer

TOOLCHAIN ?= C:/ST/STM32CubeIDE_2.1.1/STM32CubeIDE/plugins/com.st.stm32cube.ide.mcu.externaltools.gnu-tools-for-stm32.14.3.rel1.win32_1.0.100.202602081740/tools/bin
CC := $(TOOLCHAIN)/arm-none-eabi-gcc
AS := $(TOOLCHAIN)/arm-none-eabi-gcc
OBJCOPY := $(TOOLCHAIN)/arm-none-eabi-objcopy
SIZE := $(TOOLCHAIN)/arm-none-eabi-size
PYTHON ?= python

SCREEN_ASSET_MANIFEST := $(ROOT)/docs/art/iterations/companion-pet-expression-v9/rendered-200x200/v9-expression-cemp-manifest.json
SCREEN_ASSET_PACK_BUILDER := $(ROOT)/tools/build_emote_asset_pack.py
SCREEN_ASSET_PROVISION_HEADER := $(BUILD_DIR)/generated/companion_screen_asset_provision_blob.h
SCREEN_ASSET_PROVISION_BINARY := $(BUILD_DIR)/generated/companion-v9-expression-candidate-200x200.cemp
SCREEN_ASSET_PROVISION_INPUTS := \
	$(wildcard $(ROOT)/docs/art/iterations/companion-pet-expression-v9/rendered-200x200/pbm/*.pbm)
MAIN_GENERATED_DEPS :=

CPU := -mcpu=cortex-m4 -mthumb -mfpu=fpv4-sp-d16 -mfloat-abi=hard
C_OPT ?= -O2
DEFS := -DUSE_HAL_DRIVER -DUSE_STM32WBXX_NUCLEO -DCORE_CM4 -DSTM32WB55xx -DDEBUG
ifeq ($(OTA_APP),1)
DEFS += -DCOMPANION_STM32WB_OTA_APP
endif
ifeq ($(BOOT_SELFTESTS),1)
DEFS += -DCOMPANION_RUN_BOOT_SELFTESTS=1
endif
ifneq ($(strip $(MIC_PREAMP_SHIFT)),)
DEFS += -DCOMPANION_MIC_PREAMP_SHIFT=$(MIC_PREAMP_SHIFT)u
endif
ifneq ($(strip $(MIC_BACKEND)),)
DEFS += -DCOMPANION_MIC_BACKEND=$(MIC_BACKEND)u
endif
ifneq ($(strip $(PDM_DATA_AF)),)
DEFS += -DCOMPANION_PDM_DATA_AF=$(PDM_DATA_AF)
endif
ifneq ($(strip $(PDM_CLOCK_ENABLE)),)
DEFS += -DCOMPANION_PDM_CLOCK_ENABLE=$(PDM_CLOCK_ENABLE)
endif
ifneq ($(strip $(PDM_SLOT_ACTIVE)),)
DEFS += -DCOMPANION_PDM_SLOT_ACTIVE=$(PDM_SLOT_ACTIVE)
endif
ifneq ($(strip $(PDM_MIC_PAIRS)),)
DEFS += -DCOMPANION_PDM_MIC_PAIRS=$(PDM_MIC_PAIRS)u
endif
ifneq ($(strip $(PDM_PCM_SCALE)),)
DEFS += -DCOMPANION_PDM_PCM_SCALE=$(PDM_PCM_SCALE)
endif
ifneq ($(strip $(PDM_DECIMATION_FACTOR)),)
DEFS += -DCOMPANION_PDM_DECIMATION_FACTOR=$(PDM_DECIMATION_FACTOR)u
endif
ifneq ($(strip $(PDM_RAW_SAI_AUDIO_FREQUENCY)),)
DEFS += -DCOMPANION_PDM_RAW_SAI_AUDIO_FREQUENCY=$(PDM_RAW_SAI_AUDIO_FREQUENCY)
endif
ifneq ($(strip $(PDM_RAW_SAI_USE_EXPLICIT_MCKDIV)),)
DEFS += -DCOMPANION_PDM_RAW_SAI_USE_EXPLICIT_MCKDIV=$(PDM_RAW_SAI_USE_EXPLICIT_MCKDIV)u
endif
ifneq ($(strip $(PDM_RAW_SAI_MCKDIV)),)
DEFS += -DCOMPANION_PDM_RAW_SAI_MCKDIV=$(PDM_RAW_SAI_MCKDIV)u
endif
ifneq ($(strip $(PDM_RAW_SAI_USE_DMA)),)
DEFS += -DCOMPANION_PDM_RAW_SAI_USE_DMA=$(PDM_RAW_SAI_USE_DMA)u
endif
ifneq ($(strip $(PDM_BIT_ORDER_LSB)),)
DEFS += -DCOMPANION_PDM_BIT_ORDER_LSB=$(PDM_BIT_ORDER_LSB)u
endif
ifneq ($(strip $(PDM_INVERT_BITS)),)
DEFS += -DCOMPANION_PDM_INVERT_BITS=$(PDM_INVERT_BITS)u
endif
ifneq ($(strip $(PDM_USE_CIC3_FILTER)),)
DEFS += -DCOMPANION_PDM_USE_CIC3_FILTER=$(PDM_USE_CIC3_FILTER)u
endif
ifneq ($(strip $(PDM_CIC3_CHUNK_ACCUMULATE)),)
DEFS += -DCOMPANION_PDM_CIC3_CHUNK_ACCUMULATE=$(PDM_CIC3_CHUNK_ACCUMULATE)u
endif
ifneq ($(strip $(BLE_AUDIO_STREAM_FLASH_RECORDINGS)),)
DEFS += -DCOMPANION_BLE_AUDIO_STREAM_FLASH_RECORDINGS=$(BLE_AUDIO_STREAM_FLASH_RECORDINGS)u
endif
ifneq ($(strip $(FLASH_RECORDING_STAGE_BLOCKS)),)
DEFS += -DFLASH_RECORDING_STAGE_BLOCKS=$(FLASH_RECORDING_STAGE_BLOCKS)u
endif
ifneq ($(strip $(FLASH_RECORDING_APPE_PROCESS_INTERVAL_BLOCKS)),)
DEFS += -DCOMPANION_FLASH_RECORDING_APPE_PROCESS_INTERVAL_BLOCKS=$(FLASH_RECORDING_APPE_PROCESS_INTERVAL_BLOCKS)u
endif
ifeq ($(EPAPER_SSD1681_BRINGUP),1)
DEFS += -DCOMPANION_EPAPER_PANEL_SSD1681_BRINGUP=1
endif
ifeq ($(EPAPER_MENU),1)
DEFS += -DCOMPANION_SCREEN_MENU_ENABLED=1
endif
ifeq ($(EPAPER_EMOTE_DEMO),1)
DEFS += -DCOMPANION_SCREEN_EMOTE_DEMO=1
endif
ifeq ($(EPAPER_DAILY_TAP_DEMO),1)
DEFS += -DCOMPANION_SCREEN_DAILY_TAP_DEMO=1
endif
ifeq ($(EPAPER_DAILY_STROKE_DEMO),1)
DEFS += -DCOMPANION_SCREEN_DAILY_STROKE_DEMO=1
DEFS += -DCOMPANION_SCREEN_DAILY_STROKE_DEMO_DIRECTION=$(EPAPER_DAILY_STROKE_DEMO_DIRECTION)u
endif
ifeq ($(EPAPER_MAINTENANCE_DIAGNOSTIC),1)
DEFS += -DCOMPANION_SCREEN_MAINTENANCE_DIAGNOSTIC=1
endif
ifeq ($(EPAPER_REFRESH_CADENCE_DIAGNOSTIC),1)
DEFS += -DCOMPANION_SCREEN_REFRESH_CADENCE_DIAGNOSTIC=1
endif
ifeq ($(EPAPER_SSD1681_VENDOR_PARTIAL_DIAGNOSTIC),1)
DEFS += -DCOMPANION_EPAPER_SSD1681_VENDOR_PARTIAL_DIAGNOSTIC=1
endif
ifeq ($(EPAPER_SSD1681_DIRECT_GPIO_SPI_DIAGNOSTIC),1)
DEFS += -DCOMPANION_EPAPER_SSD1681_DIRECT_GPIO_SPI_DIAGNOSTIC=1
endif
ifeq ($(EPAPER_SSD1681_VERBOSE_TRACE),1)
DEFS += -DCOMPANION_EPAPER_SSD1681_VERBOSE_TRACE=1
endif
ifeq ($(TOUCH_VERBOSE_TRACE),1)
DEFS += -DCOMPANION_TOUCH_VERBOSE_TRACE=1
endif
ifneq ($(strip $(FT6336_TOUCH_THRESHOLD)),)
DEFS += -DCOMP_FT6336_COMPANION_TOUCH_THRESHOLD=$(FT6336_TOUCH_THRESHOLD)
endif
ifeq ($(EPAPER_PRODUCT_EXPRESSION_DEMO),1)
DEFS += -DCOMPANION_SCREEN_PRODUCT_EXPRESSION_DEMO=1
endif
ifneq ($(strip $(EPAPER_PRODUCT_EXPRESSION_DEMO_SIGNAL)),)
DEFS += -DCOMPANION_SCREEN_PRODUCT_EXPRESSION_DEMO_SIGNAL=$(EPAPER_PRODUCT_EXPRESSION_DEMO_SIGNAL)
endif
ifneq ($(strip $(EPAPER_PRODUCT_EXPRESSION_DEMO_END_SIGNAL)),)
DEFS += -DCOMPANION_SCREEN_PRODUCT_EXPRESSION_DEMO_END_SIGNAL=$(EPAPER_PRODUCT_EXPRESSION_DEMO_END_SIGNAL)
endif
ifneq ($(strip $(EPAPER_PRODUCT_EXPRESSION_DEMO_END_AFTER_MS)),)
DEFS += -DCOMPANION_SCREEN_PRODUCT_EXPRESSION_DEMO_END_AFTER_MS=$(EPAPER_PRODUCT_EXPRESSION_DEMO_END_AFTER_MS)
endif
ifeq ($(SCREEN_ASSET_PROVISION),1)
DEFS += -DCOMPANION_SCREEN_ASSET_PROVISION=1
MAIN_GENERATED_DEPS += $(SCREEN_ASSET_PROVISION_HEADER)
endif
ifneq ($(strip $(EPAPER_SSD1681_CS_PORT)),)
DEFS += -DCOMPANION_EPAPER_SSD1681_CS_GPIO_PORT=$(EPAPER_SSD1681_CS_PORT)
endif
ifneq ($(strip $(EPAPER_SSD1681_CS_PIN)),)
DEFS += -DCOMPANION_EPAPER_SSD1681_CS_PIN=$(EPAPER_SSD1681_CS_PIN)
endif
ifneq ($(strip $(EPAPER_SSD1681_DC_PORT)),)
DEFS += -DCOMPANION_EPAPER_SSD1681_DC_GPIO_PORT=$(EPAPER_SSD1681_DC_PORT)
endif
ifneq ($(strip $(EPAPER_SSD1681_DC_PIN)),)
DEFS += -DCOMPANION_EPAPER_SSD1681_DC_PIN=$(EPAPER_SSD1681_DC_PIN)
endif
ifneq ($(strip $(EPAPER_SSD1681_RST_PORT)),)
DEFS += -DCOMPANION_EPAPER_SSD1681_RST_GPIO_PORT=$(EPAPER_SSD1681_RST_PORT)
endif
ifneq ($(strip $(EPAPER_SSD1681_RST_PIN)),)
DEFS += -DCOMPANION_EPAPER_SSD1681_RST_PIN=$(EPAPER_SSD1681_RST_PIN)
endif
ifneq ($(strip $(EPAPER_SSD1681_HAS_BUSY)),)
DEFS += -DCOMPANION_EPAPER_SSD1681_HAS_BUSY=$(EPAPER_SSD1681_HAS_BUSY)
endif
ifneq ($(strip $(EPAPER_SSD1681_BUSY_PORT)),)
DEFS += -DCOMPANION_EPAPER_SSD1681_BUSY_GPIO_PORT=$(EPAPER_SSD1681_BUSY_PORT)
endif
ifneq ($(strip $(EPAPER_SSD1681_BUSY_PIN)),)
DEFS += -DCOMPANION_EPAPER_SSD1681_BUSY_PIN=$(EPAPER_SSD1681_BUSY_PIN)
endif
ifneq ($(strip $(EPAPER_SSD1681_ROTATION)),)
DEFS += -DCOMPANION_EPAPER_SSD1681_ROTATION_DEGREES=$(EPAPER_SSD1681_ROTATION)u
DEFS += -DCOMPANION_SCREEN_ROTATION_DEGREES=$(EPAPER_SSD1681_ROTATION)u
endif
ifneq ($(strip $(EPAPER_SSD1681_MIRROR_X)),)
DEFS += -DCOMPANION_EPAPER_SSD1681_MIRROR_X=$(EPAPER_SSD1681_MIRROR_X)u
DEFS += -DCOMPANION_SCREEN_MIRROR_X=$(EPAPER_SSD1681_MIRROR_X)u
endif
ifneq ($(strip $(EPAPER_SSD1681_WIRE_PROBE)),)
DEFS += -DCOMPANION_EPAPER_SSD1681_WIRE_PROBE=$(EPAPER_SSD1681_WIRE_PROBE)u
endif
ifneq ($(strip $(EPAPER_SSD1681_WIRE_PROBE_CYCLES)),)
DEFS += -DCOMPANION_EPAPER_SSD1681_WIRE_PROBE_CYCLES=$(EPAPER_SSD1681_WIRE_PROBE_CYCLES)u
endif
ifneq ($(strip $(EPAPER_SSD1681_WIRE_PROBE_DWELL_MS)),)
DEFS += -DCOMPANION_EPAPER_SSD1681_WIRE_PROBE_DWELL_MS=$(EPAPER_SSD1681_WIRE_PROBE_DWELL_MS)u
endif
ifneq ($(strip $(EPAPER_SSD1681_DIAGNOSTIC_PATTERN)),)
DEFS += -DCOMPANION_EPAPER_SSD1681_DIAGNOSTIC_PATTERN=$(EPAPER_SSD1681_DIAGNOSTIC_PATTERN)u
endif
ifneq ($(strip $(EPAPER_SSD1681_DIAGNOSTIC_REPEATS)),)
DEFS += -DCOMPANION_EPAPER_SSD1681_DIAGNOSTIC_REPEATS=$(EPAPER_SSD1681_DIAGNOSTIC_REPEATS)u
endif
ifneq ($(strip $(EPAPER_SSD1681_DIAGNOSTIC_INTERVAL_MS)),)
DEFS += -DCOMPANION_EPAPER_SSD1681_DIAGNOSTIC_INTERVAL_MS=$(EPAPER_SSD1681_DIAGNOSTIC_INTERVAL_MS)u
endif
ifneq ($(strip $(EPAPER_SSD1681_DIAGNOSTIC_PARTIAL)),)
DEFS += -DCOMPANION_EPAPER_SSD1681_DIAGNOSTIC_PARTIAL=$(EPAPER_SSD1681_DIAGNOSTIC_PARTIAL)u
endif
ifneq ($(strip $(EPAPER_SSD1681_OFFICIAL_FULL_DIAGNOSTIC)),)
DEFS += -DCOMPANION_EPAPER_SSD1681_OFFICIAL_FULL_DIAGNOSTIC=$(EPAPER_SSD1681_OFFICIAL_FULL_DIAGNOSTIC)
endif

INC_DIRS := \
	Core/Inc \
	$(P2P)/Core/Inc \
	$(P2P)/STM32_WPAN/App \
	$(P2P)/STM32_WPAN/Target \
	$(CUBE)/Utilities/lpm/tiny_lpm \
	$(CUBE)/Utilities/sequencer \
	$(CUBE)/Middlewares/ST/STM32_WPAN \
	$(CUBE)/Middlewares/ST/STM32_WPAN/ble \
	$(CUBE)/Middlewares/ST/STM32_WPAN/ble/core \
	$(CUBE)/Middlewares/ST/STM32_WPAN/ble/core/auto \
	$(CUBE)/Middlewares/ST/STM32_WPAN/ble/core/template \
	$(CUBE)/Middlewares/ST/STM32_WPAN/ble/svc/Inc \
	$(CUBE)/Middlewares/ST/STM32_WPAN/ble/svc/Src \
	$(CUBE)/Middlewares/ST/STM32_WPAN/interface/patterns/ble_thread \
	$(CUBE)/Middlewares/ST/STM32_WPAN/interface/patterns/ble_thread/shci \
	$(CUBE)/Middlewares/ST/STM32_WPAN/interface/patterns/ble_thread/tl \
	$(CUBE)/Middlewares/ST/STM32_WPAN/utilities \
	$(CUBE)/Drivers/BSP/P-NUCLEO-WB55.Nucleo \
	$(CUBE)/Drivers/STM32WBxx_HAL_Driver/Inc \
	$(CUBE)/Drivers/STM32WBxx_HAL_Driver/Inc/Legacy \
	$(CUBE)/Drivers/CMSIS/Device/ST/STM32WBxx/Include \
	$(CUBE)/Drivers/CMSIS/Include \
	$(ROOT)/app/companion_pendant/audio_stream \
	$(ROOT)/app/companion_pendant/diag_log \
	$(ROOT)/app/companion_pendant/epaper \
	$(ROOT)/app/companion_pendant/gatt \
	$(ROOT)/app/companion_pendant/power \
	$(ROOT)/app/companion_pendant/recording \
	$(ROOT)/app/companion_pendant/storage \
	$(ROOT)/third_party/denzic-platform/audio/embedded/c/include \
	$(ROOT)/app/companion_pendant/touch \
	$(ROOT)/app/companion_pendant/v1_features

INCLUDES := $(addprefix -I,$(INC_DIRS))
ifeq ($(SCREEN_ASSET_PROVISION),1)
INCLUDES += -I$(BUILD_DIR)/generated
endif

C_SOURCES := \
	Core/Src/app_ble.c \
	Core/Src/comp_spi_nor_stm32wb_spi1.c \
	Core/Src/companion_screen_assets_stm32wb.c \
	Core/Src/main.c \
	$(ROOT)/app/companion_pendant/storage/spi_nor_stm32wba.c \
	$(P2P)/Core/Src/app_debug.c \
	$(P2P)/Core/Src/app_entry.c \
	$(P2P)/Core/Src/hw_timerserver.c \
	$(P2P)/Core/Src/hw_uart.c \
	$(P2P)/Core/Src/stm32_lpm_if.c \
	$(P2P)/STM32_WPAN/Target/hw_ipcc.c \
	$(CUBE)/Drivers/STM32WBxx_HAL_Driver/Src/stm32wbxx_hal.c \
	$(CUBE)/Drivers/STM32WBxx_HAL_Driver/Src/stm32wbxx_hal_cortex.c \
	$(CUBE)/Drivers/STM32WBxx_HAL_Driver/Src/stm32wbxx_hal_dma.c \
	$(CUBE)/Drivers/STM32WBxx_HAL_Driver/Src/stm32wbxx_hal_dma_ex.c \
	$(CUBE)/Drivers/STM32WBxx_HAL_Driver/Src/stm32wbxx_hal_exti.c \
	$(CUBE)/Drivers/STM32WBxx_HAL_Driver/Src/stm32wbxx_hal_gpio.c \
	$(CUBE)/Drivers/STM32WBxx_HAL_Driver/Src/stm32wbxx_hal_hsem.c \
	$(CUBE)/Drivers/STM32WBxx_HAL_Driver/Src/stm32wbxx_hal_i2c.c \
	$(CUBE)/Drivers/STM32WBxx_HAL_Driver/Src/stm32wbxx_hal_i2c_ex.c \
	$(CUBE)/Drivers/STM32WBxx_HAL_Driver/Src/stm32wbxx_hal_ipcc.c \
	$(CUBE)/Drivers/STM32WBxx_HAL_Driver/Src/stm32wbxx_hal_pwr.c \
	$(CUBE)/Drivers/STM32WBxx_HAL_Driver/Src/stm32wbxx_hal_pwr_ex.c \
	$(CUBE)/Drivers/STM32WBxx_HAL_Driver/Src/stm32wbxx_hal_rcc.c \
	$(CUBE)/Drivers/STM32WBxx_HAL_Driver/Src/stm32wbxx_hal_rcc_ex.c \
	$(CUBE)/Drivers/STM32WBxx_HAL_Driver/Src/stm32wbxx_hal_rng.c \
	$(CUBE)/Drivers/STM32WBxx_HAL_Driver/Src/stm32wbxx_hal_rtc.c \
	$(CUBE)/Drivers/STM32WBxx_HAL_Driver/Src/stm32wbxx_hal_rtc_ex.c \
	$(CUBE)/Drivers/STM32WBxx_HAL_Driver/Src/stm32wbxx_hal_sai.c \
	$(CUBE)/Drivers/STM32WBxx_HAL_Driver/Src/stm32wbxx_hal_sai_ex.c \
	$(CUBE)/Drivers/STM32WBxx_HAL_Driver/Src/stm32wbxx_hal_spi.c \
	$(CUBE)/Drivers/STM32WBxx_HAL_Driver/Src/stm32wbxx_hal_spi_ex.c \
	$(CUBE)/Drivers/STM32WBxx_HAL_Driver/Src/stm32wbxx_hal_uart.c \
	$(CUBE)/Drivers/STM32WBxx_HAL_Driver/Src/stm32wbxx_hal_uart_ex.c \
	$(CUBE)/Drivers/BSP/P-NUCLEO-WB55.Nucleo/stm32wbxx_nucleo.c \
	$(CUBE)/Utilities/lpm/tiny_lpm/stm32_lpm.c \
	$(CUBE)/Utilities/sequencer/stm32_seq.c \
	$(CUBE)/Middlewares/ST/STM32_WPAN/utilities/dbg_trace.c \
	$(CUBE)/Middlewares/ST/STM32_WPAN/utilities/otp.c \
	$(CUBE)/Middlewares/ST/STM32_WPAN/utilities/stm_list.c \
	$(CUBE)/Middlewares/ST/STM32_WPAN/utilities/stm_queue.c \
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
	$(CUBE)/Middlewares/ST/STM32_WPAN/interface/patterns/ble_thread/tl/tl_mbox.c \
	$(CUBE)/Projects/P-NUCLEO-WB55.Nucleo/Applications/BLE/BLE_p2pServer/STM32CubeIDE/Application/User/Core/syscalls.c \
	$(CUBE)/Projects/P-NUCLEO-WB55.Nucleo/Applications/BLE/BLE_p2pServer/STM32CubeIDE/Application/User/Core/sysmem.c \
	$(ROOT)/app/companion_pendant/audio_stream/audio_stream.c \
	$(ROOT)/app/companion_pendant/audio_stream/audio_stream_stm32wb.c \
	$(ROOT)/app/companion_pendant/diag_log/diag_log.c \
	$(ROOT)/app/companion_pendant/diag_log/diag_log_export.c \
	$(ROOT)/app/companion_pendant/epaper/asset_store.c \
	$(ROOT)/app/companion_pendant/epaper/display_queue.c \
	$(ROOT)/app/companion_pendant/epaper/emote_asset_pack.c \
	$(ROOT)/app/companion_pendant/epaper/emote_player.c \
	$(ROOT)/app/companion_pendant/epaper/expression_asset_source.c \
	$(ROOT)/app/companion_pendant/epaper/expression_events.c \
	$(ROOT)/app/companion_pendant/epaper/expression_state.c \
	$(ROOT)/app/companion_pendant/epaper/panel_adapter.c \
	$(ROOT)/app/companion_pendant/epaper/panel_target_stm32wb.c \
	$(ROOT)/app/companion_pendant/epaper/pet_attention.c \
	$(ROOT)/app/companion_pendant/epaper/pet_behavior.c \
	$(ROOT)/app/companion_pendant/epaper/pet_performance.c \
	$(ROOT)/app/companion_pendant/epaper/pet_performance_event_bridge.c \
	$(ROOT)/app/companion_pendant/epaper/v9_candidate_resource_binding.c \
	$(ROOT)/app/companion_pendant/epaper/menu_v5_contract.c \
	$(ROOT)/app/companion_pendant/epaper/menu_v5_localization.c \
	$(ROOT)/app/companion_pendant/epaper/menu_v5_action_journey.c \
	$(ROOT)/app/companion_pendant/epaper/menu_v5_navigation.c \
	$(ROOT)/app/companion_pendant/epaper/menu_v5_target_bridge.c \
	$(ROOT)/app/companion_pendant/epaper/menu_v5_view_model.c \
	$(ROOT)/app/companion_pendant/epaper/refresh_policy.c \
	$(ROOT)/app/companion_pendant/epaper/screen_framebuffer.c \
	$(ROOT)/app/companion_pendant/epaper/screen_menu.c \
	$(ROOT)/app/companion_pendant/epaper/screen_presentation.c \
	$(ROOT)/app/companion_pendant/epaper/screen_runtime.c \
	$(ROOT)/app/companion_pendant/gatt/companion_gatt_stm32wb.c \
	$(ROOT)/app/companion_pendant/power/power_policy.c \
	$(ROOT)/app/companion_pendant/recording/microphone.c \
	$(ROOT)/app/companion_pendant/recording/recording_fsm.c \
	$(ROOT)/third_party/denzic-platform/audio/embedded/c/src/denzic_audio_recording_v1.c \
	$(ROOT)/app/companion_pendant/touch/ft6336.c \
	$(ROOT)/app/companion_pendant/touch/touch_gesture.c \
	$(ROOT)/app/companion_pendant/touch/touch_tap_arbiter.c \
	$(ROOT)/app/companion_pendant/touch/touch_target_stm32wb_ft6336.c \
	$(ROOT)/app/companion_pendant/v1_features/companion_v1_features.c

ASM_SOURCE := $(CUBE)/Projects/P-NUCLEO-WB55.Nucleo/Applications/BLE/BLE_p2pServer/STM32CubeIDE/Application/User/Startup/startup_stm32wb55rgvx.s
ifeq ($(OTA_APP),1)
SYSTEM_SOURCE := $(CUBE)/Projects/P-NUCLEO-WB55.Nucleo/Applications/BLE/BLE_p2pServer_ota/Core/Src/system_stm32wbxx.c
LD_SCRIPT := $(CUBE)/Projects/P-NUCLEO-WB55.Nucleo/Applications/BLE/BLE_p2pServer_ota/STM32CubeIDE/STM32WB55RGVX_FLASH.ld
else
SYSTEM_SOURCE := $(CUBE)/Projects/P-NUCLEO-WB55.Nucleo/Applications/BLE/BLE_p2pServer/Core/Src/system_stm32wbxx.c
LD_SCRIPT := $(CUBE)/Projects/P-NUCLEO-WB55.Nucleo/Applications/BLE/BLE_p2pServer/STM32CubeIDE/STM32WB55RGVX_FLASH.ld
endif
C_SOURCES += $(SYSTEM_SOURCE)
ifeq ($(EPAPER_SSD1681_BRINGUP),1)
C_SOURCES += $(ROOT)/app/companion_pendant/epaper/panel_target_stm32wb_ssd1681.c
endif

OBJECTS := $(addprefix $(BUILD_DIR)/,$(notdir $(C_SOURCES:.c=.o)))
ASM_OBJECT := $(BUILD_DIR)/$(notdir $(ASM_SOURCE:.s=.o))
DEPS := $(OBJECTS:.o=.d)

vpath %.c $(sort $(dir $(C_SOURCES)))

CFLAGS := $(CPU) $(DEFS) $(INCLUDES) $(C_OPT) -g3 -Wall -Wextra -ffunction-sections -fdata-sections -std=gnu11 -MMD -MP
ASFLAGS := $(CPU) $(DEFS) $(INCLUDES) -x assembler-with-cpp -MMD -MP
LDFLAGS := $(CPU) -T$(LD_SCRIPT) --specs=nano.specs --specs=nosys.specs -Wl,-Map=$(BUILD_DIR)/$(TARGET).map -Wl,--gc-sections -static -Wl,--start-group -lc -lm -Wl,--end-group

.PHONY: all
all: $(BUILD_DIR)/$(TARGET).elf $(BUILD_DIR)/$(TARGET).hex $(BUILD_DIR)/$(TARGET).bin
	$(SIZE) $(BUILD_DIR)/$(TARGET).elf

$(BUILD_DIR):
	@if not exist "$(BUILD_DIR)" mkdir "$(BUILD_DIR)"

ifeq ($(SCREEN_ASSET_PROVISION),1)
$(SCREEN_ASSET_PROVISION_HEADER): $(SCREEN_ASSET_MANIFEST) $(SCREEN_ASSET_PACK_BUILDER) $(SCREEN_ASSET_PROVISION_INPUTS) | $(BUILD_DIR)
	@if not exist "$(BUILD_DIR)\generated" mkdir "$(BUILD_DIR)\generated"
	$(PYTHON) "$(SCREEN_ASSET_PACK_BUILDER)" --manifest "$(SCREEN_ASSET_MANIFEST)" --output "$(SCREEN_ASSET_PROVISION_BINARY)" --c-header "$@"
endif

$(BUILD_DIR)/main.o: Core/Src/main.c $(MAIN_GENERATED_DEPS) | $(BUILD_DIR)
	$(CC) $(CFLAGS) -c "$<" -o "$@"

$(BUILD_DIR)/system_stm32wbxx.o: $(SYSTEM_SOURCE) | $(BUILD_DIR)
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
