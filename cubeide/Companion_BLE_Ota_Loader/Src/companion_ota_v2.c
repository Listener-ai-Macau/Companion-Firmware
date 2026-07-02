#include "app_common.h"
#include "common_blesvc.h"
#include "svc_ctl.h"
#include "flash_driver.h"
#include "companion_ota_v2.h"

#define COMPANION_OTA_V2_UUID_LENGTH             UUID_TYPE_128
#define COMPANION_OTA_V2_CONTROL_SIZE            (16u)
#define COMPANION_OTA_V2_DATA_PACKET_SIZE        (248u)
#define COMPANION_OTA_V2_DATA_HEADER_SIZE        (4u)
#define COMPANION_OTA_V2_DATA_PAYLOAD_MAX        (COMPANION_OTA_V2_DATA_PACKET_SIZE - COMPANION_OTA_V2_DATA_HEADER_SIZE)
#define COMPANION_OTA_V2_STATUS_SIZE             (24u)
#define COMPANION_OTA_V2_DEFAULT_WINDOW_CHUNKS   (8u)
#define COMPANION_OTA_V2_FLASH_WORD_SIZE         (8u)
#define COMPANION_OTA_V2_MAGIC0                  ('C')
#define COMPANION_OTA_V2_MAGIC1                  ('O')
#define COMPANION_OTA_V2_MAGIC2                  ('V')
#define COMPANION_OTA_V2_MAGIC3                  ('2')
#define COMPANION_OTA_V2_PROTOCOL_VERSION        (1u)
#define COMPANION_OTA_V2_OP_BEGIN                (1u)
#define COMPANION_OTA_V2_OP_SYNC                 (2u)
#define COMPANION_OTA_V2_OP_FINISH               (3u)
#define COMPANION_OTA_V2_OP_ABORT                (4u)
#define COMPANION_OTA_V2_APP_BASE_ADDRESS        (FLASH_BASE + (CFG_APP_START_SECTOR_INDEX * FLASH_PAGE_SIZE))
#define COMPANION_OTA_V2_REBOOT_GRACE_MS         (300u)

typedef enum
{
  COMPANION_OTA_V2_STATE_IDLE = 0u,
  COMPANION_OTA_V2_STATE_ERASING = 1u,
  COMPANION_OTA_V2_STATE_RECEIVING = 2u,
  COMPANION_OTA_V2_STATE_COMPLETE = 3u,
  COMPANION_OTA_V2_STATE_ERROR = 4u,
} CompanionOtaV2State_t;

typedef enum
{
  COMPANION_OTA_V2_ERROR_NONE = 0u,
  COMPANION_OTA_V2_ERROR_BAD_MAGIC = 1u,
  COMPANION_OTA_V2_ERROR_BAD_STATE = 2u,
  COMPANION_OTA_V2_ERROR_BAD_SIZE = 3u,
  COMPANION_OTA_V2_ERROR_OFFSET_MISMATCH = 4u,
  COMPANION_OTA_V2_ERROR_FLASH_WRITE = 5u,
  COMPANION_OTA_V2_ERROR_ERASE_FAILED = 6u,
} CompanionOtaV2Error_t;

typedef struct
{
  uint16_t service_handle;
  uint16_t control_char_handle;
  uint16_t data_char_handle;
  uint16_t status_char_handle;
} CompanionOtaV2GattContext_t;

typedef struct
{
  CompanionOtaV2State_t state;
  CompanionOtaV2Error_t last_error;
  uint32_t expected_size;
  uint32_t bytes_written;
  uint32_t flash_address;
  uint32_t data_write_count;
  uint16_t chunk_payload_bytes;
  uint16_t window_chunks;
  uint8_t write_value_index;
  uint64_t write_value;
} CompanionOtaV2Context_t;

