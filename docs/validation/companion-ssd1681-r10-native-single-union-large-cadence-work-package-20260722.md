# R10 Native Single-Union Large Cadence

This is the offline-only COMP-REQ-353 candidate. It is default-off and
production-off; this package creates no physical authorization and performs no
Execute, flash, hardware contact, or popup.

The candidate is a centered integer 24x24 solid disk with exactly 448 black
pixels at `y=80`, moving between `x=32..64` in 2px ping-pong steps. Baseline
`x=32` uses one source-bound native OTP Mode2 activation. Each logical movement
uses exactly one activation over the exact previous/current framebuffer union,
writing CPU-held current bytes with `0x24`, source `0xFF`, `0x20`, and BUSY.
Every activation performs reset low/high 10/10ms, ready, `0x3C=0x80`,
`0x44/0x45/0x4E/0x4F`, then the current plane. BUSY is at most 600ms and the
best-effort frame cadence target is 550ms; physical start-to-start cadence remains
unproven until a future Execute and owner observation.

Qualification is exactly 16 logical frames and 16 activations after baseline:
`32->34->36->38->40->42->44->46->48->46->44->42->40->38->36->34->32`.
The unbounded loop uses the same 32 transitions across `32..64` and back.
The fixed 65536-byte ring and parser validate exact positions, full-frame
hashes, union windows, current payload hashes, one-activation counts, and zero
omitted columns. Offline evidence does not claim that a physical panel has no
residue; that remains the owner’s final visual boundary, with any residue,
dirty-white flash, or missing edge a NO_GO while the r2 quality floor remains
protected.

The exact future lifecycle command, only after a separately registry-authorized
fresh one-shot physical authorization, is:

```powershell
pwsh -NoProfile -File tools/start_wb55_ssd1681_r10_native_single_union_large_cadence.ps1 -Execute -AuthorizationArtifact <fresh-unconsumed-source-authorization.json> -OutRoot <fresh-output-root>
```

`-AuthorizationArtifact` is the fresh, unconsumed, hash-bound source
authorization JSON. The persistent launcher atomically claims it and passes the
consumed receipt to the runner before any hardware-capable child starts.
