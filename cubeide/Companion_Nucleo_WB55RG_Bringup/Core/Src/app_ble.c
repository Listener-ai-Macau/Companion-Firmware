/* USER CODE BEGIN Header */
/**
  ******************************************************************************
 * @file    app_ble.c
 * @author  MCD Application Team
 * @brief   BLE Application
  ******************************************************************************
  * @attention
  *
  * Copyright (c) 2019-2021 STMicroelectronics.
  * All rights reserved.
  *
  * This software is licensed under terms that can be found in the LICENSE file
  * in the root directory of this software component.
  * If no LICENSE file comes with this software, it is provided AS-IS.
  *
  ******************************************************************************
  */
/* USER CODE END Header */

/* Includes ------------------------------------------------------------------*/
#include "app_common.h"

#include "main.h"
#include "dbg_trace.h"
#include "ble.h"
#include "tl.h"
#include "app_ble.h"

#include "stm32_seq.h"
#include "shci.h"
#include "stm32_lpm.h"
#include "hw_if.h"
#include "otp.h"

#ifdef OTA_SBSFU
#include "ota_sbsfu.h"
#endif /* OTA_SBSFU */

#include "audio_stream_stm32wb.h"
#include "ball_motion_diagnostic.h"
#include "companion_gatt_stm32wb.h"
#include "companion_screen_ui.h"
#include "companion_v1_features.h"
#include "diag_log.h"
#include "diag_log_export.h"
#include "companion_platform_adapters.h"
#include "companion_product_entry_glue.h"
#include "companion_product_identity.h"
#include "companion_product_transport.h"
#include "companion_ble_name_entry.h"
#include "display_queue.h"
#include "asset_store.h"
#include "emote_asset_pack.h"
#include "emote_player.h"
#include "expression_asset_source.h"
#include "expression_choreographer.h"
#include "expression_events.h"
#include "expression_rig_frame_source.h"
#include "expression_state.h"
#include "generated/expression_rig_v9_candidate_profile.h"
#include "generated/expression_rig_v22_emotion_separation_candidate_profile.h"
#include "motion_coordinator.h"
#include "menu_v5_target_bridge.h"
#include "panel_adapter.h"
#include "panel_target_stm32wb.h"
#include "pet_attention.h"
#include "pet_behavior.h"
#include "pet_performance.h"
#include "pet_performance_event_bridge.h"
#include "refresh_policy.h"
#include "screen_presentation.h"
#include "screen_runtime.h"
#include "v9_candidate_resource_binding.h"

/* The bring-up image does not link the resident loader.  A linked loader may
 * provide this boundary; the weak default deliberately leaves OTA blocked. */
__attribute__((weak)) bool Companion_Ota_V1_ReadCandidate(
    uint32_t *image_size, uint32_t *partition_size, bool *pending_verify,
    bool *post_update_self_check)
{
  (void)image_size; (void)partition_size; (void)pending_verify;
  (void)post_update_self_check;
  return false;
}

#ifndef COMPANION_SCREEN_MENU_ENABLED
#define COMPANION_SCREEN_MENU_ENABLED 0
#endif

/* Offline-only candidate route. Keep the real controller path disabled. */
#ifndef COMPANION_BLE_NAME_PLATFORM_GATE
#define COMPANION_BLE_NAME_PLATFORM_GATE 0
#endif

#ifndef COMPANION_SCREEN_EMOTE_DEMO
#define COMPANION_SCREEN_EMOTE_DEMO 0
#endif

#ifndef COMPANION_SCREEN_STABLE_DAILY_RECOVERY_DEMO
#define COMPANION_SCREEN_STABLE_DAILY_RECOVERY_DEMO 0
#endif

#ifndef COMPANION_SCREEN_V9_MANUAL_STEP_DIAGNOSTIC
#define COMPANION_SCREEN_V9_MANUAL_STEP_DIAGNOSTIC 0
#endif

#ifndef COMPANION_SCREEN_DAILY_TAP_DEMO
#define COMPANION_SCREEN_DAILY_TAP_DEMO 0
#endif

#ifndef COMPANION_SCREEN_DAILY_STROKE_DEMO
#define COMPANION_SCREEN_DAILY_STROKE_DEMO 0
#endif

#ifndef COMPANION_SCREEN_DAILY_STROKE_DEMO_DIRECTION
#define COMPANION_SCREEN_DAILY_STROKE_DEMO_DIRECTION 4u
#endif

#ifndef COMPANION_SCREEN_DAILY_RIG_DEMO
#define COMPANION_SCREEN_DAILY_RIG_DEMO 0
#endif

#ifndef COMPANION_SCREEN_DAILY_RIG_DEMO_DIRECTION
#define COMPANION_SCREEN_DAILY_RIG_DEMO_DIRECTION 4u
#endif

#ifndef COMPANION_SCREEN_V22_EMOTION_BRIDGE_DEMO
#define COMPANION_SCREEN_V22_EMOTION_BRIDGE_DEMO 0
#endif

#ifndef COMPANION_SCREEN_V22_EMOTION_BRIDGE_DEMO_EDGE
#define COMPANION_SCREEN_V22_EMOTION_BRIDGE_DEMO_EDGE 0u
#endif

#if COMPANION_SCREEN_DAILY_RIG_DEMO && COMPANION_SCREEN_V22_EMOTION_BRIDGE_DEMO
#error "Daily Rig and V22 emotion-bridge demos cannot share one candidate resource payload"
#endif

#if (COMPANION_SCREEN_STABLE_DAILY_RECOVERY_DEMO || \
     COMPANION_SCREEN_V9_MANUAL_STEP_DIAGNOSTIC) && \
    (COMPANION_SCREEN_EMOTE_DEMO || COMPANION_SCREEN_DAILY_TAP_DEMO || \
     COMPANION_SCREEN_DAILY_STROKE_DEMO || COMPANION_SCREEN_DAILY_RIG_DEMO || \
     COMPANION_SCREEN_V22_EMOTION_BRIDGE_DEMO || \
     COMPANION_SCREEN_PRODUCT_EXPRESSION_DEMO)
#error "Production-off V9 recovery diagnostics must be the sole expression producer"
#endif

#if COMPANION_SCREEN_STABLE_DAILY_RECOVERY_DEMO && \
    COMPANION_SCREEN_V9_MANUAL_STEP_DIAGNOSTIC
#error "Stable Daily recovery and V9 manual-step diagnostic are separate images"
#endif

#if COMPANION_SCREEN_V22_EMOTION_BRIDGE_DEMO && \
    COMPANION_SCREEN_V22_EMOTION_BRIDGE_DEMO_EDGE >= \
        COMP_V22_EMOTION_SEPARATION_RIG_CANDIDATE_BRIDGE_COUNT
#error "COMPANION_SCREEN_V22_EMOTION_BRIDGE_DEMO_EDGE must name one registered V22 bridge"
#endif

#ifndef COMPANION_SCREEN_REFRESH_CADENCE_DIAGNOSTIC
#define COMPANION_SCREEN_REFRESH_CADENCE_DIAGNOSTIC 0
#endif

#ifndef COMPANION_SCREEN_BALL_MOTION_DIAGNOSTIC
#define COMPANION_SCREEN_BALL_MOTION_DIAGNOSTIC 0
#endif

#define COMPANION_SCREEN_REFRESH_CADENCE_DIAGNOSTIC_REQUESTS 6u

#ifndef COMPANION_SCREEN_REFRESH_CADENCE_DIAGNOSTIC_GROUPS
#define COMPANION_SCREEN_REFRESH_CADENCE_DIAGNOSTIC_GROUPS 1u
#endif

#ifndef COMPANION_SCREEN_PRODUCT_EXPRESSION_DEMO
#define COMPANION_SCREEN_PRODUCT_EXPRESSION_DEMO 0
#endif

#ifndef COMPANION_SCREEN_PRODUCT_EXPRESSION_DEMO_SIGNAL
#define COMPANION_SCREEN_PRODUCT_EXPRESSION_DEMO_SIGNAL \
  COMP_EPAPER_EXPRESSION_SIGNAL_WAKE_DETECTED
#endif

#ifndef COMPANION_SCREEN_PRODUCT_EXPRESSION_DEMO_END_SIGNAL
#define COMPANION_SCREEN_PRODUCT_EXPRESSION_DEMO_END_SIGNAL \
  COMP_EPAPER_EXPRESSION_SIGNAL_COUNT
#endif

#ifndef COMPANION_SCREEN_PRODUCT_EXPRESSION_DEMO_END_AFTER_MS
#define COMPANION_SCREEN_PRODUCT_EXPRESSION_DEMO_END_AFTER_MS 10000u
#endif

#define COMPANION_SCREEN_ASSET_CLIP_CAPACITY 48u
#define COMPANION_SCREEN_ASSET_FRAME_CAPACITY 256u
#define COMPANION_SCREEN_ASSET_STRING_CAPACITY 1024u
#define COMPANION_SCREEN_ASSET_SCRATCH_BYTES 256u
#define COMPANION_DAILY_RIG_FRAME_BYTES (200u * 25u)
#define COMPANION_DAILY_RIG_COMPONENT_SCRATCH_BYTES 512u
#define COMPANION_PET_FEATURE_DIRTY_X 8u
#define COMPANION_PET_FEATURE_DIRTY_Y 18u
#define COMPANION_PET_FEATURE_DIRTY_WIDTH 184u
#define COMPANION_PET_FEATURE_DIRTY_HEIGHT 166u

/* Private includes ----------------------------------------------------------*/
/* USER CODE BEGIN Includes */
#include <stdint.h>
#include <stdio.h>
#include <string.h>

/* USER CODE END Includes */

/* Successful interaction logs can be emitted by a touch callback while the
 * SSD1681 is BUSY. Keep them in the existing trace image, not production. */
#ifndef COMPANION_TOUCH_VERBOSE_TRACE
#define COMPANION_TOUCH_VERBOSE_TRACE 0
#endif
#if COMPANION_TOUCH_VERBOSE_TRACE != 0 && COMPANION_TOUCH_VERBOSE_TRACE != 1
#error "Companion touch verbose trace must be 0 or 1"
#endif
#if COMPANION_TOUCH_VERBOSE_TRACE
#define SCREEN_INTERACTION_TRACE(...) printf(__VA_ARGS__)
#else
#define SCREEN_INTERACTION_TRACE(...) do { if (0) { printf(__VA_ARGS__); } } while (0)
#endif

/* Private typedef -----------------------------------------------------------*/
/* USER CODE BEGIN PTD */
typedef enum
{
  COMPANION_BLE_LINK_MODE_NONE = 0,
  COMPANION_BLE_LINK_MODE_ACTIVE_AUDIO = 1,
  COMPANION_BLE_LINK_MODE_IDLE = 2,
} Companion_BleLinkMode_t;

#pragma pack(push, 1)
typedef struct
{
  uint32_t recording_id;
  uint32_t started_unix_s;
  uint32_t duration_ms;
  uint8_t codec;
  uint8_t sync_state;
  uint8_t source_mode;
  uint8_t reserved;
  uint32_t total_length;
  uint8_t sha256_prefix[8];
  uint32_t content_crc32;
} Companion_Gatt_RecordingListEntryV1_t;

typedef struct
{
  uint8_t schema_version;
  uint8_t flags;
  uint16_t payload_length;
  uint32_t recording_id;
  uint32_t packet_sequence;
  uint32_t byte_offset;
  uint32_t total_length;
  uint32_t packet_crc32;
  uint8_t final_sha256[COMPANION_RECORDING_FLASH_SHA256_BYTES];
} Companion_Gatt_RecordingChunkHeaderV1_t;
#pragma pack(pop)

/* USER CODE END PTD */

/* Private defines -----------------------------------------------------------*/
#define COMPANION_BLE_PRODUCT_NAME "companion"
#define APPBLE_GAP_DEVICE_NAME_LENGTH (sizeof(COMPANION_BLE_PRODUCT_NAME) - 1u)
#define COMPANION_BLE_IO_CAPABILITY CFG_IO_CAPABILITY_NO_INPUT_NO_OUTPUT
#define COMPANION_BLE_BONDING_MODE 0
#define COMPANION_BLE_MITM_PROTECTION 0
#define COMPANION_BLE_ADDRESS_OFFSET 0u
#define COMPANION_BLE_CONN_HANDLE_INVALID 0xFFFFu
#define COMPANION_BLE_LINK_ACTIVE_INTERVAL_MIN 0x0006u
#define COMPANION_BLE_LINK_ACTIVE_INTERVAL_MAX 0x0006u
#define COMPANION_BLE_LINK_ACTIVE_LATENCY 0x0000u
#define COMPANION_BLE_LINK_ACTIVE_TIMEOUT 0x0320u
#define COMPANION_BLE_LINK_IDLE_INTERVAL_MIN 0x0050u
#define COMPANION_BLE_LINK_IDLE_INTERVAL_MAX 0x0078u
#define COMPANION_BLE_LINK_IDLE_LATENCY 0x0009u
#define COMPANION_BLE_LINK_IDLE_TIMEOUT 0x0258u
#define COMPANION_BLE_LINK_PHY_ALL_SPECIFIED 0x00u
#define COMPANION_BLE_LINK_PHY_2M 0x02u
#define COMPANION_BLE_LINK_PHY_OPTIONS_NONE 0x0000u
#define COMPANION_GATT_RECORDING_FLAG_FINAL 0x01u
#define COMPANION_GATT_RECORDING_FLAG_ERROR 0x80u
#define COMPANION_GATT_RECORDING_CHUNK_PAYLOAD_MAX \
  (COMPANION_GATT_MAX_PAYLOAD_BYTES - sizeof(Companion_Gatt_RecordingChunkHeaderV1_t))
#define COMPANION_EPAPER_EXPRESSION_CARD_SLOT 1u
#define COMPANION_EPAPER_EXPRESSION_REQUEST_BASE 0xE0000000u
#define COMPANION_EPAPER_EXPRESSION_TIMER_ID_INVALID CFG_HW_TS_MAX_NBR_CONCURRENT_TIMER
#define COMPANION_SETTINGS_FLAG_QUIET_HOURS_ACTIVE 0x0001u

#define BD_ADDR_SIZE_LOCAL    6

/* USER CODE BEGIN PD */
/* USER CODE END PD */

/* Private macro -------------------------------------------------------------*/
/* USER CODE BEGIN PM */

/* USER CODE END PM */

/* Private variables ---------------------------------------------------------*/
PLACE_IN_SECTION("MB_MEM1") ALIGN(4) static TL_CmdPacket_t BleCmdBuffer;

#if (CFG_IDENTITY_ADDRESS == GAP_PUBLIC_ADDR)
static const uint8_t a_MBdAddr[BD_ADDR_SIZE_LOCAL] =
{
  (uint8_t)((CFG_ADV_BD_ADDRESS & 0x0000000000FF)),
  (uint8_t)((CFG_ADV_BD_ADDRESS & 0x00000000FF00) >> 8),
  (uint8_t)((CFG_ADV_BD_ADDRESS & 0x000000FF0000) >> 16),
  (uint8_t)((CFG_ADV_BD_ADDRESS & 0x0000FF000000) >> 24),
  (uint8_t)((CFG_ADV_BD_ADDRESS & 0x00FF00000000) >> 32),
  (uint8_t)((CFG_ADV_BD_ADDRESS & 0xFF0000000000) >> 40)
};

static uint8_t a_BdAddrUdn[BD_ADDR_SIZE_LOCAL];
#endif

/**
 *   Identity root key used to derive IRK and DHK(Legacy)
 */
static const uint8_t a_BLE_CfgIrValue[16] = CFG_BLE_IR;

/**
 * Encryption root key used to derive LTK(Legacy) and CSRK
 */
static const uint8_t a_BLE_CfgErValue[16] = CFG_BLE_ER;
static uint16_t connectionHandle = COMPANION_BLE_CONN_HANDLE_INVALID;

static const char a_LocalName[] = { AD_TYPE_COMPLETE_LOCAL_NAME, 'c', 'o', 'm', 'p', 'a', 'n', 'i', 'o', 'n' };
uint8_t a_ManufData[14] = {
    sizeof(a_ManufData)-1,
    AD_TYPE_MANUFACTURER_SPECIFIC_DATA,
    0x01/*SKD version */,
    0x01 /* Companion app */,
    0x00 /* GROUP A Feature  */,
    0x00 /* GROUP A Feature */,
    0x00 /* GROUP B Feature */,
    0x00 /* GROUP B Feature */,
    0x00, /* BLE MAC start -MSB */
    0x00,
    0x00,
    0x00,
    0x00,
    0x00, /* BLE MAC stop */
};

/* USER CODE BEGIN PV */
static comp_audio_stream_t s_companion_audio_stream;
static comp_epaper_display_queue_t s_companion_display_queue;
static comp_epaper_expression_state_t s_companion_expression_state;
static comp_epaper_motion_coordinator_t s_companion_motion_coordinator;
static comp_pet_behavior_t s_companion_pet_behavior;
static comp_pet_performance_t s_companion_pet_performance;
static comp_epaper_panel_adapter_t s_companion_panel_adapter;
static comp_asset_store_t s_companion_screen_asset_store;
static comp_emote_asset_mount_t s_companion_screen_asset_mount;
static comp_epaper_expression_asset_source_t s_companion_expression_asset_source;
static comp_emote_player_t s_companion_emote_player;
static comp_epaper_expression_decision_t s_companion_emote_player_decision;
static comp_emote_player_frame_t s_companion_last_emote_frame;
static comp_screen_presentation_t s_companion_screen_presentation;
static bool s_companion_screen_ui_ready = false;
/* The normal runtime recheck needs one CEMP coherence proof, but emitting the
 * old per-frame status line here can stall a touch-triggered panel update. */
static bool s_companion_screen_coherent_generation_marker_logged = false;
static bool s_companion_emote_player_ready = false;
static bool s_companion_emote_player_decision_valid = false;
static bool s_companion_last_emote_frame_valid = false;
static bool s_companion_expression_transition_immediate = false;
static const char *s_companion_touch_attention_clip = NULL;
static const char *s_companion_dynamic_touch_clip = NULL;
static uint16_t s_companion_dynamic_touch_x = 100u;
static uint16_t s_companion_dynamic_touch_y = 100u;
static bool s_companion_dynamic_touch_is_stroke = false;
static uint32_t s_companion_pet_behavior_last_advanced_ms = 0u;
static comp_emote_clip_t
    s_companion_screen_asset_clips[COMPANION_SCREEN_ASSET_CLIP_CAPACITY];
static comp_emote_frame_t
    s_companion_screen_asset_frames[COMPANION_SCREEN_ASSET_FRAME_CAPACITY];
static char s_companion_screen_asset_strings[COMPANION_SCREEN_ASSET_STRING_CAPACITY];
static uint8_t s_companion_screen_asset_scratch[COMPANION_SCREEN_ASSET_SCRATCH_BYTES];
#if COMPANION_SCREEN_DAILY_RIG_DEMO || COMPANION_SCREEN_V22_EMOTION_BRIDGE_DEMO
static comp_asset_store_t s_companion_daily_rig_asset_store;
static comp_expression_rig_frame_source_t s_companion_daily_rig_frame_source;
static uint8_t s_companion_daily_rig_frame[COMPANION_DAILY_RIG_FRAME_BYTES];
static uint8_t s_companion_daily_rig_component_scratch[
    COMPANION_DAILY_RIG_COMPONENT_SCRATCH_BYTES];
static bool s_companion_daily_rig_presentation_ready = false;
#endif
static uint32_t s_companion_expression_next_request_id =
    COMPANION_EPAPER_EXPRESSION_REQUEST_BASE | 1u;
static uint32_t s_companion_auto_motion_request_id = 0u;
static uint32_t s_companion_auto_motion_token = 0u;
static uint32_t s_companion_menu_next_request_id = 0xE2000001u;
static uint8_t s_companion_expression_tick_timer_id =
    COMPANION_EPAPER_EXPRESSION_TIMER_ID_INVALID;
static bool s_companion_expression_tick_timer_created = false;
static uint32_t s_companion_expression_tick_started_ms = 0u;
#if COMPANION_SCREEN_PRODUCT_EXPRESSION_DEMO
static uint32_t s_companion_product_expression_demo_started_ms = 0u;
static bool s_companion_product_expression_demo_end_sent = false;
#endif
#if COMPANION_SCREEN_REFRESH_CADENCE_DIAGNOSTIC
static bool s_companion_refresh_cadence_diagnostic_active = false;
static bool s_companion_refresh_cadence_diagnostic_baseline_complete = false;
static uint8_t s_companion_refresh_cadence_diagnostic_queued = 0u;
static uint8_t s_companion_refresh_cadence_diagnostic_completed = 0u;
static uint8_t s_companion_refresh_cadence_diagnostic_groups_completed = 0u;
#endif
#if COMPANION_SCREEN_BALL_MOTION_DIAGNOSTIC
static bool s_companion_ball_motion_diagnostic_active = false;
static bool s_companion_ball_motion_diagnostic_started = false;
static uint8_t s_companion_ball_motion_diagnostic_step = 0u;
#endif
static uint32_t s_companion_audio_next_session_id = 1u;
static bool s_companion_ble_connected = false;
static bool s_companion_ble_advertising = false;
static Companion_BleLinkMode_t s_companion_ble_link_mode = COMPANION_BLE_LINK_MODE_NONE;
static uint32_t s_companion_gatt_card_refresh_count = 0u;
static companion_gatt_card_status_v1_t s_companion_gatt_card_status = {
    .schema_version = 1u,
    .card_slot = 0u,
    .render_state = 0u,
    .last_error = 0u,
    .request_id = 0u,
    .content_crc32 = 0u,
    .refresh_count = 0u,
};
static companion_gatt_settings_v1_t s_companion_gatt_settings = {
    .schema_version = 1u,
    .locale = 0u,
    .flags = 0u,
    .time_zone_offset_min = 0,
    .quiet_hours_start_min = 0u,
    .quiet_hours_end_min = 0u,
    .display_brightness = 80u,
    .recorder_profile_id = 1u,
};
static const companion_gatt_settings_v1_t *s_platform_pending_settings;
static const companion_gatt_meeting_control_v1_t *s_platform_pending_meeting;
static uint32_t s_platform_pending_now_ms;
static companion_v1_result_t s_platform_invoke_result =
    COMPANION_V1_RESULT_UNSUPPORTED_COMMAND;
static companion_product_entry_glue_t s_platform_product_entry;
static companion_settings_transport_t s_platform_settings_transport;
static companion_meeting_transport_t s_platform_meeting_transport;
static companion_v1_features_t s_companion_v1_features;
static companion_ble_name_state_t s_companion_ble_name_state;
static uint32_t s_companion_audio_notify_enabled_count = 0u;
static uint32_t s_companion_audio_notify_disabled_count = 0u;
static uint32_t s_companion_audio_control_write_count = 0u;
static uint32_t s_companion_audio_session_start_count = 0u;
static comp_audio_control_t s_companion_audio_last_control = COMP_AUDIO_CONTROL_NONE;
static comp_audio_stream_status_t s_companion_audio_last_control_status = COMP_AUDIO_STREAM_OK;
static comp_audio_stream_status_t s_companion_audio_last_session_start_status =
    COMP_AUDIO_STREAM_OK;

/* USER CODE END PV */

/* Private function prototypes -----------------------------------------------*/
static void BLE_UserEvtRx(void *p_Payload);
static void BLE_StatusNot(HCI_TL_CmdStatus_t Status);
static void Ble_Tl_Init( void );
static void Ble_Hci_Gap_Gatt_Init(void);
#if (CFG_IDENTITY_ADDRESS == GAP_PUBLIC_ADDR)
static const uint8_t* BleGetBdAddress( void );
#endif
static tBleStatus Adv_Request(void);

/* USER CODE BEGIN PFP */
static void Companion_Audio_Init(void);
static void Companion_Gatt_Init(void);
static bool Companion_BleName_TargetRestart(void *context,
                                            const uint8_t *name,
                                            uint8_t length);
static void Companion_BleName_SyncFeatureState(void);
static void Companion_Gatt_Task(void);
static void Companion_Display_Task(void);
static void Companion_Gatt_HandleEvent(const companion_gatt_event_t *event,
                                       void *context);
static bool Companion_Platform_ReadCapabilities(void *context,
                                                uint64_t operation_id,
                                                uint64_t idempotency_key,
                                                uint32_t *revision,
                                                uint64_t *mask);
static bool Companion_Platform_ReadSettings(void *context, uint64_t, uint64_t, uint32_t *revision);
static bool Companion_Platform_WriteSettings(void *context, uint64_t, uint64_t, uint32_t expected,
                                             uint32_t *ack_revision);
static bool Companion_Platform_Invoke(void *context, uint64_t, uint64_t, uint32_t command);
static void Companion_Gatt_PublishInitialState(void);
static void Companion_Gatt_PublishCurrent(companion_gatt_char_id_t char_id);
static void Companion_Gatt_PublishDeviceStatus(bool apply_expression_hint);
static void Companion_Display_ApplyDeviceStatusExpressionHint(
    const companion_gatt_device_status_v1_t *status);
static void Companion_Gatt_PublishBatteryCharge(bool apply_expression_hint);
static void Companion_Gatt_PublishCardStatus(uint8_t card_slot,
                                             uint32_t request_id,
                                             uint8_t render_state,
                                             uint8_t last_error,
                                             uint32_t content_crc32);
static void Companion_Display_CreateExpressionTickTimer(void);
static void Companion_Display_TickTimerElapsed(void);
static uint32_t Companion_Display_MsToTimerTicks(uint32_t timeout_ms);
static void Companion_Display_ScheduleExpressionTick(uint32_t now_ms);
static void Companion_Display_ProcessExpressionTick(void);
static void Companion_Display_ProcessAutomaticMotion(uint32_t now_ms);
static void Companion_Display_CancelAutomaticMotion(
    comp_epaper_motion_cancel_reason_t reason);
static void Companion_Display_EnterDailyMotion(uint32_t now_ms);
static void Companion_PetBehavior_Advance(void);
static void Companion_PetPerformance_ApplyExpressionSignal(
    comp_epaper_expression_signal_t signal);
static void Companion_PetPerformance_ApplyEvent(
    comp_pet_performance_event_t event);
static bool Companion_Display_EmitEmoteFrame(bool force_full);
static bool Companion_Display_EmitEmoteFrameMode(
    comp_epaper_refresh_mode_t refresh_mode);
static bool Companion_Display_EmitEmoteFrameModeInternal(
    comp_epaper_refresh_mode_t refresh_mode,
    const comp_epaper_motion_request_t *motion_request);
static bool Companion_Display_EmitAutomaticMotionFrame(
    const comp_epaper_motion_request_t *motion_request);
static void Companion_Display_EnqueueExpressionDecision(
    const comp_epaper_expression_decision_t *decision,
    const comp_epaper_expression_state_t *previous_state,
    uint32_t request_id_hint);
static bool Companion_Screen_StartExpressionMode(
    comp_epaper_expression_t expression,
    comp_epaper_refresh_mode_t refresh_mode,
    bool daily,
    const char *reason);
#if COMPANION_SCREEN_STABLE_DAILY_RECOVERY_DEMO
static bool Companion_Screen_ShowStableDailyBaseline(void);
#endif
#if COMPANION_SCREEN_V9_MANUAL_STEP_DIAGNOSTIC
static bool Companion_Screen_StartV9ManualStepDiagnostic(void);
#endif
static void Companion_Display_EnqueueExpressionSignal(
    comp_epaper_expression_signal_t signal,
    uint32_t request_id_hint);
static void Companion_Display_EnqueueExpressionEvent(uint16_t event_code,
                                                     uint8_t severity,
                                                     uint32_t request_id_hint,
                                                     uint32_t arg0,
                                                     uint32_t arg1,
                                                     uint32_t arg2,
                                                     uint32_t arg3);
static void Companion_Display_ApplyBatteryExpressionHint(
    const companion_gatt_battery_charge_v1_t *status);
static void Companion_Display_ApplyOtaExpressionHint(
    const companion_gatt_ota_readiness_v1_t *readiness);
static bool Companion_Settings_WantsSleepy(
    const companion_gatt_settings_v1_t *settings);
static void Companion_Display_ApplySettingsExpressionHint(
    const companion_gatt_settings_v1_t *settings);
