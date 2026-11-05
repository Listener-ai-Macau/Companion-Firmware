/*
 * COMP-REQ-602 supplemental OTA byte-transfer scenario (host fixture).
 *
 * WHY THIS EXISTS:
 *   The canonical test (third_party/denzic-platform/ota/embedded/c/tests/
 *   test_denzic_ota_v1.c) FAILS at the current submodule checkout: its
 *   re-BEGIN resumes with chunk=4, but it then sends a data packet whose
 *   payload is 5 bytes, so the size guard (BAD_SIZE, hard error -> state
 *   ERROR) preempts the offset-mismatch check it intended to exercise. That is
 *   a test-scenario construction bug, NOT an implementation regression.
 *
 *   This fixture compiles the REAL, unmodified denzic_ota_v1.c (read-only) and
 *   drives the SAME state machine through the SAME intended invariants, but
 *   with the scenario constructed validly (chunk stays >= payload, so the
 *   offset-mismatch recovery path is actually reached). It prints an observable
 *   per-step trace and records a non-zero exit if any invariant fails.
 *
 *   It does NOT modify denzic-platform, does NOT make the canonical test pass,
 *   and does NOT touch hardware/flash/radio. It proves the implementation's
 *   offset-mismatch recovery / finish / abort / bad-magic paths are sound when
 *   the transport scenario is valid.
 */

#include "denzic_ota_v1.h"

#include <stdio.h>
#include <string.h>

typedef struct {
    uint8_t image[64];
    size_t image_size;
    uint32_t expected_size;
    bool aborted;
    bool finished;
    uint32_t begin_count;
    uint32_t abort_count;
} storage_t;

static bool s_begin(void *ctx, uint32_t image_size)
{
    storage_t *s = (storage_t *)ctx;
    s->image_size = 0u;
    s->expected_size = image_size;
    s->aborted = false;
    s->finished = false;
    s->begin_count++;
    return image_size <= sizeof(s->image);
}

static bool s_write(void *ctx, const uint8_t *data, size_t length)
{
    storage_t *s = (storage_t *)ctx;
    if (s->image_size + length > sizeof(s->image)) {
        return false;
    }
    memcpy(&s->image[s->image_size], data, length);
    s->image_size += length;
    return true;
}

static bool s_finish(void *ctx)
{
    storage_t *s = (storage_t *)ctx;
    s->finished = (s->image_size == s->expected_size);
    return s->finished;
}

static void s_abort(void *ctx)
{
    storage_t *s = (storage_t *)ctx;
    s->aborted = true;
    s->abort_count++;
}

static int g_failures = 0;

static void check(int condition, const char *label)
{
    if (condition) {
        printf("  [PASS] %s\n", label);
    } else {
        printf("  [FAIL] %s\n", label);
        g_failures++;
    }
}

static void put_u16(uint8_t *b, uint16_t v) { b[0] = (uint8_t)(v & 0xffu); b[1] = (uint8_t)(v >> 8u); }
static void put_u32(uint8_t *b, uint32_t v)
{
    b[0] = (uint8_t)(v & 0xffu);
    b[1] = (uint8_t)((v >> 8u) & 0xffu);
    b[2] = (uint8_t)((v >> 16u) & 0xffu);
    b[3] = (uint8_t)((v >> 24u) & 0xffu);
}

static void control_packet(uint8_t *p, uint8_t op, uint32_t size, uint16_t chunk, uint16_t window, uint32_t crc)
{
    memset(p, 0, DENZIC_OTA_V1_CONTROL_BYTES);
    memcpy(p, DENZIC_OTA_V1_MAGIC, 4u);
    p[4] = op;
    p[5] = DENZIC_OTA_V1_PROTOCOL_VERSION;
    put_u32(&p[8], size);
    put_u16(&p[12], chunk);
    put_u16(&p[14], window);
    put_u32(&p[16], crc);
}

