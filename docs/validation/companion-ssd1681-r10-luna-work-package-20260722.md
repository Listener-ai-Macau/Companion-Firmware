# SSD1681 R10 Luna Work Package

Date: 2026-07-22

Authority: `COMP-REQ-323`

Status: `READY_FOR_LUNA_IMPLEMENTATION / MACHINE_ONLY`

This package is implementation instruction, not hardware authorization. Luna must stop after a stable
R10 `MACHINE_READY` and return all diffs, commands, artifacts and hashes to the primary decision agent.

## 1. Required Read Order

1. `C:/Users/Billy/.codex/skills/ai-collaboration-workflow/SKILL.md`
2. `<AI_WORKFLOW_REPO>/docs/agent_quickstart.md`
3. `<AI_WORKFLOW_REPO>/docs/codex_goal_contract.md`
4. `docs/companion_product_requirements.md`, especially `COMP-REQ-318..323`
5. `docs/validation/companion-ssd1681-lower-driver-next-agent-handoff-20260721.md`
6. `docs/validation/companion-ssd1681-lower-driver-next-agent-handoff-20260721.json`

Run `get_goal` first. Preserve the active Goal. Do not complete, block, delete or replace it.

## 2. Worktree Rules

- The worktree is massively dirty. Do not reset, checkout, delete, normalize or format unrelated files.
- Do not edit V9, Rig, CRIG, browser, art, dynamic expressions, vendor packages or
  `docs/validation/companion-pet-special-system-owner-acceptance-20260717.json`.
- Do not modify or rerun R1-R9, R8 mapping, COMP-REQ-236/237, or any consumed authorization.
- Owned implementation files for this package are the R10 header/oracle, the minimal R10 additions in
  `panel_target_stm32wb_ssd1681.c`, versioned R10 verifier/build/runner/monitor/supervisor/launcher files,
  and new R10 validation artifacts.
- Existing non-R10 changes in shared files belong to other agents. Preserve them byte-for-byte outside
  the smallest R10 insertion points.

## 3. Current Scaffold Audit

The repository currently has:

- `app/companion_pendant/epaper/r10_ball_diagnostic.h`
- `tools/verify_wb55_ssd1681_r10_ball_pixel_oracle.py`
- `docs/validation/companion-ssd1681-phase-parallel-r10-ball-pixel-oracle-20260722.json`
- default-off `COMPANION_EPAPER_SSD1681_R10_BALL_DIAGNOSTIC` definitions and some compile guards in the
  SSD1681 driver

The scaffold is incomplete. It has no R10 transport function, init dispatch, build selector, parser,
monitor, supervisor, persistent launcher, CheckOnly closure or MACHINE_READY. Do not call it buildable.

The pixel artifact currently reports 16 positive transitions and four rejected negatives. Before using
it as authority, remove the dead `assert_position_path.__wrapped__()` probe, replace it with a real
validator-driven wrong-step negative, remove unused imports, rerun the oracle twice, and require
byte-identical output and SHA-256. The current script also prints the SHA of the pre-write LF string;
on Windows the artifact is stored with CRLF, so that printed value does not match `Get-FileHash`.
Hash the final file bytes after the write and require the reported SHA to equal the filesystem SHA.

## 4. Fixed Geometry

- Frame: 200x200 monochrome, 25 bytes per row, 5000 bytes total; `1=White`, `0=Black`.
- Shape: complete solid disk in a 12x12 bounding box.
- Disk row widths: `4,8,10,10,12,12,12,12,10,10,8,4`.
- Top-left Y: `80`.
- X positions: `32,40,48,56,64`.
- Qualification current positions:
  `32,40,48,56,64,56,48,40,32,40,48,56,64,56,48,40`.
- Step: exactly 8 px. Travel span: exactly 32 px. Path: ping-pong.
- Initial previous frame: all White.
- After qualification ends at X=40, the first loop current position is X=32, then the same ping-pong
  cycle repeats.

The row masks in `r10_ball_diagnostic.h` are candidate source data, not trusted truth. The oracle must
independently derive the disk from the integer equation `(2*x-11)^2 + (2*y-11)^2 <= 144` and prove the
C masks generate the identical 112-pixel set at every position.

## 5. Driver Architecture

Implement a separate direct diagnostic under `COMPANION_EPAPER_SSD1681_R10_BALL_DIAGNOSTIC`.
The macro remains default `0`; no production path or ordinary ball-motion path may select it.

Use the existing global `s_previous_frame` and `s_frame` buffers. Do not allocate two 5000-byte frames
on the stack. Render White/ball states into those full framebuffers for every logical frame.

Place R10 helpers after the existing full-frame difference/window and plane-region helpers so they can
reuse:

- `ssd1681_window_from_difference()`
- `ssd1681_window_byte_count()`
- `ssd1681_point_probe_set_window()`
- `ssd1681_write_plane_region()`
- `ssd1681_wait_refresh_complete()`

For each logical frame, execute exactly:

1. Render full previous/current framebuffers.
2. Derive the window from their complete diff.
3. Assert first frame window is X bytes `4..5`, Y `80..91`, 24 bytes; every moving frame is the exact
   3-byte-by-12-row envelope for its old/new pair, 36 bytes.
4. Reissue window/counters, write previous framebuffer region with command `0x26` once.
5. Reissue window/counters, write current framebuffer region with command `0x24` once.
6. Send exactly `0x22=0xCF`, then one `0x20`.
7. Wait for BUSY completion with a hard 600 ms limit and record elapsed time.
8. Reissue window/counters and write current framebuffer region with `0x24` once, with no activation.

Do not use fixed 128-byte R9 pattern payload helpers for R10. Do not use the old
`ball_motion_diagnostic.h` orbit path. Do not use a shape-specific hard-coded transport window.

