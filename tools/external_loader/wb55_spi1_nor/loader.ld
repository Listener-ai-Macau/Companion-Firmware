ENTRY(Init)

MEMORY
{
    DEVINFO (r)  : ORIGIN = 0x00000000, LENGTH = 0x00000100
    RAM     (rwx): ORIGIN = 0x20000004, LENGTH = 0x0002FFFC
}

SECTIONS
{
    .DevInfo 0x00000000 :
    {
        KEEP(*(.DevInfo))
    } > DEVINFO

    .loader 0x20000004 :
    {
        KEEP(*(.loader_api))
        *(.text*)
        *(.rodata*)
        *(.data*)
    } > RAM

    .bss (NOLOAD) :
    {
        *(.bss*)
        *(COMMON)
    } > RAM

    /DISCARD/ :
    {
        *(.comment)
        *(.note*)
        *(.eh_frame*)
    }
}