static SVCCTL_EvtAckStatus_t Companion_Ota_V2_Event_Handler(void *Event);
static uint8_t Companion_Ota_V2_Is_Value_Handle(uint16_t event_handle, uint16_t char_handle);
static void Companion_Ota_V2_Handle_Control(const uint8_t *bytes, uint8_t length);
static void Companion_Ota_V2_Handle_Data(const uint8_t *bytes, uint8_t length);
static void Companion_Ota_V2_Handle_Begin(const uint8_t *bytes, uint8_t length);
static void Companion_Ota_V2_Handle_Finish(void);
static void Companion_Ota_V2_Reset_Context(void);
static void Companion_Ota_V2_Set_Error(CompanionOtaV2Error_t error);
static void Companion_Ota_V2_Set_Recoverable_Error(CompanionOtaV2Error_t error);
static uint8_t Companion_Ota_V2_Erase_App(uint32_t image_size);
static uint8_t Companion_Ota_V2_App_Was_Prepared(uint32_t sectors_to_erase);
static uint8_t Companion_Ota_V2_Write_Bytes(const uint8_t *bytes, uint32_t length);
static uint8_t Companion_Ota_V2_Flush_Word(void);
static void Companion_Ota_V2_Update_Status(void);
static uint8_t Companion_Ota_V2_Has_Magic(const uint8_t *bytes, uint8_t length);
static uint32_t Companion_Ota_V2_Read_U32_Le(const uint8_t *bytes);
static uint16_t Companion_Ota_V2_Read_U16_Le(const uint8_t *bytes);
static void Companion_Ota_V2_Write_U32_Le(uint8_t *bytes, uint32_t value);
static void Companion_Ota_V2_Write_U16_Le(uint8_t *bytes, uint16_t value);

static const uint8_t COMPANION_OTA_V2_SERVICE_UUID[16] = {
  0x00, 0x00, 0x7c, 0x1b, 0x2d, 0x6c, 0x6f, 0x9d,
  0x3d, 0x4f, 0x7d, 0x7b, 0x07, 0x80, 0x7a, 0x8f
};
static const uint8_t COMPANION_OTA_V2_CONTROL_UUID[16] = {
  0x00, 0x00, 0x7c, 0x1b, 0x2d, 0x6c, 0x6f, 0x9d,
  0x3d, 0x4f, 0x7d, 0x7b, 0x02, 0x80, 0x7a, 0x8f
};
static const uint8_t COMPANION_OTA_V2_DATA_UUID[16] = {
  0x00, 0x00, 0x7c, 0x1b, 0x2d, 0x6c, 0x6f, 0x9d,
  0x3d, 0x4f, 0x7d, 0x7b, 0x04, 0x80, 0x7a, 0x8f
};
static const uint8_t COMPANION_OTA_V2_STATUS_UUID[16] = {
  0x00, 0x00, 0x7c, 0x1b, 0x2d, 0x6c, 0x6f, 0x9d,
  0x3d, 0x4f, 0x7d, 0x7b, 0x05, 0x80, 0x7a, 0x8f
};

PLACE_IN_SECTION("BLE_DRIVER_CONTEXT") static CompanionOtaV2GattContext_t CompanionOtaV2GattContext;
static CompanionOtaV2Context_t CompanionOtaV2Context;

void Companion_Ota_V2_Init(void)
{
  SVCCTL_RegisterSvcHandler(Companion_Ota_V2_Event_Handler);

  aci_gatt_add_service(COMPANION_OTA_V2_UUID_LENGTH,
                       (Service_UUID_t *)COMPANION_OTA_V2_SERVICE_UUID,
                       PRIMARY_SERVICE,
                       1
                       + 2  /* control */
                       + 2  /* data */
                       + 2, /* status */
                       &(CompanionOtaV2GattContext.service_handle));

  aci_gatt_add_char(CompanionOtaV2GattContext.service_handle,
                    COMPANION_OTA_V2_UUID_LENGTH,
                    (Char_UUID_t *)COMPANION_OTA_V2_CONTROL_UUID,
                    COMPANION_OTA_V2_CONTROL_SIZE,
                    CHAR_PROP_WRITE,
                    ATTR_PERMISSION_NONE,
                    GATT_NOTIFY_ATTRIBUTE_WRITE,
                    10,
                    1,
                    &(CompanionOtaV2GattContext.control_char_handle));

  aci_gatt_add_char(CompanionOtaV2GattContext.service_handle,
                    COMPANION_OTA_V2_UUID_LENGTH,
                    (Char_UUID_t *)COMPANION_OTA_V2_DATA_UUID,
                    COMPANION_OTA_V2_DATA_PACKET_SIZE,
                    CHAR_PROP_WRITE | CHAR_PROP_WRITE_WITHOUT_RESP,
                    ATTR_PERMISSION_NONE,
                    GATT_NOTIFY_ATTRIBUTE_WRITE,
                    10,
                    1,
                    &(CompanionOtaV2GattContext.data_char_handle));

  aci_gatt_add_char(CompanionOtaV2GattContext.service_handle,
                    COMPANION_OTA_V2_UUID_LENGTH,
                    (Char_UUID_t *)COMPANION_OTA_V2_STATUS_UUID,
                    COMPANION_OTA_V2_STATUS_SIZE,
                    CHAR_PROP_READ,
                    ATTR_PERMISSION_NONE,
                    GATT_DONT_NOTIFY_EVENTS,
                    10,
                    0,
                    &(CompanionOtaV2GattContext.status_char_handle));

  Companion_Ota_V2_Reset_Context();
  Companion_Ota_V2_Update_Status();
}

