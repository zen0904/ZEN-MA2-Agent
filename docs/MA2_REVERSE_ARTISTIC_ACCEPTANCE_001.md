# MA2 Reverse Artistic Translator — Real-Machine Acceptance 001

Date: 2026-09-26. Code: `7b454ef` through `8cff0b1` on GitHub `main`.

## Boundary

The run used native grandMA2 Sequence XML and the offline translator. The
normal-design evidence was acquired through the existing allow-listed
read-only `List Sequence` and `Export Sequence 901` path. No Store, Edit,
Delete, Patch, Address, Fixture identity/type change, Preview approval, or
MA2 Show write occurred. The pending Sequence 302 Preview was not executed;
Sequence 302 was absent from the current `List Sequence` inventory.

An isolated Windows checkout of `main` was used for acceptance. The original
position-calibration checkout and its retained XML were not modified.

## Sequence 12: controlled Position evidence

- Source: retained `ZEN_AGENT_SEQUENCE_12_25f4bfbe73cbccfe.xml` in the
  position-calibration checkout's `cache/sequence_export_diagnostics`.
- Original XML SHA-256:
  `9aa1048c4b10b326f416c089ff760c712e96801c55013b735f94eb1e6fe3810d`.
- Native parser status: `VERIFIED`. Two numbered Cues; eight observed Fixture
  IDs, 101–108.
- Cue 1 `RAW_POSITION`: each Fixture has raw PAN `20` and TILT `30`.
- Cue 2 `PRESET_POSITION`: each Fixture has PAN and TILT referencing native
  address `1.2.13`, canonical Preset reference `2.13`. The XML also stores
  that Preset reference on DIST and VIRTUAL_POSITION_MODE rows; the translator
  reports all 32 reference uses rather than claiming all are PAN/TILT.
- The translator emits one `RAW_PAN_TILT` behavior for Cue 1 and one
  `POSITION_PRESET_REFERENCE` behavior for Cue 2, each covering eight Fixture
  IDs. It emits no recurring motif, which is correct for these different Cue
  contents.
- Independent ElementTree assertions over the original XML verified the
  expected PAN/TILT and Preset rows. The translation's source SHA-256 matched
  the original file hash.

## Sequence 901: normal design evidence

- Current read-only Sequence inventory identified `901 ZEN_SHEESH_TEST`.
- Fresh retained export: `ZEN_AGENT_SEQUENCE_901_b0885ff341b7755c.xml`
  under the isolated checkout's `cache/sequence_export_diagnostics`.
- Original XML SHA-256:
  `b6af8d37f237ccd6f31011176b86e46fd78c7bbb6a00194f8e6b1e769a7f6444`.
- Native parser status: `VERIFIED`. Fifteen numbered Cues and 56 observed
  Fixture IDs. The source contains Color and Dimmer CueData and references
  Color Presets `4.101`, `4.102`, `4.108`, `4.109`, `4.110`, `4.112`, and
  `4.113`. No Effect or Position references were observed in this export.
- The translator identifies one exact stored-content recurrence: Cue 5
  `HOOK_1_SHEESH` and Cue 10 `HOOK_2_SHEESH`. An independent direct XML
  comparison confirmed that the two Cues have identical sets of 176 native
  CueData rows. Their labels are source metadata, not proof of musical
  alignment or programmer intent.
- The translation's source SHA-256 matched the fresh XML file hash.

## Sequences 5 and 6: Effect absence/presence controls

Current read-only inventory identified `5 ZEN_AI_TEST_SHEESH_SEQ5` and
`6 ZEN_AI_EFFECT_CALL_TEST_6`. Fresh native exports were retained in the
isolated checkout:

- Sequence 5: `ZEN_AGENT_SEQUENCE_5_5c45e776e1047449.xml`, SHA-256
  `8a34891ed38a2fbe167e3a9e0bc46a4830950dde8a1d0d516b0783b6427f50a7`.
  Six Cues, 856 native CueData rows, zero Effect nodes. The translator emits
  no Effect references or Effect behavior events.
- Sequence 6: `ZEN_AGENT_SEQUENCE_6_7e4ba7141b203468.xml`, SHA-256
  `632f071aaf2ab70da4ab7524ab0afc21f9bfc5532cae888715f0cd103779d19c`.
  One Cue, eight native CueData rows with Effect address ending in `2`. The
  translator emits one `EFFECT_REFERENCE` event for Effect `2` across Fixture
  IDs 101–108.

Independent ElementTree inspection of the fresh XML confirmed both the
zero-Effect negative control and all eight positive Effect rows. The
translator does not infer Effect playback shape or visual result from these
references.

## Negative control and tests

The retained Sequence 11 calibration export translated as `PARTIAL_EVIDENCE`.
The collection translator excluded it from cross-Sequence motif claims.
Focused parser, translator, content-verifier, and resource-map tests passed
on both macOS and the Windows MA2 host: 39 tests on each platform.

## Acceptance result

`PASS` for read-only native XML ingestion, evidence provenance, canonical
resource references, controlled Position behavior, Effect absence/presence,
normal multi-Cue structure, and one independently confirmed exact-content
motif. This does
not promote a design reference into executable resources or prove visual
appearance, song timing, or author intent. Any future design use still
requires current-Show resource validation, Preview, explicit Approval, and
native post-write verification.
