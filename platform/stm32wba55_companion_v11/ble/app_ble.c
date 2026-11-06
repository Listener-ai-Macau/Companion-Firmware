/* USER CODE BEGIN Header */
/**
  ******************************************************************************
  * @file    app_ble.c
  * @author  MCD Application Team
  * @brief   BLE Application
  ******************************************************************************
  * @attention
  *
  * Copyright (c) 2022 STMicroelectronics.
  * All rights reserved.
  *
  * This software is licensed under terms that can be found in the LICENSE file
  * in the root directory of this software component.
  * If no LICENSE file comes with this software, it is provided AS-IS.
  *
  ******************************************************************************
  */
/* USER CODE END Header */

#include "main.h"
#include "ble_core.h"
#include "svc_ctl.h"
#include "baes.h"
#include "pka_ctrl.h"
#include "ble_timer.h"
#include "app_ble.h"
#include "gatt_public_hash_diagnostic.h"
#include "gatt_hash_complete.h"
#include "maintenance_protocol.h"
extern uint8_t BleStack_ctx[];
#include "host_stack_if.h"
#include "ll_sys_if.h"
#include "stm32_rtos.h"
#include "stm_list.h"
#include "advanced_memory_manager.h"
#include "blestack.h"
#include "simple_nvm_arbiter.h"
#ifndef COMPANION_WBA_EXTERNAL_BOND_NOR_ONLY
#define COMPANION_WBA_EXTERNAL_BOND_NOR_ONLY 0
#endif
#ifndef COMPANION_WBA_EXTERNAL_BOND_PROVISION
#define COMPANION_WBA_EXTERNAL_BOND_PROVISION 0
#endif
#include "wba_bond_store.h"
#include "wba_bond_seal.h"
#include "wba_storage_layout.h"
#ifndef COMPANION_WBA_EXTERNAL_BOND_STORE
#define COMPANION_WBA_EXTERNAL_BOND_STORE 0
#endif
#include "companion_gatt_stm32wb.h"
#include "ble_product.h"
#include "ble_link_budget.h"
#include "ble_packet_capacity.h"
#include "ble_directional_budget_recovery.h"
#include "ble_mtu.h"
#include "ble_event_copy.h"
#ifndef COMPANION_WBA_PEER_INDICATIONS
#define COMPANION_WBA_PEER_INDICATIONS 0
#endif
#if COMPANION_WBA_PEER_INDICATIONS
#include "ble_peer_indication.h"
static comp_v11_peer_indication_t peer_indication;
#endif
#include "diag_log.h"
#include "log_module.h"
#include "ble_route_observation.h"
#include <stdio.h>
#define BLE_GATT_BUF_SIZE BLE_TOTAL_BUFFER_SIZE_GATT(CFG_BLE_NUM_GATT_ATTRIBUTES,CFG_BLE_NUM_GATT_SERVICES,CFG_BLE_ATT_VALUE_ARRAY_SIZE)
#define BLE_HOST_EVENT_BUF_SIZE CFG_BLE_HOST_EVENT_BUF_SIZE
#define MBLOCK_COUNT CFG_BLE_MBLOCK_COUNT
#define BLE_DYN_ALLOC_SIZE BLE_TOTAL_BUFFER_SIZE(CFG_BLE_NUM_LINK,MBLOCK_COUNT,0)
/* Preserve the pinned254-word host cache independently of SNVMA pages.
 * Changing persistence must not shrink the live pairing/GATT database. */
#define BLE_HOST_NVM_SIZE_U64 254u
static uint32_t host_buffer[DIVC(BLE_DYN_ALLOC_SIZE,4)];
static uint32_t gatt_buffer[DIVC(BLE_GATT_BUF_SIZE,4)];
bool comp_v11_ble_complete_public_hash_input(uint8_t *out,size_t capacity,size_t *length)
{
    return comp_v11_complete_gatt_hash_input((uintptr_t)BleStack_ctx+COMP_V11_PINNED_GATT_SERVICE_HEAD_OFFSET,
        (uintptr_t)gatt_buffer,sizeof(gatt_buffer),out,capacity,length);
}

#if defined(COMPANION_WBA_CE_SHARED_CAPTURE) && COMPANION_WBA_CE_SHARED_CAPTURE
/* CE SRAM2 is packed against the preserved24KiB stack. Reuse remaining
 * physical SRAM1 for this bounded640-byte FIFO; ce_reset.S clears this bank.
 * No heap, capture arena, recording queue or stack budget is shortened. */
static uint16_t host_event_buffer[DIVC(BLE_HOST_EVENT_BUF_SIZE,2)]
    __attribute__((section(".sram1.bss.ble_host_events"),aligned(8)));
#else
static uint16_t host_event_buffer[DIVC(BLE_HOST_EVENT_BUF_SIZE,2)];
#endif
_Static_assert(sizeof(host_event_buffer)>=554u,"Host FIFO must fit a complete509-byte attribute event train");
static uint64_t host_nvm_buffer[BLE_HOST_NVM_SIZE_U64];
static uint8_t long_write_buffer[1],extra_data_buffer[1];
static tListNode BleAsynchEventQueue;
static AMM_VirtualMemoryCallbackFunction_t BLE_EVENTS_ResumeFlowProcessCb;
static void BLE_ResumeFlowProcessCallback(void);
#if !COMPANION_WBA_EXTERNAL_BOND_STORE
static void BLE_NvmCallback(SNVMA_Callback_Status_t status);
#endif
static uint8_t HOST_BLE_Init(void);
void Ble_UserEvtRx(void);
/* SNVMA's own per-bank CRC protects these opaque random root keys. */
static struct { uint32_t magic; uint32_t keys[8]; uint8_t address[6]; uint8_t reserved[6]; } identity;
static bool ready,advertise_pending,identity_ready;
/* 0: clear, 1: GAP stop, 2: controller stop after GAP already stopped. */
static uint8_t advertise_stop_pending;
static uint16_t connection=0xFFFFu;
static tBleStatus last_error;
static uint32_t advertising_retry;
static uint8_t advertising_link_status=0xFFu,advertising_link_mask=0xFFu;
static uint8_t advertising_stop_status=0xFFu,advertising_disable_status=0xFFu;
static uint16_t advertising_recoveries;
static uint16_t advertising_rearms;
static bool nvm_pending,nvm_busy;
static uint32_t nvm_retry;
static uint8_t host_restore_status,bonds_boot;
static uint32_t nvm_good,nvm_failed;
static bool bulk_profile;
/* Actual applied RX planning: 0 ordinary, 1 seven empty, 2 seven full. */
static uint8_t bulk_rx_profile;
/* FW268 controlled comparison: use ST's seven empty RX slots only for
 * device-to-host sealed uploads, retaining the first length exchange below.
 * Earlier empty-RX candidates also resuggested DLE; that combination dropped
 * the actual time budget. Test scheduling independently of renegotiation.
 * OTA reception and normal operation retain the bidirectional RX budget. */
static const bool bulk_empty_rx_slots=true;
/* Controlled comparison of the repeated length exchange: actual captures
 * retain the initial965/2120us through PHY2, then drop to340us around the
 * later bulk request (sometimes before the CI event). Keep the first
 * negotiation and the actual-event capacity guards. Do not resuggest or
 * align during a batch; this is a hypothesis, not a claimed peer/driver bug. */
static const bool bulk_renegotiate_dle=false;
static bool bulk_ci_requested;
/* Set when a 6/6/0/400 request is accepted, cleared by the update event.
 * Live capture may repeat that same request after the central leaves 6.
 * The callback only clears this flag; it does not send another command. */
static bool bulk_ci_wait_update;
static uint8_t bulk_ci_status=0xFFu;
static uint8_t bulk_ci_attempts;
static uint16_t bulk_ci_previous_interval;
/* Negotiation waits defer control commands only, never the payload pump.
 * Actual CI/DLE events release them; finite deadlines cover a central which
 * keeps its interval or a DLE request which changes no effective values. */
static uint32_t bulk_ci_ready_after,bulk_dle_ready_after;
static bool bulk_dle_issued,bulk_dle_waiting;
static uint8_t profile_status=0xFFu;
static uint8_t dle_attempts,dle_status=0xFFu;
/* Once per connection; only after the first initial request succeeded.
 * A second initial attempt consumes the remaining connection-wide slot.
 * Armed by actual asymmetric recovery or both-high -> both340 transition.
 * Reuse the completed initial-negotiation deadline, never add a hot timer. */
static uint8_t directional_budget_recovery;
/* Scoped once-per-batch alignment; final restoration is bounded too.
 * Never change application509-byte notification or the preferred2120us. */
static uint16_t dle_aligned_octets;
static uint8_t dle_alignment_status=0xFFu,dle_restore_status=0xFFu;
static bool dle_alignment_attempted,dle_restore_attempted;
static uint32_t dle_ready_after;
static uint32_t profile_retry;
static comp_v11_ble_mtu_t att;
/* Boot-only official capability reads distinguish supported controller limits
 * from this connection's effective DLE. Never query or print in payload work.
 * Non-success status leaves values unknown, not inferred from command acceptance. */
static struct {
    uint16_t max_tx_octets,max_tx_time,max_rx_octets,max_rx_time;
    uint16_t suggested_tx_octets,suggested_tx_time;
    uint8_t limits_status,suggested_status;
} controller_limits={.limits_status=0xFFu,.suggested_status=0xFFu};
static struct {
    uint16_t interval,latency,tx_octets,tx_time;
    uint16_t rx_octets,rx_time;
    uint8_t tx_phy,rx_phy;
} transport;
/* Sparse causal snapshots for the same sealed-file operation, never UART or
 * extra ATT reads in the payload path. Reasons: 2=CI, 3=DLE, 4=PHY,
 * 5/6=bulk profile on/off, 7=one pool sample per 256 wake events,
 * 8=foreground DLE status/state in the available word (bit7=accepted),
 * 13=bulk CI request status, 14=no-change DLE event wait expired.
 * 15=actual asymmetric recovery armed,16=one recovery command status.
 * Words: reason/latency/handle; CI/MaxTxTime; TxOctets/TxPHY/RxPHY;
 * config status/bulk enabled/available buffers. Unknown fields remain zero. */
static void transport_trace(uint8_t reason,uint16_t available)
{
    comp_diag_log_record_code(COMP_DIAG_EVT_BLE_TRANSPORT,COMP_DIAG_SEV_INFO,
        reason|((uint32_t)transport.latency<<8)|((uint32_t)connection<<16),
        transport.interval|((uint32_t)transport.tx_time<<16),
        transport.tx_octets|((uint32_t)transport.tx_phy<<16)|((uint32_t)transport.rx_phy<<24),
        profile_status|((uint32_t)bulk_rx_profile<<8)|((uint32_t)available<<16));
}
/* Reasons32..39 are receive-shape observations, not link parameters.
 * Reuse the existing bounded ring; overwritten records remain partial. */
void comp_v11_ble_rx_shape_trace(uint8_t stage,uint8_t why,uint8_t type,uint8_t event,
    uint16_t primary,uint16_t extension,uint8_t plen,uint16_t attribute,
    uint16_t offset,uint16_t length)
{
    comp_diag_log_record_code(COMP_DIAG_EVT_BLE_TRANSPORT,COMP_DIAG_SEV_INFO,
        stage|((uint32_t)why<<8)|((uint32_t)type<<16)|((uint32_t)event<<24),
        primary|((uint32_t)extension<<16),attribute|((uint32_t)length<<16),
        offset|((uint32_t)plen<<16));
}
static void rx_indication_shape(uint8_t stage,uint8_t why,const uint8_t *data,
    uint16_t length,const uint8_t *ext,uint16_t ext_length)
{
    uint32_t total=(uint32_t)length+ext_length;
    if(!data || !length || (ext_length&&!ext))return;
    if(data[0]==HCI_ACLDATA_PKT_TYPE) {
        if(total>258u)comp_v11_ble_rx_shape_trace(39u,why,data[0],0u,length,ext_length,0u,0u,0u,0u);
        return;
    }
    if(data[0]!=HCI_EVENT_PKT_TYPE || total<3u)return;
    uint8_t h[13];uint16_t n=length<sizeof(h)?length:(uint16_t)sizeof(h);
    memcpy(h,data,n);
    if(n<sizeof(h) && total>=sizeof(h))memcpy(h+n,ext,sizeof(h)-n);
    bool modified=total>=sizeof(h) && h[1]==0xffu &&
        ((uint16_t)h[3]|((uint16_t)h[4]<<8))==ACI_GATT_ATTRIBUTE_MODIFIED_VSEVT_CODE;
    uint16_t attribute=0u,offset=0u,value_length=0u;
    if(modified) {
        attribute=(uint16_t)h[7]|((uint16_t)h[8]<<8);
        offset=(uint16_t)h[9]|((uint16_t)h[10]<<8);
        value_length=(uint16_t)h[11]|((uint16_t)h[12]<<8);
    }
    if(total>258u || (modified && (value_length>244u || offset)))
        comp_v11_ble_rx_shape_trace(stage,why,h[0],h[1],length,ext_length,h[2],attribute,offset,value_length);
}
/* A small persistent cause snapshot survives a rebond/disconnect loop
 * that can overwrite the diagnostic ring. Write no UART from HCI callbacks. */
