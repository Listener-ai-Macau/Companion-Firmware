#include "microphone_hal.h"
#if COMPANION_WBA_CE_SHARED_CAPTURE
#include "companion_opus16_rt.h"
_Static_assert(COMP_V11_MIC_RAW_DMA_BYTES==COMPANION_CE_DMA_BYTES,"CE shared DMA geometry");
#endif
#include "capture_encode_window.h"
#include "companion_cpu_stage.h"

#include <string.h>

/* Same capture/queue/stop implementation on both families. Only the DMA
 * instance, request and IRQ change; pin mux and kernel clock remain owned by
 * the actual board. Its IRQ wrapper must dispatch this selected channel. */
#if defined(STM32WBA25xx)
#define COMP_V11_MIC_DMA_CHANNEL LPDMA1_Channel1
#define COMP_V11_MIC_DMA_NODE DMA_LPDMA_LINEAR_NODE
#define COMP_V11_MIC_DMA_REQUEST LPDMA1_REQUEST_SAI1_A
#define COMP_V11_MIC_DMA_IRQ LPDMA1_Channel1_IRQn
#define COMP_V11_MIC_DMA_CLOCK_ENABLE() __HAL_RCC_LPDMA1_CLK_ENABLE()
#else
#define COMP_V11_MIC_DMA_CHANNEL GPDMA1_Channel1
#define COMP_V11_MIC_DMA_NODE DMA_GPDMA_LINEAR_NODE
#define COMP_V11_MIC_DMA_REQUEST GPDMA1_REQUEST_SAI1_A
#define COMP_V11_MIC_DMA_IRQ GPDMA1_Channel1_IRQn
#define COMP_V11_MIC_DMA_CLOCK_ENABLE() __HAL_RCC_GPDMA1_CLK_ENABLE()
#endif

_Static_assert(COMP_V11_MIC_RAW_DMA_BYTES % sizeof(uint32_t) == 0u,
               "DMA buffer must be word sized");
_Static_assert(COMP_V11_MIC_RAW_HALF_BYTES % sizeof(uint32_t) == 0u,
               "processing buffer must be word sized");
_Static_assert(COMP_V11_MIC_DMA_TRANSFER_HALFWORDS <= UINT16_MAX,
               "HAL SAI transfer size must fit uint16_t");
_Static_assert(COMP_V11_MIC_EVENT_QUEUE_CAPACITY > 2u,
               "event queue must hold both DMA halves");
_Static_assert(COMP_V11_MIC_NOMINAL_PDM_HZ >= 1100000u &&
               COMP_V11_MIC_NOMINAL_PDM_HZ <= 4800000u,
               "SPH0655 recording clock must stay in normal mode");

static uint8_t *raw_dma_bytes(comp_v11_microphone_hal_t *microphone)
{
    return (uint8_t *)microphone->raw_dma_words;
}

