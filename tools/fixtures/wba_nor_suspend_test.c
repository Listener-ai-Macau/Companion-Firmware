#include "spi_nor_stm32wba.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

/* Command-level NOR model: erased data is published only on real completion;
 * SR1.BUSY and SR2.SUS are independent, as with programming during suspension.
 * This validates driver ownership/races, not electrical timing or real audio. */
#ifndef COMP_NOR_FIXTURE_BYTES
#define COMP_NOR_FIXTURE_BYTES 131072u
#endif
typedef struct {
    uint8_t bytes[COMP_NOR_FIXTURE_BYTES], sfdp[128], sr1, sr2, command;
    uint32_t address, now, erase_address, erase_bytes, erases, suspends, resumes;
    uint32_t reads, writes, delays, program_polls, erase_polls, fail_read_delay_ms, last_read_timeout;
    uint8_t fail_command;
    bool selected, erased, ignored_suspend, complete_on_suspend, ignored_resume;
    bool fail_sr2, fail_payload, automatic_erase, fail_deassert_once, fail_read_data_once;
} fake_t;
static fake_t f;
#define OK COMPANION_SPI_NOR_STM32WBA_OK
#define PENDING COMPANION_SPI_NOR_STM32WBA_PENDING
#define ERROR COMPANION_SPI_NOR_STM32WBA_ERROR

