# R10 Native Guarded Corridor No-Reset Cadence Work Package

Status: offline implementation proposal only. Authority: COMP-REQ-359.

## Protected Floor

The source physical run is:

- Root: .cache/validation/wb55-r10-native-guarded-corridor-large-cadence-execute-20260722-r1
- Final status: PASS_MACHINE_R10_NATIVE_GUARDED_CORRIDOR_LARGE_CADENCE_OBSERVATION_RESTORED_OWNER_PASSED
- Canonical selection: 通过
- Exact operator note: 嗯，这版很完美。就是你看能不能加快一下移动速度？这一把我感觉非常完美。\r\n
- Note SHA-256: C67DE3ADA1799DF58516CBF66FBBA7A87EC8879C346A1300264C70175E7565B8
- Operator review SHA-256: 4B055585A87C759B1F995B7589EED91E6CA687439C2D0B783868447A1BC925B6
- Operator result SHA-256: 92984A4BFE65EBA39AE42027DE398DED4E2EABF2CAE220F620EE84FBD179E681
- Stage SHA-256: 3ACCE6970BD9B3E11B2618A690C3E0683C415393C6AB6CE0D8E7824165E9B9C5
- Qualification: 16 frames
- Loop records: 160
- BUSY maximum: 447 ms
- Transaction maximum: 471 ms
- Maximum measured start delta: 503 ms
- Ring peak: 59855 of 65536 bytes
- Retry count: 0
- Postclean, exact 524288-byte restore/readback, normal resume and process audit: PASS
- Restore SHA-256: 223F6E7A7DB8E5562D0F7C34ED4F023DA7E37F5266505A6C84D5BD6FE304CD7C

This r1 is the protected visual-quality floor. It uses official built-in SSD1681 OTP Mode 2, a fixed guarded corridor at x bytes 3..11 and y 80..103, complete current-corridor rewrite/re-whitening, and a complete 24x24 solid disk with 448 black pixels at y=80, x=32..64 and 2px steps. The floor is complete, uncropped, fast enough for the accepted visual result, clean in the background and free of the previously observed black-line residue. The Goal remains active only for owner-requested latency optimization.

The durable owner steering is:

“我看这次是视觉效果是对的，那就做更加快的移动就好了。然后更加，呃，更加低延迟的刷新然后你看还能不能再优化一下体验，就反正我这边视觉效果是对的。”

“行，那就先这样子吧。那你那个波形是用自定波形，还是厂官方的波形？然后你继续在这一套正确基础上做优化。”

## Sole Variable

Candidate identity: r10_native_guarded_corridor_no_reset_cadence.

The baseline x=32 activation remains exactly one source-bound hardware reset low/high 10/10 ms, ready, 0x3C=0x80, exact fixed guarded corridor window 0x44/0x45/0x4E/0x4F, current 0x24 corridor bytes, 0x22=0xFF, 0x20 and BUSY. This baseline loads the official temperature-selected OTP Mode 2 state.

Every qualification and loop movement activation omits only the hardware reset. It must first perform a ready-state check, then send exactly 0x3C=0x80, the same fixed guarded corridor window, complete current 0x24 corridor bytes, 0x22=0xFF, 0x20 and BUSY. Movement source_resets is exactly 0 and reset_elapsed_ms is exactly 0. No other low-level variable is selected.

Forbidden: custom LUT, 0x32, 0x26, 0x37, C7, CF, F7, full-frame writes, second activation, post-sync, retry, maintenance, production integration or geometry/payload/window/waveform changes.

## Machine Contract

- Default-off, production-off and offline MACHINE_READY only.
- Baseline source_resets=1; every movement source_resets=0 and reset_elapsed_ms=0.
- Exactly one activation, one 0x24 write, one 0x22=0xFF, one 0x20 and one BUSY per movement.
- BUSY is at most 600 ms.
- movement transaction_elapsed_ms is at most 455 ms.
- Real movement start-to-start cadence is 1..490 ms.
- Qualification includes at least one real cadence measurement.
- Popup eligibility additionally requires at least two contiguous loop records and at least one real loop cadence measurement.
- Qualification keeps the existing exact 16-frame sequence.
- The unbounded loop keeps the existing 32-transition path.
- Telemetry ring is fixed at exactly 65536 bytes.
- The one canonical Chinese pass/fail popup remains concurrent with the continuous loop; start, cleanup and fault paths remain popup-free.
- Any fault stops, cleans both planes, restores and audits process state; no automatic retry.

## Evidence Gates

The candidate-specific oracle must prove every complete landing and exact fixed-corridor bytes. Static and parser negatives must reject:

- Any reset or nonzero reset elapsed time in a movement activation.
- A missing or invalid ready-state check.
- Changed geometry, payload, corridor window, waveform or command sequence.
- BUSY above 600 ms, transaction above 455 ms or start-to-start cadence outside 1..490 ms.
- Missing or duplicate control commands, forbidden commands, full-frame writes, a second activation or retry.
- Qualification or loop records without the required exact sequence, contiguous records or real cadence measurement.

Offline evidence must not claim optical behavior beyond the protected r1 observation. No physical authorization is created by this package.

## Allowed Write Set

Only after primary review accepts this work package, implementation may add or modify:

- Candidate-gated native header/source files for r10_native_guarded_corridor_no_reset_cadence.
- Candidate-specific oracle, static verifier, parser fixtures and candidate-specific lifecycle adapters required by the schema.
- Candidate build outputs in a distinct candidate build directory.
- Candidate validation artifacts, this work package and the minimal current-goal audit entry needed to bind the offline MACHINE_READY.

Existing generic host tools are reused by exact hash under COMP-REQ-358. They may be copied to candidate-specific names only when schema adaptation is necessary; generic launcher, runner, monitor and supervisor edits are out of scope unless primary review explicitly expands the package. Vendor directories, protected acceptance files, upper-art/V9/Rig/CRIG/browser/product integration and historical artifacts are protected.

## Required Order And Boundary

1. Primary review must approve this package and its single variable.
2. Implement default-off and production-off candidate files only.
3. Run affected-only oracle/static/parser/isolated-build/CheckOnly gates, reusing unaffected gates by exact input SHA.
4. Produce one distinct offline MACHINE_READY with hardware_contact=0, writes=0, popup_count=0, retry_count=0 and execute_authorized=false.
5. No physical authorization, ClaimOnly, Execute, flash, hardware contact or popup is permitted in this package.
