# Companion Recording Postprocess

Status: active host-side baseline

This document defines what happens after a Companion recording is pulled from
external flash. The pendant stores and syncs verified audio; the host owns
transcription, meeting minutes, search/export, and user edits.

## Product Pattern

Current AI recorder and meeting-assistant products converge on the same chain:

1. Capture audio quickly with a visible hardware/app recording state.
2. Keep a source audio asset with duration, format, and verification metadata.
3. Transcribe speech into searchable text, usually with speaker labels when the
   cloud/app can infer them.
4. Generate meeting notes: summary, key points, decisions, action items,
   questions, and templates for common meeting types.
5. Let users edit/share/export notes while retaining privacy controls for the
   original audio and derived text.

Reference surfaces checked on 2026-06-30:

- PLAUD NOTE / NotePin product pages: one-press AI voice recorder workflow,
  transcription/summaries, speaker labels, mind maps, templates, and app/web
  sync. Source: https://www.plaud.ai/products/plaud-note
- Otter AI meeting notes/help: automated summaries, highlights, comments, and
  action items around a conversation record. Source: https://otter.ai/
- Zoom AI Companion Voice Recorder / Meeting Summary docs: in-person recording
  and meeting summaries are host/cloud processing around transcript assets and
  user-controlled sharing/deletion. Source: https://support.zoom.com/
- iFLYTEK/讯飞 recorder product messaging: recorder value is fast capture plus
  transcription, translation, summary, and meeting-minutes style output. Source:
  https://www.iflyrec.com/

The implication for Companion is straightforward: do not put ASR or summary
generation on STM32WB. Keep the device responsible for reliable capture,
storage, BLE transfer, status, and privacy delete. Put transcription and minutes
generation on the phone/desktop/cloud side, where models, language packs, and
user editing can evolve independently.

## Companion Chain

The current dev-board chain is:

1. SW3 or BLE control starts/stops a microphone capture.
2. Firmware writes PCM16 mono 16 kHz audio to external QSPI flash.
3. Host reads `recording_list` and pulls bytes by byte offset.
4. Host verifies CRC32 and final SHA-256.
5. Host exports WAV.
6. Host generates a postprocess package:
   - `companion-meeting-minutes.json`
   - `companion-meeting-minutes.md`
7. Host sends delete-after-sync only after source length and SHA-256 match the
   stored recording metadata.

Current NUCLEO raw-storage capacity is deliberately a development gate, not a
one-hour product promise. PCM16 mono at 16 kHz is `32,000` bytes/second. The
firmware cap is `60 seconds`, or `1,920,000` bytes before the small metadata
header. A one-hour meeting in the same raw format needs `115,200,000` bytes
(about 109.9 MiB), which does not fit the current 16 MiB external flash part.
One-hour meetings need streaming to the host/phone, compression such as Opus or
ADPCM, or a larger storage part.

The postprocess package is deterministic when a transcript is provided. If no
transcript is available yet, the package stays in `needs_transcription` and
records the next action for the host app.

## Minutes Schema

`tools\companion_recording_postprocess.py` writes schema version 1:

```json
{
  "schema_version": 1,
  "postprocess_state": "minutes_ready",
  "source": {
    "audio": {
      "path": "sw3-button-recording-16k-mono.wav",
      "duration_s": 1.024,
      "sample_rate_hz": 16000,
      "channels": 1,
      "sha256": "..."
    },
    "recording_chain_artifact": "...",
    "recording_chain_status": "PASS",
    "recording_id": 5
  },
  "transcript": {
    "provider": "provided_text",
    "language_hint": "zh-CN",
    "text": "...",
    "segments": [
      {
        "speaker": "Billy",
        "start_s": 0.0,
        "end_s": 0.25,
        "text": "..."
      }
    ]
  },
  "summary": {
    "title": "...",
    "overview": "...",
    "bullets": ["..."],
    "decisions": [{"text": "..."}],
    "action_items": [{"id": "A01", "owner": "Billy", "text": "..."}],
    "questions": [{"text": "..."}],
    "keywords": ["Companion", "SW3"]
  },
  "wake_word": {
    "state": "detected",
    "phrases": ["你好 companion"],
    "device_control_surface": "wake_word_control/status arm/disarm/simulate_detect"
  },
  "privacy": {
    "raw_audio_delete_policy": "delete_after_sync_only_after_host_sha256_verification",
    "local_minutes_delete_policy": "host_owned; delete JSON/Markdown and cached WAV together on privacy erase"
  }
}
```

The deterministic extractor is deliberately conservative. It is a product
contract and validation scaffold, not the final AI quality layer. A later ASR
or LLM provider should fill `transcript.text` and may replace `summary`, but it
must keep `source.audio.sha256`, `recording_id`, delete policy, and user-editable
fields.

## CLI

From `Companion-Firmware`:

```powershell
python .\tools\companion_recording_postprocess.py --recording-chain .\.cache\validation\companion-button-recording-chain-<timestamp>\companion-button-recording-chain.json --transcript-file .\transcript.txt --wake-phrase "你好 companion"
```

For simulated validation:

