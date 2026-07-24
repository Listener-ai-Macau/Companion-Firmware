# R10 R4 Corridor Execute Package R1

This package is sealed by `COMP-REQ-338` for exactly one physical R4 Execute.
It is bound to the exact MACHINE_READY manifest and output root below. The
authorization is one-shot, `attempt_limit=1`, `automatic_retries=0`, and
production promotion is forbidden. R1/R2/R3 roots and authorizations are not
reused.

## Bound paths

- Output root: `C:\Users\Billy\Desktop\Denzic\Companion\Companion-Firmware\.cache\validation\wb55-r10-r4-corridor-execute-20260722-r1`
- Authorization: `C:\Users\Billy\Desktop\Denzic\Companion\Companion-Firmware\.cache\validation\wb55-r10-r4-corridor-execute-20260722-r1-authorization.json`
- MACHINE_READY: `C:\Users\Billy\Desktop\Denzic\Companion\Companion-Firmware\docs\validation\companion-ssd1681-r10-r4-corridor-machine-ready-20260722.json`

## Runtime contract

The persistent launcher atomically consumes the fresh authorization before any
hardware-capable child starts. It performs promptless dual-plane White
preclean, exactly 16 machine-gated R4 corridor frames, then the continuous
loop with one canonical Chinese `通过`/`失败` popup. A verdict or fault stops
the loop. It performs promptless dual-plane White postclean, exact 524288-byte
application restore/readback, normal resume, and final process audit. Any
failure still cleans and restores. There is no retry, second popup, promotion,
or automatic maintenance refresh.

The only physical acceptance boundary is the owner's observation through that
single canonical popup. This document records preparation only; the command
below must not be run as part of sealing.

## Exact future command

```powershell
pwsh -NoProfile -File C:\Users\Billy\Desktop\Denzic\Companion\Companion-Firmware\tools\start_wb55_ssd1681_phase_parallel_r10_ball.ps1 -Execute -OutRoot C:\Users\Billy\Desktop\Denzic\Companion\Companion-Firmware\.cache\validation\wb55-r10-r4-corridor-execute-20260722-r1 -AuthorizationArtifact C:\Users\Billy\Desktop\Denzic\Companion\Companion-Firmware\.cache\validation\wb55-r10-r4-corridor-execute-20260722-r1-authorization.json
```
