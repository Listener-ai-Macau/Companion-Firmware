#include "emote_player.h"

#include <string.h>

static bool clip_has_segments(const comp_emote_clip_t *clip)
{
    return clip != NULL && clip->loop_start < clip->loop_end;
}

static const comp_emote_clip_t *current_clip(const comp_emote_player_t *player)
{
    if (player == NULL || player->catalog == NULL ||
        player->current_clip >= player->catalog->clip_count) {
        return NULL;
    }
    return &player->catalog->clips[player->current_clip];
}

static const comp_emote_frame_t *current_frame(const comp_emote_player_t *player)
{
    const comp_emote_clip_t *clip = current_clip(player);
    size_t index;

    if (clip == NULL || player->frame_in_clip >= clip->frame_count) {
        return NULL;
    }
    index = (size_t)clip->first_frame + player->frame_in_clip;
    return index < player->catalog->frame_count ? &player->catalog->frames[index] : NULL;
}

static int find_clip(const comp_emote_catalog_t *catalog, const char *name)
{
    if (catalog == NULL || name == NULL || name[0] == '\0') {
        return -1;
    }
    for (size_t index = 0u; index < catalog->clip_count; ++index) {
        if (strcmp(catalog->clips[index].name, name) == 0) {
            return (int)index;
        }
    }
    return -1;
}

bool comp_emote_catalog_validate(const comp_emote_catalog_t *catalog)
{
    if (catalog == NULL || catalog->clips == NULL || catalog->clip_count == 0u ||
        catalog->frames == NULL || catalog->frame_count == 0u ||
        catalog->clip_count > COMP_EMOTE_PLAYER_NO_CLIP) {
        return false;
    }
    for (size_t index = 0u; index < catalog->clip_count; ++index) {
        const comp_emote_clip_t *clip = &catalog->clips[index];
        size_t end = (size_t)clip->first_frame + clip->frame_count;
        if (clip->name == NULL || clip->name[0] == '\0' || clip->frame_count == 0u ||
            end > catalog->frame_count || clip->loop_start > clip->loop_end ||
            clip->loop_end > clip->frame_count) {
            return false;
        }
        for (size_t other = index + 1u; other < catalog->clip_count; ++other) {
            if (catalog->clips[other].name != NULL &&
                strcmp(clip->name, catalog->clips[other].name) == 0) {
                return false;
            }
        }
    }
    for (size_t index = 0u; index < catalog->frame_count; ++index) {
        const comp_emote_frame_t *frame = &catalog->frames[index];
        if (frame->duration_ms == 0u || frame->data_size == 0u) {
            return false;
        }
    }
    return true;
}

bool comp_emote_player_init(comp_emote_player_t *player,
                            const comp_emote_catalog_t *catalog)
{
    if (player == NULL || !comp_emote_catalog_validate(catalog)) {
        return false;
    }
    *player = (comp_emote_player_t){
        .catalog = catalog,
        .current_clip = COMP_EMOTE_PLAYER_NO_CLIP,
        .pending_clip = COMP_EMOTE_PLAYER_NO_CLIP,
        .phase = COMP_EMOTE_PLAYER_PHASE_STOPPED,
    };
    return true;
}

static void mark_frame_ready(comp_emote_player_t *player)
{
    if (player->frame_ready) {
        player->skipped_frames++;
    }
    player->frame_ready = true;
    player->revision++;
}

static bool select_clip(comp_emote_player_t *player,
                        uint16_t clip_index,
                        bool repeat)
{
    const comp_emote_clip_t *clip;

    if (player == NULL || player->catalog == NULL ||
        clip_index >= player->catalog->clip_count) {
        return false;
    }
    clip = &player->catalog->clips[clip_index];
    player->current_clip = clip_index;
    player->pending_clip = COMP_EMOTE_PLAYER_NO_CLIP;
    player->frame_in_clip = 0u;
    player->frame_elapsed_ms = 0u;
    player->repeat = repeat;
    player->pending_repeat = false;
    player->handoff_pending = false;
    player->phase = clip_has_segments(clip) && clip->loop_start == 0u
                        ? COMP_EMOTE_PLAYER_PHASE_LOOP
                        : COMP_EMOTE_PLAYER_PHASE_INTRO;
    mark_frame_ready(player);
    return true;
}

bool comp_emote_player_play_now(comp_emote_player_t *player,
                                uint16_t clip_index,
                                bool repeat)
{
    if (!select_clip(player, clip_index, repeat)) {
        return false;
    }
    player->immediate_switches++;
    return true;
}

