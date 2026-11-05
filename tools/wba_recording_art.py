"""Recovered WB recording ink, with an explicitly reconstructed WBA timeline.

The microphone and fully entered reference wave are exact retained pixels.
The lost procedural 64-frame sequence is NOT claimed to be bit-identical.
Entry reveals 0/7/13/20 columns once; the remaining 60 frames form a smooth
periodic phase/amplitude variation of the recovered thin waveform.
"""
from functools import lru_cache
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSET = ROOT / 'docs/art/sources/comp-req-774-recording-overlay.pbm'

@lru_cache(maxsize=1)
def reference():
    data = ASSET.read_bytes()
    meta = json.loads(ASSET.with_suffix('.json').read_text())
    if hashlib.sha256(data).hexdigest() != meta['assetSha256']:
        raise ValueError('Recovered recording art changed without provenance')
    header, raw = data.split(b'\n', 2)[:2], data.split(b'\n', 2)[2]
    if header != [b'P4', b'200 200'] or len(raw) != 5000:
        raise ValueError('Recording source must be native 200x200 1bpp')
    ink = {(x,y) for y in range(156,180) for x in range(2,42)
           if raw[y*25+x//8] & (128 >> (x%8))}
    mic = {(x,y) for x,y in ink if x >= 23}
    if len(mic) != 108:
        raise ValueError('Recovered microphone no longer matches the old 108-pixel contract')
    return frozenset(mic), frozenset(ink-mic)

def pixels(index):
    if not 0 <= index < 64:
        raise ValueError('Recording timeline index out of range')
    mic, wave = reference()
    if index < 4:
        width = (0,7,13,20)[index]
        return set(mic) | {(x,y) for x,y in wave if x < 2+width}
    # Smoothly close the loop at frame 63 -> 04. Retain every pixel of the
    # original reference at its anchor; never scale or animate the microphone.
    phase = 2*math.pi*(index-3)/60
    amplitude = 1 + 0.32*math.sin(phase)
    displacement = 2*math.sin(phase)
    harmonic = 2*math.sin(2*phase)
    transformed = {(x, round(168+(y-168)*amplitude+displacement*math.sin((x-2)*math.pi/19)
                             +harmonic*math.cos((x-2)*math.pi/19)))
                   for x,y in wave}
    # Quantization must not turn the thin stroke into disconnected dots.
    stroke = set()
    previous = None
    for x in range(2,22):
        column = [y for xx,y in transformed if xx == x]
        low, high = min(column), max(column)
        if previous is not None:
            if low > previous[1]+1: low = previous[1]+1
            if high < previous[0]-1: high = previous[0]-1
        stroke.update((x,y) for y in range(low,high+1))
        previous = (low,high)
    return set(mic) | stroke

def evidence():
    mic, original = reference()
    frames = [pixels(i) for i in range(64)]
    assert frames[3] == frames[63] == set(mic|original)
    assert all(frames[i] != frames[i+1] for i in range(63))
    assert frames[63] != frames[4], 'Quantization must not stall at the loop seam'
    assert all((p & {(x,y) for x in range(23,42) for y in range(156,180)}) == mic for p in frames)
    assert all(2 <= x <= 38 and 156 <= y <= 179 for p in frames for x,y in p)
    for ink in frames[1:]:
        todo = ink-set(mic)
        visited = {todo.pop()}
        while todo:
            connected = {p for p in todo if any((p[0]+dx,p[1]+dy) in visited
                         for dx in (-1,0,1) for dy in (-1,0,1))}
            assert connected, 'Rasterized waveform contains disconnected dots'
            visited |= connected
            todo -= connected
    return {'status':'RECOVERED_KEYFRAME_RECONSTRUCTED_MOTION',
            'source':ASSET.relative_to(ROOT).as_posix(),
            'microphoneBlackPixels':len(mic), 'referenceWaveBlackPixels':len(original),
            'entryWaveColumns':[0,7,13,20], 'loop':[4,63],
            'uniqueFrames':len({frozenset(p) for p in frames}),
            'adjacentFramesDistinct':True,
            'referenceFrameExact':True, 'gen21TimelineBitIdentical':False}
