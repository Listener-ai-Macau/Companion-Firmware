#ifndef COMPANION_EPAPER_EMOTE_PLAYER_H
#define COMPANION_EPAPER_EMOTE_PLAYER_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define COMP_EMOTE_PLAYER_NO_CLIP UINT16_MAX

typedef enum {
    COMP_EMOTE_PLAYER_PHASE_STOPPED = 0u,
    COMP_EMOTE_PLAYER_PHASE_INTRO = 1u,
    COMP_EMOTE_PLAYER_PHASE_LOOP = 2u,
    COMP_EMOTE_PLAYER_PHASE_TAIL = 3u,
} comp_emote_player_phase_t;

typedef struct {
    uint32_t data_offset;
    uint32_t data_size;
    uint16_t duration_ms;
    uint16_t dirty_x;
    uint16_t dirty_y;
    uint16_t dirty_width;
    uint16_t dirty_height;
} comp_emote_frame_t;

typedef struct {
    const char *name;
    uint16_t first_frame;
    uint16_t frame_count;
    uint16_t loop_start;
    uint16_t loop_end;
} comp_emote_clip_t;

typedef struct {
    const comp_emote_clip_t *clips;
    size_t clip_count;
    const comp_emote_frame_t *frames;
    size_t frame_count;
} comp_emote_catalog_t;

typedef struct {
    const char *clip_name;
    comp_emote_frame_t frame;
    uint16_t clip_index;
    uint16_t frame_index;
    uint16_t frame_in_clip;
    comp_emote_player_phase_t phase;
    uint32_t revision;
} comp_emote_player_frame_t;

typedef struct {
    const comp_emote_catalog_t *catalog;
    uint16_t current_clip;
    uint16_t pending_clip;
    uint16_t frame_in_clip;
    uint32_t frame_elapsed_ms;
    uint32_t revision;
    uint32_t emitted_frames;
    uint32_t skipped_frames;
    uint32_t immediate_switches;
    uint32_t tail_handoffs;
    comp_emote_player_phase_t phase;
    bool repeat;
    bool pending_repeat;
    bool handoff_pending;
    bool frame_ready;
} comp_emote_player_t;

typedef struct {
    bool playing;
    bool repeat;
    bool handoff_pending;
    bool frame_ready;
    uint16_t current_clip;
    uint16_t pending_clip;
    uint16_t frame_in_clip;
    uint32_t frame_elapsed_ms;
    uint32_t revision;
    uint32_t emitted_frames;
    uint32_t skipped_frames;
    uint32_t immediate_switches;
    uint32_t tail_handoffs;
    comp_emote_player_phase_t phase;
} comp_emote_player_snapshot_t;

bool comp_emote_catalog_validate(const comp_emote_catalog_t *catalog);
bool comp_emote_player_init(comp_emote_player_t *player,
                            const comp_emote_catalog_t *catalog);
bool comp_emote_player_play_now(comp_emote_player_t *player,
                                uint16_t clip_index,
                                bool repeat);
bool comp_emote_player_play_now_name(comp_emote_player_t *player,
                                     const char *name,
                                     bool repeat);
bool comp_emote_player_play_after_tail(comp_emote_player_t *player,
                                       uint16_t clip_index,
                                       bool repeat);
bool comp_emote_player_play_after_tail_name(comp_emote_player_t *player,
                                            const char *name,
                                            bool repeat);
void comp_emote_player_stop(comp_emote_player_t *player);
bool comp_emote_player_tick(comp_emote_player_t *player, uint32_t elapsed_ms);
uint32_t comp_emote_player_next_frame_in_ms(const comp_emote_player_t *player);
bool comp_emote_player_take_frame(comp_emote_player_t *player,
                                  comp_emote_player_frame_t *out_frame);
void comp_emote_player_snapshot(const comp_emote_player_t *player,
                                comp_emote_player_snapshot_t *out_snapshot);
bool comp_emote_player_self_test(void);

#ifdef __cplusplus
}
#endif

#endif /* COMPANION_EPAPER_EMOTE_PLAYER_H */