static bool configure_dma(comp_v11_microphone_hal_t *microphone)
{
    DMA_NodeConfTypeDef node;

    memset(&node, 0, sizeof(node));
    microphone->dma.Instance = COMP_V11_MIC_DMA_CHANNEL;
    microphone->dma.InitLinkedList.Priority = DMA_HIGH_PRIORITY;
    microphone->dma.InitLinkedList.LinkStepMode = DMA_LSM_FULL_EXECUTION;
    microphone->dma.InitLinkedList.LinkAllocatedPort = DMA_LINK_ALLOCATED_PORT0;
    microphone->dma.InitLinkedList.TransferEventMode = DMA_TCEM_BLOCK_TRANSFER;
    microphone->dma.InitLinkedList.LinkedListMode = DMA_LINKEDLIST_CIRCULAR;
    if (HAL_DMAEx_List_Init(&microphone->dma) != HAL_OK) return false;

    node.NodeType = COMP_V11_MIC_DMA_NODE;
    node.Init.Request = COMP_V11_MIC_DMA_REQUEST;
    node.Init.BlkHWRequest = DMA_BREQ_SINGLE_BURST;
    node.Init.Direction = DMA_PERIPH_TO_MEMORY;
    node.Init.SrcInc = DMA_SINC_FIXED;
    node.Init.DestInc = DMA_DINC_INCREMENTED;
    node.Init.SrcDataWidth = DMA_SRC_DATAWIDTH_HALFWORD;
    node.Init.DestDataWidth = DMA_DEST_DATAWIDTH_HALFWORD;
    node.Init.Priority = DMA_HIGH_PRIORITY;
    node.Init.SrcBurstLength = 1u;
    node.Init.DestBurstLength = 1u;
    node.Init.TransferAllocatedPort =
        DMA_SRC_ALLOCATED_PORT0 | DMA_DEST_ALLOCATED_PORT0;
    node.Init.TransferEventMode = DMA_TCEM_BLOCK_TRANSFER;
    node.Init.Mode = DMA_NORMAL;
    node.DataHandlingConfig.DataExchange = DMA_EXCHANGE_NONE;
    node.DataHandlingConfig.DataAlignment = DMA_DATA_RIGHTALIGN_ZEROPADDED;
    node.TriggerConfig.TriggerMode = DMA_TRIGM_BLOCK_TRANSFER;
    node.TriggerConfig.TriggerPolarity = DMA_TRIG_POLARITY_MASKED;
    node.TriggerConfig.TriggerSelection = 0u;
    node.SrcAddress = (uint32_t)(uintptr_t)&SAI1_Block_A->DR;
    node.DstAddress = (uint32_t)(uintptr_t)raw_dma_bytes(microphone);
    node.DataSize = COMP_V11_MIC_RAW_DMA_BYTES;

    return HAL_DMAEx_List_BuildNode(&node, &microphone->dma_node) == HAL_OK &&
           HAL_DMAEx_List_InsertNode_Tail(
               &microphone->dma_queue, &microphone->dma_node) == HAL_OK &&
           HAL_DMAEx_List_SetCircularMode(&microphone->dma_queue) == HAL_OK &&
           HAL_DMAEx_List_LinkQ(
               &microphone->dma, &microphone->dma_queue) == HAL_OK;
}

static bool configure_sai(comp_v11_microphone_hal_t *microphone)
{
    SAI_HandleTypeDef *sai = &microphone->sai;

    sai->Instance = SAI1_Block_A;
    sai->Init.AudioMode = SAI_MODEMASTER_RX;
    sai->Init.Synchro = SAI_ASYNCHRONOUS;
    sai->Init.SynchroExt = SAI_SYNCEXT_DISABLE;
    sai->Init.MckOutput = SAI_MCK_OUTPUT_DISABLE;
    sai->Init.OutputDrive = SAI_OUTPUTDRIVE_ENABLE;
    sai->Init.NoDivider = SAI_MASTERDIVIDER_DISABLE;
    sai->Init.FIFOThreshold = SAI_FIFOTHRESHOLD_HF;
    sai->Init.AudioFrequency = SAI_AUDIO_FREQUENCY_MCKDIV;
    sai->Init.Mckdiv = COMP_V11_MIC_SAI_MCKDIV;
    sai->Init.MckOverSampling = SAI_MCK_OVERSAMPLING_DISABLE;
    sai->Init.MonoStereoMode = SAI_STEREOMODE;
    sai->Init.CompandingMode = SAI_NOCOMPANDING;
    sai->Init.TriState = SAI_OUTPUT_NOTRELEASED;
    sai->Init.Protocol = SAI_FREE_PROTOCOL;
    sai->Init.DataSize = SAI_DATASIZE_16;
    sai->Init.FirstBit = SAI_FIRSTBIT_MSB;
    sai->Init.ClockStrobing = SAI_CLOCKSTROBING_FALLINGEDGE;
    sai->Init.PdmInit.Activation = ENABLE;
    sai->Init.PdmInit.MicPairsNbr = 1u;
    sai->Init.PdmInit.ClockEnable = SAI_PDM_CLOCK1_ENABLE;

    sai->FrameInit.FrameLength = 16u;
    sai->FrameInit.ActiveFrameLength = 1u;
    sai->FrameInit.FSDefinition = SAI_FS_STARTFRAME;
    sai->FrameInit.FSPolarity = SAI_FS_ACTIVE_HIGH;
    /* RM0493 Table 409: PDM TDM starts on the first bit of slot 0.
     * An I2S-style one-bit lead is not the PDM receive framing. */
    sai->FrameInit.FSOffset = SAI_FS_FIRSTBIT;
    sai->SlotInit.FirstBitOffset = 0u;
    sai->SlotInit.SlotSize = SAI_SLOTSIZE_DATASIZE;
    sai->SlotInit.SlotNumber = 1u;
    sai->SlotInit.SlotActive = SAI_SLOTACTIVE_0;

    __HAL_LINKDMA(sai, hdmarx, microphone->dma);
    return HAL_SAI_Init(sai) == HAL_OK;
}

