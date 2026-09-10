# Existing Show Resource Capability Verification 001

Status: `PROFILE_BINDING_REQUIRED` — no Show-bound fixture attribute capability
is verified by this review.

This is a local/read-only technical evidence review. It occurs before human
review of B3 role eligibility and does not select any role for a song, section,
or Design Intent.

## Scope and evidence rule

The current Existing Show scan verifies Group identity, ordered membership and
the textual fixture-type label only. `ShowScanner` explicitly records that it
has no Fixture Type structure, DMX-channel, fixture-attribute, Preset-content,
or per-Group Preset-applicability provider. Therefore a Group name, a fixture
type label, an existing Focus pool entry, or an Effect name is **not** proof of
an actual fixture attribute in this Show.

The local grandMA2 3.9.60 library was inspected read-only at:

```text
C:\ProgramData\MA Lighting Technologies\grandma\gma2_V_3.9.60\library
```

It contains profiles with closely matching manufacturer/model/mode text. The
channel definitions in those local profiles are real technical evidence **for
those local profile files**, but the current Show does not expose a verified
link from `ZEN …` Fixture Type objects to a library filename, profile hash, or
channel definition. They are consequently recorded as
`LOCAL_PROFILE_CANDIDATE_UNBOUND`, never as capabilities verified for the
current Show.

## Three distinct layers

1. **Show-bound resource identity — `CONFIRMED`:** current Group, membership,
   and textual Fixture Type label from the 2026-09-09 read-only scan.
2. **Local profile capability — `LOCAL_PROFILE_CANDIDATE_UNBOUND`:** parsed
   channel definitions in a locally installed profile with a closely matching
   name/mode; no proof it is the Show's loaded or unmodified type.
3. **B3 role eligibility — `NOT_ESTABLISHED`:** may only be derived after a
   Show-bound capability source is verified. It is neither fixture priority nor
   a case role assignment.

`case_role_assignment` remains `NONE` for every Group. Geometry remains
`GEOMETRY_UNINITIALIZED`; semantic position presets are absent. Effect names
and inventory are excluded as behavioral evidence.

## Verified Show resource identity

| Group(s) | Exact scanned Group | Exact scanned Fixture Type | Members | Show-bound attribute capability |
| --- | --- | --- | --- | --- |
| 1 | HYBRID | `2 ZEN BAW 20R Mode 2` | 101–108 | `UNKNOWN` |
| 3 | BEAM | `2 ZEN BAW 20R Mode 2` | 201–208 | `UNKNOWN` |
| 2 | SPOT | `3 ZEN DMH-160 St_Preset` | 301–308 | `UNKNOWN` |
| 4 | WASH | `5 ZEN MAC AU XB Standard` | 501–508 | `UNKNOWN` |
| 5 | B-EYE | `4 ZEN K10 Shapes` | 401–408 | `UNKNOWN` |
| 6 | LED PAR | `6 ZEN LEDPar 9c 9Ch Mode A` | 601–608 | `UNKNOWN` |
| 7 | STROBE | `7 Atomic 3000 LED Extended` | 701–708 | `UNKNOWN` |

The ungrouped Fixture `9999` shares the BAW textual type but is not a Group
resource and remains excluded from this review.

## Attribute verification outcome for the current Show

For **every** Group above, the status of `DIMMER`, `COLOR`, `PAN`, `TILT`,
`POSITION`, `GOBO`, `PRISM`, `ZOOM`, `FOCUS`, `FROST`,
`SHUTTER/STROBE`, `PIXEL/SHAPE`, and other fixture attributes is
`UNKNOWN_FOR_EXISTING_SHOW`.

This is intentional, not an assertion that a fixture lacks the attribute. The
current scanner only has the textual type label and no Show-bound channel map.
The Focus preset inventory (`6.1`–`6.5`) proves only that those pool objects
exist, not that they apply to any specific Group. The legacy Effect `3520` is
Show-identity-isolated and its name/parameters cannot prove the current Show's
Dimmer or effect behavior.

## Local profile evidence — not Show-bound

The table below exposes useful local technical evidence while preserving its
boundary. `Capability read from profile` never changes the `UNKNOWN` outcome
above until a binding is proved.

