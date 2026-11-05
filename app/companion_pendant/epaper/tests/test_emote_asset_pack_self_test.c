#include "emote_asset_pack.h"

#include <stdio.h>

int main(void)
{
    if (!comp_emote_asset_pack_self_test()) {
        fprintf(stderr, "FAIL: emote asset pack self-test\n");
        return 1;
    }
    puts("PASS: preloaded CEMP catalog accepts exact Flash metadata and rejects drift.");
    return 0;
}
