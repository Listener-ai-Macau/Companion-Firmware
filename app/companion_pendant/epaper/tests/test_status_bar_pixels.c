#include "screen_menu.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define WIDTH 200u
#define HEIGHT 200u
#define STRIDE (WIDTH / 8u)
#define FRAME_BYTES (STRIDE * HEIGHT)

#define CHECK(condition, message)                 \
    do {                                          \
        if (!(condition)) {                       \
            fprintf(stderr, "%s\n", (message)); \
            return 2;                             \
        }                                         \
    } while (0)

static int next_token(FILE *stream, char *token, size_t token_bytes)
{
    int character;
    size_t length = 0u;

    do {
        character = fgetc(stream);
        if (character == '#') {
            do {
                character = fgetc(stream);
            } while (character != '\n' && character != EOF);
        }
    } while (character == ' ' || character == '\t' ||
             character == '\r' || character == '\n');
    if (character == EOF) {
        return 0;
    }
    do {
        if (length + 1u < token_bytes) {
            token[length++] = (char)character;
        }
        character = fgetc(stream);
    } while (character != EOF && character != ' ' && character != '\t' &&
             character != '\r' && character != '\n');
    token[length] = '\0';
    return 1;
}

static int load_pbm(const char *path, unsigned char frame[FRAME_BYTES])
{
    FILE *stream;
    char token[32];

    if (fopen_s(&stream, path, "rb") != 0 || stream == NULL) {
        return 0;
    }
    if (!next_token(stream, token, sizeof(token)) || strcmp(token, "P4") != 0 ||
        !next_token(stream, token, sizeof(token)) || atoi(token) != (int)WIDTH ||
        !next_token(stream, token, sizeof(token)) || atoi(token) != (int)HEIGHT ||
        fread(frame, 1u, FRAME_BYTES, stream) != FRAME_BYTES) {
        fclose(stream);
        return 0;
    }
    fclose(stream);
    /* Netpbm P4 stores 1=black. The portable framebuffer and SSD1681 transfer
     * buffers store 0=black, so replay the same polarity conversion used by
     * the external asset loader. */
    for (size_t index = 0u; index < FRAME_BYTES; ++index) {
        frame[index] = (unsigned char)~frame[index];
    }
    return 1;
}

static int save_pbm(const char *path, const unsigned char frame[FRAME_BYTES])
{
    FILE *stream;

    if (fopen_s(&stream, path, "wb") != 0 || stream == NULL) {
        return 0;
    }
    if (fprintf(stream, "P4\n%u %u\n", WIDTH, HEIGHT) < 0) {
        fclose(stream);
        return 0;
    }
    for (size_t index = 0u; index < FRAME_BYTES; ++index) {
        const unsigned char pbm_byte = (unsigned char)~frame[index];
        if (fwrite(&pbm_byte, 1u, 1u, stream) != 1u) {
            fclose(stream);
            return 0;
        }
    }
    fclose(stream);
    return 1;
}

static int region_equal(const unsigned char *left, const unsigned char *right,
                        unsigned x0, unsigned y0, unsigned x1, unsigned y1)
{
    unsigned x;
    unsigned y;

    for (y = y0; y < y1; ++y) {
        for (x = x0; x < x1; ++x) {
            const unsigned char mask = (unsigned char)(0x80u >> (x & 7u));
            if ((left[y * STRIDE + x / 8u] & mask) !=
                (right[y * STRIDE + x / 8u] & mask)) {
                return 0;
            }
        }
    }
    return 1;
}

static int region_is_black(const unsigned char *frame,
                           unsigned x0, unsigned y0, unsigned x1, unsigned y1)
{
    unsigned x;
    unsigned y;

    for (y = y0; y < y1; ++y) {
        for (x = x0; x < x1; ++x) {
            if ((frame[y * STRIDE + x / 8u] & (0x80u >> (x & 7u))) != 0u) {
                return 0;
            }
        }
    }
    return 1;
}

static int region_has_white(const unsigned char *frame,
                            unsigned x0, unsigned y0, unsigned x1, unsigned y1)
{
    return !region_is_black(frame, x0, y0, x1, y1);
}

static void contaminate_status_bar(unsigned char *frame)
{
    unsigned x;
    unsigned y;

    for (y = 0u; y < 16u; ++y) {
        for (x = 0u; x < WIDTH; ++x) {
            if (((x * 5u + y * 11u) % 17u) < 8u) {
                frame[y * STRIDE + x / 8u] ^=
                    (unsigned char)(0x80u >> (x & 7u));
            }
        }
    }
}

