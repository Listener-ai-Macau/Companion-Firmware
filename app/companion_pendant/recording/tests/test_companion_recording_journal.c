#include "companion_recording_journal.h"

#include <stdio.h>
#include <string.h>

#define TEST_FLASH_BYTES (64u * 1024u)

typedef struct {
    uint8_t bytes[TEST_FLASH_BYTES];
    uint32_t fail_program_after;
} fake_flash_t;

typedef struct {
    uint32_t read_calls, program_calls, erase_calls;
    uint32_t fail_read_call, partial_program_call, partial_program_bytes;
    uint32_t partial_erase_call, partial_erase_bytes;
    bool fail_all_reads;
} fault_plan_t;

static fault_plan_t faults;

static void reset_faults(void)
{
    memset(&faults, 0, sizeof(faults));
}

static int fail_line(int line, const char *message)
{
    fprintf(stderr, "FAIL line=%d %s\n", line, message);
    return line;
}

#define CHECK(expr, message) do { if (!(expr)) return fail_line(__LINE__, message); } while (0)

static bool fake_read(void *context, uint32_t offset,
                      uint8_t *destination, uint32_t length)
{
    fake_flash_t *flash = (fake_flash_t *)context;
    faults.read_calls++;
    if (destination == NULL || offset > TEST_FLASH_BYTES ||
        length > TEST_FLASH_BYTES - offset) {
        return false;
    }
    if (faults.fail_all_reads ||
        (faults.fail_read_call != 0u &&
         faults.read_calls == faults.fail_read_call)) return false;
    memcpy(destination, &flash->bytes[offset], length);
    return true;
}

static bool fake_program(void *context, uint32_t offset,
                         const uint8_t *source, uint32_t length)
{
    fake_flash_t *flash = (fake_flash_t *)context;
    uint32_t write_length = length;
    uint32_t i;
    faults.program_calls++;
    if (source == NULL || offset > TEST_FLASH_BYTES ||
        length > TEST_FLASH_BYTES - offset) {
        return false;
    }
    if (flash->fail_program_after != 0u &&
        flash->fail_program_after < write_length) {
        write_length = flash->fail_program_after;
    }
    if (faults.partial_program_call != 0u &&
        faults.program_calls == faults.partial_program_call &&
        faults.partial_program_bytes < write_length) {
        write_length = faults.partial_program_bytes;
    }
    for (i = 0u; i < write_length; ++i) {
        if ((flash->bytes[offset + i] & source[i]) != source[i]) {
            return false;
        }
        flash->bytes[offset + i] &= source[i];
    }
    if (write_length != length) {
        flash->fail_program_after = 0u;
        faults.partial_program_call = 0u;
        return false;
    }
    return true;
}

static bool fake_erase(void *context, uint32_t offset, uint32_t length)
{
    fake_flash_t *flash = (fake_flash_t *)context;
    uint32_t erase_length = length;
    faults.erase_calls++;
    if (offset > TEST_FLASH_BYTES || length > TEST_FLASH_BYTES - offset ||
        (offset % COMP_RECORDING_JOURNAL_SECTOR_BYTES) != 0u ||
        (length % COMP_RECORDING_JOURNAL_SECTOR_BYTES) != 0u) {
        return false;
    }
    if (faults.partial_erase_call != 0u &&
        faults.erase_calls == faults.partial_erase_call &&
        faults.partial_erase_bytes < erase_length) {
        erase_length = faults.partial_erase_bytes;
    }
    memset(&flash->bytes[offset], 0xFF, erase_length);
    if (erase_length != length) {
        faults.partial_erase_call = 0u;
        return false;
    }
    return true;
}

static uint32_t fake_crc32(uint32_t seed, const uint8_t *data, uint32_t length)
{
    uint32_t crc = seed ^ 0xFFFFFFFFu;
    uint32_t i;
    for (i = 0u; i < length; ++i) {
        uint32_t c = (crc ^ data[i]) & 0xFFu;
        uint32_t bit;
        for (bit = 0u; bit < 8u; ++bit) {
            c = (c >> 1) ^ (0xEDB88320u & (uint32_t)(-(int32_t)(c & 1u)));
        }
        crc = (crc >> 8) ^ c;
    }
    return crc ^ 0xFFFFFFFFu;
}

static comp_recording_journal_port_t fake_port(void)
{
    comp_recording_journal_port_t port;
    port.read = fake_read;
    port.program = fake_program;
    port.erase = fake_erase;
    port.crc32 = fake_crc32;
    return port;
}

static void make_sha(uint8_t out[COMP_RECORDING_JOURNAL_SHA256_BYTES],
                     uint8_t value)
{
    memset(out, value, COMP_RECORDING_JOURNAL_SHA256_BYTES);
}

static int test_three_sessions_reset_ack_reclaim(void)
{
    fake_flash_t flash;
    comp_recording_journal_port_t port = fake_port();
    comp_recording_journal_t journal;
    comp_recording_journal_t remounted;
    comp_recording_journal_entry_t reserved[4];
    uint8_t sha[3][COMP_RECORDING_JOURNAL_SHA256_BYTES];
    uint8_t wrong_sha[COMP_RECORDING_JOURNAL_SHA256_BYTES];
    uint32_t i;

    memset(&flash, 0xFF, sizeof(flash));
    flash.fail_program_after = 0u;
    CHECK(comp_recording_journal_mount(&journal, &port, &flash,
                                      TEST_FLASH_BYTES) ==
              COMP_RECORDING_JOURNAL_OK,
          "blank mount");
    CHECK(comp_recording_journal_count(&journal) == 0u, "blank count");

    for (i = 0u; i < 3u; ++i) {
        make_sha(sha[i], (uint8_t)(0x20u + i));
        CHECK(comp_recording_journal_begin(
                  &journal, 6000u, 100u + i, 200u + i, 3u, 1u,
                  &reserved[i]) == COMP_RECORDING_JOURNAL_OK,
              "begin session");
        CHECK(reserved[i].recording_id == i + 1u, "monotonic id");
        CHECK((reserved[i].payload_offset %
               COMP_RECORDING_JOURNAL_SECTOR_BYTES) == 0u,
              "aligned payload");
        CHECK(comp_recording_journal_checkpoint(
                  &journal, reserved[i].recording_id, 4096u, 2048u) ==
                  COMP_RECORDING_JOURNAL_OK,
              "durable cursor checkpoint");
        CHECK(comp_recording_journal_finalize(
                  &journal, reserved[i].recording_id, 6000u,
                  10000u + i, 0x12340000u + i, sha[i], 3u) ==
                  COMP_RECORDING_JOURNAL_OK,
              "finalize session");
    }
    CHECK(comp_recording_journal_count(&journal) == 3u, "three sessions");
    CHECK(reserved[0].payload_offset != reserved[1].payload_offset &&
              reserved[1].payload_offset != reserved[2].payload_offset,
          "non-overlap starts");

    memset(&remounted, 0, sizeof(remounted));
    CHECK(comp_recording_journal_mount(&remounted, &port, &flash,
                                      TEST_FLASH_BYTES) ==
              COMP_RECORDING_JOURNAL_OK,
          "reset remount");
    CHECK(comp_recording_journal_count(&remounted) == 3u,
          "reset preserves catalog");
    for (i = 0u; i < 3u; ++i) {
        const comp_recording_journal_entry_t *entry =
            comp_recording_journal_find(&remounted, i + 1u);
        CHECK(entry != NULL, "reset entry found");
        CHECK(entry->sync_state == COMP_RECORDING_JOURNAL_UNSYNCED,
              "reset unsynced protected");
        CHECK(entry->total_length == 6000u, "reset length");
        CHECK(memcmp(entry->sha256, sha[i], sizeof(sha[i])) == 0,
              "reset sha");
    }

    make_sha(wrong_sha, 0xEEu);
    CHECK(comp_recording_journal_ack_complete(
              &remounted, 2u, 6000u, wrong_sha) ==
              COMP_RECORDING_JOURNAL_ACK_MISMATCH,
          "bad ack rejected");
    CHECK(comp_recording_journal_reclaim_acked(&remounted, 2u) ==
              COMP_RECORDING_JOURNAL_BAD_STATE,
          "unsynced reclaim rejected");
    CHECK(comp_recording_journal_ack_complete(
              &remounted, 2u, 6000u, sha[1]) ==
              COMP_RECORDING_JOURNAL_OK,
          "full ack accepted");
    CHECK(comp_recording_journal_reclaim_acked(&remounted, 2u) ==
              COMP_RECORDING_JOURNAL_OK,
          "exact acked reclaim");
    CHECK(comp_recording_journal_count(&remounted) == 2u,
          "one exact entry reclaimed");
    CHECK(comp_recording_journal_find(&remounted, 1u) != NULL &&
              comp_recording_journal_find(&remounted, 3u) != NULL,
          "neighbors retained");

    CHECK(comp_recording_journal_begin(
              &remounted, 4096u, 500u, 600u, 3u, 1u, &reserved[3]) ==
              COMP_RECORDING_JOURNAL_OK,
          "reuse acked hole");
    CHECK(reserved[3].recording_id == 4u, "id monotonic after reclaim");
    CHECK(reserved[3].extent_offset == reserved[1].extent_offset,
          "first fit reuses exact erased hole");

    return 0;
}

