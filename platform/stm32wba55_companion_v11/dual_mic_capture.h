#ifndef COMP_V11_DUAL_MIC_CAPTURE_H
#define COMP_V11_DUAL_MIC_CAPTURE_H
#include "product_app.h"
/* Explicit wired finite engineering command only. Not a production codec or
 * automatic recording. A dynamically admitted workspace excludes normal
 * recording/OTA; the idle recorder PCM ring is restored before release. */
bool comp_v11_dual_pair_owned(const comp_v11_product_app_t *);
bool comp_v11_dual_pair_foreground_pending(const comp_v11_product_app_t *);
void comp_v11_dual_pair_accept(uint8_t);
void comp_v11_dual_pair_command(comp_v11_product_app_t *,bool normal_idle);
void comp_v11_dual_pair_poll(comp_v11_product_app_t *);
#endif
