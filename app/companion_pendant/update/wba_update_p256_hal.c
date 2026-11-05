#include "wba_update_p256_hal.h"

#include <string.h>

/* Optional diagnostics only. No trace result participates in authorization. */
#if defined(__GNUC__)
__attribute__((weak))
#endif
void comp_wba_update_p256_hal_trace(uint32_t stage,uint32_t status,uint32_t error)
{(void)stage;(void)status;(void)error;}

/* SEC 2 secp256r1/P-256 parameters, big endian as required by STM32 HAL PKA. */
static const uint8_t curve_p[32] = {
    0xff,0xff,0xff,0xff,0x00,0x00,0x00,0x01,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,
    0x00,0x00,0x00,0x00,0xff,0xff,0xff,0xff,0xff,0xff,0xff,0xff,0xff,0xff,0xff,0xff};
static const uint8_t curve_a[32] = {
    0xff,0xff,0xff,0xff,0x00,0x00,0x00,0x01,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,
    0x00,0x00,0x00,0x00,0xff,0xff,0xff,0xff,0xff,0xff,0xff,0xff,0xff,0xff,0xff,0xfc};
static const uint8_t curve_b[32] = {
    0x5a,0xc6,0x35,0xd8,0xaa,0x3a,0x93,0xe7,0xb3,0xeb,0xbd,0x55,0x76,0x98,0x86,0xbc,
    0x65,0x1d,0x06,0xb0,0xcc,0x53,0xb0,0xf6,0x3b,0xce,0x3c,0x3e,0x27,0xd2,0x60,0x4b};
static const uint8_t curve_gx[32] = {
    0x6b,0x17,0xd1,0xf2,0xe1,0x2c,0x42,0x47,0xf8,0xbc,0xe6,0xe5,0x63,0xa4,0x40,0xf2,
    0x77,0x03,0x7d,0x81,0x2d,0xeb,0x33,0xa0,0xf4,0xa1,0x39,0x45,0xd8,0x98,0xc2,0x96};
static const uint8_t curve_gy[32] = {
    0x4f,0xe3,0x42,0xe2,0xfe,0x1a,0x7f,0x9b,0x8e,0xe7,0xeb,0x4a,0x7c,0x0f,0x9e,0x16,
    0x2b,0xce,0x33,0x57,0x6b,0x31,0x5e,0xce,0xcb,0xb6,0x40,0x68,0x37,0xbf,0x51,0xf5};
static const uint8_t curve_n[32] = {
    0xff,0xff,0xff,0xff,0x00,0x00,0x00,0x00,0xff,0xff,0xff,0xff,0xff,0xff,0xff,0xff,
    0xbc,0xe6,0xfa,0xad,0xa7,0x17,0x9e,0x84,0xf3,0xb9,0xca,0xc2,0xfc,0x63,0x25,0x51};

static bool scalar_in_range(const uint8_t scalar[32])
{
    uint8_t any = 0u;
    for (size_t i = 0u; i < 32u; ++i) any |= scalar[i];
    return any != 0u && memcmp(scalar, curve_n, 32u) < 0;
}

bool comp_wba_update_p256_hal_verify_digest(
    void *context,
    const uint8_t public_key_xy[COMP_WBA_UPDATE_P256_PUBLIC_KEY_BYTES],
    const uint8_t digest[COMP_WBA_UPDATE_SHA256_BYTES],
    const uint8_t signature[COMP_WBA_UPDATE_P256_SIGNATURE_BYTES])
{
    comp_wba_update_p256_hal_t *backend = context;
    PKA_PointCheckInTypeDef point;
    PKA_ECDSAVerifInTypeDef verify;
    PKA_MontgomeryParamInTypeDef montgomery = {sizeof(curve_p), curve_p};
    uint32_t montgomery_parameter[sizeof(curve_p) / sizeof(uint32_t)];
    bool valid = false;
    if (backend == NULL || backend->hpka == NULL || backend->acquire == NULL ||
        backend->release == NULL || backend->timeout_ms == 0u ||
        public_key_xy == NULL || digest == NULL || signature == NULL ||
        !scalar_in_range(signature) || !scalar_in_range(signature + 32u) ||
        !backend->acquire(backend->context)) return false;
    HAL_StatusTypeDef status=HAL_PKA_Init(backend->hpka);
    comp_wba_update_p256_hal_trace(1u,(uint32_t)status,backend->hpka->ErrorCode);
    if (status != HAL_OK) {
        backend->release(backend->context);
        return false;
    }
    /* This CubeWBA HAL rejects PointCheck when pMontgomeryParam is NULL.
     * Generate R2 for the field modulus with the HAL, then retain its native
     * word order for PointCheck. Any failure still rejects the signature. */
    status=HAL_PKA_MontgomeryParam(backend->hpka, &montgomery,backend->timeout_ms);
    comp_wba_update_p256_hal_trace(2u,(uint32_t)status,backend->hpka->ErrorCode);
    if (status != HAL_OK) goto finished;
    HAL_PKA_MontgomeryParam_GetResult(backend->hpka, montgomery_parameter);
    memset(&point, 0, sizeof(point));
    point.modulusSize = 32u;
    point.coefSign = 0u;
    point.coefA = curve_a;
    point.coefB = curve_b;
    point.modulus = curve_p;
    point.pointX = public_key_xy;
    point.pointY = public_key_xy + 32u;
    point.pMontgomeryParam = montgomery_parameter;
    status=HAL_PKA_PointCheck(backend->hpka, &point, backend->timeout_ms);
    uint32_t on_curve=status==HAL_OK?HAL_PKA_PointCheck_IsOnCurve(backend->hpka):0u;
    comp_wba_update_p256_hal_trace(3u,(uint32_t)status,backend->hpka->ErrorCode);
    comp_wba_update_p256_hal_trace(4u,on_curve,0u);
    if (status == HAL_OK && on_curve != 0u) {
        memset(&verify, 0, sizeof(verify));
        verify.primeOrderSize = 32u;
        verify.modulusSize = 32u;
        verify.coefSign = 0u;
        verify.coef = curve_a;
        verify.modulus = curve_p;
        verify.basePointX = curve_gx;
        verify.basePointY = curve_gy;
        verify.pPubKeyCurvePtX = public_key_xy;
        verify.pPubKeyCurvePtY = public_key_xy + 32u;
        verify.RSign = signature;
        verify.SSign = signature + 32u;
        verify.hash = digest;
        verify.primeOrder = curve_n;
        status=HAL_PKA_ECDSAVerif(backend->hpka,&verify,backend->timeout_ms);
        comp_wba_update_p256_hal_trace(5u,(uint32_t)status,backend->hpka->ErrorCode);
        valid=status==HAL_OK && HAL_PKA_ECDSAVerif_IsValidSignature(backend->hpka)!=0u;
        comp_wba_update_p256_hal_trace(6u,valid,0u);
    }
finished:
    (void)HAL_PKA_DeInit(backend->hpka);
    backend->release(backend->context);
    return valid;
}