static int test_fail_closed_and_ab_recovery(void)
{
    fake_flash_t flash;
    fake_flash_t small_flash;
    comp_recording_journal_port_t port = fake_port();
    comp_recording_journal_t journal;
    comp_recording_journal_t recovered;
    comp_recording_journal_t small;
    comp_recording_journal_entry_t entry;
    uint32_t before_count;
    uint32_t recovered_abandoned;
    uint32_t i;

    memset(&flash, 0xFF, sizeof(flash));
    flash.fail_program_after = 0u;
    CHECK(comp_recording_journal_mount(&journal, &port, &flash,
                                      TEST_FLASH_BYTES) ==
              COMP_RECORDING_JOURNAL_OK,
          "ab mount");
    CHECK(comp_recording_journal_begin(&journal, 4096u, 0u, 1u, 3u, 1u,
                                      &entry) ==
              COMP_RECORDING_JOURNAL_OK,
          "ab baseline entry");
    before_count = comp_recording_journal_count(&journal);
    flash.fail_program_after = 80u;
    CHECK(comp_recording_journal_begin(&journal, 4096u, 0u, 2u, 3u, 1u,
                                      &entry) ==
              COMP_RECORDING_JOURNAL_IO_ERROR,
          "torn catalog rejected");
    CHECK(comp_recording_journal_count(&journal) == before_count,
          "ram catalog rolled back");
    CHECK(comp_recording_journal_mount(&recovered, &port, &flash,
                                      TEST_FLASH_BYTES) ==
              COMP_RECORDING_JOURNAL_OK,
          "ab remount after torn write");
    CHECK(comp_recording_journal_count(&recovered) == before_count,
          "ab chooses previous valid generation");
    {
        comp_recording_journal_entry_t after_reset;
        const comp_recording_journal_entry_t *abandoned =
            comp_recording_journal_find(&recovered, 1u);
        CHECK(abandoned != NULL &&
                  abandoned->sync_state == COMP_RECORDING_JOURNAL_WRITING,
              "reset preserves abandoned writing extent");
        CHECK(comp_recording_journal_recover_abandoned_writes(
                  &recovered, &recovered_abandoned) ==
                  COMP_RECORDING_JOURNAL_OK,
              "boot recovery commits abandoned writing cleanup");
        CHECK(recovered_abandoned == 1u &&
                  comp_recording_journal_find(&recovered, 1u) == NULL,
              "boot recovery removes zero-byte writing extent");
        CHECK(comp_recording_journal_begin(
                  &recovered, 4096u, 0u, 3u, 3u, 1u, &after_reset) ==
                  COMP_RECORDING_JOURNAL_OK,
              "new session after abandoned extent");
        CHECK(after_reset.extent_offset == 0u,
              "recovered extent is reusable after caller erase prepare");
        CHECK(comp_recording_journal_checkpoint(
                  &recovered, after_reset.recording_id, 128u, 0u) ==
                  COMP_RECORDING_JOURNAL_OK,
              "checkpoint interrupted prefix");
        recovered_abandoned = 99u;
        CHECK(comp_recording_journal_recover_abandoned_writes(
                  &recovered, &recovered_abandoned) ==
                  COMP_RECORDING_JOURNAL_OK,
              "checkpoint recovery scan succeeds");
        CHECK(recovered_abandoned == 1u &&
                  comp_recording_journal_find(
                      &recovered, after_reset.recording_id) == NULL,
              "checkpointed partial is abandoned after reboot");
    }
    CHECK(comp_recording_journal_count(&recovered) == 0u,
          "abort removes writing reservation");

    memset(&small_flash, 0xFF, sizeof(small_flash));
    small_flash.fail_program_after = 0u;
    CHECK(comp_recording_journal_mount(
              &small, &port, &small_flash,
              5u * COMP_RECORDING_JOURNAL_SECTOR_BYTES) ==
              COMP_RECORDING_JOURNAL_OK,
          "small mount");
    for (i = 0u; i < 3u; ++i) {
        CHECK(comp_recording_journal_begin(
                  &small, COMP_RECORDING_JOURNAL_SECTOR_BYTES,
                  0u, i, 3u, 1u, &entry) == COMP_RECORDING_JOURNAL_OK,
              "fill unacked extent");
    }
    CHECK(comp_recording_journal_begin(
              &small, COMP_RECORDING_JOURNAL_SECTOR_BYTES,
              0u, 9u, 3u, 1u, &entry) ==
              COMP_RECORDING_JOURNAL_STORAGE_FULL,
          "full of active writes cannot evict");
    CHECK(!comp_recording_journal_can_reserve(
              &small, COMP_RECORDING_JOURNAL_SECTOR_BYTES),
          "read-only reserve preflight protects active writes");
    CHECK(comp_recording_journal_count(&small) == 3u,
          "full preserves active writes");
    return 0;
}

