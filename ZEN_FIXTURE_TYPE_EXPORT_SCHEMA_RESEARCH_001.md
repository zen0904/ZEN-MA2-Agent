# Fixture Type Export Schema / Identity Research 001

**Scope:** bounded, real-console, read-only schema research for the currently loaded Existing Show. This document does not assign artistic roles, modify the Designer, or authorize `REAL_SONG_EXISTING_SHOW_AB_002`.

## Method

The verifier first proved the expected Existing Show fingerprint `497dfae11821c10eebc54a614fa66e81339cb79d789d50c112fcdfc33134f4ea` against a fresh Group/Fixture/Preset scan. It then issued one native external `Export FixtureType <id> "ZEN_AGENT_FT_<id>_<request>.xml" /nc` for each of the six unique current FixtureTypes. Every export used a unique Agent-owned filename, was accepted by MA2, was parsed before cleanup, and was removed after a bounded diagnostic extract was retained. Fixture `9999` was never selected or addressed.

The retained machine-readable evidence is [`data/ZEN_SHOW_BOUND_FIXTURE_TYPE_BINDING_001.json`](data/ZEN_SHOW_BOUND_FIXTURE_TYPE_BINDING_001.json). It contains request/feedback, timestamps, XML root/version, observed FixtureType attributes, compact ChannelType/ChannelFunction inventory, technical and XML SHA-256 fingerprints, and strict/compound comparisons. It does not contain raw temporary XML.

## Observed `FixtureType@index` behavior

| Requested current-Show FixtureType ID | Exact List label | XML `FixtureType@index` | Name / mode | ChannelTypes |
|---:|---|---:|---|---:|
| 2 | `2 ZEN BAW 20R Mode 2` | 1 | `ZEN BAW 20R` / `Mode 2` | 32 |
| 3 | `3 ZEN DMH-160 St_Preset` | 2 | `ZEN DMH-160` / `St_Preset` | 21 |
| 4 | `4 ZEN K10 Shapes` | 3 | `ZEN K10` / `Shapes` | 28 |
| 5 | `5 ZEN MAC AU XB Standard` | 4 | `ZEN MAC AU XB` / `Standard` | 21 |
| 6 | `6 ZEN LEDPar 9c 9Ch Mode A` | 5 | `ZEN LEDPar 9c` / `9Ch Mode A` | 9 |
| 7 | `7 Atomic 3000 LED Extended` | 6 | `Atomic 3000 LED` / `Extended` | 14 |

All six controlled exports follow `XML index = requested current-Show pool ID minus 1`. The XML root was `MA`, with version `3.9.60`; each export contained exactly one `FixtureType` directly under that root. This is observed MA2 serialization behavior for this verified show/run, not a claim that XML index is itself the Show pool ID or a universal MA2 schema assertion.

## Identity conclusion

The former single-export rule remains intact and fails closed: `XML @index == List-derived Show pool ID`. It correctly rejected this run because `@index` is not the same namespace.

The new **compound batch rule** is supported for this verified show/run:

1. Expected Existing Show identity matches the fresh scan.
2. `List Fixture` supplies an exact current-Show FixtureType ID and full label.
3. The native command addresses that exact ID and a unique owned filename.
4. MA2 feedback confirms execution of that exact command.
5. Each XML has one parseable FixtureType with a non-empty channel inventory.
6. Every XML index equals its requested ID minus one.
7. Reconstructing the List label from the **requested ID** plus exported XML name/mode exactly equals the current List-derived label.
8. Requested IDs and XML indices are unique across the full batch.

Name/mode is a component of a multi-part proof, never standalone name similarity. A swapped export cannot pass: it fails the ID-minus-one invariant, the requested-label reconstruction, or both. Duplicate/similar name/mode labels remain safe because the independently addressed requested ID and unique XML index are both required. Unit tests also reject mismatched XML indices, duplicated batch indices, and a missing Show-identity match.

## Validator decision

The strict single-export validator was **not weakened**. It continues to require equal namespaces and is retained as a conservative check. A separate `fixture_type_export_batch_binding` validates the observed alternate serialization only after the entire Show-identity-matched batch satisfies the compound invariant. A lone XML with a plausible name/mode cannot become `SHOW_BOUND_VERIFIED`.

All six current FixtureTypes are `SHOW_BOUND_VERIFIED` through `MA2_EXPORT_FIXTURE_TYPE_XML_COMPOUND_IDENTITY`. The local candidate comparison occurs only after that result. It structurally binds the DMH-160, MAC AU XB, and LEDPar candidates; the BAW candidate differs structurally, and the K10/Atomic local XMLP candidates remain unparsed/unbound by the current local candidate parser. Those local outcomes do not change the Show-bound technical evidence.

## Verified technical capability summary

Technical capability is not a permanent role or case assignment.

| FixtureType ID | Confirmed channel-derived capabilities | Not present / still unclassified |
|---:|---|---|
| 2 BAW | DIMMER, COLOR, PAN/TILT/POSITION, GOBO, PRISM, ZOOM, FOCUS, FROST, SHUTTER/STROBE | PIXEL/SHAPE unclassified |
| 3 DMH-160 | DIMMER, COLOR, PAN/TILT/POSITION, GOBO, PRISM, FOCUS, SHUTTER/STROBE | ZOOM, FROST not present; PIXEL/SHAPE unclassified |
| 4 K10 | DIMMER, COLOR, PAN/TILT/POSITION, ZOOM, FOCUS, SHUTTER/STROBE | GOBO, PRISM, FROST not present; PIXEL/SHAPE unclassified |
| 5 MAC AU XB | DIMMER, COLOR, PAN/TILT/POSITION, ZOOM, FOCUS, SHUTTER/STROBE | GOBO, PRISM, FROST not present; PIXEL/SHAPE unclassified |
| 6 LEDPar | DIMMER, COLOR, SHUTTER/STROBE | PAN/TILT/POSITION, GOBO, PRISM, ZOOM, FOCUS, FROST not present; PIXEL/SHAPE unclassified |
| 7 Atomic | DIMMER, COLOR, SHUTTER/STROBE | PAN/TILT/POSITION, GOBO, PRISM, ZOOM, FOCUS, FROST not present; PIXEL/SHAPE unclassified |

## Safety and readiness

- MA2 Show objects modified: `NONE`.
- MA2 object-write audit: `ZERO_WRITES`.
- Production Designer: `UNCHANGED`.
- B3: `GUIDANCE_ASSISTED_AB_ONLY`.
- `ZEN_STYLE_PROFILE`: `DEFERRED`.
- Geometry, semantic positions, and Effect behavior remain outside this work.

The technical binding blocker is resolved. `REAL_SONG_EXISTING_SHOW_AB_002` is **not yet authorized**: the next bounded step is updating the capability/candidate-role review with these verified technical capabilities, then recording a case-specific eligibility decision. Fixture Type identity must not become a permanent artistic role.
