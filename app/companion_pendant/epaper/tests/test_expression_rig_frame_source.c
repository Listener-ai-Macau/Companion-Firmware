#include "asset_store.h"
#include "expression_choreographer.h"
#include "expression_rig_frame_source.h"
#include "generated/expression_rig_v9_candidate_profile.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define FRAME_WIDTH 200u
#define FRAME_HEIGHT 200u
#define FRAME_STRIDE_BYTES (FRAME_WIDTH / 8u)
#define FRAME_BYTES ((size_t)FRAME_STRIDE_BYTES * FRAME_HEIGHT)
#define COMPONENT_SCRATCH_BYTES 512u

typedef struct {
    const char *name;
    comp_expression_rig_attention_t attention;
    uint8_t expected_step_count;
} daily_direction_t;

static const daily_direction_t k_daily_directions[] = {
    {"daily_left", COMP_EXPRESSION_RIG_ATTENTION_LEFT, 19u},
    {"daily_right", COMP_EXPRESSION_RIG_ATTENTION_RIGHT, 18u},
    {"daily_up", COMP_EXPRESSION_RIG_ATTENTION_UP, 19u},
    {"daily_down", COMP_EXPRESSION_RIG_ATTENTION_DOWN, 16u},
};

static const uint8_t k_locked_source_sha256[32] = {
    0x91u, 0x9Fu, 0x34u, 0x49u, 0x57u, 0x66u, 0x1Du, 0xEFu,
    0x20u, 0x99u, 0xADu, 0x56u, 0xABu, 0x12u, 0x86u, 0xCCu,
    0xA9u, 0xDBu, 0xA4u, 0xD8u, 0xF0u, 0x8Bu, 0x70u, 0x26u,
    0x17u, 0xB6u, 0xDFu, 0x5Bu, 0x1Au, 0x28u, 0xE9u, 0xDAu,
};

static int require_true(int condition, const char *message)
{
    if (!condition) {
        fprintf(stderr, "FAIL: %s\n", message);
        return 1;
    }
    return 0;
}

static int read_file(const char *path, uint8_t **out_data, size_t *out_size)
{
    FILE *file = NULL;
    long length;
    uint8_t *data;

    if (path == NULL || out_data == NULL || out_size == NULL ||
        fopen_s(&file, path, "rb") != 0 || file == NULL ||
        fseek(file, 0, SEEK_END) != 0 || (length = ftell(file)) <= 0 ||
        fseek(file, 0, SEEK_SET) != 0) {
        if (file != NULL) {
            fclose(file);
        }
        return 1;
    }
    data = (uint8_t *)malloc((size_t)length);
    if (data == NULL || fread(data, 1u, (size_t)length, file) != (size_t)length) {
        free(data);
        fclose(file);
        return 1;
    }
    fclose(file);
    *out_data = data;
    *out_size = (size_t)length;
    return 0;
}

static int write_pbm(const char *directory,
                     const char *story,
                     unsigned int frame_index,
                     const uint8_t *frame)
{
    char path[1024];
    FILE *file = NULL;
    int written;

    written = sprintf_s(path, sizeof(path), "%s\\%s_%02u.pbm",
                        directory, story, frame_index);
    if (written <= 0 || (size_t)written >= sizeof(path) ||
        fopen_s(&file, path, "wb") != 0 || file == NULL) {
        return 1;
    }
    if (fprintf(file, "P4\n%u %u\n", FRAME_WIDTH, FRAME_HEIGHT) < 0) {
        fclose(file);
        return 1;
    }
    /* Rig framebuffer bits use 1=white; PBM P4 uses 1=black. This is only
     * the host-test serialization boundary, never a target composition step. */
    for (size_t index = 0u; index < FRAME_BYTES; ++index) {
        if (fputc((int)(uint8_t)~frame[index], file) == EOF) {
            fclose(file);
            return 1;
        }
    }
    fclose(file);
    return 0;
}

