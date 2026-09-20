# SHEESH Current Show Redesign 001

**Status:** AUTHORIZED CURRENT EXPERIMENT  
**Owner decision date:** 2026-09-20  
**Target:** BABYMONSTER — SHEESH  
**Experiment ID:** `SHEESH_CURRENT_SHOW_REDESIGN_001`

## Owner decision

The currently loaded grandMA2 Show is an explicitly designated disposable Test
Show. Zen has authorized this experiment to redesign the current Stage/3D
geometry and the Agent-owned SHEESH test content using only fixtures that
actually exist in that Show.

This explicit owner decision supersedes the earlier
`SHEESH_TEST_SHOW_VISUAL_OPERATOR_REVIEW_001` gate that said the existing
SHEESH Test Show should not be overwritten before review.

This authorization is **not** production authorization and must not be
generalized to another Show.

## Execution boundary

`CODEX_ARTISTIC_INTERVENTION = NONE`

CX / Codex / Claude Code are not the lighting designer. They may:

- verify repository and runtime state;
- snapshot the currently loaded MA2 Show;
- read verified fixture inventory, Groups, capabilities and current geometry;
- invoke the existing ZEN multi-agent runtime;
- preserve diagnostics and artifacts;
- execute only already-supported, bounded ZEN write paths after all existing
  safety / preview / approval requirements for this Test Show are satisfied;
- report capability gaps exactly.

They may not:

- choose colors, fixture placement, spatial roles, cue structure or other
  artistic content themselves;
- repair or rewrite ZEN artistic output;
- invent fixtures or capabilities;
- invent raw MA2 commands when a supported write adapter does not exist;
- bypass Safety, typed validation, Resolver/Builder boundaries or read-back.

## Hard safety constraints

Use only the fingerprinted current Test Show.

Allowed scope:

- Stage View / 3D geometry for existing fixtures;
- fixture XYZ and supported orientation fields when the current Show exposes a
  verified path;
- Agent-owned Groups, Presets, Sequences and Executors;
- Agent-owned SHEESH experiment content.

Forbidden:

- DMX Patch or Address changes;
- Fixture ID changes;
- Fixture Type changes;
- adding imaginary fixtures;
- deleting real fixture inventory;
- Fixture 9999;
- unrelated existing Show objects;
- production Show write authorization.

MA text boundaries remain ASCII-only. Unsupported non-ASCII MA text or raw
commands fail closed.

## Required order

1. Verify local/USB repository HEAD against current `origin/main`.
2. Verify the currently loaded MA2 Show matches the expected Test Show.
3. Save an original read-only snapshot sufficient for rollback/audit.
4. Read real fixture inventory, Group inventory, capabilities and current
   Stage/3D geometry.
5. Produce a ZEN-owned spatial design artifact **before** SHEESH lighting
   design. Spatial design must use only verified existing fixtures and must not
   invent capability.
6. Feed the verified spatial result into the ZEN SHEESH design run.
7. Run `RESEARCHER -> LIGHTING_DESIGNER -> CRITIC -> FINALIZER` through the
   existing ZEN provider runtime. No coding-agent artistic edits are permitted.
8. Validate schema, evidence and secret boundaries.
9. Write only the parts for which an already-supported safe ZEN/Test-Show write
   path exists.
10. Read back every write and produce the experiment report.

If a required Stage/3D or autonomous-design write path is absent, stop that
portion and record a capability gap. Do not synthesize a raw MA workaround.

## Spatial-design requirement

The spatial proposal is upstream of song lighting design. Do not design SHEESH
first and then arrange fixtures to fit the design.

The spatial stage should reason about, where supported by verified Show data:

- spatial role;
- X / Y / Z;
- orientation / facing direction;
- stage-left / stage-right balance;
- height and depth layers;
- symmetry or intentional asymmetry;
- crossing and convergence;
- visual corridors;
- aerial depth;
- negative space;
- performer-zone relationships;
- effect hierarchy.

A rectangular warehouse-style grid is not a default. Repetition is allowed when
it has a design reason.

## Existing implementation evidence

The previous bounded Test Show build
`ZEN_REAL_MA2_TEST_SHOW_SHEESH_BUILD_001.md` verified that MA2 `Move3D`
coordinates can be written and read back for this fixture set, including the
special Atomic subfixture handling.

That earlier builder used a fixed
`TEST_STAGE_LAYOUT_SHEESH_001` supplied by code/data. It does **not** prove
that the current autonomous runtime can generate a spatial artifact or resolve
that artifact through a formal autonomous-design Resolver/Builder.

Therefore the following are not assumed:

- autonomous spatial role/stage support exists;
- `zen.autonomous_design.v0.1` has a verified geometry Resolver;
- the previous fixed-layout test builder is automatically suitable as a generic
  spatial write adapter.

CX must inspect current code and report the real supported boundary.

## Audio authority

If a real SHEESH audio file is supplied, that audio is arrangement truth. If
no audio is available, do not invent exact timestamps or Timecode placement.

## Required report

Return at least:

- `CURRENT_SHOW_IDENTIFIED`
- `CURRENT_SHOW_FINGERPRINT`
- `FIXTURE_COUNT`
- `FIXTURE_TYPES`
- `GROUP_COUNT`
- `CURRENT_STAGE_GEOMETRY_READABLE`
- `ORIGINAL_GEOMETRY_SNAPSHOT_SAVED`
- `SPATIAL_PROPOSAL_CREATED`
- `SPATIAL_WRITEBACK_SUPPORTED`
- `SPATIAL_WRITEBACK_PERFORMED`
- `PROPOSED_FIXTURE_COUNT`
- `RESEARCHER_PROVIDER`
- `DESIGNER_ATTEMPTED_SLOTS`
- `DESIGNER_ACCEPTED_SLOTS`
- `DESIGNER_CANDIDATE_COUNT`
- `CRITIC_ATTEMPTED_SLOTS`
- `CRITIC_ACCEPTED_SLOTS`
- `CRITIC_CANDIDATE_COUNT`
- `FINALIZER_PROVIDER`
- `FINAL_SCHEMA_VALID`
- `EVIDENCE_VALID`
- `SECRETS_LEAKED`
- `MA2_WRITES`
- `MA2_WRITE_SUMMARY`
- `CAPABILITY_GAPS`

Also explain in Traditional Chinese:

1. original Stage View arrangement;
2. ZEN spatial redesign;
3. the spatial design reasoning contained in ZEN's artifact;
4. SHEESH overall visual concept;
5. three strongest spatial choices;
6. three strongest lighting choices;
7. what Critic changed or rejected;
8. remaining weaknesses;
9. exact MA Test Show changes actually performed.

## Success definition

The experiment is not successful merely because providers return valid JSON or
tests pass.

The evidence target is whether ZEN can inspect a real existing rig, produce a
coherent spatial design from that rig, use that spatial design as upstream
context for SHEESH, survive Critic/Finalizer, and safely realize every supported
portion in the authorized Test Show without coding-agent artistic intervention.
