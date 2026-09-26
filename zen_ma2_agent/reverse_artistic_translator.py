"""Read-only translation of native MA2 Sequence evidence into design references.

This module deliberately describes what a retained native Sequence Export
proves.  It is not a Show writer, a command generator, or a claim that XML
alone reveals a programmer's musical or artistic intention.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping

from .state.providers.sequence_export import sequence_export_discovery


REVERSE_ARTISTIC_TRANSLATION_SCHEMA = "zen.ma2_reverse_artistic_translation.v0.1"
DESIGN_REFERENCE_SCHEMA = "zen.ma2_design_reference.v0.1"
SEQUENCE_COLLECTION_SCHEMA = "zen.ma2_reverse_sequence_collection.v0.1"
_DISCOVERY_SCHEMA = "zen.sequence_export_discovery.v0.1"
_SHA256 = re.compile(r"[0-9a-f]{64}")
_DIMENSIONS = {
    "DIM": "DIMMER",
    "DIMMER": "DIMMER",
    "PAN": "POSITION",
    "TILT": "POSITION",
    "FOCUS": "FOCUS",
    "ZOOM": "ZOOM",
    "FROST": "FROST",
    "GOBO": "GOBO",
    "PRISM": "PRISM",
}


class ReverseArtisticTranslationError(ValueError):
    """Native evidence is incomplete or does not meet the read-only contract."""


def _positive_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if value > 0 else None
    if isinstance(value, str) and value.isdigit():
        result = int(value)
        return result if result > 0 else None
    return None


def _cue_number(cue: Mapping[str, Any]) -> str | None:
    value = cue.get("number")
    if not isinstance(value, Mapping):
        return None
    number = _positive_int(value.get("number"))
    if number is None:
        return None
    sub = value.get("sub_number")
    return str(number) if sub in (None, "", "0", 0) else f"{number}.{sub}"


def _attribute(row: Mapping[str, Any]) -> str | None:
    channel = row.get("channel")
    if not isinstance(channel, Mapping):
        return None
    value = channel.get("attribute_name")
    if not isinstance(value, str):
        return None
    normalized = value.strip().upper()
    return normalized or None


def _dimension(attribute: str) -> str:
    if attribute.startswith("COLOR"):
        return "COLOR"
    if attribute.startswith("BEAM"):
        return "BEAM"
    if attribute.startswith("STROBE") or attribute.startswith("SHUTTER"):
        return "STROBE"
    return _DIMENSIONS.get(attribute, "UNCLASSIFIED")


def _address_reference(value: object) -> str | None:
    if not isinstance(value, Mapping):
        return None
    components = value.get("no_components")
    if not isinstance(components, list) or not components:
        return None
    cleaned = [str(item).strip() for item in components]
    return ".".join(cleaned) if all(item.isdigit() for item in cleaned) else None


def _has_raw_value(row: Mapping[str, Any]) -> bool:
    values = row.get("raw_values")
    return isinstance(values, Mapping) and values.get("Value") is not None


def _layer_kinds(row: Mapping[str, Any]) -> tuple[str, ...]:
    kinds: list[str] = []
    if _has_raw_value(row):
        kinds.append("RAW_VALUE")
    if _address_reference(row.get("preset")):
        kinds.append("PRESET_REFERENCE")
    if _address_reference(row.get("effect")):
        kinds.append("EFFECT_REFERENCE")
    return tuple(kinds) or ("UNCLASSIFIED_CUE_DATA",)


def _decimal_values(rows: list[Mapping[str, Any]], field: str) -> list[str]:
    values: list[str] = []
    for row in rows:
        raw_values = row.get("raw_values")
        raw = raw_values.get(field) if isinstance(raw_values, Mapping) else None
        if raw is None:
            continue
        try:
            values.append(str(Decimal(str(raw).strip())))
        except (InvalidOperation, ValueError):
            continue
    return values


def _cue_rows(cue: Mapping[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    parts: list[dict[str, Any]] = []
    raw_parts = cue.get("parts")
    for part in raw_parts if isinstance(raw_parts, list) else []:
        if not isinstance(part, Mapping):
            continue
        part_rows = [item for item in part.get("cue_data", []) if isinstance(item, Mapping)]
        parts.append({
            "index": part.get("index"),
            "name": part.get("name"),
            "cue_data_count": len(part_rows),
        })
        rows.extend(dict(item) for item in part_rows)
    return rows, parts


def _semantic_signature(rows: list[Mapping[str, Any]]) -> dict[str, list[str]]:
    attributes = sorted({attribute for row in rows if (attribute := _attribute(row))})
    layers = sorted({kind for row in rows for kind in _layer_kinds(row)})
    dimensions = sorted({_dimension(attribute) for attribute in attributes})
    return {"attributes": attributes, "dimensions": dimensions, "layers": layers}


def _content_signature(cue: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Canonical observed CueData, including targets, values and resource IDs.

    Repetition of attribute names alone is too weak to identify a recurring
    design. Only identical stored content qualifies for a content motif.
    """
    signature: list[dict[str, Any]] = []
    for part in cue.get("parts", []):
        if not isinstance(part, Mapping):
            continue
        for row in part.get("cue_data", []):
            if not isinstance(row, Mapping):
                continue
            channel = row.get("channel")
            raw_values = row.get("raw_values")
            signature.append({
                "part_index": part.get("index"),
                "channel": {
                    key: str(channel[key]) for key in
                    ("fixture_id", "subfixture_id", "channel_id", "attribute_name")
                    if isinstance(channel, Mapping) and key in channel
                },
                "raw_values": {
                    key: str(value) for key, value in raw_values.items() if value is not None
                } if isinstance(raw_values, Mapping) else {},
                "preset": _address_reference(row.get("preset")),
                "effect": _address_reference(row.get("effect")),
                "effect_low_preset": _address_reference(row.get("effect_low_preset")),
                "effect_high_preset": _address_reference(row.get("effect_high_preset")),
            })
    return sorted(signature, key=lambda item: json.dumps(item, sort_keys=True))