static int test_ring_evicts_oldest_acked_only(void)
{
    fake_flash_t flash;
    comp_recording_journal_port_t port = fake_port();
    comp_recording_journal_t journal;
    comp_recording_journal_entry_t entries[5];
    uint8_t sha[5][COMP_RECORDING_JOURNAL_SHA256_BYTES];
    uint32_t i;

    memset(&flash, 0xFF, sizeof(flash));
    flash.fail_program_after = 0u;
    CHECK(comp_recording_journal_mount(
              &journal, &port, &flash,
              5u * COMP_RECORDING_JOURNAL_SECTOR_BYTES) ==
              COMP_RECORDING_JOURNAL_OK,
          "ring small mount");
    for (i = 0u; i < 3u; ++i) {
        make_sha(sha[i], (uint8_t)(0x40u + i));
        CHECK(comp_recording_journal_begin(
                  &journal, COMP_RECORDING_JOURNAL_SECTOR_BYTES,
                  0u, i + 1u, 3u, 1u, &entries[i]) ==
                  COMP_RECORDING_JOURNAL_OK,
              "ring fill begin");
        CHECK(comp_recording_journal_finalize(
                  &journal, entries[i].recording_id,
                  COMP_RECORDING_JOURNAL_SECTOR_BYTES, 1000u,
                  0x100u + i, sha[i], 3u) == COMP_RECORDING_JOURNAL_OK,
              "ring fill finalize");
    }
    CHECK(!comp_recording_journal_can_reserve(
              &journal, COMP_RECORDING_JOURNAL_SECTOR_BYTES),
          "full unsynced cache is protected from implicit eviction");
    CHECK(comp_recording_journal_ack_complete(
              &journal, entries[0].recording_id,
              COMP_RECORDING_JOURNAL_SECTOR_BYTES, sha[0]) ==
              COMP_RECORDING_JOURNAL_OK,
          "oldest entry host validated before ring eviction");
    CHECK(comp_recording_journal_can_reserve(
              &journal, COMP_RECORDING_JOURNAL_SECTOR_BYTES),
          "acked capacity is reclaimable as ring");
    CHECK(comp_recording_journal_begin(
              &journal, COMP_RECORDING_JOURNAL_SECTOR_BYTES,
              0u, 10u, 3u, 1u, &entries[3]) ==
              COMP_RECORDING_JOURNAL_OK,
          "ring overwrites oldest completed");
    CHECK(entries[3].recording_id == 4u,
          "ring keeps recording ids monotonic");
    CHECK(comp_recording_journal_find(&journal, 1u) == NULL &&
              comp_recording_journal_find(&journal, 2u) != NULL &&
              comp_recording_journal_find(&journal, 3u) != NULL &&
              comp_recording_journal_find(&journal, 4u) != NULL,
          "ring evicts exactly oldest completed entry");
    CHECK(journal.last_ring_evicted_count == 1u,
          "ring publishes deterministic eviction diagnostics");

    /* A live WRITING entry and remaining UNSYNCED entries are never victims. */
    CHECK(comp_recording_journal_ack_complete(
              &journal, entries[1].recording_id,
              COMP_RECORDING_JOURNAL_SECTOR_BYTES, sha[1]) ==
              COMP_RECORDING_JOURNAL_OK,
          "next entry host validated before ring eviction");
    CHECK(comp_recording_journal_begin(
              &journal, COMP_RECORDING_JOURNAL_SECTOR_BYTES,
              0u, 11u, 3u, 1u, &entries[4]) ==
              COMP_RECORDING_JOURNAL_OK,
          "ring reserves while another capture entry is writing");
    CHECK(comp_recording_journal_find(&journal, 2u) == NULL &&
              comp_recording_journal_find(&journal, 4u) != NULL &&
              comp_recording_journal_find(&journal, 5u) != NULL,
          "ring preserves active writing and evicts completed oldest");
    return 0;
}

static int test_ring_protects_unsynced_across_ack_state(void)
{
    fake_flash_t flash;
    comp_recording_journal_port_t port = fake_port();
    comp_recording_journal_t journal;
    comp_recording_journal_entry_t entries[4];
    uint8_t sha[3][COMP_RECORDING_JOURNAL_SHA256_BYTES];
    uint32_t i;

    memset(&flash, 0xFF, sizeof(flash));
    flash.fail_program_after = 0u;
    CHECK(comp_recording_journal_mount(
              &journal, &port, &flash,
              5u * COMP_RECORDING_JOURNAL_SECTOR_BYTES) ==
              COMP_RECORDING_JOURNAL_OK,
          "acked priority mount");
    for (i = 0u; i < 3u; ++i) {
        make_sha(sha[i], (uint8_t)(0x60u + i));
        CHECK(comp_recording_journal_begin(
                  &journal, COMP_RECORDING_JOURNAL_SECTOR_BYTES,
                  0u, i + 1u, 3u, 1u, &entries[i]) ==
                  COMP_RECORDING_JOURNAL_OK,
              "acked priority fill begin");
        CHECK(comp_recording_journal_finalize(
                  &journal, entries[i].recording_id,
                  COMP_RECORDING_JOURNAL_SECTOR_BYTES, 1000u,
                  0x200u + i, sha[i], 3u) == COMP_RECORDING_JOURNAL_OK,
              "acked priority fill finalize");
    }
    CHECK(comp_recording_journal_ack_complete(
              &journal, entries[1].recording_id,
              COMP_RECORDING_JOURNAL_SECTOR_BYTES, sha[1]) ==
              COMP_RECORDING_JOURNAL_OK,
          "middle entry acknowledged");
    CHECK(comp_recording_journal_begin(
              &journal, COMP_RECORDING_JOURNAL_SECTOR_BYTES,
              0u, 10u, 3u, 1u, &entries[3]) ==
              COMP_RECORDING_JOURNAL_OK,
          "ring begins with mixed acknowledgement state");
    CHECK(comp_recording_journal_find(&journal, 1u) != NULL &&
              comp_recording_journal_find(&journal, 2u) == NULL &&
              comp_recording_journal_find(&journal, 3u) != NULL,
          "ring evicts ACKED entry and preserves older UNSYNCED audio");
    return 0;
}

static int test_ring_repairs_stale_id_high_water_before_eviction(void)
{
    fake_flash_t flash;
    comp_recording_journal_port_t port = fake_port();
    comp_recording_journal_t journal;
    comp_recording_journal_entry_t entries[4];
    uint8_t sha[3][COMP_RECORDING_JOURNAL_SHA256_BYTES];
    uint32_t i;

    memset(&flash, 0xFF, sizeof(flash));
    flash.fail_program_after = 0u;
    CHECK(comp_recording_journal_mount(
              &journal, &port, &flash,
              5u * COMP_RECORDING_JOURNAL_SECTOR_BYTES) ==
              COMP_RECORDING_JOURNAL_OK,
          "stale high-water mount");
    for (i = 0u; i < 3u; ++i) {
        make_sha(sha[i], (uint8_t)(0x70u + i));
        CHECK(comp_recording_journal_begin(
                  &journal, COMP_RECORDING_JOURNAL_SECTOR_BYTES,
                  0u, i + 1u, 3u, 1u, &entries[i]) ==
                  COMP_RECORDING_JOURNAL_OK,
              "stale high-water fill begin");
        CHECK(comp_recording_journal_finalize(
                  &journal, entries[i].recording_id,
                  COMP_RECORDING_JOURNAL_SECTOR_BYTES, 1000u,
                  0x300u + i, sha[i], 3u) == COMP_RECORDING_JOURNAL_OK,
              "stale high-water fill finalize");
    }

    /* Reproduce the field failure: the durable high-water mark points at the
     * oldest id that the full ring is about to evict. */
    CHECK(comp_recording_journal_ack_complete(
              &journal, entries[0].recording_id,
              COMP_RECORDING_JOURNAL_SECTOR_BYTES, sha[0]) ==
              COMP_RECORDING_JOURNAL_OK,
          "stale high-water victim acknowledged");
    journal.catalog.next_recording_id = entries[0].recording_id;
    CHECK(comp_recording_journal_begin(
              &journal, COMP_RECORDING_JOURNAL_SECTOR_BYTES,
              0u, 10u, 3u, 1u, &entries[3]) ==
              COMP_RECORDING_JOURNAL_OK,
          "stale high-water ring begin");
    CHECK(entries[3].recording_id == 4u,
          "ring never reuses durable id after stale high-water recovery");
    CHECK(comp_recording_journal_find(&journal, 1u) == NULL &&
              comp_recording_journal_find(&journal, 4u) != NULL,
          "stale victim evicted under a new durable identity");
    CHECK(journal.catalog.next_recording_id == 5u,
          "repaired high-water persists the following id");
    return 0;
}

