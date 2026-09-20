# ZEN MA2 Agent navigation

For substantial work, read these in order:

1. `ZEN_AUDIT_AND_FIXES_STATUS_002.md` -- current status; supersedes older
   status reports. Read this before any older `ZEN_*_00N.md` report.
2. `docs/CODING_AGENT_COLLABORATION.md` -- required if you are Claude Code or
   Codex: how the two coexist on this repo, and which tasks need the project
   owner present versus which are safe to run unattended.
3. `docs/MULTI_AGENT_DESIGN_PLAN.md` -- the implemented four-role Designer
   pipeline and its current multi-provider extension boundary, if the task
   touches autonomous design.
4. `ZEN_MULTI_PROVIDER_PARALLEL_POOL_001.md` -- current provider-pool,
   FREE_FIRST, parallel Designer/Critic, and lightweight-local-fallback state.
5. `docs/ZEN_PRODUCT_CONSTITUTION.md`
6. `docs/ZEN_WORKFLOW_CONTRACT.md`
7. The relevant console document, normally `docs/MA2_PROGRAMMING_INTELLIGENCE.md`
8. `docs/CONTINUOUS_LEARNING_POLICY.md` when researching or learning
9. Only reports and fixtures directly relevant to the current task

For a continuation, also read `docs/ZEN_DEVELOPMENT_WORKFLOW.md`,
`docs/ZEN_PRODUCT_ROADMAP.md`, and `data/zen_project_control.json`. They state
the active milestone, next acceptance gate, and explicitly deferred work; do
not choose a new task simply because it was discussed most recently.

Do not recursively read every historical report. Reports are evidence/archive;
the latest verified committed repository state is the default source of truth.
If the user says “continue”, “keep going”, or “next” in this project, recover
state from this repository and continue without requiring old handoffs.

The user-facing product is one ZEN MA2 Agent. Internal modules may remain
specialized, but routing is automatic. Designers emit typed intent only;
Builder/compiler is the sole MA2 command boundary and Preview/Approval precede
writes. Preserve the stable operator contract and treat workflow changes as
explicit proposals.

Never guess undocumented MA2 behavior, mutate production objects during
research, or commit caches/build outputs. Check current status and safety
boundaries before acting.
