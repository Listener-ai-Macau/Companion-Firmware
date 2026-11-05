/* USER CODE BEGIN Header */
/**
  ******************************************************************************
  * @file    bleplat.c
  * @author  MCD Application Team
  * @brief   This file implements the platform functions for BLE stack library.
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

#include "app_common.h"
#include "bleplat.h"
#include "app_ble.h"
#include "baes.h"
#include "pka_ctrl.h"
#include "ble_timer.h"
#include "blestack.h"
#include "host_stack_if.h"

#include "ble_wrap.c"
#include "gatt_public_hash_diagnostic.h"
#include "gatt_hash_complete.h"
extern void GATT_Compute_Database_Hash(void);
static comp_v11_public_hash_trace_t public_hash_trace;
const comp_v11_public_hash_trace_t *comp_v11_ble_public_hash_trace(void)
{ return &public_hash_trace; }
bool comp_v11_ble_public_hash_fault(void){return public_hash_trace.faults!=0u;}
/* Only this public branch reserves a temporary complete input. Other SM,
 * pairing and authentication CMAC calls retain their original stack path. */
static __attribute__((noinline)) void complete_public_hash(uint8_t *output_tag)
{
    uint8_t input[COMP_V11_PUBLIC_GATT_HASH_INPUT_CAPACITY];size_t length=0u;
    if(comp_v11_ble_complete_public_hash_input(input,sizeof(input),&length)) {
        public_hash_trace.complete_input_bytes=(uint32_t)length;
        BAES_CmacCompute(input,(uint32_t)length,output_tag);
    } else {
        /* Never certify a truncated/unknown table. A fresh invalidation
         * token avoids accepting old cached state; foreground closes this
         * connection and latches a host fault before accepting new work. */
        uint32_t token[4];HW_RNG_Get(4u,token);memcpy(output_tag,token,sizeof(token));
        public_hash_trace.complete_input_bytes=0u;
        if(public_hash_trace.faults!=UINT32_MAX)++public_hash_trace.faults;
    }
}


/*****************************************************************************/

void BLEPLAT_Init( void )
{

  return;
}

/*****************************************************************************/

void BLEPLAT_NvmStore( const uint64_t* ptr,
                              uint16_t size )
{
  UNUSED(ptr);
  UNUSED(size);

  APP_BLE_HostNvmStore();
  return;
}

/*****************************************************************************/

void BLEPLAT_RngGet( uint8_t n,
                     uint32_t* val )
{
  /* Read 32-bit random values from HW driver */
  HW_RNG_Get( n, val );
}

/*****************************************************************************/

void BLEPLAT_AesEcbEncrypt( const uint8_t* key,
                            const uint8_t* input,
                            uint8_t* output )
{
  BAES_EcbCrypt( key, input, output, 1 );
}

/*****************************************************************************/

void BLEPLAT_AesCmacSetKey( const uint8_t* key )
{
  BAES_CmacSetKey( key );
}

/*****************************************************************************/

__attribute__((noinline)) void BLEPLAT_AesCmacCompute( const uint8_t* input,
                             uint32_t input_length,
                             uint8_t* output_tag )
{
  uintptr_t caller=(uintptr_t)__builtin_return_address(0);
  if((caller&~(uintptr_t)1u)==((uintptr_t)&GATT_Compute_Database_Hash&~(uintptr_t)1u)+COMP_V11_GATT_PUBLIC_CMAC_RETURN_OFFSET && input_length<=672u) {
      complete_public_hash(output_tag);
      comp_v11_public_hash_observe(&public_hash_trace,caller,
          (uintptr_t)&GATT_Compute_Database_Hash,input_length,output_tag);
  } else {
      BAES_CmacCompute( input, input_length, output_tag );
  }
}

/*****************************************************************************/

int BLEPLAT_AesCcmCrypt( uint8_t mode,
                         const uint8_t* key,
                         uint8_t iv_length,
                         const uint8_t* iv,
                         uint16_t add_length,
                         const uint8_t* add,
                         uint32_t input_length,
                         const uint8_t* input,
                         uint8_t tag_length,
                         uint8_t* tag,
                         uint8_t* output )
{
  return BAES_CcmCrypt( mode, key, iv_length, iv, add_length, add,
                        input_length, input, tag_length, tag, output );
}

/*****************************************************************************/

int BLEPLAT_PkaStartP256Key( const uint32_t* local_private_key )
{
  return PKACTRL_StartP256Key( local_private_key );
}

/*****************************************************************************/

void BLEPLAT_PkaReadP256Key( uint32_t* local_public_key )
{
  PKACTRL_ReadP256Key( local_public_key );
}

/*****************************************************************************/

int BLEPLAT_PkaStartDhKey( const uint32_t* local_private_key,
                           const uint32_t* remote_public_key )
{
  return PKACTRL_StartDhKey( local_private_key, remote_public_key );
}

/*****************************************************************************/

int BLEPLAT_PkaReadDhKey( uint32_t* dh_key )
{
  return PKACTRL_ReadDhKey( dh_key );
}

/*****************************************************************************/

void PKACTRL_CB_Complete( void )
{
  BLEPLATCB_PkaComplete( );

  BleStackCB_Process( );
}

/*****************************************************************************/

uint8_t BLEPLAT_TimerStart( uint16_t id,
                            uint32_t timeout )
{
  return BLE_TIMER_Start( id, timeout );
}

/*****************************************************************************/

void BLEPLAT_TimerStop( uint16_t id )
{
  BLE_TIMER_Stop( id );
}
/*****************************************************************************/