static int test_legacy_import_keeps_inline_header_extent(void)
{
    fake_flash_t flash;
    comp_recording_journal_port_t port = fake_port();
    comp_recording_journal_t journal;
    comp_recording_journal_entry_t legacy;
    comp_recording_journal_entry_t next;

    memset(&flash, 0xFF, sizeof(flash));
    flash.fail_program_after = 0u;
    CHECK(comp_recording_journal_mount(&journal, &port, &flash,
                                      TEST_FLASH_BYTES) ==
              COMP_RECORDING_JOURNAL_OK,
          "legacy mount");
    memset(&legacy, 0, sizeof(legacy));
    legacy.recording_id = 12u;
    legacy.extent_offset = 0u;
    legacy.payload_offset = 68u;
    legacy.reserved_bytes = 8192u;
    legacy.committed_bytes = 6000u;
    legacy.total_length = 6000u;
    legacy.duration_ms = 10000u;
    legacy.codec = 3u;
    legacy.source_mode = 1u;
    legacy.sync_state = COMP_RECORDING_JOURNAL_UNSYNCED;
    make_sha(legacy.sha256, 0x5Au);
    CHECK(comp_recording_journal_import_legacy(&journal, &legacy) ==
              COMP_RECORDING_JOURNAL_OK,
          "legacy import");
    CHECK(comp_recording_journal_begin(&journal, 4096u, 0u, 1u, 3u, 1u,
                                      &next) ==
              COMP_RECORDING_JOURNAL_OK,
          "begin after legacy");
    CHECK(next.recording_id == 13u, "legacy advances next id");
    CHECK(next.extent_offset == 8192u,
          "legacy inline header extent remains occupied");
    return 0;
}

static bool catalog_has_no_overlap(const comp_recording_journal_t *journal)
{
    uint32_t i, k;
    for (i = 0u; i < comp_recording_journal_count(journal); ++i) {
        const comp_recording_journal_entry_t *a =
            comp_recording_journal_at(journal, i);
        if (a == NULL || a->reserved_bytes == 0u ||
            a->extent_offset > journal->data_bytes ||
            a->reserved_bytes > journal->data_bytes - a->extent_offset) return false;
        for (k = i + 1u; k < comp_recording_journal_count(journal); ++k) {
            const comp_recording_journal_entry_t *b =
                comp_recording_journal_at(journal, k);
            if (b == NULL ||
                (a->extent_offset < b->extent_offset + b->reserved_bytes &&
                 b->extent_offset < a->extent_offset + a->reserved_bytes)) return false;
        }
    }
    return true;
}

static bool prepare_unsynced(fake_flash_t *flash,
                             comp_recording_journal_entry_t *entry,
                             uint8_t sha[COMP_RECORDING_JOURNAL_SHA256_BYTES])
{
    comp_recording_journal_port_t port = fake_port();
    comp_recording_journal_t journal;
    memset(flash, 0xFF, sizeof(*flash));
    flash->fail_program_after = 0u;
    reset_faults();
    make_sha(sha, 0xA6u);
    if (comp_recording_journal_mount_strict(&journal, &port, flash,
                                            TEST_FLASH_BYTES) !=
            COMP_RECORDING_JOURNAL_OK ||
        comp_recording_journal_begin(&journal, 8192u, 100u, 200u, 3u, 1u,
                                     entry) != COMP_RECORDING_JOURNAL_OK) return false;
    memset(&flash->bytes[entry->payload_offset], 0x5Au, 6000u);
    return comp_recording_journal_finalize(
               &journal, entry->recording_id, 6000u, 12000u,
               0xAABBCCDDu, sha, 3u) == COMP_RECORDING_JOURNAL_OK;
}

static bool unsynced_payload_intact(const fake_flash_t *flash,
                                    const comp_recording_journal_entry_t *entry)
{
    uint32_t i;
    if (entry == NULL || entry->sync_state != COMP_RECORDING_JOURNAL_UNSYNCED ||
        entry->total_length != 6000u) return false;
    for (i = 0u; i < entry->total_length; ++i)
        if (flash->bytes[entry->payload_offset + i] != 0x5Au) return false;
    return true;
}

/* Model consumed/torn append slots after the current valid snapshot. This
 * forces the real commit path to rotate banks; RAM identity stays unchanged. */
static void occupy_remaining_catalog_slots(fake_flash_t *flash,
                                          const comp_recording_journal_t *j)
{
    uint32_t stride=((uint32_t)sizeof(comp_recording_journal_catalog_t)+255u)/256u*256u;
    uint32_t start=((uint32_t)j->active_catalog_slot+1u)*stride;
    uint32_t base=j->data_bytes+(uint32_t)j->active_catalog*4096u;
    if(start<4096u)memset(&flash->bytes[base+start],0u,4096u-start);
}

static int test_catalog_cut_matrix_preserves_unsynced(void)
{
    fake_flash_t baseline, flash;
    comp_recording_journal_entry_t original, extra;
    comp_recording_journal_port_t port = fake_port();
    comp_recording_journal_t journal, rebooted;
    uint8_t sha[COMP_RECORDING_JOURNAL_SHA256_BYTES];
    uint32_t cut;
    CHECK(prepare_unsynced(&baseline, &original, sha), "prepare cut matrix");

    for (cut = 1u; cut < (uint32_t)sizeof(comp_recording_journal_catalog_t); ++cut) {
        flash = baseline; reset_faults();
        CHECK(comp_recording_journal_mount_strict(&journal, &port, &flash,
                  TEST_FLASH_BYTES) == COMP_RECORDING_JOURNAL_OK,
              "program-cut baseline mount");
        reset_faults(); faults.partial_program_call = 1u;
        faults.partial_program_bytes = cut;
        CHECK(comp_recording_journal_begin(&journal, 4096u, 0u, cut, 3u, 1u,
                                           &extra) ==
                  COMP_RECORDING_JOURNAL_IO_ERROR,
              "program-cut begin fails closed");
        reset_faults();
        CHECK(comp_recording_journal_mount_strict(&rebooted, &port, &flash,
                  TEST_FLASH_BYTES) == COMP_RECORDING_JOURNAL_OK,
              "program-cut remount");
        CHECK(unsynced_payload_intact(&flash,
                  comp_recording_journal_find(&rebooted, original.recording_id)),
              "program-cut preserves unacked payload");
        CHECK(comp_recording_journal_count(&rebooted) == 1u &&
                  catalog_has_no_overlap(&rebooted),
              "program-cut has no partial entry or overlap");
    }

    for (cut = 1u; cut < COMP_RECORDING_JOURNAL_SECTOR_BYTES; ++cut) {
        flash = baseline; reset_faults();
        CHECK(comp_recording_journal_mount_strict(&journal, &port, &flash,
                  TEST_FLASH_BYTES) == COMP_RECORDING_JOURNAL_OK,
              "erase-cut baseline mount");
        occupy_remaining_catalog_slots(&flash,&journal);
        reset_faults(); faults.partial_erase_call = 1u;
        faults.partial_erase_bytes = cut;
        CHECK(comp_recording_journal_begin(&journal, 4096u, 0u, cut, 3u, 1u,
                                           &extra) ==
                  COMP_RECORDING_JOURNAL_IO_ERROR,
              "erase-cut begin fails closed");
        reset_faults();
        CHECK(comp_recording_journal_mount_strict(&rebooted, &port, &flash,
                  TEST_FLASH_BYTES) == COMP_RECORDING_JOURNAL_OK,
              "erase-cut remount");
        CHECK(unsynced_payload_intact(&flash,
                  comp_recording_journal_find(&rebooted, original.recording_id)) &&
                  comp_recording_journal_count(&rebooted) == 1u &&
                  catalog_has_no_overlap(&rebooted),
              "erase-cut preserves unacked catalog and payload");
    }

    flash = baseline; reset_faults();
    CHECK(comp_recording_journal_mount_strict(&journal, &port, &flash,
              TEST_FLASH_BYTES) == COMP_RECORDING_JOURNAL_OK,
          "readback-fault baseline mount");
    occupy_remaining_catalog_slots(&flash,&journal);
    /* Full banks have no blank-slot reads. Rotation goes directly to the
     * program readback after bounded scans of the occupied remaining slots. */
    uint32_t stride=((uint32_t)sizeof(comp_recording_journal_catalog_t)+255u)/256u*256u;
    uint32_t slots=4096u/stride;
    reset_faults(); faults.fail_read_call=(slots-1u-journal.active_catalog_slot)*(stride/128u)+1u;
    CHECK(comp_recording_journal_begin(&journal, 4096u, 0u, 9u, 3u, 1u,
                                       &extra) == COMP_RECORDING_JOURNAL_IO_ERROR,
          "catalog readback failure reported");
    reset_faults();
    CHECK(comp_recording_journal_mount_strict(&rebooted, &port, &flash,
              TEST_FLASH_BYTES) == COMP_RECORDING_JOURNAL_OK,
          "readback-fault remount");
    CHECK(unsynced_payload_intact(&flash,
              comp_recording_journal_find(&rebooted, original.recording_id)) &&
              catalog_has_no_overlap(&rebooted),
          "readback-fault preserves prior audio without overlap");
    CHECK(comp_recording_journal_recover_abandoned_writes(&rebooted, NULL) ==
              COMP_RECORDING_JOURNAL_OK,
          "readback-fault completed write can be recovered after reboot");
    return 0;
}

