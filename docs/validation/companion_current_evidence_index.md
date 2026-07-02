# Companion Current Evidence Index

Generated on 2026-07-02 from local scratch worktree
`Companion-Firmware-devboard-oai1`.

## Scope

This file indexes the current local Companion dev-board evidence. It is not a
workflow acceptance record and it does not unblock any human gate by itself.
The active branch is local scratch:

- Branch: `oai1/companion-devboard-continuation-20260702`
- Base: `main` / `origin/main` at `bb889ce`
- Do not push this branch directly. Preserve it as local scratch until the
  product changes are moved through a real workflow step.

## Hardware Readiness

Windows currently sees both the Companion WB55 board and an unrelated ESP32
serial device:

| Resource | Evidence |
|---|---|
| Companion debug/serial | `STMicroelectronics STLink Virtual COM Port (COM13)`, `USB\VID_0483&PID_374B&MI_02\...` |
| Companion board mass-storage/debug | `NOD_WB55RG`, `ST-Link Debug`, `USB\VID_0483&PID_374B\...` |
| Other serial device | `USB serial device (COM3)`, `USB\VID_303A&PID_1001\...` |
| BLE target | local name `companion`, address `00:80:E1:27:B8:EA` |

`aiw refresh-waiting -Json` was left as a dry-run because it reports
`current ESP32 serial/COM device: COM3` even while COM13/ST-Link/NOD_WB55RG is
present. Treat COM13 plus the real BLE PASS artifact below as the Companion
readiness evidence for this scratch run.

## Current Artifacts

| Artifact | Status | Notes |
|---|---:|---|
| `.cache/validation/companion-v1-real-ble-gatt-20260702-104122/companion-ble-real-bench.json` | PASS | Real Bleak scan, service discovery, card write, V1 feature GATT checks, OTA readiness, and existing recording pull. |
| `.cache/validation/companion-operator-chain-20260702-104359/companion-operator-chain-summary.json` | PASS | Uses the 2026-06-30 hardware acceptance PASS summary plus the 2026-07-02 real BLE bench. Final physical confirmation remains `PENDING_HUMAN`. |
| `.cache/validation/companion-physical-signoff-20260702-104103-679/companion-physical-signoff-summary.json` | PENDING_HUMAN | Generated with `-Execute -NoPopup -NoEpaperPanel`; wrote only cache artifacts. `docs/validation/companion_pendant_mvp_go_no_go.md` was not modified. |
| `.cache/validation/companion-operator-chain-20260702-104315/companion-operator-chain-summary.json` | FAIL | Intentional negative check: using the no-popup partial summary as hardware acceptance correctly fails because it is not PASS and has no OTA evidence. |
| `.cache/validation/companion-physical-signoff-20260702-101340-935/companion-physical-signoff-summary.json` | CANCELLED | Earlier interactive signoff was cancelled by the operator. The formal go/no-go Markdown was restored and should not be treated as updated evidence. |

## Real Recording Pull

The current real BLE bench includes a preservation-only recording pull:

- Operation: `recording_pull_existing_no_delete`
- Recording ID: `5`
- Total length: `37760` bytes
- Packet count: `236`
- Host SHA-256 and device final SHA-256:
  `d144c98b320ddd00fe932bbc0afa2b0f6569721048ac9b2b1ae91a2fea05aec0`
- Host CRC32: `0x7517a4c8`
- `no_delete`: `true`

The bench still validates the missing-recording refusal path with recording ID
`6`, then continues through settings, BLE name config, meeting, IMU, speaker,
wake word, diagnostics, delete/privacy refusal, and OTA readiness checks.

## Scratch Stack Path

The current stack should be converted into reviewed workflow work before any
default-branch push. Recommended path:

1. Keep `oai1/companion-devboard-continuation-20260702` local.
2. Create or claim a Companion workflow step for dev-board validation tooling.
3. Cherry-pick only product commits, not checkpoint branches:
   `3005739`, `255fea2`, `18f4d36`, `6edad61`, and the follow-up commit that
   adds this evidence index, no-popup partial behavior, and no-delete pull.
4. Re-run the validation commands from that workflow step and submit through
   `aiw submit`. Do not push the scratch branch.

Remaining non-automated gates:

- No real e-paper panel is installed in this run.
- Inline current measurements were not collected.
- External SPI NOR or pendant PCB timing/power remains a hardware gate.
- Human physical signoff and PCB Go/No-Go remain pending.
