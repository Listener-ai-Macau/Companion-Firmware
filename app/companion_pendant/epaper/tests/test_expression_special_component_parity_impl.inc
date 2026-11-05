#include "asset_store.h"
#include "expression_rig.h"
#include "expression_rig_asset_pack.h"
#include "expression_rig_asset_pack_set.h"
#include "expression_rig_performance_score.h"
#include SPECIAL_PROFILE_HEADER

#include <ctype.h>
#include <limits.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

enum { SPECIAL_FRAME_BYTES = 5000u };

#ifndef SPECIAL_DESCRIPTOR_IS_VALID
#define SPECIAL_DESCRIPTOR_IS_VALID(descriptor) \
    ((descriptor) != NULL && (descriptor)->score != NULL && (descriptor)->frames != NULL && \
     (descriptor)->frame_count == (descriptor)->score->step_count)
#endif

#ifndef SPECIAL_BUILD_FRAME
#define SPECIAL_BUILD_FRAME(descriptor, frame_index, out_plan) \
    comp_expression_rig_build_registered_score_step(profile, (descriptor)->score, (frame_index), NULL, (out_plan))
#endif

#ifndef SPECIAL_FRAME_PHASE
#define SPECIAL_FRAME_PHASE(descriptor, frame_index) "unknown"
#endif

typedef struct { uint8_t *data; size_t size; uint32_t reads; } special_file_nor_t;

static int special_require(bool condition, const char *message)
{
    if (!condition) { fprintf(stderr, "FAIL: %s\n", message); return 1; }
    return 0;
}

static bool special_nor_read(void *context, uint32_t offset, uint8_t *destination, size_t length)
{
    special_file_nor_t *nor = (special_file_nor_t *)context;
    if (nor == NULL || destination == NULL || offset > nor->size || length > nor->size - offset) { return false; }
    memcpy(destination, &nor->data[offset], length); nor->reads++; return true;
}

static bool special_load_file(const char *path, special_file_nor_t *out_nor)
{
    FILE *file = NULL; long length; size_t actual;
    if (path == NULL || out_nor == NULL || fopen_s(&file, path, "rb") != 0 || file == NULL ||
        fseek(file, 0L, SEEK_END) != 0 || (length = ftell(file)) <= 0L || (unsigned long)length > UINT32_MAX ||
        fseek(file, 0L, SEEK_SET) != 0) { if (file != NULL) { fclose(file); } return false; }
    out_nor->data = (uint8_t *)malloc((size_t)length);
    if (out_nor->data == NULL) { fclose(file); return false; }
    actual = fread(out_nor->data, 1u, (size_t)length, file); fclose(file);
    if (actual != (size_t)length) { free(out_nor->data); *out_nor = (special_file_nor_t){0}; return false; }
    out_nor->size = (size_t)length; return true;
}

static bool special_next_token(FILE *file, char *destination, size_t size)
{
    int value; size_t length = 0u;
    if (file == NULL || destination == NULL || size < 2u) { return false; }
    do {
        value = fgetc(file);
        if (value == '#') { do { value = fgetc(file); } while (value != EOF && value != '\n' && value != '\r'); }
    } while (value != EOF && isspace((unsigned char)value));
    if (value == EOF) { return false; }
    do { if (length + 1u >= size) { return false; } destination[length++] = (char)value; value = fgetc(file); }
    while (value != EOF && !isspace((unsigned char)value));
    destination[length] = '\0'; return length > 0u;
}

static bool special_load_p4(const char *path, uint8_t *destination, size_t destination_size)
{
    FILE *file = NULL; char token[32]; unsigned long width; unsigned long height; size_t index;
    if (path == NULL || destination == NULL || destination_size < SPECIAL_FRAME_BYTES ||
        fopen_s(&file, path, "rb") != 0 || file == NULL || !special_next_token(file, token, sizeof(token)) ||
        strcmp(token, "P4") != 0 || !special_next_token(file, token, sizeof(token))) { if (file != NULL) { fclose(file); } return false; }
    width = strtoul(token, NULL, 10);
    if (!special_next_token(file, token, sizeof(token))) { fclose(file); return false; }
    height = strtoul(token, NULL, 10);
    if (width != 200u || height != 200u || fread(destination, 1u, SPECIAL_FRAME_BYTES, file) != SPECIAL_FRAME_BYTES) { fclose(file); return false; }
    fclose(file);
    for (index = 0u; index < SPECIAL_FRAME_BYTES; ++index) { destination[index] = (uint8_t)~destination[index]; }
    return true;
}

static bool special_path(char *destination, size_t size, const char *directory, const char *filename)
{
    int written = snprintf(destination, size, "%s\\%s", directory, filename);
    return destination != NULL && directory != NULL && filename != NULL && written > 0 && (size_t)written < size;
}

