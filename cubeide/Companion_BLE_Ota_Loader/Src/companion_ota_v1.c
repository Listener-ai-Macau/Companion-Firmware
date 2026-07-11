#include "app_common.h"
#include "common_blesvc.h"
#include "svc_ctl.h"
#include "flash_driver.h"
#include "companion_ota_v1.h"
#include "denzic_ota_v1.h"

#define COMPANION_OTA_V1_UUID_LENGTH             UUID_TYPE_128
#define COMPANION_OTA_V1_DATA_PACKET_SIZE        (248u)
#define COMPANION_OTA_V1_DATA_PAYLOAD_MAX        (COMPANION_OTA_V1_DATA_PACKET_SIZE - DENZIC_OTA_V1_DATA_HEADER_BYTES)
#define COMPANION_OTA_V1_DEFAULT_WINDOW_CHUNKS   (8u)
#define COMPANION_OTA_V1_FLASH_WORD_SIZE         (8u)
#define COMPANION_OTA_V1_APP_BASE_ADDRESS        (FLASH_BASE + (CFG_APP_START_SECTOR_INDEX * FLASH_PAGE_SIZE))
#define COMPANION_OTA_V1_REBOOT_GRACE_MS         (300u)

#ifdef COMPANION_OTA_LOADER_ALWAYS_ADVERTISE
#define COMPANION_OTA_V1_FW_APP_COOKIE_VALUE  (0xC3u)
#define COMPANION_OTA_V1_FW_APP_COOKIE_MSG    (*(uint8_t*)(SRAM1_BASE+3))
#endif

typedef struct
{
  uint16_t service_handle;
  uint16_t control_char_handle;
  uint16_t data_char_handle;
  uint16_t status_char_handle;
} CompanionOtaV1GattContext_t;

typedef struct
{
  uint32_t flash_address;
  uint8_t write_value_index;
  uint64_t write_value;
} CompanionOtaV1StorageContext_t;

static SVCCTL_EvtAckStatus_t Companion_Ota_V1_Event_Handler(void *Event);
static uint8_t Companion_Ota_V1_Is_Value_Handle(uint16_t event_handle, uint16_t char_handle);
static void Companion_Ota_V1_Handle_Control(const uint8_t *bytes, uint8_t length);
static void Companion_Ota_V1_Handle_Data(const uint8_t *bytes, uint8_t length);
static void Companion_Ota_V1_Update_Status(void);
static void Companion_Ota_V1_Reboot_To_App(void);
static uint8_t Companion_Ota_V1_Erase_App(uint32_t image_size);
static uint8_t Companion_Ota_V1_App_Was_Prepared(uint32_t sectors_to_erase);
static uint8_t Companion_Ota_V1_Write_Bytes(const uint8_t *bytes, uint32_t length);
static uint8_t Companion_Ota_V1_Flush_Word(void);
static void Companion_Ota_V1_Reset_Storage(void);
static bool Companion_Ota_V1_Storage_Begin(void *driver_context, uint32_t image_size);
static bool Companion_Ota_V1_Storage_Write(void *driver_context, const uint8_t *data, size_t length);
static bool Companion_Ota_V1_Storage_Finish(void *driver_context);
static void Companion_Ota_V1_Storage_Abort(void *driver_context);

static const uint8_t COMPANION_OTA_V1_SERVICE_UUID[16] = {
  0x00, 0x00, 0x7c, 0x1b, 0x2d, 0x6c, 0x6f, 0x9d,
  0x3d, 0x4f, 0x7d, 0x7b, 0x07, 0x80, 0x7a, 0x8f
};
static const uint8_t COMPANION_OTA_V1_CONTROL_UUID[16] = {
  0x00, 0x00, 0x7c, 0x1b, 0x2d, 0x6c, 0x6f, 0x9d,
  0x3d, 0x4f, 0x7d, 0x7b, 0x02, 0x80, 0x7a, 0x8f
};
static const uint8_t COMPANION_OTA_V1_DATA_UUID[16] = {
  0x00, 0x00, 0x7c, 0x1b, 0x2d, 0x6c, 0x6f, 0x9d,
  0x3d, 0x4f, 0x7d, 0x7b, 0x04, 0x80, 0x7a, 0x8f
};
static const uint8_t COMPANION_OTA_V1_STATUS_UUID[16] = {
  0x00, 0x00, 0x7c, 0x1b, 0x2d, 0x6c, 0x6f, 0x9d,
  0x3d, 0x4f, 0x7d, 0x7b, 0x05, 0x80, 0x7a, 0x8f
};

