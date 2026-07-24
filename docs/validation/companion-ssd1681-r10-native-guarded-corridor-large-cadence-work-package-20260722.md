# R10 Native Guarded Corridor Large Cadence

This is the offline-only successor authorized by COMP-REQ-357. It addresses the
black line residue reported after COMP-REQ-356 by changing only the write-window
topology: every baseline and movement activation rewrites the fixed corridor
`x bytes 3..11, y 80..103` (216 bytes) from the complete current framebuffer.
The 24x24 centered integer disk remains 448 black pixels at y=80, x=32..64,
with 2px ping-pong and one native OTP Mode2 activation per movement.

Each activation is exactly hardware reset low/high 10/10ms, ready, `0x3C=0x80`,
`0x44/0x45/0x4E/0x4F`, one CPU-held current `0x24`, `0x22=0xFF`, `0x20`, and
BUSY. The candidate has no `0x26`, `0x32`, `0x37`, `C7`, `F7`, custom LUT,
full-frame write, second activation, post-sync, retry, maintenance or
production path. BUSY is gated at 600ms and start-to-start cadence at 550ms.

Qualification is baseline x=32 plus the unchanged 16 movement frames. The
monitor requires two contiguous surviving loop records and at least one real
cadence measurement before the sole canonical Chinese pass/fail window. The
ring is exactly 65536 bytes. The repaired `--loop-log` parser accepts a tail
starting at any positive iteration after complete old lines were evicted, but
requires strict continuity and rejects malformed complete lines, gaps,
duplicates, wrong modulo transitions, wrong corridor/payload, BUSY violations,
wrong schema/prefix, and more than one trailing partial.

Offline evidence proves framebuffer geometry, fixed corridor payloads, command
counts and fail-closed parsing only. It cannot prove optical residue absence.
The physical boundary remains owner observation: the larger ball must remain
complete, refresh faster, keep a clean background, and eliminate black line
residue. This package creates no physical authorization and must not Execute.
