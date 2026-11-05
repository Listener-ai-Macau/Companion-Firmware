/* WBA55CE: documented SRAM1 32KiB + SRAM2 64KiB; the intervening
 * 0x20008000..0x2000FFFF is not RAM. ce_reset.S initializes both banks.
 * Candidate only: 21KiB after bounded mono Opus workspace reuse. Physical
 * recording, interrupt and stack-watermark qualification remain required. */
ENTRY(Reset_Handler)
MEMORY {
  FLASH (rx) : ORIGIN = 0x08006000, LENGTH = 488K
  RAM1 (xrw) : ORIGIN = 0x20000000, LENGTH = 32K
  RAM2 (xrw) : ORIGIN = 0x20010000, LENGTH = 64K
}
_estack = ORIGIN(RAM2) + LENGTH(RAM2);
_sstack = _estack - 0x5400;
SECTIONS {
  .isr_vector : { . = ALIGN(4); KEEP(*(.isr_vector)) } > FLASH
  .text : { *(.text*) *(.rodata*) KEEP(*(.init)) KEEP(*(.fini)) . = ALIGN(4); } > FLASH
  .ARM.extab : { *(.ARM.extab*) } > FLASH
  .ARM.exidx : { __exidx_start = .; *(.ARM.exidx*) __exidx_end = .; } > FLASH
  .preinit_array (READONLY) : { PROVIDE_HIDDEN(__preinit_array_start = .); KEEP(*(.preinit_array*)) PROVIDE_HIDDEN(__preinit_array_end = .); } > FLASH
  .init_array (READONLY) : { PROVIDE_HIDDEN(__init_array_start = .); KEEP(*(SORT(.init_array.*))) KEEP(*(.init_array*)) PROVIDE_HIDDEN(__init_array_end = .); } > FLASH
  .fini_array (READONLY) : { PROVIDE_HIDDEN(__fini_array_start = .); KEEP(*(SORT(.fini_array.*))) KEEP(*(.fini_array*)) PROVIDE_HIDDEN(__fini_array_end = .); } > FLASH
  _sidata_sram2 = LOADADDR(.data_sram2);
  .data_sram2 : { . = ALIGN(8); _sdata_sram2 = .; *(.sram2.data*) . = ALIGN(8); _edata_sram2 = .; } > RAM2 AT> FLASH
  _sidata = LOADADDR(.data);
  .data : { . = ALIGN(8); _sdata = .; *(.data*) *(.RamFunc*) . = ALIGN(8); _edata = .; } > RAM1 AT> FLASH
  .bss_sram1 (NOLOAD) : { . = ALIGN(8); _sbss_sram1 = .; *(.sram1.bss*) . = ALIGN(8); _ebss_sram1 = .; } > RAM1
  .bss (NOLOAD) : { . = ALIGN(8); _sbss = .; *(.bss*) *(COMMON) . = ALIGN(8); _ebss = .; _end = .; end = .; } > RAM2
  .heap_stack _sstack (NOLOAD) : { . += 0x5400; } > RAM2
  __sram1_free_bytes = ORIGIN(RAM1) + LENGTH(RAM1) - _ebss_sram1;
  ASSERT(_ebss_sram1 <= ORIGIN(RAM1) + LENGTH(RAM1), "CE SRAM1 32KiB overflow")
  ASSERT(_ebss <= _sstack, "CE SRAM2 static data overlaps reserved stack")
  ASSERT(_estack == ORIGIN(RAM2) + LENGTH(RAM2), "CE stack outside physical SRAM2")
}