static void clear_events(comp_v11_microphone_hal_t *microphone)
{
    uint32_t primask = __get_PRIMASK();

    __disable_irq();
    microphone->event_head = 0u;
    microphone->event_tail = 0u;
    microphone->next_sequence = 0u;
    microphone->latest_half_sequence[0] = UINT32_MAX;
    microphone->latest_half_sequence[1] = UINT32_MAX;
    microphone->writing_half = 0u;
    microphone->startup_halves_remaining = 0u;
    microphone->error_pending = false;
    __DMB();
    __set_PRIMASK(primask);
}

static void publish_event(comp_v11_microphone_hal_t *microphone, uint8_t half)
{
    uint32_t sequence = microphone->next_sequence++;
    uint8_t head = microphone->event_head;
    uint8_t next = (uint8_t)((head + 1u) % COMP_V11_MIC_EVENT_QUEUE_CAPACITY);

    microphone->latest_half_sequence[half] = sequence;
    microphone->writing_half = (uint8_t)(half ^ 1u);
    if (next == microphone->event_tail) {
        microphone->event_queue_overflows++;
        return;
    }
    microphone->events[head].half = half;
    microphone->events[head].sequence = sequence;
    __DMB();
    microphone->event_head = next;
}

static bool pop_event(comp_v11_microphone_hal_t *microphone,
                      comp_v11_microphone_event_t *event)
{
    uint32_t primask = __get_PRIMASK();
    uint8_t tail;

    __disable_irq();
    tail = microphone->event_tail;
    if (tail == microphone->event_head) {
        __set_PRIMASK(primask);
        return false;
    }
    __DMB();
    event->half = microphone->events[tail].half;
    event->sequence = microphone->events[tail].sequence;
    microphone->event_tail =
        (uint8_t)((tail + 1u) % COMP_V11_MIC_EVENT_QUEUE_CAPACITY);
    __set_PRIMASK(primask);
    return true;
}

static bool half_is_current(comp_v11_microphone_hal_t *microphone,
                            const comp_v11_microphone_event_t *event)
{
    uint32_t primask = __get_PRIMASK();
    uint32_t remaining;
    uint8_t hardware_writing_half;
    bool current;

    __disable_irq();
    remaining = __HAL_DMA_GET_COUNTER(&microphone->dma);
    /* CBR1 counts bytes remaining in the circular node. Values
     * above the midpoint mean the first half is being filled; values at or
     * below it mean the second half. Zero is treated as the imminent circular
     * reload into half zero. This closes the window where DMA has crossed a
     * boundary but its IRQ has not yet updated writing_half/generation. */
    hardware_writing_half = (uint8_t)(
        (remaining == 0u || remaining > COMP_V11_MIC_RAW_HALF_BYTES) ? 0u : 1u);
    current = microphone->writing_half != event->half &&
              hardware_writing_half != event->half &&
              microphone->latest_half_sequence[event->half] == event->sequence;
    __set_PRIMASK(primask);
    return current;
}