static struct {
    uint32_t disconnects,secured_disconnects,last_disconnect_ms;
    uint32_t first_secured_disconnect_ms,first_bond_lost_ms;
    uint8_t last_reason,last_secured_reason,last_was_secured,first_secured_reason;
    uint8_t encryption_status,encryption_enabled;
    uint8_t unsecured_reason,unsecured_allowed;
} link_history={.last_reason=0xFFu,.last_secured_reason=0xFFu,.first_secured_reason=0xFFu,
    .encryption_status=0xFFu,.unsecured_reason=0xFFu};
_Static_assert(sizeof(link_history)==28u,"BLE link cause snapshot size");
static bool radio_enabled=true,auto_reconnect=true,advertising,connection_secured,connection_allowed,reconnect_requested;
static uint32_t pairing_until;
static comp_v11_ble_security_stats_t security_stats={.pairing_status=0xFFu,.pairing_reason=0xFFu,
    .pairing_failure_status=0xFFu,.pairing_failure_reason=0xFFu};
static uint8_t local_name[COMP_PREFS_NAME_BYTES]=COMP_PREFS_DEFAULT_NAME,
    local_name_length=COMP_PREFS_DEFAULT_NAME_BYTES;
static uint16_t gap_service,gap_name;
bool comp_v11_ble_host_ready(void) { return ready && !comp_v11_ble_public_hash_fault(); }
uint8_t comp_v11_ble_host_error(void) { return last_error; }
uint16_t comp_v11_ble_connection(void) { return connection; }
uint16_t comp_v11_ble_connection_interval(void) { return transport.interval; }
void comp_v11_ble_link_budget(uint8_t out[20])
{
    comp_v11_ble_link_budget_t s={0};
    if(connection!=0xFFFFu) {
        s.flags=1u|(connection_secured?2u:0u);
        if(transport.tx_octets && transport.tx_time && transport.rx_octets && transport.rx_time) {
            s.flags|=4u;s.tx_octets=transport.tx_octets;s.tx_time=transport.tx_time;
            s.rx_octets=transport.rx_octets;s.rx_time=transport.rx_time;
        }
        if(transport.tx_phy && transport.rx_phy) {
            s.flags|=8u;s.tx_phy=transport.tx_phy;s.rx_phy=transport.rx_phy;
        }
        s.interval=transport.interval;s.mtu=att.mtu;
    }
    comp_v11_ble_link_budget_encode(out,&s);
}
uint16_t comp_v11_ble_value_capacity(void) { return comp_v11_ble_mtu_value_capacity(&att); }
bool comp_v11_ble_notifications_allowed(void) { return !comp_v11_ble_public_hash_fault() && comp_v11_ble_mtu_notifications_allowed(&att); }
uint16_t comp_v11_ble_recording_capacity(void) {
    return comp_v11_ble_bulk_compact_capacity(comp_v11_ble_value_capacity(),
        transport.tx_octets,transport.tx_time,transport.tx_phy,transport.interval,
        (uint8_t)bulk_profile);
}
const comp_v11_ble_security_stats_t *comp_v11_ble_security_stats(void) { return &security_stats; }
static void record_error(tBleStatus status)
{
    if(last_error!=status)
        comp_diag_log_record_code(COMP_DIAG_EVT_BLE_HOST_ERROR,COMP_DIAG_SEV_ERROR,
            status,ready,connection,advertising);
    last_error=status;
}
static bool check(tBleStatus status)
{ if(status==BLE_STATUS_SUCCESS)return true;record_error(status);return false; }
#if !COMPANION_WBA_EXTERNAL_BOND_STORE
static void identity_written(SNVMA_Callback_Status_t status)
{
    identity_ready=status==SNVMA_OPERATION_COMPLETE;
    if(!identity_ready)record_error(0xFDu);
}
#endif

#if COMPANION_WBA_EXTERNAL_BOND_STORE
/* Explicit existing-device migration candidate. The old internal pages remain
 * allocated; reclaiming them is a later matched App/Boot/install layout. */
static companion_spi_nor_stm32wba_t *external_nor;
static comp_bond_store_t external_store;
#if !COMPANION_WBA_EXTERNAL_BOND_NOR_ONLY
static uint64_t external_marker;
#endif
static uint32_t external_revision;
#if !COMPANION_WBA_EXTERNAL_BOND_NOR_ONLY
static uint8_t external_marker_reply;
#endif
static bool external_mutations_allowed,external_backend_ready;
#define EXTERNAL_MARKER_BASE UINT64_C(0x314d424e)
#define EXTERNAL_IMPORTING (EXTERNAL_MARKER_BASE | (UINT64_C(1)<<32))
#define EXTERNAL_COMMITTED (EXTERNAL_MARKER_BASE | (UINT64_C(2)<<32))

void comp_v11_ble_bond_media_bind(companion_spi_nor_stm32wba_t *nor)
{external_nor=nor;}
static bool external_read(void *c,uint32_t at,uint8_t *p,size_t n)
{return companion_spi_nor_stm32wba_read(c,at,p,n)==COMPANION_SPI_NOR_STM32WBA_OK;}
static bool external_program(void *c,uint32_t at,const uint8_t *p,size_t n)
{return external_mutations_allowed &&
    companion_spi_nor_stm32wba_program(c,at,p,n)==COMPANION_SPI_NOR_STM32WBA_OK;}
static comp_bond_io_t external_erase(void *c,uint32_t at)
{
    companion_spi_nor_stm32wba_t *nor=c;
    if(nor->erase_active && (nor->erase_address!=at || nor->erase_bytes!=4096u))
        return COMP_BOND_IO_PENDING;
    if(!external_mutations_allowed && !nor->erase_active)return COMP_BOND_IO_PENDING;
    companion_spi_nor_stm32wba_status_t result=external_mutations_allowed?
        companion_spi_nor_stm32wba_erase_step(nor,at,4096u):
        companion_spi_nor_stm32wba_erase_finish_poll(nor,at,4096u);
    if(result==COMPANION_SPI_NOR_STM32WBA_OK)return COMP_BOND_IO_OK;
    /* Even an I/O failure cannot relinquish uncertain physical WIP. */
    if(nor->erase_active || result==COMPANION_SPI_NOR_STM32WBA_PENDING)return COMP_BOND_IO_PENDING;
    return COMP_BOND_IO_ERROR;
}
static bool external_span(uint32_t at,uint8_t *bytes,size_t n,bool restoring)
{
    const size_t host_bytes=sizeof(host_nvm_buffer),total=host_bytes+sizeof(identity);
    if(at>total || n>total-at)return false;
    while(n) {
        uint8_t *memory;size_t available;
        if(at<host_bytes){memory=(uint8_t*)host_nvm_buffer+at;available=host_bytes-at;}
        else {memory=(uint8_t*)&identity+(at-host_bytes);available=total-at;}
        size_t take=n<available?n:available;
        if(restoring)memcpy(memory,bytes,take);else memcpy(bytes,memory,take);
        at+=(uint32_t)take;bytes+=take;n-=take;
    }
    return true;
}
static bool external_source(void *c,uint32_t at,uint8_t *p,size_t n)
{(void)c;return external_span(at,p,n,false);}
static bool external_restore(void *c,uint32_t at,const uint8_t *p,size_t n)
{(void)c;return external_span(at,(uint8_t *)(uintptr_t)p,n,true);}
static uint32_t external_source_revision(void *c){(void)c;return external_revision;}
#if !COMPANION_WBA_EXTERNAL_BOND_NOR_ONLY
static void external_marker_written(SNVMA_Callback_Status_t status)
{external_marker_reply=status==SNVMA_OPERATION_COMPLETE?1u:2u;}
static bool external_write_marker(uint64_t marker)
{
    /* Startup only, before HOST_BLE_Init. There is no capture or radio event
     * processing here; APPE still holds its documented Flash RFTS bypass. */
    external_marker=marker;external_marker_reply=0u;
    if(SNVMA_Write(dummy_SNVMA_BufferId_1_3,external_marker_written)!=SNVMA_ERROR_OK)return false;
    uint32_t started=HAL_GetTick();
    while(!external_marker_reply && HAL_GetTick()-started<2000u)
        UTIL_SEQ_Run(1u<<CFG_TASK_FLASH_MANAGER);
    return external_marker_reply==1u;
}
static bool external_boot_restore(bool internal_valid)
{
    if(!external_nor || !companion_spi_nor_stm32wba_ready(external_nor) ||
       external_nor->erase_active || !external_nor->erase_suspend_supported)return false;
    comp_bond_config_t config={0};config.read=external_read;config.program=external_program;
    config.erase_step=external_erase;config.source_read=external_source;config.restore=external_restore;
    config.source_revision=external_source_revision;config.context=external_nor;
    config.bank[0]=COMP_WBA_NOR_BOND_A;config.bank[1]=COMP_WBA_NOR_BOND_B;
    config.payload_bytes=sizeof(host_nvm_buffer)+sizeof(identity);
    if(!comp_v11_hal_device_uid(config.uid) || COMP_WBA_NOR_BOND_PROTECTED_END>external_nor->info.size_bytes)return false;
    if(SNVMA_Register(dummy_SNVMA_BufferId_1_3,(uint32_t*)&external_marker,sizeof(external_marker)/4u)!=SNVMA_ERROR_OK)return false;
    SNVMA_Cmd_Status_t marker_status=SNVMA_Restore(dummy_SNVMA_BufferId_1_3);
    if(marker_status==SNVMA_ERROR_OK) {
        if(external_marker!=EXTERNAL_IMPORTING && external_marker!=EXTERNAL_COMMITTED)return false;
    } else if(marker_status==SNVMA_ERROR_BUFFER_CONFIG_MISSMATCH && internal_valid) {
        /* The validated old two-buffer bank has no migration receipt yet. */
        external_marker=0u;
    } else return false;
    comp_bond_result_t result=comp_bond_store_mount(&external_store,&config);
    /* A valid-looking image without our durable ownership receipt is not
     * authority to replace the current internal keys on this first migration. */
    if(result==COMP_BOND_READY && external_marker==0u)return false;
    if(result!=COMP_BOND_READY) {
        if(!internal_valid || external_marker==EXTERNAL_COMMITTED ||
           (result!=COMP_BOND_EMPTY && !(result==COMP_BOND_CORRUPT && external_marker==EXTERNAL_IMPORTING)))
            return false;
        /* Establish durable erase authority BEFORE the first external write.
         * A later corrupt committed store may never resurrect old peers. */
        if(external_marker!=EXTERNAL_IMPORTING && !external_write_marker(EXTERNAL_IMPORTING))return false;
        external_mutations_allowed=true;nvm_busy=true;
        result=comp_bond_store_import_begin(&external_store);
        uint32_t started=HAL_GetTick();
        while(result==COMP_BOND_PENDING && HAL_GetTick()-started<3000u)
            result=comp_bond_store_step(&external_store);
        external_mutations_allowed=false;
        if(result!=COMP_BOND_READY)return false;
    }
    if(identity.magic!=0x31494243u || (identity.address[5]&0xc0u)!=0xc0u)return false;
    if(external_marker!=EXTERNAL_COMMITTED && !external_write_marker(EXTERNAL_COMMITTED))return false;
    /* Seal existing-device authority before an installer may reclaim SNVMA.
     * A torn same seal resumes without erase; never starts a new identity. */
    external_mutations_allowed=true;
    comp_bond_seal_result_t seal=comp_bond_seal_complete_migration(&config,COMP_WBA_NOR_BOND_SEAL);
    external_mutations_allowed=false;
    if(seal!=COMP_BOND_SEAL_COMPLETE)return false;
    nvm_busy=false;external_backend_ready=true;identity_ready=true;
    host_restore_status=SNVMA_ERROR_OK;return true;
}
#else
static bool external_boot_restore(void)
{
    /* The matched NVM0 target deliberately contains no SNVMA fallback or
     * internal migration receipt. The bridge must publish and verify BND1
     * before installation may reclaim its old internal pages. */
    if(!external_nor || !companion_spi_nor_stm32wba_ready(external_nor) ||
       external_nor->erase_active || !external_nor->erase_suspend_supported)return false;
    comp_bond_config_t config={0};config.read=external_read;config.program=external_program;
    config.erase_step=external_erase;config.source_read=external_source;config.restore=external_restore;
    config.source_revision=external_source_revision;config.context=external_nor;
    config.bank[0]=COMP_WBA_NOR_BOND_A;config.bank[1]=COMP_WBA_NOR_BOND_B;
    config.payload_bytes=sizeof(host_nvm_buffer)+sizeof(identity);
    if(!comp_v11_hal_device_uid(config.uid) || COMP_WBA_NOR_BOND_PROTECTED_END>external_nor->info.size_bytes)return false;
    comp_bond_result_t result=comp_bond_store_mount(&external_store,&config);
    comp_bond_seal_result_t seal=comp_bond_seal_inspect(&config,COMP_WBA_NOR_BOND_SEAL);
#if COMPANION_WBA_EXTERNAL_BOND_PROVISION
    /* Explicit DEV new-board profile. Establish durable first intent BEFORE
     * generating keys. Completed/foreign/corrupt stores never gain this right.
     * Only a torn compatible intent with BOTH whole bond pages still blank
     * may be completed without erasing the permanent provisioning sector. */
    if(result==COMP_BOND_EMPTY && (seal==COMP_BOND_SEAL_BLANK || seal==COMP_BOND_SEAL_INVALID)) {
        external_mutations_allowed=true;
        seal=comp_bond_seal_begin_new(&config,COMP_WBA_NOR_BOND_SEAL,true);
        external_mutations_allowed=false;
    }
    if(seal==COMP_BOND_SEAL_NEW_PENDING && result!=COMP_BOND_READY) {
        if(result!=COMP_BOND_EMPTY && result!=COMP_BOND_CORRUPT)return false;
        /* No host or advertisement has run before COMPLETE. Torn first data
         * may restart under this explicit intent; no existing peers exist yet. */
        uint32_t random[2];memset(host_nvm_buffer,0xff,sizeof(host_nvm_buffer));
        memset(&identity,0,sizeof(identity));
        for(unsigned i=0;i<8u;++i)if(!comp_v11_ble_entropy(&identity.keys[i]))return false;
        if(!comp_v11_ble_entropy(&random[0]) || !comp_v11_ble_entropy(&random[1]))return false;
        memcpy(identity.address,random,6u);identity.address[5]|=0xc0u;identity.magic=0x31494243u;
        external_mutations_allowed=true;result=comp_bond_store_import_begin(&external_store);
        uint32_t started=HAL_GetTick();
        while(result==COMP_BOND_PENDING && HAL_GetTick()-started<3000u)
            result=comp_bond_store_step(&external_store);
        external_mutations_allowed=false;
    }
#endif
    if(result!=COMP_BOND_READY || identity.magic!=0x31494243u ||
       (identity.address[5]&0xc0u)!=0xc0u)return false;
    /* A valid first image after interrupted publication retains its identity.
     * Finish the monotone seal before HOST_BLE_Init, including on a normal
     * NOR-only image without the first-provision compile option. */
    if(seal==COMP_BOND_SEAL_NEW_PENDING) {
        external_mutations_allowed=true;
        seal=comp_bond_seal_complete_new(&config,COMP_WBA_NOR_BOND_SEAL);
        external_mutations_allowed=false;
    }
    if(seal!=COMP_BOND_SEAL_COMPLETE)return false;
    nvm_busy=false;external_backend_ready=true;identity_ready=true;
    host_restore_status=0u;return true;
}
#endif
static void external_nvm_poll(uint32_t now,bool writes_allowed)
{
    if(!external_backend_ready || (int32_t)(now-nvm_retry)<0)return;
    if(external_nor->erase_active && (external_nor->erase_address!=external_store.config.bank[external_store.target] ||
       external_nor->erase_bytes!=4096u))return;
    external_mutations_allowed=writes_allowed;
    comp_bond_result_t result;
    if(!nvm_busy) {
        if(!writes_allowed || !nvm_pending || external_nor->erase_active)return;
        nvm_pending=false;nvm_busy=true;result=comp_bond_store_begin(&external_store);
    } else {
        /* A revoked write gate may only retire an already-finished erase.
         * Never resume/program during recording or an update's metadata work. */
        if(!writes_allowed && !external_nor->erase_active)return;
        result=comp_bond_store_step(&external_store);
    }
    if(result==COMP_BOND_PENDING)return;
    nvm_busy=false;
    if(result==COMP_BOND_READY)++nvm_good;
    else {++nvm_failed;nvm_pending=true;nvm_retry=now+1000u;}
}
#else
void comp_v11_ble_bond_media_bind(companion_spi_nor_stm32wba_t *nor){(void)nor;}
#endif

