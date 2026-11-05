#!/usr/bin/env python3
"""Create a separate, traceable fixed-beamformer candidate from a PCM pair.

File-only engineering tool: no device, recording, network or automatic enable.
Requires synchronous post-channel/DC, pre-beamformer 16 kHz stereo PCM and
the original finite-probe calibration. A mono COP1/WAV cannot recover a pair.
Caller declarations remain declarations, not acoustic qualification. Normal
product recording/transport formats and the installed LEFT default are intact.
"""
from __future__ import annotations

import argparse
from array import array
import hashlib
import io
import json
import math
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile
import wave

import calibrate_wba_dual_mic as calibration_tool

MAX_SECONDS = 600
RATE = 16000
MAX_BYTES = MAX_SECONDS * RATE * 4 + 65536
STAGE = 'POST_CHANNEL_GAIN_DC_PRE_BEAMFORM_PCM16_NO_CLIPPING'


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def integer(value, lo: int, hi: int, field: str) -> int:
    if type(value) is not int or not lo <= value <= hi:
        raise ValueError('Invalid ' + field)
    return value


def read_json(path: Path, limit=2_000_000):
    raw = path.read_bytes()
    if len(raw) > limit:
        raise ValueError('JSON input too large')
    # Repeated security/identity fields cannot silently take the last value.
    def unique(pairs):
        result = {}
        for k, v in pairs:
            if k in result:
                raise ValueError('Duplicate JSON field')
            result[k] = v
        return result
    result = json.loads(raw, object_pairs_hook=unique)
    if not isinstance(result, dict):
        raise ValueError('JSON object required')
    return raw, result


def read_pair(raw: bytes):
    if len(raw) > MAX_BYTES:
        raise ValueError('PCM pair exceeds finite file limit')
    with wave.open(io.BytesIO(raw), 'rb') as wav:
        if (wav.getnchannels(), wav.getsampwidth(), wav.getframerate(), wav.getcomptype()) != (2, 2, RATE, 'NONE'):
            raise ValueError('Need independent synchronous 16kHz stereo PCM16, not mono or an encoded recording')
        n = wav.getnframes()
        if not 160 <= n <= MAX_SECONDS * RATE:
            raise ValueError('Invalid synchronous pair duration')
        samples = array('h', wav.readframes(n))
        if sys.byteorder != 'little':
            samples.byteswap()
        if len(samples) != n * 2:
            raise ValueError('Truncated synchronous PCM pair')
    if any(x in (-32768, 32767) for x in samples):
        raise ValueError('Clipped PCM pair cannot reproduce the pre-clipping front end')
    return samples, n


def bind_calibration(raw_probe: bytes, c: dict, manifest: dict):
    if c.get('result') != 'FIXED_FRONT_END_CALIBRATION_CANDIDATE_ONLY' or c.get('automaticApply') is not False:
        raise ValueError('Need an accepted, explicit candidate calibration; no fallback parameters')
    for key, pattern in [('deviceUid', r'[0-9a-f]{24}'), ('firmwareSource', r'[0-9a-f]{40}')]:
        if not isinstance(c.get(key), str) or not re.fullmatch(pattern, c[key]) or manifest.get(key) != c[key]:
            raise ValueError('Pair/calibration identity mismatch: ' + key)
    if c.get('probeLogSha256') != sha(raw_probe) or c.get('knownSingleSourceCallerDeclared') is not True:
        raise ValueError('Original known-source probe binding required')
    token = integer(c.get('recordingToken'), 1, 0xffffffff, 'calibration token')
    bound = c.get('maxDelaySamples')
    # Historical P638/P639 tool used the default2-sample bound but did not
    # persist it. Do not invent that missing declaration for older receipts.
    if type(bound) not in (int, float) or not math.isfinite(bound) or not 0 < bound <= 2.5:
        raise ValueError('Calibration must retain its actual geometry delay bound; regenerate from the same original probe')
    actual = calibration_tool.estimate(calibration_tool.parse_probe(raw_probe.decode('utf-8', 'strict'), token),
        known_single_source=True, max_delay_samples=bound)
    for key in ['sampleRate', 'synchronousSamples', 'delayQ8', 'rightGainQ15', 'invertRight', 'candidateBuildArguments']:
        if c.get(key) != actual.get(key):
            raise ValueError('Calibration parameter mismatch: ' + key)
    return actual