typedef struct { const uint8_t *bytes; } stable_read_context_t;
static bool read_stable_frame(void *context,size_t offset,const uint8_t **bytes,size_t *count)
{
    const stable_read_context_t *read=context;
    if(offset>=COMP_V11_MIC_RAW_HALF_BYTES)return false;
    *bytes=read->bytes+offset;*count=COMP_V11_MIC_RAW_HALF_BYTES-offset;
    return true;
}
#if defined(_MSC_VER)
#define COMP_MIC_SNAPSHOT_NOINLINE __declspec(noinline)
#elif defined(__GNUC__)
#define COMP_MIC_SNAPSHOT_NOINLINE __attribute__((noinline,noclone))
#else
#define COMP_MIC_SNAPSHOT_NOINLINE
#endif
/* Copy while DMA still owns the OTHER half, validate the entire copy, then
 * release the live DMA address from the filter's lifetime. The3.84KiB frame
 * is on the already reserved stack, not new permanent RAM. This noinline
 * frame returns before the cooperative caller can run a full Opus encode.
 * IRQs remain enabled; crossing DMA reuse during memcpy rejects the frame. */
static COMP_MIC_SNAPSHOT_NOINLINE bool process_stable_half(
    comp_v11_microphone_hal_t *microphone,const comp_v11_microphone_event_t *event,
    bool priming,bool *stale)
{
    uint32_t stable[COMP_V11_MIC_RAW_HALF_BYTES/sizeof(uint32_t)];
    if(!half_is_current(microphone,event)){*stale=true;return false;}
    memcpy(stable,raw_dma_bytes(microphone)+(size_t)event->half*COMP_V11_MIC_RAW_HALF_BYTES,sizeof(stable));
    __DMB();
    if(!half_is_current(microphone,event)){*stale=true;return false;}
    const stable_read_context_t read={(const uint8_t *)stable};
    return comp_wba_pdm_capture_read_frame(&microphone->processing,read_stable_frame,
        (void *)&read,sizeof(stable),event->sequence,priming);
}

bool comp_v11_microphone_hal_init(
    comp_v11_microphone_hal_t *microphone,
    const comp_wba_pdm_config_t *processing_config)
{
    if (microphone == NULL || processing_config == NULL ||
        processing_config->decimation != COMP_V11_MIC_DECIMATION) {
        return false;
    }
    memset(microphone, 0, sizeof(*microphone));
#if COMPANION_WBA_CE_SHARED_CAPTURE
    microphone->raw_dma_words=companion_opus16_rt_dma_address(COMP_V11_MIC_RAW_DMA_BYTES);
    if(!microphone->raw_dma_words)return false;
#endif
    comp_wba_pdm_capture_init(&microphone->processing, processing_config);
    if (!comp_wba_pdm_capture_ready(&microphone->processing)) return false;

    __HAL_RCC_SAI1_CLK_ENABLE();
    COMP_V11_MIC_DMA_CLOCK_ENABLE();
    if (!configure_dma(microphone) || !configure_sai(microphone)) return false;

    microphone->configured_pdm_clock_hz = COMP_V11_MIC_NOMINAL_PDM_HZ;
    microphone->initialized = true;
    clear_events(microphone);
    HAL_NVIC_SetPriority(COMP_V11_MIC_DMA_IRQ, 2u, 0u);
    HAL_NVIC_EnableIRQ(COMP_V11_MIC_DMA_IRQ);
    HAL_NVIC_SetPriority(SAI1_IRQn, 2u, 0u);
    HAL_NVIC_EnableIRQ(SAI1_IRQn);
    return true;
}

