# Existing Show Resource Mapping Review 001

> **Superseded candidate-role state:** the identity-origin proposals in this document predate the real-console Show-bound channel binding. They are not current eligibility evidence. The durable current review is `ZEN_EXISTING_SHOW_CAPABILITY_CANDIDATE_ROLE_ELIGIBILITY_REVIEW_001.md`; it preserves no active mappings and no case role assignments.

Historical status: `CAPABILITY_ELIGIBILITY_PENDING` — proposal only; no mapping was active
or ready for role-eligibility approval at the time of this review.

This review is the bounded next step after `ZEN_REAL_SONG_EXISTING_SHOW_AB_001.md`.
It records non-ranked candidate relationships between the scanned Existing
Show's real Groups and the *current limited B3* abstract role vocabulary for
human consideration. It does **not** create
`role_bindings`, alter the production Designer, alter the experimental B3
algorithm, or authorize any MA2 action.

## Mapping model: capability before candidate; Design Intent before selection

This document does **not** assign permanent fixture roles, fixture importance,
or a ZEN-wide Group ordering. In particular, it does not say that HYBRID must
be primary, BEAM must be secondary, or WASH must be color. A Group can serve a
different role in another song or section, or can be intentionally unused.

The terms below are deliberately separate:

1. **`resource_capabilities`** — only what is confirmed or plausibly available
   from the current resource scan. A Group name is not a capability proof.
2. **`candidate_roles`** — non-ranked B3 roles the resource *may* suit in a
   bounded context. These are not assignments and remain inferred unless
   independently verified.
3. **`case_role_assignment`** — the actual choice for a particular song,
   section, and Design Intent. None are made in this review. Design Intent
   precedes this selection; it may choose no role for an available Group.

## Read-only source boundary

The only real-show facts used here are the committed, read-only Existing Show
snapshot (`data/ZEN_CURRENT_SHOW_PROFILE.json`, captured 2026-09-09) and its
sanitized A/B fixture (`tests/fixtures/real_song_existing_show_ab_001.json`).
They confirm the Group inventory, ordered membership, fixture-type labels,
Focus preset inventory, absent semantic position presets, and geometry state.

`data/ZEN_TRAINING_CASE_001.json` is used only as a provenance-bearing
case-specific interpretation of those same labels. Its role assignments are
already `INFERRED_FROM_GROUP_IDENTITY`; this review does not promote them.

`ZEN_EXISTING_SHOW_RESOURCE_CAPABILITY_VERIFICATION_001.md` supersedes these
identity-origin role hypotheses as human-review inputs. Until a Show-bound
technical capability source or an exact profile binding is confirmed, no
candidate below is eligible for Zen to approve as a B3 role capability.

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

## Resource capability and candidate-role review

### GROUP 1 — HYBRID

- **`resource_capabilities` — confirmed inventory facts:** Group `1 HYBRID`; fixtures `101–108` in scan
  order; fixture type label `2 ZEN BAW 20R Mode 2`.
