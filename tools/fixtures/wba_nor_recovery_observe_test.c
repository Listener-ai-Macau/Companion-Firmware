#define main previous_nor_fixture_main
#include "wba_nor_suspend_test.c"
#undef main

static bool wrong_id, change_busy_after_sr2;
static unsigned commands[256];
static bool observed_transfer(void *c,const uint8_t *tx,uint8_t *rx,size_t n,uint32_t timeout)
{
    if (tx && !f.command) commands[tx[0]]++;
    bool ok=transfer(c,tx,rx,n,timeout);
    if (ok && rx && !tx && f.command==0x9Fu && wrong_id) rx[2]^=1u;
    if (ok && tx && rx && n==2u && tx[0]==0x35u && change_busy_after_sr2) f.sr1|=1u;
    return ok;
}
static void no_mutation(void)
{
    assert(!commands[0x06]&&!commands[0x02]&&!commands[0x20]&&!commands[0xD8]);
    assert(!commands[0x75]&&!commands[0x7A]&&!commands[0x66]&&!commands[0x99]&&!commands[0xAB]);
    assert(!f.selected);
}
int main(void)
{
    reset();companion_spi_nor_stm32wba_t n=make();n.config.transfer=observed_transfer;
    memset(commands,0,sizeof(commands));
    assert(companion_spi_nor_stm32wba_recovery_observe(&n)==OK);no_mutation();
    f.sr1=1u;assert(companion_spi_nor_stm32wba_recovery_observe(&n)==PENDING);f.sr1=2u;
    assert(companion_spi_nor_stm32wba_recovery_observe(&n)==PENDING);f.sr1=0u;f.sr2=128u;
    assert(companion_spi_nor_stm32wba_recovery_observe(&n)==PENDING);f.sr2=0u;
    wrong_id=true;assert(companion_spi_nor_stm32wba_recovery_observe(&n)==ERROR);wrong_id=false;
    f.fail_sr2=true;assert(companion_spi_nor_stm32wba_recovery_observe(&n)==ERROR);
    change_busy_after_sr2=true;assert(companion_spi_nor_stm32wba_recovery_observe(&n)==PENDING);
    change_busy_after_sr2=false;f.sr1=0u;
    unsigned prior_id=commands[0x9F];n.erase_active=true;
    assert(companion_spi_nor_stm32wba_recovery_observe(&n)==PENDING&&commands[0x9F]==prior_id);
    n.erase_active=false;n.erase_suspend_supported=false;
    assert(companion_spi_nor_stm32wba_recovery_observe(&n)==COMPANION_SPI_NOR_STM32WBA_UNSUPPORTED);
    n.erase_suspend_supported=true;n.probed=false;
    assert(companion_spi_nor_stm32wba_recovery_observe(&n)==COMPANION_SPI_NOR_STM32WBA_NOT_PROBED);
    no_mutation();
    puts("PASS read-only recovery observation: exact ID, WIP/WEL/SUS, lost transport, late BUSY, existing owner and no mutating commands; exclusive caller still required; software model only");
    return 0;
}
