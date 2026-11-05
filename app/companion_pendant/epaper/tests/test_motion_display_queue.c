#include "display_queue.h"

#include <stdio.h>

static int require_true(int condition, const char *message)
{
    if (!condition) {
        fprintf(stderr, "FAIL: %s\n", message);
        return 1;
    }
    return 0;
}

static comp_epaper_display_queue_result_t enqueue_expression_mode(
    comp_epaper_display_queue_t *queue,
    uint16_t flags,
    uint32_t request_id,
    comp_epaper_refresh_mode_t refresh_mode)
{
    comp_epaper_expression_decision_t decision;

    if (!comp_epaper_expression_decide(COMP_EPAPER_EXPRESSION_SIGNAL_BOOT_IDLE,
                                       &decision)) {
        return COMP_EPAPER_DISPLAY_QUEUE_UNSUPPORTED_EXPRESSION;
    }
    return comp_epaper_display_queue_enqueue_expression_frame(
               queue,
               1u,
               flags,
               0u,
               request_id,
               &decision,
               0u,
               refresh_mode,
               4u,
               4u,
               192u,
               192u,
               request_id);
}

static int enqueue_expression(comp_epaper_display_queue_t *queue,
                              uint16_t flags,
                              uint32_t request_id)
{
    return enqueue_expression_mode(
               queue, flags, request_id,
               COMP_EPAPER_REFRESH_PARTIAL_INTERACTIVE) ==
                   COMP_EPAPER_DISPLAY_QUEUE_OK
               ? 0
               : 1;
}

