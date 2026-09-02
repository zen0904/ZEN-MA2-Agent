# Geometry Clone v1

## Scope

Geometry Clone v1 is deliberately an **ordered fixture mapping** workflow, not
spatial geometry. It uses only verified, read-only state:

- Group inventory and exact Group name/number resolution;
- fresh Group membership from the local, native `Export Group` XML provider;
- Fixture IDs in the order exported by MA2.

It does not use Layout XY, Subfixture geometry, stage coordinates, Selection,
or Programmer state. Layout fixture geometry remains `UNSUPPORTED`.

## Deterministic mapping

For equally sized Groups, v1 maps each source member to the destination member
at the same Group export order:

```
Source:      101 102 103 104
Destination: 201 202 203 204
Mapping:     101->201, 102->202, 103->203, 104->204
```

The stored `GeometryCloneSpec` includes both Group identities, both ordered
member lists, the pairs, counts, the original request, and fingerprints for
both membership snapshots. A changed or unavailable membership snapshot blocks
execution with `STATE_CHANGED_SINCE_PREVIEW`.

Only equal-size `ORDERED_1_TO_1` mapping is supported. A count mismatch returns
a preview with `COUNT_MISMATCH`; it never creates MA2 Clone commands. Empty,
missing, duplicate-name, stale, error, or unsupported Group state also blocks
the workflow.

## MA2 execution boundary

Each verified pair creates one official native MA2 command:

```
Clone Fixture <source> At Fixture <destination> /nc
```

This uses MA2's documented Fixture Clone behavior. v1 does not claim a finer
scope than that native semantic and does not add unverified scope filters.
Preview explicitly identifies it as `MODIFY`, lists the destination count, and
requires approval. Execution is never initiated by a chat request alone.

Post-execution verification is intentionally `PARTIAL`: it verifies command
feedback, that both Group memberships remain unchanged, and that destination
Fixtures still exist. MA2 does not yet expose a verified read-only provider for
the cloned internal Fixture data. There is no automatic rollback; use MA2 Undo
or a saved show backup when necessary.

## Release state

The built-in Geometry Clone skill remains **Disabled** until a dedicated,
safe real-MA2 write target has passed the complete Preview, Approval, execution,
and partial read-back flow. Disabled status still permits safe real-state
mapping and Preview; it cannot create an approvable action or send Clone.

## Natural-language forms

- `把 HYBRID Clone 到 SPOT`
- `Clone Group 1 到 Group 2`
- `用 Clone From 當來源，Clone To 當目標`
- `預覽 Group 1 → Group 2 Clone`
- `幫我看 HYBRID 跟 SPOT 能不能 1:1 Clone`

The mapping/count forms are SAFE read-only queries. The Clone forms create a
MODIFY Preview only.
