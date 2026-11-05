#ifndef COMPANION_WBA_SYSTEM_JOURNAL_H
#define COMPANION_WBA_SYSTEM_JOURNAL_H
#include "wba_system_receive.h"

/* Two existing 4KiB metadata sectors, eight append-only512B positions each.
 * No payload partition or hidden record cache. The current trusted layout
 * supplies dynamic_base; resource-growth relocation belongs to the coordinator.
 * I/O is synchronous foreground-only, exclusive to this one updater.
 */
typedef struct {
    bool (*read)(void *,uint32_t,uint8_t *,size_t);
    bool (*program)(void *,uint32_t,const uint8_t *,size_t);
    bool (*erase_sector)(void *,uint32_t);
    void *context;
    uint32_t dynamic_base;
} comp_wba_system_journal_ports_t;

typedef struct {
    comp_wba_system_journal_ports_t ports;
    uint64_t sequence;
    uint8_t sector,next_slot;
    bool mounted,usable,scanned;
} comp_wba_system_journal_t;

/* Both complete sectors must be readable. A blank result requires every byte
 * erased. Torn own records can be skipped only with an intact older record;
 * foreign prefixes, equal-sequence conflicts and torn-only media fail closed.
 * Returns the latest exact488B record, whose P256 is checked by the receiver.
 */
bool comp_wba_system_journal_mount(comp_wba_system_journal_t *,
    const comp_wba_system_journal_ports_t *,uint8_t record[488],bool *blank);
/* The receiver supplies sequence+1. Append into an untouched position. On
 * rotation erase only the sector without the newest valid record; read back
 * the full512B position before acknowledging. An ambiguous failure poisons
 * this instance until mount; never advance a guessed cursor or reuse torn bits.
 */
bool comp_wba_system_journal_store(comp_wba_system_journal_t *,const uint8_t record[488]);
/* Read-only hint for a torn FIRST RECEIVING record only: the other fifteen
 * positions and all padding must still be erased. This is not a valid intent,
 * cannot authorize installation, and does not mount the journal as blank. */
bool comp_wba_system_journal_first_torn(const comp_wba_system_journal_ports_t *);
/* Caller must independently authenticate the actual current pair and admit the
 * signed candidate plus its recording-safe tail claim. Recheck all media and
 * every programmed bit against that exact seq1/RECEIVING record before erasing
 * only sector A; remount the truly blank journal. No payload is written here. */
bool comp_wba_system_journal_restart_first(comp_wba_system_journal_t *,
    const uint8_t expected[488]);
#endif
