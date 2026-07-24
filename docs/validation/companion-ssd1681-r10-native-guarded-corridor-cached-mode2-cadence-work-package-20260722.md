# R10 Native Guarded Corridor Cached Mode2 Cadence Work Package

Status: registry/work-package preparation only. Authority: COMP-REQ-360. Primary review is required before implementation or build.

## Owner Steering

Exact owner steering:

1. “问题是你这个只能对球做一些东西吗？就是我现在是那个表情要编舞。你现在可以做表情编舞吗？就是如果做好的话。”
2. “**下一档优化**
如果画质仍正确但速度提升不够，再测试官方 Mode 2 的“加载一次、后续只激活”流程，减少每帧温度和 LUT 重载。这个可能提升更多，但必须单独做人眼验收。 这个可以试试”

The ball is only a deterministic lower-driver diagnostic payload. The accepted previous/current framebuffer, guarded dirty-region and re-whitening method may generalize later to eyes, mouth and face choreography. This package does not authorize art, V9, Rig, CRIG, browser or production choreography integration; those remain outside the lower-driver acceptance boundary.

## Reviewed Stepping Stone

The reviewed no-reset candidate is an offline diagnostic stepping stone only, not a physical fact and not physically authorized or flashed:

- MACHINE_READY: `C8943E3A91D48EBA4920DDDB37E11DB0E760B4AEF81F7669F06DDAA99B7ABF21`
- Driver: `7FE69871F51E449FA0991D9F9776F380EAEA94A14988EE828FCE75BAB1E84C2B`
- Header: `928132F5A291A84CAE2F82F03481470CC5CED4C700D9208A766A9EBBE4D01403`
- ELF: `D081495B1544A688FD8D7EA7A0992D856A9A0B11D171A0E658D6360B46A1BB8E`
- HEX: `4E58151BB2E5C4DC3CC7FC1F52D4DD5B8CBF45EE7190303C1498DA7F5C30CFF6`

## Candidate Contract

Candidate identity: `r10_native_guarded_corridor_cached_mode2_cadence`.

The sole low-level variable relative to `r10_native_guarded_corridor_no_reset_cadence` is movement activation control: use official SSD1681 `0x22=0xCF` for an already baseline-loaded Display Mode 2 instead of movement `0x22=0xFF`. No custom LUT or `0x32` is permitted.

### Baseline

At x=32, exactly one source-bound activation performs:

1. Hardware reset low/high for 10/10 ms.
2. Ready wait.
3. Fixed guarded corridor setup: `0x3C=0x80`, `0x44`, `0x45`, `0x4E`, `0x4F`.
4. Complete current corridor bytes through `0x24`.
5. `0x22=0xFF`, `0x20` and BUSY completion.

This baseline loads the temperature-selected built-in OTP Mode 2 state and displays the baseline frame.

### Movement

Each of the 16 qualification frames and every loop movement performs exactly one activation with no hardware reset:

1. One ready-state check.
2. The same fixed guarded corridor setup and complete current `0x24` bytes.
3. Exactly one `0x22=0xCF`.
4. `0x20` and BUSY completion.

Movement telemetry must prove `source_resets=0`, `reset_elapsed_ms=0`, `ready_checks=1`, `source_ff=0`, `source_cf=1`, one activation and zero custom LUT loads.

## Preserved Behavior

- 24x24 centered integer solid disk with exactly 448 black pixels.
- y=80, x=32..64, 2px ping-pong trajectory.
- Full 200x200 previous/current framebuffer diff oracle.
- Fixed corridor x-bytes 3..11, y=80..103, exactly 216 bytes.
- Full current corridor rewrite/re-whitening on every movement.
- One activation per movement and fixed 65536-byte ring.
- BUSY <=600 ms and transaction_elapsed_ms <=455 ms.
- Real start-to-start cadence 1..490 ms; <=470 ms is only a measured improvement target, not an offline or pre-hardware claim.
- Exactly 16 qualification frames, with at least 15 real qualification cadence measurements.
- Popup eligibility requires at least two contiguous loop records and at least one real loop cadence measurement.
- Promptless dual-plane White preclean/postclean, exact restore/readback, normal resume and process audit remain unchanged.

Forbidden movement behavior: `0x22=0xFF`, `0x26`, `0x32`, `0x37`, `C7`, `F7`, custom LUT, voltage/tail changes, full-frame writes, a second activation, post-sync, retry, maintenance and production integration.

## Evidence Contract

The candidate oracle/static/parser must prove the preserved geometry, exact corridor bytes, current payload hashes and one-activation topology. Focused negatives must reject:

- Any movement reset, nonzero `reset_elapsed_ms` or missing ready check.
- Movement `0xFF`, missing or duplicate `0xCF`, custom LUT or changed waveform/tail.
- Changed payload, geometry or fixed corridor window.
- Transaction `456`, BUSY above `600`, cadence `491` or invalid sequence.
- Missing qualification cadence measurements, non-contiguous loops, duplicate records or popup eligibility with fewer than two loop records.

Offline evidence may establish protocol, payload, parser and lifecycle invariants only. It cannot prove physical cadence, residue absence or optical quality. A future physical run must independently satisfy the human boundary: whether the quality floor remains correct while the cached Mode 2 path measurably improves refresh latency.

## Allowed Write Set

After primary review only, implementation may add or modify:

- Candidate-gated header/source and distinct build-selector inputs for `r10_native_guarded_corridor_cached_mode2_cadence`.
- Candidate-specific oracle, static verifier, parser fixtures and only the lifecycle adapters required for the new schema/hash binding.
- Candidate outputs in a distinct build directory and offline validation artifacts.

Reuse proven generic host tools by exact hash under COMP-REQ-358. Do not modify vendor directories, upper-art, V9, Rig, CRIG, browser, production integration or protected owner-acceptance artifacts. Do not create an Execute authorization in this package.

## Required Boundary

1. Primary review approves this exact single variable and write set.
2. Implementation remains default-off, production-off and offline-only.
3. Affected-only oracle/static/parser/isolated-build/CheckOnly gates may run after review; unaffected gates are reused by exact input SHA.
4. The resulting MACHINE_READY must state `hardware_contact=0`, `writes=0`, `popup_count=0`, `retry_count=0`, `execute_authorized=false` and `authorization_created=false`.
5. No ClaimOnly, Execute, flash, hardware contact or popup is permitted before a separate physical authorization.