static void Companion_Diag_RecordAndEnqueueExpression(uint16_t event_code,
                                                      uint8_t severity,
                                                      uint32_t request_id_hint,
                                                      uint32_t arg0,
                                                      uint32_t arg1,
                                                      uint32_t arg2,
                                                      uint32_t arg3);
static void Companion_Gatt_PublishRecordingControlEcho(
    const companion_gatt_recording_control_v1_t *request,
    bool accepted);
static void Companion_Gatt_PublishRecordingChunk(
    const companion_gatt_recording_chunk_pull_v1_t *request);
static void Companion_Gatt_PublishSettings(void);
static void Companion_Gatt_PublishBleNameConfig(void);
static void Companion_Gatt_PublishMeetingStatus(bool apply_expression_hint);
static void Companion_Gatt_PublishImuStatus(void);
static void Companion_Gatt_PublishSpeakerStatus(bool apply_expression_hint);
static void Companion_Gatt_PublishWakeWordStatus(bool apply_expression_hint);
static void Companion_Display_ApplyMeetingStatusExpressionHint(
    const companion_gatt_meeting_status_v1_t *status);
static void Companion_Display_ApplySpeakerStatusExpressionHint(
    const companion_gatt_speaker_status_v1_t *status);
static void Companion_Display_ApplyWakeWordStatusExpressionHint(
    const companion_gatt_wake_word_status_v1_t *status);
static void Companion_Gatt_PublishDiagLogResponse(
    const companion_gatt_diag_log_pull_v1_t *request);
static void Companion_Gatt_PublishDeletePrivacyStatus(
    const companion_gatt_delete_privacy_v1_t *request,
    bool accepted);
static void Companion_Gatt_PublishOtaReadiness(bool apply_expression_hint);
static uint32_t Companion_Gatt_Fnv1a(const uint8_t *data, uint16_t length);
static void Companion_Audio_Control(void *context,
                                    comp_audio_control_t control,
                                    const uint8_t *data,
                                    size_t length);
static void Companion_Audio_UpdateDebugStatus(void);
static void Companion_Ble_Button1Task(void);
static void Companion_Ble_Button2Task(void);
static void Companion_Ble_Button3Task(void);
static bool Companion_Ble_IsConnected(void);
static tBleStatus Companion_Ble_RequestConnectionParams(const char *reason,
                                                        uint16_t interval_min,
                                                        uint16_t interval_max,
                                                        uint16_t latency,
                                                        uint16_t timeout,
                                                        Companion_BleLinkMode_t mode);
static tBleStatus Companion_Ble_RequestPreferred2MPhy(const char *reason);
static void Companion_Screen_RefreshBleStatus(void);
static bool Companion_Screen_MenuRequestMode(
    comp_screen_menu_view_t view,
    uint8_t flags,
    comp_screen_menu_language_t language,
    uint8_t home_page,
    comp_epaper_refresh_mode_t refresh_mode);
#if COMPANION_SCREEN_REFRESH_CADENCE_DIAGNOSTIC
static void Companion_Display_AdvanceRefreshCadenceDiagnostic(
    const comp_epaper_display_request_t *request,
    comp_epaper_panel_result_t panel_result);
#endif
#if COMPANION_SCREEN_BALL_MOTION_DIAGNOSTIC
static void Companion_Display_AdvanceBallMotionDiagnostic(
    const comp_epaper_display_request_t *request,
    comp_epaper_panel_result_t panel_result);
static bool Companion_Screen_QueueBallMotionDiagnosticFrame(
    uint8_t step,
    comp_epaper_refresh_mode_t refresh_mode);
#endif

/* USER CODE END PFP */

/* External variables --------------------------------------------------------*/

/* USER CODE BEGIN EV */

/* USER CODE END EV */

/* Functions Definition ------------------------------------------------------*/
void APP_BLE_Init( void )
{
  SHCI_CmdStatus_t status;
#if (CFG_IDENTITY_ADDRESS == GAP_PUBLIC_ADDR)
  tBleStatus ret = BLE_STATUS_INVALID_PARAMS;
#endif
  /* USER CODE BEGIN APP_BLE_Init_1 */

  /* USER CODE END APP_BLE_Init_1 */
  SHCI_C2_Ble_Init_Cmd_Packet_t ble_init_cmd_packet =
  {
    {{0,0,0}},                          /**< Header unused */
    {0,                                 /** pBleBufferAddress not used */
     0,                                 /** BleBufferSize not used */
     CFG_BLE_NUM_GATT_ATTRIBUTES,
     CFG_BLE_NUM_GATT_SERVICES,
     CFG_BLE_ATT_VALUE_ARRAY_SIZE,
     CFG_BLE_NUM_LINK,
     CFG_BLE_DATA_LENGTH_EXTENSION,
     CFG_BLE_PREPARE_WRITE_LIST_SIZE,
     CFG_BLE_MBLOCK_COUNT,
     CFG_BLE_MAX_ATT_MTU,
     CFG_BLE_PERIPHERAL_SCA,
     CFG_BLE_CENTRAL_SCA,
     CFG_BLE_LS_SOURCE,
     CFG_BLE_MAX_CONN_EVENT_LENGTH,
     CFG_BLE_HSE_STARTUP_TIME,
     CFG_BLE_VITERBI_MODE,
     CFG_BLE_OPTIONS,
     0,
     CFG_BLE_MAX_COC_INITIATOR_NBR,
     CFG_BLE_MIN_TX_POWER,
     CFG_BLE_MAX_TX_POWER,
     CFG_BLE_RX_MODEL_CONFIG,
     CFG_BLE_MAX_ADV_SET_NBR,
     CFG_BLE_MAX_ADV_DATA_LEN,
     CFG_BLE_TX_PATH_COMPENS,
     CFG_BLE_RX_PATH_COMPENS,
     CFG_BLE_CORE_VERSION,
     CFG_BLE_OPTIONS_EXT,
     CFG_BLE_MAX_ADD_EATT_BEARERS
    }
  };

  /**
   * Initialize Ble Transport Layer
   */
  Ble_Tl_Init( );

  /**
   * Do not allow standby in the application
   */
  UTIL_LPM_SetOffMode(1 << CFG_LPM_APP_BLE, UTIL_LPM_DISABLE);

  /**
   * Register the hci transport layer to handle BLE User Asynchronous Events
   */
  UTIL_SEQ_RegTask( 1<<CFG_TASK_HCI_ASYNCH_EVT_ID, UTIL_SEQ_RFU, hci_user_evt_proc);

  /**
   * Starts the BLE Stack on CPU2
   */
  status = SHCI_C2_BLE_Init(&ble_init_cmd_packet);
  if (status != SHCI_Success)
  {
    APP_DBG_MSG("  Fail   : SHCI_C2_BLE_Init command, result: 0x%02x\n\r", status);
    /* if you are here, maybe CPU2 doesn't contain STM32WB_Copro_Wireless_Binaries, see Release_Notes.html */
    Error_Handler();
  }
  else
  {
    APP_DBG_MSG("  Success: SHCI_C2_BLE_Init command\n\r");
  }

  /**
   * Initialization of HCI & GATT & GAP layer
   */
  Ble_Hci_Gap_Gatt_Init();

  /**
   * Initialization of the BLE Services
   */
  SVCCTL_Init();
  Companion_Audio_Init();
  comp_epaper_display_queue_init(&s_companion_display_queue);
  s_companion_screen_coherent_generation_marker_logged = false;
  comp_epaper_expression_state_init(&s_companion_expression_state);
  comp_epaper_motion_coordinator_init(&s_companion_motion_coordinator);
  comp_pet_behavior_init(&s_companion_pet_behavior, 0xC0A55EEDu);
  comp_pet_performance_init(&s_companion_pet_performance);
  s_companion_pet_behavior_last_advanced_ms = HAL_GetTick();
  comp_screen_presentation_init(&s_companion_screen_presentation);
  bool external_assets_ready =
      Companion_ScreenAssets_OpenExternalStore(&s_companion_screen_asset_store);
  uint8_t external_prefix[4] = {0u};
  bool external_prefix_read =
      external_assets_ready &&
      comp_asset_store_read(&s_companion_screen_asset_store,
                            0u,
                            external_prefix,
                            sizeof(external_prefix));
  const comp_screen_asset_profile_t screen_profile = {
      .width = 200u,
      .height = 200u,
      .stride_bytes = 25u,
      .pixel_format = COMP_SCREEN_PIXEL_FORMAT_MONO_1BPP_WHITE_IS_ONE_MSB,
  };
#if COMPANION_SCREEN_STABLE_DAILY_RECOVERY_DEMO || \
    COMPANION_SCREEN_V9_MANUAL_STEP_DIAGNOSTIC
  /* This production-off recovery image permits only the exact V9 CEMP so it
   * can show a verified V9 settle frame. The normal runtime remains
   * candidate-inactive in v9_candidate_resource_binding.c. */
  const bool visual_resource_activation_allowed = true;
#else
  const bool visual_resource_activation_allowed =
      comp_v9_candidate_resource_runtime_activation_allowed();
#endif
  comp_emote_asset_mount_result_t mount_result =
      external_assets_ready && visual_resource_activation_allowed
          ? comp_emote_asset_pack_mount(
                &s_companion_screen_asset_mount,
                &s_companion_screen_asset_store,
                &screen_profile,
                s_companion_screen_asset_clips,
                COMPANION_SCREEN_ASSET_CLIP_CAPACITY,
                s_companion_screen_asset_frames,
                COMPANION_SCREEN_ASSET_FRAME_CAPACITY,
                s_companion_screen_asset_strings,
                sizeof(s_companion_screen_asset_strings),
                s_companion_screen_asset_scratch,
                sizeof(s_companion_screen_asset_scratch))
          : (visual_resource_activation_allowed
                 ? COMP_EMOTE_ASSET_MOUNT_IO_ERROR
                 : COMP_EMOTE_ASSET_MOUNT_INACTIVE_BY_POLICY);
  if (mount_result == COMP_EMOTE_ASSET_MOUNT_OK &&
      !comp_v9_candidate_resource_pack_identity_matches(
          s_companion_screen_asset_mount.pack.name,
          s_companion_screen_asset_mount.pack.revision,
          s_companion_screen_asset_mount.catalog.clip_count,
          s_companion_screen_asset_mount.catalog.frame_count))
  {
    s_companion_screen_asset_mount = (comp_emote_asset_mount_t){0};
    mount_result = COMP_EMOTE_ASSET_MOUNT_REJECTED_BY_POLICY;
  }
  bool expression_assets_ready =
      mount_result == COMP_EMOTE_ASSET_MOUNT_OK &&
      comp_epaper_expression_asset_source_init(
          &s_companion_expression_asset_source,
          &s_companion_screen_asset_mount.pack);
  comp_epaper_display_queue_set_resource_revision(
      &s_companion_display_queue,
      expression_assets_ready ? s_companion_screen_asset_mount.pack.revision : 0u);
  s_companion_emote_player_ready =
      expression_assets_ready &&
      comp_emote_player_init(&s_companion_emote_player,
                             &s_companion_screen_asset_mount.catalog);
  companion_epaper_panel_stm32wb_init(
      &s_companion_panel_adapter,
      expression_assets_ready ? &s_companion_expression_asset_source : NULL);
  printf("[screen-assets] policy=v9_external_cemp store=%s prefix=%s:%02X%02X%02X%02X activation=%s identity=%s mount=%s\r\n",
         external_assets_ready ? "ready" : "unavailable",
         external_prefix_read ? "read" : "none",
         external_prefix[0],
         external_prefix[1],
         external_prefix[2],
         external_prefix[3],
         visual_resource_activation_allowed ? "allowed" : "inactive",
         mount_result == COMP_EMOTE_ASSET_MOUNT_OK ? "v9" : "not_active",
         comp_emote_asset_mount_result_name(mount_result));
  if (mount_result == COMP_EMOTE_ASSET_MOUNT_OK)
  {
    printf("[screen-assets] pack=%s revision=%lu clips=%u frames=%u profile=%ux%u stride=%u encoding=%u\r\n",
           s_companion_screen_asset_mount.pack.name,
           (unsigned long)s_companion_screen_asset_mount.pack.revision,
           (unsigned)s_companion_screen_asset_mount.catalog.clip_count,
           (unsigned)s_companion_screen_asset_mount.catalog.frame_count,
           (unsigned)s_companion_screen_asset_mount.pack.profile.width,
           (unsigned)s_companion_screen_asset_mount.pack.profile.height,
           (unsigned)s_companion_screen_asset_mount.pack.profile.stride_bytes,
           (unsigned)s_companion_screen_asset_mount.pack.frame_encoding);
  }
  printf("[screen-assets] expression_renderer=%s player=%s fallback=%s\r\n",
         expression_assets_ready ? "external_pack" : "unavailable",
         s_companion_emote_player_ready ? "ready" : "unavailable",
         "none");
  printf("[screen-assets] queue_generation revision=%lu switches=%lu last_stale_discarded=%lu stale_discarded=%lu\r\n",
         (unsigned long)comp_epaper_display_queue_active_resource_revision(
             &s_companion_display_queue),
         (unsigned long)comp_epaper_display_queue_generation_switch_count(
             &s_companion_display_queue),
         (unsigned long)comp_epaper_display_queue_last_stale_generation_discarded(
             &s_companion_display_queue),
         (unsigned long)comp_epaper_display_queue_stale_generation_discard_count(
             &s_companion_display_queue));
#if COMPANION_SCREEN_DAILY_RIG_DEMO || COMPANION_SCREEN_V22_EMOTION_BRIDGE_DEMO
  {
    static const uint8_t expected_source_sha256[32] = {
      0x91u, 0x9Fu, 0x34u, 0x49u, 0x57u, 0x66u, 0x1Du, 0xEFu,
      0x20u, 0x99u, 0xADu, 0x56u, 0xABu, 0x12u, 0x86u, 0xCCu,
      0xA9u, 0xDBu, 0xA4u, 0xD8u, 0xF0u, 0x8Bu, 0x70u, 0x26u,
      0x17u, 0xB6u, 0xDFu, 0x5Bu, 0x1Au, 0x28u, 0xE9u, 0xDAu,
    };
    const comp_expression_rig_canvas_t rig_canvas = {
      .width = 200u,
      .height = 200u,
      .stride_bytes = 25u,
    };
#if COMPANION_SCREEN_V22_EMOTION_BRIDGE_DEMO
    const uint32_t expected_rig_revision =
        COMP_V22_EMOTION_SEPARATION_RIG_CANDIDATE_REVISION;
    const uint16_t expected_rig_component_count =
        COMP_V22_EMOTION_SEPARATION_RIG_CANDIDATE_COMPONENT_COUNT;
#else
    const uint32_t expected_rig_revision =
        COMP_V9_EXPRESSION_RIG_CANDIDATE_REVISION;
    const uint16_t expected_rig_component_count =
        COMP_V9_EXPRESSION_RIG_CANDIDATE_COMPONENT_COUNT;
#endif
    uint8_t rig_header[COMP_EXPRESSION_RIG_ASSET_PACK_HEADER_BYTES] = {0u};
    uint32_t rig_pack_bytes = 0u;
    bool rig_header_ready = external_assets_ready &&
      comp_asset_store_read(&s_companion_screen_asset_store,
                            0u,
                            rig_header,
                            sizeof(rig_header));
    if (rig_header_ready) {
      rig_pack_bytes = (uint32_t)rig_header[8] |
                       ((uint32_t)rig_header[9] << 8u) |
                       ((uint32_t)rig_header[10] << 16u) |
                       ((uint32_t)rig_header[11] << 24u);
      rig_header_ready = rig_header[0] == 'C' && rig_header[1] == 'R' &&
                         rig_header[2] == 'I' && rig_header[3] == 'G' &&
                         rig_pack_bytes >= COMP_EXPRESSION_RIG_ASSET_PACK_HEADER_BYTES &&
                         rig_pack_bytes <= s_companion_screen_asset_store.size_bytes &&
                         s_companion_screen_asset_store.read != NULL;
    }
    bool rig_store_ready = rig_header_ready &&
      comp_asset_store_init_reader(&s_companion_daily_rig_asset_store,
                                   COMP_ASSET_STORAGE_EXTERNAL_NOR,
                                   rig_pack_bytes,
                                   s_companion_screen_asset_store.read,
                                   s_companion_screen_asset_store.context);
    bool rig_assets_ready = rig_store_ready &&
      comp_expression_rig_frame_source_mount(
          &s_companion_daily_rig_frame_source,
          &s_companion_daily_rig_asset_store,
          &rig_canvas,
          s_companion_daily_rig_component_scratch,
          sizeof(s_companion_daily_rig_component_scratch),
          s_companion_daily_rig_frame,
          sizeof(s_companion_daily_rig_frame));
    if (rig_assets_ready &&
        (s_companion_daily_rig_frame_source.asset_pack.revision !=
             expected_rig_revision ||
         s_companion_daily_rig_frame_source.asset_pack.component_count !=
             expected_rig_component_count ||
         memcmp(s_companion_daily_rig_frame_source.asset_pack.source_sha256,
                expected_source_sha256,
                sizeof(expected_source_sha256)) != 0)) {
      s_companion_daily_rig_frame_source = (comp_expression_rig_frame_source_t){0};
      rig_assets_ready = false;
    }
    bool rig_frame_source_ready = rig_assets_ready &&
      comp_epaper_expression_asset_source_init_frame_provider(
          &s_companion_expression_asset_source,
          comp_expression_rig_frame_source_copy_frame_index,
          &s_companion_daily_rig_frame_source);
    comp_epaper_display_queue_set_resource_revision(
        &s_companion_display_queue,
        rig_frame_source_ready ? expected_rig_revision : 0u);
    companion_epaper_panel_stm32wb_init(
        &s_companion_panel_adapter,
        rig_frame_source_ready ? &s_companion_expression_asset_source : NULL);
 #if COMPANION_SCREEN_DAILY_RIG_DEMO
    s_companion_daily_rig_presentation_ready = rig_frame_source_ready &&
      companion_epaper_panel_stm32wb_set_temporary_partial_limit(
          COMP_V9_EXPRESSION_RIG_CANDIDATE_PANEL_PARTIAL_LIMIT);
    printf("[daily-rig-demo] source=external_nor_crig header=%s bytes=%lu profile_revision=%u mount=%s presentation=%s partial_limit=%u cemp_fallback=disabled\r\n",
           rig_header_ready ? "ready" : "invalid",
           (unsigned long)rig_pack_bytes,
           (unsigned)expected_rig_revision,
           rig_frame_source_ready ? "pass" : "blocked",
           s_companion_daily_rig_presentation_ready ? "pass" : "blocked",
           (unsigned)COMP_V9_EXPRESSION_RIG_CANDIDATE_PANEL_PARTIAL_LIMIT);
 #else
    /* CWF1 is still pending.  The explicit V22 demo must never imply that a
     * generic partial-refresh sequence or residue behavior was accepted. */
    s_companion_daily_rig_presentation_ready = rig_frame_source_ready;
    printf("[v22-rig-demo] production=off source=external_nor_crig header=%s bytes=%lu profile_revision=%u components=%u mount=%s refresh=full_only waveform=vendor_cwf1_pending cemp_fallback=disabled\r\n",
           rig_header_ready ? "ready" : "invalid",
           (unsigned long)rig_pack_bytes,
           (unsigned)expected_rig_revision,
           (unsigned)expected_rig_component_count,
           rig_frame_source_ready ? "pass" : "blocked");
 #endif
  }
#endif
  printf("[screen] core_selftest menu_v5_bridge=%s gesture=%s presentation=%s emote_player=%s asset_store=%s asset_pack=%s expression_source=%s refresh_policy=%s\r\n",
         comp_menu_v5_target_bridge_self_test() ? "pass" : "fail",
         comp_touch_gesture_self_test() ? "pass" : "fail",
         comp_screen_presentation_self_test() ? "pass" : "fail",
         comp_emote_player_self_test() ? "pass" : "fail",
         comp_asset_store_self_test() ? "pass" : "fail",
         comp_emote_asset_pack_self_test() ? "pass" : "fail",
         comp_epaper_expression_asset_source_self_test() ? "pass" : "fail",
         comp_epaper_refresh_policy_self_test() ? "pass" : "fail");
  printf("[screen] pet_attention_selftest=%s\r\n",
         comp_pet_attention_self_test() ? "pass" : "fail");
  /* The host suite owns retired procedural-face and complete menu-renderer
   * self-tests.  Product firmware only renders approved external CEMP bases. */
  printf("[pet-performance] selftest=%s bridge=%s resource_activation=disabled\r\n",
         comp_pet_performance_self_test() ? "pass" : "fail",
         comp_pet_performance_event_bridge_self_test() ? "pass" : "fail");
  printf("[pet-emotion] boot mood=%s valence=%d arousal=%u curiosity=%u affection=%u attachment=%u traits=%u,%u,%u\r\n",
         comp_pet_behavior_mood_name(comp_pet_behavior_mood(&s_companion_pet_behavior)),
         (int)s_companion_pet_behavior.valence,
         (unsigned)s_companion_pet_behavior.arousal,
         (unsigned)s_companion_pet_behavior.curiosity,
         (unsigned)s_companion_pet_behavior.affection,
         (unsigned)s_companion_pet_behavior.attachment,
         (unsigned)s_companion_pet_behavior.sociability,
         (unsigned)s_companion_pet_behavior.sensitivity,
         (unsigned)s_companion_pet_behavior.playfulness);
  Companion_Gatt_Init();
  UTIL_SEQ_RegTask(1 << CFG_TASK_SW1_BUTTON_PUSHED_ID,
                   UTIL_SEQ_RFU,
                   Companion_Ble_Button1Task);
  UTIL_SEQ_RegTask(1 << CFG_TASK_SW2_BUTTON_PUSHED_ID,
                   UTIL_SEQ_RFU,
                   Companion_Ble_Button2Task);
  UTIL_SEQ_RegTask(1 << CFG_TASK_SW3_BUTTON_PUSHED_ID,
                   UTIL_SEQ_RFU,
                   Companion_Ble_Button3Task);
  UTIL_SEQ_RegTask(1 << CFG_TASK_COMPANION_GATT_ID,
                   UTIL_SEQ_RFU,
                   Companion_Gatt_Task);
  UTIL_SEQ_RegTask(1 << CFG_TASK_COMPANION_DISPLAY_ID,
                   UTIL_SEQ_RFU,
                   Companion_Display_Task);
  Companion_Display_CreateExpressionTickTimer();
#if COMPANION_SCREEN_MENU_ENABLED
#if COMPANION_SCREEN_REFRESH_CADENCE_DIAGNOSTIC
  s_companion_refresh_cadence_diagnostic_active = true;
  s_companion_refresh_cadence_diagnostic_baseline_complete = false;
  s_companion_refresh_cadence_diagnostic_queued = 0u;
  s_companion_refresh_cadence_diagnostic_completed = 0u;
  s_companion_refresh_cadence_diagnostic_groups_completed = 0u;
  printf("[screen] refresh_cadence_diagnostic start requests=%u groups=%u\r\n",
         (unsigned)COMPANION_SCREEN_REFRESH_CADENCE_DIAGNOSTIC_REQUESTS,
         (unsigned)COMPANION_SCREEN_REFRESH_CADENCE_DIAGNOSTIC_GROUPS);
  Companion_Screen_MenuRequest(COMP_SCREEN_MENU_VIEW_HOME,
                               0u,
                               COMP_SCREEN_MENU_LANGUAGE_ZH,
                               0u);
#elif COMPANION_SCREEN_BALL_MOTION_DIAGNOSTIC
  s_companion_ball_motion_diagnostic_active = false;
  s_companion_ball_motion_diagnostic_started = false;
  s_companion_ball_motion_diagnostic_step = 0u;
  printf("[screen] ball_motion_diagnostic ready action=single_touch frames=%u partial_steps=%u\r\n",
         (unsigned)(COMP_EPAPER_BALL_MOTION_DIAGNOSTIC_PARTIAL_STEPS + 1u),
         (unsigned)COMP_EPAPER_BALL_MOTION_DIAGNOSTIC_PARTIAL_STEPS);
  (void)Companion_Screen_ShowDaily();
#elif COMPANION_SCREEN_DAILY_TAP_DEMO
  if (Companion_Screen_ShowDaily())
  {
    printf("[screen] daily_tap_demo start\r\n");
    (void)Companion_Screen_DailyTap();
  }
#elif COMPANION_SCREEN_DAILY_STROKE_DEMO
  if (Companion_Screen_ShowDaily())
  {
#if COMPANION_SCREEN_DAILY_STROKE_DEMO_DIRECTION == 1u
    printf("[screen] daily_stroke_demo direction=left start=180,100 end=20,100 duration_ms=600\r\n");
    (void)Companion_Screen_DailyStrokeAt(180u, 100u, 20u, 100u, 600u);
#elif COMPANION_SCREEN_DAILY_STROKE_DEMO_DIRECTION == 2u
    printf("[screen] daily_stroke_demo direction=right start=20,100 end=180,100 duration_ms=600\r\n");
    (void)Companion_Screen_DailyStrokeAt(20u, 100u, 180u, 100u, 600u);
#elif COMPANION_SCREEN_DAILY_STROKE_DEMO_DIRECTION == 3u
    printf("[screen] daily_stroke_demo direction=up start=100,180 end=100,20 duration_ms=600\r\n");
    (void)Companion_Screen_DailyStrokeAt(100u, 180u, 100u, 20u, 600u);
#elif COMPANION_SCREEN_DAILY_STROKE_DEMO_DIRECTION == 4u
    printf("[screen] daily_stroke_demo direction=down start=100,20 end=100,180 duration_ms=600\r\n");
    (void)Companion_Screen_DailyStrokeAt(100u, 20u, 100u, 180u, 600u);
#else
#error "COMPANION_SCREEN_DAILY_STROKE_DEMO_DIRECTION must be 1..4"
#endif
  }
#elif COMPANION_SCREEN_DAILY_RIG_DEMO
  (void)Companion_Screen_PlayDailyRigDemo();
#elif COMPANION_SCREEN_V22_EMOTION_BRIDGE_DEMO
  (void)Companion_Screen_PlayV22EmotionBridgeDemo();
#elif COMPANION_SCREEN_V9_MANUAL_STEP_DIAGNOSTIC
  (void)Companion_Screen_StartV9ManualStepDiagnostic();
#elif COMPANION_SCREEN_STABLE_DAILY_RECOVERY_DEMO
  (void)Companion_Screen_ShowStableDailyBaseline();
#elif COMPANION_SCREEN_PRODUCT_EXPRESSION_DEMO
  s_companion_product_expression_demo_started_ms = HAL_GetTick();
  s_companion_product_expression_demo_end_sent = false;
  Companion_Display_EnqueueExpressionSignal(
      COMPANION_SCREEN_PRODUCT_EXPRESSION_DEMO_SIGNAL,
      0u);
#elif COMPANION_SCREEN_EMOTE_DEMO
  (void)Companion_Screen_ExpressionPreview(COMP_EPAPER_EXPRESSION_IDLE);
#else
  (void)Companion_Screen_ShowDaily();
#endif
#else
  Companion_Display_EnqueueExpressionSignal(COMP_EPAPER_EXPRESSION_SIGNAL_BOOT_IDLE,
                                             0u);
#endif
  s_companion_screen_ui_ready = true;

  /**
   * From here, all initialization are BLE application specific
   */
  /**
   * This is a safe clear in case the engi bytes are not all written
   * The error flag should be cleared before moving forward
   */
  __HAL_FLASH_CLEAR_FLAG(FLASH_FLAG_OPTVERR);

#if (CFG_IDENTITY_ADDRESS == GAP_PUBLIC_ADDR)
  const uint8_t *p_BdAddr;
  uint8_t a_BdAddrNew[6];

  p_BdAddr = BleGetBdAddress();
  /* BLE MAC */
  a_ManufData[ sizeof(a_ManufData)-6] = p_BdAddr[5];
  a_ManufData[ sizeof(a_ManufData)-5] = p_BdAddr[4];
  a_ManufData[ sizeof(a_ManufData)-4] = p_BdAddr[3];
  a_ManufData[ sizeof(a_ManufData)-3] = p_BdAddr[2];
  a_ManufData[ sizeof(a_ManufData)-2] = p_BdAddr[1];
  a_ManufData[ sizeof(a_ManufData)-1] = p_BdAddr[0] + COMPANION_BLE_ADDRESS_OFFSET;

  a_BdAddrNew[5] = p_BdAddr[5];
  a_BdAddrNew[4] = p_BdAddr[4];
  a_BdAddrNew[3] = p_BdAddr[3];
  a_BdAddrNew[2] = p_BdAddr[2];
  a_BdAddrNew[1] = p_BdAddr[1];
  a_BdAddrNew[0] = p_BdAddr[0] + COMPANION_BLE_ADDRESS_OFFSET;

  ret = aci_hal_write_config_data(CONFIG_DATA_PUBLIC_ADDRESS_OFFSET,
                                  CONFIG_DATA_PUBLIC_ADDRESS_LEN,
                                  (uint8_t*) a_BdAddrNew);
  if (ret != BLE_STATUS_SUCCESS)
  {
    APP_DBG_MSG("  Fail   : aci_hal_write_config_data command - CONFIG_DATA_PUBLIC_ADDRESS_OFFSET, result: 0x%x \n", ret);
  }
  else
  {
    APP_DBG_MSG("  Success: aci_hal_write_config_data command - CONFIG_DATA_PUBLIC_ADDRESS_OFFSET\n");
    APP_DBG_MSG("  New Public Bluetooth Address: %02x:%02x:%02x:%02x:%02x:%02x\n",a_BdAddrNew[5],a_BdAddrNew[4],a_BdAddrNew[3],a_BdAddrNew[2],a_BdAddrNew[1],a_BdAddrNew[0]);
  }
#endif

  Adv_Request();

  /* USER CODE BEGIN APP_BLE_Init_2 */

  /* USER CODE END APP_BLE_Init_2 */

  return;
}

