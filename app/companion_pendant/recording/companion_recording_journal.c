#include "companion_recording_journal.h"

#include <string.h>

#define COMP_RECORDING_JOURNAL_MAGIC 0x314A5243u /* CRJ1 */
#define COMP_RECORDING_JOURNAL_VERSION 1u
#define COMP_RECORDING_JOURNAL_APPEND_MAGIC 0x324A5243u /* CRJ2 */
#define CATALOG_STRIDE ((uint32_t)((sizeof(comp_recording_journal_catalog_t)+255u)/256u)*256u)
#define CATALOG_SLOTS (COMP_RECORDING_JOURNAL_SECTOR_BYTES/CATALOG_STRIDE)
_Static_assert(CATALOG_SLOTS >= 2u,"catalog append slots do not fit");

static bool catalog_future(const comp_recording_journal_catalog_t *c)
{
    return (c->magic&UINT32_C(0x00FFFFFF))==UINT32_C(0x004A5243)&&
        ((c->magic!=COMP_RECORDING_JOURNAL_MAGIC&&c->magic!=COMP_RECORDING_JOURNAL_APPEND_MAGIC&&
          (c->magic>>24u)!=255u)||(c->version>1u&&c->version<UINT16_C(0x8000)));
}

static uint32_t align_up(uint32_t value, uint32_t alignment)
{
    uint32_t remainder = value % alignment;
    return remainder == 0u ? value : value + alignment - remainder;
}

static uint32_t catalog_offset(const comp_recording_journal_t *journal,
                               uint8_t catalog_index)
{
    return journal->data_bytes +
           (uint32_t)catalog_index * COMP_RECORDING_JOURNAL_SECTOR_BYTES;
}

static bool entry_live(const comp_recording_journal_entry_t *entry)
{
    return entry != NULL && entry->recording_id != 0u &&
           entry->sync_state != COMP_RECORDING_JOURNAL_EMPTY;
}

static uint32_t catalog_crc(comp_recording_journal_t *journal,
                            comp_recording_journal_catalog_t *catalog)
{
    uint32_t saved = catalog->crc32;
    catalog->crc32 = 0u;
    uint32_t crc = journal->port.crc32(
        0u, (const uint8_t *)catalog, (uint32_t)sizeof(*catalog));
    catalog->crc32 = saved;
    return crc;
}

static bool catalog_valid(comp_recording_journal_t *journal,
                          comp_recording_journal_catalog_t *catalog)
{
    if ((catalog->magic != COMP_RECORDING_JOURNAL_MAGIC &&
        !(journal->append_catalogs && catalog->magic == COMP_RECORDING_JOURNAL_APPEND_MAGIC)) ||
        catalog->version != COMP_RECORDING_JOURNAL_VERSION ||
        catalog->entry_capacity != COMP_RECORDING_JOURNAL_MAX_ENTRIES ||
        catalog->next_recording_id == 0u) {
        return false;
    }
    return catalog_crc(journal, catalog) == catalog->crc32;
}

static bool generation_after(uint32_t candidate, uint32_t current)
{
    return (int32_t)(candidate - current) > 0;
}

static comp_recording_journal_result_t commit_catalog(
    comp_recording_journal_t *journal)
{
    uint8_t target = journal->active_catalog == 0u ? 1u : 0u;
    uint32_t offset = catalog_offset(journal, target);
    comp_recording_journal_catalog_t verify;
    uint8_t slot=0u;
    bool needs_erase=true;
    if(journal->append_catalogs) {
        uint8_t bytes[128];
        /* Skip partially programmed slots left by interrupted commits. */
        for(uint32_t candidate=(uint32_t)journal->active_catalog_slot+1u;candidate<CATALOG_SLOTS;++candidate) {
            bool blank=true;
            uint32_t base=catalog_offset(journal,journal->active_catalog)+candidate*CATALOG_STRIDE;
            for(uint32_t n=0u;n<CATALOG_STRIDE;n+=(uint32_t)sizeof(bytes)) {
                if(!journal->port.read(journal->port_context,base+n,bytes,(uint32_t)sizeof(bytes)))
                    return COMP_RECORDING_JOURNAL_IO_ERROR;
                for(size_t i=0u;i<sizeof(bytes);++i)if(bytes[i]!=255u)blank=false;
            }
            if(blank) {target=journal->active_catalog;slot=(uint8_t)candidate;needs_erase=false;break;}
        }
        offset=catalog_offset(journal,target)+(uint32_t)slot*CATALOG_STRIDE;
        journal->catalog.magic=COMP_RECORDING_JOURNAL_APPEND_MAGIC;
    }

    journal->catalog.generation++;
    if (journal->catalog.generation == 0u) {
        journal->catalog.generation = 1u;
    }
    journal->catalog.crc32 = catalog_crc(journal, &journal->catalog);
    if ((needs_erase && !journal->port.erase(journal->port_context,catalog_offset(journal,target),
                             COMP_RECORDING_JOURNAL_SECTOR_BYTES)) ||
        !journal->port.program(journal->port_context, offset,
                               (const uint8_t *)&journal->catalog,
                               (uint32_t)sizeof(journal->catalog)) ||
        !journal->port.read(journal->port_context, offset,
                            (uint8_t *)&verify, (uint32_t)sizeof(verify)) ||
        !catalog_valid(journal, &verify) ||
        verify.generation != journal->catalog.generation) {
        return COMP_RECORDING_JOURNAL_IO_ERROR;
    }
    journal->active_catalog = target;
    journal->active_catalog_slot=slot;
    return COMP_RECORDING_JOURNAL_OK;
}

static comp_recording_journal_entry_t *find_mutable(
    comp_recording_journal_t *journal, uint32_t recording_id)
{
    uint32_t i;
    for (i = 0u; i < COMP_RECORDING_JOURNAL_MAX_ENTRIES; ++i) {
        comp_recording_journal_entry_t *entry = &journal->catalog.entries[i];
        if (entry_live(entry) && entry->recording_id == recording_id) {
            return entry;
        }
    }
    return NULL;
}

typedef struct {
    uint32_t magic;
    uint32_t recording_id;
    uint32_t started_tick_ms;
    uint32_t committed_bytes;
    uint32_t content_crc32;
    uint8_t sha256[32];
    uint32_t started_unix_s;
    uint32_t extent_offset;
    uint32_t crc32;
} checkpoint_record_t;
#define CHECKPOINT_MAGIC 0x31504352u /* RCP1 */
_Static_assert(sizeof(checkpoint_record_t)==COMP_RECORDING_CHECKPOINT_RECORD_BYTES,
               "checkpoint must fit one aligned NOR page fragment");

uint32_t comp_recording_journal_payload_limit(const comp_recording_journal_entry_t *e)
{
    if(!e || e->payload_offset<e->extent_offset ||
       e->payload_offset-e->extent_offset>e->reserved_bytes)return 0u;
    uint32_t bytes=e->reserved_bytes-(e->payload_offset-e->extent_offset);
    if(e->reserved&COMP_RECORDING_CHECKPOINT_LOG_READY) {
        if(bytes<=COMP_RECORDING_JOURNAL_SECTOR_BYTES)return 0u;
        bytes-=COMP_RECORDING_JOURNAL_SECTOR_BYTES;
    }
    return bytes;
}

