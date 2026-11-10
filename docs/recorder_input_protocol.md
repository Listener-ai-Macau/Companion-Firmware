# Recorder and desktop input (CIN1)

This uses the existing encrypted `8f7a4001-7b7d-4f3d-9d6f-6c2d1b7c0000`
settings characteristic. Legacy settings and PMP1 are unchanged. There are no new
GATT attributes. Clients opt in by sending CIN1; legacy clients receive no CIN1
notifications. All integers are little endian; CRC is the existing IEEE CRC32.

The 36-byte request is `CIN1`, schema1 at4, operation at5 (0=query,1=set mode),
mode at6, options at7, nonzero request nonce u32 at8, device UID12 at12,
format epoch u64 at24, CRC32 of bytes0..31 at32. Query requires mode/options0.
Wrong identity/CRC/schema/size is rejected without changing state.

Modes: 0=recorder,1=desktop dictation,2=presentation. Optional gestures:
bit0=flick to submit, bit1=shake to cancel, bit2=double tap to undo. Default
recorder mode has no optional gestures. Mode change is refused while recording,
preparing, saving, holding a key or updating. Mode is volatile, not a preference.

The 64-byte reply is:

| Offset | Value |
|---|---|
|0|`CIN1`|
|4|schema1|
|5|result:0 accepted,1 busy,2 invalid mode/options|
|6|actual mode|
|7|flags: bit0 key held, bit1 microphone running, bit2 recording owned|
|8|u32 request nonce;0 means unsolicited live event/status|
|12|u32 device event sequence; nonzero, wraps skipping0|
|16|u32 event device tick in milliseconds|
|20|u16 event bits|
|22|actual optional gesture bits|
|23|existing `comp_capture_feedback_t.state` (preparing/recording/saving/saved/error...)|
|24|u32 current recording token|
|28|u64 logical session ID|
|36|u32 durable bookmark sequence if an engine exists|
|40|device UID12|
|52|u64 format epoch|
|60|CRC32 of bytes0..59|

Event bits:1 start accepted,2 stop requested,4 mark requested,8 undo last
dictation,16 cancel current dictation,32 submit with Return,64 next slide,
128 previous slide,256 motion wake. Several pending bits can be coalesced.
Capture feedback and normal CMS3, not a START event alone, establish actual
sampling and durable completion. A bookmark request is pending until the
durable sequence advances. Hosts deduplicate events by device/epoch/sequence;
query/set replies establish a baseline and never execute historical shortcuts.

Recorder: a qualified release toggles recording; holding has no action. Double
tap uses the existing durable audio timeline. Idle motion wakes the core without
starting audio. Desktop: qualified DOWN requests capture, UP stops the same
token. Releasing during preparation uses normal cancellation. Optional shake
stops once and tells the host to discard pending text; it does not erase other
recordings. Optional flick stops once and requests Return only after that
dictation's final text is inserted. Text failure never sends Return alone.

Disconnect never stops a held dictation. Physical release still ends and saves
it locally, then recorder mode returns. New connections do not inherit a desktop
mode. Desktop undo is scoped to the host's last insertion and original target;
it must not issue a blind global Undo. Presentation uses verified mounting axes;
held left/right tilt emits previous/next. Air pointer is not implemented here.

Audio remains the existing CRV2/COP1/CMC3 path. CIN1 does not introduce a second
microphone, codec, audio format or raw six-axis stream. Existing 9001 IMU raw
status remains unchanged. Enclosure sensitivity, first-word capture, real Mac
insertion, power and physical gestures require separate actual-device evidence.
