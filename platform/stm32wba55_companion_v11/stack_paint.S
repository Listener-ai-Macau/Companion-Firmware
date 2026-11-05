/* Wrap the pinned ST startup's first SystemInit call. At this point startup
 * has set MSP/MSPLIM but made no stack writes. No push, C, or BSS dependency:
 * paint the whole reserved region, then tail-call the original SystemInit.
 * The application alone links --wrap=SystemInit; resident boot is unchanged. */
.syntax unified
.cpu cortex-m33
.thumb
.section .text.__wrap_SystemInit,"ax",%progbits
.global __wrap_SystemInit
.type __wrap_SystemInit,%function
.thumb_func
__wrap_SystemInit:
    ldr r0, =_sstack
    ldr r1, =_estack
    ldr r2, =0xA55A3CC3
1:
    cmp r0, r1
    bcs 2f
    str r2, [r0], #4
    b 1b
2:
    b __real_SystemInit
.size __wrap_SystemInit, .-__wrap_SystemInit