static uint32_t checkpoint_crc(comp_recording_journal_t *j,checkpoint_record_t *r)
{
    uint32_t saved=r->crc32;r->crc32=0u;
    uint32_t crc=j->port.crc32(0u,(const uint8_t *)r,(uint32_t)sizeof(*r));
    r->crc32=saved;return crc;
}

static bool restore_checkpoint_logs(comp_recording_journal_t *j)
{
    for(uint32_t index=0u;index<COMP_RECORDING_JOURNAL_MAX_ENTRIES;++index) {
        comp_recording_journal_entry_t *e=&j->catalog.entries[index];
        if(e->sync_state!=COMP_RECORDING_JOURNAL_WRITING ||
           !(e->reserved&COMP_RECORDING_CHECKPOINT_LOG_READY))continue;
        uint32_t limit=comp_recording_journal_payload_limit(e);
        if(limit<12u)return false;
        uint32_t base=e->extent_offset+e->reserved_bytes-COMP_RECORDING_JOURNAL_SECTOR_BYTES;
        for(uint32_t slot=0u;slot<COMP_RECORDING_CHECKPOINT_LOG_SLOTS;++slot) {
            checkpoint_record_t r;
            if(!j->port.read(j->port_context,base+slot*(uint32_t)sizeof(r),
                            (uint8_t *)&r,(uint32_t)sizeof(r)))return false;
            bool blank=true;
            for(size_t byte=0u;byte<sizeof(r);++byte)
                if(((uint8_t *)&r)[byte]!=255u)blank=false;
            if(blank)continue;
            j->checkpoint_slots[index]=(uint8_t)(slot+1u);
            if(r.magic!=CHECKPOINT_MAGIC || r.recording_id!=e->recording_id ||
               r.started_tick_ms!=e->started_tick_ms || r.started_unix_s!=e->started_unix_s ||
               r.extent_offset!=e->extent_offset || r.committed_bytes<12u ||
               r.committed_bytes>limit || r.committed_bytes<=e->committed_bytes ||
               checkpoint_crc(j,&r)!=r.crc32)continue;
            e->committed_bytes=r.committed_bytes;e->content_crc32=r.content_crc32;
            memcpy(e->sha256,r.sha256,32u);e->reserved|=COMP_RECORDING_CHECKPOINT_VERIFIED;
        }
    }
    return true;
}

comp_recording_journal_result_t comp_recording_journal_checkpoint_log_init(
    comp_recording_journal_t *j,uint32_t id)
{
    if(!j || !j->mounted || !j->append_catalogs)return COMP_RECORDING_JOURNAL_BAD_ARGUMENT;
    comp_recording_journal_entry_t *e=find_mutable(j,id);
    if(!e)return COMP_RECORDING_JOURNAL_NOT_FOUND;
    if(e->sync_state!=COMP_RECORDING_JOURNAL_WRITING || e->committed_bytes!=0u ||
       e->reserved || e->reserved_bytes<2u*COMP_RECORDING_JOURNAL_SECTOR_BYTES)
        return COMP_RECORDING_JOURNAL_BAD_STATE;
    uint32_t base=e->extent_offset+e->reserved_bytes-COMP_RECORDING_JOURNAL_SECTOR_BYTES;
    uint8_t page[256];
    for(uint32_t offset=0u;offset<COMP_RECORDING_JOURNAL_SECTOR_BYTES;offset+=(uint32_t)sizeof(page)) {
        if(!j->port.read(j->port_context,base+offset,page,(uint32_t)sizeof(page)))
            return COMP_RECORDING_JOURNAL_IO_ERROR;
        for(size_t byte=0u;byte<sizeof(page);++byte)
            if(page[byte]!=255u)return COMP_RECORDING_JOURNAL_BAD_STATE;
    }
    comp_recording_journal_catalog_t before=j->catalog;
    e->reserved|=COMP_RECORDING_CHECKPOINT_LOG_READY;
    if(commit_catalog(j)!=COMP_RECORDING_JOURNAL_OK) {j->catalog=before;return COMP_RECORDING_JOURNAL_IO_ERROR;}
    j->checkpoint_slots[e-j->catalog.entries]=0u;
    return COMP_RECORDING_JOURNAL_OK;
}

static bool range_overlaps(uint32_t a_offset, uint32_t a_bytes,
                           uint32_t b_offset, uint32_t b_bytes)
{
    return a_offset < b_offset + b_bytes && b_offset < a_offset + a_bytes;
}

static bool find_extent_ignoring(const comp_recording_journal_t *journal,
                                 uint32_t bytes,
                                 uint32_t ignored_mask,
                                 uint32_t *out_offset)
{
    uint32_t candidate = 0u;
    while (candidate <= journal->allocation_bytes &&
           bytes <= journal->allocation_bytes - candidate) {
        bool collision = false;
        uint32_t next = candidate + COMP_RECORDING_JOURNAL_SECTOR_BYTES;
        uint32_t i;
        for (i = 0u; i < COMP_RECORDING_JOURNAL_MAX_ENTRIES; ++i) {
            const comp_recording_journal_entry_t *entry =
                &journal->catalog.entries[i];
            if ((ignored_mask & (1u << i)) != 0u || !entry_live(entry)) {
                continue;
            }
            if (range_overlaps(candidate, bytes, entry->extent_offset,
                               entry->reserved_bytes)) {
                collision = true;
                next = align_up(entry->extent_offset + entry->reserved_bytes,
                                COMP_RECORDING_JOURNAL_SECTOR_BYTES);
                break;
            }
        }
        if (!collision) {
            *out_offset = candidate;
            return true;
        }
        candidate = next;
    }
    return false;
}

static bool recording_id_before(uint32_t candidate, uint32_t current)
{
    return current == 0u || (int32_t)(candidate - current) < 0;
}

bool comp_recording_journal_set_allocation_bytes(comp_recording_journal_t *j,uint32_t bytes)
{
    if(!j||!j->mounted||bytes>j->data_bytes||bytes%COMP_RECORDING_JOURNAL_SECTOR_BYTES)return false;
    for(size_t i=0;i<COMP_RECORDING_JOURNAL_MAX_ENTRIES;i++) {
        const comp_recording_journal_entry_t *e=&j->catalog.entries[i];
        if(entry_live(e)&&(e->extent_offset>bytes||e->reserved_bytes>bytes-e->extent_offset))return false;
    }
    j->allocation_bytes=bytes;return true;
}