SVCCTL_UserEvtFlowStatus_t SVCCTL_App_Notification( void *p_Pckt )
{
  hci_event_pckt *p_event_pckt;
  evt_le_meta_event *p_meta_evt;
  evt_blecore_aci *p_blecore_evt;
  hci_le_connection_complete_event_rp0        *p_connection_complete_event;


  p_event_pckt = (hci_event_pckt*) ((hci_uart_pckt *) p_Pckt)->data;

  /* USER CODE BEGIN SVCCTL_App_Notification */

  /* USER CODE END SVCCTL_App_Notification */

  switch (p_event_pckt->evt)
  {
    case HCI_DISCONNECTION_COMPLETE_EVT_CODE:
    {
      s_companion_ble_connected = false;
      s_companion_ble_advertising = false;
      companion_ble_name_set_connection(&s_companion_ble_name_state, false, false);
      Companion_Screen_RefreshBleStatus();
      connectionHandle = COMPANION_BLE_CONN_HANDLE_INVALID;
      s_companion_ble_link_mode = COMPANION_BLE_LINK_MODE_NONE;
      comp_audio_stream_set_notify_enabled(&s_companion_audio_stream, false);
      Companion_Audio_UpdateDebugStatus();
      Companion_App_HandleBleLinkReadyChanged(false);
      Adv_Request();

    }
    /* USER CODE BEGIN EVT_DISCONN_COMPLETE */

    /* USER CODE END EVT_DISCONN_COMPLETE */
    break; /* HCI_DISCONNECTION_COMPLETE_EVT_CODE */

    case HCI_LE_META_EVT_CODE:
      p_meta_evt = (evt_le_meta_event*) p_event_pckt->data;
      /* USER CODE BEGIN EVT_LE_META_EVENT */

      /* USER CODE END EVT_LE_META_EVENT */
      switch (p_meta_evt->subevent)
      {
        case HCI_LE_CONNECTION_COMPLETE_SUBEVT_CODE:
          p_connection_complete_event = (hci_le_connection_complete_event_rp0 *) p_meta_evt->data;
          connectionHandle = p_connection_complete_event->Connection_Handle;
          s_companion_ble_connected = true;
          s_companion_ble_advertising = false;
          companion_ble_name_set_connection(&s_companion_ble_name_state, true, false);
          Companion_Screen_RefreshBleStatus();
          s_companion_ble_link_mode = COMPANION_BLE_LINK_MODE_NONE;
          APP_DBG_MSG("==>> Companion connected handle=0x%04X; audio high-speed link deferred until active recording\n",
                      connectionHandle);

          /* USER CODE BEGIN HCI_EVT_LE_CONN_COMPLETE */

          /* USER CODE END HCI_EVT_LE_CONN_COMPLETE */
          break; /* HCI_LE_CONNECTION_COMPLETE_SUBEVT_CODE */

        case HCI_LE_CONNECTION_UPDATE_COMPLETE_SUBEVT_CODE:
        {
          hci_le_connection_update_complete_event_rp0 *p_connection_update_complete_event =
              (hci_le_connection_update_complete_event_rp0 *)p_meta_evt->data;
          APP_DBG_MSG("==>> Companion connection update status=0x%02X interval=0x%04X latency=%u timeout=0x%04X mode=%u\n",
                      p_connection_update_complete_event->Status,
                      p_connection_update_complete_event->Conn_Interval,
                      p_connection_update_complete_event->Conn_Latency,
                      p_connection_update_complete_event->Supervision_Timeout,
                      (unsigned int)s_companion_ble_link_mode);
          break;
        }

        case HCI_LE_PHY_UPDATE_COMPLETE_SUBEVT_CODE:
        {
          hci_le_phy_update_complete_event_rp0 *p_phy_update_complete_event =
              (hci_le_phy_update_complete_event_rp0 *)p_meta_evt->data;
          APP_DBG_MSG("==>> Companion PHY update status=0x%02X handle=0x%04X tx_phy=%u rx_phy=%u\n",
                      p_phy_update_complete_event->Status,
                      p_phy_update_complete_event->Connection_Handle,
                      p_phy_update_complete_event->TX_PHY,
                      p_phy_update_complete_event->RX_PHY);
          break;
        }

        default:
          /* USER CODE BEGIN SUBEVENT_DEFAULT */

          /* USER CODE END SUBEVENT_DEFAULT */
          break;
      }

      /* USER CODE BEGIN META_EVT */

      /* USER CODE END META_EVT */
      break; /* HCI_LE_META_EVT_CODE */

        case HCI_VENDOR_SPECIFIC_DEBUG_EVT_CODE:
          p_blecore_evt = (evt_blecore_aci*) p_event_pckt->data;
          /* USER CODE BEGIN EVT_VENDOR */

          /* USER CODE END EVT_VENDOR */
          switch (p_blecore_evt->ecode)
          {
          case ACI_GATT_INDICATION_VSEVT_CODE:
            {
              APP_DBG_MSG(">>== ACI_GATT_INDICATION_VSEVT_CODE \r");
              aci_gatt_confirm_indication(connectionHandle);
            }
            break;
            /* USER CODE BEGIN ecode */
            case ACI_GAP_PROC_COMPLETE_VSEVT_CODE:
              /* USER CODE BEGIN EVT_BLUE_GAP_PROCEDURE_COMPLETE */

              /* USER CODE END EVT_BLUE_GAP_PROCEDURE_COMPLETE */
              break; /* ACI_GAP_PROC_COMPLETE_VSEVT_CODE */

            /* USER CODE BEGIN BLUE_EVT */

            /* USER CODE END BLUE_EVT */
          }
          break; /* HCI_VENDOR_SPECIFIC_DEBUG_EVT_CODE */

          /* USER CODE BEGIN EVENT_PCKT */

          /* USER CODE END EVENT_PCKT */

          default:
            /* USER CODE BEGIN ECODE_DEFAULT*/

            /* USER CODE END ECODE_DEFAULT*/
            break;
  }

  return (SVCCTL_UserEvtFlowEnable);
}

void APP_BLE_Key_Button1_Action(void)
{
  UTIL_SEQ_SetTask(1 << CFG_TASK_SW1_BUTTON_PUSHED_ID, CFG_SCH_PRIO_0);
}

void APP_BLE_Key_Button2_Action(void)
{
  UTIL_SEQ_SetTask(1 << CFG_TASK_SW2_BUTTON_PUSHED_ID, CFG_SCH_PRIO_0);
}

void APP_BLE_Key_Button3_Action(void)
{
  UTIL_SEQ_SetTask(1 << CFG_TASK_SW3_BUTTON_PUSHED_ID, CFG_SCH_PRIO_0);
}

static void Companion_Audio_Init(void)
{
  comp_audio_stream_config_t config =
      comp_audio_stream_stm32wb_default_config(Companion_Audio_Control, NULL);
  comp_audio_stream_init(&s_companion_audio_stream, &config);

  tBleStatus status = comp_audio_stream_stm32wb_init(&s_companion_audio_stream);
  if (status != BLE_STATUS_SUCCESS)
  {
    APP_DBG_MSG("  Fail   : Companion VKA1 audio service init, result: 0x%x\n", status);
  }
  else
  {
    static const uint8_t capabilities[] =
        "caps:vka1=1 pcm16=1 live_notify=1 gatt_value=153 source=mic controls=vrec";
    (void)comp_audio_stream_stm32wb_update_capabilities(capabilities,
                                                        (uint8_t)(sizeof(capabilities) - 1u));
    Companion_Audio_UpdateDebugStatus();
    APP_DBG_MSG("  Success: Companion VKA1 audio service init\n");
  }
}

static void Companion_Ble_Button1Task(void)
{
  Companion_App_HandleBleControl(COMP_AUDIO_CONTROL_RECORDING_TOGGLE,
                                 (const uint8_t *)"BUTTON1",
                                 7u);
}

static void Companion_Ble_Button2Task(void)
{
  Companion_App_HandleBleControl(COMP_AUDIO_CONTROL_RECORDING_CANCEL,
                                 (const uint8_t *)"BUTTON2",
                                 7u);
}

static void Companion_Ble_Button3Task(void)
{
  Companion_App_HandleBleControl(COMP_AUDIO_CONTROL_RECORDING_STOP,
                                 (const uint8_t *)"BUTTON3",
                                 7u);
}

static bool Companion_Platform_ReadCapabilities(void *context,
                                                uint64_t operation_id,
                                                uint64_t idempotency_key,
                                                uint32_t *revision,
                                                uint64_t *mask)
{
  (void)context; (void)operation_id; (void)idempotency_key;
  if (revision == NULL || mask == NULL)
  {
    return false;
  }
  *revision = s_platform_settings_transport.revision;
  *mask = (UINT64_C(1) << COMPANION_GATT_CHAR_COUNT) - 1u;
  return true;
}

static bool Companion_Platform_ReadSettings(void *context, uint64_t operation_id,
                                            uint64_t idempotency_key, uint32_t *revision)
{
  (void)context; (void)operation_id; (void)idempotency_key;
  if (revision == NULL)
  {
    return false;
  }
  *revision = s_platform_settings_transport.revision;
  return true;
}

static bool Companion_Platform_WriteSettings(void *context, uint64_t operation_id,
                                             uint64_t idempotency_key, uint32_t expected,
                                             uint32_t *ack_revision)
{
  (void)context; (void)idempotency_key;
  return s_platform_pending_settings != NULL && ack_revision != NULL &&
      expected != 0u && companion_settings_transport_apply(
          &s_platform_settings_transport, HAL_GetTick(), operation_id, idempotency_key, expected,
          s_platform_pending_settings, ack_revision);
}

static bool Companion_Platform_Invoke(void *context, uint64_t operation_id,
                                      uint64_t idempotency_key, uint32_t command)
{
  (void)context; (void)idempotency_key;
  if (s_platform_pending_meeting == NULL ||
      command != s_platform_pending_meeting->command)
  {
    return false;
  }
  return companion_meeting_transport_apply(&s_platform_meeting_transport,
                                            s_platform_pending_now_ms, operation_id, idempotency_key,
                                            s_platform_pending_meeting);
}

static bool Companion_Product_ApplyMeeting(void *context, uint64_t request_id)
{
  (void)context;
  s_platform_invoke_result = companion_v1_apply_meeting_control(
      &s_companion_v1_features, s_platform_pending_meeting,
      s_platform_pending_now_ms);
  (void)request_id;
  return s_platform_invoke_result == COMPANION_V1_RESULT_OK;
}

static bool Companion_Product_BeginSettings(void *context, uint32_t now_ms,
                                            uint64_t request_id,
                                            uint64_t idempotency_key,
                                            uint32_t expected_revision,
                                            const void *payload,
                                            uint32_t *ack_revision)
{
  (void)context;
  (void)payload;
  return companion_platform_device_control_settings_event(
      now_ms, request_id, idempotency_key, expected_revision, ack_revision);
}

static bool Companion_Product_BeginMeeting(void *context, uint32_t now_ms,
                                           uint64_t request_id,
                                           uint64_t idempotency_key,
                                           const void *payload)
{
  (void)context;
  (void)payload;
  s_platform_pending_now_ms = now_ms;
  return companion_platform_device_control_invoke_event(
      now_ms, request_id, idempotency_key, s_platform_pending_meeting->command);
}

static bool Companion_BleName_TargetRestart(void *context,
                                            const uint8_t *name,
                                            uint8_t length)
{
  /* Production-off boundary: no GAP, advertising, or controller call here. */
  (void)context;
  (void)name;
  (void)length;
  return false;
}

static void Companion_BleName_SyncFeatureState(void)
{
#if COMPANION_BLE_NAME_PLATFORM_GATE
  companion_ble_name_get_config(&s_companion_ble_name_state,
                                &s_companion_v1_features.ble_name);
#endif
}

static void Companion_Gatt_Init(void)
{
  companion_v1_features_init(&s_companion_v1_features, HAL_GetTick());
  companion_ble_name_init(&s_companion_ble_name_state);
  s_platform_settings_transport.current = &s_companion_gatt_settings;
  s_platform_settings_transport.size = sizeof(s_companion_gatt_settings);
  s_platform_settings_transport.revision = 1u;
  s_platform_meeting_transport.apply = Companion_Product_ApplyMeeting;
  s_platform_meeting_transport.apply_context = NULL;
  const companion_device_control_transport_t transport = {
      NULL,
      Companion_Platform_ReadCapabilities,
      Companion_Platform_ReadSettings,
      Companion_Platform_WriteSettings,
      Companion_Platform_Invoke};
  companion_platform_device_control_bind(&transport);
  companion_product_entry_glue_init(&s_platform_product_entry, NULL,
                                     Companion_Product_BeginSettings,
                                     Companion_Product_BeginMeeting);

  tBleStatus status = companion_gatt_stm32wb_init();
  if (status != BLE_STATUS_SUCCESS)
  {
    APP_DBG_MSG("  Fail   : Companion native GATT service init, result: 0x%x\n", status);
  }
  else
  {
    Companion_Gatt_PublishInitialState();
    APP_DBG_MSG("  Success: Companion native GATT service init\n");
  }
}

static void Companion_Gatt_Task(void)
{
  (void)companion_gatt_stm32wb_drain(Companion_Gatt_HandleEvent, NULL);
}

static uint32_t Companion_Display_PackRuntimePair(uint32_t high, uint32_t low)
{
  return ((high & 0xFFFFu) << 16) | (low & 0xFFFFu);
}

static void Companion_Display_RecordRuntimeSnapshot(
    const comp_epaper_screen_runtime_snapshot_t *runtime_stats)
{
  if (runtime_stats == NULL)
  {
    return;
  }

  comp_diag_log_record_code(
      COMP_DIAG_EVT_EPAPER_RUNTIME_SNAPSHOT,
      runtime_stats->panel.error_count != 0u ? COMP_DIAG_SEV_WARN
                                             : COMP_DIAG_SEV_INFO,
      Companion_Display_PackRuntimePair(
          (uint32_t)runtime_stats->expression.current,
          (uint32_t)runtime_stats->expression.last_signal),
      Companion_Display_PackRuntimePair(
          (uint32_t)runtime_stats->display_queue.pending_count,
          (uint32_t)runtime_stats->display_queue.high_water_count),
      runtime_stats->display_queue.dropped_count,
      Companion_Display_PackRuntimePair(runtime_stats->panel.deferred_count,
                                        runtime_stats->panel.error_count));
}

#if COMPANION_SCREEN_REFRESH_CADENCE_DIAGNOSTIC
static void Companion_Display_AdvanceRefreshCadenceDiagnostic(
    const comp_epaper_display_request_t *request,
    comp_epaper_panel_result_t panel_result)
{
  uint8_t item;
  uint8_t flags;

  if (!s_companion_refresh_cadence_diagnostic_active ||
      request == NULL ||
      request->request_kind != COMP_EPAPER_DISPLAY_REQUEST_MENU)
  {
    return;
  }
  if (panel_result != COMP_EPAPER_PANEL_RESULT_OK)
  {
    s_companion_refresh_cadence_diagnostic_active = false;
    printf("[screen] refresh_cadence_diagnostic abort panel_result=%u\r\n",
           (unsigned)panel_result);
    return;
  }
  if (!s_companion_refresh_cadence_diagnostic_baseline_complete)
  {
    s_companion_refresh_cadence_diagnostic_baseline_complete = true;
    printf("[screen] refresh_cadence_diagnostic baseline_complete=1\r\n");
    printf("[screen] refresh_cadence_diagnostic group_start group=1\r\n");
  }
  else if (s_companion_refresh_cadence_diagnostic_completed <
           s_companion_refresh_cadence_diagnostic_queued)
  {
    s_companion_refresh_cadence_diagnostic_completed++;
    printf("[screen] refresh_cadence_diagnostic complete step=%u\r\n",
           (unsigned)s_companion_refresh_cadence_diagnostic_completed);
  }

  if (s_companion_refresh_cadence_diagnostic_completed >=
      COMPANION_SCREEN_REFRESH_CADENCE_DIAGNOSTIC_REQUESTS)
  {
    s_companion_refresh_cadence_diagnostic_groups_completed++;
    printf("[screen] refresh_cadence_diagnostic group_complete group=%u\r\n",
           (unsigned)s_companion_refresh_cadence_diagnostic_groups_completed);
    if (s_companion_refresh_cadence_diagnostic_groups_completed >=
        COMPANION_SCREEN_REFRESH_CADENCE_DIAGNOSTIC_GROUPS)
    {
      s_companion_refresh_cadence_diagnostic_active = false;
      printf("[screen] refresh_cadence_diagnostic done interactive_requests=%u cleanup_expected=1 groups=%u\r\n",
             (unsigned)COMPANION_SCREEN_REFRESH_CADENCE_DIAGNOSTIC_REQUESTS,
             (unsigned)s_companion_refresh_cadence_diagnostic_groups_completed);
      return;
    }
    s_companion_refresh_cadence_diagnostic_queued = 0u;
    s_companion_refresh_cadence_diagnostic_completed = 0u;
    printf("[screen] refresh_cadence_diagnostic group_start group=%u\r\n",
           (unsigned)(s_companion_refresh_cadence_diagnostic_groups_completed + 1u));
  }

  item = (uint8_t)(s_companion_refresh_cadence_diagnostic_queued %
                   COMP_SCREEN_MENU_ITEM_COUNT);
  flags = (uint8_t)(COMP_SCREEN_MENU_FLAG_PRESS_ACTIVE |
                    (item << COMP_SCREEN_MENU_FLAG_PRESS_ITEM_SHIFT));
  if (Companion_Screen_MenuRequestMode(
          COMP_SCREEN_MENU_VIEW_HOME,
          flags,
          COMP_SCREEN_MENU_LANGUAGE_ZH,
          (uint8_t)(s_companion_refresh_cadence_diagnostic_groups_completed *
                        COMPANION_SCREEN_REFRESH_CADENCE_DIAGNOSTIC_REQUESTS +
                    s_companion_refresh_cadence_diagnostic_queued + 1u),
          COMP_EPAPER_REFRESH_PARTIAL_INTERACTIVE))
  {
    s_companion_refresh_cadence_diagnostic_queued++;
    printf("[screen] refresh_cadence_diagnostic queue step=%u item=%u refresh=interactive\r\n",
           (unsigned)s_companion_refresh_cadence_diagnostic_queued,
           (unsigned)item);
  }
  else
  {
    s_companion_refresh_cadence_diagnostic_active = false;
    printf("[screen] refresh_cadence_diagnostic abort queue=failed\r\n");
  }
}
#endif

#if COMPANION_SCREEN_BALL_MOTION_DIAGNOSTIC
static bool Companion_Screen_QueueBallMotionDiagnosticFrame(
    uint8_t step,
    comp_epaper_refresh_mode_t refresh_mode)
{
  bool queued = Companion_Screen_MenuRequestMode(
      COMP_SCREEN_MENU_VIEW_HOME,
      0u,
      COMP_SCREEN_MENU_LANGUAGE_ZH,
      step,
      refresh_mode);

  if (queued)
  {
    printf("[screen] ball_motion_diagnostic queue step=%u pose=%s center=%u,%u refresh=%s\r\n",
           (unsigned)step,
           comp_epaper_ball_motion_diagnostic_position_name(step),
           (unsigned)comp_epaper_ball_motion_diagnostic_center_x(step),
           (unsigned)comp_epaper_ball_motion_diagnostic_center_y(step),
           refresh_mode == COMP_EPAPER_REFRESH_FULL ? "full" : "interactive");
  }
  return queued;
}

bool Companion_Screen_BallMotionDiagnosticStart(void)
{
  if (s_companion_ball_motion_diagnostic_started)
  {
    return false;
  }
  s_companion_ball_motion_diagnostic_started = true;
  s_companion_ball_motion_diagnostic_active = true;
  s_companion_ball_motion_diagnostic_step = 0u;
  if (!Companion_Screen_QueueBallMotionDiagnosticFrame(
          0u,
          COMP_EPAPER_REFRESH_FULL))
  {
    s_companion_ball_motion_diagnostic_active = false;
    printf("[screen] ball_motion_diagnostic abort queue=failed step=0\r\n");
    return false;
  }
  printf("[screen] ball_motion_diagnostic start trigger=single_touch path=center_up_right_down_left_center\r\n");
  return true;
}

bool Companion_Screen_BallMotionDiagnosticIsActive(void)
{
  return s_companion_ball_motion_diagnostic_active;
}

static void Companion_Display_AdvanceBallMotionDiagnostic(
    const comp_epaper_display_request_t *request,
    comp_epaper_panel_result_t panel_result)
{
  uint8_t next_step;

  if (!s_companion_ball_motion_diagnostic_active || request == NULL ||
      request->request_kind != COMP_EPAPER_DISPLAY_REQUEST_MENU ||
      request->menu_page != s_companion_ball_motion_diagnostic_step)
  {
    return;
  }
  if (panel_result != COMP_EPAPER_PANEL_RESULT_OK)
  {
    s_companion_ball_motion_diagnostic_active = false;
    printf("[screen] ball_motion_diagnostic abort panel_result=%u step=%u\r\n",
           (unsigned)panel_result,
           (unsigned)request->menu_page);
    return;
  }

  printf("[screen] ball_motion_diagnostic complete step=%u pose=%s\r\n",
         (unsigned)request->menu_page,
         comp_epaper_ball_motion_diagnostic_position_name(request->menu_page));
  if (request->menu_page >= COMP_EPAPER_BALL_MOTION_DIAGNOSTIC_PARTIAL_STEPS)
  {
    s_companion_ball_motion_diagnostic_active = false;
    printf("[screen] ball_motion_diagnostic done orbit=up_right_down_left return_center=1 cleanup_expected=1\r\n");
    return;
  }

  next_step = (uint8_t)(request->menu_page + 1u);
  s_companion_ball_motion_diagnostic_step = next_step;
  if (!Companion_Screen_QueueBallMotionDiagnosticFrame(
          next_step,
          COMP_EPAPER_REFRESH_PARTIAL_INTERACTIVE))
  {
    s_companion_ball_motion_diagnostic_active = false;
    printf("[screen] ball_motion_diagnostic abort queue=failed step=%u\r\n",
           (unsigned)next_step);
  }
}
#else
bool Companion_Screen_BallMotionDiagnosticStart(void)
{
  return false;
}

bool Companion_Screen_BallMotionDiagnosticIsActive(void)
{
  return false;
}
#endif

static void Companion_Display_Task(void)
{
  comp_epaper_display_request_t request;
  comp_epaper_screen_runtime_snapshot_t runtime_stats;
  comp_epaper_panel_report_t report;
  comp_epaper_panel_result_t panel_result;
  uint8_t render_state;
  uint8_t status_error;

  Companion_Display_ProcessExpressionTick();

  if (!comp_epaper_display_queue_dequeue(&s_companion_display_queue, &request))
  {
    return;
  }

  panel_result = comp_epaper_panel_adapter_refresh_card(&s_companion_panel_adapter,
                                                        &request,
                                                        &report);
  render_state = comp_epaper_panel_adapter_render_state(panel_result);
  status_error = comp_epaper_panel_adapter_status_error(panel_result);
  comp_epaper_screen_runtime_snapshot(&s_companion_expression_state,
                                      &s_companion_display_queue,
                                      &s_companion_panel_adapter,
                                      &runtime_stats);

  comp_diag_log_record_code(COMP_DIAG_EVT_EPAPER_UPDATE_RESULT,
                            panel_result == COMP_EPAPER_PANEL_RESULT_OK
                                ? COMP_DIAG_SEV_INFO
                                : COMP_DIAG_SEV_WARN,
                            request.request_id,
                            request.content_crc32,
                            runtime_stats.panel.attempted_count,
                            (uint32_t)panel_result);
  if (!s_companion_screen_coherent_generation_marker_logged &&
      panel_result == COMP_EPAPER_PANEL_RESULT_OK &&
      request.resource_revision == runtime_stats.display_queue.active_resource_revision)
  {
    /* Keep the serial evidence contract without putting a print in every
     * interaction frame. This is reset only when the screen queue is rebuilt. */
    s_companion_screen_coherent_generation_marker_logged = true;
    printf("[screen] coherent_generation=1 resource_revision=%lu active_revision=%lu\r\n",
           (unsigned long)request.resource_revision,
           (unsigned long)runtime_stats.display_queue.active_resource_revision);
  }
  SCREEN_INTERACTION_TRACE("[screen] display_result id=%lu kind=%u resource_revision=%lu active_revision=%lu coherent_generation=%u generation_switches=%lu last_stale_discarded=%lu pending=%lu stale_generation_discarded=%lu panel_result=%u\r\n",
         (unsigned long)request.request_id,
         (unsigned)request.request_kind,
         (unsigned long)request.resource_revision,
         (unsigned long)runtime_stats.display_queue.active_resource_revision,
         request.resource_revision == runtime_stats.display_queue.active_resource_revision ? 1u : 0u,
         (unsigned long)runtime_stats.display_queue.generation_switch_count,
         (unsigned long)runtime_stats.display_queue.last_stale_generation_discarded,
         (unsigned long)runtime_stats.display_queue.pending_count,
         (unsigned long)runtime_stats.display_queue.stale_generation_discard_count,
         (unsigned)panel_result);
  Companion_Display_RecordRuntimeSnapshot(&runtime_stats);
  Companion_Gatt_PublishCardStatus(request.card_slot,
                                   request.request_id,
                                   render_state,
                                   status_error,
                                   request.content_crc32);
  if ((request.display_flags & COMP_EPAPER_DISPLAY_FLAG_AUTO_MOTION) != 0u)
  {
    bool completed = request.request_id == s_companion_auto_motion_request_id &&
                     comp_epaper_motion_coordinator_complete_request(
                         &s_companion_motion_coordinator,
                         s_companion_auto_motion_token,
                         HAL_GetTick(),
                         panel_result == COMP_EPAPER_PANEL_RESULT_OK);
    SCREEN_INTERACTION_TRACE("[screen-motion] completion request=%lu token=%lu visible=%u accepted=%u\r\n",
                             (unsigned long)request.request_id,
                             (unsigned long)s_companion_auto_motion_token,
                             panel_result == COMP_EPAPER_PANEL_RESULT_OK ? 1u : 0u,
                             completed ? 1u : 0u);
    s_companion_auto_motion_request_id = 0u;
    s_companion_auto_motion_token = 0u;
    /* A matching failed transaction remains in the coordinator's retry state.
     * Only an unmatched completion can no longer identify a safe phase to retry. */
    if (!completed)
    {
      Companion_Display_CancelAutomaticMotion(COMP_EPAPER_MOTION_CANCEL_ERROR);
    }
    Companion_Display_ScheduleExpressionTick(HAL_GetTick());
  }
#if COMPANION_SCREEN_REFRESH_CADENCE_DIAGNOSTIC
  Companion_Display_AdvanceRefreshCadenceDiagnostic(&request, panel_result);
#endif
#if COMPANION_SCREEN_BALL_MOTION_DIAGNOSTIC
  Companion_Display_AdvanceBallMotionDiagnostic(&request, panel_result);
#endif
  /* The panel transaction is synchronous. Return the power decision to the
   * application before the sequencer can sleep again. */
  Companion_App_OnScreenRefreshComplete();

  /* A completion callback can enqueue the next diagnostic or animation frame.
   * Inspect the live queue rather than the pre-callback runtime snapshot. */
  if (comp_epaper_display_queue_pending(&s_companion_display_queue) != 0u)
  {
    UTIL_SEQ_SetTask(1 << CFG_TASK_COMPANION_DISPLAY_ID, CFG_SCH_PRIO_0);
  }
}

