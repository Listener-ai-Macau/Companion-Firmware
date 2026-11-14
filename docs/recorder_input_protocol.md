# Recorder and desktop input (CIN1)

This uses the existing encrypted `8f7a4001-7b7d-4f3d-9d6f-6c2d1b7c0000`
settings characteristic. Legacy settings and PMP1 are unchanged. There are no new
GATT attributes. Clients opt in by sending CIN1; legacy clients receive no CIN1
notifications. All integers are little endian; CRC is the existing IEEE CRC32.

The 36-byte request is `CIN1`, schema1 at4, operation at5 (0=query,1=set mode,2=pointer ACK),
mode at6, options at7, nonzero request nonce u32 at8, device UID12 at12,
format epoch u64 at24, CRC32 of bytes0..31 at32. Query requires mode/options0.
Wrong identity/CRC/schema/size is rejected without changing state.

Modes: 0=recorder,1=desktop dictation,2=presentation,3=air pointer. Optional gestures:
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
|7|flags: bit0 key held, bit1 microphone running, bit2 recording owned, bit3 latest mark pending, bit4 latest mark durably confirmed|
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
held left/right tilt emits previous/next. Pointer mode never starts the microphone;
the existing button level is sent to its host for click/drag interpretation.

Pointer mode alone uses104Hz gyro/417Hz hardware-tap accel, polled near100Hz.
It reuses upstream Fusion AHRS/bias on the MCU at61.44MHz and publishes each
fresh sample on the same encrypted4001 subscription. Recorder gyro remains52Hz.
The existing bulk interval hint is shared and restored on exit. Legacy9001 remains the1Hz diagnostic interface. CIM1 is32 bytes:
magic0..3, schema1(raw),2(legacy fused) or3(device calibrated) at4, mode3 at5, held bit0 and schema3 calibrated bit1 at6,
mod256 hardware-double-tap serial at7, u32 sequence at8,
u32 original sensor milliseconds at12, three i16 acceleration mg at16, three i16
angular rates in0.01deg/s at22, IEEE CRC32 at28. The peer UID/epoch are already
validated by the CIN1 handshake. Schema2 substitutes fused gravity in mg for
raw acceleration and bias-corrected gyro rates; hosts must not fuse it again.
Schema3 sends unit gravity in signed Q14, corrected gyro and an explicit device-ready bit; hosts wait for the measured stationary interval and must not learn a second fixed bias. It retains the same32B size.
The first tap serial establishes a baseline; advance1 means one click. Repeats,
paused/stale events, held-button taps and multi-event loss are never replayed. No buffered old samples are replayed after loss.
Disconnect returns mode0 and the existing low-power policy. Clients must stop
pointer output on stale samples and release an owned drag. The optional compact
CPU observer can measure pointer-only scopes; these are not recording CPU results.

Audio remains the existing CRV2/COP1/CMC3 path. CIN1 does not introduce a second
microphone, codec, audio format or raw six-axis stream. Existing 9001 IMU raw
status remains unchanged. Enclosure sensitivity, first-word capture, real Mac
insertion, power and physical gestures require separate actual-device evidence.


### Reliable pointer ACK

In opted-in pointer mode, operation2 uses the nonzero event sequence at8 as
the ACK; mode/options at6/7 must be0 and UID/epoch/CRC remain required. It removes
only the exact queued head, never a later gesture or microphone state. An old
duplicate ACK is idempotent. Query/mode replies are still notified normally.

Successful pointer ACKs update the cached readable CIN status but do not emit an
ACK-of-ACK notification. Hosts do not await that echo: the next queued physical
edge is notified separately with request0, and can be acknowledged in turn.
Invalid/unsupported ACK operations retain their error reply. ATT write success
alone is not evidence that the application applied an ACK: a genuinely new
device retry after a completed write may still need another ACK. Client-side
coalescing is limited to duplicates already received during that same in-flight
ACK, and an older callback must not replace a newer pending sequence.
