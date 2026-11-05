#include "companion_opus_memory.h"
#include <stdio.h>
#include <string.h>
#if defined(_WIN32)
#include <windows.h>
#endif
#define CHECK(x) do {if(!(x)){fprintf(stderr,"line %d: %s\n",__LINE__,#x);return 1;}}while(0)
static void fill(unsigned char *p,size_t n)
{for(size_t i=0;i<n;++i)p[i]=(unsigned char)((i*181u+71u)^(i>>2u));}
int main(void)
{
    unsigned char source[544],actual[544],expected[544];
    unsigned long cases=0;
    fill(source,sizeof(source));
    for(size_t n=0;n<=257;++n)for(size_t a=0;a<16;++a)for(size_t b=0;b<16;++b) {
        memset(actual,0xa5,sizeof(actual));memcpy(expected,actual,sizeof(actual));
        memcpy(expected+32+a,source+32+b,n);
        CHECK(companion_opus_copy(actual+32+a,source+32+b,n)==actual+32+a);
        CHECK(memcmp(actual,expected,sizeof(actual))==0);++cases;
        memset(expected+32+a,0,n);
        CHECK(companion_opus_clear(actual+32+a,n)==actual+32+a);
        CHECK(memcmp(actual,expected,sizeof(actual))==0);++cases;
        fill(actual,sizeof(actual));memcpy(expected,actual,sizeof(actual));
        memmove(expected+32+a,expected+32+b,n);
        CHECK(companion_opus_move(actual+32+a,actual+32+b,n)==actual+32+a);
        CHECK(memcmp(actual,expected,sizeof(actual))==0);++cases;
    }
    /* Larger disjoint moves and group boundaries, including self moves. */
    for(size_t n=0;n<=257;++n)for(size_t a=0;a<16;++a) {
        fill(actual,sizeof(actual));memcpy(expected,actual,sizeof(actual));
        memmove(expected+272+a,expected+8+a,n);
        companion_opus_move(actual+272+a,actual+8+a,n);
        CHECK(memcmp(actual,expected,sizeof(actual))==0);++cases;
    }
#if defined(_WIN32)
    SYSTEM_INFO info;GetSystemInfo(&info);size_t page=info.dwPageSize;DWORD prior;
    unsigned char *input=VirtualAlloc(NULL,page*2u,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE);
    unsigned char *output=VirtualAlloc(NULL,page*2u,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE);
    CHECK(input && output);CHECK(VirtualProtect(input+page,page,PAGE_NOACCESS,&prior));
    CHECK(VirtualProtect(output+page,page,PAGE_NOACCESS,&prior));fill(input,page);
    for(size_t n=0;n<=257;++n) {
        unsigned char *s=input+page-n,*d=output+page-n;
        companion_opus_copy(d,s,n);CHECK(!n || memcmp(d,s,n)==0);++cases;
        companion_opus_clear(d,n);for(size_t i=0;i<n;++i)CHECK(d[i]==0);++cases;
    }
    CHECK(VirtualFree(input,0,MEM_RELEASE));CHECK(VirtualFree(output,0,MEM_RELEASE));
#endif
    CHECK(companion_opus_copy(NULL,NULL,0)==NULL);
    CHECK(companion_opus_move(NULL,NULL,0)==NULL);
    CHECK(companion_opus_clear(NULL,0)==NULL);
    printf("OPUS_MEMORY_LIBC_EQUIVALENCE cases=%lu SOFTWARE_ONLY\n",cases);
    return 0;
}
