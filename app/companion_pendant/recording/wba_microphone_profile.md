# Dual-microphone session selection

The existing recorder setting uses `0` for voice and `1` for meeting. At an
accepted product prepare, `capture_profile` snapshots this setting. Hardware
START and resume use that same snapshot; mutable preferences do not retarget
an ongoing logical recording. A rejected prepare does not publish a new snapshot.

With no explicit calibrated build configuration both modes keep the original
LEFT mono path. With the existing explicit delay/gain/polarity candidate,
voice selects fixed delay-and-sum before the original PCM16/Opus path. Meeting,
boot and the independent-pair service diagnostic keep LEFT. There is no new
filtering claim for a meeting or automatic selection of a person's identity.
An invalid or actually running microphone refuses a profile change before DMA
START; a rejected selection cannot start capture.

Selection allocates no buffer, changes no clock or sample rate and runs no
I/O. It preserves pair observation and lifetime counters. Existing START
discard/prime warms the selected filters and delay history before PCM delivery.
The old selected-only optimization remains when LEFT has no pair observer.

This is a source candidate based on actual FW699. No new image or install is
qualified by the host checks. The physical calibration declaration, desired
speech/interference comparison, voice fidelity, normal durable per-recording
processing metadata and long capture/coexistence qualification remain open.
Normal enhancement remains disabled. Do not install an old whole source tree:
merge this explicit delta into the latest shared firmware, together with any
other accepted upper changes, and retain current lower changes.