bool comp_v11_microphone_hal_start(comp_v11_microphone_hal_t *microphone)
{
    if (microphone == NULL || !microphone->initialized || microphone->running) {
        return false;
    }
    clear_events(microphone);
    /* SPH0655 RevD Table2 allows35ms to wake/start. RM0493 first-bit
     * validity alone does not establish microphone acoustic settling.
     * With10ms DMA halves, skip the first30ms, prime CIC/DC exactly once
     * using the30..40ms half, then retain PCM from40ms onward. No blocking
     * sleep or fabricated silence; startup discard remains explicitly counted. */
    microphone->startup_halves_remaining = 4u;
    memset(&microphone->pdm_duration, 0, sizeof(microphone->pdm_duration));
    comp_wba_pdm_capture_reset_stream(&microphone->processing);
#if COMPANION_WBA_CE_SHARED_CAPTURE
    if(!companion_opus16_rt_dma_claim(microphone))return false;
#endif
    if (HAL_SAI_Receive_DMA(&microphone->sai, raw_dma_bytes(microphone),
                            (uint16_t)COMP_V11_MIC_DMA_TRANSFER_HALFWORDS) !=
        HAL_OK) {
#if COMPANION_WBA_CE_SHARED_CAPTURE
        /* A failed start may have armed a partial DMA. Do not return this
         * memory to OTA unless the actual DMA stop has succeeded. */
        if(!comp_v11_microphone_hal_stop(microphone)) {
            /* Transfer liveness is uncertain, not an idle buffer. Keep the
             * power/OTA exclusion and let the foreground error path stop it. */
            microphone->running=true;microphone->error_pending=true;
            microphone->partial_start_cleanup=true;microphone->partial_stop_attempts=0u;
            microphone->partial_stop_due_ms=HAL_GetTick();
        }
#endif
        return false;
    }
    microphone->running = true;
    microphone->starts++;
    return true;
}

bool comp_v11_microphone_hal_stop(comp_v11_microphone_hal_t *microphone)
{
    bool stopped;
    bool was_running;

    if (microphone == NULL || !microphone->initialized) return false;
    was_running = microphone->running;
    stopped = HAL_SAI_DMAStop(&microphone->sai) == HAL_OK;
#if COMPANION_WBA_CE_SHARED_CAPTURE
    /* CubeWBA SAI may mark its handle READY even if DMA abort timed out.
     * A later HAL_OK alone therefore cannot release shared capture memory. */
    __DMB();
    if (stopped && microphone->dma.Instance != NULL && microphone->sai.Instance != NULL &&
        (microphone->sai.Instance->CR1 & (SAI_xCR1_SAIEN | SAI_xCR1_DMAEN)) == 0u &&
        ((microphone->dma.Instance->CCR & DMA_CCR_EN) != 0u ||
         microphone->dma.State != HAL_DMA_STATE_READY) &&
        microphone->dma.LinkedListQueue == &microphone->dma_queue &&
        microphone->dma_queue.State == HAL_DMA_QUEUE_STATE_READY) {
        /* Only this capture channel is recovered, after block A has stopped.
         * Cube's linked-list init disables the channel and clears its transfer
         * registers so the original queue can be loaded on the next start.
         * Keep the shared workspace claimed if hardware still will not stop. */
        const uint32_t irq_enabled = NVIC_GetEnableIRQ(COMP_V11_MIC_DMA_IRQ);
        HAL_NVIC_DisableIRQ(COMP_V11_MIC_DMA_IRQ);
        const bool recovered = HAL_DMAEx_List_Init(&microphone->dma) == HAL_OK &&
            (microphone->dma.Instance->CCR & DMA_CCR_EN) == 0u;
        if (recovered) {
            __HAL_DMA_CLEAR_FLAG(&microphone->dma, DMA_FLAG_TC | DMA_FLAG_HT |
                DMA_FLAG_DTE | DMA_FLAG_ULE | DMA_FLAG_USE | DMA_FLAG_SUSP | DMA_FLAG_TO);
            HAL_NVIC_ClearPendingIRQ(COMP_V11_MIC_DMA_IRQ);
        }
        if (irq_enabled != 0u) HAL_NVIC_EnableIRQ(COMP_V11_MIC_DMA_IRQ);
        if (!recovered) return false;
    }
    if(!stopped||!microphone->dma.Instance||!microphone->sai.Instance||
       (microphone->dma.Instance->CCR&DMA_CCR_EN)!=0u||
       microphone->dma.State != HAL_DMA_STATE_READY||
       (microphone->sai.Instance->CR1&(SAI_xCR1_SAIEN|SAI_xCR1_DMAEN))!=0u)return false;
    companion_opus16_rt_dma_release(microphone);
#endif
    microphone->running = false;
    microphone->partial_start_cleanup=false;microphone->partial_stop_attempts=0u;
    clear_events(microphone);
    comp_wba_pdm_capture_reset_stream(&microphone->processing);
    if (was_running) microphone->stops++;
    return stopped;
}