Compile the existing byte-identical `ssd1681_phase_parallel_r9_lut` for R10 and load it exactly once:

- `0x32`: bytes 0..152
- `0x3F`: `22`
- `0x03`: `17`
- `0x04`: `41 A8 32`
- `0x2C`: `58`

Protected LUT SHA-256:
`9BCBAC1A07ED0A112D26409FBCDB8F5FE27CE07D922C2E18881C10A53229DDCD`.

Forbidden in candidate frames: full-frame writes/activations, `F7`, `C7`, `FF`, `0x37`, second
activation, erase/draw pass, maintenance refresh, retry, dwell and automatic full refresh.

## 6. Trace Schema

Use a versioned prefix: `[epaper] phase_parallel_r10_ball`.

Emit one start record with geometry, LUT hash, tail, mapping, BUSY limit and all forbidden counters.
Emit one qualification record per completed frame containing:

- step, previous/current X (`white` for initial previous)
- previous/current full-frame SHA or oracle identity
- X-byte/Y window and byte count
- WW/WB/BW/BB counts
- `0x26` bytes, staged `0x24` bytes, `0xCF`, `0x20`, BUSY elapsed
- post-sync `0x24` bytes and `post_sync_refresh=0`
- `step_ok=1`

After exactly 16 records emit `qualification_result=ok` only if every invariant passed. Otherwise emit
`qualification_result=no_go`, restore the GPIO bus and return without an observation-ready marker.

The loop emits monotonically increasing iteration numbers and the same per-frame evidence. UART may
stream, but the host must retain only a fixed 65536-byte ring. On transport/BUSY failure emit one fault
record, restore the GPIO bus and return. No in-firmware retry or popup is allowed.

## 7. Static and Negative Gates

Create a versioned R10 source/static verifier. It must parse C arrays, not only search strings, and prove:

- macro default-off and mutually exclusive
- geometry/masks match the independent oracle
- R9 LUT all 159 bytes and tail are byte-identical
- full framebuffer diff is used
- dynamic 24/36-byte windows, not fixed 128-byte payloads
- exact command order and one activation per frame
- no forbidden command/path
- exact 16-position qualification and loop continuation
- init dispatch exists only under the R10 macro

Create log parser positive and negative fixtures for: missing/extra frame, wrong position, wrong step,
wrong window, clipped disk, square payload, wrong framebuffer/payload hash, wrong class count, missing or
extra `0x26`, staged/post-sync `0x24`, `0xCF`, `0x20`, BUSY >600, second activation, full-frame/F7/C7/FF/
0x37, retry, non-contiguous loop iteration, qualification failure followed by observation, unbounded
storage, popup on a routine/fault path and stale R9 marker acceptance.

## 8. Build and Lifecycle Tools

Add a dedicated isolated build selector and output directory. Do not overload or replace R9 targets.
The build must produce distinct ELF and HEX names containing `R10Ball`.

Create versioned R10 runner, parser, monitor, prompt supervisor and persistent launcher by preserving
the proven R9 continuous R2 lifecycle while replacing R9 marker/schema identities with R10. Do not edit
the archived R9 runner or artifacts.

The supervisor must use the canonical Chinese `aiw operator-prompt` with only `通过` and `失败`, and only
after qualification PASS, concurrently with the loop. In CheckOnly and simulation regression it starts
zero real popup. Start, cleanup, recovery, fault and machine-failure popup counts are zero.

The runner must retain promptless dual-plane White pre/post-clean, exact 524288-byte raw application
restore/readback and normal-resume gates. Protected application SHA-256:
`223F6E7A7DB8E5562D0F7C34ED4F023DA7E37F5266505A6C84D5BD6FE304CD7C`.

CheckOnly must use a fresh output root and prove:

- `hardware_contact=0`
- programmer/panel/application writes `=0`
- popup `=0`
- retry `=0`
- child exit and durable stdout/stderr closure
- fixed 65536-byte ring

## 9. Audit Compatibility

`tools/verify_companion_ssd1681_lower_driver_handoff.py` is the historical paused-handoff verifier and
expects R10 to be absent. Do not weaken or rewrite it to manufacture a PASS after R10 starts.

Update or supersede `verify_companion_current_goal_audit.py` explicitly for COMP-REQ-323 so the current
audit recognizes R10 as active while retaining the pre-R10 artifact as historical evidence. Record the
successor verifier in registry/MACHINE_READY evidence.

## 10. Required Commands Before Return

Run, at minimum:

```powershell
python tools/verify_wb55_ssd1681_r10_ball_pixel_oracle.py --write
python tools/verify_companion_product_requirements.py
python tools/verify_companion_current_goal_audit.py
python <new-r10-static-verifier>
python <new-r10-log-parser-positive-and-negatives>
pwsh -NoProfile -File tools/build_nucleo_bringup.ps1 <new-r10-build-switch>
pwsh -NoProfile -File <new-r10-persistent-launcher> -CheckOnly -OutputRoot <fresh-root>
git diff --check -- <owned-files>
```

Run all relevant legacy R9 protected-hash verifiers that do not require R10 absence. Do not execute any
hardware command in this package.

## 11. Return Contract

Return to the primary decision agent with:

- exact owned file list and diff summary
- every command and PASS/FAIL result
- oracle/static/parser/negative/CheckOnly artifacts and SHA-256
- ELF, HEX, LUT, runner, monitor, supervisor, launcher and MACHINE_READY SHA-256
- exact future Execute command, not run
- `hardware_contact=0`, write `=0`, popup `=0`
- process-exit audit
- all unproved items and `NO_GO` conditions

Stop at `MACHINE_READY`. The primary decision agent alone reviews and decides whether to request a fresh
hash-bound one-shot hardware authorization.
