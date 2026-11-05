"""Exercise the actual engineering GPIO binding; this is not hardware evidence."""
from pathlib import Path
import argparse, hashlib, json, subprocess
from verify_wba_spi_nor_adapter import find_vsdevcmd

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'platform/stm32wba55_companion_v11/board_hal.c'
PRELUDE = r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#define COMP_V11_PANEL_SOFTWARE_SPI 1
#define COMP_SSD1681_WBA_FRAME_BYTES 5000
#define COMP_V11_POWER_READY 1
#define COMP_SSD1681_WBA_COMPLETE 2
#define GPIOA 0
#define GPIOB 1
#define GPIO_PIN_0 0
#define GPIO_PIN_4 4
#define GPIO_PIN_11 11
#define GPIO_PIN_12 12
#define GPIO_PIN_15 15
#define GPIO_PIN_RESET 0
#define GPIO_PIN_SET 1
#define GPIO_MODE_OUTPUT_PP 1
#define GPIO_MODE_AF_PP 2
#define GPIO_MODE_INPUT 3
#define GPIO_NOPULL 0
#define GPIO_AF5_SPI1 5
#define __NOP() ((void)0)
static int spi_shared, irq, busy, edges, bits[512], modes[2][16], pins[2][16];
static bool spi_owned;
static uint8_t incoming[10016];
static unsigned incoming_size, incoming_bit;
static char console[1024];
static struct {
    struct { int state; } display_power;
    struct { bool running; } microphone;
    bool playback_active;
    struct { int status; } panel;
} board, *active_board = &board;
static unsigned __get_IPSR(void) { return (unsigned)irq; }
static void spi_disable(int *spi) { assert(spi == &spi_shared && spi_owned); }
#define __HAL_SPI_DISABLE(spi) spi_disable(spi)
static void gpio(int port,int pin,int mode,int pull,int af)
{
    (void)pull;
    if (mode == GPIO_MODE_AF_PP) assert(af == 5);
    if (port == GPIOA && pin == 15 && mode == GPIO_MODE_INPUT)
        assert(pins[GPIOB][4] == 1 && pins[GPIOA][11] == 1 && pins[GPIOB][0] == 0);
    modes[port][pin] = mode;
}
static void HAL_GPIO_WritePin(int port,int pin,int value)
{
    if (port == GPIOB && pin == 4 && value == 1 && pins[port][pin] == 0 &&
        pins[GPIOB][0] == 0 && modes[GPIOA][15] == GPIO_MODE_OUTPUT_PP) {
        assert(edges < 512 && spi_owned && pins[GPIOB][15] == 1);
        bits[edges++] = pins[GPIOA][15];
    }
    pins[port][pin] = value;
}
static int HAL_GPIO_ReadPin(int port,int pin)
{
    assert(port == GPIOA && pin == 15 && modes[port][pin] == GPIO_MODE_INPUT &&
        pins[GPIOB][4] == 1 && spi_owned && incoming_bit < incoming_size * 8);
    unsigned at = incoming_bit++;
    return (incoming[at / 8] >> (7 - at % 8)) & 1;
}
static bool comp_v11_hal_panel_busy(void) { return busy != 0; }
static bool comp_v11_hal_debug_write(const char *line)
{ size_t at=strlen(console), n=strlen(line); assert(at+n < sizeof(console)); memcpy(console+at,line,n+1); return true; }
'''
TEST = r'''
static void reset(void)
{
    memset(&board,0,sizeof(board)); active_board=&board;
    board.display_power.state=COMP_V11_POWER_READY; board.panel.status=COMP_SSD1681_WBA_COMPLETE;
    memset(pins,0,sizeof(pins)); memset(modes,0,sizeof(modes));
    pins[GPIOB][0]=1; edges=irq=busy=0; spi_owned=false;
    incoming_size=incoming_bit=0; console[0]=0;
}
static void restored(void)
{
    assert(!spi_owned && pins[GPIOB][0] == 1 && pins[GPIOB][4] == 0);
    assert(modes[GPIOA][15] == GPIO_MODE_AF_PP && modes[GPIOB][4] == GPIO_MODE_AF_PP);
}
int main(void)
{
    uint8_t bytes[]={0xA5,0x3C}; reset();
    assert(comp_v11_hal_panel_transfer(true,bytes,2)); assert(edges==16); restored();
    for (unsigned bit=0;bit<16;++bit) assert(bits[bit] == ((bytes[bit/8]>>(7-bit%8))&1));
    reset(); assert(!comp_v11_hal_panel_transfer(true,NULL,2));
    assert(!comp_v11_hal_panel_transfer(true,bytes,0));
    irq=1; assert(!comp_v11_hal_panel_transfer(true,bytes,2)); irq=0;
    spi_owned=true; assert(!comp_v11_hal_panel_transfer(true,bytes,2)); spi_owned=false;
    board.display_power.state=0; assert(!comp_v11_hal_panel_transfer(true,bytes,2));
    active_board=NULL; assert(!comp_v11_hal_panel_transfer(true,bytes,2)); assert(edges==0);
    uint8_t frame[5000]; memset(frame,0xFF,sizeof(frame)); reset();
    assert(!comp_v11_hal_panel_audit(NULL,5000)); assert(!comp_v11_hal_panel_audit(frame,4999));
    board.microphone.running=true; assert(!comp_v11_hal_panel_audit(frame,5000));
    board.microphone.running=false; board.playback_active=true; assert(!comp_v11_hal_panel_audit(frame,5000));
    board.playback_active=false; busy=1; assert(!comp_v11_hal_panel_audit(frame,5000)); assert(edges==0);
    reset(); incoming_size=14; memset(incoming,0xFF,incoming_size);
    assert(!comp_v11_hal_panel_audit(frame,5000)); restored();
    assert(incoming_bit==112 && strstr(console,"id_valid=0") && !strstr(console,"ram_bytes="));
    reset(); incoming_size=sizeof(incoming); memset(incoming,0xFF,sizeof(incoming));
    incoming[0]=incoming[1]=incoming[2]=1;
    assert(comp_v11_hal_panel_audit(frame,5000)); restored();
    assert(incoming_bit==incoming_size*8 && strstr(console,"bw_mismatch=0 old_mismatch=0"));
    reset(); incoming_size=sizeof(incoming); memset(incoming,0xFF,sizeof(incoming));
    incoming[0]=incoming[1]=incoming[2]=1; incoming[15]=0;
    assert(!comp_v11_hal_panel_audit(frame,5000)); restored();
    assert(strstr(console,"bw_mismatch=1 old_mismatch=0"));
    puts("PASS_SOFTWARE_ONLY: GPIO bit order, SDIN turnaround, AF restoration, busy/audio/ISR guards, invalid identity and RAM mismatch");
    return 0;
}
'''

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    out = parser.parse_args().output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    source = SOURCE.read_text(encoding='utf-8')
    start = source.index('#if COMP_V11_PANEL_SOFTWARE_SPI')
    end = source.index('bool comp_v11_hal_panel_busy(void)', start)
    harness = out / 'binding.c'
    harness.write_text(PRELUDE + source[start:end] + TEST, encoding='utf-8')
    exe = out / 'test.exe'
    argv = ['cl.exe', '/nologo', '/std:c11', '/W4', '/WX', str(harness), '/Fe:' + str(exe)]
    build = out / 'build.cmd'
    build.write_text('@echo off\ncall "' + str(find_vsdevcmd()) +
                     '" -arch=amd64 -host_arch=amd64 >nul\nif errorlevel 1 exit /b %errorlevel%\n' +
                     subprocess.list2cmdline(argv) + '\n', encoding='utf-8')
    log = []
    for command in (['cmd.exe', '/d', '/c', str(build)], [str(exe)]):
        result = subprocess.run(command, cwd=out, text=True, capture_output=True)
        log.append(result.stdout + result.stderr)
        (out / 'test.log').write_text('\n'.join(log), encoding='utf-8')
        if result.returncode:
            raise RuntimeError('Panel binding test failed: ' + str(out / 'test.log'))
    receipt = {'result': 'PASS_PANEL_GPIO_SOFTWARE_ONLY', 'hardwareAcceptance': 'NOT_RUN',
               'source_sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(), 'output': log[-1].strip()}
    (out / 'result.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
    print(receipt['output'])

if __name__ == '__main__':
    main()
