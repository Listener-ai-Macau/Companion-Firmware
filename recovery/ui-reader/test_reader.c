#include "loader.h"
#include <assert.h>
#include <stdio.h>
static unsigned reads;
bool factory_hw_init(void){return true;}
bool factory_hw_read(uint32_t offset,uint8_t *data,uint32_t size)
{(void)data;assert(size&&offset+size<=COMP_FACTORY_UI_BYTES);reads++;return true;}
int main(void){uint8_t data[1];
 assert(!Read(COMP_FACTORY_BASE,1u,data));assert(Init());
 assert(Read(COMP_FACTORY_BASE,1u,data));
 assert(Read(COMP_FACTORY_BASE+COMP_FACTORY_UI_BYTES-1u,1u,data));
 assert(!Read(COMP_FACTORY_BASE-1u,1u,data));
 assert(!Read(COMP_FACTORY_BASE+COMP_FACTORY_UI_BYTES,1u,data));
 assert(!Read(COMP_FACTORY_BASE+COMP_FACTORY_UI_BYTES-1u,2u,data));
 assert(!Read(COMP_FACTORY_BASE,UINT32_MAX,data));assert(!Read(UINT32_MAX,1u,data));
 assert(!Read(COMP_FACTORY_BASE,1u,NULL));assert(!Read(COMP_FACTORY_BASE,0u,data));
 assert(!Write(COMP_FACTORY_BASE,1u,data));assert(!SectorErase(COMP_FACTORY_BASE,COMP_FACTORY_BASE));assert(!MassErase());
 assert(reads==2u);puts("PASS UI reader: only950272-byte public bank readable; all mutation exports refuse; no board IO");return 0;
}