bool comp_emote_player_play_now_name(comp_emote_player_t *player,
                                     const char *name,
                                     bool repeat)
{
    int index = player == NULL ? -1 : find_clip(player->catalog, name);
    return index >= 0 && comp_emote_player_play_now(player, (uint16_t)index, repeat);
}

bool comp_emote_player_play_after_tail(comp_emote_player_t *player,
                                       uint16_t clip_index,
                                       bool repeat)
{
    if (player == NULL || player->catalog == NULL ||
        clip_index >= player->catalog->clip_count) {
        return false;
    }
    if (player->phase == COMP_EMOTE_PLAYER_PHASE_STOPPED ||
        player->current_clip == COMP_EMOTE_PLAYER_NO_CLIP) {
        return comp_emote_player_play_now(player, clip_index, repeat);
    }
    player->pending_clip = clip_index;
    player->pending_repeat = repeat;
    player->handoff_pending = true;
    player->revision++;
    return true;
}

bool comp_emote_player_play_after_tail_name(comp_emote_player_t *player,
                                            const char *name,
                                            bool repeat)
{
    int index = player == NULL ? -1 : find_clip(player->catalog, name);
    return index >= 0 &&
           comp_emote_player_play_after_tail(player, (uint16_t)index, repeat);
}

void comp_emote_player_stop(comp_emote_player_t *player)
{
    if (player == NULL) {
        return;
    }
    player->current_clip = COMP_EMOTE_PLAYER_NO_CLIP;
    player->pending_clip = COMP_EMOTE_PLAYER_NO_CLIP;
    player->frame_in_clip = 0u;
    player->frame_elapsed_ms = 0u;
    player->repeat = false;
    player->pending_repeat = false;
    player->handoff_pending = false;
    player->frame_ready = false;
    player->phase = COMP_EMOTE_PLAYER_PHASE_STOPPED;
    player->revision++;
}

static void stop_on_current_frame(comp_emote_player_t *player)
{
    player->phase = COMP_EMOTE_PLAYER_PHASE_STOPPED;
    player->frame_elapsed_ms = 0u;
    player->revision++;
}

static bool switch_to_pending(comp_emote_player_t *player)
{
    uint16_t pending = player->pending_clip;
    bool repeat = player->pending_repeat;

    if (!player->handoff_pending || pending == COMP_EMOTE_PLAYER_NO_CLIP) {
        return false;
    }
    if (!select_clip(player, pending, repeat)) {
        return false;
    }
    player->tail_handoffs++;
    return true;
}

static bool advance_frame(comp_emote_player_t *player)
{
    const comp_emote_clip_t *clip = current_clip(player);
    bool segmented;

    if (clip == NULL || player->phase == COMP_EMOTE_PLAYER_PHASE_STOPPED) {
        return false;
    }
    segmented = clip_has_segments(clip);
    if (!segmented) {
        if ((uint16_t)(player->frame_in_clip + 1u) < clip->frame_count) {
            player->frame_in_clip++;
            mark_frame_ready(player);
            return true;
        }
        if (player->handoff_pending) {
            return switch_to_pending(player);
        }
        if (player->repeat) {
            player->frame_in_clip = 0u;
            mark_frame_ready(player);
            return true;
        }
        stop_on_current_frame(player);
        return false;
    }

    if (player->phase == COMP_EMOTE_PLAYER_PHASE_INTRO) {
        if ((uint16_t)(player->frame_in_clip + 1u) < clip->loop_start) {
            player->frame_in_clip++;
            mark_frame_ready(player);
            return true;
        }
        if (player->handoff_pending) {
            if (clip->loop_end < clip->frame_count) {
                player->frame_in_clip = clip->loop_end;
                player->phase = COMP_EMOTE_PLAYER_PHASE_TAIL;
                mark_frame_ready(player);
                return true;
            }
            return switch_to_pending(player);
        }
        player->frame_in_clip = clip->loop_start;
        player->phase = COMP_EMOTE_PLAYER_PHASE_LOOP;
        mark_frame_ready(player);
        return true;
    }

    if (player->phase == COMP_EMOTE_PLAYER_PHASE_LOOP) {
        if (player->handoff_pending) {
            if (clip->loop_end < clip->frame_count) {
                player->frame_in_clip = clip->loop_end;
                player->phase = COMP_EMOTE_PLAYER_PHASE_TAIL;
                mark_frame_ready(player);
                return true;
            }
            return switch_to_pending(player);
        }
        if ((uint16_t)(player->frame_in_clip + 1u) < clip->loop_end) {
            player->frame_in_clip++;
            mark_frame_ready(player);
            return true;
        }
        if (player->repeat) {
            player->frame_in_clip = clip->loop_start;
            mark_frame_ready(player);
            return true;
        }
        if (clip->loop_end < clip->frame_count) {
            player->frame_in_clip = clip->loop_end;
            player->phase = COMP_EMOTE_PLAYER_PHASE_TAIL;
            mark_frame_ready(player);
            return true;
        }
        stop_on_current_frame(player);
        return false;
    }

    if ((uint16_t)(player->frame_in_clip + 1u) < clip->frame_count) {
        player->frame_in_clip++;
        mark_frame_ready(player);
        return true;
    }
    if (player->handoff_pending) {
        return switch_to_pending(player);
    }
    stop_on_current_frame(player);
    return false;
}

