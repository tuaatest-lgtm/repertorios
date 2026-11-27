"""Reconstrucción de cadenas de ligaduras ya confirmadas por revisión humana.

Una cadena de ligaduras representa un único ataque musical cuya duración
abarca varias cabezas/notaciones. Este módulo no detecta ni confirma arcos:
consume exclusivamente propuestas no ambiguas y confirmaciones explícitas.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from fractions import Fraction

from .duration_math import sum_tied_durations
from .tie_candidates import TieLinkCandidate, TieReviewConfirmation


@dataclass(frozen=True)
class ReviewedTieChain:
    """Una única nota sostenida a través de varios eventos notados."""

    event_ids: tuple[str, ...]
    combined_duration_quarters: Fraction

    def to_dict(self) -> dict:
        result = asdict(self)
        result["combined_duration_quarters"] = str(self.combined_duration_quarters)
        return result


def build_reviewed_tie_chains(
    candidates: Sequence[TieLinkCandidate],
    confirmations: Sequence[TieReviewConfirmation],
    event_durations_quarters: Mapping[str, Fraction | int | float],
) -> tuple[ReviewedTieChain, ...]:
    """Une ligaduras confirmadas en cadenas sin crear ataques intermedios.

    Cada evento puede tener como máximo un predecesor y un sucesor. Se
    rechazan bifurcaciones, fusiones y ciclos; las cadenas se devuelven desde
    su primera nota y con duración exacta (Fraction). Los eventos no enlazados
    no se incluyen: el llamador conserva sus ataques normales.
    """
    outgoing: dict[str, str] = {}
    incoming: dict[str, str] = {}
    seen_confirmation_indices: set[int] = set()

    for confirmation in confirmations:
        if not isinstance(confirmation, TieReviewConfirmation):
            raise ValueError("Todas las confirmaciones deben ser TieReviewConfirmation")
        index = confirmation.candidate_index
        if (
            not isinstance(index, int) or isinstance(index, bool)
            or not 0 <= index < len(candidates)
        ):
            raise ValueError("candidate_index fuera del rango de candidatos")
        if index in seen_confirmation_indices:
            raise ValueError("Una propuesta solo puede confirmarse una vez")
        seen_confirmation_indices.add(index)
        candidate = candidates[index]
        if candidate.status != "proposed_tie":
            raise ValueError("Una propuesta ambigua no puede confirmarse")
        if confirmation.reviewer_confirmed is not True:
            raise ValueError("Se requiere revisión humana explícita")
        if confirmation.arc_is_tie_confirmed is not True:
            raise ValueError("El arco debe confirmarse como ligadura de prolongación")
        if confirmation.same_notated_pitch_confirmed is not True:
            raise ValueError("Debe confirmarse que ambas notas tienen la misma escritura")

        source, target = candidate.source_event_id, candidate.target_event_id
        if source == target:
            raise ValueError("Una ligadura no puede enlazar un evento consigo mismo")
        if source in outgoing:
            raise ValueError("Una nota no puede tener dos sucesoras en una cadena de ligaduras")
        if target in incoming:
            raise ValueError("Una nota no puede tener dos predecesoras en una cadena de ligaduras")
        outgoing[source] = target
        incoming[target] = source

    if not outgoing:
        return ()

    nodes = set(outgoing) | set(incoming)
    missing_durations = nodes - set(event_durations_quarters)
    if missing_durations:
        raise ValueError("Faltan duraciones para eventos enlazados: " + ", ".join(sorted(missing_durations)))

    starts = sorted(nodes - set(incoming))
    visited: set[str] = set()
    chains: list[ReviewedTieChain] = []
    for start in starts:
        chain: list[str] = []
        current = start
        while current in outgoing:
            if current in visited:
                raise ValueError("Se detectó un ciclo en la cadena de ligaduras")
            visited.add(current)
            chain.append(current)
            current = outgoing[current]
        if current in visited:
            raise ValueError("Se detectó un ciclo en la cadena de ligaduras")
        visited.add(current)
        chain.append(current)
        duration = sum_tied_durations(event_durations_quarters[item] for item in chain)
        chains.append(ReviewedTieChain(tuple(chain), duration))

    if visited != nodes:
        raise ValueError("La cadena de ligaduras contiene un ciclo sin nota inicial")
    return tuple(chains)