/* Initial LL failures and unowned disconnects used to be invisible in
 * GAP1. Twelve bytes retain their cause without keys, allocations, UART or
 * new controller commands in the callback. This does not re-arm/re-pair. */
static struct {
    uint32_t last_ms;
    uint16_t seen,failed,unowned;
    uint8_t kind,code;
} initial_link_observation;
_Static_assert(sizeof(initial_link_observation)==12u,"initial link observation budget");
static void initial_link_observe(uint8_t kind,uint8_t code,uint16_t handle,bool unowned)
{
    if(unowned) {
        if(initial_link_observation.unowned!=UINT16_MAX)++initial_link_observation.unowned;
    } else {
        if(initial_link_observation.seen!=UINT16_MAX)++initial_link_observation.seen;
        if(code && initial_link_observation.failed!=UINT16_MAX)++initial_link_observation.failed;
    }
    initial_link_observation.last_ms=HAL_GetTick();
    initial_link_observation.kind=kind;initial_link_observation.code=code;
    comp_diag_log_record_code(COMP_DIAG_EVT_BLE_SECURITY,
        code?COMP_DIAG_SEV_WARN:COMP_DIAG_SEV_INFO,
        0x80000000u|kind,handle,code,unowned?1u:0u);
}
static bool pairing_open(void) {return pairing_until && (int32_t)(pairing_until-HAL_GetTick())>0;}
static void pairing_result(uint8_t status,uint8_t reason)
{
    security_stats.pairing_status=status;security_stats.pairing_reason=reason;
    if(status){security_stats.pairing_failure_status=status;security_stats.pairing_failure_reason=reason;}
}
void comp_v11_ble_maintenance_diagnostics(uint8_t response[32])
{
    const uint32_t now=HAL_GetTick();
    const bool failed=security_stats.pairing_failure_status!=0xFFu;
    response[6]=(uint8_t)((radio_enabled?1u:0u)|(advertising?2u:0u)|(pairing_open()?4u:0u)|
        (connection!=0xFFFFu?8u:0u)|(connection_allowed?16u:0u)|(connection_secured?32u:0u)|
        (failed?64u:0u)|(link_history.unsecured_allowed?128u:0u));
    response[7]=last_error;
    response[12]=failed?security_stats.pairing_failure_status:security_stats.pairing_status;
    response[13]=failed?security_stats.pairing_failure_reason:security_stats.pairing_reason;
    response[14]=link_history.unsecured_reason;response[15]=link_history.encryption_status;
    comp_maint_put32(response+16u,pairing_until&&(int32_t)(pairing_until-now)>0?pairing_until-now:0u);
    comp_maint_put32(response+20u,(uint32_t)initial_link_observation.seen|((uint32_t)initial_link_observation.failed<<16u));
    const uint32_t lost=security_stats.bond_lost_events>UINT16_MAX?UINT16_MAX:security_stats.bond_lost_events;
    const uint32_t retried=security_stats.rebond_attempts>UINT16_MAX?UINT16_MAX:security_stats.rebond_attempts;
    comp_maint_put32(response+24u,lost|(retried<<16u));
}
static void connection_opened(uint16_t handle,uint8_t type,const uint8_t *address)
{
    uint8_t identity_type,identity_address[6];
    connection=handle;advertising=false;connection_secured=false;connection_allowed=false;
#if COMPANION_WBA_PEER_INDICATIONS
    comp_v11_peer_indication_reset(&peer_indication);
#endif
    bulk_ci_requested=false;bulk_ci_previous_interval=0u;
    bulk_ci_attempts=0u;bulk_ci_wait_update=false;
    bulk_ci_ready_after=bulk_dle_ready_after=0u;
    bulk_dle_issued=bulk_dle_waiting=false;
    dle_attempts=0u;dle_status=0xFFu;directional_budget_recovery=0u;
    dle_aligned_octets=0u;dle_alignment_attempted=false;dle_restore_attempted=false;
    dle_alignment_status=0xFFu;dle_restore_status=0xFFu;
    dle_ready_after=HAL_GetTick()+2000u;
    comp_v11_ble_mtu_open(&att,HAL_GetTick());
    memset(&transport,0,sizeof(transport));
    if(!radio_enabled || (!pairing_open() &&
       aci_gap_check_bonded_device(type&1u,address,&identity_type,identity_address)!=BLE_STATUS_SUCCESS)) {
        (void)hci_disconnect(handle,0x13u);return;
    }
    connection_allowed=true;comp_v11_ble_link(true,false);
    /* Prompt the central to establish encryption before private attributes.
     * Negotiation failures leave the privacy gate shut; no unsecured fallback. */
    (void)check(aci_gap_peripheral_security_req(handle));
    /* DLE follows completed encryption in an allowed foreground command slot.
     * Do not discard an early request's result during security negotiation. */
}
void comp_v11_ble_apply_preferences(const comp_preferences_values_t *v)
{
    if(!v || !comp_preferences_valid(v))return;
    bool changed=local_name_length!=v->name_length || memcmp(local_name,v->name,v->name_length)!=0;
    radio_enabled=v->radio_enabled;auto_reconnect=v->policy.auto_reconnect;
    local_name_length=v->name_length;memcpy(local_name,v->name,local_name_length);
    if(!ready)return;
    if(changed) {
        (void)check(aci_gatt_update_char_value(gap_service,gap_name,0,local_name_length,local_name));
        if(advertising) {(void)aci_gap_set_non_discoverable();advertising=false;advertise_pending=true;}
    }
    if(!radio_enabled) {
        if(advertising)(void)aci_gap_set_non_discoverable();
        advertising=false;advertise_pending=false;advertise_stop_pending=false;
        if(connection!=0xFFFFu)(void)hci_disconnect(connection,0x13u);
    } else if(connection==0xFFFFu && !advertising)advertise_pending=true;
}
bool comp_v11_ble_reconnect(bool pairing)
{
    if(!ready || !radio_enabled)return false;
    if(connection!=0xFFFFu) {
        if(!check(hci_disconnect(connection,0x13u)))return false;
        reconnect_requested=true;
        if(pairing)pairing_until=HAL_GetTick()+120000u;
        return true;
    }
    /* An explicit local reconnect must re-arm GAP even when our cached flag
     * still says advertising. The foreground owns stop/start; bonds, identity
     * and the finite pairing authorization remain unchanged. */
    if(pairing)pairing_until=HAL_GetTick()+120000u;
    advertise_pending=true;advertise_stop_pending=true;
    advertising_retry=HAL_GetTick();return true;
}
bool comp_v11_ble_open_pairing_window(void)
{
    if(!ready||!radio_enabled)return false;
    pairing_until=HAL_GetTick()+120000u;
    if(connection==0xFFFFu)advertise_pending=true;
    return true;
}
bool comp_v11_ble_clear_bonds(void)
{
    if(!ready||!radio_enabled||nvm_pending||nvm_busy)return false;
    if(aci_gap_clear_security_db()!=BLE_STATUS_SUCCESS)return false;
    /* Persist the SDK's existing key cache through the original NOR owner.
     * Keep the current encrypted link long enough to report the durable result. */
    APP_BLE_HostNvmStore();
    return comp_v11_ble_open_pairing_window();
}
bool comp_v11_ble_bond_count(uint8_t *count)
{
    if(!count||!ready||nvm_pending||nvm_busy)return false;
    Bonded_Device_Entry_t peers[36];uint8_t n=0u;
    if(aci_gap_get_bonded_devices(&n,peers)!=BLE_STATUS_SUCCESS)return false;
    *count=n;return true;
}
uint32_t comp_v11_ble_bond_generation(void)
{
#if COMPANION_WBA_EXTERNAL_BOND_STORE
    return external_store.generation;
#else
    return nvm_good;
#endif
}
uint32_t comp_v11_ble_bond_failures(void){return nvm_failed;}
void APP_BLE_Init(void)
{
    uint16_t gap,name,appearance; uint8_t no_extra_gap_records=0;
    LST_init_head(&BleAsynchEventQueue);
    UTIL_SEQ_RegTask(1U<<CFG_TASK_BLE_HOST,UTIL_SEQ_RFU,BleStack_Process_BG);
    UTIL_SEQ_RegTask(1U<<CFG_TASK_HCI_ASYNCH_EVT_ID,UTIL_SEQ_RFU,Ble_UserEvtRx);
#if COMPANION_WBA_EXTERNAL_BOND_NOR_ONLY
    if(!external_boot_restore()) {record_error(0xF6u);return;}
#else
    if(SNVMA_Register(APP_BLE_Host_SNVMA_BufferId_1_1,(uint32_t*)host_nvm_buffer,sizeof(host_nvm_buffer)/4)!=SNVMA_ERROR_OK ||
       SNVMA_Register(dummy_SNVMA_BufferId_1_2,(uint32_t*)&identity,sizeof(identity)/4)!=SNVMA_ERROR_OK) { record_error(0xFFu);return; }
    host_restore_status=(uint8_t)SNVMA_Restore(APP_BLE_Host_SNVMA_BufferId_1_1);
    identity_ready=SNVMA_Restore(dummy_SNVMA_BufferId_1_2)==SNVMA_ERROR_OK &&
        identity.magic==0x31494243u && (identity.address[5]&0xC0u)==0xC0u;
#if COMPANION_WBA_EXTERNAL_BOND_STORE
    if(!external_boot_restore(identity_ready && host_restore_status==SNVMA_ERROR_OK)) {record_error(0xF6u);return;}
#else
    if(!identity_ready) {
        uint32_t random[2];
        memset(&identity,0,sizeof(identity));
        for(unsigned i=0;i<8u;++i) if(!comp_v11_ble_entropy(&identity.keys[i])) {record_error(0xFEu);return;}
        if(!comp_v11_ble_entropy(&random[0]) || !comp_v11_ble_entropy(&random[1])) {record_error(0xFEu);return;}
        memcpy(identity.address,random,6); identity.address[5]|=0xC0u;
        identity.magic=0x31494243u;
        if(SNVMA_Write(dummy_SNVMA_BufferId_1_2,identity_written)!=SNVMA_ERROR_OK) {record_error(0xFDu);return;}
    }
#endif
#endif /* internal or migration startup */
    BAES_Reset(); PKACTRL_Reset(); BLE_TIMER_Init();
    if(!check(HOST_BLE_Init()))return;
    if(!check(aci_hal_write_config_data(CONFIG_DATA_GAP_ADD_REC_NBR_OFFSET,CONFIG_DATA_GAP_ADD_REC_NBR_LEN,&no_extra_gap_records)) ||
       !check(aci_hal_write_config_data(CONFIG_DATA_IR_OFFSET,CONFIG_DATA_IR_LEN,(uint8_t*)identity.keys)) ||
       !check(aci_hal_write_config_data(CONFIG_DATA_ER_OFFSET,CONFIG_DATA_ER_LEN,(uint8_t*)&identity.keys[4])) ||
       /* GAP keeps its own static-random identity. Setting the controller only
        * via HCI is insufficient: GAP_Set_Own_Address replaces it from this
        * host config on advertising, otherwise with the all-zero default. */
       !check(aci_hal_write_config_data(CONFIG_DATA_RANDOM_ADDRESS_OFFSET,CONFIG_DATA_RANDOM_ADDRESS_LEN,identity.address)) ||
       !check(aci_hal_set_tx_power_level(1,CFG_TX_POWER)) || !check(aci_gatt_init()) ||
       !check(aci_gap_init(GAP_PERIPHERAL_ROLE,PRIVACY_DISABLED,COMP_PREFS_NAME_BYTES,&gap,&name,&appearance)) ||
       !check(hci_le_set_random_address(identity.address)) ||
       !check(aci_gatt_update_char_value(gap,name,0,local_name_length,local_name)) ||
       !check(aci_gap_set_io_capability(IO_CAP_NO_INPUT_NO_OUTPUT)) ||
       !check(aci_gap_set_authentication_requirement(1,MITM_PROTECTION_NOT_REQUIRED,SC_PAIRING_OPTIONAL,
          KEYPRESS_NOT_SUPPORTED,16,16,USE_FIXED_PIN_FOR_PAIRING_FORBIDDEN,0,GAP_STATIC_RANDOM_ADDR)))return;
    SVCCTL_Init();
    if(!check(companion_gatt_stm32wb_init()))return;
    comp_diag_log_record_code(COMP_DIAG_EVT_GATT_SERVICE_READY,COMP_DIAG_SEV_INFO,
        COMPANION_GATT_CHAR_COUNT,0u,0u,0u);
    (void)hci_le_set_default_phy(0,HCI_TX_PHYS_LE_2M_PREF,HCI_RX_PHYS_LE_2M_PREF);
    /* Establish the suggested packet budget before a central opens a link.
     * Per-connection requests remain bounded and actual negotiated timing
     * still comes only from DATA_LENGTH_CHANGE, never this command result. */
    (void)check(hci_le_write_suggested_default_data_length(251u,2120u));
    uint16_t tx_octets=0u,tx_time=0u,rx_octets=0u,rx_time=0u;
    controller_limits.limits_status=hci_le_read_maximum_data_length(
        &tx_octets,&tx_time,&rx_octets,&rx_time);
    if(controller_limits.limits_status==BLE_STATUS_SUCCESS) {
        controller_limits.max_tx_octets=tx_octets;controller_limits.max_tx_time=tx_time;
        controller_limits.max_rx_octets=rx_octets;controller_limits.max_rx_time=rx_time;
    }
    tx_octets=0u;tx_time=0u;
    controller_limits.suggested_status=hci_le_read_suggested_default_data_length(&tx_octets,&tx_time);
    if(controller_limits.suggested_status==BLE_STATUS_SUCCESS) {
        controller_limits.suggested_tx_octets=tx_octets;controller_limits.suggested_tx_time=tx_time;
    }
    gap_service=gap;gap_name=name;
    /* HCI response is at most 255 bytes, hence at most 36 seven-byte peers. */
    Bonded_Device_Entry_t peers[36];uint8_t count=0;
    if(!check(aci_gap_get_bonded_devices(&count,peers)))return;
    bonds_boot=count;
    if(count==0u)pairing_until=HAL_GetTick()+120000u;
    ready=true; advertise_pending=radio_enabled;
}
void comp_v11_ble_advertise_poll(uint32_t now,bool commands_allowed)
{
    if(!ready || !commands_allowed)return;
    if(comp_v11_ble_public_hash_fault()) {
        if(connection!=0xFFFFu)(void)hci_disconnect(connection,0x13u);
        comp_v11_ble_link(false,false);ready=false;advertise_pending=false;record_error(0xFBu);return;
    }
#if COMPANION_WBA_PEER_INDICATIONS
    /* The shared control slot is available after audio service even while
     * recording; the bulk/NVM mutation gate is deliberately closed then.
     * Confirm public peer metadata only here, before advertising work. No
     * private access, discovery, Flash mutation or bulk negotiation is enabled.
     * One admitted command, then return to the cooperative scheduler. */
    if(comp_v11_peer_indication_due(&peer_indication,connection,connection_allowed&&radio_enabled,
        commands_allowed,now)) {
        tBleStatus status=aci_gatt_confirm_indication(connection);
        comp_v11_peer_indication_result(&peer_indication,status,
            status==BLE_STATUS_BUSY || status==BLE_STATUS_INSUFFICIENT_RESOURCES,HAL_GetTick());
        comp_diag_log_record_code(COMP_DIAG_EVT_BLE_TRANSPORT,
            status?COMP_DIAG_SEV_WARN:COMP_DIAG_SEV_INFO,0x494e4401u,
            connection,peer_indication.attribute,status);
        return;
    }
#endif
    /* Bounded retry: stack busy never causes a tight ACI loop. */
    uint8_t name[1u+COMP_PREFS_NAME_BYTES];name[0]=AD_TYPE_COMPLETE_LOCAL_NAME;
    memcpy(name+1,local_name,local_name_length);
    if(connection!=0xFFFFu && !connection_secured && pairing_until && !pairing_open()) {
        pairing_until=0;(void)hci_disconnect(connection,0x13u);
    }
    if(!radio_enabled || connection!=0xFFFFu || !identity_ready || (int32_t)(now-advertising_retry)<0)return;
    if(!advertise_pending) {
        if(!advertising)return;
        /* Reconcile with the SDK link state while disconnected only. Never
         * treat a failed query or another active role as an idle controller,
         * and never stop a healthy advertisement as a periodic workaround. */
        uint8_t links[22]={0};uint16_t handles[22];
        advertising_retry=now+10000u;
        advertising_link_status=aci_hal_get_link_status_v2(links,handles);
        advertising_link_mask=0xFFu;
        if(advertising_link_status!=BLE_STATUS_SUCCESS)return;
        advertising_link_mask=0u;
        for(unsigned i=0;i<sizeof(links);++i)
            advertising_link_mask|=links[i]==1u?1u:links[i]?2u:0u;
        if(advertising_link_mask)return;
        ++advertising_recoveries;advertise_pending=true;
        return;
    }
    if(advertise_stop_pending || advertising) {
        /* Clear the GAP state before enabling again, in separate foreground
         * turns. Keep pending on failure, using the existing bounded retry. */
        tBleStatus stopped;
        if(advertise_stop_pending==2u) {
            advertising_disable_status=hci_le_set_advertising_enable(0u);
            stopped=advertising_disable_status;
        } else {
            advertising_disable_status=0xFFu;
            advertising_stop_status=aci_gap_set_non_discoverable();
            stopped=advertising_stop_status;
        }
        /* After a disconnect GAP can already be non-discoverable (0x0c).
         * Still require a successful controller disable before re-enabling;
         * do not turn the rejected GAP command into a successful stop. */
        if(advertise_stop_pending!=2u && stopped==HCI_COMMAND_DISALLOWED_ERR_CODE) {
            /* One controller command per admitted foreground audio window.
             * The normal next turn performs the required controller disable. */
            advertise_stop_pending=2u;
            advertising_retry=now+1u;
            return;
        }
        if(check(stopped)) {
            advertising=false;advertise_stop_pending=false;++advertising_rearms;
        }
        else advertising_retry=now+1000u;
        return;
    }
    if(check(aci_gap_set_discoverable(ADV_IND,160,240,GAP_STATIC_RANDOM_ADDR,NO_WHITE_LIST_USE,
         (uint8_t)(local_name_length+1u),name,0,NULL,0,0))) {
        advertise_pending=false;advertising=true;advertising_retry=now+10000u;
        comp_diag_log_record_code(COMP_DIAG_EVT_BLE_ADVERTISING,COMP_DIAG_SEV_INFO,
            1u,pairing_open(),local_name_length,0u);
    }
    else advertising_retry=now+1000u;
}
void comp_v11_ble_bulk_profile(comp_v11_ble_bulk_direction_t direction,bool interval_hint,
    bool commands_allowed,bool restore_allowed)
{
    if(!ready || (!commands_allowed&&!restore_allowed))return;
    bool enabled=direction!=COMP_V11_BLE_BULK_NONE;
    const bool transmit_file=direction==COMP_V11_BLE_BULK_DEVICE_TO_HOST;
    /* This product is the peripheral/GATT server. The central owns MTU
     * exchange; the stack responds with configured512 and the actual event
     * below sets min(peer,local). Core ATT3.4.2 permits one exchange for both
     * directions. Three captured cross-over exchanges stopped notifications
     * ~30s after OUR request despite visible peer responses. Do not initiate
     * a second client transaction here. No synthetic agreement or MTU raise:
     * peers which do not exchange retain ATT23 and existing capacity guards. */
    /* Queue acceptance completes a physical segment before its last radio
     * fragments reach the central. Keep the finite authenticated batch owner
     * across tail/inter-file gaps. Signed OTA reception owns the same CI/DLE
     * negotiation, with ordinary bidirectional RX and no outgoing alignment. */
    enabled=commands_allowed&&(enabled||interval_hint)&&connection_secured&&connection!=0xFFFFu;
    interval_hint=commands_allowed&&interval_hint&&connection_secured&&connection!=0xFFFFu;
    if((int32_t)(HAL_GetTick()-profile_retry)<0)return;
    /* A batch can hand the active bulk owner from recording TX to OTA RX
     * without an idle turn. Track the successfully applied RX policy too;
     * an unchanged enabled bit must not leave OTA on seven empty RX slots.
     * Direction-only handoffs keep the existing CI owner and DLE bounds. */
    const bool rx_empty=enabled&&transmit_file&&bulk_empty_rx_slots;
    /* SDK LL_RX_ACL_CTRL is expected RX count/length, not a packet cap.
     * During OTA reserve for seven full incoming ACL packets; recording TX
     * keeps seven empty replies, and idle/inter-file hints keep ordinary RX.
     * This cannot force the peer's DLE/CI or claim a measured speed benefit. */
    const uint8_t rx_profile=rx_empty?1u:
        (enabled && direction==COMP_V11_BLE_BULK_HOST_TO_DEVICE?2u:0u);
    const bool owner_changed=enabled!=bulk_profile;
    if(owner_changed || rx_profile!=bulk_rx_profile) {
        uint8_t profile[2]={rx_profile?7u:0u,
            rx_profile==1u?0u:(rx_profile==2u?251u:32u)};
        profile_status=aci_hal_write_config_data(CONFIG_DATA_LL_RX_ACL_CTRL_OFFSET,2u,profile);
        if(profile_status==BLE_STATUS_SUCCESS) {
            bulk_profile=enabled;bulk_rx_profile=rx_profile;
        }
        else {transport_trace(enabled?5u:6u,0u);profile_retry=HAL_GetTick()+1000u;return;}
        transport_trace(enabled?5u:6u,0u);
        /* An accepted setup request may precede the one-way RX budget.
         * Re-suggest DLE once under that budget, keeping the connection-wide
         * two-attempt ceiling. Acceptance never substitutes for the actual
         * DATA_LENGTH_CHANGE event; no per-file or per-packet retry loop. */
        if(owner_changed && enabled && bulk_renegotiate_dle && dle_attempts==0x81u)dle_attempts=1u;
        if(owner_changed && enabled) {
            bulk_ci_attempts=0u;
            bulk_ci_ready_after=HAL_GetTick()+1000u;
            /* Keep the existing connection-wide two-request bound. A later
             * batch does not manufacture another initial/bulk DLE attempt. */
            bulk_dle_issued=bulk_renegotiate_dle&&dle_attempts==0x82u;
            bulk_dle_waiting=false;
        }
        if(!enabled)transport_trace(8u,dle_status|((uint16_t)dle_attempts<<8));
        return;
    }
    /* Request the bulk interval BEFORE re-suggesting DLE. A successful ACI
     * return only accepts the request; wait for actual CI6 or the finite
     * deadline below. ST documents 0x3a when DLE overlaps a connection update.
     * Payload work continues with the current measured capacity throughout.
     * Live capture uses ordinary RX. Each time a connection update leaves
     * interval 6, repeat the same 6/6/0/400 request once. Sealed uploads and
     * OTA keep the single request. The saved idle interval is not replaced. */
    if(direction==COMP_V11_BLE_BULK_NONE && interval_hint && bulk_ci_requested &&
       transport.interval>6u && !bulk_ci_wait_update) {
        bulk_ci_requested=false;
        if(bulk_ci_attempts>=2u)bulk_ci_attempts=1u;
    }
    if(enabled && !bulk_ci_requested && bulk_ci_attempts<2u && transport.interval>6u) {
        uint16_t owner=connection;
        if(!bulk_ci_attempts)bulk_ci_previous_interval=transport.interval;
        uint8_t attempt=++bulk_ci_attempts;
        bulk_ci_ready_after=HAL_GetTick()+1000u;
        uint8_t status=aci_l2cap_connection_parameter_update_req(owner,6u,6u,0u,400u);
        if(connection!=owner || bulk_ci_attempts!=attempt)return;
        bulk_ci_status=status;
        transport_trace(13u,status);
        if(status==BLE_STATUS_SUCCESS){bulk_ci_requested=true;bulk_ci_wait_update=true;}
        else profile_retry=HAL_GetTick()+1000u;
        return;
    }
    bool bulk_ci_ready=!enabled || transport.interval==6u ||
        (int32_t)(HAL_GetTick()-bulk_ci_ready_after)>=0;
    /* Apply the RX budget and actual/bounded CI wait before bulk DLE. The
     * ordinary initial request waits for actual PHY2 or a security-relative bounded fallback and the same
     * connection-wide two slots. One controller command per foreground turn. */
    if(commands_allowed&&connection_secured && dle_attempts<2u &&
       (!enabled || dle_attempts==0u || bulk_renegotiate_dle) &&
       bulk_ci_ready &&
       ((transport.tx_phy==2u && transport.rx_phy==2u) || (int32_t)(HAL_GetTick()-dle_ready_after)>=0)) {
        uint16_t owner=connection;
        uint8_t attempt=++dle_attempts;
        if(enabled) {
            bulk_dle_issued=true;bulk_dle_waiting=true;
            bulk_dle_ready_after=HAL_GetTick()+500u;
        }
        uint8_t status=hci_le_set_data_length(owner,251u,2120u);
        if(connection!=owner || dle_attempts!=attempt)return;
        dle_status=status;
        transport_trace(8u,dle_status|((uint16_t)dle_attempts<<8));
        if(dle_status==BLE_STATUS_SUCCESS)dle_attempts|=0x80u;
        else {bulk_dle_waiting=false;profile_retry=HAL_GetTick()+1000u;}
        return;
    }
    /* Unlike the rejected unconditional bulk re-suggestion, this requires
     * an observed budget transition after the initial accepted request.
     * A newly symmetric340 link additionally needs active bulk and actualCI6,
     * with settling rearmed by that CI event, not its bounded fallback.
     * An admitted foreground slot, completed/bounded CI and200ms settling
     * avoid submitting from an HCI callback or the active update instant.
     * Record acceptance only; DATA_LENGTH_CHANGE still owns effective values.
     * A rejected/no-change attempt is not automatically repeated. */
    if(connection!=0xFFFFu && comp_ble_budget_recovery_take(&directional_budget_recovery,
        commands_allowed,connection_secured,
        bulk_ci_ready && (directional_budget_recovery!=3u ||
            (enabled && transport.interval==6u)),
        transport.tx_phy==2u&&transport.rx_phy==2u,
        transport.tx_time,transport.rx_time,HAL_GetTick(),dle_ready_after)) {
        uint16_t owner=connection;
        uint8_t status=hci_le_set_data_length(owner,251u,2120u);
        if(connection==owner && directional_budget_recovery==2u)transport_trace(16u,status);
        return;
    }
    if(enabled && bulk_dle_waiting) {
        if((int32_t)(HAL_GetTick()-bulk_dle_ready_after)<0)return;
        /* No-change requests need not emit DATA_LENGTH_CHANGE. This timeout
         * permits alignment using the last real event, never fabricates a
         * larger time/octet value or a successful negotiation. */
        bulk_dle_waiting=false;transport_trace(14u,0u);
    }
    /* Initial/bulk maximum-size requests remain unchanged. Only an actual
     * short-event2M link whose effective octet and airtime ceilings disagree
     * gets one explicit host-fragment alignment per explicit batch. Invoke in an admitted
     * foreground slot, never in HCI callbacks or once per file/packet.
     * Request acceptance is not qualification: DATA_LENGTH_CHANGE and the
     * same-file HCI timing must establish its actual effect. */
    if(bulk_renegotiate_dle && enabled && transmit_file && interval_hint && dle_restore_attempted && dle_restore_status==BLE_STATUS_SUCCESS) {
        dle_alignment_attempted=false;dle_restore_attempted=false;
        dle_aligned_octets=0u;dle_alignment_status=0xFFu;dle_restore_status=0xFFu;
    }
    if(bulk_renegotiate_dle && enabled && transmit_file && interval_hint && bulk_ci_ready && bulk_dle_issued &&
       (dle_attempts&0x80u) && !dle_alignment_attempted) {
        uint16_t aligned=comp_v11_ble_bulk_aligned_octets(transport.tx_octets,
            transport.tx_time,transport.tx_phy,transport.interval);
        if(aligned) {
            uint16_t owner=connection;
            dle_alignment_attempted=true;dle_aligned_octets=aligned;
            uint8_t status=hci_le_set_data_length(owner,aligned,2120u);
            /* The command may dispatch disconnect/reconnection while waiting.
             * connection_opened clears ownership before new foreground work. */
            if(connection==owner && dle_alignment_attempted && dle_aligned_octets==aligned) {
                dle_alignment_status=status;
                transport_trace(11u,aligned);
            }
            return;
        }
    }
    /* Keep alignment across all physical segments in this explicit batch;
     * there is no DLE request at every inter-file attribute exchange. */
    if(!enabled && !interval_hint && restore_allowed && connection_secured && connection!=0xFFFFu &&
       dle_alignment_attempted && dle_alignment_status==BLE_STATUS_SUCCESS && !dle_restore_attempted) {
        uint16_t owner=connection,aligned=dle_aligned_octets;
        dle_restore_attempted=true;
        uint8_t status=hci_le_set_data_length(owner,251u,2120u);
        if(connection==owner && dle_restore_attempted && dle_aligned_octets==aligned) {
            dle_restore_status=status;
            transport_trace(12u,251u);
        }
        return;
    }
    if(!enabled&&!interval_hint && bulk_ci_requested) {
        /* Restore even if the earlier request's timing event is still in
         * flight. A busy host is retried later, never spun in a callback. */
        if(connection==0xFFFFu)bulk_ci_requested=false;
        else {
            uint16_t owner=connection;
            uint8_t status=aci_l2cap_connection_parameter_update_req(owner,
                bulk_ci_previous_interval,bulk_ci_previous_interval,0u,400u);
            if(connection!=owner)return;
            bulk_ci_status=status;
            if(bulk_ci_status==BLE_STATUS_SUCCESS)bulk_ci_requested=false;
            else profile_retry=HAL_GetTick()+1000u;
        }
    }
}
/* Export only existing BLE transport metadata after the payload owner is idle.
 * No extra resident ring, per-packet UART, HCI command, address/key or audio.
 * Cursor1 excludes boot event1; overwritten history remains explicitly partial. */
