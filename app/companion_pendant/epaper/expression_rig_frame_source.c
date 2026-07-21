#include "expression_rig_frame_source.h"

#include <string.h>

static bool canvas_is_valid(const comp_expression_rig_canvas_t *canvas,
                            size_t *out_required_size)
{
    size_t required_size;

    if (canvas == NULL || out_required_size == NULL || canvas->width == 0u ||
        canvas->height == 0u ||
        canvas->stride_bytes < (uint16_t)((canvas->width + 7u) / 8u)) {
        return false;
    }
    required_size = (size_t)canvas->stride_bytes * canvas->height;
    if (required_size == 0u) {
        return false;
    }
    *out_required_size = required_size;
    return true;
}

bool comp_expression_rig_frame_source_mount(
    comp_expression_rig_frame_source_t *source,
    const comp_asset_store_t *asset_store,
    const comp_expression_rig_canvas_t *canvas,
    uint8_t *component_scratch,
    size_t component_scratch_size,
    uint8_t *frame,
    size_t frame_size)
{
    size_t required_size;
    comp_expression_rig_asset_mount_result_t mount_result;

    if (source == NULL || component_scratch == NULL || component_scratch_size == 0u ||
        frame == NULL || !canvas_is_valid(canvas, &required_size) || frame_size < required_size) {
        return false;
    }
    memset(source, 0, sizeof(*source));
    mount_result = comp_expression_rig_asset_pack_mount(&source->asset_pack,
                                                         asset_store,
                                                         canvas);
    if (mount_result != COMP_EXPRESSION_RIG_ASSET_MOUNT_OK ||
        !comp_expression_rig_asset_pack_verify_payload(&source->asset_pack,
                                                        component_scratch,
                                                        component_scratch_size)) {
        memset(source, 0, sizeof(*source));
        return false;
    }
    source->canvas = *canvas;
    source->component_scratch = component_scratch;
    source->component_scratch_size = component_scratch_size;
    source->frame = frame;
    source->frame_size = frame_size;
    return true;
}

bool comp_expression_rig_frame_source_compose(
    comp_expression_rig_frame_source_t *source,
    const comp_expression_rig_plan_t *plan,
    uint16_t frame_index)
{
    comp_expression_rig_bounds_t bounds;

    if (source == NULL || source->asset_pack.store == NULL || plan == NULL ||
        !comp_expression_rig_compose_1bpp(&source->canvas,
                                           plan,
                                           comp_expression_rig_asset_pack_read_component,
                                           &source->asset_pack,
                                           source->component_scratch,
                                           source->component_scratch_size,
                                           source->frame,
                                           source->frame_size,
                                           &bounds)) {
        return false;
    }
    source->current_bounds = bounds;
    source->current_frame_index = frame_index;
    source->frame_valid = true;
    source->composed_frame_count++;
    return true;
}

bool comp_expression_rig_frame_source_copy_frame_index(
    void *context,
    uint16_t frame_index,
    uint8_t *destination,
    size_t destination_size)
{
    comp_expression_rig_frame_source_t *source =
        (comp_expression_rig_frame_source_t *)context;
    size_t required_size;

    if (source == NULL || destination == NULL || !source->frame_valid ||
        !canvas_is_valid(&source->canvas, &required_size) ||
        destination_size < required_size || frame_index != source->current_frame_index) {
        if (source != NULL) {
            source->rejected_copy_count++;
        }
        return false;
    }
    memcpy(destination, source->frame, required_size);
    return true;
}