static int test_finalize_ack_reclaim_cut_matrix(void)
{
    fake_flash_t baseline, flash;
    comp_recording_journal_port_t port = fake_port();
    comp_recording_journal_t journal, rebooted;
    comp_recording_journal_entry_t entry;
    uint8_t sha[COMP_RECORDING_JOURNAL_SHA256_BYTES];
    uint32_t cut, cursor;
    bool complete;

    memset(&baseline, 0xFF, sizeof(baseline)); baseline.fail_program_after = 0u;
    reset_faults(); make_sha(sha, 0xB7u);
    CHECK(comp_recording_journal_mount_strict(&journal, &port, &baseline,
              TEST_FLASH_BYTES) == COMP_RECORDING_JOURNAL_OK &&
          comp_recording_journal_begin(&journal, 8192u, 0u, 1u, 3u, 1u,
              &entry) == COMP_RECORDING_JOURNAL_OK,
          "prepare finalize cut matrix");
    memset(&baseline.bytes[entry.payload_offset], 0x5Au, 6000u);
    for (cut = 1u; cut < (uint32_t)sizeof(comp_recording_journal_catalog_t); ++cut) {
        flash = baseline; reset_faults();
        CHECK(comp_recording_journal_mount_strict(&journal, &port, &flash,
                  TEST_FLASH_BYTES) == COMP_RECORDING_JOURNAL_OK,
              "finalize-cut mount");
        reset_faults(); faults.partial_program_call = 1u;
        faults.partial_program_bytes = cut;
        CHECK(comp_recording_journal_finalize(&journal, entry.recording_id,
                  6000u, 1000u, 7u, sha, 3u) == COMP_RECORDING_JOURNAL_IO_ERROR,
              "finalize-cut fails closed");
        reset_faults();
        CHECK(comp_recording_journal_mount_strict(&rebooted, &port, &flash,
                  TEST_FLASH_BYTES) == COMP_RECORDING_JOURNAL_OK,
              "finalize-cut remount");
        const comp_recording_journal_entry_t *found =
            comp_recording_journal_find(&rebooted, entry.recording_id);
        CHECK(found != NULL && found->sync_state == COMP_RECORDING_JOURNAL_WRITING &&
                  found->total_length == 0u,
              "torn finalize never becomes finalized");
    }

    CHECK(prepare_unsynced(&baseline, &entry, sha), "prepare ACK cut matrix");
    for (cut = 1u; cut < (uint32_t)sizeof(comp_recording_journal_catalog_t); ++cut) {
        flash = baseline; reset_faults();
        CHECK(comp_recording_journal_mount_strict(&journal, &port, &flash,
                  TEST_FLASH_BYTES) == COMP_RECORDING_JOURNAL_OK,
              "ack-cut mount");
        reset_faults(); faults.partial_program_call = 1u;
        faults.partial_program_bytes = cut;
        CHECK(comp_recording_journal_ack_complete(&journal, entry.recording_id,
                  6000u, sha) == COMP_RECORDING_JOURNAL_IO_ERROR,
              "ack-cut fails closed");
        reset_faults();
        CHECK(comp_recording_journal_mount_strict(&rebooted, &port, &flash,
                  TEST_FLASH_BYTES) == COMP_RECORDING_JOURNAL_OK,
              "ack-cut remount");
        CHECK(unsynced_payload_intact(&flash,
                  comp_recording_journal_find(&rebooted, entry.recording_id)),
              "torn ACK preserves unacked payload");
    }

    CHECK(prepare_unsynced(&baseline, &entry, sha), "prepare reclaim cut matrix");
    reset_faults();
    CHECK(comp_recording_journal_mount_strict(&journal, &port, &baseline,
              TEST_FLASH_BYTES) == COMP_RECORDING_JOURNAL_OK &&
          comp_recording_journal_ack_complete(&journal, entry.recording_id,
              6000u, sha) == COMP_RECORDING_JOURNAL_OK &&
          comp_recording_journal_begin_reclaim(&journal, entry.recording_id) ==
              COMP_RECORDING_JOURNAL_OK,
          "prepare durable ERASING state");
    {
        static const uint32_t cuts[] = {1u, 2u, 63u, 511u, 2048u, 4095u};
        size_t i;
        for (i = 0u; i < sizeof(cuts) / sizeof(cuts[0]); ++i) {
            flash = baseline; reset_faults();
            CHECK(comp_recording_journal_mount_strict(&journal, &port, &flash,
                      TEST_FLASH_BYTES) == COMP_RECORDING_JOURNAL_OK,
                  "reclaim-cut mount");
            cursor = 0u; complete = false; reset_faults();
            faults.partial_erase_call = 1u; faults.partial_erase_bytes = cuts[i];
            CHECK(comp_recording_journal_reclaim_step(&journal, entry.recording_id,
                      &cursor, &complete) == COMP_RECORDING_JOURNAL_IO_ERROR &&
                      cursor == 0u && !complete,
                  "partial reclaim erase does not advance cursor");
            reset_faults();
            CHECK(comp_recording_journal_mount_strict(&rebooted, &port, &flash,
                      TEST_FLASH_BYTES) == COMP_RECORDING_JOURNAL_OK &&
                  comp_recording_journal_find(&rebooted, entry.recording_id) != NULL &&
                  comp_recording_journal_find(&rebooted, entry.recording_id)->sync_state ==
                      COMP_RECORDING_JOURNAL_ERASING,
                  "partial reclaim remains resumable after reboot");
            cursor = 0u; complete = false;
            while (!complete) CHECK(comp_recording_journal_reclaim_step(
                      &rebooted, entry.recording_id, &cursor, &complete) ==
                      COMP_RECORDING_JOURNAL_OK,
                  "reclaim restarts safely from sector zero");
            CHECK(comp_recording_journal_find(&rebooted, entry.recording_id) == NULL &&
                      catalog_has_no_overlap(&rebooted),
                  "resumed reclaim removes only acknowledged entry");
        }
    }
    return 0;
}

