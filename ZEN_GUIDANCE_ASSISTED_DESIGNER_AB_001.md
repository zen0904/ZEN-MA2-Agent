# Guidance-Assisted Designer A/B Experiment 001

Status: `GUIDANCE_ASSISTED_AB_ONLY / LOCAL_ONLY`. The production
`FirstSongDesigner` is unchanged. No Builder, Resolver, MA2, Telnet, plugin, or
showfile path is invoked.

## Experimental architecture

```text
same Song Analysis + scanned profile
  -> A: unchanged FirstSongDesigner -> baseline typed ZEN_SHOW_PLAN
  -> B: explicit GuidanceAssistedExperimentalDesigner
        + shadow Guidance Context
        + normalized Rig Context
        + CONFIRMED role-to-scanned-Group bindings only
        -> experimental typed ZEN_SHOW_PLAN candidate
```

B first calls the normal deterministic Designer, then replaces cue actions only
where all three things are known: the shadow resource choice, a confirmed role
binding, and a Group that is present in the supplied profile. Abstract roles
are never silently converted into MA2 Groups. If a context has no confirmed
binding, B is intentionally a typed baseline candidate with
`NO_CONFIRMED_BINDING_NO_ACTION_CHANGE`.

Both plans remain `zen.show_plan.v0.1` and contain only existing typed
operations: `CALL_PRESET`, `SET_DIMMER`, and a previously present
`CALL_EFFECT`. There are no raw command fields. The experimental plan marks its
designer metadata with `GUIDANCE_ASSISTED_AB_ONLY`; default routing never
constructs this class.

## Evidence boundary

Song structure, rhythmic events, dynamics, buildup/release, and repeated
sections remain separate signals. Rig Context supplies roles, affordances,
constraints, provenance, asymmetry, and unknowns. Human-confirmed complete
energy states, hierarchy, palette coherence, restraint, and progressive arc
inform the resource-adaptation advisory.

Industry packs remain independently review-gated. No reviewed industry-specific
mapping exists in this experiment that can safely select a typed action, so
industry evidence is retained in the Guidance Context and review trace but does
not manufacture a fixture/preset/effect choice.

The context-dependent candidates—dominant theme color, strong transient impact,
high section delta, restraint between peaks, controlled buildup, and geometric
composition—remain inactive as fixed rules. Rejected/non-global
interpretations remain inactive: `HIGH_IMPACT_ALWAYS`,
`MAXIMALISM_EQUALS_CLUTTER`, `MULTICOLOR_EQUALS_BAD`,
`MINIMALISM_EQUALS_LOW_PREFERENCE`, and `KPOP_YG_EQUALS_GLOBAL_STYLE_RULE`.

## Evaluation method

All cases are `SYNTHETIC_EVALUATION_ONLY`; their profiles and confirmed
role-to-Group bindings exist solely for deterministic A/B comparison. The
baseline Designer is re-run after B for every case and must return exactly the
same baseline plan. B is evaluated independently for musical structure, energy
arc, complete-look quality, hierarchy, palette, restraint/impact, repeated
development, resource use, context fit, non-formulaic design, specificity, and
live usability. There is no weighted total.

### Case 1 — Buildup / Drop, resource-rich user-confirmed layout

**A:** one baseline Group and a normal Focus preset per section; energy changes
are primarily Dimmer/fade/occurrence variation.

**B:**

- Low intro/reset: keep `PRIMARY_FOCUS` plus `COLOR_FIELD`, reduce
  `DENSITY_LAYER`, omit `TIMING_LAYER` and `MOVER_TEXTURE_LAYER`.
- Medium builds: add density and texture while reducing timing.
- High drops: use all explicitly bound roles, but only at the actual high
  sections; no newly created effect or maximum-impact rule is introduced.

**Delta:** B creates typed Group-targeted layer allocation and omission rather
than only changing the original Group's level. The two drops keep shared intent
but are still governed by song occurrence and current resource composition.

**Result:** `B_BETTER` under the structural rubric. This is not an aesthetic
approval; a human still decides whether the particular palette/layer balance is
desirable.

### Case 2 — Restrained / Minimal, medium assisted floor-only proposal

**A:** retains the baseline Group/preset pattern across the restrained song.

**B:** low intro/verse keeps limited focus/color, reduces density, and
intentionally omits timing/texture. Medium refrains add only available density
and texture. The candidate does not create a chase/effect merely because a
high-energy strategy exists elsewhere.

**Delta:** the quiet state is a role composition with negative space—not the
same high look at a lower Dimmer level.

**Result:** `B_BETTER` structurally, because the typed candidate records
intentional omissions and different complete low/medium role sets. Actual
minimal-show taste remains a human review question.

### Case 3 — Buildup / Drop, LED-only assisted rig

**A:** baseline ignores the limited role vocabulary and uses its one generic
Group.

**B:**

- Low: `COLOR_FIELD` only, with density/timing deliberately absent.
- Medium: color plus `DENSITY_LAYER`.
- High: color, density, and `TIMING_LAYER`.

**Delta:** B changes existing typed Group/preset/dimmer intent using only the
confirmed synthetic LED role bindings. It requests no beam, gobo, mover,
position, or aerial language. It does not require geometric relationships.

**Result:** `B_BETTER` structurally: it supplies a real LED-capable composition
instead of a generic unavailable-resource warning.

### Case 4 — Buildup / Drop, asymmetric user-confirmed layout

**A:** baseline has no way to distinguish the confirmed uneven layout.

**B:** preserves the user-confirmed layout, chooses only the bound focus/color/
texture/density/timing roles, and contains no mirror or symmetry request.

