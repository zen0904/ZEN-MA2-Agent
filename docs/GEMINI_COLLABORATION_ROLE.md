# Gemini Collaboration Role

Status: **ACTIVE ARCHITECTURE POLICY**

This document defines where Gemini fits inside ZEN MA2 Agent collaboration.
It does not make Gemini the ZEN Primary Brain, grant MA authority, or change the
operator-facing ZEN workflow.

## 1. Architectural position

Gemini is a **specialized worker/provider** under the existing
`STRONG_PRIMARY_BRAIN_MATURE_UPSTREAM_001` invariant.

Canonical shape:

```text
Operator
  -> ZEN / Strong Primary Brain
       -> architecture, intent, artistic judgment, task decomposition
       -> specialized worker dispatch
            -> Gemini
                 - large-context repository scan
                 - Vision / image / video evidence extraction
                 - bounded implementation after the contract is frozen
                 - regression / evidence comparison
            -> Codex / other coding worker
                 - bounded implementation and tests
       -> reviewer / acceptance
       -> deterministic ZEN Compiler / Safety / Preview / Human Approval
       -> Builder / Field Core / native readback
```

Gemini is not a permanent artistic committee member and does not become a
second source of product authority merely because it can process a large
context window.

## 2. Preferred Gemini duties

Use Gemini when one or more of these characteristics dominate the task:

- large repository or many-file context must be scanned before a bounded task
  is cut;
- visual evidence must be extracted from images, video, screenshots, GDTF/MVR
  or previs-related material;
- a mechanically bounded implementation has already been specified and can be
  completed without inventing architecture, artistic behavior or operator
  workflow;
- an independent regression/evidence comparison is useful before acceptance;
- a second model perspective has high information value and the result will be
  reviewed rather than treated as truth.

## 3. Duties Gemini must not own

Gemini must not independently:

- replace the ZEN Strong Primary Brain;
- change the ZEN Operator Workflow;
- make final artistic lighting decisions when those decisions alter the
  established artistic contract;
- change architecture or safety invariants without explicit owner approval;
- approve its own implementation for production;
- acquire MA2/MA3 execution authority;
- emit or forward raw MA commands around the deterministic Builder boundary;
- bypass Preview, Human Approval, protected-object policy, Field Core or native
  readback;
- write provider credentials or secrets into the repository.

`MA2_WRITES=0` for Gemini reasoning/worker activity unless a separately
approved ZEN execution path reaches the existing deterministic write boundary.
Gemini itself never owns that boundary.

## 4. Parallel work policy

Parallel reasoning is allowed. Parallel uncontrolled editing is not.

Safe parallel pattern:

```text
ChatGPT / Primary Reviewer
  -> architecture, contract, acceptance criteria, review

Gemini
  -> read-only scan, Vision, evidence extraction, or bounded worker task

Codex
  -> implementation when assigned
```

When Gemini performs implementation:

1. the task contract must already be frozen;
2. it must use an isolated branch/worktree when another coding agent is active;
3. no two agents may edit the same source path concurrently;
4. the implementation must stop at a reviewable commit;
5. tests/evidence must be recorded;
6. another reviewer performs acceptance;
7. Git commit state, not chat prose, is the handoff.

A timeout or ambiguous worker result is not permission to replay the same
mutation through another agent without first proving the previous mutation did
not occur.

## 5. Current repository integration

Gemini already exists in repository infrastructure as:

- provider example slot 1 in `config/providers.free_pool.env.example`;
- provider entity `google-gemini` in
  `data/ZEN_RUNTIME_ENTITY_REGISTRY.json`.

Those entries establish provider/runtime visibility only. They do not grant the
architectural duties above by themselves.

This policy formally adds Gemini to the collaboration topology while preserving
the existing provider router, Strong Primary Brain invariant, deterministic
execution authority, and operator workflow.

## 6. Model/version policy

Do not encode a specific Gemini model as permanent architectural truth.

The configured model may change as provider availability, capability, quota and
pricing change. Select the concrete model at runtime/configuration time, while
keeping this role contract stable.

## 7. Acceptance rule

Gemini output is evidence or a candidate artifact, not authority.

For any change that affects production behavior, architecture, artistic
behavior, safety, or MA execution, acceptance remains with the existing ZEN
review/approval chain and the project owner where required.
