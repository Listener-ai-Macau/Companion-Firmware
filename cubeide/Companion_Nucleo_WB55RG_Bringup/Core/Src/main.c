#include "main.h"

#include "app_conf.h"
#include "app_entry.h"
#include "audio_stream_stm32wb.h"
#include "comp_qspi_nor.h"
#include "companion_screen_assets_stm32wb.h"
#include "companion_screen_ui.h"
#include "diag_log.h"
#include "panel_target_stm32wb_ssd1681.h"
#include "power_policy.h"
#include "recording_fsm.h"
#include "screen_menu.h"
#include "stm32_lpm.h"
#include "touch_target_stm32wb_ft6336.h"

#include <limits.h>
#include <stdbool.h>
#include <stdio.h>
#include <string.h>

#ifndef COMPANION_SCREEN_ASSET_PROVISION
#define COMPANION_SCREEN_ASSET_PROVISION 0
#endif
#ifndef COMPANION_EPAPER_PANEL_SSD1681_BRINGUP
#define COMPANION_EPAPER_PANEL_SSD1681_BRINGUP 0
#endif
#if COMPANION_SCREEN_ASSET_PROVISION
#include "companion_screen_asset_provision_blob.h"
#endif

#if defined(COMPANION_STM32WB_OTA_APP)
#define COMPANION_PLACE_IN_SECTION(name) __attribute__((section(name), used))
COMPANION_PLACE_IN_SECTION("TAG_OTA_END") const uint32_t MagicKeywordValue = 0x94448A29u;
COMPANION_PLACE_IN_SECTION("TAG_OTA_START") const uint32_t MagicKeywordAddress =
    (uint32_t)&MagicKeywordValue;
#endif

#define FLASH_QSPI_NCS_GPIO_PORT GPIOA
#define FLASH_QSPI_NCS_PIN GPIO_PIN_2
#define FLASH_QSPI_CLK_GPIO_PORT GPIOA
#define FLASH_QSPI_CLK_PIN GPIO_PIN_3
#define FLASH_QSPI_IO1_GPIO_PORT GPIOB
#define FLASH_QSPI_IO1_PIN GPIO_PIN_8
#define FLASH_QSPI_IO0_GPIO_PORT GPIOB
#define FLASH_QSPI_IO0_PIN GPIO_PIN_9

#define BOARD_SPI2_CS_GPIO_PORT GPIOA
#define BOARD_SPI2_CS_PIN GPIO_PIN_6
#define BOARD_EPAPER_SPI_BAUDRATE_PRESCALER SPI_BAUDRATEPRESCALER_16
#define BOARD_EPAPER_SPI_HZ 2000000u
#define BOARD_MAX98357_SD_GPIO_PORT GPIOA
#define BOARD_MAX98357_SD_PIN GPIO_PIN_15

#define BOARD_SW1_GPIO_PORT GPIOC
#define BOARD_SW1_PIN GPIO_PIN_4
#define BOARD_SW2_GPIO_PORT GPIOD
#define BOARD_SW2_PIN GPIO_PIN_0
#define BOARD_SW3_GPIO_PORT GPIOD
#define BOARD_SW3_PIN GPIO_PIN_1

#define BUTTON_DEBOUNCE_MS 35u
#define BUTTON_IDLE_POLL_MS 10u
#define HEARTBEAT_PERIOD_MS 5000u
#define TOUCH_IDLE_POLL_MS 8u
#define TOUCH_ACTIVE_POLL_MS 5u
#define TOUCH_REFRESH_POLL_MS 5u
#define TOUCH_REFRESH_BUFFER_CAPACITY 256u
#define TOUCH_TAP_MAX_DURATION_MS 1100u
#define TOUCH_HOLD_FEEDBACK_MIN_DURATION_MS 650u
#define TOUCH_MENU_LONG_PRESS_DURATION_MS 3000u
#define TOUCH_LONG_PRESS_MAX_MOVE_PX 46u
#define TOUCH_MENU_ENTRY_CUE_MS 360u
#define TOUCH_MENU_PRESS_CUE_DELAY_MS 160u
#define TOUCH_SAMPLE_LOG_INTERVAL_MS 250u
#define TOUCH_TAP_MAX_MOVE_PX 24u
#define TOUCH_DOUBLE_TAP_MAX_GAP_MS 650u
#define TOUCH_DOUBLE_TAP_MAX_MOVE_PX 40u
#define TOUCH_SWIPE_MIN_MOVE_PX 30u
#define TOUCH_AXIS_LOCK_MIN_MOVE_PX 10u
#define TOUCH_AXIS_SLOP_PX 5u
#define TOUCH_AXIS_DOMINANCE_PERCENT 120u
#define TOUCH_SWIPE_MAX_DURATION_MS 1400u
#define TOUCH_MIN_CONTACT_SAMPLES 1u
#define TOUCH_RELEASE_DEBOUNCE_SAMPLES 1u
#define TOUCH_I2C_RECOVERY_FAILURES 8u
#define TOUCH_I2C_RECOVERY_COOLDOWN_MS 1000u
#define TOUCH_I2C_RECOVERY_CLOCKS 9u
#define TOUCH_RESET_LOW_MS 10u
#define TOUCH_RESET_BOOT_MS 320u
#define TOUCH_SCREEN_MAINTENANCE_QUIET_MS 1200u

#define BOARD_TOUCH_INT_GPIO_PORT GPIOC
#define BOARD_TOUCH_INT_PIN GPIO_PIN_6
#define BOARD_TOUCH_RST_GPIO_PORT GPIOC
#define BOARD_TOUCH_RST_PIN GPIO_PIN_10

#define COMPANION_TOUCH_MIRROR_X 0u
#define COMPANION_TOUCH_MIRROR_Y 0u

#ifndef COMPANION_SCREEN_MIRROR_X
#define COMPANION_SCREEN_MIRROR_X 0u
#endif
#define MANUAL_RECORDING_LOG_EVERY_BLOCKS 50u
#define MANUAL_RECORDING_DIAGNOSTIC_EVERY_BLOCKS 200u

#ifndef COMPANION_SCREEN_MAINTENANCE_DIAGNOSTIC
#define COMPANION_SCREEN_MAINTENANCE_DIAGNOSTIC 0
#endif

#define COMPANION_SCREEN_MAINTENANCE_DIAGNOSTIC_DELAY_MS 3500u

#ifndef COMPANION_TYPE_READY_AUTOSTREAM_BLOCKS
#define COMPANION_TYPE_READY_AUTOSTREAM_BLOCKS 24u
#endif
#define COMPANION_TYPE_READY_AUTOSTREAM_PCM_BYTES 128u
#ifndef COMPANION_TYPE_READY_A1_AUTOSTREAM_BLOCKS
#define COMPANION_TYPE_READY_A1_AUTOSTREAM_BLOCKS 500u
#endif
#define COMPANION_TYPE_READY_A1_AUTOSTREAM_PCM_BYTES 320u
#ifndef COMPANION_TYPE_READY_A2_AUTOSTREAM_BLOCKS
#define COMPANION_TYPE_READY_A2_AUTOSTREAM_BLOCKS 3000u
#endif
#define COMPANION_TYPE_READY_A2_AUTOSTREAM_PCM_BYTES 320u
#define COMPANION_BLE_NOTIFY_PUMP_DELAY_MS 1u

#ifndef COMPANION_BLE_AUDIO_STREAM_FLASH_RECORDINGS
#define COMPANION_BLE_AUDIO_STREAM_FLASH_RECORDINGS 0
#endif
#ifndef COMPANION_FLASH_RECORDING_APPE_PROCESS_INTERVAL_BLOCKS
#define COMPANION_FLASH_RECORDING_APPE_PROCESS_INTERVAL_BLOCKS 8u
#endif

#ifndef COMPANION_RUN_BOOT_SELFTESTS
#define COMPANION_RUN_BOOT_SELFTESTS 0
#endif
#ifndef COMPANION_SCREEN_MENU_ENABLED
#define COMPANION_SCREEN_MENU_ENABLED 0
#endif

#define MIC_PCM_SAMPLE_RATE_HZ 16000u
#define MIC_I2S_SAMPLE_RATE_HZ 16000u
#ifndef COMPANION_MIC_BACKEND
#define COMPANION_MIC_BACKEND COMPANION_MIC_BACKEND_SPH0655_PDM
#endif
#define MIC_SAMPLE_RATE_HZ MIC_PCM_SAMPLE_RATE_HZ
#define MIC_PCM_SAMPLES_PER_BATCH 160u
#define MIC_DOWNSAMPLE_FACTOR (MIC_I2S_SAMPLE_RATE_HZ / MIC_PCM_SAMPLE_RATE_HZ)
#if MIC_I2S_SAMPLE_RATE_HZ != (MIC_PCM_SAMPLE_RATE_HZ * MIC_DOWNSAMPLE_FACTOR)
#error "MIC_I2S_SAMPLE_RATE_HZ must be an integer multiple of MIC_PCM_SAMPLE_RATE_HZ"
#endif
#define MIC_FRAMES_PER_BATCH (MIC_PCM_SAMPLES_PER_BATCH * MIC_DOWNSAMPLE_FACTOR)
#define MIC_SLOT_COUNT 2u
#define MIC_I2S_WORDS (MIC_FRAMES_PER_BATCH * MIC_SLOT_COUNT)
#ifndef COMPANION_PDM_USE_HARDWARE_INTERFACE
#define COMPANION_PDM_USE_HARDWARE_INTERFACE 0
#endif
#ifndef COMPANION_PDM_DECIMATION_FACTOR
#if COMPANION_PDM_USE_HARDWARE_INTERFACE
#define COMPANION_PDM_DECIMATION_FACTOR 80u
#else
#define COMPANION_PDM_DECIMATION_FACTOR 96u
#endif
#endif
#ifndef COMPANION_PDM_RAW_SAI_AUDIO_FREQUENCY
#define COMPANION_PDM_RAW_SAI_AUDIO_FREQUENCY SAI_AUDIO_FREQUENCY_24K
#endif
#ifndef COMPANION_PDM_RAW_SAI_USE_EXPLICIT_MCKDIV
#define COMPANION_PDM_RAW_SAI_USE_EXPLICIT_MCKDIV 1
#endif
#ifndef COMPANION_PDM_RAW_SAI_MCKDIV
#define COMPANION_PDM_RAW_SAI_MCKDIV 31u
#endif
#ifndef COMPANION_PDM_CLOCK_KHZ
#define COMPANION_PDM_CLOCK_KHZ ((MIC_PCM_SAMPLE_RATE_HZ * COMPANION_PDM_DECIMATION_FACTOR) / 1000u)
#endif
#ifndef COMPANION_PDM_PCM_SCALE
#if COMPANION_PDM_USE_HARDWARE_INTERFACE
#define COMPANION_PDM_PCM_SCALE 384
#else
#define COMPANION_PDM_PCM_SCALE 128
#endif
#endif
#ifndef COMPANION_PDM_USE_CIC3_FILTER
#define COMPANION_PDM_USE_CIC3_FILTER 1
#endif
#ifndef COMPANION_PDM_CIC3_CHUNK_ACCUMULATE
#define COMPANION_PDM_CIC3_CHUNK_ACCUMULATE 0
#endif
#if COMPANION_PDM_USE_CIC3_FILTER
#if COMPANION_PDM_CIC3_CHUNK_ACCUMULATE
#define MIC_PDM_FILTER_TEXT "cic3_chunk"
#else
#define MIC_PDM_FILTER_TEXT "cic3"
#endif
#else
#define MIC_PDM_FILTER_TEXT "boxcar"
#endif
#ifndef COMPANION_PDM_BIT_ORDER_LSB
#if COMPANION_PDM_USE_HARDWARE_INTERFACE
#define COMPANION_PDM_BIT_ORDER_LSB 1
#else
#define COMPANION_PDM_BIT_ORDER_LSB 0
#endif
#endif
#ifndef COMPANION_PDM_INVERT_BITS
#define COMPANION_PDM_INVERT_BITS 0
#endif
#ifndef COMPANION_PDM_CLOCK_ENABLE
#define COMPANION_PDM_CLOCK_ENABLE SAI_PDM_CLOCK2_ENABLE
#endif
#ifndef COMPANION_PDM_MIC_PAIRS
#define COMPANION_PDM_MIC_PAIRS 2u
#endif
#ifndef COMPANION_PDM_SLOT_ACTIVE
#define COMPANION_PDM_SLOT_ACTIVE SAI_SLOTACTIVE_1
#endif
#ifndef COMPANION_PDM_DATA_AF
#if COMPANION_PDM_USE_HARDWARE_INTERFACE
#define COMPANION_PDM_DATA_AF GPIO_AF3_SAI1
#else
#define COMPANION_PDM_DATA_AF GPIO_AF13_SAI1
#endif
#endif
#ifndef COMPANION_PDM_RESTART_EACH_BLOCK
#define COMPANION_PDM_RESTART_EACH_BLOCK COMPANION_PDM_USE_HARDWARE_INTERFACE
#endif
#ifndef COMPANION_PDM_RAW_SAI_USE_DMA
#define COMPANION_PDM_RAW_SAI_USE_DMA (!COMPANION_PDM_USE_HARDWARE_INTERFACE)
#endif
#define MIC_PDM_BITS_PER_BATCH (MIC_PCM_SAMPLES_PER_BATCH * COMPANION_PDM_DECIMATION_FACTOR)
#define MIC_PDM_WORDS_PER_BATCH ((MIC_PDM_BITS_PER_BATCH + 31u) / 32u)
#if COMPANION_MIC_BACKEND == COMPANION_MIC_BACKEND_SPH0655_PDM
#define MIC_RAW_WORDS MIC_PDM_WORDS_PER_BATCH
#else
#define MIC_RAW_WORDS MIC_I2S_WORDS
#endif
#if (COMPANION_MIC_BACKEND == COMPANION_MIC_BACKEND_SPH0655_PDM) && COMPANION_PDM_RAW_SAI_USE_DMA
#define MIC_RAW_DMA_WORDS (MIC_RAW_WORDS * 2u)
#define MIC_RAW_DMA_HALF0_READY 0x01u
#define MIC_RAW_DMA_HALF1_READY 0x02u
#endif
#define MIC_CAPTURE_BLOCKS 4u
#ifndef COMPANION_MIC_PREAMP_SHIFT
#if COMPANION_MIC_BACKEND == COMPANION_MIC_BACKEND_SPH0655_PDM
#define COMPANION_MIC_PREAMP_SHIFT 3u
#else
#define COMPANION_MIC_PREAMP_SHIFT 0u
#endif
#endif
#ifndef COMPANION_MIC_SELECTED_SLOT
#define COMPANION_MIC_SELECTED_SLOT 0u
#endif
#ifndef COMPANION_MIC_SLOT_AUTO_SELECT
#define COMPANION_MIC_SLOT_AUTO_SELECT 0
#endif
#ifndef COMPANION_MIC_SD_PULLDOWN
#define COMPANION_MIC_SD_PULLDOWN 1
#endif
#ifndef COMPANION_MIC_CLOCK_STROBING
#define COMPANION_MIC_CLOCK_STROBING SAI_CLOCKSTROBING_FALLINGEDGE
#endif
#define MIC_PREAMP_SHIFT COMPANION_MIC_PREAMP_SHIFT
#define MIC_SELECTED_SLOT (COMPANION_MIC_SELECTED_SLOT < MIC_SLOT_COUNT ? COMPANION_MIC_SELECTED_SLOT : 0u)
#if COMPANION_MIC_SLOT_AUTO_SELECT
#define MIC_SLOT_POLICY_TEXT "auto"
#else
#define MIC_SLOT_POLICY_TEXT "fixed"
#endif
#if COMPANION_MIC_SD_PULLDOWN
#define MIC_SD_PULL_TEXT "pulldown"
#else
#define MIC_SD_PULL_TEXT "nopull"
#endif
#if COMPANION_MIC_CLOCK_STROBING == SAI_CLOCKSTROBING_FALLINGEDGE
#define MIC_CLOCK_STROBING_TEXT "falling"
#elif COMPANION_MIC_CLOCK_STROBING == SAI_CLOCKSTROBING_RISINGEDGE
#define MIC_CLOCK_STROBING_TEXT "rising"
#else
#define MIC_CLOCK_STROBING_TEXT "custom"
#endif

#define FLASH_TEST_ADDRESS 0x00FFF000u
#define FLASH_TEST_SIZE 256u
#define FLASH_BUSY_TIMEOUT_MS 5000u

#define FLASH_RECORDING_MAGIC 0x31434552u
#define FLASH_RECORDING_VERSION 1u
#define FLASH_RECORDING_BASE_PREFERRED 0x00010000u
#define FLASH_UI_ASSETS_BASE 0x00200000u
#define FLASH_UI_ASSETS_SIZE 0x00200000u
#define FLASH_RECORDING_SAMPLE_RATE_HZ 16000u
#define FLASH_RECORDING_BITS_PER_SAMPLE 16u
#define FLASH_RECORDING_BYTES_PER_SECOND \
    ((FLASH_RECORDING_SAMPLE_RATE_HZ * FLASH_RECORDING_BITS_PER_SAMPLE) / 8u)
#define FLASH_RECORDING_DEV_MAX_SECONDS 60u
#define FLASH_RECORDING_MAX_BYTES \
    (FLASH_RECORDING_BYTES_PER_SECOND * FLASH_RECORDING_DEV_MAX_SECONDS)
#ifndef FLASH_RECORDING_STAGE_BLOCKS
#if COMPANION_MIC_BACKEND == COMPANION_MIC_BACKEND_SPH0655_PDM
#define FLASH_RECORDING_STAGE_BLOCKS 450u
#else
#define FLASH_RECORDING_STAGE_BLOCKS 128u
#endif
#endif
#define FLASH_RECORDING_STAGE_BYTES \
    (MIC_PCM_SAMPLES_PER_BATCH * sizeof(int16_t) * FLASH_RECORDING_STAGE_BLOCKS)
#define FLASH_RECORDING_CODEC_PCM16 1u
#define FLASH_RECORDING_SYNC_UNSYNCED 0u
#define FLASH_RECORDING_SYNC_TRANSFER_ACTIVE 1u
#define FLASH_RECORDING_SYNC_TRANSFERRED 2u
#define FLASH_RECORDING_SYNC_DELETED 3u
#define FLASH_RECORDING_SOURCE_MIC_SAI_VALUE 1u

enum {
    COMPANION_RECORDING_CONTROL_START = 1u,
    COMPANION_RECORDING_CONTROL_STOP = 2u,
    COMPANION_RECORDING_CONTROL_CANCEL = 3u,
};

typedef enum {
    OTA_READY_STATE_READY = 0,
    OTA_READY_STATE_BLOCKED = 1,
} ota_ready_state_t;

enum {
    OTA_BLOCKER_RECORDING_ACTIVE = 1u << 0,
    OTA_BLOCKER_TRANSFER_ACTIVE = 1u << 1,
    OTA_BLOCKER_DIAG_EXPORT_ACTIVE = 1u << 2,
    OTA_BLOCKER_LOW_BATTERY = 1u << 3,
    OTA_BLOCKER_WRONG_BOARD_TARGET = 1u << 4,
    OTA_BLOCKER_INVALID_HASH = 1u << 5,
    OTA_BLOCKER_INTERRUPTED_TRANSFER = 1u << 6,
};

typedef struct {
    uint32_t min;
    uint32_t max;
    int64_t sum;
    uint32_t zero_count;
    uint32_t same_count;
    uint32_t crc32;
} raw_stats_t;

typedef struct {
    int16_t min;
    int16_t max;
    int64_t sum;
    uint32_t zero_count;
    uint32_t clipped_count;
    uint32_t crc32;
} pcm_stats_t;

typedef struct {
    uint32_t selected_slot;
    int32_t slot_mean[MIC_SLOT_COUNT];
    int16_t slot_min[MIC_SLOT_COUNT];
    int16_t slot_max[MIC_SLOT_COUNT];
    uint32_t slot_zero_count[MIC_SLOT_COUNT];
    uint32_t slot_ac_peak[MIC_SLOT_COUNT];
    uint64_t slot_ac_energy[MIC_SLOT_COUNT];
    uint32_t preamp_shift;
    uint32_t preamp_clip_count;
} mic_decode_stats_t;

typedef struct {
    const char *name;
    uint32_t prescaler;
    uint32_t sample_shifting;
} flash_qspi_probe_config_t;

typedef struct {
    const char *name;
    GPIO_TypeDef *port;
    uint16_t pin;
    bool last_raw_pressed;
    bool stable_pressed;
    uint32_t last_change_ms;
} board_button_t;

typedef struct {
    uint32_t state[8];
    uint64_t bit_count;
    uint8_t block[64];
    uint32_t block_len;
} comp_sha256_ctx_t;

#pragma pack(push, 1)
typedef struct {
    uint32_t magic;
    uint32_t version;
    uint32_t recording_id;
    uint32_t started_unix_s;
    uint32_t started_tick_ms;
    uint32_t duration_ms;
    uint32_t total_length;
    uint32_t content_crc32;
    uint8_t sha256[COMPANION_RECORDING_FLASH_SHA256_BYTES];
    uint8_t codec;
    uint8_t sync_state;
    uint8_t source_mode;
    uint8_t reserved;
} recording_flash_header_t;
#pragma pack(pop)

typedef struct {
    bool ready;
    bool capture_active;
    bool stored;
    bool write_failed;
    uint32_t base_address;
    uint32_t data_address;
    uint32_t capacity_bytes;
    uint32_t recording_id;
    uint32_t next_recording_id;
    uint32_t started_tick_ms;
    uint32_t bytes_written;
    uint32_t content_crc32;
    uint32_t packet_sequence_next;
    recording_flash_header_t header;
    comp_sha256_ctx_t sha256;
} recording_flash_state_t;

UART_HandleTypeDef hlpuart1;
UART_HandleTypeDef huart1;
DMA_HandleTypeDef hdma_usart1_tx;
#if (COMPANION_MIC_BACKEND == COMPANION_MIC_BACKEND_SPH0655_PDM) && COMPANION_PDM_RAW_SAI_USE_DMA
DMA_HandleTypeDef hdma_sai1_a_rx;
#endif
I2C_HandleTypeDef hi2c3;
IPCC_HandleTypeDef hipcc;
QSPI_HandleTypeDef hqspi;
RNG_HandleTypeDef hrng;
RTC_HandleTypeDef hrtc;
SAI_HandleTypeDef hsai_BlockA1;
SAI_HandleTypeDef hsai_BlockB1;
SPI_HandleTypeDef hspi2;

static comp_recording_fsm_t s_recording_fsm;
static comp_power_policy_t s_power_policy;
static bool s_low_power_stop_allowed;
static comp_qspi_nor_t s_flash;
static companion_screen_assets_stm32wb_t s_screen_assets_adapter;
static companion_touch_ft6336_stm32wb_t s_touch;
typedef struct {
    comp_ft6336_touch_sample_t sample;
    uint32_t timestamp_ms;
} buffered_touch_sample_t;

static comp_screen_menu_t s_screen_menu;
static bool s_touch_last_sample_valid;
static comp_ft6336_touch_sample_t s_touch_last_sample;
static uint32_t s_touch_next_poll_ms;
static uint32_t s_touch_next_recovery_ms;
static uint32_t s_touch_recovery_count;
static uint16_t s_touch_consecutive_failures;
static volatile uint32_t s_touch_irq_count;
static uint32_t s_touch_irq_consumed_count;
static bool s_touch_contact_active;
static uint32_t s_touch_last_sample_log_ms;
static buffered_touch_sample_t
    s_touch_refresh_buffer[TOUCH_REFRESH_BUFFER_CAPACITY];
static uint16_t s_touch_refresh_buffer_read;
static uint16_t s_touch_refresh_buffer_write;
static uint16_t s_touch_refresh_buffer_count;
static uint32_t s_touch_refresh_buffered_count;
static uint32_t s_touch_refresh_buffer_dropped_count;
static uint32_t s_touch_refresh_buffer_coalesced_count;
static bool s_touch_refresh_capture_active;
static bool s_touch_refresh_latest_contact_valid;
static buffered_touch_sample_t s_touch_refresh_latest_contact;
static bool s_touch_wait_buffer_selftest_pass;
static comp_touch_gesture_state_t s_touch_gesture;
static bool s_menu_entry_pending;
static comp_screen_menu_view_t s_menu_entry_target;
static uint32_t s_menu_entry_due_ms;
static bool s_menu_home_press_active;
static uint8_t s_menu_home_press_item;
static bool s_menu_home_press_candidate;
static uint8_t s_menu_home_press_candidate_item;
static uint32_t s_menu_home_press_candidate_due_ms;
static bool s_screen_maintenance_pending;
static uint32_t s_screen_maintenance_due_ms;
static bool s_low_power_idle_pose_attempted;
static bool s_low_power_touch_wake_requested;
#if COMPANION_SCREEN_MAINTENANCE_DIAGNOSTIC
static uint32_t s_maintenance_diagnostic_started_ms;
static bool s_maintenance_diagnostic_enqueued;
#endif
static recording_flash_state_t s_recording_flash;
static uint8_t s_recording_flash_stage[FLASH_RECORDING_STAGE_BYTES];
static uint32_t s_recording_flash_stage_len;
static const char *s_error_stage = "reset";
static bool s_uart_ready;
static board_button_t s_buttons[] = {
    {"SW1", BOARD_SW1_GPIO_PORT, BOARD_SW1_PIN, false, false, 0u},
    {"SW2", BOARD_SW2_GPIO_PORT, BOARD_SW2_PIN, false, false, 0u},
    {"SW3", BOARD_SW3_GPIO_PORT, BOARD_SW3_PIN, false, false, 0u},
};
static uint32_t s_manual_recording_block_count;
static bool s_ble_link_ready;
static bool s_ble_session_active;
static bool s_ble_type_ready_autostream_active;
static bool s_ble_type_ready_autostream_pending;
static uint32_t s_ble_type_ready_autostream_blocks_remaining;
static uint32_t s_ble_type_ready_autostream_pending_blocks;
static uint16_t s_ble_type_ready_autostream_pcm_bytes;
static uint16_t s_ble_type_ready_autostream_pending_pcm_bytes;
static uint32_t s_ble_session_id;
#if (COMPANION_MIC_BACKEND == COMPANION_MIC_BACKEND_SPH0655_PDM) && COMPANION_PDM_RAW_SAI_USE_DMA
static uint32_t s_pdm_raw_dma_words[MIC_RAW_DMA_WORDS];
static volatile uint8_t s_pdm_raw_dma_ready_mask;
static volatile uint8_t s_pdm_raw_dma_last_completed_half;
static volatile uint32_t s_pdm_raw_dma_overrun_count;
static bool s_pdm_raw_dma_started;
#endif
#if (COMPANION_MIC_BACKEND == COMPANION_MIC_BACKEND_SPH0655_PDM) && COMPANION_PDM_USE_CIC3_FILTER
typedef struct {
    int8_t sum;
    int16_t weighted1;
    int16_t weighted2;
} pdm_cic3_byte_moments_t;

typedef struct {
    int64_t integrator1;
    int64_t integrator2;
    int64_t integrator3;
    int64_t comb1;
    int64_t comb2;
    int64_t comb3;
} pdm_cic3_state_t;

static pdm_cic3_state_t s_pdm_cic3_state;
static pdm_cic3_byte_moments_t s_pdm_cic3_byte_moments[256];
static bool s_pdm_cic3_lookup_ready;
#endif

#if COMPANION_LOW_POWER_ENABLE
/* CubeWB's trace module supplies _write only when trace is enabled. The
 * low-power build intentionally disables that module, so keep bounded
 * diagnostic output on the already-configured USART without re-enabling its
 * periodic trace infrastructure. */
int _write(int file, char *data, int length)
{
    (void)file;
    if (!s_uart_ready || data == NULL || length <= 0) {
        return 0;
    }
    return HAL_UART_Transmit(&huart1,
                             (uint8_t *)data,
                             (uint16_t)length,
                             100u) == HAL_OK
               ? length
               : 0;
}
#endif

static void SystemClock_Config(void);
static void PeriphCommonClock_Config(void);
static void MX_GPIO_Init(void);
static void MX_DMA_Init(void);
static void MX_IPCC_Init(void);
static void MX_RNG_Init(void);
static void MX_RTC_Init(void);
static void MX_RF_Init(void);
void MX_USART1_UART_Init(void);
static void MX_I2C3_Init(void);
static void MX_QUADSPI_Init(void);
static void MX_SAI1_Init(void);
static void MX_SPI2_Init(void);

#ifndef COMPANION_SCREEN_ROTATION_DEGREES
#define COMPANION_SCREEN_ROTATION_DEGREES 0u
#endif

#if COMPANION_SCREEN_ROTATION_DEGREES != 0u && \
    COMPANION_SCREEN_ROTATION_DEGREES != 180u
#error "Companion screen rotation must be 0 or 180 degrees"
#endif

static void init_board_buttons(void);
static void disable_board_button_exti_irqs(void);
static void poll_board_buttons(void);
static void handle_button_press(size_t index);
static void init_touch_debug(void);
static void poll_touch_debug(void);
static void print_touch_health(void);
static void request_low_power_touch_wake(void);
static bool recover_touch_i2c3_bus(void);
static void reset_touch_controller(void);
static void capture_touch_during_display_wait(void *context, uint32_t now_ms);
static void process_touch_debug_sample(const comp_ft6336_touch_sample_t *sample,
                                       uint32_t now_ms);
static void push_buffered_touch_sample(const comp_ft6336_touch_sample_t *sample,
                                       uint32_t now_ms);
static bool pop_buffered_touch_sample(buffered_touch_sample_t *entry);
static void reset_touch_refresh_buffer(void);
static void flush_buffered_touch_latest_contact(void);
static void buffer_touch_sample_during_panel_wait(
    const comp_ft6336_touch_sample_t *sample,
    uint32_t now_ms);
static bool touch_wait_buffer_self_test(void);
static void handle_touch_menu_sample(const comp_ft6336_touch_sample_t *sample,
                                     uint16_t logical_x,
                                     uint16_t logical_y,
                                     uint32_t now_ms);
static void schedule_touch_screen_maintenance(uint32_t now_ms);
static void cancel_touch_screen_maintenance(void);
static void process_touch_screen_maintenance(uint32_t now_ms);
static void process_menu_entry_transition(uint32_t now_ms);
static void update_low_power_policy(void);
static void start_recording(comp_recording_source_t source, const char *reason);
static void stop_recording(comp_recording_source_t source, const char *reason);
static void cancel_recording(comp_recording_source_t source, const char *reason);
static void start_user_recording(comp_recording_source_t source, const char *reason);
static void stop_user_recording(comp_recording_source_t source, const char *reason);
static void toggle_touch_recording(void);
static void start_manual_recording(void);
static void stop_manual_recording(const char *reason);
static void cancel_manual_recording(void);
static void request_ble_type_ready_autostream(const char *reason,
                                              uint32_t blocks,
                                              uint16_t pcm_bytes);
static void clear_ble_type_ready_autostream(void);
static bool ble_audio_stream_enabled_for_recording(void);
static bool recording_loop_should_process_app(uint32_t block_index);
static void start_ble_session_if_ready(const char *reason);
static void end_ble_session_if_active(bool cancel, const char *reason);
#if COMPANION_MIC_BACKEND == COMPANION_MIC_BACKEND_SPH0655_PDM
static void pdm_decoder_reset(void);
#if COMPANION_PDM_RAW_SAI_USE_DMA
static void pdm_raw_dma_reset_stream(void);
static HAL_StatusTypeDef pdm_raw_dma_read_block(uint32_t *raw_words,
                                                uint32_t timeout_ms,
                                                uint32_t *overruns);
#endif
#endif
static void run_manual_probe_request(void);
static void run_flash_probe(void);
static HAL_StatusTypeDef apply_flash_qspi_probe_config(const flash_qspi_probe_config_t *config);
static void flash_release_powerdown(void);
static HAL_StatusTypeDef qspi_read_command(uint8_t instruction,
                                           uint32_t address_mode,
                                           uint32_t address,
                                           uint32_t data_mode,
                                           uint32_t dummy_cycles,
                                           uint8_t *data,
                                           uint32_t length);
