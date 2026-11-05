/* Sealed-backlog pump during opus_encode. PendSV is the lowest priority, so
 * the radio IRQ that asked for the switch has already returned. The pump runs
 * in thread mode on its own stack: NOR and GATT refuse or deadlock in handler
 * mode, and the opus frame only has a few KiB of main-stack margin. MSPLIM
 * keeps this stack off the main stack. A state of 0 returns with no switch. */
.syntax unified
.cpu cortex-m33
.fpu fpv5-sp-d16
.thumb
.section .text.PendSV_Handler,"ax",%progbits
.global PendSV_Handler
.type PendSV_Handler,%function
.thumb_func
PendSV_Handler:
    ldr r0, =comp_blackout_state
    ldr r1, [r0]
    cmp r1, #1
    beq switch_to_pump
    cmp r1, #3
    beq switch_to_opus
    bx lr
switch_to_pump:
    tst lr, #0x10
    it eq
    vstmdbeq sp!, {s16-s31}
    stmdb sp!, {r4-r11, lr}
    ldr r2, =comp_blackout_opus_msp
    str sp, [r2]
    ldr r2, =comp_blackout_pump_base
    ldr r2, [r2]
    msr MSPLIM, r2
    isb
    ldr r2, =comp_blackout_pump_msp
    ldr sp, [r2]
    movs r1, #2
    str r1, [r0]
    b restore
switch_to_opus:
    tst lr, #0x10
    it eq
    vstmdbeq sp!, {s16-s31}
    stmdb sp!, {r4-r11, lr}
    ldr r2, =comp_blackout_pump_msp
    str sp, [r2]
    ldr r2, =comp_blackout_opus_msp
    ldr sp, [r2]
    ldr r2, =comp_blackout_main_msplim
    ldr r2, [r2]
    msr MSPLIM, r2
    isb
    movs r1, #0
    str r1, [r0]
restore:
    ldmia sp!, {r4-r11, lr}
    tst lr, #0x10
    it eq
    vldmiaeq sp!, {s16-s31}
    bx lr
    .ltorg
.size PendSV_Handler, .-PendSV_Handler
