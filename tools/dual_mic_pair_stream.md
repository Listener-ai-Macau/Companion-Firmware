# Finite independent microphone pairs (engineering candidate)

This source is **not enabled in the normal product**. The normal mono Opus,
BLE recording protocol, storage allocation and LEFT default are unchanged.
It adds a firmware-compatible caller-owned packet queue and a file decoder;
the real board storage/transport port is still missing. The software fixture
runs the unchanged current PDM converter and observer, not a simulated stereo
copy of an existing mono file. Its source samples are explicitly synthetic.

`app/companion_pendant/recording/wba_dual_mic_pair_stream.h` accepts one verified
160-frame16kHz interleaved L/R block. The source position must come from the
actual capture sequence and startup/sample origin. On missing/stale/rejected
capture, queue overflow or other capture fault, invalidate the stream. Finish
only after the finite observation window and actual capture counters have been
checked. No packet printing, storage I/O, heap or waiting belongs in the pair
callback. All queue calls use the same foreground task; this is not an ISR or
concurrent producer/consumer queue. A caller may drain complete packets outside
the callback and consume only after its actual sink accepts them. Pending or
failed sink operations must retain identical pending bytes.

The format is DMP1 header80B, contiguous DMPF blocks664B and DMPE terminal48B.
All integers/PCM are little endian. Each packet has CRC32; the terminal binds
header CRC, original PCM CRC, real accepted source count and clip/fault counts.
UID, immutable capture-image source, recording identity, source offset and
synthetic origin remain in-band. CRC and an external receipt are consistency
checks, **not authentication** or proof of acoustic geometry.

The caller must provide a real independently reserved storage/transport port,
respect current recording/OTA ownership, verify completion and release its own
actual handles. No permanently reserved NOR region, unsafe worktree install,
reused OTA lease, unbounded PCM RAM, or production codec substitution is added.
In particular115200 UART cannot continuously carry stereo PCM16 at16kHz
(64000 payload bytes/s before framing). Raising baud, blocking in callbacks or
dropping frames is not a substitute for integrating a proper port. Board-side
integration and physical timing/continuous-operation qualification remain OPEN.

`tools/decode_wba_dual_mic_stream.py` takes `--stream`, `--capture-evidence`,
`--destination` and optional explicit `--use-case`. It refuses incomplete,
reordered, repeated, altered, unidentified or faulted streams. The matching
`companion.dual-mic-pair-capture.v1` receipt must bind the original stream hash,
identity/sample/clip counts, both processed channels, actual source position,
complete capture status and every required zero capture-fault counter. A
software fixture cannot silently become BOARD_SAI_PDM evidence. No hardware
capture command or automatically generated physical receipt is supplied.

The new destination retains original DMP bytes, original independent stereo
WAV, source manifest and unmodified external capture receipt. Existing outputs
and originals are never overwritten. A clipped source can be retained honestly,
but cannot enter the existing unclipped fixed-beamformer processor. Every
source starts GENERAL_DUAL_MIC_CAPTURE; FRONT_CLOSE_TALK_CANDIDATE is explicit.
ALL_PARTICIPANT_MEETING remains eligible for source export but cannot silently
enter the fixed-front processing tool. Neither choice identifies the owner or
qualifies noise reduction.

The existing `process_wba_dual_mic_pair.py` can use an eligible decoded pair,
its manifest and original capture receipt with an accepted finite calibration.
Original channels remain independent; enhancement is a separate candidate with
its own parameters, implementation hash and exact source sample range. Real
noise suppression, speech preservation, wrong direction, meeting pickup,
long recording and normal product per-record provenance still need actual
current-board evidence. Source/host checks alone do not enable this feature.

Affected software check: `tools/tests/test_dual_mic_pair_stream.py` exercises
the actual unchanged production PDM C through the pair observer, bounded
queue, decoder, stereo source and existing processing/C-reference path. These
are software fixtures, not recordings made by the board.
