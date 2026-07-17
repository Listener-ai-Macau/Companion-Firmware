# SSD1681 Vendor Waveform Freeze

## Status

`FROZEN_WAITING_FOR_VENDOR_CWF1`

The current target is the Good Display `GDEY0154D67-T03` with SSD1681-class
controller behavior. No new fast/partial/maintenance waveform experiment is
authorized until the panel supplier provides a matching vendor package.

## Fail-Closed Rule

Do not use generic LUT data, a nearby panel's LUT, a web example, guessed
bytes, or a temperature assumption as a waveform candidate. No panel command,
Flash write, or firmware image is produced by this rule.

## Required Vendor Package

The candidate package uses the `CWF1` manifest format and must include:

1. Exact panel model `GDEY0154D67-T03`, controller and panel batch/lot scope.
2. Temperature range and test condition, plus the supplier's intended
   temperature compensation rule.
3. Complete waveform payload and byte count for the stated update profile.
4. CRC/SHA-256 of the received payload, supplier/source identity, document
   revision and receipt date.
5. The supplier's initialization/update-control sequence that binds that exact
   waveform to the stated panel and temperature range.

The future CWF1 parser must reject a package unless model, batch/lot,
temperature range, payload CRC, source identity and document revision all
match the approved request. A parser validation is not a panel update; a
validated candidate may only be used later in one short hardware-locked
experiment with BUSY, visible-frame and residual evidence.

The supplier-facing Chinese request and intake checklist are in
`docs/companion_ssd1681_vendor_waveform_request.md`. The supplier may send
original source, an archive, a binary waveform file or a complete command
table; CWF1 is an internal intake format, not a required supplier file format.

## Latest Supplier Response

The owner supplied a 2026-07-17 chat screenshot in which the supplier states
that the waveform is internal and that partial refresh uses a room-temperature
waveform already optimized for that batch. This rules out assuming that a
separate external `0x32` payload will be sent, but it does not identify the
numeric temperature range, internal-profile selection sequence, lot scope,
partial-cycle cleanup limit or residue criterion. The freeze therefore remains
in force. The recorded intake and focused follow-up questions are in
`docs/validation/companion-ssd1681-vendor-response-intake-20260717.json`.

## Temperature Boundary

There is currently no approved panel-temperature measurement or OTP read in
the normal product path. "Room temperature" is only an operator-recorded test
condition, not a claim that the panel knows its temperature. Temperature and
OTP diagnostics remain off by default and must not affect normal rendering.

## Exit Criteria

The freeze ends only after the matching CWF1 package is archived, parser
validation passes, and the owner explicitly begins the bounded hardware
acceptance session. Residual acceptability takes priority over the 0.5 s
refresh aspiration.
