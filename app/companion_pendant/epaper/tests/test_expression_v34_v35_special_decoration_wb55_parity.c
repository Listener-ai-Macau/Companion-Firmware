#include "asset_store.h"
#include "expression_rig.h"
#include "expression_rig_asset_pack.h"
#include "expression_rig_asset_pack_set.h"
#include "expression_rig_performance_score.h"
#include "generated/expression_rig_v34_v35_special_decoration_candidate_profile.h"

#include <ctype.h>
#include <limits.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

enum { FRAME_BYTES = 5000u };

typedef struct {
    uint8_t *data;
    size_t size;
    uint32_t read_count;
} file_nor_t;

static int require_true(bool condition, const char *message)
{
    if (!condition) {
        fprintf(stderr, "FAIL: %s\n", message);
        return 1;
    }
    return 0;
}

static bool file_nor_read(void *context, uint32_t offset, uint8_t *destination, size_t length)
{
    file_nor_t *nor = (file_nor_t *)context;

    if (nor == NULL || destination == NULL || offset > nor->size || length > nor->size - offset) {
        return false;
    }
    memcpy(destination, &nor->data[offset], length);
    nor->read_count++;
    return true;
}

static bool load_file(const char *path, file_nor_t *out_nor)
{
    FILE *file = NULL;
    long length;
    size_t read_count;

    if (path == NULL || out_nor == NULL || fopen_s(&file, path, "rb") != 0 || file == NULL ||
        fseek(file, 0L, SEEK_END) != 0 || (length = ftell(file)) <= 0L ||
        (unsigned long)length > UINT32_MAX || fseek(file, 0L, SEEK_SET) != 0) {
        if (file != NULL) {
            fclose(file);
        }
        return false;
    }
    out_nor->data = (uint8_t *)malloc((size_t)length);
    if (out_nor->data == NULL) {
        fclose(file);
        return false;
    }
    read_count = fread(out_nor->data, 1u, (size_t)length, file);
    fclose(file);
    if (read_count != (size_t)length) {
        free(out_nor->data);
        *out_nor = (file_nor_t){0};
        return false;
    }
    out_nor->size = (size_t)length;
    return true;
}

static bool next_token(FILE *file, char *destination, size_t destination_size)
{
    int value;
    size_t length = 0u;

    if (file == NULL || destination == NULL || destination_size < 2u) {
        return false;
    }
    do {
        value = fgetc(file);
        if (value == '#') {
            do {
                value = fgetc(file);
            } while (value != EOF && value != '\n' && value != '\r');
        }
    } while (value != EOF && isspace((unsigned char)value));
    if (value == EOF) {
        return false;
    }
    do {
        if (length + 1u >= destination_size) {
            return false;
        }
        destination[length++] = (char)value;
        value = fgetc(file);
    } while (value != EOF && !isspace((unsigned char)value));
    destination[length] = '\0';
    return length > 0u;
}

static bool load_p4_target_bytes(const char *path, uint8_t *destination, size_t destination_size)
{
    FILE *file = NULL;
    char token[32];
    unsigned long width;
    unsigned long height;
    size_t index;

    if (path == NULL || destination == NULL || destination_size < FRAME_BYTES ||
        fopen_s(&file, path, "rb") != 0 || file == NULL || !next_token(file, token, sizeof(token)) ||
        strcmp(token, "P4") != 0 || !next_token(file, token, sizeof(token))) {
        if (file != NULL) {
            fclose(file);
        }
        return false;
    }
    width = strtoul(token, NULL, 10);
    if (!next_token(file, token, sizeof(token))) {
        fclose(file);
        return false;
    }
    height = strtoul(token, NULL, 10);
    if (width != 200u || height != 200u || fread(destination, 1u, FRAME_BYTES, file) != FRAME_BYTES) {
        fclose(file);
        return false;
    }
    fclose(file);
    for (index = 0u; index < FRAME_BYTES; ++index) {
        destination[index] = (uint8_t)~destination[index];
    }
    return true;
}

