#include "companion_browser_interaction_contract.h"
#include "companion_renderer.h"
#include "companion_resources.h"
#include "companion_wba_menu_geometry.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

enum {
    FRAME_BYTES = 5000u,
    PATH_BYTES = 1024u,
};

typedef struct {
    comp_runtime_resources_t *resources;
    const char *override_state;
    char requested_state[128];
    char rendered_state[128];
} preview_reader_t;

typedef struct {
    const char *name;
    const char *purpose;
    uint8_t locale;
    uint8_t screen;
    uint8_t page;
    uint8_t variant;
    uint8_t feedback_item;
    uint8_t feedback_phase;
    uint32_t status_packed;
    uint16_t recording_count;
    uint16_t recording_storage_kib;
    denzic_audio_recording_state_v1_t recording;
    uint32_t recording_elapsed_seconds;
    comp_runtime_result_t last_result;
} fixture_t;

static uint8_t *load_file(const char *path, size_t *size)
{
    FILE *file;
    long length;
    uint8_t *data;

    if (path == NULL || size == NULL || (file = fopen(path, "rb")) == NULL) {
        return NULL;
    }
    if (fseek(file, 0, SEEK_END) != 0 || (length = ftell(file)) <= 0 ||
        fseek(file, 0, SEEK_SET) != 0) {
        fclose(file);
        return NULL;
    }
    data = (uint8_t *)malloc((size_t)length);
    if (data == NULL || fread(data, 1u, (size_t)length, file) != (size_t)length) {
        free(data);
        fclose(file);
        return NULL;
    }
    fclose(file);
    *size = (size_t)length;
    return data;
}

static bool preview_read_state(void *context,
                               const char *requested,
                               uint8_t frame[FRAME_BYTES])
{
    preview_reader_t *reader = (preview_reader_t *)context;
    const char *selected;

    if (reader == NULL || reader->resources == NULL || requested == NULL ||
        frame == NULL) {
        return false;
    }
    selected = reader->override_state != NULL ? reader->override_state : requested;
    if (snprintf(reader->requested_state, sizeof(reader->requested_state), "%s",
                 requested) < 0 ||
        snprintf(reader->rendered_state, sizeof(reader->rendered_state), "%s",
                 selected) < 0) {
        return false;
    }
    return comp_runtime_resources_read(reader->resources, selected, frame);
}

static uint32_t fixture_status(bool clock_valid,
                               uint8_t hour,
                               uint8_t minute,
                               bool connected,
                               bool battery_valid,
                               uint8_t battery_percent)
{
    uint32_t packed = ((uint32_t)battery_percent << 24u);
    if (clock_valid) {
        packed |= 0x8000u | ((uint32_t)hour << 8u) | minute;
    }
    if (connected) packed |= 1u << 16u;
    if (battery_valid) packed |= 1u << 17u;
    return packed;
}

static void apply_variant(comp_screen_menu_t *menu, uint8_t screen, uint8_t variant)
{
    static const uint8_t recording_limits[4] = {30u, 15u, 60u, 0u};
    static const int16_t timezones[3] = {480, 0, -300};
    static const uint8_t sleep_minutes[4] = {3u, 5u, 0u, 1u};
    uint8_t index;

    if (menu == NULL) return;
    switch (screen) {
    case 1u:
        menu->browser.silent_auto_stop = (variant & 1u) == 0u;
        index = (uint8_t)((variant >> 1u) & 3u);
        menu->browser.recording_limit_minutes = recording_limits[index];
        menu->browser.recorder_profile = (uint8_t)((variant >> 3u) & 1u);
        menu->browser.recording_gesture = (uint8_t)((variant >> 4u) & 1u);
        break;
    case 2u:
        menu->browser.clock_24_hour = variant == 0u;
        break;
    case 3u:
        menu->browser.link_connected = variant < 2u;
        menu->browser.auto_reconnect = (variant & 1u) == 0u;
        break;
    case 4u:
        menu->browser.time_zone_offset_minutes = timezones[variant / 3u];
        menu->browser.quiet_hours = (uint8_t)(variant % 3u);
        break;
    case 5u:
        menu->browser.recording_gesture = variant;
        break;
    case 8u:
        menu->browser.natural_blink = (variant & 1u) == 0u;
        menu->browser.gaze_follow = ((variant >> 1u) & 1u) == 0u;
        index = (uint8_t)((variant >> 2u) % 3u);
        menu->browser.interaction_level = index == 0u
                                               ? COMP_SCREEN_MENU_INTERACTION_STANDARD
                                               : index == 1u
                                                     ? COMP_SCREEN_MENU_INTERACTION_LIVELY
                                                     : COMP_SCREEN_MENU_INTERACTION_QUIET;
        menu->browser.recording_gesture = (uint8_t)(variant / 12u);
        break;
    case 9u:
    case 11u:
        menu->browser.recording_count = variant == 1u ? 0u : 3u;
        break;
    case 10u:
        menu->browser.auto_sleep_minutes = sleep_minutes[variant];
        break;
    default:
        break;
    }
}

