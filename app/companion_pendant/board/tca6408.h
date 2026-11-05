#ifndef COMP_TCA6408_H
#define COMP_TCA6408_H
#include <stdbool.h>
#include <stdint.h>

typedef bool (*comp_tca6408_read_fn)(void *, uint8_t, uint8_t, uint8_t *);
typedef bool (*comp_tca6408_write_fn)(void *, uint8_t, uint8_t, uint8_t);
typedef bool (*comp_tca6408_admit_fn)(void *);
typedef struct {
    comp_tca6408_read_fn read;
    comp_tca6408_write_fn write;
    /* Optional single-owner preflight, before any write is attempted. Set
     * after init. A rejected admission preserves the confirmed latch. */
    comp_tca6408_admit_fn admit_write;
    void *context;
    uint8_t address;
    uint8_t inputs;
    uint8_t outputs;
    bool ready;
    uint32_t errors;
} comp_tca6408_t;

/* Single task owns the expander; IRQ only wakes that task. Safe latch is
 * written BEFORE enabling output directions. Masks: 1=input, 0=output. */
bool comp_tca6408_init(comp_tca6408_t *io, comp_tca6408_read_fn read,
                      comp_tca6408_write_fn write, void *context,
                      uint8_t address, uint8_t input_mask, uint8_t safe_outputs);
bool comp_tca6408_update(comp_tca6408_t *io, uint8_t mask, uint8_t values);
bool comp_tca6408_sample(comp_tca6408_t *io, uint8_t *inputs);
#endif