static HAL_StatusTypeDef qspi_no_data_command(uint8_t instruction);
static void run_flash_write_read_smoke(uint32_t jedec);
static void run_flash_bitbang_probe(void);
static void run_flash_bitbang_variant(const char *name, bool swap_io0_io1);
static uint8_t bitbang_spi_transfer(GPIO_TypeDef *mosi_port,
                                    uint16_t mosi_pin,
                                    GPIO_TypeDef *miso_port,
                                    uint16_t miso_pin,
                                    uint8_t tx);
static void configure_flash_pins_for_bitbang(bool swap_io0_io1);
static void run_ota_readiness_probe(void);
static void run_microphone_probe(void);
static void print_diag_tail(void);
static bool capture_microphone_block(uint32_t block_index, bool verbose, const char *tag);
static void print_recording_summary(const char *tag);
static bool recording_flash_ensure_ready(void);
static bool recording_flash_begin_capture(uint16_t max_seconds);
static void recording_flash_append_pcm(const uint8_t *pcm, uint32_t length);
static bool recording_flash_write_bytes(const uint8_t *data, uint32_t length);
static bool recording_flash_flush_stage(void);
static bool recording_flash_finalize_capture(void);
static bool recording_flash_load_header(void);
static void recording_flash_clear_state(void);
static bool recording_flash_erase_region(void);
static uint32_t recording_flash_sector_count(uint32_t bytes);
static uint32_t recording_flash_total_region_bytes(void);
static uint32_t recording_flash_limit_bytes_for_seconds(uint16_t max_seconds);
static uint32_t recording_flash_compute_base(const comp_qspi_nor_info_t *info);
static void sha256_init(comp_sha256_ctx_t *ctx);
static void sha256_update(comp_sha256_ctx_t *ctx, const uint8_t *data, uint32_t length);
static void sha256_final(comp_sha256_ctx_t *ctx,
                         uint8_t digest[COMPANION_RECORDING_FLASH_SHA256_BYTES]);
static void write_le32(uint8_t *out, uint32_t value);

static uint32_t diag_clock_ms(void *context)
{
    (void)context;
    return HAL_GetTick();
}

int __io_putchar(int ch)
{
    uint8_t byte = (uint8_t)ch;
    (void)HAL_UART_Transmit(&huart1, &byte, 1u, 1000u);
    return ch;
}

static uint32_t crc32_update(uint32_t crc, const uint8_t *data, uint32_t len)
{
    crc = ~crc;
    for (uint32_t i = 0; i < len; ++i) {
        crc ^= data[i];
        for (uint32_t bit = 0; bit < 8u; ++bit) {
            uint32_t mask = 0u - (crc & 1u);
            crc = (crc >> 1) ^ (0xEDB88320u & mask);
        }
    }
    return ~crc;
}

#if COMPANION_SCREEN_ASSET_PROVISION
static bool screen_asset_flash_crc(uint32_t address,
                                   uint32_t length,
                                   uint32_t *out_crc)
{
    uint8_t buffer[256];
    uint32_t offset = 0u;
    uint32_t crc = 0u;

    if (out_crc == NULL) {
        return false;
    }
    while (offset < length) {
        uint32_t chunk = length - offset;
        if (chunk > sizeof(buffer)) {
            chunk = sizeof(buffer);
        }
        if (comp_qspi_nor_read(&s_flash, address + offset, buffer, chunk) !=
            COMP_QSPI_NOR_OK) {
            return false;
        }
        crc = crc32_update(crc, buffer, chunk);
        offset += chunk;
    }
    *out_crc = crc;
    return true;
}

static void screen_asset_provision(void)
{
    comp_qspi_nor_info_t info;
    uint32_t current_crc = 0u;
    uint32_t verify_crc = 0u;
    uint32_t erase_bytes;
    comp_qspi_nor_status_t status;

    _Static_assert(sizeof(companion_screen_asset_provision_blob) ==
                       COMPANION_SCREEN_ASSET_PROVISION_BLOB_SIZE,
                   "generated screen asset size mismatch");
    status = comp_qspi_nor_probe(&s_flash, &info);
    if (status != COMP_QSPI_NOR_OK || info.sector_size != 4096u ||
        COMPANION_SCREEN_ASSET_PROVISION_BLOB_SIZE > FLASH_UI_ASSETS_SIZE ||
        FLASH_UI_ASSETS_BASE > info.size_bytes ||
        FLASH_UI_ASSETS_SIZE > info.size_bytes - FLASH_UI_ASSETS_BASE) {
        printf("[screen-assets-provision] result=blocked probe=%s flash_bytes=%lu sector=%lu blob_bytes=%lu\r\n",
               comp_qspi_nor_status_name(status),
               (unsigned long)(status == COMP_QSPI_NOR_OK ? info.size_bytes : 0u),
               (unsigned long)(status == COMP_QSPI_NOR_OK ? info.sector_size : 0u),
               (unsigned long)COMPANION_SCREEN_ASSET_PROVISION_BLOB_SIZE);
        return;
    }

    bool current_read = screen_asset_flash_crc(
        FLASH_UI_ASSETS_BASE,
        COMPANION_SCREEN_ASSET_PROVISION_BLOB_SIZE,
        &current_crc);
    printf("[screen-assets-provision] begin base=0x%08lX blob_bytes=%lu expected_crc=0x%08lX current=%s:0x%08lX\r\n",
           (unsigned long)FLASH_UI_ASSETS_BASE,
           (unsigned long)COMPANION_SCREEN_ASSET_PROVISION_BLOB_SIZE,
           (unsigned long)COMPANION_SCREEN_ASSET_PROVISION_BLOB_CRC32,
           current_read ? "read" : "error",
           (unsigned long)current_crc);
    if (current_read && current_crc == COMPANION_SCREEN_ASSET_PROVISION_BLOB_CRC32) {
        printf("[screen-assets-provision] result=pass action=already_current crc=0x%08lX\r\n",
               (unsigned long)current_crc);
        return;
    }

    erase_bytes = (COMPANION_SCREEN_ASSET_PROVISION_BLOB_SIZE + info.sector_size - 1u) /
                  info.sector_size * info.sector_size;
    for (uint32_t offset = 0u; offset < erase_bytes; offset += info.sector_size) {
        status = comp_qspi_nor_erase_4k(&s_flash, FLASH_UI_ASSETS_BASE + offset);
        if (status != COMP_QSPI_NOR_OK) {
            printf("[screen-assets-provision] result=fail stage=erase address=0x%08lX status=%s\r\n",
                   (unsigned long)(FLASH_UI_ASSETS_BASE + offset),
                   comp_qspi_nor_status_name(status));
            return;
        }
    }
    status = comp_qspi_nor_write(&s_flash,
                                 FLASH_UI_ASSETS_BASE,
                                 companion_screen_asset_provision_blob,
                                 COMPANION_SCREEN_ASSET_PROVISION_BLOB_SIZE);
    if (status != COMP_QSPI_NOR_OK) {
        printf("[screen-assets-provision] result=fail stage=write status=%s\r\n",
               comp_qspi_nor_status_name(status));
        return;
    }
    bool verify_read = screen_asset_flash_crc(
        FLASH_UI_ASSETS_BASE,
        COMPANION_SCREEN_ASSET_PROVISION_BLOB_SIZE,
        &verify_crc);
    bool pass = verify_read &&
                verify_crc == COMPANION_SCREEN_ASSET_PROVISION_BLOB_CRC32;
    printf("[screen-assets-provision] result=%s action=erase_write_verify erased_bytes=%lu verify=%s:0x%08lX\r\n",
           pass ? "pass" : "fail",
           (unsigned long)erase_bytes,
           verify_read ? "read" : "error",
           (unsigned long)verify_crc);
}
#endif

static uint32_t rotr32(uint32_t value, uint32_t bits)
{
    return (value >> bits) | (value << (32u - bits));
}

static void sha256_process_block(comp_sha256_ctx_t *ctx, const uint8_t block[64])
{
    static const uint32_t k[64] = {
        0x428A2F98u, 0x71374491u, 0xB5C0FBCFu, 0xE9B5DBA5u,
        0x3956C25Bu, 0x59F111F1u, 0x923F82A4u, 0xAB1C5ED5u,
        0xD807AA98u, 0x12835B01u, 0x243185BEu, 0x550C7DC3u,
        0x72BE5D74u, 0x80DEB1FEu, 0x9BDC06A7u, 0xC19BF174u,
        0xE49B69C1u, 0xEFBE4786u, 0x0FC19DC6u, 0x240CA1CCu,
        0x2DE92C6Fu, 0x4A7484AAu, 0x5CB0A9DCu, 0x76F988DAu,
        0x983E5152u, 0xA831C66Du, 0xB00327C8u, 0xBF597FC7u,
        0xC6E00BF3u, 0xD5A79147u, 0x06CA6351u, 0x14292967u,
        0x27B70A85u, 0x2E1B2138u, 0x4D2C6DFCu, 0x53380D13u,
        0x650A7354u, 0x766A0ABBu, 0x81C2C92Eu, 0x92722C85u,
        0xA2BFE8A1u, 0xA81A664Bu, 0xC24B8B70u, 0xC76C51A3u,
        0xD192E819u, 0xD6990624u, 0xF40E3585u, 0x106AA070u,
        0x19A4C116u, 0x1E376C08u, 0x2748774Cu, 0x34B0BCB5u,
        0x391C0CB3u, 0x4ED8AA4Au, 0x5B9CCA4Fu, 0x682E6FF3u,
        0x748F82EEu, 0x78A5636Fu, 0x84C87814u, 0x8CC70208u,
        0x90BEFFFAu, 0xA4506CEBu, 0xBEF9A3F7u, 0xC67178F2u,
    };
    uint32_t w[64];
    for (uint32_t i = 0u; i < 16u; ++i) {
        w[i] = ((uint32_t)block[i * 4u] << 24) |
               ((uint32_t)block[(i * 4u) + 1u] << 16) |
               ((uint32_t)block[(i * 4u) + 2u] << 8) |
               (uint32_t)block[(i * 4u) + 3u];
    }
    for (uint32_t i = 16u; i < 64u; ++i) {
        uint32_t s0 = rotr32(w[i - 15u], 7u) ^ rotr32(w[i - 15u], 18u) ^ (w[i - 15u] >> 3);
        uint32_t s1 = rotr32(w[i - 2u], 17u) ^ rotr32(w[i - 2u], 19u) ^ (w[i - 2u] >> 10);
        w[i] = w[i - 16u] + s0 + w[i - 7u] + s1;
    }

    uint32_t a = ctx->state[0];
    uint32_t b = ctx->state[1];
    uint32_t c = ctx->state[2];
    uint32_t d = ctx->state[3];
    uint32_t e = ctx->state[4];
    uint32_t f = ctx->state[5];
    uint32_t g = ctx->state[6];
    uint32_t h = ctx->state[7];

    for (uint32_t i = 0u; i < 64u; ++i) {
        uint32_t s1 = rotr32(e, 6u) ^ rotr32(e, 11u) ^ rotr32(e, 25u);
        uint32_t ch = (e & f) ^ ((~e) & g);
        uint32_t temp1 = h + s1 + ch + k[i] + w[i];
        uint32_t s0 = rotr32(a, 2u) ^ rotr32(a, 13u) ^ rotr32(a, 22u);
        uint32_t maj = (a & b) ^ (a & c) ^ (b & c);
        uint32_t temp2 = s0 + maj;
        h = g;
        g = f;
        f = e;
        e = d + temp1;
        d = c;
        c = b;
        b = a;
        a = temp1 + temp2;
    }

    ctx->state[0] += a;
    ctx->state[1] += b;
    ctx->state[2] += c;
    ctx->state[3] += d;
    ctx->state[4] += e;
    ctx->state[5] += f;
    ctx->state[6] += g;
    ctx->state[7] += h;
}

static void sha256_init(comp_sha256_ctx_t *ctx)
{
    memset(ctx, 0, sizeof(*ctx));
    ctx->state[0] = 0x6A09E667u;
    ctx->state[1] = 0xBB67AE85u;
    ctx->state[2] = 0x3C6EF372u;
    ctx->state[3] = 0xA54FF53Au;
    ctx->state[4] = 0x510E527Fu;
    ctx->state[5] = 0x9B05688Cu;
    ctx->state[6] = 0x1F83D9ABu;
    ctx->state[7] = 0x5BE0CD19u;
}

static void sha256_update(comp_sha256_ctx_t *ctx, const uint8_t *data, uint32_t length)
{
    if (ctx == NULL || data == NULL || length == 0u) {
        return;
    }
    ctx->bit_count += ((uint64_t)length * 8u);
    for (uint32_t i = 0u; i < length; ++i) {
        ctx->block[ctx->block_len++] = data[i];
        if (ctx->block_len == sizeof(ctx->block)) {
            sha256_process_block(ctx, ctx->block);
            ctx->block_len = 0u;
        }
    }
}

static void sha256_final(comp_sha256_ctx_t *ctx,
                         uint8_t digest[COMPANION_RECORDING_FLASH_SHA256_BYTES])
{
    if (ctx == NULL || digest == NULL) {
        return;
    }

    uint64_t bit_count = ctx->bit_count;
    ctx->block[ctx->block_len++] = 0x80u;
    if (ctx->block_len > 56u) {
        while (ctx->block_len < sizeof(ctx->block)) {
            ctx->block[ctx->block_len++] = 0u;
        }
        sha256_process_block(ctx, ctx->block);
        ctx->block_len = 0u;
    }
    while (ctx->block_len < 56u) {
        ctx->block[ctx->block_len++] = 0u;
    }
    for (int i = 7; i >= 0; --i) {
        ctx->block[ctx->block_len++] = (uint8_t)(bit_count >> ((uint32_t)i * 8u));
    }
    sha256_process_block(ctx, ctx->block);

    for (uint32_t i = 0u; i < 8u; ++i) {
        digest[(i * 4u)] = (uint8_t)(ctx->state[i] >> 24);
        digest[(i * 4u) + 1u] = (uint8_t)(ctx->state[i] >> 16);
        digest[(i * 4u) + 2u] = (uint8_t)(ctx->state[i] >> 8);
        digest[(i * 4u) + 3u] = (uint8_t)ctx->state[i];
    }
}

static void write_le32(uint8_t *out, uint32_t value)
{
    out[0] = (uint8_t)value;
    out[1] = (uint8_t)(value >> 8);
    out[2] = (uint8_t)(value >> 16);
    out[3] = (uint8_t)(value >> 24);
}

static const char *hal_status_name(HAL_StatusTypeDef status)
{
    switch (status) {
    case HAL_OK:
        return "ok";
    case HAL_ERROR:
        return "error";
    case HAL_BUSY:
        return "busy";
    case HAL_TIMEOUT:
        return "timeout";
    default:
        return "unknown";
    }
}

int main(void)
{
    s_error_stage = "HAL_Init";
    HAL_Init();
    s_error_stage = "MX_APPE_Config";
    MX_APPE_Config();
    s_error_stage = "SystemClock_Config";
    SystemClock_Config();
    s_error_stage = "PeriphCommonClock_Config";
    PeriphCommonClock_Config();
    s_error_stage = "MX_IPCC_Init";
    MX_IPCC_Init();

    s_error_stage = "MX_GPIO_Init";
    MX_GPIO_Init();
    s_error_stage = "MX_DMA_Init";
    MX_DMA_Init();
    s_error_stage = "MX_I2C3_Init";
    MX_I2C3_Init();
    printf("[stage] i2c3 ok scl=PC0 sda=PB11\r\n");
    s_error_stage = "MX_RTC_Init";
    MX_RTC_Init();
    s_error_stage = "MX_RNG_Init";
    MX_RNG_Init();
    s_error_stage = "MX_RF_Init";
    MX_RF_Init();
    s_error_stage = "MX_SPI2_Init";
    MX_SPI2_Init();
    printf("[stage] spi2 ok sck=PA9 mosi=PC1 miso=PC2 cs=PA6\r\n");
    s_error_stage = "MX_USART1_UART_Init";
    MX_USART1_UART_Init();
    s_uart_ready = true;
    printf("\r\n[stage] uart ok\r\n");
    init_touch_debug();
    comp_screen_menu_init(&s_screen_menu);
    s_error_stage = "MX_QUADSPI_Init";
    MX_QUADSPI_Init();
    comp_qspi_nor_init(&s_flash, &hqspi);
    printf("[stage] qspi ok\r\n");
#if COMPANION_SCREEN_ASSET_PROVISION
    screen_asset_provision();
#endif
    s_error_stage = "MX_SAI1_Init";
    MX_SAI1_Init();
    printf("[stage] sai1 ok clk=%lu a_cr1=0x%08lX a_frcr=0x%08lX a_slotr=0x%08lX b_cr1=0x%08lX\r\n",
           (unsigned long)HAL_RCCEx_GetPeriphCLKFreq(RCC_PERIPHCLK_SAI1),
           (unsigned long)SAI1_Block_A->CR1,
           (unsigned long)SAI1_Block_A->FRCR,
           (unsigned long)SAI1_Block_A->SLOTR,
           (unsigned long)SAI1_Block_B->CR1);

    s_error_stage = "diag_recording_init";
    comp_diag_log_init();
    comp_diag_log_set_clock(diag_clock_ms, NULL);
    comp_recording_fsm_init(&s_recording_fsm);

    comp_diag_log_record_code(COMP_DIAG_EVT_BOOT_START,
                              COMP_DIAG_SEV_INFO,
                              0x57423535u,
                              HAL_GetTick(),
                              0u,
                              0u);

    printf("\r\n[boot] Companion NUCLEO-WB55RG bringup\r\n");
    printf("[boot] uart=USART1 PB6/PB7 115200 flash=QSPI-2IO PA2/PA3/PB9/PB8 spi2=PA9/PC1/PC2 cs=PA6 hz=%lu i2c3=PC0/PB11 touch_irq=PC6 touch_reset=PC10\r\n",
           (unsigned long)BOARD_EPAPER_SPI_HZ);
    printf("[boot] mic=SAI1A PA8/PB12/PC3 speaker=SAI1B PB3/PA4/PA5 max98357_sd=PA15\r\n");
#if COMPANION_MIC_BACKEND == COMPANION_MIC_BACKEND_SPH0655_PDM
    printf("[boot] mic=sph0655_pdm%luk_to_pcm%lu_soft_decim%lu_scale%d raw_fs=%lu mckdiv=%lu filter=%s clock=0x%08lX slot_active=0x%08lX data_af=0x%02X preamp%lu listener_reuse=pdm_backend\r\n",
           (unsigned long)COMPANION_PDM_CLOCK_KHZ,
           (unsigned long)MIC_PCM_SAMPLE_RATE_HZ,
           (unsigned long)COMPANION_PDM_DECIMATION_FACTOR,
           (int)COMPANION_PDM_PCM_SCALE,
           (unsigned long)COMPANION_PDM_RAW_SAI_AUDIO_FREQUENCY,
           (unsigned long)COMPANION_PDM_RAW_SAI_MCKDIV,
           MIC_PDM_FILTER_TEXT,
           (unsigned long)COMPANION_PDM_CLOCK_ENABLE,
           (unsigned long)COMPANION_PDM_SLOT_ACTIVE,
           (unsigned int)COMPANION_PDM_DATA_AF,
           (unsigned long)(1u << MIC_PREAMP_SHIFT));
#else
    printf("[boot] mic=sph0645_i2s%lu_to_pcm%lu_slot%lu_%s_sd_%s_edge_%s_dc_preamp%lu listener_v2_sph0655_pdm=separate_backend ble=companion_vka1 ota=ble_package_ready\r\n",
           (unsigned long)MIC_I2S_SAMPLE_RATE_HZ,
           (unsigned long)MIC_PCM_SAMPLE_RATE_HZ,
           (unsigned long)MIC_SELECTED_SLOT,
           MIC_SLOT_POLICY_TEXT,
           MIC_SD_PULL_TEXT,
           MIC_CLOCK_STROBING_TEXT,
           (unsigned long)(1u << MIC_PREAMP_SHIFT));
#endif
    printf("[boot] buttons: SW1=PC4 flash+ota+mic+diag probe, SW2=PD0 cancel/recover, SW3=PD1 start/stop recording\r\n");

    s_error_stage = "MX_APPE_Init";
    MX_APPE_Init();
    printf("[stage] ble app init requested name=companion service=VKA1\r\n");
    comp_power_policy_init(&s_power_policy);
    comp_power_policy_set_touch_wake_ready(
        &s_power_policy,
        COMPANION_TOUCH_INT_WIRED != 0u && s_touch.interrupt_mode_valid);
    UTIL_LPM_SetStopMode(1u << CFG_LPM_APP, UTIL_LPM_DISABLE);
    init_board_buttons();

#if COMPANION_RUN_BOOT_SELFTESTS
    printf("\r\n[tick] boot_selftest t_ms=%lu\r\n", (unsigned long)HAL_GetTick());
    MX_APPE_Process();
    run_flash_probe();
    MX_APPE_Process();
    run_ota_readiness_probe();
    MX_APPE_Process();
    run_microphone_probe();
    MX_APPE_Process();
    print_diag_tail();
#else
    printf("[boot] boot_selftests=skipped reason=production_ble_path\r\n");
    MX_APPE_Process();
#endif

    comp_power_policy_set_blocker(&s_power_policy, COMP_POWER_BLOCKER_BOOT, false);
    /* Preserve the configured FT6336/TP_INT state before the normal idle
     * path can enter Stop and defer its periodic heartbeat. */
    print_touch_health();
    update_low_power_policy();
    printf("[power] policy_selftest=%s touch_irq_wake=%s lpm=%s\r\n",
           comp_power_policy_self_test() ? "pass" : "fail",
           COMPANION_TOUCH_INT_WIRED != 0u && s_touch.interrupt_mode_valid
               ? "ready"
               : "fallback_poll",
           CFG_LPM_SUPPORTED ? "enabled" : "disabled");

    uint32_t last_heartbeat_ms = HAL_GetTick();
#if COMPANION_SCREEN_MAINTENANCE_DIAGNOSTIC
    s_maintenance_diagnostic_started_ms = 0u;
    s_maintenance_diagnostic_enqueued = false;
#endif
    while (1) {
        if (s_recording_fsm.state == COMP_RECORDING_STATE_RECORDING) {
            update_low_power_policy();
            bool process_app =
                recording_loop_should_process_app(s_manual_recording_block_count);
            if (process_app) {
                MX_APPE_Process();
                if (s_recording_fsm.state != COMP_RECORDING_STATE_RECORDING) {
                    continue;
                }
            }
            poll_board_buttons();
            poll_touch_debug();
            if (s_recording_fsm.state != COMP_RECORDING_STATE_RECORDING) {
                continue;
            }

            if (!s_ble_session_active &&
                s_recording_fsm.active_source == COMP_RECORDING_SOURCE_HOST_BLE_CONTROL &&
                ble_audio_stream_enabled_for_recording() &&
                Companion_BleAudio_IsReady()) {
                start_ble_session_if_ready("recording_loop");
            }

            uint32_t block_index = s_manual_recording_block_count;
            bool log_timing = (block_index % MANUAL_RECORDING_LOG_EVERY_BLOCKS) == 0u;
            bool collect_diagnostics =
                (block_index % MANUAL_RECORDING_DIAGNOSTIC_EVERY_BLOCKS) == 0u;
            uint32_t capture_start_ms = HAL_GetTick();
            bool captured = capture_microphone_block(block_index,
                                                     collect_diagnostics,
                                                     "mic-manual");
            uint32_t capture_elapsed_ms = HAL_GetTick() - capture_start_ms;
            if (log_timing) {
                printf("[mic-loop] block=%lu capture_ms=%lu diag=%u app_pump=%u ble_stream=%u\r\n",
                       (unsigned long)block_index,
                       (unsigned long)capture_elapsed_ms,
                       collect_diagnostics ? 1u : 0u,
                       process_app ? 1u : 0u,
                       ble_audio_stream_enabled_for_recording() ? 1u : 0u);
            }
            s_manual_recording_block_count++;
            if (captured &&
                s_ble_session_active &&
                s_ble_type_ready_autostream_active &&
                s_ble_type_ready_autostream_blocks_remaining > 0u) {
                s_ble_type_ready_autostream_blocks_remaining--;
                if (s_ble_type_ready_autostream_blocks_remaining == 0u &&
                    s_recording_fsm.state == COMP_RECORDING_STATE_RECORDING) {
                    s_ble_type_ready_autostream_active = false;
                    MX_APPE_Process();
                    HAL_Delay(40u);
                    MX_APPE_Process();
                    stop_recording(COMP_RECORDING_SOURCE_HOST_BLE_CONTROL,
                                   "ble_type_ready_autostream");
                }
            }
            if (ble_audio_stream_enabled_for_recording()) {
                MX_APPE_Process();
            }
            continue;
        }

        update_low_power_policy();
        MX_APPE_Process();
        poll_board_buttons();
        poll_touch_debug();

        uint32_t now = HAL_GetTick();
#if COMPANION_SCREEN_MAINTENANCE_DIAGNOSTIC
        if (s_maintenance_diagnostic_started_ms == 0u &&
            Companion_Screen_IsReady()) {
            s_maintenance_diagnostic_started_ms = now;
            Companion_Screen_MenuRequest(COMP_SCREEN_MENU_VIEW_HOME,
                                         0u,
                                         COMP_SCREEN_MENU_LANGUAGE_ZH,
                                         0u);
            printf("[screen] maintenance_diagnostic start delay_ms=%lu\r\n",
                   (unsigned long)COMPANION_SCREEN_MAINTENANCE_DIAGNOSTIC_DELAY_MS);
        } else if (!s_maintenance_diagnostic_enqueued &&
            s_maintenance_diagnostic_started_ms != 0u &&
            now - s_maintenance_diagnostic_started_ms >=
                COMPANION_SCREEN_MAINTENANCE_DIAGNOSTIC_DELAY_MS) {
            bool queued = Companion_Screen_MenuMaintenance();

            s_maintenance_diagnostic_enqueued = true;
            printf("[screen] maintenance_diagnostic enqueue=%u elapsed_ms=%lu\r\n",
                   queued ? 1u : 0u,
                   (unsigned long)(now - s_maintenance_diagnostic_started_ms));
        }
#endif
        if ((now - last_heartbeat_ms) >= HEARTBEAT_PERIOD_MS) {
            last_heartbeat_ms = now;
            printf("\r\n[tick] t_ms=%lu state=%s buttons=ready raw=SW1:%u SW2:%u SW3:%u\r\n",
                   (unsigned long)now,
                   comp_recording_state_name(s_recording_fsm.state),
                   HAL_GPIO_ReadPin(BOARD_SW1_GPIO_PORT, BOARD_SW1_PIN) == GPIO_PIN_SET ? 1u : 0u,
                   HAL_GPIO_ReadPin(BOARD_SW2_GPIO_PORT, BOARD_SW2_PIN) == GPIO_PIN_SET ? 1u : 0u,
                   HAL_GPIO_ReadPin(BOARD_SW3_GPIO_PORT, BOARD_SW3_PIN) == GPIO_PIN_SET ? 1u : 0u);
            print_touch_health();
        }
        update_low_power_policy();
        MX_APPE_Process();
        if (!s_low_power_stop_allowed) {
            /* Active touch, a display deadline, recording, or the no-INT
             * fallback still needs a short polling cadence.  The stable
             * touch-INT idle path returns to CubeWB LPM without a SysTick
             * wake every 10 ms. */
            HAL_Delay(BUTTON_IDLE_POLL_MS);
        }
    }
}

static bool button_is_pressed(const board_button_t *button)
{
    return HAL_GPIO_ReadPin(button->port, button->pin) == GPIO_PIN_RESET;
}

static void init_board_buttons(void)
{
    disable_board_button_exti_irqs();
    MX_GPIO_Init();
    for (size_t i = 0u; i < sizeof(s_buttons) / sizeof(s_buttons[0]); ++i) {
        bool pressed = button_is_pressed(&s_buttons[i]);
        s_buttons[i].last_raw_pressed = pressed;
        s_buttons[i].stable_pressed = pressed;
        s_buttons[i].last_change_ms = HAL_GetTick();
    }
    printf("[button] gpio_poll_ready raw=SW1:%u SW2:%u SW3:%u\r\n",
           HAL_GPIO_ReadPin(BOARD_SW1_GPIO_PORT, BOARD_SW1_PIN) == GPIO_PIN_SET ? 1u : 0u,
           HAL_GPIO_ReadPin(BOARD_SW2_GPIO_PORT, BOARD_SW2_PIN) == GPIO_PIN_SET ? 1u : 0u,
           HAL_GPIO_ReadPin(BOARD_SW3_GPIO_PORT, BOARD_SW3_PIN) == GPIO_PIN_SET ? 1u : 0u);
}

static void disable_board_button_exti_irqs(void)
{
    HAL_NVIC_DisableIRQ(EXTI4_IRQn);
    HAL_NVIC_ClearPendingIRQ(EXTI4_IRQn);
    HAL_NVIC_DisableIRQ(EXTI0_IRQn);
    HAL_NVIC_ClearPendingIRQ(EXTI0_IRQn);
    HAL_NVIC_DisableIRQ(EXTI1_IRQn);
    HAL_NVIC_ClearPendingIRQ(EXTI1_IRQn);
    __HAL_GPIO_EXTI_CLEAR_IT(BOARD_SW1_PIN);
    __HAL_GPIO_EXTI_CLEAR_IT(BOARD_SW2_PIN);
    __HAL_GPIO_EXTI_CLEAR_IT(BOARD_SW3_PIN);
}

static void poll_board_buttons(void)
{
    uint32_t now = HAL_GetTick();
    for (size_t i = 0u; i < sizeof(s_buttons) / sizeof(s_buttons[0]); ++i) {
        bool raw_pressed = button_is_pressed(&s_buttons[i]);
        if (raw_pressed != s_buttons[i].last_raw_pressed) {
            s_buttons[i].last_raw_pressed = raw_pressed;
            s_buttons[i].last_change_ms = now;
            printf("[button-raw] %s active_low=%u gpio_level=%u t_ms=%lu\r\n",
                   s_buttons[i].name,
                   raw_pressed ? 1u : 0u,
                   raw_pressed ? 0u : 1u,
                   (unsigned long)now);
        }
        if (raw_pressed != s_buttons[i].stable_pressed &&
            (now - s_buttons[i].last_change_ms) >= BUTTON_DEBOUNCE_MS) {
            s_buttons[i].stable_pressed = raw_pressed;
            if (raw_pressed) {
                handle_button_press(i);
            }
        }
    }
}

static void handle_button_press(size_t index)
{
    printf("[button] %s pressed t_ms=%lu state=%s\r\n",
           s_buttons[index].name,
           (unsigned long)HAL_GetTick(),
           comp_recording_state_name(s_recording_fsm.state));

    if (index == 0u) {
        run_manual_probe_request();
    } else if (index == 1u) {
        cancel_manual_recording();
    } else if (index == 2u) {
        if (s_recording_fsm.state == COMP_RECORDING_STATE_RECORDING) {
            stop_manual_recording("sw3");
        } else {
            start_manual_recording();
        }
    }
}

void Companion_App_HandleBleLinkReadyChanged(bool ready)
{
    s_ble_link_ready = ready;
    printf("[ble] link_ready=%u stream_ready=%u session_active=%u state=%s\r\n",
           ready ? 1u : 0u,
           Companion_BleAudio_IsReady() ? 1u : 0u,
           s_ble_session_active ? 1u : 0u,
           comp_recording_state_name(s_recording_fsm.state));

    if (ready) {
        if (s_ble_type_ready_autostream_pending) {
            request_ble_type_ready_autostream("pending_type_ready",
                                              s_ble_type_ready_autostream_pending_blocks,
                                              s_ble_type_ready_autostream_pending_pcm_bytes);
        } else if (ble_audio_stream_enabled_for_recording()) {
            start_ble_session_if_ready("link_ready");
        }
    } else {
        s_ble_session_active = false;
        if (s_recording_fsm.state == COMP_RECORDING_STATE_RECORDING &&
            s_recording_fsm.active_source == COMP_RECORDING_SOURCE_HOST_BLE_CONTROL) {
            clear_ble_type_ready_autostream();
            cancel_recording(COMP_RECORDING_SOURCE_HOST_BLE_CONTROL,
                             "ble_notify_disabled");
        } else {
            clear_ble_type_ready_autostream();
        }
    }
}

