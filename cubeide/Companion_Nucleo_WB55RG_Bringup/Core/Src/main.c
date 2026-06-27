#include "main.h"

#include "app_conf.h"
#include "app_entry.h"
#include "comp_qspi_nor.h"
#include "diag_log.h"
#include "recording_fsm.h"

#include <limits.h>
#include <stdbool.h>
#include <stdio.h>
#include <string.h>

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
#define FLASH_QSPI_IO3_GPIO_PORT GPIOA
#define FLASH_QSPI_IO3_PIN GPIO_PIN_6
#define FLASH_QSPI_IO2_GPIO_PORT GPIOA
#define FLASH_QSPI_IO2_PIN GPIO_PIN_7
#define FLASH_QSPI_IO1_GPIO_PORT GPIOB
#define FLASH_QSPI_IO1_PIN GPIO_PIN_8
#define FLASH_QSPI_IO0_GPIO_PORT GPIOB
#define FLASH_QSPI_IO0_PIN GPIO_PIN_9

#define BOARD_SW1_GPIO_PORT GPIOC
#define BOARD_SW1_PIN GPIO_PIN_4
#define BOARD_SW2_GPIO_PORT GPIOD
#define BOARD_SW2_PIN GPIO_PIN_0
#define BOARD_SW3_GPIO_PORT GPIOD
#define BOARD_SW3_PIN GPIO_PIN_1

#define BUTTON_DEBOUNCE_MS 35u
#define BUTTON_IDLE_POLL_MS 10u
#define HEARTBEAT_PERIOD_MS 5000u
#define MANUAL_RECORDING_LOG_EVERY_BLOCKS 50u

#ifndef COMPANION_TYPE_READY_AUTOSTREAM_BLOCKS
#define COMPANION_TYPE_READY_AUTOSTREAM_BLOCKS 24u
#endif
#define COMPANION_TYPE_READY_AUTOSTREAM_PCM_BYTES 128u
#ifndef COMPANION_TYPE_READY_A1_AUTOSTREAM_BLOCKS
#define COMPANION_TYPE_READY_A1_AUTOSTREAM_BLOCKS 600u
#endif
#define COMPANION_TYPE_READY_A1_AUTOSTREAM_PCM_BYTES (MIC_FRAMES_PER_BATCH * sizeof(int16_t))
#ifndef COMPANION_TYPE_READY_A2_AUTOSTREAM_BLOCKS
#define COMPANION_TYPE_READY_A2_AUTOSTREAM_BLOCKS 3000u
#endif
#define COMPANION_TYPE_READY_A2_AUTOSTREAM_PCM_BYTES (MIC_FRAMES_PER_BATCH * sizeof(int16_t))

#define MIC_SAMPLE_RATE_HZ 16000u
#define MIC_FRAMES_PER_BATCH 160u
#define MIC_SLOT_COUNT 2u
#define MIC_I2S_WORDS (MIC_FRAMES_PER_BATCH * MIC_SLOT_COUNT)
#define MIC_CAPTURE_BLOCKS 4u

#define FLASH_TEST_ADDRESS 0x00FFF000u
#define FLASH_TEST_SIZE 256u
#define FLASH_BUSY_TIMEOUT_MS 5000u

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

UART_HandleTypeDef hlpuart1;
UART_HandleTypeDef huart1;
DMA_HandleTypeDef hdma_usart1_tx;
IPCC_HandleTypeDef hipcc;
QSPI_HandleTypeDef hqspi;
RNG_HandleTypeDef hrng;
RTC_HandleTypeDef hrtc;
SAI_HandleTypeDef hsai_BlockA1;

static comp_recording_fsm_t s_recording_fsm;
static comp_qspi_nor_t s_flash;
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

static void SystemClock_Config(void);
static void PeriphCommonClock_Config(void);
static void MX_GPIO_Init(void);
static void MX_DMA_Init(void);
static void MX_IPCC_Init(void);
static void MX_RNG_Init(void);
static void MX_RTC_Init(void);
static void MX_RF_Init(void);
void MX_USART1_UART_Init(void);
static void MX_QUADSPI_Init(void);
static void MX_SAI1_Init(void);

