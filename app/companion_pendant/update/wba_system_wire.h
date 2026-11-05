#ifndef COMPANION_WBA_SYSTEM_WIRE_H
#define COMPANION_WBA_SYSTEM_WIRE_H

#include "wba_update_p256.h"

/* WSB2 v2 binds the new firmware/resource pair and both Flash geometries.
 * All integers are LE; signatures remain raw big-endian r||s. This 452-byte
 * descriptor fits one negotiated512 ATT write, but the production GATT
 * receiver must explicitly advertise the new paired capability before use.
 * It is NOT a WUM1 manifest and cannot activate either component alone.
 * bytes0..383 are signed;384..447 hold the signature;448..451 hold CRC32.
 * No old-image backup/rollback is permitted by flags1.
 */
#define COMP_WBA_SYSTEM_WIRE_BYTES 452u
#define COMP_WBA_SYSTEM_SIGNED_BYTES 384u
#define COMP_WBA_SYSTEM_NEW_ONLY_FLAGS 1u
#define COMP_WBA_SYSTEM_WIRE_VERSION 2u
/* Temporary metadata snapshot and two discoverable tail anchors are part of
 * this update's ONE dynamic claim, not permanent partitions/old image copies.
 * Their locations are derived from the signed pair's extent. */
#define COMP_WBA_SYSTEM_ANCHOR_BYTES (2u*COMP_WBA_NOR_SECTOR_BYTES)
#define COMP_WBA_SYSTEM_RECOVERY_BYTES (COMP_WBA_NOR_SYSTEM_BYTES+COMP_WBA_SYSTEM_ANCHOR_BYTES)

typedef struct {
    uint8_t bundle_id[32];
    uint32_t key_id;
    uint32_t nor_bytes;
    uint32_t static_bytes;
    uint32_t system_bytes;
    uint32_t firmware_offset;
    uint32_t resource_offset;
    uint32_t staging_bytes;
    uint32_t root_a;
    uint32_t root_b;
    comp_wba_update_manifest_envelope_t firmware;
    comp_wba_update_manifest_envelope_t resources;
} comp_wba_system_pair_t;

/* Structural parsing only, no authorization or storage mutation. Geometry
 * must match this compiled MCU/Boot target; new bank growth is represented,
 * never interpreted as permission to overwrite existing dynamic metadata.
 * Output is cleared on failure; wire and output must not overlap.
 */
bool comp_wba_system_wire_decode(const uint8_t *wire, size_t bytes,
                                 comp_wba_system_pair_t *pair);

/* Use the existing product's P256 trust callback (hardware PKA on WBA).
 * Verify the outer pair AND the two ordinary component signatures, borrowing
 * one hash workspace per call. No persistent RAM buffer, allocation, NOR,
 * reset, radio or private SDK interface is used here.
 */
bool comp_wba_system_wire_authorize(const uint8_t *wire, size_t bytes,
    const comp_wba_update_p256_trust_t *trust, comp_wba_system_pair_t *pair);

#endif
