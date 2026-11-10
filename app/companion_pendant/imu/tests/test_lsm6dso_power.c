#include "lsm6dso.h"

#include <stdio.h>
#include <string.h>

typedef struct {
    uint8_t registers[256];
    uint8_t fail_write_register;
} fake_bus_t;

static int fail(const char *message)
{
    fprintf(stderr, "FAIL: %s\n", message);
    return 1;
}

static bool bus_read(void *context, uint8_t reg, uint8_t *bytes, size_t count)
{
    fake_bus_t *bus = context;
    if (bus == NULL || bytes == NULL || (size_t)reg + count > sizeof(bus->registers)) {
        return false;
    }
    memcpy(bytes, &bus->registers[reg], count);
    return true;
}

static bool bus_write(void *context, uint8_t reg, const uint8_t *bytes, size_t count)
{
    fake_bus_t *bus = context;
    if (bus == NULL || bytes == NULL || count == 0u ||
        (size_t)reg + count > sizeof(bus->registers) ||
        reg == bus->fail_write_register) {
        return false;
    }
    memcpy(&bus->registers[reg], bytes, count);
    return true;
}

static bool start_ready(comp_lsm6dso_t *imu, fake_bus_t *bus)
{
    comp_imu_sample_t sample;
    memset(bus, 0, sizeof(*bus));
    bus->registers[0x0Fu] = 0x6Cu;
    bus->fail_write_register = 0xFFu;
    if (!comp_lsm6dso_start(imu, bus_read, bus_write, bus, 10u)) return false;
    bus->registers[0x12u] = 0u; /* model completion of SW_RESET */
    return comp_lsm6dso_poll(imu, 11u, &sample) == COMP_IMU_NO_SAMPLE &&
           imu->state == COMP_IMU_READY;
}

int main(void)
{
    comp_lsm6dso_t imu;
    comp_imu_sample_t sample;
    fake_bus_t bus;

    if (!start_ready(&imu, &bus) || bus.registers[0x10u] != 0x38u ||
        bus.registers[0x11u] != 0x30u || bus.registers[0x0Du] != 0x03u) {
        return fail("run-mode initialization");
    }

    if (!comp_lsm6dso_set_idle(&imu,true,12u) || !imu.idle_accel_only ||
        bus.registers[0x10u] != 0x18u || bus.registers[0x11u] != 0x00u ||
        bus.registers[0x15u] != 0x10u || bus.registers[0x0Du] != 0x00u || bus.registers[0x5Eu]!=0u) {
        return fail("idle accel-only register contract");
    }

    bus.registers[0x1Eu] = 0x01u; /* accel ready; gyro intentionally absent */
    bus.registers[0x28u] = 0xE8u; bus.registers[0x29u] = 0x03u; /* 1000 raw */
    bus.registers[0x2Au] = 0x18u; bus.registers[0x2Bu] = 0xFCu; /* -1000 raw */
    bus.registers[0x2Cu] = 0x00u; bus.registers[0x2Du] = 0x20u;
    memset(&sample, 0xA5, sizeof(sample));
    if (comp_lsm6dso_poll(&imu, 100u, &sample) != COMP_IMU_SAMPLE ||
        sample.accel_mg[0] != 122 || sample.accel_mg[1] != -122 ||
        sample.accel_mg[2] != 999 || sample.gyro_mdps[0] != 0 ||
        sample.gyro_mdps[1] != 0 || sample.gyro_mdps[2] != 0) {
        return fail("idle poll accepts accel-only data-ready");
    }

    if (!comp_lsm6dso_set_idle(&imu,false,12u) || imu.idle_accel_only ||
        bus.registers[0x10u] != 0x38u || bus.registers[0x11u] != 0x30u ||
        bus.registers[0x15u] != 0x00u || bus.registers[0x0Du] != 0x03u) {
        return fail("run-mode restore");
    }
    bus.registers[0x1Eu] = 0x01u;
    if (comp_lsm6dso_poll(&imu, 110u, &sample) != COMP_IMU_NO_SAMPLE) {
        return fail("run mode still requires accel and gyro data-ready");
    }

    if (!start_ready(&imu, &bus)) return fail("fault test setup");
    bus.fail_write_register = 0x15u;
    if (comp_lsm6dso_set_idle(&imu,true,12u) || imu.state != COMP_IMU_FAULT ||
        imu.errors != 1u) {
        return fail("partial mode switch fails closed");
    }

    printf("PASS_HOST_ONLY: LSM6DSO idle mode powers gyro down, keeps 12.5Hz "
           "low-power accel pickup samples, restores 52Hz run mode, and "
           "fails closed on bus error\n");
    return 0;
}