static int test_capacity_and_fixed_duration_admission(void)
{
    fake_flash_t flash;
    comp_recording_journal_t journal, before;
    comp_recording_journal_port_t port = fake_port();
    comp_recording_journal_space_t space;
    comp_recording_journal_entry_t entry[4];
    uint32_t budget = 1u;
    uint8_t sha[32];
    memset(&flash, 255, sizeof(flash)); flash.fail_program_after = 0u;
    reset_faults();
    CHECK(comp_recording_journal_mount(&journal,&port,&flash,TEST_FLASH_BYTES)==
          COMP_RECORDING_JOURNAL_OK,"capacity mount");
    reset_faults(); before=journal;
    CHECK(comp_recording_journal_space(&journal,&space) &&
          space.free_bytes==57344u && space.largest_free_extent==57344u &&
          space.used_entries==0u,"actual mounted bytes exclude both catalogs");
    CHECK(comp_recording_journal_recording_budget(&journal,25u,&budget) && budget==57344u,
          "exact rounded fixed-duration fit");
    CHECK(!comp_recording_journal_recording_budget(&journal,26u,&budget) && !budget,
          "fixed duration must not shrink to fit");
    CHECK(!comp_recording_journal_recording_budget(&journal,UINT32_MAX,&budget) && !budget,
          "overflow must fail closed");
    CHECK(comp_recording_journal_recording_budget(&journal,0u,&budget) && budget==57344u,
          "no time ceiling still has finite storage ceiling");
    CHECK(!faults.read_calls && !faults.program_calls && !faults.erase_calls &&
          memcmp(&journal,&before,sizeof(journal))==0,"query is read-only RAM snapshot");

    make_sha(sha,0x51u);
    for (uint32_t i=0u;i<4u;++i) {
        CHECK(comp_recording_journal_begin(&journal,8192u,0u,i,3u,1u,&entry[i])==
              COMP_RECORDING_JOURNAL_OK,"capacity fixture reserve");
        if (i<3u) CHECK(comp_recording_journal_finalize(&journal,entry[i].recording_id,
              6000u,1000u,0u,sha,3u)==COMP_RECORDING_JOURNAL_OK,"capacity fixture finalize");
    }
    CHECK(comp_recording_journal_ack_complete(&journal,entry[1].recording_id,6000u,sha)==
          COMP_RECORDING_JOURNAL_OK,"capacity fixture ACK");
    CHECK(comp_recording_journal_reclaim_acked(&journal,entry[1].recording_id)==
          COMP_RECORDING_JOURNAL_OK,"create an interior free extent");
    CHECK(comp_recording_journal_ack_complete(&journal,entry[2].recording_id,6000u,sha)==
          COMP_RECORDING_JOURNAL_OK,"capacity fixture consumed");
    CHECK(comp_recording_journal_space(&journal,&space) && space.free_bytes==32768u &&
          space.largest_free_extent==24576u && space.protected_bytes==16384u &&
          space.consumed_bytes==8192u && space.used_entries==3u &&
          space.unsynced_entries==1u && space.writing_entries==1u && space.consumed_entries==1u,
          "fragmentation, active and acknowledged reservations count honestly");
    CHECK(!comp_recording_journal_recording_budget(&journal,10u,&budget) && !budget,
          "total free bytes cannot substitute for one contiguous extent");
    CHECK(comp_recording_journal_begin_reclaim(&journal,entry[2].recording_id)==
          COMP_RECORDING_JOURNAL_OK && comp_recording_journal_space(&journal,&space) &&
          space.consumed_bytes==8192u && space.free_bytes==32768u,
          "ERASING is occupied until durable removal");
    before=journal;
    journal.catalog.entries[0].reserved_bytes=TEST_FLASH_BYTES;
    CHECK(!comp_recording_journal_space(&journal,&space) && !space.free_bytes &&
          !comp_recording_journal_recording_budget(&journal,1u,&budget) && !budget,
          "out-of-range reservation cannot advertise capacity");
    journal=before;
    journal.catalog.entries[2].extent_offset=journal.catalog.entries[0].extent_offset;
    CHECK(!comp_recording_journal_space(&journal,&space),"overlapping catalog fails closed");
    journal=before;
    while (comp_recording_journal_count(&journal)<COMP_RECORDING_JOURNAL_MAX_ENTRIES)
        CHECK(comp_recording_journal_begin(&journal,4096u,0u,0u,3u,1u,&entry[0])==
              COMP_RECORDING_JOURNAL_OK,"fill catalog with protected reservations");
    CHECK(comp_recording_journal_space(&journal,&space) && space.free_bytes>4096u &&
          !comp_recording_journal_recording_budget(&journal,1u,&budget) && !budget,
          "free bytes do not bypass the seven-entry directory ceiling");
    puts("PASS_RECORDING_CAPACITY_HOST actual_geometry=1 fragmented=1 consumed_occupied=1 fixed_no_clamp=1 directory_full=1 invalid_fail_closed=1 read_only=1");
    return 0;
}

static int test_confirmed_discard_intent_cut_matrix(void)
{
    fake_flash_t baseline, flash;
    comp_recording_journal_entry_t original;
    comp_recording_journal_port_t port = fake_port();
    comp_recording_journal_t journal, rebooted;
    uint8_t sha[COMP_RECORDING_JOURNAL_SHA256_BYTES];
    CHECK(prepare_unsynced(&baseline, &original, sha), "prepare confirmed loss cuts");
    for (uint32_t mode=0u; mode<2u; ++mode) {
        const uint32_t bytes=mode==0u ? (uint32_t)sizeof(comp_recording_journal_catalog_t)
                                    : COMP_RECORDING_JOURNAL_SECTOR_BYTES;
        for (uint32_t cut=1u; cut<bytes; ++cut) {
            flash=baseline; reset_faults();
            CHECK(comp_recording_journal_mount_strict(&journal,&port,&flash,TEST_FLASH_BYTES)==
                  COMP_RECORDING_JOURNAL_OK,"mount before confirmed loss cut");
            const comp_recording_journal_entry_t *finalized=comp_recording_journal_find(
                  &journal,original.recording_id);
            CHECK(finalized && finalized->total_length==6000u,"read finalized cut identity");
            original=*finalized;
            const uint32_t generation=journal.catalog.generation;
            if(mode==1u)occupy_remaining_catalog_slots(&flash,&journal);
            reset_faults();
            if (mode==0u) {faults.partial_program_call=1u;faults.partial_program_bytes=cut;}
            else {faults.partial_erase_call=1u;faults.partial_erase_bytes=cut;}
            CHECK(comp_recording_journal_discard_oldest_confirmed(&journal,generation,
                  original.recording_id,original.total_length,sha)==COMP_RECORDING_JOURNAL_IO_ERROR,
                  "torn user-loss intent reports IO failure");
            CHECK(unsynced_payload_intact(&flash,comp_recording_journal_find(&journal,
                  original.recording_id)),"RAM rollback never erases the original");
            reset_faults();
            CHECK(comp_recording_journal_mount_strict(&rebooted,&port,&flash,TEST_FLASH_BYTES)==
                  COMP_RECORDING_JOURNAL_OK,"confirmed loss cut remount");
            const comp_recording_journal_entry_t *entry=comp_recording_journal_find(
                  &rebooted,original.recording_id);
            /* A valid complete CRC may already be durable even if the port
             * reported an IO error. Only that exact user-approved identity may
             * survive as ERASING; incomplete intent must remain UNSYNCED. */
            CHECK(entry && entry->total_length==original.total_length &&
                  entry->acked_offset==0u && memcmp(entry->sha256,sha,sizeof(sha))==0 &&
                  (entry->sync_state==COMP_RECORDING_JOURNAL_UNSYNCED ||
                   entry->sync_state==COMP_RECORDING_JOURNAL_ERASING) &&
                  comp_recording_journal_count(&rebooted)==1u && catalog_has_no_overlap(&rebooted),
                  "loss cut retains exact identity without forging consume");
            for (uint32_t i=0u;i<entry->total_length;++i)
                CHECK(flash.bytes[entry->payload_offset+i]==0x5Au,"intent cut never erases payload");
            CHECK(entry->sync_state!=COMP_RECORDING_JOURNAL_ERASING ||
                  rebooted.catalog.generation==generation+1u,"erase authority needs full newer catalog");
        }
    }
    puts("PASS_CONFIRMED_DISCARD_INTENT_CUT_MATRIX all_catalog_program_prefixes=1 all_catalog_erase_prefixes=1 exact_identity=1 payload_intact=1 forged_ack=0");
    return 0;
}