def validate_manifest(m: dict, pair_raw: bytes, frames: int):
    if m.get('schema') != 1 or m.get('sourceKind') != 'SYNCHRONOUS_DUAL_PCM':
        raise ValueError('Synchronous source manifest required')
    if m.get('channels') != ['left', 'right'] or m.get('processingStage') != STAGE:
        raise ValueError('Independent channel order and processing stage required')
    if m.get('pairWavSha256') != sha(pair_raw) or m.get('sampleRateHz') != RATE or m.get('sampleCount') != frames:
        raise ValueError('Pair bytes/sample identity mismatch')
    if m.get('continuityVerified') is not True or type(m.get('synthetic')) is not bool:
        raise ValueError('Explicit source/continuity declaration required')
    integer(m.get('recordingId'), 1, 0xffffffff, 'recording ID')
    integer(m.get('recordingToken'), 1, 0xffffffff, 'recording token')
    integer(m.get('sourceSampleOffset'), 0, (1 << 53) - frames, 'source sample offset')
    if m.get('useCase') != 'FRONT_CLOSE_TALK_CANDIDATE':
        raise ValueError('Fixed-direction candidate must not silently replace meeting pickup')
    if not isinstance(m.get('captureEvidenceSha256'), str) or not re.fullmatch(r'[0-9a-f]{64}', m['captureEvidenceSha256']):
        raise ValueError('Capture evidence hash required')


