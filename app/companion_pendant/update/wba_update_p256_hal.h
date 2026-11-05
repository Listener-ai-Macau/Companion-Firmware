#ifndef COMPANION_WBA_UPDATE_P256_HAL_H
#define COMPANION_WBA_UPDATE_P256_HAL_H

#include "wba_update_p256.h"
#include "stm32wbaxx_hal.h"
#include "stm32wbaxx_hal_pka.h"

#ifdef __cplusplus
extern "C" {
#endif

/* The acquire callback must serialize with CubeWBA PKACTRL/BLE users and make
 * the already initialized PKA clock/security domain usable. Verification is
 * foreground-only. release is always called after a successful acquire. */
typedef struct {
    PKA_HandleTypeDef *hpka;
    bool (*acquire)(void *context);
    void (*release)(void *context);
    void *context;
    uint32_t timeout_ms;
} comp_wba_update_p256_hal_t;

bool comp_wba_update_p256_hal_verify_digest(
    void *context,
    const uint8_t public_key_xy[COMP_WBA_UPDATE_P256_PUBLIC_KEY_BYTES],
    const uint8_t digest[COMP_WBA_UPDATE_SHA256_BYTES],
    const uint8_t signature[COMP_WBA_UPDATE_P256_SIGNATURE_BYTES]);

#ifdef __cplusplus
}
#endif

#endif