static bool conversion_window_open(comp_v11_microphone_hal_t *microphone)
{
    if(!microphone->conversion_window || !microphone->running ||
       microphone->startup_halves_remaining>1u)return true;
    uint32_t mask=__get_PRIMASK();__disable_irq();
    uint8_t tail=microphone->event_tail;
    bool pending=tail!=microphone->event_head;
    comp_v11_microphone_event_t event={0};uint32_t remaining=0u;
    if(pending) {
        __DMB();event.half=microphone->events[tail].half;
        event.sequence=microphone->events[tail].sequence;
        remaining=__HAL_DMA_GET_COUNTER(&microphone->dma);
    }
    __set_PRIMASK(mask);
    /* A stale event must reach the existing fault accounting immediately. */
    return !pending || !half_is_current(microphone,&event) ||
        microphone->conversion_window(remaining,COMP_V11_MIC_RAW_HALF_BYTES);
}
static comp_v11_microphone_poll_result_t microphone_hal_poll_body(
    comp_v11_microphone_hal_t *microphone)
{
    comp_v11_microphone_event_t event;
    uint32_t primask;
    bool error;

    if (microphone == NULL || !microphone->initialized) {
        return COMP_V11_MIC_POLL_ERROR;
    }
    /* Failed start may have armed DMA even though the engine never acquired
     * capture. Its owner remains here until an actual stop succeeds. */
    if(microphone->partial_start_cleanup) {
        uint32_t now=HAL_GetTick();
        if(microphone->partial_stop_attempts<3u &&
           (int32_t)(now-microphone->partial_stop_due_ms)>=0) {
            ++microphone->partial_stop_attempts;microphone->partial_stop_due_ms=now+100u;
            (void)comp_v11_microphone_hal_stop(microphone);
        }
        return COMP_V11_MIC_POLL_ERROR;
    }
    primask = __get_PRIMASK();
    __disable_irq();
    error = microphone->error_pending;
    microphone->error_pending = false;
    __set_PRIMASK(primask);
    if (error) {
        /* Some SAI errors (for example CNRDY) deliberately leave a transfer
         * active in the CubeWBA HAL. Always quiesce Block A and Channel 1 in
         * foreground context before discarding state. */
        (void)comp_v11_microphone_hal_stop(microphone);
        return COMP_V11_MIC_POLL_ERROR;
    }
    if (!conversion_window_open(microphone)) return COMP_V11_MIC_POLL_IDLE;
    if (!pop_event(microphone, &event)) return COMP_V11_MIC_POLL_IDLE;
    if (!half_is_current(microphone, &event)) {
        microphone->stale_dma_halves++;
        return COMP_V11_MIC_POLL_DROPPED;
    }
    if (microphone->startup_halves_remaining > 1u) {
        /* These real DMA halves precede the sensor settling boundary. Do
         * not feed them to CIC/DC or call prime repeatedly: prime is a
         * single initial continuous span, not a reusable discard mode. */
        microphone->startup_halves_remaining--;
        microphone->startup_halves_discarded++;
        return COMP_V11_MIC_POLL_DROPPED;
    }
    bool priming = microphone->startup_halves_remaining != 0u;
    bool stale=false;
    comp_duration_stamp_t started=comp_duration_begin(HAL_GetTick());
    comp_cpu_stage_span_t cpu_span=comp_cpu_stage_begin();
    bool accepted=process_stable_half(microphone,&event,priming,&stale);
    comp_cpu_stage_end(COMP_CPU_STAGE_PDM,cpu_span,true); /* includes priming/failing conversion attempts */
    /* Include bounded DMA copies, the PCM handoff and interrupt time. Idle
     * polls have no sample; priming/failing conversion attempts stay visible. */
    comp_duration_end(&microphone->pdm_duration,started,HAL_GetTick());
    if (!accepted) {
        if (stale) microphone->stale_dma_halves++;
        else microphone->processing_rejections++;
        comp_wba_pdm_capture_reset_stream(&microphone->processing);
        return COMP_V11_MIC_POLL_DROPPED;
    }
    if (priming) {
        microphone->startup_halves_remaining--;
        microphone->startup_halves_discarded++;
        return COMP_V11_MIC_POLL_DROPPED;
    }
    microphone->processed_dma_halves++;
    return COMP_V11_MIC_POLL_PROCESSED;
}