static int test_append_catalog_and_compact_checkpoints(void)
{
    fake_flash_t flash,baseline;comp_recording_journal_t j,rebooted;
    comp_recording_journal_port_t port=fake_port();comp_recording_journal_entry_t entry;
    uint8_t sha[32];make_sha(sha,0xC8u);
    memset(&flash,255,sizeof(flash));flash.fail_program_after=0u;reset_faults();
    CHECK(comp_recording_journal_mount_strict(&j,&port,&flash,TEST_FLASH_BYTES)==COMP_RECORDING_JOURNAL_OK,"append blank mount");
    CHECK(comp_recording_journal_begin(&j,8192u,44u,55u,3u,1u,&entry)==COMP_RECORDING_JOURNAL_OK,"append writing intent");
    CHECK(comp_recording_journal_checkpoint_log_init(&j,entry.recording_id)==COMP_RECORDING_JOURNAL_OK,"erased footer ready intent");
    uint32_t generation=j.catalog.generation,erases=faults.erase_calls;
    for(uint32_t slot=0u;slot<64u;++slot) {
        CHECK(comp_recording_journal_checkpoint_verified(&j,entry.recording_id,32u*(slot+1u),slot,sha)==COMP_RECORDING_JOURNAL_OK,"compact checkpoint append");
        CHECK(j.catalog.generation==generation && faults.erase_calls==erases,"capture checkpoints never erase or commit catalog");
    }
    CHECK(comp_recording_journal_checkpoint_verified(&j,entry.recording_id,2080u,0u,sha)==COMP_RECORDING_JOURNAL_STORAGE_FULL,"bounded log cannot overwrite checkpoints");
    reset_faults();
    CHECK(comp_recording_journal_mount_strict(&rebooted,&port,&flash,TEST_FLASH_BYTES)==COMP_RECORDING_JOURNAL_OK,"compact log reload");
    CHECK(comp_recording_journal_find(&rebooted,entry.recording_id)->committed_bytes==2048u &&
          rebooted.checkpoint_slots[0]==64u,"reload restores newest valid digest and next slot");

    memset(&baseline,255,sizeof(baseline));baseline.fail_program_after=0u;reset_faults();
    CHECK(comp_recording_journal_mount_strict(&j,&port,&baseline,TEST_FLASH_BYTES)==COMP_RECORDING_JOURNAL_OK &&
          comp_recording_journal_begin(&j,8192u,44u,55u,3u,1u,&entry)==COMP_RECORDING_JOURNAL_OK &&
          comp_recording_journal_checkpoint_log_init(&j,entry.recording_id)==COMP_RECORDING_JOURNAL_OK &&
          comp_recording_journal_checkpoint_verified(&j,entry.recording_id,256u,0x1122u,sha)==COMP_RECORDING_JOURNAL_OK,"compact cut baseline");
    for(uint32_t cut=1u;cut<64u;++cut) {
        flash=baseline;reset_faults();
        CHECK(comp_recording_journal_mount_strict(&j,&port,&flash,TEST_FLASH_BYTES)==COMP_RECORDING_JOURNAL_OK,"compact cut mount");
        reset_faults();faults.partial_program_call=1u;faults.partial_program_bytes=cut;
        CHECK(comp_recording_journal_checkpoint_verified(&j,entry.recording_id,512u,0x3344u,sha)==COMP_RECORDING_JOURNAL_IO_ERROR,"torn compact write fails");
        CHECK(faults.erase_calls==0u && comp_recording_journal_find(&j,entry.recording_id)->committed_bytes==256u,"failed checkpoint preserves prior identity in RAM");
        reset_faults();
        CHECK(comp_recording_journal_mount_strict(&rebooted,&port,&flash,TEST_FLASH_BYTES)==COMP_RECORDING_JOURNAL_OK,"compact cut reboot");
        const comp_recording_journal_entry_t *saved=comp_recording_journal_find(&rebooted,entry.recording_id);
        CHECK(saved && saved->committed_bytes==256u && saved->acked_offset==0u && saved->sync_state==COMP_RECORDING_JOURNAL_WRITING,"torn footer cannot forge progress or ACK");
        CHECK(comp_recording_journal_checkpoint_verified(&rebooted,entry.recording_id,768u,0x5566u,sha)==COMP_RECORDING_JOURNAL_OK,"retry skips torn slot");
    }
    /* Legacy CRJ1 data remains readable through the first CRJ2 commit. */
    memset(&flash,255,sizeof(flash));flash.fail_program_after=0u;reset_faults();
    CHECK(comp_recording_journal_mount(&j,&port,&flash,TEST_FLASH_BYTES)==COMP_RECORDING_JOURNAL_OK &&
          comp_recording_journal_begin(&j,8192u,0u,0u,3u,1u,&entry)==COMP_RECORDING_JOURNAL_OK &&
          comp_recording_journal_finalize(&j,entry.recording_id,6000u,1u,1u,sha,3u)==COMP_RECORDING_JOURNAL_OK,"legacy migration baseline");
    CHECK(comp_recording_journal_mount_strict(&rebooted,&port,&flash,TEST_FLASH_BYTES)==COMP_RECORDING_JOURNAL_OK &&
          comp_recording_journal_find(&rebooted,entry.recording_id)->total_length==6000u,"CRJ1 remains readable");
    comp_recording_journal_entry_t other;
    erases=faults.erase_calls;
    CHECK(comp_recording_journal_begin(&rebooted,4096u,0u,0u,3u,1u,&other)==COMP_RECORDING_JOURNAL_OK &&
          faults.erase_calls==erases,"legacy migrates by appending without erasing live catalog");
    puts("PASS_APPEND_CHECKPOINTS_HOST compact_cuts=all capture_catalog_writes=0 capture_erases=0 bounded_slots=64 legacy_read=1");
    return 0;
}

