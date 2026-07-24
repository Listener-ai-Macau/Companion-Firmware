# SSD1681 R10 R2 Luna Work Package

Date: 2026-07-22

R1 is recorded as `NO_GO_R1_HOST_EVIDENCE_PERSISTENCE` in the runtime
disposition artifact. Its post-run parser recheck is diagnostic evidence only;
it does not reclassify the original monitor gate, create an owner verdict, or
prove visual acceptance.

## Offline-Only Contract

COMP-REQ-327 authorizes only this host repair and a new no-hardware
`MACHINE_READY`. It authorizes no Execute, flash, board contact, popup,
production promotion or owner acceptance. The R10 candidate ELF, HEX, LUT and
driver bytes must remain identical to R1.

`verify_wb55_ssd1681_r10_ball_log.py --log --write` must atomically replace the
requested artifact and print the exact same parsed object. It accepts explicit
`--hardware-contact 0|1`; offline fixtures use `0`, while Execute monitor
qualification and loop artifacts use `1`. The monitor must parse the artifact
back, verify it exists and matches the printed object, and require
`PASS_R10_BALL_LOG`, exactly 16 qualification frames, ring 65536 and
`hardware_contact=1` before writing the qualification signal. The supervisor
requires `1` in Execute and `0` in `SimulateQualifiedPrompt`.

The parser tool SHA is bound in the R2 MACHINE_READY artifact, launcher
expected hashes, consumed-receipt schema, runner locked hashes and lifecycle
fixtures. The old R1 authorization is not reused and no R2 authorization is
created here.

## Offline Commands

Focused parser check:

```powershell
python tools/verify_wb55_ssd1681_r10_ball_log.py
```

R2 MACHINE_READY generation, intentionally not an Execute command:

```powershell
python tools/verify_wb55_ssd1681_r10_ball_machine_ready.py --write
```

The resulting MACHINE_READY must be generated twice and byte-identical. Any
future physical command requires a new root authorization bound to the new
MACHINE_READY and parser SHA; this package creates none.