static uint32_t Companion_Display_NextExpressionRequestId(uint32_t request_id_hint)
{
  uint32_t request_id;

  if (request_id_hint != 0u)
  {
    return request_id_hint;
  }

  request_id = s_companion_expression_next_request_id++;
  if ((s_companion_expression_next_request_id & 0xF0000000u) !=
      COMPANION_EPAPER_EXPRESSION_REQUEST_BASE)
  {
    s_companion_expression_next_request_id =
        COMPANION_EPAPER_EXPRESSION_REQUEST_BASE | 1u;
  }
  return request_id;
}

static void Companion_Display_CreateExpressionTickTimer(void)
{
  if (s_companion_expression_tick_timer_created)
  {
    return;
  }
  if (HW_TS_Create(CFG_TIM_PROC_ID_ISR,
                   &s_companion_expression_tick_timer_id,
                   hw_ts_SingleShot,
                   Companion_Display_TickTimerElapsed) == hw_ts_Successful)
  {
    s_companion_expression_tick_timer_created = true;
  }
}

static void Companion_Display_TickTimerElapsed(void)
{
  UTIL_SEQ_SetTask(1 << CFG_TASK_COMPANION_DISPLAY_ID, CFG_SCH_PRIO_0);
}

static uint32_t Companion_Display_MsToTimerTicks(uint32_t timeout_ms)
{
  uint64_t timeout_us = (uint64_t)timeout_ms * 1000u;
  uint32_t ticks =
      (uint32_t)((timeout_us + (uint64_t)CFG_TS_TICK_VAL - 1u) /
                 (uint64_t)CFG_TS_TICK_VAL);
  return ticks == 0u ? 1u : ticks;
}

static void Companion_PetBehavior_Advance(void)
{
  uint32_t now_ms = HAL_GetTick();
  uint32_t elapsed_ms = now_ms - s_companion_pet_behavior_last_advanced_ms;

  s_companion_pet_behavior_last_advanced_ms = now_ms;
  comp_pet_behavior_advance(&s_companion_pet_behavior, elapsed_ms);
}

static void Companion_PetPerformance_ApplyExpressionSignal(
    comp_epaper_expression_signal_t signal)
{
  comp_pet_performance_frame_t frame;

  if (comp_pet_performance_apply_expression_signal(
          &s_companion_pet_performance, signal, &frame))
  {
    printf("[pet-performance] source=expression_signal signal=%u scene=%s phase=%s generation=%lu priority=%u resource=%s activation=disabled\r\n",
           (unsigned)signal,
           frame.scene_name,
           frame.phase_name,
           (unsigned long)frame.generation,
           (unsigned)frame.priority,
           frame.resource_family);
  }
}

static void Companion_PetPerformance_ApplyEvent(
    comp_pet_performance_event_t event)
{
  comp_pet_performance_frame_t frame;

  if (comp_pet_performance_apply_event(&s_companion_pet_performance,
                                        event,
                                        &frame))
  {
    printf("[pet-performance] source=product_event event=%s scene=%s phase=%s generation=%lu priority=%u resource=%s activation=disabled\r\n",
           comp_pet_performance_event_name(event),
           frame.scene_name,
           frame.phase_name,
           (unsigned long)frame.generation,
           (unsigned)frame.priority,
           frame.resource_family);
  }
}

static bool Companion_Display_EmitEmoteFrameModeInternal(
    comp_epaper_refresh_mode_t refresh_mode,
    const comp_epaper_motion_request_t *motion_request)
{
  comp_emote_player_frame_t player_frame;
  comp_epaper_expression_decision_t frame_decision;
  comp_epaper_display_queue_result_t queue_result;
  uint32_t request_id;
  uint32_t content_crc32;
  bool touch_pose;

  if (!s_companion_emote_player_ready ||
      !s_companion_emote_player_decision_valid ||
      !comp_emote_player_take_frame(&s_companion_emote_player, &player_frame))
  {
    return false;
  }

  /* CEMP supplies the approved generated-art bitmap timeline. Pet behavior
   * still selects the clip; the displayed pixels come from external Flash so
   * prompt/style swaps do not require internal firmware bitmap growth. */
  frame_decision = s_companion_emote_player_decision;
  frame_decision.name = player_frame.clip_name;
  touch_pose = s_companion_dynamic_touch_clip != NULL &&
               strcmp(player_frame.clip_name, s_companion_dynamic_touch_clip) == 0;
  if (motion_request != NULL &&
      (frame_decision.expression != COMP_EPAPER_EXPRESSION_IDLE ||
       strcmp(player_frame.clip_name, "idle") != 0 ||
       player_frame.frame_in_clip != (uint16_t)motion_request->phase))
  {
    SCREEN_INTERACTION_TRACE("[screen-motion] reject clip=%s frame=%u requested_phase=%u\r\n",
                             player_frame.clip_name,
                             (unsigned)player_frame.frame_in_clip,
                             (unsigned)motion_request->phase);
    return false;
  }
  const bool allow_stable_daily_settle =
#if COMPANION_SCREEN_STABLE_DAILY_RECOVERY_DEMO || \
    COMPANION_SCREEN_V9_MANUAL_STEP_DIAGNOSTIC
      true;
#else
      false;
#endif
  if (motion_request == NULL && !touch_pose && !allow_stable_daily_settle &&
      frame_decision.expression == COMP_EPAPER_EXPRESSION_IDLE &&
      player_frame.frame_in_clip != 0u)
  {
    /* Idle keeps a quiet first pose; only an actual interaction earns a refresh. */
    SCREEN_INTERACTION_TRACE("[pet-renderer] idle_frame_suppressed frame=%u in_clip=%u\r\n",
           (unsigned)player_frame.frame_index,
           (unsigned)player_frame.frame_in_clip);
    return true;
  }
  request_id = Companion_Display_NextExpressionRequestId(0u);
  content_crc32 = comp_epaper_expression_decision_crc32(&frame_decision) ^
                  ((uint32_t)player_frame.frame_index << 8) ^
                  ((uint32_t)player_frame.frame_in_clip << 20) ^
                  ((uint32_t)player_frame.frame.dirty_x << 1) ^
                  ((uint32_t)player_frame.frame.dirty_y << 9);
  queue_result = comp_epaper_display_queue_enqueue_expression_frame(
      &s_companion_display_queue,
      COMPANION_EPAPER_EXPRESSION_CARD_SLOT,
      motion_request == NULL ? 0u : COMP_EPAPER_DISPLAY_FLAG_AUTO_MOTION,
      request_id,
      &frame_decision,
      player_frame.frame_index,
      refresh_mode,
      player_frame.frame.dirty_x,
      player_frame.frame.dirty_y,
      player_frame.frame.dirty_width,
      player_frame.frame.dirty_height,
      content_crc32);
  if (queue_result != COMP_EPAPER_DISPLAY_QUEUE_OK)
  {
    return false;
  }
  s_companion_last_emote_frame = player_frame;
  s_companion_last_emote_frame_valid = true;
  if (motion_request != NULL)
  {
    s_companion_auto_motion_request_id = request_id;
    s_companion_auto_motion_token = motion_request->token;
  }
  Companion_Gatt_PublishCardStatus(
      COMPANION_EPAPER_EXPRESSION_CARD_SLOT,
      request_id,
      (uint8_t)COMP_EPAPER_RENDER_STATE_ACCEPTED,
      0u,
      content_crc32);
  UTIL_SEQ_SetTask(1 << CFG_TASK_COMPANION_DISPLAY_ID, CFG_SCH_PRIO_0);
  SCREEN_INTERACTION_TRACE("[pet-renderer] clip=%s frame=%u in_clip=%u phase=%u touch=%u auto=%u refresh=%u duration_ms=%u source=external_flash\r\n",
         player_frame.clip_name,
         (unsigned)player_frame.frame_index,
         (unsigned)player_frame.frame_in_clip,
         (unsigned)player_frame.phase,
         touch_pose ? 1u : 0u,
         motion_request != NULL ? 1u : 0u,
         (unsigned)refresh_mode,
         (unsigned)player_frame.frame.duration_ms);
  return true;
}

static bool Companion_Display_EmitEmoteFrameMode(
    comp_epaper_refresh_mode_t refresh_mode)
{
  return Companion_Display_EmitEmoteFrameModeInternal(refresh_mode, NULL);
}

static bool Companion_Display_EmitEmoteFrame(bool force_full)
{
  return Companion_Display_EmitEmoteFrameMode(
      force_full ? COMP_EPAPER_REFRESH_FULL
                 : COMP_EPAPER_REFRESH_PARTIAL_INTERACTIVE);
}

static void Companion_Display_CancelAutomaticMotion(
    comp_epaper_motion_cancel_reason_t reason)
{
  size_t discarded = comp_epaper_display_queue_discard_display_flags(
      &s_companion_display_queue, COMP_EPAPER_DISPLAY_FLAG_AUTO_MOTION);

  comp_epaper_motion_coordinator_cancel(&s_companion_motion_coordinator, reason);
  s_companion_auto_motion_request_id = 0u;
  s_companion_auto_motion_token = 0u;
  if (s_companion_emote_player_ready)
  {
    comp_emote_player_stop(&s_companion_emote_player);
    s_companion_emote_player_decision_valid = false;
  }
  SCREEN_INTERACTION_TRACE("[screen-motion] cancel reason=%u discarded=%u\r\n",
                           (unsigned)reason,
                           (unsigned)discarded);
}

static void Companion_Display_EnterDailyMotion(uint32_t now_ms)
{
  comp_epaper_motion_coordinator_enter_daily(&s_companion_motion_coordinator, now_ms);
  SCREEN_INTERACTION_TRACE("[screen-motion] daily_enter next_phase=entry at=%lu\r\n",
                           (unsigned long)now_ms);
}

static bool Companion_Display_EmitAutomaticMotionFrame(
    const comp_epaper_motion_request_t *motion_request)
{
  uint32_t frame_wait_ms;

  if (motion_request == NULL || !s_companion_emote_player_ready ||
      !s_companion_emote_player_decision_valid ||
      s_companion_emote_player_decision.expression != COMP_EPAPER_EXPRESSION_IDLE)
  {
    return false;
  }
  if (motion_request->phase == COMP_EPAPER_MOTION_PHASE_ENTRY)
  {
    if (!comp_emote_player_play_now_name(&s_companion_emote_player, "idle", false))
    {
      return false;
    }
  }
  else
  {
    frame_wait_ms = comp_emote_player_next_frame_in_ms(&s_companion_emote_player);
    if (frame_wait_ms == 0u ||
        !comp_emote_player_tick(&s_companion_emote_player, frame_wait_ms))
    {
      return false;
    }
  }
  return Companion_Display_EmitEmoteFrameModeInternal(
      COMP_EPAPER_REFRESH_PARTIAL_INTERACTIVE, motion_request);
}

static void Companion_Display_ProcessAutomaticMotion(uint32_t now_ms)
{
  comp_epaper_motion_snapshot_t motion_snapshot;
  comp_epaper_motion_request_t motion_request;

  comp_epaper_motion_coordinator_snapshot(&s_companion_motion_coordinator,
                                           &motion_snapshot);
  if (!motion_snapshot.daily_awake)
  {
    return;
  }
  if (comp_epaper_motion_coordinator_idle_timeout_elapsed(
          &s_companion_motion_coordinator, now_ms))
  {
    Companion_Display_CancelAutomaticMotion(COMP_EPAPER_MOTION_CANCEL_LOW_POWER);
    return;
  }
  if (s_companion_screen_presentation.mode != COMP_SCREEN_PRESENTATION_EXPRESSION ||
      !s_companion_emote_player_ready ||
      !s_companion_emote_player_decision_valid ||
      s_companion_emote_player_decision.expression != COMP_EPAPER_EXPRESSION_IDLE ||
      comp_epaper_display_queue_pending(&s_companion_display_queue) != 0u)
  {
    Companion_Display_CancelAutomaticMotion(
        COMP_EPAPER_MOTION_CANCEL_HIGH_PRIORITY);
    return;
  }
  if (comp_epaper_motion_coordinator_take_request(&s_companion_motion_coordinator,
                                                   now_ms,
                                                   &motion_request) &&
      !Companion_Display_EmitAutomaticMotionFrame(&motion_request))
  {
    Companion_Display_CancelAutomaticMotion(COMP_EPAPER_MOTION_CANCEL_ERROR);
  }
}

static void Companion_Display_ScheduleExpressionTick(uint32_t now_ms)
{
  comp_epaper_expression_state_snapshot_t expression_stats;
  comp_epaper_motion_snapshot_t motion_stats;
  uint32_t recover_ms;
  uint32_t remaining_ms = 0u;
  uint32_t player_remaining_ms;

  if (!s_companion_expression_tick_timer_created)
  {
    return;
  }

  comp_epaper_expression_state_snapshot(&s_companion_expression_state,
                                        &expression_stats);
  recover_ms = expression_stats.auto_recover_ms;
  HW_TS_Stop(s_companion_expression_tick_timer_id);

  comp_epaper_motion_coordinator_snapshot(&s_companion_motion_coordinator,
                                           &motion_stats);
  if (motion_stats.daily_awake)
  {
    if (motion_stats.request_outstanding)
    {
      return;
    }
    remaining_ms =
        comp_epaper_motion_coordinator_idle_timeout_elapsed(
            &s_companion_motion_coordinator, now_ms) ||
                (int32_t)(now_ms - motion_stats.next_request_ms) >= 0
            ? 1u
            : motion_stats.next_request_ms - now_ms;
    s_companion_expression_tick_started_ms = now_ms;
    HW_TS_Start(s_companion_expression_tick_timer_id,
                Companion_Display_MsToTimerTicks(remaining_ms));
    return;
  }

  if (expression_stats.initialized &&
      recover_ms != COMP_EPAPER_EXPRESSION_AUTO_RECOVER_DISABLED_MS)
  {
    remaining_ms =
        expression_stats.visible_age_ms >= recover_ms
            ? 1u
            : recover_ms - expression_stats.visible_age_ms;
  }
  player_remaining_ms = s_companion_emote_player_ready
                            ? comp_emote_player_next_frame_in_ms(
                                  &s_companion_emote_player)
                            : 0u;
  if (player_remaining_ms != 0u &&
      (remaining_ms == 0u || player_remaining_ms < remaining_ms))
  {
    remaining_ms = player_remaining_ms;
  }
  if (remaining_ms == 0u)
  {
    return;
  }
  s_companion_expression_tick_started_ms = now_ms;
  HW_TS_Start(s_companion_expression_tick_timer_id,
              Companion_Display_MsToTimerTicks(remaining_ms));
}

static void Companion_Display_ProcessExpressionTick(void)
{
  comp_epaper_expression_decision_t decision;
  comp_epaper_expression_state_t previous_state = s_companion_expression_state;
  uint32_t now_ms;
  uint32_t elapsed_ms;
  bool expression_changed = false;

  if (!s_companion_expression_tick_timer_created)
  {
    return;
  }

  now_ms = HAL_GetTick();
#if COMPANION_SCREEN_PRODUCT_EXPRESSION_DEMO
  if (!s_companion_product_expression_demo_end_sent &&
      COMPANION_SCREEN_PRODUCT_EXPRESSION_DEMO_END_SIGNAL <
          COMP_EPAPER_EXPRESSION_SIGNAL_COUNT &&
      now_ms - s_companion_product_expression_demo_started_ms >=
          COMPANION_SCREEN_PRODUCT_EXPRESSION_DEMO_END_AFTER_MS)
  {
    s_companion_product_expression_demo_end_sent = true;
    printf("[screen] product_demo_end signal=%u elapsed_ms=%lu\r\n",
           (unsigned)COMPANION_SCREEN_PRODUCT_EXPRESSION_DEMO_END_SIGNAL,
           (unsigned long)(now_ms - s_companion_product_expression_demo_started_ms));
    Companion_Display_EnqueueExpressionSignal(
        COMPANION_SCREEN_PRODUCT_EXPRESSION_DEMO_END_SIGNAL,
        0u);
    Companion_Display_ScheduleExpressionTick(now_ms);
    return;
  }
#endif
  elapsed_ms = now_ms - s_companion_expression_tick_started_ms;
  if (elapsed_ms == 0u)
  {
    Companion_Display_ScheduleExpressionTick(now_ms);
    return;
  }

  if (s_companion_motion_coordinator.daily_awake)
  {
    Companion_Display_ProcessAutomaticMotion(now_ms);
    Companion_Display_ScheduleExpressionTick(now_ms);
    return;
  }

  if (s_companion_expression_state.initialized &&
      comp_epaper_expression_state_tick(&s_companion_expression_state,
                                        elapsed_ms,
                                        &decision))
  {
    expression_changed = true;
    Companion_Display_EnqueueExpressionDecision(&decision, &previous_state, 0u);
  }
  if (!expression_changed && s_companion_emote_player_ready &&
      comp_emote_player_tick(&s_companion_emote_player, elapsed_ms))
  {
    Companion_Display_EmitEmoteFrame(false);
  }
  Companion_Display_ScheduleExpressionTick(now_ms);
}

static void Companion_Display_EnqueueExpressionDecision(
    const comp_epaper_expression_decision_t *decision,
    const comp_epaper_expression_state_t *previous_state,
    uint32_t request_id_hint)
{
  uint32_t request_id;
  uint32_t content_crc32;
  comp_epaper_display_queue_snapshot_t queue_stats;
  comp_epaper_display_queue_result_t queue_result;
  comp_emote_player_snapshot_t player_snapshot;
  bool player_started;

  if (decision == NULL)
  {
    return;
  }
  if (decision->expression != COMP_EPAPER_EXPRESSION_IDLE)
  {
    Companion_Display_CancelAutomaticMotion(
        COMP_EPAPER_MOTION_CANCEL_HIGH_PRIORITY);
  }
  if (s_companion_dynamic_touch_clip != NULL &&
      (decision->name == NULL ||
       strcmp(decision->name, s_companion_dynamic_touch_clip) != 0))
  {
    s_companion_dynamic_touch_clip = NULL;
    s_companion_dynamic_touch_is_stroke = false;
  }

#if COMPANION_SCREEN_MENU_ENABLED
  comp_screen_presentation_action_t presentation_action =
      comp_screen_presentation_apply_product_expression(
          &s_companion_screen_presentation,
          decision->expression);
  if (presentation_action == COMP_SCREEN_PRESENTATION_ACTION_IGNORE)
  {
    return;
  }
  if (presentation_action == COMP_SCREEN_PRESENTATION_ACTION_RESTORE_MENU)
  {
    SCREEN_INTERACTION_TRACE("[screen] presentation=restore_menu view=%u page=%u language=%u\r\n",
           (unsigned)s_companion_screen_presentation.menu_view,
           (unsigned)s_companion_screen_presentation.menu_page,
           (unsigned)s_companion_screen_presentation.menu_language);
    Companion_Screen_MenuRequest(
        s_companion_screen_presentation.menu_view,
        s_companion_screen_presentation.menu_flags,
        s_companion_screen_presentation.menu_language,
        s_companion_screen_presentation.menu_page);
    return;
  }
#endif

  /* A completed touch or product scene returns through idle. Re-enter the
   * daily coordinator here so cancellation is immediate but not permanent. */
  if (decision->expression == COMP_EPAPER_EXPRESSION_IDLE &&
      s_companion_screen_presentation.mode ==
          COMP_SCREEN_PRESENTATION_EXPRESSION &&
      !s_companion_screen_presentation.expression_returns_to_menu)
  {
    (void)Companion_Screen_StartExpressionMode(
        COMP_EPAPER_EXPRESSION_IDLE,
        COMP_EPAPER_REFRESH_PARTIAL_INTERACTIVE,
        true,
        decision->reason == NULL ? "daily_auto_resume" : decision->reason);
    return;
  }

  Companion_PetBehavior_Advance();
  comp_pet_behavior_apply_expression(&s_companion_pet_behavior,
                                     decision->expression);
  s_companion_last_emote_frame_valid = false;
  SCREEN_INTERACTION_TRACE("[pet-emotion] expression=%s mood=%s valence=%d arousal=%u curiosity=%u affection=%u attachment=%u quiet_ms=%lu engagement=%u interactions=%lu\r\n",
         comp_epaper_expression_name(decision->expression),
         comp_pet_behavior_mood_name(comp_pet_behavior_mood(&s_companion_pet_behavior)),
         (int)s_companion_pet_behavior.valence,
         (unsigned)s_companion_pet_behavior.arousal,
         (unsigned)s_companion_pet_behavior.curiosity,
         (unsigned)s_companion_pet_behavior.affection,
         (unsigned)s_companion_pet_behavior.attachment,
         (unsigned long)s_companion_pet_behavior.quiet_elapsed_ms,
         (unsigned)s_companion_pet_behavior.engagement,
         (unsigned long)s_companion_pet_behavior.interaction_count);
  if (s_companion_emote_player_ready)
  {
    s_companion_emote_player_decision = *decision;
    s_companion_emote_player_decision_valid = true;
    player_started = s_companion_expression_transition_immediate
                         ? comp_emote_player_play_now_name(
                               &s_companion_emote_player,
                               decision->name,
                               false)
                         : comp_emote_player_play_after_tail_name(
                               &s_companion_emote_player,
                               decision->name,
                               false);
    if (player_started)
    {
      if (s_companion_expression_transition_immediate)
      {
        SCREEN_INTERACTION_TRACE("[emote-player] transition=immediate name=%s\r\n",
               decision->name);
      }
      comp_emote_player_snapshot(&s_companion_emote_player, &player_snapshot);
      if (player_snapshot.handoff_pending)
      {
        SCREEN_INTERACTION_TRACE("[emote-player] handoff_pending name=%s\r\n", decision->name);
        Companion_Display_ScheduleExpressionTick(HAL_GetTick());
        return;
      }
      if (Companion_Display_EmitEmoteFrame(false))
      {
        Companion_Display_ScheduleExpressionTick(HAL_GetTick());
        return;
      }
      comp_emote_player_stop(&s_companion_emote_player);
      s_companion_emote_player_decision_valid = false;
    }
  }

  request_id = Companion_Display_NextExpressionRequestId(request_id_hint);
  content_crc32 = comp_epaper_expression_decision_crc32(decision);
  queue_result = comp_epaper_display_queue_enqueue_expression(
      &s_companion_display_queue,
      COMPANION_EPAPER_EXPRESSION_CARD_SLOT,
      0u,
      request_id,
      decision,
      content_crc32);
  comp_epaper_display_queue_snapshot(&s_companion_display_queue, &queue_stats);

  if (queue_result == COMP_EPAPER_DISPLAY_QUEUE_OK)
  {
    comp_diag_log_record_code(COMP_DIAG_EVT_EPAPER_RENDER_REQUEST,
                              COMP_DIAG_SEV_INFO,
                              request_id,
                              content_crc32,
                              (uint32_t)queue_stats.pending_count,
                              ((uint32_t)decision->expression << 16) |
                                  (uint32_t)decision->signal);
    Companion_Gatt_PublishCardStatus(
        COMPANION_EPAPER_EXPRESSION_CARD_SLOT,
        request_id,
        (uint8_t)COMP_EPAPER_RENDER_STATE_ACCEPTED,
        0u,
        content_crc32);
    Companion_Display_ScheduleExpressionTick(HAL_GetTick());
    UTIL_SEQ_SetTask(1 << CFG_TASK_COMPANION_DISPLAY_ID, CFG_SCH_PRIO_0);
  }
  else
  {
    uint8_t status_error = comp_epaper_display_queue_status_error(queue_result);
    uint8_t render_state =
        queue_result == COMP_EPAPER_DISPLAY_QUEUE_FULL
            ? (uint8_t)COMP_EPAPER_RENDER_STATE_BUSY
            : (uint8_t)COMP_EPAPER_RENDER_STATE_FAILED;
    if (previous_state != NULL)
    {
      s_companion_expression_state = *previous_state;
    }
    comp_diag_log_record_code(COMP_DIAG_EVT_EPAPER_UPDATE_RESULT,
                              queue_result == COMP_EPAPER_DISPLAY_QUEUE_FULL
                                  ? COMP_DIAG_SEV_WARN
                                  : COMP_DIAG_SEV_ERROR,
                              request_id,
                              content_crc32,
                              queue_stats.dropped_count,
                              status_error);
    Companion_Gatt_PublishCardStatus(COMPANION_EPAPER_EXPRESSION_CARD_SLOT,
                                     request_id,
                                     render_state,
                                     status_error,
                                     content_crc32);
    Companion_Display_ScheduleExpressionTick(HAL_GetTick());
  }
}

static bool Companion_Screen_MenuRequestMode(
    comp_screen_menu_view_t view,
    uint8_t flags,
    comp_screen_menu_language_t language,
    uint8_t home_page,
    comp_epaper_refresh_mode_t refresh_mode)
{
  comp_epaper_display_queue_result_t queue_result;
  uint32_t request_id;
  uint32_t content_crc32;
  size_t discarded_expression_frames;

  flags &= (uint8_t)~(COMP_SCREEN_MENU_FLAG_RECORDING |
                      COMP_SCREEN_MENU_FLAG_TOUCH_OK);
  Companion_Display_CancelAutomaticMotion(COMP_EPAPER_MOTION_CANCEL_MENU);
  flags |= Companion_Screen_RuntimeMenuFlags() &
           (COMP_SCREEN_MENU_FLAG_RECORDING | COMP_SCREEN_MENU_FLAG_TOUCH_OK);
  flags = comp_screen_menu_with_ble_flag(flags, s_companion_ble_connected);
  if (s_companion_emote_player_ready)
  {
    comp_emote_player_stop(&s_companion_emote_player);
    s_companion_emote_player_decision_valid = false;
    Companion_Display_ScheduleExpressionTick(HAL_GetTick());
  }
  discarded_expression_frames = comp_epaper_display_queue_discard_kind(
      &s_companion_display_queue,
      COMP_EPAPER_DISPLAY_REQUEST_EXPRESSION);
  s_companion_last_emote_frame_valid = false;
  request_id = s_companion_menu_next_request_id++;
  content_crc32 = 0x811C9DC5u;
  content_crc32 = (content_crc32 ^ (uint8_t)view) * 0x01000193u;
  content_crc32 = (content_crc32 ^ flags) * 0x01000193u;
  content_crc32 = (content_crc32 ^ (uint8_t)language) * 0x01000193u;
  content_crc32 = (content_crc32 ^ home_page) * 0x01000193u;
  content_crc32 = (content_crc32 ^ (uint8_t)refresh_mode) * 0x01000193u;
  queue_result = comp_epaper_display_queue_enqueue_menu(
      &s_companion_display_queue,
      0xFEu,
      request_id,
      (uint8_t)view,
      flags,
      (uint8_t)language,
      home_page,
      refresh_mode,
      content_crc32);
  if (queue_result == COMP_EPAPER_DISPLAY_QUEUE_OK)
  {
    comp_screen_presentation_show_menu(
        &s_companion_screen_presentation,
        view,
        (uint8_t)(flags &
                  (uint8_t)~(COMP_SCREEN_MENU_FLAG_PRESS_ACTIVE |
                             COMP_SCREEN_MENU_FLAG_PRESS_ITEM_MASK)),
        language,
        home_page);
    SCREEN_INTERACTION_TRACE("[screen] menu enqueue id=%lu view=%u page=%u language=%u flags=0x%02X refresh=%u discarded_expression_frames=%u\r\n",
           (unsigned long)request_id,
           (unsigned)view,
           (unsigned)home_page,
           (unsigned)language,
           (unsigned)flags,
           (unsigned)refresh_mode,
           (unsigned)discarded_expression_frames);
    UTIL_SEQ_SetTask(1 << CFG_TASK_COMPANION_DISPLAY_ID, CFG_SCH_PRIO_0);
    return true;
  }
  else
  {
    printf("[screen] menu enqueue_failed result=%u view=%u\r\n",
           (unsigned)queue_result,
           (unsigned)view);
    return false;
  }
}

