# MA2 Reverse Artistic Translator 001

## Status

Implemented as an offline, read-only MVP.  It consumes a retained native MA2
`Export Sequence` XML file (or the existing parsed discovery artifact) and
produces deterministic JSON.  It does not connect to MA2, send commands,
create previews, allocate resources, or alter the Builder/verifier path.

## Existing evidence inventory

| Existing component | Status and role in this MVP |
| --- | --- |
| `state/providers/sequence_export.py` | Current native XML authority. Parses Cue/CuePart/CueData, raw fields, Preset and Effect identities with a source SHA-256. |
| `cue_content_verifier.py` | Existing post-write comparator. It stays an acceptance verifier; the translator never substitutes for it. |
| `artistic_resources.py` | Existing current-Show capability/applicability authority. Any future reuse of a reference still needs this map. |
| `docs/reference_cases/LIGHTING_REFERENCE_CASE_001.md` | Existing visual-reference analysis. It records observations separately from MA2 stored-content evidence. |
| `ma2-reverse-research-full-archive-2026` | Historical `.show.gz` binary/Cue/Effect-Layer research. Useful background, but not an executable or authoritative source for this translator. |

## Input contract

The only accepted evidence authority is
`zen.sequence_export_discovery.v0.1` from `MA2_EXPORT_SEQUENCE_XML` with
`read_only: true` and a valid native XML SHA-256. `VERIFIED` and `PARTIAL`
evidence are accepted; `PARTIAL` remains `PARTIAL_EVIDENCE` in the result.

The convenience entry point is:

```python
from zen_ma2_agent.reverse_artistic_translator import translate_sequence_xml

reference = translate_sequence_xml(retained_sequence_xml, sequence_no=302)
```

This operates on already-retained data and makes no network or MA2 call.

## Output contract

`zen.ma2_reverse_artistic_translation.v0.1` contains four separate layers:

1. `technical_structure` — cue/part counts, observed attributes/dimensions,
   Preset/Effect reference use counts, fixture cardinality, and source
   integrity.
2. `cue_semantics` — per-Cue observable layers (`RAW_VALUE`,
   `PRESET_REFERENCE`, `EFFECT_REFERENCE`), attributes, dimensions, timing
   strings, resource identities, and a structural fingerprint.
3. `recurring_artistic_motifs` — only repeated stored cue structures. This is
   intentionally an observed structural motif, not a claim about visual or
   musical intent.
4. `machine_readable_design_reference` — reusable descriptive vocabulary plus
   the source hash, evidence status, prohibited inferences, and reuse guards.

The translator never normalizes MA2 raw values into intensity, color, angle,
tempo, or visual-output claims. It never infers an artist's intention, song
sections, camera result, fixture type, Patch, Address, or fixture identity.

## Relationship to prior binary research

The 2026 archive's `.show.gz` research remains useful historical structure
evidence, particularly for Sequence/Cue/Effect-Layer investigation. It is not
the authority for this MVP because several binary hypotheses remain only
strongly supported or rejected, and structural parser success does not prove
safe MA2 playback. Native Sequence XML remains the current authoritative
content path.

## Reuse boundary

A design reference is descriptive learning material. Before any future design
uses a Preset or Effect from it, the current Show must independently validate
the resource through the Artistic Resource Map. Existing Preview → explicit
Approval → native post-write verification remains unchanged; this module
cannot bypass or weaken any of those gates.
