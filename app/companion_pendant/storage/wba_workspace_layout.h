#ifndef COMPANION_WBA_WORKSPACE_LAYOUT_H
#define COMPANION_WBA_WORKSPACE_LAYOUT_H
#include "wba_storage_layout.h"
#include <stdbool.h>
#include <stddef.h>
typedef bool (*comp_wba_layout_read_fn)(void *,uint32_t,uint8_t *,size_t);
/* Read-only geometry guard for resident boot and app. Missing, corrupt or
 * unsupported media is never authority to initialize or erase storage. */
bool comp_wba_workspace_layout_valid(comp_wba_layout_read_fn,void *);
/* A recovery anchor supplies an authenticated/validated old geometry. This
 * checks roots at that geometry without guessing or mutating current media. */
bool comp_wba_workspace_layout_valid_at(comp_wba_layout_read_fn,void *,uint32_t static_bytes);
#endif
