# Existing Show Resource Mapping Review 001

Status: `READY_FOR_HUMAN_REVIEW` — proposal only; no mapping is active.

This review is the bounded next step after `ZEN_REAL_SONG_EXISTING_SHOW_AB_001.md`.
It maps the scanned Existing Show's real Groups to the *current limited B3
abstract role vocabulary for human consideration. It does **not** create
`role_bindings`, alter the production Designer, alter the experimental B3
algorithm, or authorize any MA2 action.

## Read-only source boundary

The only real-show facts used here are the committed, read-only Existing Show
snapshot (`data/ZEN_CURRENT_SHOW_PROFILE.json`, captured 2026-09-09) and its
sanitized A/B fixture (`tests/fixtures/real_song_existing_show_ab_001.json`).
They confirm the Group inventory, ordered membership, fixture-type labels,
Focus preset inventory, absent semantic position presets, and geometry state.

`data/ZEN_TRAINING_CASE_001.json` is used only as a provenance-bearing
case-specific interpretation of those same labels. Its role assignments are
already `INFERRED_FROM_GROUP_IDENTITY`; this review does not promote them.

### Confirmed facts

- The Show has seven non-empty Groups, each with eight ordered fixtures:
  `HYBRID`, `SPOT`, `BEAM`, `WASH`, `B-EYE`, `LED PAR`, and `STROBE`.
- Fixture-type labels are available in the scan/training-case snapshot.
- Focus presets `6.1 narrow`, `6.2 normal`, `6.3 wide`, `6.4 min Focus`, and
  `6.5 max Focus` exist in the captured inventory.
- Geometry is `GEOMETRY_UNINITIALIZED`; semantic position presets are absent.
- Effect names/inventory do not establish action-level effect behavior.

### Inferred facts

The candidate roles below are based on exact Group identity plus fixture-type
labels, and, where stated, the existing Training Case 001 interpretation. They
are `INFERRED_FROM_GROUP_IDENTITY`, `CASE_SPECIFIC`, and require explicit human
review before a future resolver can use them.

### Unknown facts

For every Group, the current scan does **not** independently verify attribute
capability, real programming intent, per-Group preset applicability, color
behavior, texture behavior, effect behavior, physical placement, or a
calibrated stage relationship. No candidate below establishes any of those.

## Candidate mapping review

### GROUP 1 — HYBRID

- **Confirmed resource facts:** Group `1 HYBRID`; fixtures `101–108` in scan
  order; fixture type label `2 ZEN BAW 20R Mode 2`.
