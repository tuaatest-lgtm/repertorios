"""Candidatos de armadura derivados de glifos etiquetados por una persona.

La secuencia y la posición se comprueban musicalmente, pero el resultado sigue
siendo candidato: nunca se aplica a alturas sin una aceptación posterior.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from typing import Mapping

from .pitch import pitch_from_staff_step


_SHARP_ORDER = ("F", "C", "G", "D", "A", "E", "B")
_FLAT_ORDER = ("B", "E", "A", "D", "G", "C", "F")
_LABEL_TO_ALTERATION = {"sharp": 1, "flat": -1}


@dataclass(frozen=True)
class KeySignatureCandidate:
    staff_index: int
    status: str
    key_signature: dict[str, int] | None
    accidental_type: str | None
    glyph_ids: list[str]
    observed_letters: list[str]
    warning: str

    def to_dict(self) -> dict:
        return asdict(self)


def build_key_signature_candidates(
    manifest: dict,
    *,
    page_number: int,
    staff_clefs: Mapping[int, str],
    staff_lines: Mapping[int, list[float]],
) -> list[KeySignatureCandidate]:
    """Deriva armaduras candidatas solo de etiquetas humanas y posiciones.

    Exige que los glifos estén etiquetados por una persona, que pertenezcan a
    una misma página/pentagrama y que su secuencia horizontal coincida con el
    orden convencional de sostenidos o bemoles. El resultado requiere revisión.
    """
    glyphs = manifest.get("glyphs")
    if not isinstance(glyphs, list):
        raise ValueError("manifest debe contener una lista glyphs")
    if not isinstance(page_number, int) or isinstance(page_number, bool) or page_number < 1:
        raise ValueError("page_number debe ser un entero positivo")

    grouped: dict[int, list[dict]] = {}
    for glyph in glyphs:
        if not isinstance(glyph, dict):
            raise ValueError("Cada glifo debe ser un objeto")
        if glyph.get("page_number") != page_number or glyph.get("label_status") != "labeled_by_human":
            continue
        if glyph.get("label") not in _LABEL_TO_ALTERATION:
            continue
        staff_index = glyph.get("staff_index")
        bbox = glyph.get("candidate_bbox")
        if not isinstance(staff_index, int) or isinstance(staff_index, bool) or staff_index < 0:
            raise ValueError("staff_index inválido en glifo etiquetado")
        if not isinstance(bbox, list) or len(bbox) != 4 or any(
            not isinstance(value, (int, float)) or isinstance(value, bool)
            or not math.isfinite(float(value)) for value in bbox
        ):
            raise ValueError("candidate_bbox inválido en glifo etiquetado")
        if bbox[0] < 0 or bbox[1] < 0 or bbox[2] <= 0 or bbox[3] <= 0:
            raise ValueError("candidate_bbox debe tener origen no negativo y dimensiones positivas")
        grouped.setdefault(staff_index, []).append(glyph)

    results = []
    for staff_index, items in sorted(grouped.items()):
        clef = staff_clefs.get(staff_index)
        lines = staff_lines.get(staff_index)
        ids = [str(item.get("candidate_id", "")) for item in sorted(items, key=lambda g: g["candidate_bbox"][0])]
        if clef is None or not isinstance(lines, list) or len(lines) != 5:
            results.append(KeySignatureCandidate(
                staff_index, "unresolved_staff_context", None, None, ids, [],
                "Falta clave confirmada o las cinco líneas del pentagrama; no se infiere armadura.",
            ))
            continue
        if any(
            isinstance(value, bool) or not isinstance(value, (int, float))
            or not math.isfinite(float(value)) for value in lines
        ):
            raise ValueError("Las líneas del pentagrama deben ser coordenadas finitas")
        if any(float(lines[index]) >= float(lines[index + 1]) for index in range(4)):
            raise ValueError("Las cinco líneas deben estar ordenadas de arriba hacia abajo")
        spacing = (float(lines[-1]) - float(lines[0])) / 4.0
        if spacing <= 1:
            raise ValueError("El espaciado del pentagrama no es válido")
        ordered = sorted(items, key=lambda glyph: glyph["candidate_bbox"][0])
        labels = [glyph["label"] for glyph in ordered]
        if len(set(labels)) != 1:
            results.append(KeySignatureCandidate(
                staff_index, "ambiguous_mixed_accidentals", None, None, ids, [],
                "Se mezclan sostenidos y bemoles; la armadura queda sin resolver.",
            ))
            continue
        accidental_type = labels[0]
        expected = _SHARP_ORDER if accidental_type == "sharp" else _FLAT_ORDER
        observed = []
        for glyph in ordered:
            _, y, _, height = glyph["candidate_bbox"]
            center_y = float(y) + float(height) / 2.0
            step = int(round((float(lines[-1]) - center_y) / (spacing / 2.0)))
            snapped_y = float(lines[-1]) - step * spacing / 2.0
            if abs(center_y - snapped_y) > spacing * 0.30:
                observed.append("?")
                continue
            pitch = pitch_from_staff_step(step, clef)
            observed.append(pitch.step)
        valid = (
            1 <= len(observed) <= 7
            and "?" not in observed
            and tuple(observed) == expected[:len(observed)]
        )
        if not valid:
            results.append(KeySignatureCandidate(
                staff_index, "ambiguous_order_or_position", None, accidental_type,
                ids, observed,
                "La posición o el orden no coincide con una secuencia convencional; requiere revisión.",
            ))
            continue
        alteration = _LABEL_TO_ALTERATION[accidental_type]
        signature = {letter: alteration for letter in observed}
        results.append(KeySignatureCandidate(
            staff_index, "candidate_requires_human_acceptance", signature,
            accidental_type, ids, observed,
            "Armadura candidata derivada de etiquetas humanas; no se aplica automáticamente a las notas.",
        ))
    return results
