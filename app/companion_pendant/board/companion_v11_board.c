#include "companion_v11_board.h"
#include <stddef.h>

bool comp_v11_battery_enable(comp_tca6408_t *io,bool enabled,uint8_t *observation)
{
    const uint8_t mask=COMP_V11_BATTERY_ENABLE;
    uint8_t output,direction,input;
    if(observation)*observation=0u;
    if(!io||!io->ready||(io->inputs&mask)||!io->read||!io->write)return false;
    if(io->admit_write&&!io->admit_write(io->context)){io->errors++;return false;}
    if(!io->read(io->context,io->address,1u,&output)||
       !io->read(io->context,io->address,3u,&direction))goto failed;
    /* Preserve every other pin. Set the latch before driving P7 so reset's
     * input direction cannot briefly drive the divider with the wrong value. */
    output=(uint8_t)((output&~mask)|(enabled?mask:0u));
    if(!io->write(io->context,io->address,1u,output))goto failed;
    if((direction&mask)&&!io->write(io->context,io->address,3u,(uint8_t)(direction&~mask)))goto failed;
    if(!io->read(io->context,io->address,0u,&input))goto failed;
    io->outputs=output;
    if(observation)*observation=(uint8_t)(8u|((output&mask)?1u:0u)|((input&mask)?2u:0u));
    if(((input&mask)!=0u)==enabled)return true;
failed:
    io->errors++;io->ready=false;return false;
}

void comp_v11_power_init(comp_v11_power_t *power, comp_tca6408_t *io)
{
    if (power != NULL) { *power = (comp_v11_power_t){.io = io, .switched = true}; }
}
void comp_v11_power_init_always_on(comp_v11_power_t *power, comp_tca6408_t *io)
{
    comp_v11_power_init(power, io);
    if (power != NULL) power->switched = false;
}
bool comp_v11_power_request(comp_v11_power_t *power, bool on, uint32_t now_ms)
{
    if (power == NULL || power->io == NULL || !power->io->ready) { return false; }
    if (!on && !power->switched) { return false; }
    if (on && power->state != COMP_V11_POWER_OFF) {
        return power->state != COMP_V11_POWER_FAULT;
    }
    if (!comp_tca6408_update(power->io,
                            COMP_V11_TP_RESET | (power->switched ? COMP_V11_SCREEN_POWER : 0u),
                            on && power->switched ? COMP_V11_SCREEN_POWER : 0u)) {
        power->state = COMP_V11_POWER_FAULT; return false;
    }
    power->changed_ms = now_ms;
    power->state = on ? COMP_V11_POWER_SETTLE : COMP_V11_POWER_OFF;
    return true;
}
void comp_v11_power_poll(comp_v11_power_t *power, uint32_t now_ms)
{
    if (power == NULL) { return; }
    if (power->io == NULL || !power->io->ready) {
        power->state = COMP_V11_POWER_FAULT; return;
    }
    if (power->state == COMP_V11_POWER_SETTLE && now_ms - power->changed_ms >= 20u) {
        if (!comp_tca6408_update(power->io, COMP_V11_TP_RESET, COMP_V11_TP_RESET)) {
            power->state = COMP_V11_POWER_FAULT; return;
        }
        power->changed_ms = now_ms;
        power->state = COMP_V11_TOUCH_RESET_WAIT;
    } else if (power->state == COMP_V11_TOUCH_RESET_WAIT &&
               now_ms - power->changed_ms >= COMP_V11_TOUCH_STARTUP_MS) {
        power->state = COMP_V11_POWER_READY;
    }
}
bool comp_v11_battery_divider_safe(uint32_t top_ohm, uint32_t bottom_ohm,
                                  uint16_t vdda_mv, uint16_t max_battery_mv)
{
    uint64_t sum = (uint64_t)top_ohm + bottom_ohm;
    return top_ohm != 0u && bottom_ohm != 0u && vdda_mv > 100u && vdda_mv <= 3600u &&
           max_battery_mv != 0u &&
           (uint64_t)max_battery_mv * bottom_ohm <= (uint64_t)(vdda_mv - 100u) * sum;
}
bool comp_v11_battery_mv(uint16_t adc, uint16_t adc_full_scale,
                         uint16_t vdda_mv, uint32_t top_ohm,
                         uint32_t bottom_ohm, uint16_t *millivolts)
{
    uint64_t value;
    if (millivolts == NULL || adc_full_scale < 16u || adc >= adc_full_scale - 2u ||
        !comp_v11_battery_divider_safe(top_ohm, bottom_ohm, vdda_mv, 4350u)) { return false; }
    value = (uint64_t)adc * vdda_mv * ((uint64_t)top_ohm + bottom_ohm) /
            ((uint64_t)adc_full_scale * bottom_ohm);
    if (value > UINT16_MAX) { return false; }
    *millivolts = (uint16_t)value;
    return true;
}