bool comp_recording_journal_space(const comp_recording_journal_t *journal,
                                 comp_recording_journal_space_t *space)
{
    uint32_t cursor=0u;
    if (!space) return false;
    memset(space,0,sizeof(*space));
    if (!journal || !journal->mounted || journal->region_bytes<8192u ||
        journal->data_bytes!=journal->region_bytes-8192u ||
        journal->data_bytes%COMP_RECORDING_JOURNAL_SECTOR_BYTES ||
        journal->allocation_bytes>journal->data_bytes ||
        journal->allocation_bytes%COMP_RECORDING_JOURNAL_SECTOR_BYTES) return false;
    for (uint32_t i=0u;i<COMP_RECORDING_JOURNAL_MAX_ENTRIES;++i) {
        const comp_recording_journal_entry_t *e=&journal->catalog.entries[i];
        if ((e->recording_id==0u)!=(e->sync_state==COMP_RECORDING_JOURNAL_EMPTY)) goto invalid;
        if (!entry_live(e)) continue;
        if (e->sync_state<COMP_RECORDING_JOURNAL_WRITING ||
            e->sync_state>COMP_RECORDING_JOURNAL_ERASING || !e->reserved_bytes ||
            e->extent_offset%COMP_RECORDING_JOURNAL_SECTOR_BYTES ||
            e->reserved_bytes%COMP_RECORDING_JOURNAL_SECTOR_BYTES ||
            e->extent_offset>journal->allocation_bytes ||
            e->reserved_bytes>journal->allocation_bytes-e->extent_offset ||
            e->payload_offset<e->extent_offset ||
            e->payload_offset>e->extent_offset+e->reserved_bytes ||
            e->total_length>e->extent_offset+e->reserved_bytes-e->payload_offset)
            goto invalid;
        for (uint32_t k=0u;k<i;++k) {
            const comp_recording_journal_entry_t *other=&journal->catalog.entries[k];
            if (entry_live(other) && (other->recording_id==e->recording_id ||
                range_overlaps(e->extent_offset,e->reserved_bytes,
                               other->extent_offset,other->reserved_bytes))) goto invalid;
        }
        ++space->used_entries;
        if (e->sync_state==COMP_RECORDING_JOURNAL_ACKED ||
            e->sync_state==COMP_RECORDING_JOURNAL_ERASING)
        {
            space->consumed_bytes+=e->reserved_bytes;
            ++space->consumed_entries;
        } else {
            space->protected_bytes+=e->reserved_bytes;
            if (e->sync_state==COMP_RECORDING_JOURNAL_WRITING) ++space->writing_entries;
            else ++space->unsynced_entries;
        }
    }
    space->free_bytes=journal->allocation_bytes-space->protected_bytes-space->consumed_bytes;
    while (cursor<journal->allocation_bytes) {
        uint32_t next=journal->allocation_bytes,end=cursor;
        for (uint32_t i=0u;i<COMP_RECORDING_JOURNAL_MAX_ENTRIES;++i) {
            const comp_recording_journal_entry_t *e=&journal->catalog.entries[i];
            if (!entry_live(e)) continue;
            if (e->extent_offset>=cursor && e->extent_offset<next) next=e->extent_offset;
            if (e->extent_offset<=cursor && e->extent_offset+e->reserved_bytes>end)
                end=e->extent_offset+e->reserved_bytes;
        }
        if (end>cursor) {cursor=end;continue;}
        if (next-cursor>space->largest_free_extent) space->largest_free_extent=next-cursor;
        if (next==journal->allocation_bytes) break;
        cursor=next;
    }
    return true;
invalid:
    memset(space,0,sizeof(*space));return false;
}

bool comp_recording_journal_recording_budget(const comp_recording_journal_t *journal,
                                            uint32_t seconds,uint32_t *bytes)
{
    comp_recording_journal_space_t space;
    uint32_t wanted;
    if (!bytes) return false;
    *bytes=0u;
    if (!comp_recording_journal_space(journal,&space) ||
        space.used_entries>=COMP_RECORDING_JOURNAL_MAX_ENTRIES) return false;
    if (seconds) {
        if (seconds>(UINT32_MAX-COMP_RECORDING_RESERVE_HEADROOM-4095u)/
                    COMP_RECORDING_BYTES_PER_SECOND) return false;
        wanted=align_up(seconds*COMP_RECORDING_BYTES_PER_SECOND+
                        COMP_RECORDING_RESERVE_HEADROOM,
                        COMP_RECORDING_JOURNAL_SECTOR_BYTES);
    } else wanted=space.largest_free_extent;
    if (wanted<COMP_RECORDING_RESERVE_HEADROOM || wanted>space.largest_free_extent)
        return false;
    *bytes=wanted;return true;
}

static int32_t find_oldest_ring_victim(
    const comp_recording_journal_t *journal,
    uint32_t ignored_mask)
{
    int32_t victim = -1;
    uint32_t oldest_id = 0u;
    uint32_t i;
    for (i = 0u; i < COMP_RECORDING_JOURNAL_MAX_ENTRIES; ++i) {
        const comp_recording_journal_entry_t *entry =
            &journal->catalog.entries[i];
        if ((ignored_mask & (1u << i)) != 0u || !entry_live(entry) ||
            entry->sync_state != COMP_RECORDING_JOURNAL_ACKED) {
            continue;
        }
        if (victim < 0 || recording_id_before(entry->recording_id, oldest_id)) {
            victim = (int32_t)i;
            oldest_id = entry->recording_id;
        }
    }
    return victim;
}

static bool plan_ring_reservation(
    const comp_recording_journal_t *journal,
    uint32_t bytes,
    uint32_t *out_offset,
    uint32_t *out_slot,
    uint32_t *out_evicted_mask)
{
    uint32_t ignored_mask = 0u;

    for (;;) {
        uint32_t slot;
        bool have_slot = false;
        uint32_t offset = 0u;
        bool have_extent;
        int32_t victim;

        for (slot = 0u; slot < COMP_RECORDING_JOURNAL_MAX_ENTRIES; ++slot) {
            if ((ignored_mask & (1u << slot)) != 0u ||
                !entry_live(&journal->catalog.entries[slot])) {
                have_slot = true;
                break;
            }
        }
        have_extent = find_extent_ignoring(journal, bytes, ignored_mask,
                                           &offset);
        if (have_slot && have_extent) {
            *out_offset = offset;
            *out_slot = slot;
            *out_evicted_mask = ignored_mask;
            return true;
        }

        /* Automatic capacity recovery may discard only data that the host has
         * validated completely.  UNSYNCED audio remains durable until an ACK
         * or an explicit physical delete-all action changes its state. */
        victim = find_oldest_ring_victim(journal, ignored_mask);
        if (victim < 0) {
            return false;
        }
        ignored_mask |= 1u << (uint32_t)victim;
    }
}