void comp_audio_stream_stm32wb_notify_pump(void)
{
    MX_APPE_Process();
    HAL_Delay(COMPANION_BLE_NOTIFY_PUMP_DELAY_MS);
    MX_APPE_Process();
}

void Companion_App_HandleBleControl(comp_audio_control_t control,
                                    const uint8_t *data,
                                    size_t length)
{
    (void)data;
    (void)length;

    printf("[ble] control=%s state=%s ready=%u\r\n",
           comp_audio_stream_control_name(control),
           comp_recording_state_name(s_recording_fsm.state),
           Companion_BleAudio_IsReady() ? 1u : 0u);

    switch (control) {
    case COMP_AUDIO_CONTROL_TYPE_READY:
        s_ble_link_ready = true;
        request_ble_type_ready_autostream("type_ready",
                                          COMPANION_TYPE_READY_AUTOSTREAM_BLOCKS,
                                          COMPANION_TYPE_READY_AUTOSTREAM_PCM_BYTES);
        break;

    case COMP_AUDIO_CONTROL_TYPE_READY_A1:
        s_ble_link_ready = true;
        request_ble_type_ready_autostream("type_ready_a1",
                                          COMPANION_TYPE_READY_A1_AUTOSTREAM_BLOCKS,
                                          COMPANION_TYPE_READY_A1_AUTOSTREAM_PCM_BYTES);
        break;

    case COMP_AUDIO_CONTROL_TYPE_READY_A2:
        s_ble_link_ready = true;
        request_ble_type_ready_autostream("type_ready_a2",
                                          COMPANION_TYPE_READY_A2_AUTOSTREAM_BLOCKS,
                                          COMPANION_TYPE_READY_A2_AUTOSTREAM_PCM_BYTES);
        break;

    case COMP_AUDIO_CONTROL_TYPE_HEARTBEAT:
        s_ble_link_ready = true;
        start_ble_session_if_ready("type_heartbeat");
        break;

    case COMP_AUDIO_CONTROL_TYPE_STOP:
        s_ble_link_ready = false;
        clear_ble_type_ready_autostream();
        cancel_recording(COMP_RECORDING_SOURCE_HOST_BLE_CONTROL, "ble_type_stop");
        break;

    case COMP_AUDIO_CONTROL_RECORDING_TOGGLE:
        if (s_recording_fsm.state == COMP_RECORDING_STATE_RECORDING) {
            stop_recording(COMP_RECORDING_SOURCE_HOST_BLE_CONTROL, "ble_toggle");
        } else {
            start_recording(COMP_RECORDING_SOURCE_HOST_BLE_CONTROL, "ble_toggle");
        }
        break;

    case COMP_AUDIO_CONTROL_RECORDING_STOP:
        stop_recording(COMP_RECORDING_SOURCE_HOST_BLE_CONTROL, "ble_stop");
        break;

    case COMP_AUDIO_CONTROL_RECORDING_CANCEL:
        cancel_recording(COMP_RECORDING_SOURCE_HOST_BLE_CONTROL, "ble_cancel");
        break;

    case COMP_AUDIO_CONTROL_RECORDING_PROCESSING_START:
    case COMP_AUDIO_CONTROL_RECORDING_PROCESSING_STOP:
    case COMP_AUDIO_CONTROL_RECORDING_PROCESSING_DONE:
    case COMP_AUDIO_CONTROL_RECORDING_PROCESSING_WARN:
        printf("[ble] processing_control=%s observed\r\n",
               comp_audio_stream_control_name(control));
        break;

    default:
        break;
    }
}

static void start_ble_session_if_ready(const char *reason)
{
    if (s_ble_session_active ||
        s_recording_fsm.state != COMP_RECORDING_STATE_RECORDING ||
        !ble_audio_stream_enabled_for_recording() ||
        !Companion_BleAudio_IsReady()) {
        return;
    }

    s_ble_session_id = Companion_BleAudio_NextSessionId();
    comp_audio_stream_status_t status = Companion_BleAudio_SendSessionStart(s_ble_session_id);
    if (status == COMP_AUDIO_STREAM_OK) {
        s_ble_session_active = true;
    }
    printf("[ble] %s session_start id=%lu status=%s\r\n",
           reason,
           (unsigned long)s_ble_session_id,
           comp_audio_stream_status_name(status));
}

static void init_touch_debug(void)
{
    const comp_touch_gesture_config_t gesture_config = {
        .tap_max_move_px = TOUCH_TAP_MAX_MOVE_PX,
        .long_press_max_move_px = TOUCH_LONG_PRESS_MAX_MOVE_PX,
        .swipe_min_move_px = TOUCH_SWIPE_MIN_MOVE_PX,
        .axis_lock_min_move_px = TOUCH_AXIS_LOCK_MIN_MOVE_PX,
        .axis_slop_px = TOUCH_AXIS_SLOP_PX,
        .tap_max_duration_ms = TOUCH_TAP_MAX_DURATION_MS,
        .swipe_max_duration_ms = TOUCH_SWIPE_MAX_DURATION_MS,
        .hold_feedback_min_duration_ms = TOUCH_HOLD_FEEDBACK_MIN_DURATION_MS,
        .long_press_min_duration_ms = TOUCH_MENU_LONG_PRESS_DURATION_MS,
        .double_tap_max_gap_ms = TOUCH_DOUBLE_TAP_MAX_GAP_MS,
        .double_tap_max_move_px = TOUCH_DOUBLE_TAP_MAX_MOVE_PX,
        .axis_dominance_percent = TOUCH_AXIS_DOMINANCE_PERCENT,
        .min_contact_samples = TOUCH_MIN_CONTACT_SAMPLES,
        .release_debounce_samples = TOUCH_RELEASE_DEBOUNCE_SAMPLES,
    };

    reset_touch_controller();
    comp_touch_gesture_init(&s_touch_gesture, &gesture_config);
    companion_touch_ft6336_stm32wb_init(&s_touch, &hi2c3);
    s_touch_wait_buffer_selftest_pass = touch_wait_buffer_self_test();
#if COMPANION_EPAPER_PANEL_SSD1681_BRINGUP
    companion_epaper_panel_stm32wb_ssd1681_set_wait_service(
        capture_touch_during_display_wait,
        NULL,
        TOUCH_REFRESH_POLL_MS);
#endif
    printf("[touch] ft6336 decoder=%s gesture=%s addr=0x%02X probe=%s probes=%lu irq_mode=%s irq_cfg_errors=%lu tuning=%s threshold=0x%02X period=%u/%u tuning_errors=%lu poll_ms=%u/%u irq=PC6 wired=%u reset=PC10 wired=%u refresh_poll_ms=%u\r\n",
           comp_ft6336_decoder_self_test() ? "pass" : "fail",
           comp_touch_gesture_self_test() ? "pass" : "fail",
           COMP_FT6336_I2C_ADDRESS_7BIT,
           s_touch.detected ? "present" : "waiting",
           (unsigned long)s_touch.probe_count,
           s_touch.interrupt_mode_valid ? "trigger" : "poll-fallback",
           (unsigned long)s_touch.interrupt_config_error_count,
           s_touch.runtime_tuning_valid ? "applied" : "default",
           (unsigned)s_touch.touch_threshold,
           (unsigned)s_touch.active_period,
           (unsigned)s_touch.monitor_period,
           (unsigned long)s_touch.runtime_tuning_error_count,
           (unsigned)TOUCH_ACTIVE_POLL_MS,
           (unsigned)TOUCH_IDLE_POLL_MS,
           (unsigned)COMPANION_TOUCH_INT_WIRED,
           (unsigned)COMPANION_TOUCH_RST_WIRED,
           (unsigned)TOUCH_REFRESH_POLL_MS);
}

static void reset_touch_controller(void)
{
#if COMPANION_TOUCH_RST_WIRED
    HAL_GPIO_WritePin(BOARD_TOUCH_RST_GPIO_PORT,
                      BOARD_TOUCH_RST_PIN,
                      GPIO_PIN_RESET);
    HAL_Delay(TOUCH_RESET_LOW_MS);
    HAL_GPIO_WritePin(BOARD_TOUCH_RST_GPIO_PORT,
                      BOARD_TOUCH_RST_PIN,
                      GPIO_PIN_SET);
    HAL_Delay(TOUCH_RESET_BOOT_MS);
#else
    /* Keep the controller power-on settle time without toggling an unconnected
     * MCU GPIO and claiming that a hardware reset occurred. */
    HAL_Delay(TOUCH_RESET_BOOT_MS);
#endif
}

static bool recover_touch_i2c3_bus(void)
{
    GPIO_InitTypeDef gpio = {0};
    GPIO_PinState scl_before;
    GPIO_PinState sda_before;
    uint8_t clocks = 0u;

    if (HAL_I2C_DeInit(&hi2c3) != HAL_OK) {
        printf("[touch-recovery] deinit=fail count=%lu\r\n",
               (unsigned long)s_touch_recovery_count);
        return false;
    }

    __HAL_RCC_GPIOB_CLK_ENABLE();
    __HAL_RCC_GPIOC_CLK_ENABLE();
    gpio.Mode = GPIO_MODE_OUTPUT_OD;
    gpio.Pull = GPIO_PULLUP;
    gpio.Speed = GPIO_SPEED_FREQ_HIGH;
    gpio.Pin = GPIO_PIN_0;
    HAL_GPIO_Init(GPIOC, &gpio);
    gpio.Pin = GPIO_PIN_11;
    HAL_GPIO_Init(GPIOB, &gpio);

    HAL_GPIO_WritePin(GPIOC, GPIO_PIN_0, GPIO_PIN_SET);
    HAL_GPIO_WritePin(GPIOB, GPIO_PIN_11, GPIO_PIN_SET);
    HAL_Delay(1u);
    scl_before = HAL_GPIO_ReadPin(GPIOC, GPIO_PIN_0);
    sda_before = HAL_GPIO_ReadPin(GPIOB, GPIO_PIN_11);

    while (HAL_GPIO_ReadPin(GPIOB, GPIO_PIN_11) == GPIO_PIN_RESET &&
           clocks < TOUCH_I2C_RECOVERY_CLOCKS) {
        HAL_GPIO_WritePin(GPIOC, GPIO_PIN_0, GPIO_PIN_RESET);
        HAL_Delay(1u);
        HAL_GPIO_WritePin(GPIOC, GPIO_PIN_0, GPIO_PIN_SET);
        HAL_Delay(1u);
        clocks++;
    }

    /* Emit a STOP after any interrupted slave transfer. */
    HAL_GPIO_WritePin(GPIOC, GPIO_PIN_0, GPIO_PIN_RESET);
    HAL_GPIO_WritePin(GPIOB, GPIO_PIN_11, GPIO_PIN_RESET);
    HAL_Delay(1u);
    HAL_GPIO_WritePin(GPIOC, GPIO_PIN_0, GPIO_PIN_SET);
    HAL_Delay(1u);
    HAL_GPIO_WritePin(GPIOB, GPIO_PIN_11, GPIO_PIN_SET);
    HAL_Delay(1u);

    MX_I2C3_Init();
    s_touch_recovery_count++;
    reset_touch_controller();
    companion_touch_ft6336_stm32wb_init(&s_touch, &hi2c3);
    printf("[touch-recovery] count=%lu scl_before=%u sda_before=%u clocks=%u detected=%u hal_error=0x%08lX\r\n",
           (unsigned long)s_touch_recovery_count,
           scl_before == GPIO_PIN_SET ? 1u : 0u,
           sda_before == GPIO_PIN_SET ? 1u : 0u,
           (unsigned)clocks,
           s_touch.detected ? 1u : 0u,
           (unsigned long)HAL_I2C_GetError(&hi2c3));
    return s_touch.detected;
}

static void print_touch_health(void)
{
    printf("[touch-health] detected=%u identity=%u addr=0x%02X cipher=0x%02X fw=0x%02X chip=0x%02X probes=%lu identity_reads=%lu irq_mode=%u irq_cfg=%lu irq_cfg_errors=%lu tuning=%u threshold=0x%02X active_period=%u monitor_period=%u tuning_cfg=%lu tuning_errors=%lu samples=%lu errors=%lu recoveries=%lu failure_streak=%u irq=%lu irq_consumed=%lu buffered=%lu dropped=%lu wait_buffer_selftest=%u\r\n",
           s_touch.detected ? 1u : 0u,
           s_touch.identity_valid ? 1u : 0u,
           (unsigned)COMP_FT6336_I2C_ADDRESS_7BIT,
           (unsigned)s_touch.identity.cipher,
           (unsigned)s_touch.identity.firmware_id,
           (unsigned)s_touch.identity.chip_id,
           (unsigned long)s_touch.probe_count,
           (unsigned long)s_touch.identity_read_count,
           s_touch.interrupt_mode_valid ? 1u : 0u,
           (unsigned long)s_touch.interrupt_config_count,
           (unsigned long)s_touch.interrupt_config_error_count,
           s_touch.runtime_tuning_valid ? 1u : 0u,
           (unsigned)s_touch.touch_threshold,
           (unsigned)s_touch.active_period,
           (unsigned)s_touch.monitor_period,
           (unsigned long)s_touch.runtime_tuning_config_count,
           (unsigned long)s_touch.runtime_tuning_error_count,
           (unsigned long)s_touch.read_count,
           (unsigned long)s_touch.error_count,
           (unsigned long)s_touch_recovery_count,
           (unsigned)s_touch_consecutive_failures,
           (unsigned long)s_touch_irq_count,
           (unsigned long)s_touch_irq_consumed_count,
           (unsigned long)s_touch_refresh_buffered_count,
           (unsigned long)s_touch_refresh_buffer_dropped_count,
           s_touch_wait_buffer_selftest_pass ? 1u : 0u);
}

static void push_buffered_touch_sample(const comp_ft6336_touch_sample_t *sample,
                                       uint32_t now_ms)
{
    if (sample == NULL) {
        return;
    }
    if (s_touch_refresh_buffer_count == TOUCH_REFRESH_BUFFER_CAPACITY) {
        s_touch_refresh_buffer_read = (uint16_t)(
            (s_touch_refresh_buffer_read + 1u) % TOUCH_REFRESH_BUFFER_CAPACITY);
        s_touch_refresh_buffer_count--;
        s_touch_refresh_buffer_dropped_count++;
    }
    s_touch_refresh_buffer[s_touch_refresh_buffer_write] =
        (buffered_touch_sample_t){
            .sample = *sample,
            .timestamp_ms = now_ms,
        };
    s_touch_refresh_buffer_write = (uint16_t)(
        (s_touch_refresh_buffer_write + 1u) % TOUCH_REFRESH_BUFFER_CAPACITY);
    s_touch_refresh_buffer_count++;
    s_touch_refresh_buffered_count++;
}

static void reset_touch_refresh_buffer(void)
{
    s_touch_refresh_buffer_read = 0u;
    s_touch_refresh_buffer_write = 0u;
    s_touch_refresh_buffer_count = 0u;
    s_touch_refresh_buffered_count = 0u;
    s_touch_refresh_buffer_dropped_count = 0u;
    s_touch_refresh_buffer_coalesced_count = 0u;
    s_touch_refresh_capture_active = false;
    s_touch_refresh_latest_contact_valid = false;
    memset(&s_touch_refresh_latest_contact, 0, sizeof(s_touch_refresh_latest_contact));
}

static void flush_buffered_touch_latest_contact(void)
{
    if (!s_touch_refresh_latest_contact_valid) {
        return;
    }
    push_buffered_touch_sample(&s_touch_refresh_latest_contact.sample,
                               s_touch_refresh_latest_contact.timestamp_ms);
    s_touch_refresh_latest_contact_valid = false;
}

static void buffer_touch_sample_during_panel_wait(
    const comp_ft6336_touch_sample_t *sample,
    uint32_t now_ms)
{
    bool contact_now;

    if (sample == NULL) {
        return;
    }
    contact_now = sample->touch_count > 0u &&
                  sample->event != COMP_FT6336_TOUCH_EVENT_UP;
    if (contact_now) {
        if (!s_touch_refresh_capture_active) {
            /* Preserve the gesture anchor, then coalesce any motion while
             * e-paper transport owns the CPU. */
            push_buffered_touch_sample(sample, now_ms);
            s_touch_refresh_capture_active = true;
        } else {
            s_touch_refresh_latest_contact = (buffered_touch_sample_t){
                .sample = *sample,
                .timestamp_ms = now_ms,
            };
            s_touch_refresh_latest_contact_valid = true;
            s_touch_refresh_buffer_coalesced_count++;
        }
        return;
    }

    if (s_touch_refresh_capture_active) {
        /* The newest held position must reach the anchor-based gesture state
         * machine before the release sample. Idle samples before a touch are
         * deliberately discarded. */
        flush_buffered_touch_latest_contact();
        push_buffered_touch_sample(sample, now_ms);
        s_touch_refresh_capture_active = false;
    }
}

static bool touch_wait_buffer_self_test(void)
{
    const comp_ft6336_touch_sample_t idle = {
        .touch_count = 0u,
        .event = COMP_FT6336_TOUCH_EVENT_NONE,
    };
    const comp_ft6336_touch_sample_t down = {
        .touch_count = 1u,
        .event = COMP_FT6336_TOUCH_EVENT_DOWN,
        .touch_id = 1u,
        .x = 20u,
        .y = 30u,
    };
    const comp_ft6336_touch_sample_t contact_first = {
        .touch_count = 1u,
        .event = COMP_FT6336_TOUCH_EVENT_CONTACT,
        .touch_id = 1u,
        .x = 55u,
        .y = 60u,
    };
    const comp_ft6336_touch_sample_t contact_latest = {
        .touch_count = 1u,
        .event = COMP_FT6336_TOUCH_EVENT_CONTACT,
        .touch_id = 1u,
        .x = 90u,
        .y = 100u,
    };
    const comp_ft6336_touch_sample_t up = {
        .touch_count = 1u,
        .event = COMP_FT6336_TOUCH_EVENT_UP,
        .touch_id = 1u,
        .x = 90u,
        .y = 100u,
    };
    buffered_touch_sample_t entry;
    bool passed = false;

    reset_touch_refresh_buffer();
    buffer_touch_sample_during_panel_wait(&idle, 1u);
    buffer_touch_sample_during_panel_wait(&down, 2u);
    buffer_touch_sample_during_panel_wait(&contact_first, 3u);
    buffer_touch_sample_during_panel_wait(&contact_latest, 4u);
    flush_buffered_touch_latest_contact();
    buffer_touch_sample_during_panel_wait(&up, 5u);
    passed = s_touch_refresh_buffer_count == 3u &&
             s_touch_refresh_buffer_coalesced_count == 2u &&
             s_touch_refresh_buffer_dropped_count == 0u &&
             pop_buffered_touch_sample(&entry) &&
             entry.sample.event == COMP_FT6336_TOUCH_EVENT_DOWN &&
             entry.sample.x == 20u &&
             pop_buffered_touch_sample(&entry) &&
             entry.sample.event == COMP_FT6336_TOUCH_EVENT_CONTACT &&
             entry.sample.x == 90u && entry.sample.y == 100u &&
             pop_buffered_touch_sample(&entry) &&
             entry.sample.event == COMP_FT6336_TOUCH_EVENT_UP &&
             !pop_buffered_touch_sample(&entry);
    reset_touch_refresh_buffer();
    return passed;
}

static bool pop_buffered_touch_sample(buffered_touch_sample_t *entry)
{
    if (entry == NULL || s_touch_refresh_buffer_count == 0u) {
        return false;
    }
    *entry = s_touch_refresh_buffer[s_touch_refresh_buffer_read];
    s_touch_refresh_buffer_read = (uint16_t)(
        (s_touch_refresh_buffer_read + 1u) % TOUCH_REFRESH_BUFFER_CAPACITY);
    s_touch_refresh_buffer_count--;
    return true;
}

static void capture_touch_during_display_wait(void *context, uint32_t now_ms)
{
    comp_ft6336_touch_sample_t sample;
    companion_touch_ft6336_stm32wb_result_t result;
    (void)context;

    result = companion_touch_ft6336_stm32wb_poll(&s_touch, &sample);
    if (result != COMPANION_TOUCH_FT6336_STM32WB_OK) {
        return;
    }
    buffer_touch_sample_during_panel_wait(&sample, now_ms);
}

static void process_touch_debug_sample(const comp_ft6336_touch_sample_t *sample,
                                       uint32_t now_ms)
{
    uint16_t logical_x;
    uint16_t logical_y;
    uint32_t sample_age_ms;
    bool sample_changed;
    bool phase_changed;
    bool log_sample;

    if (sample == NULL) {
        return;
    }
    sample_age_ms = HAL_GetTick() - now_ms;

    s_touch_contact_active = sample->touch_count > 0u &&
                             sample->event != COMP_FT6336_TOUCH_EVENT_UP;
    if (!s_touch_contact_active) {
        /* A release observed outside the panel wait loop also closes the
         * buffered contact lifecycle before the next gesture begins. */
        s_touch_refresh_capture_active = false;
        s_touch_refresh_latest_contact_valid = false;
        s_low_power_touch_wake_requested = false;
    }
    logical_x = sample->x < 200u ? sample->x : 199u;
    logical_y = sample->y < 200u ? sample->y : 199u;
#if COMPANION_TOUCH_MIRROR_X != 0u
    if (sample->touch_count > 0u) {
        logical_x = (uint16_t)(199u - logical_x);
    }
#endif
#if COMPANION_TOUCH_MIRROR_Y != 0u
    if (sample->touch_count > 0u) {
        logical_y = (uint16_t)(199u - logical_y);
    }
#endif

    sample_changed = !s_touch_last_sample_valid ||
                     memcmp(sample, &s_touch_last_sample, sizeof(*sample)) != 0;
    phase_changed = !s_touch_last_sample_valid ||
                    sample->touch_count != s_touch_last_sample.touch_count ||
                    sample->event != s_touch_last_sample.event ||
                    sample->touch_id != s_touch_last_sample.touch_id;
    log_sample = phase_changed ||
                 (sample_changed &&
                  (uint32_t)(now_ms - s_touch_last_sample_log_ms) >=
                      TOUCH_SAMPLE_LOG_INTERVAL_MS);
    if (sample_changed) {
        s_touch_last_sample = *sample;
        s_touch_last_sample_valid = true;
    }
    if (log_sample) {
        s_touch_last_sample_log_ms = now_ms;
        printf("[touch] contacts=%u event=%s id=%u raw_x=%u raw_y=%u x=%u y=%u mirror_x=%u mirror_y=%u sample_age_ms=%lu reads=%lu\r\n",
               (unsigned)sample->touch_count,
               comp_ft6336_touch_event_name(sample->event),
               (unsigned)sample->touch_id,
               (unsigned)sample->x,
               (unsigned)sample->y,
               (unsigned)logical_x,
               (unsigned)logical_y,
               (unsigned)COMPANION_TOUCH_MIRROR_X,
               (unsigned)COMPANION_TOUCH_MIRROR_Y,
               (unsigned long)sample_age_ms,
               (unsigned long)s_touch.read_count);
    }
    if (s_touch_contact_active) {
        request_low_power_touch_wake();
    }
    handle_touch_menu_sample(sample, logical_x, logical_y, now_ms);
}

static void request_low_power_touch_wake(void)
{
    if (s_low_power_touch_wake_requested ||
        !s_low_power_idle_pose_attempted ||
        !Companion_Screen_IsReady() ||
        Companion_Screen_IsMenuVisible()) {
        return;
    }

    s_low_power_touch_wake_requested = true;
    /* A differential idle redraw holds this panel for roughly one partial
     * waveform before the user's first gesture can own the screen. Wake the
     * MCU and preserve the 5 ms touch timeline now; tap/swipe/record/menu
     * will enqueue the first visible response after classification. */
    printf("[touch-ui] low_power_touch_wake state=active visual=gesture_owned result=deferred\r\n");
}

static void poll_touch_debug(void)
{
    buffered_touch_sample_t entry;
    comp_ft6336_touch_sample_t sample;
    companion_touch_ft6336_stm32wb_result_t result;
    bool was_detected;
    bool irq_pending;
    uint32_t irq_snapshot;
    uint16_t drained = 0u;
    uint32_t now = HAL_GetTick();

    flush_buffered_touch_latest_contact();
    while (pop_buffered_touch_sample(&entry)) {
        process_touch_debug_sample(&entry.sample, entry.timestamp_ms);
        drained++;
    }
    if (drained > 0u) {
        printf("[touch-buffer] drained=%u total=%lu coalesced=%lu dropped=%lu\r\n",
               (unsigned)drained,
               (unsigned long)s_touch_refresh_buffered_count,
               (unsigned long)s_touch_refresh_buffer_coalesced_count,
               (unsigned long)s_touch_refresh_buffer_dropped_count);
    }

    /* Buffered contacts are authoritative: never maintain while a held touch
     * has not yet reached the gesture state machine. */
    process_menu_entry_transition(now);
    process_touch_screen_maintenance(now);

    irq_snapshot = s_touch_irq_count;
    irq_pending = irq_snapshot != s_touch_irq_consumed_count;
    if (!irq_pending &&
        (int32_t)(now - s_touch_next_poll_ms) < 0) {
        return;
    }
    s_touch_irq_consumed_count = irq_snapshot;
    s_touch_next_poll_ms = now +
        (s_touch_contact_active ? TOUCH_ACTIVE_POLL_MS : TOUCH_IDLE_POLL_MS);
    was_detected = s_touch.detected;
    result = companion_touch_ft6336_stm32wb_poll(&s_touch, &sample);
    if (!was_detected && s_touch.detected) {
        printf("[touch] ft6336 detected probes=%lu\r\n",
               (unsigned long)s_touch.probe_count);
    }
    if (result != COMPANION_TOUCH_FT6336_STM32WB_OK) {
        if (s_touch_consecutive_failures < UINT16_MAX) {
            s_touch_consecutive_failures++;
        }
        if (s_touch_consecutive_failures >= TOUCH_I2C_RECOVERY_FAILURES &&
            now >= s_touch_next_recovery_ms) {
            s_touch_next_recovery_ms = now + TOUCH_I2C_RECOVERY_COOLDOWN_MS;
            if (recover_touch_i2c3_bus()) {
                s_touch_consecutive_failures = 0u;
            }
        }
        if (result != COMPANION_TOUCH_FT6336_STM32WB_NOT_DETECTED &&
            s_touch.error_count == 1u) {
            printf("[touch] poll=%s errors=%lu\r\n",
                   companion_touch_ft6336_stm32wb_result_name(result),
                   (unsigned long)s_touch.error_count);
        }
        return;
    }
    s_touch_consecutive_failures = 0u;
    process_touch_debug_sample(&sample, now);
}

static void schedule_touch_screen_maintenance(uint32_t now_ms)
{
#if COMPANION_SCREEN_MENU_ENABLED
    if (Companion_Screen_IsReady()) {
        s_screen_maintenance_pending = true;
        s_screen_maintenance_due_ms = now_ms + TOUCH_SCREEN_MAINTENANCE_QUIET_MS;
    }
#else
    (void)now_ms;
#endif
}

static void cancel_touch_screen_maintenance(void)
{
#if COMPANION_SCREEN_MENU_ENABLED
    if (s_screen_maintenance_pending) {
        printf("[touch-ui] screen_maintenance cancelled=transition\r\n");
    }
    s_screen_maintenance_pending = false;
#endif
}

static void process_touch_screen_maintenance(uint32_t now_ms)
{
#if COMPANION_SCREEN_MENU_ENABLED
    bool maintained;

    if (!s_screen_maintenance_pending || s_touch_contact_active ||
        (int32_t)(now_ms - s_screen_maintenance_due_ms) < 0) {
        return;
    }
    maintained = Companion_Screen_IsMenuVisible()
                     ? Companion_Screen_MenuMaintenance()
                     : Companion_Screen_ExpressionMaintenance();
    if (maintained) {
        s_screen_maintenance_pending = false;
        printf("[touch-ui] screen_maintenance quiet_ms=%u surface=%s\r\n",
               (unsigned)TOUCH_SCREEN_MAINTENANCE_QUIET_MS,
               Companion_Screen_IsMenuVisible() ? "menu" : "pet");
    } else {
        /* A short pet response must settle before its contrast cleanup. */
        s_screen_maintenance_due_ms = now_ms + 250u;
    }
#else
    (void)now_ms;
#endif
}

static void update_low_power_policy(void)
{
    bool stop_allowed;

    comp_power_policy_set_touch_wake_ready(
        &s_power_policy,
        COMPANION_TOUCH_INT_WIRED != 0u && s_touch.interrupt_mode_valid);
    comp_power_policy_set_blocker(
        &s_power_policy,
        COMP_POWER_BLOCKER_MIC_CAPTURE,
        s_recording_fsm.state == COMP_RECORDING_STATE_RECORDING ||
            s_recording_flash.capture_active);
    comp_power_policy_set_blocker(&s_power_policy,
                                  COMP_POWER_BLOCKER_TOUCH_CONTACT,
                                  s_touch_contact_active);
    comp_power_policy_set_blocker(&s_power_policy,
                                  COMP_POWER_BLOCKER_MENU_TIMER,
                                  s_menu_entry_pending);
    comp_power_policy_set_blocker(&s_power_policy,
                                  COMP_POWER_BLOCKER_SCREEN_MAINTENANCE,
                                  s_screen_maintenance_pending);
    comp_power_policy_set_blocker(&s_power_policy,
                                  COMP_POWER_BLOCKER_SCREEN_WAIT,
                                  s_touch_refresh_capture_active);

    stop_allowed = comp_power_policy_stop_allowed(&s_power_policy);
    if (!stop_allowed) {
        s_low_power_idle_pose_attempted = false;
    } else if (!s_low_power_idle_pose_attempted && Companion_Screen_IsReady() &&
               !Companion_Screen_IsMenuVisible()) {
        s_low_power_idle_pose_attempted = true;
        if (Companion_Screen_EnterLowPowerIdle()) {
            /* The queued partial frame must run before LPM can put the core
             * back into Stop. The next normal loop processes it, then this
             * one-shot guard permits Stop without a periodic art timer. */
            stop_allowed = false;
            printf("[power] low_power_face request=sleepy animation=static\r\n");
        } else {
            printf("[power] low_power_face request=sleepy result=unavailable\r\n");
        }
    }
    if (stop_allowed == s_low_power_stop_allowed) {
        return;
    }
    s_low_power_stop_allowed = stop_allowed;
    UTIL_LPM_SetStopMode(1u << CFG_LPM_APP,
                         stop_allowed ? UTIL_LPM_ENABLE : UTIL_LPM_DISABLE);
    printf("[power] stop=%s blockers=0x%08lX touch_irq=%u\r\n",
           stop_allowed ? "allowed" : "blocked",
           (unsigned long)s_power_policy.blockers,
           s_power_policy.touch_wake_ready ? 1u : 0u);
}

static void process_menu_entry_transition(uint32_t now_ms)
{
#if COMPANION_SCREEN_MENU_ENABLED
    uint8_t entry_flags;

    if (!s_menu_entry_pending || (int32_t)(now_ms - s_menu_entry_due_ms) < 0) {
        return;
    }
    s_menu_entry_pending = false;
    s_screen_menu.view = s_menu_entry_target;
    s_screen_menu.revision++;
    comp_screen_menu_set_flags(&s_screen_menu, Companion_Screen_RuntimeMenuFlags());
    entry_flags = (uint8_t)(s_screen_menu.flags |
                            COMP_SCREEN_MENU_FLAG_PRESS_ACTIVE);
    printf("[touch-ui] menu_entry_arrive target_view=%u revision=%lu\r\n",
           (unsigned)s_screen_menu.view,
           (unsigned long)s_screen_menu.revision);
    Companion_Screen_MenuRequest(s_screen_menu.view,
                                 entry_flags,
                                 s_screen_menu.language,
                                 s_screen_menu.home_page);
    schedule_touch_screen_maintenance(now_ms);
#else
    (void)now_ms;
#endif
}

uint8_t Companion_Screen_RuntimeMenuFlags(void)
{
    uint8_t flags = s_touch.detected ? COMP_SCREEN_MENU_FLAG_TOUCH_OK : 0u;
    if (s_recording_fsm.state == COMP_RECORDING_STATE_RECORDING) {
        flags |= COMP_SCREEN_MENU_FLAG_RECORDING;
    }
    return flags;
}