- **`candidate_roles` — non-ranked:** `MOVER_TEXTURE_LAYER`,
  `PRIMARY_FOCUS` (bounded translation of Training Case's `KEY_LAYER`), and
  conditional `DENSITY_LAYER` if a later capability/look review supports it.
- **`case_role_assignment`:** `NONE` — must be selected, or intentionally not
  selected, from a specific Design Intent.
- **Unsupported / unsafe assumptions:** aerial placement, position/movement
  capability, mirror geometry, beam behavior, effect use, or that availability
  means the Group should be active.
- **Evidence:** Existing Show Group identity and fixture-type snapshot;
  Training Case 001 calls this a case-specific `AERIAL` / `KEY_LAYER` /
  `TEXTURE` candidate.
- **Confidence:** `INFERRED_FROM_GROUP_IDENTITY`.
- **HUMAN ROLE ELIGIBILITY REVIEW:** `DEFERRED_PENDING_CAPABILITY_BINDING`.

### GROUP 2 — SPOT

- **`resource_capabilities` — confirmed inventory facts:** Group `2 SPOT`; fixtures `301–308` in scan
  order; fixture type label `3 ZEN DMH-160 St_Preset`.
- **`candidate_roles` — non-ranked:** `PRIMARY_FOCUS`; conditional
  `MOVER_TEXTURE_LAYER` (not a verified movement instruction).
- **`case_role_assignment`:** `NONE` — Design Intent may select either,
  neither, or another safe strategy for the section.
- **Unsupported / unsafe assumptions:** performer location, focus coverage,
  position semantics, gobo/beam behavior, or automatic use of Focus presets on
  this Group.
- **Evidence:** Existing Show Group identity and fixture-type snapshot;
  Training Case 001's case-specific `KEY_LAYER` / `PERFORMER_FOCUS` reading.
- **Confidence:** `INFERRED_FROM_GROUP_IDENTITY`.
- **HUMAN ROLE ELIGIBILITY REVIEW:** `DEFERRED_PENDING_CAPABILITY_BINDING`.

### GROUP 3 — BEAM

- **`resource_capabilities` — confirmed inventory facts:** Group `3 BEAM`; fixtures `201–208` in scan
  order; fixture type label `2 ZEN BAW 20R Mode 2`.
- **`candidate_roles` — non-ranked:** no safe direct B3 translation currently;
  conditional `MOVER_TEXTURE_LAYER` only if a future
  human/capability review confirms that this is the appropriate abstract
  translation of the case-specific beam/aerial use.
- **`case_role_assignment`:** `NONE` — no selection can be made until the
  B3 translation is reviewed rather than collapsed.
- **Unsupported / unsafe assumptions:** a B3 `BEAM_LAYER` does not exist;
  geometry, aerial placement, beam parameters, impact behavior, and effect use
  must not be inferred from the name.
- **Evidence:** Existing Show Group identity and fixture-type snapshot;
  Training Case 001's inferred `BEAM_LAYER` / `AERIAL` interpretation.
- **Confidence:** `UNKNOWN_FOR_CURRENT_B3_MAPPING` — the limited B3 vocabulary
  cannot safely express the case-specific candidate without collapsing it.
- **HUMAN ROLE ELIGIBILITY REVIEW:** `DEFERRED_PENDING_CAPABILITY_BINDING`.

### GROUP 4 — WASH

- **`resource_capabilities` — confirmed inventory facts:** Group `4 WASH`; fixtures `501–508` in scan
  order; fixture type label `5 ZEN MAC AU XB Standard`.
- **`candidate_roles` — non-ranked:** `COLOR_FIELD`, `DENSITY_LAYER`.
- **`case_role_assignment`:** `NONE` — `WASH` is not a permanent color role;
  the song/case decision may select either candidate, neither, or another
  safe strategy.
- **Unsupported / unsafe assumptions:** actual color attributes, preset
  compatibility, broad physical coverage, environment/area semantics, or any
  position relationship.
- **Evidence:** Existing Show Group identity and fixture-type snapshot;
  Training Case 001's inferred `WASH_LAYER` / `COLOR_LAYER` /
  `ENVIRONMENT` interpretation.
- **Confidence:** `INFERRED_FROM_GROUP_IDENTITY`.
- **HUMAN ROLE ELIGIBILITY REVIEW:** `DEFERRED_PENDING_CAPABILITY_BINDING`.

### GROUP 5 — B-EYE

- **`resource_capabilities` — confirmed inventory facts:** Group `5 B-EYE`; fixtures `401–408` in scan
  order; fixture type label `4 ZEN K10 Shapes`.
- **`candidate_roles` — non-ranked:** `MOVER_TEXTURE_LAYER`, `COLOR_FIELD`.
- **`case_role_assignment`:** `NONE` — Design Intent determines whether either
  candidate is useful for the current section.
- **Unsupported / unsafe assumptions:** pixel/shape behavior, movement,
  texture quality, effect behavior, geometry, and any claim that eye-candy is
  appropriate for a given section.
- **Evidence:** Existing Show Group identity and fixture-type snapshot;
  Training Case 001's case-specific `TEXTURE` / `COLOR_LAYER` interpretation.
- **Confidence:** `INFERRED_FROM_GROUP_IDENTITY`.
- **HUMAN ROLE ELIGIBILITY REVIEW:** `DEFERRED_PENDING_CAPABILITY_BINDING`.

### GROUP 6 — LED PAR

- **`resource_capabilities` — confirmed inventory facts:** Group `6 LED PAR`; fixtures `601–608` in scan
  order; fixture type label `6 ZEN LEDPar 9c 9Ch Mode A`.
- **`candidate_roles` — non-ranked:** `COLOR_FIELD`, `DENSITY_LAYER`.
- **`case_role_assignment`:** `NONE` — availability never requires use, and
  the Design Intent determines any chosen role.
- **Unsupported / unsafe assumptions:** actual color mixing/preset support,
  floor or rear placement, directional coverage, timing/effect behavior, or
  any semantic left/right relationship.
- **Evidence:** Existing Show Group identity and fixture-type snapshot;
  Training Case 001's inferred `COLOR_LAYER` / `WASH_LAYER` reading.
- **Confidence:** `INFERRED_FROM_GROUP_IDENTITY`.
- **HUMAN ROLE ELIGIBILITY REVIEW:** `DEFERRED_PENDING_CAPABILITY_BINDING`.

### GROUP 7 — STROBE

- **`resource_capabilities` — confirmed inventory facts:** Group `7 STROBE`; fixtures `701–708` in scan
  order; fixture type label `7 Atomic 3000 LED Extended`.
- **`candidate_roles` — non-ranked:** conditional `TIMING_LAYER`; no additional
  safe current B3 candidate.
- **`case_role_assignment`:** `NONE` — a high-energy section does not imply
  use of this Group, and no timing/impact action is authorized here.
- **Unsupported / unsafe assumptions:** flash, pulse, impact, effect grammar,
  safe intensity/rate, physical placement, or that a high-energy section
  should use this Group. The observed Effect inventory is not action-level
  evidence.
- **Evidence:** Existing Show Group identity and fixture-type snapshot;
  Training Case 001's inferred `IMPACT` / `ACCENT` reading.
- **Confidence:** `INFERRED_FROM_GROUP_IDENTITY`; `UNSAFE_FOR_ACTION` until
  behavior is independently verified and reviewed.
- **HUMAN ROLE ELIGIBILITY REVIEW:** `DEFERRED_PENDING_CAPABILITY_BINDING`.

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

| Group | Non-ranked identity-origin hypothesis | Current case-role assignment | Mapping state | Evidence confidence | Role eligibility review |
| --- | --- | --- | --- | --- | --- |
| 1 HYBRID | `MOVER_TEXTURE_LAYER`, `PRIMARY_FOCUS`, conditional `DENSITY_LAYER` | `NONE` | capability eligibility pending | `INFERRED_FROM_GROUP_IDENTITY` | `DEFERRED_PENDING_CAPABILITY_BINDING` |
| 2 SPOT | `PRIMARY_FOCUS`, conditional `MOVER_TEXTURE_LAYER` | `NONE` | capability eligibility pending | `INFERRED_FROM_GROUP_IDENTITY` | `DEFERRED_PENDING_CAPABILITY_BINDING` |
| 3 BEAM | no safe direct B3 translation; conditional `MOVER_TEXTURE_LAYER` | `NONE` | no safe B3 translation | `UNKNOWN_FOR_CURRENT_B3_MAPPING` | `DEFERRED_PENDING_CAPABILITY_BINDING` |
| 4 WASH | `COLOR_FIELD`, `DENSITY_LAYER` | `NONE` | capability eligibility pending | `INFERRED_FROM_GROUP_IDENTITY` | `DEFERRED_PENDING_CAPABILITY_BINDING` |
| 5 B-EYE | `MOVER_TEXTURE_LAYER`, `COLOR_FIELD` | `NONE` | capability eligibility pending | `INFERRED_FROM_GROUP_IDENTITY` | `DEFERRED_PENDING_CAPABILITY_BINDING` |
| 6 LED PAR | `COLOR_FIELD`, `DENSITY_LAYER` | `NONE` | capability eligibility pending | `INFERRED_FROM_GROUP_IDENTITY` | `DEFERRED_PENDING_CAPABILITY_BINDING` |
| 7 STROBE | conditional `TIMING_LAYER` | `NONE` | capability eligibility pending; action unsafe | `INFERRED_FROM_GROUP_IDENTITY` | `DEFERRED_PENDING_CAPABILITY_BINDING` |

**Count:** confirmed resource-to-role mappings `0`; inferred candidate-role
proposals `6`; current-B3 unmapped/unknown candidate-role cases `1`; Groups with
capability-level unknowns `7`.

## Next bounded decision

First review the technical profile binding in
`ZEN_EXISTING_SHOW_RESOURCE_CAPABILITY_VERIFICATION_001.md`; do not approve
role eligibility from this document's identity-origin hypotheses. After a
Show-bound capability is confirmed, a later accepted eligibility mapping must
remain provenance-bearing and experimental. It only makes a resource eligible
for selection by a future song/case Design Intent; it is not a fixture-role
habit or a priority order. It may make a future Existing Show B3 A/B run
expressible, but it must not silently change the production Designer, create a
`ZEN_STYLE_PROFILE`, or authorize MA2 writes.