static void special_write_actual_p4(const char *path, const uint8_t *frame)
{
    FILE *file = NULL;
    size_t index;

    if (path == NULL || frame == NULL || fopen_s(&file, path, "wb") != 0 || file == NULL) {
        return;
    }
    (void)fwrite("P4\n200 200\n", 1u, 11u, file);
    for (index = 0u; index < SPECIAL_FRAME_BYTES; ++index) {
        (void)fputc((int)(uint8_t)~frame[index], file);
    }
    fclose(file);
}

typedef struct {
    const char *score;
    const char *cue;
    const char *pbm;
    const char *phase;
    uint16_t duration_ms;
    uint8_t layer_count;
    comp_expression_rig_layer_t layers[COMP_EXPRESSION_RIG_MAX_LAYERS];
} special_frame_record_t;

static const char *special_pack_name(uint16_t component_id)
{
    return component_id >= 512u ? SPECIAL_PACK_LABEL : "v22_face";
}

static const char *special_composite_name(comp_expression_rig_composite_op_t operation)
{
    return operation == COMP_EXPRESSION_RIG_COMPOSITE_ERASE ? "erase" :
           operation == COMP_EXPRESSION_RIG_COMPOSITE_INK ? "ink" : "unknown";
}

static int special_write_report(const char *path,
                                const special_frame_record_t *records,
                                unsigned int replayed)
{
    FILE *file = NULL; unsigned int frame_index;
    if (path == NULL) { return 0; }
    if (records == NULL || replayed > SPECIAL_EXPECTED_FRAME_COUNT ||
        fopen_s(&file, path, "wb") != 0 || file == NULL) { return 1; }
    fprintf(file, "{\n  \"schema\": \"%s\",\n  \"status\": \"PASS_BROWSER_WB55_COMPONENT_PIXEL_PARITY_RUNTIME_INACTIVE\",\n  \"target\": \"STM32WB55 upper expression component path\",\n  \"canvas\": {\"width\": 200, \"height\": 200, \"stride_bytes\": 25},\n  \"source_packs\": [\"v22_face\", \"%s\"],\n  \"component_count\": %u,\n  \"replayed_frame_count\": %u,\n  \"frames\": [\n", SPECIAL_REPORT_SCHEMA, SPECIAL_PACK_LABEL, (unsigned)SPECIAL_COMPONENT_COUNT, replayed);
    for (frame_index = 0u; frame_index < replayed; ++frame_index) {
        const special_frame_record_t *record = &records[frame_index];
        uint8_t layer_index;
        fprintf(file, "    {\"score\": \"%s\", \"cue\": \"%s\", \"phase\": \"%s\", \"pbm\": \"%s\", \"duration_ms\": %u, \"layers\": [",
                record->score, record->cue, record->phase, record->pbm, (unsigned)record->duration_ms);
        for (layer_index = 0u; layer_index < record->layer_count; ++layer_index) {
            const comp_expression_rig_layer_t *layer = &record->layers[layer_index];
            fprintf(file, "%s{\"component_id\": %u, \"pack\": \"%s\", \"anchor\": [%d, %d], \"offset\": [%d, %d], \"composite_op\": \"%s\"}",
                    layer_index == 0u ? "" : ",", (unsigned)layer->component_id, special_pack_name(layer->component_id),
                    (int)layer->base_x, (int)layer->base_y, (int)layer->offset_x, (int)layer->offset_y,
                    special_composite_name(layer->composite_op));
        }
        fprintf(file, "]}%s\n", frame_index + 1u == replayed ? "" : ",");
    }
    fprintf(file, "  ],\n  \"runtime_resource_activated\": false,\n  \"special_event_binding\": \"forbidden_until_total_machine_audit_and_owner_review\",\n  \"non_claims\": [\"no_firmware_flash\", \"no_panel_or_driver_change\", \"no_human_acceptance\"]\n}\n");
    fclose(file); return 0;
}

