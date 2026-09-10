# ZEN MA2 Agent navigation

For substantial work, read these in order:

1. `docs/ZEN_PRODUCT_CONSTITUTION.md`
2. `docs/ZEN_WORKFLOW_CONTRACT.md`
3. The relevant console document, normally `docs/MA2_PROGRAMMING_INTELLIGENCE.md`
4. `docs/CONTINUOUS_LEARNING_POLICY.md` when researching or learning
5. `ZEN_MA2_AGENT_STATUS_REPORT.md`
6. Only reports and fixtures directly relevant to the current task

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
