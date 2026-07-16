#include "asset_store.h"
#include "emote_asset_pack.h"
#include "screen_assets_stm32wba.h"

#include <limits.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct {
    uint8_t *data;
    size_t size;
    uint32_t read_count;
} file_nor_t;

static int require_true(bool condition, const char *message)
{
    if (!condition) {
        fprintf(stderr, "FAIL: %s\n", message);
        return 1;
    }
    return 0;
}

static bool file_nor_read(void *context,
                          uint32_t partition_offset,
                          uint8_t *destination,
                          size_t length)
{
    file_nor_t *nor = (file_nor_t *)context;

    if (nor == NULL || destination == NULL ||
        partition_offset > nor->size || length > nor->size - partition_offset) {
        return false;
    }
    memcpy(destination, &nor->data[partition_offset], length);
    nor->read_count++;
    return true;
}

static bool load_file(const char *path, file_nor_t *out_nor)
{
    FILE *file = NULL;
    long length;
    size_t bytes_read;

    if (path == NULL || out_nor == NULL || fopen_s(&file, path, "rb") != 0 ||
        file == NULL) {
        return false;
    }
    if (fseek(file, 0L, SEEK_END) != 0 || (length = ftell(file)) <= 0L ||
        (unsigned long)length > UINT32_MAX || fseek(file, 0L, SEEK_SET) != 0) {
        fclose(file);
        return false;
    }
    out_nor->data = (uint8_t *)malloc((size_t)length);
    if (out_nor->data == NULL) {
        fclose(file);
        return false;
    }
    bytes_read = fread(out_nor->data, 1u, (size_t)length, file);
    fclose(file);
    if (bytes_read != (size_t)length) {
        free(out_nor->data);
        out_nor->data = NULL;
        return false;
    }
    out_nor->size = (size_t)length;
    return true;
}

static bool frame_has_black_and_white(const uint8_t *frame, size_t size)
{
    bool saw_black = false;
    bool saw_white = false;

    for (size_t index = 0u; index < size; ++index) {
        saw_black = saw_black || frame[index] != 0xFFu;
        saw_white = saw_white || frame[index] != 0x00u;
    }
    return saw_black && saw_white;
}

static int exercise_target(file_nor_t *nor,
                           companion_epaper_panel_stm32wba_target_t target)
{
    static const comp_screen_asset_profile_t profile = {
        .width = 200u,
        .height = 200u,
        .stride_bytes = 25u,
        .pixel_format = COMP_SCREEN_PIXEL_FORMAT_MONO_1BPP_WHITE_IS_ONE_MSB,
    };
    companion_screen_assets_stm32wba_t adapter;
    companion_screen_assets_stm32wba_config_t config;
    comp_asset_store_t store;
    comp_emote_asset_mount_t mount;
    comp_emote_clip_t clips[16];
    comp_emote_frame_t frames[48];
    char strings[1024];
    uint8_t scratch[256];
    uint8_t output[5000];
    uint8_t byte = 0u;

    companion_screen_assets_stm32wba_init(&adapter);
    config = (companion_screen_assets_stm32wba_config_t){
        .target = target,
        .partition_size = (uint32_t)nor->size,
        .read = file_nor_read,
        .context = nor,
    };
    if (require_true(companion_screen_assets_stm32wba_bind(&adapter, &store, &config),
                     "WBA assets adapter must bind an external NOR callback") ||
        require_true(companion_screen_assets_stm32wba_ready(&adapter),
                     "WBA assets adapter must be ready after binding") ||
        require_true(store.storage_class == COMP_ASSET_STORAGE_EXTERNAL_NOR &&
                         store.mapped_data == NULL && store.read != NULL,
                     "WBA asset store must remain callback-only external NOR") ||
        require_true(!comp_asset_store_read(&store, (uint32_t)nor->size, &byte, 1u),
                     "WBA asset store must reject an out-of-partition read")) {
        return 1;
    }

    if (require_true(comp_emote_asset_pack_mount(
                         &mount,
                         &store,
                         &profile,
                         clips,
                         sizeof(clips) / sizeof(clips[0]),
                         frames,
                         sizeof(frames) / sizeof(frames[0]),
                         strings,
                         sizeof(strings),
                         scratch,
                         sizeof(scratch)) == COMP_EMOTE_ASSET_MOUNT_OK,
                     "v9 candidate CEMP must mount through the WBA callback") ||
        require_true(strcmp(mount.pack.name,
                             "companion-v9-expression-candidate-200x200") == 0 &&
                         mount.pack.revision == 90u && mount.catalog.clip_count == 13u &&
                         mount.catalog.frame_count == 39u,
                     "mounted CEMP must retain the locked v9 identity") ||
        require_true(comp_emote_asset_pack_verify_payload(&mount.pack,
                                                           scratch,
                                                           sizeof(scratch)),
                     "mounted v9 candidate payload CRC must verify")) {
        return 1;
    }

    for (size_t index = 0u; index < mount.catalog.frame_count; ++index) {
        memset(output, 0, sizeof(output));
        if (require_true(comp_emote_asset_pack_read_frame(&mount.pack,
                                                           &mount.catalog.frames[index],
                                                           output,
                                                           sizeof(output)),
                         "every v9 CEMP frame must read through the WBA callback") ||
            require_true(frame_has_black_and_white(output, sizeof(output)),
                         "decoded v9 frame must keep visible black and white pixels")) {
            return 1;
        }
    }
    return require_true(nor->read_count > 0u,
                        "WBA replay must issue callback reads to the simulated external NOR");
}

int main(int argc, char **argv)
{
    file_nor_t nor = {0};
    int result;

    if (argc != 2 || !load_file(argv[1], &nor)) {
        fprintf(stderr, "FAIL: expected one readable v9 candidate CEMP path\n");
        return 1;
    }
    result = exercise_target(&nor, COMPANION_EPAPER_PANEL_STM32WBA_TARGET_WBA55);
    if (result == 0) {
        result = exercise_target(&nor, COMPANION_EPAPER_PANEL_STM32WBA_TARGET_WBA65);
    }
    free(nor.data);
    if (result == 0) {
        printf("PASS: WBA external-NOR callback mounted v9 candidate CEMP for WBA55 and WBA65 without runtime activation.\n");
    }
    return result;
}