static void init_board_buttons(void);
static void poll_board_buttons(void);
static void handle_button_press(size_t index);
static void start_recording(comp_recording_source_t source, const char *reason);
static void stop_recording(comp_recording_source_t source, const char *reason);
static void cancel_recording(comp_recording_source_t source, const char *reason);
static void start_manual_recording(void);
static void stop_manual_recording(const char *reason);
static void cancel_manual_recording(void);
static void request_ble_type_ready_autostream(const char *reason,
                                              uint32_t blocks,
                                              uint16_t pcm_bytes);
static void clear_ble_type_ready_autostream(void);
static void start_ble_session_if_ready(const char *reason);
static void end_ble_session_if_active(bool cancel, const char *reason);
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
    s_error_stage = "MX_RTC_Init";
    MX_RTC_Init();
    s_error_stage = "MX_RNG_Init";
    MX_RNG_Init();
    s_error_stage = "MX_RF_Init";
    MX_RF_Init();
    s_error_stage = "MX_USART1_UART_Init";
    MX_USART1_UART_Init();
    s_uart_ready = true;
    printf("\r\n[stage] uart ok\r\n");
    s_error_stage = "MX_QUADSPI_Init";
    MX_QUADSPI_Init();
    comp_qspi_nor_init(&s_flash, &hqspi);
    printf("[stage] qspi ok\r\n");
    s_error_stage = "MX_SAI1_Init";
    MX_SAI1_Init();
    printf("[stage] sai1 ok clk=%lu cr1=0x%08lX frcr=0x%08lX slotr=0x%08lX\r\n",
           (unsigned long)HAL_RCCEx_GetPeriphCLKFreq(RCC_PERIPHCLK_SAI1),
           (unsigned long)SAI1_Block_A->CR1,
           (unsigned long)SAI1_Block_A->FRCR,
           (unsigned long)SAI1_Block_A->SLOTR);

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
    printf("[boot] uart=USART1 PB6/PB7 115200 flash=QSPI PA2/PA3/PB9/PB8/PA7/PA6 mic=SAI1 PA8/PB12/PC3\r\n");
    printf("[boot] mic=i2s_master_rx_32bit_slots_downshift16 ble=companion_vka1 ota=ble_package_ready\r\n");
    printf("[boot] buttons: SW1=PC4 start/stop recording, SW2=PD0 cancel/recover, SW3=PD1 flash+ota+diag probe\r\n");
    init_board_buttons();

    s_error_stage = "MX_APPE_Init";
    MX_APPE_Init();
    printf("[stage] ble app init requested name=companion service=VKA1\r\n");

    printf("\r\n[tick] boot_selftest t_ms=%lu\r\n", (unsigned long)HAL_GetTick());
    MX_APPE_Process();
    run_flash_probe();
    MX_APPE_Process();
    run_ota_readiness_probe();
    MX_APPE_Process();
    run_microphone_probe();
    MX_APPE_Process();
    print_diag_tail();

    uint32_t last_heartbeat_ms = HAL_GetTick();
    while (1) {
        MX_APPE_Process();
        poll_board_buttons();

        if (s_recording_fsm.state == COMP_RECORDING_STATE_RECORDING) {
            bool verbose = (s_manual_recording_block_count % MANUAL_RECORDING_LOG_EVERY_BLOCKS) == 0u;
            bool captured = capture_microphone_block(s_manual_recording_block_count,
                                                     verbose,
                                                     "mic-manual");
            s_manual_recording_block_count++;
            if (captured &&
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
            MX_APPE_Process();
            continue;
        }

        uint32_t now = HAL_GetTick();
        if ((now - last_heartbeat_ms) >= HEARTBEAT_PERIOD_MS) {
            last_heartbeat_ms = now;
            printf("\r\n[tick] t_ms=%lu state=%s buttons=ready\r\n",
                   (unsigned long)now,
                   comp_recording_state_name(s_recording_fsm.state));
        }
        MX_APPE_Process();
        HAL_Delay(BUTTON_IDLE_POLL_MS);
    }
}

static bool button_is_pressed(const board_button_t *button)
{
    return HAL_GPIO_ReadPin(button->port, button->pin) == GPIO_PIN_RESET;
}

static void init_board_buttons(void)
{
    for (size_t i = 0u; i < sizeof(s_buttons) / sizeof(s_buttons[0]); ++i) {
        bool pressed = button_is_pressed(&s_buttons[i]);
        s_buttons[i].last_raw_pressed = pressed;
        s_buttons[i].stable_pressed = pressed;
        s_buttons[i].last_change_ms = HAL_GetTick();
    }
}