| Current Show type | Read-only local profile candidate | Parsed profile channel capability | Current-Show status |
| --- | --- | --- | --- |
| `2 ZEN BAW 20R Mode 2` | `zhong_light@zhong_light_xp20rbsw@mode_2.xml` — `Zhong Light XP20RBSW`, `Mode 2` | Dimmer; color features; Pan/Tilt and Position; Focus; Frost; Gobo 1/2; Shutter; Zoom. | `LOCAL_PROFILE_CANDIDATE_UNBOUND` |
| `3 ZEN DMH-160 St_Preset` | `zhong_light@zhong_light_dmh-160@st_preset.xml` — `Zhong Light DMH-160`, `St_Preset` | Dimmer; color; Pan/Tilt and Position; Focus; Gobo 1/2; Iris; Shutter with Strobe mode. | `LOCAL_PROFILE_CANDIDATE_UNBOUND` |
| `5 ZEN MAC AU XB Standard` | `zhong_light@zhong_light_mac_au_xb@standard.xml` — `Zhong Light MAC AU XB`, `Standard` | Dimmer; RGB/color-mix features; Pan/Tilt and Position; Zoom; Shutter/Strobe; effect-macro attributes. | `LOCAL_PROFILE_CANDIDATE_UNBOUND` |
| `4 ZEN K10 Shapes` | `clay_paky@a.leda_b-eye_k10@shapes.xmlp` — `A.leda B-EYE K10`, `Shapes` | Dimmer; RGBW/all-color controls; Pan/Tilt and Position; Zoom; shutter/strobe; macro/effect controls. The candidate profile's info says its pixel engine is disabled; this is not current-Show pixel evidence. | `LOCAL_PROFILE_CANDIDATE_UNBOUND` |
| `6 ZEN LEDPar 9c 9Ch Mode A` | `zhong_light@zhong_light_led_par_9ch@9ch_mode_a.xml` — `Zhong Light LED Par 9Ch`, `9Ch Mode A` | Dimmer; RGB/color-mix features; Shutter. No Pan/Tilt/Position feature appears in this candidate profile. | `LOCAL_PROFILE_CANDIDATE_UNBOUND` |
| `7 Atomic 3000 LED Extended` | `martin@atomic_3000_led@extended.xmlp` — `Atomic 3000 LED`, `Extended` | Dimmer; RGB/color-mix features; Shutter; Strobe duration/mode; macro/effect controls. No Pan/Tilt/Position feature appears in this candidate profile. | `LOCAL_PROFILE_CANDIDATE_UNBOUND` |

Every local candidate association above is based on similar model/mode text,
not a Show-exported binding. The BAW type is used by both HYBRID and BEAM
Groups; that shared type does not make their song/case role, importance, or
visual use the same.

## Candidate role eligibility

No B3 role is currently `ELIGIBLE_FROM_VERIFIED_SHOW_CAPABILITY` for any Group.
The reason is technical provenance, not a rejection of the resource:

| Group | Role eligibility from verified current-Show capability | Reason |
| --- | --- | --- |
| 1 HYBRID | `NONE` | no bound channel/profile evidence |
| 2 SPOT | `NONE` | no bound channel/profile evidence |
| 3 BEAM | `NONE` | no bound channel/profile evidence; no safe reason to collapse it into `MOVER_TEXTURE_LAYER` |
| 4 WASH | `NONE` | no bound channel/profile evidence |
| 5 B-EYE | `NONE` | no bound channel/profile evidence |
| 6 LED PAR | `NONE` | no bound channel/profile evidence |
| 7 STROBE | `NONE` | no bound channel/profile evidence; no safe action grammar/behavior proof |

This preserves the candidate-role review's non-ranked hypotheses as
`IDENTITY_ORIGIN_HYPOTHESES_ONLY`. They are not human-approvable eligibility
records yet, and no Group is required to be used.

## Current B3 vocabulary gaps

- B3 roles are abstract visual functions, not Fixture Type capabilities. There
  is no verified capability-to-role resolver for this Show.
- `BEAM_LAYER`, `AERIAL`, and `IMPACT` are not current B3 roles. A readable
  local BAW/Atomic profile must not be collapsed into `MOVER_TEXTURE_LAYER` or
  `TIMING_LAYER` just because the vocabulary is narrower.
- `TIMING_LAYER` cannot be inferred from a local shutter/strobe channel. It
  would additionally require a safe, verified action path for this Show.
- Geometry, semantic position, Effect line behavior, Preset contents, and
  Preset-to-Group applicability remain unavailable; no capability profile may
  silently fill those gaps.

## Practical human review items

This review does **not** ask Zen to set a global fixture priority, permanent
role, or artistic preference. The only useful human decisions are profile
binding decisions for each actual Show Fixture Type:

1. `CONFIRM_EXACT_PROFILE_BINDING` — the Show type is known to be this local
   profile and has not been materially edited.
2. `REJECT_PROFILE_MATCH` — the similarly named local profile is not the Show
   type used by these fixtures.
3. `NEEDS_SHOW_BOUND_READONLY_EVIDENCE` — no reliable confirmation is
   available; retain all attributes and role eligibility as unknown.

Every decision must retain the exact type, profile path/reference, reviewer,
scope, and Show identity. Even a confirmed binding would make only technical
capabilities eligible for future case-specific selection; it would not create
a global role or `case_role_assignment`.

## Readiness and next technical blocker

`REAL_SONG_EXISTING_SHOW_AB_002` is **not ready for an expressive action-delta
experiment**. With no Show-bound capability evidence, it would either repeat
the existing no-action B3 result or guess. The smallest next step is a
read-only, provenance-preserving source that binds each scanned Fixture Type to
its actual channel definition (or explicitly records a human-confirmed exact
profile binding). No MA2 write, Effect probing, preset creation, role
assignment, or Designer activation is authorized by this document.

## Safety

- Production Designer: `UNCHANGED`.
- Experimental Designer: `GUIDANCE_ASSISTED_AB_ONLY`.
- `ZEN_STYLE_PROFILE`: `DEFERRED`.
- `REAL_VENUE_VALIDATION`: `WAIT_FOR_REAL_CASE`.
- MA2 objects modified: `NONE`.
- MA2 write audit: `ZERO_WRITES`.