static void Companion_Screen_RefreshRecordingStatus(void)
{
#if COMPANION_SCREEN_MENU_ENABLED
    uint8_t previous_flags;

    if (!Companion_Screen_IsMenuVisible() ||
        (s_screen_menu.view != COMP_SCREEN_MENU_VIEW_RECORD &&
         s_screen_menu.view != COMP_SCREEN_MENU_VIEW_STATUS)) {
        return;
    }
    previous_flags = s_screen_menu.flags;
    comp_screen_menu_set_flags(&s_screen_menu, Companion_Screen_RuntimeMenuFlags());
    if (s_screen_menu.flags == previous_flags) {
        return;
    }
    printf("[screen] record_state active=%u refresh=partial\r\n",
           s_recording_fsm.state == COMP_RECORDING_STATE_RECORDING ? 1u : 0u);
    Companion_Screen_MenuRequest(s_screen_menu.view,
                                 s_screen_menu.flags,
                                 s_screen_menu.language,
                                 s_screen_menu.home_page);
#endif
}

static void handle_touch_menu_sample(const comp_ft6336_touch_sample_t *sample,
                                     uint16_t logical_x,
                                     uint16_t logical_y,
                                     uint32_t now_ms)
{
#if COMPANION_SCREEN_MENU_ENABLED
    bool contact_now;
    bool explicit_release;
    bool gesture_ready;
    bool home_press_was_active = false;
    uint8_t home_press_item = 0u;
    comp_touch_gesture_event_t gesture;
    comp_screen_menu_result_t menu_result;

    if (sample == NULL) {
        return;
    }
    contact_now = sample->touch_count > 0u &&
                  sample->event != COMP_FT6336_TOUCH_EVENT_UP;
    explicit_release = sample->touch_count > 0u &&
                       sample->event == COMP_FT6336_TOUCH_EVENT_UP;

    gesture_ready = comp_touch_gesture_process(&s_touch_gesture,
                                               contact_now,
                                               explicit_release,
                                               logical_x,
                                               logical_y,
                                               now_ms,
                                               &gesture);
    /* A long press has already consumed this contact to enter the menu.  The
     * panel wait loop may replay held samples after the new menu arrives;
     * never turn those residual samples into a second menu press refresh. */
    if (s_touch_gesture.consumed_until_release && Companion_Screen_IsMenuVisible()) {
        s_menu_home_press_candidate = false;
        return;
    }
    if (!gesture_ready) {
        /* Delay the visual press cue until a horizontal exit has had time to
         * lock its axis.  Starting an e-paper update on touch-down makes the
         * right swipe wait behind BUSY and feels like a missed gesture. */
        if (!contact_now) {
            s_menu_home_press_candidate = false;
        } else if (Companion_Screen_IsMenuVisible() &&
                   s_screen_menu.view == COMP_SCREEN_MENU_VIEW_HOME &&
                   !s_menu_entry_pending) {
            uint8_t item;
            comp_screen_menu_view_t target_view;

            if (comp_touch_gesture_is_horizontal_drag(&s_touch_gesture) ||
                !comp_screen_menu_home_hit_test(&s_screen_menu,
                                                logical_x,
                                                logical_y,
                                                &item,
                                                &target_view)) {
                s_menu_home_press_candidate = false;
            } else if (s_menu_home_press_active &&
                       s_menu_home_press_item == item) {
                s_menu_home_press_candidate = false;
            } else {
                if (!s_menu_home_press_candidate ||
                    s_menu_home_press_candidate_item != item) {
                    s_menu_home_press_candidate = true;
                    s_menu_home_press_candidate_item = item;
                    s_menu_home_press_candidate_due_ms =
                        now_ms + TOUCH_MENU_PRESS_CUE_DELAY_MS;
                    printf("[touch-ui] menu_press_deferred item=%u target_view=%u cue_ms=%u\r\n",
                           (unsigned)item,
                           (unsigned)target_view,
                           (unsigned)TOUCH_MENU_PRESS_CUE_DELAY_MS);
                }
                if ((int32_t)(now_ms - s_menu_home_press_candidate_due_ms) >= 0) {
                    uint8_t entry_flags;

                    comp_screen_menu_set_flags(&s_screen_menu,
                                               Companion_Screen_RuntimeMenuFlags());
                    entry_flags = (uint8_t)(s_screen_menu.flags |
                                            COMP_SCREEN_MENU_FLAG_PRESS_ACTIVE |
                                            (item << COMP_SCREEN_MENU_FLAG_PRESS_ITEM_SHIFT));
                    s_menu_home_press_active = true;
                    s_menu_home_press_item = item;
                    s_menu_home_press_candidate = false;
                    printf("[touch-ui] menu_press item=%u target_view=%u sample_age_ms=%lu\r\n",
                           (unsigned)item,
                           (unsigned)target_view,
                           (unsigned long)(HAL_GetTick() - now_ms));
                    Companion_Screen_MenuRequest(COMP_SCREEN_MENU_VIEW_HOME,
                                                 entry_flags,
                                                 s_screen_menu.language,
                                                 s_screen_menu.home_page);
                }
            }
        }
        return;
    }
    if (!contact_now) {
        home_press_was_active = s_menu_home_press_active;
        home_press_item = s_menu_home_press_item;
        s_menu_home_press_active = false;
        s_menu_home_press_candidate = false;
    }
    printf("[touch-ui] gesture=%s start=%u,%u end=%u,%u duration_ms=%u sample_age_ms=%lu\r\n",
           comp_touch_gesture_name(gesture.type),
           (unsigned)gesture.start_x,
           (unsigned)gesture.start_y,
           (unsigned)gesture.end_x,
           (unsigned)gesture.end_y,
           (unsigned)gesture.duration_ms,
           (unsigned long)(HAL_GetTick() - now_ms));
    if (!Companion_Screen_IsMenuVisible()) {
        if (gesture.type == COMP_TOUCH_GESTURE_HOLD) {
            /* Keep the 650 ms acknowledgement non-blocking.  An e-paper
             * refresh here used to delay the real 3 s decision while BUSY. */
            printf("[touch-ui] daily_hold_menu_prepare x=%u y=%u duration_ms=%u visual=deferred_until_menu\r\n",
                   (unsigned)gesture.end_x,
                   (unsigned)gesture.end_y,
                   (unsigned)gesture.duration_ms);
        } else if (comp_screen_menu_is_daily_entry_gesture(&gesture)) {
            s_menu_entry_pending = false;
            cancel_touch_screen_maintenance();
            s_screen_menu.view = COMP_SCREEN_MENU_VIEW_HOME;
            s_screen_menu.revision++;
            comp_screen_menu_set_flags(&s_screen_menu,
                                       Companion_Screen_RuntimeMenuFlags());
            printf("[touch-ui] daily_to_menu gesture=any_long_press duration_ms=%u selection=%u revision=%lu\r\n",
                   (unsigned)gesture.duration_ms,
                   (unsigned)s_screen_menu.home_page,
                   (unsigned long)s_screen_menu.revision);
            (void)Companion_Screen_MenuRequestClean(s_screen_menu.view,
                                                     s_screen_menu.flags,
                                                     s_screen_menu.language,
                                                     s_screen_menu.home_page);
        } else if (gesture.type == COMP_TOUCH_GESTURE_DOUBLE_TAP) {
            /* The first tap may have scheduled a quiet cleanup.  Recording
             * owns the next visual beat, so do not let that stale task redraw
             * over the generated recording state expression. */
            cancel_touch_screen_maintenance();
            printf("[touch-ui] daily_double_tap_recording x=%u y=%u state=%s\r\n",
                   (unsigned)gesture.end_x,
                   (unsigned)gesture.end_y,
                   comp_recording_state_name(s_recording_fsm.state));
            toggle_touch_recording();
        } else if (gesture.type == COMP_TOUCH_GESTURE_TAP) {
            printf("[touch-ui] daily_reaction x=%u y=%u\r\n",
                   (unsigned)gesture.end_x,
                   (unsigned)gesture.end_y);
            if (Companion_Screen_DailyTapAt(gesture.end_x, gesture.end_y)) {
                schedule_touch_screen_maintenance(now_ms);
            }
        } else if (gesture.type == COMP_TOUCH_GESTURE_SWIPE_LEFT ||
                   gesture.type == COMP_TOUCH_GESTURE_SWIPE_RIGHT ||
                   gesture.type == COMP_TOUCH_GESTURE_SWIPE_UP ||
                   gesture.type == COMP_TOUCH_GESTURE_SWIPE_DOWN) {
            printf("[touch-ui] daily_stroke gesture=%s start=%u,%u end=%u,%u duration_ms=%u\r\n",
                   comp_touch_gesture_name(gesture.type),
                   (unsigned)gesture.start_x,
                   (unsigned)gesture.start_y,
                   (unsigned)gesture.end_x,
                   (unsigned)gesture.end_y,
                   (unsigned)gesture.duration_ms);
            if (Companion_Screen_DailyStrokeAt(gesture.start_x,
                                               gesture.start_y,
                                               gesture.end_x,
                                               gesture.end_y,
                                               gesture.duration_ms)) {
                schedule_touch_screen_maintenance(now_ms);
            }
        }
        return;
    }
    if (comp_screen_menu_is_exit_gesture(&gesture)) {
        s_menu_entry_pending = false;
        s_menu_home_press_active = false;
        s_menu_home_press_candidate = false;
        cancel_touch_screen_maintenance();
        printf("[touch-ui] menu_right_swipe_exit view=%u page=%u start=%u,%u end=%u,%u\r\n",
               (unsigned)s_screen_menu.view,
               (unsigned)s_screen_menu.home_page,
               (unsigned)gesture.start_x,
               (unsigned)gesture.start_y,
               (unsigned)gesture.end_x,
               (unsigned)gesture.end_y);
        (void)Companion_Screen_ShowDailyClean();
        return;
    }
    if (s_screen_menu.view == COMP_SCREEN_MENU_VIEW_HOME &&
        gesture.type == COMP_TOUCH_GESTURE_TAP) {
        uint8_t item;
        uint8_t entry_flags;
        comp_screen_menu_view_t target_view;

        if (comp_screen_menu_home_hit_test(&s_screen_menu,
                                           gesture.end_x,
                                           gesture.end_y,
                                           &item,
                                           &target_view)) {
            comp_screen_menu_set_flags(&s_screen_menu,
                                       Companion_Screen_RuntimeMenuFlags());
            printf("[touch-ui] menu_entry_activate item=%u target_view=%u revision=%lu\r\n",
                   (unsigned)item,
                   (unsigned)target_view,
                   (unsigned long)s_screen_menu.revision);
            entry_flags = (uint8_t)(s_screen_menu.flags |
                                    COMP_SCREEN_MENU_FLAG_PRESS_ACTIVE |
                                    (item << COMP_SCREEN_MENU_FLAG_PRESS_ITEM_SHIFT));
            s_menu_entry_target = target_view;
            s_menu_entry_due_ms = now_ms + TOUCH_MENU_ENTRY_CUE_MS;
            s_menu_entry_pending = true;
            if (!home_press_was_active || home_press_item != item) {
                Companion_Screen_MenuRequest(COMP_SCREEN_MENU_VIEW_HOME,
                                             entry_flags,
                                             s_screen_menu.language,
                                             s_screen_menu.home_page);
            }
        }
        return;
    }
    if (home_press_was_active &&
        s_screen_menu.view == COMP_SCREEN_MENU_VIEW_HOME) {
        Companion_Screen_MenuRequest(COMP_SCREEN_MENU_VIEW_HOME,
                                     s_screen_menu.flags,
                                     s_screen_menu.language,
                                     s_screen_menu.home_page);
    }
    comp_screen_menu_set_flags(&s_screen_menu, Companion_Screen_RuntimeMenuFlags());
    menu_result = gesture.type == COMP_TOUCH_GESTURE_TAP
                      ? comp_screen_menu_tap(&s_screen_menu,
                                             gesture.end_x,
                                             gesture.end_y)
                      : comp_screen_menu_gesture(&s_screen_menu, &gesture);
    if (!menu_result.changed) {
        return;
    }
    printf("[touch-ui] navigate view=%u page=%u language=%u action=%u revision=%lu\r\n",
           (unsigned)menu_result.view,
           (unsigned)menu_result.home_page,
           (unsigned)menu_result.language,
           (unsigned)menu_result.action,
           (unsigned long)menu_result.revision);

    if (menu_result.action == COMP_SCREEN_MENU_ACTION_RECORD_START) {
        comp_screen_menu_set_flags(&s_screen_menu, Companion_Screen_RuntimeMenuFlags());
        MX_APPE_Process();
        start_manual_recording();
    } else if (menu_result.action == COMP_SCREEN_MENU_ACTION_RECORD_STOP) {
        comp_screen_menu_set_flags(&s_screen_menu, Companion_Screen_RuntimeMenuFlags());
        stop_manual_recording("touch-menu");
    } else if (menu_result.action == COMP_SCREEN_MENU_ACTION_PHONE_RECONNECT) {
        companion_ble_advertising_request_result_t retry =
            Companion_Ble_RequestAdvertising("touch-menu");
        comp_screen_menu_phone_reconnect_state_t retry_state =
            retry == COMPANION_BLE_ADVERTISING_REQUEST_FAILED
                ? COMP_SCREEN_MENU_PHONE_RECONNECT_FAILED
                : retry == COMPANION_BLE_ADVERTISING_REQUEST_ALREADY_CONNECTED
                      ? COMP_SCREEN_MENU_PHONE_RECONNECT_CONNECTED
                      : COMP_SCREEN_MENU_PHONE_RECONNECT_ADVERTISING;

        comp_screen_menu_set_phone_reconnect_state(&s_screen_menu, retry_state);
        comp_screen_menu_set_flags(&s_screen_menu, Companion_Screen_RuntimeMenuFlags());
        printf("[touch-ui] phone_reconnect result=%u state=%u\r\n",
               (unsigned)retry,
               (unsigned)retry_state);
        Companion_Screen_MenuRequest(s_screen_menu.view,
                                     s_screen_menu.flags,
                                     s_screen_menu.language,
                                     s_screen_menu.home_page);
        schedule_touch_screen_maintenance(now_ms);
    } else {
        Companion_Screen_MenuRequest(menu_result.view,
                                     menu_result.flags,
                                     menu_result.language,
                                     menu_result.home_page);
        schedule_touch_screen_maintenance(now_ms);
    }
#else
    (void)sample;
    (void)logical_x;
    (void)logical_y;
    (void)now_ms;
#endif
}

static bool ble_audio_stream_enabled_for_recording(void)
{
#if COMPANION_BLE_AUDIO_STREAM_FLASH_RECORDINGS
    return true;
#else
    return s_ble_type_ready_autostream_active;
#endif
}

static bool recording_loop_should_process_app(uint32_t block_index)
{
    if (ble_audio_stream_enabled_for_recording()) {
        return true;
    }
#if COMPANION_FLASH_RECORDING_APPE_PROCESS_INTERVAL_BLOCKS <= 1u
    (void)block_index;
    return true;
#else
    return (block_index % COMPANION_FLASH_RECORDING_APPE_PROCESS_INTERVAL_BLOCKS) == 0u;
#endif
}

static void clear_ble_type_ready_autostream(void)
{
    s_ble_type_ready_autostream_active = false;
    s_ble_type_ready_autostream_pending = false;
    s_ble_type_ready_autostream_blocks_remaining = 0u;
    s_ble_type_ready_autostream_pending_blocks = 0u;
    s_ble_type_ready_autostream_pcm_bytes = 0u;
    s_ble_type_ready_autostream_pending_pcm_bytes = 0u;
}

static void request_ble_type_ready_autostream(const char *reason,
                                              uint32_t blocks,
                                              uint16_t pcm_bytes)
{
#if (COMPANION_TYPE_READY_AUTOSTREAM_BLOCKS > 0u) || \
    (COMPANION_TYPE_READY_A1_AUTOSTREAM_BLOCKS > 0u) || \
    (COMPANION_TYPE_READY_A2_AUTOSTREAM_BLOCKS > 0u)
    Companion_BleAudio_RequestActiveLink(reason);
    if (!Companion_BleAudio_IsReady()) {
        s_ble_type_ready_autostream_pending = true;
        s_ble_type_ready_autostream_pending_blocks = blocks;
        s_ble_type_ready_autostream_pending_pcm_bytes = pcm_bytes;
        printf("[ble] %s autostream=pending stream_ready=%u state=%s\r\n",
               reason,
               Companion_BleAudio_IsReady() ? 1u : 0u,
               comp_recording_state_name(s_recording_fsm.state));
        return;
    }

    s_ble_type_ready_autostream_pending = false;
    s_ble_type_ready_autostream_pending_blocks = 0u;
    s_ble_type_ready_autostream_pending_pcm_bytes = 0u;
    if (s_recording_fsm.state == COMP_RECORDING_STATE_RECORDING) {
        if (s_recording_fsm.active_source == COMP_RECORDING_SOURCE_HOST_BLE_CONTROL) {
            s_ble_type_ready_autostream_active = true;
            s_ble_type_ready_autostream_blocks_remaining = blocks;
            s_ble_type_ready_autostream_pcm_bytes = pcm_bytes;
            s_manual_recording_block_count = 0u;
        }
        start_ble_session_if_ready(reason);
        return;
    }
    if (s_recording_fsm.state != COMP_RECORDING_STATE_IDLE) {
        printf("[ble] %s autostream=ignored state=%s\r\n",
               reason,
               comp_recording_state_name(s_recording_fsm.state));
        return;
    }

    s_ble_type_ready_autostream_active = true;
    s_ble_type_ready_autostream_blocks_remaining = blocks;
    s_ble_type_ready_autostream_pcm_bytes = pcm_bytes;
    start_recording(COMP_RECORDING_SOURCE_HOST_BLE_CONTROL, reason);
    if (s_recording_fsm.state != COMP_RECORDING_STATE_RECORDING) {
        clear_ble_type_ready_autostream();
    }
#else
    (void)reason;
    (void)blocks;
    (void)pcm_bytes;
    start_ble_session_if_ready("type_ready");
#endif
}

static void end_ble_session_if_active(bool cancel, const char *reason)
{
    if (!s_ble_session_active) {
        return;
    }

    comp_audio_stream_status_t status =
        cancel ? Companion_BleAudio_SendSessionCancel()
               : Companion_BleAudio_SendSessionStop();
    printf("[ble] %s session_%s id=%lu status=%s\r\n",
           reason,
           cancel ? "cancel" : "stop",
           (unsigned long)s_ble_session_id,
           comp_audio_stream_status_name(status));
    s_ble_session_active = false;
}

static void start_recording(comp_recording_source_t source, const char *reason)
{
    if (s_recording_fsm.state == COMP_RECORDING_STATE_ERROR_RECOVERY ||
        s_recording_fsm.state == COMP_RECORDING_STATE_CANCELED ||
        s_recording_fsm.state == COMP_RECORDING_STATE_TRANSFERRED) {
        (void)comp_recording_fsm_dispatch(&s_recording_fsm,
                                          COMP_RECORDING_EVENT_RECOVERY_COMPLETE,
                                          source);
    }

    comp_recording_result_t result = comp_recording_fsm_dispatch(
        &s_recording_fsm,
        COMP_RECORDING_EVENT_START_REQUEST,
        source);
#if COMPANION_MIC_BACKEND == COMPANION_MIC_BACKEND_SPH0655_PDM
    pdm_decoder_reset();
#if COMPANION_PDM_RAW_SAI_USE_DMA
    pdm_raw_dma_reset_stream();
#endif
#endif
    s_manual_recording_block_count = 0u;
    if (s_recording_fsm.state == COMP_RECORDING_STATE_RECORDING &&
        ble_audio_stream_enabled_for_recording()) {
        Companion_BleAudio_RequestActiveLink(reason);
        start_ble_session_if_ready(reason);
    }
    printf("[record] %s action=start source=%lu result=%lu state=%s\r\n",
           reason,
           (unsigned long)source,
           (unsigned long)result,
           comp_recording_state_name(s_recording_fsm.state));
    Companion_Screen_RefreshRecordingStatus();
    if (source == COMP_RECORDING_SOURCE_USER_TOUCH &&
        s_recording_fsm.state == COMP_RECORDING_STATE_RECORDING) {
        bool shown = Companion_Screen_DailyExpressionSignal(
            COMP_EPAPER_EXPRESSION_SIGNAL_RECORDING_START,
            "touch_recording_started");
        printf("[record-visual] action=start expression=recording result=%u\r\n",
               shown ? 1u : 0u);
    }
}

static void stop_recording(comp_recording_source_t source, const char *reason)
{
    comp_recording_result_t stop_result = comp_recording_fsm_dispatch(
        &s_recording_fsm,
        COMP_RECORDING_EVENT_STOP_REQUEST,
        source);
    comp_recording_result_t finish_result = comp_recording_fsm_dispatch(
        &s_recording_fsm,
        COMP_RECORDING_EVENT_SESSION_FINISHED,
        source);

    printf("[record] %s action=stop source=%lu stop_result=%lu finish_result=%lu state=%s\r\n",
           reason,
           (unsigned long)source,
           (unsigned long)stop_result,
           (unsigned long)finish_result,
           comp_recording_state_name(s_recording_fsm.state));
    print_recording_summary(reason);
    end_ble_session_if_active(false, reason);
    clear_ble_type_ready_autostream();
    Companion_BleAudio_RequestIdleLink(reason);

    (void)comp_recording_fsm_dispatch(&s_recording_fsm,
                                      COMP_RECORDING_EVENT_TRANSFER_BEGIN,
                                      source);
    (void)comp_recording_fsm_dispatch(&s_recording_fsm,
                                      COMP_RECORDING_EVENT_TRANSFER_FINISHED,
                                      source);
    (void)comp_recording_fsm_dispatch(&s_recording_fsm,
                                      COMP_RECORDING_EVENT_RECOVERY_COMPLETE,
                                      source);
    printf("[record] %s action=sync_complete state=%s\r\n",
           reason,
           comp_recording_state_name(s_recording_fsm.state));
    Companion_Screen_RefreshRecordingStatus();
}

static void cancel_recording(comp_recording_source_t source, const char *reason)
{
    comp_recording_result_t cancel_result = comp_recording_fsm_dispatch(
        &s_recording_fsm,
        COMP_RECORDING_EVENT_CANCEL_REQUEST,
        source);
    end_ble_session_if_active(true, reason);
    clear_ble_type_ready_autostream();
    Companion_BleAudio_RequestIdleLink(reason);
    printf("[record] %s action=cancel source=%lu result=%lu state=%s\r\n",
           reason,
           (unsigned long)source,
           (unsigned long)cancel_result,
           comp_recording_state_name(s_recording_fsm.state));
    if (s_recording_fsm.state == COMP_RECORDING_STATE_CANCELED ||
        s_recording_fsm.state == COMP_RECORDING_STATE_ERROR_RECOVERY ||
        s_recording_fsm.state == COMP_RECORDING_STATE_TRANSFERRED) {
        (void)comp_recording_fsm_dispatch(&s_recording_fsm,
                                          COMP_RECORDING_EVENT_RECOVERY_COMPLETE,
                                          source);
        printf("[record] %s action=recover state=%s\r\n",
               reason,
               comp_recording_state_name(s_recording_fsm.state));
    }
    Companion_Screen_RefreshRecordingStatus();
}

static void start_user_recording(comp_recording_source_t source, const char *reason)
{
    if (s_recording_flash.capture_active) {
        printf("[record] %s action=start ignored=flash_capture_active state=%s\r\n",
               reason,
               comp_recording_state_name(s_recording_fsm.state));
        return;
    }
    if (!recording_flash_begin_capture(0u)) {
        printf("[record] %s action=start rejected=flash_capture_begin_failed state=%s\r\n",
               reason,
               comp_recording_state_name(s_recording_fsm.state));
        if (source == COMP_RECORDING_SOURCE_USER_TOUCH) {
            bool shown = Companion_Screen_DailyExpressionSignal(
                COMP_EPAPER_EXPRESSION_SIGNAL_ERROR,
                "touch_recording_capture_prepare_failed");
            printf("[record-visual] action=start_failed expression=error result=%u\r\n",
                   shown ? 1u : 0u);
        }
        return;
    }
    start_recording(source, reason);
    if (s_recording_fsm.state != COMP_RECORDING_STATE_RECORDING) {
        s_recording_flash.capture_active = false;
        printf("[record] %s action=start rejected=recording_fsm_state state=%s\r\n",
               reason,
               comp_recording_state_name(s_recording_fsm.state));
        if (source == COMP_RECORDING_SOURCE_USER_TOUCH) {
            bool shown = Companion_Screen_DailyExpressionSignal(
                COMP_EPAPER_EXPRESSION_SIGNAL_ERROR,
                "touch_recording_start_rejected");
            printf("[record-visual] action=start_failed expression=error result=%u\r\n",
                   shown ? 1u : 0u);
        }
    }
}

static void stop_user_recording(comp_recording_source_t source, const char *reason)
{
    stop_recording(source, reason);
    bool stored = recording_flash_finalize_capture();
    printf("[record] %s action=user_store result=%u state=%s\r\n",
           reason,
           stored ? 1u : 0u,
           comp_recording_state_name(s_recording_fsm.state));
    if (source == COMP_RECORDING_SOURCE_USER_TOUCH) {
        bool shown = Companion_Screen_DailyExpressionSignal(
            stored ? COMP_EPAPER_EXPRESSION_SIGNAL_RECORDING_FINISHED
                   : COMP_EPAPER_EXPRESSION_SIGNAL_ERROR,
            stored ? "touch_recording_saved" : "touch_recording_store_failed");
        printf("[record-visual] action=store expression=%s result=%u\r\n",
               stored ? "sync_complete" : "error",
               shown ? 1u : 0u);
    }
    Companion_Gatt_PublishRecordingList();
}

static void toggle_touch_recording(void)
{
    if (s_recording_fsm.state == COMP_RECORDING_STATE_RECORDING) {
        if (s_recording_fsm.active_source == COMP_RECORDING_SOURCE_USER_TOUCH) {
            stop_user_recording(COMP_RECORDING_SOURCE_USER_TOUCH,
                                "touch_double_tap");
        } else {
            printf("[record] touch_double_tap action=ignored active_source=%lu state=%s\r\n",
                   (unsigned long)s_recording_fsm.active_source,
                   comp_recording_state_name(s_recording_fsm.state));
        }
        return;
    }
    start_user_recording(COMP_RECORDING_SOURCE_USER_TOUCH, "touch_double_tap");
}

static void start_manual_recording(void)
{
    start_user_recording(COMP_RECORDING_SOURCE_USER_BUTTON, "sw3");
}

static void stop_manual_recording(const char *reason)
{
    stop_user_recording(COMP_RECORDING_SOURCE_USER_BUTTON, reason);
}

static void cancel_manual_recording(void)
{
    cancel_recording(COMP_RECORDING_SOURCE_USER_BUTTON, "sw2");
    if (s_recording_flash.capture_active || s_recording_flash.stored) {
        if (recording_flash_ensure_ready()) {
            (void)recording_flash_erase_region();
        }
        recording_flash_clear_state();
        printf("[record] sw2 action=manual_flash_clear state=%s\r\n",
               comp_recording_state_name(s_recording_fsm.state));
        Companion_Gatt_PublishRecordingList();
    }
}

static void run_manual_probe_request(void)
{
    if (s_recording_fsm.state == COMP_RECORDING_STATE_RECORDING ||
        s_recording_fsm.state == COMP_RECORDING_STATE_STOPPING) {
        printf("[button] sw1 action=probe ignored=recording_active state=%s\r\n",
               comp_recording_state_name(s_recording_fsm.state));
        return;
    }
    printf("\r\n[button] sw1 action=probe_begin t_ms=%lu\r\n",
           (unsigned long)HAL_GetTick());
    run_flash_probe();
    run_ota_readiness_probe();
    run_microphone_probe();
    print_diag_tail();
    printf("[button] sw1 action=probe_done t_ms=%lu\r\n",
           (unsigned long)HAL_GetTick());
}

static void run_flash_probe(void)
{
    static const flash_qspi_probe_config_t configs[] = {
        {"qspi_mode0_500khz", 63u, QSPI_SAMPLE_SHIFTING_NONE},
        {"qspi_mode0_2mhz", 15u, QSPI_SAMPLE_SHIFTING_NONE},
        {"qspi_mode0_4mhz_half", 7u, QSPI_SAMPLE_SHIFTING_HALFCYCLE},
    };

    uint32_t best_jedec = 0xFFFFFFFFu;
    uint8_t best_status1 = 0xFFu;
    uint8_t best_status2 = 0xFFu;
    bool any_valid = false;
    HAL_StatusTypeDef best_id_status = HAL_ERROR;
    HAL_StatusTypeDef best_sr1_status = HAL_ERROR;
    HAL_StatusTypeDef best_sr2_status = HAL_ERROR;

    for (size_t index = 0u; index < (sizeof(configs) / sizeof(configs[0])); ++index) {
        const flash_qspi_probe_config_t *config = &configs[index];
        HAL_StatusTypeDef cfg_status = apply_flash_qspi_probe_config(config);
        uint8_t jedec_id[3] = {0};
        uint8_t status1 = 0u;
        uint8_t status2 = 0u;
        uint8_t read_1_1_1[8] = {0};
        uint8_t read_1_1_2[8] = {0};
        HAL_StatusTypeDef read_111_status = HAL_ERROR;
        HAL_StatusTypeDef read_112_status = HAL_ERROR;

        if (cfg_status == HAL_OK) {
            flash_release_powerdown();
            best_id_status = qspi_read_command(0x9Fu,
                                               QSPI_ADDRESS_NONE,
                                               0u,
                                               QSPI_DATA_1_LINE,
                                               0u,
                                               jedec_id,
                                               sizeof(jedec_id));
            best_sr1_status = qspi_read_command(0x05u,
                                                QSPI_ADDRESS_NONE,
                                                0u,
                                                QSPI_DATA_1_LINE,
                                                0u,
                                                &status1,
                                                1u);
            best_sr2_status = qspi_read_command(0x35u,
                                                QSPI_ADDRESS_NONE,
                                                0u,
                                                QSPI_DATA_1_LINE,
                                                0u,
                                                &status2,
                                                1u);
        } else {
            best_id_status = cfg_status;
            best_sr1_status = cfg_status;
            best_sr2_status = cfg_status;
        }

        uint32_t jedec = ((uint32_t)jedec_id[0] << 16) |
                         ((uint32_t)jedec_id[1] << 8) |
                         (uint32_t)jedec_id[2];
        bool valid = cfg_status == HAL_OK &&
                     best_id_status == HAL_OK &&
                     jedec != 0x000000u &&
                     jedec != 0xFFFFFFu;

        if (valid) {
            read_111_status = qspi_read_command(0x03u,
                                                QSPI_ADDRESS_1_LINE,
                                                0u,
                                                QSPI_DATA_1_LINE,
                                                0u,
                                                read_1_1_1,
                                                sizeof(read_1_1_1));
            read_112_status = qspi_read_command(0x3Bu,
                                                QSPI_ADDRESS_1_LINE,
                                                0u,
                                                QSPI_DATA_2_LINES,
                                                8u,
                                                read_1_1_2,
                                                sizeof(read_1_1_2));
        }

        if (valid && !any_valid) {
            best_jedec = jedec;
            best_status1 = status1;
            best_status2 = status2;
            any_valid = true;
        } else if (!any_valid) {
            best_jedec = jedec;
            best_status1 = status1;
            best_status2 = status2;
        }

        printf("[flash] cfg=%s cfg_status=%s id_status=%s sr1_status=%s sr2_status=%s jedec=%02X-%02X-%02X sr1=0x%02X sr2=0x%02X valid=%u\r\n",
               config->name,
               hal_status_name(cfg_status),
               hal_status_name(best_id_status),
               hal_status_name(best_sr1_status),
               hal_status_name(best_sr2_status),
               jedec_id[0],
               jedec_id[1],
               jedec_id[2],
               status1,
               status2,
               valid ? 1u : 0u);
        if (valid) {
            printf("[flash] read addr0 1-1-1=%s %02X %02X %02X %02X %02X %02X %02X %02X 1-1-2=%s %02X %02X %02X %02X %02X %02X %02X %02X\r\n",
                   hal_status_name(read_111_status),
                   read_1_1_1[0],
                   read_1_1_1[1],
                   read_1_1_1[2],
                   read_1_1_1[3],
                   read_1_1_1[4],
                   read_1_1_1[5],
                   read_1_1_1[6],
                   read_1_1_1[7],
                   hal_status_name(read_112_status),
                   read_1_1_2[0],
                   read_1_1_2[1],
                   read_1_1_2[2],
                   read_1_1_2[3],
                   read_1_1_2[4],
                   read_1_1_2[5],
                   read_1_1_2[6],
                   read_1_1_2[7]);
        }
    }

    printf("[flash] summary valid=%u best_jedec=0x%06lX best_sr1=0x%02X best_sr2=0x%02X note=%s\r\n",
           any_valid ? 1u : 0u,
           (unsigned long)best_jedec,
           best_status1,
           best_status2,
           any_valid ? "qspi_flash_detected" : "no_qspi_flash_response");
    run_flash_bitbang_probe();
    comp_qspi_nor_init(&s_flash, &hqspi);
    comp_qspi_nor_info_t driver_info;
    comp_qspi_nor_status_t driver_status = comp_qspi_nor_probe(&s_flash, &driver_info);
    printf("[flash-driver] probe=%s jedec=0x%06lX size=%lu sector=%lu page=%lu quad=%u sfdp=%u sr1=0x%02X sr2=0x%02X\r\n",
           comp_qspi_nor_status_name(driver_status),
           (unsigned long)(driver_status == COMP_QSPI_NOR_OK ? driver_info.jedec_id : 0xFFFFFFFFu),
           (unsigned long)(driver_status == COMP_QSPI_NOR_OK ? driver_info.size_bytes : 0u),
           (unsigned long)(driver_status == COMP_QSPI_NOR_OK ? driver_info.sector_size : 0u),
           (unsigned long)(driver_status == COMP_QSPI_NOR_OK ? driver_info.page_size : 0u),
           driver_status == COMP_QSPI_NOR_OK && driver_info.quad_enabled ? 1u : 0u,
           driver_status == COMP_QSPI_NOR_OK && driver_info.sfdp_present ? 1u : 0u,
           driver_status == COMP_QSPI_NOR_OK ? driver_info.status1 : 0xFFu,
           driver_status == COMP_QSPI_NOR_OK ? driver_info.status2 : 0xFFu);
    if (driver_status == COMP_QSPI_NOR_OK) {
        run_flash_write_read_smoke(driver_info.jedec_id);
    }

    comp_diag_log_record_code(COMP_DIAG_EVT_SPI_FLASH_CACHE_READ,
                              driver_status == COMP_QSPI_NOR_OK ? COMP_DIAG_SEV_INFO : COMP_DIAG_SEV_WARN,
                              driver_status == COMP_QSPI_NOR_OK ? driver_info.jedec_id : best_jedec,
                              driver_status == COMP_QSPI_NOR_OK
                                  ? (((uint32_t)driver_info.status1 << 8) | driver_info.status2)
                                  : (((uint32_t)best_status1 << 8) | best_status2),
                              (uint32_t)best_id_status,
                              (uint32_t)driver_status);
}