static bool build_path(char *destination, size_t destination_size, const char *directory, const char *filename)
{
    int written;

    if (destination == NULL || destination_size == 0u || directory == NULL || filename == NULL) {
        return false;
    }
    written = snprintf(destination, destination_size, "%s\\%s", directory, filename);
    return written > 0 && (size_t)written < destination_size;
}

static int write_report(const char *path, unsigned int replayed_steps)
{
    FILE *file = NULL;
    uint8_t score_index;

    if (path == NULL) {
        return 0;
    }
    if (fopen_s(&file, path, "wb") != 0 || file == NULL) {
        return 1;
    }
    fprintf(file,
            "{\n"
            "  \"schema\": \"companion.v34_v35_special_decoration_wb55_component_parity_host.v1\",\n"
            "  \"status\": \"PASS_BROWSER_WB55_COMPONENT_PIXEL_PARITY_RUNTIME_INACTIVE\",\n"
            "  \"target\": \"STM32WB55 upper expression component path\",\n"
            "  \"canvas\": {\"width\": 200, \"height\": 200, \"stride_bytes\": 25},\n"
            "  \"source_packs\": [\"v22_face\", \"v34_v35_decoration\"],\n"
            "  \"component_count\": %u,\n"
            "  \"replayed_frame_count\": %u,\n"
            "  \"frames\": [\n",
            (unsigned)COMP_V34_V35_SPECIAL_DECORATION_CANDIDATE_COMPONENT_COUNT, replayed_steps);
    for (score_index = 0u;
         score_index < comp_v34_v35_special_decoration_candidate_score_count();
         ++score_index) {
        const comp_v34_v35_special_decoration_candidate_score_t *descriptor =
            comp_v34_v35_special_decoration_candidate_score(score_index);
        uint8_t frame_index;

        for (frame_index = 0u; descriptor != NULL && frame_index < descriptor->frame_count; ++frame_index) {
            bool last = score_index + 1u == comp_v34_v35_special_decoration_candidate_score_count() &&
                        frame_index + 1u == descriptor->frame_count;
            fprintf(file,
                    "    {\"score\": \"%s\", \"cue\": \"%s\", \"pbm\": \"%s\", \"duration_ms\": %u}%s\n",
                    descriptor->name, descriptor->frames[frame_index].cue,
                    descriptor->frames[frame_index].browser_pbm_filename,
                    (unsigned)descriptor->frames[frame_index].duration_ms, last ? "" : ",");
        }
    }
    fprintf(file,
            "  ],\n"
            "  \"runtime_resource_activated\": false,\n"
            "  \"special_event_binding\": \"forbidden_until_owner_review\",\n"
            "  \"dream_cloud\": \"fail_closed_pending_v9_sleep_profile\",\n"
            "  \"non_claims\": [\"no_firmware_flash\", \"no_panel_or_driver_change\", \"no_human_acceptance\"]\n"
            "}\n");
    fclose(file);
    return 0;
}

