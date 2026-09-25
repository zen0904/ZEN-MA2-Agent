# Bounded Position Application Evidence PoC

Status: **read-only discovery and non-executable Preview foundation**. No
Position Group/Preset binding is verified by this implementation alone. No
MA2 Show write, provider call, or owner approval occurred in this gate.

## Current Show discovery (grandMA2 onPC 3.9.60)

The supported local read path was used on 2026-09-26 against the disposable
Test Show. A fresh `List Group`, `List Fixture`, Group Export, FixtureType
Export, `List Sequence`, `List Preset All`, and bounded `List Preset 2.1`
returned the following scoped facts:

- Eight Groups are present. Group 1 has exact parent selection refs
  `101,102,103,104,105,106,108,107`; Groups 2–5 also have parent refs.
  Group 6 is LED PAR and lacks verified POSITION channels. Historical Group 7
  is `.1` only and must not be repaired. Agent-owned Group 8 is `.2` only.
- The verified FixtureType profiles for Groups 1–5 contain POSITION capability.
  FixtureTypes for Groups 6–8 do not show POSITION in their exported profiles.
  This is technical capability, **not Preset applicability**.
- `List Preset Position` returned `Error #14: OBJECT DOES NOT EXIST` on this
  machine. The supported `List Preset All` result nevertheless contains 19
  current Position-pool references: `2.1`–`2.11`, `2.24`, `2.25`, and
  `2.27`–`2.32`. A direct `List Preset 2.1` confirmed exact ref `2.1`, type
  `Position`, label `HOME`. This verifies identity only, not Group applicability.
- A fresh conservative scanned Show identity was recorded in the generated
  machine-local Preview. It is a partial profile fingerprint, not a console
  Show UUID. The Preview is invalid if the scanned identity changes.
- The existing native Sequence Export parser exposes CueData `fixture_id`,
  `subfixture_id`, `attribute_name`, and Preset `No` components. This is a
  candidate content-readback grammar. Command acceptance or Cue metadata alone
  cannot establish Position application.

## Engineering boundary

`zen.position_application_poc_preview.v0.1` is a deterministic, explicitly
**non-executable** Preview. It binds a fresh exact Group Export membership, a
show-bound POSITION technical profile, exact current Preset type/ref/label,
and a first-free non-protected Sequence candidate. It describes one typed
`CALL_PRESET` action and the existing deterministic MA2 command grammar. It
does not register an approval action, send a command, allocate an Executor, or
authorize a write. The Group 1 / Preset 2.1 candidate is an engineering probe,
not an aesthetic recommendation or a Designer resource.

`zen.position_preset_application_binding.v0.1` can be derived only **after a
future separately owner-approved probe** has actually written a new Agent-owned
test Cue and native Sequence Export proves the exact Preset reference on PAN
or TILT channel rows for every exact selected member, with no foreign member.
The binding retains scanned Show identity, exact Group name/member set,
Preset type/ref/label, Sequence/Cue, native export SHA-256, matched exact
channel refs and attributes, and MA2 version family. A parent ref is accepted
only for a single verified subfixture; multi-instance dotted refs require
their own exact subfixture-level readback. This proof is never inferred from a
FixtureType label or root-level capability alone.

The existing `artistic_resources.py` path accepts a POSITION binding only when
the exact proof schema and current Show/Group/Preset identity all match. Other
dimensions keep their existing rules. The model-facing contract and generic
artistic compiler continue to reject any unrelated Position Preset or Group.
Show, membership, label, ref, type, or capability drift fails closed.

## Next interactive step

Owner may review the machine-local read-only Preview and, in a separate
interactive session, explicitly authorize a bounded POC execution path. That
future implementation must re-read the target Group, Preset, Sequence vacancy,
and Show identity immediately before any write, use the existing Preview /
Human Approval / Builder boundary, read back the exact Cue content, and scope
rollback only to the newly created Agent-owned Sequence after identity proof.
No existing Sequence, Executor, Group, Preset, geometry, Patch, Address,
Fixture identity/type, or Fixture 9999 may be changed. Until then, POSITION
application remains unavailable to the normal OpenClaw Designer.
