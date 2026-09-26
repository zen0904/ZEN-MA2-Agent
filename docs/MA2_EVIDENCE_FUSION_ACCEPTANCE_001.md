# MA2 Evidence Fusion — Real-Show Acceptance 001

Date: 2026-09-26
Code under acceptance: `451eb3350085de9e341aab84260b9b05dad33f7a` (`feat: add offline artistic evidence fusion`).

## Result

**PASS** for the offline Evidence Fusion / Artistic Reconstruction boundary.

The acceptance used retained real-machine grandMA2 Sequence evidence plus
already committed Test Show context. It did not contact MA2, enter the Builder,
approve a Preview, allocate an MA object, or mutate any Show state.

The accepted fusion artifact is a read-only
`zen.artistic_evidence_fusion.v0.1` document with three non-interchangeable
layers:

- `FACT`: 34 findings;
- `INFERENCE`: 16 findings;
- `HYPOTHESIS`: 1 explicitly low-confidence reconstruction possibility.

The generated artifact SHA-256 is:

`b1faa96108adc15e4cba5b626f1fe7940776869621b6edc9e0bd8702acdfb8f9`

It was created under the ignored acceptance cache and is not committed as
runtime/design truth.

## Primary native source: Sequence 901

The primary reverse translation was regenerated from the retained native
Sequence 901 XML using the current translator, not reused from an older
PowerShell-encoded artifact.

- Sequence: `901 ZEN_SHEESH_TEST`
- Native XML SHA-256:
  `b6af8d37f237ccd6f31011176b86e46fd78c7bbb6a00194f8e6b1e769a7f6444`
- Translation status: `OBSERVED`
- Translation UTF-8 JSON SHA-256:
  `1d303421bfc6df57de63f99196202c04476c56c4ddddfb804c0d85fc212adf24`
- Exact stored-content recurrence:
  `CONTENT_9B7677692DE7`, Cue `5` and Cue `10`
- Cue 5 source label: `HOOK_1_SHEESH`
- Cue 10 source label: `HOOK_2_SHEESH`
- Both Cue fingerprints:
  `9b7677692de775b821213255eaff22843a1e3936cf89cff54ebab8714701a39f`

The exact recurrence is a native stored-content fact. The cue labels remain
source metadata and do not independently establish musical alignment or
authorial intent.

## Supplied context evidence

### Song structure

Source:
`data/zen_real_ma2_test_show_sheesh_001_plan.json`

Status: `VERIFIED` as a retained Test Show plan artifact.

Each of the 15 planned Cue labels was supplied as explicit
`SONG_STRUCTURE` context. Cue 5 and Cue 10 both carry the supplied tag
`HOOK`.

This produced the bounded inference:

`INFERENCE_CONTENT_9B7677692DE7_TAG_HOOK`

with:

- classification:
  `EXACT_CONTENT_RECURRENCE_WITH_SHARED_CONTEXT_TAG`;
- confidence: `MEDIUM`;
- limits:
  `TAG_CORRELATION_ONLY`,
  `DOES_NOT_ESTABLISH_A_DESIGN_MOTIF_INTENTION`,
  `DOES_NOT_ESTABLISH_VISUAL_OUTPUT`.

Therefore the fusion layer may state that exact stored CueData recurs on two
Cues that the supplied plan labels as HOOK anchors. It may not state that the
programmer deliberately created a hook motif as fact.

### Timing / Timecode

Source:
`data/zen_real_ma2_test_show_sheesh_001_plan.json#designer.timecode`

Status: `PARTIAL`.

The source explicitly records
`NOT_WRITTEN_AUDIO_NOT_AVAILABLE`. No exact playback timecode or seconds were
invented. The resulting contextual fact is downgraded to `LOW`.

### Audio analysis

Source:
`data/zen_real_ma2_test_show_sheesh_001_plan.json#designer.timecode`

Status: `PARTIAL`.

The retained plan explicitly states that audio was not available. No beat,
onset, section-timestamp, or audio-causal claim was fabricated. The resulting
contextual fact is `LOW` and creates no Cue correlation.

### Stage View / visual evidence

