# Companion Dev-Board Physical Checklist

This checklist is for the current NUCLEO-WB55RG development-board phase. It is
not a pendant-PCB release checklist.

## Before The Run

- Use the clean canonical checkout only for normal workflow commands.
- Keep the current product stack in the scratch worktree:
  `C:\Users\Billy\Desktop\Denzic\Companion\Companion-Firmware-devboard-oai1`.
- If collecting physical evidence, hold the workflow hardware lock for the
  short flash, serial, BLE, or operator-prompt window only.
- The development-board record button is the NUCLEO-WB55RG `SW3/B3` user
  button on `PD1`. Do not use RESET, ST-LINK reset, BOOT0, or a host keyboard.
- If no real e-paper panel is connected, record `N/A`. PBM fallback renders are
  automated display-contract evidence, not real panel evidence.

## Operator Chain

Run the automated chain first. It should remain `PASS` while reporting final
physical confirmation as `PENDING_HUMAN`.

```powershell
python .\tools\verify_companion_operator_chain.py --hardware-acceptance-summary C:\Users\Billy\Desktop\Denzic\Companion\Companion-Firmware\.cache\validation\companion-hardware-acceptance-20260630-112402\companion-hardware-acceptance-summary.json --real-ble-bench C:\Users\Billy\Desktop\Denzic\Companion\Companion-Firmware\.cache\validation\companion-v1-real-ble-gatt-20260630-114513\companion-ble-real-bench.json --json
```

## Physical Signoff Prompt

Dry-run the prompt without touching hardware:

```powershell
pwsh -NoProfile -File .\tools\verify_companion_physical_signoff.ps1 -NoEpaperPanel
```

Execute it only under the workflow hardware lock:

```powershell
pwsh -NoProfile -File C:\Users\Billy\Desktop\Denzic\ai-collaboration-workflow\scripts\aiw.ps1 with-lock -Resource Companion-WB55 -Purpose "Companion final physical signoff" -Run pwsh -NoProfile -File .\tools\verify_companion_physical_signoff.ps1 -Execute -WorkflowLockHeld -NoEpaperPanel
```

`-NoEpaperPanel` records all e-paper observation checks and the e-paper refresh
current row as `N/A` with the note `no e-paper panel installed`. Remove the flag
only after a real panel is connected.

## Human Observations To Record

- Real e-paper default card, recording card, sync-complete card, and BLE-written
  short card, or explicit `N/A` if no panel is installed. Use
  `-NoEpaperPanel` for the current no-panel bench.
- Real `SW3/B3` button press causes a capture or recording affordance.
- Real microphone/storage chain can capture, pull a non-empty recording, verify
  length plus SHA-256, and delete only after host verification.
- Current measurements for boot/idle, BLE advertising, connected idle,
  recording, e-paper refresh, BLE chunk transfer, and charge or external power.
- PCB decision remains `continue_dev_board_iteration_before_first_pendant_pcb`
  unless a human explicitly overrides it with evidence.

## Current Default Decision

The current default is to continue development-board iteration before a first
pendant PCB. PCB go still needs real display timing/refresh observation, real
external SPI NOR timing and power, and measured battery/charger/fuel-gauge or
external-power behavior.
