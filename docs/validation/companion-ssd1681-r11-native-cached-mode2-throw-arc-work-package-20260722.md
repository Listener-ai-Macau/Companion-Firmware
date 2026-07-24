# R11 Native Cached Mode2 Throw Arc Work Package

Status: registry-first, offline implementation package under COMP-REQ-367. Primary review is required before any physical authorization. This package creates no physical authorization.

## Protected R2 Floor

COMP-REQ-364 archives the accepted cached Mode2 r2 observation at:

`.cache/validation/wb55-r10-native-guarded-corridor-cached-mode2-cadence-execute-20260722-r2`

The accepted status is `PASS_MACHINE_R10_NATIVE_GUARDED_CORRIDOR_CACHED_MODE2_CADENCE_OBSERVATION_RESTORED_OWNER_PASSED`, with canonical selection `通过` and the CRLF-only operator note SHA-256 `7EB70257593DA06F682A3DDDA54A9D260D4FC514F645237F5CA74B08F8DA61A6`.

Evidence identities:

- Stage: `5BABE221C090E41BBF3EADF758C4FA83CABD50D2F77705377F35732D938DF056`
- Operator review: `819EFDE658185E0C8C23633B1F6F5E7E303CAA26BED2021771E952DAD8283EA7`
- Operator result: `9912F1EF55BC4E9B60A5688341509BC29CA1730F480F9B9F7B011822469A2E0E`
- Monitor: `BF83A241F6DCEC6B0CC5D74AE7D5189A1B17A5B66EB9ADB927B4231826171D67`
- Qualification: `184A385B73CCD22A1CBC50B7B57727623EAAA8701581B2BB130DD2CE895672DD`

The machine evidence is 16 qualification frames, 58 loop records, BUSY 441..443 ms, transaction 444..445 ms, maximum start delta 483 ms, ring peak 32199/65536, baseline reset/FF counts 1/1, movement reset/FF counts 0/0, movement CF count 1, and retries 0. Promptless dual-plane White pre/postclean, exact 524288-byte restore/readback SHA-256 `223F6E7A7DB8E5562D0F7C34ED4F023DA7E37F5266505A6C84D5BD6FE304CD7C`, and normal resume passed.

The protected floor is a complete, clean, latency-accepted 24x24 ball using official cached Mode2. The owner’s newest steering is exactly:

> 我感觉这次修的很可以啊，你看下这个球的运动速度能不能加快点？然后做那种抛球的动画，我感觉这次就很可以。

## Candidate

Candidate identity: `r11_native_cached_mode2_throw_arc`.

The purpose is to test a visibly faster two-dimensional throw arc, not to claim that the approximately 442 ms official waveform core refresh lower bound has been reduced. The spatial motion may appear faster because each frame advances 12 px horizontally; the machine contract must report this as spatial step speed, never as a 6x refresh-rate claim. The throw arc is a deterministic lower-driver diagnostic payload and a possible foundation for later expression choreography; this package does not authorize art, V9, Rig, CRIG, browser or production integration.

## Fixed Contract

- Preserve the 24x24 centered integer solid disk with exactly 448 black pixels.
- Use official cached Mode2: one baseline at x=32 with `0x22=0xFF`, then movement frames with no reset and exactly one `0x22=0xCF` activation.
- Preserve one activation per movement, complete current bytes, full previous/current framebuffer diff calculation, and full current fixed-corridor rewrite/re-whitening.
- Preserve default-off and production-off boundaries and the existing promptless dual-White, qualification, canonical single-popup, stop, cleanup, exact restore/readback, normal-resume and process-audit lifecycle.
- Use nine unique top-left positions, in this exact order:
  `[(32,112),(44,91),(56,76),(68,67),(80,64),(92,67),(104,76),(116,91),(128,112)]`.
