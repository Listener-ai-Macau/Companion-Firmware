# R10 R3 Stable-Hold Execute Package v2

Status: host-only bind repair completed; this package is sealed for preparation only. No Execute, flash, hardware contact or real popup has occurred.

## Authority and historical boundary

This v2 package is governed by `COMP-REQ-335` and repairs only the R3 MACHINE_READY path binding recorded as the `COMP-REQ-334` successor to the historical `COMP-REQ-333` NO_GO. The old authorization remains untouched and non-reusable:

- old authorization SHA-256: `886E53989D6A2C4504D15DE316C7EBAA29AAA3D945F9B594C9DB249EE4E6FCDA`
- old output root: `C:\Users\Billy\Desktop\Denzic\Companion\Companion-Firmware\.cache\validation\wb55-r10-r3-stable-hold-execute-20260722-r1` (must remain absent)
- new authorization: `C:\Users\Billy\Desktop\Denzic\Companion\Companion-Firmware\.cache\validation\wb55-r10-r3-stable-hold-execute-20260722-r1-authorization-v2.json`
- successor MR: `docs/validation/companion-ssd1681-r10-r3-execute-ready-machine-ready-20260722.json`

The persistent launcher must atomically claim the fresh v2 source before a hardware-capable child, create the consumed receipt, and pass the exact successor MR path and SHA to the runner. The runner must validate the same path and SHA, all candidate/tool hashes and the consumed receipt. `attempt_limit=1`, automatic retry is zero, and promotion is forbidden.

## Bound identities

| Artifact | SHA-256 |
| --- | --- |
| LUT | `9BCBAC1A07ED0A112D26409FBCDB8F5FE27CE07D922C2E18881C10A53229DDCD` |
| ELF | `A08FD3105087879BB325526B0F60E4E4693E7E2AF830575E7704B9794132D354` |
| HEX | `E62DEC303E51F6DA3143D849E50B129BD6F2EC1B32F2CBD6389B7683CA73A9F0` |
| parser | `14DF9BD2B0966F41EDC9807F18D7F4794708A7179ED3759B36A68F0C6F66F563` |
| monitor | `4FE14A93D819B653C0A98BE8611B7F6A8178792FCA5CDDC90E28FAB558595E23` |
| launcher | `D368453930C1258BFBE2B6717F206B30BCAE046DCC5D982141095155197D4462` |
| runner | `417C9C10ACA4C76AC58D2EDD5D02CAD7B99A88EDB721C68AB917DCF991148F9E` |
| supervisor | `F712AD30EE4A52D26EEB8168CBB50F12D52C4AEF7DB3A8B0FF7A37BFF65757F1` |
| successor MACHINE_READY | `0E6516170429112784C188A1C5EAFEC8997EE6D28BE301FCD4C4E00F8EAAFBCF` |
| restore application | `223F6E7A7DB8E5562D0F7C34ED4F023DA7E37F5266505A6C84D5BD6FE304CD7C` |
| protected owner acceptance | `8A3BDF4BD1254B0D0F4DE13A7F293C3D74587C800339ABD4C61FEB0B7737E227` |

## Preserved lifecycle

The future physical path remains promptless dual-plane White preclean, exactly 16 hold-aware qualification frames (`BUSY<=600 ms`, post-sync hold 400..410 ms, `hold_count=1`, exact command/window/count contract), continuous loop, exactly one canonical `aiw operator-prompt` with `通过`/`失败`, stop on verdict or fault, promptless postclean, exact 524288-byte restore/readback, normal resume and process audit. Failures still clean and restore; no start/cleanup/fault popup, retry or production promotion is permitted.

## Exact future command

Record only; do not execute in this host-repair task:

```powershell
pwsh -NoProfile -File tools/start_wb55_ssd1681_phase_parallel_r10_ball.ps1 -Execute -OutRoot "C:\Users\Billy\Desktop\Denzic\Companion\Companion-Firmware\.cache\validation\wb55-r10-r3-stable-hold-execute-20260722-r1" -AuthorizationArtifact "C:\Users\Billy\Desktop\Denzic\Companion\Companion-Firmware\.cache\validation\wb55-r10-r3-stable-hold-execute-20260722-r1-authorization-v2.json"
```

Preparation evidence is `hardware_contact=0`, `write=0`, `popup=0`, `retry=0`; it is not a physical verdict.
