#include "screen_menu.h"
#include "screen_framebuffer.h"

#include <stdio.h>
#include <string.h>

#define CHECK(c) do { if (!(c)) { \
    fprintf(stderr, "FAIL:%d: %s\n", __LINE__, #c); return 1; } } while (0)
static bool ink(const uint8_t *frame, unsigned x, unsigned y)
{ return (frame[y * 25u + x / 8u] & (0x80u >> (x % 8u))) == 0u; }
static bool same_region(const uint8_t *a, const uint8_t *b, unsigned x0, unsigned x1)
{
    for (unsigned y = 0; y < 16u; ++y)
        for (unsigned x = x0; x < x1; ++x)
            if (ink(a, x, y) != ink(b, x, y)) return false;
    return true;
}
int main(void)
{
    uint8_t frame[5000], expected[5000], unknown[5000], zero[5000];
    const uint32_t flags = COMP_SCREEN_STATUS_REQUIRE_MEASURED_BATTERY | 0x8000u | (10u << 8) | 28u;
    static const uint8_t percent_rows[7] = {0x19u,0x19u,0x02u,0x04u,0x08u,0x13u,0x13u};
    for (unsigned percent = 0; percent <= 100u; ++percent) {
        const unsigned fill = (14u * percent + 99u) / 100u;
        memset(frame, 0x5A, sizeof(frame));
        CHECK(comp_screen_menu_render_status_bar(flags | (1u << 17) | (percent << 24), frame, 5000u, 200u, 200u));
        for (unsigned y = 6; y < 11u; ++y)
            for (unsigned x = 177; x < 191u; ++x)
                CHECK(ink(frame, x, y) == (x - 177u < fill));
        /* '%' was previously absent from the small framebuffer alphabet. */
        for (unsigned y = 0; y < 7u; ++y)
            for (unsigned x = 0; x < 5u; ++x)
                CHECK(ink(frame, 159u + x, 5u + y) == ((percent_rows[y] & (0x10u >> x)) != 0u));
        for (unsigned i = 400; i < 5000u; ++i) CHECK(frame[i] == 0x5Au);
        if (percent == 0u) memcpy(zero, frame, 5000u);
    }
    memset(unknown, 0x5A, sizeof(unknown));
    CHECK(comp_screen_menu_render_status_bar(flags, unknown, 5000u, 200u, 200u));
    CHECK(!same_region(unknown, zero, 141u, 165u));
    CHECK(!same_region(unknown, zero, 177u, 191u));
    CHECK(ink(unknown, 155u, 8u) && ink(unknown, 161u, 8u));

    /* Out-of-range percentages use exactly the unknown product display. */
    for (unsigned percent = 101; percent <= 255u; ++percent) {
        memset(frame, 0x5A, sizeof(frame));
        CHECK(comp_screen_menu_render_status_bar(flags | (1u << 17) | (percent << 24), frame, 5000u, 200u, 200u));
        CHECK(!memcmp(frame, unknown, 5000u));
    }
    /* Clearing the whole rail removes old digits when 100% becomes 7%. */
    memset(frame, 0x5A, sizeof(frame)); memset(expected, 0x5A, sizeof(expected));
    CHECK(comp_screen_menu_render_status_bar(flags | (1u << 17) | (100u << 24), frame, 5000u, 200u, 200u));
    CHECK(comp_screen_menu_render_status_bar(flags | (1u << 17) | (7u << 24), frame, 5000u, 200u, 200u));
    CHECK(comp_screen_menu_render_status_bar(flags | (1u << 17) | (7u << 24), expected, 5000u, 200u, 200u));
    CHECK(!memcmp(frame, expected, 5000u));
    CHECK(same_region(frame, zero, 0u, 141u));

    CHECK(comp_screen_menu_render_status_bar(flags | COMP_SCREEN_STATUS_EXTERNAL_POWER, frame, 5000u, 200u, 200u));
    CHECK(same_region(frame, unknown, 141u, 165u));
    CHECK(same_region(frame, unknown, 175u, 196u));
    CHECK(comp_screen_menu_render_status_bar(flags | COMP_SCREEN_STATUS_CHARGER_FAULT, expected, 5000u, 200u, 200u));
    CHECK(ink(expected, 169u, 5u) && ink(expected, 169u, 11u));
    CHECK(same_region(expected, unknown, 141u, 165u));
    puts("PASS_BATTERY_STATUS_PROGRESS: 0..100 fill and percent glyph, 101..255 unknown, stale digits erased, clock/link and y>=16 preserved, charger never invents SOC; hardware NOT_RUN");
    return 0;
}