```powershell
python .\tools\companion_recording_postprocess.py --audio-path .\some.wav --transcript-text "Billy: 待办：oai1 负责整理会议纪要。"
```

The one-command wrapper for the full host chain is:

```powershell
python .\tools\companion_recording_to_minutes.py --audio-path .\some.wav --transcript-file .\transcript.txt --wake-phrase "你好 companion"
```

It can also consume a pulled recording-chain artifact:

```powershell
python .\tools\companion_recording_to_minutes.py --recording-chain .\.cache\validation\companion-button-recording-chain-<timestamp>\companion-button-recording-chain.json --transcript-file .\transcript.txt
```

For real hardware, run the source capture under the workflow hardware lock:

```powershell
pwsh -NoProfile -File <ai-collaboration-workflow>\scripts\aiw.ps1 with-lock -Resource Companion-WB55,BLE-Companion -Purpose "Companion recording to minutes validation" -Run python .\tools\companion_recording_to_minutes.py --ble-auto --record-seconds 10 --asr-provider listener-type --wake-phrase "你好 companion"
```

`--sw3` runs the physical SW3/B3 button recording chain first, including the
Chinese desktop prompts from `tools\companion_button_recording_chain.py`.

Output defaults to:

```text
.cache/validation/companion-recording-postprocess-<timestamp>/companion-meeting-minutes.json
.cache/validation/companion-recording-postprocess-<timestamp>/companion-meeting-minutes.md
.cache/validation/companion-recording-to-minutes-<timestamp>/companion-recording-to-minutes.json
```

## ASR Provider Bridge

`tools\companion_recording_to_minutes.py --asr-provider listener-type` calls the
existing Listener-Type CLI with the embedded-audio replay entrypoint for the
recording format:

- WAV: `listener-type --submit-embedded-audio-wav-stream <wav>`
- PCM/raw: `listener-type --submit-embedded-audio-pcm16le-stream <pcm>`

The wrapper also sets `LISTENER_TYPE_DEBUG_TRANSCRIPT_FILE` so a Type build that
exports the debug transcript can feed Companion minutes directly. This is a
bridge only: Companion does not modify Listener-Type, does not make Type UI a
release dependency, and falls back to `needs_transcription` unless a transcript
is actually produced. Use `--require-transcript` when a validation run should
fail instead of producing a pending-transcription package.

## Validation

Static/simulated postprocess validation:

```powershell
python .\tools\verify_companion_postprocess.py
python .\tools\verify_companion_recording_to_minutes.py
```

This creates:

```text
docs/validation/companion-recording-postprocess-fixture.json
docs/validation/companion-recording-to-minutes-fixture.json
```

The fixture proves that a valid WAV plus Chinese transcript produces:

- `postprocess_state=minutes_ready`
- audio SHA-256/duration/sample-rate metadata
- transcript segments with speaker labels
- summary bullets
- at least one decision
- at least one action item
- at least one question
- wake-word detection from transcript text when a configured phrase appears
- Markdown export
- one-command wrapper output with `companion-recording-to-minutes.json`
- capacity math for 60 seconds and one-hour raw PCM

## Wake Word

Companion has two different wake-word layers:

1. **Current validated control surface**:
   `wake_word_control/status` lets the host arm, disarm, simulate detection,
   and observe rejection/detection counters. `tools\companion_ble_real_bench.py`
   already validates reject-while-disarmed, arm, simulate_detect, and disarm on
   the live BLE surface.
2. **Current host postprocess detection**:
   `tools\companion_recording_postprocess.py --wake-phrase "<phrase>"` marks
   a transcript segment as a wake-word hit and records it in
   `wake_word.detections`. This is useful for UI and simulated product-chain
   validation, but it happens after audio has already been recorded/transcribed.

True production wake word is a separate hardware/firmware gate. It needs a
continuous microphone path or short rolling audio buffer, a keyword-spotting
engine/model, false-accept/false-reject tests, latency limits, privacy UI, and
power measurements. The STM32WB firmware must not claim real always-on wake
until those pass.

## What The Host Should Do With Audio

The host pipeline should be:

1. Keep the raw WAV in a local recording cache while processing.
2. Attach recording metadata: `recording_id`, duration, sample format, byte
   length, CRC32, SHA-256, BLE source artifact, and capture time if available.
3. Run transcription. The current tool accepts provided text; a later provider
   can be local ASR, phone OS dictation, OpenAI, or another cloud ASR.
4. Generate minutes JSON and Markdown.
5. Present a user-editable view before sharing/export.
6. After successful sync and user policy approval, send delete-after-sync to
   the pendant with verified length and SHA-256.
7. On privacy erase, delete the local WAV, transcript, JSON, Markdown, and any
   provider-side cached transcript if that provider was used.

## Firmware Boundary

Firmware should continue to expose:

- recording list and byte-offset chunk pull
- meeting start/stop status
- transfer/delete/diagnostics status
- OTA blockers while recording or transfer is active

Firmware should not expose:

- transcript text generated on-device
- AI summary generated on-device
- unbounded raw log or audio dumps
- delete operations that do not include verified length and SHA-256

This keeps the first pendant practical: reliable audio capture and privacy
state on the device, rich notes on the host.
