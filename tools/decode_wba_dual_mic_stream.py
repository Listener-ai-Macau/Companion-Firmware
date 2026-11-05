#!/usr/bin/env python3
"""Export a complete finite DMP1 source as independent stereo PCM.

File-only decoder, not a hardware capture/transport command. No device, cloud,
automatic enhancement or source authentication. In-band CRC and an external
capture receipt detect inconsistency, not forgery. Board transport must still
bind actual image identity, capture counters, storage ownership and completion.
"""
from __future__ import annotations
import argparse
from array import array
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import struct
import sys
import tempfile
import wave
import zlib

RATE = 16000
BLOCK = 160
MAX_BLOCKS = 6000
MAX_BYTES = 80 + 664 * MAX_BLOCKS + 48
FAULT_COUNTERS = ('missingDmaBlocks', 'reorderedDmaBlocks', 'invalidDmaBlocks',
    'rejectedPcmFrames', 'staleDmaHalves', 'eventQueueOverflows', 'errorIrqs', 'budgetViolations')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def unique_json(raw):
    def unique(items):
        result = {}
        for key, value in items:
            require(key not in result, 'Duplicate capture receipt field')
            result[key] = value
        return result
    result = json.loads(raw, object_pairs_hook=unique)
    require(isinstance(result, dict), 'Capture receipt must be an object')
    return result


def u16(raw, offset):
    return struct.unpack_from('<H', raw, offset)[0]


def u32(raw, offset):
    return struct.unpack_from('<I', raw, offset)[0]


def u64(raw, offset):
    return struct.unpack_from('<Q', raw, offset)[0]


def crc_packet(raw):
    require(len(raw) >= 4 and zlib.crc32(raw[:-4]) == u32(raw, len(raw) - 4), 'Packet CRC mismatch')


def decode(raw):
    require(80 + 664 + 48 <= len(raw) <= MAX_BYTES, 'Incomplete or oversized finite pair stream')
    h = raw[:80]
    crc_packet(h)
    require(h[:4] == b'DMP1' and (u16(h, 4), u16(h, 6)) == (1, 80), 'Unsupported pair stream')
    require((u32(h, 8), u16(h, 12), h[14], h[15]) == (RATE, BLOCK, 2, 2), 'Unsupported PCM geometry')
    require(u32(h, 68) in (0, 1) and u32(h, 72) == 0, 'Unknown flags or reserved bytes')
    require(any(h[16:28]) and any(h[28:48]) and u32(h, 48) and u32(h, 52), 'Missing source identity')
    limit, first = u32(h, 64), u64(h, 56)
    require(1 <= limit <= MAX_BLOCKS and first <= (1 << 53) - limit * BLOCK, 'Invalid finite source range')
    pcm = bytearray()
    clips = [0, 0]
    count, cursor, pcm_crc = 0, 80, 0
    while raw[cursor:cursor + 4] == b'DMPF':
        require(count < limit and cursor + 664 <= len(raw), 'Truncated/overlong pair block')
        p = raw[cursor:cursor + 664]
        crc_packet(p)
        require(u32(p, 4) == count and u64(p, 8) == first + count * BLOCK,
            'Missing, repeated, reordered or discontinuous source block')
        require(u16(p, 16) == BLOCK and u16(p, 18) == 0, 'Invalid pair block shape')
        data = p[20:660]
        samples = array('h', data)
        if sys.byteorder != 'little':
            samples.byteswap()
        for i, value in enumerate(samples):
            if value in (-32768, 32767):
                clips[i % 2] += 1
        pcm.extend(data)
        pcm_crc = zlib.crc32(data, pcm_crc)
        count += 1
        cursor += 664
    require(count > 0 and cursor + 48 == len(raw), 'Missing terminal packet or extra trailing data')
    e = raw[cursor:]
    crc_packet(e)
    require(e[:4] == b'DMPE' and u32(e, 4) == count and u64(e, 8) == count * BLOCK, 'Terminal source count mismatch')
    require(u32(e, 16) == 0 and u32(e, 32) == 0, 'Producer marked an incomplete or invalid capture')
    require([u32(e, 20), u32(e, 24)] == clips and u32(e, 28) == pcm_crc, 'Terminal PCM summary mismatch')
    require(u32(e, 36) == u32(h, 76) and u32(e, 40) == 0, 'Terminal header binding mismatch')
    identity = dict(deviceUid=h[16:28].hex(), firmwareSource=h[28:48].hex(),
        recordingToken=u32(h, 48), recordingId=u32(h, 52), sourceSampleOffset=first,
        sampleRateHz=RATE, sampleCount=count * BLOCK, blockCount=count,
        clippedLeft=clips[0], clippedRight=clips[1], synthetic=bool(u32(h, 68)))
    return bytes(pcm), identity


