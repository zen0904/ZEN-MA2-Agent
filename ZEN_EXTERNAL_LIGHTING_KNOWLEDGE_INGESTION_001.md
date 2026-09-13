# External Lighting Knowledge Ingestion 001

## Decision

`EXTERNAL_LIGHTING_KNOWLEDGE_PACK_001` is a small, source-diverse,
provenance-bearing **shadow knowledge** foundation. It is not model training,
a web archive, a global rule set, or a Designer activation. Its 25 concise
records are schema-reviewed for traceability and copyright safety; they are
not human-promoted production truth.

```text
ExternalKnowledgeSource
  -> normalized LightingKnowledgeRecord
  -> External Lighting Knowledge Pack
  -> optional SHADOW_ONLY Knowledge Context
  -> review / critique / later case evaluation
  -> separate human review, test, case trial, or rejection
```

Neither the Production Designer nor B3 consumes this pack. The only executable
demonstration is an inert critique helper: it can attach source-linked review
questions to already observed A/B 002 limitations, returns no action changes,
and explicitly requires Show-specific visual evidence.

## Source selection and storage policy

The source registry is
[`data/external_lighting_knowledge_source_registry_001.json`](data/external_lighting_knowledge_source_registry_001.json).
Every source is stored as metadata, URL, retrieved date, authority, scope bias,
and a derived-note copyright policy. The pack stores only normalized claims
under 500 characters and summaries under 600 characters; it stores no full
article, manual, transcript, screenshot, video, dataset, or bulk web archive.

Source priority is: official console/fixture documentation, established
education, professional trade-practice material, then case evidence. Community
discussion is permitted only as explicitly labelled `COMMUNITY_PRACTICE`; none
is in Pack 001. A source cannot be silently promoted, and a single case cannot
become a general requirement.

