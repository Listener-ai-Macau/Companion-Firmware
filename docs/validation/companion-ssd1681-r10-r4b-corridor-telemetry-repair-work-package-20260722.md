# R10 R4b Corridor Telemetry Repair

This is the offline-only successor required by `COMP-REQ-339`. R4 reached all
16 qualification frames with BUSY 597..599 ms and wrote the fixed corridor for
all three plane writes, but the monitor rejected loop iteration 1 because the
firmware reported obsolete direction-only payload hashes. The popup was never
invoked, so R4 has no visual verdict. White pre/post-clean, exact restore
`223F6E7A7DB8E5562D0F7C34ED4F023DA7E37F5266505A6C84D5BD6FE304CD7C`, normal
resume and retry=0 passed.

R4b changes only the R10 telemetry reporter. A single position-keyed lookup
reports the fixed-corridor payload hash for both `previous_x` and `current_x`:
white, 32, 40, 48, 56 and 64 use the six hashes recorded in the R4 oracle.
Unknown positions return `NULL`. Frame writes, corridor geometry, LUT/tail,
mapping, `0xCF`/`0x20`/BUSY, hold timing, lifecycle, cleanup, restore and popup
policy are unchanged.

Focused evidence rejects a mutated loop-iteration-1 payload hash and proves the
captured shape `previous_x=40`, `current_x=32`, `previous_payload_sha256=B96D...`,
`current_payload_sha256=51EC...`, `busy_elapsed_ms=599`. The fresh MACHINE_READY
is default-off, production-off, `hardware_contact=0` and
`execute_authorized=false`; it reuses unchanged host gates by their exact SHA.
No authorization is prepared and no Execute is permitted by this package.
