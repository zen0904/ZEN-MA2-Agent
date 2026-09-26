# Bounded Position Application Evidence PoC

Status: **approval-aware Action Preview implemented; application unverified**.
The prior standalone non-executable Preview remains historical discovery
evidence, not an execution authority. No Position Group/Preset binding is
verified by this implementation alone. No MA2 Show write, provider call, or
owner approval occurred in this gate.

`zen.position.preview` now requires explicit expected Show fingerprint, Group
ID/name/exact ordered refs, and Position Preset ref/label. Before registering
an Action it freshly reads the Show's Groups, exact Group exports, Fixtures,
geometry, FixtureType profiles, Sequence inventory, Preset inventory, and the
exact Position Preset. Any drift fails closed. Sequence allocation may advance
to a newly free safe slot, but that new slot is displayed in the Action.
Registration returns a nonempty `action_id`, `PENDING_APPROVAL`,
`root_state=READY`, and `phase=PREVIEW`; it never calls approval or MA transport
execution. The Action contains only the deterministic six-command candidate,
one new Agent-owned Sequence/Cue, and `Executor=None`.

The shared `zen.approve` boundary is not invoked by Preview. If a human later
explicitly approves, the Core must re-read the same Show/Group/Preset/Sequence
facts and reject any change to the approved Preview, including new Sequence
occupancy. Only after that check may the bounded deterministic plan execute.
Command acceptance and Cue metadata are insufficient: the existing native
Sequence Export verifier and `derive_position_application_binding()` must
prove exact PAN/TILT Preset evidence for every member before
`PositionApplicationBindingStore.record_after_readback()` records a binding.
A failed post-write verification retains the new Sequence as audit evidence;
no automatic Delete is generated. This future approval path was not executed
in this task. Position resources remain absent from the normal Designer while
the verified binding store is empty.

Offline regression for this approval-boundary implementation: 828/828
`unittest` PASS, `main.py --self-check` PASS, `git diff --check` PASS.
On this isolated development checkout, TCP port 30000 was listening but the
currently deployed Field Core (8876) and MA Bridge (8877) were not online.
Therefore no durable live Action was registered, no new `action_id` was
claimed, and no MA2 write occurred. This local availability observation does
not change the product-level Preview capability or promote application
evidence.

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

The current machine-local Preview is
`data/position_application_poc_preview_001.json`, Preview ID
`41ac18753c44d07e`, scanned profile fingerprint
`f88c5d6fe638b8cc967432239d9f5a43dd98f354f98dbe77bdf40e0eb3383b7d`
(`confidence=PARTIAL`). It proposes only Group 1 `HYBRID`, exact refs
`101,102,103,104,105,106,108,107`, Preset `2.1 HOME`, first-free Sequence 10
with label `ZEN_POSITION_APPLICATION_POC_SEQ10`, Cue 1, and no Executor. These
are time-specific read-only observations; the next session must re-read them.

## Engineering boundary

`zen.position_application_poc_preview.v0.1` remains a deterministic,
**non-executable standalone** Preview. It binds a fresh exact Group Export membership, a
show-bound POSITION technical profile, exact current Preset type/ref/label,
and a first-free non-protected Sequence candidate. It describes one typed
`CALL_PRESET` action and the existing deterministic MA2 command grammar. It
does not itself register an approval action; the new Core/Skill wrapper does.
Neither path sends a command or allocates an Executor at Preview time. The
Group 1 / Preset 2.1 candidate is an engineering probe,
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
`PositionApplicationBindingStore` persists only a binding derived from exact
content readback. The normal lean Core loads only current-matching entries and
performs a fresh bounded direct `List Preset <ref>` identity check before
offering a Position resource to the model. Today the store is empty; no
Position Preset is exposed by this gate.

## Next interactive step

Owner may review a newly registered approval-aware Position Action Preview
from the running Field Core. The old machine-local Preview ID is never an
approval target. Any future explicit approval must use the new `action_id`,
re-read the target identities before any write, read back exact Cue content,
and scope rollback only to the newly created Agent-owned Sequence after
identity proof.
No existing Sequence, Executor, Group, Preset, geometry, Patch, Address,
Fixture identity/type, or Fixture 9999 may be changed. Until then, POSITION
application remains unavailable to the normal OpenClaw Designer.
