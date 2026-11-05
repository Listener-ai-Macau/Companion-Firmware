ENTRY(busy_capture_entry)
MEMORY { CAPTURE (rx) : ORIGIN = 0x2001a000, LENGTH = 1K }
SECTIONS {
    .text : { KEEP(*(.capture_entry)) *(.text*) *(.rodata*) } > CAPTURE
    /DISCARD/ : { *(.ARM.exidx*) *(.ARM.extab*) *(.comment*) *(.note*) }
    ASSERT(SIZEOF(.text) <= 0x400, "Capture code overlaps result")
}
