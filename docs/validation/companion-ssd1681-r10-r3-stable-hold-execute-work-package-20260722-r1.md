# Companion SSD1681 R10 R3 Stable-Hold Execute Package

Status: sealed one-shot authorization preparation only. This package is not an Execute instruction for the current agent: no command below has been run, no board has been contacted, and no popup has been opened.

## Authority and root

This package is authorized by `COMP-REQ-333`, which cites the owner's accepted slow single-variable method in `COMP-REQ-329`, the physical iteration authority in `COMP-REQ-322`, and the primary R3 review PASS. It authorizes exactly one R3 stable-hold physical attempt. R1 and R2 consumed authorizations and output roots are historical and must not be reused.

- Output root: `C:\Users\Billy\Desktop\Denzic\Companion\Companion-Firmware\.cache\validation\wb55-r10-r3-stable-hold-execute-20260722-r1`
- Fresh authorization source: `C:\Users\Billy\Desktop\Denzic\Companion\Companion-Firmware\.cache\validation\wb55-r10-r3-stable-hold-execute-20260722-r1-authorization.json`
- Authorization state at sealing: `AUTHORIZED_R10_BALL_ONCE`, `consumed=false`
- `requirement_id=COMP-REQ-323`; `authorization_requirement_id=COMP-REQ-333`
- `attempt_limit=1`; `automatic_retries=0`; no production promotion
- The persistent launcher must atomically claim/spend the fresh source before starting any hardware-capable child. Any crash after claim spends the attempt safely.

## Sealed identities

| Artifact | SHA-256 |
| --- | --- |
| LUT | `9BCBAC1A07ED0A112D26409FBCDB8F5FE27CE07D922C2E18881C10A53229DDCD` |
| ELF | `A08FD3105087879BB325526B0F60E4E4693E7E2AF830575E7704B9794132D354` |
| HEX | `E62DEC303E51F6DA3143D849E50B129BD6F2EC1B32F2CBD6389B7683CA73A9F0` |
| parser | `14DF9BD2B0966F41EDC9807F18D7F4794708A7179ED3759B36A68F0C6F66F563` |
| monitor | `4FE14A93D819B653C0A98BE8611B7F6A8178792FCA5CDDC90E28FAB558595E23` |
| launcher | `7239FB33F0BC35887CD46CF85B8B0BBA1788987F73D0A239C20DDBCD14350659` |
| runner | `3E7A1316CC2101EF8F35420C6166728FA785E2FCC2CC472ADC7B503B383FDAAE` |
| supervisor | `F712AD30EE4A52D26EEB8168CBB50F12D52C4AEF7DB3A8B0FF7A37BFF65757F1` |
| MACHINE_READY | `C41948595CE27041349949A80E5777CB381ABB416FACB8F08274701503911B23` |
| restore application | `223F6E7A7DB8E5562D0F7C34ED4F023DA7E37F5266505A6C84D5BD6FE304CD7C` |
| protected owner acceptance | `8A3BDF4BD1254B0D0F4DE13A7F293C3D74587C800339ABD4C61FEB0B7737E227` |

## Required physical lifecycle

The persistent launcher runs the R3 `PhaseParallelR10Ball` path only. It must perform promptless dual-plane White preclean, then exactly 16 qualification frames. Each frame must satisfy `BUSY<=600 ms`, one 400..410 ms post-sync stable hold after `0x24` and before the next frame, `hold_count=1`, and the existing exact R10 command, window, payload, cleanup and R9 LUT/tail/mapping contract. The same hold-aware frame contract applies to the continuous loop.

Only after qualification PASS may the runner start the continuous loop and the supervisor open exactly one canonical `aiw operator-prompt` with choices `通过` and `失败`. The supervisor stops on the owner verdict or any fault. Start, cleanup and fault paths remain popup-free. Every verdict or failure performs promptless dual-plane White postclean, exact 524288-byte application restore with readback, normal resume verification and process audit. Retry is never automatic and production promotion is forbidden.

## Exact future command

This is recorded for the authorized operator and is intentionally not executed here:

```powershell
pwsh -NoProfile -File tools/start_wb55_ssd1681_phase_parallel_r10_ball.ps1 -Execute -OutRoot "C:\Users\Billy\Desktop\Denzic\Companion\Companion-Firmware\.cache\validation\wb55-r10-r3-stable-hold-execute-20260722-r1" -AuthorizationArtifact "C:\Users\Billy\Desktop\Denzic\Companion\Companion-Firmware\.cache\validation\wb55-r10-r3-stable-hold-execute-20260722-r1-authorization.json"
```

The command deliberately uses the persistent launcher and the sealed authorization. Preparation evidence must remain `hardware_contact=0`, `write=0`, `popup=0`; those values describe this offline preparation and are not a physical verdict.
