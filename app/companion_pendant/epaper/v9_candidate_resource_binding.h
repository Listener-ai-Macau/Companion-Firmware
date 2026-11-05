#ifndef COMPANION_EPAPER_V9_CANDIDATE_RESOURCE_BINDING_H
#define COMPANION_EPAPER_V9_CANDIDATE_RESOURCE_BINDING_H

#include <stdbool.h>
#include <stdint.h>

#include "pet_performance.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef enum {
    COMP_V9_CANDIDATE_RESOURCE_AVAILABLE_NOT_ACTIVE = 0u,
    COMP_V9_CANDIDATE_RESOURCE_PENDING_VISUAL_BASELINE,
    COMP_V9_CANDIDATE_RESOURCE_PENDING_MENU_VISUAL_BASELINE,
    COMP_V9_CANDIDATE_RESOURCE_INVALID,
} comp_v9_candidate_resource_status_t;

typedef struct {
    comp_v9_candidate_resource_status_t status;
    const char *resource_family;
    const char *candidate_pack_name;
    uint32_t candidate_pack_revision;
    const char *candidate_clip_name;
    uint8_t candidate_frame_index;
    bool frame_available;
    bool runtime_activation_allowed;
} comp_v9_candidate_resource_binding_t;

const char *comp_v9_candidate_resource_status_name(
    comp_v9_candidate_resource_status_t status);

/* This is metadata only. It deliberately does not mount, select, or activate
 * the CEMP candidate pack. Pending scenes never borrow a legacy face. */
bool comp_v9_candidate_resource_resolve(
    const comp_pet_performance_frame_t *performance_frame,
    comp_v9_candidate_resource_binding_t *out_binding);
bool comp_v9_candidate_resource_runtime_activation_allowed(void);
bool comp_v9_candidate_resource_pack_identity_matches(
    const char *pack_name,
    uint32_t pack_revision,
    uint16_t clip_count,
    uint16_t frame_count);
bool comp_v9_candidate_resource_binding_self_test(void);

#ifdef __cplusplus
}
#endif

#endif /* COMPANION_EPAPER_V9_CANDIDATE_RESOURCE_BINDING_H */