PLACE_IN_SECTION("BLE_DRIVER_CONTEXT") static CompanionOtaV1GattContext_t CompanionOtaV1GattContext;
static CompanionOtaV1StorageContext_t CompanionOtaV1StorageContext;
static denzic_ota_v1_context_t CompanionOtaV1Context;

void Companion_Ota_V1_Init(void)
{
  denzic_ota_v1_storage_driver_t storage_driver = {
    .begin = Companion_Ota_V1_Storage_Begin,
    .write = Companion_Ota_V1_Storage_Write,
    .finish = Companion_Ota_V1_Storage_Finish,
    .abort = Companion_Ota_V1_Storage_Abort,
  };

  SVCCTL_RegisterSvcHandler(Companion_Ota_V1_Event_Handler);
  aci_gatt_add_service(COMPANION_OTA_V1_UUID_LENGTH,
                       (Service_UUID_t *)COMPANION_OTA_V1_SERVICE_UUID,
                       PRIMARY_SERVICE,
                       1 + 2 + 2 + 2,
                       &(CompanionOtaV1GattContext.service_handle));
  aci_gatt_add_char(CompanionOtaV1GattContext.service_handle,
                    COMPANION_OTA_V1_UUID_LENGTH,
                    (Char_UUID_t *)COMPANION_OTA_V1_CONTROL_UUID,
                    DENZIC_OTA_V1_CONTROL_BYTES,
                    CHAR_PROP_WRITE,
                    ATTR_PERMISSION_NONE,
                    GATT_NOTIFY_ATTRIBUTE_WRITE,
                    10,
                    1,
                    &(CompanionOtaV1GattContext.control_char_handle));
  aci_gatt_add_char(CompanionOtaV1GattContext.service_handle,
                    COMPANION_OTA_V1_UUID_LENGTH,
                    (Char_UUID_t *)COMPANION_OTA_V1_DATA_UUID,
                    COMPANION_OTA_V1_DATA_PACKET_SIZE,
                    CHAR_PROP_WRITE | CHAR_PROP_WRITE_WITHOUT_RESP,
                    ATTR_PERMISSION_NONE,
                    GATT_NOTIFY_ATTRIBUTE_WRITE,
                    10,
                    1,
                    &(CompanionOtaV1GattContext.data_char_handle));
  aci_gatt_add_char(CompanionOtaV1GattContext.service_handle,
                    COMPANION_OTA_V1_UUID_LENGTH,
                    (Char_UUID_t *)COMPANION_OTA_V1_STATUS_UUID,
                    DENZIC_OTA_V1_STATUS_BYTES,
                    CHAR_PROP_READ,
                    ATTR_PERMISSION_NONE,
                    GATT_DONT_NOTIFY_EVENTS,
                    10,
                    0,
                    &(CompanionOtaV1GattContext.status_char_handle));

  Companion_Ota_V1_Reset_Storage();
  denzic_ota_v1_init(&CompanionOtaV1Context,
                     storage_driver,
                     &CompanionOtaV1StorageContext,
                     COMPANION_OTA_V1_DATA_PAYLOAD_MAX,
                     COMPANION_OTA_V1_DEFAULT_WINDOW_CHUNKS);
  Companion_Ota_V1_Update_Status();
}

void SVCCTL_SvcInit(void)
{
  Companion_Ota_V1_Init();
}

