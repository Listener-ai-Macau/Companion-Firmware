#include "asset_store.h"

#include <limits.h>
#include <string.h>

static bool range_is_valid(uint32_t size_bytes, uint32_t offset, size_t length)
{
    return length <= UINT32_MAX && offset <= size_bytes &&
           (uint32_t)length <= (size_bytes - offset);
}

bool comp_asset_store_init_memory(comp_asset_store_t *store,
                                  comp_asset_storage_class_t storage_class,
                                  const uint8_t *data,
                                  size_t size_bytes)
{
    if (store == NULL || data == NULL || size_bytes == 0u || size_bytes > UINT32_MAX) {
        return false;
    }
    *store = (comp_asset_store_t){
        .storage_class = storage_class,
        .size_bytes = (uint32_t)size_bytes,
        .mapped_data = data,
    };
    return true;
}

bool comp_asset_store_init_reader(comp_asset_store_t *store,
                                  comp_asset_storage_class_t storage_class,
                                  uint32_t size_bytes,
                                  comp_asset_store_read_fn_t read,
                                  void *context)
{
    if (store == NULL || size_bytes == 0u || read == NULL) {
        return false;
    }
    *store = (comp_asset_store_t){
        .storage_class = storage_class,
        .size_bytes = size_bytes,
        .read = read,
        .context = context,
    };
    return true;
}

bool comp_asset_store_read(const comp_asset_store_t *store,
                           uint32_t offset,
                           uint8_t *destination,
                           size_t length)
{
    if (store == NULL || destination == NULL ||
        !range_is_valid(store->size_bytes, offset, length)) {
        return false;
    }
    if (length == 0u) {
        return true;
    }
    if (store->mapped_data != NULL) {
        memcpy(destination, &store->mapped_data[offset], length);
        return true;
    }
    return store->read != NULL && store->read(store->context, offset, destination, length);
}

typedef struct {
    const uint8_t *data;
    size_t size;
    uint32_t reads;
} test_reader_t;

static bool test_read(void *context, uint32_t offset, uint8_t *destination, size_t length)
{
    test_reader_t *reader = (test_reader_t *)context;
    if (reader == NULL || offset > reader->size || length > reader->size - offset) {
        return false;
    }
    memcpy(destination, &reader->data[offset], length);
    reader->reads++;
    return true;
}

bool comp_asset_store_self_test(void)
{
    static const uint8_t data[] = {0x10u, 0x20u, 0x30u, 0x40u};
    comp_asset_store_t memory_store;
    comp_asset_store_t reader_store;
    test_reader_t reader = {.data = data, .size = sizeof(data)};
    uint8_t output[2] = {0u};

    if (!comp_asset_store_init_memory(&memory_store,
                                      COMP_ASSET_STORAGE_INTERNAL_FLASH,
                                      data,
                                      sizeof(data)) ||
        !comp_asset_store_read(&memory_store, 1u, output, sizeof(output)) ||
        output[0] != 0x20u || output[1] != 0x30u ||
        comp_asset_store_read(&memory_store, 3u, output, sizeof(output))) {
        return false;
    }
    memset(output, 0, sizeof(output));
    if (!comp_asset_store_init_reader(&reader_store,
                                      COMP_ASSET_STORAGE_EXTERNAL_NOR,
                                      (uint32_t)sizeof(data),
                                      test_read,
                                      &reader) ||
        !comp_asset_store_read(&reader_store, 2u, output, sizeof(output)) ||
        output[0] != 0x30u || output[1] != 0x40u || reader.reads != 1u) {
        return false;
    }
    return true;
}