void Companion_Screen_MenuRequest(comp_screen_menu_view_t view,
                                  uint8_t flags,
                                  comp_screen_menu_language_t language,
                                  uint8_t home_page)
{
  (void)Companion_Screen_MenuRequestMode(
      view,
      flags,
      language,
      home_page,
      COMP_EPAPER_REFRESH_PARTIAL_INTERACTIVE);
}

bool Companion_Screen_MenuRequestClean(comp_screen_menu_view_t view,
                                       uint8_t flags,
                                       comp_screen_menu_language_t language,
                                       uint8_t home_page)
{
  bool requested;

  SCREEN_INTERACTION_TRACE("[screen] menu_boundary=enter view=%u page=%u refresh=fast_if_baseline\r\n",
         (unsigned)view,
         (unsigned)home_page);
  requested = Companion_Screen_MenuRequestMode(view,
                                                flags,
                                                language,
                                                home_page,
                                                COMP_EPAPER_REFRESH_MAINTENANCE);
  if (requested)
  {
    Companion_PetPerformance_ApplyEvent(COMP_PET_PERFORMANCE_EVENT_MENU_OPEN);
  }
  return requested;
}

bool Companion_Screen_MenuMaintenance(void)
{
  if (s_companion_screen_presentation.mode != COMP_SCREEN_PRESENTATION_MENU)
  {
    return false;
  }
  return Companion_Screen_MenuRequestMode(
      s_companion_screen_presentation.menu_view,
      s_companion_screen_presentation.menu_flags,
      s_companion_screen_presentation.menu_language,
      s_companion_screen_presentation.menu_page,
      COMP_EPAPER_REFRESH_MAINTENANCE);
}

bool Companion_Screen_ExpressionMaintenance(void)
{
  comp_epaper_expression_decision_t decision;
  comp_emote_player_snapshot_t player_snapshot;
  comp_epaper_display_queue_result_t queue_result;
  uint32_t request_id;
  uint32_t content_crc32;

  if (s_companion_screen_presentation.mode !=
           COMP_SCREEN_PRESENTATION_EXPRESSION ||
       !s_companion_emote_player_decision_valid ||
       !s_companion_last_emote_frame_valid)
  {
    return false;
  }
  if (s_companion_emote_player_ready)
  {
    comp_emote_player_snapshot(&s_companion_emote_player, &player_snapshot);
    if (player_snapshot.playing || player_snapshot.handoff_pending ||
        player_snapshot.frame_ready)
    {
      return false;
    }
  }
  decision = s_companion_emote_player_decision;
  decision.name = s_companion_last_emote_frame.clip_name;
  request_id = Companion_Display_NextExpressionRequestId(0u);
  content_crc32 = comp_epaper_expression_decision_crc32(&decision) ^
                  ((uint32_t)s_companion_last_emote_frame.frame_index << 8) ^
                  ((uint32_t)s_companion_last_emote_frame.frame_in_clip << 20) ^
                  ((uint32_t)s_companion_last_emote_frame.frame.dirty_x << 1) ^
                  ((uint32_t)s_companion_last_emote_frame.frame.dirty_y << 9);
  queue_result = comp_epaper_display_queue_enqueue_expression_frame(
      &s_companion_display_queue,
      COMPANION_EPAPER_EXPRESSION_CARD_SLOT,
      0u,
      request_id,
      &decision,
      s_companion_last_emote_frame.frame_index,
      COMP_EPAPER_REFRESH_MAINTENANCE,
      s_companion_last_emote_frame.frame.dirty_x,
      s_companion_last_emote_frame.frame.dirty_y,
      s_companion_last_emote_frame.frame.dirty_width,
      s_companion_last_emote_frame.frame.dirty_height,
      content_crc32);
  if (queue_result != COMP_EPAPER_DISPLAY_QUEUE_OK)
  {
    return false;
  }
  Companion_Gatt_PublishCardStatus(COMPANION_EPAPER_EXPRESSION_CARD_SLOT,
                                   request_id,
                                   (uint8_t)COMP_EPAPER_RENDER_STATE_ACCEPTED,
                                   0u,
                                   content_crc32);
  UTIL_SEQ_SetTask(1 << CFG_TASK_COMPANION_DISPLAY_ID, CFG_SCH_PRIO_0);
  SCREEN_INTERACTION_TRACE("[screen] expression_maintenance source=external_flash frame=%u\r\n",
         (unsigned)s_companion_last_emote_frame.frame_index);
  return true;
}

static void Companion_Screen_RefreshBleStatus(void)
{
#if COMPANION_SCREEN_MENU_ENABLED
  uint8_t refreshed_flags;

  if (s_companion_screen_presentation.mode != COMP_SCREEN_PRESENTATION_MENU ||
      (s_companion_screen_presentation.menu_view != COMP_SCREEN_MENU_VIEW_STATUS &&
       s_companion_screen_presentation.menu_view != COMP_SCREEN_MENU_VIEW_PHONE))
  {
    return;
  }
  refreshed_flags = comp_screen_menu_with_ble_flag(
      s_companion_screen_presentation.menu_flags, s_companion_ble_connected);
  if (refreshed_flags == s_companion_screen_presentation.menu_flags)
  {
    return;
  }
  SCREEN_INTERACTION_TRACE("[screen] status_ble connected=%u refresh=partial\r\n",
         s_companion_ble_connected ? 1u : 0u);
  Companion_Screen_MenuRequest(s_companion_screen_presentation.menu_view,
                               refreshed_flags,
                               s_companion_screen_presentation.menu_language,
                               s_companion_screen_presentation.menu_page);
#endif
}

static bool Companion_Screen_StartExpressionMode(
    comp_epaper_expression_t expression,
    comp_epaper_refresh_mode_t refresh_mode,
    bool daily,
    const char *reason)
{
  comp_epaper_expression_decision_t decision;
  const char *clip_name;
  bool automatic_daily;

  if (!s_companion_emote_player_ready ||
      !comp_epaper_expression_is_supported(expression))
  {
    return false;
  }
  automatic_daily = daily && expression == COMP_EPAPER_EXPRESSION_IDLE;
  Companion_Display_CancelAutomaticMotion(
      expression == COMP_EPAPER_EXPRESSION_SLEEPY
          ? COMP_EPAPER_MOTION_CANCEL_LOW_POWER
          : COMP_EPAPER_MOTION_CANCEL_HIGH_PRIORITY);
  clip_name = comp_epaper_expression_name(expression);
  decision = (comp_epaper_expression_decision_t){
      .expression = expression,
      .signal = COMP_EPAPER_EXPRESSION_SIGNAL_BOOT_IDLE,
      .priority = comp_epaper_expression_priority(expression),
      .name = clip_name,
      .title = clip_name,
      .body = "preview",
      .footer = "external_flash",
      .reason = reason,
  };
  s_companion_emote_player_decision = decision;
  s_companion_emote_player_decision_valid = true;
  s_companion_last_emote_frame_valid = false;
  if (daily)
  {
    Companion_PetBehavior_Advance();
    comp_pet_behavior_apply_expression(&s_companion_pet_behavior, expression);
    comp_screen_presentation_show_daily(&s_companion_screen_presentation);
  }
  else
  {
    comp_screen_presentation_show_expression(&s_companion_screen_presentation,
                                             expression);
  }
  Companion_Display_CreateExpressionTickTimer();
  if (!comp_emote_player_play_now_name(&s_companion_emote_player,
                                        clip_name,
                                        false))
  {
    goto preview_failed;
  }
  if (automatic_daily)
  {
    Companion_Display_EnterDailyMotion(HAL_GetTick());
    Companion_Display_ProcessAutomaticMotion(HAL_GetTick());
    if (s_companion_auto_motion_token == 0u)
    {
      goto preview_failed;
    }
  }
  else if (!Companion_Display_EmitEmoteFrameMode(refresh_mode))
  {
preview_failed:
    comp_emote_player_stop(&s_companion_emote_player);
    s_companion_emote_player_decision_valid = false;
    Companion_Display_CancelAutomaticMotion(COMP_EPAPER_MOTION_CANCEL_ERROR);
    comp_screen_presentation_show_menu(
        &s_companion_screen_presentation,
        s_companion_screen_presentation.menu_view,
        s_companion_screen_presentation.menu_flags,
        s_companion_screen_presentation.menu_language,
        s_companion_screen_presentation.menu_page);
    printf("[emote-player] preview_failed name=%s\r\n", clip_name);
    return false;
  }
  printf("[emote-player] preview_started name=%s\r\n", clip_name);
  Companion_Display_ScheduleExpressionTick(HAL_GetTick());
  return true;
}

static bool Companion_Screen_StartExpression(comp_epaper_expression_t expression,
                                             bool force_full,
                                             bool daily,
                                             const char *reason)
{
  return Companion_Screen_StartExpressionMode(
      expression,
      force_full ? COMP_EPAPER_REFRESH_FULL
                 : COMP_EPAPER_REFRESH_PARTIAL_INTERACTIVE,
      daily,
      reason);
}

bool Companion_Screen_ExpressionPreview(comp_epaper_expression_t expression)
{
  return Companion_Screen_StartExpression(expression, false, false, "touch_menu");
}

#if COMPANION_SCREEN_STABLE_DAILY_RECOVERY_DEMO
static bool Companion_Screen_ShowStableDailyBaseline(void)
{
  comp_emote_player_frame_t entry;
  comp_emote_player_frame_t sustain;
  comp_emote_player_snapshot_t snapshot;

  if (!s_companion_emote_player_ready)
  {
    goto failed;
  }
  s_companion_emote_player_decision = (comp_epaper_expression_decision_t){
      .expression = COMP_EPAPER_EXPRESSION_IDLE,
      .signal = COMP_EPAPER_EXPRESSION_SIGNAL_BOOT_IDLE,
      .priority = comp_epaper_expression_priority(COMP_EPAPER_EXPRESSION_IDLE),
      .name = "idle",
      .title = "idle",
      .body = "stable_v9_recovery",
      .footer = "external_flash",
      .reason = "stable_daily_recovery",
  };
  s_companion_emote_player_decision_valid = true;
  s_companion_last_emote_frame_valid = false;
  Companion_Display_CancelAutomaticMotion(COMP_EPAPER_MOTION_CANCEL_HIGH_PRIORITY);
  if (!comp_emote_player_play_now_name(&s_companion_emote_player, "idle", false))
  {
    goto failed;
  }
  comp_screen_presentation_show_daily(&s_companion_screen_presentation);

  if (!comp_emote_player_take_frame(&s_companion_emote_player, &entry) ||
      entry.frame_in_clip != 0u ||
      !comp_emote_player_tick(&s_companion_emote_player, entry.frame.duration_ms) ||
      !comp_emote_player_take_frame(&s_companion_emote_player, &sustain) ||
      sustain.frame_in_clip != 1u ||
      !comp_emote_player_tick(&s_companion_emote_player, sustain.frame.duration_ms))
  {
    goto failed;
  }
  comp_emote_player_snapshot(&s_companion_emote_player, &snapshot);
  if (!snapshot.frame_ready || snapshot.frame_in_clip != 2u ||
      !Companion_Display_EmitEmoteFrameMode(COMP_EPAPER_REFRESH_FULL))
  {
    goto failed;
  }
  comp_emote_player_stop(&s_companion_emote_player);
  printf("[stable-daily-recovery] result=queued clip=idle frame=2 refresh=full player=stopped source=locked_v9_cemp\r\n");
  return true;

failed:
  comp_emote_player_stop(&s_companion_emote_player);
  s_companion_emote_player_decision_valid = false;
  printf("[stable-daily-recovery] result=blocked reason=idle_settle_unavailable\r\n");
  return false;
}
#endif

#if COMPANION_SCREEN_V9_MANUAL_STEP_DIAGNOSTIC
static const char *const k_companion_v9_manual_step_clips[] = {
    "idle",
    "touch",
    "swipe_left",
    "swipe_right",
};
static uint8_t s_companion_v9_manual_step_index = 0u;

static bool Companion_Screen_QueueV9ManualStep(uint8_t step_index)
{
  comp_emote_player_frame_t entry;
  comp_emote_player_frame_t sustain;
  comp_emote_player_snapshot_t snapshot;
  const char *clip_name;

  if (step_index >= sizeof(k_companion_v9_manual_step_clips) /
                        sizeof(k_companion_v9_manual_step_clips[0]) ||
      !s_companion_emote_player_ready ||
      comp_epaper_display_queue_pending(&s_companion_display_queue) != 0u)
  {
    printf("[v9-manual-step] result=blocked step=%u reason=resource_or_refresh_busy\r\n",
           (unsigned)step_index);
    return false;
  }

  clip_name = k_companion_v9_manual_step_clips[step_index];
  Companion_Display_CancelAutomaticMotion(COMP_EPAPER_MOTION_CANCEL_HIGH_PRIORITY);
  s_companion_emote_player_decision = (comp_epaper_expression_decision_t){
      .expression = COMP_EPAPER_EXPRESSION_IDLE,
      .signal = COMP_EPAPER_EXPRESSION_SIGNAL_BOOT_IDLE,
      .priority = comp_epaper_expression_priority(COMP_EPAPER_EXPRESSION_IDLE),
      .name = clip_name,
      .title = "v9_manual_step",
      .body = "locked_v9_settle",
      .footer = "external_flash",
      .reason = "v9_manual_step_diagnostic",
  };
  s_companion_emote_player_decision_valid = true;
  s_companion_last_emote_frame_valid = false;
  if (!comp_emote_player_play_now_name(&s_companion_emote_player, clip_name, false))
  {
    goto failed;
  }
  comp_screen_presentation_show_daily(&s_companion_screen_presentation);

  if (!comp_emote_player_take_frame(&s_companion_emote_player, &entry) ||
      entry.frame_in_clip != 0u ||
      !comp_emote_player_tick(&s_companion_emote_player, entry.frame.duration_ms) ||
      !comp_emote_player_take_frame(&s_companion_emote_player, &sustain) ||
      sustain.frame_in_clip != 1u ||
      !comp_emote_player_tick(&s_companion_emote_player, sustain.frame.duration_ms))
  {
    goto failed;
  }
  comp_emote_player_snapshot(&s_companion_emote_player, &snapshot);
  if (!snapshot.frame_ready || snapshot.frame_in_clip != 2u ||
      !Companion_Display_EmitEmoteFrameMode(COMP_EPAPER_REFRESH_FULL))
  {
    goto failed;
  }
  comp_emote_player_stop(&s_companion_emote_player);
  printf("[v9-manual-step] result=queued step=%u clip=%s frame=2 refresh=full player=stopped source=locked_v9_cemp\r\n",
         (unsigned)step_index,
         clip_name);
  return true;

failed:
  comp_emote_player_stop(&s_companion_emote_player);
  s_companion_emote_player_decision_valid = false;
  printf("[v9-manual-step] result=blocked step=%u clip=%s reason=settle_unavailable\r\n",
         (unsigned)step_index,
         clip_name == NULL ? "none" : clip_name);
  return false;
}

static bool Companion_Screen_StartV9ManualStepDiagnostic(void)
{
  s_companion_v9_manual_step_index = 0u;
  return Companion_Screen_QueueV9ManualStep(s_companion_v9_manual_step_index);
}
#endif

bool Companion_Screen_V9ManualStepDiagnosticAdvance(void)
{
#if COMPANION_SCREEN_V9_MANUAL_STEP_DIAGNOSTIC
  const uint8_t step_count =
      (uint8_t)(sizeof(k_companion_v9_manual_step_clips) /
                sizeof(k_companion_v9_manual_step_clips[0]));
  const uint8_t next_index =
      (uint8_t)((s_companion_v9_manual_step_index + 1u) % step_count);

  if (!Companion_Screen_QueueV9ManualStep(next_index))
  {
    return false;
  }
  s_companion_v9_manual_step_index = next_index;
  return true;
#else
  return false;
#endif
}

bool Companion_Screen_PlayDailyRigDemo(void)
{
#if COMPANION_SCREEN_DAILY_RIG_DEMO
  const comp_expression_rig_profile_t *profile =
      comp_v9_expression_rig_candidate_profile();
  comp_expression_rig_choreography_input_t input;
  uint32_t full_frame_refresh_count = 0u;
  uint32_t partial_or_hold_count = 0u;
  const uint8_t story_count =
      comp_v9_expression_rig_candidate_daily_presentation_story_count();

  if (profile == NULL || s_companion_daily_rig_frame_source.asset_pack.store == NULL ||
      !s_companion_daily_rig_presentation_ready ||
      COMP_V9_EXPRESSION_RIG_CANDIDATE_PANEL_CONTINUOUS_REPLAY != 1u ||
      story_count != COMP_V9_EXPRESSION_RIG_CANDIDATE_PANEL_STORY_COUNT) {
    printf("[daily-rig-demo] result=blocked reason=external_crig_or_presentation_unavailable\r\n");
    return false;
  }
  input = (comp_expression_rig_choreography_input_t){
    .event = COMP_EXPRESSION_RIG_EVENT_DAILY_AUTO,
    .attention = COMP_EXPRESSION_RIG_ATTENTION_LEFT,
    .energy = COMP_EXPRESSION_RIG_ENERGY_NORMAL,
    .interaction_memory = 0u,
    .seed = 0xD911A11Eu,
    .phase = COMP_EXPRESSION_RIG_PHASE_ENTRY,
  };
  printf("[daily-rig-demo] start replay=continuous_story_cycle stories=%u source=external_nor_crig renderer=component_compositor initial_dwell_ms=%u minimum_dwell_ms=%u\r\n",
         (unsigned)story_count,
         (unsigned)COMP_V9_EXPRESSION_RIG_CANDIDATE_PANEL_INITIAL_DWELL_MS,
         (unsigned)COMP_V9_EXPRESSION_RIG_CANDIDATE_PANEL_MINIMUM_DWELL_MS);
  for (uint32_t cycle_index = 0u;; ++cycle_index) {
    for (uint8_t story_index = 0u; story_index < story_count; ++story_index) {
      comp_expression_rig_attention_t attention;
      const comp_expression_rig_performance_score_t *score;

      if (!comp_v9_expression_rig_candidate_daily_presentation_attention(
              story_index, &attention)) {
        printf("[daily-rig-demo] result=blocked cycle=%lu story=%u reason=profile_story_order\r\n",
               (unsigned long)cycle_index,
               (unsigned)story_index);
        return false;
      }
      score = comp_v9_expression_rig_candidate_daily_score(attention);
      if (score == NULL || score->steps == NULL || score->step_count != 15u) {
        printf("[daily-rig-demo] result=blocked cycle=%lu story=%u reason=score_unavailable\r\n",
               (unsigned long)cycle_index,
               (unsigned)story_index);
        return false;
      }
      input.attention = attention;
      for (uint8_t step_index = 0u; step_index < score->step_count; ++step_index) {
        comp_expression_rig_plan_t plan;
        const comp_expression_rig_score_step_t *score_step = &score->steps[step_index];
        const bool initial_baseline =
            cycle_index == 0u && story_index == 0u && step_index == 0u;
        comp_epaper_display_request_t request;
        comp_epaper_panel_report_t report;
        comp_epaper_panel_result_t result;
        uint16_t presentation_duration_ms = score_step->duration_ms;
        uint32_t refresh_started_ms;
        uint32_t refresh_elapsed_ms;
        uint32_t post_refresh_delay_ms;
        uint32_t replay_frame_index =
            ((cycle_index * (uint32_t)story_count) + (uint32_t)story_index) *
                (uint32_t)score->step_count +
            (uint32_t)step_index;

        if (!comp_expression_rig_choreograph_daily_score_plan(profile,
                                                               &input,
                                                               score,
                                                               step_index,
                                                               &plan) ||
            !comp_expression_rig_frame_source_compose(&s_companion_daily_rig_frame_source,
                                                       &plan,
                                                       step_index)) {
          printf("[daily-rig-demo] result=blocked cycle=%lu story=%u step=%u reason=compose\r\n",
                 (unsigned long)cycle_index,
                 (unsigned)story_index,
                 (unsigned)step_index);
          return false;
        }
        if (step_index == 0u) {
          if (presentation_duration_ms <
              COMP_V9_EXPRESSION_RIG_CANDIDATE_PANEL_INITIAL_DWELL_MS) {
            presentation_duration_ms =
                COMP_V9_EXPRESSION_RIG_CANDIDATE_PANEL_INITIAL_DWELL_MS;
          }
        } else if (presentation_duration_ms <
                   COMP_V9_EXPRESSION_RIG_CANDIDATE_PANEL_MINIMUM_DWELL_MS) {
          presentation_duration_ms =
              COMP_V9_EXPRESSION_RIG_CANDIDATE_PANEL_MINIMUM_DWELL_MS;
        }
        request = (comp_epaper_display_request_t){
          .request_id = COMPANION_EPAPER_EXPRESSION_REQUEST_BASE | 0x00100000u |
                        (replay_frame_index & 0x000FFFFFu),
          .content_crc32 = 0xD9110000u | (replay_frame_index & 0x0000FFFFu),
          .request_kind = COMP_EPAPER_DISPLAY_REQUEST_EXPRESSION,
          .expression = (uint8_t)COMP_EPAPER_EXPRESSION_IDLE,
          .asset_frame_valid = 1u,
          .asset_frame_index = step_index,
          .refresh_mode = initial_baseline
                            ? COMP_EPAPER_REFRESH_FULL
                            : COMP_EPAPER_REFRESH_PARTIAL_INTERACTIVE,
          .dirty_x = s_companion_daily_rig_frame_source.current_bounds.left,
          .dirty_y = s_companion_daily_rig_frame_source.current_bounds.top,
          .dirty_width = s_companion_daily_rig_frame_source.current_bounds.width,
          .dirty_height = s_companion_daily_rig_frame_source.current_bounds.height,
        };
        refresh_started_ms = HAL_GetTick();
        result = comp_epaper_panel_adapter_refresh_card(&s_companion_panel_adapter,
                                                         &request,
                                                         &report);
        refresh_elapsed_ms = HAL_GetTick() - refresh_started_ms;
        if (result != COMP_EPAPER_PANEL_RESULT_OK) {
          printf("[daily-rig-demo] result=blocked cycle=%lu story=%u step=%u reason=panel result=%u\r\n",
                 (unsigned long)cycle_index,
                 (unsigned)story_index,
                 (unsigned)step_index,
                 (unsigned)result);
          return false;
        }
        if ((initial_baseline && report.transferred_bytes < 10000u) ||
            (!initial_baseline && report.transferred_bytes >= 10000u)) {
          printf("[daily-rig-demo] result=blocked cycle=%lu story=%u step=%u reason=whole_frame_after_boot bytes=%lu\r\n",
                 (unsigned long)cycle_index,
                 (unsigned)story_index,
                 (unsigned)step_index,
                 (unsigned long)report.transferred_bytes);
          return false;
        }
        if (initial_baseline) {
          full_frame_refresh_count++;
        } else {
          partial_or_hold_count++;
        }
        post_refresh_delay_ms = refresh_elapsed_ms < presentation_duration_ms
                                    ? (uint32_t)presentation_duration_ms - refresh_elapsed_ms
                                    : 0u;
        printf("[daily-rig-demo] cycle=%lu story=%u attention=%u step=%u phase=%s phase_id=%u score_duration_ms=%u presentation_duration_ms=%u refresh_elapsed_ms=%lu post_refresh_delay_ms=%lu layers=%u panel=%u bytes=%lu\r\n",
               (unsigned long)cycle_index,
               (unsigned)story_index,
               (unsigned)attention,
               (unsigned)step_index,
               comp_expression_rig_score_phase_name(score_step->phase),
               (unsigned)score_step->phase,
               (unsigned)score_step->duration_ms,
               (unsigned)presentation_duration_ms,
               (unsigned long)refresh_elapsed_ms,
               (unsigned long)post_refresh_delay_ms,
               (unsigned)plan.layer_count,
               (unsigned)result,
               (unsigned long)report.transferred_bytes);
        HAL_Delay(post_refresh_delay_ms);
      }
    }
    printf("[daily-rig-demo] cycle=%lu result=pass stories=%u frames=%u composed=%lu rejected_copies=%lu full_frame_refreshes=%lu partial_or_holds=%lu\r\n",
           (unsigned long)cycle_index,
           (unsigned)story_count,
           (unsigned)((uint32_t)story_count * 15u),
           (unsigned long)s_companion_daily_rig_frame_source.composed_frame_count,
           (unsigned long)s_companion_daily_rig_frame_source.rejected_copy_count,
           (unsigned long)full_frame_refresh_count,
           (unsigned long)partial_or_hold_count);
  }
#else
  return false;
#endif
}

bool Companion_Screen_PlayV22EmotionBridgeDemo(void)
{
#if COMPANION_SCREEN_V22_EMOTION_BRIDGE_DEMO
  const comp_expression_rig_profile_t *profile =
      comp_v22_emotion_separation_rig_candidate_profile();
  const comp_v22_emotion_separation_rig_bridge_t *bridge =
      comp_v22_emotion_separation_rig_candidate_bridge(
          COMPANION_SCREEN_V22_EMOTION_BRIDGE_DEMO_EDGE);
  uint8_t step_index;

  if (profile == NULL || bridge == NULL || bridge->score == NULL ||
      bridge->frames == NULL || bridge->frame_count == 0u ||
      bridge->score->step_count != bridge->frame_count ||
      s_companion_daily_rig_frame_source.asset_pack.store == NULL ||
      !s_companion_daily_rig_presentation_ready ||
      comp_v22_emotion_separation_rig_candidate_runtime_activation_allowed()) {
    printf("[v22-rig-demo] result=blocked reason=external_crig_profile_or_policy\r\n");
    return false;
  }

  printf("[v22-rig-demo] production=off start bridge=%s source=%s target=%s event=%s frames=%u refresh=full_only reverse=disabled playlist=disabled\r\n",
         bridge->name,
         bridge->source_emotion,
         bridge->target_emotion,
         bridge->event_name,
         (unsigned)bridge->frame_count);
  for (step_index = 0u; step_index < bridge->frame_count; ++step_index) {
    const comp_v22_emotion_separation_rig_frame_t *frame =
        &bridge->frames[step_index];
    comp_expression_rig_plan_t plan;
    comp_epaper_display_request_t request;
    comp_epaper_panel_report_t report;
    comp_epaper_panel_result_t result;
    uint32_t refresh_started_ms;
    uint32_t refresh_elapsed_ms;
    uint32_t post_refresh_delay_ms;

    if (!comp_expression_rig_build_registered_score_step(profile,
                                                          bridge->score,
                                                          step_index,
                                                          NULL,
                                                          &plan) ||
        !comp_expression_rig_frame_source_compose(&s_companion_daily_rig_frame_source,
                                                   &plan,
                                                   step_index)) {
      printf("[v22-rig-demo] result=blocked bridge=%s step=%u reason=compose\r\n",
             bridge->name,
             (unsigned)step_index);
      return false;
    }
    request = (comp_epaper_display_request_t){
      .request_id = COMPANION_EPAPER_EXPRESSION_REQUEST_BASE | 0x00220000u |
                    ((uint32_t)COMPANION_SCREEN_V22_EMOTION_BRIDGE_DEMO_EDGE << 8u) |
                    (uint32_t)step_index,
      .content_crc32 = 0xD9220000u |
                       ((uint32_t)COMPANION_SCREEN_V22_EMOTION_BRIDGE_DEMO_EDGE << 8u) |
                       (uint32_t)step_index,
      .request_kind = COMP_EPAPER_DISPLAY_REQUEST_EXPRESSION,
      .expression = (uint8_t)COMP_EPAPER_EXPRESSION_IDLE,
      .asset_frame_valid = 1u,
      .asset_frame_index = step_index,
      .refresh_mode = COMP_EPAPER_REFRESH_FULL,
      .dirty_x = s_companion_daily_rig_frame_source.current_bounds.left,
      .dirty_y = s_companion_daily_rig_frame_source.current_bounds.top,
      .dirty_width = s_companion_daily_rig_frame_source.current_bounds.width,
      .dirty_height = s_companion_daily_rig_frame_source.current_bounds.height,
    };
    refresh_started_ms = HAL_GetTick();
    result = comp_epaper_panel_adapter_refresh_card(&s_companion_panel_adapter,
                                                     &request,
                                                     &report);
    refresh_elapsed_ms = HAL_GetTick() - refresh_started_ms;
    if (result != COMP_EPAPER_PANEL_RESULT_OK || report.transferred_bytes < 10000u) {
      printf("[v22-rig-demo] result=blocked bridge=%s step=%u reason=panel result=%u bytes=%lu\r\n",
             bridge->name,
             (unsigned)step_index,
             (unsigned)result,
             (unsigned long)report.transferred_bytes);
      return false;
    }
    post_refresh_delay_ms = refresh_elapsed_ms < frame->duration_ms
                                ? (uint32_t)frame->duration_ms - refresh_elapsed_ms
                                : 0u;
    printf("[v22-rig-demo] bridge=%s step=%u cue=%s source_phase=%s score_duration_ms=%u refresh_elapsed_ms=%lu post_refresh_delay_ms=%lu layers=%u bytes=%lu\r\n",
           bridge->name,
           (unsigned)step_index,
           frame->cue,
           frame->source_phase,
           (unsigned)frame->duration_ms,
           (unsigned long)refresh_elapsed_ms,
           (unsigned long)post_refresh_delay_ms,
           (unsigned)plan.layer_count,
           (unsigned long)report.transferred_bytes);
    HAL_Delay(post_refresh_delay_ms);
  }
  printf("[v22-rig-demo] result=pass bridge=%s settled_target=%s composed=%lu rejected_copies=%lu reverse=disabled next_auto_frame=none\r\n",
         bridge->name,
         bridge->target_emotion,
         (unsigned long)s_companion_daily_rig_frame_source.composed_frame_count,
         (unsigned long)s_companion_daily_rig_frame_source.rejected_copy_count);
  return true;
#else
  return false;
#endif
}