- **Candidate primary role:** `MOVER_TEXTURE_LAYER`.
- **Candidate secondary roles:** `PRIMARY_FOCUS` (bounded translation of the
  Training Case's `KEY_LAYER`); `DENSITY_LAYER` only if later capability and
  look-composition review support broad coverage.
- **Unsupported / unsafe assumptions:** aerial placement, position/movement
  capability, mirror geometry, beam behavior, effect use, or that availability
  means the Group should be active.
- **Evidence:** Existing Show Group identity and fixture-type snapshot;
  Training Case 001 calls this a case-specific `AERIAL` / `KEY_LAYER` /
  `TEXTURE` candidate.
- **Confidence:** `INFERRED_FROM_GROUP_IDENTITY`.
- **HUMAN REVIEW:** `UNSET`.

### GROUP 2 — SPOT

- **Confirmed resource facts:** Group `2 SPOT`; fixtures `301–308` in scan
  order; fixture type label `3 ZEN DMH-160 St_Preset`.
- **Candidate primary role:** `PRIMARY_FOCUS`.
- **Candidate secondary roles:** `MOVER_TEXTURE_LAYER` (only as a conditional
  candidate; it is not a verified movement instruction).
- **Unsupported / unsafe assumptions:** performer location, focus coverage,
  position semantics, gobo/beam behavior, or automatic use of Focus presets on
  this Group.
- **Evidence:** Existing Show Group identity and fixture-type snapshot;
  Training Case 001's case-specific `KEY_LAYER` / `PERFORMER_FOCUS` reading.
- **Confidence:** `INFERRED_FROM_GROUP_IDENTITY`.
- **HUMAN REVIEW:** `UNSET`.

### GROUP 3 — BEAM

- **Confirmed resource facts:** Group `3 BEAM`; fixtures `201–208` in scan
  order; fixture type label `2 ZEN BAW 20R Mode 2`.
- **Candidate primary role:** `NO_CURRENT_B3_PRIMARY_ROLE_CANDIDATE`.
- **Candidate secondary roles:** `MOVER_TEXTURE_LAYER` only if a future
  human/capability review confirms that this is the appropriate abstract
  translation of the case-specific beam/aerial use.
- **Unsupported / unsafe assumptions:** a B3 `BEAM_LAYER` does not exist;
  geometry, aerial placement, beam parameters, impact behavior, and effect use
  must not be inferred from the name.
- **Evidence:** Existing Show Group identity and fixture-type snapshot;
  Training Case 001's inferred `BEAM_LAYER` / `AERIAL` interpretation.
- **Confidence:** `UNKNOWN_FOR_CURRENT_B3_MAPPING` — the limited B3 vocabulary
  cannot safely express the case-specific primary role without collapsing it.
- **HUMAN REVIEW:** `UNSET`.

### GROUP 4 — WASH

- **Confirmed resource facts:** Group `4 WASH`; fixtures `501–508` in scan
  order; fixture type label `5 ZEN MAC AU XB Standard`.
- **Candidate primary role:** `COLOR_FIELD`.
- **Candidate secondary roles:** `DENSITY_LAYER`.
- **Unsupported / unsafe assumptions:** actual color attributes, preset
  compatibility, broad physical coverage, environment/area semantics, or any
  position relationship.
- **Evidence:** Existing Show Group identity and fixture-type snapshot;
  Training Case 001's inferred `WASH_LAYER` / `COLOR_LAYER` /
  `ENVIRONMENT` interpretation.
- **Confidence:** `INFERRED_FROM_GROUP_IDENTITY`.
- **HUMAN REVIEW:** `UNSET`.

### GROUP 5 — B-EYE

- **Confirmed resource facts:** Group `5 B-EYE`; fixtures `401–408` in scan
  order; fixture type label `4 ZEN K10 Shapes`.
- **Candidate primary role:** `MOVER_TEXTURE_LAYER`.
- **Candidate secondary roles:** `COLOR_FIELD`.
- **Unsupported / unsafe assumptions:** pixel/shape behavior, movement,
  texture quality, effect behavior, geometry, and any claim that eye-candy is
  appropriate for a given section.
- **Evidence:** Existing Show Group identity and fixture-type snapshot;
  Training Case 001's case-specific `TEXTURE` / `COLOR_LAYER` interpretation.
- **Confidence:** `INFERRED_FROM_GROUP_IDENTITY`.
- **HUMAN REVIEW:** `UNSET`.

### GROUP 6 — LED PAR

- **Confirmed resource facts:** Group `6 LED PAR`; fixtures `601–608` in scan
  order; fixture type label `6 ZEN LEDPar 9c 9Ch Mode A`.
- **Candidate primary role:** `COLOR_FIELD`.
- **Candidate secondary roles:** `DENSITY_LAYER`.
- **Unsupported / unsafe assumptions:** actual color mixing/preset support,
  floor or rear placement, directional coverage, timing/effect behavior, or
  any semantic left/right relationship.
- **Evidence:** Existing Show Group identity and fixture-type snapshot;
  Training Case 001's inferred `COLOR_LAYER` / `WASH_LAYER` reading.
- **Confidence:** `INFERRED_FROM_GROUP_IDENTITY`.
- **HUMAN REVIEW:** `UNSET`.

### GROUP 7 — STROBE

- **Confirmed resource facts:** Group `7 STROBE`; fixtures `701–708` in scan
  order; fixture type label `7 Atomic 3000 LED Extended`.
- **Candidate primary role:** `TIMING_LAYER` — conditional only.
- **Candidate secondary roles:** `NONE` in the current B3 vocabulary.
- **Unsupported / unsafe assumptions:** flash, pulse, impact, effect grammar,
  safe intensity/rate, physical placement, or that a high-energy section
  should use this Group. The observed Effect inventory is not action-level
  evidence.
- **Evidence:** Existing Show Group identity and fixture-type snapshot;
  Training Case 001's inferred `IMPACT` / `ACCENT` reading.
- **Confidence:** `INFERRED_FROM_GROUP_IDENTITY`; `UNSAFE_FOR_ACTION` until
  behavior is independently verified and reviewed.
- **HUMAN REVIEW:** `UNSET`.

## Explicitly excluded mappings

- **Semantic position mapping:** excluded — no semantic Position presets and
  geometry is uninitialized.
- **Effect mapping:** excluded — labels/inventory alone cannot prove internal
  behavior or safe action-level application.
- **Training Case promotion:** excluded — Case 001 is evidence, not a binding
  for the Existing Show.
- **Production activation:** excluded — the production Designer remains
  unchanged and B3 remains `GUIDANCE_ASSISTED_AB_ONLY`.

## Compact review matrix

| Group | Candidate primary role | Candidate secondary role(s) | Mapping state | Evidence confidence | Human review |
| --- | --- | --- | --- | --- | --- |
| 1 HYBRID | `MOVER_TEXTURE_LAYER` | `PRIMARY_FOCUS`, conditional `DENSITY_LAYER` | proposal only | `INFERRED_FROM_GROUP_IDENTITY` | `UNSET` |
| 2 SPOT | `PRIMARY_FOCUS` | conditional `MOVER_TEXTURE_LAYER` | proposal only | `INFERRED_FROM_GROUP_IDENTITY` | `UNSET` |
| 3 BEAM | `NO_CURRENT_B3_PRIMARY_ROLE_CANDIDATE` | conditional `MOVER_TEXTURE_LAYER` | no safe B3 translation | `UNKNOWN_FOR_CURRENT_B3_MAPPING` | `UNSET` |
| 4 WASH | `COLOR_FIELD` | `DENSITY_LAYER` | proposal only | `INFERRED_FROM_GROUP_IDENTITY` | `UNSET` |
| 5 B-EYE | `MOVER_TEXTURE_LAYER` | `COLOR_FIELD` | proposal only | `INFERRED_FROM_GROUP_IDENTITY` | `UNSET` |
| 6 LED PAR | `COLOR_FIELD` | `DENSITY_LAYER` | proposal only | `INFERRED_FROM_GROUP_IDENTITY` | `UNSET` |
| 7 STROBE | conditional `TIMING_LAYER` | `NONE` | proposal only; action unsafe | `INFERRED_FROM_GROUP_IDENTITY` | `UNSET` |

**Count:** confirmed active mappings `0`; inferred candidate mapping proposals
`6`; current-B3 unmapped/unknown primary-role cases `1`; Groups with
capability-level unknowns `7`.

## Next bounded decision

Zen should review each candidate individually. A later accepted mapping must
remain provenance-bearing and experimental; it can make a future Existing Show
B3 A/B run expressible, but it must not silently change the production
Designer, create a `ZEN_STYLE_PROFILE`, or authorize MA2 writes.
