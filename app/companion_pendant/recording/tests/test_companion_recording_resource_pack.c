#include "companion_recording_resource_pack.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int fail(const char *message)
{
    fprintf(stderr, "FAIL_RECORDING_RESOURCE_PACK %s\n", message);
    return 1;
}

static uint8_t *read_file(const char *path, size_t *size)
{
    FILE *stream = fopen(path, "rb");
    if (stream == NULL || fseek(stream, 0, SEEK_END) != 0) {
        if (stream != NULL) fclose(stream);
        return NULL;
    }
    long length = ftell(stream);
    if (length <= 0 || fseek(stream, 0, SEEK_SET) != 0) {
        fclose(stream);
        return NULL;
    }
    uint8_t *data = (uint8_t *)malloc((size_t)length);
    if (data == NULL || fread(data, 1u, (size_t)length, stream) !=
                            (size_t)length) {
        free(data);
        fclose(stream);
        return NULL;
    }
    fclose(stream);
    *size = (size_t)length;
    return data;
}

int main(int argc, char **argv)
{
    if (argc != 2) {
        return fail("usage: test_companion_recording_resource_pack pack.crrp");
    }
    size_t size = 0u;
    uint8_t *data = read_file(argv[1], &size);
    if (data == NULL) {
        return fail("read");
    }

    comp_asset_store_t store;
    comp_recording_resource_pack_t pack;
    uint8_t scratch[257];
    if (!comp_asset_store_init_memory(&store,
                                      COMP_ASSET_STORAGE_EXTERNAL_NOR,
                                      data,
                                      size)) {
        free(data);
        return fail("store_init");
    }
    comp_recording_resource_mount_result_t mounted =
        comp_recording_resource_pack_mount(&pack, &store);
    if (mounted != COMP_RECORDING_RESOURCE_MOUNT_OK) {
        free(data);
        return fail(comp_recording_resource_mount_result_name(mounted));
    }
    if (!comp_recording_resource_pack_verify_all(
            &pack, scratch, sizeof(scratch))) {
        free(data);
        return fail("verify_all");
    }

    comp_recording_resource_entry_t g7;
    comp_recording_resource_entry_t opus;
    uint8_t first[16];
    uint8_t last[16];
    if (!comp_recording_resource_pack_get(
            &pack, COMP_RECORDING_RESOURCE_G7_SPEECH_PCM, &g7) ||
        !comp_recording_resource_pack_get(
            &pack, COMP_RECORDING_RESOURCE_OPUS16_FIXTURE, &opus) ||
        !comp_recording_resource_pack_read(
            &pack, COMP_RECORDING_RESOURCE_OPUS16_FIXTURE,
            0u, first, sizeof(first)) ||
        !comp_recording_resource_pack_read(
            &pack, COMP_RECORDING_RESOURCE_G7_SPEECH_PCM,
            g7.data_bytes - sizeof(last), last, sizeof(last)) ||
        comp_recording_resource_pack_read(
            &pack, COMP_RECORDING_RESOURCE_G7_SPEECH_PCM,
            g7.data_bytes, last, 1u)) {
        free(data);
        return fail("read_contract");
    }

    uint8_t saved = data[g7.data_offset + 100u];
    data[g7.data_offset + 100u] ^= 0x01u;
    pack.verified_mask = 0u;
    bool corruption_rejected = !comp_recording_resource_pack_verify(
        &pack, COMP_RECORDING_RESOURCE_G7_SPEECH_PCM,
        scratch, sizeof(scratch));
    data[g7.data_offset + 100u] = saved;
    if (!corruption_rejected) {
        free(data);
        return fail("payload_corruption_not_rejected");
    }

    printf("PASS_RECORDING_RESOURCE_PACK bytes=%zu g7=%lu opus=%lu "
           "corruption_rejected=1\n",
           size,
           (unsigned long)g7.data_bytes,
           (unsigned long)opus.data_bytes);
    free(data);
    return 0;
}
