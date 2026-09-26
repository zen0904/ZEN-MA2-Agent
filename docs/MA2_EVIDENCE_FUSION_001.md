# MA2 Evidence Fusion / Artistic Reconstruction 001

## Status

Implemented as an offline, read-only extension of the existing MA2 Reverse
Artistic Translator. It accepts the translator's existing full translation JSON
(including its embedded `machine_readable_design_reference`) and does not create
a parallel XML parser or a new MA2 resource model.

It does not contact MA2, modify a Show, create a Preview, allocate a resource,
or enter the Builder path. Patch, Address, Fixture identity/type, and current
Show resource eligibility remain outside this pipeline.

## Input contract

The first input must be an existing
`zen.ma2_reverse_artistic_translation.v0.1` with `read_only: true`. Native
Sequence XML therefore remains the authority for stored CueData, source hash,
and exact repeated-content motifs.

Each additional evidence file must be an offline
`zen.artistic_context_evidence.v0.1` artifact with:

- `read_only: true`;
- a unique `evidence_id`, `source_ref`, and `status` (`VERIFIED` or `PARTIAL`);
- one or more observations, each with an `observation_id`, a source-specific
  `kind`, a literal `claim`, an explicit `confidence`, optional Cue references,
  and optional controlled tags.

Supported `source_type` values are:

```text
TIMING_TIMECODE
SONG_STRUCTURE
AUDIO_ANALYSIS
STAGE_VIEW_VISUAL
```

An observation is evidence *about its supplied source*, not proof that MA2 XML
created a visual result or that a programmer had a particular intent. A Stage
View observation may record what is visible in a documented frame; it does not
turn fixture IDs or raw PAN/TILT values into a visible-stage claim.

Example song-structure artifact:

```json
{
  "schema": "zen.artistic_context_evidence.v0.1",
  "read_only": true,
  "evidence_id": "song-analysis-001",
  "source_type": "SONG_STRUCTURE",
  "source_ref": "offline/song-analysis-001.json",
  "status": "VERIFIED",
  "observations": [{
    "observation_id": "hook-cues",
    "kind": "SECTION_ANCHOR",
    "claim": "Supplied song analysis labels Cue anchors 5 and 10 as HOOK.",
    "cue_refs": ["5", "10"],
    "tags": ["HOOK"],
    "confidence": "HIGH"
  }]
}
```

`temporal_evidence` is optional for any observation and may retain a documented
`timecode` plus non-negative `start_seconds` / `end_seconds`. The fusion output
preserves it verbatim as supplied evidence; it does not calculate timecode from
MA2 cue numbers. Native CuePart names are retained alongside each native Cue
fact as labels observed in the retained Sequence XML, without assuming they are
musical sections.

Cue references are explicit associations supplied by the artifact author. A
reference to a Cue missing from the translation is retained as a supplied fact,
but produces no cue correlation. This prevents positional guessing across
unrelated sequence exports.

Optional hypotheses use `zen.artistic_reconstruction_hypotheses.v0.1`, also
with `read_only: true`. Every hypothesis must cite already-emitted evidence
references. The fusioner fixes all hypothesis confidence to `LOW` and adds
`NOT_A_FACT` / `NOT_EXECUTION_AUTHORIZATION` limits; it does not invent
hypotheses from XML or media evidence.

## Output contract

`zen.artistic_evidence_fusion.v0.1` has three mandatory, non-interchangeable
layers:

| Layer | Contents | Required traceability |
| --- | --- | --- |
| `FACT` | Native CueData and exact repeated-content observations; literal supplied contextual observations. | Every finding has `evidence_refs` and `confidence`. Context observations retain a `source_ref`. |
| `INFERENCE` | Explicit Cue-to-context correlations and exact-content recurrences whose Cues carry the same supplied song/audio tag. | Every inference has source refs, an explicit `LOW` / `MEDIUM` confidence, and correlation-only limits. |
| `HYPOTHESIS` | Caller-supplied, traceable artistic reconstruction possibilities. | Every hypothesis must reference emitted evidence; it is always `LOW` confidence and never a fact. |

The generated inference vocabulary intentionally does **not** include visual
appearance, causal playback behavior, musical intention, or programmer / artist
intent. Exact CueData repeated at two song anchors can support only the bounded
statement that the stored content recurs with the supplied context tag. It does
not prove a visual motif, chorus treatment, author decision, or playback result.

Partial reverse translations or partial context artifacts lower generated
correlation confidence to `LOW`; the pipeline never upgrades incomplete
evidence to verified fact.

## Offline CLI

```text
python3 -m scripts.fuse_artistic_evidence \
  sequence901_design_reference.json \
  --context song-analysis-001.json \
  --context timecode-001.json \
  --context audio-analysis-001.json \
  --context stage-view-001.json \
  --hypotheses reconstruction-hypotheses.json \
  --output sequence901-evidence-fusion.json
```

The tool reads only existing UTF-8 JSON. With `--output` it creates a new
UTF-8 JSON file and refuses to overwrite one. It never modifies its input
files or sends an MA2 command.

## Safety boundary

The fusion artifact is descriptive research material. It does not authorize
use of a Preset, Effect, Cue, fixture, or timing object in another Show. Any
future design or execution still needs current-Show Artistic Resource Map
validation, Preview, explicit Approval, and native post-write verification.