static SVCCTL_EvtAckStatus_t Companion_Ota_V1_Event_Handler(void *Event)
{
  SVCCTL_EvtAckStatus_t return_value = SVCCTL_EvtNotAck;
  hci_event_pckt *event_pckt = (hci_event_pckt *)(((hci_uart_pckt*)Event)->data);
  evt_blecore_aci *blecore_evt;
  aci_gatt_attribute_modified_event_rp0 *attribute_modified;

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
  if(Companion_Ota_V1_Is_Value_Handle(attribute_modified->Attr_Handle,
                                      CompanionOtaV1GattContext.control_char_handle) != 0u)
  {
    Companion_Ota_V1_Handle_Control(&attribute_modified->Attr_Data[0],
                                    attribute_modified->Attr_Data_Length);
    return_value = SVCCTL_EvtAckFlowEnable;
  }
  else if(Companion_Ota_V1_Is_Value_Handle(attribute_modified->Attr_Handle,
                                           CompanionOtaV1GattContext.data_char_handle) != 0u)
  {
    Companion_Ota_V1_Handle_Data(&attribute_modified->Attr_Data[0],
                                 attribute_modified->Attr_Data_Length);
    return_value = SVCCTL_EvtAckFlowEnable;
  }
  return return_value;
}

static uint8_t Companion_Ota_V1_Is_Value_Handle(uint16_t event_handle, uint16_t char_handle)
{
  return ((event_handle == char_handle) ||
          (event_handle == (char_handle + 1u)) ||
          (event_handle == (char_handle + 2u))) ? 1u : 0u;
}

static void Companion_Ota_V1_Handle_Control(const uint8_t *bytes, uint8_t length)
{
  uint8_t operation = (length > 4u) ? bytes[4] : 0u;
  bool accepted = denzic_ota_v1_handle_control(&CompanionOtaV1Context, bytes, length);
  Companion_Ota_V1_Update_Status();
  if(accepted && operation == DENZIC_OTA_V1_OP_FINISH)
  {
    Companion_Ota_V1_Reboot_To_App();
  }
}

static void Companion_Ota_V1_Handle_Data(const uint8_t *bytes, uint8_t length)
{
  (void)denzic_ota_v1_handle_data(&CompanionOtaV1Context, bytes, length);
  Companion_Ota_V1_Update_Status();
}

static bool Companion_Ota_V1_Storage_Begin(void *driver_context, uint32_t image_size)
{
  (void)driver_context;
  Companion_Ota_V1_Reset_Storage();
  return Companion_Ota_V1_Erase_App(image_size) != 0u;
}

static bool Companion_Ota_V1_Storage_Write(void *driver_context, const uint8_t *data, size_t length)
{
  (void)driver_context;
  return Companion_Ota_V1_Write_Bytes(data, (uint32_t)length) != 0u;
}

static bool Companion_Ota_V1_Storage_Finish(void *driver_context)
{
  (void)driver_context;
  return Companion_Ota_V1_Flush_Word() != 0u;
}

static void Companion_Ota_V1_Storage_Abort(void *driver_context)
{
  (void)driver_context;
  Companion_Ota_V1_Reset_Storage();
}

static void Companion_Ota_V1_Reboot_To_App(void)
{
#ifdef COMPANION_OTA_LOADER_ALWAYS_ADVERTISE
  COMPANION_OTA_V1_FW_APP_COOKIE_MSG = COMPANION_OTA_V1_FW_APP_COOKIE_VALUE;
#endif
  CFG_OTA_REBOOT_VAL_MSG = CFG_REBOOT_ON_FW_APP;
  HAL_Delay(COMPANION_OTA_V1_REBOOT_GRACE_MS);
  NVIC_SystemReset();
}

static void Companion_Ota_V1_Reset_Storage(void)
{
  memset(&CompanionOtaV1StorageContext, 0, sizeof(CompanionOtaV1StorageContext));
  CompanionOtaV1StorageContext.flash_address = COMPANION_OTA_V1_APP_BASE_ADDRESS;
}

