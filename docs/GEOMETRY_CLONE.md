# Geometry Clone — design only

## Objective

The show template intentionally contains a small number of template fixtures.
For each venue, the Agent maps them onto a larger destination rig, while MA2
itself performs the final native `Clone` command.

## Inputs

- Template Group and Destination Group supplied by the operator.
- Fixture identity and selection order from MA2.
- Layout XY coordinates supplied by `gma2/plugins/ZEN_AGENT.lua` where suitable.

## Deterministic mapping pipeline

1. Read source and destination members and their Layout XY positions.
2. Normalize each point cloud into a local 0–1 coordinate space.
3. Infer left/right, rows, mirror symmetry, and selection order.
4. Calculate and display source → destination mapping using a selected mode.
5. Validate cardinality and ambiguous geometry; require the operator to choose
   or correct any ambiguous mapping.
6. Preview MA2-native Clone commands. The Agent never reimplements Clone.

## Mapping modes

| Mode | Rule |
| --- | --- |
| `LINEAR` | Preserve ordered source-to-destination progression. |
| `MIRROR` | Pair source positions symmetrically around the layout centre. |
| `GEOMETRY` | Assign by normalized XY proximity and inferred rows/sides. |
| `EDGE` | Anchor source endpoints to destination edges, interpolate interior. |

Example: four template fixtures mapped to ten rig fixtures first preserves the
chosen geometry mode, then emits an explicit mapping table for review.

## Position and effects

Position is not always cloned. A later Layout Geometry Auto Position Generator
can compute position data independently. A later effects module can detect
template or selective effects and reflow them against the confirmed mapping.