bool comp_emote_player_tick(comp_emote_player_t *player, uint32_t elapsed_ms)
{
    bool changed = false;
    const comp_emote_frame_t *frame;

    if (player == NULL || elapsed_ms == 0u ||
        player->phase == COMP_EMOTE_PLAYER_PHASE_STOPPED) {
        return false;
    }
    player->frame_elapsed_ms += elapsed_ms;
    while ((frame = current_frame(player)) != NULL &&
           player->frame_elapsed_ms >= frame->duration_ms) {
        player->frame_elapsed_ms -= frame->duration_ms;
        if (!advance_frame(player)) {
            break;
        }
        changed = true;
    }
    return changed;
}

bool comp_emote_player_tick_sequential(comp_emote_player_t *player,
                                       uint32_t elapsed_ms)
{
    const comp_emote_frame_t *frame;

    if (player == NULL || elapsed_ms == 0u || player->frame_ready ||
        player->phase == COMP_EMOTE_PLAYER_PHASE_STOPPED) {
        return false;
    }
    if (UINT32_MAX - player->frame_elapsed_ms < elapsed_ms) {
        player->frame_elapsed_ms = UINT32_MAX;
    } else {
        player->frame_elapsed_ms += elapsed_ms;
    }
    frame = current_frame(player);
    if (frame == NULL || player->frame_elapsed_ms < frame->duration_ms) {
        return false;
    }

    /* Interactive CEMP frames are authored poses, not disposable video
     * samples. Drop late wall-clock debt so a slow physical panel never
     * overwrites an unshown pose while trying to catch up. */
    player->frame_elapsed_ms = 0u;
    return advance_frame(player);
}

uint32_t comp_emote_player_next_frame_in_ms(const comp_emote_player_t *player)
{
    const comp_emote_frame_t *frame = current_frame(player);

    if (frame == NULL || player->phase == COMP_EMOTE_PLAYER_PHASE_STOPPED) {
        return 0u;
    }
    return player->frame_elapsed_ms >= frame->duration_ms
               ? 1u
               : (uint32_t)frame->duration_ms - player->frame_elapsed_ms;
}

bool comp_emote_player_take_frame(comp_emote_player_t *player,
                                  comp_emote_player_frame_t *out_frame)
{
    const comp_emote_clip_t *clip;
    const comp_emote_frame_t *frame;

    if (player == NULL || out_frame == NULL || !player->frame_ready) {
        return false;
    }
    clip = current_clip(player);
    frame = current_frame(player);
    if (clip == NULL || frame == NULL) {
        return false;
    }
    *out_frame = (comp_emote_player_frame_t){
        .clip_name = clip->name,
        .frame = *frame,
        .clip_index = player->current_clip,
        .frame_index = (uint16_t)(clip->first_frame + player->frame_in_clip),
        .frame_in_clip = player->frame_in_clip,
        .phase = player->phase,
        .revision = player->revision,
    };
    player->frame_ready = false;
    player->emitted_frames++;
    return true;
}

void comp_emote_player_snapshot(const comp_emote_player_t *player,
                                comp_emote_player_snapshot_t *out_snapshot)
{
    if (out_snapshot == NULL) {
        return;
    }
    memset(out_snapshot, 0, sizeof(*out_snapshot));
    out_snapshot->current_clip = COMP_EMOTE_PLAYER_NO_CLIP;
    out_snapshot->pending_clip = COMP_EMOTE_PLAYER_NO_CLIP;
    if (player == NULL) {
        return;
    }
    out_snapshot->playing = player->phase != COMP_EMOTE_PLAYER_PHASE_STOPPED;
    out_snapshot->repeat = player->repeat;
    out_snapshot->handoff_pending = player->handoff_pending;
    out_snapshot->frame_ready = player->frame_ready;
    out_snapshot->current_clip = player->current_clip;
    out_snapshot->pending_clip = player->pending_clip;
    out_snapshot->frame_in_clip = player->frame_in_clip;
    out_snapshot->frame_elapsed_ms = player->frame_elapsed_ms;
    out_snapshot->revision = player->revision;
    out_snapshot->emitted_frames = player->emitted_frames;
    out_snapshot->skipped_frames = player->skipped_frames;
    out_snapshot->immediate_switches = player->immediate_switches;
    out_snapshot->tail_handoffs = player->tail_handoffs;
    out_snapshot->phase = player->phase;
}

