# Companion Firmware Codex Workflow

This repo uses a two-track STM32 workflow so Codex can keep making verifiable
progress without depending on CubeIDE GUI state for every edit.

## Recommended Shape

1. Keep `cubeide/Companion_Nucleo_WB55RG_Bringup` as the hardware bring-up
   project for the current NUCLEO-WB55RG bench board.
   - Codex can build it with `tools/build_nucleo_bringup.ps1`.
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

3. Keep generated code and handwritten product code separated.
   - CubeMX owns peripheral init and files it generates.
   - Codex owns portable modules, validation scripts, build/flash/capture
     wrappers, and code inside explicit USER CODE regions when generated files
     must be extended.
   - Do not edit `third_party/STM32CubeWB/**`; it remains an official reference.

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
