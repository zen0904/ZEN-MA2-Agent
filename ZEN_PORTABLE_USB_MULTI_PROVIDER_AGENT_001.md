# Portable USB Multi-Provider Agent 001

## Result

The portable installation root is `ZEN_HOME`, discovered by the Windows and
macOS launchers from their own location. The portable working copy is
`ZEN_HOME/repo/ZEN-MA2-Agent` and retains `.git`; mutable logs, context,
projects, cache, and USB-local secrets live outside that Git tree.

Three replaceable provider slots and `PRIMARY_ONLY`, `FALLBACK`, and `ROUTED`
policies are implemented. The current HTTP adapter is deliberately limited to
OpenAI-compatible Chat Completions; native adapters can be added without
changing the Designer or Builder boundary.

The autonomous path is strict:

```text
USB provider config -> Provider Router -> real LLM -> typed zen.autonomous_design.v0.1
-> deterministic validation -> later compiler/approval -> MA2
```

Provider output containing raw MA2, Telnet, Lua, shell, or command fields is
rejected. It receives a bounded, provenance-bearing context containing current
project constraints, Show-bound technical evidence, virtual-rig evidence,
external lighting knowledge, source provenance, the prior SHEESH test artifact,
and the operator/product constraints. The legacy deterministic Designer is not
presented as autonomous output.

## Portable self-test

The Windows USB runtime was bootstrapped under
`ZEN_HOME/runtime/windows/venv`. The provider self-test was run through the
USB launcher. At this point all three configuration slots are blank, so the
truthful outcome is:

```text
AUTONOMOUS_DESIGNER_AVAILABLE = NO
REAL_ZEN_LLM_PROVIDER = NO
```

No API key, endpoint, or secret value is recorded here. No real provider
inference, autonomous artistic plan, SHEESH redesign, or MA2 write occurred.
This is fail-closed: Codex did not substitute artistic content.

## How to unblock the real autonomous build

On the USB, fill at least one eligible slot in:

`ZEN_HOME/secrets/providers.private.env`

For the existing adapter, set `TYPE=OPENAI_COMPATIBLE`, `MODEL`, `BASE_URL`,
and `API_KEY`, then run:

```text
run_zen_windows.cmd --provider-self-test
```

Only a successful structured real-provider probe permits the SHEESH autonomous
design run. The run will write its non-secret design JSON and provenance to
`ZEN_HOME/projects/runs/`; it does not itself write MA2.

## Safety status

- `PORTABLE_USB_ZEN_AGENT`: YES
- `MULTI_PROVIDER_ROUTER`: YES
- `DETERMINISTIC_DESIGNER_ONLY`: NO (available only as clearly non-autonomous legacy utility)
- `KNOWLEDGE_USED_IN_REAL_DESIGNER_CONTEXT`: READY, pending a real provider
- `CODEX_ARTISTIC_INTERVENTION`: NONE
- `AUTONOMOUS_DESIGNER_AVAILABLE`: NO (no configured provider)
- MA2 writes in this task: `0`
- Fixture 9999: untouched
- Existing test and protected MA2 objects: untouched

The next action after a successful provider self-test is the user-authorized
SHEESH autonomous design and Test Show build; no Codex-authored artistic
fallback is permitted.
