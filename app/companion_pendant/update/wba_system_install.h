#ifndef COMPANION_WBA_SYSTEM_INSTALL_H
#define COMPANION_WBA_SYSTEM_INSTALL_H
#include "wba_system_anchor.h"

typedef enum {
    COMP_WBA_SYSTEM_INSTALL_WORK=1,
    COMP_WBA_SYSTEM_INSTALL_BOOT_PAIR=2,
    COMP_WBA_SYSTEM_INSTALL_RECOVERY=3
} comp_wba_system_install_action_t;

typedef struct {
    bool (*flash_read)(void *,uint32_t,uint8_t *,size_t);
    bool (*flash_erase_page)(void *,uint32_t);
    bool (*flash_program)(void *,uint32_t,const uint8_t *,size_t);
    /* Mandatory durable plan/policy: snapshot catalog ownership, front growth
     * conflicts and any specifically authorized unsynced loss. A tail claim,
     * an app version or an idle state alone must NEVER satisfy this callback.
     * Called before PREPARED changes and again on INSTALLING resume. */
    bool (*layout_authorized)(void *,const uint8_t anchor[556]);
    /* Relocate/transform dynamic metadata from the verified frozen snapshot.
     * One step may erase at most one metadata sector. Must be idempotent from
     * the anchor after restart, preserve identity/settings and translate exact
     * recording ownership; never silently initialize a missing catalog. */
    bool (*layout_step)(void *,const uint8_t anchor[556],uint8_t *,size_t,bool *done);
    bool (*layout_verified)(void *,const uint8_t anchor[556]);
    void *context;
} comp_wba_system_install_ports_t;

typedef struct {
    comp_wba_system_install_ports_t ports;
    comp_wba_system_anchor_t *anchor;
    companion_sha256_t hash;
    uint32_t page,offset,crc;
    uint8_t stage,component;
    bool page_diff,usable;
} comp_wba_system_installer_t;

/* Resident Boot ONLY. Requires a mounted signed PREPARED/INSTALLING/INSTALLED
 * anchor. Retired/no-anchor normal boot and long-term confirmed geometry lookup
 * are separate. No old-image fallback, release, reset or radio operation.
 * Init needs distinct caller scratch512..8192B. On resume every staged byte
 * and snapshot is reverified before erase; no RAM cursor is trusted. */
bool comp_wba_system_install_init(comp_wba_system_installer_t *,
    comp_wba_system_anchor_t *,const comp_wba_system_install_ports_t *,uint8_t *,size_t);
/* Borrowed scratch is split into source/readback halves; no page buffer/BSS.
 * Each poll copies/compares/hashes at most half the scratch or erases one8KiB
 * app page/one4KiB resource sector. Partial target pages are erased again after
 * restart; exact pages are skipped. Source and target never overlap.
 * BOOT_PAIR follows actual destination hashes, layout verification and durable
 * INSTALLED only. It is not runtime joint confirmation or updater release. */
comp_wba_system_install_action_t comp_wba_system_install_poll(
    comp_wba_system_installer_t *,uint8_t *,size_t);
#endif
