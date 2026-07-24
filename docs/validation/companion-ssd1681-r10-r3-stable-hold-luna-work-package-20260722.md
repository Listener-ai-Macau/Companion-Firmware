# R10 R3 Stable-Hold Luna Work Package

This package implements only COMP-REQ-332 in `Companion-Firmware/main`.

## Chosen Variable

R3 changes exactly one low-level behavior: after a successful frame's post-sync
`0x24` write completes, the driver performs one explicit stable hold. The hold
is before the next frame's window setup or `0x26` write, applies identically to
all 16 qualification frames and the unbounded loop, and records
`hold_elapsed_ms` plus `hold_count=1`.

The target is 400 ms. Machine evidence accepts only `400 <= hold_elapsed_ms <=
410`. The hold is not placed before activation, during BUSY, on an error path,
as a countdown, or at a second dwell location.

## Protected R2 Contract

The 12x12 solid 112-pixel disk, positions `32,40,48,56,64`, 8 px step,
32 px travel, full previous/current framebuffer diff, exact union window,
`0x26`/staged `0x24`/`0xCF`/`0x20`/BUSY/post-sync `0x24` counts, R9 LUT SHA,
tail, mapping, BUSY <=600 ms, forbidden-command counters, cleanup, restore,
normal resume, popup lifecycle and finalization rule remain unchanged.

The pixel and payload hashes must equal R2 exactly. R3 is a cadence
discriminator only; it is not a final visual repair claim.

## Offline Gates

The package must pass the hold-aware oracle, parser, static and negative
fixtures, isolated R10 build, persistent CheckOnly, registry verifier and
canonical `python tools/verify_companion_current_goal_audit.py`. The R3
MACHINE_READY generator must invoke that canonical audit directly and may also
invoke the R10 successor audit. The final artifact is distinct and byte-stable
across two generations, with CheckOnly `hardware_contact=0`, writes `0`, popup
`0` and retries `0`.

No Execute authorization is created. No board, serial port, popup or production
integration is used by this package.