| ID | Source and classification | Why it is bounded |
| --- | --- | --- |
| `ETC_EDUCATIONAL_RESOURCES` | [ETC Educational Resources](https://www.etcconnect.com/Support/Training-Events/Educational-Resources.aspx) — `GENERAL_DESIGN_KNOWLEDGE` | Established education; theatre-oriented examples are not concert rules. |
| `MA2_CUE_CONTENT_TRACKING_MANUAL` | [grandMA2 cue content / tracking](https://help2.malighting.com/Page/grandMA2/cs_cue_content/en/3.3) — `OFFICIAL_DOCUMENTED` | Console behavior and handover only, never artistic prescription. |
| `GDTF_DMX_CHANNELS` | [GDTF Define DMX Channels](https://gdtf-share.com/help/users/gdtf_builder/dmx/index.html) — `OFFICIAL_DOCUMENTED` | Technical fixture-mode provenance; an external profile still needs Show binding. |
| `GDTF_FIXTURE_INFORMATION` | [GDTF Fixture Information](https://gdtf-share.com/help/users/gdtf_share/navigate/fixture_information/index.html) — `OFFICIAL_DOCUMENTED` | Revision/test status is evidence metadata, not rig geometry. |
| `PLASA_PARADISE_UNDER_THE_STARS` | [PLASA case reference](https://ftp.plasa.org/news/wl-supports-paradise-under-the-stars) — `PROFESSIONAL_PRACTICE` | One immersive-production case; no universal energy curve. |
| `LSA_MUSE_TOUR_CASE` | [Lighting&Sound America tour case](https://www.lightingandsoundamerica.com/news/story.asp?ID=UFCTQP) — `INDUSTRY_REFERENCE` | Large touring context only; no genre or fixture recipe. |
| `PLASA_CHAUVET_CHURCH_VIDEO` | [PLASA camera-oriented case](https://ftp.plasa.org/news/chauvet-animates-church-s-music-video) — `CASE_CONTEXT` | Camera/pop-rock case; explicitly protects against `MULTICOLOR_EQUALS_BAD`. |

The implementation rejects raw console fields, copied-text fields, unknown
source references, long claims, and a `PROMOTED` state in an ingestion pack.
It introduces no Git LFS, CI workflow, cache, media, or raw research corpus.

## Pack 001 knowledge summary

[`data/external_lighting_knowledge_pack_001.json`](data/external_lighting_knowledge_pack_001.json)
contains 25 `DESCRIPTIVE` records across 14 topics:

| Design dimension | What Pack 001 contributes | Explicit non-rule boundary |
| --- | --- | --- |
| Visual hierarchy / focus | Hierarchy may use multiple controllable properties; attention is contextual. | No inferred performer target, Group priority, or fixture role. |
| Negative space / restraint | Omission, darkness, and quiet scenes can be intentional compositions. | Not a low-energy recipe or mandated reset. |
| Density / layering / contrast | Density and depth are compositional dimensions, not fixture count alone. | Not `HIGH_ENERGY = MORE_LAYERS`. |
| Color relationships | Palette is contextual; limited palette is one case strategy. | Not dominant-color-only or anti-multicolor. |
| Movement / texture | Motion can be selected for a compositional reason. | Availability never requires movement or texture. |
| Rhythmic punctuation | Timing/strobe can be a contextual mechanism. | Not every hit/drop/high section needs it. |
| Energy / repetition / headroom | Whole-show relationships, contrast, intentional similarity, and development can be reviewed. | No monotonic energy arc, repeat escalation, or save-for-final rule. |
| Resource / fixture provenance | Mode/version/channel evidence needs source and binding. | Technical capability is not role, selection, or visual dominance. |
| Console maintainability | MA2 tracking/content inspection supports native editability and handover. | Does not dictate current implementation or execute console actions. |

### Conflicts and applicability

The pack deliberately retains conflict notes instead of calculating a weighted
truth score. For example, touring-case continuous change coexists with valid
intentional palette continuity; a case using limited color coexists with
multicolor designs; contrast can be abrupt, gradual, or absent when a sustained
state is appropriate. Theatre education, touring concert work, immersive
production, and camera-oriented music-video references remain scoped to their
own disciplines.

## Shadow-only A/B 002 critique demonstration

`critique_ab002_density_limits()` receives the already documented A/B 002
findings, not a new plan. It associates:

| Existing observed finding | Knowledge topics supplied | Output |
| --- | --- | --- |
| `FINAL_COHORT_SATURATION_RISK` | visual hierarchy, negative-space/restraint, resource headroom | Ask a human whether the realized composition preserves hierarchy/headroom. |
| `GROUP_LEVEL_HOMOGENEITY_UNRESOLVED` | visual hierarchy, contrast, layering/depth | Ask a human whether equal levels conceal missing visual differentiation. |

It does **not** select Groups, change dimmer levels, suggest a new cue, call a
preset/effect, or modify A/B 002 actions. It returns
`REVIEW_REQUIRED_SHOW_SPECIFIC_EVIDENCE` because general knowledge cannot tell
which existing-Show Group should be visually dominant.

## Current Show visual relationship boundary

External knowledge cannot establish for the current Existing Show:

- physical location, coverage, orientation, trim, audience-facing geometry, or
  visual weight of Groups 1–7;
- center/side/rear/floor/overhead semantics, beam intersection, performer
  target, stage axes, or a valid spatial hierarchy;
- whether one Group's equal dimmer level visually outweighs another;
- safe color/preset, movement, texture, timing, effect, pixel, or focus action
  applicability.

Those require fresh Current Show visual/spatial evidence, verified action
grammar, and case-level human decisions. Group names and Pack 001 sources do
not fill these gaps.

## Promotion boundary

External records remain `INGESTED_UNREVIEWED`, `SHADOW_ONLY`,
`HUMAN_REVIEW_REQUIRED`, or `CONTEXT_DEPENDENT`. Any later use must follow the
durable lifecycle:

```text
DISCOVER -> UNDERSTAND -> SOURCE_CLASSIFY -> VERSION_CHECK -> COMPARE
 -> TEST -> EVALUATE -> CASE_TRIAL -> PROMOTE / CONTEXT_DEPENDENT / REJECT
```

Human acceptance makes an interpretation eligible for later consideration; it
does not make a global Designer rule, a permanent ZEN preference, or a console
action. Professional/user-style divergence remains preserved rather than
averaged away.

## Safety and recommendation

- Production Designer: `UNCHANGED`.
- B3: `GUIDANCE_ASSISTED_AB_ONLY`; no new B3 action input is wired.
- A/B 002 actions: `UNCHANGED`.
- `ZEN_STYLE_PROFILE`: `DEFERRED`.
- MA2 objects modified: `NONE`; MA2 write audit: `ZERO_WRITES`.
- Fixture 9999: untouched.
- MA3 implementation: not started.

**Recommended next highest-leverage step:** obtain a bounded, human-reviewable
Current Show visual/spatial relationship survey (or an explicitly
user-confirmed rig layout). Then use Pack 001 only in shadow critique to assess
the actual A/B 002 cohort composition before considering any richer
case-specific expressive action experiment.

## Canonical knowledge, training, and benchmark foundation (001)

The existing pack now has a reusable canonical boundary in
`zen_ma2_agent/knowledge_store.py`. `load_canonical_store()` validates the
Source Registry and Pack before normalizing records; source metadata remains
registry-owned and is never authored by an LLM. Records retain complete
provenance and are classified into `GLOBAL_LIGHTING_DESIGN_KNOWLEDGE`,
`MA2_TECHNICAL_KNOWLEDGE`, or `FIXTURE_TECHNICAL_KNOWLEDGE`. The extension
categories `SHOW_FACTS` and `ZEN_STYLE_AND_WORKFLOW_KNOWLEDGE` are supported
without inventing unverified records.

Retrieval is deterministic and role-aware: role/topic relevance, request and
context overlap, topic caps, and stable record-id ordering are preserved. The
agent projection keeps `record_id`, claim, scope, exclusions, confidence,
promotion state, and summary. The multi-agent runtime no longer uses blind
first-N character excerpts for professional knowledge.

The same module provides an Evidence Ledger boundary where `VERIFIED_FACT`,
`DESIGN_KNOWLEDGE`, `ARTISTIC_PROPOSAL`, and `UNKNOWN` stay distinct; unknown
references fail closed. The existing external pack remains `SHADOW_ONLY` and
is not activated in Production Designer or B3.

`zen_ma2_agent/training_dataset.py` defines reviewable samples and portable
`training/{raw,reviewed,rejected,exports}` directories. Samples preserve run,
commit, provider/model, context hash, knowledge references, review/approval
state, and `CODEX_ARTISTIC_INTERVENTION = NONE`. Only explicitly `APPROVED`
samples export to JSONL, and Codex cannot self-approve artistic ground truth.
Training was not executed.

`zen_ma2_agent/benchmark.py` plus `data/benchmark_cases_001.json` provide
deterministic, non-artistic structural scoring for schema validity, forbidden
commands, unknown/unsupported evidence, uncertainty, fixture-role locking,
evidence references, retrieval coverage/diversity, retries, runtime, and
output size. It does not grade artistic quality.

`data/zen_knowledge_store_001.json` is a compact index referencing the existing
registry and pack rather than duplicating them. No vector database, LangChain,
model training, cloud call, MA2/Telnet/Builder execution, media archive, LFS,
or CI expansion was introduced. Production Designer behavior and B3 remain
unchanged.
