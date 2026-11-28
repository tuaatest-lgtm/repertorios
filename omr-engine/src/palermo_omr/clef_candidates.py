"""Contexto de clave por pentagrama con trazabilidad y estado explícito.

Solo las etiquetas humanas confirmadas producen una clave resuelta. Los glifos
pendientes, las contradicciones y la ausencia de evidencia nunca se convierten
en una clave por defecto.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .glyph_labeling import validate_glyph_manifest_data

_CLEF_LABELS = {
    "treble_clef": "treble",
    "bass_clef": "bass",
    "alto_clef": "alto",
    "tenor_clef": "tenor",
}


@dataclass(frozen=True)
class StaffClefCandidate:
    page_number: int
    staff_index: int
    status: str
    clef: str | None
    glyph_ids: tuple[str, ...]
    pending_glyph_ids: tuple[str, ...]
    warning: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_staff_clef_candidates(
    manifest: dict[str, Any],
    *,
    page_number: int,
    staff_indices: list[int],
) -> list[StaffClefCandidate]:
    """Construye un registro de clave por pentagrama sin inferir claves ausentes."""
    validate_glyph_manifest_data(manifest)
    if not isinstance(page_number, int) or isinstance(page_number, bool) or page_number < 1:
        raise ValueError("page_number debe ser un entero positivo")
    if not isinstance(staff_indices, list) or not staff_indices:
        raise ValueError("staff_indices debe contener al menos un índice")
    if any(not isinstance(i, int) or isinstance(i, bool) or i < 0 for i in staff_indices):
        raise ValueError("staff_indices debe contener enteros no negativos")
    if len(set(staff_indices)) != len(staff_indices):
        raise ValueError("staff_indices no puede contener duplicados")

    page_glyphs = [
        glyph for glyph in manifest["glyphs"]
        if glyph["page_number"] == page_number
        and glyph["staff_index"] in set(staff_indices)
    ]
    results = []
    for staff_index in staff_indices:
        glyphs = [g for g in page_glyphs if g["staff_index"] == staff_index]
        confirmed = [
            g for g in glyphs
            if g["label_status"] == "labeled_by_human"
            and g["label"] in _CLEF_LABELS
        ]
        pending = [
            g for g in glyphs
            if g["label_status"] == "pending_human_review"
        ]
        clefs = {_CLEF_LABELS[g["label"]] for g in confirmed}
        confirmed_ids = tuple(sorted(g["candidate_id"] for g in confirmed))
        pending_ids = tuple(sorted(g["candidate_id"] for g in pending))

        if len(clefs) > 1:
            results.append(StaffClefCandidate(
                page_number, staff_index, "conflicting_human_labels", None,
                confirmed_ids, pending_ids,
                "Hay etiquetas humanas de claves incompatibles; requiere resolver la contradicción.",
            ))
        elif len(clefs) == 1:
            clef = next(iter(clefs))
            results.append(StaffClefCandidate(
                page_number, staff_index, "human_confirmed", clef,
                confirmed_ids, pending_ids,
                "Clave confirmada mediante etiqueta humana; no se infiere desde geometría.",
            ))
        elif pending:
            results.append(StaffClefCandidate(
                page_number, staff_index, "pending_human_review", None,
                (), pending_ids,
                "Hay glifos pendientes; la clave permanece sin resolver.",
            ))
        else:
            results.append(StaffClefCandidate(
                page_number, staff_index, "no_clef_evidence", None,
                (), (),
                "No hay evidencia de clave para este pentagrama; no se asigna una por defecto.",
            ))
    return results
