# Companion E-Paper Renderer

This directory owns the no-hardware Companion pendant e-paper card model and
framebuffer renderer. The code is intentionally independent from an SPI driver
so it can be tested before a panel is wired.

Supported card inputs:

- Mood, name, event, and reminder cards from the BLE `CardWriteV1` payload.
- Local recording, sync-complete, low-battery, and error states.
- Boot/default card fixtures used by bring-up validation.

Supported display variants:

- `2.13in`: 250 by 122 monochrome pixels.
- `1.54in`: 200 by 200 monochrome pixels.

The renderer produces 1-bit PBM bitmap fixtures with deterministic Bayer
dithering for gray regions. Text rendering uses a compact built-in ASCII font;
unsupported Unicode codepoints are rendered as deterministic placeholder boxes
so multilingual payloads do not disappear.

Hardware boundary:

- Renderer model, text fallback, dithering, dimensions, and framebuffer export
  are AI-testable now.
- Real e-paper SPI timing, busy-pin handling, partial refresh behavior, and
  refresh waveform validation are deferred to later hardware gates.
- BLE callbacks should map `CardWriteV1` into this model and enqueue display
  work; they should not block on panel IO.
