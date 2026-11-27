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


def apply_reviewed_tie_chains_to_page_timelines(
    timelines: list[dict],
    candidates: Sequence[TieLinkCandidate],
    confirmations: Sequence[TieReviewConfirmation],
) -> list[dict]:
    """Aplica ligaduras revisadas también entre compases contiguos de una página."""
    if not isinstance(timelines, list):
        raise ValueError("timelines debe ser una lista")
    measure_offsets: dict[int, Fraction] = {}
    cursor = Fraction(0)
    previous_index = None
    for timeline in timelines:
        index = timeline.get("measure_index")
        if not isinstance(index, int) or isinstance(index, bool):
            raise ValueError("Cada timeline debe tener measure_index")
        if previous_index is not None and index <= previous_index:
            raise ValueError("Los compases deben estar en orden estrictamente creciente")
        if previous_index is not None and index != previous_index + 1:
            raise ValueError("No se puede asumir continuidad entre compases no consecutivos")
        measure_offsets[index] = cursor
        cursor += Fraction(timeline["expected_quarters"])
        previous_index = index

    by_id: dict[str, tuple[dict, dict]] = {}
    for timeline in timelines:
        for event in timeline.get("events", []):
            event_id = event.get("event_id")
            if not isinstance(event_id, str) or not event_id or event_id in by_id:
                raise ValueError("Los IDs de evento deben ser únicos en la página")
            by_id[event_id] = (event, timeline)
    for candidate in candidates:
        if candidate.source_event_id not in by_id or candidate.target_event_id not in by_id:
            raise ValueError("Una ligadura de página referencia un evento inexistente")

    chains = build_reviewed_tie_chains(
        candidates, confirmations,
        {event_id: Fraction(event["duration_quarters"])
         for event_id, (event, _) in by_id.items()
         if event.get("duration_quarters") is not None},
    )
    consumed: set[str] = set()
    records = []
    for chain in chains:
        chain_events = [by_id[event_id] for event_id in chain.event_ids]
        for event, _ in chain_events:
            if event.get("event_type") != "note":
                raise ValueError("Una ligadura solo puede unir eventos de nota")
        for (previous, previous_timeline), (current, current_timeline) in zip(chain_events, chain_events[1:]):
            if previous.get("voice_id") != current.get("voice_id"):
                raise ValueError("Una ligadura no puede cruzar voces")
            prev_measure, curr_measure = previous_timeline["measure_index"], current_timeline["measure_index"]
            if curr_measure not in {prev_measure, prev_measure + 1}:
                raise ValueError("Una ligadura solo puede cruzar al compás consecutivo")
            if previous.get("onset_quarters") is None or previous.get("duration_quarters") is None or current.get("onset_quarters") is None:
                raise ValueError("La ligadura requiere inicios y duraciones conocidos")
            previous_global_end = measure_offsets[prev_measure] + Fraction(previous["onset_quarters"]) + Fraction(previous["duration_quarters"])
            current_global_onset = measure_offsets[curr_measure] + Fraction(current["onset_quarters"])
            if previous_global_end != current_global_onset:
                raise ValueError("Los eventos ligados no son temporalmente contiguos")
            previous_pitch, current_pitch = previous.get("confirmed_pitches"), current.get("confirmed_pitches")
            if previous_pitch is not None and current_pitch is not None and previous_pitch != current_pitch:
                raise ValueError("Las alturas revisadas de las notas ligadas no coinciden")
        first = chain_events[0][0]
        first["duration_quarters"] = str(chain.combined_duration_quarters)
        first["tied_event_ids"] = list(chain.event_ids)
        first["tie_global_end_quarters"] = str(
            measure_offsets[chain_events[-1][1]["measure_index"]]
            + Fraction(chain_events[-1][0]["onset_quarters"])
            + Fraction(chain_events[-1][0]["duration_quarters"])
        )
        consumed.update(chain.event_ids[1:])
        records.append(chain.to_dict())

    for timeline in timelines:
        timeline["events"] = [event for event in timeline.get("events", []) if event["event_id"] not in consumed]
        grouped: dict[str, list[str]] = {}
        for event in timeline["events"]:
            if event.get("onset_quarters") is not None:
                grouped.setdefault(str(event["onset_quarters"]), []).append(event["event_id"])
        timeline["onset_groups"] = [
            {"onset_quarters": onset, "event_ids": sorted(ids)}
            for onset, ids in sorted(grouped.items(), key=lambda item: Fraction(item[0]))
        ]
    if records:
        timelines[0]["reviewed_tie_chains_across_measures"] = records
        timelines[0]["tie_review_status"] = "human_confirmed_ties_applied_across_measures"
    return timelines