void SVCCTL_InitCustomSvc(void)
{
  Companion_Ota_V2_Init();
}

static SVCCTL_EvtAckStatus_t Companion_Ota_V2_Event_Handler(void *Event)
{
  SVCCTL_EvtAckStatus_t return_value = SVCCTL_EvtNotAck;
  hci_event_pckt *event_pckt;
  evt_blecore_aci *blecore_evt;
  aci_gatt_attribute_modified_event_rp0 *attribute_modified;

  event_pckt = (hci_event_pckt *)(((hci_uart_pckt*)Event)->data);

  if(event_pckt->evt != HCI_VENDOR_SPECIFIC_DEBUG_EVT_CODE)
  {
    return return_value;
  }

  blecore_evt = (evt_blecore_aci*)event_pckt->data;
  if(blecore_evt->ecode != ACI_GATT_ATTRIBUTE_MODIFIED_VSEVT_CODE)
  {
    return return_value;
  }

  attribute_modified = (aci_gatt_attribute_modified_event_rp0*)blecore_evt->data;
  if(Companion_Ota_V2_Is_Value_Handle(attribute_modified->Attr_Handle,
                                      CompanionOtaV2GattContext.control_char_handle) != 0u)
  {
    Companion_Ota_V2_Handle_Control(&attribute_modified->Attr_Data[0],
                                    attribute_modified->Attr_Data_Length);
    return_value = SVCCTL_EvtAckFlowEnable;
  }
  else if(Companion_Ota_V2_Is_Value_Handle(attribute_modified->Attr_Handle,
                                           CompanionOtaV2GattContext.data_char_handle) != 0u)
  {
    Companion_Ota_V2_Handle_Data(&attribute_modified->Attr_Data[0],
                                 attribute_modified->Attr_Data_Length);
    return_value = SVCCTL_EvtAckFlowEnable;
  }

  return return_value;
}

static uint8_t Companion_Ota_V2_Is_Value_Handle(uint16_t event_handle, uint16_t char_handle)
{
  return ((event_handle == char_handle) ||
          (event_handle == (char_handle + 1u)) ||
          (event_handle == (char_handle + 2u)));
}

static void Companion_Ota_V2_Handle_Control(const uint8_t *bytes, uint8_t length)
{
  if(Companion_Ota_V2_Has_Magic(bytes, length) == 0u)
  {
    Companion_Ota_V2_Set_Error(COMPANION_OTA_V2_ERROR_BAD_MAGIC);
    return;
  }

  if(bytes[5] != COMPANION_OTA_V2_PROTOCOL_VERSION)
  {
    Companion_Ota_V2_Set_Error(COMPANION_OTA_V2_ERROR_BAD_MAGIC);
    return;
  }

  switch(bytes[4])
  {
    case COMPANION_OTA_V2_OP_BEGIN:
      Companion_Ota_V2_Handle_Begin(bytes, length);
      break;

    case COMPANION_OTA_V2_OP_SYNC:
      Companion_Ota_V2_Update_Status();
      break;

    case COMPANION_OTA_V2_OP_FINISH:
      Companion_Ota_V2_Handle_Finish();
      break;

    case COMPANION_OTA_V2_OP_ABORT:
      Companion_Ota_V2_Reset_Context();
      Companion_Ota_V2_Update_Status();
      break;

    default:
      Companion_Ota_V2_Set_Error(COMPANION_OTA_V2_ERROR_BAD_MAGIC);
      break;
  }
}

