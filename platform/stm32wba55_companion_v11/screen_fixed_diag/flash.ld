/* Temporary fixed-frame diagnostic. Installer restores product Flash. */
ENTRY(Reset_Handler)
MEMORY { FLASH (rx) : ORIGIN = 0x08000000, LENGTH = 64K
         SRAM (rwx) : ORIGIN = 0x20000000, LENGTH = 128K }
_estack = ORIGIN(SRAM) + LENGTH(SRAM);
_sstack = _estack - 0x6000;
SECTIONS {
  .isr_vector : { . = ALIGN(512); KEEP(*(.isr_vector)) } > FLASH
  .text : { *(.text*) *(.rodata*) KEEP(*(.init)) KEEP(*(.fini)) . = ALIGN(4); } > FLASH
  .ARM.extab : { *(.ARM.extab*) } > FLASH
  .ARM.exidx : { __exidx_start = .; *(.ARM.exidx*) __exidx_end = .; } > FLASH
  .preinit_array : { PROVIDE_HIDDEN(__preinit_array_start = .); KEEP(*(.preinit_array*)) PROVIDE_HIDDEN(__preinit_array_end = .); } > FLASH
  .init_array : { PROVIDE_HIDDEN(__init_array_start = .); KEEP(*(SORT(.init_array.*))) KEEP(*(.init_array*)) PROVIDE_HIDDEN(__init_array_end = .); } > FLASH
  .fini_array : { PROVIDE_HIDDEN(__fini_array_start = .); KEEP(*(.fini_array*)) PROVIDE_HIDDEN(__fini_array_end = .); } > FLASH
  .data : { . = ALIGN(4); _sdata = .; *(.data*) . = ALIGN(4); _edata = .; } > SRAM AT>FLASH
  _sidata = LOADADDR(.data);
  .bss (NOLOAD) : { . = ALIGN(8); _sbss = .; *(.bss*) *(COMMON) . = ALIGN(8); _ebss = .; } > SRAM
  _end = .; end = .;
  ASSERT(_ebss <= _sstack, "Screen diagnostic exceeds SRAM with 24KiB stack reserved")
}
