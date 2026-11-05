"""Emotion ornaments derived from the retained native character components.

This changes a candidate's decoration layer only. Faces, recording art and
the default generation-58 bank retain their existing sources and geometry.
"""
from functools import lru_cache
from pathlib import Path
import hashlib

from wba_native_art_components import read_pbm

NATIVE = Path('docs/art/iterations/companion-pet-expression-v9-rig-v1/'
              'candidate/rendered-200x200/components')


def place(points, center=153, bottom=59):
    if not points:
        return frozenset()
    left = min(x for x, y in points)
    right = max(x for x, y in points)
    lower = max(y for x, y in points)
    return frozenset((x + center - (left + right) // 2, y + bottom - lower)
                     for x, y in points)


def contour(points, stroke=2):
    """Keep the source heart's silhouette, with a quieter hollow interior."""
    points = frozenset(points)
    interior = {p for p in points
                if all((p[0] + dx, p[1] + dy) in points
                       for dx in range(-stroke, stroke + 1)
                       for dy in range(-stroke, stroke + 1))}
    return points - interior


def largest_component(points):
    remaining = set(points)
    components = []
    while remaining:
        start = remaining.pop()
        group = {start}
        pending = [start]
        while pending:
            x, y = pending.pop()
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    candidate = (x + dx, y + dy)
                    if candidate in remaining:
                        remaining.remove(candidate)
                        group.add(candidate)
                        pending.append(candidate)
        components.append(group)
    return frozenset(max(components, key=len))


class EmotionOrnaments:
    def __init__(self, root, authority):
        self.root = Path(root)
        self.sources = {}
        self.sources[Path(__file__).relative_to(self.root).as_posix()] = (
            hashlib.sha256(Path(__file__).read_bytes()).hexdigest().upper())
        self.heart = contour(self.read('charm_heart'))
        self.star = self.read('charm_star')
        self.thought = self.read('charm_menu_ellipsis')
        # The original crescent is a separate connected mask within moon+Z.
        self.moon = largest_component(self.read('charm_sleep_moon_z'))
        self.sparkle = authority.components[('v22_face', 23)].pixels
        self.question = [authority.components[('v45_special_source', i)].pixels
                         for i in (512, 513, 514)]
        self.alert = [authority.components[('v45_special_source', i)].pixels
                      for i in (521, 522, 523)]
        self.sleep_z = [authority.components[('v45_special_source', i)].pixels
                        for i in (595, 596)]

    def read(self, name):
        path = self.root / NATIVE / (name + '.pbm')
        self.sources[path.relative_to(self.root).as_posix()] = (
            hashlib.sha256(path.read_bytes()).hexdigest().upper())
        return read_pbm(path)[2]

    @lru_cache(maxsize=None)
    def frame(self, family, stage):
        # Motion is a small native translation. The same resting mask is
        # retained by status updates, pointer following and blink composition.
        lift = {0: 2, 1: -1, 2: -3, 3: 0, 4: 1}[stage]
        bottom = 59 + lift
        accent = 2 if stage == 2 else 0 if stage == 0 else 1
        if family == 'calm':
            ink = place(self.sparkle, 153, 53 + lift)
        elif family == 'curious':
            ink = place(self.question[accent], 153, bottom)
        elif family == 'delighted':
            ink = place(self.star, 153, bottom)
        elif family == 'warm':
            ink = place(self.heart, 153, bottom)
        elif family == 'playful':
            ink = place(self.star, 151, bottom) | place(self.sparkle, 177, 44 + lift)
        elif family == 'sleepy':
            ink = (place(self.moon, 146, bottom)
                   | place(self.sleep_z[0], 171, 43 + lift)
                   | place(self.sleep_z[1], 184, 34 + lift))
        elif family == 'bashful':
            ink = place(self.heart, 148, 61 + lift)
        elif family == 'thoughtful':
            ink = place(self.thought, 153, 54 + lift)
        elif family == 'focused':
            ink = place(self.sparkle, 153, bottom)
        elif family == 'alert':
            ink = place(self.alert[accent], 153, bottom)
        else:
            raise ValueError('Unregistered ornament family: ' + family)
        if not ink or any(not (112 <= x <= 190 and 20 <= y <= 64) for x, y in ink):
            raise ValueError('Ornament leaves the face-free upper-right area: ' + family)
        return ink

    def evidence(self):
        return {
            'source': 'registered V22/V45 components and retained V9 charm masks',
            'faceGeometry': 'unchanged registered anatomy; decoration composed separately',
            'heartTreatment': 'original silhouette with a two-pixel hollow contour',
            'placement': 'upper-right, below the status rail and above the brows',
            'motion': 'native integer translation; response rises, then returns with the face',
            'familyCharms': {
                'calm': 'small quiet sparkle', 'curious': 'question mark',
                'delighted': 'native four-point star', 'warm': 'hollow heart',
                'playful': 'two native sparkles', 'sleepy': 'crescent and two Z components',
                'bashful': 'lower hollow heart', 'thoughtful': 'three pondering dots',
                'focused': 'single attention sparkle', 'alert': 'exclamation mark'},
            'sourceSha256': self.sources,
        }