static int special_replay(special_file_nor_t *face_nor, special_file_nor_t *special_nor, const char *frame_dir, const char *report)
{
    static const comp_expression_rig_canvas_t canvas = {.width = 200u, .height = 200u, .stride_bytes = 25u};
    const comp_expression_rig_profile_t *profile = SPECIAL_GET_PROFILE();
    comp_asset_store_t face_store; comp_asset_store_t special_store; comp_expression_rig_asset_pack_t face_pack; comp_expression_rig_asset_pack_t special_pack;
    comp_expression_rig_asset_pack_set_t set; uint8_t scratch[SPECIAL_COMPONENT_SCRATCH_BYTES]; uint8_t output[SPECIAL_FRAME_BYTES]; uint8_t expected[SPECIAL_FRAME_BYTES]; special_frame_record_t records[SPECIAL_EXPECTED_FRAME_COUNT]; unsigned int replayed = 0u; uint8_t score_index;
    if (special_require(profile != NULL && !SPECIAL_ACTIVATION_ALLOWED() &&
                        comp_asset_store_init_reader(&face_store, COMP_ASSET_STORAGE_EXTERNAL_NOR, (uint32_t)face_nor->size, special_nor_read, face_nor) &&
                        comp_asset_store_init_reader(&special_store, COMP_ASSET_STORAGE_EXTERNAL_NOR, (uint32_t)special_nor->size, special_nor_read, special_nor) &&
                        face_store.mapped_data == NULL && special_store.mapped_data == NULL &&
                        comp_expression_rig_asset_pack_mount(&face_pack, &face_store, &canvas) == COMP_EXPRESSION_RIG_ASSET_MOUNT_OK &&
                        comp_expression_rig_asset_pack_mount(&special_pack, &special_store, &canvas) == COMP_EXPRESSION_RIG_ASSET_MOUNT_OK &&
                        face_pack.component_count == 37u && special_pack.component_count == SPECIAL_PACK_COMPONENT_COUNT &&
                        SPECIAL_COMPONENT_SCRATCH_BYTES >= SPECIAL_MAX_COMPONENT_MASK_BYTES &&
                        comp_expression_rig_asset_pack_verify_payload(&face_pack, scratch, sizeof(scratch)) &&
                        comp_expression_rig_asset_pack_verify_payload(&special_pack, scratch, sizeof(scratch)),
                        "both source CRIG packs and the declared component scratch budget must be valid")) { return 1; }
    comp_expression_rig_asset_pack_set_init(&set);
    if (special_require(comp_expression_rig_asset_pack_set_add(&set, &face_pack) && comp_expression_rig_asset_pack_set_add(&set, &special_pack), "component source namespaces must not overlap")) { return 1; }
    for (score_index = 0u; score_index < SPECIAL_SCORE_COUNT(); ++score_index) {
        const SPECIAL_SCORE_TYPE *descriptor = SPECIAL_GET_SCORE(score_index); uint8_t frame_index;
        if (special_require(SPECIAL_DESCRIPTOR_IS_VALID(descriptor), "generated score/frame descriptor must remain one-to-one")) { return 1; }
        for (frame_index = 0u; frame_index < descriptor->frame_count; ++frame_index) {
            comp_expression_rig_plan_t plan; comp_expression_rig_bounds_t bounds; char expected_path[512]; bool matched;
            matched = SPECIAL_BUILD_FRAME(descriptor, frame_index, &plan) &&
                                plan.layer_count > 0u && plan.layer_count <= COMP_EXPRESSION_RIG_MAX_LAYERS &&
                                comp_expression_rig_compose_1bpp(&canvas, &plan, comp_expression_rig_asset_pack_set_read_component, &set, scratch, sizeof(scratch), output, sizeof(output), &bounds) && bounds.has_ink &&
                                special_path(expected_path, sizeof(expected_path), frame_dir, descriptor->frames[frame_index].browser_pbm_filename) &&
                                special_load_p4(expected_path, expected, sizeof(expected)) && memcmp(output, expected, sizeof(output)) == 0;
            if (!matched) {
                special_write_actual_p4("special-wb55-parity-mismatch.pbm", output);
                fprintf(stderr, "FAIL: browser/WB55 mismatch: score=%s cue=%s pbm=%s\n", descriptor->name, descriptor->frames[frame_index].cue, descriptor->frames[frame_index].browser_pbm_filename);
                return 1;
            }
            if (replayed >= SPECIAL_EXPECTED_FRAME_COUNT) {
                return 1;
            }
            records[replayed] = (special_frame_record_t){
                .score = descriptor->name,
                .cue = descriptor->frames[frame_index].cue,
                .pbm = descriptor->frames[frame_index].browser_pbm_filename,
                .phase = SPECIAL_FRAME_PHASE(descriptor, frame_index),
                .duration_ms = descriptor->frames[frame_index].duration_ms,
                .layer_count = plan.layer_count,
            };
            memcpy(records[replayed].layers, plan.layers,
                   (size_t)plan.layer_count * sizeof(plan.layers[0]));
            replayed++;
        }
    }
    if (special_require(replayed == SPECIAL_EXPECTED_FRAME_COUNT && face_nor->reads > 0u && special_nor->reads > 0u, "both external NOR packs must service the full replay") || special_write_report(report, records, replayed) != 0) { return 1; }
    return 0;
}

int main(int argc, char **argv)
{
    special_file_nor_t face = {0}; special_file_nor_t special = {0}; int result;
    if (argc != 5 || !special_load_file(argv[1], &face) || !special_load_file(argv[2], &special)) {
        fprintf(stderr, "FAIL: usage: special-parity <v22.crig> <special.crig> <browser-frame-dir> <report.json>\n"); free(face.data); free(special.data); return 1;
    }
    result = special_replay(&face, &special, argv[3], argv[4]); free(face.data); free(special.data);
    if (result != 0) { return result; }
    puts("PASS: WB55 upper path rebuilds every browser frame from dual external-NOR source component packs"); return 0;
}
