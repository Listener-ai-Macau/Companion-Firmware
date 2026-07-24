#ifndef COMPANION_OTA_V1_H
#define COMPANION_OTA_V1_H

#include <stdbool.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

void Companion_Ota_V1_Init(void);

bool Companion_Ota_V1_ReadCandidate(
    uint32_t *image_size, uint32_t *partition_size, bool *pending_verify,
    bool *post_update_self_check);

#ifdef __cplusplus
}
#endif

#endif /* COMPANION_OTA_V1_H */
