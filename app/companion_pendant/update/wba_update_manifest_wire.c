#include "../storage/companion_crc32.h"
#include "wba_update_manifest_wire.h"

#include <string.h>

enum {
    OFF_MAGIC = 0,
    OFF_SCHEMA = 4,
    OFF_TARGET = 5,
    OFF_FORMAT = 6,
    OFF_FAMILY = 8,
    OFF_BOARD = 12,
    OFF_COMPONENT_VERSION = 16,
    OFF_MIN_APP = 20,
    OFF_MAX_APP = 24,
    OFF_SIZE = 28,
    OFF_PAYLOAD_CRC = 32,
    OFF_SHA256 = 36,
    OFF_ALGORITHM = 68,
    OFF_FLAGS = 69,
    OFF_RESERVED = 70,
    OFF_KEY_ID = 72,
    OFF_SIGNATURE = 76,
    OFF_WIRE_CRC = 140,
};

static void put16(uint8_t *p, uint16_t value)
{
    p[0] = (uint8_t)value;
    p[1] = (uint8_t)(value >> 8);
}

static void put32(uint8_t *p, uint32_t value)
{
    p[0] = (uint8_t)value;
    p[1] = (uint8_t)(value >> 8);
    p[2] = (uint8_t)(value >> 16);
    p[3] = (uint8_t)(value >> 24);
}

static uint16_t get16(const uint8_t *p)
{
    return (uint16_t)((uint16_t)p[0] | ((uint16_t)p[1] << 8));
}

static uint32_t get32(const uint8_t *p)
{
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8) |
           ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}

uint32_t comp_wba_update_wire_crc32(const uint8_t *data, size_t length)
{
    if (data == NULL && length != 0u) return 0u;
    /* Existing shared finalized-seed IEEE implementation accepts size_t
     * directly. Preserve the public empty/invalid-input convention. */
    return companion_crc32(0u, data, length);
}

bool comp_wba_update_manifest_signed_bytes(
    const comp_wba_update_manifest_t *manifest, uint32_t key_id,
    uint8_t output[COMP_WBA_UPDATE_MANIFEST_SIGNED_BYTES])
{
    if (manifest == NULL || output == NULL || key_id == 0u ||
        manifest->schema_version != COMP_WBA_UPDATE_MANIFEST_SCHEMA ||
        (manifest->target != COMP_WBA_UPDATE_TARGET_FIRMWARE &&
         manifest->target != COMP_WBA_UPDATE_TARGET_UI_ASSETS) ||
        manifest->format_version == 0u || manifest->target_family == 0u ||
        manifest->board_target == 0u || manifest->component_version == 0u ||
        manifest->size_bytes == 0u) return false;
    memset(output, 0, COMP_WBA_UPDATE_MANIFEST_SIGNED_BYTES);
    memcpy(output + OFF_MAGIC, "WUM1", 4u);
    output[OFF_SCHEMA] = manifest->schema_version;
    output[OFF_TARGET] = manifest->target;
    put16(output + OFF_FORMAT, manifest->format_version);
    put32(output + OFF_FAMILY, manifest->target_family);
    put32(output + OFF_BOARD, manifest->board_target);
    put32(output + OFF_COMPONENT_VERSION, manifest->component_version);
    put32(output + OFF_MIN_APP, manifest->minimum_app_version);
    put32(output + OFF_MAX_APP, manifest->maximum_app_version);
    put32(output + OFF_SIZE, manifest->size_bytes);
    put32(output + OFF_PAYLOAD_CRC, manifest->crc32);
    memcpy(output + OFF_SHA256, manifest->sha256, 32u);
    output[OFF_ALGORITHM] = COMP_WBA_UPDATE_SIGNATURE_P256_SHA256;
    put32(output + OFF_KEY_ID, key_id);
    return true;
}

bool comp_wba_update_manifest_wire_encode(
    const comp_wba_update_manifest_t *manifest, uint32_t key_id,
    const uint8_t signature[COMP_WBA_UPDATE_P256_SIGNATURE_BYTES],
    uint8_t output[COMP_WBA_UPDATE_MANIFEST_WIRE_BYTES])
{
    if (signature == NULL || output == NULL ||
        !comp_wba_update_manifest_signed_bytes(manifest, key_id, output)) return false;
    memcpy(output + OFF_SIGNATURE, signature, COMP_WBA_UPDATE_P256_SIGNATURE_BYTES);
    put32(output + OFF_WIRE_CRC,
          comp_wba_update_wire_crc32(output, OFF_WIRE_CRC));
    return true;
}

bool comp_wba_update_manifest_wire_decode(
    const uint8_t *wire, size_t wire_bytes,
    comp_wba_update_manifest_envelope_t *envelope)
{
    uint8_t canonical[COMP_WBA_UPDATE_MANIFEST_SIGNED_BYTES];
    if (wire == NULL || envelope == NULL ||
        wire_bytes != COMP_WBA_UPDATE_MANIFEST_WIRE_BYTES ||
        memcmp(wire + OFF_MAGIC, "WUM1", 4u) != 0 ||
        wire[OFF_SCHEMA] != COMP_WBA_UPDATE_MANIFEST_SCHEMA ||
        wire[OFF_ALGORITHM] != COMP_WBA_UPDATE_SIGNATURE_P256_SHA256 ||
        wire[OFF_FLAGS] != 0u || get16(wire + OFF_RESERVED) != 0u ||
        get32(wire + OFF_WIRE_CRC) !=
            comp_wba_update_wire_crc32(wire, OFF_WIRE_CRC)) return false;
    memset(envelope, 0, sizeof(*envelope));
    envelope->manifest.schema_version = wire[OFF_SCHEMA];
    envelope->manifest.target = wire[OFF_TARGET];
    envelope->manifest.format_version = get16(wire + OFF_FORMAT);
    envelope->manifest.target_family = get32(wire + OFF_FAMILY);
    envelope->manifest.board_target = get32(wire + OFF_BOARD);
    envelope->manifest.component_version = get32(wire + OFF_COMPONENT_VERSION);
    envelope->manifest.minimum_app_version = get32(wire + OFF_MIN_APP);
    envelope->manifest.maximum_app_version = get32(wire + OFF_MAX_APP);
    envelope->manifest.size_bytes = get32(wire + OFF_SIZE);
    envelope->manifest.crc32 = get32(wire + OFF_PAYLOAD_CRC);
    memcpy(envelope->manifest.sha256, wire + OFF_SHA256, 32u);
    envelope->key_id = get32(wire + OFF_KEY_ID);
    memcpy(envelope->signature, wire + OFF_SIGNATURE,
           COMP_WBA_UPDATE_P256_SIGNATURE_BYTES);
    if (!comp_wba_update_manifest_signed_bytes(&envelope->manifest,
                                                envelope->key_id, canonical) ||
        memcmp(canonical, wire, sizeof(canonical)) != 0) {
        memset(envelope, 0, sizeof(*envelope));
        return false;
    }
    return true;
}