static uint32_t cooperative_calls,cooperative_credit;
static bool cooperative_fail;
static bool cooperative_erase(void *context,uint32_t offset,uint32_t remaining,uint32_t *erased)
{
    cooperative_calls++;*erased=0u;
    if(cooperative_fail)return false;
    if(!cooperative_credit)return true;
    *erased=cooperative_credit;
    if(*erased>remaining || *erased%4096u)return true; /* malformed port result */
    return fake_erase(context,offset,*erased);
}
static int test_cooperative_reclaim(void)
{
    fake_flash_t flash;
    comp_recording_journal_t j,rebooted;
    comp_recording_journal_port_t port=fake_port();
    comp_recording_journal_entry_t first,other;
    uint8_t sha[32];make_sha(sha,0x67u);
    memset(&flash,255,sizeof(flash));flash.fail_program_after=0u;reset_faults();
    CHECK(comp_recording_journal_mount_strict(&j,&port,&flash,TEST_FLASH_BYTES)==COMP_RECORDING_JOURNAL_OK,"cooperative mount");
    CHECK(comp_recording_journal_begin(&j,12288u,0u,0u,3u,1u,&first)==COMP_RECORDING_JOURNAL_OK &&
          comp_recording_journal_finalize(&j,first.recording_id,6000u,1000u,0u,sha,3u)==COMP_RECORDING_JOURNAL_OK &&
          comp_recording_journal_begin(&j,4096u,0u,0u,3u,1u,&other)==COMP_RECORDING_JOURNAL_OK,"two non-overlapping owners");
    memset(flash.bytes+first.extent_offset,0xA5u,first.reserved_bytes);
    memset(flash.bytes+other.extent_offset,0x69u,other.reserved_bytes);
    j.reclaim_erase_step=cooperative_erase;
    uint32_t cursor=0u;bool complete=false;cooperative_calls=0u;cooperative_credit=0u;cooperative_fail=false;
    CHECK(comp_recording_journal_reclaim_step(&j,first.recording_id,&cursor,&complete)==COMP_RECORDING_JOURNAL_BAD_STATE && cooperative_calls==0u,"UNSYNCED never reaches erase port");
    CHECK(comp_recording_journal_ack_complete(&j,first.recording_id,6000u,sha)==COMP_RECORDING_JOURNAL_OK &&
          comp_recording_journal_begin_reclaim(&j,first.recording_id)==COMP_RECORDING_JOURNAL_OK,"durable ERASING before physical start");
    uint32_t generation=j.catalog.generation,erases=faults.erase_calls;
    CHECK(comp_recording_journal_reclaim_step(&j,first.recording_id,&cursor,&complete)==COMP_RECORDING_JOURNAL_OK && cursor==0u && !complete &&
          faults.erase_calls==erases && j.catalog.generation==generation,"pending leaves reservation and cursor intact");
    cooperative_fail=true;
    CHECK(comp_recording_journal_reclaim_step(&j,first.recording_id,&cursor,&complete)==COMP_RECORDING_JOURNAL_IO_ERROR && cursor==0u && !complete,"erase error no credit");
    cooperative_fail=false;cooperative_credit=1u;
    CHECK(comp_recording_journal_reclaim_step(&j,first.recording_id,&cursor,&complete)==COMP_RECORDING_JOURNAL_IO_ERROR && cursor==0u,"unaligned credit refused");
    cooperative_credit=first.reserved_bytes+4096u;
    CHECK(comp_recording_journal_reclaim_step(&j,first.recording_id,&cursor,&complete)==COMP_RECORDING_JOURNAL_IO_ERROR && cursor==0u,"out-of-extent credit refused");
    cooperative_credit=8192u;
    CHECK(comp_recording_journal_reclaim_step(&j,first.recording_id,&cursor,&complete)==COMP_RECORDING_JOURNAL_OK && cursor==8192u && !complete &&
          comp_recording_journal_find(&j,first.recording_id)!=NULL,"completed portion retained until full erase");
    CHECK(comp_recording_journal_mount_strict(&rebooted,&port,&flash,TEST_FLASH_BYTES)==COMP_RECORDING_JOURNAL_OK && !rebooted.reclaim_erase_step,"mount resets transient port");
    rebooted.reclaim_erase_step=cooperative_erase;cursor=0u;cooperative_credit=4096u;
    while(!complete)CHECK(comp_recording_journal_reclaim_step(&rebooted,first.recording_id,&cursor,&complete)==COMP_RECORDING_JOURNAL_OK,"reset restarts from durable ERASING");
    CHECK(comp_recording_journal_find(&rebooted,first.recording_id)==NULL &&
          comp_recording_journal_find(&rebooted,other.recording_id)!=NULL,"only exact consumed owner removed");
    for(uint32_t i=0u;i<other.reserved_bytes;i++)CHECK(flash.bytes[other.extent_offset+i]==0x69u,"neighbour payload preserved after recovery");
    puts("PASS_COOPERATIVE_RECLAIM_HOST_ONLY pending_no_credit=1 failure_no_credit=1 remount_resume=1 neighbour_preserved=1");
    return 0;
}

int main(int argc,char **argv)
{
    if(argc==2 && strcmp(argv[1],"--cooperative-reclaim")==0)return test_cooperative_reclaim();
    /* OTA claims a shared tail, leaving the existing recording catalog intact.
     * Releasing the claim must restore capacity without erasing any recording. */
    {
        fake_flash_t flash;comp_recording_journal_t j;comp_recording_journal_space_t space;
        memset(&flash,255,sizeof(flash));flash.fail_program_after=0u;reset_faults();
        const comp_recording_journal_port_t p={fake_read,fake_program,fake_erase,fake_crc32};
        CHECK(comp_recording_journal_mount_strict(&j,&p,&flash,TEST_FLASH_BYTES)==COMP_RECORDING_JOURNAL_OK,"shared mount");
        CHECK(comp_recording_journal_set_allocation_bytes(&j,32768u),"reserve OTA tail");
        CHECK(comp_recording_journal_space(&j,&space)&&space.free_bytes==32768u,"claim excluded from free capacity");
        comp_recording_journal_entry_t e;
        CHECK(comp_recording_journal_begin(&j,32768u,0u,0u,3u,1u,&e)==COMP_RECORDING_JOURNAL_OK,"recording fits before claim");
        CHECK(e.extent_offset+e.reserved_bytes<=32768u,"recording never crosses claim");
        CHECK(!comp_recording_journal_set_allocation_bytes(&j,28672u),"OTA cannot overwrite live reservation");
        CHECK(!comp_recording_journal_can_reserve(&j,4096u),"full prefix protected");
        CHECK(comp_recording_journal_set_allocation_bytes(&j,j.data_bytes),"release tail");
        CHECK(comp_recording_journal_can_reserve(&j,4096u),"released bytes reusable");
    }
    int rc = test_cooperative_reclaim();
    if(rc!=0)return rc;
    rc = test_capacity_and_fixed_duration_admission();
    if (rc != 0) return rc;
    rc = test_three_sessions_reset_ack_reclaim();
    if (rc != 0) {
        return rc;
    }
    rc = test_fail_closed_and_ab_recovery();
    if (rc != 0) {
        return rc;
    }
    rc = test_legacy_import_keeps_inline_header_extent();
    if (rc != 0) {
        return rc;
    }
    rc = test_ring_evicts_oldest_acked_only();
    if (rc != 0) {
        return rc;
    }
    rc = test_ring_protects_unsynced_across_ack_state();
    if (rc != 0) {
        return rc;
    }
    rc = test_ring_repairs_stale_id_high_water_before_eviction();
    if (rc != 0) {
        return rc;
    }
    rc = test_catalog_cut_matrix_preserves_unsynced();
    if (rc != 0) return rc;
    rc = test_finalize_ack_reclaim_cut_matrix();
    if (rc != 0) return rc;
    rc = test_confirmed_discard_intent_cut_matrix();
    if (rc != 0) return rc;
    rc = test_append_catalog_and_compact_checkpoints();
    if (rc != 0) return rc;
    puts("PASS_COMP_REQ_778_RECORDING_JOURNAL_HOST");
    puts("PASS_RECORDING_JOURNAL_FAULT_MATRIX program_cuts=all catalog_bytes erase_cuts=all catalog_sector_bytes readback_failure=1 finalize_torn=1 ack_torn=1 reclaim_partial_resume=1 unsynced_preserved=1 overlap=0");
    return 0;
}
