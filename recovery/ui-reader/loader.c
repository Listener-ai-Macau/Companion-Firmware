/* SRAM-only recovery of the existing public UI bank. Not product firmware. */
#include "loader.h"
#include <stddef.h>
static bool initialized;
int Init(void) {initialized=false;initialized=factory_hw_init();return initialized?1:0;}
int Read(uint32_t address,uint32_t size,uint8_t *buffer)
{
    if(!initialized||!buffer||!size||address<COMP_FACTORY_BASE)return 0;
    uint32_t offset=address-COMP_FACTORY_BASE;
    if(offset>=COMP_FACTORY_UI_BYTES||size>COMP_FACTORY_UI_BYTES-offset)return 0;
    return factory_hw_read(offset,buffer,size)?1:0;
}
int Write(uint32_t address,uint32_t size,uint8_t *buffer)
{(void)address;(void)size;(void)buffer;return 0;}
int SectorErase(uint32_t start,uint32_t end) {(void)start;(void)end;return 0;}
int MassErase(void) {return 0;}
typedef struct {
    char name[100];uint16_t type;uint32_t start,size,page;uint8_t erased;
    struct {uint32_t count,size;} sectors[10];
} storage_info_t;
_Static_assert(sizeof(storage_info_t)==200,"ST StorageInfo ABI");
#if defined(__GNUC__)
__attribute__((used,section(".Dev_info")))
#endif
const storage_info_t StorageInfo={"Companion_UI85_READ_ONLY",7,COMP_FACTORY_BASE,
    COMP_FACTORY_UI_BYTES,256,0xff,{{COMP_FACTORY_UI_BYTES/4096u,4096u}}};