static void run_flash_write_read_smoke(uint32_t jedec)
{
    uint8_t pattern[FLASH_TEST_SIZE];
    uint8_t readback[FLASH_TEST_SIZE];
    uint8_t erased_prefix[16];
    uint32_t test_address = FLASH_TEST_ADDRESS;

    if (s_flash.info.size_bytes >= s_flash.info.sector_size &&
        (test_address + s_flash.info.sector_size) > s_flash.info.size_bytes) {
        test_address = s_flash.info.size_bytes - s_flash.info.sector_size;
    }

    for (uint32_t i = 0u; i < FLASH_TEST_SIZE; ++i) {
        pattern[i] = (uint8_t)(0xA5u ^ (uint8_t)i ^ (uint8_t)(i >> 1));
        readback[i] = 0u;
    }
    memset(erased_prefix, 0u, sizeof(erased_prefix));

    uint32_t pattern_crc = crc32_update(0u, pattern, sizeof(pattern));
    printf("[flash-write] begin addr=0x%08lX size=%lu jedec=0x%06lX pattern_crc=0x%08lX\r\n",
           (unsigned long)test_address,
           (unsigned long)FLASH_TEST_SIZE,
           (unsigned long)jedec,
           (unsigned long)pattern_crc);

    comp_qspi_nor_status_t erase_status = comp_qspi_nor_erase_4k(&s_flash, test_address);
    comp_qspi_nor_status_t erased_read_status = COMP_QSPI_NOR_ERROR;
    bool erased_ok = false;
    if (erase_status == COMP_QSPI_NOR_OK) {
        erased_read_status = comp_qspi_nor_read(&s_flash, test_address, erased_prefix, sizeof(erased_prefix));
        erased_ok = erased_read_status == COMP_QSPI_NOR_OK;
        for (size_t i = 0u; i < sizeof(erased_prefix); ++i) {
            if (erased_prefix[i] != 0xFFu) {
                erased_ok = false;
                break;
            }
        }
    }

    printf("[flash-write] erase=%s erased_read=%s erased_prefix=%02X %02X %02X %02X %02X %02X %02X %02X erased_ok=%u\r\n",
           comp_qspi_nor_status_name(erase_status),
           comp_qspi_nor_status_name(erased_read_status),
           erased_prefix[0],
           erased_prefix[1],
           erased_prefix[2],
           erased_prefix[3],
           erased_prefix[4],
           erased_prefix[5],
           erased_prefix[6],
           erased_prefix[7],
           erased_ok ? 1u : 0u);

    comp_qspi_nor_status_t write_status = COMP_QSPI_NOR_ERROR;
    comp_qspi_nor_status_t read_status = COMP_QSPI_NOR_ERROR;
    uint32_t read_crc = 0u;
    uint32_t mismatch_count = 0u;
    uint32_t first_mismatch = UINT_MAX;

    if (erased_ok) {
        write_status = comp_qspi_nor_write(&s_flash, test_address, pattern, sizeof(pattern));
        if (write_status == COMP_QSPI_NOR_OK) {
            read_status = comp_qspi_nor_read(&s_flash, test_address, readback, sizeof(readback));
            if (read_status == COMP_QSPI_NOR_OK) {
                read_crc = crc32_update(0u, readback, sizeof(readback));
                for (uint32_t i = 0u; i < FLASH_TEST_SIZE; ++i) {
                    if (readback[i] != pattern[i]) {
                        if (first_mismatch == UINT_MAX) {
                            first_mismatch = i;
                        }
                        mismatch_count++;
                    }
                }
            }
        }
    }

    bool pass = erased_ok &&
                write_status == COMP_QSPI_NOR_OK &&
                read_status == COMP_QSPI_NOR_OK &&
                read_crc == pattern_crc &&
                mismatch_count == 0u;
    printf("[flash-write] verify write=%s read=%s read_crc=0x%08lX mismatches=%lu first_mismatch=%ld pass=%u\r\n",
           comp_qspi_nor_status_name(write_status),
           comp_qspi_nor_status_name(read_status),
           (unsigned long)read_crc,
           (unsigned long)mismatch_count,
           first_mismatch == UINT_MAX ? -1L : (long)first_mismatch,
           pass ? 1u : 0u);

    comp_diag_log_record_code(COMP_DIAG_EVT_SPI_FLASH_CACHE_WRITE,
                              pass ? COMP_DIAG_SEV_INFO : COMP_DIAG_SEV_WARN,
                              jedec,
                              test_address,
                              pattern_crc,
                              read_crc);
}

static uint32_t recording_flash_total_region_bytes(void)
{
    return (uint32_t)sizeof(recording_flash_header_t) + FLASH_RECORDING_MAX_BYTES;
}

static uint32_t recording_flash_limit_bytes_for_seconds(uint16_t max_seconds)
{
    if (max_seconds == 0u) {
        return FLASH_RECORDING_MAX_BYTES;
    }

    uint32_t requested = (uint32_t)max_seconds * FLASH_RECORDING_BYTES_PER_SECOND;
    if (requested == 0u || requested > FLASH_RECORDING_MAX_BYTES) {
        return FLASH_RECORDING_MAX_BYTES;
    }
    return requested;
}

static uint32_t recording_flash_sector_count(uint32_t bytes)
{
    uint32_t sector_size = s_flash.info.sector_size != 0u ? s_flash.info.sector_size : 4096u;
    return (bytes + sector_size - 1u) / sector_size;
}

static uint32_t recording_flash_compute_base(const comp_qspi_nor_info_t *info)
{
    uint32_t sector_size = info->sector_size != 0u ? info->sector_size : 4096u;
    uint32_t region_sectors = recording_flash_sector_count(recording_flash_total_region_bytes());
    uint32_t region_bytes = region_sectors * sector_size;

    if ((FLASH_RECORDING_BASE_PREFERRED + region_bytes) <= info->size_bytes) {
        return FLASH_RECORDING_BASE_PREFERRED;
    }
    if (region_bytes < info->size_bytes) {
        return (info->size_bytes - region_bytes) & ~(sector_size - 1u);
    }
    return 0u;
}

static bool recording_flash_load_header(void)
{
    recording_flash_header_t header;
    memset(&header, 0, sizeof(header));
    comp_qspi_nor_status_t status = comp_qspi_nor_read(&s_flash,
                                                       s_recording_flash.base_address,
                                                       (uint8_t *)&header,
                                                       sizeof(header));
    if (status != COMP_QSPI_NOR_OK ||
        header.magic != FLASH_RECORDING_MAGIC ||
        header.version != FLASH_RECORDING_VERSION ||
        header.total_length == 0u ||
        header.total_length > FLASH_RECORDING_MAX_BYTES ||
        header.sync_state == FLASH_RECORDING_SYNC_DELETED) {
        return false;
    }

    s_recording_flash.header = header;
    s_recording_flash.recording_id = header.recording_id;
    s_recording_flash.bytes_written = header.total_length;
    s_recording_flash.content_crc32 = header.content_crc32;
    s_recording_flash.packet_sequence_next = 0u;
    s_recording_flash.stored = true;
    if (s_recording_flash.next_recording_id <= header.recording_id) {
        s_recording_flash.next_recording_id = header.recording_id + 1u;
    }
    return true;
}

static bool recording_flash_ensure_ready(void)
{
    if (s_recording_flash.ready) {
        return true;
    }

    comp_qspi_nor_init(&s_flash, &hqspi);
    comp_qspi_nor_info_t info;
    comp_qspi_nor_status_t status = comp_qspi_nor_probe(&s_flash, &info);
    if (status != COMP_QSPI_NOR_OK ||
        info.size_bytes < recording_flash_total_region_bytes()) {
        printf("[rec-flash] probe=%s size=%lu required=%lu ready=0\r\n",
               comp_qspi_nor_status_name(status),
               (unsigned long)(status == COMP_QSPI_NOR_OK ? info.size_bytes : 0u),
               (unsigned long)recording_flash_total_region_bytes());
        comp_diag_log_record_code(COMP_DIAG_EVT_SPI_FLASH_CACHE_LOW_STORAGE,
                                  COMP_DIAG_SEV_WARN,
                                  status == COMP_QSPI_NOR_OK ? info.size_bytes : 0u,
                                  recording_flash_total_region_bytes(),
                                  (uint32_t)status,
                                  0u);
        return false;
    }

    s_recording_flash.ready = true;
    s_recording_flash.base_address = recording_flash_compute_base(&info);
    s_recording_flash.data_address =
        s_recording_flash.base_address + (uint32_t)sizeof(recording_flash_header_t);
    s_recording_flash.capacity_bytes = FLASH_RECORDING_MAX_BYTES;
    if (s_recording_flash.next_recording_id == 0u) {
        s_recording_flash.next_recording_id = 1u;
    }
    (void)recording_flash_load_header();
    printf("[rec-flash] ready=1 jedec=0x%06lX base=0x%08lX data=0x%08lX capacity=%lu\r\n",
           (unsigned long)info.jedec_id,
           (unsigned long)s_recording_flash.base_address,
           (unsigned long)s_recording_flash.data_address,
           (unsigned long)s_recording_flash.capacity_bytes);
    return true;
}

static void recording_flash_clear_state(void)
{
    s_recording_flash.capture_active = false;
    s_recording_flash.stored = false;
    s_recording_flash.write_failed = false;
    s_recording_flash.bytes_written = 0u;
    s_recording_flash.content_crc32 = 0u;
    s_recording_flash.packet_sequence_next = 0u;
    s_recording_flash_stage_len = 0u;
    memset(&s_recording_flash.header, 0, sizeof(s_recording_flash.header));
    sha256_init(&s_recording_flash.sha256);
}

bool Companion_ScreenAssets_OpenExternalStore(comp_asset_store_t *store)
{
    comp_qspi_nor_info_t info;
    comp_qspi_nor_status_t status;

    if (store == NULL) {
        return false;
    }
    comp_qspi_nor_init(&s_flash, &hqspi);
    status = comp_qspi_nor_probe(&s_flash, &info);
    if (status != COMP_QSPI_NOR_OK ||
        FLASH_UI_ASSETS_BASE > info.size_bytes ||
        FLASH_UI_ASSETS_SIZE > info.size_bytes - FLASH_UI_ASSETS_BASE) {
        printf("[screen-assets] external_store=unavailable probe=%s size=%lu required_end=0x%08lX\r\n",
               comp_qspi_nor_status_name(status),
               (unsigned long)(status == COMP_QSPI_NOR_OK ? info.size_bytes : 0u),
               (unsigned long)(FLASH_UI_ASSETS_BASE + FLASH_UI_ASSETS_SIZE));
        return false;
    }
    if (!companion_screen_assets_stm32wb_init(&s_screen_assets_adapter,
                                              store,
                                              &s_flash,
                                              FLASH_UI_ASSETS_BASE,
                                              FLASH_UI_ASSETS_SIZE)) {
        return false;
    }
    printf("[screen-assets] external_store=ready kind=qspi_nor base=0x%08lX bytes=%lu\r\n",
           (unsigned long)FLASH_UI_ASSETS_BASE,
           (unsigned long)FLASH_UI_ASSETS_SIZE);
    return true;
}

static bool recording_flash_erase_region(void)
{
    uint32_t sector_size = s_flash.info.sector_size != 0u ? s_flash.info.sector_size : 4096u;
    uint32_t sectors = recording_flash_sector_count(recording_flash_total_region_bytes());
    uint32_t remaining = sectors * sector_size;
    uint32_t address = s_recording_flash.base_address;
    const uint32_t block_size = 65536u;

    while (remaining > 0u) {
        if (remaining >= block_size && (address % block_size) == 0u) {
            comp_qspi_nor_status_t block_status = comp_qspi_nor_erase_64k(&s_flash, address);
            if (block_status == COMP_QSPI_NOR_OK) {
                address += block_size;
                remaining -= block_size;
                continue;
            }
            printf("[rec-flash] erase64 address=0x%08lX status=%s fallback=4k\r\n",
                   (unsigned long)address,
                   comp_qspi_nor_status_name(block_status));
        }

        comp_qspi_nor_status_t status = comp_qspi_nor_erase_4k(&s_flash, address);
        if (status != COMP_QSPI_NOR_OK) {
            printf("[rec-flash] erase address=0x%08lX status=%s\r\n",
                   (unsigned long)address,
                   comp_qspi_nor_status_name(status));
            return false;
        }
        address += sector_size;
        remaining = remaining > sector_size ? (remaining - sector_size) : 0u;
    }
    return true;
}

static bool recording_flash_begin_capture(uint16_t max_seconds)
{
    if (!recording_flash_ensure_ready()) {
        return false;
    }
    if (!recording_flash_erase_region()) {
        comp_diag_log_record_code(COMP_DIAG_EVT_SPI_FLASH_CACHE_INTERRUPTED_WRITE,
                                  COMP_DIAG_SEV_WARN,
                                  s_recording_flash.base_address,
                                  recording_flash_total_region_bytes(),
                                  0u,
                                  0u);
        return false;
    }

    recording_flash_clear_state();
    s_recording_flash.capacity_bytes = recording_flash_limit_bytes_for_seconds(max_seconds);
    s_recording_flash.capture_active = true;
    s_recording_flash.recording_id = s_recording_flash.next_recording_id++;
    s_recording_flash.started_tick_ms = HAL_GetTick();
    printf("[rec-flash] capture_begin id=%lu base=0x%08lX max=%lu max_seconds=%u stage=%lu\r\n",
           (unsigned long)s_recording_flash.recording_id,
           (unsigned long)s_recording_flash.base_address,
           (unsigned long)s_recording_flash.capacity_bytes,
           (unsigned)max_seconds,
           (unsigned long)FLASH_RECORDING_STAGE_BYTES);
    comp_diag_log_record_code(COMP_DIAG_EVT_SPI_FLASH_CACHE_WRITE,
                              COMP_DIAG_SEV_INFO,
                              s_recording_flash.recording_id,
                              s_recording_flash.base_address,
                              s_recording_flash.capacity_bytes,
                              0u);
    return true;
}

static void recording_flash_append_pcm(const uint8_t *pcm, uint32_t length)
{
    if (!s_recording_flash.capture_active ||
        s_recording_flash.write_failed ||
        pcm == NULL ||
        length == 0u) {
        return;
    }

    uint32_t committed_and_staged =
        s_recording_flash.bytes_written + s_recording_flash_stage_len;
    uint32_t remaining =
        committed_and_staged < s_recording_flash.capacity_bytes
            ? (s_recording_flash.capacity_bytes - committed_and_staged)
            : 0u;
    uint32_t chunk = length <= remaining ? length : remaining;
    if (chunk == 0u) {
        return;
    }

    if (chunk > (FLASH_RECORDING_STAGE_BYTES - s_recording_flash_stage_len) &&
        !recording_flash_flush_stage()) {
        return;
    }

    if (chunk > FLASH_RECORDING_STAGE_BYTES) {
        (void)recording_flash_write_bytes(pcm, chunk);
        return;
    }

    memcpy(&s_recording_flash_stage[s_recording_flash_stage_len], pcm, chunk);
    s_recording_flash_stage_len += chunk;
    if (s_recording_flash_stage_len >= FLASH_RECORDING_STAGE_BYTES) {
        (void)recording_flash_flush_stage();
    }
}

static bool recording_flash_write_bytes(const uint8_t *data, uint32_t length)
{
    if (s_recording_flash.write_failed || data == NULL || length == 0u) {
        return !s_recording_flash.write_failed;
    }

    uint32_t address = s_recording_flash.data_address + s_recording_flash.bytes_written;
    comp_qspi_nor_status_t status = comp_qspi_nor_write(&s_flash, address, data, length);
    if (status != COMP_QSPI_NOR_OK) {
        s_recording_flash.write_failed = true;
        printf("[rec-flash] append_failed id=%lu offset=%lu length=%lu status=%s\r\n",
               (unsigned long)s_recording_flash.recording_id,
               (unsigned long)s_recording_flash.bytes_written,
               (unsigned long)length,
               comp_qspi_nor_status_name(status));
        comp_diag_log_record_code(COMP_DIAG_EVT_SPI_FLASH_CACHE_INTERRUPTED_WRITE,
                                  COMP_DIAG_SEV_WARN,
                                  s_recording_flash.recording_id,
                                  s_recording_flash.bytes_written,
                                  length,
                                  (uint32_t)status);
        return false;
    }

    s_recording_flash.content_crc32 =
        crc32_update(s_recording_flash.content_crc32, data, length);
    sha256_update(&s_recording_flash.sha256, data, length);
    s_recording_flash.bytes_written += length;
    return true;
}

static bool recording_flash_flush_stage(void)
{
    if (s_recording_flash_stage_len == 0u) {
        return true;
    }

    uint32_t length = s_recording_flash_stage_len;
    if (!recording_flash_write_bytes(s_recording_flash_stage, length)) {
        return false;
    }
    s_recording_flash_stage_len = 0u;
    return true;
}

static bool recording_flash_finalize_capture(void)
{
    if (!s_recording_flash.capture_active) {
        return s_recording_flash.stored;
    }
    (void)recording_flash_flush_stage();
    s_recording_flash.capture_active = false;

    if (s_recording_flash.write_failed || s_recording_flash.bytes_written == 0u) {
        printf("[rec-flash] capture_finalize_failed id=%lu bytes=%lu write_failed=%u\r\n",
               (unsigned long)s_recording_flash.recording_id,
               (unsigned long)s_recording_flash.bytes_written,
               s_recording_flash.write_failed ? 1u : 0u);
        comp_diag_log_record_code(COMP_DIAG_EVT_SPI_FLASH_CACHE_INTERRUPTED_WRITE,
                                  COMP_DIAG_SEV_WARN,
                                  s_recording_flash.recording_id,
                                  s_recording_flash.bytes_written,
                                  s_recording_flash.write_failed ? 1u : 0u,
                                  0u);
        return false;
    }

    recording_flash_header_t header;
    memset(&header, 0, sizeof(header));
    header.magic = FLASH_RECORDING_MAGIC;
    header.version = FLASH_RECORDING_VERSION;
    header.recording_id = s_recording_flash.recording_id;
    header.started_unix_s = 0u;
    header.started_tick_ms = s_recording_flash.started_tick_ms;
    header.total_length = s_recording_flash.bytes_written;
    uint64_t duration_ms =
        ((uint64_t)s_recording_flash.bytes_written * 8u * 1000u) /
        (FLASH_RECORDING_SAMPLE_RATE_HZ * FLASH_RECORDING_BITS_PER_SAMPLE);
    header.duration_ms = duration_ms > 0xFFFFFFFFu ? 0xFFFFFFFFu : (uint32_t)duration_ms;
    header.content_crc32 = s_recording_flash.content_crc32;
    header.codec = FLASH_RECORDING_CODEC_PCM16;
    header.sync_state = FLASH_RECORDING_SYNC_UNSYNCED;
    header.source_mode = FLASH_RECORDING_SOURCE_MIC_SAI_VALUE;
    sha256_final(&s_recording_flash.sha256, header.sha256);

    comp_qspi_nor_status_t status = comp_qspi_nor_write(&s_flash,
                                                        s_recording_flash.base_address,
                                                        (const uint8_t *)&header,
                                                        sizeof(header));
    if (status != COMP_QSPI_NOR_OK) {
        printf("[rec-flash] header_write_failed id=%lu status=%s\r\n",
               (unsigned long)header.recording_id,
               comp_qspi_nor_status_name(status));
        return false;
    }

    s_recording_flash.header = header;
    s_recording_flash.stored = true;
    s_recording_flash.packet_sequence_next = 0u;
    uint32_t wall_ms = HAL_GetTick() - s_recording_flash.started_tick_ms;
    printf("[rec-flash] stored id=%lu bytes=%lu duration_ms=%lu wall_ms=%lu crc=0x%08lX sha_prefix=%02X%02X%02X%02X%02X%02X%02X%02X\r\n",
           (unsigned long)header.recording_id,
           (unsigned long)header.total_length,
           (unsigned long)header.duration_ms,
           (unsigned long)wall_ms,
           (unsigned long)header.content_crc32,
           header.sha256[0],
           header.sha256[1],
           header.sha256[2],
           header.sha256[3],
           header.sha256[4],
           header.sha256[5],
           header.sha256[6],
           header.sha256[7]);
    comp_diag_log_record_code(COMP_DIAG_EVT_SPI_FLASH_CACHE_WRITE,
                              COMP_DIAG_SEV_INFO,
                              header.recording_id,
                              header.total_length,
                              header.duration_ms,
                              header.content_crc32);
    return true;
}

bool Companion_RecordingFlash_HandleControl(uint8_t command,
                                            uint16_t max_seconds)
{
    switch (command) {
    case COMPANION_RECORDING_CONTROL_START:
        if (s_recording_flash.capture_active) {
            return false;
        }
        if (!recording_flash_begin_capture(max_seconds)) {
            return false;
        }
        start_recording(COMP_RECORDING_SOURCE_HOST_BLE_CONTROL, "gatt_recording_start");
        if (s_recording_fsm.state != COMP_RECORDING_STATE_RECORDING) {
            s_recording_flash.capture_active = false;
            return false;
        }
        return true;

    case COMPANION_RECORDING_CONTROL_STOP:
        if (!s_recording_flash.capture_active) {
            return false;
        }
        stop_recording(COMP_RECORDING_SOURCE_HOST_BLE_CONTROL, "gatt_recording_stop");
        return recording_flash_finalize_capture();

    case COMPANION_RECORDING_CONTROL_CANCEL:
        if (s_recording_flash.capture_active) {
            cancel_recording(COMP_RECORDING_SOURCE_HOST_BLE_CONTROL, "gatt_recording_cancel");
        }
        if (recording_flash_ensure_ready()) {
            (void)recording_flash_erase_region();
        }
        recording_flash_clear_state();
        return true;

    default:
        return false;
    }
}

bool Companion_RecordingFlash_GetMetadata(companion_recording_flash_metadata_t *out)
{
    if (out == NULL || !recording_flash_ensure_ready()) {
        return false;
    }
    if (!s_recording_flash.stored && !recording_flash_load_header()) {
        return false;
    }

    memset(out, 0, sizeof(*out));
    out->recording_id = s_recording_flash.header.recording_id;
    out->started_unix_s = s_recording_flash.header.started_unix_s;
    out->started_tick_ms = s_recording_flash.header.started_tick_ms;
    out->duration_ms = s_recording_flash.header.duration_ms;
    out->total_length = s_recording_flash.header.total_length;
    out->content_crc32 = s_recording_flash.header.content_crc32;
    memcpy(out->sha256, s_recording_flash.header.sha256, sizeof(out->sha256));
    out->codec = s_recording_flash.header.codec;
    out->sync_state = s_recording_flash.header.sync_state;
    out->source_mode = s_recording_flash.header.source_mode;
    return true;
}

bool Companion_RecordingFlash_ReadChunk(uint32_t recording_id,
                                        uint32_t byte_offset,
                                        uint16_t requested_length,
                                        uint8_t *payload,
                                        uint16_t payload_capacity,
                                        companion_recording_flash_chunk_t *out)
{
    if (out != NULL) {
        memset(out, 0, sizeof(*out));
        out->recording_id = recording_id;
        out->byte_offset = byte_offset;
    }

    if (payload == NULL ||
        out == NULL ||
        requested_length == 0u ||
        payload_capacity == 0u) {
        if (out != NULL) {
            out->error_code = COMPANION_RECORDING_FLASH_READ_BAD_ARGUMENT;
        }
        return false;
    }
    if (!recording_flash_ensure_ready()) {
        out->error_code = COMPANION_RECORDING_FLASH_READ_NOT_READY;
        return false;
    }
    if (!s_recording_flash.stored && !recording_flash_load_header()) {
        out->error_code = COMPANION_RECORDING_FLASH_READ_NO_STORED_RECORDING;
        return false;
    }
    out->total_length = s_recording_flash.header.total_length;
    if (recording_id != s_recording_flash.header.recording_id) {
        out->error_code = COMPANION_RECORDING_FLASH_READ_ID_MISMATCH;
        return false;
    }
    if (byte_offset >= s_recording_flash.header.total_length) {
        out->error_code = COMPANION_RECORDING_FLASH_READ_OFFSET_OUT_OF_RANGE;
        return false;
    }

    uint32_t available = s_recording_flash.header.total_length - byte_offset;
    uint32_t length = requested_length;
    if (length > payload_capacity) {
        length = payload_capacity;
    }
    if (length > available) {
        length = available;
    }

    comp_qspi_nor_status_t status = comp_qspi_nor_read(&s_flash,
                                                       s_recording_flash.data_address + byte_offset,
                                                       payload,
                                                       length);
    if (status != COMP_QSPI_NOR_OK) {
        out->error_code = COMPANION_RECORDING_FLASH_READ_QSPI_BASE |
                          (((uint32_t)(-(int32_t)status)) & 0xFFu);
        out->payload_length = (uint16_t)length;
        printf("[rec-flash] read_error id=%lu offset=%lu length=%lu status=%s code=0x%08lX total=%lu\r\n",
               (unsigned long)recording_id,
               (unsigned long)byte_offset,
               (unsigned long)length,
               comp_qspi_nor_status_name(status),
               (unsigned long)out->error_code,
               (unsigned long)s_recording_flash.header.total_length);
        comp_diag_log_record_code(COMP_DIAG_EVT_SPI_FLASH_CACHE_INTERRUPTED_READ,
                                  COMP_DIAG_SEV_WARN,
                                  recording_id,
                                  byte_offset,
                                  length,
                                  (uint32_t)status);
        return false;
    }

    if (byte_offset == 0u) {
        s_recording_flash.packet_sequence_next = 0u;
    }
    uint32_t sequence = s_recording_flash.packet_sequence_next++;
    bool final_packet = (byte_offset + length) >= s_recording_flash.header.total_length;

    uint8_t crc_header[16];
    write_le32(&crc_header[0], recording_id);
    write_le32(&crc_header[4], sequence);
    write_le32(&crc_header[8], byte_offset);
    write_le32(&crc_header[12], s_recording_flash.header.total_length);
    uint32_t packet_crc = crc32_update(0u, crc_header, sizeof(crc_header));
    packet_crc = crc32_update(packet_crc, payload, length);

    s_recording_flash.header.sync_state =
        final_packet ? FLASH_RECORDING_SYNC_TRANSFERRED : FLASH_RECORDING_SYNC_TRANSFER_ACTIVE;
    out->recording_id = recording_id;
    out->packet_sequence = sequence;
    out->byte_offset = byte_offset;
    out->total_length = s_recording_flash.header.total_length;
    out->packet_crc32 = packet_crc;
    out->error_code = COMPANION_RECORDING_FLASH_READ_OK;
    out->payload_length = (uint16_t)length;
    out->final_packet = final_packet;
    if (final_packet) {
        memcpy(out->final_sha256,
               s_recording_flash.header.sha256,
               sizeof(out->final_sha256));
    }
    comp_diag_log_record_code(COMP_DIAG_EVT_SPI_FLASH_CACHE_READ,
                              COMP_DIAG_SEV_INFO,
                              recording_id,
                              byte_offset,
                              length,
                              packet_crc);
    return true;
}

bool Companion_RecordingFlash_Delete(uint8_t operation,
                                     uint32_t recording_id,
                                     uint32_t validated_total_length,
                                     const uint8_t validated_sha256[COMPANION_RECORDING_FLASH_SHA256_BYTES])
{
    if (!recording_flash_ensure_ready()) {
        return false;
    }
    if (!s_recording_flash.stored && !recording_flash_load_header()) {
        return false;
    }

    bool delete_all = operation == 2u || operation == 3u;
    bool exact_match =
        operation == 1u &&
        recording_id == s_recording_flash.header.recording_id &&
        validated_total_length == s_recording_flash.header.total_length &&
        validated_sha256 != NULL &&
        memcmp(validated_sha256,
               s_recording_flash.header.sha256,
               COMPANION_RECORDING_FLASH_SHA256_BYTES) == 0;
    if (!delete_all && !exact_match) {
        comp_diag_log_record_code(COMP_DIAG_EVT_SPI_FLASH_CACHE_DELETE,
                                  COMP_DIAG_SEV_WARN,
                                  recording_id,
                                  validated_total_length,
                                  s_recording_flash.header.total_length,
                                  0u);
        return false;
    }

    bool erased = recording_flash_erase_region();
    if (erased) {
        s_recording_flash.header.sync_state = FLASH_RECORDING_SYNC_DELETED;
        recording_flash_clear_state();
    }
    comp_diag_log_record_code(delete_all ? COMP_DIAG_EVT_SPI_FLASH_CACHE_PRIVACY_ERASE
                                         : COMP_DIAG_EVT_SPI_FLASH_CACHE_DELETE,
                              erased ? COMP_DIAG_SEV_INFO : COMP_DIAG_SEV_WARN,
                              recording_id,
                              validated_total_length,
                              delete_all ? 1u : 0u,
                              erased ? 0u : 1u);
    return erased;
}

static HAL_StatusTypeDef apply_flash_qspi_probe_config(const flash_qspi_probe_config_t *config)
{
    if (HAL_QSPI_DeInit(&hqspi) != HAL_OK) {
        return HAL_ERROR;
    }

    hqspi.Instance = QUADSPI;
    hqspi.Init.ClockPrescaler = config->prescaler;
    hqspi.Init.FifoThreshold = 4u;
    hqspi.Init.SampleShifting = config->sample_shifting;
    hqspi.Init.FlashSize = 23u;
    hqspi.Init.ChipSelectHighTime = QSPI_CS_HIGH_TIME_8_CYCLE;
    hqspi.Init.ClockMode = QSPI_CLOCK_MODE_0;

    return HAL_QSPI_Init(&hqspi);
}