static void transport_history_diagnostic(char *line,size_t bytes)
{
    if(comp_v11_ble_blocking_diagnostic_busy())return;
    uint32_t cursor=1u;comp_diag_event_t e;size_t available;
    int n=snprintf(line,bytes,"BLETRACE0 retained=%lu capacity=%lu cursor_from=1 partial=1\r\n",
        (unsigned long)comp_diag_log_count(),(unsigned long)comp_diag_log_capacity());
    if(n>0 && (size_t)n<bytes)(void)comp_v11_hal_debug_write(line);
    for(size_t i=0u;i<comp_diag_log_capacity();++i) {
        if(!comp_diag_log_read_page(cursor,1u<<(COMP_DIAG_SRC_BLE-1u),0u,&e,1u,&available))break;
        cursor=e.sequence;
        if(e.event_id!=COMP_DIAG_EVENT_ID(COMP_DIAG_EVT_BLE_TRANSPORT) ||
           (uint8_t)e.arg0==7u)continue; /* pool sampling is not a parameter transition */
        if((uint8_t)e.arg0>=32u && (uint8_t)e.arg0<=39u) {
            n=snprintf(line,bytes,"RXTRACE1 seq=%lu ms=%lu stage=%u p=%u x=%u plen=%u type=%u evt=%u attr=%u off=%u n=%u why=%u\r\n",
                (unsigned long)e.sequence,(unsigned long)e.t_ms,(unsigned)(uint8_t)e.arg0,
                (unsigned)(uint16_t)e.arg1,(unsigned)(uint16_t)(e.arg1>>16),
                (unsigned)(uint8_t)(e.arg3>>16),(unsigned)(uint8_t)(e.arg0>>16),
                (unsigned)(uint8_t)(e.arg0>>24),(unsigned)(uint16_t)e.arg2,
                (unsigned)(uint16_t)e.arg3,(unsigned)(uint16_t)(e.arg2>>16),
                (unsigned)(uint8_t)(e.arg0>>8));
        } else n=snprintf(line,bytes,"BLETRACE1 seq=%lu ms=%lu reason=%u handle=%u ci=%u tx_us=%u octets=%u tx_phy=%u rx_phy=%u status=%u bulk=%u detail=%u\r\n",
            (unsigned long)e.sequence,(unsigned long)e.t_ms,(unsigned)(uint8_t)e.arg0,
            (unsigned)(uint16_t)(e.arg0>>16),(unsigned)(uint16_t)e.arg1,
            (unsigned)(uint16_t)(e.arg1>>16),(unsigned)(uint16_t)e.arg2,
            (unsigned)(uint8_t)(e.arg2>>16),(unsigned)(uint8_t)(e.arg2>>24),
            (unsigned)(uint8_t)e.arg3,(unsigned)(uint8_t)(e.arg3>>8),
            (unsigned)(uint16_t)(e.arg3>>16));
        if(n>0 && (size_t)n<bytes)(void)comp_v11_hal_debug_write(line);
    }
    (void)comp_v11_hal_debug_write("BLETRACE2 END partial=1\r\n");
}
void comp_v11_ble_transport_diagnostic(void)
{
    char line[192];
    transport_history_diagnostic(line,sizeof(line));
    int n=snprintf(line,sizeof(line),
        "LINK1 ci_units=%u latency=%u tx_phy=%u rx_phy=%u tx_octets=%u connected=%u bp=%lu pool=%lu timer=%lu rx_profile=%u rx_status=%u att_mtu=%u mtu_state=%u mtu_status=%u\r\n",
        transport.interval,transport.latency,transport.tx_phy,transport.rx_phy,
        transport.tx_octets,connection!=0xFFFFu,
        (unsigned long)comp_v11_ble_transfer_backpressure(),
        (unsigned long)comp_v11_ble_tx_pool_events(),(unsigned long)comp_v11_ble_tx_timed_retries(),
        (unsigned)bulk_rx_profile,profile_status,att.mtu,att.attempts,att.status);
    if(n>0 && (unsigned)n<sizeof(line))(void)comp_v11_hal_debug_write(line);
    /* Keep the actual DLE airtime and the resulting product limits beside
     * LINK1 in its existing foreground snapshot. An ATT MTU alone cannot
     * explain a 224 -> 43 byte payload change. Zero TxTime is still unknown;
     * these limits are policy values, not proof of transmitted packet size.
     * Use another line rather than growing the existing stack buffer or
     * truncating LINK1. No UART or new ACI work runs in an HCI callback. */
    n=snprintf(line,sizeof(line),
        "LINK2 tx_time_us=%u compact_limit_bytes=%u value_limit_bytes=%u single_ll_audio_estimate=%u dle_attempts=%u dle_accepted=%u dle_status=%u ci_request_status=%u\r\n",
        transport.tx_time,comp_v11_ble_recording_capacity(),comp_v11_ble_value_capacity(),
        comp_v11_ble_single_ll_compact_capacity(transport.tx_octets,transport.tx_time,transport.tx_phy),
        (unsigned)(dle_attempts&0x7Fu),(unsigned)((dle_attempts&0x80u)!=0u),
        (unsigned)dle_status,(unsigned)bulk_ci_status);
    if(n>0 && (unsigned)n<sizeof(line))(void)comp_v11_hal_debug_write(line);
    n=snprintf(line,sizeof(line),
        "LINK3 aligned_octets=%u alignment_attempted=%u alignment_status=%u restore_attempted=%u restore_status=%u ci_attempts=%u dle_waiting=%u\r\n",
        (unsigned)dle_aligned_octets,(unsigned)dle_alignment_attempted,(unsigned)dle_alignment_status,
        (unsigned)dle_restore_attempted,(unsigned)dle_restore_status,
        (unsigned)bulk_ci_attempts,(unsigned)bulk_dle_waiting);
    if(n>0 && (unsigned)n<sizeof(line))(void)comp_v11_hal_debug_write(line);
    n=snprintf(line,sizeof(line),
        "LINK4 limits_status=%u max_tx_octets=%u max_tx_us=%u max_rx_octets=%u max_rx_us=%u\r\n",
        (unsigned)controller_limits.limits_status,(unsigned)controller_limits.max_tx_octets,
        (unsigned)controller_limits.max_tx_time,(unsigned)controller_limits.max_rx_octets,
        (unsigned)controller_limits.max_rx_time);
    if(n>0 && (unsigned)n<sizeof(line))(void)comp_v11_hal_debug_write(line);
    n=snprintf(line,sizeof(line),
        "LINK5 suggested_status=%u suggested_tx_octets=%u suggested_tx_us=%u effective_rx_octets=%u effective_rx_us=%u\r\n",
        (unsigned)controller_limits.suggested_status,
        (unsigned)controller_limits.suggested_tx_octets,(unsigned)controller_limits.suggested_tx_time,
        (unsigned)transport.rx_octets,(unsigned)transport.rx_time);
    if(n>0 && (unsigned)n<sizeof(line))(void)comp_v11_hal_debug_write(line);
    /* Existing guarded idle diagnostic only: no GATT command, write or
     * private pairing data. Do not print a hash until its scope is valid. */
    const comp_v11_public_hash_trace_t *ht=comp_v11_ble_public_hash_trace();
    char last_hash[33],previous_hash[33];
    comp_v11_public_hash_hex(ht->last,last_hash);
    comp_v11_public_hash_hex(ht->previous,previous_hash);
    n=snprintf(line,sizeof(line),"GATTHASH1 calls=%lu input_bytes=%lu last=%s previous=%s scope=public_db\r\n",
        (unsigned long)ht->calls,(unsigned long)ht->input_bytes,
        ht->calls?last_hash:"none",ht->calls>1u?previous_hash:"none");
    if(n>0 && (unsigned)n<sizeof(line))(void)comp_v11_hal_debug_write(line);
    n=snprintf(line,sizeof(line),"GATTHASH3 complete_input_bytes=%lu faults=%lu scope=public_db\r\n",
        (unsigned long)ht->complete_input_bytes,(unsigned long)ht->faults);
    if(n>0 && (unsigned)n<sizeof(line))(void)comp_v11_hal_debug_write(line);
    comp_v11_public_nvm_digest_t hd=comp_v11_public_nvm_digest(host_nvm_buffer,sizeof(host_nvm_buffer));
    comp_v11_public_hash_hex(hd.hash,last_hash);
    n=snprintf(line,sizeof(line),"GATTHASH2 envelope_valid=%u live_records=%u hash_valid=%u hash=%s sc_present=%u sc_cccd=%u\r\n",
        (unsigned)hd.envelope_valid,(unsigned)hd.live_records,(unsigned)hd.hash_valid,
        hd.hash_valid?last_hash:"none",(unsigned)hd.service_changed_present,(unsigned)hd.service_changed_cccd);
    if(n>0 && (unsigned)n<sizeof(line))(void)comp_v11_hal_debug_write(line);
    n=snprintf(line,sizeof(line),
        "BOND1 restore=%u peers_boot=%u pending=%u busy=%u writes_ok=%lu writes_failed=%lu bulk_ci_status=%u\r\n",
        host_restore_status,bonds_boot,nvm_pending,nvm_busy,
        (unsigned long)nvm_good,(unsigned long)nvm_failed,bulk_ci_status);
    if(n>0 && (unsigned)n<sizeof(line))(void)comp_v11_hal_debug_write(line);
    n=snprintf(line,sizeof(line),
        "GAP1 disconnects=%lu secured_disconnects=%lu last_ms=%lu reason=%02x secured_reason=%02x was_secured=%u enc_status=%02x enc_enabled=%u\r\n",
        (unsigned long)link_history.disconnects,(unsigned long)link_history.secured_disconnects,
        (unsigned long)link_history.last_disconnect_ms,(unsigned)link_history.last_reason,
        (unsigned)link_history.last_secured_reason,(unsigned)link_history.last_was_secured,
        (unsigned)link_history.encryption_status,(unsigned)link_history.encryption_enabled);
    if(n>0 && (unsigned)n<sizeof(line))(void)comp_v11_hal_debug_write(line);
    n=snprintf(line,sizeof(line),
        "GAP3 first_secured_disconnect_ms=%lu first_secured_reason=%02x first_bond_lost_ms=%lu\r\n",
        (unsigned long)link_history.first_secured_disconnect_ms,
        (unsigned)link_history.first_secured_reason,
        (unsigned long)link_history.first_bond_lost_ms);
    if(n>0 && (unsigned)n<sizeof(line))(void)comp_v11_hal_debug_write(line);
    n=snprintf(line,sizeof(line),
        "GAP2 radio=%u auto_reconnect=%u advertising=%u pending=%u pair_open=%u connection_allowed=%u ll_status=%02x ll_mask=%02x recoveries=%u stop_pending=%u rearms=%u gap_stop=%02x ctrl_stop=%02x\r\n",
        (unsigned)radio_enabled,(unsigned)auto_reconnect,(unsigned)advertising,
        (unsigned)advertise_pending,(unsigned)pairing_open(),(unsigned)connection_allowed,
        (unsigned)advertising_link_status,(unsigned)advertising_link_mask,(unsigned)advertising_recoveries,
        (unsigned)advertise_stop_pending,(unsigned)advertising_rearms,
        (unsigned)advertising_stop_status,(unsigned)advertising_disable_status);
    if(n>0 && (unsigned)n<sizeof(line))(void)comp_v11_hal_debug_write(line);
    /* kind1/10: LE completion status; kind5: an unowned disconnect reason.
     * A successful completion is not proof of encryption or usable GATT. */
    n=snprintf(line,sizeof(line),
        "GAP4 seen=%u failed=%u unowned=%u kind=%02x code=%02x last_ms=%lu\r\n",
        (unsigned)initial_link_observation.seen,(unsigned)initial_link_observation.failed,
        (unsigned)initial_link_observation.unowned,(unsigned)initial_link_observation.kind,
        (unsigned)initial_link_observation.code,(unsigned long)initial_link_observation.last_ms);
    if(n>0 && (unsigned)n<sizeof(line))(void)comp_v11_hal_debug_write(line);
    comp_v11_ble_download_timing_diagnostic();
}
static void gap_security_event(uint16_t code,const uint8_t *data,uint8_t length)
{
    if(code==ACI_GAP_BOND_LOST_VSEVT_CODE) {
        aci_gap_bond_lost_event_rp0 lost;
        if(length<sizeof(lost))return;
        memcpy(&lost,data,sizeof(lost));
        if(lost.Connection_Handle!=connection || connection==0xFFFFu)return;
        if(security_stats.bond_lost_events==0u)link_history.first_bond_lost_ms=HAL_GetTick();
        ++security_stats.bond_lost_events;
        bool allowed=radio_enabled && connection_allowed && pairing_open();
        comp_diag_log_record_code(COMP_DIAG_EVT_BLE_SECURITY,COMP_DIAG_SEV_WARN,
            code,connection,allowed,0u);
        /* A known central can legitimately lose its old keys. ST requires an
         * explicit reply, otherwise SMP times out. Only the local finite
         * pairing window authorizes replacing this peer's bond; existing
         * bonds and recordings are not erased. Encryption remains mandatory. */
        if(allowed) {
            ++security_stats.rebond_attempts;
            if(check(aci_gap_allow_rebond(connection)))return;
        }
        (void)check(hci_disconnect(connection,0x05u));
    } else if(code==ACI_GAP_PAIRING_COMPLETE_VSEVT_CODE) {
        aci_gap_pairing_complete_event_rp0 paired;
        if(length<sizeof(paired))return;
        memcpy(&paired,data,sizeof(paired));
        if(paired.Connection_Handle!=connection || connection==0xFFFFu)return;
        pairing_result(paired.Status,paired.Reason);
        comp_diag_log_record_code(COMP_DIAG_EVT_BLE_SECURITY,
            paired.Status?COMP_DIAG_SEV_ERROR:COMP_DIAG_SEV_INFO,
            code,connection,paired.Status,paired.Reason);
        if(paired.Status) {
            connection_secured=false;
            comp_v11_ble_link(true,false);
            (void)check(hci_disconnect(connection,0x05u));
        }
        /* Success is not a substitute for HCI_ENCRYPTION_CHANGE: only that
         * event can open access to private GATT data. */
    }
}
SVCCTL_UserEvtFlowStatus_t SVCCTL_App_Notification(void *packet)
{
    if(!packet)return SVCCTL_UserEvtFlowEnable;
    hci_event_pckt *evt=(hci_event_pckt*)((hci_uart_pckt*)packet)->data;
    if(evt->evt==HCI_VENDOR_SPECIFIC_DEBUG_EVT_CODE) {
        if(evt->plen<2u)return SVCCTL_UserEvtFlowEnable;
        const uint16_t code=(uint16_t)evt->data[0]|((uint16_t)evt->data[1]<<8);
#if COMPANION_WBA_PEER_INDICATIONS
        if(code==ACI_GATT_INDICATION_VSEVT_CODE || code==ACI_GATT_INDICATION_EXT_VSEVT_CODE) {
            if(comp_v11_peer_indication_receive(&peer_indication,connection,connection_allowed,
                code==ACI_GATT_INDICATION_EXT_VSEVT_CODE,evt->data+2u,(uint16_t)(evt->plen-2u),HAL_GetTick()))
                comp_diag_log_record_code(COMP_DIAG_EVT_BLE_TRANSPORT,COMP_DIAG_SEV_INFO,
                    0x494e4400u,connection,peer_indication.attribute,code);
        }
#endif
        if(code==ACI_ATT_EXCHANGE_MTU_RESP_VSEVT_CODE &&
           evt->plen>=2u+sizeof(aci_att_exchange_mtu_resp_event_rp0)) {
            aci_att_exchange_mtu_resp_event_rp0 mtu;
            memcpy(&mtu,evt->data+2u,sizeof(mtu));
            if(connection!=0xFFFFu && mtu.Connection_Handle==connection &&
               comp_v11_ble_mtu_agreed(&att,mtu.Server_RX_MTU,CFG_BLE_ATT_MTU_MAX))
                comp_diag_log_record_code(COMP_DIAG_EVT_BLE_TRANSPORT,COMP_DIAG_SEV_INFO,
                    10u|((uint32_t)connection<<16),att.mtu,comp_v11_ble_value_capacity(),0u);
        }
        if(code==ACI_GATT_TX_POOL_AVAILABLE_VSEVT_CODE &&
           evt->plen>=2u+sizeof(aci_gatt_tx_pool_available_event_rp0)) {
            aci_gatt_tx_pool_available_event_rp0 available;
            memcpy(&available,evt->data+2u,sizeof(available));
            if(available.Available_Buffers)comp_v11_ble_observe_route_run(0u);
            /* ST documents Connection_Handle as unused for this event.
             * Just wake the foreground retry; never call GATT from here. */
            if(available.Available_Buffers) {
                if(bulk_profile && (comp_v11_ble_tx_pool_events()&255u)==0u)
                    transport_trace(7u,available.Available_Buffers);
                comp_v11_ble_tx_pool_available();
            }
        }
        if(code==ACI_GATT_NOTIFICATION_COMPLETE_VSEVT_CODE && evt->plen>=4u &&
           connection!=0xFFFFu && connection_secured) {
            uint16_t handle=(uint16_t)evt->data[2]|((uint16_t)evt->data[3]<<8);
            if(companion_gatt_stm32wb_is_recording_value_handle(handle)) {
                comp_v11_ble_observe_completion_dispatched(handle);
                comp_v11_ble_recording_notification_complete();
            }
        }
        if(code==ACI_GATT_ERROR_RESP_VSEVT_CODE &&
           evt->plen>=2u+sizeof(aci_gatt_error_resp_event_rp0)) {
            aci_gatt_error_resp_event_rp0 error;
            memcpy(&error,evt->data+2u,sizeof(error));
            if(connection!=0xFFFFu && error.Connection_Handle==connection && error.Req_Opcode==0x02u)
                (void)comp_v11_ble_mtu_refused(&att,error.Error_Code);
        }
        gap_security_event(code,evt->data+2u,(uint8_t)(evt->plen-2u));
    } else if(evt->evt==HCI_DISCONNECTION_COMPLETE_EVT_CODE) {
        hci_disconnection_complete_event_rp0 *d=(void*)evt->data;
        if(evt->plen<sizeof(*d) || d->Status!=0)
            return SVCCTL_UserEvtFlowEnable;
        if(d->Connection_Handle!=connection) {
            initial_link_observe(HCI_DISCONNECTION_COMPLETE_EVT_CODE,d->Reason,
                d->Connection_Handle,true);
            return SVCCTL_UserEvtFlowEnable;
        }
        comp_v11_ble_observe_capture_radio(false,d->Connection_Handle,d->Reason);
        ++link_history.disconnects;
        link_history.last_disconnect_ms=HAL_GetTick();
        link_history.last_reason=d->Reason;
        link_history.last_was_secured=connection_secured;
        if(!connection_secured) {
            link_history.unsecured_reason=d->Reason;
            link_history.unsecured_allowed=connection_allowed;
        }
        if(connection_secured) {
            if(link_history.secured_disconnects==0u) {
                link_history.first_secured_disconnect_ms=HAL_GetTick();
                link_history.first_secured_reason=d->Reason;
            }
            ++link_history.secured_disconnects;
            link_history.last_secured_reason=d->Reason;
        }
        comp_diag_log_record_code(COMP_DIAG_EVT_BLE_SECURITY,COMP_DIAG_SEV_WARN,
            evt->evt,connection,d->Reason,connection_secured);
        connection=0xFFFFu;connection_secured=false;
#if COMPANION_WBA_PEER_INDICATIONS
        comp_v11_peer_indication_reset(&peer_indication);
#endif
        advertise_pending=radio_enabled && (auto_reconnect || reconnect_requested || pairing_open());
        /* A complete disconnect requires the same foreground GAP stop/start
         * as explicit local recovery. The pre-connection cached advertising
         * flag is false, so it cannot decide whether the old GAP state needs
         * clearing. Never re-arm during an active link or a capture command. */
        advertise_stop_pending=advertise_pending;
        reconnect_requested=false;advertising_retry=HAL_GetTick();
        comp_v11_ble_link(false,false);
    } else if(evt->evt==HCI_LE_META_EVT_CODE) {
        if(evt->plen<1u)return SVCCTL_UserEvtFlowEnable;
        evt_le_meta_event *meta=(evt_le_meta_event*)evt->data;
        if(meta->subevent==HCI_LE_CONNECTION_COMPLETE_SUBEVT_CODE) {
            hci_le_connection_complete_event_rp0 *c=(void*)meta->data;
            if(evt->plen<1u+sizeof(*c))return SVCCTL_UserEvtFlowEnable;
            initial_link_observe(HCI_LE_CONNECTION_COMPLETE_SUBEVT_CODE,c->Status,
                c->Status?0xFFFFu:c->Connection_Handle,false);
            if(c->Status==0) {
                comp_v11_ble_observe_capture_radio(true,c->Connection_Handle,0u);
                connection_opened(c->Connection_Handle,c->Peer_Address_Type,c->Peer_Address);
                transport.interval=c->Conn_Interval;transport.latency=c->Conn_Latency;
            }
        } else if(meta->subevent==HCI_LE_ENHANCED_CONNECTION_COMPLETE_SUBEVT_CODE) {
            hci_le_enhanced_connection_complete_event_rp0 *c=(void*)meta->data;
            if(evt->plen<1u+sizeof(*c))return SVCCTL_UserEvtFlowEnable;
            initial_link_observe(HCI_LE_ENHANCED_CONNECTION_COMPLETE_SUBEVT_CODE,c->Status,
                c->Status?0xFFFFu:c->Connection_Handle,false);
            if(c->Status==0) {
                comp_v11_ble_observe_capture_radio(true,c->Connection_Handle,0u);
                connection_opened(c->Connection_Handle,c->Peer_Address_Type,c->Peer_Address);
                transport.interval=c->Conn_Interval;transport.latency=c->Conn_Latency;
            }
        } else if(meta->subevent==HCI_LE_CONNECTION_UPDATE_COMPLETE_SUBEVT_CODE) {
            const hci_le_connection_update_complete_event_rp0 *c=(void*)meta->data;
            if(evt->plen>=1u+sizeof(*c) && c->Status==0 && c->Connection_Handle==connection) {
                transport.interval=c->Conn_Interval;transport.latency=c->Conn_Latency;
                if(directional_budget_recovery==3u && c->Conn_Interval==6u)
                    dle_ready_after=HAL_GetTick()+200u;
                bulk_ci_wait_update=false;
                transport_trace(2u,0u);
            }
        } else if(meta->subevent==HCI_LE_DATA_LENGTH_CHANGE_SUBEVT_CODE) {
            const hci_le_data_length_change_event_rp0 *c=(void*)meta->data;
            if(evt->plen>=1u+sizeof(*c) && c->Connection_Handle==connection) {
                bool recover=comp_ble_budget_recovery_observe(&directional_budget_recovery,
                    dle_attempts==0x81u,transport.tx_phy==2u&&transport.rx_phy==2u,
                    transport.tx_time,transport.rx_time,c->MaxTxTime,c->MaxRxTime,
                    HAL_GetTick(),&dle_ready_after);
                transport.tx_octets=c->MaxTxOctets;transport.tx_time=c->MaxTxTime;
                transport.rx_octets=c->MaxRxOctets;transport.rx_time=c->MaxRxTime;
                if(recover)transport_trace(15u,directional_budget_recovery);
                bulk_dle_waiting=false;
                transport_trace(3u,c->MaxRxTime);
            }
        } else if(meta->subevent==HCI_LE_PHY_UPDATE_COMPLETE_SUBEVT_CODE) {
            const hci_le_phy_update_complete_event_rp0 *c=(void*)meta->data;
            if(evt->plen>=1u+sizeof(*c) && c->Status==0 && c->Connection_Handle==connection) {
                transport.tx_phy=c->TX_PHY;transport.rx_phy=c->RX_PHY;
                transport_trace(4u,0u);
            }
        }
    } else if(evt->evt==HCI_ENCRYPTION_CHANGE_EVT_CODE) {
        hci_encryption_change_event_rp0 *e=(void*)evt->data;
        if(evt->plen<sizeof(*e))return SVCCTL_UserEvtFlowEnable;
        if(e->Connection_Handle==connection) {
            link_history.encryption_status=e->Status;
            link_history.encryption_enabled=e->Encryption_Enabled;
            comp_diag_log_record_code(COMP_DIAG_EVT_BLE_SECURITY,
                e->Status?COMP_DIAG_SEV_ERROR:COMP_DIAG_SEV_INFO,
                evt->evt,connection,e->Status,e->Encryption_Enabled);
            connection_secured=connection_allowed && radio_enabled && e->Status==0 && e->Encryption_Enabled!=0;
            if(connection_secured) {
                pairing_until=0;
                /* The old deadline began before security and could already
                 * expire while encryption was establishing. The retained
                 * trace shows DLE returned780ms before PHY2 completion.
                 * Arm the initial bounded compatibility wait here; actual
                 * PHY2 completion admits early. This is not a bulk retry. */
                if(!dle_attempts) {
                    dle_ready_after=HAL_GetTick()+2000u;
                    transport_trace(15u,2000u);
                }
            }
            comp_v11_ble_link(connection!=0xFFFFu,connection_secured);
        }
    }
    return SVCCTL_UserEvtFlowEnable;
}
static uint8_t HOST_BLE_Init(void)
{
  /* The SDK consumes a const configuration; all writable buffers remain
   * static below their existing owners. Keep the persistent descriptor in
   * Flash instead of reserving 68B of CE RAM for startup-only assignments.
   * No stack/buffer reduction or change to negotiated BLE parameters. */
  static const BleStack_init_t pInitParams = {
      .numAttrRecord = CFG_BLE_NUM_GATT_ATTRIBUTES,
      .numAttrServ = CFG_BLE_NUM_GATT_SERVICES,
      .attrValueArrSize = CFG_BLE_ATT_VALUE_ARRAY_SIZE,
      .prWriteListSize = CFG_BLE_ATTR_PREPARE_WRITE_VALUE_SIZE,
      .attMtu = CFG_BLE_ATT_MTU_MAX,
      .max_coc_nbr = CFG_BLE_COC_NBR_MAX,
      .max_coc_mps = CFG_BLE_COC_MPS_MAX,
      .max_coc_initiator_nbr = CFG_BLE_COC_INITIATOR_NBR_MAX,
      .max_add_eatt_bearers = CFG_BLE_EATT_BEARER_PER_LINK * CFG_BLE_NUM_LINK,
      .numOfLinks = CFG_BLE_NUM_LINK,
      .mblockCount = CFG_BLE_MBLOCK_COUNT,
      .bleStartRamAddress = (uint8_t*)host_buffer,
      .total_buffer_size = BLE_DYN_ALLOC_SIZE,
      .bleStartRamAddress_GATT = (uint8_t*)gatt_buffer,
      .total_buffer_size_GATT = BLE_GATT_BUF_SIZE,
      .extra_data_buffer_size = CFG_BLE_EXTRA_DATA_BUF_SIZE,
      .extra_data_buffer = (uint8_t*)extra_data_buffer,
      .gatt_long_write_buffer = (uint8_t*)long_write_buffer,
      .host_event_fifo_buffer = host_event_buffer,
      .host_event_fifo_buffer_size = DIVC(BLE_HOST_EVENT_BUF_SIZE, 2),
      .nvm_cache_buffer = host_nvm_buffer,
      .nvm_cache_max_size = BLE_HOST_NVM_SIZE_U64,
      .nvm_cache_size = BLE_HOST_NVM_SIZE_U64 - 1,
      .options = CFG_BLE_OPTIONS,
      .debug = 0U,
  };
  return (uint8_t)BleStack_Init(&pInitParams);
}

