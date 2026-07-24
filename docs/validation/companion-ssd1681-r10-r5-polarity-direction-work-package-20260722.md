# R10 R5 Polarity-Direction Offline Work Package

Authority: `COMP-REQ-341`. This package is offline-only and ends at
`MACHINE_READY`; it creates no authorization and makes no hardware contact.

R4b is archived as a machine-valid but visually rejected fixed-corridor run:
16 qualification frames, 68 loop records, BUSY maximum 597 ms, one canonical
Chinese failure popup, promptless post-clean, exact application restore
`223F6E7A7DB8E5562D0F7C34ED4F023DA7E37F5266505A6C84D5BD6FE304CD7C`, normal
resume, and zero retry. The R5 discriminator changes only the dedicated 159
byte LUT: the 4 bytes at offsets 12..15 and the 4 bytes at offsets 24..27 are
swapped between the two polarity directions. The historical R9 LUT remains
byte-identical and is never used by R10 R5.

The R10 ball, fixed corridor (`x4..9`, `y80..91`, 72 bytes), full-frame diff,
`0x26` old plane, `0x24` current plane, one `0xCF`/`0x20` activation, post-sync
`0x24`, 400..410 ms hold, BUSY limit, cleanup/restore/popup lifecycle, and
production-off boundary remain unchanged. Schema v4 reports the R5 LUT hash;
v2/v3 remain accepted unchanged. Focused evidence must reject an old LUT hash,
wrong payload hash, and reversed direction. Build and registry/current-goal
checks are targeted only; cached unchanged host gates are reused by exact SHA.

No Execute command is authorized by this document.
