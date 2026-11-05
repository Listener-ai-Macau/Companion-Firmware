#ifndef COMP_DIAG_FLASH_JOURNAL_H
#define COMP_DIAG_FLASH_JOURNAL_H
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

/* Fixed 64-byte wire record: magic, sequence, twelve data words, CRC, commit.
 * No erase operation is exposed. All addresses belong to the caller's region. */
enum { COMP_DJ_FW, COMP_DJ_RESET, COMP_DJ_TICK, COMP_DJ_PHASE, COMP_DJ_STATE,
       COMP_DJ_FAULT, COMP_DJ_PC, COMP_DJ_LR, COMP_DJ_CFSR, COMP_DJ_HFSR,
       COMP_DJ_BFAR, COMP_DJ_EXC_RETURN, COMP_DJ_WORDS };
typedef struct { uint32_t word[COMP_DJ_WORDS]; } comp_diag_flash_data_t;
typedef struct {
    bool (*read)(void *,uint32_t,uint8_t *,size_t);
    bool (*program)(void *,uint32_t,const uint8_t *,size_t);
    void *context;
    uint32_t base,bytes;
} comp_diag_flash_ports_t;
typedef void (*comp_diag_flash_visit_fn)(void *,uint32_t,const comp_diag_flash_data_t *);
typedef struct { bool scanned,appended;uint32_t valid,sequence; } comp_diag_flash_result_t;
comp_diag_flash_result_t comp_diag_flash_journal(const comp_diag_flash_ports_t *,
    const comp_diag_flash_data_t *,comp_diag_flash_visit_fn,void *);
#endif
