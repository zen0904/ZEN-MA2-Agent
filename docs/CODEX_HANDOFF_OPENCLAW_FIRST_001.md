# Codex Handoff — ZEN OpenClaw-First Integration 001

Status: **READY FOR LOCAL EXECUTION WHEN DEVELOPMENT HOST IS ONLINE**

Start from the current `origin/main` after fetching and reviewing any newer commits.

## Objective

Adopt OpenClaw as the primary ZEN operator interface without making OpenClaw a safety-critical dependency.

Target boundary:

```text
OpenClaw Control UI / Chat
        ↓
ZEN OpenClaw adapter/plugin
        ↓
ZEN versioned local API
        ↓
ZEN Field Core
        ├─ MA Bridge
        ├─ Safety
        ├─ Resolver / Builder
        ├─ Worker Router
        └─ Artifact/Show State
```

Read first:

- `docs/ZEN_OPENCLAW_FIRST_UI_ARCHITECTURE.md`
- `docs/ZEN_FIELD_HOME_DISTRIBUTED_ARCHITECTURE.md`
- existing MA-initiated architecture documents
- current runtime/provider tests before touching implementation

## Hard constraints

Do not modify artistic prompts, lighting knowledge, retrieval semantics, model behavior, cue design, colors, positions, fixture artistic roles, or other artistic content.

Keep:

```text
CODEX_ARTISTIC_INTERVENTION=NONE
MA2_WRITES=0
```

Do not expose arbitrary shell execution, arbitrary filesystem access, raw MA command execution, or MA credentials through OpenClaw.

OpenClaw failure must not make ZEN Field Core unavailable.

## Phase A — Local OpenClaw verification

On the powered development computer:

1. Inspect OS, Node, npm/pnpm, Git.
2. Use current official OpenClaw installation guidance.
3. Install OpenClaw safely.
4. Record exact installed version.
5. Run safe help/doctor/status diagnostics.
6. Start Control UI localhost-only if possible without fake credentials.
7. Do not invent model keys or account credentials.
8. If onboarding requires user credentials, mark that step `BLOCKED_USER_CREDENTIAL` and continue repository work.

Record:

```text
OPENCLAW_TESTED_VERSION=<exact version>
```

Do not configure production systems to track untested `latest` automatically.

## Phase B — Repository integration

Create a clean integration boundary, preferably:

```text
integrations/openclaw/
```

Use the plugin/extension mechanism supported by the exact installed OpenClaw version. Do not patch global OpenClaw package files or edit `node_modules` manually.

The adapter should be thin. Core ZEN logic remains in ZEN.

Initial tool/status surface may include:

```text
zen.status
zen.worker.status
zen.ma.status
zen.artifact.latest
zen.design.request
zen.preview
zen.approve
```

Only implement operations that have real backend support. Others must return structured `NOT_IMPLEMENTED`.

## Phase C — ZEN local API

Create or consolidate a versioned, typed, localhost-first API for the OpenClaw adapter.

Minimum useful read-only state:

- Field Core health
- MA Bridge state
- MA connection state if known
- remote AI availability
- Worker states
- pipeline role states
- latest artifact identity/metadata

Preserve `UNKNOWN` rather than inventing state.

Default sensitive binds must remain localhost-only unless explicitly configured otherwise.

## Phase D — OpenClaw ZEN surface

Use OpenClaw as the UI shell. Do not build a competing full frontend.

Desired first view:

```text
ZEN CONTROL

FIELD CORE
MA BRIDGE
MA2
REMOTE AI
WORKER A
WORKER B

PIPELINE
Researcher
Designer
Critic
Finalizer

Latest artifact
Recent bounded status/log summary
```

Initial safe actions:

- Refresh Status
- Worker Status
- MA Status
- Open Latest Artifact

Design/Preview/Approve actions may exist only if backed by typed ZEN APIs; otherwise return `NOT_IMPLEMENTED`.

No production execute/live-write button in this phase.

## Phase E — Failure isolation

Test explicitly:

```text
OPENCLAW_AVAILABLE=NO
FIELD_CORE_AVAILABLE=YES
```

when ZEN local core is healthy.

Stopping the OpenClaw UI/plugin must not directly stop or invalidate:

- Bridge
- Safety
- Resolver
- Builder
- Worker registry
- artifact cache
- local backend state

## Phase F — Three-machine compatibility

Keep the current intended deployment:

```text
Field Node:
2012 Mac mini / Ubuntu / i7-3615QM / 8 GB

Worker A:
Ubuntu / 16 GB / GTX 1650 4 GB

Worker B:
Ubuntu / 16 GB / weak GPU / exact model UNKNOWN
```

Only the Mac mini travels.

OpenClaw is intended to live on or alongside the Field Node operator surface, but actual Mac mini deployment is a separate controlled step after local compatibility is verified.

## Testing

At minimum verify:

- ZEN backend imports/runs without OpenClaw installed or running
- adapter handles backend unavailable state cleanly
- status schema is bounded and typed
- unknown state remains unknown
- no generic shell tool exists
- no raw MA command tool exists
- no LLM is required just to launch/read status
- no MA write occurs
- existing Python tests remain green
- OpenClaw plugin package builds/tests for the pinned OpenClaw version
- plugin loads through the supported mechanism
- Control UI renders the ZEN surface if browser verification is available

Do not run a long Qwen smoke test in this task.

## Deliverables

Update/create as appropriate:

- `integrations/openclaw/`
- compatibility/version metadata
- ZEN local API implementation/tests
- OpenClaw adapter tests
- `docs/ZEN_OPENCLAW_INTEGRATION.md`
- `docs/ZEN_UBUNTU_MULTI_NODE_DEPLOYMENT.md` if deployment assumptions need updating
- existing architecture docs only where necessary

## Final report

Report:

```text
START_HEAD=
END_HEAD=
OPENCLAW_INSTALLED=
OPENCLAW_TESTED_VERSION=
OPENCLAW_GATEWAY_STATUS=
OPENCLAW_CONTROL_UI_STATUS=
ZEN_OPENCLAW_PLUGIN=
ZEN_LOCAL_API=
ZEN_BACKEND_INDEPENDENT=YES|NO
OPENCLAW_REQUIRED_FOR_FIELD_CORE=NO
FIELD_CORE_WITH_OPENCLAW_OFFLINE=
MA2_WRITES=0
QWEN_CALLED=NO
CLOUD_ARTISTIC_USE=NO
ARTISTIC_PROMPTS_CHANGED=NO
KNOWLEDGE_CHANGED=NO
CODEX_ARTISTIC_INTERVENTION=NONE
TESTS=
BLOCKED=
DEFERRED=
```

Commit and push only after reviewing the diff and running the available tests. Do not force-push. Stop after this task; do not proceed automatically into CUDA/Qwen deployment or real MA2 writes.
