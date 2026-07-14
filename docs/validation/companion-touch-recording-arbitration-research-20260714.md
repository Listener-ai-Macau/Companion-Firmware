# Companion Touch Recording Arbitration Research

Date: 2026-07-14

Status: implementation candidate complete; WB55 reset-bounded rerun pending.

## Failure evidence

The third focused recording run captured a real FT6336 sequence in which a
wake contact was followed by a new `DOWN`, release, and a later second tap. The
first tap immediately entered `daily_reaction` and started an e-paper refresh.
The second tap therefore arrived too late to form the intended double tap.
The operator selected `通过`, but the machine report was
`NO_GO_INCOMPLETE_TOUCH_WAKE_EVIDENCE`; recording never started in that run.
Earlier runs separately proved SAI clock restoration, successful DMA, and
changing PCM, but did not prove the second double tap, stop, or store.

Human selection is retained as observation evidence. It cannot convert an
incomplete machine trace into PASS.

## Mature implementation references

- Android AOSP `GestureDetector` schedules the single-tap confirmation after
  the double-tap timeout and cancels/reclassifies it when the second tap is
  recognized. This is the direct behavioral reference for provisional first
  taps: <https://android.googlesource.com/platform/frameworks/base.git/+/master/core/java/android/view/GestureDetector.java>
- AndroidX `GestureTrackerTest` explicitly separates `FIRST_TAP`, confirmed
  `SINGLE_TAP`, and `DOUBLE_TAP`, with the single tap emitted only after its
  timeout: <https://android.googlesource.com/platform/frameworks/support/+/0624f640fd3a47edfcf8a070f609d278fb5eb41b/pdf/pdf-viewer/src/test/kotlin/androidx/pdf/view/GestureTrackerTest.kt>
- Zephyr exposes double-tap delay as input configuration rather than coupling
  it to an application action: <https://docs.zephyrproject.org/latest/build/dts/api/bindings/input/zephyr%2Cinput-double-tap.html>
- Espressif's official FT5x06 component treats the controller as a regularly
  read input device whose state is stored in RAM, supporting a clean boundary
  between acquisition and gesture policy: <https://components.espressif.com/components/espressif/esp_lcd_touch_ft5x06/versions/0.9.0?language=en>
- Good Display rates GDEY0154D67 partial update at about 0.26 s and full update
  at about 2 s. E-paper refresh must therefore remain downstream of gesture
  commitment; it cannot be allowed to block first-tap arbitration:
  <https://kr.good-display.com/product/455.html?productCateId=91>

## Adopted contract

1. Acquisition reads FT6336 samples and timestamps; it performs no product
   action.
2. Portable gesture logic owns contact lifecycle, missed-release re-contact,
   tap, double tap, swipe, hold, and long press.
3. `touch_tap_arbiter` keeps the first tap provisional through the configured
   double-tap window. Active contact or detector-pending state also prevents
   early confirmation.
4. A double tap cancels the provisional single tap before recording starts.
5. Display and recording work run only from committed actions. A provisional
   tap cannot synchronously request an SSD1681 refresh.
6. WB55 and future WBA55/WBA65 share acquisition-independent gesture and
   arbitration code; only I2C/EXTI, timer, SAI/PDM, storage, and display target
   adapters change.

## Regression evidence

The embedded self-test replays the captured coordinates and timing:
`CONTACT(0,159) -> recontact DOWN(129,81) -> TAP -> release(121,83) -> TAP ->
second tap(109,88) -> DOUBLE_TAP`. It proves the provisional single-tap event is
cancelled and never reaches the display action. A second test proves an actual
single tap is emitted only after the timeout and after contact/detector pending
state clears.

The recording log parser requires all of the following before PASS:

- two `daily_double_tap_recording` actions;
- recording start;
- SAI clock restored and enabled;
- DMA start successful;
- at least two valid PCM blocks with different CRCs and a nonzero sample span;
- no microphone timeout;
- recording stop;
- external-Flash `user_store result=1`;
- operator selection `通过` in the matching canonical review artifact.

Validation commands:

```powershell
python tools/verify_touch_ft6336.py
python tools/verify_wb55_touch_wake_log.py --self-test --scope double-tap-recording
pwsh -NoProfile -File tools/build_nucleo_bringup.ps1 -EpaperSsd1681Bringup -EpaperMenu 1 -Force
pwsh -NoProfile -File tools/build_nucleo_bringup.ps1 -EpaperSsd1681Bringup -EpaperMenu 1 -EpaperSsd1681VerboseTrace -Force
```

No physical acceptance is claimed by this document. The next hardware action
is one machine-first boot capture followed by one focused recording review only
after the startup arbiter self-test passes.
