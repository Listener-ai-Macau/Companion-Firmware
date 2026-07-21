#ifndef COMPANION_EPAPER_EXPRESSION_RIG_FRAME_SOURCE_H
#define COMPANION_EPAPER_EXPRESSION_RIG_FRAME_SOURCE_H

#include "expression_rig_asset_pack.h"

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* This is a transient target framebuffer, not an art asset. Every visible
 * pixel is composed from one mounted, source-derived external-NOR component. */
typedef struct {
    comp_expression_rig_asset_pack_t asset_pack;
    comp_expression_rig_canvas_t canvas;
    uint8_t *component_scratch;
    size_t component_scratch_size;
    uint8_t *frame;
    size_t frame_size;
    comp_expression_rig_bounds_t current_bounds;
    uint16_t current_frame_index;
    uint32_t composed_frame_count;
    uint32_t rejected_copy_count;
    bool frame_valid;
} comp_expression_rig_frame_source_t;

bool comp_expression_rig_frame_source_mount(
    comp_expression_rig_frame_source_t *source,
    const comp_asset_store_t *asset_store,
    const comp_expression_rig_canvas_t *canvas,
    uint8_t *component_scratch,
    size_t component_scratch_size,
    uint8_t *frame,
    size_t frame_size);

bool comp_expression_rig_frame_source_compose(
    comp_expression_rig_frame_source_t *source,
    const comp_expression_rig_plan_t *plan,
    uint16_t frame_index);

bool comp_expression_rig_frame_source_copy_frame_index(
    void *context,
    uint16_t frame_index,
    uint8_t *destination,
    size_t destination_size);

#ifdef __cplusplus
}
#endif

#endif /* COMPANION_EPAPER_EXPRESSION_RIG_FRAME_SOURCE_H */
