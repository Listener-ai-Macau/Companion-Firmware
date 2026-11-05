/* CE has two disjoint SRAM banks. Override only the pinned SDK's weak reset
 * handler; retain its vector/IRQ table and SystemInit unchanged. There are no
 * C calls or zero-initialized-data dependencies before both banks are ready.
 * App links its existing SystemInit stack-paint wrapper; Boot does not. */
.syntax unified
.cpu cortex-m33
.thumb
.section .text.Reset_Handler,"ax",%progbits
.global Reset_Handler
.type Reset_Handler,%function
.thumb_func
Reset_Handler:
    ldr sp, =_estack
    ldr r0, =_sstack
    msr MSPLIM, r0
    bl SystemInit
    ldr r0, =_sdata
    ldr r1, =_edata
    ldr r2, =_sidata
1:
    cmp r0, r1
    bcs 2f
    ldr r3, [r2], #4
    str r3, [r0], #4
    b 1b
2:
    ldr r0, =_sdata_sram2
    ldr r1, =_edata_sram2
    ldr r2, =_sidata_sram2
3:
    cmp r0, r1
    bcs 4f
    ldr r3, [r2], #4
    str r3, [r0], #4
    b 3b
4:
    ldr r0, =_sbss
    ldr r1, =_ebss
    movs r2, #0
5:
    cmp r0, r1
    bcs 6f
    str r2, [r0], #4
    b 5b
6:
    ldr r0, =_sbss_sram1
    ldr r1, =_ebss_sram1
7:
    cmp r0, r1
    bcs 8f
    str r2, [r0], #4
    b 7b
8:
    bl __libc_init_array
    bl main
9:
    b 9b
.size Reset_Handler, .-Reset_Handler
