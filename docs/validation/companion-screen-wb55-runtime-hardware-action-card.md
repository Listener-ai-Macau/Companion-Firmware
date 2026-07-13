# WB55 Rev53 Runtime 硬件执行卡

这张卡是生成文件，只用于 rev53 机器 runtime recheck。它不代表人工触摸/视觉验收已开始。

- 状态: `NO_GO_WAITING_FOR_REAL_HARDWARE_RUN`
- 目标: `NUCLEO-WB55RG + GDEY0154D67-T03 + FT6336U`
- 资源: revision `53`, bytes `49901`, CRC `0x2332E300`
- build matrix: `PASS`, variants `dry_run_default, screen_asset_provision, ssd1681_real_panel`
- ScreenAssetProvision size: `{'bss': 192239, 'data': 2433, 'dec': 602988, 'hex': '9336c', 'text': 408316}`
- SCR-17 ledger: `RUNTIME_PROMOTED_HUMAN_VISUAL_PENDING`, first frame `coherent_generation=1`, stale discard model `3`
- runtime logs gate: `NO_GO_INCOMPLETE_RUNTIME_MARKERS`
- promotion gate: `APPLIED`
- pre-acceptance: `NO_GO_INTERACTION_PROFILE_RUNTIME_RECHECK_PENDING`
- human review record: `NO_GO_OPEN_REVIEW_ITEMS`
- flash preflight: `PASS`
- serial capture preflight: `PASS_STATIC_SERIAL_CAPTURE_PREFLIGHT`
- failure recovery restores normal: `True`
- no-hardware recovery self-test: `FAIL`, restored normal `True`

## 先做预演

```powershell
pwsh -NoProfile -File .\tools\run_wb55_screen_runtime_recheck.ps1 -CheckOnly
```

再跑失败恢复自测。这个命令不刷机、不开串口，只证明 provision 后失败会触发 normal 恢复：

```powershell
pwsh -NoProfile -File .\tools\run_wb55_screen_runtime_recheck.ps1 -SelfTestRecovery -OutRoot .\.cache\validation\rev53-runtime-recovery-selftest
```

- self-test report: `.cache/validation/rev53-runtime-recovery-selftest/runtime-recheck-run.json`
- expected status: `FAIL`
- expected recovery: `flash_normal_after_failure=PASS`, `normal_firmware_restored=true`

空串口日志自测也必须保持 FAIL；它不打开 COM 口，只证明 0 字节日志不会被当作 runtime evidence：

```powershell
pwsh -NoProfile -File .\tools\capture_nucleo_serial.ps1 -SelfTestEmptyCapture -OutDir .\.cache\validation\nucleo-serial-empty-selftest
```

- self-test summary: `.cache/validation/nucleo-serial-empty-selftest/nucleo-serial-summary.json`
- expected status: `FAIL`
- expected bytes_read: `0`

复位超时自测也必须保持 FAIL；它不打开真实硬件，只用 stub 进程证明 STM32 reset 不会无限挂住：

```powershell
pwsh -NoProfile -File .\tools\capture_nucleo_serial.ps1 -SelfTestResetTimeout -OutDir .\.cache\validation\nucleo-serial-reset-timeout-selftest
```

- self-test summary: `.cache/validation/nucleo-serial-reset-timeout-selftest/nucleo-serial-summary.json`
- expected status: `FAIL`
- expected reset timeout error: `reset timed out after 5 second(s)`

## 真实硬件执行

刷机预检：

- provision image: `cubeide/Companion_Nucleo_WB55RG_Bringup/build_screen_asset_provision/Companion_Nucleo_WB55RG_ScreenAssetProvision.hex` (`exists=True`)
- normal image: `cubeide/Companion_Nucleo_WB55RG_Bringup/build/Companion_Nucleo_WB55RG_Bringup.hex` (`exists=True`)
- programmer exists: `True`
- flash timeout: provision `120` s, normal `120` s
- serial capture script: `tools/capture_nucleo_serial.ps1`
- serial outputs: `nucleo-serial-raw.log`, `nucleo-serial-summary.json`
- reset timeout: `15` s
- empty serial capture fails: `True`
- empty serial self-test: `FAIL`, bytes `0`
- reset timeout self-test: `FAIL`, reset stdout `True`, reset stderr `True`

必须通过 workflow hardware lock 执行：