Source:
`data/sheesh_spatial_fact_calibration_001.json#stage_view_evidence_input`

Status: `PARTIAL`.

The retained spatial calibration records
`STAGE_VIEW_IMAGE_AVAILABLE=NO` and no Stage View image artifact. No visual
frame correlation, beam appearance, stage target, performer target, or venue
appearance claim was generated. The resulting contextual fact is `LOW`.

## Hypothesis boundary

One acceptance-only hypothesis was supplied:

> One possible artistic reconstruction is that the same stored lighting state
> was deliberately reused at the two supplied HOOK anchors.

The fusioner did not promote it. Output confidence is fixed to `LOW` and the
finding carries:

- `NOT_A_FACT`;
- `NOT_EXECUTION_AUTHORIZATION`;
- `DOES_NOT_ESTABLISH_VISUAL_OUTPUT_OR_AUTHORIAL_INTENT`.

The hypothesis cites the exact native recurrence plus both supplied HOOK
observations.

## Native control sequences

The current `451eb33` translator was also rerun offline against the retained
real-machine controls.

### Sequence 6 — Effect positive control

- Native XML SHA-256:
  `632f071aaf2ab70da4ab7524ab0afc21f9bfc5532cae888715f0cd103779d19c`
- Translation status: `OBSERVED`
- Cue 1 source label: `FX_CALL_TEST`
- Effect references: `2`
- Observable behavior:
  `EFFECT_REFERENCE` on exact Fixture IDs 101–108
- Effect playback / visual semantics: not claimed.

### Sequence 12 — Position control

- Native XML SHA-256:
  `9aa1048c4b10b326f416c089ff760c712e96801c55013b735f94eb1e6fe3810d`
- Translation status: `OBSERVED`
- Cue 1 `RAW_POSITION`:
  `RAW_PAN_TILT` on exact Fixture IDs 101–108
- Cue 2 `PRESET_POSITION`:
  Position Preset reference `2.13`,
  `POSITION_PRESET_REFERENCE` on exact Fixture IDs 101–108
- Physical aim / degree / visible-stage semantics: not claimed.

These controls confirm that adding the fusion layer did not regress the
existing native Position and Effect reverse-translation evidence.

## Artifact and CLI checks

Acceptance assertions passed:

- output decodes as UTF-8 with no BOM;
- `read_only=true`;
- source Sequence is exactly 901 with `OBSERVED` translation status;
- one exact native recurrence fact is `HIGH`;
- the shared HOOK recurrence inference is exactly `MEDIUM`;
- all facts derived from `PARTIAL` timing/audio/Stage View sources are
  downgraded to `LOW`;
- the hypothesis is exactly `LOW`;
- no top-level command, candidate-command, MA-write, approval, executor, Patch,
  or Address field is present;
- CLI overwrite refusal returned exit code `2` on an existing output.

## Tests

Environment dependencies were installed into an isolated temporary virtual
environment from the repository's existing `requirements.txt`; no repository
dependency versions were changed.

macOS full discovery:

```text
Ran 873 tests in 20.331s
OK
```

Windows focused fusion + reverse-translator regression:

```text
Ran 14 tests in 0.065s
OK
```

The macOS suite emitted Starlette/httpx deprecation and test HTTP cleanup
warnings only; there were no test failures or import errors.

## Safety / authority result

Throughout this acceptance:

- `MA2_WRITES=0`;
- Patch was not modified;
- Address was not modified;
- Fixture identity/type was not modified;
- Fixture 9999 was not touched;
- no pending Preview was approved or executed;
- the existing Preview / Approval / deterministic Builder / native post-write
  verification boundaries remain unchanged.

The fusion artifact is descriptive evidence for Designer/Critic context only.
It is not an executable Show Plan, not a verified current-Show resource map,
and not MA write authority.

## Acceptance status

`EVIDENCE_FUSION_REAL_SHOW_ACCEPTANCE_001 = PASS`

This acceptance does **not** change the mainline
`FULL_ARTISTIC_POSITION_EXECUTION_001` owner-approval gate. The pending
Sequence 302 / Executor 2.8 Preview remains unexecuted until the owner
explicitly approves that exact Action.