static void Companion_Ota_V2_Handle_Begin(const uint8_t *bytes, uint8_t length)
{
  uint32_t expected_size;
  uint16_t chunk_payload_bytes;
  uint16_t window_chunks;

  if(length < COMPANION_OTA_V2_CONTROL_SIZE)
  {
    Companion_Ota_V2_Set_Error(COMPANION_OTA_V2_ERROR_BAD_SIZE);
    return;
  }

  expected_size = Companion_Ota_V2_Read_U32_Le(&bytes[8]);
  chunk_payload_bytes = Companion_Ota_V2_Read_U16_Le(&bytes[12]);
  window_chunks = Companion_Ota_V2_Read_U16_Le(&bytes[14]);

  if((expected_size == 0u) ||
     (chunk_payload_bytes == 0u) ||
     (chunk_payload_bytes > COMPANION_OTA_V2_DATA_PAYLOAD_MAX))
  {
    Companion_Ota_V2_Set_Error(COMPANION_OTA_V2_ERROR_BAD_SIZE);
    return;
  }
  if(window_chunks == 0u)
  {
    window_chunks = COMPANION_OTA_V2_DEFAULT_WINDOW_CHUNKS;
  }

  Companion_Ota_V2_Reset_Context();
  CompanionOtaV2Context.state = COMPANION_OTA_V2_STATE_ERASING;
  CompanionOtaV2Context.expected_size = expected_size;
  CompanionOtaV2Context.chunk_payload_bytes = chunk_payload_bytes;
  CompanionOtaV2Context.window_chunks = window_chunks;
  Companion_Ota_V2_Update_Status();

  if(Companion_Ota_V2_Erase_App(expected_size) == 0u)
  {
    Companion_Ota_V2_Set_Error(COMPANION_OTA_V2_ERROR_ERASE_FAILED);
    return;
  }

  CompanionOtaV2Context.state = COMPANION_OTA_V2_STATE_RECEIVING;
  Companion_Ota_V2_Update_Status();
}

static void Companion_Ota_V2_Handle_Data(const uint8_t *bytes, uint8_t length)
{
  uint32_t offset;
  uint32_t payload_length;

  if(length <= COMPANION_OTA_V2_DATA_HEADER_SIZE)
  {
    Companion_Ota_V2_Set_Error(COMPANION_OTA_V2_ERROR_BAD_SIZE);
    return;
  }
  if(CompanionOtaV2Context.state != COMPANION_OTA_V2_STATE_RECEIVING)
  {
    Companion_Ota_V2_Set_Error(COMPANION_OTA_V2_ERROR_BAD_STATE);
    return;
  }

  offset = Companion_Ota_V2_Read_U32_Le(bytes);
  payload_length = ((uint32_t)length) - COMPANION_OTA_V2_DATA_HEADER_SIZE;

  if(offset < CompanionOtaV2Context.bytes_written)
  {
    if((offset + payload_length) <= CompanionOtaV2Context.bytes_written)
    {
      CompanionOtaV2Context.data_write_count++;
      Companion_Ota_V2_Update_Status();
      return;
    }
    Companion_Ota_V2_Set_Recoverable_Error(COMPANION_OTA_V2_ERROR_OFFSET_MISMATCH);
    return;
  }

  if(offset != CompanionOtaV2Context.bytes_written)
  {
    Companion_Ota_V2_Set_Recoverable_Error(COMPANION_OTA_V2_ERROR_OFFSET_MISMATCH);
    return;
  }
  if((payload_length == 0u) ||
     ((CompanionOtaV2Context.bytes_written + payload_length) > CompanionOtaV2Context.expected_size))
  {
    Companion_Ota_V2_Set_Error(COMPANION_OTA_V2_ERROR_BAD_SIZE);
    return;
  }

  if(Companion_Ota_V2_Write_Bytes(&bytes[COMPANION_OTA_V2_DATA_HEADER_SIZE], payload_length) == 0u)
  {
    Companion_Ota_V2_Set_Error(COMPANION_OTA_V2_ERROR_FLASH_WRITE);
    return;
  }

  CompanionOtaV2Context.bytes_written += payload_length;
  CompanionOtaV2Context.data_write_count++;
  CompanionOtaV2Context.last_error = COMPANION_OTA_V2_ERROR_NONE;
  Companion_Ota_V2_Update_Status();
}

static void Companion_Ota_V2_Handle_Finish(void)
{
  if(CompanionOtaV2Context.state != COMPANION_OTA_V2_STATE_RECEIVING)
  {
    Companion_Ota_V2_Set_Error(COMPANION_OTA_V2_ERROR_BAD_STATE);
    return;
  }
  if(CompanionOtaV2Context.bytes_written != CompanionOtaV2Context.expected_size)
  {
    Companion_Ota_V2_Set_Error(COMPANION_OTA_V2_ERROR_BAD_SIZE);
    return;
  }
  if(Companion_Ota_V2_Flush_Word() == 0u)
  {
    Companion_Ota_V2_Set_Error(COMPANION_OTA_V2_ERROR_FLASH_WRITE);
    return;
  }

  CompanionOtaV2Context.state = COMPANION_OTA_V2_STATE_COMPLETE;
  Companion_Ota_V2_Update_Status();

  CFG_OTA_REBOOT_VAL_MSG = CFG_REBOOT_ON_FW_APP;
  HAL_Delay(COMPANION_OTA_V2_REBOOT_GRACE_MS);
  NVIC_SystemReset();
}

