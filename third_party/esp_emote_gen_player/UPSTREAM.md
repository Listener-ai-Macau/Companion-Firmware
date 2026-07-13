# Upstream Snapshot

- Project: `esp_emote_gen_player`
- Upstream: https://github.com/espressif2022/esp_emote_gen_player
- Commit: `7139b46c6616d466ff153cb9d2ddf63661434f22`
- Component version: `0.0.2`
- License: Apache-2.0; see `LICENSE` and the SPDX headers in source files.

This is a source snapshot, not a Git submodule. The upstream ESP-IDF runtime is
kept unchanged as the reference implementation for emote taxonomy, pack index,
and clip switching. Companion STM32 targets do not compile this component
directly because it depends on ESP-IDF, `esp_emote_gfx`, FreeRTOS, and
`esp_mmap_assets`. Host-generated monochrome keyframes and target-named panel
adapters provide the WB55/WBA boundary.