comp_v11_microphone_poll_result_t comp_v11_microphone_hal_poll(comp_v11_microphone_hal_t *microphone)
{
    comp_cpu_stage_span_t cpu=comp_cpu_detail_begin();
    comp_v11_microphone_poll_result_t r=microphone_hal_poll_body(microphone);
    comp_cpu_detail_end(COMP_CPU_STAGE_MIC_POLL,cpu,true);
    return r;
}

bool comp_v11_microphone_hal_encode_window(comp_v11_microphone_hal_t *microphone)
{
    if (microphone == NULL || !microphone->initialized) return false;
    uint32_t primask = __get_PRIMASK();
    __disable_irq();
    bool allowed = !microphone->running;
    if (microphone->running) {
        uint32_t remaining = __HAL_DMA_GET_COUNTER(&microphone->dma);
        allowed = !microphone->error_pending &&
            comp_v11_capture_encode_window_open(remaining,
                COMP_V11_MIC_RAW_HALF_BYTES, microphone->writing_half,
                microphone->event_head != microphone->event_tail);
    }
    __set_PRIMASK(primask);
    return allowed;
}

void comp_v11_microphone_hal_fault_baseline(const comp_v11_microphone_hal_t *microphone,
                                             comp_v11_microphone_fault_baseline_t *out)
{
    if (!microphone || !out) return;
    uint32_t primask=__get_PRIMASK();
    __disable_irq();
    out->error_irqs=microphone->error_irqs;
    out->event_queue_overflows=microphone->event_queue_overflows;
    out->stale_dma_halves=microphone->stale_dma_halves;
    out->processing_rejections=microphone->processing_rejections;
    __set_PRIMASK(primask);
}
bool comp_v11_microphone_hal_fault_baseline_matches(const comp_v11_microphone_hal_t *microphone,
                                             const comp_v11_microphone_fault_baseline_t *baseline)
{
    if (!microphone || !baseline) return false;
    uint32_t primask=__get_PRIMASK();
    __disable_irq();
    bool matches=microphone->running &&
        microphone->stale_dma_halves==baseline->stale_dma_halves &&
        microphone->event_queue_overflows==baseline->event_queue_overflows &&
        microphone->processing_rejections==baseline->processing_rejections &&
        microphone->error_irqs==baseline->error_irqs;
    __set_PRIMASK(primask);
    return matches;
}

bool comp_v11_microphone_hal_capture_matches(
    const comp_v11_microphone_hal_t *microphone,
    const comp_v11_microphone_stats_t *baseline)
{
    if(microphone==NULL || baseline==NULL)return false;
    uint32_t primask=__get_PRIMASK();
    __disable_irq();
    bool matches=microphone->running &&
        microphone->stale_dma_halves==baseline->stale_dma_halves &&
        microphone->event_queue_overflows==baseline->event_queue_overflows &&
        microphone->processing_rejections==baseline->processing_rejections &&
        microphone->error_irqs==baseline->error_irqs;
    __set_PRIMASK(primask);
    return matches;
}