static const comp_recording_journal_entry_t *oldest_unsynced(
    const comp_recording_journal_t *j)
{
    const comp_recording_journal_entry_t *oldest=NULL;
    comp_recording_journal_space_t space;
    if (!comp_recording_journal_space(j,&space) || !j->catalog.generation ||
        space.writing_entries || space.consumed_entries) return NULL;
    for (uint32_t i=0u;i<COMP_RECORDING_JOURNAL_MAX_ENTRIES;++i) {
        const comp_recording_journal_entry_t *e=&j->catalog.entries[i];
        if (e->sync_state!=COMP_RECORDING_JOURNAL_UNSYNCED || !e->total_length ||
            e->committed_bytes!=e->total_length) continue;
        if (!oldest || recording_id_before(e->recording_id,oldest->recording_id)) oldest=e;
    }
    return oldest;
}
bool comp_recording_journal_discard_candidate(const comp_recording_journal_t *j,
    uint32_t seconds,comp_recording_journal_entry_t *candidate,uint32_t *largest_after)
{
    uint32_t budget;
    comp_recording_journal_t preview;
    comp_recording_journal_space_t space;
    const comp_recording_journal_entry_t *oldest;
    if (!candidate || !largest_after) return false;
    memset(candidate,0,sizeof(*candidate));*largest_after=0u;
    if (comp_recording_journal_recording_budget(j,seconds,&budget) ||
        !(oldest=oldest_unsynced(j))) return false;
    /* Removing an entry from this RAM snapshot never touches the real catalog. */
    preview=*j;
    memset(&preview.catalog.entries[oldest-j->catalog.entries],0,sizeof(*oldest));
    if (!comp_recording_journal_space(&preview,&space)) return false;
    *candidate=*oldest;*largest_after=space.largest_free_extent;return true;
}
comp_recording_journal_result_t comp_recording_journal_discard_oldest_confirmed(
    comp_recording_journal_t *j,uint32_t generation,uint32_t id,
    uint32_t total_length,const uint8_t sha256[COMP_RECORDING_JOURNAL_SHA256_BYTES])
{
    const comp_recording_journal_entry_t *oldest=oldest_unsynced(j);
    comp_recording_journal_catalog_t before;
    if (!sha256 || !oldest || j->catalog.generation!=generation ||
        oldest->recording_id!=id || oldest->total_length!=total_length ||
        memcmp(oldest->sha256,sha256,COMP_RECORDING_JOURNAL_SHA256_BYTES)!=0)
        return COMP_RECORDING_JOURNAL_ACK_MISMATCH;
    before=j->catalog;
    j->catalog.entries[oldest-j->catalog.entries].sync_state=COMP_RECORDING_JOURNAL_ERASING;
    if (commit_catalog(j)!=COMP_RECORDING_JOURNAL_OK) {
        j->catalog=before;return COMP_RECORDING_JOURNAL_IO_ERROR;
    }
    return COMP_RECORDING_JOURNAL_OK;
}
comp_recording_journal_result_t comp_recording_journal_discard_all_confirmed(comp_recording_journal_t *j)
{
    comp_recording_journal_catalog_t before;
    bool changed=false;
    if(!j || !j->mounted)return COMP_RECORDING_JOURNAL_BAD_STATE;
    for(unsigned i=0;i<COMP_RECORDING_JOURNAL_MAX_ENTRIES;++i)
        if(j->catalog.entries[i].sync_state==COMP_RECORDING_JOURNAL_WRITING)return COMP_RECORDING_JOURNAL_BAD_STATE;
    before=j->catalog;
    for(unsigned i=0;i<COMP_RECORDING_JOURNAL_MAX_ENTRIES;++i) {
        comp_recording_journal_entry_t *e=&j->catalog.entries[i];
        if(entry_live(e) && e->sync_state!=COMP_RECORDING_JOURNAL_ERASING) {e->sync_state=COMP_RECORDING_JOURNAL_ERASING;changed=true;}
    }
    if(!changed)return COMP_RECORDING_JOURNAL_OK;
    comp_recording_journal_result_t result=commit_catalog(j);
    if(result!=COMP_RECORDING_JOURNAL_OK)j->catalog=before;
    return result;
}
static bool catalog_extents_valid(const comp_recording_journal_t *j,
                                  const comp_recording_journal_catalog_t *c)
{
    for (uint32_t i=0;i<COMP_RECORDING_JOURNAL_MAX_ENTRIES;++i) {
        const comp_recording_journal_entry_t *e=&c->entries[i];
        if (e->sync_state==COMP_RECORDING_JOURNAL_EMPTY) continue;
        if (!e->recording_id || e->sync_state>COMP_RECORDING_JOURNAL_ERASING ||
            e->extent_offset%4096u || !e->reserved_bytes || e->reserved_bytes%4096u ||
            e->extent_offset>j->data_bytes || e->reserved_bytes>j->data_bytes-e->extent_offset ||
            e->payload_offset<e->extent_offset || e->payload_offset-e->extent_offset>e->reserved_bytes ||
            e->total_length>e->reserved_bytes-(e->payload_offset-e->extent_offset) ||
            e->committed_bytes>e->reserved_bytes-(e->payload_offset-e->extent_offset) ||
            e->acked_offset>e->committed_bytes) return false;
        for(uint32_t k=0;k<i;++k) {
            const comp_recording_journal_entry_t *p=&c->entries[k];
            if(p->sync_state!=COMP_RECORDING_JOURNAL_EMPTY &&
               (p->recording_id==e->recording_id || range_overlaps(e->extent_offset,e->reserved_bytes,
                                                                  p->extent_offset,p->reserved_bytes))) return false;
        }
    }
    return true;
}
static comp_recording_journal_result_t mount_internal(
    comp_recording_journal_t *journal,
    const comp_recording_journal_port_t *port,
    void *port_context,
    uint32_t region_bytes, bool strict, bool readonly)
{
    comp_recording_journal_catalog_t b;
    bool valid_a;
    bool valid_b;

    if (journal == NULL || port == NULL || port->read == NULL ||
        port->program == NULL || port->erase == NULL || port->crc32 == NULL ||
        region_bytes < 3u * COMP_RECORDING_JOURNAL_SECTOR_BYTES ||
        (region_bytes % COMP_RECORDING_JOURNAL_SECTOR_BYTES) != 0u) {
        return COMP_RECORDING_JOURNAL_BAD_ARGUMENT;
    }

    memset(journal, 0, sizeof(*journal));
    journal->port = *port;
    journal->port_context = port_context;
    journal->append_catalogs=strict;
    journal->region_bytes = region_bytes;
    journal->data_bytes = region_bytes -
        COMP_RECORDING_JOURNAL_CATALOG_SECTORS *
            COMP_RECORDING_JOURNAL_SECTOR_BYTES;
    journal->allocation_bytes=journal->data_bytes;

    /* Read A directly into the destination journal and keep only B on the
     * stack.  The prior two-local implementation consumed nearly the complete
     * WB55 BLE service-task stack when delete-all immediately remounted to
     * publish its empty directory. */
    bool read_a = port->read(port_context, catalog_offset(journal, 0u),
                         (uint8_t *)&journal->catalog,
                         (uint32_t)sizeof(journal->catalog));
    bool read_b = port->read(port_context, catalog_offset(journal, 1u),
                         (uint8_t *)&b, (uint32_t)sizeof(b));
    if(readonly&&(!read_a||!read_b))return COMP_RECORDING_JOURNAL_IO_ERROR;
    if(readonly&&(catalog_future(&journal->catalog)||catalog_future(&b)))return COMP_RECORDING_JOURNAL_BAD_STATE;
    valid_a = read_a && catalog_valid(journal, &journal->catalog);
    valid_b = read_b && catalog_valid(journal, &b);
    if(strict) {
        valid_a=valid_a && catalog_extents_valid(journal,&journal->catalog);
        valid_b=valid_b && catalog_extents_valid(journal,&b);
    }
    if(readonly&&valid_a&&valid_b&&journal->catalog.generation==b.generation&&
       memcmp(&journal->catalog,&b,sizeof(b)))return COMP_RECORDING_JOURNAL_BAD_STATE;
    if(strict) {
        bool found=valid_a;
        journal->active_catalog=0u;
        journal->active_catalog_slot=0u;
        if(valid_b && (!found || generation_after(b.generation,journal->catalog.generation))) {
            journal->catalog=b;journal->active_catalog=1u;found=true;
        }
        for(uint32_t sector=0u;sector<2u;++sector)for(uint32_t slot=1u;slot<CATALOG_SLOTS;++slot) {
            if(!port->read(port_context,catalog_offset(journal,(uint8_t)sector)+slot*CATALOG_STRIDE,(uint8_t *)&b,(uint32_t)sizeof(b)))
                return COMP_RECORDING_JOURNAL_IO_ERROR;
            if(readonly&&catalog_future(&b))return COMP_RECORDING_JOURNAL_BAD_STATE;
            if(catalog_valid(journal,&b) && catalog_extents_valid(journal,&b) &&
                (!found || generation_after(b.generation,journal->catalog.generation))) {
                journal->catalog=b;journal->active_catalog=(uint8_t)sector;journal->active_catalog_slot=(uint8_t)slot;found=true;
            } else if(readonly&&found&&catalog_valid(journal,&b)&&catalog_extents_valid(journal,&b)&&
                    b.generation==journal->catalog.generation&&memcmp(&journal->catalog,&b,sizeof(b))) {
                return COMP_RECORDING_JOURNAL_BAD_STATE;
            }
        }
        if(found) {
            journal->mounted=true;
            if(!restore_checkpoint_logs(journal)) {journal->mounted=false;return COMP_RECORDING_JOURNAL_IO_ERROR;}
            return COMP_RECORDING_JOURNAL_OK;
        }
    }
    if (!strict && (valid_a || valid_b)) {
        if (valid_b &&
            (!valid_a || generation_after(b.generation,
                                          journal->catalog.generation))) {
            journal->catalog = b;
            journal->active_catalog = 1u;
        } else {
            journal->active_catalog = 0u;
        }
        journal->mounted = true;
        return COMP_RECORDING_JOURNAL_OK;
    }

    if(strict) {
        uint8_t bytes[128];
        /* With both catalogs lost, payload can still contain the only copy of
         * a meeting. Format only genuinely blank media, not just blank roots. */
        for(uint32_t offset=0;offset<region_bytes;offset+=sizeof(bytes)) {
            if(!port->read(port_context,offset,bytes,sizeof(bytes))) return COMP_RECORDING_JOURNAL_IO_ERROR;
            for(size_t i=0;i<sizeof(bytes);++i) if(bytes[i]!=255u) return COMP_RECORDING_JOURNAL_BAD_STATE;
        }
    }
    memset(&journal->catalog, 0, sizeof(journal->catalog));
    journal->catalog.magic = COMP_RECORDING_JOURNAL_MAGIC;
    journal->catalog.version = COMP_RECORDING_JOURNAL_VERSION;
    journal->catalog.entry_capacity = COMP_RECORDING_JOURNAL_MAX_ENTRIES;
    journal->catalog.next_recording_id = 1u;
    journal->active_catalog = 1u; /* first commit targets A */
    journal->active_catalog_slot=(uint8_t)(CATALOG_SLOTS-1u);
    if (!readonly && commit_catalog(journal) != COMP_RECORDING_JOURNAL_OK) {
        return COMP_RECORDING_JOURNAL_IO_ERROR;
    }
    journal->mounted = true;
    return COMP_RECORDING_JOURNAL_OK;
}

