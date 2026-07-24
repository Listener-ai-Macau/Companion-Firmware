# R10 Native Two-Pass Fine-Stride Work Package

Authority: `COMP-REQ-349`. This package is default-off and production-off. It is an offline MACHINE_READY candidate only; it creates no authorization and does not contact hardware.

The candidate `r10_native_two_pass_fine_stride` uses the owner-accepted COMP-REQ-236 native OTP Mode2 path. It renders a 112-pixel solid 12x12 disk at `y=80`, positions `x=32..64`, and moves in 2-pixel ping-pong steps. A baseline uses one bounded local `0x24` write with source `0xFF`, `0x20`, and BUSY. Every movement has exactly two activations: pass 1 uses the previous-black bounding window and pass 2 uses the full previous/current diff window. Each activation writes CPU current data through `0x24`, uses the source reset/border path and source `0xFF`, activates `0x20`, and requires BUSY <=600 ms. Qualification is 16 logical frames and 32 activations after baseline, followed by the same bounded path in an unlimited loop.

No motion `0x26`, `0x32`, `0x37`, `0xC7`, custom LUT/tail, full-frame candidate write, third activation, retry, maintenance refresh, or production path is permitted. The persistent lifecycle retains promptless dual-White cleaning, one canonical Chinese owner prompt after qualification, promptless post-clean, exact restore/readback, normal resume, and process audit.

Future authorization, if separately approved, must bind the generated MACHINE_READY and all current candidate/tool hashes. The exact command is intentionally recorded without creating or executing authorization:

```powershell
pwsh -NoProfile -File tools/start_wb55_ssd1681_r10_native_two_pass_fine_stride.ps1 -Execute -OutRoot .cache/validation/wb55-r10-native-two-pass-fine-stride-execute-20260722-r1 -AuthorizationArtifact .cache/validation/wb55-r10-native-two-pass-fine-stride-execute-20260722-r1-authorization.json
```