static void le32(uint8_t *p, uint32_t v)
{ for (unsigned i=0;i<4;i++) p[i]=(uint8_t)(v>>(i*8u)); }
static void complete(void)
{
    memset(f.bytes+f.erase_address,255,f.erase_bytes);
    f.sr1=0; f.sr2=0; f.erased=true;
}
static void reset(void)
{
    memset(&f,0,sizeof(f)); memset(f.bytes,255,sizeof(f.bytes));
    memset(f.sfdp,255,sizeof(f.sfdp)); memcpy(f.sfdp,"SFDP",4);
    f.sfdp[4]=6; f.sfdp[5]=1; f.sfdp[6]=0; f.sfdp[7]=255;
    f.sfdp[8]=0; f.sfdp[9]=6; f.sfdp[10]=1; f.sfdp[11]=16;
    f.sfdp[12]=48; f.sfdp[13]=0; f.sfdp[14]=0; f.sfdp[15]=255;
    le32(f.sfdp+52,0x07FFFFFFu);
    f.sfdp[76]=12; f.sfdp[77]=0x20; f.sfdp[78]=16; f.sfdp[79]=0xD8;
    le32(f.sfdp+88,0x80u);
    le32(f.sfdp+92,0x330001ECu); /* 20us latency, 64us resume guard, nibble E */
    le32(f.sfdp+96,0x757A757Au);
}
static bool cs(void *c, bool active)
{ (void)c; assert(f.selected!=active); f.selected=active; if(active)f.command=0; else if(f.fail_deassert_once){f.fail_deassert_once=false;return false;} return true; }
static bool transfer(void *c,const uint8_t *tx,uint8_t *rx,size_t n,uint32_t timeout)
{
    (void)c; assert(f.selected && timeout && n);
    /* WBA/EF6018 status reads combine opcode and dummy byte under one CS.
     * Execute the same model command/status phases; neither invent a ready
     * result nor skip program/erase completion or injected failures. */
    if(tx && rx && n==2u && !f.command && (tx[0]==5u || tx[0]==0x35u)) {
        rx[0]=0u;
        return transfer(c,tx,NULL,1u,timeout) && transfer(c,NULL,rx+1u,1u,timeout);
    }
    if(tx && !f.command) {
        f.command=tx[0];
        if(n==4 || n==5)f.address=((uint32_t)tx[1]<<16)|((uint32_t)tx[2]<<8)|tx[3];
        if(f.command==6) { assert(!(f.sr1&1)); f.sr1|=2; }
        if(f.command==0x20 || f.command==0x52 || f.command==0xD8) {
            assert(!(f.sr1&1) && !(f.sr2&128) && (f.sr1&2));
            f.erases++; f.erase_address=f.address;
            f.erase_bytes=f.command==0x20?4096u:f.command==0x52?32768u:65536u;
            assert(f.erase_address+f.erase_bytes<=sizeof(f.bytes));
            f.sr1=1; f.erased=false; f.erase_polls=0;
        }
        if(f.command==0x75) {
            f.suspends++;
            if(f.complete_on_suspend)complete();
            else if(!f.ignored_suspend) {assert((f.sr1&1)&&!(f.sr2&128));f.sr1=0;f.sr2=128;}
        }
        if(f.command==0x7A) {
            f.resumes++; assert(!(f.sr1&1)&&(f.sr2&128));
            if(!f.ignored_resume) {f.sr1=1;f.sr2=0;}
        }
        if(f.fail_command==f.command) {f.fail_command=0;return false;}
        return true;
    }
    if(rx) {
        if(f.command==0x9F) {assert(n==3);rx[0]=0xEF;rx[1]=0x60;rx[2]=0x18;return true;}
        if(f.command==0x05) {
            assert(n==1);
            if(f.program_polls && --f.program_polls==0)f.sr1=0;
            if(f.automatic_erase && !(f.sr2&128) && (f.sr1&1) &&
                !f.program_polls && ++f.erase_polls>=3)complete();
            rx[0]=f.sr1;return true;
        }
        if(f.command==0x35) {
            assert(n==1);if(f.fail_sr2){f.fail_sr2=false;return false;}rx[0]=f.sr2;return true;
        }
        if(f.command==0x5A) {assert(f.address+n<=sizeof(f.sfdp));memcpy(rx,f.sfdp+f.address,n);return true;}
        assert(f.command==3 && !(f.sr1&1));
        f.last_read_timeout=timeout;
        if(f.fail_read_data_once){f.fail_read_data_once=false;f.now+=f.fail_read_delay_ms<timeout?f.fail_read_delay_ms:timeout;memset(rx,0xA5,n/2u);return false;}
        assert(!(f.sr2&128) || f.address>=f.erase_address+f.erase_bytes ||
               f.address+n<=f.erase_address);
        assert(f.address+n<=sizeof(f.bytes)); memcpy(rx,f.bytes+f.address,n);f.reads++;return true;
    }
    assert(tx && f.command==2 && (f.sr1&2) && !(f.sr1&1));
    assert(f.address+n<=sizeof(f.bytes) && n<=256-(f.address%256));
    assert(!(f.sr2&128) || f.address>=f.erase_address+f.erase_bytes || f.address+n<=f.erase_address);
    for(size_t i=0;i<n;i++)f.bytes[f.address+i]&=tx[i];
    f.sr1=1; f.program_polls=3; f.writes++;
    if(f.fail_payload){f.fail_payload=false;return false;}return true;
}
static uint32_t now(void *c) { (void)c;return f.now; }
static void delay(void *c,uint32_t ms) { (void)c;f.now+=ms;f.delays++; }
static companion_spi_nor_stm32wba_t make(void)
{
    companion_spi_nor_stm32wba_t n;
    companion_spi_nor_stm32wba_config_t config={0};
    config.target=COMPANION_SPI_NOR_STM32WBA_TARGET_WBA55;
    config.chip_select=cs;config.transfer=transfer;config.now_ms=now;config.delay_ms=delay;
    config.sector_erase_timeout_ms=100;
    assert(companion_spi_nor_stm32wba_init(&n,&config));
    assert(companion_spi_nor_stm32wba_probe(&n,NULL)==OK);return n;
}
static void start(companion_spi_nor_stm32wba_t *n)
{ memset(f.bytes,0,65536);assert(companion_spi_nor_stm32wba_erase_step(n,0,65536)==PENDING); }
static void suspend(companion_spi_nor_stm32wba_t *n)
{
    f.now+=n->resume_guard_ms;
    assert(companion_spi_nor_stm32wba_erase_suspend_step(n)==PENDING);
    assert(!companion_spi_nor_stm32wba_erase_is_suspended(n));
    f.now+=n->suspend_wait_ms;
    assert(companion_spi_nor_stm32wba_erase_suspend_step(n)==OK);
    assert(companion_spi_nor_stm32wba_erase_is_suspended(n));
}
static void capabilities(void)
{
    for(unsigned which=0;which<6;which++) {
        reset();
        if(which==0)f.sfdp[95]|=128;
        if(which==1)f.sfdp[99]=0xB0;
        if(which==2)f.sfdp[92]=0xCC;
        if(which==3)f.sfdp[52]=0xEE;
        if(which==4)f.sfdp[88]=0x90;
        if(which==5)f.sfdp[11]=9;
        companion_spi_nor_stm32wba_t n=make();assert(!n.erase_suspend_supported);
        start(&n);f.now+=10;assert(companion_spi_nor_stm32wba_erase_suspend_step(&n)==COMPANION_SPI_NOR_STM32WBA_UNSUPPORTED);
        assert(f.suspends==0 && n.erase_active);
    }
    puts("PASS capability: density/geometry/restrictions/opcodes/negative-support-bit fail closed");
}
static void owner_and_audio_page(void)
{
    reset();companion_spi_nor_stm32wba_t n=make();assert(n.erase_suspend_supported);
    assert(n.suspend_wait_ms==2 && n.resume_guard_ms==2);
    uint8_t value=0xA5,read=0;start(&n);uint32_t delays=f.delays;
    assert(companion_spi_nor_stm32wba_erase_suspend_step(&n)==PENDING && f.suspends==0);
    f.now+=2;assert(companion_spi_nor_stm32wba_erase_suspend_step(&n)==PENDING);
    assert(companion_spi_nor_stm32wba_read(&n,65536,&read,1)==PENDING);
    f.now++;assert(companion_spi_nor_stm32wba_erase_suspend_step(&n)==PENDING);
    f.now++;assert(companion_spi_nor_stm32wba_erase_suspend_step(&n)==OK);
    assert(f.delays==delays && !f.erased && n.erase_active);
    assert(companion_spi_nor_stm32wba_read(&n,0,&read,1)==PENDING);
    assert(companion_spi_nor_stm32wba_read(&n,65535,&read,2)==PENDING);
    assert(companion_spi_nor_stm32wba_program(&n,65535,&value,1)==PENDING);
    assert(companion_spi_nor_stm32wba_erase_4k(&n,65536)==PENDING);
    assert(companion_spi_nor_stm32wba_erase_step(&n,65536,4096)==COMPANION_SPI_NOR_STM32WBA_BAD_PARAM);
    assert(companion_spi_nor_stm32wba_program(&n,65536,&value,1)==OK);
    assert(companion_spi_nor_stm32wba_read(&n,65536,&read,1)==OK && read==value);
    f.now+=5000;assert(companion_spi_nor_stm32wba_erase_step(&n,0,65536)==PENDING);
    assert(companion_spi_nor_stm32wba_read(&n,65536,&read,1)==PENDING);
    f.now+=2;assert(companion_spi_nor_stm32wba_erase_step(&n,0,65536)==PENDING);
    assert(companion_spi_nor_stm32wba_erase_step(&n,0,65536)==PENDING);
    complete();assert(companion_spi_nor_stm32wba_erase_step(&n,0,65536)==OK);
    assert(!n.erase_active && f.erases==1 && f.bytes[0]==255 && f.bytes[65536]==value);
    puts("PASS owner: other-sector PCM page allowed, overlap/nested erase blocked, suspended wall time excluded");
}
static void races_and_transport(void)
{
    uint8_t b=0xAA;
    reset();companion_spi_nor_stm32wba_t n=make();start(&n);
    f.complete_on_suspend=true;f.now+=2;
    assert(companion_spi_nor_stm32wba_erase_suspend_step(&n)==PENDING);
    f.now+=2;assert(companion_spi_nor_stm32wba_erase_suspend_step(&n)==OK && n.erase_active);
    assert(companion_spi_nor_stm32wba_program(&n,65536,&b,1)==OK);
    assert(companion_spi_nor_stm32wba_erase_step(&n,0,65536)==OK && f.erases==1);
    reset();n=make();start(&n);f.fail_command=0x75;f.now+=2;
    assert(companion_spi_nor_stm32wba_erase_suspend_step(&n)==ERROR);
    assert(companion_spi_nor_stm32wba_read(&n,65536,&b,1)==PENDING);
    f.now+=2;f.fail_sr2=true;assert(companion_spi_nor_stm32wba_erase_suspend_step(&n)==ERROR && n.erase_active);
    assert(companion_spi_nor_stm32wba_erase_suspend_step(&n)==OK);
    f.fail_command=0x7A;assert(companion_spi_nor_stm32wba_erase_step(&n,0,65536)==ERROR);
    f.now+=2;assert(companion_spi_nor_stm32wba_erase_step(&n,0,65536)==PENDING);
    complete();assert(companion_spi_nor_stm32wba_erase_step(&n,0,65536)==OK);
    reset();n=make();start(&n);suspend(&n);f.ignored_resume=true;
    assert(companion_spi_nor_stm32wba_erase_step(&n,0,65536)==PENDING);
    f.now+=2;assert(companion_spi_nor_stm32wba_erase_step(&n,0,65536)==ERROR && n.erase_active);
    f.ignored_resume=false;assert(companion_spi_nor_stm32wba_erase_step(&n,0,65536)==PENDING);
    f.now+=2;assert(companion_spi_nor_stm32wba_erase_step(&n,0,65536)==PENDING);
    complete();assert(companion_spi_nor_stm32wba_erase_step(&n,0,65536)==OK && f.erases==1);
    reset();n=make();f.fail_command=0xD8;
    assert(companion_spi_nor_stm32wba_erase_step(&n,0,65536)==ERROR && n.erase_active);
    complete();assert(companion_spi_nor_stm32wba_erase_step(&n,0,65536)==ERROR);
    puts("PASS races: natural completion latched once; uncertain suspend/resume/status/erase retain ownership");
}
static void reset_recovery_and_failed_program(void)
{
    reset();companion_spi_nor_stm32wba_t n=make();start(&n);suspend(&n);
    f.fail_payload=true;uint8_t value=0x99;
    assert(companion_spi_nor_stm32wba_program(&n,65536,&value,1)==ERROR);
    assert(companion_spi_nor_stm32wba_read(&n,65536,&value,1)==PENDING);
    while(f.program_polls) {uint8_t v;assert(cs(NULL,true));uint8_t cmd=5;assert(transfer(NULL,&cmd,NULL,1,1));assert(transfer(NULL,NULL,&v,1,1));assert(cs(NULL,false));}
    assert(companion_spi_nor_stm32wba_read(&n,65536,&value,1)==OK && value==0x99);
    f.automatic_erase=true;n=make();assert(n.erase_suspend_supported && !n.erase_active);
    assert(f.resumes==1 && f.erases==1 && f.erased && f.sr2==0);
    puts("PASS reset: qualified prior SUS resumes before mount; failed in-suspend program blocks read until BUSY clears");
}
int main(void)
{
    capabilities();owner_and_audio_page();races_and_transport();reset_recovery_and_failed_program();
    printf("PASS NOR suspend driver behavior; context=%zu, no hardware/audio qualification claimed\n",
           sizeof(companion_spi_nor_stm32wba_t));return 0;
}
