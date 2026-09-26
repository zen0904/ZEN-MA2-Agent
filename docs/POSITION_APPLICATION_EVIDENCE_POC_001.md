# Bounded Position Application Evidence PoC

## Consolidated Position Calibration transaction (owner-approved 2026-09-26)

The owner explicitly approved replacing the separate Raw Position Cue and
Position Preset application Actions with one more efficient calibration
transaction. This is a workflow-design approval, not approval for any future
live Action. A fresh live Preview and separate explicit approval remain
mandatory before MA2 writes.

The transaction is intentionally bounded to Group 1 and one newly allocated
Agent-owned selective Position Preset plus one newly allocated Agent-owned
Sequence with two Cues and no Executor:

```text
ClearAll
Group 1
Attribute "Pan" At 20
Attribute "Tilt" At 30
Store Cue 1 Sequence <fresh> "RAW_POSITION" Fade 0 /nc
Store Preset 2.<fresh> "ZEN_POSITION_CAL_P<n>" /selective /nc
ClearAll
Group 1
At Preset 2.<fresh>
Store Cue 2 Sequence <fresh> "PRESET_POSITION" Fade 0 /nc
Label Sequence <fresh> "ZEN_POSITION_CAL_SEQ<n>" /nc
ClearAll
```

Approval-time fresh state must match the exact Preview. Phase B is unreachable
until a direct `List Preset 2.<fresh>` read proves the newly created Preset
has the exact expected reference, POSITION type and Agent-owned label. The
post-write Show fingerprint is predicted from the approved pre-write profile
plus exactly that one new Preset; any unrelated Preset or Group drift fails
closed.

One retained native Sequence Export is used for both gates. Cue 1 must contain
exact PAN=20 and TILT=30 exported raw values for every exact Group member and no
foreign member. Cue 2 must contain both PAN and TILT rows for every expected
Position channel, each linked to the exact newly created Preset reference.
Only then may the Position application binding be recorded as
`REAL_MACHINE_CONTENT_VERIFIED`. Physical aim/degree semantics are not
claimed from the raw numeric values.

No automatic cleanup is performed. The Agent-owned calibration Preset and
Sequence remain audit evidence until the owner separately approves deletion.

Implementation regression at this gate: 858/858 Python tests PASS,
`main.py --self-check` PASS, `git diff --check` PASS, and the OpenClaw
plugin tests are 2/2 PASS. Implementation/Preview work performs zero MA2
writes.

### Live calibration result and correction

Owner explicitly approved live Action `f87b868f4a96`, Preview
`d994c2040078ec1d`. Approval-time revalidation passed and the bounded
transaction executed against Group 1. Position Preset `2.12` /
`ZEN_POSITION_CAL_P12` was created and its exact identity was directly
verified before Phase B. Sequence `11` / `ZEN_POSITION_CAL_SEQ11` was
created with Cue 1 `RAW_POSITION` and Cue 2 `PRESET_POSITION`.

Native Sequence Export
`ZEN_AGENT_SEQUENCE_11_ca4e803a2c9c29fd.xml` proves that Cue 1 contains
PAN=20 and TILT=30 for every exact HYBRID member 101-108. It also proves Cue 2
contains no CueData. The export status `PARTIAL` is therefore correct and
must not be weakened into VERIFIED. No Position application binding was
recorded. Preset 2.12 and Sequence 11 remain retained audit evidence; no
automatic Delete was performed.

The real-machine result disproved one workflow assumption: after storing the
raw Cue, the transaction cannot rely on programmer values still being in a
Preset-storable active state. The corrected transaction now performs a fresh
`ClearAll -> Group 1 -> Attribute "Pan" At 20 -> Attribute "Tilt" At 30`
reactivation before `Store Preset`. This remains inside the same single
approval-gated calibration transaction and still uses one native Sequence
Export for both final proofs.

The failed Action is consumed. Its approval does not authorize the corrected
future Action; a new live Preview and new explicit owner approval remain
mandatory.

## Raw Position Cue transport/content foundation (2026-09-26)

The owner reports that the explicitly approved `2.1 HOME` application probe
created Agent-owned Sequence 10 / Cue 1, but native Sequence Export contained
no CueData because that Preset was empty. No Position binding was recorded.
The owner separately approved deletion of that failed Sequence; fresh
`List Sequence 10` then returned no object. This is historical operator/run
evidence, not authority to reuse Sequence 10 without a new inventory scan.

The independent `zen.position.raw.preview` path now assembles a narrow
approval-aware Action from fresh Show, exact Group, FixtureType capability,
Preset inventory (for the same conservative Show fingerprint), and Sequence
inventory. It only permits Group 1, exact verified parent/subfixture selection,
and fixed engineering natural-value commands `Attribute "Pan" At 20` and
`Attribute "Tilt" At 30`. The Action uses first-free non-protected Sequence
allocation, one Cue, an Agent-owned ASCII label, and no Executor. Preview
registers `PENDING_APPROVAL` under the existing WorkflowPlan/Action registry;
it sends no MA2 command. Approval must re-scan and compare the *entire* exact
Preview, including Sequence candidate. A newly occupied candidate makes the
approved Action stale; approval never silently reallocates.

After a **later explicit human approval only**, the existing deterministic
Core/Skill execution boundary may send exactly the seven previewed commands.
Native Sequence Export must show one Cue 1 with nonempty raw Value fields on
both PAN and TILT CueData rows for every expected exact channel ref, with no
foreign ref. The retained native XML SHA-256 is audit evidence. No assertion
about physical units or equality to natural values 20/30 is made by this
parser. A failed readback leaves the new Sequence for owner review; ClearAll
is attempted, but Delete is never automatic.

`RAW_POSITION_CUE_CONTENT_VERIFIED` is intentionally **not**
`REAL_MACHINE_CONTENT_VERIFIED` Position Preset applicability. This path never
calls `PositionApplicationBindingStore.record_after_readback()`. The ordinary
Designer Position resource count remains zero while the binding store is
empty. Creating a new Agent-owned Position Preset and then proving Preset
application is a separate future gate; this implementation does not do it.

Status: **approval-aware Action Preview implemented; application unverified**.
The prior standalone non-executable Preview remains historical discovery
evidence, not an execution authority. No Position Group/Preset binding is
verified by this implementation alone. The previous approval-boundary
implementation gate itself performed no MA2 Show write or owner approval;
the subsequent owner-approved failed application probe is recorded above.

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
