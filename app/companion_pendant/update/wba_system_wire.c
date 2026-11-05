#include "wba_system_wire.h"
#include <string.h>

static uint32_t u32(const uint8_t *p)
{
    return (uint32_t)p[0] | ((uint32_t)p[1]<<8) |
        ((uint32_t)p[2]<<16) | ((uint32_t)p[3]<<24);
}

bool comp_wba_system_wire_decode(const uint8_t *wire,size_t bytes,
                                 comp_wba_system_pair_t *pair)
{
    uint8_t nonzero=0u;
    uint32_t aligned_firmware;
    if(pair==NULL)return false;
    memset(pair,0,sizeof(*pair));
    if(wire==NULL || bytes!=COMP_WBA_SYSTEM_WIRE_BYTES ||
        memcmp(wire,"WSB2",4u) || wire[4]!=COMP_WBA_SYSTEM_WIRE_VERSION ||
        wire[5]!=COMP_WBA_SYSTEM_NEW_ONLY_FLAGS || wire[6]!=96u || wire[7]!=0u ||
        u32(wire+8u)!=COMP_WBA_UPDATE_TARGET_FAMILY_STM32WBA ||
        u32(wire+12u)!=COMP_WBA_UPDATE_BOARD_COMPANION_V11 ||
        u32(wire+20u)!=COMP_WBA_APP_ADDRESS ||
        u32(wire+24u)!=COMP_WBA_BOOT_APP_CAPACITY ||
        u32(wire+28u)!=COMP_WBA_APP_END ||
        u32(wire+448u)!=comp_wba_update_wire_crc32(wire,448u))return false;
    pair->key_id=u32(wire+16u);
    pair->nor_bytes=u32(wire+32u);
    pair->static_bytes=u32(wire+36u);
    pair->system_bytes=u32(wire+40u);
    pair->firmware_offset=u32(wire+44u);
    pair->resource_offset=u32(wire+48u);
    pair->staging_bytes=u32(wire+52u);
    pair->root_a=u32(wire+56u);
    pair->root_b=u32(wire+60u);
    memcpy(pair->bundle_id,wire+64u,32u);
    for(size_t i=0u;i<32u;i++)nonzero|=pair->bundle_id[i];
    if(pair->key_id==0u || !nonzero ||
        pair->nor_bytes!=COMP_WBA_NOR_TOTAL_BYTES ||
        pair->system_bytes!=COMP_WBA_NOR_SYSTEM_BYTES ||
        pair->static_bytes<2u*COMP_WBA_NOR_SECTOR_BYTES ||
        pair->static_bytes%COMP_WBA_NOR_SECTOR_BYTES ||
        pair->static_bytes>pair->nor_bytes-pair->system_bytes-COMP_WBA_NOR_SECTOR_BYTES ||
        pair->root_a!=pair->static_bytes-2u*COMP_WBA_NOR_SECTOR_BYTES ||
        pair->root_b!=pair->static_bytes-COMP_WBA_NOR_SECTOR_BYTES ||
        pair->firmware_offset!=0u ||
        !comp_wba_update_manifest_wire_decode(wire+96u,144u,&pair->firmware) ||
        !comp_wba_update_manifest_wire_decode(wire+240u,144u,&pair->resources))goto failed;
    const comp_wba_update_manifest_t *fw=&pair->firmware.manifest;
    const comp_wba_update_manifest_t *ui=&pair->resources.manifest;
    if(pair->firmware.key_id!=pair->key_id || pair->resources.key_id!=pair->key_id ||
        fw->target!=COMP_WBA_UPDATE_TARGET_FIRMWARE ||
        fw->format_version!=COMP_WBA_UPDATE_FIRMWARE_FORMAT_RELOCATED_BIN ||
        fw->target_family!=COMP_WBA_UPDATE_TARGET_FAMILY_STM32WBA ||
        fw->board_target!=COMP_WBA_UPDATE_BOARD_COMPANION_V11 ||
        fw->size_bytes<8u || fw->size_bytes>COMP_WBA_BOOT_APP_CAPACITY ||
        ui->target!=COMP_WBA_UPDATE_TARGET_UI_ASSETS ||
        ui->format_version!=COMP_WBA_UPDATE_UI_FORMAT_PARTITION_IMAGE_V1 ||
        ui->target_family!=fw->target_family || ui->board_target!=fw->board_target ||
        ui->size_bytes!=pair->static_bytes ||
        ui->minimum_app_version!=fw->component_version ||
        ui->maximum_app_version!=fw->component_version)goto failed;
    /* fw capacity bounds the addition; static is bounded before subtraction.
     * One shared reservation contains the new pair and temporary recovery
     * metadata/anchors. It never contains old firmware/resource backups.
     */
    aligned_firmware=(fw->size_bytes+COMP_WBA_NOR_SECTOR_BYTES-1u)&
        ~(COMP_WBA_NOR_SECTOR_BYTES-1u);
    if(pair->resource_offset!=aligned_firmware ||
        pair->staging_bytes!=aligned_firmware+pair->static_bytes+COMP_WBA_SYSTEM_RECOVERY_BYTES ||
        pair->staging_bytes>pair->nor_bytes-pair->static_bytes-pair->system_bytes)
        goto failed;
    return true;
failed:
    memset(pair,0,sizeof(*pair));
    return false;
}

bool comp_wba_system_wire_authorize(const uint8_t *wire,size_t bytes,
    const comp_wba_update_p256_trust_t *trust,comp_wba_system_pair_t *pair)
{
    companion_sha256_t hash;
    uint8_t digest[32];
    if(!comp_wba_system_wire_decode(wire,bytes,pair))return false;
    if(!comp_wba_update_p256_trust_configured(trust) || pair->key_id!=trust->key_id)
        goto failed;
    companion_sha256_init(&hash);
    companion_sha256_update(&hash,wire,COMP_WBA_SYSTEM_SIGNED_BYTES);
    companion_sha256_final(&hash,digest);
    if(!trust->verify_digest(trust->verify_context,trust->public_key_xy,digest,wire+384u) ||
        !comp_wba_update_p256_authorize_manifest((void *)trust,&pair->firmware.manifest,
            pair->firmware.signature,COMP_WBA_UPDATE_P256_SIGNATURE_BYTES) ||
        !comp_wba_update_p256_authorize_manifest((void *)trust,&pair->resources.manifest,
            pair->resources.signature,COMP_WBA_UPDATE_P256_SIGNATURE_BYTES))goto failed;
    return true;
failed:
    memset(pair,0,sizeof(*pair));
    return false;
}