int main(void)
{
    comp_epaper_display_queue_t queue;
    comp_epaper_display_request_t request;
    comp_epaper_expression_decision_t overlay_decision;

    comp_epaper_display_queue_init(&queue);
    if (require_true(
            comp_epaper_expression_decide(
                COMP_EPAPER_EXPRESSION_SIGNAL_BOOT_IDLE,
                &overlay_decision),
            "recording overlay keeps the home expression identity") ||
        require_true(
            comp_epaper_display_queue_enqueue_expression_frame_with_recording_overlay(
                &queue,
                1u,
                COMP_EPAPER_DISPLAY_FLAG_AUTO_ACCESSORY,
                0u,
                true,
                true,
                133u,
                0x775638AAu,
                0x1934AB77u,
                COMP_EPAPER_DISPLAY_CLASS_RECORDING,
                91u,
                &overlay_decision,
                42u,
                COMP_EPAPER_REFRESH_PARTIAL_INTERACTIVE,
                2u,
                156u,
                40u,
                24u,
                0xA55AA55Au) == COMP_EPAPER_DISPLAY_QUEUE_OK,
            "independent recording overlay queues") ||
        require_true(
            comp_epaper_display_queue_dequeue(&queue, &request) &&
                request.request_id == 91u &&
                request.asset_frame_index == 42u &&
                request.recording_overlay_present == 1u &&
                request.recording_overlay_only == 1u &&
                request.display_class == COMP_EPAPER_DISPLAY_CLASS_RECORDING &&
                request.recording_overlay_frame_index == 133u &&
                request.asset_state_hash == 0x775638AAu &&
                request.recording_overlay_state_hash == 0x1934AB77u,
            "recording overlay identity survives dequeue")) {
        return 1;
    }

    comp_epaper_display_queue_init(&queue);
    if (require_true(enqueue_expression(&queue, 0u, 101u) == 0,
                     "manual expression queues") ||
        require_true(enqueue_expression(&queue,
                                        COMP_EPAPER_DISPLAY_FLAG_AUTO_MOTION,
                                        102u) == 0,
                     "automatic expression queues") ||
        require_true(enqueue_expression(&queue,
                                        COMP_EPAPER_DISPLAY_FLAG_AUTO_MOTION,
                                        103u) == 0,
                     "second automatic expression queues for cancellation test") ||
        require_true(comp_epaper_display_queue_discard_display_flags(
                         &queue, COMP_EPAPER_DISPLAY_FLAG_AUTO_MOTION) == 2u,
                     "event cancellation removes every pending automatic frame") ||
        require_true(comp_epaper_display_queue_pending(&queue) == 1u,
                     "manual request survives automatic-frame cancellation") ||
        require_true(comp_epaper_display_queue_dequeue(&queue, &request) &&
                         request.request_id == 101u && request.display_flags == 0u,
                     "surviving manual request keeps its identity and flags") ||
        require_true(!comp_epaper_display_queue_dequeue(&queue, &request),
                     "automatic frames cannot reappear after cancellation")) {
        return 1;
    }

    comp_epaper_display_queue_init(&queue);
    if (require_true(enqueue_expression(&queue, 0u, 151u) == 0,
                     "base frame queues before class discard") ||
        require_true(
            comp_epaper_expression_decide(
                COMP_EPAPER_EXPRESSION_SIGNAL_BOOT_IDLE,
                &overlay_decision),
            "touch-class expression resolves") ||
        require_true(
            comp_epaper_display_queue_enqueue_expression_frame_with_recording_overlay(
                &queue, 1u, 0u, 0u, false, false, 0u, 0u, 0u,
                COMP_EPAPER_DISPLAY_CLASS_TOUCH, 152u, &overlay_decision, 0u,
                COMP_EPAPER_REFRESH_PARTIAL_INTERACTIVE,
                0u, 0u, 200u, 200u, 152u) == COMP_EPAPER_DISPLAY_QUEUE_OK,
            "touch frame queues with explicit class") ||
        require_true(comp_epaper_display_queue_discard_display_class(
                         &queue, COMP_EPAPER_DISPLAY_CLASS_TOUCH) == 1u,
                     "recording intent can discard only stale touch frames") ||
        require_true(comp_epaper_display_queue_pending(&queue) == 1u,
                     "base frame survives touch-class discard") ||
        require_true(comp_epaper_display_queue_dequeue(&queue, &request) &&
                         request.request_id == 151u,
                     "surviving base frame keeps FIFO identity")) {
        return 1;
    }

    comp_epaper_display_queue_init(&queue);
    if (require_true(enqueue_expression_mode(
                         &queue, 0u, 200u,
                         COMP_EPAPER_REFRESH_IDLE_ENTER_STRONG) ==
                         COMP_EPAPER_DISPLAY_QUEUE_OK,
                     "idle-enter strong boundary queues") ||
        require_true(comp_epaper_display_queue_dequeue(&queue, &request) &&
                         request.request_id == 200u &&
                         comp_epaper_display_request_is_boundary(&request),
                     "idle-enter strong mode owns a boundary") ||
        require_true(comp_epaper_display_queue_complete(&queue, 200u),
                     "idle-enter strong boundary completes")) {
        return 1;
    }

    comp_epaper_display_queue_init(&queue);
    if (require_true(enqueue_expression(&queue, 0u, 201u) == 0,
                     "ordinary frame queues before boundary") ||
        require_true(enqueue_expression_mode(
                         &queue, 0u, 202u,
                         COMP_EPAPER_REFRESH_MAINTENANCE) ==
                         COMP_EPAPER_DISPLAY_QUEUE_OK,
                     "boundary queues") ||
        require_true(comp_epaper_display_queue_pending(&queue) == 1u,
                     "boundary supersedes queued ordinary frames") ||
        require_true(comp_epaper_display_queue_boundary_owned(&queue),
                     "pending boundary owns display") ||
        require_true(enqueue_expression_mode(
                         &queue, 0u, 203u,
                         COMP_EPAPER_REFRESH_PARTIAL) ==
                         COMP_EPAPER_DISPLAY_QUEUE_BOUNDARY_OWNS_DISPLAY,
                     "pending boundary rejects ordinary frame") ||
        require_true(comp_epaper_display_queue_discard_display_class(
                         &queue, COMP_EPAPER_DISPLAY_CLASS_BASE) == 0u,
                     "class discard cannot remove a pending boundary") ||
        require_true(comp_epaper_display_queue_discard_kind(
                         &queue, COMP_EPAPER_DISPLAY_REQUEST_EXPRESSION) == 0u,
                     "feature discard cannot remove boundary") ||
        require_true(comp_epaper_display_queue_dequeue(&queue, &request) &&
                         request.request_id == 202u &&
                         comp_epaper_display_request_is_boundary(&request),
                     "boundary dequeues with identity") ||
        require_true(comp_epaper_display_queue_boundary_owned(&queue),
                     "dequeued boundary remains owned until commit") ||
        require_true(enqueue_expression_mode(
                         &queue, 0u, 204u,
                         COMP_EPAPER_REFRESH_PARTIAL) ==
                         COMP_EPAPER_DISPLAY_QUEUE_BOUNDARY_OWNS_DISPLAY,
                     "in-flight boundary rejects ordinary frame") ||
        require_true(!comp_epaper_display_queue_complete(&queue, 999u),
                     "wrong completion cannot release boundary") ||
        require_true(comp_epaper_display_queue_complete(&queue, 202u),
                     "matching panel commit releases boundary") ||
        require_true(!comp_epaper_display_queue_boundary_owned(&queue),
                     "boundary ownership clears after commit") ||
        require_true(enqueue_expression(&queue, 0u, 205u) == 0,
                     "ordinary frame resumes after boundary commit")) {
        return 1;
    }

    comp_epaper_display_queue_init(&queue);
    for (uint32_t id = 301u; id < 305u; ++id) {
        if (require_true(enqueue_expression_mode(
                             &queue, 0u, id,
                             COMP_EPAPER_REFRESH_MAINTENANCE) ==
                             COMP_EPAPER_DISPLAY_QUEUE_OK,
                         "boundary queue fills deterministically")) {
            return 1;
        }
    }
    if (require_true(enqueue_expression_mode(
                         &queue, 0u, 305u,
                         COMP_EPAPER_REFRESH_MAINTENANCE) ==
                         COMP_EPAPER_DISPLAY_QUEUE_FULL,
                     "boundary queue full fails closed") ||
        require_true(comp_epaper_display_queue_dequeue(&queue, &request) &&
                         request.request_id == 301u,
                     "queued boundaries preserve FIFO order") ||
        require_true(comp_epaper_display_queue_complete(&queue, 301u),
                     "first boundary completes") ||
        require_true(comp_epaper_display_queue_boundary_owned(&queue),
                     "later pending boundary retains ownership") ||
        require_true(enqueue_expression(&queue, 0u, 306u) != 0,
                     "ordinary frame cannot enter between boundaries")) {
        return 1;
    }

    comp_epaper_display_queue_init(&queue);
    if (require_true(enqueue_expression_mode(
                         &queue, 0u, 401u,
                         COMP_EPAPER_REFRESH_MAINTENANCE) ==
                         COMP_EPAPER_DISPLAY_QUEUE_OK,
                     "generation test boundary queues") ||
        require_true(comp_epaper_display_queue_dequeue(&queue, &request),
                     "generation test boundary dequeues") ||
        require_true(comp_epaper_display_queue_boundary_owned(&queue),
                     "generation test owns boundary")) {
        return 1;
    }
    comp_epaper_display_queue_set_resource_revision(&queue, 17u);
    if (require_true(!comp_epaper_display_queue_boundary_owned(&queue),
                     "generation switch clears obsolete ownership") ||
        require_true(enqueue_expression(&queue, 0u, 402u) == 0,
                     "new generation can submit ordinary frame")) {
        return 1;
    }

    puts("PASS: display transaction arbiter protects boundaries through panel commit");
    return 0;
}