bool Companion_Screen_EnterLowPowerIdle(void)
{
  if (s_companion_screen_presentation.mode !=
      COMP_SCREEN_PRESENTATION_EXPRESSION ||
      !Companion_Screen_StartExpression(COMP_EPAPER_EXPRESSION_SLEEPY,
                                        false,
                                        true,
                                        "low_power_idle"))
  {
    return false;
  }

  /* Stop keeps the first external-Flash sleep frame visible. It must not run
   * a timer or issue periodic e-paper refreshes merely to animate breathing. */
  comp_emote_player_stop(&s_companion_emote_player);
  s_companion_emote_player_decision_valid = false;
  if (s_companion_expression_tick_timer_created)
  {
    HW_TS_Stop(s_companion_expression_tick_timer_id);
  }
  Companion_PetPerformance_ApplyEvent(COMP_PET_PERFORMANCE_EVENT_SLEEP_ENTRY);
  printf("[screen] low_power_idle pose=sleepy animation=stopped\r\n");
  return true;
}

bool Companion_Screen_ShowDaily(void)
{
  return Companion_Screen_StartExpression(COMP_EPAPER_EXPRESSION_IDLE,
                                          false,
                                          true,
                                          "daily_navigation");
}

bool Companion_Screen_ShowDailyClean(void)
{
  bool shown;

  SCREEN_INTERACTION_TRACE("[screen] menu_boundary=exit expression=idle refresh=fast_if_baseline\r\n");
  shown = Companion_Screen_StartExpressionMode(
      COMP_EPAPER_EXPRESSION_IDLE,
      COMP_EPAPER_REFRESH_MAINTENANCE,
      true,
      "menu_exit_clean");
  if (shown)
  {
    Companion_PetPerformance_ApplyEvent(COMP_PET_PERFORMANCE_EVENT_MENU_EXIT);
    /* The screen has committed the daily surface, so release the menu
     * performance priority before accepting the next touch performance. */
    Companion_PetPerformance_ApplyExpressionSignal(
        COMP_EPAPER_EXPRESSION_SIGNAL_RECOVERY);
  }
  return shown;
}

bool Companion_Screen_DailyExpression(comp_epaper_expression_t expression,
                                      const char *reason)
{
  if (s_companion_screen_presentation.mode !=
      COMP_SCREEN_PRESENTATION_EXPRESSION)
  {
    printf("[screen-expression] daily_expression=%s result=rejected surface=menu\r\n",
           comp_epaper_expression_name(expression));
    return false;
  }
  return Companion_Screen_StartExpression(expression,
                                          false,
                                          true,
                                          reason == NULL ? "daily_expression" : reason);
}

bool Companion_Screen_DailyExpressionSignal(
    comp_epaper_expression_signal_t signal,
    const char *reason)
{
  comp_epaper_expression_decision_t decision;
  comp_epaper_expression_state_t previous_state;

  if (s_companion_screen_presentation.mode !=
      COMP_SCREEN_PRESENTATION_EXPRESSION)
  {
    printf("[screen-expression] daily_signal=%u result=rejected surface=menu\r\n",
           (unsigned)signal);
    return false;
  }
  previous_state = s_companion_expression_state;
  if (!comp_epaper_expression_state_apply_signal(
          &s_companion_expression_state, signal, &decision))
  {
    printf("[screen-expression] daily_signal=%u result=suppressed current=%s\r\n",
           (unsigned)signal,
           comp_epaper_expression_name(s_companion_expression_state.current));
    return false;
  }
  decision.reason = reason == NULL ? decision.reason : reason;
  s_companion_expression_transition_immediate = true;
  Companion_Display_EnqueueExpressionDecision(&decision, &previous_state, 0u);
  s_companion_expression_transition_immediate = false;
  Companion_PetPerformance_ApplyExpressionSignal(signal);
  SCREEN_INTERACTION_TRACE("[screen-expression] daily_signal=%u expression=%s result=requested reason=%s\r\n",
         (unsigned)signal,
         decision.name,
         decision.reason);
  return true;
}

bool Companion_Screen_DailyTap(void)
{
  return Companion_Screen_DailyTapAt(100u, 100u);
}

bool Companion_Screen_DailyTapAt(uint16_t x, uint16_t y)
{
  comp_epaper_expression_decision_t decision;
  comp_epaper_expression_state_t previous_state;
  comp_pet_attention_direction_t direction;

  if (s_companion_screen_presentation.mode !=
      COMP_SCREEN_PRESENTATION_EXPRESSION)
  {
    return false;
  }
  Companion_Display_CancelAutomaticMotion(COMP_EPAPER_MOTION_CANCEL_TOUCH);
  direction = comp_pet_attention_from_touch(x, y, 200u, 200u);
  Companion_PetBehavior_Advance();
  comp_pet_behavior_note_touch(&s_companion_pet_behavior, x, y, 200u, 200u);
  s_companion_touch_attention_clip = comp_pet_attention_clip_name(direction);
  s_companion_dynamic_touch_clip = s_companion_touch_attention_clip;
  s_companion_dynamic_touch_x = x;
  s_companion_dynamic_touch_y = y;
  s_companion_dynamic_touch_is_stroke = false;
  s_companion_expression_transition_immediate = true;
  previous_state = s_companion_expression_state;
  if (s_companion_expression_state.initialized &&
      s_companion_expression_state.current == COMP_EPAPER_EXPRESSION_HAPPY &&
      comp_epaper_expression_decide(COMP_EPAPER_EXPRESSION_SIGNAL_SPEAKER_RESULT,
                                    &decision))
  {
    /* A second touch is an intentional new eye-contact cue, not a duplicate. */
    decision.name = s_companion_touch_attention_clip;
    decision.title = "Touch response";
    decision.body = "Directional eye contact";
    decision.footer = "EXPR ATTENTION";
    decision.reason = "daily touch direction";
    s_companion_expression_state.visible_age_ms = 0u;
    Companion_Display_EnqueueExpressionDecision(&decision, &previous_state, 0u);
  }
  else
  {
    Companion_Display_EnqueueExpressionSignal(
        COMP_EPAPER_EXPRESSION_SIGNAL_SPEAKER_RESULT,
        0u);
  }
  s_companion_expression_transition_immediate = false;
  Companion_PetPerformance_ApplyEvent(COMP_PET_PERFORMANCE_EVENT_DAILY_TAP);
  SCREEN_INTERACTION_TRACE("[pet-attention] x=%u y=%u direction=%u clip=%s mood=%s valence=%d arousal=%u curiosity=%u affection=%u attachment=%u engagement=%u\r\n",
         (unsigned)x,
         (unsigned)y,
         (unsigned)direction,
         s_companion_touch_attention_clip,
         comp_pet_behavior_mood_name(comp_pet_behavior_mood(&s_companion_pet_behavior)),
         (int)s_companion_pet_behavior.valence,
         (unsigned)s_companion_pet_behavior.arousal,
         (unsigned)s_companion_pet_behavior.curiosity,
         (unsigned)s_companion_pet_behavior.affection,
         (unsigned)s_companion_pet_behavior.attachment,
         (unsigned)s_companion_pet_behavior.engagement);
  s_companion_touch_attention_clip = NULL;
  Companion_Display_ScheduleExpressionTick(HAL_GetTick());
  return true;
}

bool Companion_Screen_DailyStrokeAt(uint16_t start_x,
                                    uint16_t start_y,
                                    uint16_t end_x,
                                    uint16_t end_y,
                                    uint32_t duration_ms)
{
  comp_epaper_expression_decision_t decision;
  comp_epaper_expression_state_t previous_state;
  comp_pet_attention_direction_t attention;
  comp_pet_stroke_direction_t stroke;
  comp_pet_performance_event_t performance_event;

  if (s_companion_screen_presentation.mode !=
      COMP_SCREEN_PRESENTATION_EXPRESSION)
  {
    return false;
  }
  Companion_Display_CancelAutomaticMotion(COMP_EPAPER_MOTION_CANCEL_TOUCH);
  stroke = comp_pet_behavior_stroke_direction(start_x, start_y, end_x, end_y);
  if (stroke == COMP_PET_STROKE_NONE)
  {
    return Companion_Screen_DailyTapAt(end_x, end_y);
  }
  performance_event = COMP_PET_PERFORMANCE_EVENT_DAILY_STROKE;
  switch (stroke)
  {
  case COMP_PET_STROKE_LEFT:
    performance_event = COMP_PET_PERFORMANCE_EVENT_DAILY_SWIPE_LEFT;
    break;
  case COMP_PET_STROKE_RIGHT:
    performance_event = COMP_PET_PERFORMANCE_EVENT_DAILY_SWIPE_RIGHT;
    break;
  case COMP_PET_STROKE_UP:
    performance_event = COMP_PET_PERFORMANCE_EVENT_DAILY_SWIPE_UP;
    break;
  case COMP_PET_STROKE_DOWN:
    performance_event = COMP_PET_PERFORMANCE_EVENT_DAILY_SWIPE_DOWN;
    break;
  case COMP_PET_STROKE_NONE:
  default:
    break;
  }
  attention = comp_pet_attention_from_touch(end_x, end_y, 200u, 200u);
  Companion_PetBehavior_Advance();
  comp_pet_behavior_note_stroke(&s_companion_pet_behavior,
                                 start_x,
                                 start_y,
                                 end_x,
                                 end_y,
                                 200u,
                                 200u,
                                 duration_ms);
  s_companion_touch_attention_clip = comp_pet_attention_clip_name(attention);
  s_companion_dynamic_touch_clip = s_companion_touch_attention_clip;
  s_companion_dynamic_touch_x = end_x;
  s_companion_dynamic_touch_y = end_y;
  s_companion_dynamic_touch_is_stroke = true;
  s_companion_expression_transition_immediate = true;
  previous_state = s_companion_expression_state;
  if (s_companion_expression_state.initialized &&
      s_companion_expression_state.current == COMP_EPAPER_EXPRESSION_HAPPY &&
      comp_epaper_expression_decide(COMP_EPAPER_EXPRESSION_SIGNAL_SPEAKER_RESULT,
                                    &decision))
  {
    decision.name = s_companion_touch_attention_clip;
    decision.title = "Stroke response";
    decision.body = comp_pet_behavior_stroke_name(stroke);
    decision.footer = "EXPR STROKE";
    decision.reason = "daily stroke direction";
    s_companion_expression_state.visible_age_ms = 0u;
    Companion_Display_EnqueueExpressionDecision(&decision, &previous_state, 0u);
  }
  else
  {
    Companion_Display_EnqueueExpressionSignal(
        COMP_EPAPER_EXPRESSION_SIGNAL_SPEAKER_RESULT,
        0u);
  }
  s_companion_expression_transition_immediate = false;
  Companion_PetPerformance_ApplyEvent(performance_event);
  SCREEN_INTERACTION_TRACE("[pet-stroke] direction=%s start=%u,%u end=%u,%u duration_ms=%lu clip=%s mood=%s valence=%d arousal=%u curiosity=%u affection=%u attachment=%u engagement=%u\r\n",
         comp_pet_behavior_stroke_name(stroke),
         (unsigned)start_x,
         (unsigned)start_y,
         (unsigned)end_x,
         (unsigned)end_y,
         (unsigned long)duration_ms,
         s_companion_touch_attention_clip,
         comp_pet_behavior_mood_name(comp_pet_behavior_mood(&s_companion_pet_behavior)),
         (int)s_companion_pet_behavior.valence,
         (unsigned)s_companion_pet_behavior.arousal,
         (unsigned)s_companion_pet_behavior.curiosity,
         (unsigned)s_companion_pet_behavior.affection,
         (unsigned)s_companion_pet_behavior.attachment,
         (unsigned)s_companion_pet_behavior.engagement);
  s_companion_touch_attention_clip = NULL;
  Companion_Display_ScheduleExpressionTick(HAL_GetTick());
  return true;
}

bool Companion_Screen_IsReady(void)
{
  return s_companion_screen_ui_ready;
}

bool Companion_Screen_IsMenuVisible(void)
{
  return s_companion_screen_presentation.mode == COMP_SCREEN_PRESENTATION_MENU;
}

static void Companion_Display_EnqueueExpressionSignal(
    comp_epaper_expression_signal_t signal,
    uint32_t request_id_hint)
{
  comp_epaper_expression_decision_t decision;
  comp_epaper_expression_state_t previous_state = s_companion_expression_state;

  switch (signal)
  {
  case COMP_EPAPER_EXPRESSION_SIGNAL_RECORDING_START:
  case COMP_EPAPER_EXPRESSION_SIGNAL_RECORDING_STOP:
  case COMP_EPAPER_EXPRESSION_SIGNAL_RECORDING_CANCEL:
  case COMP_EPAPER_EXPRESSION_SIGNAL_RECORDING_FINISHED:
    Companion_Display_CancelAutomaticMotion(
        COMP_EPAPER_MOTION_CANCEL_RECORDING);
    break;
  case COMP_EPAPER_EXPRESSION_SIGNAL_LOW_BATTERY:
  case COMP_EPAPER_EXPRESSION_SIGNAL_SETTINGS_SLEEPY:
    Companion_Display_CancelAutomaticMotion(
        COMP_EPAPER_MOTION_CANCEL_LOW_POWER);
    break;
  case COMP_EPAPER_EXPRESSION_SIGNAL_ERROR:
    Companion_Display_CancelAutomaticMotion(COMP_EPAPER_MOTION_CANCEL_ERROR);
    break;
  default:
    break;
  }

  if (!comp_epaper_expression_state_apply_signal(&s_companion_expression_state,
                                                 signal,
                                                 &decision))
  {
    if (s_companion_expression_state.suppressed_duplicate_count !=
        previous_state.suppressed_duplicate_count)
    {
      Companion_Display_ScheduleExpressionTick(HAL_GetTick());
    }
    return;
  }

  Companion_PetPerformance_ApplyExpressionSignal(signal);

  if (signal == COMP_EPAPER_EXPRESSION_SIGNAL_SPEAKER_RESULT &&
      s_companion_touch_attention_clip != NULL)
  {
    decision.name = s_companion_touch_attention_clip;
    decision.title = s_companion_dynamic_touch_is_stroke ? "Stroke response" :
                                                         "Touch response";
    decision.body = s_companion_dynamic_touch_is_stroke ? "Directional stroke" :
                                                        "Directional eye contact";
    decision.footer = s_companion_dynamic_touch_is_stroke ? "EXPR STROKE" :
                                                          "EXPR ATTENTION";
    decision.reason = s_companion_dynamic_touch_is_stroke ? "daily stroke direction" :
                                                          "daily touch direction";
  }
  else if (s_companion_dynamic_touch_clip != NULL &&
           (decision.name == NULL ||
            strcmp(decision.name, s_companion_dynamic_touch_clip) != 0))
  {
    s_companion_dynamic_touch_clip = NULL;
  }

  Companion_Display_EnqueueExpressionDecision(&decision,
                                              &previous_state,
                                              request_id_hint);
}

static void Companion_Display_EnqueueExpressionEvent(uint16_t event_code,
                                                     uint8_t severity,
                                                     uint32_t request_id_hint,
                                                     uint32_t arg0,
                                                     uint32_t arg1,
                                                     uint32_t arg2,
                                                     uint32_t arg3)
{
  comp_epaper_expression_signal_t signal;
  if (comp_epaper_expression_signal_from_diag_event(event_code,
                                                   severity,
                                                   arg0,
                                                   arg1,
                                                   arg2,
                                                   arg3,
                                                   &signal))
  {
    Companion_Display_EnqueueExpressionSignal(signal, request_id_hint);
  }
}

static void Companion_Display_ApplyDeviceStatusExpressionHint(
    const companion_gatt_device_status_v1_t *status)
{
  comp_epaper_expression_signal_t signal;
  if (status == NULL)
  {
    return;
  }

  if (comp_epaper_expression_signal_from_device_status(status->active_mode,
                                                       status->fault_bitmap,
                                                       &signal))
  {
    Companion_Display_EnqueueExpressionSignal(signal, 0u);
  }
}

static void Companion_Display_ApplyBatteryExpressionHint(
    const companion_gatt_battery_charge_v1_t *status)
{
  if (status == NULL)
  {
    return;
  }

  Companion_Display_EnqueueExpressionEvent(
      COMP_DIAG_EVT_BATTERY_CHARGING_SAMPLE,
      COMP_DIAG_SEV_INFO,
      0u,
      (uint32_t)status->percent,
      (uint32_t)status->millivolts,
      (uint32_t)status->charger_present,
      (uint32_t)status->charge_state);
}

static void Companion_Display_ApplyOtaExpressionHint(
    const companion_gatt_ota_readiness_v1_t *readiness)
{
  comp_epaper_expression_signal_t signal;
  if (readiness == NULL)
  {
    return;
  }

  if (comp_epaper_expression_signal_from_ota_readiness(
          readiness->blocker_bitmap,
          &signal))
  {
    Companion_Display_EnqueueExpressionSignal(signal, 0u);
  }
}

static void Companion_Display_ApplyMeetingStatusExpressionHint(
    const companion_gatt_meeting_status_v1_t *status)
{
  comp_epaper_expression_signal_t signal;
  if (status == NULL)
  {
    return;
  }

  if (comp_epaper_expression_signal_from_meeting_status(status->state,
                                                        status->summary_state,
                                                        status->sync_state,
                                                        status->last_error,
                                                        &signal))
  {
    Companion_Display_EnqueueExpressionSignal(signal, 0u);
  }
}

static void Companion_Display_ApplySpeakerStatusExpressionHint(
    const companion_gatt_speaker_status_v1_t *status)
{
  comp_epaper_expression_signal_t signal;
  if (status == NULL)
  {
    return;
  }

  if (comp_epaper_expression_signal_from_speaker_status(status->state,
                                                        status->last_error,
                                                        &signal))
  {
    Companion_Display_EnqueueExpressionSignal(signal, 0u);
  }
}

static void Companion_Display_ApplyWakeWordStatusExpressionHint(
    const companion_gatt_wake_word_status_v1_t *status)
{
  comp_epaper_expression_signal_t signal;
  if (status == NULL)
  {
    return;
  }

  if (comp_epaper_expression_signal_from_wake_word_status(status->armed,
                                                          status->engine_state,
                                                          status->last_event,
                                                          status->last_error,
                                                          &signal))
  {
    Companion_Display_EnqueueExpressionSignal(signal, 0u);
  }
}

static bool Companion_Settings_WantsSleepy(
    const companion_gatt_settings_v1_t *settings)
{
  if (settings == NULL)
  {
    return false;
  }
  return settings->display_brightness == 0u ||
         ((settings->flags & COMPANION_SETTINGS_FLAG_QUIET_HOURS_ACTIVE) != 0u);
}

static void Companion_Display_ApplySettingsExpressionHint(
    const companion_gatt_settings_v1_t *settings)
{
  if (Companion_Settings_WantsSleepy(settings))
  {
    Companion_Display_EnqueueExpressionSignal(
        COMP_EPAPER_EXPRESSION_SIGNAL_SETTINGS_SLEEPY,
        0u);
  }
  else if (s_companion_expression_state.current == COMP_EPAPER_EXPRESSION_SLEEPY &&
           s_companion_expression_state.last_signal ==
               COMP_EPAPER_EXPRESSION_SIGNAL_SETTINGS_SLEEPY)
  {
    Companion_Display_EnqueueExpressionSignal(
        COMP_EPAPER_EXPRESSION_SIGNAL_RECOVERY,
        0u);
  }
}

static void Companion_Diag_RecordAndEnqueueExpression(uint16_t event_code,
                                                      uint8_t severity,
                                                      uint32_t request_id_hint,
                                                      uint32_t arg0,
                                                      uint32_t arg1,
                                                      uint32_t arg2,
                                                      uint32_t arg3)
{
  comp_diag_log_record_code(event_code, severity, arg0, arg1, arg2, arg3);
  Companion_Display_EnqueueExpressionEvent(event_code,
                                           severity,
                                           request_id_hint,
                                           arg0,
                                           arg1,
                                           arg2,
                                           arg3);
}