void comp_v11_microphone_hal_get_stats(
    comp_v11_microphone_hal_t *microphone,
    comp_v11_microphone_stats_t *stats)
{
    uint32_t primask;
    const comp_wba_pdm_stats_t *processing;

    if (microphone == NULL || stats == NULL) return;
    memset(stats, 0, sizeof(*stats));
    primask = __get_PRIMASK();
    __disable_irq();
    stats->rx_half_irqs = microphone->rx_half_irqs;
    stats->rx_complete_irqs = microphone->rx_complete_irqs;
    stats->error_irqs = microphone->error_irqs;
    stats->ignored_callbacks = microphone->ignored_callbacks;
    stats->event_queue_overflows = microphone->event_queue_overflows;
    stats->last_hal_error = microphone->last_hal_error;
    stats->running = microphone->running;
    __set_PRIMASK(primask);
    stats->starts = microphone->starts;
    stats->stops = microphone->stops;
    stats->stale_dma_halves = microphone->stale_dma_halves;
    stats->startup_halves_discarded = microphone->startup_halves_discarded;
    stats->processed_dma_halves = microphone->processed_dma_halves;
    stats->processing_rejections = microphone->processing_rejections;
    stats->configured_pdm_clock_hz = microphone->configured_pdm_clock_hz;
    stats->initialized = microphone->initialized;
    processing = comp_wba_pdm_capture_stats(&microphone->processing);
    if (processing != NULL) stats->processing = *processing;
}

SAI_HandleTypeDef *comp_v11_microphone_hal_sai_handle(
    comp_v11_microphone_hal_t *microphone)
{
    return microphone != NULL ? &microphone->sai : NULL;
}

DMA_HandleTypeDef *comp_v11_microphone_hal_dma_handle(
    comp_v11_microphone_hal_t *microphone)
{
    return microphone != NULL ? &microphone->dma : NULL;
}

void comp_v11_microphone_hal_dma_irq(comp_v11_microphone_hal_t *microphone)
{
    if (microphone != NULL && microphone->initialized) {
        HAL_DMA_IRQHandler(&microphone->dma);
    }
}

void comp_v11_microphone_hal_sai_irq(comp_v11_microphone_hal_t *microphone)
{
    if (microphone != NULL && microphone->initialized) {
        HAL_SAI_IRQHandler(&microphone->sai);
    }
}

bool comp_v11_microphone_hal_on_rx_half(
    comp_v11_microphone_hal_t *microphone, SAI_HandleTypeDef *hsai)
{
    if (microphone == NULL || hsai != &microphone->sai) return false;
    if (!microphone->running) {
        microphone->ignored_callbacks++;
        return true;
    }
    microphone->rx_half_irqs++;
    publish_event(microphone, 0u);
    return true;
}

bool comp_v11_microphone_hal_on_rx_complete(
    comp_v11_microphone_hal_t *microphone, SAI_HandleTypeDef *hsai)
{
    if (microphone == NULL || hsai != &microphone->sai) return false;
    if (!microphone->running) {
        microphone->ignored_callbacks++;
        return true;
    }
    microphone->rx_complete_irqs++;
    publish_event(microphone, 1u);
    return true;
}

bool comp_v11_microphone_hal_on_error(
    comp_v11_microphone_hal_t *microphone, SAI_HandleTypeDef *hsai)
{
    if (microphone == NULL || hsai != &microphone->sai) return false;
    microphone->last_hal_error = hsai->ErrorCode;
    microphone->error_irqs++;
    microphone->error_pending = true;
    /* HAL errors do not prove DMA stopped. Keep the previous liveness until
     * a foreground HAL_SAI_DMAStop succeeds. */
    return true;
}
