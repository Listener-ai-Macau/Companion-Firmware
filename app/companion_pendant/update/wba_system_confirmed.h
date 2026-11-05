#ifndef COMPANION_WBA_SYSTEM_CONFIRMED_H
#define COMPANION_WBA_SYSTEM_CONFIRMED_H
#include "wba_system_wire.h"
#define COMP_WBA_SYSTEM_CONFIRMED_BYTES 472u
#define COMP_WBA_SYSTEM_CONFIRMED_A 0xA000u
#define COMP_WBA_SYSTEM_CONFIRMED_B 0xB000u
typedef struct {
    bool (*read)(void *,uint32_t,uint8_t *,size_t);
    bool (*program)(void *,uint32_t,const uint8_t *,size_t);
    bool (*erase_sector)(void *,uint32_t);
    void (*keep_alive)(void *);
    bool (*pair_verified)(void *,const uint8_t wire[452]);
    void *context;
    comp_wba_update_p256_trust_t trust;
} comp_wba_system_confirmed_ports_t;
typedef struct {
    comp_wba_system_confirmed_ports_t ports;
    uint8_t record[COMP_WBA_SYSTEM_CONFIRMED_BYTES];
    uint32_t static_bytes;
    uint8_t bank;
    bool loaded,usable;
} comp_wba_system_confirmed_t;
/* Two small receipts INSIDE existing dynamic metadata, not another partition
 * or old image backup. Full signed pair and both actual destination hashes are
 * mandatory. Commit this before retiring/releasing the temporary OTA tail.
 * Mount alone does not qualify running firmware/resources. */
bool comp_wba_system_confirmed_mount(comp_wba_system_confirmed_t *,
    const comp_wba_system_confirmed_ports_t *,uint32_t static_bytes,bool *blank);
bool comp_wba_system_confirmed_store(comp_wba_system_confirmed_t *,const uint8_t wire[452]);
/* Read-only Boot discovery after resource growth and tail reuse. CFL3 is only
 * an untrusted bounded locator; authority comes from all three signatures and
 * actual firmware/resource hashes. Refuses two different qualifying receipts.
 * Does not assume the Boot's original compiled resource size. */
bool comp_wba_system_confirmed_find(comp_wba_system_confirmed_t *,
    const comp_wba_system_confirmed_ports_t *);
#endif