static void Companion_Gatt_HandleEvent(const companion_gatt_event_t *event,
                                       void *context)
{
  (void)context;

  if (event == NULL)
  {
    return;
  }

  APP_DBG_MSG("  Info   : Companion GATT %s event=%u len=%u\n",
              companion_gatt_char_name(event->char_id),
              (unsigned int)event->type,
              (unsigned int)event->payload_len);

  if (event->type == COMPANION_GATT_EVENT_NOTIFY_ENABLED)
  {
    Companion_Gatt_PublishCurrent(event->char_id);
    return;
  }

  if (event->type != COMPANION_GATT_EVENT_WRITE)
  {
    return;
  }

  switch (event->char_id)
  {
    case COMPANION_GATT_CHAR_E_PAPER_CARD_WRITE:
    {
      companion_gatt_card_write_v1_t request;
      companion_gatt_parse_result_t parse_result =
          companion_gatt_parse_card_write_v1(event->payload,
                                             event->payload_len,
                                             &request);
      if (parse_result == COMPANION_GATT_PARSE_OK)
      {
        uint16_t header_len = (uint16_t)sizeof(request);
        uint16_t content_len = (uint16_t)(event->payload_len - header_len);
        uint32_t content_crc32 =
            Companion_Gatt_Fnv1a(&event->payload[header_len], content_len);
        comp_epaper_display_queue_snapshot_t queue_stats;
        comp_epaper_display_queue_result_t queue_result =
            comp_epaper_display_queue_enqueue_card_write(
                &s_companion_display_queue,
                request.card_slot,
                request.display_flags,
                request.request_id,
                request.utf8_title_len,
                request.utf8_body_len,
                &event->payload[header_len],
                content_len,
                content_crc32);
        comp_epaper_display_queue_snapshot(&s_companion_display_queue,
                                           &queue_stats);

        if (queue_result == COMP_EPAPER_DISPLAY_QUEUE_OK)
        {
          comp_diag_log_record_code(COMP_DIAG_EVT_EPAPER_RENDER_REQUEST,
                                    COMP_DIAG_SEV_INFO,
                                    request.request_id,
                                    content_crc32,
                                    (uint32_t)queue_stats.pending_count,
                                    (uint32_t)request.display_flags);
          Companion_Gatt_PublishCardStatus(
            request.card_slot,
            request.request_id,
            (uint8_t)COMP_EPAPER_RENDER_STATE_ACCEPTED,
            0u,
            content_crc32);
          UTIL_SEQ_SetTask(1 << CFG_TASK_COMPANION_DISPLAY_ID, CFG_SCH_PRIO_0);
        }
        else
        {
          uint8_t status_error =
              comp_epaper_display_queue_status_error(queue_result);
          uint8_t render_state =
              queue_result == COMP_EPAPER_DISPLAY_QUEUE_FULL
                  ? (uint8_t)COMP_EPAPER_RENDER_STATE_BUSY
                  : (uint8_t)COMP_EPAPER_RENDER_STATE_FAILED;
          comp_diag_log_record_code(COMP_DIAG_EVT_EPAPER_UPDATE_RESULT,
                                    queue_result == COMP_EPAPER_DISPLAY_QUEUE_FULL
                                        ? COMP_DIAG_SEV_WARN
                                        : COMP_DIAG_SEV_ERROR,
                                    request.request_id,
                                    content_crc32,
                                    queue_stats.dropped_count,
                                    status_error);
          Companion_Gatt_PublishCardStatus(request.card_slot,
                                           request.request_id,
                                           render_state,
                                           status_error,
                                           content_crc32);
        }
      }
      else
      {
        Companion_Gatt_PublishCardStatus(0u,
                                         0u,
                                         (uint8_t)COMP_EPAPER_RENDER_STATE_FAILED,
                                         (uint8_t)parse_result,
                                         0u);
      }
      break;
    }

    case COMPANION_GATT_CHAR_RECORDING_CONTROL:
    {
      companion_gatt_recording_control_v1_t request;
      if (companion_gatt_parse_recording_control_v1(event->payload,
                                                    event->payload_len,
                                                    &request) ==
          COMPANION_GATT_PARSE_OK)
      {
        bool accepted = Companion_RecordingFlash_HandleControl(request.command,
                                                               request.max_seconds);
        Companion_Gatt_PublishRecordingControlEcho(&request, accepted);
        if (!accepted)
        {
          Companion_Display_EnqueueExpressionEvent(
              COMP_DIAG_EVT_RECORDING_FSM_REJECTED,
              COMP_DIAG_SEV_WARN,
              request.request_id,
              request.command,
              request.max_seconds,
              0u,
              0u);
        }
        else if (request.command == 1u)
        {
          Companion_Display_EnqueueExpressionEvent(
              COMP_DIAG_EVT_RECORDING_FSM_START_REQUEST,
              COMP_DIAG_SEV_INFO,
              request.request_id,
              request.command,
              request.max_seconds,
              0u,
              0u);
        }
        else if (request.command == 2u)
        {
          Companion_Display_EnqueueExpressionEvent(
              COMP_DIAG_EVT_RECORDING_FSM_STOP_REQUEST,
              COMP_DIAG_SEV_INFO,
              request.request_id,
              request.command,
              request.max_seconds,
              0u,
              0u);
        }
        else if (request.command == 3u)
        {
          Companion_Display_EnqueueExpressionEvent(
              COMP_DIAG_EVT_RECORDING_FSM_CANCEL_REQUEST,
              COMP_DIAG_SEV_INFO,
              request.request_id,
              request.command,
              request.max_seconds,
              0u,
              0u);
        }
      }
      Companion_Gatt_PublishRecordingList();
      break;
    }

    case COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL:
    {
      companion_gatt_recording_chunk_pull_v1_t request;
      if (companion_gatt_parse_recording_chunk_pull_v1(event->payload,
                                                       event->payload_len,
                                                       &request) ==
          COMPANION_GATT_PARSE_OK)
      {
        Companion_Gatt_PublishRecordingChunk(&request);
      }
      break;
    }

    case COMPANION_GATT_CHAR_SETTINGS:
    {
      companion_gatt_settings_v1_t request;
      if (companion_gatt_parse_settings_v1(event->payload,
                                           event->payload_len,
                                           &request) ==
          COMPANION_GATT_PARSE_OK)
      {
        uint32_t acknowledged_revision = 0u;
        bool replayed = false;
        uint32_t now_ms = HAL_GetTick();
        s_platform_pending_settings = &request;
        companion_product_identity_t identity;
        if (companion_product_identity_derive(
                "companion.settings", 0u, &request, sizeof(request), &identity) &&
            companion_product_entry_settings(
                &s_platform_product_entry, identity.operation_id, identity.idempotency_key,
                now_ms, now_ms + 1000u, s_platform_settings_transport.revision,
                &request, &acknowledged_revision, &replayed))
        {
          (void)acknowledged_revision;
        }
        s_platform_pending_settings = NULL;
        Companion_Gatt_PublishSettings();
        Companion_Display_ApplySettingsExpressionHint(&s_companion_gatt_settings);
      }
      break;
    }

    case COMPANION_GATT_CHAR_BLE_NAME_CONFIG:
    {
      companion_gatt_ble_name_config_v1_t request;
      if (companion_gatt_parse_ble_name_config_v1(event->payload,
                                                  event->payload_len,
                                                  &request) ==
          COMPANION_GATT_PARSE_OK)
      {
#if COMPANION_BLE_NAME_PLATFORM_GATE
        const uint32_t idempotency_key = request.request_id ^ 0xB1E5A9C3u;
        (void)companion_ble_name_product_entry(
            &s_companion_ble_name_state, event->payload, event->payload_len,
            idempotency_key, Companion_BleName_TargetRestart, NULL);
        Companion_BleName_SyncFeatureState();
#else
        (void)companion_v1_apply_ble_name_config(&s_companion_v1_features,
                                                 &request);
#endif
      }
      Companion_Gatt_PublishBleNameConfig();
      break;
    }

    case COMPANION_GATT_CHAR_MEETING_CONTROL:
    {
      companion_gatt_meeting_control_v1_t request;
      if (companion_gatt_parse_meeting_control_v1(event->payload,
                                                  event->payload_len,
                                                  &request) ==
          COMPANION_GATT_PARSE_OK)
      {
        s_platform_pending_meeting = &request;
        s_platform_pending_now_ms = HAL_GetTick();
        s_platform_invoke_result = COMPANION_V1_RESULT_UNSUPPORTED_COMMAND;
        bool replayed = false;
        companion_product_identity_t identity;
        bool invoked = companion_product_identity_derive(
            "companion.meeting", request.request_id, &request, sizeof(request), &identity) &&
            companion_product_entry_meeting(
            &s_platform_product_entry, identity.operation_id, identity.idempotency_key,
            s_platform_pending_now_ms, s_platform_pending_now_ms + 1000u,
            &request, &replayed);
        s_platform_pending_meeting = NULL;
        if (replayed && invoked)
        {
          s_platform_invoke_result = COMPANION_V1_RESULT_OK;
        }
        companion_v1_result_t result = invoked
            ? s_platform_invoke_result
            : COMPANION_V1_RESULT_UNSUPPORTED_COMMAND;
        if (result != COMPANION_V1_RESULT_OK)
        {
          Companion_Diag_RecordAndEnqueueExpression(COMP_DIAG_EVT_MEETING_REJECTED,
                                                    COMP_DIAG_SEV_WARN,
                                                    request.request_id,
                                                    request.command,
                                                    request.max_seconds,
                                                    (uint32_t)result,
                                                    0u);
        }
        else if (request.command == 1u)
        {
          Companion_Diag_RecordAndEnqueueExpression(COMP_DIAG_EVT_MEETING_START,
                                                    COMP_DIAG_SEV_INFO,
                                                    request.request_id,
                                                    request.request_id,
                                                    request.max_seconds,
                                                    request.flags,
                                                    0u);
        }
        else if (request.command == 2u)
        {
          Companion_Diag_RecordAndEnqueueExpression(COMP_DIAG_EVT_MEETING_FINALIZE,
                                                    COMP_DIAG_SEV_INFO,
                                                    request.request_id,
                                                    request.request_id,
                                                    request.max_seconds,
                                                    request.flags,
                                                    0u);
        }
        else if (request.command == 3u)
        {
          Companion_Display_EnqueueExpressionSignal(
              COMP_EPAPER_EXPRESSION_SIGNAL_RECOVERY,
              request.request_id);
        }
      }
      Companion_Gatt_PublishMeetingStatus(true);
      break;
    }

    case COMPANION_GATT_CHAR_SPEAKER_CONTROL:
    {
      companion_gatt_speaker_control_v1_t request;
      if (companion_gatt_parse_speaker_control_v1(event->payload,
                                                  event->payload_len,
                                                  &request) ==
          COMPANION_GATT_PARSE_OK)
      {
        companion_v1_result_t result =
            companion_v1_apply_speaker_control(&s_companion_v1_features,
                                               &request,
                                               HAL_GetTick());
        Companion_Diag_RecordAndEnqueueExpression(
            result == COMPANION_V1_RESULT_OK
                ? COMP_DIAG_EVT_SPEAKER_PROMPT
                : COMP_DIAG_EVT_SPEAKER_REJECTED,
            result == COMPANION_V1_RESULT_OK
                ? COMP_DIAG_SEV_INFO
                : COMP_DIAG_SEV_WARN,
            request.request_id,
            request.prompt_id,
            request.volume_percent,
            (uint32_t)result,
            0u);
      }
      Companion_Gatt_PublishSpeakerStatus(true);
      break;
    }

    case COMPANION_GATT_CHAR_WAKE_WORD_CONTROL:
    {
      companion_gatt_wake_word_control_v1_t request;
      if (companion_gatt_parse_wake_word_control_v1(event->payload,
                                                    event->payload_len,
                                                    &request) ==
          COMPANION_GATT_PARSE_OK)
      {
        companion_v1_result_t result =
            companion_v1_apply_wake_word_control(&s_companion_v1_features,
                                                 &request,
                                                 HAL_GetTick());
        if (result != COMPANION_V1_RESULT_OK)
        {
          Companion_Diag_RecordAndEnqueueExpression(COMP_DIAG_EVT_WAKE_WORD_REJECTED,
                                                    COMP_DIAG_SEV_WARN,
                                                    request.request_id,
                                                    request.command,
                                                    request.sensitivity,
                                                    (uint32_t)result,
                                                    0u);
        }
        else if (request.command == 1u)
        {
          Companion_Diag_RecordAndEnqueueExpression(COMP_DIAG_EVT_WAKE_WORD_ARMED,
                                                    COMP_DIAG_SEV_INFO,
                                                    request.request_id,
                                                    request.sensitivity,
                                                    request.model_id,
                                                    request.flags,
                                                    0u);
        }
        else if (request.command == 2u)
        {
          Companion_Diag_RecordAndEnqueueExpression(COMP_DIAG_EVT_WAKE_WORD_DISABLED,
                                                    COMP_DIAG_SEV_INFO,
                                                    request.request_id,
                                                    request.sensitivity,
                                                    request.model_id,
                                                    request.flags,
                                                    0u);
        }
        else if (request.command == 3u)
        {
          Companion_Diag_RecordAndEnqueueExpression(COMP_DIAG_EVT_WAKE_WORD_DETECTED,
                                                    COMP_DIAG_SEV_INFO,
                                                    request.request_id,
                                                    request.sensitivity,
                                                    request.model_id,
                                                    request.flags,
                                                    0u);
        }
      }
      Companion_Gatt_PublishWakeWordStatus(true);
      break;
    }

    case COMPANION_GATT_CHAR_DIAGNOSTICS_LOG_PULL:
    {
      companion_gatt_diag_log_pull_v1_t request;
      if (companion_gatt_parse_diag_log_pull_v1(event->payload,
                                                event->payload_len,
                                                &request) ==
          COMPANION_GATT_PARSE_OK)
      {
        Companion_Gatt_PublishDiagLogResponse(&request);
      }
      break;
    }

    case COMPANION_GATT_CHAR_DELETE_PRIVACY:
    {
      companion_gatt_delete_privacy_v1_t request;
      if (companion_gatt_parse_delete_privacy_v1(event->payload,
                                                 event->payload_len,
                                                 &request) ==
          COMPANION_GATT_PARSE_OK)
      {
        bool accepted = Companion_RecordingFlash_Delete(request.operation,
                                                        request.recording_id,
                                                        request.validated_total_length,
                                                        request.validated_sha256);
        Companion_Gatt_PublishDeletePrivacyStatus(&request, accepted);
        Companion_Gatt_PublishRecordingList();
      }
      break;
    }

    default:
      break;
  }
}

static void Companion_Gatt_PublishInitialState(void)
{
  Companion_Gatt_PublishDeviceStatus(false);
  Companion_Gatt_PublishBatteryCharge(false);
  Companion_Gatt_PublishCardStatus(0u, 0u, 0u, 0u, 0u);
  Companion_Gatt_PublishRecordingList();
  Companion_Gatt_PublishSettings();
  Companion_Gatt_PublishBleNameConfig();
  Companion_Gatt_PublishMeetingStatus(false);
  Companion_Gatt_PublishImuStatus();
  Companion_Gatt_PublishSpeakerStatus(false);
  Companion_Gatt_PublishWakeWordStatus(false);
  Companion_Gatt_PublishOtaReadiness(false);
}

static void Companion_Gatt_PublishCurrent(companion_gatt_char_id_t char_id)
{
  switch (char_id)
  {
    case COMPANION_GATT_CHAR_DEVICE_STATUS:
      Companion_Gatt_PublishDeviceStatus(true);
      break;

    case COMPANION_GATT_CHAR_BATTERY_CHARGE:
      Companion_Gatt_PublishBatteryCharge(true);
      break;

    case COMPANION_GATT_CHAR_E_PAPER_CARD_STATUS:
      (void)companion_gatt_stm32wb_publish(
          COMPANION_GATT_CHAR_E_PAPER_CARD_STATUS,
          (const uint8_t *)&s_companion_gatt_card_status,
          (uint16_t)sizeof(s_companion_gatt_card_status));
      break;

    case COMPANION_GATT_CHAR_RECORDING_LIST:
      Companion_Gatt_PublishRecordingList();
      break;

    case COMPANION_GATT_CHAR_SETTINGS:
      Companion_Gatt_PublishSettings();
      break;

    case COMPANION_GATT_CHAR_BLE_NAME_CONFIG:
      Companion_Gatt_PublishBleNameConfig();
      break;

    case COMPANION_GATT_CHAR_MEETING_STATUS:
      Companion_Gatt_PublishMeetingStatus(true);
      break;

    case COMPANION_GATT_CHAR_IMU_STATUS:
      Companion_Gatt_PublishImuStatus();
      break;

    case COMPANION_GATT_CHAR_SPEAKER_STATUS:
      Companion_Gatt_PublishSpeakerStatus(true);
      break;

    case COMPANION_GATT_CHAR_WAKE_WORD_STATUS:
      Companion_Gatt_PublishWakeWordStatus(true);
      break;

    case COMPANION_GATT_CHAR_OTA_READINESS:
      Companion_Gatt_PublishOtaReadiness(true);
      break;

    default:
      break;
  }
}

static void Companion_Gatt_PublishDeviceStatus(bool apply_expression_hint)
{
  companion_gatt_device_status_v1_t status = {
      .schema_version = 1u,
      .active_mode = s_companion_audio_stream.notify_enabled ? 1u :
                     (s_companion_ble_connected ? 2u : 0u),
      .fault_bitmap = 0u,
      .firmware_version = 0x00010001u,
      .build_id = 0x0DB7E50Du,
      .board_id = 0xB55A0001u,
      .uptime_ms = HAL_GetTick(),
  };
  uint32_t capability_revision = 0u;
  uint64_t capability_mask = 0u;
  if (!companion_platform_device_control_capabilities_event(
          status.uptime_ms, 1u, 0xC001u,
          &capability_revision, &capability_mask))
  {
    status.fault_bitmap |= 0x0001u;
  }

  (void)companion_gatt_stm32wb_publish(COMPANION_GATT_CHAR_DEVICE_STATUS,
                                       (const uint8_t *)&status,
                                       (uint16_t)sizeof(status));
  if (apply_expression_hint)
  {
    Companion_Display_ApplyDeviceStatusExpressionHint(&status);
  }
}

static void Companion_Gatt_PublishBatteryCharge(bool apply_expression_hint)
{
  companion_gatt_battery_charge_v1_t status = {
      .schema_version = 1u,
      .percent = 100u,
      .charge_state = 1u,
      .charger_present = 1u,
      .millivolts = 5000u,
      .temperature_c_x10 = 250,
  };

  (void)companion_gatt_stm32wb_publish(COMPANION_GATT_CHAR_BATTERY_CHARGE,
                                       (const uint8_t *)&status,
                                       (uint16_t)sizeof(status));
  if (apply_expression_hint)
  {
    Companion_Display_ApplyBatteryExpressionHint(&status);
  }
}

static void Companion_Gatt_PublishCardStatus(uint8_t card_slot,
                                             uint32_t request_id,
                                             uint8_t render_state,
                                             uint8_t last_error,
                                             uint32_t content_crc32)
{
  s_companion_gatt_card_status.schema_version = 1u;
  s_companion_gatt_card_status.card_slot = card_slot;
  s_companion_gatt_card_status.render_state = render_state;
  s_companion_gatt_card_status.last_error = last_error;
  s_companion_gatt_card_status.request_id = request_id;
  s_companion_gatt_card_status.content_crc32 = content_crc32;
  s_companion_gatt_card_status.refresh_count = ++s_companion_gatt_card_refresh_count;

  (void)companion_gatt_stm32wb_publish(COMPANION_GATT_CHAR_E_PAPER_CARD_STATUS,
                                       (const uint8_t *)&s_companion_gatt_card_status,
                                       (uint16_t)sizeof(s_companion_gatt_card_status));
}

static void Companion_Gatt_PublishRecordingControlEcho(
    const companion_gatt_recording_control_v1_t *request,
    bool accepted)
{
  if (request == NULL)
  {
    return;
  }

  companion_gatt_recording_control_v1_t response = *request;
  response.schema_version = 1u;
  if (!accepted)
  {
    response.privacy_flags |= COMPANION_GATT_RECORDING_FLAG_ERROR;
  }
  (void)companion_gatt_stm32wb_publish(COMPANION_GATT_CHAR_RECORDING_CONTROL,
                                       (const uint8_t *)&response,
                                       (uint16_t)sizeof(response));
}

void Companion_Gatt_PublishRecordingList(void)
{
  companion_recording_flash_metadata_t metadata;
  bool has_recording = Companion_RecordingFlash_GetMetadata(&metadata);
  uint8_t payload[sizeof(companion_gatt_recording_list_v1_t) +
                  sizeof(Companion_Gatt_RecordingListEntryV1_t)];
  companion_gatt_recording_list_v1_t list = {
      .schema_version = 1u,
      .count = has_recording ? 1u : 0u,
      .entry_bytes = has_recording
          ? (uint16_t)sizeof(Companion_Gatt_RecordingListEntryV1_t)
          : 0u,
  };
  memcpy(payload, &list, sizeof(list));

  uint16_t payload_len = (uint16_t)sizeof(list);
  if (has_recording)
  {
    Companion_Gatt_RecordingListEntryV1_t entry;
    memset(&entry, 0, sizeof(entry));
    entry.recording_id = metadata.recording_id;
    entry.started_unix_s = metadata.started_unix_s;
    entry.duration_ms = metadata.duration_ms;
    entry.codec = metadata.codec;
    entry.sync_state = metadata.sync_state;
    entry.source_mode = metadata.source_mode;
    entry.total_length = metadata.total_length;
    memcpy(entry.sha256_prefix, metadata.sha256, sizeof(entry.sha256_prefix));
    entry.content_crc32 = metadata.content_crc32;
    memcpy(&payload[payload_len], &entry, sizeof(entry));
    payload_len = (uint16_t)(payload_len + sizeof(entry));
  }
  (void)companion_gatt_stm32wb_publish(COMPANION_GATT_CHAR_RECORDING_LIST,
                                       payload,
                                       payload_len);
}

static void Companion_Gatt_PublishRecordingChunk(
    const companion_gatt_recording_chunk_pull_v1_t *request)
{
  if (request == NULL)
  {
    return;
  }

  uint8_t payload[COMPANION_GATT_MAX_PAYLOAD_BYTES];
  Companion_Gatt_RecordingChunkHeaderV1_t header;
  memset(&header, 0, sizeof(header));
  uint16_t payload_capacity =
      (uint16_t)COMPANION_GATT_RECORDING_CHUNK_PAYLOAD_MAX;
  uint16_t requested_length = request->requested_length;
  if (requested_length > payload_capacity)
  {
    requested_length = payload_capacity;
  }

  companion_recording_flash_chunk_t chunk;
  bool ok = Companion_RecordingFlash_ReadChunk(request->recording_id,
                                               request->byte_offset,
                                               requested_length,
                                               &payload[sizeof(header)],
                                               payload_capacity,
                                               &chunk);
  header.schema_version = 1u;
  if (ok)
  {
    header.flags = chunk.final_packet ? COMPANION_GATT_RECORDING_FLAG_FINAL : 0u;
    header.payload_length = chunk.payload_length;
    header.recording_id = chunk.recording_id;
    header.packet_sequence = chunk.packet_sequence;
    header.byte_offset = chunk.byte_offset;
    header.total_length = chunk.total_length;
    header.packet_crc32 = chunk.packet_crc32;
    memcpy(header.final_sha256, chunk.final_sha256, sizeof(header.final_sha256));
  }
  else
  {
    header.flags = COMPANION_GATT_RECORDING_FLAG_ERROR;
    header.payload_length = 0u;
    header.recording_id = request->recording_id;
    header.packet_sequence = chunk.packet_sequence;
    header.byte_offset = request->byte_offset;
    header.total_length = chunk.total_length;
    header.packet_crc32 = chunk.error_code;
  }

  memcpy(payload, &header, sizeof(header));
  (void)companion_gatt_stm32wb_publish(COMPANION_GATT_CHAR_RECORDING_CHUNK_PULL,
                                       payload,
                                       (uint16_t)(sizeof(header) + header.payload_length));
}

static void Companion_Gatt_PublishSettings(void)
{
  s_companion_gatt_settings.schema_version = 1u;
  (void)companion_gatt_stm32wb_publish(COMPANION_GATT_CHAR_SETTINGS,
                                       (const uint8_t *)&s_companion_gatt_settings,
                                       (uint16_t)sizeof(s_companion_gatt_settings));
}

static void Companion_Gatt_PublishBleNameConfig(void)
{
  companion_gatt_ble_name_config_v1_t status;
  companion_v1_get_ble_name_config(&s_companion_v1_features, &status);
  (void)companion_gatt_stm32wb_publish(COMPANION_GATT_CHAR_BLE_NAME_CONFIG,
                                       (const uint8_t *)&status,
                                       (uint16_t)sizeof(status));
}

static void Companion_Gatt_PublishMeetingStatus(bool apply_expression_hint)
{
  companion_gatt_meeting_status_v1_t status;
  companion_v1_get_meeting_status(&s_companion_v1_features, &status);
  (void)companion_gatt_stm32wb_publish(COMPANION_GATT_CHAR_MEETING_STATUS,
                                       (const uint8_t *)&status,
                                       (uint16_t)sizeof(status));
  if (apply_expression_hint)
  {
    Companion_Display_ApplyMeetingStatusExpressionHint(&status);
  }
}

static void Companion_Gatt_PublishImuStatus(void)
{
  companion_gatt_imu_status_v1_t status;
  companion_v1_get_imu_status(&s_companion_v1_features, &status);
  status.sample_timestamp_ms = HAL_GetTick();
  (void)companion_gatt_stm32wb_publish(COMPANION_GATT_CHAR_IMU_STATUS,
                                       (const uint8_t *)&status,
                                       (uint16_t)sizeof(status));
}

static void Companion_Gatt_PublishSpeakerStatus(bool apply_expression_hint)
{
  companion_gatt_speaker_status_v1_t status;
  companion_v1_get_speaker_status(&s_companion_v1_features, &status);
  (void)companion_gatt_stm32wb_publish(COMPANION_GATT_CHAR_SPEAKER_STATUS,
                                       (const uint8_t *)&status,
                                       (uint16_t)sizeof(status));
  if (apply_expression_hint)
  {
    Companion_Display_ApplySpeakerStatusExpressionHint(&status);
  }
}

static void Companion_Gatt_PublishWakeWordStatus(bool apply_expression_hint)
{
  companion_gatt_wake_word_status_v1_t status;
  companion_v1_get_wake_word_status(&s_companion_v1_features, &status);
  (void)companion_gatt_stm32wb_publish(COMPANION_GATT_CHAR_WAKE_WORD_STATUS,
                                       (const uint8_t *)&status,
                                       (uint16_t)sizeof(status));
  if (apply_expression_hint)
  {
    Companion_Display_ApplyWakeWordStatusExpressionHint(&status);
  }
}

typedef struct
{
  comp_diag_log_export_request_t request;
  uint8_t packet[COMPANION_GATT_MAX_PAYLOAD_BYTES];
  size_t packet_bytes;
  uint16_t available_events;
  bool stopped;
} Companion_PlatformDiagExport_t;

static bool Companion_PlatformDiag_Count(void *context, uint16_t *count)
{
  Companion_PlatformDiagExport_t *export_context =
      (Companion_PlatformDiagExport_t *)context;
  comp_diag_log_export_packet_t response;
  size_t response_bytes = 0u;
  if (export_context == NULL || count == NULL ||
      !comp_diag_log_export_build(&export_context->request, &response,
                                  &response_bytes))
  {
    return false;
  }
  export_context->available_events = response.total_available;
  *count = response.total_available;
  return true;
}

static bool Companion_PlatformDiag_Start(void *context)
{
  return context != NULL;
}

static bool Companion_PlatformDiag_Read(void *context, uint32_t offset,
                                        uint8_t *packet, size_t capacity,
                                        size_t *packet_bytes)
{
  Companion_PlatformDiagExport_t *export_context =
      (Companion_PlatformDiagExport_t *)context;
  comp_diag_log_export_packet_t response;
  size_t response_bytes = 0u;
  if (export_context == NULL || packet == NULL || packet_bytes == NULL)
  {
    return false;
  }
  export_context->request.cursor = offset;
  if (!comp_diag_log_export_build(&export_context->request, &response,
                                  &response_bytes) ||
      response_bytes > COMPANION_GATT_MAX_PAYLOAD_BYTES)
  {
    return false;
  }
  bool encoded = companion_platform_diag_encode_chunk(
      offset, response.event_count, (const uint8_t *)response.events,
      (size_t)response.event_count * sizeof(response.events[0]), packet,
      capacity, packet_bytes);
  if (encoded)
  {
    export_context->packet_bytes = *packet_bytes;
    memcpy(export_context->packet, packet, *packet_bytes);
  }
  return encoded;
}

static bool Companion_PlatformDiag_Stop(void *context)
{
  Companion_PlatformDiagExport_t *export_context =
      (Companion_PlatformDiagExport_t *)context;
  if (export_context == NULL) return false;
  export_context->stopped = true;
  return true;
}

static void Companion_Gatt_PublishDiagLogResponse(
    const companion_gatt_diag_log_pull_v1_t *request)
{
  Companion_PlatformDiagExport_t export_context;
  companion_diag_transport_t transport;
  companion_diag_result_t result;

  if (request == NULL)
  {
    return;
  }

  comp_diag_log_record_code(COMP_DIAG_EVT_GATT_LOG_EXPORT_REQUEST,
                            COMP_DIAG_SEV_INFO,
                            request->cursor,
                            request->max_events,
                            request->max_bytes,
                            ((uint32_t)request->severity_mask << 8u) |
                                request->source_mask);

  memset(&export_context, 0, sizeof(export_context));
  export_context.request.cursor = request->cursor;
  export_context.request.source_mask = request->source_mask;
  export_context.request.severity_mask = request->severity_mask;
  export_context.request.max_events = request->max_events;
  export_context.request.max_bytes = request->max_bytes;
  transport.context = &export_context;
  transport.count = Companion_PlatformDiag_Count;
  transport.start = Companion_PlatformDiag_Start;
  transport.read = Companion_PlatformDiag_Read;
  transport.stop = Companion_PlatformDiag_Stop;
  if (!companion_diag_log_pull(&transport, &result) ||
      !export_context.stopped || export_context.packet_bytes == 0u)
  {
    return;
  }
  (void)companion_gatt_stm32wb_publish(COMPANION_GATT_CHAR_DIAGNOSTICS_LOG_PULL,
                                       export_context.packet,
                                       (uint16_t)export_context.packet_bytes);
}

static void Companion_Gatt_PublishDeletePrivacyStatus(
    const companion_gatt_delete_privacy_v1_t *request,
    bool accepted)
{
  if (request == NULL)
  {
    return;
  }

  companion_gatt_delete_privacy_v1_t response = *request;
  response.schema_version = 1u;
  if (accepted)
  {
    response.flags &= (uint16_t)~0x0001u;
  }
  else
  {
    response.flags |= 0x0001u;
  }
  (void)companion_gatt_stm32wb_publish(COMPANION_GATT_CHAR_DELETE_PRIVACY,
                                       (const uint8_t *)&response,
                                       (uint16_t)sizeof(response));
}

static void Companion_Gatt_PublishOtaReadiness(bool apply_expression_hint)
{
  uint32_t image_size = 0u;
  uint32_t partition_size = 0u;
  bool pending_verify = false;
  bool post_update_self_check = false;
  bool candidate_available = Companion_Ota_V1_ReadCandidate(
      &image_size, &partition_size, &pending_verify, &post_update_self_check);
  companion_gatt_ota_readiness_v1_t readiness = {
      .schema_version = 1u,
      .ready_state = 0u,
      .boot_slot = 0u,
      .battery_percent = 0u,
      .minimum_required_mv = 3700u,
      .blocker_bitmap = 0x0010u,
      .manifest_version = 2u,
      .image_size = image_size,
  };

  companion_ota_admission_result_t ota_admission =
      companion_platform_ota_readiness_event(false,
                                              s_companion_audio_stream.session_active,
                                              false, readiness.battery_percent,
                                              candidate_available, image_size,
                                              partition_size, pending_verify,
                                              post_update_self_check);
  if (ota_admission.accepted)
  {
    readiness.ready_state = 1u;
    readiness.blocker_bitmap = 0u;
  }
  else
  {
    readiness.blocker_bitmap = (uint16_t)(1u << (uint8_t)ota_admission.blocker);
  }

  (void)companion_gatt_stm32wb_publish(COMPANION_GATT_CHAR_OTA_READINESS,
                                       (const uint8_t *)&readiness,
                                       (uint16_t)sizeof(readiness));
  if (apply_expression_hint)
  {
    Companion_Display_ApplyOtaExpressionHint(&readiness);
  }
}

static uint32_t Companion_Gatt_Fnv1a(const uint8_t *data, uint16_t length)
{
  uint32_t hash = 2166136261u;
  for (uint16_t i = 0u; i < length; ++i)
  {
    hash ^= data[i];
    hash *= 16777619u;
  }
  return hash;
}

static void Companion_Audio_UpdateDebugStatus(void)
{
  char readiness[COMP_AUDIO_STREAM_STM32WB_READINESS_VALUE_BYTES];
  int written = snprintf(
      readiness,
      sizeof(readiness),
      "ready:listener_vka1 app=companion n=%u t=%u r=%u ss=%lu lc=%u cs=%u",
      s_companion_audio_stream.notify_enabled ? 1u : 0u,
      comp_audio_stream_is_type_link_ready(&s_companion_audio_stream) ? 1u : 0u,
      comp_audio_stream_is_ready(&s_companion_audio_stream) ? 1u : 0u,
      (unsigned long)s_companion_audio_session_start_count,
      (unsigned int)s_companion_audio_last_control,
      (unsigned int)s_companion_audio_last_control_status);

  if (written <= 0)
  {
    return;
  }

  uint8_t length = (uint8_t)written;
  if ((size_t)written >= sizeof(readiness))
  {
    length = (uint8_t)(sizeof(readiness) - 1u);
  }
  (void)comp_audio_stream_stm32wb_update_readiness((const uint8_t *)readiness,
                                                   length);
}

