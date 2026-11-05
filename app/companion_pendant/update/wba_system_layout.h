#ifndef COMPANION_WBA_SYSTEM_LAYOUT_H
#define COMPANION_WBA_SYSTEM_LAYOUT_H
#include "wba_system_anchor.h"
#include "companion_segment_catalog.h"
#include "companion_recording_journal.h"

typedef struct {
    bool (*read)(void *,uint32_t,uint8_t *,size_t);
    bool (*program)(void *,uint32_t,const uint8_t *,size_t);
    bool (*erase_sector)(void *,uint32_t);
    void (*keep_alive)(void *);
    void *context;
} comp_wba_system_layout_ports_t;
typedef struct {
    comp_wba_system_layout_ports_t ports;
    comp_segment_catalog_t segments;
    comp_recording_journal_catalog_t legacy;
    uint32_t old_static,new_static,source,tail,sector,offset;
    uint8_t layout_root[64],phase;
    bool legacy_blank,usable,finished,immutable_source;
} comp_wba_system_layout_t;

/* Read-only actual ownership preflight. source is either old_static BEFORE
 * download, or the authenticated131072B frozen snapshot during Boot. Includes
 * both legacy and segmented directories, CSI1 UID/epoch and front/tail bounds.
 * Active/recovering records, unknown/corrupt roots, overlaps or any collision
 * are refused; there is no implicit loss authorization/formatting. The product
 * can first finish/sync or separately obtain specific loss confirmation.
 * All metadata writers must stay frozen after this plan is created. */
bool comp_wba_system_layout_init(comp_wba_system_layout_t *,
    const comp_wba_system_layout_ports_t *,uint32_t old_static,uint32_t new_static,
    uint32_t protected_tail,uint32_t metadata_source,const uint8_t uid[12]);
/* Resident installer ports. Exact canonical catalog relocation, settings and
 * namespace byte preservation, original physical audio untouched. Restart
 * reconstructs the same plan from the frozen snapshot and skips exact pages.
 * One poll compares/programs<=256B or erases one4KiB sector. scratch>=256B.
 * Failed/uncertain I/O poisons this plan; remount the anchor and reinitialize.
 * done follows byte-for-byte verification, not just a new CFL3 root. */
bool comp_wba_system_layout_step(comp_wba_system_layout_t *,uint8_t *,size_t,bool *done);
bool comp_wba_system_layout_verify(comp_wba_system_layout_t *,uint8_t *,size_t);
#endif