void Ble_UserEvtRx( void)
{
  SVCCTL_UserEvtFlowStatus_t svctl_return_status;
  BleEvtPacket_t *phcievt = NULL;

  if (LST_is_empty(&BleAsynchEventQueue))return;
  LST_remove_head ( &BleAsynchEventQueue, (tListNode **)&phcievt );

  svctl_return_status = SVCCTL_UserEvtRx((void *)&(phcievt->evtserial));

  if (svctl_return_status != SVCCTL_UserEvtFlowDisable)
  {
    AMM_Free((uint32_t *)phcievt);
  }
  else
  {
    LST_insert_head ( &BleAsynchEventQueue, (tListNode *)phcievt );
  }

  if ((LST_is_empty(&BleAsynchEventQueue) == FALSE) && (svctl_return_status != SVCCTL_UserEvtFlowDisable) )
  {
    UTIL_SEQ_SetTask(1U << CFG_TASK_HCI_ASYNCH_EVT_ID, CFG_SEQ_PRIO_0);
  }

  /* Trigger BLE Host stack to process */
  BleStackCB_Process();

}

void BleStack_Process_BG(void)
{
  const uint8_t status=BleStack_Process();
  comp_v11_ble_host_cycle_completed();
  if (status == 0x0)
  {
    BleStackCB_Process();
  }
}