int main(void)
{
    denzic_ota_v1_context_t ctx;
    storage_t st;
    memset(&st, 0, sizeof(st));
    denzic_ota_v1_storage_driver_t drv = { s_begin, s_write, s_finish, s_abort };
    uint8_t control[DENZIC_OTA_V1_CONTROL_BYTES];
    uint8_t data[DENZIC_OTA_V1_DATA_HEADER_BYTES + 5u];
    uint8_t status[DENZIC_OTA_V1_STATUS_BYTES];

    printf("ota_transfer_supplemental begin (denzic_ota_v1 real core, RAM-backed storage)\n");

    /* init + BEGIN -> RECEIVING */
    denzic_ota_v1_init(&ctx, drv, &st, 5u, 3u);
    control_packet(control, DENZIC_OTA_V1_OP_BEGIN, 8u, 5u, 3u, 0x12345678u);
    check(denzic_ota_v1_handle_control(&ctx, control, sizeof(control)) == 1, "BEGIN accepted");
    check(ctx.state == DENZIC_OTA_V1_STATE_RECEIVING, "state==RECEIVING after BEGIN");

    /* data @offset0, 5B */
    put_u32(data, 0u);
    memcpy(&data[4], "abcde", 5u);
    check(denzic_ota_v1_handle_data(&ctx, data, sizeof(data)) == 1, "data @offset0 written");
    check(ctx.bytes_written == 5u, "bytes_written==5");

    /* re-BEGIN SAME crc, chunk kept at 5 (>= payload) -> resume, no re-begin/abort */
    control_packet(control, DENZIC_OTA_V1_OP_BEGIN, 8u, 5u, 2u, 0x12345678u);
    check(denzic_ota_v1_handle_control(&ctx, control, sizeof(control)) == 1, "re-BEGIN same CRC resumed");
    check(st.begin_count == 1u, "begin_count==1 (resume, storage_begin not re-called)");
    check(st.abort_count == 0u, "abort_count==0");

    /* offset-mismatch packet: chunk is 5, payload 5B fits (9 <= 5+4), so the
     * offset check is REACHED -> OFFSET_MISMATCH recoverable, state STAYS RECEIVING.
     * (This is the path the canonical test intended but preempted via BAD_SIZE.) */
    put_u32(data, 7u);
    check(denzic_ota_v1_handle_data(&ctx, data, sizeof(data)) == 0, "offset-mismatch data rejected");
    check(ctx.state == DENZIC_OTA_V1_STATE_RECEIVING, "state STAYS RECEIVING after recoverable offset mismatch");
    check(ctx.last_error == DENZIC_OTA_V1_ERROR_OFFSET_MISMATCH, "last_error==OFFSET_MISMATCH (recoverable, no state corruption)");

    /* resume at correct offset -> append */
    put_u32(data, 5u);
    memcpy(&data[4], "fgh", 3u);
    check(denzic_ota_v1_handle_data(&ctx, data, DENZIC_OTA_V1_DATA_HEADER_BYTES + 3u) == 1, "data @offset5 appended");
    check(ctx.bytes_written == 8u, "bytes_written==8");
    check(ctx.last_error == DENZIC_OTA_V1_ERROR_NONE, "last_error cleared to NONE");

    /* FINISH -> COMPLETE */
    control_packet(control, DENZIC_OTA_V1_OP_FINISH, 8u, 5u, 3u, 0x12345678u);
    check(denzic_ota_v1_handle_control(&ctx, control, sizeof(control)) == 1, "FINISH accepted");
    check(st.finished, "storage finished");
    check(ctx.state == DENZIC_OTA_V1_STATE_COMPLETE, "state==COMPLETE");

    /* status encode -> DOV1 + state + ACTIVE_LINK_CONFIRMED */
    denzic_ota_v1_set_status_flags(&ctx, DENZIC_OTA_V1_STATUS_FLAG_ACTIVE_LINK_CONFIRMED);
    check(denzic_ota_v1_encode_status(&ctx, status, sizeof(status)) == sizeof(status), "status encoded");
    check(memcmp(status, "DOV1", 4u) == 0, "status magic==DOV1");
    check(status[4] == DENZIC_OTA_V1_PROTOCOL_VERSION, "status protocol version");
    check(status[5] == DENZIC_OTA_V1_STATE_COMPLETE, "status state==COMPLETE");
    check(status[7] == DENZIC_OTA_V1_STATUS_FLAG_ACTIVE_LINK_CONFIRMED, "status ACTIVE_LINK_CONFIRMED flag");

    /* re-BEGIN DIFFERENT crc -> abort prior transfer */
    denzic_ota_v1_reset(&ctx);
    control_packet(control, DENZIC_OTA_V1_OP_BEGIN, 8u, 5u, 3u, 0x12345678u);
    denzic_ota_v1_handle_control(&ctx, control, sizeof(control));
    put_u32(data, 0u);
    memcpy(&data[4], "abcde", 5u);
    denzic_ota_v1_handle_data(&ctx, data, sizeof(data));
    control_packet(control, DENZIC_OTA_V1_OP_BEGIN, 8u, 5u, 3u, 0x87654321u);
    check(denzic_ota_v1_handle_control(&ctx, control, sizeof(control)) == 1, "re-BEGIN different CRC accepted (aborts prior)");
    check(ctx.bytes_written == 0u, "bytes_written==0 after abort");
    check(st.abort_count == 1u, "abort_count==1 (interrupted_transfer)");

    /* BAD_MAGIC rejected */
    denzic_ota_v1_reset(&ctx);
    memcpy(control, "BAD!", 4u);
    check(denzic_ota_v1_handle_control(&ctx, control, sizeof(control)) == 0, "BAD_MAGIC control rejected");
    check(ctx.last_error == DENZIC_OTA_V1_ERROR_BAD_MAGIC, "last_error==BAD_MAGIC");

    printf("ota_transfer_supplemental end failures=%d\n", g_failures);
    return g_failures == 0 ? 0 : 1;
}
