# ZEN Production Engineering Evidence Policy

Status: ARCHITECTURE_V0_1
Implementation authority: NOT_GRANTED
Parent: docs/ZEN_PRODUCTION_DESIGN_SYSTEM.md

## 1. Purpose

This policy prevents ZEN from turning plausible engineering language into unsafe certainty.

Production design contains high-consequence facts: load capacity, support strength, temporary
structure stability, hoist capacity, floor loading and scaffold configuration. These require
stronger evidence rules than ordinary artistic reasoning.

## 2. Evidence classes

Use:

~~~text
VENUE_ENGINEERING_DOCUMENT
MANUFACTURER_ENGINEERING_DATA
REGULATORY_OR_STANDARD_REFERENCE
MEASURED_PROJECT_FACT
VERIFIED_SYSTEM_IMPORT
QUALIFIED_HUMAN_ENGINEERING_DECISION
OPERATOR_CONFIRMED_NON_ENGINEERING_FACT
ASSUMPTION
VISION_INFERENCE
MODEL_PROPOSAL
~~~

Only the first six may support engineering truth, and only within their stated scope.

## 3. Product identity rule

Never apply a capacity table unless the product identity required by that table is verified.

Rejected examples:

- "looks like Prolyte";
- "probably H30";
- "400 mm box truss";
- "standard Layher";
- "1 ton motor" with no exact unit/model evidence.

Acceptable engineering lookup requires exact enough identity to bind the source data.

## 4. Load-table rule

Manufacturer tables are bounded evidence, not universal solvers.

Before using a table verify, as applicable:

- exact series/model;
- span;
- support condition;
- orientation;
- load case definition;
- point-load locations;
- self-weight treatment;
- connector/system assumptions;
- applicable manual/table version;
- whether the table explicitly covers the proposed configuration.

If a proposed structure falls outside the table/configuration, return
STRUCTURAL_ANALYSIS_REQUIRED.

## 5. Complex structures

Do not extrapolate simple-span tables into:

- multiple-span systems;
- 3D grids;
- towers;
- large cantilevers;
- non-standard support configurations;
- mixed systems;
- suspended scaffold/scenic frames;
- significant wind-exposed structures.

Use dedicated verified engineering methods or escalate.

## 6. Hoists and rigging hardware

WLL/SWL/capacity claims require exact equipment/hardware data and configuration.

Do not infer capacity from:

- hook size;
- chain appearance;
- common rental practice;
- label color;
- model-family resemblance.

Hardware compatibility and load path matter as much as headline WLL.

## 7. Venue support authority

A truss being strong enough does not prove the roof/pick/floor is strong enough.

Venue-side structural facts require venue engineering documentation or qualified current
project evidence.

Unknown venue capacity means the load path is not approved.

## 8. Wind / outdoor / dynamic effects

Outdoor and dynamic cases are escalation-sensitive.

Do not generate project wind loads, dynamic coefficients, ballast requirements or seismic
claims from generic intuition.

A production can still be designed artistically while those fields remain unresolved, but
its feasibility state must reflect that.

## 9. Software-analysis boundary

Braceworks or other structural software can produce valuable analysis/calculation reports.
Software output is evidence from a configured model, not an automatic engineering stamp.

Record:

- software/tool/version;
- model/context revision;
- input assumptions;
- material/product data source;
- load cases;
- warnings/errors;
- result artifact hash;
- reviewer/sign-off status.

## 10. MVR/GDTF boundary

MVR/GDTF can prove scene/device data within the imported file's scope.

They do not prove:

- truss capacity;
- roof capacity;
- legal compliance;
- actual on-site assembly;
- current equipment condition.

Use them as geometry/identity/interchange evidence.

## 11. Multimodal/vision boundary

Vision models are useful for:

- identifying candidate objects;
- extracting dimension annotations from drawings;
- locating obstructions;
- comparing a photograph with a plan;
- spotting missing coordination;
- proposing questions for verification.

Vision output must be tagged VISION_INFERENCE until corroborated.

Never use a vision-only observation for a structural capacity claim.

## 12. Taiwan safety/regulatory research boundary

For Taiwan projects, applicable law and site requirements must be checked at project time.

Taiwan OSHA scaffold guidance provides a concrete example: certain scaffold construction,
including referenced cases involving structures 5 m and above, requires design based on
structural mechanics, calculation/drawing documentation and designated engineering/experienced
personnel under the cited occupational-safety framework.

This establishes a product rule for ZEN:

~~~text
AI-generated scaffold/rigging proposal
!=
required engineering documentation/signature
~~~

The repository is not a legal-compliance engine. It must link the current official source and
require human verification for the actual project.

Research anchor:
https://www.osha.gov.tw/media/rojjkges/%E6%96%BD%E5%B7%A5%E6%9E%B6%E4%BD%9C%E6%A5%AD%E5%AE%89%E5%85%A8%E6%AA%A2%E6%9F%A5%E9%87%8D%E9%BB%9E%E5%8F%8A%E6%B3%A8%E6%84%8F%E4%BA%8B%E9%A0%85.pdf

## 13. Source anchors

### Vectorworks Braceworks

Official product/help material describes entertainment rigging modeling, hoists/supports/loads,
3D structural/static/FEM analysis and calculation reports used in engineering review.

Sources:
https://www.vectorworks.net/en-US/braceworks
https://app-help.vectorworks.net/2024/eng/VW2024_Guide/Braceworks/Concept_Braceworks_structural_analysis.htm

### GDTF / MVR

Official MVR 1.6 documentation describes entertainment-scene exchange including fixtures,
trusses, supports, video screens and scene geometry. GDTF geometry documentation models device
physical hierarchy and 3D dimensions.

Sources:
https://gdtf-share.com/help/developers/mvr_1_6/index.html
https://gdtf-share.com/help/developers/mvr_1_6/file-format-definition/index.html
https://gdtf-share.com/help/users/gdtf_builder/geometry/index.html

### Prolyte

Official manuals/product data publish allowable loading by exact truss/product, span and load
case, including deflection information.

Sources:
https://www.prolyte.com/support/manuals
https://www.prolyte.com/products/aluminium-truss/rectangular-truss/s36prf-l122-pre-rig-truss-fixed-length-4ft

### Layher

Official downloads describe approvals, verified structural calculations, assembly/use
instructions and material requirement data. Layher SIM describes 3D scaffold planning,
material lists/assembly plans and transfer to structural-analysis workflows.

Sources:
https://www.layher.com/en/services/downloads
https://www.layher.com/en/knowledge/layher-sim

## 14. Fail-closed behavior

Return UNKNOWN or escalation when:

- source version/scope is unclear;
- exact product identity is absent;
- support condition differs;
- source assumptions do not match the proposal;
- venue capacity is missing;
- units/coordinate transform are uncertain;
- load case is incomplete;
- imported geometry is stale;
- human sign-off is required.

A confident sentence is not evidence.

## 15. Evidence promotion

External research begins as reference knowledge. Project use requires binding it to:

- exact product/project object;
- exact revision;
- source hash/URL;
- retrieved/version date where available;
- scope;
- limitations.

No global rule such as "this truss supports X kg" should be learned without the span/load-case
context that makes the statement meaningful.