comp_recording_journal_result_t comp_recording_journal_mount(
    comp_recording_journal_t *j,const comp_recording_journal_port_t *p,void *c,uint32_t n)
{ return mount_internal(j,p,c,n,false,false); }
comp_recording_journal_result_t comp_recording_journal_mount_strict(
    comp_recording_journal_t *j,const comp_recording_journal_port_t *p,void *c,uint32_t n)
{ return mount_internal(j,p,c,n,true,false); }
comp_recording_journal_result_t comp_recording_journal_mount_readonly_strict(
    comp_recording_journal_t *j,const comp_recording_journal_port_t *p,void *c,uint32_t n)
{ return mount_internal(j,p,c,n,true,true); }

comp_recording_journal_result_t comp_recording_journal_import_legacy(
    comp_recording_journal_t *journal,
    const comp_recording_journal_entry_t *legacy)
{
    comp_recording_journal_catalog_t before;
    uint32_t i;
    if (journal == NULL || !journal->mounted || legacy == NULL ||
        legacy->recording_id == 0u || legacy->total_length == 0u ||
        legacy->reserved_bytes == 0u ||
        legacy->extent_offset > journal->data_bytes ||
        legacy->payload_offset < legacy->extent_offset ||
        legacy->payload_offset > journal->data_bytes ||
        legacy->reserved_bytes > journal->data_bytes - legacy->extent_offset ||
        legacy->total_length > journal->data_bytes - legacy->payload_offset) {
        return COMP_RECORDING_JOURNAL_BAD_ARGUMENT;
    }
    if (comp_recording_journal_find(journal, legacy->recording_id) != NULL) {
        return COMP_RECORDING_JOURNAL_OK;
    }
    before = journal->catalog;
    for (i = 0u; i < COMP_RECORDING_JOURNAL_MAX_ENTRIES; ++i) {
        if (!entry_live(&journal->catalog.entries[i])) {
            journal->catalog.entries[i] = *legacy;
            if (journal->catalog.next_recording_id <= legacy->recording_id) {
                journal->catalog.next_recording_id = legacy->recording_id + 1u;
                if (journal->catalog.next_recording_id == 0u) {
                    journal->catalog.next_recording_id = 1u;
                }
            }
            if (commit_catalog(journal) == COMP_RECORDING_JOURNAL_OK) {
                return COMP_RECORDING_JOURNAL_OK;
            }
            journal->catalog = before;
            return COMP_RECORDING_JOURNAL_IO_ERROR;
        }
    }
    return COMP_RECORDING_JOURNAL_DIRECTORY_FULL;
}

bool comp_recording_journal_can_reserve(
    const comp_recording_journal_t *journal,
    uint32_t reserve_payload_bytes)
{
    uint32_t bytes;
    uint32_t offset;
    uint32_t slot;
    uint32_t evicted_mask;

    if (journal == NULL || !journal->mounted || reserve_payload_bytes == 0u) {
        return false;
    }
    bytes = align_up(reserve_payload_bytes,
                     COMP_RECORDING_JOURNAL_SECTOR_BYTES);
    if (bytes == 0u || bytes > journal->data_bytes) {
        return false;
    }
    return plan_ring_reservation(journal, bytes, &offset, &slot,
                                 &evicted_mask);
}

comp_recording_journal_result_t
comp_recording_journal_recover_abandoned_writes(
    comp_recording_journal_t *journal,
    uint32_t *out_recovered_count)
{
    comp_recording_journal_catalog_t before;
    uint32_t recovered = 0u;
    uint32_t i;

    if (out_recovered_count != NULL) {
        *out_recovered_count = 0u;
    }
    if (journal == NULL || !journal->mounted) {
        return COMP_RECORDING_JOURNAL_BAD_ARGUMENT;
    }
    before = journal->catalog;
    for (i = 0u; i < COMP_RECORDING_JOURNAL_MAX_ENTRIES; ++i) {
        comp_recording_journal_entry_t *entry = &journal->catalog.entries[i];
        if (entry_live(entry) &&
            entry->sync_state == COMP_RECORDING_JOURNAL_WRITING) {
            memset(entry, 0, sizeof(*entry));
            recovered++;
        }
    }
    if (recovered == 0u) {
        return COMP_RECORDING_JOURNAL_OK;
    }
    if (commit_catalog(journal) != COMP_RECORDING_JOURNAL_OK) {
        journal->catalog = before;
        return COMP_RECORDING_JOURNAL_IO_ERROR;
    }
    if (out_recovered_count != NULL) {
        *out_recovered_count = recovered;
    }
    return COMP_RECORDING_JOURNAL_OK;
}