static void flash_release_powerdown(void)
{
    (void)qspi_no_data_command(0xABu);
    HAL_Delay(1u);
}

static HAL_StatusTypeDef qspi_read_command(uint8_t instruction,
                                           uint32_t address_mode,
                                           uint32_t address,
                                           uint32_t data_mode,
                                           uint32_t dummy_cycles,
                                           uint8_t *data,
                                           uint32_t length)
{
    QSPI_CommandTypeDef command = {0};

    command.Instruction = instruction;
    command.Address = address;
    command.AlternateBytes = 0u;
    command.AddressSize = QSPI_ADDRESS_24_BITS;
    command.AlternateBytesSize = QSPI_ALTERNATE_BYTES_8_BITS;
    command.DummyCycles = dummy_cycles;
    command.InstructionMode = QSPI_INSTRUCTION_1_LINE;
    command.AddressMode = address_mode;
    command.AlternateByteMode = QSPI_ALTERNATE_BYTES_NONE;
    command.DataMode = data_mode;
    command.NbData = length;
    command.DdrMode = QSPI_DDR_MODE_DISABLE;
    command.SIOOMode = QSPI_SIOO_INST_EVERY_CMD;

    HAL_StatusTypeDef status = HAL_QSPI_Command(&hqspi, &command, 200u);
    if (status != HAL_OK) {
        return status;
    }
    return HAL_QSPI_Receive(&hqspi, data, 200u);
}

static HAL_StatusTypeDef qspi_no_data_command(uint8_t instruction)
{
    QSPI_CommandTypeDef command = {0};

    command.Instruction = instruction;
    command.Address = 0u;
    command.AlternateBytes = 0u;
    command.AddressSize = QSPI_ADDRESS_24_BITS;
    command.AlternateBytesSize = QSPI_ALTERNATE_BYTES_8_BITS;
    command.DummyCycles = 0u;
    command.InstructionMode = QSPI_INSTRUCTION_1_LINE;
    command.AddressMode = QSPI_ADDRESS_NONE;
    command.AlternateByteMode = QSPI_ALTERNATE_BYTES_NONE;
    command.DataMode = QSPI_DATA_NONE;
    command.NbData = 0u;
    command.DdrMode = QSPI_DDR_MODE_DISABLE;
    command.SIOOMode = QSPI_SIOO_INST_EVERY_CMD;

    return HAL_QSPI_Command(&hqspi, &command, 200u);
}

static void run_flash_bitbang_probe(void)
{
    HAL_StatusTypeDef deinit_status = HAL_QSPI_DeInit(&hqspi);
    printf("[flash-bb] begin qspi_deinit=%s note=manual_gpio_spi_on_qspi_pins\r\n",
           hal_status_name(deinit_status));
    run_flash_bitbang_variant("normal_io0_mosi_io1_miso", false);
    run_flash_bitbang_variant("swapped_io1_mosi_io0_miso", true);
    MX_QUADSPI_Init();
}

static void run_flash_bitbang_variant(const char *name, bool swap_io0_io1)
{
    GPIO_TypeDef *mosi_port = swap_io0_io1 ? FLASH_QSPI_IO1_GPIO_PORT : FLASH_QSPI_IO0_GPIO_PORT;
    uint16_t mosi_pin = swap_io0_io1 ? FLASH_QSPI_IO1_PIN : FLASH_QSPI_IO0_PIN;
    GPIO_TypeDef *miso_port = swap_io0_io1 ? FLASH_QSPI_IO0_GPIO_PORT : FLASH_QSPI_IO1_GPIO_PORT;
    uint16_t miso_pin = swap_io0_io1 ? FLASH_QSPI_IO0_PIN : FLASH_QSPI_IO1_PIN;
    uint8_t jedec_id[3] = {0};
    uint8_t status1 = 0u;

    configure_flash_pins_for_bitbang(swap_io0_io1);

    HAL_GPIO_WritePin(FLASH_QSPI_NCS_GPIO_PORT, FLASH_QSPI_NCS_PIN, GPIO_PIN_RESET);
    (void)bitbang_spi_transfer(mosi_port, mosi_pin, miso_port, miso_pin, 0xABu);
    HAL_GPIO_WritePin(FLASH_QSPI_NCS_GPIO_PORT, FLASH_QSPI_NCS_PIN, GPIO_PIN_SET);
    HAL_Delay(1u);

    HAL_GPIO_WritePin(FLASH_QSPI_NCS_GPIO_PORT, FLASH_QSPI_NCS_PIN, GPIO_PIN_RESET);
    (void)bitbang_spi_transfer(mosi_port, mosi_pin, miso_port, miso_pin, 0x9Fu);
    jedec_id[0] = bitbang_spi_transfer(mosi_port, mosi_pin, miso_port, miso_pin, 0xFFu);
    jedec_id[1] = bitbang_spi_transfer(mosi_port, mosi_pin, miso_port, miso_pin, 0xFFu);
    jedec_id[2] = bitbang_spi_transfer(mosi_port, mosi_pin, miso_port, miso_pin, 0xFFu);
    HAL_GPIO_WritePin(FLASH_QSPI_NCS_GPIO_PORT, FLASH_QSPI_NCS_PIN, GPIO_PIN_SET);

    HAL_GPIO_WritePin(FLASH_QSPI_NCS_GPIO_PORT, FLASH_QSPI_NCS_PIN, GPIO_PIN_RESET);
    (void)bitbang_spi_transfer(mosi_port, mosi_pin, miso_port, miso_pin, 0x05u);
    status1 = bitbang_spi_transfer(mosi_port, mosi_pin, miso_port, miso_pin, 0xFFu);
    HAL_GPIO_WritePin(FLASH_QSPI_NCS_GPIO_PORT, FLASH_QSPI_NCS_PIN, GPIO_PIN_SET);

    uint32_t jedec = ((uint32_t)jedec_id[0] << 16) |
                     ((uint32_t)jedec_id[1] << 8) |
                     (uint32_t)jedec_id[2];
    bool valid = jedec != 0x000000u && jedec != 0xFFFFFFu;

    GPIO_PinState io0_level = HAL_GPIO_ReadPin(FLASH_QSPI_IO0_GPIO_PORT, FLASH_QSPI_IO0_PIN);
    GPIO_PinState io1_level = HAL_GPIO_ReadPin(FLASH_QSPI_IO1_GPIO_PORT, FLASH_QSPI_IO1_PIN);

    printf("[flash-bb] cfg=%s jedec=%02X-%02X-%02X sr1=0x%02X valid=%u idle_io0=%u idle_io1=%u\r\n",
           name,
           jedec_id[0],
           jedec_id[1],
           jedec_id[2],
           status1,
           valid ? 1u : 0u,
           io0_level == GPIO_PIN_SET ? 1u : 0u,
           io1_level == GPIO_PIN_SET ? 1u : 0u);
}

static uint8_t bitbang_spi_transfer(GPIO_TypeDef *mosi_port,
                                    uint16_t mosi_pin,
                                    GPIO_TypeDef *miso_port,
                                    uint16_t miso_pin,
                                    uint8_t tx)
{
    uint8_t rx = 0u;

    for (int bit = 7; bit >= 0; --bit) {
        HAL_GPIO_WritePin(mosi_port,
                          mosi_pin,
                          ((tx >> bit) & 1u) ? GPIO_PIN_SET : GPIO_PIN_RESET);
        for (volatile uint32_t delay = 0u; delay < 80u; ++delay) {
        }
        HAL_GPIO_WritePin(FLASH_QSPI_CLK_GPIO_PORT, FLASH_QSPI_CLK_PIN, GPIO_PIN_SET);
        for (volatile uint32_t delay = 0u; delay < 80u; ++delay) {
        }
        rx <<= 1;
        if (HAL_GPIO_ReadPin(miso_port, miso_pin) == GPIO_PIN_SET) {
            rx |= 1u;
        }
        HAL_GPIO_WritePin(FLASH_QSPI_CLK_GPIO_PORT, FLASH_QSPI_CLK_PIN, GPIO_PIN_RESET);
        for (volatile uint32_t delay = 0u; delay < 80u; ++delay) {
        }
    }

    return rx;
}

static void configure_flash_pins_for_bitbang(bool swap_io0_io1)
{
    GPIO_InitTypeDef GPIO_InitStruct = {0};
    uint16_t mosi_pin = swap_io0_io1 ? FLASH_QSPI_IO1_PIN : FLASH_QSPI_IO0_PIN;
    uint16_t miso_pin = swap_io0_io1 ? FLASH_QSPI_IO0_PIN : FLASH_QSPI_IO1_PIN;

    HAL_GPIO_WritePin(FLASH_QSPI_NCS_GPIO_PORT, FLASH_QSPI_NCS_PIN, GPIO_PIN_SET);
    HAL_GPIO_WritePin(FLASH_QSPI_CLK_GPIO_PORT, FLASH_QSPI_CLK_PIN, GPIO_PIN_RESET);

    GPIO_InitStruct.Pin = FLASH_QSPI_NCS_PIN | FLASH_QSPI_CLK_PIN;
    GPIO_InitStruct.Mode = GPIO_MODE_OUTPUT_PP;
    GPIO_InitStruct.Pull = GPIO_PULLUP;
    GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_LOW;
    HAL_GPIO_Init(GPIOA, &GPIO_InitStruct);

    GPIO_InitStruct.Pin = mosi_pin;
    GPIO_InitStruct.Mode = GPIO_MODE_OUTPUT_PP;
    GPIO_InitStruct.Pull = GPIO_NOPULL;
    GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_LOW;
    HAL_GPIO_Init(GPIOB, &GPIO_InitStruct);

    GPIO_InitStruct.Pin = miso_pin;
    GPIO_InitStruct.Mode = GPIO_MODE_INPUT;
    GPIO_InitStruct.Pull = GPIO_PULLUP;
    GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_LOW;
    HAL_GPIO_Init(GPIOB, &GPIO_InitStruct);
}

static uint32_t ota_blockers(bool recording_active,
                             bool transfer_active,
                             bool diag_export_active,
                             uint8_t battery_percent,
                             bool board_target_ok,
                             bool manifest_hash_ok,
                             bool interrupted_transfer)
{
    uint32_t blockers = 0u;
    if (recording_active) {
        blockers |= OTA_BLOCKER_RECORDING_ACTIVE;
    }
    if (transfer_active) {
        blockers |= OTA_BLOCKER_TRANSFER_ACTIVE;
    }
    if (diag_export_active) {
        blockers |= OTA_BLOCKER_DIAG_EXPORT_ACTIVE;
    }
    if (battery_percent < 30u) {
        blockers |= OTA_BLOCKER_LOW_BATTERY;
    }
    if (!board_target_ok) {
        blockers |= OTA_BLOCKER_WRONG_BOARD_TARGET;
    }
    if (!manifest_hash_ok) {
        blockers |= OTA_BLOCKER_INVALID_HASH;
    }
    if (interrupted_transfer) {
        blockers |= OTA_BLOCKER_INTERRUPTED_TRANSFER;
    }
    return blockers;
}

static void print_ota_case(const char *name,
                           bool recording_active,
                           bool transfer_active,
                           bool diag_export_active,
                           uint8_t battery_percent,
                           bool board_target_ok,
                           bool manifest_hash_ok,
                           bool interrupted_transfer)
{
    uint32_t blockers = ota_blockers(recording_active,
                                     transfer_active,
                                     diag_export_active,
                                     battery_percent,
                                     board_target_ok,
                                     manifest_hash_ok,
                                     interrupted_transfer);
    ota_ready_state_t ready_state = blockers == 0u ? OTA_READY_STATE_READY : OTA_READY_STATE_BLOCKED;

    printf("[ota] case=%s ready_state=%lu battery=%u charger=1 min_mv=3600 blockers=0x%08lX\r\n",
           name,
           (unsigned long)ready_state,
           battery_percent,
           (unsigned long)blockers);

    comp_diag_log_record_code(COMP_DIAG_EVT_OTA_READINESS,
                              blockers == 0u ? COMP_DIAG_SEV_INFO : COMP_DIAG_SEV_WARN,
                              (uint32_t)ready_state,
                              (uint32_t)battery_percent,
                              blockers,
                              3600u);

    comp_diag_log_record_code(COMP_DIAG_EVT_OTA_BLOCK_RESULT,
                              blockers == 0u ? COMP_DIAG_SEV_INFO : COMP_DIAG_SEV_WARN,
                              blockers,
                              (uint32_t)ready_state,
                              (uint32_t)battery_percent,
                              3600u);

    if (blockers != 0u) {
        comp_diag_log_record_code(COMP_DIAG_EVT_OTA_BLOCKER,
                                  COMP_DIAG_SEV_WARN,
                                  blockers,
                                  recording_active ? 1u : 0u,
                                  transfer_active ? 1u : 0u,
                                  interrupted_transfer ? 1u : 0u);
    }
    if (interrupted_transfer) {
        comp_diag_log_record_code(COMP_DIAG_EVT_OTA_INTERRUPTED_TRANSFER,
                                  COMP_DIAG_SEV_WARN,
                                  0u,
                                  blockers,
                                  0u,
                                  0u);
    }
}

static void run_ota_readiness_probe(void)
{
    const uint32_t manifest_version = 1u;
    const uint32_t image_size = 0u;
    const uint32_t sha256_prefix = 0u;
    const uint32_t resume_token = 0u;

    printf("[ota] manifest version=%lu image_size=%lu sha256_prefix=0x%08lX resume_token=0x%08lX\r\n",
           (unsigned long)manifest_version,
           (unsigned long)image_size,
           (unsigned long)sha256_prefix,
           (unsigned long)resume_token);

    comp_diag_log_record_code(COMP_DIAG_EVT_OTA_MANIFEST,
                              COMP_DIAG_SEV_INFO,
                              manifest_version,
                              image_size,
                              sha256_prefix,
                              resume_token);

    print_ota_case("ready", false, false, false, 100u, true, true, false);
    print_ota_case("recording_active_blocked", true, false, false, 100u, true, true, false);
    print_ota_case("transfer_active_blocked", false, true, false, 100u, true, true, false);
    print_ota_case("diag_export_blocked", false, false, true, 100u, true, true, false);
    print_ota_case("low_battery_blocked", false, false, false, 12u, true, true, false);
    print_ota_case("wrong_board_blocked", false, false, false, 100u, false, true, false);
    print_ota_case("invalid_hash_blocked", false, false, false, 100u, true, false, false);
    print_ota_case("interrupted_transfer_blocked", false, false, false, 100u, true, true, true);

    comp_diag_log_record_code(COMP_DIAG_EVT_OTA_POST_UPDATE_SELF_CHECK,
                              COMP_DIAG_SEV_INFO,
                              1u,
                              0u,
                              0u,
                              0u);
}

#if COMPANION_MIC_BACKEND != COMPANION_MIC_BACKEND_SPH0655_PDM
static int16_t i2s_word_to_pcm16(uint32_t word)
{
    return (int16_t)((int32_t)word >> 16);
}
#endif

static int16_t clamp_pcm16_from_i32(int32_t value)
{
    if (value > INT16_MAX) {
        return INT16_MAX;
    }
    if (value < INT16_MIN) {
        return INT16_MIN;
    }
    return (int16_t)value;
}

static uint32_t pdm_read_bit(const uint32_t *words, uint32_t bit_index)
{
    uint32_t word = words[bit_index / 32u];
#if COMPANION_PDM_BIT_ORDER_LSB
    uint32_t bit = (word >> (bit_index & 31u)) & 1u;
#else
    uint32_t bit = (word >> (31u - (bit_index & 31u))) & 1u;
#endif
#if COMPANION_PDM_INVERT_BITS
    bit ^= 1u;
#endif
    return bit;
}

#if COMPANION_MIC_BACKEND == COMPANION_MIC_BACKEND_SPH0655_PDM
static void pdm_decoder_reset(void)
{
#if COMPANION_PDM_USE_CIC3_FILTER
    memset(&s_pdm_cic3_state, 0, sizeof(s_pdm_cic3_state));
#endif
}

#if COMPANION_PDM_RAW_SAI_USE_DMA
static void pdm_raw_dma_reset_stream(void)
{
    if (s_pdm_raw_dma_started) {
        (void)HAL_SAI_DMAStop(&hsai_BlockA1);
        s_pdm_raw_dma_started = false;
    }

    __disable_irq();
    s_pdm_raw_dma_ready_mask = 0u;
    s_pdm_raw_dma_last_completed_half = 0u;
    s_pdm_raw_dma_overrun_count = 0u;
    __enable_irq();
    memset(s_pdm_raw_dma_words, 0, sizeof(s_pdm_raw_dma_words));

    __HAL_SAI_DISABLE(&hsai_BlockA1);
    SET_BIT(hsai_BlockA1.Instance->CR2, SAI_xCR2_FFLUSH);
}

static HAL_StatusTypeDef pdm_raw_dma_start_if_needed(void)
{
    if (s_pdm_raw_dma_started) {
        return HAL_OK;
    }

    __disable_irq();
    s_pdm_raw_dma_ready_mask = 0u;
    s_pdm_raw_dma_last_completed_half = 0u;
    __enable_irq();

    HAL_StatusTypeDef status =
        HAL_SAI_Receive_DMA(&hsai_BlockA1,
                            (uint8_t *)s_pdm_raw_dma_words,
                            (uint16_t)MIC_RAW_DMA_WORDS);
    if (status == HAL_OK) {
        s_pdm_raw_dma_started = true;
    }
    return status;
}

static HAL_StatusTypeDef pdm_raw_dma_read_block(uint32_t *raw_words,
                                                uint32_t timeout_ms,
                                                uint32_t *overruns)
{
    HAL_StatusTypeDef status = pdm_raw_dma_start_if_needed();
    if (status != HAL_OK) {
        return status;
    }

    const uint32_t start_ms = HAL_GetTick();
    while (true) {
        uint8_t half = 0u;
        uint8_t have_half = 0u;

        __disable_irq();
        uint8_t mask = s_pdm_raw_dma_ready_mask;
        if (mask != 0u) {
            if (mask == (MIC_RAW_DMA_HALF0_READY | MIC_RAW_DMA_HALF1_READY)) {
                half = s_pdm_raw_dma_last_completed_half;
                s_pdm_raw_dma_ready_mask = 0u;
                s_pdm_raw_dma_overrun_count++;
            } else if ((mask & MIC_RAW_DMA_HALF0_READY) != 0u) {
                half = 0u;
                s_pdm_raw_dma_ready_mask = (uint8_t)(mask & ~MIC_RAW_DMA_HALF0_READY);
            } else {
                half = 1u;
                s_pdm_raw_dma_ready_mask = (uint8_t)(mask & ~MIC_RAW_DMA_HALF1_READY);
            }
            have_half = 1u;
        }
        uint32_t overrun_snapshot = s_pdm_raw_dma_overrun_count;
        __enable_irq();

        if (have_half != 0u) {
            memcpy(raw_words,
                   &s_pdm_raw_dma_words[(uint32_t)half * MIC_RAW_WORDS],
                   MIC_RAW_WORDS * sizeof(raw_words[0]));
            if (overruns != NULL) {
                *overruns = overrun_snapshot;
            }
            return HAL_OK;
        }

        if ((HAL_GetTick() - start_ms) >= timeout_ms) {
            if (overruns != NULL) {
                *overruns = overrun_snapshot;
            }
            return HAL_TIMEOUT;
        }
    }
}
#endif

#if COMPANION_PDM_USE_CIC3_FILTER
static void pdm_cic3_init_lookup(void)
{
    if (s_pdm_cic3_lookup_ready) {
        return;
    }

    for (uint32_t value = 0u; value < 256u; ++value) {
        int32_t sum = 0;
        int32_t weighted1 = 0;
        int32_t weighted2 = 0;
        for (uint32_t index = 0u; index < 8u; ++index) {
#if COMPANION_PDM_BIT_ORDER_LSB
            uint32_t bit = (value >> index) & 1u;
#else
            uint32_t bit = (value >> (7u - index)) & 1u;
#endif
#if COMPANION_PDM_INVERT_BITS
            bit ^= 1u;
#endif
            int32_t x = bit ? 1 : -1;
            int32_t remaining = (int32_t)(8u - index);
            sum += x;
            weighted1 += remaining * x;
            weighted2 += ((remaining * (remaining + 1)) / 2) * x;
        }
        s_pdm_cic3_byte_moments[value].sum = (int8_t)sum;
        s_pdm_cic3_byte_moments[value].weighted1 = (int16_t)weighted1;
        s_pdm_cic3_byte_moments[value].weighted2 = (int16_t)weighted2;
    }
    s_pdm_cic3_lookup_ready = true;
}

#if COMPANION_PDM_CIC3_CHUNK_ACCUMULATE
static int32_t pdm_cic3_triangle_i32(int32_t value)
{
    return (value * (value + 1)) / 2;
}

static void pdm_cic3_add_chunk_byte(uint8_t value,
                                    uint32_t remaining_bits_after_byte,
                                    int32_t *sum,
                                    int32_t *weighted1,
                                    int32_t *weighted2)
{
    const pdm_cic3_byte_moments_t *moments =
        &s_pdm_cic3_byte_moments[value];
    const int32_t remaining = (int32_t)remaining_bits_after_byte;

    *sum += moments->sum;
    *weighted1 += (remaining * (int32_t)moments->sum) +
                  (int32_t)moments->weighted1;
    *weighted2 +=
        (pdm_cic3_triangle_i32(remaining) * (int32_t)moments->sum) +
        (remaining * (int32_t)moments->weighted1) +
        (int32_t)moments->weighted2;
}

static void pdm_cic3_accumulate_aligned_words(const uint32_t *words,
                                              uint32_t word_count)
{
    const uint32_t byte_count = word_count * 4u;
    int32_t sum = 0;
    int32_t weighted1 = 0;
    int32_t weighted2 = 0;
    uint32_t byte_index = 0u;

    for (uint32_t w = 0u; w < word_count; ++w) {
        const uint32_t word = words[w];
#if COMPANION_PDM_BIT_ORDER_LSB
        const uint8_t bytes[4] = {
            (uint8_t)(word & 0xFFu),
            (uint8_t)((word >> 8) & 0xFFu),
            (uint8_t)((word >> 16) & 0xFFu),
            (uint8_t)((word >> 24) & 0xFFu),
        };
#else
        const uint8_t bytes[4] = {
            (uint8_t)((word >> 24) & 0xFFu),
            (uint8_t)((word >> 16) & 0xFFu),
            (uint8_t)((word >> 8) & 0xFFu),
            (uint8_t)(word & 0xFFu),
        };
#endif
        for (uint32_t b = 0u; b < 4u; ++b) {
            const uint32_t remaining_bits_after_byte =
                (byte_count - byte_index - 1u) * 8u;
            pdm_cic3_add_chunk_byte(bytes[b],
                                    remaining_bits_after_byte,
                                    &sum,
                                    &weighted1,
                                    &weighted2);
            byte_index++;
        }
    }

    const int64_t bit_count = (int64_t)byte_count * 8;
    const int64_t triangular_bit_count =
        (bit_count * (bit_count + 1)) / 2;
    const int64_t integrator1 = s_pdm_cic3_state.integrator1;
    const int64_t integrator2 = s_pdm_cic3_state.integrator2;

    s_pdm_cic3_state.integrator3 +=
        (bit_count * integrator2) +
        (triangular_bit_count * integrator1) +
        (int64_t)weighted2;
    s_pdm_cic3_state.integrator2 +=
        (bit_count * integrator1) + (int64_t)weighted1;
    s_pdm_cic3_state.integrator1 += (int64_t)sum;
}
#else
static void pdm_cic3_accumulate_byte(uint8_t value)
{
    const pdm_cic3_byte_moments_t *moments =
        &s_pdm_cic3_byte_moments[value];
    int64_t integrator1 = s_pdm_cic3_state.integrator1;
    int64_t integrator2 = s_pdm_cic3_state.integrator2;

    s_pdm_cic3_state.integrator3 +=
        (8 * integrator2) + (36 * integrator1) + moments->weighted2;
    s_pdm_cic3_state.integrator2 +=
        (8 * integrator1) + moments->weighted1;
    s_pdm_cic3_state.integrator1 += moments->sum;
}

static void pdm_cic3_accumulate_word(uint32_t word)
{
#if COMPANION_PDM_BIT_ORDER_LSB
    pdm_cic3_accumulate_byte((uint8_t)(word & 0xFFu));
    pdm_cic3_accumulate_byte((uint8_t)((word >> 8) & 0xFFu));
    pdm_cic3_accumulate_byte((uint8_t)((word >> 16) & 0xFFu));
    pdm_cic3_accumulate_byte((uint8_t)((word >> 24) & 0xFFu));
#else
    pdm_cic3_accumulate_byte((uint8_t)((word >> 24) & 0xFFu));
    pdm_cic3_accumulate_byte((uint8_t)((word >> 16) & 0xFFu));
    pdm_cic3_accumulate_byte((uint8_t)((word >> 8) & 0xFFu));
    pdm_cic3_accumulate_byte((uint8_t)(word & 0xFFu));
#endif
}
#endif

static void pdm_cic3_accumulate_bit(int64_t bit)
{
    s_pdm_cic3_state.integrator1 += bit;
    s_pdm_cic3_state.integrator2 += s_pdm_cic3_state.integrator1;
    s_pdm_cic3_state.integrator3 += s_pdm_cic3_state.integrator2;
}

static int32_t pdm_cic3_decode_sample(const uint32_t *words, uint32_t *bit_index)
{
    if (((*bit_index & 31u) == 0u) &&
        ((COMPANION_PDM_DECIMATION_FACTOR % 32u) == 0u)) {
        uint32_t word_index = *bit_index / 32u;
#if COMPANION_PDM_CIC3_CHUNK_ACCUMULATE
        pdm_cic3_accumulate_aligned_words(
            &words[word_index],
            COMPANION_PDM_DECIMATION_FACTOR / 32u);
#else
        for (uint32_t w = 0u;
             w < (COMPANION_PDM_DECIMATION_FACTOR / 32u);
             ++w) {
            pdm_cic3_accumulate_word(words[word_index + w]);
        }
#endif
        *bit_index += COMPANION_PDM_DECIMATION_FACTOR;
    } else {
        for (uint32_t b = 0u; b < COMPANION_PDM_DECIMATION_FACTOR; ++b) {
            int64_t bit = pdm_read_bit(words, (*bit_index)++) ? 1 : -1;
            pdm_cic3_accumulate_bit(bit);
        }
    }

    int64_t comb_in = s_pdm_cic3_state.integrator3;
    int64_t comb1 = comb_in - s_pdm_cic3_state.comb1;
    s_pdm_cic3_state.comb1 = comb_in;
    int64_t comb2 = comb1 - s_pdm_cic3_state.comb2;
    s_pdm_cic3_state.comb2 = comb1;
    int64_t comb3 = comb2 - s_pdm_cic3_state.comb3;
    s_pdm_cic3_state.comb3 = comb2;

    const int64_t cic_gain =
        (int64_t)COMPANION_PDM_DECIMATION_FACTOR *
        (int64_t)COMPANION_PDM_DECIMATION_FACTOR;
    int64_t scaled =
        (comb3 * (int64_t)COMPANION_PDM_PCM_SCALE) / cic_gain;
    if (scaled > INT32_MAX) {
        return INT32_MAX;
    }
    if (scaled < INT32_MIN) {
        return INT32_MIN;
    }
    return (int32_t)scaled;
}
#else
static uint32_t pdm_count_ones(const uint32_t *words, uint32_t *bit_index)
{
    uint32_t ones = 0u;
    if (((*bit_index & 31u) == 0u) &&
        ((COMPANION_PDM_DECIMATION_FACTOR % 32u) == 0u)) {
        uint32_t word_index = *bit_index / 32u;
        for (uint32_t w = 0u;
             w < (COMPANION_PDM_DECIMATION_FACTOR / 32u);
             ++w) {
            ones += (uint32_t)__builtin_popcount(words[word_index + w]);
        }
        *bit_index += COMPANION_PDM_DECIMATION_FACTOR;
#if COMPANION_PDM_INVERT_BITS
        ones = COMPANION_PDM_DECIMATION_FACTOR - ones;
#endif
        return ones;
    }

    for (uint32_t b = 0u; b < COMPANION_PDM_DECIMATION_FACTOR; ++b) {
        ones += pdm_read_bit(words, (*bit_index)++);
    }
    return ones;
}
#endif
#endif

static void raw_stats_init(raw_stats_t *stats)
{
    stats->min = UINT_MAX;
    stats->max = 0u;
    stats->sum = 0;
    stats->zero_count = 0u;
    stats->same_count = 0u;
    stats->crc32 = 0u;
}

static void pcm_stats_init(pcm_stats_t *stats)
{
    stats->min = INT16_MAX;
    stats->max = INT16_MIN;
    stats->sum = 0;
    stats->zero_count = 0u;
    stats->clipped_count = 0u;
    stats->crc32 = 0u;
}

static void mic_decode_stats_init(mic_decode_stats_t *stats)
{
    stats->selected_slot = 0u;
    stats->preamp_shift = MIC_PREAMP_SHIFT;
    stats->preamp_clip_count = 0u;
    for (uint32_t slot = 0u; slot < MIC_SLOT_COUNT; ++slot) {
        stats->slot_mean[slot] = 0;
        stats->slot_min[slot] = INT16_MAX;
        stats->slot_max[slot] = INT16_MIN;
        stats->slot_zero_count[slot] = 0u;
        stats->slot_ac_peak[slot] = 0u;
        stats->slot_ac_energy[slot] = 0u;
    }
}

