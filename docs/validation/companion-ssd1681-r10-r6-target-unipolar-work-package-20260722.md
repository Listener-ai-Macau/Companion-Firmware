# R10 R6 Target-Unipolar Offline Work Package

Authority: `COMP-REQ-345`. R5 r2 is archived as a machine-valid, owner-FAIL
run: 16 qualification frames, 132 loop records, BUSY maximum 599 ms, one
canonical failure popup, promptless cleanup, exact application restore
`223F6E7A7DB8E5562D0F7C34ED4F023DA7E37F5266505A6C84D5BD6FE304CD7C`, normal
resume and zero retry. The R5 polarity reversal did not change the observed
effect and is not retried.

R6 changes exactly one variable: retain all 16 shared transition frames and
make BW unipolar at offsets 12..15 (`80 80 80 80`) and WB unipolar at offsets
24..27 (`40 40 40 40`). Historical R9 and R5 LUT arrays remain byte-identical.
The fixed corridor, ball/frame/payload hashes, `0x26`/`0x24`/`0xCF`/`0x20`,
BUSY limit, post-sync write, 400..410 ms hold, cleanup, restore and popup
lifecycle are unchanged. Schema v5 reports only the R6 LUT identity; parser
v2-v4 compatibility remains protected.

This package is default-off, production-off and offline-only. It creates no
authorization and makes no hardware contact.
