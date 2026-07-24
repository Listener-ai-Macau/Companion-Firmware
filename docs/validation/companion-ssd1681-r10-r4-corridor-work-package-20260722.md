# SSD1681 R10 R4 Corridor Work Package

Status: offline MACHINE_READY only. This package implements the single R4 variable selected by the primary agent under `COMP-REQ-336`; it creates no authorization, does not Execute, and does not contact hardware.

## R3 disposition

R3 is archived in `docs/validation/companion-ssd1681-r10-r3-runtime-disposition-20260722.json`. Its physical result is a visual FAIL after 16 qualification PASS frames (`busy_max_ms=599`, hold 400..410 ms), 31 live loop records and one canonical popup. The owner note and subsequent verbatim correction are retained there. Postclean, exact restore `223F6E7A7DB8E5562D0F7C34ED4F023DA7E37F5266505A6C84D5BD6FE304CD7C`, normal resume and zero retry passed. `NO_GO_FINALIZATION` is classified as a short-ring complete qualification-preamble finalization issue, not a qualification or screen failure.

## Sole R4 visual variable

R4 changes only the three per-frame RAM windows. After rendering the full previous/current 200x200 framebuffers, old `0x26`, staged current `0x24` and post-sync `0x24` each use the fixed byte-aligned motion corridor `x bytes 4..9` (`pixels 32..79`), `y 80..91`, exactly 72 bytes. The R3 400..410 ms post-sync hold remains exactly once after the post-sync write and before the next frame.

The 12x12/112-pixel solid ball, positions 32/40/48/56/64, 8 px step, 32 px travel, full-frame diff source, R9 LUT/tail/mapping, `0xCF/0x20/BUSY`, command counts, no second activation, no full-frame write, no F7/C7/FF/37, no retry and cleanup/restore/popup policy remain unchanged. Expected transition classes are `ww=376`, `wb=88`, `bw=88`, `bb=24`; the first frame is `ww=464`, `wb=112`, `bw=0`, `bb=0`.

## Host-only repairs

The final loop parser may ignore only a strict, format-valid complete R10 qualification/start/observation preamble before loop records and records its ignored count. Unknown, fault, no-go, malformed or incomplete loop content still fails closed. Ring eviction is line-boundary based and preserves at most one non-newline trailing partial fragment.

Launcher and runner use an authorization-bound generic `machine_ready_path`, restricted to a repository `docs/validation` leaf JSON with the required schema/status/artifact hashes. The same exact path and hash travel from source authorization through atomic claim, consumed receipt and runner validation. Future candidates therefore change only their MR/auth artifacts.

## Incremental validation

Only affected R4 oracle, static, parser, targeted host fixtures and one isolated build are required. Unchanged gates are reused by their recorded input SHA. A single final closure will be generated after those targeted gates, including one final CheckOnly; no authorization is created and no physical command is run.
