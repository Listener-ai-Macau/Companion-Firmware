#include "ssd1681_wba.h"

#include <stdio.h>
#include <string.h>

#define CHECK(c) do { if (!(c)) { \
    fprintf(stderr, "FAIL:%d: %s\n", __LINE__, #c); return 1; } } while (0)

/* Digital command/address/RAM model only. It does not model electrophoretic
 * drive, translated electrical signals, power, or prove physical ghosting. */
typedef struct {
    uint8_t ram[2][5000];
    uint8_t command, entry, control, x_start, x_end, x;
    uint16_t y_start, y_end, y;
    uint32_t now, busy_until, transfers_this_poll, visible, full, plane_writes[2];
    uint32_t wave_writes[2], activated_this_operation;
    uint32_t injected_ms;
    bool fail_post_previous, inject_write_busy, injected, stuck_write_busy;
    const uint8_t *expected_old, *expected_current;
    comp_ssd1681_wba_window_t expected_window;
} fixture_t;

static bool same_window(const comp_ssd1681_wba_window_t *a,
                        const comp_ssd1681_wba_window_t *b)
{
    return a->x_start_byte == b->x_start_byte && a->x_end_byte == b->x_end_byte &&
           a->y_start == b->y_start && a->y_end == b->y_end;
}
static bool plane_equals(const fixture_t *f, unsigned plane, const uint8_t *frame)
{
    for (unsigned y = 0; y < 200u; ++y)
        if (memcmp(f->ram[plane] + (199u - y) * 25u, frame + y * 25u, 25u)) return false;
    return true;
}
static comp_ssd1681_wba_window_t dirty(const uint8_t *a, const uint8_t *b)
{
    comp_ssd1681_wba_window_t w = {24u, 0u, 199u, 0u};
    for (unsigned y = 0; y < 200u; ++y) for (unsigned x = 0; x < 25u; ++x) {
        if (a[y * 25u + x] == b[y * 25u + x]) continue;
        if (x < w.x_start_byte) w.x_start_byte = (uint8_t)x;
        if (x > w.x_end_byte) w.x_end_byte = (uint8_t)x;
        if (y < w.y_start) w.y_start = (uint16_t)y;
        if (y > w.y_end) w.y_end = (uint16_t)y;
    }
    return w;
}
static bool transfer(void *context, bool data, const uint8_t *bytes, uint16_t size)
{
    fixture_t *f = context;
    ++f->transfers_this_poll;
    if (!bytes || !size) return false;
    if ((int32_t)(f->now - f->busy_until) < 0) {
        fputs("SPI_WRITE_WHILE_BUSY\n", stderr); return false;
    }
    if (f->injected && f->now - f->injected_ms < 55u) {
        fputs("SPI_WRITE_BEFORE_STABLE_READY\n", stderr); return false;
    }
    if (!data) {
        if (size != 1u) return false;
        f->command = bytes[0];
        if (f->command == 0x12u) {
            /* Datasheet SWRESET restores parameters and preserves RAM. */
            f->entry = 3u; f->control = 0xFFu;
            f->busy_until = f->now + 30u;
        }
        if (f->command == 0x20u) {
            f->busy_until = f->now + 30u;
            if (f->control & 4u) {
                comp_ssd1681_wba_window_t actual = {f->x_start, f->x_end,
                    (uint16_t)(199u - f->y_start), (uint16_t)(199u - f->y_end)};
                if (!same_window(&actual, &f->expected_window)) {
                    fprintf(stderr, "ACTIVATION_WINDOW_MISMATCH expected x=%u..%u y=%u..%u; got x=%u..%u y=%u..%u\n",
                        (unsigned)f->expected_window.x_start_byte, (unsigned)f->expected_window.x_end_byte,
                        (unsigned)f->expected_window.y_start, (unsigned)f->expected_window.y_end,
                        (unsigned)actual.x_start_byte, (unsigned)actual.x_end_byte,
                        (unsigned)actual.y_start, (unsigned)actual.y_end);
                    return false;
                }
                if (!plane_equals(f, 0u, f->expected_current) ||
                    !plane_equals(f, 1u, f->expected_old)) {
                    fputs("ACTIVATION_RAM_PAIR_MISMATCH\n", stderr); return false;
                }
                ++f->visible; ++f->activated_this_operation;
                if (f->control == 0xF7u) ++f->full;
            }
        }
        return true;
    }
    if (f->command == 0x24u || f->command == 0x26u) {
        const unsigned plane = f->command == 0x26u ? 1u : 0u;
        if (f->fail_post_previous && plane == 1u && f->activated_this_operation) return false;
        for (unsigned i = 0; i < size; ++i) {
            if (f->x < f->x_start || f->x > f->x_end || f->y > 199u || f->entry != 1u) return false;
            f->ram[plane][f->y * 25u + f->x] = bytes[i]; ++f->plane_writes[plane];
            const unsigned logical_y = 199u - f->y;
            if (f->x <= COMP_SSD1681_WBA_RECORDING_CONTROLLER_X_BYTE_MAX &&
                logical_y >= COMP_SSD1681_WBA_RECORDING_CONTROLLER_Y_MIN &&
                logical_y <= COMP_SSD1681_WBA_RECORDING_CONTROLLER_Y_MAX) ++f->wave_writes[plane];
            if (f->x == f->x_end) {
                f->x = f->x_start;
                f->y = f->y == f->y_end ? f->y_start : (uint16_t)(f->y - 1u);
            } else ++f->x;
        }
        return true;
    }
    switch (f->command) {
    case 0x11u: if (size != 1u) return false; f->entry = bytes[0]; break;
    case 0x22u: if (size != 1u) return false; f->control = bytes[0]; break;
    case 0x44u: if (size != 2u) return false; f->x_start = bytes[0]; f->x_end = bytes[1]; break;
    case 0x45u:
        if (size != 4u) return false;
        f->y_start = (uint16_t)(bytes[0] | ((uint16_t)bytes[1] << 8));
        f->y_end = (uint16_t)(bytes[2] | ((uint16_t)bytes[3] << 8)); break;
    case 0x4Eu: if (size != 1u) return false; f->x = bytes[0]; break;
    case 0x4Fu: if (size != 2u) return false; f->y = (uint16_t)(bytes[0] | ((uint16_t)bytes[1] << 8)); break;
    default: break;
    }
    return true;
}
static bool busy(void *context)
{ const fixture_t *f = context; return (int32_t)(f->now - f->busy_until) < 0; }
static uint32_t tick(void *context) { return ((fixture_t *)context)->now; }
static bool drive(comp_ssd1681_wba_t *driver, fixture_t *f)
{
    for (unsigned i = 0; i < 8000u; ++i) {
        if (f->inject_write_busy && !f->injected && f->command == 0x24u &&
            f->plane_writes[0] >= 4u && !f->activated_this_operation) {
            f->injected = true; f->injected_ms = f->now;
            f->busy_until = f->now + (f->stuck_write_busy ? 6000u : 35u);
        }
        f->transfers_this_poll = 0u;
        const comp_ssd1681_wba_status_t status = comp_ssd1681_wba_poll(driver);
        if (f->transfers_this_poll > 2u) return false;
        if (status != COMP_SSD1681_WBA_ACTIVE) return status == COMP_SSD1681_WBA_COMPLETE;
        ++f->now;
    }
    return false;
}
static void expect(fixture_t *f, const uint8_t *old, const uint8_t *current,
                   comp_ssd1681_wba_window_t window)
{
    f->expected_old = old; f->expected_current = current; f->expected_window = window;
    f->activated_this_operation = 0u;
    memset(f->plane_writes, 0, sizeof(f->plane_writes));
    memset(f->wave_writes, 0, sizeof(f->wave_writes));
}
int main(void)
{
    fixture_t f = {.now = 100u}; comp_ssd1681_wba_t panel;
    uint8_t previous[5000], current[5000];
    const comp_ssd1681_wba_window_t full = {0u, 24u, 0u, 199u};
    const comp_ssd1681_wba_window_t recording = {
        COMP_SSD1681_WBA_RECORDING_CONTROLLER_X_BYTE_MIN,
        COMP_SSD1681_WBA_RECORDING_CONTROLLER_X_BYTE_MAX,
        COMP_SSD1681_WBA_RECORDING_CONTROLLER_Y_MIN,
        COMP_SSD1681_WBA_RECORDING_CONTROLLER_Y_MAX};
    const comp_ssd1681_wba_config_t config = {
        .transfer = transfer, .is_busy = busy, .now_ms = tick, .context = &f,
        .reset_mode = COMP_SSD1681_WBA_RESET_SOFTWARE_ONLY,
        .payload_chunk_bytes = 128u, .busy_timeout_ms = 5000u, .partial_limit = UINT8_MAX};
    CHECK(comp_ssd1681_wba_init(&panel, &config));
    memset(previous, 255, sizeof(previous)); memcpy(current, previous, sizeof(current));
    current[22u * 25u + 3u] = 0u; /* Unchanged microphone in later sparse transactions. */
    current[100u * 25u + 10u] = 0x03u;
    expect(&f, previous, current, full);
    CHECK(comp_ssd1681_wba_start_full(&panel, previous, current, 5000u));
    CHECK(drive(&panel, &f) && f.full == 1u && f.activated_this_operation == 1u);
    CHECK(plane_equals(&f, 0u, current) && plane_equals(&f, 1u, current));
    memcpy(previous, current, 5000u);

    /* An ordinary local pair keeps its local activation and complete post-sync. */
    current[98u * 25u + 9u] ^= 0x80u; current[101u * 25u + 12u] ^= 0x01u;
    comp_ssd1681_wba_window_t local = dirty(previous, current);
    expect(&f, previous, current, local);
    f.inject_write_busy = true;
    CHECK(comp_ssd1681_wba_start_partial_pair(&panel, previous, current, 5000u, &local));
    CHECK(drive(&panel, &f) && f.control == 0xFFu && f.activated_this_operation == 1u);
    CHECK(f.injected);
    f.inject_write_busy = false;
    CHECK(plane_equals(&f, 0u, current) && plane_equals(&f, 1u, current));
    memcpy(previous, current, 5000u);

    /* Two disjoint recording runs, then mixed face/status/recording, then
     * ordinary-only recording, then stop removal. Activation must retain the
     * union, rather than whichever write run was visited last. */
    for (unsigned scenario = 0; scenario < 4u; ++scenario) {
        if (scenario == 0u) { current[23u * 25u + 1u] ^= 0xC0u; current[25u * 25u + 4u] ^= 0x0Fu; }
        if (scenario == 1u) { current[24u * 25u + 2u] ^= 0x55u; current[95u * 25u + 12u] ^= 0x30u; current[196u * 25u + 20u] ^= 0x40u; }
        if (scenario == 2u) { current[88u * 25u + 11u] ^= 0x7Fu; current[193u * 25u + 19u] ^= 0x08u; }
        if (scenario == 3u) { current[23u * 25u + 1u] = 255u; current[25u * 25u + 4u] = 255u; current[24u * 25u + 2u] = 255u; current[100u * 25u + 10u] ^= 0x03u; }
        local = dirty(previous, current); expect(&f, previous, current, local);
        CHECK(comp_ssd1681_wba_start_recording_partial(&panel, previous, current, 5000u, &recording));
        CHECK(drive(&panel, &f) && f.control == 0xCFu && f.activated_this_operation == 1u);
        CHECK(plane_equals(&f, 0u, current) && plane_equals(&f, 1u, current));
        CHECK(panel.baseline_valid && f.full == 1u);
        if (scenario == 0u) CHECK(f.wave_writes[0] == 4u && f.wave_writes[1] == 4u);
        memcpy(previous, current, 5000u);
    }

    /* A failed post-visible previous-plane write cannot qualify the next base. */
    current[24u * 25u + 2u] ^= 0x55u;
    local = dirty(previous, current); expect(&f, previous, current, local); f.fail_post_previous = true;
    CHECK(comp_ssd1681_wba_start_recording_partial(&panel, previous, current, 5000u, &recording));
    CHECK(!drive(&panel, &f) && panel.error == COMP_SSD1681_WBA_ERROR_TRANSPORT && !panel.baseline_valid);
    CHECK(f.activated_this_operation == 1u && f.full == 1u);

    /* Restore once, then an unexpected stuck BUSY during a RAM write must
     * expire without another byte or a visible activation being issued. */
    f.fail_post_previous = false; expect(&f, previous, current, full);
    CHECK(comp_ssd1681_wba_start_full(&panel, previous, current, 5000u));
    CHECK(drive(&panel, &f) && panel.baseline_valid);
    memcpy(previous, current, 5000u);
    current[98u * 25u + 9u] ^= 0x80u; current[99u * 25u + 12u] ^= 0x01u;
    local = dirty(previous, current); expect(&f, previous, current, local);
    f.inject_write_busy = true; f.injected = false; f.stuck_write_busy = true;
    CHECK(comp_ssd1681_wba_start_partial_pair(&panel, previous, current, 5000u, &local));
    CHECK(!drive(&panel, &f) && panel.error == COMP_SSD1681_WBA_ERROR_BUSY_TIMEOUT && !panel.baseline_valid);
    CHECK(f.injected && f.activated_this_operation == 0u);
    puts("PASS_ACTIVATION_WINDOW_AND_RAM: recording mixed/stop union; true old/current planes; sparse microphone; one activation; late BUSY pauses SPI until stable-ready and stuck BUSY expires; post-write failure invalidates base; hardware NOT_RUN");
    return 0;
}