- Qualification is exactly 16 transitions: A0 through A8 and back to A0, with the sequence `A0,A1,A2,A3,A4,A5,A6,A7,A8,A7,A6,A5,A4,A3,A2,A1,A0`.
- Continuous observation uses the same bidirectional 16-transition loop repeatedly, with no teleport and no dwell. Each transition advances 12 px horizontally; total travel is 96 px and apex height is 48 px.
- Use a fixed guarded arc corridor of x-bytes 3..19 and y=64..135: 17 x 72 = 1224 bytes. Every activation writes the complete current corridor bytes and therefore re-whitens the full trajectory corridor.
- BUSY must be <=600 ms. `transaction_elapsed_ms` must be <=460 ms. Real qualification and loop start-to-start cadence must be `1..480 ms` inclusive. `<=450 ms` is an aspirational optimization target only, not a physical acceptance requirement. These are machine gates, not physical claims before Execute.
- Popup eligibility requires the complete 16-transition qualification, at least two contiguous loop records and the existing real cadence measurement gate. The canonical Chinese acceptance window remains the sole human boundary.

## Compact Telemetry Budget

COMP-REQ-365 records the accepted r2 timing facts: BUSY 441..443 ms, transaction 444..445 ms and start_delta 482..483 ms. The approximately 37..39 ms difference is treated as the blocking cost of the accepted approximately 394-byte ASCII UART line at 115200 baud, not as SSD1681 refresh time. The official cached Mode2 waveform and the protected visual floor remain unchanged; this package does not authorize a custom waveform.

R11 telemetry must keep the same 115200 baud and use one exact candidate prefix followed by single-letter `key=value` fields separated by one ASCII space. The prefix identifies `r11_native_cached_mode2_throw_arc`; the required key mapping is:

| Key | Meaning |
| --- | --- |
| `s` | schema |
| `q` or `i` | qualification sequence or loop sequence, exactly one of the two |
| `p` / `n` | previous/current node |
| `w` | exact corridor window |
| `h` | complete 64-hex current payload SHA |
| `r` / `t` / `b` / `d` | reset elapsed / transaction elapsed / BUSY elapsed / start delta |
| `a` / `x` / `y` | activation / source resets / ready checks |
| `f` / `c` / `l` | source FF / source CF / custom LUT loads |
| `v` / `g` | forbidden count / complete landing |

The grammar is strict: each key occurs exactly once, no key outside this mapping is accepted, `q` and `i` cannot be mixed, and the record ends in exactly one CRLF. Every qualification and loop record must include all required fields above, including the complete payload SHA. The complete record hard limit is 192 bytes including CRLF; the ring remains a fixed 65536 bytes.

The UART-budget oracle must render the worst-case qualification and loop records, including a UINT32_MAX loop sequence, and prove each is <=192 bytes. It must compare the measured byte length with the accepted v13 394-byte line and prove a reduction of at least 200 bytes. At 115200 baud, using the existing 10-bit-per-byte UART budget, the theoretical saving must be at least 17 ms. This is a host timing budget only and must never be reported as a physical cadence result.

## Machine Evidence

The offline oracle must calculate every full-frame SHA, exact diff union, corridor bytes and exact 24x24/448 landing for all qualification and loop transitions. It must prove that each landing is a complete disk and that every emitted payload is the current framebuffer restricted to the fixed 1224-byte corridor.

Targeted negative fixtures must reject:

- Any changed node, disk geometry, payload or corridor window.
- Teleport, wrong direction/order, skipped node or dwell.
- Movement `0xFF`, reset, missing or duplicate `0xCF`, second activation or full-frame write.
- BUSY over 600 ms, transaction over 460 ms or qualification/loop cadence at 481 ms or above. The targeted negative set accepts 480 ms and rejects 481 ms.
- Any complete telemetry line over 192 bytes, unknown or duplicate key, missing required key, malformed record, non-contiguous record or invalid payload/window hash.

Telemetry remains fixed-size and bounded. The parser must retain the existing finalization and trailing-partial rules, and all machine artifacts must remain default-off, production-off and hardware-contact-free. Offline evidence cannot prove optical residue absence or human perception of natural motion.

## Review Boundary

This is an offline-only R11 implementation package. The primary review covers the single-variable/topology change, exact trajectory contract, machine oracle and lifecycle preservation. MACHINE_READY is permitted only with default-off, production-off, hardware_contact=0 and no authorization; ClaimOnly, Execute, flash, popup and hardware contact remain forbidden under this package.