bool comp_emote_player_self_test(void)
{
    static const comp_emote_frame_t frames[] = {
        {.data_offset = 0u, .data_size = 1u, .duration_ms = 10u},
        {.data_offset = 1u, .data_size = 1u, .duration_ms = 10u},
        {.data_offset = 2u, .data_size = 1u, .duration_ms = 10u},
        {.data_offset = 3u, .data_size = 1u, .duration_ms = 10u},
        {.data_offset = 4u, .data_size = 1u, .duration_ms = 10u},
        {.data_offset = 5u, .data_size = 1u, .duration_ms = 20u},
        {.data_offset = 6u, .data_size = 1u, .duration_ms = 20u},
    };
    static const comp_emote_clip_t clips[] = {
        {.name = "idle", .first_frame = 0u, .frame_count = 5u,
         .loop_start = 1u, .loop_end = 3u},
        {.name = "happy", .first_frame = 5u, .frame_count = 2u},
    };
    static const comp_emote_catalog_t catalog = {
        .clips = clips,
        .clip_count = 2u,
        .frames = frames,
        .frame_count = 7u,
    };
    comp_emote_player_t player;
    comp_emote_player_frame_t frame;
    comp_emote_player_snapshot_t snapshot;
    uint32_t sequential_skipped_before;

    if (!comp_emote_player_init(&player, &catalog) ||
        !comp_emote_player_play_now_name(&player, "idle", true) ||
        comp_emote_player_next_frame_in_ms(&player) != 10u ||
        !comp_emote_player_take_frame(&player, &frame) ||
        frame.frame_in_clip != 0u || frame.phase != COMP_EMOTE_PLAYER_PHASE_INTRO) {
        return false;
    }
    if (!comp_emote_player_tick(&player, 10u) ||
        !comp_emote_player_take_frame(&player, &frame) ||
        frame.frame_in_clip != 1u || frame.phase != COMP_EMOTE_PLAYER_PHASE_LOOP) {
        return false;
    }
    if (!comp_emote_player_play_after_tail_name(&player, "happy", false) ||
        !comp_emote_player_tick(&player, 10u) ||
        !comp_emote_player_take_frame(&player, &frame) ||
        frame.frame_in_clip != 3u || frame.phase != COMP_EMOTE_PLAYER_PHASE_TAIL) {
        return false;
    }
    if (!comp_emote_player_tick(&player, 20u) ||
        !comp_emote_player_take_frame(&player, &frame) ||
        strcmp(frame.clip_name, "happy") != 0 || frame.frame_in_clip != 0u) {
        return false;
    }
    comp_emote_player_tick(&player, 40u);
    comp_emote_player_snapshot(&player, &snapshot);
    if (snapshot.playing || snapshot.tail_handoffs != 1u ||
        snapshot.immediate_switches != 1u ||
        comp_emote_player_play_now_name(&player, "missing", true) ||
        !comp_emote_player_play_now_name(&player, "idle", true) ||
        !comp_emote_player_take_frame(&player, &frame)) {
        return false;
    }
    comp_emote_player_snapshot(&player, &snapshot);
    sequential_skipped_before = snapshot.skipped_frames;
    if (!comp_emote_player_play_now_name(&player, "happy", false) ||
        !comp_emote_player_take_frame(&player, &frame) ||
        frame.frame_in_clip != 0u ||
        !comp_emote_player_tick_sequential(&player, 100u) ||
        !comp_emote_player_take_frame(&player, &frame) ||
        frame.frame_in_clip != 1u ||
        comp_emote_player_tick_sequential(&player, 19u) ||
        comp_emote_player_next_frame_in_ms(&player) != 1u ||
        comp_emote_player_tick_sequential(&player, 1u)) {
        return false;
    }
    comp_emote_player_snapshot(&player, &snapshot);
    if (snapshot.playing ||
        snapshot.skipped_frames != sequential_skipped_before) {
        return false;
    }
    comp_emote_player_stop(&player);
    comp_emote_player_snapshot(&player, &snapshot);
    return !snapshot.playing && !snapshot.frame_ready &&
           snapshot.current_clip == COMP_EMOTE_PLAYER_NO_CLIP;
}
