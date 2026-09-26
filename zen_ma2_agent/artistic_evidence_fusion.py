"""Read-only fusion of reverse-translation and contextual artistic evidence.

The fusion layer keeps native MA2 observations, supplied contextual observations,
and limited cross-source correlations separate.  It never creates MA2 commands
or turns a correlation into a claim about visual output or authorial intent.
"""
from __future__ import annotations

from collections import defaultdict
import math
from typing import Any, Mapping, Sequence

from .reverse_artistic_translator import (
    DESIGN_REFERENCE_SCHEMA,
    REVERSE_ARTISTIC_TRANSLATION_SCHEMA,
)


ARTISTIC_EVIDENCE_FUSION_SCHEMA = "zen.artistic_evidence_fusion.v0.1"
CONTEXT_EVIDENCE_SCHEMA = "zen.artistic_context_evidence.v0.1"
HYPOTHESIS_INPUT_SCHEMA = "zen.artistic_reconstruction_hypotheses.v0.1"

_CONTEXT_TYPES = {
    "TIMING_TIMECODE",
    "SONG_STRUCTURE",
    "AUDIO_ANALYSIS",
    "STAGE_VIEW_VISUAL",
}
_EVIDENCE_STATUS = {"VERIFIED", "PARTIAL"}
_CONFIDENCE = {"HIGH", "MEDIUM", "LOW"}


class ArtisticEvidenceFusionError(ValueError):
    """Input is not a traceable, offline evidence artifact."""


