# Codebase Memory MCP Integration

Status: APPROVED DEVELOPMENT INFRASTRUCTURE
Owner decision date: 2026-09-28
External project: https://github.com/DeusData/codebase-memory-mcp

## Purpose

ZEN may use Codebase Memory MCP (CBM) as a local structural code-intelligence and
persistent code-memory layer for substantial repository work.

Its intended job is to reduce repeated file-by-file rediscovery by exposing indexed
architecture, symbols, imports, call/dependency relationships, impact analysis,
targeted code search, change mapping, and index-coverage evidence to coding agents.

CBM is development infrastructure. It is not part of the operator-facing ZEN MA2
workflow and it is not part of the MA2 execution authority chain.

## Authority boundary

CBM never supersedes:

1. the committed Git repository and current working tree;
2. `AGENTS.md`;
3. `data/zen_project_control.json`;
4. current Product / Workflow / Safety contracts;
5. source files and tests used to verify an implementation;
6. native MA2 evidence and deterministic Builder/readback boundaries.

A graph result is an index-derived observation, not an authorization to mutate code,
Show state, MA2 objects, provider credentials, or operator workflow.

No CBM tool may become a path from an LLM directly to MA2. The existing rule remains:

```text
LLM / coding intelligence
        ↓
reviewed source change or artistic intent
        ↓
ZEN deterministic boundary
        ↓
Preview + explicit approval where required
        ↓
verified execution/readback
```

## Default use

When CBM is available, a coding agent SHOULD prefer it for substantial codebase
exploration before broad recursive file reading, especially for:

- architecture and subsystem discovery;
- locating implementations from concepts/symbols;
- call-chain and dependency tracing;
- impact analysis before refactors;
- finding likely tests and callers;
- cross-file relationship questions;
- comparing indexed structure across changes;
- checking whether an apparent absence may instead be an indexing-coverage gap.

After CBM narrows the target, verify consequential claims against the actual current
source, tests, git diff, or native evidence before changing behavior.

For small known-file edits, exact-path reads remain simpler and are preferred.

If CBM is unavailable, stale, or reports incomplete coverage, continue with normal
repository search/read tools. CBM availability must never block ordinary project work.

## Coverage and uncertainty

“No matching graph node/edge” is not proof that code or behavior does not exist.

Before using an absence as a design or safety conclusion:

- inspect CBM index coverage when practical;
- search the actual repository;
- read the relevant implementation;
- run the relevant tests or evidence checks.

Treat unresolved index gaps as uncertainty, not as verified absence.

## Installation / configuration policy

CBM is optional local development infrastructure, not a runtime dependency of ZEN.

Initial deployment should be conservative:

- inspect the upstream release/source before installation;
- prefer a binary-only / `--skip-config` first pass when auditing a new machine;
- review any proposed coding-agent configuration or instruction changes before
  activating them;
- preserve this repository's `AGENTS.md` and ZEN contracts as project authority;
- do not commit CBM indexes, caches, daemon logs, generated graphs, or machine-local
  configuration to this repository;
- do not weaken protected-object, provider, approval, or write/readback controls to
  make CBM integration easier.

Upstream installation may configure supported coding-agent clients. Any generated
global/client instruction is subordinate to this repository's committed rules.

## Acceptance gate for a ZEN development machine

A machine may be recorded as CBM-enabled only after all of the following are true:

1. CBM installs and starts locally.
2. The ZEN repository indexes successfully.
3. Architecture/search/trace queries return plausible results for known code paths.
4. Index coverage is checked for the relevant languages/areas.
5. Indexing/configuration produces no unintended repository diff.
6. Existing ZEN tests remain unchanged/passing for the touched scope.
7. `MA2_WRITES=0` for the installation/indexing/integration verification.
8. No product runtime dependency on CBM has been introduced.

## Architectural placement

```text
Committed ZEN repository
  ├─ AGENTS / Constitution / Workflow / Current State  ← semantic authority
  ├─ source + tests                                    ← implementation authority
  │
  └─ Codebase Memory MCP                              ← structural code memory
        ↓
     Codex / Claude / other coding agents
        ↓
     reviewed source changes
        ↓
     existing ZEN verification and safety boundaries
```

This separation is intentional. CBM can make coding agents less forgetful without
becoming another autonomous product brain, another Source of Truth, or another MA2
write path.
