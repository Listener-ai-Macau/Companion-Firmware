#ifndef COMPANION_WBA_SIMPLE_PACKAGE_H
#define COMPANION_WBA_SIMPLE_PACKAGE_H

#include "wba_update_p256.h"

/* One file: existing signed WUM1(144), CUP3 descriptor(32), App, UI bank.
 * WUM1 firmware format3 signs the entire descriptor+App+UI payload. Legacy
 * relocated-bin format1 and paired WSB2 are not this install protocol.
 * Download uses DOV1 unchanged; only Boot authenticates/installs the file. */
#define COMP_WBA_SIMPLE_FORMAT 3u
#define COMP_WBA_SIMPLE_DESCRIPTOR_BYTES 32u
#define COMP_WBA_SIMPLE_HEADER_BYTES (COMP_WBA_UPDATE_MANIFEST_WIRE_BYTES+32u)

typedef struct {
    uint32_t board_target,app_address,app_capacity;
    uint32_t static_bytes,nor_bytes,metadata_bytes;
} comp_wba_simple_limits_t;

typedef struct {
    comp_wba_update_manifest_envelope_t signed_manifest;
    uint8_t descriptor[COMP_WBA_SIMPLE_DESCRIPTOR_BYTES];
    uint32_t app_bytes,resource_bytes,resource_version;
} comp_wba_simple_package_t;

/* Structural checks only: no signature claim and no storage mutation.
 * First implementation requires the current static extent, not a permanent
 *1MiB limit. Geometry changes require a separately supported migration. */
bool comp_wba_simple_package_open(comp_wba_simple_package_t *,
    const uint8_t *header,size_t header_bytes,const comp_wba_simple_limits_t *);

/* Monotonic admission for a new download. Boot resuming an interrupted
 * install instead uses the exact retained pending header, not this predicate. */
bool comp_wba_simple_package_newer(const comp_wba_simple_package_t *,
    uint32_t installed_app,uint32_t installed_resources);

typedef bool (*comp_wba_simple_read_fn)(void *,uint32_t file_offset,
                                      uint8_t *,size_t);

/* Read-only full-file verification. Verify the existing P-256 signature,
 * whole signed payload SHA/CRC, then physical CE vector bounds. scratch is
 * caller-owned; this module allocates no heap or static receive buffer.
 * Neither a successful decode nor a DOV1 FINISH authorizes installation.
 * A Boot adapter may erase destinations only AFTER this returns true. */
bool comp_wba_simple_package_verify(const comp_wba_simple_package_t *,
    const comp_wba_simple_limits_t *,const comp_wba_update_p256_trust_t *,
    comp_wba_simple_read_fn,void *,uint8_t *scratch,size_t scratch_bytes);
/* Failure-only Boot diagnostic, outside the PKA critical sequence. */
void comp_wba_simple_verify_failure(uint32_t stage);

#endif
