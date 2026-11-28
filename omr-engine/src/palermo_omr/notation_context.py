"""Orquestación segura de clave, armadura y alturas para una página."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping, Sequence

from .clef_candidates import StaffClefCandidate, build_staff_clef_candidates
from .key_signature_candidates import KeySignatureCandidate, build_key_signature_candidates
from .pitch_candidates import PitchCandidate, build_pitch_candidates


@dataclass(frozen=True)
class NotationPitchResult:
    clef_context: tuple[StaffClefCandidate, ...]
    key_signature_candidates: tuple[KeySignatureCandidate, ...]
    applied_key_signatures: dict[int, dict[str, int]]
    pitch_candidates: tuple[PitchCandidate, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "clef_context": [item.to_dict() for item in self.clef_context],
            "key_signature_candidates": [item.to_dict() for item in self.key_signature_candidates],
            "applied_key_signatures": {str(i): dict(v) for i, v in self.applied_key_signatures.items()},
            "pitch_candidates": [item.to_dict() for item in self.pitch_candidates],
        }


def build_pitch_candidates_with_notation_context(
    noteheads: Sequence[Any], manifest: dict[str, Any], *, page_number: int,
    staff_indices: list[int], staff_lines: Mapping[int, list[float]],
    accepted_key_signature_staff_indices: set[int] | None = None,
    source_kinds: Sequence[str] | None = None,
    explicit_accidentals: Sequence[str | None] | None = None,
    measure_ids: Sequence[str | int] | None = None,
    simultaneous_group_ids: Sequence[str | int] | None = None,
    source_indices: Sequence[int] | None = None,
) -> NotationPitchResult:
    """Usa claves confirmadas; aplica armaduras solo para pentagramas aceptados."""
    clef_context = build_staff_clef_candidates(
        manifest, page_number=page_number, staff_indices=staff_indices
    )
    confirmed_clefs = {
        item.staff_index: item.clef for item in clef_context
        if item.status == "human_confirmed" and item.clef is not None
    }
    key_candidates = build_key_signature_candidates(
        manifest, page_number=page_number, staff_clefs=confirmed_clefs,
        staff_lines=staff_lines,
    )
    accepted = accepted_key_signature_staff_indices
    if accepted is None:
        accepted = set()
    if not isinstance(accepted, set) or any(
        not isinstance(i, int) or isinstance(i, bool) or i < 0 for i in accepted
    ):
        raise ValueError("accepted_key_signature_staff_indices debe ser un conjunto de índices no negativos")
    unknown = accepted - set(staff_indices)
    if unknown:
        raise ValueError(f"Se intentó aceptar armadura de pentagramas fuera del alcance: {sorted(unknown)}")
    by_staff = {item.staff_index: item for item in key_candidates}
    invalid = {
        i for i in accepted
        if i not in by_staff or by_staff[i].status != "candidate_requires_human_acceptance"
    }
    if invalid:
        raise ValueError(f"No hay candidato de armadura válido para aceptar en pentagramas: {sorted(invalid)}")
    applied = {i: dict(by_staff[i].key_signature or {}) for i in sorted(accepted)}
    pitches = build_pitch_candidates(
        noteheads, staff_clefs=confirmed_clefs, key_signatures=applied,
        source_kinds=source_kinds, explicit_accidentals=explicit_accidentals,
        measure_ids=measure_ids, simultaneous_group_ids=simultaneous_group_ids,
        source_indices=source_indices,
    )
    return NotationPitchResult(tuple(clef_context), tuple(key_candidates), applied, tuple(pitches))