static void Companion_Ota_V2_Reset_Context(void)
{
  memset(&CompanionOtaV2Context, 0, sizeof(CompanionOtaV2Context));
  CompanionOtaV2Context.state = COMPANION_OTA_V2_STATE_IDLE;
  CompanionOtaV2Context.last_error = COMPANION_OTA_V2_ERROR_NONE;
  CompanionOtaV2Context.flash_address = COMPANION_OTA_V2_APP_BASE_ADDRESS;
  CompanionOtaV2Context.chunk_payload_bytes = COMPANION_OTA_V2_DATA_PAYLOAD_MAX;
  CompanionOtaV2Context.window_chunks = COMPANION_OTA_V2_DEFAULT_WINDOW_CHUNKS;
}

static void Companion_Ota_V2_Set_Error(CompanionOtaV2Error_t error)
{
  CompanionOtaV2Context.state = COMPANION_OTA_V2_STATE_ERROR;
  CompanionOtaV2Context.last_error = error;
  Companion_Ota_V2_Update_Status();
}

static void Companion_Ota_V2_Set_Recoverable_Error(CompanionOtaV2Error_t error)
{
  CompanionOtaV2Context.last_error = error;
  Companion_Ota_V2_Update_Status();
}

static uint8_t Companion_Ota_V2_Erase_App(uint32_t image_size)
{
  uint32_t first_secure_sector_idx;
  uint32_t max_app_sectors;
  uint32_t sectors_to_erase;
  uint32_t max_app_size;

  first_secure_sector_idx = (READ_BIT(FLASH->SFR, FLASH_SFR_SFSA) >> FLASH_SFR_SFSA_Pos);
  if(first_secure_sector_idx <= CFG_APP_START_SECTOR_INDEX)
  {
    return 0u;
  }

  max_app_sectors = first_secure_sector_idx - CFG_APP_START_SECTOR_INDEX;
  max_app_size = max_app_sectors * FLASH_PAGE_SIZE;
  if((image_size == 0u) || (image_size > max_app_size))
  {
    return 0u;
  }

  sectors_to_erase = (image_size + FLASH_PAGE_SIZE - 1u) / FLASH_PAGE_SIZE;
  if(sectors_to_erase == 0u)
  {
    return 0u;
  }

  if(Companion_Ota_V2_App_Was_Prepared(sectors_to_erase) != 0u)
  {
    return 1u;
  }

  return (FD_EraseSectors(CFG_APP_START_SECTOR_INDEX, sectors_to_erase) == 0u) ? 1u : 0u;
}

static uint8_t Companion_Ota_V2_App_Was_Prepared(uint32_t sectors_to_erase)
{
  return ((CFG_OTA_REBOOT_VAL_MSG == CFG_REBOOT_ON_BLE_OTA_APP) &&
          (CFG_OTA_START_SECTOR_IDX_VAL_MSG == CFG_APP_START_SECTOR_INDEX) &&
          (((uint32_t)CFG_OTA_NBR_OF_SECTOR_VAL_MSG) >= sectors_to_erase)) ? 1u : 0u;
}

static uint8_t Companion_Ota_V2_Write_Bytes(const uint8_t *bytes, uint32_t length)
{
  uint32_t count = 0u;

  while(count < length)
  {
    uint32_t bytes_to_copy = COMPANION_OTA_V2_FLASH_WORD_SIZE - CompanionOtaV2Context.write_value_index;
    uint32_t bytes_left = length - count;
    if(bytes_to_copy > bytes_left)
    {
      bytes_to_copy = bytes_left;
    }

    memcpy((uint8_t*)&CompanionOtaV2Context.write_value + CompanionOtaV2Context.write_value_index,
           bytes + count,
           bytes_to_copy);
    CompanionOtaV2Context.write_value_index += (uint8_t)bytes_to_copy;
    count += bytes_to_copy;

    if(CompanionOtaV2Context.write_value_index == COMPANION_OTA_V2_FLASH_WORD_SIZE)
    {
      if(Companion_Ota_V2_Flush_Word() == 0u)
      {
        return 0u;
      }
    }
  }

  return 1u;
}

