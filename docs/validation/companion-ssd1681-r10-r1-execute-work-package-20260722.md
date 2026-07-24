# SSD1681 R10 R1 Execute Work Package

Date: 2026-07-22

This package is the mechanical one-shot physical authorization prepared under
`COMP-REQ-325`, based on the owner's 2026-07-22 start/reflash steering in
`COMP-REQ-322` and the primary-agent implementation boundary in
`COMP-REQ-323`. Preparation does not Execute, flash, contact hardware, or open
a popup.

## Sealed Scope

The exact fresh output root is:

`C:\Users\Billy\Desktop\Denzic\Companion\Companion-Firmware\.cache\validation\wb55-r10-ball-execute-20260722-r1`

The exact authorization source is:

`C:\Users\Billy\Desktop\Denzic\Companion\Companion-Firmware\.cache\validation\wb55-r10-ball-r1-authorization.json`

The source is `AUTHORIZED_R10_BALL_ONCE`, remains `consumed=false` until the
persistent launcher atomically claims it, and carries the audit state
`AUTHORIZED_R10_R1_ONCE_PENDING_EXECUTE`. The authorization binds the exact
LUT, ELF, HEX, runner, monitor, supervisor, launcher, MACHINE_READY and
restored-application SHA-256 identities listed in the JSON, plus the exact
fresh output root. It permits `attempt_limit=1`, `automatic_retries=0`, and no
production promotion.

The persistent launcher must atomically spend the source before starting any
hardware-capable child and pass the consumed receipt to the runner. The runner
must validate the receipt, spent source, claim marker, claim id, exact output
root and all bound hashes. A crash after the claim remains safely consumed.

## Required Lifecycle

1. Promptless dual-plane White pre-clean.
2. Candidate flash and the exact 16-frame machine qualification gate.
3. After qualification PASS only, one canonical Chinese `通过`/`失败` popup
   runs concurrently with the continuous ball loop.
4. Stop on the owner verdict, monitor failure, emergency fault or abnormal
   child exit. Persist selected result, verbatim note and note SHA-256.
5. Promptless dual-plane White post-clean on every completion and failure path.
6. Restore and read back exactly 524288 application bytes, then prove normal
   application resume and process exit.

There is no retry, second activation, promotion, or alternate popup. The
qualification and loop retain the admitted R9 LUT, tail, mapping, refresh
control, cleanup, restore and popup boundaries; R10 changes only the payload
topology to the complete moving 12x12 solid ball already proven by MACHINE_READY.

## Exact Command

This command is recorded for the owner and is intentionally **not executed**
in this preparation task:

```powershell
pwsh -NoProfile -File tools/start_wb55_ssd1681_phase_parallel_r10_ball.ps1 -Execute -OutRoot "C:\Users\Billy\Desktop\Denzic\Companion\Companion-Firmware\.cache\validation\wb55-r10-ball-execute-20260722-r1" -AuthorizationArtifact "C:\Users\Billy\Desktop\Denzic\Companion\Companion-Firmware\.cache\validation\wb55-r10-ball-r1-authorization.json"
```

The command is the only permitted future physical entry point. No direct
runner, monitor, supervisor or programmer command is authorized.