def _fingerprint(signature: Mapping[str, object]) -> str:
    encoded = json.dumps(signature, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _validate_discovery(discovery: Mapping[str, Any]) -> None:
    if discovery.get("schema") != _DISCOVERY_SCHEMA:
        raise ReverseArtisticTranslationError("UNSUPPORTED_SEQUENCE_EVIDENCE_SCHEMA")
    if discovery.get("read_only") is not True:
        raise ReverseArtisticTranslationError("SEQUENCE_EVIDENCE_MUST_BE_READ_ONLY")
    if discovery.get("source") != "MA2_EXPORT_SEQUENCE_XML":
        raise ReverseArtisticTranslationError("UNSUPPORTED_SEQUENCE_EVIDENCE_SOURCE")
    if discovery.get("status") not in {"VERIFIED", "PARTIAL"}:
        raise ReverseArtisticTranslationError("SEQUENCE_EVIDENCE_NOT_TRANSLATABLE")
    if _positive_int(discovery.get("sequence_no")) is None:
        raise ReverseArtisticTranslationError("SEQUENCE_EVIDENCE_SEQUENCE_INVALID")
    xml = discovery.get("xml_discovery")
    if not isinstance(xml, Mapping) or not isinstance(xml.get("sha256"), str) or not _SHA256.fullmatch(xml["sha256"]):
        raise ReverseArtisticTranslationError("SEQUENCE_EVIDENCE_SHA256_INVALID")
    if not isinstance(discovery.get("cues"), list):
        raise ReverseArtisticTranslationError("SEQUENCE_EVIDENCE_CUES_INVALID")


def translate_sequence_evidence(discovery: Mapping[str, Any]) -> dict[str, Any]:
    """Create a descriptive, machine-readable design reference from one Sequence.

    ``discovery`` must be output from :func:`sequence_export_discovery` or the
    same immutable data contract.  Partial source evidence remains partial in
    every output layer; this function never upgrades it to a write-verifier.
    """
    _validate_discovery(discovery)
    cue_semantics: list[dict[str, Any]] = []
    numbered_cues = 0
    unnumbered_cues = 0
    attributes: Counter[str] = Counter()
    dimensions: Counter[str] = Counter()
    fixture_ids: set[int] = set()
    preset_refs: Counter[str] = Counter()
    effect_refs: Counter[str] = Counter()

    for ordinal, raw_cue in enumerate(discovery["cues"], start=1):
        if not isinstance(raw_cue, Mapping):
            continue
        number = _cue_number(raw_cue)
        if number is None:
            unnumbered_cues += 1
            continue
        numbered_cues += 1
        rows, parts = _cue_rows(raw_cue)
        signature = _semantic_signature(rows)
        content_signature = _content_signature(raw_cue)
        cue_attributes = signature["attributes"]
        cue_dimensions = signature["dimensions"]
        attributes.update(cue_attributes)
        dimensions.update(cue_dimensions)
        layer_counts = Counter(kind for row in rows for kind in _layer_kinds(row))
        cue_fixtures: set[int] = set()
        for row in rows:
            channel = row.get("channel")
            fixture = _positive_int(channel.get("fixture_id")) if isinstance(channel, Mapping) else None
            if fixture is not None:
                fixture_ids.add(fixture)
                cue_fixtures.add(fixture)
            if (reference := _address_reference(row.get("preset"))):
                preset_refs[reference] += 1
            if (reference := _address_reference(row.get("effect"))):
                effect_refs[reference] += 1
        cue_semantics.append({
            "cue_number": number,
            "source_ordinal": ordinal,
            "parts": parts,
            "evidence_status": "OBSERVED" if rows else "NO_CUE_DATA_OBSERVED",
            "observable_layers": dict(sorted(layer_counts.items())),
            "observable_attributes": cue_attributes,
            "observable_dimensions": cue_dimensions,
            "fixture_count": len(cue_fixtures),
            "preset_references": sorted({_address_reference(row.get("preset")) for row in rows} - {None}),
            "effect_references": sorted({_address_reference(row.get("effect")) for row in rows} - {None}),
            "timing_values": {
                "fade": sorted(set(_decimal_values(rows, "Fade"))),
                "delay": sorted(set(_decimal_values(rows, "Delay"))),
            },
            "structural_fingerprint": _fingerprint(signature),
            "content_fingerprint": _fingerprint({"cue_data": content_signature}),
            "observed_cue_data": content_signature,
            "intent_status": "NOT_INFERRED_FROM_SEQUENCE_XML",
        })

    recurring: list[dict[str, Any]] = []
    by_fingerprint: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for cue in cue_semantics:
        if discovery["status"] == "VERIFIED" and cue["evidence_status"] == "OBSERVED":
            by_fingerprint[str(cue["content_fingerprint"])].append(cue)
    for fingerprint, cues in sorted(by_fingerprint.items()):
        if len(cues) < 2:
            continue
        recurring.append({
            "motif_id": f"CONTENT_{fingerprint[:12].upper()}",
            "classification": "RECURRING_STORED_CUE_CONTENT",
            "confidence": "OBSERVED_IN_NATIVE_SEQUENCE_EVIDENCE",
            "cue_numbers": [cue["cue_number"] for cue in cues],
            "occurrences": len(cues),
            "observable_signature": {
                "attributes": cues[0]["observable_attributes"],
                "dimensions": cues[0]["observable_dimensions"],
                "layers": sorted(cues[0]["observable_layers"]),
            },
            "interpretation_limit": "Identical stored CueData does not prove song section, visual result, or programmer intent.",
        })

    source_status = str(discovery["status"])
    technical_structure = {
        "sequence_no": discovery["sequence_no"],
        "numbered_cue_count": numbered_cues,
        "unnumbered_system_cue_count": unnumbered_cues,
        "observed_fixture_count": len(fixture_ids),
        "observed_attributes": dict(sorted(attributes.items())),
        "observed_dimensions": dict(sorted(dimensions.items())),
        "preset_reference_uses": dict(sorted(preset_refs.items())),
        "effect_reference_uses": dict(sorted(effect_refs.items())),
        "source_integrity": source_status,
    }
    design_reference = {
        "schema": DESIGN_REFERENCE_SCHEMA,
        "reference_kind": "READ_ONLY_SEQUENCE_DESIGN_REFERENCE",
        "source_evidence": {
            "source": discovery["source"],
            "sequence_no": discovery["sequence_no"],
            "sequence_export_sha256": discovery["xml_discovery"]["sha256"],
            "integrity": source_status,
        },
        "observed_cue_vocabulary": {
            "dimensions": sorted(dimensions),
            "preset_references": sorted(preset_refs),
            "effect_references": sorted(effect_refs),
        },
        "cue_patterns": [
            {
                "cue_number": cue["cue_number"],
                "source_ordinal": cue["source_ordinal"],
                "evidence_status": cue["evidence_status"],
                "dimensions": cue["observable_dimensions"],
                "layers": cue["observable_layers"],
                "preset_references": cue["preset_references"],
                "effect_references": cue["effect_references"],
                "structural_fingerprint": cue["structural_fingerprint"],
                "content_fingerprint": cue["content_fingerprint"],
                "observed_cue_data": cue["observed_cue_data"],
            }
            for cue in cue_semantics
        ],
        "recurring_motifs": recurring,
        "prohibited_inferences": [
            "ARTIST_OR_PROGRAMMER_INTENT",
            "SONG_SECTION_OR_MUSICAL_ALIGNMENT",
            "VISUAL_OUTPUT_OR_CAMERA_RESULT",
            "PATCH_ADDRESS_FIXTURE_IDENTITY_OR_TYPE",
            "MA2_WRITE_COMMANDS",
        ],
        "use_constraints": [
            "DESCRIPTIVE_ONLY",
            "REQUIRES_CURRENT_SHOW_RESOURCE_VALIDATION_BEFORE_ANY_REUSE",
            "DOES_NOT_BYPASS_PREVIEW_APPROVAL_OR_POSTWRITE_VERIFICATION",
        ],
    }
    return {
        "schema": REVERSE_ARTISTIC_TRANSLATION_SCHEMA,
        "read_only": True,
        "translation_status": "PARTIAL_EVIDENCE" if source_status == "PARTIAL" else "OBSERVED",
        "technical_structure": technical_structure,
        "cue_semantics": cue_semantics,
        "recurring_artistic_motifs": recurring,
        "machine_readable_design_reference": design_reference,
    }


def translate_sequence_xml(xml: str | bytes, sequence_no: int) -> dict[str, Any]:
    """Offline convenience entry point for a retained native Sequence XML file."""
    return translate_sequence_evidence(sequence_export_discovery(xml, sequence_no))


def translate_sequence_collection(discoveries: list[Mapping[str, Any]]) -> dict[str, Any]:
    """Find repeated stored content across distinct offline Sequence exports.

    Native Sequence XML does not contain an authoritative Show UUID. Callers
    must not interpret collection membership as proof of a shared Show.
    """
    if not discoveries:
        raise ReverseArtisticTranslationError("SEQUENCE_COLLECTION_EMPTY")
    translations = [translate_sequence_evidence(item) for item in discoveries]
    sequence_numbers = [item["technical_structure"]["sequence_no"] for item in translations]
    if len(sequence_numbers) != len(set(sequence_numbers)):
        raise ReverseArtisticTranslationError("SEQUENCE_COLLECTION_DUPLICATE_NUMBER")
    occurrences: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for translation in translations:
        if translation["translation_status"] != "OBSERVED":
            continue
        sequence_no = translation["technical_structure"]["sequence_no"]
        for cue in translation["cue_semantics"]:
            if cue["evidence_status"] == "OBSERVED":
                occurrences[cue["content_fingerprint"]].append({
                    "sequence_no": sequence_no,
                    "cue_number": cue["cue_number"],
                })
    motifs = [
        {
            "motif_id": f"CONTENT_{fingerprint[:12].upper()}",
            "classification": "RECURRING_STORED_CUE_CONTENT_ACROSS_SEQUENCES",
            "content_fingerprint": fingerprint,
            "occurrences": occurrences[fingerprint],
            "source_relation": "SAME_SHOW_NOT_VERIFIED_BY_SEQUENCE_XML",
        }
        for fingerprint in sorted(occurrences)
        if len({item["sequence_no"] for item in occurrences[fingerprint]}) > 1
    ]
    return {
        "schema": SEQUENCE_COLLECTION_SCHEMA,
        "read_only": True,
        "source_relation": "SAME_SHOW_NOT_VERIFIED_BY_SEQUENCE_XML",
        "sequence_translations": translations,
        "cross_sequence_motifs": motifs,
    }


__all__ = [
    "DESIGN_REFERENCE_SCHEMA",
    "REVERSE_ARTISTIC_TRANSLATION_SCHEMA",
    "SEQUENCE_COLLECTION_SCHEMA",
    "ReverseArtisticTranslationError",
    "translate_sequence_evidence",
    "translate_sequence_collection",
    "translate_sequence_xml",
]
