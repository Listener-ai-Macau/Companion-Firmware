#include "touch_target_stm32wba_ft6336.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

typedef struct {
    uint8_t registers[256];
    unsigned calls, fail_call, mismatch_register;
    uint8_t written[3];
    unsigned writes;
} port_t;

static bool probe(void *context, uint8_t address)
{ (void)context; return address == 0x38u; }
static bool read_register(void *context, uint8_t address, uint8_t reg,
                          uint8_t *data, uint16_t size)
{
    port_t *p = context;
    assert(address == 0x38u && size == 1u);
    if (++p->calls == p->fail_call) return false;
    *data = p->registers[reg];
    if (reg == p->mismatch_register) *data ^= 1u;
    return true;
}
static bool write_register(void *context, uint8_t address, uint8_t reg,
                           const uint8_t *data, uint16_t size)
{
    port_t *p = context;
    assert(address == 0x38u && size == 1u);
    if (++p->calls == p->fail_call) return false;
    assert(p->writes < sizeof(p->written));
    p->written[p->writes++] = reg;
    p->registers[reg] = *data;
    return true;
}
static companion_touch_ft6336_stm32wba_t fixture(port_t *p)
{
    memset(p, 0, sizeof(*p));
    p->mismatch_register = 256u;
    p->registers[COMP_FT6336_DEVICE_MODE_REGISTER] = 0x40u;
    p->registers[COMP_FT6336_POWER_MODE_REGISTER] = 3u;
    companion_touch_ft6336_stm32wba_t touch = {0};
    touch.config = (companion_touch_ft6336_stm32wba_config_t){
        COMPANION_TOUCH_FT6336_STM32WBA_TARGET_WBA55,
        probe, read_register, write_register, p};
    touch.address_7bit = 0x38u;
    touch.detected = true;
    return touch;
}
int main(void)
{
    port_t p;
    companion_touch_ft6336_stm32wba_t touch = fixture(&p);
    assert(companion_touch_ft6336_stm32wba_configure_interrupt(&touch));
    assert(p.calls == 6u && p.writes == 3u);
    assert(p.written[0] == COMP_FT6336_DEVICE_MODE_REGISTER);
    assert(p.written[1] == COMP_FT6336_POWER_MODE_REGISTER);
    assert(p.written[2] == COMP_FT6336_G_MODE_REGISTER);
    assert(p.registers[COMP_FT6336_DEVICE_MODE_REGISTER] == 0u);
    assert(p.registers[COMP_FT6336_POWER_MODE_REGISTER] == 0u);
    assert(p.registers[COMP_FT6336_G_MODE_REGISTER] == COMP_FT6336_G_MODE_TRIGGER);
    assert(touch.interrupt_mode_valid && touch.interrupt_config_count == 1u);
    for (unsigned failure = 1u; failure <= 6u; ++failure) {
        touch = fixture(&p); p.fail_call = failure;
        /* A previous success must not survive failed reconfiguration. */
        touch.interrupt_mode_valid = true;
        assert(!companion_touch_ft6336_stm32wba_configure_interrupt(&touch));
        assert(!touch.interrupt_mode_valid && p.calls == failure);
        assert(touch.interrupt_config_error_count == 1u);
    }
    const uint8_t mismatch[] = {COMP_FT6336_DEVICE_MODE_REGISTER,
        COMP_FT6336_POWER_MODE_REGISTER, COMP_FT6336_G_MODE_REGISTER};
    for (size_t i = 0u; i < sizeof(mismatch); ++i) {
        touch = fixture(&p); p.mismatch_register = mismatch[i];
        assert(!companion_touch_ft6336_stm32wba_configure_interrupt(&touch));
        assert(!touch.interrupt_mode_valid && touch.interrupt_config_error_count == 1u);
        assert(p.calls == (i + 1u) * 2u);
    }
    assert(!companion_touch_ft6336_stm32wba_configure_working_mode(NULL));
    touch = fixture(&p); touch.detected = false;
    assert(!companion_touch_ft6336_stm32wba_configure_working_mode(&touch) && p.calls == 0u);
    puts("PASS: WBA working/active readback precedes trigger setup; six I/O and three mismatch failures reject readiness. No hardware claim.");
    return 0;
}