static void BLE_ResumeFlowProcessCallback(void)
{
  /* Receive any events from the LL. */
  change_state_options_t notify_options;

  notify_options.combined_value = 0x0F;

  ll_intf_chng_evnt_hndlr_state( notify_options );
}

#if !COMPANION_WBA_EXTERNAL_BOND_STORE
static void BLE_NvmCallback(SNVMA_Callback_Status_t CbkStatus)
{
    nvm_busy=false;
    if(CbkStatus!=SNVMA_OPERATION_COMPLETE) {
        ++nvm_failed;
        nvm_pending=true;
        nvm_retry=HAL_GetTick()+1000u;
    } else ++nvm_good;
}
#endif

void APP_BLE_HostNvmStore(void)
{
    /* A pairing event may arrive during capture. The foreground service owns
     * starting internal-flash work; callbacks never retry flash recursively. */
#if COMPANION_WBA_EXTERNAL_BOND_STORE
    ++external_revision;
#endif
    nvm_pending=true;
}

bool comp_v11_ble_store_gatt_for_reboot(void)
{
    uint32_t now=HAL_GetTick();
    if(!ready || nvm_busy || (int32_t)(now-nvm_retry)<0)return false;
    /* The SDK normally snapshots GATT on disconnection. OTA resets while
     * bonded and connected, so explicitly include live CCCDs/database state.
     * Coalesce into the same existing SNVMA owner; no peer/key deletion. */
    if(connection!=0xFFFFu) {
        tBleStatus status=aci_gatt_store_db();
        /* One foreground-only result per attempted planned reset. No UART in
         * HCI/capture callbacks, no additional resident diagnostic buffer. */
        char line[96];
        (void)snprintf(line,sizeof(line),"GATTSTORE1 status=%u options=%lu connected=1\r\n",
            (unsigned)status,(unsigned long)CFG_BLE_OPTIONS);
        (void)comp_v11_hal_debug_write(line);
        if(status!=BLE_STATUS_SUCCESS) {nvm_retry=now+1000u;return false;}
    }
    APP_BLE_HostNvmStore();
    return true;
}

