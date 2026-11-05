#!/usr/bin/env python3
"""Calibrate a saved finite pair and create a separate comparison candidate.

Pure file processing. Requires the exact known-source setup retained BEFORE
capture, independent DMP1 original, and its completed capture evidence. This
does not turn an unlabelled environment take into a calibration, enable a
device, or qualify noise reduction. Synthetic fixtures remain synthetic.
"""
from __future__ import annotations
import argparse
from array import array
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile

import calibrate_wba_dual_mic as estimator
import decode_wba_dual_mic_stream as decoder
import process_wba_dual_mic_pair as processor
import dual_mic_calibration_stability as stability


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def validate_setup(raw, uid, firmware_source):
    s = decoder.unique_json(raw)
    decoder.require(s.get('schema') == 'companion.dual-mic-known-source.v1', 'Known-source setup schema required')
    decoder.require(re.fullmatch(r'[0-9a-f]{24}', uid) and re.fullmatch(r'[0-9a-f]{40}', firmware_source), 'Explicit image identity required')
    decoder.require(s.get('deviceUid') == uid and s.get('firmwareSource') == firmware_source, 'Setup/image identity mismatch')
    decoder.require(s.get('knownSingleBroadbandSourceConfirmed') is True, 'Known single broadband source was not confirmed')
    decoder.require(s.get('useCase') == 'FRONT_CLOSE_TALK_CANDIDATE', 'Do not steer general/meeting capture implicitly')
    description = s.get('sourceDescription')
    decoder.require(isinstance(description, str) and 1 <= len(description.strip()) <= 300, 'Actual source/setup description required')
    bound = s.get('maxDelaySamples')
    decoder.require(type(bound) in (int, float) and math.isfinite(bound) and 0 < bound <= 2.5, 'Explicit current-geometry delay bound required')
    return s


def probe_from_pcm(pcm, token):
    """Reproduce the finite production C probe, including its six end samples.

    For each center t=3..N-4, correlate L[t] and R[t+lag]. The initial/final
    three frames are real source samples, excluded from sums rather than padded.
    All original samples still participate in the clipping checks.
    """
    samples = array('h', pcm)
    if sys.byteorder != 'little':
        samples.byteswap()
    decoder.require(len(samples) % 2 == 0, 'Incomplete synchronous PCM frame')
    n = len(samples) // 2
    decoder.require(8006 <= n <= estimator.MAX_SAMPLES, 'Need a finite 0.5..2 second calibration pair')
    left, right = samples[::2], samples[1::2]
    centered = left[3:n-3]
    def wide(name, value):
        value &= (1 << 64) - 1
        hi = value >> 32
        if hi >= 1 << 31:
            hi -= 1 << 32
        return f'{name}_hi={hi} {name}_lo={value & 0xffffffff}'
    header = f'DMIC1 schema=1 token={token} samples={n} count={n-6} invalid=0 clip_l={sum(x in (-32768,32767) for x in left)} clip_r={sum(x in (-32768,32767) for x in right)} '
    lines = [header + wide('ls',sum(centered)) + ' ' + wide('lss',sum(x*x for x in centered))]
    for lag in estimator.LAGS:
        r = right[3+lag:n-3+lag]
        lines.append(f'DMIC1 lag={lag} ' + wide('rs',sum(r)) + ' ' + wide('rss',sum(x*x for x in r)) + ' ' + wide('cross',sum(l*v for l,v in zip(centered,r))))
    return ('\n'.join(lines) + '\n').encode('ascii')


def require_temporal_stability(pcm, token, config, max_delay_samples):
    """Reject an apparent fixed trim supported only by a shared onset.

    Check two disjoint source windows with the unchanged production probe and
    its existing energy/coherence/peak criteria. Retain the entire original and
    the full-pair statistics; no warmup samples are deleted or recalibrated.
    The agreement bounds are candidate admission limits, not noise-reduction
    or speech-fidelity qualification.
    """
    n = len(pcm) // 4
    midpoint = n // 2
    decoder.require(midpoint >= stability.MIN_WINDOW_FRAMES and n-midpoint >= stability.MIN_WINDOW_FRAMES,
                    'Temporal calibration needs two independent windows of at least8006 frames')
    windows = []
    for first, last in ((0, midpoint), (midpoint, n)):
        raw = probe_from_pcm(pcm[first*4:last*4], token)
        try:
            candidate = estimator.estimate(estimator.parse_probe(raw.decode('ascii'), token),
                known_single_source=True, max_delay_samples=max_delay_samples)
        except ValueError as error:
            raise ValueError(f'Temporal calibration window {first}..{last} refused: {error}') from error
        windows.append(dict(firstSample=first, endSample=last, probeLogSha256=sha(raw),
            delayQ8=candidate['delayQ8'], rightGainQ15=candidate['rightGainQ15'],
            invertRight=candidate['invertRight']))
    estimates = [config, *windows]
    delay_spread = max(x['delayQ8'] for x in estimates)-min(x['delayQ8'] for x in estimates)
    gain_spread_db = 20*math.log10(max(x['rightGainQ15'] for x in estimates)/
                                 min(x['rightGainQ15'] for x in estimates))
    proof = dict(schema=1, result='TWO_DISJOINT_WINDOWS_AGREE_WITH_FULL_PAIR',
        windows=windows, maximumDelaySpreadQ8=stability.MAX_DELAY_SPREAD_Q8,
        maximumGainSpreadDb=stability.MAX_GAIN_SPREAD_DB,
        delaySpreadQ8=delay_spread, gainSpreadDb=gain_spread_db,
        sourceSamplesDiscarded=0, physicalNoiseReductionQualified=False)
    stability.validate(dict(config, temporalStability=proof))
    return proof