static void analyze_capture(const uint32_t *raw_words,
                            int16_t *pcm_samples,
                            raw_stats_t *raw_stats,
                            pcm_stats_t *pcm_stats,
                            mic_decode_stats_t *decode_stats,
                            bool collect_diagnostics)
{
    pcm_stats_init(pcm_stats);

    if (collect_diagnostics) {
        uint32_t previous = raw_words[0];
        for (uint32_t i = 0u; i < MIC_RAW_WORDS; ++i) {
            uint32_t word = raw_words[i];
            if (word < raw_stats->min) {
                raw_stats->min = word;
            }
            if (word > raw_stats->max) {
                raw_stats->max = word;
            }
            raw_stats->sum += (int64_t)(int32_t)word;
            if (word == 0u) {
                raw_stats->zero_count++;
            }
            if (i != 0u && word == previous) {
                raw_stats->same_count++;
            }
            previous = word;
        }
        raw_stats->crc32 = crc32_update(0u,
                                        (const uint8_t *)raw_words,
                                        MIC_RAW_WORDS * sizeof(raw_words[0]));
    }

#if COMPANION_MIC_BACKEND == COMPANION_MIC_BACKEND_SPH0655_PDM
    int32_t raw_pcm[MIC_PCM_SAMPLES_PER_BATCH];
    int64_t raw_sum = 0;
    uint32_t bit_index = 0u;

#if COMPANION_PDM_USE_CIC3_FILTER
    pdm_cic3_init_lookup();
#endif
    if (collect_diagnostics) {
        decode_stats->selected_slot = 0u;
    }
    for (uint32_t i = 0u; i < MIC_PCM_SAMPLES_PER_BATCH; ++i) {
#if COMPANION_PDM_USE_CIC3_FILTER
        int32_t sample = pdm_cic3_decode_sample(raw_words, &bit_index);
#else
        uint32_t ones = pdm_count_ones(raw_words, &bit_index);
        int32_t density =
            ((int32_t)ones * 2) - (int32_t)COMPANION_PDM_DECIMATION_FACTOR;
        int32_t sample = density * (int32_t)COMPANION_PDM_PCM_SCALE;
#endif
        raw_pcm[i] = sample;
        raw_sum += sample;
        if (collect_diagnostics) {
            if (sample < decode_stats->slot_min[0]) {
                decode_stats->slot_min[0] = sample < INT16_MIN ? INT16_MIN : (int16_t)sample;
            }
            if (sample > decode_stats->slot_max[0]) {
                decode_stats->slot_max[0] = sample > INT16_MAX ? INT16_MAX : (int16_t)sample;
            }
            if (sample == 0) {
                decode_stats->slot_zero_count[0]++;
            }
        }
    }

    const int32_t slot_mean =
        (int32_t)(raw_sum / (int64_t)MIC_PCM_SAMPLES_PER_BATCH);
    if (collect_diagnostics) {
        decode_stats->slot_mean[0] = slot_mean;
    }
    const int32_t preamp_gain = (int32_t)(1u << MIC_PREAMP_SHIFT);
    for (uint32_t i = 0u; i < MIC_PCM_SAMPLES_PER_BATCH; ++i) {
        int32_t centered = raw_pcm[i] - slot_mean;
        if (collect_diagnostics) {
            uint32_t magnitude =
                (uint32_t)(centered < 0 ? -centered : centered);
            if (magnitude > decode_stats->slot_ac_peak[0]) {
                decode_stats->slot_ac_peak[0] = magnitude;
            }
            decode_stats->slot_ac_energy[0] +=
                ((uint64_t)magnitude * (uint64_t)magnitude);
        }

        int32_t amplified = centered * preamp_gain;
        int16_t sample = clamp_pcm16_from_i32(amplified);
        pcm_samples[i] = sample;
        if (collect_diagnostics) {
            if ((int32_t)sample != amplified) {
                decode_stats->preamp_clip_count++;
            }
            if (sample < pcm_stats->min) {
                pcm_stats->min = sample;
            }
            if (sample > pcm_stats->max) {
                pcm_stats->max = sample;
            }
            pcm_stats->sum += sample;
            if (sample == 0) {
                pcm_stats->zero_count++;
            }
            if (sample == INT16_MIN || sample == INT16_MAX) {
                pcm_stats->clipped_count++;
            }
        }
    }
    pcm_stats->crc32 = crc32_update(0u,
                                    (const uint8_t *)pcm_samples,
                                    MIC_PCM_SAMPLES_PER_BATCH * sizeof(pcm_samples[0]));
#else
    mic_decode_stats_init(decode_stats);
    int64_t slot_sum[MIC_SLOT_COUNT] = { 0 };
    for (uint32_t i = 0u; i < MIC_FRAMES_PER_BATCH; ++i) {
        for (uint32_t slot = 0u; slot < MIC_SLOT_COUNT; ++slot) {
            int16_t sample =
                i2s_word_to_pcm16(raw_words[(i * MIC_SLOT_COUNT) + slot]);
            if (sample < decode_stats->slot_min[slot]) {
                decode_stats->slot_min[slot] = sample;
            }
            if (sample > decode_stats->slot_max[slot]) {
                decode_stats->slot_max[slot] = sample;
            }
            if (sample == 0) {
                decode_stats->slot_zero_count[slot]++;
            }
            slot_sum[slot] += sample;
        }
    }

    for (uint32_t slot = 0u; slot < MIC_SLOT_COUNT; ++slot) {
        decode_stats->slot_mean[slot] =
            (int32_t)(slot_sum[slot] / (int64_t)MIC_FRAMES_PER_BATCH);
    }

    for (uint32_t i = 0u; i < MIC_FRAMES_PER_BATCH; ++i) {
        for (uint32_t slot = 0u; slot < MIC_SLOT_COUNT; ++slot) {
            int16_t sample =
                i2s_word_to_pcm16(raw_words[(i * MIC_SLOT_COUNT) + slot]);
            int64_t centered =
                (int64_t)sample - (int64_t)decode_stats->slot_mean[slot];
            uint32_t magnitude =
                (uint32_t)(centered < 0 ? -centered : centered);
            if (magnitude > decode_stats->slot_ac_peak[slot]) {
                decode_stats->slot_ac_peak[slot] = magnitude;
            }
            decode_stats->slot_ac_energy[slot] +=
                ((uint64_t)magnitude * (uint64_t)magnitude);
        }
    }

    decode_stats->selected_slot = MIC_SELECTED_SLOT;
#if COMPANION_MIC_SLOT_AUTO_SELECT
    if ((decode_stats->slot_ac_energy[1] > decode_stats->slot_ac_energy[0]) ||
        ((decode_stats->slot_ac_energy[1] == decode_stats->slot_ac_energy[0]) &&
         (decode_stats->slot_ac_peak[1] > decode_stats->slot_ac_peak[0]))) {
        decode_stats->selected_slot = 1u;
    }
#endif

    const uint32_t selected_slot = decode_stats->selected_slot;
    const int32_t preamp_gain = (int32_t)(1u << MIC_PREAMP_SHIFT);
    for (uint32_t i = 0u; i < MIC_PCM_SAMPLES_PER_BATCH; ++i) {
        int32_t centered_sum = 0;
        const uint32_t source_base = i * MIC_DOWNSAMPLE_FACTOR;
        for (uint32_t d = 0u; d < MIC_DOWNSAMPLE_FACTOR; ++d) {
            int16_t raw_sample = i2s_word_to_pcm16(
                raw_words[((source_base + d) * MIC_SLOT_COUNT) + selected_slot]);
            centered_sum +=
                (int32_t)raw_sample - decode_stats->slot_mean[selected_slot];
        }
        int32_t centered = centered_sum / (int32_t)MIC_DOWNSAMPLE_FACTOR;
        int32_t amplified = centered * preamp_gain;
        int16_t sample = clamp_pcm16_from_i32(amplified);
        pcm_samples[i] = sample;
        if ((int32_t)sample != amplified) {
            decode_stats->preamp_clip_count++;
        }
        if (sample < pcm_stats->min) {
            pcm_stats->min = sample;
        }
        if (sample > pcm_stats->max) {
            pcm_stats->max = sample;
        }
        pcm_stats->sum += sample;
        if (sample == 0) {
            pcm_stats->zero_count++;
        }
        if (sample == INT16_MIN || sample == INT16_MAX) {
            pcm_stats->clipped_count++;
        }
    }
    pcm_stats->crc32 = crc32_update(0u,
                                    (const uint8_t *)pcm_samples,
                                    MIC_PCM_SAMPLES_PER_BATCH * sizeof(pcm_samples[0]));
#endif
}

static const char *mic_capture_quality_label(const raw_stats_t *raw_stats,
                                             const pcm_stats_t *pcm_stats,
                                             const mic_decode_stats_t *decode_stats)
{
    const uint32_t selected_slot = decode_stats->selected_slot;
    if (raw_stats->zero_count == MIC_RAW_WORDS) {
        return "all_zero";
    }
    if ((raw_stats->same_count + 1u) >= MIC_RAW_WORDS) {
        return "stuck";
    }
    if (decode_stats->slot_ac_peak[selected_slot] < 8u ||
        pcm_stats->zero_count == MIC_PCM_SAMPLES_PER_BATCH) {
        return "silent";
    }
    if (pcm_stats->clipped_count > (MIC_PCM_SAMPLES_PER_BATCH / 8u)) {
        return "clipped";
    }
    if (decode_stats->preamp_clip_count > (MIC_PCM_SAMPLES_PER_BATCH / 4u)) {
        return "preamp_hot";
    }
    return "active";
}

static void feed_drop_to_recording_fsm(void)
{
    comp_microphone_frame_batch_t batch = {
        .frame_count = 0u,
        .samples_per_frame = MIC_PCM_SAMPLES_PER_BATCH,
        .bytes_per_frame = MIC_PCM_SAMPLES_PER_BATCH * sizeof(int16_t),
        .duration_ms = 0u,
        .dropped_frames = 1u,
        .crc32 = 0u,
    };
    (void)comp_recording_fsm_feed_microphone_frames(&s_recording_fsm, &batch);
}

static void run_microphone_probe(void)
{
    comp_recording_result_t result = comp_recording_fsm_dispatch(
        &s_recording_fsm,
        COMP_RECORDING_EVENT_START_REQUEST,
        COMP_RECORDING_SOURCE_SYNTHETIC_FIXTURE);

    printf("[mic] start result=%lu state=%s\r\n",
           (unsigned long)result,
           comp_recording_state_name(s_recording_fsm.state));

    for (uint32_t block = 0u; block < MIC_CAPTURE_BLOCKS; ++block) {
        capture_microphone_block(block, true, "mic");
    }

    (void)comp_recording_fsm_dispatch(&s_recording_fsm,
                                      COMP_RECORDING_EVENT_STOP_REQUEST,
                                      COMP_RECORDING_SOURCE_SYNTHETIC_FIXTURE);
    (void)comp_recording_fsm_dispatch(&s_recording_fsm,
                                      COMP_RECORDING_EVENT_SESSION_FINISHED,
                                      COMP_RECORDING_SOURCE_SYNTHETIC_FIXTURE);

    print_recording_summary("mic");

    (void)comp_recording_fsm_dispatch(&s_recording_fsm,
                                      COMP_RECORDING_EVENT_TRANSFER_BEGIN,
                                      COMP_RECORDING_SOURCE_SYNTHETIC_FIXTURE);
    (void)comp_recording_fsm_dispatch(&s_recording_fsm,
                                      COMP_RECORDING_EVENT_TRANSFER_FINISHED,
                                      COMP_RECORDING_SOURCE_SYNTHETIC_FIXTURE);
    (void)comp_recording_fsm_dispatch(&s_recording_fsm,
                                      COMP_RECORDING_EVENT_RECOVERY_COMPLETE,
                                      COMP_RECORDING_SOURCE_SYNTHETIC_FIXTURE);
}

static bool capture_microphone_block(uint32_t block_index, bool verbose, const char *tag)
{
    static uint32_t raw_words[MIC_RAW_WORDS];
    static int16_t pcm_samples[MIC_PCM_SAMPLES_PER_BATCH];
    static int16_t ble_compacted_samples[MIC_PCM_SAMPLES_PER_BATCH];
    uint32_t dma_overruns = 0u;

#if (COMPANION_MIC_BACKEND == COMPANION_MIC_BACKEND_SPH0655_PDM) && COMPANION_PDM_RAW_SAI_USE_DMA
    HAL_StatusTypeDef status =
        pdm_raw_dma_read_block(raw_words, 1000u, &dma_overruns);
#else
    HAL_StatusTypeDef status = HAL_SAI_Receive(&hsai_BlockA1,
                                               (uint8_t *)raw_words,
                                               MIC_RAW_WORDS,
                                               1000u);
#if (COMPANION_MIC_BACKEND == COMPANION_MIC_BACKEND_SPH0655_PDM) && COMPANION_PDM_RESTART_EACH_BLOCK
    if (status == HAL_OK) {
        __HAL_SAI_DISABLE(&hsai_BlockA1);
        SET_BIT(hsai_BlockA1.Instance->CR2, SAI_xCR2_FFLUSH);
    }
#endif
#endif
    if (status != HAL_OK) {
        printf("[%s] block=%lu status=%s sai_error=0x%08lX\r\n",
               tag,
               (unsigned long)block_index,
               hal_status_name(status),
               (unsigned long)HAL_SAI_GetError(&hsai_BlockA1));
        feed_drop_to_recording_fsm();
        if (s_ble_session_active) {
            (void)Companion_BleAudio_SendSessionError(COMP_AUDIO_SESSION_ERROR_TRANSPORT);
            s_ble_session_active = false;
            Companion_BleAudio_RequestIdleLink("mic_capture_failed");
        }
        return false;
    }

    raw_stats_t raw_stats = { 0 };
    pcm_stats_t pcm_stats;
    mic_decode_stats_t decode_stats = { 0 };
    if (verbose) {
        raw_stats_init(&raw_stats);
        mic_decode_stats_init(&decode_stats);
    }
    analyze_capture(raw_words,
                    pcm_samples,
                    &raw_stats,
                    &pcm_stats,
                    &decode_stats,
                    verbose);
    recording_flash_append_pcm((const uint8_t *)pcm_samples, sizeof(pcm_samples));

    comp_microphone_frame_batch_t batch = {
        .frame_count = 1u,
        .samples_per_frame = MIC_PCM_SAMPLES_PER_BATCH,
        .bytes_per_frame = MIC_PCM_SAMPLES_PER_BATCH * sizeof(pcm_samples[0]),
        .duration_ms = (MIC_PCM_SAMPLES_PER_BATCH * 1000u) / MIC_SAMPLE_RATE_HZ,
        .dropped_frames = 0u,
        .crc32 = pcm_stats.crc32,
    };
    comp_recording_result_t result =
        comp_recording_fsm_feed_microphone_frames(&s_recording_fsm, &batch);

    if (s_ble_session_active) {
        uint16_t mic_frame_pcm_bytes = (uint16_t)sizeof(pcm_samples);
        uint16_t ble_payload_bytes = mic_frame_pcm_bytes;
        const uint8_t *ble_payload = (const uint8_t *)pcm_samples;
        bool use_partial_ble_frame = false;
        if (s_ble_type_ready_autostream_active &&
            s_ble_type_ready_autostream_pcm_bytes > 0u &&
            ble_payload_bytes > s_ble_type_ready_autostream_pcm_bytes) {
            /*
             * Keep BLE load bounded while preserving the real microphone time span.
             * The payload is an evenly sampled compact view of this full 10 ms frame.
             */
            ble_payload_bytes = s_ble_type_ready_autostream_pcm_bytes;
            use_partial_ble_frame = true;
        }
        comp_audio_stream_status_t stream_status = COMP_AUDIO_STREAM_OK;
        if (use_partial_ble_frame) {
            uint16_t payload_samples =
                (uint16_t)(ble_payload_bytes / sizeof(pcm_samples[0]));
            ble_payload_bytes = (uint16_t)(payload_samples * sizeof(pcm_samples[0]));
            if (payload_samples == 0u) {
                stream_status = COMP_AUDIO_STREAM_BAD_ARGUMENT;
            } else {
                for (uint16_t i = 0u; i < payload_samples; ++i) {
                    uint32_t source_index = 0u;
                    if (payload_samples > 1u) {
                        source_index =
                            ((uint32_t)i * (MIC_PCM_SAMPLES_PER_BATCH - 1u)) +
                            (((uint32_t)payload_samples - 1u) / 2u);
                        source_index /= ((uint32_t)payload_samples - 1u);
                    }
                    ble_compacted_samples[i] = pcm_samples[source_index];
                }
                ble_payload = (const uint8_t *)ble_compacted_samples;
                stream_status = Companion_BleAudio_SendPcmFrame(ble_payload,
                                                               ble_payload_bytes,
                                                               mic_frame_pcm_bytes);
            }
        } else {
            stream_status = Companion_BleAudio_SendPcmBytes(ble_payload,
                                                           mic_frame_pcm_bytes);
        }
        if (stream_status != COMP_AUDIO_STREAM_OK) {
            printf("[%s] ble_audio status=%s raw=0x%02X id=%lu block=%lu\r\n",
                   tag,
                   comp_audio_stream_status_name(stream_status),
                   (unsigned int)comp_audio_stream_stm32wb_last_notify_status(),
                   (unsigned long)s_ble_session_id,
                   (unsigned long)block_index);
            (void)Companion_BleAudio_SendSessionError(COMP_AUDIO_SESSION_ERROR_TRANSPORT);
            s_ble_session_active = false;
            if (s_recording_fsm.active_source == COMP_RECORDING_SOURCE_HOST_BLE_CONTROL) {
                clear_ble_type_ready_autostream();
                cancel_recording(COMP_RECORDING_SOURCE_HOST_BLE_CONTROL,
                                 "ble_audio_notify_failed");
            }
        }
    }

    if (verbose) {
        const char *quality =
            mic_capture_quality_label(&raw_stats, &pcm_stats, &decode_stats);
        printf("[%s] block=%lu status=ok quality=%s raw_min=0x%08lX raw_max=0x%08lX raw_zero=%lu raw_same=%lu raw_crc=0x%08lX slot=%lu slot0_mean=%ld slot0_peak=%lu slot1_mean=%ld slot1_peak=%lu gain=%lux preclip=%lu pcm_min=%d pcm_max=%d pcm_mean=%ld pcm_zero=%lu pcm_clip=%lu pcm_crc=0x%08lX feed=%lu\r\n",
               tag,
               (unsigned long)block_index,
               quality,
               (unsigned long)raw_stats.min,
               (unsigned long)raw_stats.max,
               (unsigned long)raw_stats.zero_count,
               (unsigned long)raw_stats.same_count,
               (unsigned long)raw_stats.crc32,
               (unsigned long)decode_stats.selected_slot,
               (long)decode_stats.slot_mean[0],
               (unsigned long)decode_stats.slot_ac_peak[0],
               (long)decode_stats.slot_mean[1],
               (unsigned long)decode_stats.slot_ac_peak[1],
               (unsigned long)(1u << decode_stats.preamp_shift),
               (unsigned long)decode_stats.preamp_clip_count,
               (int)pcm_stats.min,
               (int)pcm_stats.max,
               (long)(pcm_stats.sum / (int64_t)MIC_PCM_SAMPLES_PER_BATCH),
               (unsigned long)pcm_stats.zero_count,
               (unsigned long)pcm_stats.clipped_count,
               (unsigned long)pcm_stats.crc32,
               (unsigned long)result);
#if (COMPANION_MIC_BACKEND == COMPANION_MIC_BACKEND_SPH0655_PDM) && COMPANION_PDM_RAW_SAI_USE_DMA
        if (dma_overruns != 0u) {
            printf("[%s] block=%lu dma_rx_overruns=%lu\r\n",
                   tag,
                   (unsigned long)block_index,
                   (unsigned long)dma_overruns);
        }
#endif
    }
    return true;
}

static void print_recording_summary(const char *tag)
{
    const comp_recording_metadata_t *metadata = comp_recording_fsm_metadata(&s_recording_fsm);
    if (metadata == NULL) {
        printf("[%s] summary unavailable\r\n", tag);
        return;
    }
    printf("[%s] stop state=%s id=%lu duration_ms=%lu frames=%lu bytes=%lu dropped=%lu crc=0x%08lX sync=%lu\r\n",
           tag,
           comp_recording_state_name(s_recording_fsm.state),
           (unsigned long)metadata->recording_id,
           (unsigned long)metadata->duration_ms,
           (unsigned long)metadata->frame_count,
           (unsigned long)metadata->total_length,
           (unsigned long)metadata->dropped_frames,
           (unsigned long)metadata->content_crc32,
           (unsigned long)metadata->sync_state);
}

static void print_diag_tail(void)
{
    comp_diag_event_t events[16];
    size_t count = comp_diag_log_read_tail(events, sizeof(events) / sizeof(events[0]));

    printf("[diag] tail_count=%lu total=%lu\r\n",
           (unsigned long)count,
           (unsigned long)comp_diag_log_count());

    for (size_t i = 0u; i < count; ++i) {
        printf("[diag] #%lu t=%lu source=%s event=0x%02X sev=%s args=%lu,%lu,%lu,%lu\r\n",
               (unsigned long)events[i].sequence,
               (unsigned long)events[i].t_ms,
               comp_diag_source_name(events[i].source),
               events[i].event_id,
               comp_diag_severity_name(events[i].severity),
               (unsigned long)events[i].arg0,
               (unsigned long)events[i].arg1,
               (unsigned long)events[i].arg2,
               (unsigned long)events[i].arg3);
    }
}

static void SystemClock_Config(void)
{
    RCC_OscInitTypeDef RCC_OscInitStruct = {0};
    RCC_ClkInitTypeDef RCC_ClkInitStruct = {0};

    HAL_PWR_EnableBkUpAccess();
    __HAL_RCC_LSEDRIVE_CONFIG(RCC_LSEDRIVE_LOW);
    __HAL_PWR_VOLTAGESCALING_CONFIG(PWR_REGULATOR_VOLTAGE_SCALE1);

    RCC_OscInitStruct.OscillatorType = RCC_OSCILLATORTYPE_HSI48 |
                                       RCC_OSCILLATORTYPE_HSI |
                                       RCC_OSCILLATORTYPE_HSE |
                                       RCC_OSCILLATORTYPE_LSE;
    RCC_OscInitStruct.HSEState = RCC_HSE_ON;
    RCC_OscInitStruct.LSEState = RCC_LSE_ON;
    RCC_OscInitStruct.HSIState = RCC_HSI_ON;
    RCC_OscInitStruct.HSI48State = RCC_HSI48_ON;
    RCC_OscInitStruct.HSICalibrationValue = RCC_HSICALIBRATION_DEFAULT;
    RCC_OscInitStruct.PLL.PLLState = RCC_PLL_ON;
    RCC_OscInitStruct.PLL.PLLSource = RCC_PLLSOURCE_HSE;
    RCC_OscInitStruct.PLL.PLLM = RCC_PLLM_DIV8;
    RCC_OscInitStruct.PLL.PLLN = 32u;
    RCC_OscInitStruct.PLL.PLLP = RCC_PLLP_DIV2;
    RCC_OscInitStruct.PLL.PLLQ = RCC_PLLQ_DIV2;
    RCC_OscInitStruct.PLL.PLLR = RCC_PLLR_DIV2;
    if (HAL_RCC_OscConfig(&RCC_OscInitStruct) != HAL_OK) {
        Error_Handler();
    }

    RCC_ClkInitStruct.ClockType = RCC_CLOCKTYPE_HCLK4 |
                                  RCC_CLOCKTYPE_HCLK2 |
                                  RCC_CLOCKTYPE_HCLK |
                                  RCC_CLOCKTYPE_SYSCLK |
                                  RCC_CLOCKTYPE_PCLK1 |
                                  RCC_CLOCKTYPE_PCLK2;
    RCC_ClkInitStruct.SYSCLKSource = RCC_SYSCLKSOURCE_HSE;
    RCC_ClkInitStruct.AHBCLKDivider = RCC_SYSCLK_DIV1;
    RCC_ClkInitStruct.APB1CLKDivider = RCC_HCLK_DIV1;
    RCC_ClkInitStruct.APB2CLKDivider = RCC_HCLK_DIV1;
    RCC_ClkInitStruct.AHBCLK2Divider = RCC_SYSCLK_DIV1;
    RCC_ClkInitStruct.AHBCLK4Divider = RCC_SYSCLK_DIV1;

    if (HAL_RCC_ClockConfig(&RCC_ClkInitStruct, FLASH_LATENCY_1) != HAL_OK) {
        Error_Handler();
    }
}

static void PeriphCommonClock_Config(void)
{
    RCC_PeriphCLKInitTypeDef PeriphClkInitStruct = {0};

    PeriphClkInitStruct.PeriphClockSelection = RCC_PERIPHCLK_SMPS | RCC_PERIPHCLK_RFWAKEUP;
    PeriphClkInitStruct.RFWakeUpClockSelection = RCC_RFWKPCLKSOURCE_LSE;
    PeriphClkInitStruct.SmpsClockSelection = RCC_SMPSCLKSOURCE_HSE;
    PeriphClkInitStruct.SmpsDivSelection = RCC_SMPSCLKDIV_RANGE1;

    if (HAL_RCCEx_PeriphCLKConfig(&PeriphClkInitStruct) != HAL_OK) {
        Error_Handler();
    }
}

static void MX_IPCC_Init(void)
{
    hipcc.Instance = IPCC;
    if (HAL_IPCC_Init(&hipcc) != HAL_OK) {
        Error_Handler();
    }
}

static void MX_RNG_Init(void)
{
    hrng.Instance = RNG;
    hrng.Init.ClockErrorDetection = RNG_CED_ENABLE;
    if (HAL_RNG_Init(&hrng) != HAL_OK) {
        Error_Handler();
    }
}

static void MX_RTC_Init(void)
{
    hrtc.Instance = RTC;
    hrtc.Init.HourFormat = RTC_HOURFORMAT_24;
    hrtc.Init.AsynchPrediv = CFG_RTC_ASYNCH_PRESCALER;
    hrtc.Init.SynchPrediv = CFG_RTC_SYNCH_PRESCALER;
    hrtc.Init.OutPut = RTC_OUTPUT_DISABLE;
    hrtc.Init.OutPutPolarity = RTC_OUTPUT_POLARITY_HIGH;
    hrtc.Init.OutPutType = RTC_OUTPUT_TYPE_OPENDRAIN;
    hrtc.Init.OutPutRemap = RTC_OUTPUT_REMAP_NONE;
    if (HAL_RTC_Init(&hrtc) != HAL_OK) {
        Error_Handler();
    }
    if (HAL_RTCEx_SetWakeUpTimer_IT(&hrtc, 0u, RTC_WAKEUPCLOCK_RTCCLK_DIV16) != HAL_OK) {
        Error_Handler();
    }
}

static void MX_RF_Init(void)
{
}

static void MX_DMA_Init(void)
{
    __HAL_RCC_DMAMUX1_CLK_ENABLE();
    __HAL_RCC_DMA1_CLK_ENABLE();
    __HAL_RCC_DMA2_CLK_ENABLE();

    HAL_NVIC_SetPriority(DMA2_Channel4_IRQn, 15, 0);
    HAL_NVIC_EnableIRQ(DMA2_Channel4_IRQn);
}

static void MX_GPIO_Init(void)
{
    GPIO_InitTypeDef GPIO_InitStruct = {0};

    __HAL_RCC_GPIOA_CLK_ENABLE();
    __HAL_RCC_GPIOB_CLK_ENABLE();
    __HAL_RCC_GPIOC_CLK_ENABLE();
    __HAL_RCC_GPIOD_CLK_ENABLE();

    HAL_GPIO_WritePin(BOARD_SPI2_CS_GPIO_PORT, BOARD_SPI2_CS_PIN, GPIO_PIN_SET);
    HAL_GPIO_WritePin(BOARD_MAX98357_SD_GPIO_PORT, BOARD_MAX98357_SD_PIN, GPIO_PIN_RESET);
#if COMPANION_TOUCH_RST_WIRED
    HAL_GPIO_WritePin(BOARD_TOUCH_RST_GPIO_PORT,
                      BOARD_TOUCH_RST_PIN,
                      GPIO_PIN_SET);
#endif

    GPIO_InitStruct.Pin = BOARD_SPI2_CS_PIN | BOARD_MAX98357_SD_PIN;
    GPIO_InitStruct.Mode = GPIO_MODE_OUTPUT_PP;
    GPIO_InitStruct.Pull = GPIO_NOPULL;
    GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_LOW;
    HAL_GPIO_Init(GPIOA, &GPIO_InitStruct);

    GPIO_InitStruct.Pin = BOARD_SW1_PIN;
    GPIO_InitStruct.Mode = GPIO_MODE_INPUT;
    GPIO_InitStruct.Pull = GPIO_PULLUP;
    GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_HIGH;
    HAL_GPIO_Init(BOARD_SW1_GPIO_PORT, &GPIO_InitStruct);

    GPIO_InitStruct.Pin = BOARD_SW2_PIN | BOARD_SW3_PIN;
    GPIO_InitStruct.Mode = GPIO_MODE_INPUT;
    GPIO_InitStruct.Pull = GPIO_PULLUP;
    GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_HIGH;
    HAL_GPIO_Init(GPIOD, &GPIO_InitStruct);

#if COMPANION_TOUCH_RST_WIRED
    GPIO_InitStruct.Pin = BOARD_TOUCH_RST_PIN;
    GPIO_InitStruct.Mode = GPIO_MODE_OUTPUT_PP;
    GPIO_InitStruct.Pull = GPIO_NOPULL;
    GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_LOW;
    HAL_GPIO_Init(BOARD_TOUCH_RST_GPIO_PORT, &GPIO_InitStruct);
#endif

#if COMPANION_TOUCH_INT_WIRED
    GPIO_InitStruct.Pin = BOARD_TOUCH_INT_PIN;
    GPIO_InitStruct.Mode = GPIO_MODE_IT_FALLING;
    GPIO_InitStruct.Pull = GPIO_PULLUP;
    GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_HIGH;
    HAL_GPIO_Init(BOARD_TOUCH_INT_GPIO_PORT, &GPIO_InitStruct);

    HAL_NVIC_SetPriority(EXTI9_5_IRQn, 8, 0);
    HAL_NVIC_EnableIRQ(EXTI9_5_IRQn);
#endif
}

static void MX_I2C3_Init(void)
{
    hi2c3.Instance = I2C3;
    hi2c3.Init.Timing = 0x00707CBBu;
    hi2c3.Init.OwnAddress1 = 0u;
    hi2c3.Init.AddressingMode = I2C_ADDRESSINGMODE_7BIT;
    hi2c3.Init.DualAddressMode = I2C_DUALADDRESS_DISABLE;
    hi2c3.Init.OwnAddress2 = 0u;
    hi2c3.Init.OwnAddress2Masks = I2C_OA2_NOMASK;
    hi2c3.Init.GeneralCallMode = I2C_GENERALCALL_DISABLE;
    hi2c3.Init.NoStretchMode = I2C_NOSTRETCH_DISABLE;

    if (HAL_I2C_Init(&hi2c3) != HAL_OK) {
        Error_Handler();
    }
    if (HAL_I2CEx_ConfigAnalogFilter(&hi2c3, I2C_ANALOGFILTER_ENABLE) != HAL_OK) {
        Error_Handler();
    }
    if (HAL_I2CEx_ConfigDigitalFilter(&hi2c3, 0u) != HAL_OK) {
        Error_Handler();
    }
}

void MX_USART1_UART_Init(void)
{
    huart1.Instance = USART1;
    huart1.Init.BaudRate = 115200;
    huart1.Init.WordLength = UART_WORDLENGTH_8B;
    huart1.Init.StopBits = UART_STOPBITS_1;
    huart1.Init.Parity = UART_PARITY_NONE;
    huart1.Init.Mode = UART_MODE_TX_RX;
    huart1.Init.HwFlowCtl = UART_HWCONTROL_NONE;
    huart1.Init.OverSampling = UART_OVERSAMPLING_8;
    huart1.Init.OneBitSampling = UART_ONE_BIT_SAMPLE_DISABLE;
    huart1.Init.ClockPrescaler = UART_PRESCALER_DIV1;
    huart1.AdvancedInit.AdvFeatureInit = UART_ADVFEATURE_NO_INIT;

    if (HAL_UART_Init(&huart1) != HAL_OK) {
        Error_Handler();
    }
    if (HAL_UARTEx_SetTxFifoThreshold(&huart1, UART_TXFIFO_THRESHOLD_1_8) != HAL_OK) {
        Error_Handler();
    }
    if (HAL_UARTEx_SetRxFifoThreshold(&huart1, UART_RXFIFO_THRESHOLD_1_8) != HAL_OK) {
        Error_Handler();
    }
    if (HAL_UARTEx_DisableFifoMode(&huart1) != HAL_OK) {
        Error_Handler();
    }
}

static void MX_SPI2_Init(void)
{
    hspi2.Instance = SPI2;
    hspi2.Init.Mode = SPI_MODE_MASTER;
    hspi2.Init.Direction = SPI_DIRECTION_2LINES;
    hspi2.Init.DataSize = SPI_DATASIZE_8BIT;
    hspi2.Init.CLKPolarity = SPI_POLARITY_LOW;
    hspi2.Init.CLKPhase = SPI_PHASE_1EDGE;
    hspi2.Init.NSS = SPI_NSS_SOFT;
    hspi2.Init.BaudRatePrescaler = BOARD_EPAPER_SPI_BAUDRATE_PRESCALER;
    hspi2.Init.FirstBit = SPI_FIRSTBIT_MSB;
    hspi2.Init.TIMode = SPI_TIMODE_DISABLE;
    hspi2.Init.CRCCalculation = SPI_CRCCALCULATION_DISABLE;
    hspi2.Init.CRCPolynomial = 7u;
    hspi2.Init.CRCLength = SPI_CRC_LENGTH_DATASIZE;
    hspi2.Init.NSSPMode = SPI_NSS_PULSE_ENABLE;

    if (HAL_SPI_Init(&hspi2) != HAL_OK) {
        Error_Handler();
    }
}

static void MX_QUADSPI_Init(void)
{
    hqspi.Instance = QUADSPI;
    hqspi.Init.ClockPrescaler = 15u;
    hqspi.Init.FifoThreshold = 4u;
    hqspi.Init.SampleShifting = QSPI_SAMPLE_SHIFTING_NONE;
    hqspi.Init.FlashSize = 23u;
    hqspi.Init.ChipSelectHighTime = QSPI_CS_HIGH_TIME_8_CYCLE;
    hqspi.Init.ClockMode = QSPI_CLOCK_MODE_0;

    if (HAL_QSPI_Init(&hqspi) != HAL_OK) {
        Error_Handler();
    }
}

