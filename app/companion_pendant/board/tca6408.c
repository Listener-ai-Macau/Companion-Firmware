#include "tca6408.h"
#include <string.h>

/* TI SCPS192E: input=0, output=1, polarity=2, configuration=3. */
bool comp_tca6408_init(comp_tca6408_t *io, comp_tca6408_read_fn read,
                      comp_tca6408_write_fn write, void *context,
                      uint8_t address, uint8_t input_mask, uint8_t safe_outputs)
{
    uint8_t actual;
    if (io == NULL) { return false; }
    memset(io, 0, sizeof(*io));
    if (read == NULL || write == NULL || (address != 0x20u && address != 0x21u)) {
        return false;
    }
    io->read = read; io->write = write; io->context = context;
    io->address = address; io->inputs = input_mask;
    if (!write(context, address, 1u, safe_outputs) ||
        !write(context, address, 2u, 0u) ||
        !write(context, address, 3u, input_mask) ||
        !read(context, address, 3u, &actual) || actual != input_mask ||
        !read(context, address, 1u, &actual) || actual != safe_outputs) {
        io->errors++;
        return false;
    }
    io->outputs = safe_outputs;
    io->ready = true;
    return true;
}

bool comp_tca6408_update(comp_tca6408_t *io, uint8_t mask, uint8_t values)
{
    uint8_t next;
    if (io == NULL || !io->ready || (mask & io->inputs) != 0u) { return false; }
    next = (uint8_t)((io->outputs & (uint8_t)~mask) | (values & mask));
    if (next == io->outputs) { return true; }
    if (io->admit_write != NULL && !io->admit_write(io->context)) {
        /* No byte was sent: this failed request must not invalidate every
         * output owner. Do not report success or retry it automatically. */
        io->errors++; return false;
    }
    if (!io->write(io->context, io->address, 1u, next)) {
        /* Transfer may have reached the chip despite a lost ACK; do not trust
         * the old shadow or let another output owner overwrite it. Reinit. */
        io->ready = false; io->errors++; return false;
    }
    io->outputs = next;
    return true;
}

bool comp_tca6408_sample(comp_tca6408_t *io, uint8_t *inputs)
{
    uint8_t value;
    if (io == NULL || !io->ready || inputs == NULL) { return false; }
    if (!io->read(io->context, io->address, 0u, &value)) {
        io->errors++; return false;
    }
    *inputs = (uint8_t)(value & io->inputs);
    return true;
}