def apply_reviewed_tie_chains_across_pages(
    pages: Sequence[tuple[int, list[dict]]],
    candidates: Sequence[TieLinkCandidate],
    confirmations: Sequence[TieReviewConfirmation],
) -> Sequence[tuple[int, list[dict]]]:
    """Aplica ligaduras humanas que cruzan páginas consecutivas.

    Requiere que se entreguen todas las páginas implicadas, con sus compases
    revisados completos, empezando en el índice 0 y sin saltos. Una ligadura
    solo puede salir del último compás de una página y entrar al primero de la
    página siguiente. Así no se inventa continuidad a través de páginas o
    compases omitidos.
    """
    if not isinstance(pages, Sequence) or isinstance(pages, (str, bytes)) or not pages:
        raise ValueError("pages debe contener páginas revisadas")
    normalized_pages: list[tuple[int, list[dict]]] = []
    page_offsets: dict[int, Fraction] = {}
    event_locations: dict[str, tuple[dict, dict, int, Fraction]] = {}
    cursor = Fraction(0)
    previous_page_number = None

    for page_number, timelines in pages:
        if not isinstance(page_number, int) or isinstance(page_number, bool) or page_number < 1:
            raise ValueError("El número de página debe ser un entero positivo")
        if previous_page_number is not None and page_number != previous_page_number + 1:
            raise ValueError("Las páginas deben ser consecutivas y estar completas")
        if not isinstance(timelines, list) or not timelines:
            raise ValueError("Cada página debe contener compases revisados")
        indices = [item.get("measure_index") for item in timelines]
        if indices != list(range(len(indices))):
            raise ValueError("Cada página debe incluir todos sus compases revisados desde el índice 0")
        page_offsets[page_number] = cursor
        local_offsets: dict[int, Fraction] = {}
        local_cursor = Fraction(0)
        for timeline in timelines:
            index = timeline["measure_index"]
            local_offsets[index] = local_cursor
            local_cursor += Fraction(timeline["expected_quarters"])
            for event in timeline.get("events", []):
                event_id = event.get("event_id")
                if not isinstance(event_id, str) or not event_id or event_id in event_locations:
                    raise ValueError("Los IDs de evento deben ser únicos entre todas las páginas")
                event_locations[event_id] = (event, timeline, page_number, local_offsets[index])
        cursor += local_cursor
        normalized_pages.append((page_number, timelines))
        previous_page_number = page_number

    for candidate in candidates:
        if candidate.source_event_id not in event_locations or candidate.target_event_id not in event_locations:
            raise ValueError("Una ligadura entre páginas referencia un evento inexistente")

    chains = build_reviewed_tie_chains(
        candidates,
        confirmations,
        {
            event_id: Fraction(event["duration_quarters"])
            for event_id, (event, _, _, _) in event_locations.items()
            if event.get("duration_quarters") is not None
        },
    )
    if not chains:
        return normalized_pages

    consumed_targets: set[str] = set()
    records_by_page: dict[int, list[dict]] = {}
    for chain in chains:
        chain_locations = [event_locations[event_id] for event_id in chain.event_ids]
        chain_events = [item[0] for item in chain_locations]
        if not any(
            left[2] != right[2]
            for left, right in zip(chain_locations, chain_locations[1:])
        ):
            raise ValueError("Esta operación solo acepta cadenas que cruzan páginas")
        for event in chain_events:
            if event.get("event_type") != "note":
                raise ValueError("Una ligadura solo puede unir eventos de nota")
        for left, right in zip(chain_locations, chain_locations[1:]):
            previous, previous_timeline, previous_page, previous_measure_offset = left
            current, current_timeline, current_page, current_measure_offset = right
            if previous.get("voice_id") != current.get("voice_id"):
                raise ValueError("Una ligadura no puede cruzar voces")
            if current_page not in {previous_page, previous_page + 1}:
                raise ValueError("Una ligadura solo puede cruzar a la página consecutiva")
            if previous.get("onset_quarters") is None or previous.get("duration_quarters") is None or current.get("onset_quarters") is None:
                raise ValueError("La ligadura requiere inicios y duraciones conocidos")
            if current_page != previous_page:
                previous_page_timelines = next(items for number, items in normalized_pages if number == previous_page)
                current_page_timelines = next(items for number, items in normalized_pages if number == current_page)
                if previous_timeline is not previous_page_timelines[-1]:
                    raise ValueError("La nota de salida debe estar en el último compás de la página")
                if current_timeline is not current_page_timelines[0]:
                    raise ValueError("La nota de entrada debe estar en el primer compás de la página")
            previous_global_end = (
                page_offsets[previous_page] + previous_measure_offset
                + Fraction(previous["onset_quarters"]) + Fraction(previous["duration_quarters"])
            )
            current_global_onset = (
                page_offsets[current_page] + current_measure_offset
                + Fraction(current["onset_quarters"])
            )
            if previous_global_end != current_global_onset:
                raise ValueError("Los eventos ligados no son temporalmente contiguos entre páginas")
            previous_pitch = previous.get("confirmed_pitches")
            current_pitch = current.get("confirmed_pitches")
            if previous_pitch is not None and current_pitch is not None and previous_pitch != current_pitch:
                raise ValueError("Las alturas revisadas de las notas ligadas no coinciden")

        first = chain_locations[0][0]
        last, last_timeline, last_page, last_measure_offset = chain_locations[-1]
        first["duration_quarters"] = str(chain.combined_duration_quarters)
        first["tied_event_ids"] = list(chain.event_ids)
        first["tie_global_end_quarters"] = str(
            page_offsets[last_page] + last_measure_offset
            + Fraction(last["onset_quarters"]) + Fraction(last["duration_quarters"])
        )
        consumed_targets.update(chain.event_ids[1:])
        records_by_page.setdefault(chain_locations[0][2], []).append(chain.to_dict())

    for page_number, timelines in normalized_pages:
        for timeline in timelines:
            timeline["events"] = [
                event for event in timeline.get("events", [])
                if event["event_id"] not in consumed_targets
            ]
            grouped: dict[str, list[str]] = {}
            for event in timeline["events"]:
                if event.get("onset_quarters") is not None:
                    grouped.setdefault(str(event["onset_quarters"]), []).append(event["event_id"])
            timeline["onset_groups"] = [
                {"onset_quarters": onset, "event_ids": sorted(ids)}
                for onset, ids in sorted(grouped.items(), key=lambda item: Fraction(item[0]))
            ]
        if page_number in records_by_page:
            timelines[0]["reviewed_tie_chains_across_pages"] = records_by_page[page_number]
            timelines[0]["tie_review_status"] = "human_confirmed_ties_applied_across_pages"
    return normalized_pages
