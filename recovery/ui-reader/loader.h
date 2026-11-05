#ifndef COMP_WBA_FACTORY_LOADER_H
#define COMP_WBA_FACTORY_LOADER_H
#include <stdbool.h>
#include <stdint.h>
#define COMP_FACTORY_BASE UINT32_C(0x90000000)
#define COMP_FACTORY_NOR_BYTES UINT32_C(0x1000000)
#ifndef COMP_WBA_NOR_UI_BYTES
#error "Factory writer must bind the actual resource extent explicitly"
#endif
#define COMP_FACTORY_UI_BYTES COMP_WBA_NOR_UI_BYTES
#define COMP_FACTORY_BOND_A (COMP_FACTORY_UI_BYTES + UINT32_C(0xC000))
#define COMP_FACTORY_BOND_END (COMP_FACTORY_UI_BYTES + UINT32_C(0xF000))
bool factory_mutation_allowed(uint32_t offset,uint32_t bytes);
#if defined(COMP_FACTORY_DEVELOPMENT_FORMAT) && COMP_FACTORY_DEVELOPMENT_FORMAT
#define COMP_FACTORY_WRITE_BYTES COMP_FACTORY_NOR_BYTES
#else
#define COMP_FACTORY_WRITE_BYTES COMP_FACTORY_UI_BYTES
#endif
/* CubeProgrammer virtual addresses; SPI3 NOR is NOT memory mapped. */
bool factory_hw_init(void);
bool factory_hw_read(uint32_t offset, uint8_t *data, uint32_t size);
bool factory_hw_write(uint32_t offset, const uint8_t *data, uint32_t size);
bool factory_hw_erase(uint32_t offset);
int Init(void);
int Read(uint32_t address, uint32_t size, uint8_t *buffer);
int Write(uint32_t address, uint32_t size, uint8_t *buffer);
int SectorErase(uint32_t start, uint32_t end);
int MassErase(void);
#endif