static uint8_t Companion_Ota_V2_Flush_Word(void)
{
  uint32_t pending;

  if(CompanionOtaV2Context.write_value_index == 0u)
  {
    return 1u;
  }

  if(CompanionOtaV2Context.write_value_index < COMPANION_OTA_V2_FLASH_WORD_SIZE)
  {
    memset((uint8_t*)&CompanionOtaV2Context.write_value + CompanionOtaV2Context.write_value_index,
           0xFF,
           COMPANION_OTA_V2_FLASH_WORD_SIZE - CompanionOtaV2Context.write_value_index);
  }

  pending = 1u;
  while(pending > 0u)
  {
    pending = FD_WriteData(CompanionOtaV2Context.flash_address,
                           &(CompanionOtaV2Context.write_value),
                           1u);
  }

  if(*(uint64_t*)(CompanionOtaV2Context.flash_address) != CompanionOtaV2Context.write_value)
  {
    return 0u;
  }

  CompanionOtaV2Context.flash_address += COMPANION_OTA_V2_FLASH_WORD_SIZE;
  CompanionOtaV2Context.write_value = 0u;
  CompanionOtaV2Context.write_value_index = 0u;
  return 1u;
}

static void Companion_Ota_V2_Update_Status(void)
{
  uint8_t status[COMPANION_OTA_V2_STATUS_SIZE];

  memset(status, 0, sizeof(status));
  status[0] = COMPANION_OTA_V2_MAGIC0;
  status[1] = COMPANION_OTA_V2_MAGIC1;
  status[2] = COMPANION_OTA_V2_MAGIC2;
  status[3] = COMPANION_OTA_V2_MAGIC3;
  status[4] = COMPANION_OTA_V2_PROTOCOL_VERSION;
  status[5] = (uint8_t)CompanionOtaV2Context.state;
  status[6] = (uint8_t)CompanionOtaV2Context.last_error;
  Companion_Ota_V2_Write_U32_Le(&status[8], CompanionOtaV2Context.bytes_written);
  Companion_Ota_V2_Write_U32_Le(&status[12], CompanionOtaV2Context.expected_size);
  Companion_Ota_V2_Write_U16_Le(&status[16], CompanionOtaV2Context.chunk_payload_bytes);
  Companion_Ota_V2_Write_U16_Le(&status[18], CompanionOtaV2Context.window_chunks);
  Companion_Ota_V2_Write_U32_Le(&status[20], CompanionOtaV2Context.data_write_count);

  (void)aci_gatt_update_char_value(CompanionOtaV2GattContext.service_handle,
                                   CompanionOtaV2GattContext.status_char_handle,
                                   0,
                                   COMPANION_OTA_V2_STATUS_SIZE,
                                   status);
}

static uint8_t Companion_Ota_V2_Has_Magic(const uint8_t *bytes, uint8_t length)
{
  return ((length >= 6u) &&
          (bytes[0] == COMPANION_OTA_V2_MAGIC0) &&
          (bytes[1] == COMPANION_OTA_V2_MAGIC1) &&
          (bytes[2] == COMPANION_OTA_V2_MAGIC2) &&
          (bytes[3] == COMPANION_OTA_V2_MAGIC3)) ? 1u : 0u;
}

static uint32_t Companion_Ota_V2_Read_U32_Le(const uint8_t *bytes)
{
  return ((uint32_t)bytes[0]) |
         (((uint32_t)bytes[1]) << 8) |
         (((uint32_t)bytes[2]) << 16) |
         (((uint32_t)bytes[3]) << 24);
}

static uint16_t Companion_Ota_V2_Read_U16_Le(const uint8_t *bytes)
{
  return (uint16_t)(((uint16_t)bytes[0]) | (((uint16_t)bytes[1]) << 8));
}

static void Companion_Ota_V2_Write_U32_Le(uint8_t *bytes, uint32_t value)
{
  bytes[0] = (uint8_t)(value & 0xFFu);
  bytes[1] = (uint8_t)((value >> 8) & 0xFFu);
  bytes[2] = (uint8_t)((value >> 16) & 0xFFu);
  bytes[3] = (uint8_t)((value >> 24) & 0xFFu);
}

static void Companion_Ota_V2_Write_U16_Le(uint8_t *bytes, uint16_t value)
{
  bytes[0] = (uint8_t)(value & 0xFFu);
  bytes[1] = (uint8_t)((value >> 8) & 0xFFu);
}