void comp_v11_ble_nvm_poll(uint32_t now,bool writes_allowed)
{
#if COMPANION_WBA_EXTERNAL_BOND_STORE
    external_nvm_poll(now,writes_allowed);
#else
    if(!writes_allowed || !nvm_pending || nvm_busy || (int32_t)(now-nvm_retry)<0)return;
    nvm_pending=false; nvm_busy=true;
    if(SNVMA_Write(APP_BLE_Host_SNVMA_BufferId_1_1,BLE_NvmCallback)!=SNVMA_ERROR_OK) {
        nvm_busy=false; nvm_pending=true; nvm_retry=now+1000u;
    }
#endif
}
bool comp_v11_ble_nvm_busy(void) { return nvm_pending || nvm_busy; }
/* A queued snapshot owns no Flash. The write gate still defers it while
 * recording, but it must not block reconnect advertising or the public peer
 * indication confirmation needed after connecting. A live NVM owner and
 * all idle paths retain the stricter original gate. */
bool comp_v11_ble_nvm_control_blocked(bool microphone_running)
{
    return nvm_busy || (nvm_pending && !microphone_running);
}

tBleStatus BLECB_Indication( const uint8_t* data,
                          uint16_t length,
                          const uint8_t* ext_data,
                          uint16_t ext_length )
{
  uint8_t status = BLE_STATUS_FAILED;
  BleEvtPacket_t *phcievt = NULL;
  uint16_t total_length = 0u;
  uint32_t provided_length;
  const uint32_t entered_ms=HAL_GetTick();

  /* USER CODE BEGIN BLECB_Indication */

  /* USER CODE END BLECB_Indication */

  if ((data == NULL) || (length == 0u) ||
      ((ext_length != 0u) && (ext_data == NULL)))
  {
    return BLE_STATUS_FAILED;
  }
  provided_length = (uint32_t)length + (uint32_t)ext_length;
  rx_indication_shape(32u,0u,data,length,ext_data,ext_length);

  if (data[0] == HCI_EVENT_PKT_TYPE)
  {
    uint16_t copied_length = 0u;
    comp_v11_ble_event_copy_result_t plan=comp_v11_ble_event_plan(
        data,length,ext_data,ext_length,&total_length);
    if(plan!=COMP_V11_BLE_EVENT_COPY_OK) {
      rx_indication_shape(33u,(uint8_t)plan,data,length,ext_data,ext_length);
      return BLE_STATUS_FAILED;
    }
    BLE_EVENTS_ResumeFlowProcessCb.Callback = BLE_ResumeFlowProcessCallback;
    if (AMM_Alloc (CFG_AMM_VIRTUAL_BLE_EVENTS,
                   DIVC((sizeof(BleEvtPacketHeader_t) + total_length), sizeof (uint32_t)),
                   (uint32_t **)&phcievt,
                   &BLE_EVENTS_ResumeFlowProcessCb) != AMM_ERROR_OK)
    {
      LOG_INFO_APP("Alloc failed\n");
      status = BLE_STATUS_FAILED;
    }
    else if (phcievt != (BleEvtPacket_t *)0 )
    {
      if (comp_v11_ble_event_flatten(
              data, length, ext_data, ext_length,
              (uint8_t *)&phcievt->evtserial, total_length,
              &copied_length) != COMP_V11_BLE_EVENT_COPY_OK ||
          copied_length != total_length)
      {
        AMM_Free((uint32_t *)phcievt);
      }
      else
      {
        LST_insert_tail(&BleAsynchEventQueue, (tListNode *)phcievt);
        rx_indication_shape(34u,0u,data,length,ext_data,ext_length);
        const uint8_t *queued=(const uint8_t*)&phcievt->evtserial;
        if(total_length==7u && queued[0]==HCI_EVENT_PKT_TYPE && queued[1]==0xffu &&
           queued[2]==4u && queued[3]==(uint8_t)ACI_GATT_NOTIFICATION_COMPLETE_VSEVT_CODE &&
           queued[4]==(uint8_t)(ACI_GATT_NOTIFICATION_COMPLETE_VSEVT_CODE>>8u))
            comp_v11_ble_observe_completion_enqueued((uint16_t)queued[5]|((uint16_t)queued[6]<<8u));
        if(comp_v11_ble_route_pool_packet((const uint8_t*)&phcievt->evtserial,total_length,
            ACI_GATT_TX_POOL_AVAILABLE_VSEVT_CODE)) {
            comp_v11_ble_observe_pool_callback(entered_ms);
            comp_v11_ble_observe_route_ready(0u);
        }
        UTIL_SEQ_SetTask(1U << CFG_TASK_HCI_ASYNCH_EVT_ID, CFG_SEQ_PRIO_0);
        status = BLE_STATUS_SUCCESS;
      }
    }
  }
  else if (data[0] == HCI_ACLDATA_PKT_TYPE)
  {
    /* ACL is consumed inside the host stack; validate its standard header so
     * malformed callback arguments cannot be acknowledged as a full packet. */
    if (length >= 5u && provided_length <= UINT16_MAX &&
        provided_length == 5u + (uint32_t)data[3] +
                               ((uint32_t)data[4] << 8u))
    {
      status = BLE_STATUS_SUCCESS;
    }
  }
  return status;
}