static bool render_fixture(comp_runtime_resources_t *resources,
                           const fixture_t *fixture,
                           uint32_t token,
                           const char *raw_directory,
                           FILE *manifest)
{
    comp_runtime_renderer_t renderer;
    comp_runtime_frame_t frame_request = {0};
    preview_reader_t reader = {0};
    uint8_t frame[FRAME_BYTES];
    char override_state[128] = {0};
    char output_path[PATH_BYTES];
    FILE *output;
    uint8_t actual_variant;

    comp_screen_menu_init(&frame_request.menu);
    frame_request.menu.view = (comp_screen_menu_view_t)(
        COMP_SCREEN_MENU_VIEW_BROWSER_HOME + fixture->screen);
    frame_request.menu.language = (comp_screen_menu_language_t)fixture->locale;
    frame_request.menu.home_page = fixture->page;
    frame_request.menu.browser.recording_count = fixture->recording_count;
    frame_request.menu.browser.recording_storage_kb = fixture->recording_storage_kib;
    frame_request.menu.browser.battery_percent =
        (fixture->status_packed & (1u << 17u)) != 0u
            ? (uint8_t)(fixture->status_packed >> 24u)
            : 0xFFu;
    frame_request.menu.browser.link_connected =
        (fixture->status_packed & (1u << 16u)) != 0u;
    apply_variant(&frame_request.menu, fixture->screen, fixture->variant);
    actual_variant = comp_screen_menu_browser_variant(&frame_request.menu);
    if (actual_variant != fixture->variant) {
        fprintf(stderr, "variant mismatch for %s: expected=%u actual=%u\n",
                fixture->name, (unsigned)fixture->variant,
                (unsigned)actual_variant);
        return false;
    }

    if (fixture->feedback_phase != 0u &&
        !companion_browser_menu_state_id_format(
            override_state, sizeof(override_state), fixture->locale,
            fixture->screen, fixture->page, fixture->feedback_item,
            fixture->feedback_phase, fixture->variant)) {
        fprintf(stderr, "invalid feedback state for %s\n", fixture->name);
        return false;
    }

    reader.resources = resources;
    reader.override_state = fixture->feedback_phase == 0u ? NULL : override_state;
    comp_runtime_renderer_init(&renderer, preview_read_state, &reader);
    frame_request.token = token;
    frame_request.family = COMP_BROWSER_FAMILY_CALM;
    frame_request.surface = COMP_SCREEN_SURFACE_MENU;
    frame_request.status_packed = fixture->status_packed;
    frame_request.recording = fixture->recording;
    frame_request.recording_elapsed_seconds = fixture->recording_elapsed_seconds;
    frame_request.last_result = fixture->last_result;
    if (!comp_runtime_renderer_render(&renderer, &frame_request, frame) ||
        !comp_runtime_renderer_complete(&renderer, token, true)) {
        fprintf(stderr, "renderer failed for %s\n", fixture->name);
        return false;
    }

    if (snprintf(output_path, sizeof(output_path), "%s/%s.bin", raw_directory,
                 fixture->name) < 0 ||
        (output = fopen(output_path, "wb")) == NULL) {
        return false;
    }
    if (fwrite(frame, 1u, sizeof(frame), output) != sizeof(frame) ||
        fclose(output) != 0) {
        return false;
    }

    fprintf(manifest,
            "%s\t%s\t%u\t%u\t%u\t%u\t%u\t%u\t%s\t%s\t0x%08lX\t%u\t%u\t%u\t%lu\t%u\t%u\n",
            fixture->name, fixture->purpose, (unsigned)fixture->locale,
            (unsigned)fixture->screen, (unsigned)fixture->page,
            (unsigned)fixture->variant, (unsigned)fixture->feedback_item,
            (unsigned)fixture->feedback_phase, reader.requested_state,
            reader.rendered_state, (unsigned long)fixture->status_packed,
            (unsigned)fixture->recording_count,
            (unsigned)fixture->recording_storage_kib,
            (unsigned)fixture->recording,
            (unsigned long)fixture->recording_elapsed_seconds,
            (fixture->status_packed & (1u << 17u)) != 0u ? 1u : 0u,
            (unsigned)(uint8_t)(fixture->status_packed >> 24u));
    return true;
}

