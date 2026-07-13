# Companion Firmware Codex Workflow

This repo uses a two-track STM32 workflow so Codex can keep making verifiable
progress without depending on CubeIDE GUI state for every edit.

## Recommended Shape

1. Keep `cubeide/Companion_Nucleo_WB55RG_Bringup` as the hardware bring-up
   project for the current NUCLEO-WB55RG bench board.
   - Codex can build it with `tools/build_nucleo_bringup.ps1`.
   - The repo-owned development-board IOC is
     `cubeide/Companion_Nucleo_WB55RG/Companion_Nucleo_WB55RG.ioc`; it tracks
     the user-provided `C:\Users\Billy\Desktop\STM32.ioc` hardware settings
     while keeping CubeIDE project metadata local. Validate that import with
     `python .\tools\verify_devboard_ioc_import.py`.
   - It owns temporary board-button input: SW1 starts/stops recording, SW2
     cancels and recovers to idle, SW3 runs flash/OTA/diag probes.
   - Use this project for microphone, external flash, serial logs, and quick
     pressure tests before the pendant PCB exists.

2. Treat `Companion_Pendant.ioc` as the product CubeMX source of truth.
   - Do not create a separate ad-hoc CubeIDE project from scratch.
   - Open the existing `.ioc` in STM32CubeIDE and generate the product project
     from that file.
   - Generated `Core/`, `.project`, and `.cproject` are product-project output;
   application logic should stay in repo-owned modules such as
   `app/companion_pendant/` whenever possible.

3. Keep WBA migration rules active during WB55 work.
   - Follow [stm32wba_migration_rules.md](stm32wba_migration_rules.md) for
     every BLE, audio, flash, OTA, low-power, security, or board-layer change.
   - Assume WB55 validation comes first, then a platform port to WBA55 or
     WBA65. New code must keep portable Companion logic separate from WB55
     CPU2/FUS/IPCC/HSEM/STM32_WPAN mechanics.

4. Keep generated code and handwritten product code separated.
   - CubeMX owns peripheral init and files it generates.
   - Codex owns portable modules, validation scripts, build/flash/capture
     wrappers, and code inside explicit USER CODE regions when generated files
     must be extended.
   - Do not edit `third_party/STM32CubeWB/**`; it remains an official reference.
   - VS Code uses `.vscode/settings.json` with `git.detectSubmodulesLimit`
     above the 13 nested STM32CubeWB submodules, so the Git extension does not
     show the default "will not be opened automatically" warning. This is a
     workspace convenience only; nested ST submodules still stay read-only.
   - Validate this workspace policy with
     `python .\tools\verify_workspace_submodule_policy.py`.

## Day-to-Day Loop

For NUCLEO bring-up:

```powershell
pwsh -NoProfile -File .\tools\build_nucleo_bringup.ps1
pwsh -NoProfile -File .\tools\flash_nucleo_bringup.ps1
pwsh -NoProfile -File .\tools\capture_nucleo_serial.ps1 -CheckOnly
pwsh -NoProfile -File C:\Users\Billy\Desktop\Denzic\ai-collaboration-workflow\scripts\aiw.ps1 with-lock -Resource Companion-WB55 -Purpose "Companion NUCLEO serial capture" -Run pwsh -NoProfile -File .\tools\capture_nucleo_serial.ps1 -Execute -WorkflowLockHeld -Seconds 30 -ResetAfterOpen
```

For product CubeIDE work:

1. Open `Companion_Pendant.ioc` in STM32CubeIDE.
2. Make pin/peripheral changes in CubeMX.
3. Generate code.
4. Build in CubeIDE until the generated product project has 0 errors.
5. Add or update a scriptable build wrapper once the generated project path is
   stable, so Codex can verify future non-GUI changes.

## Division Of Labor

Use CubeIDE/CubeMX for:

- Pinout and alternate-function choices.
- Peripheral mode changes.
- DMA/NVIC generator output.
- Initial STM32_WPAN project skeleton generation.

Use Codex for:

- Recording FSM, diagnostic log, cache model, e-paper renderer, and BLE contract
  code under `app/companion_pendant/`.
- Build/flash/log scripts under `tools/`.
- Static verification and validation evidence under `docs/validation/`.
- Focused generated-code fixes after CubeMX output is reviewed.

This keeps CubeIDE as the hardware configuration tool and Codex as the repeatable
engineering loop.

## Operator Prompt Discipline

Do not use blocking desktop prompts for AI-only work such as flashing, resetting,
BLE scans, log capture, static checks, package creation, or cleanup. Use command
output and validation artifacts for those actions.

Use a blocking visible prompt only when progress is waiting on a real human
action or inspection: pressing a board button, unplugging or replugging a cable,
observing LEDs/audio, clicking a desktop app, or acknowledging a live hardware
state. The prompt must be in Chinese, say exactly what to do and what success
looks like, and include a short sound cue when the wrapper/platform supports it.

## BLE And OTA Fix Discipline

When changing STM32WB BLE, GATT, OTA, boot handoff, Windows BLE integration, or
Listener-Type Companion transport behavior:

- Capture the repair lesson in a repo document before closing the work. Include
  the symptom, root cause, code paths, validation artifacts, and the exact
  recovery command if hardware can get stuck.
- Check official ST and Microsoft references, plus external field reports when
  useful. Prefer the local `third_party/STM32CubeWB` examples and official ST
  application notes as design authority.
- Record what will or will not carry to STM32WBA. Separate portable business
  logic and GATT contracts from WB55-specific CPU2/FUS/SRAM-handoff mechanics.
- Update static validation or scripts when the failure mode is repeatable, so
  the same regression is caught without relying on memory.