int main(int argc, char **argv)
{
    const comp_expression_rig_profile_t *profile =
        comp_v9_expression_rig_candidate_profile();
    comp_expression_rig_canvas_t canvas = {
        .width = FRAME_WIDTH,
        .height = FRAME_HEIGHT,
        .stride_bytes = FRAME_STRIDE_BYTES,
    };
    comp_expression_rig_choreography_input_t input = {
        .event = COMP_EXPRESSION_RIG_EVENT_DAILY_AUTO,
        .energy = COMP_EXPRESSION_RIG_ENERGY_NORMAL,
        .interaction_memory = 0u,
        .seed = 0xD9117E5u,
        .phase = COMP_EXPRESSION_RIG_PHASE_ENTRY,
    };
    comp_asset_store_t store;
    comp_expression_rig_frame_source_t source;
    uint8_t component_scratch[COMPONENT_SCRATCH_BYTES];
    uint8_t frame[FRAME_BYTES];
    uint8_t copied[FRAME_BYTES];
    uint8_t *pack_data = NULL;
    size_t pack_size = 0u;
    size_t direction_index;

    if (argc != 3) {
        fprintf(stderr, "usage: %s <candidate.crig> <output-directory>\n", argv[0]);
        return 2;
    }
    if (read_file(argv[1], &pack_data, &pack_size) != 0 ||
        require_true(pack_size <= UINT32_MAX, "component pack has a valid size") ||
        require_true(comp_asset_store_init_memory(&store, COMP_ASSET_STORAGE_EXTERNAL_NOR,
                                                  pack_data, pack_size),
                     "host source mounts the candidate pack as external NOR") ||
        require_true(comp_expression_rig_frame_source_mount(&source, &store, &canvas,
                                                             component_scratch,
                                                             sizeof(component_scratch),
                                                             frame, sizeof(frame)),
                     "frame source verifies and mounts the source-derived CRIG pack") ||
        require_true(source.asset_pack.revision == COMP_V9_EXPRESSION_RIG_CANDIDATE_REVISION &&
                         memcmp(source.asset_pack.source_sha256, k_locked_source_sha256,
                                sizeof(k_locked_source_sha256)) == 0,
                     "mounted CRIG revision and source hash match the locked v9 profile")) {
        free(pack_data);
        return 1;
    }

    for (direction_index = 0u;
         direction_index < sizeof(k_daily_directions) / sizeof(k_daily_directions[0]);
         ++direction_index) {
        const daily_direction_t *direction = &k_daily_directions[direction_index];
        const comp_expression_rig_performance_score_t *score;
        uint8_t entry_frame[FRAME_BYTES];
        uint8_t step_index;

        input.attention = direction->attention;
        score = comp_v9_expression_rig_candidate_daily_score(direction->attention);
        if (require_true(score != NULL && score->step_count == direction->expected_step_count,
                         "every Daily direction has its registered dynamic-rest score length")) {
            free(pack_data);
            return 1;
        }
        for (step_index = 0u; step_index < score->step_count; ++step_index) {
            comp_expression_rig_plan_t plan;

            if (require_true(comp_expression_rig_choreograph_daily_score_plan(profile, &input,
                                                                               score, step_index, &plan),
                             "target choreographer creates a Daily score plan") ||
                require_true(comp_expression_rig_frame_source_compose(&source, &plan, step_index),
                             "target frame source composes only the registered source masks") ||
                require_true(comp_expression_rig_frame_source_copy_frame_index(&source, step_index,
                                                                                copied, sizeof(copied)) &&
                                 memcmp(frame, copied, sizeof(frame)) == 0,
                             "panel source can copy only the current composed score frame") ||
                require_true(!comp_expression_rig_frame_source_copy_frame_index(&source,
                                                                                 (uint16_t)(step_index + 1u),
                                                                                 copied, sizeof(copied)),
                             "frame provider rejects a mismatched whole-face frame index") ||
                require_true(write_pbm(argv[2], direction->name, step_index, frame) == 0,
                             "target frame export succeeds")) {
                free(pack_data);
                return 1;
            }
            if (step_index == 0u) {
                memcpy(entry_frame, frame, sizeof(entry_frame));
            } else if (step_index + 1u == score->step_count &&
                       require_true(memcmp(entry_frame, frame, sizeof(entry_frame)) == 0,
                                    "Daily score returns exactly to the entry raster")) {
                free(pack_data);
                return 1;
            }
        }
    }

    free(pack_data);
    puts("PASS: external-NOR Rig frame source exported the four shared calibrated Daily scores");
    return 0;
}
