#!/usr/bin/env python3
"""Native menu outcome journeys; production C, explicitly simulated peripherals.

No browser, radio, real recording or device access. Returned framebuffers are
saved unchanged, so these tests establish software behavior only.
"""
import hashlib
import json
from pathlib import Path
from PIL import Image
from wba_runtime_preview import ROOT, OUT as BUILD_OUT, Runtime, build

OUT = ROOT / '.cache/wba-menu-feedback-host'


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    dll = build()
    r = Runtime(dll=dll)
    checks, frames = [], []

    def advance(ms):
        r.advance(r.now + ms)
        state = r.state()
        assert state['missingStates'] == 0, state
        return state

    def tap(x, y, settle=1100):
        r.command(dict(kind='touch', down=True, x=x, y=y))
        advance(100)
        r.command(dict(kind='touch', down=False, x=x, y=y))
        return advance(settle)

    def back():
        assert r.command(dict(kind='action', action=6))
        return advance(1500)

    def up():
        for y in (174, 145, 116, 87, 58):
            r.command(dict(kind='touch', down=True, x=100, y=y))
            advance(60)
        r.command(dict(kind='touch', down=False, x=100, y=58))
        return advance(1100)

    def capture(label):
        raw = r.raw()
        (OUT / (label + '.bin')).write_bytes(raw)
        im = Image.frombytes('1', (200, 200), raw)
        im.save(OUT / (label + '.png'))
        im.resize((400, 400), Image.Resampling.NEAREST).save(OUT / (label + '-2x.png'))
        frames.append(dict(label=label, sha256=hashlib.sha256(raw).hexdigest(), state=r.state()))

    def open_menu(locale=1):
        r.reset()
        advance(1000)
        assert r.command(dict(kind='action', action=5))
        s = advance(5400)
        assert s['surface'] == 1 and s['menuView'] == 16, s
        if locale != 1:
            assert up()['menuPage'] == 4
            assert tap(51, 153)['menuView'] == 20
            assert tap(100, 65)['menuView'] == 22
            s = tap(100, {0: 103, 2: 137}[locale])
            assert s['language'] == locale and s['menuFeedback'] == 4, s
            back()
            assert back()['menuPage'] == 4
            # A downward whole-page swipe returns to the connection tiles.
            for y in (58, 87, 116, 145, 174):
                r.command(dict(kind='touch', down=True, x=100, y=y))
                advance(60)
            r.command(dict(kind='touch', down=False, x=100, y=174))
            assert advance(1100)['menuPage'] == 0

    def recording_fixture():
        assert r.command(dict(kind='action', action=1))
        assert advance(2200)['capturing']
        assert r.command(dict(kind='action', action=2))
        s = advance(2200)
        assert s['recordingCount'] == 1 and not s['capturing'], s

    def clear_confirm():
        assert up()['menuPage'] == 4
        assert tap(51, 80)['menuView'] == 25
        assert tap(100, 137)['menuView'] == 27

    # Every locale uses native text and retains the real catalog until the
    # simulated backend actually completes. A wrong token has no effects.
    for locale, name in ((1, 'zh_cn'), (2, 'zh_tw'), (0, 'en')):
        open_menu(locale)
        recording_fixture()
        clear_confirm()
        count = r.raw()[110*25:135*25]
        r.command(dict(kind='menuBackend', mode=1, delayMs=10000))
        s = tap(145, 179)
        assert s['menuPending'] and s['visibleMenuFeedback'] == 3 and s['recordingCount'] == 1, s
        assert r.raw()[110*25:135*25] == count
        capture(name + '-clear-pending')
        token, calls, pixels = s['menuToken'], s['menuActionCalls'], r.raw()
        assert not r.command(dict(kind='menuComplete', token=token+1, result=0))
        assert r.raw() == pixels and r.state()['recordingCount'] == 1
        s = tap(145, 179)
        assert s['menuActionCalls'] == calls and s['menuPending'] and s['menuFeedback'] == 3, s
        assert not r.command(dict(kind='action', action=1))
        s = advance(1000)
        version, pixels = s['version'], r.raw()
        s = advance(2000)
        assert s['version'] == version and r.raw() == pixels, s
        assert r.command(dict(kind='menuComplete', token=token, result=0))
        s = advance(1100)
        assert not s['menuPending'] and s['visibleMenuFeedback'] == 5 and s['recordingCount'] == 0, s
        assert r.raw()[110*25:135*25] != count
        capture(name + '-clear-complete')
        assert not r.command(dict(kind='menuComplete', token=token, result=3))
        version, pixels = s['version'], r.raw()
        assert advance(3000)['version'] == version and r.raw() == pixels
        assert back()['menuFeedback'] == 0
    checks.append('three locales: pending clear preserves count, stale/duplicate results rejected, repeated action and capture blocked, completion alone clears catalog, terminal result static until navigation')

    # Persistent-save failure restores the actual pre-tap setting instead of
    # displaying an optimistic switch position. Retrying saves once.
    open_menu()
    assert tap(149, 80)['menuView'] == 18
    baseline = r.raw()
    r.command(dict(kind='menuBackend', mode=3))
    s = tap(100, 65)
    assert s['visibleMenuFeedback'] == 10 and not s['menuPending'], s
    assert r.raw()[16*25:186*25] == baseline[16*25:186*25], (s, [i//25 for i,(a,b) in enumerate(zip(r.raw(),baseline)) if a!=b][:50])
    capture('zh_cn-setting-failed')
    r.command(dict(kind='menuBackend', mode=0))
    before = s['version']
    s = tap(100, 65)
    assert s['visibleMenuFeedback'] == 4 and s['version'] == before+1, s
    assert r.raw()[:186*25] != baseline[:186*25]
    capture('zh_cn-setting-saved')
    checks.append('verified settings: failed save rolls back visible value; fresh retry saves and makes one final commit without forced processing frames')

    # A recording preference error is not a failed audio recording. Keep its
    # ready-state row intact and identify the failed save in the message strip.
    open_menu()
    assert tap(51, 80)['menuView'] == 17
    baseline = r.raw()
    r.command(dict(kind='menuBackend', mode=3))
    s = tap(100, 137)
    assert s['visibleMenuFeedback'] == 10 and s['recording'] == 0, s
    assert r.raw()[16*25:186*25] == baseline[16*25:186*25]
    capture('zh_cn-recording-setting-failed')
    checks.append('recording preference save error never changes Ready into Recording failed')

    # Deferred erase errors retain the catalog and stay visible across the
    # bounded backend retries, without redrawing unchanged progress.
    open_menu()
    recording_fixture()
    clear_confirm()
    r.command(dict(kind='menuBackend', mode=2, delayMs=2500))
    assert tap(145, 179)['menuPending']
    s = advance(2500)
    assert s['visibleMenuFeedback'] == 10 and s['recordingCount'] == 1, s
    capture('zh_cn-clear-failed')
    r.command(dict(kind='menuBackend', mode=5, delayMs=10000))
    s = tap(145, 179)
    assert s['visibleMenuFeedback'] == 11 and s['menuPending'] and s['recordingCount'] == 1, s
    capture('zh_cn-clear-retrying')
    pixels, version = r.raw(), s['version']
    assert advance(2500)['version'] == version and r.raw() == pixels
    assert back()['menuFeedback'] == 11
    assert advance(9000)['visibleMenuFeedback'] == 5
    checks.append('deferred failure and erase retry: never show success early; retry strip stays static, follows navigation, eventually completes from backend')

    # A pre-existing connection never completes a new pair operation. The
    # timeout is actionable and permits a new attempt with a distinct token.
    open_menu()
    assert r.command(dict(kind='action', action=4))
    advance(1100)
    assert tap(149, 153)['menuView'] == 19
    r.command(dict(kind='menuBackend', mode=4, delayMs=4000))
    s = tap(100, 103)
    assert s['menuPending'] and s['visibleMenuFeedback'] == 2 and s['connected'], s
    capture('zh_cn-pair-waiting')
    old = s['menuToken']
    s = advance(4000)
    assert not s['menuPending'] and s['visibleMenuFeedback'] == 12, s
    capture('zh_cn-pair-timeout')
    r.command(dict(kind='menuBackend', mode=1, delayMs=10000))
    s = tap(100, 103)
    assert s['menuPending'] and s['menuToken'] != old and s['menuFeedback'] == 2, s
    assert not r.command(dict(kind='menuComplete', token=old, result=0))
    # This represents an explicit new secure event from the simulated port,
    # not proof that a physical Bluetooth bond was persisted.
    assert r.command(dict(kind='menuComplete', token=s['menuToken'], result=0))
    assert advance(1100)['visibleMenuFeedback'] == 7
    capture('zh_cn-pair-secure-ready')
    checks.append('pair outcome: existing link is insufficient; waiting, timeout, fresh retry and exact-token secure-ready result remain distinct')

    # A result arriving while the slow panel is BUSY must be rendered after
    # its pending frame. Touches spanning either frame are ineligible.
    open_menu()
    clear_confirm()
    r.command(dict(kind='panel', latencyMs=1000, fail=True))
    r.command(dict(kind='menuBackend', mode=1, delayMs=650))
    pixels = r.raw()
    s = tap(145, 179, settle=400)
    assert s['panelPending'] and s['menuPending'] and r.raw() == pixels, s
    r.command(dict(kind='touch', down=True, x=145, y=179))
    s = advance(2200)
    calls = s['menuActionCalls']
    assert s['failures'] == 1 and not s['menuPending'] and s['menuFeedback'] == 5, s
    r.command(dict(kind='touch', down=False, x=145, y=179))
    s = advance(1800)
    assert s['menuActionCalls'] == calls and s['visibleMenuFeedback'] == 5, s
    capture('zh_cn-clear-slow-panel-recovered')
    checks.append('slow failed panel: actual completion survives failed in-flight progress frame and retry; cross-frame contact never dispatches another clear')

    sources = json.loads((BUILD_OUT / 'build-result.json').read_text())['source_sha256']
    sources[Path(__file__).relative_to(ROOT).as_posix()] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    report = dict(result='PASS_HOST_MENU_FEEDBACK_JOURNEYS', hardwareAcceptance='NOT_RUN', fullChainAcceptance='NOT_RUN',
        scope='Production C runtime/resource/renderer; explicit fake recording, settings, radio and panel callbacks',
        resourceImageSha256=hashlib.sha256(r.image).hexdigest(), sourceSha256=sources, checks=checks, frames=frames)
    (OUT / 'result.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(report['result'])
    print('\n'.join(checks))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
