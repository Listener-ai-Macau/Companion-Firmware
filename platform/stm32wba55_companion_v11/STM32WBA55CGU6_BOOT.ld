/* Resident signed-update installer. The application begins at 0x08008000. */
ENTRY(Reset_Handler)
MEMORY {
  FLASH (rx) : ORIGIN = 0x08000000, LENGTH = 32K
  RAM (xrw) : ORIGIN = 0x20000000, LENGTH = 128K
}
_estack = ORIGIN(RAM) + LENGTH(RAM);
_sstack = _estack - 0x1000;
SECTIONS {
  .isr_vector : { . = ALIGN(4); KEEP(*(.isr_vector)) } > FLASH
  .text : { *(.text*) *(.rodata*) KEEP(*(.init)) KEEP(*(.fini)) . = ALIGN(4); } > FLASH
  .ARM.extab : { *(.ARM.extab*) } > FLASH
  .ARM.exidx : { __exidx_start = .; *(.ARM.exidx*) __exidx_end = .; } > FLASH
  .preinit_array (READONLY) : { PROVIDE_HIDDEN(__preinit_array_start = .); KEEP(*(.preinit_array*)) PROVIDE_HIDDEN(__preinit_array_end = .); } > FLASH
  .init_array (READONLY) : { PROVIDE_HIDDEN(__init_array_start = .); KEEP(*(SORT(.init_array.*))) KEEP(*(.init_array*)) PROVIDE_HIDDEN(__init_array_end = .); } > FLASH
  .fini_array (READONLY) : { PROVIDE_HIDDEN(__fini_array_start = .); KEEP(*(SORT(.fini_array.*))) KEEP(*(.fini_array*)) PROVIDE_HIDDEN(__fini_array_end = .); } > FLASH
  _sidata = LOADADDR(.data);
  .data : { . = ALIGN(4); _sdata = .; *(.data*) *(.RamFunc*) . = ALIGN(4); _edata = .; } > RAM AT> FLASH
  .bss (NOLOAD) : { . = ALIGN(8); _sbss = .; *(.bss*) *(COMMON) . = ALIGN(8); _ebss = .; } > RAM
  .heap_stack (NOLOAD) : { _end = .; end = .; . += 0x1000; } > RAM
  ASSERT(SIZEOF(.isr_vector) + SIZEOF(.text) + SIZEOF(.ARM.extab) + SIZEOF(.ARM.exidx) + SIZEOF(.data) <= 32K,
         "resident boot image exceeds protected 32KiB region")
  ASSERT(_ebss + 0x1000 <= _estack, "resident boot leaves less than 4KiB stack")
}
