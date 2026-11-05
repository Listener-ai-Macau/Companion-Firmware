/* SRAM-only callable ELF. CubeProgrammer supplies stack/call trampoline and
 * transfer buffers beyond the loader's allocated SRAM segments. */
ENTRY(Init)
EXTERN(Init Read Write SectorErase MassErase StorageInfo)
MEMORY { RAM (xrw) : ORIGIN = 0x20000004, LENGTH = 32K - 4 }
PHDRS { Loader PT_LOAD; SgInfo PT_LOAD; }
SECTIONS {
  .text : { *(.text*) *(.rodata*) } > RAM :Loader
  .ARM.exidx : { *(.ARM.exidx*) } > RAM :Loader
  .data : { *(.data*) } > RAM :Loader
  .bss : { . = ALIGN(8); *(.bss*) *(COMMON) . = ALIGN(8); } > RAM :Loader
  .Dev_info : { KEEP(*(.Dev_info)) } > RAM :SgInfo
  /DISCARD/ : { *(.comment) *(.note*) }
}