def create_bundle(stream, evidence_path, setup_path, destination):
    destination = destination.absolute()
    decoder.require(not destination.exists() and not destination.is_symlink(), 'Destination already exists')
    decoder.require(destination.parent.is_dir(), 'Destination parent must exist')
    paths = [stream, evidence_path, setup_path]
    decoder.require(stream.stat().st_size <= decoder.MAX_BYTES and all(p.stat().st_size <= 2_000_000 for p in paths[1:]), 'Inputs exceed finite limits')
    raw, evidence_raw, setup_raw = inputs = [p.read_bytes() for p in paths]
    pcm, identity = decoder.decode(raw)
    evidence = decoder.unique_json(evidence_raw)
    decoder.validate_receipt(evidence, raw, identity)
    setup = validate_setup(setup_raw, identity['deviceUid'], identity['firmwareSource'])
    decoder.require(evidence.get('knownFrontSourceConfirmed') is True and evidence.get('knownSourceSetupSha256') == sha(setup_raw), 'Setup was not bound at capture; retain unlabelled original without calibration')
    decoder.require(not identity['clippedLeft'] and not identity['clippedRight'], 'Clipped source cannot be calibrated')
    probe_raw = probe_from_pcm(pcm, identity['recordingToken'])
    probe = estimator.parse_probe(probe_raw.decode('ascii'), identity['recordingToken'])
    config = estimator.estimate(probe, known_single_source=True, max_delay_samples=setup['maxDelaySamples'])
    config['temporalStability'] = require_temporal_stability(pcm, identity['recordingToken'],
        config, setup['maxDelaySamples'])
    config.update(deviceUid=identity['deviceUid'], firmwareSource=identity['firmwareSource'], recordingToken=identity['recordingToken'],
        probeLogSha256=sha(probe_raw), knownSingleSourceCallerDeclared=True, identityCallerDeclared=True,
        sourceStreamSha256=sha(raw), knownSourceSetupSha256=sha(setup_raw), synthetic=identity['synthetic'])
    temporary = Path(tempfile.mkdtemp(prefix=destination.name + '.partial-', dir=destination.parent))
    try:
        decoder.create_bundle(stream, evidence_path, temporary/'independent-source', use_case=setup['useCase'])
        files = {'known-source-setup.json':setup_raw, 'pair-derived-probe.log':probe_raw,
            'calibration.json':(json.dumps(config,indent=2)+'\n').encode()}
        for name, data in files.items():
            with (temporary/name).open('xb') as file:
                file.write(data); file.flush(); os.fsync(file.fileno())
        independent = temporary/'independent-source'
        processed = processor.create_bundle(independent/'original-pair.wav', independent/'source.json',
            temporary/'calibration.json', temporary/'pair-derived-probe.log', independent/'capture-evidence.json', temporary/'comparison')
        result = dict(result='PAIR_CALIBRATION_AND_SEPARATE_CANDIDATE_NOT_PHYSICAL_QUALIFICATION',
            deviceUid=identity['deviceUid'], firmwareSource=identity['firmwareSource'], recordingToken=identity['recordingToken'],
            sourceStreamSha256=sha(raw), captureEvidenceSha256=sha(evidence_raw), knownSourceSetupSha256=sha(setup_raw),
            originalSourceRetained=True, synthetic=identity['synthetic'], parameters=processed['parameters'],
            inputSamples=identity['sampleCount'], outputSamples=processed['outputSamples'],
            processingManifest='comparison/processing.json',
            processingManifestSha256=sha((temporary/'comparison/processing.json').read_bytes()),
            outputClippedSamples=processed['outputClippedSamples'],
            candidateHasClipping=processed['candidateHasClipping'],
            automaticallyApplied=False, physicalNoiseReductionQualified=False, speechIntelligibilityQualified=False,
            knownSourceIsCallerDeclaration=True, speakerIdentityExtraction=False,
            implementations={m.__name__:sha(Path(m.__file__).read_bytes()) for m in [estimator,decoder,processor]},
            orchestrationSha256=sha(Path(__file__).read_bytes()),
            next='Compare desired speech and interference from controlled same-take inputs; correlation and generated audio do not qualify the product.')
        (temporary/'result.json').write_text(json.dumps(result,indent=2)+'\n')
        decoder.require(all(p.read_bytes() == data for p,data in zip(paths,inputs)), 'Input changed during calibration; no bundle published')
        temporary.rename(destination)
    finally:
        if temporary.exists():
            decoder.require(temporary.resolve().parent == destination.parent.resolve() and temporary.name.startswith(destination.name+'.partial-'), 'Unsafe temporary cleanup')
            shutil.rmtree(temporary)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('stream','capture-evidence','known-source-setup','destination'):
        parser.add_argument('--'+name,type=Path,required=True)
    args = parser.parse_args()
    try:
        result = create_bundle(args.stream,args.capture_evidence,args.known_source_setup,args.destination)
    except (ValueError,OSError,EOFError) as error:
        print(json.dumps(dict(result='REFUSED_OR_FAILED_ORIGINAL_RETAINED',reason=str(error))))
        return 2
    print(json.dumps(result))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
