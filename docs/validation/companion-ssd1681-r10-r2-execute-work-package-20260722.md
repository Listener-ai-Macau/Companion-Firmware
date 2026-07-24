# SSD1681 R10 R2 Execute Work Package

Date: 2026-07-22

This is the exact one-shot physical package authorized by `COMP-REQ-328` after
the R2 offline review PASS. Only the host persistence and hash-binding repair
changed from consumed R1. This package is preparation only: it does not
Execute, flash, contact hardware or open a popup.

Current audit state: `AUTHORIZED_R10_R2_ONCE_PENDING_EXECUTE`.

The persistent launcher must atomically consume the fresh authorization before
starting any hardware-capable child. It must bind the exact R2 parser,
launcher, runner, monitor, supervisor, MACHINE_READY, HEX, ELF, LUT, restore
hashes and this exact fresh output root. The consumed R1 source, receipt and
output root are not reusable.

Required lifecycle: promptless dual-plane White pre-clean; exact 16-frame
qualification gate; the sole canonical Chinese `通过`/`失败` popup concurrent
with the continuous loop; stop on owner verdict, monitor failure or emergency;
promptless dual-plane post-clean; exact 524288-byte restore/readback; normal
resume; process-exit proof; zero retry and no production promotion.

Authorization JSON:

`C:\Users\Billy\Desktop\Denzic\Companion\Companion-Firmware\.cache\validation\wb55-r10-ball-r2-authorization.json`

Fresh output root:

`C:\Users\Billy\Desktop\Denzic\Companion\Companion-Firmware\.cache\validation\wb55-r10-ball-execute-20260722-r2`

Exact command, recorded but intentionally not run:

```powershell
pwsh -NoProfile -File tools/start_wb55_ssd1681_phase_parallel_r10_ball.ps1 -Execute -OutRoot "C:\Users\Billy\Desktop\Denzic\Companion\Companion-Firmware\.cache\validation\wb55-r10-ball-execute-20260722-r2" -AuthorizationArtifact "C:\Users\Billy\Desktop\Denzic\Companion\Companion-Firmware\.cache\validation\wb55-r10-ball-r2-authorization.json"
```
