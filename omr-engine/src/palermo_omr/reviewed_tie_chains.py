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


def apply_reviewed_tie_chains_to_timeline(
    timeline_data: dict,
    candidates: Sequence[TieLinkCandidate],
    confirmations: Sequence[TieReviewConfirmation],
) -> dict:
    """Aplica ligaduras confirmadas: un ataque, duración acumulada y trazabilidad.

    Solo procesa enlaces dentro del mismo compás. Los enlaces entre compases
    requieren una línea temporal global revisada y no se adivinan aquí.
    """
    if not isinstance(timeline_data, dict):
        raise ValueError("timeline_data debe ser un objeto")
    events = timeline_data.get("events")
    if not isinstance(events, list):
        raise ValueError("El timeline debe contener una lista de eventos")
    by_id = {event.get("event_id"): event for event in events}
    if len(by_id) != len(events) or None in by_id:
        raise ValueError("Los eventos del timeline deben tener IDs únicos")

    for candidate in candidates:
        if candidate.source_event_id not in by_id or candidate.target_event_id not in by_id:
            raise ValueError(
                "Los dos eventos de una ligadura deben pertenecer al mismo compás revisado"
            )

    chains = build_reviewed_tie_chains(
        candidates,
        confirmations,
        {
            event["event_id"]: Fraction(event["duration_quarters"])
            for event in events
            if event.get("duration_quarters") is not None
        },
    )
    if not chains:
        return timeline_data

    consumed_targets: set[str] = set()
    chain_records = []
    for chain in chains:
        chain_events = [by_id[event_id] for event_id in chain.event_ids]
        for event in chain_events:
            if event.get("event_type") != "note":
                raise ValueError("Una ligadura solo puede unir eventos de nota")
        for previous, current in zip(chain_events, chain_events[1:]):
            if previous.get("voice_id") != current.get("voice_id"):
                raise ValueError("Una ligadura no puede cruzar voces")
            if previous.get("measure_index") != current.get("measure_index"):
                raise ValueError("Una ligadura no puede cruzar compases")
            if previous.get("onset_quarters") is None or previous.get("duration_quarters") is None:
                raise ValueError("La ligadura requiere inicio y duración conocidos")
            expected_onset = Fraction(previous["onset_quarters"]) + Fraction(previous["duration_quarters"])
            if expected_onset != Fraction(current["onset_quarters"]):
                raise ValueError("Los eventos ligados no son temporalmente contiguos")
            previous_pitch = previous.get("confirmed_pitches")
            current_pitch = current.get("confirmed_pitches")
            if previous_pitch is not None and current_pitch is not None and previous_pitch != current_pitch:
                raise ValueError("Las alturas revisadas de las notas ligadas no coinciden")
        first = chain_events[0]
        first["duration_quarters"] = str(chain.combined_duration_quarters)
        first["tied_event_ids"] = list(chain.event_ids)
        consumed_targets.update(chain.event_ids[1:])
        chain_records.append(chain.to_dict())

    retained = [event for event in events if event["event_id"] not in consumed_targets]
    timeline_data["events"] = retained
    onset_groups: dict[str, list[str]] = {}
    for event in retained:
        onset = event.get("onset_quarters")
        if onset is not None:
            onset_groups.setdefault(str(onset), []).append(event["event_id"])
    timeline_data["onset_groups"] = [
        {"onset_quarters": onset, "event_ids": sorted(ids)}
        for onset, ids in sorted(onset_groups.items(), key=lambda item: Fraction(item[0]))
    ]
    timeline_data["reviewed_tie_chains"] = chain_records
    timeline_data["tie_review_status"] = "human_confirmed_ties_applied"
    return timeline_data
