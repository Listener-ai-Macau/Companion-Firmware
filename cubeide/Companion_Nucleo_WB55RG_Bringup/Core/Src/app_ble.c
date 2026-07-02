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
#include "otp.h"

#ifdef OTA_SBSFU
#include "ota_sbsfu.h"
#endif /* OTA_SBSFU */

#include "audio_stream_stm32wb.h"
#include "companion_gatt_stm32wb.h"
#include "companion_v1_features.h"

/* Private includes ----------------------------------------------------------*/
/* USER CODE BEGIN Includes */
#include <stdio.h>
#include <string.h>

/* USER CODE END Includes */

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
static uint32_t s_companion_audio_next_session_id = 1u;
static bool s_companion_ble_connected = false;
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
static companion_v1_features_t s_companion_v1_features;
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
static void Adv_Request(void);

/* USER CODE BEGIN PFP */
static void Companion_Audio_Init(void);
static void Companion_Gatt_Init(void);
static void Companion_Gatt_Task(void);
static void Companion_Gatt_HandleEvent(const companion_gatt_event_t *event,
                                       void *context);
static void Companion_Gatt_PublishInitialState(void);
static void Companion_Gatt_PublishCurrent(companion_gatt_char_id_t char_id);
static void Companion_Gatt_PublishDeviceStatus(void);
static void Companion_Gatt_PublishBatteryCharge(void);
static void Companion_Gatt_PublishCardStatus(uint32_t request_id,
                                             uint8_t render_state,
                                             uint8_t last_error,
                                             uint32_t content_crc32);
static void Companion_Gatt_PublishRecordingControlEcho(
    const companion_gatt_recording_control_v1_t *request,
    bool accepted);
static void Companion_Gatt_PublishRecordingChunk(
    const companion_gatt_recording_chunk_pull_v1_t *request);
static void Companion_Gatt_PublishSettings(void);
static void Companion_Gatt_PublishBleNameConfig(void);
static void Companion_Gatt_PublishMeetingStatus(void);
static void Companion_Gatt_PublishImuStatus(void);
static void Companion_Gatt_PublishSpeakerStatus(void);
static void Companion_Gatt_PublishWakeWordStatus(void);
static void Companion_Gatt_PublishDiagLogResponse(
    const companion_gatt_diag_log_pull_v1_t *request);
static void Companion_Gatt_PublishDeletePrivacyStatus(
    const companion_gatt_delete_privacy_v1_t *request,
    bool accepted);
static void Companion_Gatt_PublishOtaReadiness(void);
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

static void Companion_Gatt_Init(void)
{
  companion_v1_features_init(&s_companion_v1_features, HAL_GetTick());

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
        Companion_Gatt_PublishCardStatus(
            request.request_id,
            1u,
            0u,
            Companion_Gatt_Fnv1a(&event->payload[header_len], content_len));
      }
      else
      {
        Companion_Gatt_PublishCardStatus(0u, 3u, (uint8_t)parse_result, 0u);
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
        s_companion_gatt_settings = request;
        Companion_Gatt_PublishSettings();
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
        (void)companion_v1_apply_ble_name_config(&s_companion_v1_features,
                                                 &request);
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
        (void)companion_v1_apply_meeting_control(&s_companion_v1_features,
                                                 &request,
                                                 HAL_GetTick());
      }
      Companion_Gatt_PublishMeetingStatus();
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
        (void)companion_v1_apply_speaker_control(&s_companion_v1_features,
                                                 &request,
                                                 HAL_GetTick());
      }
      Companion_Gatt_PublishSpeakerStatus();
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
        (void)companion_v1_apply_wake_word_control(&s_companion_v1_features,
                                                   &request,
                                                   HAL_GetTick());
      }
      Companion_Gatt_PublishWakeWordStatus();
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
  Companion_Gatt_PublishDeviceStatus();
  Companion_Gatt_PublishBatteryCharge();
  Companion_Gatt_PublishCardStatus(0u, 0u, 0u, 0u);
  Companion_Gatt_PublishRecordingList();
  Companion_Gatt_PublishSettings();
  Companion_Gatt_PublishBleNameConfig();
  Companion_Gatt_PublishMeetingStatus();
  Companion_Gatt_PublishImuStatus();
  Companion_Gatt_PublishSpeakerStatus();
  Companion_Gatt_PublishWakeWordStatus();
  Companion_Gatt_PublishOtaReadiness();
}

