/* Temporary CE qualification image. No LOAD segment may address Flash. */
ENTRY(Reset_Handler)
MEMORY { SRAM (rwx) : ORIGIN = 0x20000000, LENGTH = 128K }
_estack = ORIGIN(SRAM) + LENGTH(SRAM);
_sstack = _estack - 0x6000;
SECTIONS {
  .isr_vector : { . = ALIGN(512); KEEP(*(.isr_vector)) } > SRAM
  .text : { *(.text*) *(.rodata*) KEEP(*(.init)) KEEP(*(.fini)) . = ALIGN(4); } > SRAM
  .ARM.extab : { *(.ARM.extab*) } > SRAM
  .ARM.exidx : { __exidx_start = .; *(.ARM.exidx*) __exidx_end = .; } > SRAM
  .preinit_array : { PROVIDE_HIDDEN(__preinit_array_start = .); KEEP(*(.preinit_array*)) PROVIDE_HIDDEN(__preinit_array_end = .); } > SRAM
  .init_array : { PROVIDE_HIDDEN(__init_array_start = .); KEEP(*(SORT(.init_array.*))) KEEP(*(.init_array*)) PROVIDE_HIDDEN(__init_array_end = .); } > SRAM
  .fini_array : { PROVIDE_HIDDEN(__fini_array_start = .); KEEP(*(SORT(.fini_array.*))) KEEP(*(.fini_array*)) PROVIDE_HIDDEN(__fini_array_end = .); } > SRAM
  .data : { . = ALIGN(4); _sdata = .; *(.data*) . = ALIGN(4); _edata = .; } > SRAM
  _sidata = LOADADDR(.data);
  .bss (NOLOAD) : { . = ALIGN(8); _sbss = .; *(.bss*) *(COMMON) . = ALIGN(8); _ebss = .; } > SRAM
  _end = .; end = .;
  ASSERT(_ebss <= _sstack, "Peripheral diagnostic exceeds SRAM with 24KiB stack reserved")
}