static uint8_t Companion_Ota_V1_Erase_App(uint32_t image_size)
{
  uint32_t first_secure_sector_idx =
    (READ_BIT(FLASH->SFR, FLASH_SFR_SFSA) >> FLASH_SFR_SFSA_Pos);
  uint32_t max_app_sectors;
  uint32_t sectors_to_erase;
  uint32_t max_app_size;

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
  if(Companion_Ota_V1_App_Was_Prepared(sectors_to_erase) != 0u)
  {
    return 1u;
  }
  return (FD_EraseSectors(CFG_APP_START_SECTOR_INDEX, sectors_to_erase) == 0u) ? 1u : 0u;
}

static uint8_t Companion_Ota_V1_App_Was_Prepared(uint32_t sectors_to_erase)
{
  return ((CFG_OTA_REBOOT_VAL_MSG == CFG_REBOOT_ON_BLE_OTA_APP) &&
          (CFG_OTA_START_SECTOR_IDX_VAL_MSG == CFG_APP_START_SECTOR_INDEX) &&
          (((uint32_t)CFG_OTA_NBR_OF_SECTOR_VAL_MSG) >= sectors_to_erase)) ? 1u : 0u;
}

static uint8_t Companion_Ota_V1_Write_Bytes(const uint8_t *bytes, uint32_t length)
{
  uint32_t count = 0u;
  while(count < length)
  {
    uint32_t bytes_to_copy =
      COMPANION_OTA_V1_FLASH_WORD_SIZE - CompanionOtaV1StorageContext.write_value_index;
    uint32_t bytes_left = length - count;
    if(bytes_to_copy > bytes_left)
    {
      bytes_to_copy = bytes_left;
    }
    memcpy((uint8_t*)&CompanionOtaV1StorageContext.write_value +
             CompanionOtaV1StorageContext.write_value_index,
           bytes + count,
           bytes_to_copy);
    CompanionOtaV1StorageContext.write_value_index += (uint8_t)bytes_to_copy;
    count += bytes_to_copy;
    if((CompanionOtaV1StorageContext.write_value_index == COMPANION_OTA_V1_FLASH_WORD_SIZE) &&
       (Companion_Ota_V1_Flush_Word() == 0u))
    {
      return 0u;
    }
  }
  return 1u;
}

static uint8_t Companion_Ota_V1_Flush_Word(void)
{
  uint32_t pending;
  if(CompanionOtaV1StorageContext.write_value_index == 0u)
  {
    return 1u;
  }
  if(CompanionOtaV1StorageContext.write_value_index < COMPANION_OTA_V1_FLASH_WORD_SIZE)
  {
    memset((uint8_t*)&CompanionOtaV1StorageContext.write_value +
             CompanionOtaV1StorageContext.write_value_index,
           0xFF,
           COMPANION_OTA_V1_FLASH_WORD_SIZE - CompanionOtaV1StorageContext.write_value_index);
  }
  pending = 1u;
  while(pending > 0u)
  {
    pending = FD_WriteData(CompanionOtaV1StorageContext.flash_address,
                           &(CompanionOtaV1StorageContext.write_value),
                           1u);
  }
  if(*(uint64_t*)(CompanionOtaV1StorageContext.flash_address) !=
     CompanionOtaV1StorageContext.write_value)
  {
    return 0u;
  }
  CompanionOtaV1StorageContext.flash_address += COMPANION_OTA_V1_FLASH_WORD_SIZE;
  CompanionOtaV1StorageContext.write_value = 0u;
  CompanionOtaV1StorageContext.write_value_index = 0u;
  return 1u;
}

static void Companion_Ota_V1_Update_Status(void)
{
  uint8_t status[DENZIC_OTA_V1_STATUS_BYTES];
  denzic_ota_v1_set_status_flags(
    &CompanionOtaV1Context,
    DENZIC_OTA_V1_STATUS_FLAG_ACTIVE_LINK_CONFIRMED);
  if(denzic_ota_v1_encode_status(&CompanionOtaV1Context, status, sizeof(status)) == 0u)
  {
    return;
  }
  (void)aci_gatt_update_char_value(CompanionOtaV1GattContext.service_handle,
                                   CompanionOtaV1GattContext.status_char_handle,
                                   0,
                                   DENZIC_OTA_V1_STATUS_BYTES,
                                   status);
}