static fixture_t base_fixture(const char *name,
                              const char *purpose,
                              uint8_t locale,
                              uint8_t screen,
                              uint8_t page)
{
    fixture_t fixture = {
        .name = name,
        .purpose = purpose,
        .locale = locale,
        .screen = screen,
        .page = page,
        .variant = 0u,
        .feedback_item = 255u,
        .feedback_phase = 0u,
        .status_packed = 0u,
        .recording_count = 3u,
        .recording_storage_kib = 1536u,
        .recording = DENZIC_AUDIO_RECORDING_STATE_IDLE,
        .recording_elapsed_seconds = 0u,
        .last_result = COMP_RUNTIME_OK,
    };
    fixture.status_packed = fixture_status(true, 9u, 41u, true, false, 0xFFu);
    return fixture;
}

static bool append_fixture(fixture_t *fixtures,
                           size_t capacity,
                           size_t *count,
                           fixture_t fixture)
{
    if (fixtures == NULL || count == NULL || *count >= capacity) return false;
    fixtures[(*count)++] = fixture;
    return true;
}

int main(int argc, char **argv)
{
    static const char *const locale_names[3] = {"en", "zh_cn", "zh_tw"};
    static const char *const screen_names[13] = {
        "home", "recording", "display", "connection", "preferences",
        "record-gesture", "language", "about", "interaction", "storage",
        "power", "clear-recordings", "restore-defaults",
    };
    enum { PREVIEW_CAPACITY = 192u };
    fixture_t fixtures[PREVIEW_CAPACITY];
    size_t fixture_count = 0u;
    size_t image_size = 0u;
    uint8_t *image;
    comp_asset_store_t store;
    comp_runtime_resources_t resources;
    FILE *manifest;
    char manifest_path[PATH_BYTES];
    char names[PREVIEW_CAPACITY][96];
    char resource_id[65];
    uint32_t token = 1u;

    if (argc != 3) {
        fprintf(stderr, "usage: render_wba_menu_review <ui-partition.bin> <raw-output-dir>\n");
        return 2;
    }
    image = load_file(argv[1], &image_size);
    if (image == NULL ||
        !comp_asset_store_init_memory(&store, COMP_ASSET_STORAGE_HOST_STREAM,
                                      image, image_size) ||
        !comp_runtime_resources_mount(&resources, &store)) {
        fprintf(stderr, "failed to mount UI partition\n");
        free(image);
        return 3;
    }

    for (uint8_t locale = 0u; locale < 3u; ++locale) {
        for (uint8_t screen = 0u; screen < 13u; ++screen) {
            (void)snprintf(names[fixture_count], sizeof(names[fixture_count]),
                           "%s-%02u-%s-p0", locale_names[locale],
                           (unsigned)screen, screen_names[screen]);
            if (!append_fixture(fixtures, PREVIEW_CAPACITY, &fixture_count,
                                base_fixture(names[fixture_count], "catalog",
                                             locale, screen, 0u))) {
                free(image);
                return 4;
            }
        }
        (void)snprintf(names[fixture_count], sizeof(names[fixture_count]),
                       "%s-00-home-p1", locale_names[locale]);
        if (!append_fixture(fixtures, PREVIEW_CAPACITY, &fixture_count,
                            base_fixture(names[fixture_count], "home-page-2",
                                         locale, 0u, 4u))) {
            free(image);
            return 4;
        }

        /* Review every complete page with the same default settings.
         * The retained special fixtures deliberately change settings and
         * cannot stand in for a continuous view of a submenu. */
        for (uint8_t screen = 1u; screen < 13u; ++screen) {
            uint8_t rows = companion_browser_menu_item_counts[screen];
            for (uint8_t page = COMP_WBA_MENU_VISIBLE_ROWS; page < rows;
                 page = (uint8_t)(page + COMP_WBA_MENU_VISIBLE_ROWS)) {
                (void)snprintf(names[fixture_count], sizeof(names[fixture_count]),
                               "%s-%02u-%s-p%u", locale_names[locale],
                               (unsigned)screen, screen_names[screen], (unsigned)page);
                if (!append_fixture(fixtures, PREVIEW_CAPACITY, &fixture_count,
                                    base_fixture(names[fixture_count], "catalog-scroll",
                                                 locale, screen, page))) {
                    free(image);
                    return 4;
                }
            }
        }

#define ADD_SPECIAL(suffix, purpose_text, screen_value, page_value)             \
        do {                                                                    \
            fixture_t special;                                                  \
            (void)snprintf(names[fixture_count], sizeof(names[fixture_count]),   \
                           "%s-%s", locale_names[locale], suffix);              \
            special = base_fixture(names[fixture_count], purpose_text, locale,  \
                                   screen_value, page_value);                   \
            if (!append_fixture(fixtures, PREVIEW_CAPACITY, &fixture_count, special)) { \
                free(image);                                                    \
                return 4;                                                       \
            }                                                                   \
        } while (0)

        ADD_SPECIAL("recording-active", "dynamic-recording-status", 1u, 0u);
        fixtures[fixture_count - 1u].recording =
            DENZIC_AUDIO_RECORDING_STATE_RECORDING;
        fixtures[fixture_count - 1u].recording_elapsed_seconds = 754u;
        fixtures[fixture_count - 1u].status_packed =
            fixture_status(true, 10u, 5u, true, true, 73u);

        ADD_SPECIAL("recording-failed", "dynamic-recording-failure", 1u, 0u);
        fixtures[fixture_count - 1u].last_result = COMP_RUNTIME_BACKEND_FAILED;

        ADD_SPECIAL("recording-settings-p1", "page-and-settings", 1u, 4u);
        fixtures[fixture_count - 1u].variant = 31u;

        ADD_SPECIAL("connection-disconnected", "disconnected-status", 3u, 0u);
        fixtures[fixture_count - 1u].variant = 3u;
        fixtures[fixture_count - 1u].status_packed =
            fixture_status(false, 0u, 0u, false, false, 0xFFu);

        ADD_SPECIAL("interaction-scroll-last", "setting-variant", 8u, 4u);
        fixtures[fixture_count - 1u].variant = 23u;

        ADD_SPECIAL("storage-live-values", "dynamic-storage-overlay", 9u, 0u);
        fixtures[fixture_count - 1u].recording_count = 7u;
        fixtures[fixture_count - 1u].recording_storage_kib = 7168u;

        ADD_SPECIAL("power-measured", "measured-battery-overlay", 10u, 0u);
        fixtures[fixture_count - 1u].variant = 1u;
        fixtures[fixture_count - 1u].status_packed =
            fixture_status(true, 16u, 28u, true, true, 73u);

        for (uint8_t phase = 1u; phase <= 3u; ++phase) {
            static const char *const phase_names[4] = {
                "normal", "ack", "processing", "result",
            };
            fixture_t feedback;
            (void)snprintf(names[fixture_count], sizeof(names[fixture_count]),
                           "%s-clear-%s", locale_names[locale], phase_names[phase]);
            feedback = base_fixture(names[fixture_count], "press-feedback-clear",
                                    locale, 11u, 0u);
            feedback.feedback_item = 1u;
            feedback.feedback_phase = phase;
            if (!append_fixture(fixtures, PREVIEW_CAPACITY, &fixture_count, feedback)) {
                free(image);
                return 4;
            }

            (void)snprintf(names[fixture_count], sizeof(names[fixture_count]),
                           "%s-restore-%s", locale_names[locale], phase_names[phase]);
            feedback = base_fixture(names[fixture_count], "press-feedback-restore",
                                    locale, 12u, 0u);
            feedback.feedback_item = 1u;
            feedback.feedback_phase = phase;
            if (!append_fixture(fixtures, PREVIEW_CAPACITY, &fixture_count, feedback)) {
                free(image);
                return 4;
            }
        }
#undef ADD_SPECIAL
    }

    if (snprintf(manifest_path, sizeof(manifest_path), "%s/frames.tsv", argv[2]) < 0 ||
        (manifest = fopen(manifest_path, "wb")) == NULL) {
        free(image);
        return 5;
    }
    fprintf(manifest,
            "name\tpurpose\tlocale\tscreen\tpage\tvariant\tfeedback_item\tfeedback_phase\trequested_state\trendered_state\tstatus_packed\trecording_count\trecording_storage_kib\trecording_state\trecording_elapsed_seconds\tbattery_valid\tbattery_percent_raw\n");
    for (size_t index = 0u; index < fixture_count; ++index) {
        if (!render_fixture(&resources, &fixtures[index], token++, argv[2],
                            manifest)) {
            fclose(manifest);
            free(image);
            return 6;
        }
    }
    if (fclose(manifest) != 0) {
        free(image);
        return 7;
    }

    for (size_t index = 0u; index < 32u; ++index) {
        (void)snprintf(&resource_id[index * 2u], 3u, "%02X",
                       resources.generation.root.resource_id[index]);
    }
    resource_id[64] = '\0';
    printf("IDENTITY\tgeneration=%lu\tresource_id=%s\tbase_pack_size=%lu\tentry_count=%u\tpartition_bytes=%lu\n",
           (unsigned long)resources.generation.root.generation, resource_id,
           (unsigned long)resources.generation.root.base_pack_size,
           (unsigned)resources.generation.entry_count,
           (unsigned long)image_size);
    printf("PASS_NATIVE_WBA_MENU_REVIEW\tframes=%lu\tlocales=3\tscreens=13\thome_pages=2\n",
           (unsigned long)fixture_count);
    free(image);
    return 0;
}