**Delta:** B makes the asymmetry visible in context and refuses physical
rebalance. It cannot yet judge the actual visual composition because no real
venue geometry or human aesthetic review is available.

**Result:** `MIXED`. Context preservation is an improvement, but physical
asymmetry design quality remains unproven.

## Cue-by-cue review contract

The evaluator generates a record for every cue containing section, baseline
typed actions, B typed actions, changed/unchanged status, selected/reduced/
omitted roles, substitutions, evidence references, and `HUMAN_REVIEW=UNSET`.
This is the review surface; no human decision is pre-filled.

For example, a low `INTRO` in Case 3 changes from its generic baseline action
set to a color-field action only, records density/timing as omitted/reduced, and
cites the complete-energy-state advisory. A high `DROP` records color/density/
timing as selected. These are typed action deltas, not programming prose.

### Review matrix — Case 1

| Section | Baseline A | Guidance-assisted B | Why | Human review |
|---|---|---|---|---|
| INTRO | generic focus/group action | keep focus/color; reduce density; omit texture/timing | low energy, headroom, complete quiet state | UNSET |
| BUILD 1 | same Group with energy level | add density/texture; timing reduced | BUILD signal and dynamic rise | UNSET |
| DROP 1 | same Group high level | all bound roles selectively active | hit + high energy, controlled impact | UNSET |
| RESET | generic lower level | return to focus/color composition; omit texture/timing | reset and negative space | UNSET |
| BUILD 2 | repeated baseline role | same medium palette/focus basis with resource composition | repeated development without automatic maximum | UNSET |
| DROP 2 | repeated baseline high level | bounded high-role composition again | repeated hit; no universal larger-every-time rule | UNSET |
| OUTRO | generic lower level | focus/color with deliberate omissions | release and hierarchy | UNSET |

### Review matrix — Case 2

| Section | Baseline A | Guidance-assisted B | Why | Human review |
|---|---|---|---|---|
| INTRO | generic focus/group action | focus/color; density reduced; timing/texture omitted | complete low-energy state and negative space | UNSET |
| VERSE 1 | same baseline action pattern | low role composition remains intentionally sparse | restrained song context | UNSET |
| REFRAIN 1 | energy-raised baseline | medium focus/color/density/texture; timing reduced | a different complete medium look, not just level | UNSET |
| VERSE 2 | repeated baseline role | returns to sparse low role set | verse/refrain relationship, not fixed escalation | UNSET |
| REFRAIN 2 | repeated baseline role | repeats medium family with song occurrence trace | meaningful relation without forced maximalism | UNSET |
| INSTRUMENTAL | generic baseline action | sparse low composition | visual rest remains allowed | UNSET |
| OUTRO | generic lower level | focus/color with omitted nonessential roles | final release | UNSET |

### Review matrix — Case 3

| Section | Baseline A | Guidance-assisted B | Why | Human review |
|---|---|---|---|---|
| INTRO / RESET / OUTRO | generic Group action | `COLOR_FIELD`; density/timing absent | LED-only quiet look and intentional negative space | UNSET |
| BUILD 1 / BUILD 2 | generic Group action | color plus density | LED-capable medium development | UNSET |
| DROP 1 / DROP 2 | generic Group action | color + density + timing | high state via available timing/density, not beam/mover language | UNSET |

### Review matrix — Case 4

| Section state | Baseline A | Guidance-assisted B | Why | Human review |
|---|---|---|---|---|
| LOW (INTRO / RESET / OUTRO) | generic Group action | confirmed role composition with omissions | preserve user layout and quiet imbalance | UNSET |
| MEDIUM (BUILD 1 / BUILD 2) | generic Group action | focus/color/density/texture; no mirror request | declared asymmetry is context, not a defect | UNSET |
| HIGH (DROP 1 / DROP 2) | generic Group action | all confirmed bound roles; no physical rebalance | high-energy intent without claiming a symmetric rig | UNSET |

## Complete look and repeated section findings

B gives the resource-rich/medium and LED-only cases distinct low, medium, and
high action-role signatures. The restrained case has distinct low and medium
complete states. It does not force every song into a monotonic A-to-B-to-C arc;
the supplied section identity, rise/fall, reset, hit, and repeated-section
signals remain intact. Repeated roles are not automatically copied or made
universally larger.

## Honest limitations

- B does **not** win by definition. The asymmetric case is `MIXED`: safe
  context preservation alone does not prove a visually better composition.
  An `EXISTING_SHOW` Rig Context with no confirmed role-to-Group binding is
  intentionally `NO_MEANINGFUL_DIFFERENCE`; B retains the baseline candidate
  rather than guessing a resource allocation.
- The bindings and profiles are synthetic evaluation material, not live MA2
  rig mappings.
- B has no verified typed mechanism for new position, gobo, color-effect, or
  movement-effect creation; it never invents one.
- Industry evidence has no reviewed action-level translation yet.
- No live lighting output, venue, camera, performer, or audience review has
  occurred.
- `EXISTING_SHOW` without confirmed role bindings correctly yields
  `NO_MEANINGFUL_DIFFERENCE`; B does not pretend to improve it.

## Readiness

`READY_FOR_HUMAN_AB_REVIEW` for the four bounded synthetic comparisons only.
This is not production activation, Guidance-Assisted Designer A/B runtime
activation, MA2 build readiness, or real venue validation. `ZEN_STYLE_PROFILE`
remains deferred; `REAL_VENUE_VALIDATION=WAIT_FOR_REAL_CASE`.