static void Companion_Audio_Control(void *context,
                                    comp_audio_control_t control,
                                    const uint8_t *data,
                                    size_t length)
{
  (void)context;

  APP_DBG_MSG("  Info   : VKA1 companion control %s\n",
              comp_audio_stream_control_name(control));
  s_companion_audio_last_control = control;
  Companion_App_HandleBleControl(control, data, length);
}

bool Companion_BleAudio_IsReady(void)
{
  return comp_audio_stream_is_ready(&s_companion_audio_stream);
}

bool Companion_BleAudio_IsSessionActive(void)
{
  return s_companion_audio_stream.session_active;
}

uint32_t Companion_BleAudio_NextSessionId(void)
{
  return s_companion_audio_next_session_id++;
}

comp_audio_stream_status_t Companion_BleAudio_SendSessionStart(uint32_t session_id)
{
  comp_audio_stream_status_t status =
      comp_audio_stream_send_session_start(&s_companion_audio_stream, session_id);
  s_companion_audio_session_start_count++;
  s_companion_audio_last_session_start_status = status;
  Companion_Audio_UpdateDebugStatus();
  return status;
}

comp_audio_stream_status_t Companion_BleAudio_SendPcmBytes(const uint8_t *pcm,
                                                           uint16_t pcm_bytes)
{
  return comp_audio_stream_send_session_audio(&s_companion_audio_stream,
                                              pcm,
                                              pcm_bytes);
}

comp_audio_stream_status_t Companion_BleAudio_SendPcmFrame(const uint8_t *pcm,
                                                           uint16_t payload_bytes,
                                                           uint16_t packet_pcm_bytes)
{
  return comp_audio_stream_send_session_audio_frame(&s_companion_audio_stream,
                                                    pcm,
                                                    payload_bytes,
                                                    packet_pcm_bytes);
}

comp_audio_stream_status_t Companion_BleAudio_SendSessionStop(void)
{
  return comp_audio_stream_send_session_stop(&s_companion_audio_stream);
}

comp_audio_stream_status_t Companion_BleAudio_SendSessionCancel(void)
{
  return comp_audio_stream_send_session_cancel(&s_companion_audio_stream);
}

comp_audio_stream_status_t Companion_BleAudio_SendSessionError(comp_audio_session_error_t error_code)
{
  return comp_audio_stream_send_session_error(&s_companion_audio_stream, error_code);
}

void Companion_BleAudio_RequestActiveLink(const char *reason)
{
  const char *request_reason = reason != NULL ? reason : "active_audio";
  (void)Companion_Ble_RequestConnectionParams(request_reason,
                                             COMPANION_BLE_LINK_ACTIVE_INTERVAL_MIN,
                                             COMPANION_BLE_LINK_ACTIVE_INTERVAL_MAX,
                                             COMPANION_BLE_LINK_ACTIVE_LATENCY,
                                             COMPANION_BLE_LINK_ACTIVE_TIMEOUT,
                                             COMPANION_BLE_LINK_MODE_ACTIVE_AUDIO);
  (void)Companion_Ble_RequestPreferred2MPhy(request_reason);
}

void Companion_BleAudio_RequestIdleLink(const char *reason)
{
  Companion_Ble_RequestConnectionParams(reason != NULL ? reason : "idle",
                                       COMPANION_BLE_LINK_IDLE_INTERVAL_MIN,
                                       COMPANION_BLE_LINK_IDLE_INTERVAL_MAX,
                                       COMPANION_BLE_LINK_IDLE_LATENCY,
                                       COMPANION_BLE_LINK_IDLE_TIMEOUT,
                                       COMPANION_BLE_LINK_MODE_IDLE);
}

void comp_audio_stream_stm32wb_app_notification(
    const comp_audio_stream_stm32wb_notification_t *notification)
{
  if (notification == NULL)
  {
    return;
  }

  switch (notification->event)
  {
    case COMP_AUDIO_STREAM_STM32WB_NOTIFY_ENABLED:
      s_companion_audio_notify_enabled_count++;
      Companion_Audio_UpdateDebugStatus();
      APP_DBG_MSG("  Info   : VKA1 notify enabled\n");
      Companion_App_HandleBleLinkReadyChanged(Companion_BleAudio_IsReady());
      break;

    case COMP_AUDIO_STREAM_STM32WB_NOTIFY_DISABLED:
      s_companion_audio_notify_disabled_count++;
      Companion_Audio_UpdateDebugStatus();
      APP_DBG_MSG("  Info   : VKA1 notify disabled\n");
      Companion_App_HandleBleLinkReadyChanged(false);
      break;

    case COMP_AUDIO_STREAM_STM32WB_CONTROL_WRITE:
      s_companion_audio_control_write_count++;
      s_companion_audio_last_control_status = notification->control_status;
      Companion_Audio_UpdateDebugStatus();
      APP_DBG_MSG("  Info   : VKA1 control write status=%s len=%u\n",
                  comp_audio_stream_status_name(notification->control_status),
                  notification->length);
      break;

    default:
      break;
  }
}

void companion_gatt_stm32wb_schedule_task(void)
{
  UTIL_SEQ_SetTask(1 << CFG_TASK_COMPANION_GATT_ID, CFG_SCH_PRIO_0);
}

static bool Companion_Ble_IsConnected(void)
{
  return s_companion_ble_connected &&
         connectionHandle != COMPANION_BLE_CONN_HANDLE_INVALID;
}

static tBleStatus Companion_Ble_RequestConnectionParams(const char *reason,
                                                        uint16_t interval_min,
                                                        uint16_t interval_max,
                                                        uint16_t latency,
                                                        uint16_t timeout,
                                                        Companion_BleLinkMode_t mode)
{
  if (!Companion_Ble_IsConnected())
  {
    APP_DBG_MSG("==>> Companion BLE link %s skipped: not connected\n",
                reason != NULL ? reason : "request");
    return BLE_STATUS_INVALID_PARAMS;
  }
  if (s_companion_ble_link_mode == mode)
  {
    APP_DBG_MSG("==>> Companion BLE link %s already requested mode=%u handle=0x%04X\n",
                reason != NULL ? reason : "request",
                (unsigned int)mode,
                connectionHandle);
    return BLE_STATUS_SUCCESS;
  }

  tBleStatus ret = aci_l2cap_connection_parameter_update_req(connectionHandle,
                                                            interval_min,
                                                            interval_max,
                                                            latency,
                                                            timeout);
  if (ret == BLE_STATUS_SUCCESS)
  {
    s_companion_ble_link_mode = mode;
    APP_DBG_MSG("==>> Companion BLE link %s requested interval=0x%04X-0x%04X latency=%u timeout=0x%04X mode=%u\n",
                reason != NULL ? reason : "request",
                interval_min,
                interval_max,
                latency,
                timeout,
                (unsigned int)mode);
  }
  else
  {
    APP_DBG_MSG("==>> Companion BLE link %s request failed: result=0x%x mode=%u\n",
                reason != NULL ? reason : "request",
                ret,
                (unsigned int)mode);
  }
  return ret;
}

static tBleStatus Companion_Ble_RequestPreferred2MPhy(const char *reason)
{
  if (!Companion_Ble_IsConnected())
  {
    APP_DBG_MSG("==>> Companion BLE PHY %s skipped: not connected\n",
                reason != NULL ? reason : "request");
    return BLE_STATUS_INVALID_PARAMS;
  }

  tBleStatus ret = hci_le_set_phy(connectionHandle,
                                  COMPANION_BLE_LINK_PHY_ALL_SPECIFIED,
                                  COMPANION_BLE_LINK_PHY_2M,
                                  COMPANION_BLE_LINK_PHY_2M,
                                  COMPANION_BLE_LINK_PHY_OPTIONS_NONE);
  if (ret == BLE_STATUS_SUCCESS)
  {
    APP_DBG_MSG("==>> Companion BLE PHY %s requested 2M handle=0x%04X\n",
                reason != NULL ? reason : "request",
                connectionHandle);
  }
  else
  {
    APP_DBG_MSG("==>> Companion BLE PHY %s request failed: result=0x%x\n",
                reason != NULL ? reason : "request",
                ret);
  }
  return ret;
}

/* USER CODE END FD*/

/*************************************************************
 *
 * LOCAL FUNCTIONS
 *
 *************************************************************/
static void Ble_Tl_Init( void )
{
  HCI_TL_HciInitConf_t Hci_Tl_Init_Conf;

  Hci_Tl_Init_Conf.p_cmdbuffer = (uint8_t*)&BleCmdBuffer;
  Hci_Tl_Init_Conf.StatusNotCallBack = BLE_StatusNot;
  hci_init(BLE_UserEvtRx, (void*) &Hci_Tl_Init_Conf);

  return;
}

static void Ble_Hci_Gap_Gatt_Init(void)
{
  uint8_t role;
  uint16_t gap_service_handle, gap_dev_name_char_handle, gap_appearance_char_handle;
#if (CFG_IDENTITY_ADDRESS == GAP_PUBLIC_ADDR)
  const uint8_t *p_bd_addr;
#endif
#if (CFG_IDENTITY_ADDRESS != GAP_PUBLIC_ADDR)
  uint32_t a_srd_bd_addr[2];
#endif
  uint16_t a_appearance[1] = {BLE_CFG_GAP_APPEARANCE};
  tBleStatus ret = BLE_STATUS_INVALID_PARAMS;
  /* USER CODE BEGIN Ble_Hci_Gap_Gatt_Init*/

  /* USER CODE END Ble_Hci_Gap_Gatt_Init*/

  APP_DBG_MSG("==>> Start Ble_Hci_Gap_Gatt_Init function\n");

  /**
   * Initialize HCI layer
   */
  /*HCI Reset to synchronise BLE Stack*/
  ret = hci_reset();
  if (ret != BLE_STATUS_SUCCESS)
  {
    APP_DBG_MSG("  Fail   : hci_reset command, result: 0x%x \n", ret);
  }
  else
  {
    APP_DBG_MSG("  Success: hci_reset command\n");
  }

  /**
   * Write the BD Address
   */
#if (CFG_IDENTITY_ADDRESS == GAP_PUBLIC_ADDR)
  p_bd_addr = BleGetBdAddress();
  ret = aci_hal_write_config_data(CONFIG_DATA_PUBLIC_ADDRESS_OFFSET, CONFIG_DATA_PUBLIC_ADDRESS_LEN, (uint8_t*) p_bd_addr);
  if (ret != BLE_STATUS_SUCCESS)
  {
    APP_DBG_MSG("  Fail   : aci_hal_write_config_data command - CONFIG_DATA_PUBLIC_ADDRESS_OFFSET, result: 0x%x \n", ret);
  }
  else
  {
    APP_DBG_MSG("  Success: aci_hal_write_config_data command - CONFIG_DATA_PUBLIC_ADDRESS_OFFSET\n");
    APP_DBG_MSG("  Public Bluetooth Address: %02x:%02x:%02x:%02x:%02x:%02x\n",p_bd_addr[5],p_bd_addr[4],p_bd_addr[3],p_bd_addr[2],p_bd_addr[1],p_bd_addr[0]);
  }
#endif

#if (CFG_IDENTITY_ADDRESS == GAP_PUBLIC_ADDR)
  /* BLE MAC in ADV Packet */
  a_ManufData[ sizeof(a_ManufData)-6] = p_bd_addr[5];
  a_ManufData[ sizeof(a_ManufData)-5] = p_bd_addr[4];
  a_ManufData[ sizeof(a_ManufData)-4] = p_bd_addr[3];
  a_ManufData[ sizeof(a_ManufData)-3] = p_bd_addr[2];
  a_ManufData[ sizeof(a_ManufData)-2] = p_bd_addr[1];
  a_ManufData[ sizeof(a_ManufData)-1] = p_bd_addr[0];
#endif /* CFG_IDENTITY_ADDRESS == GAP_PUBLIC_ADDR */

  /**
   * Static random Address
   * The two upper bits shall be set to 1
   * The lowest 32bits is read from the UDN to differentiate between devices
   * The RNG may be used to provide a random number on each power on
   */
#if (CFG_IDENTITY_ADDRESS == GAP_STATIC_RANDOM_ADDR)
#if defined(CFG_STATIC_RANDOM_ADDRESS)
  a_srd_bd_addr[0] = CFG_STATIC_RANDOM_ADDRESS & 0xFFFFFFFF;
  a_srd_bd_addr[1] = (uint32_t)((uint64_t)CFG_STATIC_RANDOM_ADDRESS >> 32);
  a_srd_bd_addr[1] |= 0xC000; /* The two upper bits shall be set to 1 */

  /* BLE MAC in ADV Packet */
  a_ManufData[ sizeof(a_ManufData)-6] = a_srd_bd_addr[1] >> 8 ;
  a_ManufData[ sizeof(a_ManufData)-5] = a_srd_bd_addr[1];
  a_ManufData[ sizeof(a_ManufData)-4] = a_srd_bd_addr[0] >> 24;
  a_ManufData[ sizeof(a_ManufData)-3] = a_srd_bd_addr[0] >> 16;
  a_ManufData[ sizeof(a_ManufData)-2] = a_srd_bd_addr[0] >> 8;
  a_ManufData[ sizeof(a_ManufData)-1] = a_srd_bd_addr[0];

  ret = aci_hal_write_config_data(CONFIG_DATA_RANDOM_ADDRESS_OFFSET, CONFIG_DATA_RANDOM_ADDRESS_LEN, (uint8_t*)a_srd_bd_addr);
  if (ret != BLE_STATUS_SUCCESS)
  {
    APP_DBG_MSG("  Fail   : aci_hal_write_config_data command - CONFIG_DATA_RANDOM_ADDRESS_OFFSET, result: 0x%x \n", ret);
  }
  else
  {
    APP_DBG_MSG("  Success: aci_hal_write_config_data command - CONFIG_DATA_RANDOM_ADDRESS_OFFSET\n");
    APP_DBG_MSG("  Random Bluetooth Address: %02x:%02x:%02x:%02x:%02x:%02x\n", (uint8_t)(a_srd_bd_addr[1] >> 8),
                                                                               (uint8_t)(a_srd_bd_addr[1]),
                                                                               (uint8_t)(a_srd_bd_addr[0] >> 24),
                                                                               (uint8_t)(a_srd_bd_addr[0] >> 16),
                                                                               (uint8_t)(a_srd_bd_addr[0] >> 8),
                                                                               (uint8_t)(a_srd_bd_addr[0]));
  }
#else
  UNUSED(a_srd_bd_addr);
  APP_DBG_MSG(" !! => Warning: define CFG_STATIC_RANDOM_ADDRESS when GAP_STATIC_RANDOM_ADDR selected otherwise configure RNG module !!\n");
#endif /* CFG_STATIC_RANDOM_ADDRESS */
#endif

  /**
   * Write Identity root key used to derive IRK and DHK(Legacy)
   */
  ret = aci_hal_write_config_data(CONFIG_DATA_IR_OFFSET, CONFIG_DATA_IR_LEN, (uint8_t*)a_BLE_CfgIrValue);
  if (ret != BLE_STATUS_SUCCESS)
  {
    APP_DBG_MSG("  Fail   : aci_hal_write_config_data command - CONFIG_DATA_IR_OFFSET, result: 0x%x \n", ret);
  }
  else
  {
    APP_DBG_MSG("  Success: aci_hal_write_config_data command - CONFIG_DATA_IR_OFFSET\n");
  }

  /**
   * Write Encryption root key used to derive LTK and CSRK
   */
  ret = aci_hal_write_config_data(CONFIG_DATA_ER_OFFSET, CONFIG_DATA_ER_LEN, (uint8_t*)a_BLE_CfgErValue);
  if (ret != BLE_STATUS_SUCCESS)
  {
    APP_DBG_MSG("  Fail   : aci_hal_write_config_data command - CONFIG_DATA_ER_OFFSET, result: 0x%x \n", ret);
  }
  else
  {
    APP_DBG_MSG("  Success: aci_hal_write_config_data command - CONFIG_DATA_ER_OFFSET\n");
  }

  /**
   * Set TX Power.
   */
  ret = aci_hal_set_tx_power_level(1, CFG_TX_POWER);
  if (ret != BLE_STATUS_SUCCESS)
  {
    APP_DBG_MSG("  Fail   : aci_hal_set_tx_power_level command, result: 0x%x \n", ret);
  }
  else
  {
    APP_DBG_MSG("  Success: aci_hal_set_tx_power_level command\n");
  }

  /**
   * Initialize GATT interface
   */
  ret = aci_gatt_init();
  if (ret != BLE_STATUS_SUCCESS)
  {
    APP_DBG_MSG("  Fail   : aci_gatt_init command, result: 0x%x \n", ret);
  }
  else
  {
    APP_DBG_MSG("  Success: aci_gatt_init command\n");
  }

  /**
   * Initialize GAP interface
   */
  role = 0;

#if (BLE_CFG_PERIPHERAL == 1)
  role |= GAP_PERIPHERAL_ROLE;
#endif /* BLE_CFG_PERIPHERAL == 1 */

#if (BLE_CFG_CENTRAL == 1)
  role |= GAP_CENTRAL_ROLE;
#endif /* BLE_CFG_CENTRAL == 1 */

/* USER CODE BEGIN Role_Mngt*/

/* USER CODE END Role_Mngt */

  if (role > 0)
  {
    const char *name = COMPANION_BLE_PRODUCT_NAME;

    ret = aci_gap_init(role,
                       CFG_PRIVACY,
                       APPBLE_GAP_DEVICE_NAME_LENGTH,
                       &gap_service_handle,
                       &gap_dev_name_char_handle,
                       &gap_appearance_char_handle);

    if (ret != BLE_STATUS_SUCCESS)
    {
      APP_DBG_MSG("  Fail   : aci_gap_init command, result: 0x%x \n", ret);
    }
    else
    {
      APP_DBG_MSG("  Success: aci_gap_init command\n");
    }

    ret = aci_gatt_update_char_value(gap_service_handle, gap_dev_name_char_handle, 0, strlen(name), (uint8_t *) name);
    if (ret != BLE_STATUS_SUCCESS)
    {
      BLE_DBG_SVCCTL_MSG("  Fail   : aci_gatt_update_char_value - Device Name\n");
    }
    else
    {
      BLE_DBG_SVCCTL_MSG("  Success: aci_gatt_update_char_value - Device Name\n");
    }
  }

  ret = aci_gatt_update_char_value(gap_service_handle,
                                   gap_appearance_char_handle,
                                   0,
                                   2,
                                   (uint8_t *)&a_appearance);
  if (ret != BLE_STATUS_SUCCESS)
  {
    BLE_DBG_SVCCTL_MSG("  Fail   : aci_gatt_update_char_value - Appearance\n");
  }
  else
  {
    BLE_DBG_SVCCTL_MSG("  Success: aci_gatt_update_char_value - Appearance\n");
  }



  /**
   * Initialize IO capability
   */
  ret = aci_gap_set_io_capability(COMPANION_BLE_IO_CAPABILITY);
  if (ret != BLE_STATUS_SUCCESS)
  {
    APP_DBG_MSG("  Fail   : aci_gap_set_io_capability command, result: 0x%x \n", ret);
  }
  else
  {
    APP_DBG_MSG("  Success: aci_gap_set_io_capability command\n");
  }

  /**
   * Initialize authentication
   */
  ret = aci_gap_set_authentication_requirement(COMPANION_BLE_BONDING_MODE,
                                         COMPANION_BLE_MITM_PROTECTION,
                                         0,
                                         0,
                                         CFG_ENCRYPTION_KEY_SIZE_MIN,
                                         CFG_ENCRYPTION_KEY_SIZE_MAX,
                                         USE_FIXED_PIN_FOR_PAIRING_FORBIDDEN, /* deprecated feature */
                                         0,                                   /* deprecated feature */
                                         0);
  if (ret != BLE_STATUS_SUCCESS)
  {
    APP_DBG_MSG("  Fail   : aci_gap_set_authentication_requirement command, result: 0x%x \n", ret);
  }
  else
  {
    APP_DBG_MSG("  Success: aci_gap_set_authentication_requirement command\n");
  }

}

companion_ble_advertising_request_result_t Companion_Ble_RequestAdvertising(
    const char *reason)
{
  if (s_companion_ble_connected)
  {
    APP_DBG_MSG("==>> Companion advertising %s skipped: already connected\n",
                reason != NULL ? reason : "request");
    return COMPANION_BLE_ADVERTISING_REQUEST_ALREADY_CONNECTED;
  }
  if (s_companion_ble_advertising)
  {
    APP_DBG_MSG("==>> Companion advertising %s skipped: already active\n",
                reason != NULL ? reason : "request");
    return COMPANION_BLE_ADVERTISING_REQUEST_ALREADY_ACTIVE;
  }
  if (Adv_Request() != BLE_STATUS_SUCCESS)
  {
    APP_DBG_MSG("==>> Companion advertising %s failed\n",
                reason != NULL ? reason : "request");
    return COMPANION_BLE_ADVERTISING_REQUEST_FAILED;
  }
  APP_DBG_MSG("==>> Companion advertising %s started\n",
              reason != NULL ? reason : "request");
  return COMPANION_BLE_ADVERTISING_REQUEST_STARTED;
}

static tBleStatus Adv_Request(void)
{
  tBleStatus ret;

  APP_DBG_MSG("==>> Companion advertising request name=%s name_len=%u addr_type=%u\n",
              COMPANION_BLE_PRODUCT_NAME,
              (unsigned int)APPBLE_GAP_DEVICE_NAME_LENGTH,
              (unsigned int)CFG_BLE_ADDRESS_TYPE);

  ret = aci_gap_set_discoverable(ADV_IND,
                                 CFG_FAST_CONN_ADV_INTERVAL_MIN,
                                 CFG_FAST_CONN_ADV_INTERVAL_MAX,
                                 CFG_BLE_ADDRESS_TYPE,
                                 NO_WHITE_LIST_USE,
                                 sizeof(a_LocalName),
                                 (uint8_t*) &a_LocalName,
                                 0,
                                 0,
                                 0,
                                 0);
  if (ret != BLE_STATUS_SUCCESS)
  {
    APP_DBG_MSG("==>> Companion advertising start failed: aci_gap_set_discoverable result=0x%x\n",
                ret);
    return ret;
  }
  s_companion_ble_advertising = true;
  APP_DBG_MSG("==>> Companion advertising discoverable started\n");

  /* Send Advertising data */
  ret = aci_gap_update_adv_data(sizeof(a_ManufData), (uint8_t*) a_ManufData);
  if (ret != BLE_STATUS_SUCCESS)
  {
    APP_DBG_MSG("==>> Companion advertising data update failed: result=0x%x\n", ret);
    /* The controller is already discoverable. Keep the state truthful and
     * report the data-path warning separately through the existing log. */
    return BLE_STATUS_SUCCESS;
  }
  APP_DBG_MSG("==>> Companion advertising data active name=%s manuf_len=%u\n",
              COMPANION_BLE_PRODUCT_NAME,
              (unsigned int)sizeof(a_ManufData));
  return BLE_STATUS_SUCCESS;
}

#if (CFG_IDENTITY_ADDRESS == GAP_PUBLIC_ADDR)
const uint8_t* BleGetBdAddress( void )
{
  uint8_t *p_otp_addr;
  const uint8_t *p_bd_addr;
  uint32_t udn;
  uint32_t company_id;
  uint32_t device_id;

  udn = LL_FLASH_GetUDN();

  if(udn != 0xFFFFFFFF)
  {
    company_id = LL_FLASH_GetSTCompanyID();
    device_id = LL_FLASH_GetDeviceID();

/**
 * Public Address with the ST company ID
 * bit[47:24] : 24bits (OUI) equal to the company ID
 * bit[23:16] : Device ID.
 * bit[15:0] : The last 16bits from the UDN
 * Note: In order to use the Public Address in a final product, a dedicated
 * 24bits company ID (OUI) shall be bought.
 */
    a_BdAddrUdn[0] = (uint8_t)(udn & 0x000000FF);
    a_BdAddrUdn[1] = (uint8_t)( (udn & 0x0000FF00) >> 8 );
    a_BdAddrUdn[2] = (uint8_t)device_id;
    a_BdAddrUdn[3] = (uint8_t)(company_id & 0x000000FF);
    a_BdAddrUdn[4] = (uint8_t)( (company_id & 0x0000FF00) >> 8 );
    a_BdAddrUdn[5] = (uint8_t)( (company_id & 0x00FF0000) >> 16 );

    p_bd_addr = (const uint8_t *)a_BdAddrUdn;
  }
  else
  {
    p_otp_addr = OTP_Read(0);
    if (p_otp_addr)
    {
      p_bd_addr = ((OTP_ID0_t*)p_otp_addr)->bd_address;
    }
    else
    {
      p_bd_addr = a_MBdAddr;
    }
  }

  return p_bd_addr;
}
#endif
/* USER CODE BEGIN FD_LOCAL_FUNCTION */

/* USER CODE END FD_LOCAL_FUNCTION */

/*************************************************************
 *
 *SPECIFIC FUNCTIONS
 *
 *************************************************************/
/* USER CODE BEGIN FD_SPECIFIC_FUNCTIONS */

/* USER CODE END FD_SPECIFIC_FUNCTIONS */
/*************************************************************
 *
 * WRAP FUNCTIONS
 *
 *************************************************************/
void hci_notify_asynch_evt(void* p_Data)
{
  UTIL_SEQ_SetTask(1 << CFG_TASK_HCI_ASYNCH_EVT_ID, CFG_SCH_PRIO_0);

  return;
}

void hci_cmd_resp_release(uint32_t Flag)
{
  UTIL_SEQ_SetEvt(1 << CFG_IDLEEVT_HCI_CMD_EVT_RSP_ID);

  return;
}

void hci_cmd_resp_wait(uint32_t Timeout)
{
  UTIL_SEQ_WaitEvt(1 << CFG_IDLEEVT_HCI_CMD_EVT_RSP_ID);

  return;
}

static void BLE_UserEvtRx(void *p_Payload)
{
  SVCCTL_UserEvtFlowStatus_t svctl_return_status;
  tHCI_UserEvtRxParam *p_param;

  p_param = (tHCI_UserEvtRxParam *)p_Payload;

  svctl_return_status = SVCCTL_UserEvtRx((void *)&(p_param->pckt->evtserial));
  if (svctl_return_status != SVCCTL_UserEvtFlowDisable)
  {
    p_param->status = HCI_TL_UserEventFlow_Enable;
  }
  else
  {
    p_param->status = HCI_TL_UserEventFlow_Disable;
  }

  return;
}

static void BLE_StatusNot(HCI_TL_CmdStatus_t Status)
{
  uint32_t task_id_list;
  switch (Status)
  {
    case HCI_TL_CmdBusy:
      /**
       * All tasks that may send an aci/hci commands shall be listed here
       * This is to prevent a new command is sent while one is already pending
       */
      task_id_list = (1 << CFG_LAST_TASK_ID_WITH_HCICMD) - 1;
      UTIL_SEQ_PauseTask(task_id_list);
      /* USER CODE BEGIN HCI_TL_CmdBusy */

      /* USER CODE END HCI_TL_CmdBusy */
      break;

    case HCI_TL_CmdAvailable:
      /**
       * All tasks that may send an aci/hci commands shall be listed here
       * This is to prevent a new command is sent while one is already pending
       */
      task_id_list = (1 << CFG_LAST_TASK_ID_WITH_HCICMD) - 1;
      UTIL_SEQ_ResumeTask(task_id_list);
      /* USER CODE BEGIN HCI_TL_CmdAvailable */

      /* USER CODE END HCI_TL_CmdAvailable */
      break;

    default:
      /* USER CODE BEGIN Status */

      /* USER CODE END Status */
      break;
  }

  return;
}

void SVCCTL_ResumeUserEventFlow( void )
{
  hci_resume_flow();

  return;
}

/* USER CODE BEGIN FD_WRAP_FUNCTIONS */

/* USER CODE END FD_WRAP_FUNCTIONS */
