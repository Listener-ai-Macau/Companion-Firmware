# Reused generated contracts

Both headers are byte-for-byte copies of the existing WB build's
`cubeide/Companion_Nucleo_WB55RG_Bringup/build_freertos/generated/` headers.
They freeze the existing behavior/index metadata for the WBA target without
making it depend on an ignored build folder. They contain no new bitmap art.

`provenance.json` records source/destination hashes. The interaction contract
binds resource `B07892037FF33928733ECE88E1080C4D30F4A592F003F46C0F613E29FF85E202`,
identified as generation 21 in COMP-REQ-789/790. This establishes intended
compatibility, not installation on a new board. The matching full external
resource image has not been located in this workspace; `companion_resources`
refuses mismatched identities. A compiler/test result is not resource or visual
acceptance. Do not hand-edit these headers or substitute another generation.
