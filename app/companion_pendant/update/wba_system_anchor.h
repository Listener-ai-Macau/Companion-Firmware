#ifndef COMPANION_WBA_SYSTEM_ANCHOR_H
#define COMPANION_WBA_SYSTEM_ANCHOR_H
#include "wba_system_journal.h"

#define COMP_WBA_SYSTEM_ANCHOR_RECORD_BYTES 556u
#define COMP_WBA_SYSTEM_ANCHOR_PREPARED 1u
#define COMP_WBA_SYSTEM_ANCHOR_INSTALLING 2u
#define COMP_WBA_SYSTEM_ANCHOR_INSTALLED 3u
#define COMP_WBA_SYSTEM_ANCHOR_RETIRED 4u

/* Fixed discovery addresses are usable ONLY inside the authenticated tail
 * claim. They are not a third partition: reserve includes both sectors and
 * the131072B metadata snapshot; all are reclaimed after joint confirmation.
 * No old firmware/resource backup is made. */
typedef struct {
    bool (*read)(void *,uint32_t,uint8_t *,size_t);
    bool (*program)(void *,uint32_t,const uint8_t *,size_t);
    bool (*erase_sector)(void *,uint32_t);
    /* idle must freeze ALL dynamic metadata writers, not merely audio/BLE. */
    bool (*idle)(void *);
    bool (*claim_held)(void *,uint32_t base,uint32_t bytes);
    void (*keep_alive)(void *);
    /* Resident installer checks destination app+bank before INSTALLED.
     * Running app checks actual Flash AND mounted bank before RETIRED. */
    bool (*installed_pair_verified)(void *,const uint8_t wire[452]);
    bool (*running_pair_verified)(void *,const uint8_t wire[452]);
    void *context;
    comp_wba_update_p256_trust_t trust;
} comp_wba_system_anchor_ports_t;

typedef struct {
    comp_wba_system_anchor_ports_t ports;
    uint8_t record[COMP_WBA_SYSTEM_ANCHOR_RECORD_BYTES];
    uint8_t sector;
    bool mounted,loaded,usable;
} comp_wba_system_anchor_t;

/* Read-only discovery works even after old dynamic roots are overwritten.
 * Both entire sectors must be readable. Torn-only/foreign/conflicting anchors
 * fail closed; an intact signed peer permits resuming after a torn transition.
 */
bool comp_wba_system_anchor_mount(comp_wba_system_anchor_t *,
    const comp_wba_system_anchor_ports_t *,bool *blank);
/* Requires exact durable PAIR_READY in the old geometry's actual WSR2 journal,
 * its CFL3 roots, and an exclusive full tail claim. Snapshot is read back and
 * hashed before PREPARED is committed. scratch>=256, no hidden payload buffer.
 * Receiver finish clears both anchors before VERIFYING; prepare never formats
 * foreign/torn-only data. Remount is required after any ambiguous I/O failure.
 */
bool comp_wba_system_anchor_prepare(comp_wba_system_anchor_t *,
    const uint8_t ready_record[488],uint32_t old_static_bytes,uint8_t *scratch,size_t capacity);
/* Repair ONLY the first torn PREPARED write, with bank B still fully erased.
 * Caller supplies an authenticated, actually running CFC2 current pair. The
 * exact ready journal, full tail lease, frozen metadata SHA and every programmed
 * bit of bank A must match the expected first record. No current destination or
 * metadata is erased; prepare recopies the current metadata after this repair.
 * Foreign, conflicting, later-phase, or unreadable records remain blocked. */
bool comp_wba_system_anchor_reprepare_first(comp_wba_system_anchor_t *,
    const uint8_t ready_record[488],const uint8_t current_wire[452],
    uint32_t old_static_bytes,uint8_t *scratch,size_t capacity);
/* Rehash the frozen snapshot, no mutation; Boot must do this before migrating.
 * It does not prove recording-directory relocation or loss authorization. */
bool comp_wba_system_anchor_verify_snapshot(comp_wba_system_anchor_t *,uint8_t *,size_t);
/* Reusable on every resident-boot resume BEFORE any destructive write, even
 * when INSTALLING was already durable before power loss. Read-only; verifies
 * both staged images, exact vector bounds and frozen metadata snapshot. */
bool comp_wba_system_anchor_verify_candidate(comp_wba_system_anchor_t *,uint8_t *,size_t);
/* PREPARED->INSTALLING freshly verifies BOTH staged images (SHA/CRC/vector)
 * and snapshot. Subsequent transitions require the actual pair callbacks.
 * One failed/torn store never authorizes destructive work or releases claim.
 * Caller handles actual installation, metadata relocation, and final release.
 */
bool comp_wba_system_anchor_advance(comp_wba_system_anchor_t *,uint8_t phase,uint8_t *,size_t);
#endif