def _non_empty_string(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    value = value.strip()
    return value or None


def _cue_number(value: object) -> str | None:
    value = _non_empty_string(value)
    if value is None:
        return None
    pieces = value.split(".")
    if not all(piece.isdigit() for piece in pieces) or int(pieces[0]) <= 0:
        return None
    return value


def _read_only_translation(translation: Mapping[str, Any]) -> tuple[int, str, list[Mapping[str, Any]], list[Mapping[str, Any]]]:
    if translation.get("schema") != REVERSE_ARTISTIC_TRANSLATION_SCHEMA:
        raise ArtisticEvidenceFusionError("UNSUPPORTED_REVERSE_TRANSLATION_SCHEMA")
    if translation.get("read_only") is not True:
        raise ArtisticEvidenceFusionError("REVERSE_TRANSLATION_MUST_BE_READ_ONLY")
    if translation.get("translation_status") not in {"OBSERVED", "PARTIAL_EVIDENCE"}:
        raise ArtisticEvidenceFusionError("REVERSE_TRANSLATION_STATUS_INVALID")
    reference = translation.get("machine_readable_design_reference")
    if not isinstance(reference, Mapping) or reference.get("schema") != DESIGN_REFERENCE_SCHEMA:
        raise ArtisticEvidenceFusionError("REVERSE_TRANSLATION_DESIGN_REFERENCE_INVALID")
    source = reference.get("source_evidence")
    if not isinstance(source, Mapping) or source.get("source") != "MA2_EXPORT_SEQUENCE_XML":
        raise ArtisticEvidenceFusionError("REVERSE_TRANSLATION_SOURCE_INVALID")
    sequence_no = source.get("sequence_no")
    if isinstance(sequence_no, bool) or not isinstance(sequence_no, int) or sequence_no <= 0:
        raise ArtisticEvidenceFusionError("REVERSE_TRANSLATION_SEQUENCE_INVALID")
    cues = translation.get("cue_semantics")
    motifs = translation.get("recurring_artistic_motifs")
    if not isinstance(cues, list) or not isinstance(motifs, list):
        raise ArtisticEvidenceFusionError("REVERSE_TRANSLATION_CONTENT_INVALID")
    normalized_cues = [cue for cue in cues if isinstance(cue, Mapping) and _cue_number(cue.get("cue_number"))]
    if len(normalized_cues) != len(cues):
        raise ArtisticEvidenceFusionError("REVERSE_TRANSLATION_CUE_INVALID")
    if not all(isinstance(motif, Mapping) for motif in motifs):
        raise ArtisticEvidenceFusionError("REVERSE_TRANSLATION_MOTIF_INVALID")
    return sequence_no, str(translation["translation_status"]), normalized_cues, motifs


def _source_ref(evidence_id: str, observation_id: str) -> str:
    return f"context:{evidence_id}:observation:{observation_id}"


def _temporal_evidence(value: object) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise ArtisticEvidenceFusionError("CONTEXT_EVIDENCE_TEMPORAL_INVALID")
    result: dict[str, Any] = {}
    timecode = _non_empty_string(value.get("timecode"))
    if timecode is not None:
        result["timecode"] = timecode
    for key in ("start_seconds", "end_seconds"):
        number = value.get(key)
        if number is None:
            continue
        if isinstance(number, bool) or not isinstance(number, (int, float)) or not math.isfinite(number) or number < 0:
            raise ArtisticEvidenceFusionError("CONTEXT_EVIDENCE_TEMPORAL_INVALID")
        result[key] = number
    if "start_seconds" in result and "end_seconds" in result and result["end_seconds"] < result["start_seconds"]:
        raise ArtisticEvidenceFusionError("CONTEXT_EVIDENCE_TEMPORAL_RANGE_INVALID")
    return result


def _validate_context_evidence(item: Mapping[str, Any]) -> dict[str, Any]:
    if item.get("schema") != CONTEXT_EVIDENCE_SCHEMA:
        raise ArtisticEvidenceFusionError("UNSUPPORTED_CONTEXT_EVIDENCE_SCHEMA")
    if item.get("read_only") is not True:
        raise ArtisticEvidenceFusionError("CONTEXT_EVIDENCE_MUST_BE_READ_ONLY")
    evidence_id = _non_empty_string(item.get("evidence_id"))
    source_type = _non_empty_string(item.get("source_type"))
    source_ref = _non_empty_string(item.get("source_ref"))
    status = item.get("status")
    if evidence_id is None or source_type not in _CONTEXT_TYPES or source_ref is None:
        raise ArtisticEvidenceFusionError("CONTEXT_EVIDENCE_IDENTITY_INVALID")
    if status not in _EVIDENCE_STATUS:
        raise ArtisticEvidenceFusionError("CONTEXT_EVIDENCE_STATUS_INVALID")
    observations = item.get("observations")
    if not isinstance(observations, list) or not observations:
        raise ArtisticEvidenceFusionError("CONTEXT_EVIDENCE_OBSERVATIONS_INVALID")
    seen_ids: set[str] = set()
    normalized: list[dict[str, Any]] = []
    for observation in observations:
        if not isinstance(observation, Mapping):
            raise ArtisticEvidenceFusionError("CONTEXT_EVIDENCE_OBSERVATION_INVALID")
        observation_id = _non_empty_string(observation.get("observation_id"))
        kind = _non_empty_string(observation.get("kind"))
        claim = _non_empty_string(observation.get("claim"))
        confidence = observation.get("confidence")
        if observation_id is None or observation_id in seen_ids or kind is None or claim is None:
            raise ArtisticEvidenceFusionError("CONTEXT_EVIDENCE_OBSERVATION_IDENTITY_INVALID")
        if confidence not in _CONFIDENCE:
            raise ArtisticEvidenceFusionError("CONTEXT_EVIDENCE_OBSERVATION_CONFIDENCE_INVALID")
        seen_ids.add(observation_id)
        cue_refs = observation.get("cue_refs", [])
        if not isinstance(cue_refs, list):
            raise ArtisticEvidenceFusionError("CONTEXT_EVIDENCE_CUE_REFS_INVALID")
        parsed_cues = {_cue_number(value) for value in cue_refs}
        if None in parsed_cues:
            raise ArtisticEvidenceFusionError("CONTEXT_EVIDENCE_CUE_REFERENCE_INVALID")
        normalized_cues = sorted(parsed_cues)
        tags = observation.get("tags", [])
        if not isinstance(tags, list) or any(_non_empty_string(tag) is None for tag in tags):
            raise ArtisticEvidenceFusionError("CONTEXT_EVIDENCE_TAGS_INVALID")
        normalized.append({
            "observation_id": observation_id,
            "kind": kind,
            "claim": claim,
            "cue_refs": normalized_cues,
            "tags": sorted({_non_empty_string(tag) for tag in tags}),
            "temporal_evidence": _temporal_evidence(observation.get("temporal_evidence")),
            "confidence": confidence,
        })
    return {
        "evidence_id": evidence_id,
        "source_type": source_type,
        "source_ref": source_ref,
        "status": status,
        "observations": normalized,
    }


def _fact_confidence(translation_status: str, cue_status: object = "OBSERVED") -> str:
    return "HIGH" if translation_status == "OBSERVED" and cue_status == "OBSERVED" else "MEDIUM"


def _correlation_confidence(translation_status: str, evidence_status: str, observation_confidence: str) -> str:
    if translation_status != "OBSERVED" or evidence_status != "VERIFIED" or observation_confidence == "LOW":
        return "LOW"
    return "MEDIUM"


def _validate_hypotheses(value: Mapping[str, Any] | None, known_refs: set[str]) -> list[dict[str, Any]]:
    if value is None:
        return []
    if value.get("schema") != HYPOTHESIS_INPUT_SCHEMA or value.get("read_only") is not True:
        raise ArtisticEvidenceFusionError("HYPOTHESIS_INPUT_MUST_BE_READ_ONLY")
    hypotheses = value.get("hypotheses")
    if not isinstance(hypotheses, list):
        raise ArtisticEvidenceFusionError("HYPOTHESIS_INPUT_INVALID")
    result: list[dict[str, Any]] = []
    ids: set[str] = set()
    for item in hypotheses:
        if not isinstance(item, Mapping):
            raise ArtisticEvidenceFusionError("HYPOTHESIS_INVALID")
        hypothesis_id = _non_empty_string(item.get("hypothesis_id"))
        statement = _non_empty_string(item.get("statement"))
        refs = item.get("evidence_refs")
        if hypothesis_id is None or hypothesis_id in ids or statement is None or not isinstance(refs, list) or not refs:
            raise ArtisticEvidenceFusionError("HYPOTHESIS_IDENTITY_INVALID")
        if any(not isinstance(ref, str) or ref not in known_refs for ref in refs):
            raise ArtisticEvidenceFusionError("HYPOTHESIS_EVIDENCE_REF_INVALID")
        ids.add(hypothesis_id)
        result.append({
            "finding_id": f"HYPOTHESIS_{hypothesis_id}",
            "classification": "UNVERIFIED_ARTISTIC_RECONSTRUCTION_HYPOTHESIS",
            "statement": statement,
            "evidence_refs": sorted(set(refs)),
            "confidence": "LOW",
            "limits": [
                "NOT_A_FACT",
                "NOT_EXECUTION_AUTHORIZATION",
                "DOES_NOT_ESTABLISH_VISUAL_OUTPUT_OR_AUTHORIAL_INTENT",
            ],
        })
    return sorted(result, key=lambda item: item["finding_id"])


def fuse_artistic_evidence(
    sequence_translation: Mapping[str, Any],
    context_evidence: Sequence[Mapping[str, Any]],
    hypotheses: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Fuse a reverse translation with traceable offline context artifacts.

    Context artifacts describe supplied observations; their claims are never
    reclassified as native MA2 observations.  The only generated inferences are
    cue-to-context correlations and repeated-content/tag correlations.
    """
    sequence_no, translation_status, cues, motifs = _read_only_translation(sequence_translation)
    sources = sorted((_validate_context_evidence(item) for item in context_evidence), key=lambda item: item["evidence_id"])
    if len({item["evidence_id"] for item in sources}) != len(sources):
        raise ArtisticEvidenceFusionError("CONTEXT_EVIDENCE_DUPLICATE_ID")

    facts: list[dict[str, Any]] = []
    context_by_cue: dict[str, list[dict[str, Any]]] = defaultdict(list)
    known_refs: set[str] = set()
    cue_ref_by_number: dict[str, str] = {}
    for cue in cues:
        number = str(cue["cue_number"])
        ref = f"sequence:{sequence_no}:cue:{number}"
        cue_ref_by_number[number] = ref
        known_refs.add(ref)
        facts.append({
            "finding_id": f"FACT_SEQUENCE_{sequence_no}_CUE_{number.replace('.', '_')}",
            "classification": "NATIVE_SEQUENCE_CUE_OBSERVATION",
            "statement": f"Native Sequence {sequence_no} Cue {number} has recorded CueData observations.",
            "evidence_refs": [ref],
            "confidence": _fact_confidence(translation_status, cue.get("evidence_status")),
            "observed": {
                "cue_parts": cue.get("parts", []),
                "dimensions": cue.get("observable_dimensions", []),
                "preset_references": cue.get("preset_references", []),
                "effect_references": cue.get("effect_references", []),
                "content_fingerprint": cue.get("content_fingerprint"),
            },
            "limits": ["NO_VISUAL_OUTPUT_CLAIM", "NO_AUTHORIAL_INTENT_CLAIM"],
        })

    for motif in motifs:
        motif_id = _non_empty_string(motif.get("motif_id"))
        cue_numbers = motif.get("cue_numbers")
        if motif_id is None or not isinstance(cue_numbers, list) or not all(_cue_number(number) for number in cue_numbers):
            raise ArtisticEvidenceFusionError("REVERSE_TRANSLATION_MOTIF_CONTENT_INVALID")
        refs = [cue_ref_by_number[number] for number in cue_numbers if number in cue_ref_by_number]
        if len(refs) != len(cue_numbers):
            raise ArtisticEvidenceFusionError("REVERSE_TRANSLATION_MOTIF_CUE_REFERENCE_INVALID")
        motif_ref = f"sequence:{sequence_no}:motif:{motif_id}"
        known_refs.add(motif_ref)
        facts.append({
            "finding_id": f"FACT_{motif_id}",
            "classification": "EXACT_RECURRING_STORED_CUE_CONTENT",
            "statement": f"Native Sequence {sequence_no} contains exact repeated stored CueData for Cues {', '.join(cue_numbers)}.",
            "evidence_refs": [motif_ref, *refs],
            "confidence": _fact_confidence(translation_status),
            "limits": ["NO_SONG_SECTION_CLAIM", "NO_VISUAL_OUTPUT_CLAIM", "NO_AUTHORIAL_INTENT_CLAIM"],
        })

    for source in sources:
        for observation in source["observations"]:
            ref = _source_ref(source["evidence_id"], observation["observation_id"])
            known_refs.add(ref)
            facts.append({
                "finding_id": f"FACT_CONTEXT_{source['evidence_id']}_{observation['observation_id']}",
                "classification": f"SUPPLIED_{source['source_type']}_OBSERVATION",
                "statement": observation["claim"],
                "evidence_refs": [ref],
                "confidence": observation["confidence"] if source["status"] == "VERIFIED" else "LOW",
                "source_ref": source["source_ref"],
                "temporal_evidence": observation["temporal_evidence"],
                "limits": ["SUPPLIED_CONTEXT_NOT_NATIVE_SEQUENCE_FACT", "NO_AUTHORIAL_INTENT_CLAIM"],
            })
            for cue_number in observation["cue_refs"]:
                if cue_number in cue_ref_by_number:
                    context_by_cue[cue_number].append({**source, "observation": observation, "ref": ref})

    inferences: list[dict[str, Any]] = []
    for cue_number, entries in sorted(context_by_cue.items()):
        for entry in entries:
            observation = entry["observation"]
            inferences.append({
                "finding_id": f"INFERENCE_SEQUENCE_{sequence_no}_CUE_{cue_number.replace('.', '_')}_{entry['evidence_id']}_{observation['observation_id']}",
                "classification": "EXPLICIT_CUE_TO_CONTEXT_CORRELATION",
                "statement": (
                    f"Sequence {sequence_no} Cue {cue_number} is explicitly linked by supplied "
                    f"{entry['source_type']} evidence to observation {observation['observation_id']}."
                ),
                "evidence_refs": [cue_ref_by_number[cue_number], entry["ref"]],
                "confidence": _correlation_confidence(translation_status, entry["status"], observation["confidence"]),
                "limits": [
                    "CORRELATION_ONLY",
                    "DOES_NOT_ESTABLISH_VISUAL_OUTPUT",
                    "DOES_NOT_ESTABLISH_PROGRAMMER_OR_ARTIST_INTENT",
                ],
            })

    for motif in motifs:
        motif_id = _non_empty_string(motif.get("motif_id"))
        cue_numbers = [str(number) for number in motif.get("cue_numbers", [])]
        if motif_id is None or not cue_numbers:
            continue
        tag_sets: list[set[str]] = []
        matching_refs: dict[str, list[str]] = defaultdict(list)
        for cue_number in cue_numbers:
            tags = {
                tag
                for entry in context_by_cue.get(cue_number, [])
                if entry["source_type"] in {"SONG_STRUCTURE", "AUDIO_ANALYSIS"}
                for tag in entry["observation"]["tags"]
            }
            tag_sets.append(tags)
            for entry in context_by_cue.get(cue_number, []):
                if entry["source_type"] in {"SONG_STRUCTURE", "AUDIO_ANALYSIS"}:
                    for tag in entry["observation"]["tags"]:
                        matching_refs[tag].append(entry["ref"])
        common_tags = set.intersection(*tag_sets) if tag_sets else set()
        for tag in sorted(common_tags):
            refs = [f"sequence:{sequence_no}:motif:{motif_id}", *sorted(set(matching_refs[tag]))]
            inferences.append({
                "finding_id": f"INFERENCE_{motif_id}_TAG_{tag}",
                "classification": "EXACT_CONTENT_RECURRENCE_WITH_SHARED_CONTEXT_TAG",
                "statement": (
                    f"Exact repeated stored CueData {motif_id} occurs on Cues carrying the supplied "
                    f"song/audio context tag {tag}."
                ),
                "evidence_refs": refs,
                "confidence": "MEDIUM" if translation_status == "OBSERVED" else "LOW",
                "limits": [
                    "TAG_CORRELATION_ONLY",
                    "DOES_NOT_ESTABLISH_A_DESIGN_MOTIF_INTENTION",
                    "DOES_NOT_ESTABLISH_VISUAL_OUTPUT",
                ],
            })

    hypotheses_output = _validate_hypotheses(hypotheses, known_refs)
    return {
        "schema": ARTISTIC_EVIDENCE_FUSION_SCHEMA,
        "reference_kind": "READ_ONLY_OFFLINE_ARTISTIC_EVIDENCE_FUSION",
        "read_only": True,
        "source_sequence": {
            "sequence_no": sequence_no,
            "translation_status": translation_status,
        },
        "source_evidence": [
            {key: source[key] for key in ("evidence_id", "source_type", "source_ref", "status")}
            for source in sources
        ],
        "layers": {
            "FACT": sorted(facts, key=lambda item: item["finding_id"]),
            "INFERENCE": sorted(inferences, key=lambda item: item["finding_id"]),
            "HYPOTHESIS": hypotheses_output,
        },
        "prohibited_promotions": [
            "NATIVE_XML_TO_VISUAL_OUTPUT_FACT",
            "NATIVE_XML_TO_AUTHORIAL_INTENT_FACT",
            "CONTEXT_CORRELATION_TO_CAUSALITY_FACT",
            "ANY_FUSION_FINDING_TO_MA2_WRITE_AUTHORIZATION",
        ],
        "use_constraints": [
            "DESCRIPTIVE_AND_RECONSTRUCTION_RESEARCH_ONLY",
            "REQUIRES_CURRENT_SHOW_RESOURCE_VALIDATION_BEFORE_ANY_REUSE",
            "DOES_NOT_BYPASS_PREVIEW_APPROVAL_OR_POSTWRITE_VERIFICATION",
        ],
    }


__all__ = [
    "ARTISTIC_EVIDENCE_FUSION_SCHEMA",
    "CONTEXT_EVIDENCE_SCHEMA",
    "HYPOTHESIS_INPUT_SCHEMA",
    "ArtisticEvidenceFusionError",
    "fuse_artistic_evidence",
]