static void Companion_Gatt_PublishCurrent(companion_gatt_char_id_t char_id)
{
  switch (char_id)
  {
    case COMPANION_GATT_CHAR_DEVICE_STATUS:
      Companion_Gatt_PublishDeviceStatus();
      break;

    case COMPANION_GATT_CHAR_BATTERY_CHARGE:
      Companion_Gatt_PublishBatteryCharge();
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
      Companion_Gatt_PublishMeetingStatus();
      break;

    case COMPANION_GATT_CHAR_IMU_STATUS:
      Companion_Gatt_PublishImuStatus();
      break;

    case COMPANION_GATT_CHAR_SPEAKER_STATUS:
      Companion_Gatt_PublishSpeakerStatus();
      break;

    case COMPANION_GATT_CHAR_WAKE_WORD_STATUS:
      Companion_Gatt_PublishWakeWordStatus();
      break;

    case COMPANION_GATT_CHAR_OTA_READINESS:
      Companion_Gatt_PublishOtaReadiness();
      break;

    default:
      break;
  }
}

static void Companion_Gatt_PublishDeviceStatus(void)
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

  (void)companion_gatt_stm32wb_publish(COMPANION_GATT_CHAR_DEVICE_STATUS,
                                       (const uint8_t *)&status,
                                       (uint16_t)sizeof(status));
}

static void Companion_Gatt_PublishBatteryCharge(void)
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
}

static void Companion_Gatt_PublishCardStatus(uint32_t request_id,
                                             uint8_t render_state,
                                             uint8_t last_error,
                                             uint32_t content_crc32)
{
  s_companion_gatt_card_status.schema_version = 1u;
  s_companion_gatt_card_status.card_slot = 0u;
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

static void Companion_Gatt_PublishMeetingStatus(void)
{
  companion_gatt_meeting_status_v1_t status;
  companion_v1_get_meeting_status(&s_companion_v1_features, &status);
  (void)companion_gatt_stm32wb_publish(COMPANION_GATT_CHAR_MEETING_STATUS,
                                       (const uint8_t *)&status,
                                       (uint16_t)sizeof(status));
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

static void Companion_Gatt_PublishSpeakerStatus(void)
{
  companion_gatt_speaker_status_v1_t status;
  companion_v1_get_speaker_status(&s_companion_v1_features, &status);
  (void)companion_gatt_stm32wb_publish(COMPANION_GATT_CHAR_SPEAKER_STATUS,
                                       (const uint8_t *)&status,
                                       (uint16_t)sizeof(status));
}

static void Companion_Gatt_PublishWakeWordStatus(void)
{
  companion_gatt_wake_word_status_v1_t status;
  companion_v1_get_wake_word_status(&s_companion_v1_features, &status);
  (void)companion_gatt_stm32wb_publish(COMPANION_GATT_CHAR_WAKE_WORD_STATUS,
                                       (const uint8_t *)&status,
                                       (uint16_t)sizeof(status));
}

static void Companion_Gatt_PublishDiagLogResponse(
    const companion_gatt_diag_log_pull_v1_t *request)
{
  if (request == NULL)
  {
    return;
  }

  companion_gatt_diag_log_pull_v1_t response = *request;
  response.schema_version = 1u;
  response.cursor = request->cursor + 1u;
  response.max_events = request->max_events == 0u ? 0u : 1u;
  if (response.max_bytes > 64u)
  {
    response.max_bytes = 64u;
  }

  (void)companion_gatt_stm32wb_publish(COMPANION_GATT_CHAR_DIAGNOSTICS_LOG_PULL,
                                       (const uint8_t *)&response,
                                       (uint16_t)sizeof(response));
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

static void Companion_Gatt_PublishOtaReadiness(void)
{
  static const uint8_t sha_prefix[8] = {
      0xBEu, 0xFAu, 0xEBu, 0x26u, 0x11u, 0x66u, 0x0Du, 0x9Eu,
  };
  companion_gatt_ota_readiness_v1_t readiness = {
      .schema_version = 1u,
      .ready_state = 1u,
      .boot_slot = 0u,
      .battery_percent = 100u,
      .minimum_required_mv = 3700u,
      .blocker_bitmap = 0x0010u,
      .manifest_version = 1u,
      .image_size = 68240u,
  };
  memcpy(readiness.image_sha256_prefix, sha_prefix, sizeof(sha_prefix));

  (void)companion_gatt_stm32wb_publish(COMPANION_GATT_CHAR_OTA_READINESS,
                                       (const uint8_t *)&readiness,
                                       (uint16_t)sizeof(readiness));
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

static void Adv_Request(void)
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
    return;
  }
  APP_DBG_MSG("==>> Companion advertising discoverable started\n");

  /* Send Advertising data */
  ret = aci_gap_update_adv_data(sizeof(a_ManufData), (uint8_t*) a_ManufData);
  if (ret != BLE_STATUS_SUCCESS)
  {
    APP_DBG_MSG("==>> Companion advertising data update failed: result=0x%x\n", ret);
    return;
  }
  APP_DBG_MSG("==>> Companion advertising data active name=%s manuf_len=%u\n",
              COMPANION_BLE_PRODUCT_NAME,
              (unsigned int)sizeof(a_ManufData));
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