static int replay(file_nor_t *face_nor, file_nor_t *decoration_nor, const char *frame_directory,
                  const char *report_path)
{
    static const comp_expression_rig_canvas_t canvas = {
        .width = 200u, .height = 200u, .stride_bytes = 25u,
    };
    const comp_expression_rig_profile_t *profile =
        comp_v34_v35_special_decoration_candidate_profile();
    comp_asset_store_t face_store;
    comp_asset_store_t decoration_store;
    comp_expression_rig_asset_pack_t face_pack;
    comp_expression_rig_asset_pack_t decoration_pack;
    comp_expression_rig_asset_pack_set_t pack_set;
    uint8_t scratch[256];
    uint8_t output[FRAME_BYTES];
    uint8_t expected[FRAME_BYTES];
    unsigned int replayed_steps = 0u;
    uint8_t score_index;

    if (require_true(profile != NULL && !comp_v34_v35_special_decoration_candidate_runtime_activation_allowed() &&
                     comp_asset_store_init_reader(&face_store, COMP_ASSET_STORAGE_EXTERNAL_NOR,
                                                  (uint32_t)face_nor->size, file_nor_read, face_nor) &&
                     comp_asset_store_init_reader(&decoration_store, COMP_ASSET_STORAGE_EXTERNAL_NOR,
                                                  (uint32_t)decoration_nor->size, file_nor_read, decoration_nor) &&
                     face_store.mapped_data == NULL && decoration_store.mapped_data == NULL &&
                     comp_expression_rig_asset_pack_mount(&face_pack, &face_store, &canvas) ==
                         COMP_EXPRESSION_RIG_ASSET_MOUNT_OK &&
                     comp_expression_rig_asset_pack_mount(&decoration_pack, &decoration_store, &canvas) ==
                         COMP_EXPRESSION_RIG_ASSET_MOUNT_OK &&
                     face_pack.component_count == 37u && decoration_pack.component_count == 39u &&
                     comp_expression_rig_asset_pack_verify_payload(&face_pack, scratch, sizeof(scratch)) &&
                     comp_expression_rig_asset_pack_verify_payload(&decoration_pack, scratch, sizeof(scratch)),
                     "both CRIG packs must mount from callback-only external NOR")) {
        return 1;
    }
    comp_expression_rig_asset_pack_set_init(&pack_set);
    if (require_true(comp_expression_rig_asset_pack_set_add(&pack_set, &face_pack) &&
                     comp_expression_rig_asset_pack_set_add(&pack_set, &decoration_pack),
                     "WB55 source reader must combine only non-overlapping registered CRIG namespaces")) {
        return 1;
    }
    for (score_index = 0u;
         score_index < comp_v34_v35_special_decoration_candidate_score_count();
         ++score_index) {
        const comp_v34_v35_special_decoration_candidate_score_t *descriptor =
            comp_v34_v35_special_decoration_candidate_score(score_index);
        uint8_t frame_index;

        if (require_true(descriptor != NULL && descriptor->score != NULL && descriptor->frames != NULL &&
                         descriptor->frame_count == descriptor->score->step_count && descriptor->frame_count == 3u,
                         "generated special score and browser frame descriptor must remain one-to-one")) {
            return 1;
        }
        for (frame_index = 0u; frame_index < descriptor->frame_count; ++frame_index) {
            comp_expression_rig_plan_t plan;
            comp_expression_rig_bounds_t bounds;
            char expected_path[512];

            if (require_true(comp_expression_rig_build_registered_score_step(
                                 profile, descriptor->score, frame_index, NULL, &plan) &&
                             plan.layer_count > 0u && plan.layer_count <= COMP_EXPRESSION_RIG_MAX_LAYERS &&
                             comp_expression_rig_compose_1bpp(
                                 &canvas, &plan, comp_expression_rig_asset_pack_set_read_component, &pack_set,
                                 scratch, sizeof(scratch), output, sizeof(output), &bounds) && bounds.has_ink &&
                             build_path(expected_path, sizeof(expected_path), frame_directory,
                                        descriptor->frames[frame_index].browser_pbm_filename) &&
                             load_p4_target_bytes(expected_path, expected, sizeof(expected)) &&
                             memcmp(output, expected, sizeof(output)) == 0,
                             "WB55 dual-CRIG component composition must exactly match its browser source frame")) {
                return 1;
            }
            replayed_steps++;
        }
    }
    if (require_true(replayed_steps == 12u && face_nor->read_count > 0u && decoration_nor->read_count > 0u,
                     "both external NOR component namespaces must service the complete WB55 replay") ||
        write_report(report_path, replayed_steps) != 0) {
        return 1;
    }
    return 0;
}

int main(int argc, char **argv)
{
    file_nor_t face_nor = {0};
    file_nor_t decoration_nor = {0};
    int result;

    if (argc != 5 || !load_file(argv[1], &face_nor) || !load_file(argv[2], &decoration_nor)) {
        fprintf(stderr, "FAIL: usage: test_expression_v34_v35_special_decoration_wb55_parity <v22.crig> <special.crig> <browser-frame-dir> <report.json>\n");
        free(face_nor.data);
        free(decoration_nor.data);
        return 1;
    }
    result = replay(&face_nor, &decoration_nor, argv[3], argv[4]);
    free(face_nor.data);
    free(decoration_nor.data);
    if (result != 0) {
        return result;
    }
    puts("PASS: WB55 upper path rebuilds all twelve V34/V35 browser frames from dual external-NOR CRIG source masks");
    return 0;
}