static void poll_board_buttons(void)
{
    uint32_t now = HAL_GetTick();
    for (size_t i = 0u; i < sizeof(s_buttons) / sizeof(s_buttons[0]); ++i) {
        bool raw_pressed = button_is_pressed(&s_buttons[i]);
        if (raw_pressed != s_buttons[i].last_raw_pressed) {
            s_buttons[i].last_raw_pressed = raw_pressed;
            s_buttons[i].last_change_ms = now;
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
        if (s_recording_fsm.state == COMP_RECORDING_STATE_RECORDING) {
            stop_manual_recording("sw1");
        } else {
            start_manual_recording();
        }
    } else if (index == 1u) {
        cancel_manual_recording();
    } else if (index == 2u) {
        run_manual_probe_request();
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
        } else {
            start_ble_session_if_ready("link_ready");
        }
    } else {
        s_ble_session_active = false;
        if (s_ble_type_ready_autostream_active &&
            s_recording_fsm.state == COMP_RECORDING_STATE_RECORDING) {
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
    HAL_Delay(2u);
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
    s_manual_recording_block_count = 0u;
    if (s_recording_fsm.state == COMP_RECORDING_STATE_RECORDING) {
        start_ble_session_if_ready(reason);
    }
    printf("[record] %s action=start source=%lu result=%lu state=%s\r\n",
           reason,
           (unsigned long)source,
           (unsigned long)result,
           comp_recording_state_name(s_recording_fsm.state));
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
}

static void cancel_recording(comp_recording_source_t source, const char *reason)
{
    comp_recording_result_t cancel_result = comp_recording_fsm_dispatch(
        &s_recording_fsm,
        COMP_RECORDING_EVENT_CANCEL_REQUEST,
        source);
    end_ble_session_if_active(true, reason);
    clear_ble_type_ready_autostream();
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
}

static void start_manual_recording(void)
{
    start_recording(COMP_RECORDING_SOURCE_USER_BUTTON, "sw1");
}

static void stop_manual_recording(const char *reason)
{
    stop_recording(COMP_RECORDING_SOURCE_USER_BUTTON, reason);
}

static void cancel_manual_recording(void)
{
    cancel_recording(COMP_RECORDING_SOURCE_USER_BUTTON, "sw2");
}

static void run_manual_probe_request(void)
{
    if (s_recording_fsm.state == COMP_RECORDING_STATE_RECORDING ||
        s_recording_fsm.state == COMP_RECORDING_STATE_STOPPING) {
        printf("[button] sw3 action=probe ignored=recording_active state=%s\r\n",
               comp_recording_state_name(s_recording_fsm.state));
        return;
    }
    printf("\r\n[button] sw3 action=probe_begin t_ms=%lu\r\n",
           (unsigned long)HAL_GetTick());
    run_flash_probe();
    run_ota_readiness_probe();
    print_diag_tail();
    printf("[button] sw3 action=probe_done t_ms=%lu\r\n",
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
        uint8_t read_1_1_4[8] = {0};
        HAL_StatusTypeDef read_111_status = HAL_ERROR;
        HAL_StatusTypeDef read_112_status = HAL_ERROR;
        HAL_StatusTypeDef read_114_status = HAL_ERROR;

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
            read_114_status = qspi_read_command(0x6Bu,
                                                QSPI_ADDRESS_1_LINE,
                                                0u,
                                                QSPI_DATA_4_LINES,
                                                8u,
                                                read_1_1_4,
                                                sizeof(read_1_1_4));
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
            printf("[flash] read addr0 1-1-1=%s %02X %02X %02X %02X %02X %02X %02X %02X 1-1-2=%s %02X %02X %02X %02X %02X %02X %02X %02X 1-1-4=%s %02X %02X %02X %02X %02X %02X %02X %02X\r\n",
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
                   read_1_1_2[7],
                   hal_status_name(read_114_status),
                   read_1_1_4[0],
                   read_1_1_4[1],
                   read_1_1_4[2],
                   read_1_1_4[3],
                   read_1_1_4[4],
                   read_1_1_4[5],
                   read_1_1_4[6],
                   read_1_1_4[7]);
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
    GPIO_PinState io2_level = HAL_GPIO_ReadPin(FLASH_QSPI_IO2_GPIO_PORT, FLASH_QSPI_IO2_PIN);
    GPIO_PinState io3_level = HAL_GPIO_ReadPin(FLASH_QSPI_IO3_GPIO_PORT, FLASH_QSPI_IO3_PIN);

    printf("[flash-bb] cfg=%s jedec=%02X-%02X-%02X sr1=0x%02X valid=%u idle_io0=%u idle_io1=%u idle_io2=%u idle_io3=%u\r\n",
           name,
           jedec_id[0],
           jedec_id[1],
           jedec_id[2],
           status1,
           valid ? 1u : 0u,
           io0_level == GPIO_PIN_SET ? 1u : 0u,
           io1_level == GPIO_PIN_SET ? 1u : 0u,
           io2_level == GPIO_PIN_SET ? 1u : 0u,
           io3_level == GPIO_PIN_SET ? 1u : 0u);
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
    HAL_GPIO_WritePin(FLASH_QSPI_IO2_GPIO_PORT, FLASH_QSPI_IO2_PIN, GPIO_PIN_SET);
    HAL_GPIO_WritePin(FLASH_QSPI_IO3_GPIO_PORT, FLASH_QSPI_IO3_PIN, GPIO_PIN_SET);

    GPIO_InitStruct.Pin = FLASH_QSPI_NCS_PIN | FLASH_QSPI_CLK_PIN | FLASH_QSPI_IO2_PIN | FLASH_QSPI_IO3_PIN;
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

static int16_t i2s_word_to_pcm16(uint32_t word)
{
    return (int16_t)((int32_t)word >> 16);
}

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

static void analyze_capture(const uint32_t *raw_words,
                            int16_t *pcm_samples,
                            raw_stats_t *raw_stats,
                            pcm_stats_t *pcm_stats)
{
    raw_stats_init(raw_stats);
    pcm_stats_init(pcm_stats);

    uint32_t previous = raw_words[0];
    for (uint32_t i = 0u; i < MIC_I2S_WORDS; ++i) {
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
                                    MIC_I2S_WORDS * sizeof(raw_words[0]));

    for (uint32_t i = 0u; i < MIC_FRAMES_PER_BATCH; ++i) {
        int16_t sample = i2s_word_to_pcm16(raw_words[i * MIC_SLOT_COUNT]);
        pcm_samples[i] = sample;
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
                                    MIC_FRAMES_PER_BATCH * sizeof(pcm_samples[0]));
}

static void feed_drop_to_recording_fsm(void)
{
    comp_microphone_frame_batch_t batch = {
        .frame_count = 0u,
        .samples_per_frame = MIC_FRAMES_PER_BATCH,
        .bytes_per_frame = MIC_FRAMES_PER_BATCH * sizeof(int16_t),
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
    static uint32_t raw_words[MIC_I2S_WORDS];
    static int16_t pcm_samples[MIC_FRAMES_PER_BATCH];

    memset(raw_words, 0, sizeof(raw_words));
    HAL_StatusTypeDef status = HAL_SAI_Receive(&hsai_BlockA1,
                                               (uint8_t *)raw_words,
                                               MIC_I2S_WORDS,
                                               1000u);
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
        }
        return false;
    }

    raw_stats_t raw_stats;
    pcm_stats_t pcm_stats;
    analyze_capture(raw_words, pcm_samples, &raw_stats, &pcm_stats);

    comp_microphone_frame_batch_t batch = {
        .frame_count = 1u,
        .samples_per_frame = MIC_FRAMES_PER_BATCH,
        .bytes_per_frame = MIC_FRAMES_PER_BATCH * sizeof(pcm_samples[0]),
        .duration_ms = (MIC_FRAMES_PER_BATCH * 1000u) / MIC_SAMPLE_RATE_HZ,
        .dropped_frames = 0u,
        .crc32 = pcm_stats.crc32,
    };
    comp_recording_result_t result =
        comp_recording_fsm_feed_microphone_frames(&s_recording_fsm, &batch);

    if (s_ble_session_active) {
        uint16_t ble_pcm_bytes = (uint16_t)sizeof(pcm_samples);
        if (s_ble_type_ready_autostream_active &&
            s_ble_type_ready_autostream_pcm_bytes > 0u &&
            ble_pcm_bytes > s_ble_type_ready_autostream_pcm_bytes) {
            ble_pcm_bytes = s_ble_type_ready_autostream_pcm_bytes;
        }
        comp_audio_stream_status_t stream_status =
            Companion_BleAudio_SendPcmBytes((const uint8_t *)pcm_samples,
                                            ble_pcm_bytes);
        if (stream_status != COMP_AUDIO_STREAM_OK) {
            printf("[%s] ble_audio status=%s id=%lu\r\n",
                   tag,
                   comp_audio_stream_status_name(stream_status),
                   (unsigned long)s_ble_session_id);
            (void)Companion_BleAudio_SendSessionError(COMP_AUDIO_SESSION_ERROR_TRANSPORT);
            s_ble_session_active = false;
        }
    }

    if (verbose) {
        printf("[%s] block=%lu status=ok raw_min=0x%08lX raw_max=0x%08lX raw_zero=%lu raw_same=%lu raw_crc=0x%08lX pcm_min=%d pcm_max=%d pcm_mean=%ld pcm_zero=%lu pcm_clip=%lu pcm_crc=0x%08lX feed=%lu\r\n",
               tag,
               (unsigned long)block_index,
               (unsigned long)raw_stats.min,
               (unsigned long)raw_stats.max,
               (unsigned long)raw_stats.zero_count,
               (unsigned long)raw_stats.same_count,
               (unsigned long)raw_stats.crc32,
               (int)pcm_stats.min,
               (int)pcm_stats.max,
               (long)(pcm_stats.sum / (int64_t)MIC_FRAMES_PER_BATCH),
               (unsigned long)pcm_stats.zero_count,
               (unsigned long)pcm_stats.clipped_count,
               (unsigned long)pcm_stats.crc32,
               (unsigned long)result);
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
    hsai_BlockA1.Init.Protocol = SAI_FREE_PROTOCOL;
    hsai_BlockA1.Init.AudioMode = SAI_MODEMASTER_RX;
    hsai_BlockA1.Init.DataSize = SAI_DATASIZE_32;
    hsai_BlockA1.Init.FirstBit = SAI_FIRSTBIT_MSB;
    hsai_BlockA1.Init.ClockStrobing = SAI_CLOCKSTROBING_RISINGEDGE;
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

    if (HAL_SAI_Init(&hsai_BlockA1) != HAL_OK) {
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

        GPIO_InitStruct.Pin = GPIO_PIN_6 | GPIO_PIN_7;
        GPIO_InitStruct.Mode = GPIO_MODE_AF_PP;
        GPIO_InitStruct.Pull = GPIO_PULLUP;
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
        HAL_GPIO_DeInit(GPIOA, GPIO_PIN_2 | GPIO_PIN_3 | GPIO_PIN_6 | GPIO_PIN_7);
        HAL_GPIO_DeInit(GPIOB, GPIO_PIN_8 | GPIO_PIN_9);
        __HAL_RCC_QUADSPI_CLK_DISABLE();
    }
}

void HAL_SAI_MspInit(SAI_HandleTypeDef *saiHandle)
{
    static uint32_t sai1_client_count = 0u;
    GPIO_InitTypeDef GPIO_InitStruct = {0};
    RCC_PeriphCLKInitTypeDef PeriphClkInitStruct = {0};

    if (saiHandle->Instance == SAI1_Block_A) {
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

        GPIO_InitStruct.Pin = GPIO_PIN_8;
        GPIO_InitStruct.Mode = GPIO_MODE_AF_PP;
        GPIO_InitStruct.Pull = GPIO_NOPULL;
        GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_VERY_HIGH;
        GPIO_InitStruct.Alternate = GPIO_AF13_SAI1;
        HAL_GPIO_Init(GPIOA, &GPIO_InitStruct);

        GPIO_InitStruct.Pin = GPIO_PIN_12;
        GPIO_InitStruct.Mode = GPIO_MODE_AF_PP;
        GPIO_InitStruct.Pull = GPIO_NOPULL;
        GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_VERY_HIGH;
        GPIO_InitStruct.Alternate = GPIO_AF13_SAI1;
        HAL_GPIO_Init(GPIOB, &GPIO_InitStruct);

        GPIO_InitStruct.Pin = GPIO_PIN_3;
        GPIO_InitStruct.Mode = GPIO_MODE_AF_PP;
        GPIO_InitStruct.Pull = GPIO_NOPULL;
        GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_VERY_HIGH;
        GPIO_InitStruct.Alternate = GPIO_AF13_SAI1;
        HAL_GPIO_Init(GPIOC, &GPIO_InitStruct);
    }
}

void USART1_IRQHandler(void)
{
    HAL_UART_IRQHandler(&huart1);
}

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
