# Per-recording microphone processing provenance (source candidate)

COP1 schema5 has flags15 and preserves schema4's explicit CONFIG/END source
sample boundary. Each physical segment starts with the12-byte COP1 header,
the32-byte CDB1 CONFIG, then exactly one96-byte APM1. Audio, pause/mark events,
padding and END follow the existing semantics. All APM1 bytes participate in
the same original segment CRC/SHA and descriptor UID/epoch/session binding.
APM1 is metadata, never audio samples, silence, a recording duration, proof of
noise reduction or a cryptographic attestation of physical calibration.

The payload retains output route, recorder purpose, actually filtered channel
mask, polarity flags, common gain, fractional delay/right trim, firmware
version/source, calibration SHA256 identity, decimation/layout/bit order and
algorithm version. The source identity must be nonzero. Baseline/mix routes
carry no applied calibration; directional output requires the calibration
identity and is restricted to voice. CRC is framing, not authentication.

The new optional engine callback is pure, uses the immutable accepted-session
snapshot and performs no I/O. Every segment repeats that snapshot. A changed
profile CRC faults before a successor prelude/audio becomes durable. Type
also compares the complete parameters across segments and rejects relabelling
the original, including while creating its online view. Historical recordings
have no invented profile or current-setting fallback.

Use the explicit `comp_wba_recording_product_prepare_audio_profile` entry
only with a profile callback and profile-aware capacity planning. The extra
prelude must fit before reserving. Existing product entry points continue to
write schemas1..4. Type supports parsing/recovering/persisting schema5 in this
candidate, but the current installed application does not include it.

Still required before normal product enable: board snapshot/build calibration
and exact image/source provider, matching receiver capability/release handling,
complete image/link and delivery, real capture/deadline/coexistence evidence.
Independent stereo originals and the pending controlled acoustic comparison
remain separate. Do not enable directional output or infer physical success
from the synthetic C golden/real-Opus NOR model. Android and standalone-import
metadata presentation are not qualified by these Windows V2 receiver checks.
