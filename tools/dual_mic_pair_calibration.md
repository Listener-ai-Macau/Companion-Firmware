# Saved-pair calibration and separate candidate

This host-only path joins the existing finite DMP1 capture, the unchanged
production C correlation convention, and the existing separate beamformed
candidate exporter. It does not enable enhancement in normal recordings.

Before a controlled capture, prepare an actual setup declaration with schema
`companion.dual-mic-known-source.v1`, the exact `deviceUid` and `firmwareSource`,
`knownSingleBroadbandSourceConfirmed: true`,
`useCase: FRONT_CLOSE_TALK_CANDIDATE`, a factual `sourceDescription`, and an
explicit `maxDelaySamples` based on the current acoustic geometry. An archived
PCB reference-center distance does not verify today's assembled acoustic path.
Do not invent these fields while the actual source or position is unknown.

Pass this file as `--known-source-setup` to `capture_wba_dual_mic_pair.py` along
with its existing required arguments. The optional file is checked before any
serial import, endpoint selection or device access, and its original bytes and
hash are retained by the capture. With no file, the original general-purpose
two-second capture behavior remains; it is explicitly uncalibrated. Neither
mode starts a BLE central, playback or a cloud request.

After the capture has completed and released its actual microphone/workspace
and serial handle, use the same source files offline:

```text
python tools/calibrate_wba_dual_mic_pair.py --stream capture/original-pair.dmp --capture-evidence capture/capture-evidence.json --known-source-setup capture/known-source-setup.json --destination new-comparison
```

The output contains the unchanged DMP1, independent stereo WAV and capture
evidence, the original setup declaration, statistics derived from precisely
those PCM samples, calibration parameters, and a separate mono candidate.
The original stream, recording token, sample positions, image and all input
hashes are retained. Unavailable fractional-delay startup history is withheld
explicitly by the existing processor, with no invented silence.

Before publishing a saved-pair calibration, the tool now applies the unchanged
energy/coherence/peak criteria independently to the first and second halves.
Each disjoint half needs at least8006 frames; the ordinary two-second capture
provides both. Full-pair and half-window delays must agree within0.25samples,
right gains within1dB, and polarity must agree. A common onset or changing gain
cannot qualify an otherwise unsupported steady source. The full original is
retained; no warmup samples are cut or changed. `temporalStability` binds the
source intervals and each window-probe hash. The normal build input reader
requires this same proof and rejects older unsupported calibration JSON; it
does not enable enhancement or relax the known-front-source requirement.

The tool refuses missing or retrospectively changed setup, wrong identity,
failed continuity/capture counters, clipping, insufficient energy, ambiguous
correlation or out-of-bound delay. It does not repair missing source samples,
replace existing outputs or overwrite an original. General/meeting capture
cannot silently acquire a forward-facing profile. Synthetic input remains
labelled synthetic throughout.

The derived statistics match `wba_dual_mic_probe.h` sample-for-sample in the
affected software checks. That confirms arithmetic, not acoustic direction,
speech fidelity, denoising, speaker identification or real-time qualification.
Actual same-take desired-speech/interference comparison is still required before
considering a normal product profile. Existing unlabelled FW695 environment
audio remains ineligible; no retrospective setup is attached to it.

The comparison folder also contains `comparison-left.wav` and
`comparison-right.wav`. These retain the raw single-channel gain and use
precisely the same capture sample interval as `enhanced-candidate.wav`, after
the explicitly withheld startup history. There is no loudness normalization
or added silence. This is a common source-index window, not a proof of acoustic
arrival-time alignment. The unchanged full independent stereo original stays
available separately.

`processing.json` associates each audio file's role, SHA-256, source interval,
sample rate and channel identity with the recording ID/token, device, image,
calibration and implementation. It also reports the exact number of published
output samples that the fixed front end saturated. A clipped candidate remains
an explicitly marked comparison artifact; neither a clean output nor the act of
exporting it proves speech fidelity or actual noise reduction. The parent
calibration result binds that exact processing manifest and preserves the
clipping result. None of these file-only changes enable normal product
processing or qualify its per-recording metadata integration.