def divide_zero(value: int, denominator: int) -> int:
    return -(abs(value) // denominator) if value < 0 else value // denominator


def process_samples(pairs, delay_q8: int, gain_q15: int, invert: bool, metrics=None):
    """Integer order mirrors wba_dual_mic_beamformer.h; C cross-check required.

    Pair observation follows the channel/DC gain and PCM16 clipping. Clipped
    inputs are refused above, so the original wide input equals these samples.
    The withheld initial delay history is reported, never padded as real audio.
    """
    integer(delay_q8, -2048, 2048, 'delay')
    integer(gain_q15, 16384, 65535, 'right gain')
    if type(invert) is not bool or len(pairs) % 2:
        raise ValueError('Invalid pair/polarity')
    history = [[0] * 10, [0] * 10]
    write = 0
    output = array('h')
    withheld = (abs(delay_q8) + 255) // 256
    clipped = 0
    for i in range(0, len(pairs), 2):
        right = divide_zero(pairs[i + 1] * gain_q15, 32768)
        history[0][write] = pairs[i]
        history[1][write] = -right if invert else right
        def tap(channel, delay):
            whole, fraction = divmod(delay, 256)
            j = (write + 10 - whole) % 10
            return divide_zero(history[channel][j] * (256 - fraction) + history[channel][(j + 9) % 10] * fraction, 256)
        left = tap(0, max(delay_q8, 0))
        right = tap(1, max(-delay_q8, 0))
        value = divide_zero(left + right, 2)
        if i // 2 >= withheld and (value < -32768 or value > 32767):
            clipped += 1
        output.append(max(-32768, min(32767, value)))
        write = (write + 1) % 10
    if metrics is not None:
        metrics['outputClippedSamples'] = clipped
    return output[withheld:], withheld


def mono_wav(samples):
    # Copy before byteswapping so all caller-owned originals stay unchanged.
    values = array('h', samples)
    if sys.byteorder != 'little':
        values.byteswap()
    buffer = io.BytesIO()
    with wave.open(buffer, 'wb') as wav:
        wav.setnchannels(1); wav.setsampwidth(2); wav.setframerate(RATE)
        wav.writeframes(values.tobytes())
    return buffer.getvalue()


def create_bundle(pair: Path, source: Path, calibration: Path, probe: Path, capture_evidence: Path, destination: Path):
    destination = destination.absolute()
    if destination.exists() or destination.is_symlink():
        raise ValueError('Destination already exists; previous artifacts are immutable')
    if not destination.parent.is_dir():
        raise ValueError('Destination parent must already exist')
    paths = [pair, source, calibration, probe, capture_evidence]
    if pair.stat().st_size > MAX_BYTES or any(p.stat().st_size > 2_000_000 for p in paths[1:]):
        raise ValueError('Input exceeds finite file limit')
    inputs = [p.read_bytes() for p in paths]
    pair_raw, source_raw, calibration_raw, probe_raw, evidence_raw = inputs
    if len(probe_raw) > 2_000_000 or len(evidence_raw) > 2_000_000:
        raise ValueError('Evidence exceeds finite file limit')
    _, m = read_json(source)
    _, c = read_json(calibration)
    if source.read_bytes() != source_raw or calibration.read_bytes() != calibration_raw:
        raise ValueError('Input changed while loading')
    samples, count = read_pair(pair_raw)
    validate_manifest(m, pair_raw, count)
    if sha(evidence_raw) != m['captureEvidenceSha256']:
        raise ValueError('Capture evidence changed')
    config = bind_calibration(probe_raw, c, m)
    metrics = {}
    output, withheld = process_samples(samples, config['delayQ8'], config['rightGainQ15'], config['invertRight'], metrics)
    result_raw = mono_wav(output)
    # Same capture index interval for a fair listening comparison. The source
    # channels keep their original gains/delays: these are references, not a
    # claim of acoustic arrival-time alignment or matched speech loudness.
    left_raw = mono_wav(samples[withheld * 2::2])
    right_raw = mono_wav(samples[withheld * 2 + 1::2])
    output_offset = m['sourceSampleOffset'] + withheld
    def artifact(raw, role, channels, offset, frames):
        return dict(sha256=sha(raw), role=role, channels=channels,
            sourceSampleOffset=offset, sampleCount=frames, sampleRateHz=RATE)
    artifacts = {
        'original-pair.wav': artifact(pair_raw, 'UNCHANGED_INDEPENDENT_PAIR', ['left','right'], m['sourceSampleOffset'], count),
        'comparison-left.wav': artifact(left_raw, 'UNPROCESSED_LEFT_REFERENCE', ['left'], output_offset, len(output)),
        'comparison-right.wav': artifact(right_raw, 'UNPROCESSED_RIGHT_REFERENCE', ['right'], output_offset, len(output)),
        'enhanced-candidate.wav': artifact(result_raw, 'DERIVED_FIXED_BEAMFORMER_CANDIDATE', ['mono'], output_offset, len(output))}
    receipt = dict(schema=1, result='SEPARATE_DUAL_MIC_CANDIDATE_NOT_PRODUCT_QUALIFICATION',
        algorithm='fixed-fractional-delay-and-sum-v1', sampleRateHz=RATE,
        processingImplementationSha256=sha(Path(__file__).read_bytes()),
        parameters={k: config[k] for k in ['delayQ8', 'rightGainQ15', 'invertRight']},
        deviceUid=m['deviceUid'], firmwareSource=m['firmwareSource'], recordingId=m['recordingId'],
        recordingToken=m['recordingToken'], calibrationRecordingToken=c['recordingToken'],
        sourceSampleOffset=m['sourceSampleOffset'], inputSamples=count, withheldHistorySamples=withheld,
        outputSourceSampleOffset=m['sourceSampleOffset'] + withheld, outputSamples=count - withheld,
        insertedSilenceSamples=0, inputPairSha256=sha(pair_raw), outputSha256=sha(result_raw),
        calibrationSha256=sha(calibration_raw), originalProbeSha256=sha(probe_raw),
        sourceManifestSha256=sha(source_raw), captureEvidenceSha256=sha(evidence_raw),
        artifacts=artifacts, outputClippedSamples=metrics['outputClippedSamples'],
        candidateHasClipping=metrics['outputClippedSamples'] != 0,
        comparison=dict(normalization='NONE', sourceSampleOffset=output_offset,
            sampleCount=len(output), withheldHistorySamples=withheld,
            acousticTimeAlignmentQualified=False,
            note='Same capture sample range; raw channel gains and arrival times are retained. No loudness normalization, inserted silence or acoustic benefit claim.'),
        originalPairPreservedAs='original-pair.wav', sourceAssertionsCallerDeclared=True, synthetic=m['synthetic'],
        physicalNoiseReductionQualified=False, speechIntelligibilityQualified=False,
        speakerIdentityExtraction=False, automaticallyApplied=False, useCase=m['useCase'],
        warning='Independent pair retained; same-take input history omitted explicitly. A caller manifest is not proof of physical channel order, desired direction, source identity or speech/noise benefit.')
    temp = Path(tempfile.mkdtemp(prefix=destination.name + '.partial-', dir=destination.parent))
    try:
        files = {'original-pair.wav': pair_raw, 'source.json': source_raw,
            'calibration.json': calibration_raw, 'calibration-probe.log': probe_raw,
            'capture-evidence.json': evidence_raw, 'enhanced-candidate.wav': result_raw,
            'comparison-left.wav': left_raw, 'comparison-right.wav': right_raw,
            'processing.json': (json.dumps(receipt, ensure_ascii=False, indent=2) + '\n').encode('utf-8')}
        for name, raw in files.items():
            with (temp / name).open('xb') as file:
                file.write(raw); file.flush(); os.fsync(file.fileno())
        if any(p.read_bytes() != raw for p, raw in zip(paths, inputs)):
            raise ValueError('Input changed during processing; no bundle published')
        # Windows rename fails if a destination appeared meanwhile. No replace.
        temp.rename(destination)
    finally:
        if temp.exists():
            if temp.resolve().parent != destination.parent.resolve() or not temp.name.startswith(destination.name + '.partial-'):
                raise RuntimeError('Unsafe temporary cleanup target')
            shutil.rmtree(temp)
    return receipt


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for flag in ['pair', 'source', 'calibration', 'probe', 'capture-evidence', 'destination']:
        p.add_argument('--' + flag, type=Path, required=True)
    args = p.parse_args()
    try:
        result = create_bundle(args.pair, args.source, args.calibration, args.probe, args.capture_evidence, args.destination)
    except (ValueError, OSError, wave.Error, EOFError) as error:
        print(json.dumps({'result': 'REFUSED_OR_FAILED_ORIGINAL_RETAINED', 'reason': str(error)}, ensure_ascii=False))
        return 2
    print(json.dumps({k: result[k] for k in ['result', 'outputSamples', 'withheldHistorySamples', 'automaticallyApplied']}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