def validate_receipt(evidence, raw, identity):
    require(evidence.get('schema') == 'companion.dual-mic-pair-capture.v1', 'Capture receipt schema required')
    require(evidence.get('streamSha256') == sha(raw), 'Capture receipt does not bind these original bytes')
    for key, value in identity.items():
        require(type(evidence.get(key)) is type(value) and evidence[key] == value, 'Capture identity mismatch: ' + key)
    require(evidence.get('processedChannelMask') == 3 and evidence.get('sourcePositionFromCapture') is True,
        'Actual independent source position and both filtered channels required')
    kind = 'SOFTWARE_FIXTURE' if identity['synthetic'] else 'BOARD_SAI_PDM'
    require(evidence.get('captureKind') == kind, 'Synthetic/physical origin mismatch')
    require(evidence.get('processingStage') == 'POST_CHANNEL_GAIN_DC_PRE_BEAMFORM_PCM16', 'Capture stage required')
    counters = evidence.get('captureFaultCounters')
    require(isinstance(counters, dict) and all(type(counters.get(k)) is int and counters[k] == 0 for k in FAULT_COUNTERS),
        'Incomplete or failed capture counters')
    require(evidence.get('completed') is True, 'Capture completion was not confirmed')


def create_bundle(stream: Path, evidence_path: Path, destination: Path, *, use_case: str):
    require(use_case in ('GENERAL_DUAL_MIC_CAPTURE', 'FRONT_CLOSE_TALK_CANDIDATE', 'ALL_PARTICIPANT_MEETING'), 'Unknown use case')
    destination = destination.absolute()
    require(not destination.exists() and not destination.is_symlink(), 'Destination already exists')
    require(destination.parent.is_dir(), 'Destination parent must exist')
    require(stream.stat().st_size <= MAX_BYTES and evidence_path.stat().st_size <= 2_000_000, 'Inputs exceed finite limits')
    raw, evidence_raw = stream.read_bytes(), evidence_path.read_bytes()
    pcm, identity = decode(raw)
    validate_receipt(unique_json(evidence_raw), raw, identity)
    out = io.BytesIO()
    with wave.open(out, 'wb') as wav:
        wav.setnchannels(2); wav.setsampwidth(2); wav.setframerate(RATE); wav.writeframes(pcm)
    wav_raw = out.getvalue()
    clipped = bool(identity['clippedLeft'] or identity['clippedRight'])
    source = dict(schema=1, sourceKind='SYNCHRONOUS_DUAL_PCM', channels=['left', 'right'],
        processingStage='POST_CHANNEL_GAIN_DC_PRE_BEAMFORM_PCM16_' + ('CLIPPED' if clipped else 'NO_CLIPPING'),
        pairWavSha256=sha(wav_raw), captureEvidenceSha256=sha(evidence_raw),
        continuityVerified=True, useCase=use_case, **identity)
    receipt = dict(result='DECODED_INDEPENDENT_PAIR_CANDIDATE_NOT_ACOUSTIC_QUALIFICATION',
        streamSha256=sha(raw), captureEvidenceSha256=sha(evidence_raw), pairWavSha256=sha(wav_raw),
        decoderSha256=sha(Path(__file__).read_bytes()), synthetic=identity['synthetic'],
        inputPairOriginalRetained=True, physicalNoiseReductionQualified=False, automaticallyApplied=False,
        insertedSilenceSamples=0, discardedSamples=0, clipped=clipped,
        sourceAssertionsCallerDeclared=True, authenticatedBoardTransport=False)
    temporary = Path(tempfile.mkdtemp(prefix=destination.name + '.partial-', dir=destination.parent))
    try:
        files = {'original-pair.dmp': raw, 'capture-evidence.json': evidence_raw,
            'original-pair.wav': wav_raw, 'source.json': (json.dumps(source, indent=2) + '\n').encode(),
            'decode.json': (json.dumps(receipt, indent=2) + '\n').encode()}
        for name, data in files.items():
            with (temporary / name).open('xb') as file:
                file.write(data); file.flush(); os.fsync(file.fileno())
        require(stream.read_bytes() == raw and evidence_path.read_bytes() == evidence_raw, 'Input changed during export')
        temporary.rename(destination)
    finally:
        if temporary.exists():
            require(temporary.resolve().parent == destination.parent.resolve() and temporary.name.startswith(destination.name + '.partial-'), 'Unsafe cleanup target')
            shutil.rmtree(temporary)
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ('stream', 'capture-evidence', 'destination'):
        parser.add_argument('--' + flag, type=Path, required=True)
    parser.add_argument('--use-case', choices=['GENERAL_DUAL_MIC_CAPTURE', 'FRONT_CLOSE_TALK_CANDIDATE', 'ALL_PARTICIPANT_MEETING'],
        default='GENERAL_DUAL_MIC_CAPTURE')
    args = parser.parse_args()
    try:
        result = create_bundle(args.stream, args.capture_evidence, args.destination, use_case=args.use_case)
    except (ValueError, OSError, EOFError, struct.error, wave.Error) as error:
        print(json.dumps(dict(result='REFUSED_OR_FAILED_ORIGINAL_RETAINED', reason=str(error))))
        return 2
    print(json.dumps(result))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