comp_recording_journal_result_t comp_recording_journal_begin(
    comp_recording_journal_t *journal,
    uint32_t reserve_payload_bytes,
    uint32_t started_unix_s,
    uint32_t started_tick_ms,
    uint8_t codec,
    uint8_t source_mode,
    comp_recording_journal_entry_t *out_entry)
{
    comp_recording_journal_catalog_t before;
    uint32_t bytes;
    uint32_t offset;
    uint32_t slot;
    uint32_t evicted_mask;
    uint32_t evicted_count = 0u;
    uint32_t recording_id;
    uint32_t i;
    if (journal == NULL || !journal->mounted || reserve_payload_bytes == 0u) {
        return COMP_RECORDING_JOURNAL_BAD_ARGUMENT;
    }
    journal->last_ring_evicted_count = 0u;
    bytes = align_up(reserve_payload_bytes, COMP_RECORDING_JOURNAL_SECTOR_BYTES);
    if (bytes == 0u || bytes > journal->data_bytes) {
        return COMP_RECORDING_JOURNAL_STORAGE_FULL;
    }
    if (!plan_ring_reservation(journal, bytes, &offset, &slot,
                               &evicted_mask)) {
        return COMP_RECORDING_JOURNAL_STORAGE_FULL;
    }

    /* Durable host resume keys include recording_id.  Never reuse an id that
     * is still visible in the ring, even if a recovered/stale catalog high
     * water mark points at that entry and the same reservation will evict it.
     * Otherwise a new capture can inherit an old .part file and correctly
     * fail final SHA verification after a disconnect/resume cycle. */
    recording_id = journal->catalog.next_recording_id;
    if (recording_id == 0u) {
        recording_id = 1u;
    }
    for (i = 0u; i < COMP_RECORDING_JOURNAL_MAX_ENTRIES; ++i) {
        const comp_recording_journal_entry_t *existing =
            &journal->catalog.entries[i];
        if (entry_live(existing) &&
            (int32_t)(existing->recording_id - recording_id) >= 0) {
            recording_id = existing->recording_id + 1u;
            if (recording_id == 0u) {
                recording_id = 1u;
            }
        }
    }
    before = journal->catalog;
    for (i = 0u; i < COMP_RECORDING_JOURNAL_MAX_ENTRIES; ++i) {
        if ((evicted_mask & (1u << i)) != 0u) {
            memset(&journal->catalog.entries[i], 0,
                   sizeof(journal->catalog.entries[i]));
            evicted_count++;
        }
    }
    comp_recording_journal_entry_t *entry = &journal->catalog.entries[slot];
    memset(entry, 0, sizeof(*entry));
    entry->recording_id = recording_id;
    journal->catalog.next_recording_id = recording_id + 1u;
    if (journal->catalog.next_recording_id == 0u) {
        journal->catalog.next_recording_id = 1u;
    }
    entry->extent_offset = offset;
    entry->payload_offset = offset;
    entry->reserved_bytes = bytes;
    entry->started_unix_s = started_unix_s;
    entry->started_tick_ms = started_tick_ms;
    entry->codec = codec;
    entry->source_mode = source_mode;
    entry->sync_state = COMP_RECORDING_JOURNAL_WRITING;
    if (commit_catalog(journal) != COMP_RECORDING_JOURNAL_OK) {
        journal->catalog = before;
        return COMP_RECORDING_JOURNAL_IO_ERROR;
    }
    if (out_entry != NULL) {
        *out_entry = *entry;
    }
    journal->last_ring_evicted_count = evicted_count;
    return COMP_RECORDING_JOURNAL_OK;
}

comp_recording_journal_result_t comp_recording_journal_abort(
    comp_recording_journal_t *journal, uint32_t recording_id)
{
    comp_recording_journal_catalog_t before;
    comp_recording_journal_entry_t *entry;
    if (journal == NULL || !journal->mounted) {
        return COMP_RECORDING_JOURNAL_BAD_ARGUMENT;
    }
    entry = find_mutable(journal, recording_id);
    if (entry == NULL) {
        return COMP_RECORDING_JOURNAL_NOT_FOUND;
    }
    if (entry->sync_state != COMP_RECORDING_JOURNAL_WRITING) {
        return COMP_RECORDING_JOURNAL_BAD_STATE;
    }
    before = journal->catalog;
    memset(entry, 0, sizeof(*entry));
    if (commit_catalog(journal) != COMP_RECORDING_JOURNAL_OK) {
        journal->catalog = before;
        return COMP_RECORDING_JOURNAL_IO_ERROR;
    }
    return COMP_RECORDING_JOURNAL_OK;
}

comp_recording_journal_result_t comp_recording_journal_checkpoint(
    comp_recording_journal_t *journal,
    uint32_t recording_id,
    uint32_t committed_bytes,
    uint32_t acked_offset)
{
    comp_recording_journal_catalog_t before;
    comp_recording_journal_entry_t *entry;
    if (journal == NULL || !journal->mounted) {
        return COMP_RECORDING_JOURNAL_BAD_ARGUMENT;
    }
    entry = find_mutable(journal, recording_id);
    if (entry == NULL) {
        return COMP_RECORDING_JOURNAL_NOT_FOUND;
    }
    if (entry->sync_state != COMP_RECORDING_JOURNAL_WRITING ||
        committed_bytes < entry->committed_bytes ||
        committed_bytes > entry->reserved_bytes ||
        acked_offset < entry->acked_offset || acked_offset > committed_bytes) {
        return COMP_RECORDING_JOURNAL_BAD_STATE;
    }
    before = journal->catalog;
    entry->committed_bytes = committed_bytes;
    entry->acked_offset = acked_offset;
    if (commit_catalog(journal) != COMP_RECORDING_JOURNAL_OK) {
        journal->catalog = before;
        return COMP_RECORDING_JOURNAL_IO_ERROR;
    }
    return COMP_RECORDING_JOURNAL_OK;
}

