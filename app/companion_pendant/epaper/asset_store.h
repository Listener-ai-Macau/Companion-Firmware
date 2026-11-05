#ifndef COMPANION_EPAPER_ASSET_STORE_H
#define COMPANION_EPAPER_ASSET_STORE_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef enum {
    COMP_ASSET_STORAGE_INTERNAL_FLASH = 0u,
    COMP_ASSET_STORAGE_EXTERNAL_NOR = 1u,
    COMP_ASSET_STORAGE_HOST_STREAM = 2u,
} comp_asset_storage_class_t;

typedef bool (*comp_asset_store_read_fn_t)(void *context,
                                           uint32_t offset,
                                           uint8_t *destination,
                                           size_t length);

typedef struct {
    comp_asset_storage_class_t storage_class;
    uint32_t size_bytes;
    const uint8_t *mapped_data;
    comp_asset_store_read_fn_t read;
    void *context;
} comp_asset_store_t;

bool comp_asset_store_init_memory(comp_asset_store_t *store,
                                  comp_asset_storage_class_t storage_class,
                                  const uint8_t *data,
                                  size_t size_bytes);
bool comp_asset_store_init_reader(comp_asset_store_t *store,
                                  comp_asset_storage_class_t storage_class,
                                  uint32_t size_bytes,
                                  comp_asset_store_read_fn_t read,
                                  void *context);
bool comp_asset_store_read(const comp_asset_store_t *store,
                           uint32_t offset,
                           uint8_t *destination,
                           size_t length);
bool comp_asset_store_self_test(void);

#ifdef __cplusplus
}
#endif

#endif /* COMPANION_EPAPER_ASSET_STORE_H */
