# POSITION_MERGE_FORENSIC_001

Date: 2026-09-27 (Taiwan)

## Result

Action `97d3a82f1220` did write the approved bounded Position-only merge to existing Sequence 302 Cues 1-29. The initial post-write failure `POSITION_MERGE_NON_POSITION_CONTENT_CHANGED` was a verifier false negative, not evidence that protected Dimmer/Color/Preset/Effect content changed. No retry or rewrite was required.

## Retained native exports

- PRE: `cache/sequence_export_diagnostics/ZEN_AGENT_SEQUENCE_302_455a15dee8e5146b.xml`
  - SHA256 `6a2246632e2d9a44f691db0bea86c6a44c52f9670984dec5ac436c325ca4f608`
  - 1,018,936 bytes
- POST: `cache/sequence_export_diagnostics/ZEN_AGENT_SEQUENCE_302_719d510d7963c061.xml`
  - SHA256 `104ec49ee4582b35aee84967266d0bfe18bc6415a7d4efd32ca3a008d4ab0936`
  - 1,348,800 bytes

## Forensic finding

The old verifier excluded only `PAN` and `TILT` from the protected non-Position fingerprint. grandMA2 expanded stored Position content with the verified Position-family companion attributes `VIRTUAL_POSITION_MODE`, `MARK`, `STAGEX`, `STAGEY`, `STAGEZ`, `FLIP`, and `DIST`. These attributes are classified as Position-preset channels by the committed Show-bound fixture-type evidence.

Across the retained exports, each companion attribute increased from 8 rows to 232 rows. The delta is 224 rows per attribute, or 1,568 additional companion rows total. Protected artistic content did not drift: `DIM` remained 1,376 rows; `COLORRGB1`, `COLORRGB2`, and `COLORRGB3` remained 912 rows each; Preset references and Effects were unchanged.

Exact Position verification passed `464/464` PAN/TILT rows. All 29 Cue labels and Fade metadata values remained unchanged. Fixture 9999 is absent from the Position writes.

## Fix

`zen_ma2_agent/position_existing_cue_merge.py` now separates primary Position axes (`PAN`, `TILT`) from the complete verified Position-family exclusion set used only for protected non-Position fingerprinting. Calibration and exact Position-value verification remain PAN/TILT-only and fail-closed. Unknown attributes still count as protected non-Position content.

Fix commit: `ef774ba` (`fix: classify MA2 position companion channels`).

A compact regression fixture derived from the retained real Sequence 302 pre/post XML is stored at `tests/fixtures/position_merge_forensic_001.json` with both original source SHA256 values.

Offline re-verification of all 29 Cues produced the same canonical protected-content SHA256 for PRE and POST:

`4df741a03932fd59628a48a86724c98b65a1f46e7424b720448a44739d29bd5d`

Windows authoritative suite after the fix: `894 tests / OK`.

## Executor evidence limitation

Executor `2.8 -> Sequence 302` was freshly confirmed immediately before the live write and no Executor/Assign command was issued by the approved Position-only plan. A separate retained post-write Executor refresh was not captured. A later independent read-only session did not reach READY, so no unsupported PASS claim is made from that attempt.

## Safety / write accounting

- The forensic investigation and verifier fix performed no MA2 Show writes.
- No automatic Delete or rollback occurred after the original verification failure.
- Sequence 302 is retained as forensic/live Test Show evidence.
- Action `97d3a82f1220` must not be approved or replayed again.
- No additional Position rewrite is required for this acceptance.