comp_recording_journal_result_t comp_recording_journal_checkpoint_verified(
    comp_recording_journal_t *j,uint32_t id,uint32_t bytes,uint32_t crc,const uint8_t sha[32])
{
    if(!j || !j->mounted || !sha || !j->append_catalogs)return COMP_RECORDING_JOURNAL_BAD_ARGUMENT;
    comp_recording_journal_entry_t *e=find_mutable(j,id);
    if(!e)return COMP_RECORDING_JOURNAL_NOT_FOUND;
    if(e->sync_state!=COMP_RECORDING_JOURNAL_WRITING || bytes<e->committed_bytes || bytes>comp_recording_journal_payload_limit(e))
        return COMP_RECORDING_JOURNAL_BAD_STATE;
    if(e->reserved&COMP_RECORDING_CHECKPOINT_LOG_READY) {
        uint32_t index=(uint32_t)(e-j->catalog.entries),slot=j->checkpoint_slots[index];
        if(slot>=COMP_RECORDING_CHECKPOINT_LOG_SLOTS)return COMP_RECORDING_JOURNAL_STORAGE_FULL;
        checkpoint_record_t r={0},verify;
        uint32_t offset=e->extent_offset+e->reserved_bytes-COMP_RECORDING_JOURNAL_SECTOR_BYTES+
                        slot*(uint32_t)sizeof(r);
        if(!j->port.read(j->port_context,offset,(uint8_t *)&verify,(uint32_t)sizeof(verify)))
            return COMP_RECORDING_JOURNAL_IO_ERROR;
        for(size_t n=0u;n<sizeof(verify);++n)
            if(((uint8_t *)&verify)[n]!=255u)return COMP_RECORDING_JOURNAL_BAD_STATE;
        r.magic=CHECKPOINT_MAGIC;r.recording_id=id;r.started_tick_ms=e->started_tick_ms;
        r.started_unix_s=e->started_unix_s;r.extent_offset=e->extent_offset;
        r.committed_bytes=bytes;r.content_crc32=crc;memcpy(r.sha256,sha,32u);
        r.crc32=checkpoint_crc(j,&r);
        /* Advance even after a torn program; no slot is ever programmed twice. */
        j->checkpoint_slots[index]=(uint8_t)(slot+1u);
        if(!j->port.program(j->port_context,offset,(const uint8_t *)&r,(uint32_t)sizeof(r)) ||
           !j->port.read(j->port_context,offset,(uint8_t *)&verify,(uint32_t)sizeof(verify)) ||
           memcmp(&verify,&r,sizeof(r))!=0)return COMP_RECORDING_JOURNAL_IO_ERROR;
        e->committed_bytes=bytes;e->content_crc32=crc;memcpy(e->sha256,sha,32u);
        e->reserved|=COMP_RECORDING_CHECKPOINT_VERIFIED;return COMP_RECORDING_JOURNAL_OK;
    }
    comp_recording_journal_catalog_t before=j->catalog;
    e->committed_bytes=bytes;e->content_crc32=crc;memcpy(e->sha256,sha,32u);
    e->reserved|=COMP_RECORDING_CHECKPOINT_VERIFIED;
    if(commit_catalog(j)!=COMP_RECORDING_JOURNAL_OK) {j->catalog=before;return COMP_RECORDING_JOURNAL_IO_ERROR;}
    return COMP_RECORDING_JOURNAL_OK;
}

comp_recording_journal_result_t comp_recording_journal_finalize(
    comp_recording_journal_t *journal,
    uint32_t recording_id,
    uint32_t total_length,
    uint32_t duration_ms,
    uint32_t content_crc32,
    const uint8_t sha256[COMP_RECORDING_JOURNAL_SHA256_BYTES],
    uint8_t codec)
{
    comp_recording_journal_catalog_t before;
    comp_recording_journal_entry_t *entry;
    if (journal == NULL || !journal->mounted || sha256 == NULL ||
        total_length == 0u) {
        return COMP_RECORDING_JOURNAL_BAD_ARGUMENT;
    }
    entry = find_mutable(journal, recording_id);
    if (entry == NULL) {
        return COMP_RECORDING_JOURNAL_NOT_FOUND;
    }
    if (entry->sync_state != COMP_RECORDING_JOURNAL_WRITING ||
        total_length > entry->reserved_bytes) {
        return COMP_RECORDING_JOURNAL_BAD_STATE;
    }
    before = journal->catalog;
    entry->committed_bytes = total_length;
    entry->total_length = total_length;
    entry->duration_ms = duration_ms;
    entry->content_crc32 = content_crc32;
    entry->codec = codec;
    memcpy(entry->sha256, sha256, COMP_RECORDING_JOURNAL_SHA256_BYTES);
    entry->reserved=(uint8_t)(entry->reserved&COMP_RECORDING_RECOVERED_PREFIX);
    entry->sync_state = COMP_RECORDING_JOURNAL_UNSYNCED;
    if (commit_catalog(journal) != COMP_RECORDING_JOURNAL_OK) {
        journal->catalog = before;
        return COMP_RECORDING_JOURNAL_IO_ERROR;
    }
    return COMP_RECORDING_JOURNAL_OK;
}

comp_recording_journal_result_t comp_recording_journal_finalize_recovered(
    comp_recording_journal_t *j,uint32_t id,uint32_t bytes,uint32_t duration,uint32_t crc,const uint8_t sha[32])
{
    if(!j || !j->append_catalogs)return COMP_RECORDING_JOURNAL_BAD_ARGUMENT;
    comp_recording_journal_entry_t *e=find_mutable(j,id);
    if(!e)return COMP_RECORDING_JOURNAL_NOT_FOUND;
    if(!(e->reserved&COMP_RECORDING_CHECKPOINT_VERIFIED) || bytes>e->committed_bytes)
        return COMP_RECORDING_JOURNAL_BAD_STATE;
    comp_recording_journal_catalog_t before=j->catalog;
    e->reserved|=COMP_RECORDING_RECOVERED_PREFIX;
    comp_recording_journal_result_t result=comp_recording_journal_finalize(j,id,bytes,duration,crc,sha,e->codec);
    if(result!=COMP_RECORDING_JOURNAL_OK)j->catalog=before;
    return result;
}

comp_recording_journal_result_t comp_recording_journal_trim_completed_extent(
    comp_recording_journal_t *journal, uint32_t recording_id)
{
    comp_recording_journal_catalog_t before;
    comp_recording_journal_entry_t *entry;
    uint32_t payload_prefix;
    uint32_t used_bytes;
    uint32_t trimmed_bytes;

    if (journal == NULL || !journal->mounted) {
        return COMP_RECORDING_JOURNAL_BAD_ARGUMENT;
    }
    entry = find_mutable(journal, recording_id);
    if (entry == NULL) return COMP_RECORDING_JOURNAL_NOT_FOUND;
    if ((entry->sync_state != COMP_RECORDING_JOURNAL_UNSYNCED &&
         entry->sync_state != COMP_RECORDING_JOURNAL_ACKED) ||
        entry->payload_offset < entry->extent_offset ||
        entry->total_length == 0u) {
        return COMP_RECORDING_JOURNAL_BAD_STATE;
    }
    payload_prefix = entry->payload_offset - entry->extent_offset;
    if (entry->total_length > UINT32_MAX - payload_prefix) {
        return COMP_RECORDING_JOURNAL_BAD_STATE;
    }
    used_bytes = payload_prefix + entry->total_length;
    trimmed_bytes = align_up(used_bytes, COMP_RECORDING_JOURNAL_SECTOR_BYTES);
    if (trimmed_bytes == 0u || trimmed_bytes > entry->reserved_bytes) {
        return COMP_RECORDING_JOURNAL_BAD_STATE;
    }
    if (trimmed_bytes == entry->reserved_bytes) {
        return COMP_RECORDING_JOURNAL_OK;
    }
    before = journal->catalog;
    entry->reserved_bytes = trimmed_bytes;
    if (commit_catalog(journal) != COMP_RECORDING_JOURNAL_OK) {
        journal->catalog = before;
        return COMP_RECORDING_JOURNAL_IO_ERROR;
    }
    return COMP_RECORDING_JOURNAL_OK;
}