```powershell
pwsh -NoProfile -File C:\Users\Billy\Desktop\Denzic\ai-collaboration-workflow\scripts\aiw.ps1 with-lock -Resource Companion-WB55 -Purpose "Companion WB55 rev53 screen runtime recheck" -Run pwsh -NoProfile -File .\tools\run_wb55_screen_runtime_recheck.ps1 -Execute -WorkflowLockHeld
```

该命令内部按顺序执行：

1. `flash_provision`
   - 刷入带外部 CEMP 资源写入逻辑的 provision 固件。
   - `pwsh -NoProfile -File .\tools\flash_nucleo_bringup.ps1 -ScreenAssetProvision -ProgrammerRoot C:\ST\STM32CubeIDE_2.1.1\STM32CubeIDE\plugins`
2. `capture_provision`
   - 复位并抓取 provision 启动串口日志，证明资源写入/挂载链路。
   - `pwsh -NoProfile -File .\tools\capture_nucleo_serial.ps1 -Execute -WorkflowLockHeld -Seconds 25 -ResetAfterOpen -OutDir C:\Users\Billy\Desktop\Denzic\Companion\Companion-Firmware-devboard-oai1\.cache\validation\rev53-runtime-current\provision`
3. `flash_normal`
   - 刷回普通运行固件，避免设备停留在 provision 镜像。
   - `pwsh -NoProfile -File .\tools\flash_nucleo_bringup.ps1 -ProgrammerRoot C:\ST\STM32CubeIDE_2.1.1\STM32CubeIDE\plugins`
4. `capture_normal`
   - 复位并抓取 normal 启动串口日志，证明普通固件从外部 Flash 挂载 rev53。
   - `pwsh -NoProfile -File .\tools\capture_nucleo_serial.ps1 -Execute -WorkflowLockHeld -Seconds 25 -ResetAfterOpen -OutDir C:\Users\Billy\Desktop\Denzic\Companion\Companion-Firmware-devboard-oai1\.cache\validation\rev53-runtime-current\normal`

## Provision 串口日志必须包含

- `mount=ok`
- `revision=53`
- `clips=33 frames=75`
- `expression_renderer=external_pack`
- `source=external_flash`
- `pet_behavior_selftest=pass failure_code=0`
- `touch-health] detected=1 identity=1 addr=0x38`
- `queue_generation revision=53`
- `coherent_generation=1`
- `generation_switches=`
- `last_stale_discarded=`
- `refresh mode=full`
- `complete=1`
- `external_store=ready`
- `preview_started name=idle`

## Normal 串口日志必须包含

- `mount=ok`
- `revision=53`
- `clips=33 frames=75`
- `expression_renderer=external_pack`
- `source=external_flash`
- `pet_behavior_selftest=pass failure_code=0`
- `touch-health] detected=1 identity=1 addr=0x38`
- `queue_generation revision=53`
- `coherent_generation=1`
- `generation_switches=`
- `last_stale_discarded=`
- `refresh mode=full`
- `complete=1`
- `[build] interaction_profile=quiet epaper_trace=0 touch_trace=0 ft6336_threshold=0x70 touch_poll_active_ms=5 touch_poll_refresh_ms=5 refresh_policy=partial_x5_then_fast_cleanup`
- `frame rotation=180 mirror_x=1`
- `preview_started name=idle`

这些 marker 同时用于 SCR-17 release ledger：确认 rev53 是唯一 active generation，旧队列已丢弃，首帧是当前 generation。

## 跑完硬件后

```powershell
python .\tools\verify_screen_generation_release_ledger.py
```
```powershell
python .\tools\verify_wb55_screen_runtime_recheck_logs.py --write
```
```powershell
python .\tools\verify_companion_screen_pre_acceptance_health.py
```
```powershell
python .\tools\verify_companion_screen_goal_audit.py
```

## 不要做

- 不要手工把 REVISION_53_RUNTIME_RECHECK_PENDING 改成 PASS。
- 不要跳过 normal 固件恢复；provision 只用于写资源。
- 如果 provision 后失败，runner 会尝试 flash_normal_after_failure；若 normal_firmware_restored 不是 true，不要继续验收。
- 不要在 runtime logs PASS 和 promotion --apply 前启动触摸/视觉人工验收。
- 不要把 DRY-RUN report 当作真实硬件日志。

人工验收入口规则：只有 rev53 provision/normal runtime logs 验证 PASS、当前 quiet interaction profile 在 normal log 中完整出现、resource promotion 已适用且 pre-acceptance health PASS 后，操作者明确说“开始验收”，才进入触摸/视觉人工验收。