int main(int argc, char **argv)
{
    unsigned char source[FRAME_BYTES];
    unsigned char connected[FRAME_BYTES];
    unsigned char disconnected[FRAME_BYTES];
    unsigned char unsynced[FRAME_BYTES];
    unsigned char measured_battery[FRAME_BYTES];
    unsigned char contaminated[FRAME_BYTES];
    unsigned char invalid[FRAME_BYTES];
    const unsigned clock_0347 = 0x8000u | (3u << 8u) | 47u;
    char output_path[1024];

    CHECK(argc == 3, "usage: test_status_bar_pixels source.pbm output-dir");
    CHECK(load_pbm(argv[1], source), "could not load the 200x200 product source PBM");
    memcpy(connected, source, sizeof(source));
    memcpy(disconnected, source, sizeof(source));
    memcpy(unsynced, source, sizeof(source));
    memcpy(measured_battery, source, sizeof(source));
    memcpy(contaminated, source, sizeof(source));
    memcpy(invalid, source, sizeof(source));
    contaminate_status_bar(contaminated);

    CHECK(comp_screen_menu_render_status_bar(clock_0347 | (1u << 16u),
                                             connected, sizeof(connected),
                                             WIDTH, HEIGHT),
          "connected status render failed");
    CHECK(comp_screen_menu_render_status_bar(clock_0347,
                                             disconnected, sizeof(disconnected),
                                             WIDTH, HEIGHT),
          "disconnected status render failed");
    CHECK(comp_screen_menu_render_status_bar(1u << 16u,
                                             unsynced, sizeof(unsynced),
                                             WIDTH, HEIGHT),
          "unsynced status render failed");
    CHECK(comp_screen_menu_render_status_bar(
              clock_0347 | (1u << 16u) | (1u << 17u) | (50u << 24u),
              measured_battery, sizeof(measured_battery), WIDTH, HEIGHT),
          "measured battery status render failed");
    CHECK(comp_screen_menu_render_status_bar(clock_0347 | (1u << 16u),
                                             contaminated,
                                             sizeof(contaminated), WIDTH,
                                             HEIGHT),
          "contaminated-source status render failed");
    CHECK(!comp_screen_menu_render_status_bar(0x8000u | (24u << 8u),
                                              invalid, sizeof(invalid),
                                              WIDTH, HEIGHT),
          "invalid 24:00 clock was accepted");
    CHECK(memcmp(invalid, source, sizeof(source)) == 0,
          "rejected clock changed framebuffer pixels");

    CHECK(region_equal(source, connected, 0u, 16u, WIDTH, HEIGHT) &&
              region_equal(source, disconnected, 0u, 16u, WIDTH, HEIGHT) &&
              region_equal(source, unsynced, 0u, 16u, WIDTH, HEIGHT),
          "status renderer changed pixels below y=15");
    CHECK(memcmp(connected, contaminated, sizeof(connected)) == 0,
          "status output still depends on authored top-strip pixels");
    CHECK(!region_equal(connected, disconnected, 148u, 0u, 168u, 16u),
          "connected and disconnected Bluetooth states are identical");
    CHECK(region_has_white(connected, 148u, 0u, 168u, 16u) &&
              region_has_white(disconnected, 148u, 0u, 168u, 16u),
          "a Bluetooth state marker disappeared");
    CHECK(region_has_white(connected, 172u, 0u, WIDTH, 16u) &&
              region_equal(connected, disconnected, 172u, 0u, WIDTH, 16u) &&
              region_equal(connected, unsynced, 172u, 0u, WIDTH, 16u),
          "unmeasured dev-board battery did not produce the stable 80-percent fallback");
    CHECK(region_has_white(measured_battery, 172u, 0u, WIDTH, 16u) &&
              !region_equal(connected, measured_battery,
                            172u, 0u, WIDTH, 16u),
          "a real measured battery did not produce a distinct glyph");
    CHECK(region_is_black(connected, 40u, 0u, 146u, 16u) &&
              region_is_black(connected, 166u, 0u, 172u, 16u),
          "canonical status bar contains unintended white leaks");
    CHECK(!region_equal(source, connected, 0u, 0u, 40u, 16u),
          "valid clock did not replace the authored time field");
    CHECK(!region_equal(connected, unsynced, 0u, 0u, 40u, 16u),
          "unknown-time state is indistinguishable from a valid clock");

    CHECK(sprintf_s(output_path, sizeof(output_path), "%s\\connected-03-47.pbm", argv[2]) > 0 &&
              save_pbm(output_path, connected),
          "failed to save connected preview");
    CHECK(sprintf_s(output_path, sizeof(output_path), "%s\\disconnected-03-47.pbm", argv[2]) > 0 &&
              save_pbm(output_path, disconnected),
          "failed to save disconnected preview");
    CHECK(sprintf_s(output_path, sizeof(output_path), "%s\\connected-unknown-clock.pbm", argv[2]) > 0 &&
              save_pbm(output_path, unsynced),
          "failed to save unsynced preview");
    CHECK(sprintf_s(output_path, sizeof(output_path), "%s\\connected-measured-battery-50.pbm", argv[2]) > 0 &&
              save_pbm(output_path, measured_battery),
          "failed to save measured-battery preview");

    puts("PASS status_bar_pixels canonical_top_strip=1 compact_clock=1 source_independent=1 below_y16_unchanged=1 ble_connected_and_disconnected=1 nucleo_screen_fallback_80=1 gatt_battery_unavailable=1 measured_battery_visible=1 invalid_clock_rejected=1");
    return 0;
}