comp_recording_journal_result_t comp_recording_journal_ack_complete(
    comp_recording_journal_t *journal,
    uint32_t recording_id,
    uint32_t validated_total_length,
    const uint8_t validated_sha256[COMP_RECORDING_JOURNAL_SHA256_BYTES])
{
    comp_recording_journal_catalog_t before;
    comp_recording_journal_entry_t *entry;
    if (journal == NULL || !journal->mounted || validated_sha256 == NULL) {
        return COMP_RECORDING_JOURNAL_BAD_ARGUMENT;
    }
    entry = find_mutable(journal, recording_id);
    if (entry == NULL) {
        return COMP_RECORDING_JOURNAL_NOT_FOUND;
    }
    if (entry->sync_state != COMP_RECORDING_JOURNAL_UNSYNCED) {
        return COMP_RECORDING_JOURNAL_BAD_STATE;
    }
    if (entry->total_length != validated_total_length ||
        memcmp(entry->sha256, validated_sha256,
               COMP_RECORDING_JOURNAL_SHA256_BYTES) != 0) {
        return COMP_RECORDING_JOURNAL_ACK_MISMATCH;
    }
    before = journal->catalog;
    entry->acked_offset = entry->total_length;
    entry->sync_state = COMP_RECORDING_JOURNAL_ACKED;
    if (commit_catalog(journal) != COMP_RECORDING_JOURNAL_OK) {
        journal->catalog = before;
        return COMP_RECORDING_JOURNAL_IO_ERROR;
    }
    return COMP_RECORDING_JOURNAL_OK;
}

comp_recording_journal_result_t comp_recording_journal_reclaim_acked(
    comp_recording_journal_t *journal,
    uint32_t recording_id)
{
    comp_recording_journal_catalog_t before;
    comp_recording_journal_entry_t *entry;
    uint32_t offset;
    uint32_t bytes;
    if (journal == NULL || !journal->mounted) {
        return COMP_RECORDING_JOURNAL_BAD_ARGUMENT;
    }
    entry = find_mutable(journal, recording_id);
    if (entry == NULL) {
        return COMP_RECORDING_JOURNAL_NOT_FOUND;
    }
    if (entry->sync_state != COMP_RECORDING_JOURNAL_ACKED) {
        return COMP_RECORDING_JOURNAL_BAD_STATE;
    }
    offset = entry->extent_offset;
    bytes = entry->reserved_bytes;
    if (!journal->port.erase(journal->port_context, offset, bytes)) {
        return COMP_RECORDING_JOURNAL_IO_ERROR;
    }
    before = journal->catalog;
    memset(entry, 0, sizeof(*entry));
    if (commit_catalog(journal) != COMP_RECORDING_JOURNAL_OK) {
        journal->catalog = before;
        return COMP_RECORDING_JOURNAL_IO_ERROR;
    }
    return COMP_RECORDING_JOURNAL_OK;
}

comp_recording_journal_result_t comp_recording_journal_begin_reclaim(
    comp_recording_journal_t *journal, uint32_t recording_id)
{
    comp_recording_journal_catalog_t before;
    comp_recording_journal_entry_t *entry;
    if (!journal || !journal->mounted) return COMP_RECORDING_JOURNAL_BAD_ARGUMENT;
    entry=find_mutable(journal,recording_id);
    if (!entry) return COMP_RECORDING_JOURNAL_NOT_FOUND;
    if (entry->sync_state==COMP_RECORDING_JOURNAL_ERASING) return COMP_RECORDING_JOURNAL_OK;
    if (entry->sync_state!=COMP_RECORDING_JOURNAL_ACKED) return COMP_RECORDING_JOURNAL_BAD_STATE;
    before=journal->catalog;
    entry->sync_state=COMP_RECORDING_JOURNAL_ERASING;
    if (commit_catalog(journal)!=COMP_RECORDING_JOURNAL_OK) {
        journal->catalog=before;return COMP_RECORDING_JOURNAL_IO_ERROR;
    }
    return COMP_RECORDING_JOURNAL_OK;
}
comp_recording_journal_result_t comp_recording_journal_reclaim_step(
    comp_recording_journal_t *journal,uint32_t recording_id,uint32_t *cursor,bool *complete)
{
    comp_recording_journal_catalog_t before;
    comp_recording_journal_entry_t *entry;
    if (!journal || !journal->mounted || !cursor || !complete) return COMP_RECORDING_JOURNAL_BAD_ARGUMENT;
    *complete=false;
    entry=find_mutable(journal,recording_id);
    if (!entry) return COMP_RECORDING_JOURNAL_NOT_FOUND;
    if (entry->sync_state!=COMP_RECORDING_JOURNAL_ERASING) return COMP_RECORDING_JOURNAL_BAD_STATE;
    if (entry->extent_offset%COMP_RECORDING_JOURNAL_SECTOR_BYTES ||
        entry->reserved_bytes%COMP_RECORDING_JOURNAL_SECTOR_BYTES ||
        entry->extent_offset>journal->data_bytes ||
        entry->reserved_bytes>journal->data_bytes-entry->extent_offset ||
        *cursor>entry->reserved_bytes || *cursor%COMP_RECORDING_JOURNAL_SECTOR_BYTES)
        return COMP_RECORDING_JOURNAL_BAD_ARGUMENT;
    if (*cursor<entry->reserved_bytes) {
        uint32_t erased=COMP_RECORDING_JOURNAL_SECTOR_BYTES;
        uint32_t remaining=entry->reserved_bytes-*cursor;
        if(journal->reclaim_erase_step) {
            erased=0u;
            if(!journal->reclaim_erase_step(journal->port_context,
                    entry->extent_offset+*cursor,remaining,&erased) ||
               erased>remaining || erased%COMP_RECORDING_JOURNAL_SECTOR_BYTES)
                return COMP_RECORDING_JOURNAL_IO_ERROR;
        } else if (!journal->port.erase(journal->port_context,entry->extent_offset+*cursor,
                                       erased))return COMP_RECORDING_JOURNAL_IO_ERROR;
        *cursor+=erased;
        return COMP_RECORDING_JOURNAL_OK;
    }
    before=journal->catalog; memset(entry,0,sizeof(*entry));
    if (commit_catalog(journal)!=COMP_RECORDING_JOURNAL_OK) {
        journal->catalog=before;return COMP_RECORDING_JOURNAL_IO_ERROR;
    }
    *complete=true;return COMP_RECORDING_JOURNAL_OK;
}

uint32_t comp_recording_journal_count(const comp_recording_journal_t *journal)
{
    uint32_t count = 0u;
    uint32_t i;
    if (journal == NULL || !journal->mounted) {
        return 0u;
    }
    for (i = 0u; i < COMP_RECORDING_JOURNAL_MAX_ENTRIES; ++i) {
        if (entry_live(&journal->catalog.entries[i])) {
            ++count;
        }
    }
    return count;
}

const comp_recording_journal_entry_t *comp_recording_journal_at(
    const comp_recording_journal_t *journal, uint32_t index)
{
    uint32_t seen = 0u;
    uint32_t i;
    if (journal == NULL || !journal->mounted) {
        return NULL;
    }
    for (i = 0u; i < COMP_RECORDING_JOURNAL_MAX_ENTRIES; ++i) {
        const comp_recording_journal_entry_t *entry = &journal->catalog.entries[i];
        if (!entry_live(entry)) {
            continue;
        }
        if (seen++ == index) {
            return entry;
        }
    }
    return NULL;
}

const comp_recording_journal_entry_t *comp_recording_journal_find(
    const comp_recording_journal_t *journal, uint32_t recording_id)
{
    uint32_t i;
    if (journal == NULL || !journal->mounted || recording_id == 0u) {
        return NULL;
    }
    for (i = 0u; i < COMP_RECORDING_JOURNAL_MAX_ENTRIES; ++i) {
        const comp_recording_journal_entry_t *entry = &journal->catalog.entries[i];
        if (entry_live(entry) && entry->recording_id == recording_id) {
            return entry;
        }
    }
    return NULL;
}