static void MX_SAI1_Init(void)
{
    hsai_BlockA1.Instance = SAI1_Block_A;
#if COMPANION_MIC_BACKEND == COMPANION_MIC_BACKEND_SPH0655_PDM
#if COMPANION_PDM_USE_HARDWARE_INTERFACE
    hsai_BlockA1.Init.Protocol = SAI_FREE_PROTOCOL;
    hsai_BlockA1.Init.AudioMode = SAI_MODEMASTER_RX;
    hsai_BlockA1.Init.DataSize = SAI_DATASIZE_32;
    hsai_BlockA1.Init.FirstBit = SAI_FIRSTBIT_MSB;
    hsai_BlockA1.Init.ClockStrobing = SAI_CLOCKSTROBING_FALLINGEDGE;
    hsai_BlockA1.Init.Synchro = SAI_ASYNCHRONOUS;
    hsai_BlockA1.Init.OutputDrive = SAI_OUTPUTDRIVE_DISABLE;
    hsai_BlockA1.Init.NoDivider = SAI_MASTERDIVIDER_DISABLE;
    hsai_BlockA1.Init.MckOutput = SAI_MCK_OUTPUT_DISABLE;
    hsai_BlockA1.Init.FIFOThreshold = SAI_FIFOTHRESHOLD_EMPTY;
    hsai_BlockA1.Init.AudioFrequency =
        ((COMPANION_PDM_CLOCK_KHZ * 1000u) / 32u) * 4u;
    hsai_BlockA1.Init.SynchroExt = SAI_SYNCEXT_DISABLE;
    hsai_BlockA1.Init.MonoStereoMode = SAI_STEREOMODE;
    hsai_BlockA1.Init.CompandingMode = SAI_NOCOMPANDING;
    hsai_BlockA1.Init.TriState = SAI_OUTPUT_NOTRELEASED;
    hsai_BlockA1.Init.MckOverSampling = SAI_MCK_OVERSAMPLING_DISABLE;
    hsai_BlockA1.Init.PdmInit.Activation = ENABLE;
    hsai_BlockA1.Init.PdmInit.ClockEnable = COMPANION_PDM_CLOCK_ENABLE;
    hsai_BlockA1.Init.PdmInit.MicPairsNbr = COMPANION_PDM_MIC_PAIRS;
    hsai_BlockA1.FrameInit.FrameLength = 32u;
    hsai_BlockA1.FrameInit.ActiveFrameLength = 1u;
    hsai_BlockA1.FrameInit.FSDefinition = SAI_FS_STARTFRAME;
    hsai_BlockA1.FrameInit.FSPolarity = SAI_FS_ACTIVE_HIGH;
    hsai_BlockA1.FrameInit.FSOffset = SAI_FS_FIRSTBIT;
    hsai_BlockA1.SlotInit.FirstBitOffset = 0u;
    hsai_BlockA1.SlotInit.SlotSize = SAI_SLOTSIZE_DATASIZE;
    hsai_BlockA1.SlotInit.SlotNumber = 4u;
    hsai_BlockA1.SlotInit.SlotActive = COMPANION_PDM_SLOT_ACTIVE;
#else
    hsai_BlockA1.Init.Protocol = SAI_FREE_PROTOCOL;
    hsai_BlockA1.Init.AudioMode = SAI_MODEMASTER_RX;
    hsai_BlockA1.Init.DataSize = SAI_DATASIZE_32;
    hsai_BlockA1.Init.FirstBit = SAI_FIRSTBIT_MSB;
    hsai_BlockA1.Init.ClockStrobing = COMPANION_MIC_CLOCK_STROBING;
    hsai_BlockA1.Init.Synchro = SAI_ASYNCHRONOUS;
    hsai_BlockA1.Init.OutputDrive = SAI_OUTPUTDRIVE_ENABLE;
    hsai_BlockA1.Init.NoDivider = SAI_MASTERDIVIDER_DISABLE;
    hsai_BlockA1.Init.MckOutput = SAI_MCK_OUTPUT_DISABLE;
    hsai_BlockA1.Init.FIFOThreshold = SAI_FIFOTHRESHOLD_1QF;
#if COMPANION_PDM_RAW_SAI_USE_EXPLICIT_MCKDIV
    hsai_BlockA1.Init.AudioFrequency = SAI_AUDIO_FREQUENCY_MCKDIV;
    hsai_BlockA1.Init.Mckdiv = COMPANION_PDM_RAW_SAI_MCKDIV;
#else
    hsai_BlockA1.Init.AudioFrequency = COMPANION_PDM_RAW_SAI_AUDIO_FREQUENCY;
#endif
    hsai_BlockA1.Init.SynchroExt = SAI_SYNCEXT_DISABLE;
    hsai_BlockA1.Init.MonoStereoMode = SAI_STEREOMODE;
    hsai_BlockA1.Init.CompandingMode = SAI_NOCOMPANDING;
    hsai_BlockA1.Init.TriState = SAI_OUTPUT_NOTRELEASED;
    hsai_BlockA1.Init.MckOverSampling = SAI_MCK_OVERSAMPLING_DISABLE;
    hsai_BlockA1.Init.PdmInit.Activation = DISABLE;
    hsai_BlockA1.Init.PdmInit.ClockEnable = 0u;
    hsai_BlockA1.Init.PdmInit.MicPairsNbr = 1u;
    hsai_BlockA1.FrameInit.FrameLength = 64u;
    hsai_BlockA1.FrameInit.ActiveFrameLength = 32u;
    hsai_BlockA1.FrameInit.FSDefinition = SAI_FS_CHANNEL_IDENTIFICATION;
    hsai_BlockA1.FrameInit.FSPolarity = SAI_FS_ACTIVE_LOW;
    hsai_BlockA1.FrameInit.FSOffset = SAI_FS_BEFOREFIRSTBIT;
    hsai_BlockA1.SlotInit.FirstBitOffset = 0u;
    hsai_BlockA1.SlotInit.SlotSize = SAI_SLOTSIZE_32B;
    hsai_BlockA1.SlotInit.SlotNumber = 2u;
    hsai_BlockA1.SlotInit.SlotActive = SAI_SLOTACTIVE_0 | SAI_SLOTACTIVE_1;
#endif
#else
    hsai_BlockA1.Init.Protocol = SAI_FREE_PROTOCOL;
    hsai_BlockA1.Init.AudioMode = SAI_MODEMASTER_RX;
    hsai_BlockA1.Init.DataSize = SAI_DATASIZE_32;
    hsai_BlockA1.Init.FirstBit = SAI_FIRSTBIT_MSB;
    hsai_BlockA1.Init.ClockStrobing = COMPANION_MIC_CLOCK_STROBING;
    hsai_BlockA1.Init.Synchro = SAI_ASYNCHRONOUS;
    hsai_BlockA1.Init.OutputDrive = SAI_OUTPUTDRIVE_ENABLE;
    hsai_BlockA1.Init.NoDivider = SAI_MASTERDIVIDER_ENABLE;
    hsai_BlockA1.Init.MckOutput = SAI_MCK_OUTPUT_DISABLE;
    hsai_BlockA1.Init.FIFOThreshold = SAI_FIFOTHRESHOLD_1QF;
    hsai_BlockA1.Init.AudioFrequency = SAI_AUDIO_FREQUENCY_16K;
    hsai_BlockA1.Init.SynchroExt = SAI_SYNCEXT_DISABLE;
    hsai_BlockA1.Init.MonoStereoMode = SAI_STEREOMODE;
    hsai_BlockA1.Init.CompandingMode = SAI_NOCOMPANDING;
    hsai_BlockA1.Init.TriState = SAI_OUTPUT_NOTRELEASED;
    hsai_BlockA1.Init.MckOverSampling = SAI_MCK_OVERSAMPLING_DISABLE;
    hsai_BlockA1.FrameInit.FrameLength = 64u;
    hsai_BlockA1.FrameInit.ActiveFrameLength = 32u;
    hsai_BlockA1.FrameInit.FSDefinition = SAI_FS_CHANNEL_IDENTIFICATION;
    hsai_BlockA1.FrameInit.FSPolarity = SAI_FS_ACTIVE_LOW;
    hsai_BlockA1.FrameInit.FSOffset = SAI_FS_BEFOREFIRSTBIT;
    hsai_BlockA1.SlotInit.FirstBitOffset = 0u;
    hsai_BlockA1.SlotInit.SlotSize = SAI_SLOTSIZE_32B;
    hsai_BlockA1.SlotInit.SlotNumber = 2u;
    hsai_BlockA1.SlotInit.SlotActive = SAI_SLOTACTIVE_0 | SAI_SLOTACTIVE_1;
#endif

    if (HAL_SAI_Init(&hsai_BlockA1) != HAL_OK) {
        Error_Handler();
    }

    hsai_BlockB1.Instance = SAI1_Block_B;
    hsai_BlockB1.Init.Protocol = SAI_FREE_PROTOCOL;
    hsai_BlockB1.Init.AudioMode = SAI_MODEMASTER_TX;
    hsai_BlockB1.Init.DataSize = SAI_DATASIZE_16;
    hsai_BlockB1.Init.FirstBit = SAI_FIRSTBIT_MSB;
    hsai_BlockB1.Init.ClockStrobing = SAI_CLOCKSTROBING_FALLINGEDGE;
    hsai_BlockB1.Init.Synchro = SAI_ASYNCHRONOUS;
    hsai_BlockB1.Init.OutputDrive = SAI_OUTPUTDRIVE_ENABLE;
    hsai_BlockB1.Init.NoDivider = SAI_MASTERDIVIDER_ENABLE;
    hsai_BlockB1.Init.MckOutput = SAI_MCK_OUTPUT_DISABLE;
    hsai_BlockB1.Init.FIFOThreshold = SAI_FIFOTHRESHOLD_1QF;
    hsai_BlockB1.Init.AudioFrequency = SAI_AUDIO_FREQUENCY_16K;
    hsai_BlockB1.Init.SynchroExt = SAI_SYNCEXT_DISABLE;
    hsai_BlockB1.Init.MonoStereoMode = SAI_STEREOMODE;
    hsai_BlockB1.Init.CompandingMode = SAI_NOCOMPANDING;
    hsai_BlockB1.Init.TriState = SAI_OUTPUT_NOTRELEASED;
    hsai_BlockB1.Init.MckOverSampling = SAI_MCK_OVERSAMPLING_DISABLE;
    hsai_BlockB1.FrameInit.FrameLength = 32u;
    hsai_BlockB1.FrameInit.ActiveFrameLength = 16u;
    hsai_BlockB1.FrameInit.FSDefinition = SAI_FS_CHANNEL_IDENTIFICATION;
    hsai_BlockB1.FrameInit.FSPolarity = SAI_FS_ACTIVE_LOW;
    hsai_BlockB1.FrameInit.FSOffset = SAI_FS_BEFOREFIRSTBIT;
    hsai_BlockB1.SlotInit.FirstBitOffset = 0u;
    hsai_BlockB1.SlotInit.SlotSize = SAI_SLOTSIZE_16B;
    hsai_BlockB1.SlotInit.SlotNumber = 2u;
    hsai_BlockB1.SlotInit.SlotActive = SAI_SLOTACTIVE_0 | SAI_SLOTACTIVE_1;

    if (HAL_SAI_Init(&hsai_BlockB1) != HAL_OK) {
        Error_Handler();
    }
}

void HAL_MspInit(void)
{
    __HAL_RCC_HSEM_CLK_ENABLE();

    HAL_NVIC_SetPriority(HSEM_IRQn, 0, 0);
    HAL_NVIC_EnableIRQ(HSEM_IRQn);
}

void HAL_IPCC_MspInit(IPCC_HandleTypeDef *ipccHandle)
{
    if (ipccHandle->Instance == IPCC) {
        __HAL_RCC_IPCC_CLK_ENABLE();

        HAL_NVIC_SetPriority(IPCC_C1_RX_IRQn, 0, 0);
        HAL_NVIC_EnableIRQ(IPCC_C1_RX_IRQn);
        HAL_NVIC_SetPriority(IPCC_C1_TX_IRQn, 0, 0);
        HAL_NVIC_EnableIRQ(IPCC_C1_TX_IRQn);
    }
}

void HAL_IPCC_MspDeInit(IPCC_HandleTypeDef *ipccHandle)
{
    if (ipccHandle->Instance == IPCC) {
        HAL_NVIC_DisableIRQ(IPCC_C1_RX_IRQn);
        HAL_NVIC_DisableIRQ(IPCC_C1_TX_IRQn);
        __HAL_RCC_IPCC_CLK_DISABLE();
    }
}

void HAL_RNG_MspInit(RNG_HandleTypeDef *rngHandle)
{
    RCC_PeriphCLKInitTypeDef PeriphClkInitStruct = {0};

    if (rngHandle->Instance == RNG) {
        PeriphClkInitStruct.PeriphClockSelection = RCC_PERIPHCLK_RNG;
        PeriphClkInitStruct.RngClockSelection = RCC_RNGCLKSOURCE_HSI48;
        if (HAL_RCCEx_PeriphCLKConfig(&PeriphClkInitStruct) != HAL_OK) {
            Error_Handler();
        }

        __HAL_RCC_RNG_CLK_ENABLE();
    }
}

void HAL_RNG_MspDeInit(RNG_HandleTypeDef *rngHandle)
{
    if (rngHandle->Instance == RNG) {
        __HAL_RCC_RNG_CLK_DISABLE();
    }
}

void HAL_RTC_MspInit(RTC_HandleTypeDef *rtcHandle)
{
    RCC_PeriphCLKInitTypeDef PeriphClkInitStruct = {0};

    if (rtcHandle->Instance == RTC) {
        PeriphClkInitStruct.PeriphClockSelection = RCC_PERIPHCLK_RTC;
        PeriphClkInitStruct.RTCClockSelection = RCC_RTCCLKSOURCE_LSE;
        if (HAL_RCCEx_PeriphCLKConfig(&PeriphClkInitStruct) != HAL_OK) {
            Error_Handler();
        }

        __HAL_RCC_RTC_ENABLE();
        __HAL_RCC_RTCAPB_CLK_ENABLE();

        HAL_NVIC_SetPriority(RTC_WKUP_IRQn, 0, 0);
        HAL_NVIC_EnableIRQ(RTC_WKUP_IRQn);
        HAL_RTCEx_EnableBypassShadow(rtcHandle);
    }
}

void HAL_RTC_MspDeInit(RTC_HandleTypeDef *rtcHandle)
{
    if (rtcHandle->Instance == RTC) {
        HAL_NVIC_DisableIRQ(RTC_WKUP_IRQn);
        __HAL_RCC_RTC_DISABLE();
        __HAL_RCC_RTCAPB_CLK_DISABLE();
    }
}

void HAL_I2C_MspInit(I2C_HandleTypeDef *i2cHandle)
{
    GPIO_InitTypeDef GPIO_InitStruct = {0};
    RCC_PeriphCLKInitTypeDef PeriphClkInitStruct = {0};

    if (i2cHandle->Instance == I2C3) {
        PeriphClkInitStruct.PeriphClockSelection = RCC_PERIPHCLK_I2C3;
        PeriphClkInitStruct.I2c3ClockSelection = RCC_I2C3CLKSOURCE_PCLK1;
        if (HAL_RCCEx_PeriphCLKConfig(&PeriphClkInitStruct) != HAL_OK) {
            Error_Handler();
        }

        __HAL_RCC_GPIOB_CLK_ENABLE();
        __HAL_RCC_GPIOC_CLK_ENABLE();
        __HAL_RCC_I2C3_CLK_ENABLE();

        GPIO_InitStruct.Pin = GPIO_PIN_0;
        GPIO_InitStruct.Mode = GPIO_MODE_AF_OD;
        GPIO_InitStruct.Pull = GPIO_PULLUP;
        GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_VERY_HIGH;
        GPIO_InitStruct.Alternate = GPIO_AF4_I2C3;
        HAL_GPIO_Init(GPIOC, &GPIO_InitStruct);

        GPIO_InitStruct.Pin = GPIO_PIN_11;
        GPIO_InitStruct.Mode = GPIO_MODE_AF_OD;
        GPIO_InitStruct.Pull = GPIO_PULLUP;
        GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_VERY_HIGH;
        GPIO_InitStruct.Alternate = GPIO_AF4_I2C3;
        HAL_GPIO_Init(GPIOB, &GPIO_InitStruct);
    }
}

void HAL_I2C_MspDeInit(I2C_HandleTypeDef *i2cHandle)
{
    if (i2cHandle->Instance == I2C3) {
        HAL_GPIO_DeInit(GPIOC, GPIO_PIN_0);
        HAL_GPIO_DeInit(GPIOB, GPIO_PIN_11);
        __HAL_RCC_I2C3_CLK_DISABLE();
    }
}

void HAL_UART_MspInit(UART_HandleTypeDef *uartHandle)
{
    GPIO_InitTypeDef GPIO_InitStruct = {0};
    HAL_DMA_MuxSyncConfigTypeDef pSyncConfig = {0};
    RCC_PeriphCLKInitTypeDef PeriphClkInitStruct = {0};

    if (uartHandle->Instance == USART1) {
        PeriphClkInitStruct.PeriphClockSelection = RCC_PERIPHCLK_USART1;
        PeriphClkInitStruct.Usart1ClockSelection = RCC_USART1CLKSOURCE_PCLK2;
        if (HAL_RCCEx_PeriphCLKConfig(&PeriphClkInitStruct) != HAL_OK) {
            Error_Handler();
        }

        __HAL_RCC_USART1_CLK_ENABLE();
        __HAL_RCC_GPIOB_CLK_ENABLE();

        GPIO_InitStruct.Pin = GPIO_PIN_6 | GPIO_PIN_7;
        GPIO_InitStruct.Mode = GPIO_MODE_AF_PP;
        GPIO_InitStruct.Pull = GPIO_PULLUP;
        GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_VERY_HIGH;
        GPIO_InitStruct.Alternate = GPIO_AF7_USART1;
        HAL_GPIO_Init(GPIOB, &GPIO_InitStruct);

        hdma_usart1_tx.Instance = DMA2_Channel4;
        hdma_usart1_tx.Init.Request = DMA_REQUEST_USART1_TX;
        hdma_usart1_tx.Init.Direction = DMA_MEMORY_TO_PERIPH;
        hdma_usart1_tx.Init.PeriphInc = DMA_PINC_DISABLE;
        hdma_usart1_tx.Init.MemInc = DMA_MINC_ENABLE;
        hdma_usart1_tx.Init.PeriphDataAlignment = DMA_PDATAALIGN_BYTE;
        hdma_usart1_tx.Init.MemDataAlignment = DMA_MDATAALIGN_BYTE;
        hdma_usart1_tx.Init.Mode = DMA_NORMAL;
        hdma_usart1_tx.Init.Priority = DMA_PRIORITY_LOW;
        if (HAL_DMA_Init(&hdma_usart1_tx) != HAL_OK) {
            Error_Handler();
        }

        pSyncConfig.SyncSignalID = HAL_DMAMUX1_SYNC_DMAMUX1_CH1_EVT;
        pSyncConfig.SyncPolarity = HAL_DMAMUX_SYNC_NO_EVENT;
        pSyncConfig.SyncEnable = DISABLE;
        pSyncConfig.EventEnable = DISABLE;
        pSyncConfig.RequestNumber = 1u;
        if (HAL_DMAEx_ConfigMuxSync(&hdma_usart1_tx, &pSyncConfig) != HAL_OK) {
            Error_Handler();
        }

        __HAL_LINKDMA(uartHandle, hdmatx, hdma_usart1_tx);

        HAL_NVIC_SetPriority(USART1_IRQn, 0, 0);
        HAL_NVIC_EnableIRQ(USART1_IRQn);
    }
}

void HAL_SPI_MspInit(SPI_HandleTypeDef *spiHandle)
{
    GPIO_InitTypeDef GPIO_InitStruct = {0};

    if (spiHandle->Instance == SPI2) {
        __HAL_RCC_SPI2_CLK_ENABLE();
        __HAL_RCC_GPIOA_CLK_ENABLE();
        __HAL_RCC_GPIOC_CLK_ENABLE();

        GPIO_InitStruct.Pin = GPIO_PIN_9;
        GPIO_InitStruct.Mode = GPIO_MODE_AF_PP;
        GPIO_InitStruct.Pull = GPIO_NOPULL;
        GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_VERY_HIGH;
        GPIO_InitStruct.Alternate = GPIO_AF5_SPI2;
        HAL_GPIO_Init(GPIOA, &GPIO_InitStruct);

        GPIO_InitStruct.Pin = GPIO_PIN_1 | GPIO_PIN_2;
        GPIO_InitStruct.Mode = GPIO_MODE_AF_PP;
        GPIO_InitStruct.Pull = GPIO_NOPULL;
        GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_VERY_HIGH;
        GPIO_InitStruct.Alternate = GPIO_AF5_SPI2;
        HAL_GPIO_Init(GPIOC, &GPIO_InitStruct);
    }
}

void HAL_SPI_MspDeInit(SPI_HandleTypeDef *spiHandle)
{
    if (spiHandle->Instance == SPI2) {
        HAL_GPIO_DeInit(GPIOA, GPIO_PIN_9);
        HAL_GPIO_DeInit(GPIOC, GPIO_PIN_1 | GPIO_PIN_2);
        __HAL_RCC_SPI2_CLK_DISABLE();
    }
}

void HAL_QSPI_MspInit(QSPI_HandleTypeDef *qspiHandle)
{
    GPIO_InitTypeDef GPIO_InitStruct = {0};

    if (qspiHandle->Instance == QUADSPI) {
        __HAL_RCC_QUADSPI_CLK_ENABLE();
        __HAL_RCC_GPIOA_CLK_ENABLE();
        __HAL_RCC_GPIOB_CLK_ENABLE();

        GPIO_InitStruct.Pin = GPIO_PIN_2;
        GPIO_InitStruct.Mode = GPIO_MODE_AF_PP;
        GPIO_InitStruct.Pull = GPIO_PULLUP;
        GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_VERY_HIGH;
        GPIO_InitStruct.Alternate = GPIO_AF10_QUADSPI;
        HAL_GPIO_Init(GPIOA, &GPIO_InitStruct);

        GPIO_InitStruct.Pin = GPIO_PIN_3;
        GPIO_InitStruct.Mode = GPIO_MODE_AF_PP;
        GPIO_InitStruct.Pull = GPIO_NOPULL;
        GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_VERY_HIGH;
        GPIO_InitStruct.Alternate = GPIO_AF10_QUADSPI;
        HAL_GPIO_Init(GPIOA, &GPIO_InitStruct);

        GPIO_InitStruct.Pin = GPIO_PIN_8 | GPIO_PIN_9;
        GPIO_InitStruct.Mode = GPIO_MODE_AF_PP;
        GPIO_InitStruct.Pull = GPIO_NOPULL;
        GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_VERY_HIGH;
        GPIO_InitStruct.Alternate = GPIO_AF10_QUADSPI;
        HAL_GPIO_Init(GPIOB, &GPIO_InitStruct);
    }
}

void HAL_QSPI_MspDeInit(QSPI_HandleTypeDef *qspiHandle)
{
    if (qspiHandle->Instance == QUADSPI) {
        HAL_GPIO_DeInit(GPIOA, GPIO_PIN_2 | GPIO_PIN_3);
        HAL_GPIO_DeInit(GPIOB, GPIO_PIN_8 | GPIO_PIN_9);
        __HAL_RCC_QUADSPI_CLK_DISABLE();
    }
}

void HAL_SAI_MspInit(SAI_HandleTypeDef *saiHandle)
{
    static uint32_t sai1_client_count = 0u;
    GPIO_InitTypeDef GPIO_InitStruct = {0};
    RCC_PeriphCLKInitTypeDef PeriphClkInitStruct = {0};

    if (saiHandle->Instance == SAI1_Block_A ||
        saiHandle->Instance == SAI1_Block_B) {
        if (sai1_client_count == 0u) {
            PeriphClkInitStruct.PeriphClockSelection = RCC_PERIPHCLK_SAI1;
            PeriphClkInitStruct.PLLSAI1.PLLN = 24u;
            PeriphClkInitStruct.PLLSAI1.PLLP = RCC_PLLP_DIV2;
            PeriphClkInitStruct.PLLSAI1.PLLSAI1ClockOut = RCC_PLLSAI1_SAI1CLK;
            PeriphClkInitStruct.Sai1ClockSelection = RCC_SAI1CLKSOURCE_PLLSAI1;
            if (HAL_RCCEx_PeriphCLKConfig(&PeriphClkInitStruct) != HAL_OK) {
                Error_Handler();
            }
            __HAL_RCC_SAI1_CLK_ENABLE();
        }
        sai1_client_count++;

        __HAL_RCC_GPIOA_CLK_ENABLE();
        __HAL_RCC_GPIOB_CLK_ENABLE();
        __HAL_RCC_GPIOC_CLK_ENABLE();

        if (saiHandle->Instance == SAI1_Block_A) {
            GPIO_InitStruct.Pin = GPIO_PIN_8;
            GPIO_InitStruct.Mode = GPIO_MODE_AF_PP;
            GPIO_InitStruct.Pull = GPIO_NOPULL;
            GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_VERY_HIGH;
#if COMPANION_MIC_BACKEND == COMPANION_MIC_BACKEND_SPH0655_PDM
#if COMPANION_PDM_USE_HARDWARE_INTERFACE
            GPIO_InitStruct.Alternate = GPIO_AF3_SAI1;
#else
            GPIO_InitStruct.Alternate = GPIO_AF13_SAI1;
#endif
#else
            GPIO_InitStruct.Alternate = GPIO_AF13_SAI1;
#endif
            HAL_GPIO_Init(GPIOA, &GPIO_InitStruct);

#if (COMPANION_MIC_BACKEND != COMPANION_MIC_BACKEND_SPH0655_PDM) || !COMPANION_PDM_USE_HARDWARE_INTERFACE
            GPIO_InitStruct.Pin = GPIO_PIN_12;
            GPIO_InitStruct.Mode = GPIO_MODE_AF_PP;
            GPIO_InitStruct.Pull = GPIO_NOPULL;
            GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_VERY_HIGH;
            GPIO_InitStruct.Alternate = GPIO_AF13_SAI1;
            HAL_GPIO_Init(GPIOB, &GPIO_InitStruct);
#endif

            GPIO_InitStruct.Pin = GPIO_PIN_3;
            GPIO_InitStruct.Mode = GPIO_MODE_AF_PP;
#if COMPANION_MIC_BACKEND == COMPANION_MIC_BACKEND_SPH0655_PDM
#if COMPANION_PDM_USE_HARDWARE_INTERFACE
            GPIO_InitStruct.Pull = GPIO_PULLUP;
            GPIO_InitStruct.Alternate = COMPANION_PDM_DATA_AF;
#else
            GPIO_InitStruct.Pull = GPIO_NOPULL;
            GPIO_InitStruct.Alternate = COMPANION_PDM_DATA_AF;
#endif
#else
#if COMPANION_MIC_SD_PULLDOWN
            GPIO_InitStruct.Pull = GPIO_PULLDOWN;
#else
            GPIO_InitStruct.Pull = GPIO_NOPULL;
#endif
            GPIO_InitStruct.Alternate = GPIO_AF13_SAI1;
#endif
            GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_VERY_HIGH;
            HAL_GPIO_Init(GPIOC, &GPIO_InitStruct);

#if (COMPANION_MIC_BACKEND == COMPANION_MIC_BACKEND_SPH0655_PDM) && COMPANION_PDM_RAW_SAI_USE_DMA
            hdma_sai1_a_rx.Instance = DMA1_Channel1;
            hdma_sai1_a_rx.Init.Request = DMA_REQUEST_SAI1_A;
            hdma_sai1_a_rx.Init.Direction = DMA_PERIPH_TO_MEMORY;
            hdma_sai1_a_rx.Init.PeriphInc = DMA_PINC_DISABLE;
            hdma_sai1_a_rx.Init.MemInc = DMA_MINC_ENABLE;
            hdma_sai1_a_rx.Init.PeriphDataAlignment = DMA_PDATAALIGN_WORD;
            hdma_sai1_a_rx.Init.MemDataAlignment = DMA_MDATAALIGN_WORD;
            hdma_sai1_a_rx.Init.Mode = DMA_CIRCULAR;
            hdma_sai1_a_rx.Init.Priority = DMA_PRIORITY_HIGH;
            __HAL_LINKDMA(saiHandle, hdmarx, hdma_sai1_a_rx);
            (void)HAL_DMA_DeInit(&hdma_sai1_a_rx);
            if (HAL_DMA_Init(&hdma_sai1_a_rx) != HAL_OK) {
                Error_Handler();
            }
            HAL_NVIC_SetPriority(DMA1_Channel1_IRQn, 7, 0);
            HAL_NVIC_EnableIRQ(DMA1_Channel1_IRQn);
#endif
        } else {
            GPIO_InitStruct.Pin = GPIO_PIN_4 | GPIO_PIN_5;
            GPIO_InitStruct.Mode = GPIO_MODE_AF_PP;
            GPIO_InitStruct.Pull = GPIO_NOPULL;
            GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_VERY_HIGH;
            GPIO_InitStruct.Alternate = GPIO_AF13_SAI1;
            HAL_GPIO_Init(GPIOA, &GPIO_InitStruct);

            GPIO_InitStruct.Pin = GPIO_PIN_3;
            GPIO_InitStruct.Mode = GPIO_MODE_AF_PP;
            GPIO_InitStruct.Pull = GPIO_NOPULL;
            GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_VERY_HIGH;
            GPIO_InitStruct.Alternate = GPIO_AF13_SAI1;
            HAL_GPIO_Init(GPIOB, &GPIO_InitStruct);
        }
    }
}

void USART1_IRQHandler(void)
{
    HAL_UART_IRQHandler(&huart1);
}

void EXTI9_5_IRQHandler(void)
{
    if (__HAL_GPIO_EXTI_GET_IT(BOARD_TOUCH_INT_PIN) != 0u) {
        __HAL_GPIO_EXTI_CLEAR_IT(BOARD_TOUCH_INT_PIN);
        s_touch_irq_count++;
    }
}

#if (COMPANION_MIC_BACKEND == COMPANION_MIC_BACKEND_SPH0655_PDM) && COMPANION_PDM_RAW_SAI_USE_DMA
void DMA1_Channel1_IRQHandler(void)
{
    HAL_DMA_IRQHandler(&hdma_sai1_a_rx);
}

static void pdm_raw_dma_mark_half(uint8_t half)
{
    const uint8_t bit =
        (half == 0u) ? MIC_RAW_DMA_HALF0_READY : MIC_RAW_DMA_HALF1_READY;
    if ((s_pdm_raw_dma_ready_mask & bit) != 0u) {
        s_pdm_raw_dma_overrun_count++;
    }
    s_pdm_raw_dma_ready_mask |= bit;
    s_pdm_raw_dma_last_completed_half = half;
}

void HAL_SAI_RxHalfCpltCallback(SAI_HandleTypeDef *hSai)
{
    if (hSai != NULL && hSai->Instance == SAI1_Block_A) {
        pdm_raw_dma_mark_half(0u);
    }
}

void HAL_SAI_RxCpltCallback(SAI_HandleTypeDef *hSai)
{
    if (hSai != NULL && hSai->Instance == SAI1_Block_A) {
        pdm_raw_dma_mark_half(1u);
    }
}
#endif

void DMA2_Channel4_IRQHandler(void)
{
    HAL_DMA_IRQHandler(&hdma_usart1_tx);
}

void RTC_WKUP_IRQHandler(void)
{
    HAL_RTCEx_WakeUpTimerIRQHandler(&hrtc);
}

void IPCC_C1_RX_IRQHandler(void)
{
    HAL_IPCC_RX_IRQHandler(&hipcc);
}

void IPCC_C1_TX_IRQHandler(void)
{
    HAL_IPCC_TX_IRQHandler(&hipcc);
}

void HSEM_IRQHandler(void)
{
    HAL_HSEM_IRQHandler();
}

void SysTick_Handler(void)
{
    HAL_IncTick();
}

void Error_Handler(void)
{
    if (s_uart_ready) {
        printf("\r\n[error] stage=%s tick=%lu\r\n",
               s_error_stage,
               (unsigned long)HAL_GetTick());
    }
    __disable_irq();
    while (1) {
    }
}
