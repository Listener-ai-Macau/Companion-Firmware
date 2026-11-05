#ifndef COMP_DMIC_TEST_PLATFORM_H
#define COMP_DMIC_TEST_PLATFORM_H
#include "companion_continuous_recording.h"
#include "wba_pdm_capture.h"
#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>
#define COMPANION_DMIC_CAPTURE_SOURCE_BYTES {1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1}
typedef struct {
 uint32_t stale_dma_halves,event_queue_overflows,processing_rejections,error_irqs;
 comp_wba_pdm_stats_t processing;
} comp_v11_microphone_stats_t;
typedef struct {
 comp_wba_pdm_capture_t processing;
 uint32_t stale_dma_halves,event_queue_overflows,processing_rejections,error_irqs;
 bool running;
} comp_v11_microphone_hal_t;
typedef enum {COMP_V11_MIC_POLL_IDLE,COMP_V11_MIC_POLL_PROCESSED,COMP_V11_MIC_POLL_DROPPED,COMP_V11_MIC_POLL_ERROR} comp_v11_microphone_poll_result_t;
typedef enum {COMPANION_SPI_NOR_STM32WBA_OK=0,COMPANION_SPI_NOR_STM32WBA_PENDING=1,COMPANION_SPI_NOR_STM32WBA_ERROR=-1} companion_spi_nor_stm32wba_status_t;
typedef struct {bool erase_active;uint32_t erase_address,erase_bytes;struct{uint32_t page_program_timeout_ms;}config;} companion_spi_nor_stm32wba_t;
typedef struct {uint32_t blockers;} comp_power_policy_t;
#define COMP_POWER_BLOCKER_STORAGE 4u
typedef struct {
 comp_v11_microphone_hal_t microphone;companion_spi_nor_stm32wba_t nor;comp_power_policy_t power;
 comp_wba_pdm_pcm_frame_fn_t pcm_sink;void *pcm_sink_context;
 struct{bool playback_inhibited;}services;
 bool power_sampling_inhibited,playback_active;
} comp_v11_hal_t;
typedef struct {
 comp_v11_hal_t *board;bool storage_layout_ready,recording_ready;
 struct{bool ready,media_ready;struct{uint32_t workspace_bytes,workspace_requested;}pipeline;
  struct{comp_cont_recording_t engine;}capture;}recording;
 struct{bool writing;}pet_profile;
 struct{bool prepare_pending,start_pending,command_pending,capture_active,stop_pending;}runtime;
} comp_v11_product_app_t;
uint32_t HAL_GetTick(void);
bool comp_v11_ble_linked(void);
bool comp_v11_update_product_busy(void);
void comp_v11_hal_log(const char *);
bool comp_v11_hal_set_pair_sink(comp_v11_hal_t *,comp_wba_pdm_pair_frame_fn_t,void *);
bool comp_v11_hal_set_pcm_sink(comp_v11_hal_t *,comp_wba_pdm_pcm_frame_fn_t,void *);
bool comp_v11_hal_microphone_enable(comp_v11_hal_t *,bool);
void comp_v11_hal_dual_mic_report(const comp_v11_hal_t *,uint32_t);
bool comp_v11_hal_device_uid(uint8_t[12]);
void comp_v11_ble_console_idle_progress(void);
bool comp_v11_hal_random_u32(comp_v11_hal_t *,uint32_t *);
bool companion_opus16_rt_workspace_available(void);
bool comp_wba_recording_product_workspace(void *,uint32_t,uint32_t *);
void comp_power_policy_set_blocker(comp_power_policy_t *,uint32_t,bool);
void comp_v11_microphone_hal_get_stats(comp_v11_microphone_hal_t *,comp_v11_microphone_stats_t *);
bool comp_v11_microphone_hal_capture_matches(const comp_v11_microphone_hal_t *,const comp_v11_microphone_stats_t *);
comp_v11_microphone_poll_result_t comp_v11_microphone_hal_poll(comp_v11_microphone_hal_t *);
companion_spi_nor_stm32wba_status_t companion_spi_nor_stm32wba_erase_step(companion_spi_nor_stm32wba_t *,uint32_t,uint32_t);
companion_spi_nor_stm32wba_status_t companion_spi_nor_stm32wba_erase_finish_poll(companion_spi_nor_stm32wba_t *,uint32_t,uint32_t);
companion_spi_nor_stm32wba_status_t companion_spi_nor_stm32wba_wait_ready(companion_spi_nor_stm32wba_t *,uint32_t);
companion_spi_nor_stm32wba_status_t companion_spi_nor_stm32wba_read(companion_spi_nor_stm32wba_t *,uint32_t,uint8_t *,size_t);
companion_spi_nor_stm32wba_status_t companion_spi_nor_stm32wba_program(companion_spi_nor_stm32wba_t *,uint32_t,const uint8_t *,size_t);
#endif