/* Public typed LL admission and formed-report callbacks; all arguments/results
 * go to the original SDK functions. No private C ABI, IRQ/queue policy changes. */
#include "ble_credit_profile.h" /* verified raw0x13 field decoder */
#include "ble_send_failure_profile.h"
#include "ble_pending_acl_ownership.h"
#if COMPANION_WBA_ACL_READINESS_PROFILE
#include "ble_acl_readiness_profile.h"
#endif
#include "ble_credit_wakeup.h"
#include "hci.h"
static hci_trnsprt_cbk report_original_transport;
static comp_v11_ble_send_failure_profile_t ll_send_failures;
void comp_v11_ble_ll_failure_snapshot(uint32_t values[3])
{
    uint32_t mask=__get_PRIMASK();__disable_irq();
    values[0]=ll_send_failures.count;
    values[1]=ll_send_failures.first;
    values[2]=ll_send_failures.last;
    __set_PRIMASK(mask);
}
_Static_assert(sizeof(report_original_transport)==4u,"84B observer+4B callback");
bool comp_v11_ble_report_callback_bound(void)
{return report_original_transport==hci_queue_send_pckt;}
uint8_t comp_v11_ble_controller_buffer_size(uint16_t *bytes,uint8_t *packets)
{return ll_intf_le_read_buffer_size(bytes,packets);}
static uint8_t comp_v11_report_transport(ble_buff_hdr_t *header)
{
    bool progress=false;
    if(header && header->ble_hdr_flags==8u && header->buff_start && header->data_size){
        const uint8_t *event=header->buff_start+header->data_offset;
        if(event[0]==0x13u){
            uint32_t packets=0u;uint16_t h=comp_v11_ble_observe_ll_handle();
            bool valid=header->data_size>=3u && comp_credit_packet_count(event,h,&packets) &&
                header->data_size==(uint16_t)event[1]+2u;
            comp_v11_ble_observe_ll_completed(packets,valid);
            progress=valid&&packets&&h==connection&&connection_secured;
        }else if(event[0]==0x05u && header->data_size==6u && event[2]==0u){
            comp_v11_ble_observe_ll_disconnect((uint16_t)event[3]|((uint16_t)event[4]<<8u));
        }
    }
    const uint8_t status=report_original_transport(header);
    /* The original queue owns header now. Only retained scalar validation
     * is used; queue acceptance is not a claim that credits were consumed. */
    if(comp_credit_wakeup_transport_queued(progress,report_original_transport==hci_queue_send_pckt,status))
        comp_v11_ble_controller_progress_hint();
    return status;
}
ble_stat_t __real_ll_hci_init(hci_trnsprt_cbk callback);
ble_stat_t __wrap_ll_hci_init(hci_trnsprt_cbk callback)
{
    if(callback && callback!=comp_v11_report_transport){
        report_original_transport=callback;return __real_ll_hci_init(comp_v11_report_transport);
    }
    return __real_ll_hci_init(callback);
}
ble_stat_t __real_ll_intf_acl_data_from_host_to_cntrlr(uint16_t h,ble_buff_hdr_t *packet);
ble_stat_t __wrap_ll_intf_acl_data_from_host_to_cntrlr(uint16_t h,ble_buff_hdr_t *packet)
{
    bool observed=packet!=NULL && h<0x0f00u;
    /* REAL may consume/free the descriptor even on failure. Capture public
     * metadata before ownership crosses the interface; never read it after. */
    const uint16_t bytes=observed?packet->data_size:0u;
    const uint8_t flags=observed?packet->ble_hdr_flags:0u;
#if COMPANION_WBA_ACL_READINESS_PROFILE
    if(observed) {
        const bool bounded=comp_acl_ready_slice_valid(packet->buff_start,
            packet->data_offset,bytes,packet->total_len);
        comp_v11_ble_acl_admission_begin(h,bounded?packet->buff_start+packet->data_offset:NULL,bytes,flags);
    }
#endif
    if(observed)comp_v11_ble_observe_ll_send(h,true,false);
    ble_stat_t status=__real_ll_intf_acl_data_from_host_to_cntrlr(h,packet);
#if COMPANION_WBA_ACL_READINESS_PROFILE
    /* Original owns/freed packet: finish uses only saved scalar metadata. */
    if(observed)comp_v11_ble_acl_admission_end(status==BLE_STATUS_SUCCESS);
#endif
    comp_v11_ble_pending_acl_send_result(status);
    if(observed && status!=BLE_STATUS_SUCCESS){
        uint32_t mask=__get_PRIMASK();__disable_irq();
        comp_v11_ble_send_failure_record(&ll_send_failures,status,flags,bytes);
        __set_PRIMASK(mask);
    }
    if(observed)comp_v11_ble_observe_ll_send(h,false,status==BLE_STATUS_SUCCESS);
    return status;
}
