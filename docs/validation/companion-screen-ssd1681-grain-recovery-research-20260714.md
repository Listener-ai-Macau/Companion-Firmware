# SSD1681 grain recovery research - 2026-07-14

Status: `P0 / recovery candidate ready`

## Physical result

The operator completed the requested 20 second power removal, kept FTS02 `P3` at
`2.2`, reseated and latched the 24-pin e-paper FPC in `P5`, left touch FPC `P6`
untouched, restored USB, and pressed the NUCLEO physical RESET. The panel did not
recover from black-white grain/noise.

## Official reference

- Good Display package: `S-GDEY0154D67-FP-Touch.rar`
- Package SHA-256: `202ADAB27515FDBA790565F643C3C83C52C11FF36844E8C387F66676C3D82CD4`
- Reference source: `HARDWARE/EPD/Display_EPD_W21.c`
- Target: GDEY0154D67-T03, 200 x 200, SSD1681

## Sequence comparison

| Area | Good Display reference | Current WB55 target | Result |
|---|---|---|---|
| Software SPI | SCK low, set MOSI, SCK high, SCK low | Same edge order | match |
| Hardware reset | RST low 10 ms, high 10 ms | Same | match |
| Software reset | wait ready, `0x12`, wait ready | Same | match |
| Full init | `01 C7 00 00`, `11 01`, full `44/45`, `3C 05`, `18 80`, full `4E/4F` | Same values | match |
| BUSY polarity | raw GPIO, loop while high, continue low | low is ready | match |
| Normal full data | `0x24`, 5000 bytes, `0x22 F7`, `0x20` | `0x26` same frame, then `0x24`, then `F7` | differs |

The GDEY0154D67-T03 PDF contains contradictory prose around BUSY, but the matching
official source reads the raw GPIO without inversion and explicitly loops while it
is high. The executable reference behavior therefore supports high-busy/low-ready.

## FTS02 analog repair map

The FTS02 schematic and its page 9 troubleshooting instructions identify the
panel's external boost network as:

- `L2`: 47 uH, 500 mA inductor for SSD-series controllers.
- `Q1`: Si1308EDL MOSFET; the manual says the MOSFET is the most common failing
  component and permits a suitable AO3400 substitute.
- `D2`, `D3`, `D4`: MBR0530 Schottky diodes.
- `C6`, `C7`, `C8`, `C9`: the nearby input/pump/output capacitors; the manual
  specifically warns that inadequate voltage rating can destroy boost capacitors.
- `P3=2.2`: selects the 2.2 ohm `RESE` current-feedback resistor required by the
  SSD controller family.

The vendor troubleshooting order is: measure PREVGH/PREVGL; if boost fails,
inspect component choice, capacitor rating, soldering and especially Q1; if boost
passes, inspect the FPC connector/contact; inspect software last. This matches the
current evidence because the digital command/BUSY path already passes.

## Recovery decision

Add a production-off diagnostic switch which leaves the normal product path
unchanged and makes full refresh match the official normal-full sequence exactly:
write only `0x24`, then activate `0xF7`. Build and flash deterministic white and
black variants separately, capture BUSY, and compare the physical panel result.

Passing evidence requires both solid white and solid black plus a BUSY transition.
Another grain/noise result with BUSY fixed low moves the P0 away from rendering and
toward the control, refresh-voltage, FTS02, or panel path.
