"""Construcción de líneas temporales candidatas desde eventos fusionados.

A diferencia del adaptador de revisión, esta ruta no exige ni simula aprobación
humana. Solo ordena eventos con asignación de voz y orden explícitos; conserva
los eventos incompletos fuera de la línea temporal y los enumera en el informe.
"""
from __future__ import annotations

from collections import defaultdict
from fractions import Fraction
from typing import Any, Mapping, Sequence

from .event_fusion import ScoreEventCandidate
from .rhythmic_timeline import analyze_ordered_measure_voices
from .voice_sequence_timing import OrderedVoiceEvent


def build_candidate_measure_timelines(
    events: Sequence[ScoreEventCandidate],
    measure_specs: Mapping[int, tuple[int, int]],
    event_order_indices: Mapping[str, int],
    event_measure_indices: Mapping[str, int],
) -> list[dict[str, Any]]:
    """Genera una línea temporal por compás desde candidatos fusionados.

    measure_specs asigna compás -> (numerador, denominador).
    event_order_indices debe proporcionar el orden musical explícito de cada
    evento incluido. No se infiere tiempo desde coordenadas ni se confirma
    ningún evento. Un evento sin voz, duración o compás queda en unresolved.
    """
    if not isinstance(measure_specs, Mapping) or not measure_specs:
        raise ValueError("measure_specs debe contener al menos un compás")
    normalized_specs: dict[int, tuple[int, int]] = {}
    for index, signature in measure_specs.items():
        if not isinstance(index, int) or isinstance(index, bool) or index < 0:
            raise ValueError("Los índices de compás deben ser enteros no negativos")
        if not isinstance(signature, tuple) or len(signature) != 2:
            raise ValueError("Cada métrica debe ser una tupla (numerador, denominador)")
        numerator, denominator = signature
        if any(not isinstance(value, int) or isinstance(value, bool) or value <= 0 for value in signature):
            raise ValueError("Numerador y denominador deben ser enteros positivos")
        normalized_specs[index] = (numerator, denominator)

    by_id: dict[str, ScoreEventCandidate] = {}
    for event in events:
        if not isinstance(event, ScoreEventCandidate):
            raise ValueError("Todos los eventos deben ser ScoreEventCandidate")
        if not event.event_id or event.event_id in by_id:
            raise ValueError("Los event_id deben ser únicos y no vacíos")
        by_id[event.event_id] = event
    if set(event_order_indices) - set(by_id):
        raise ValueError("El orden referencia eventos inexistentes")
    if set(event_measure_indices) - set(by_id):
        raise ValueError("El compás referencia eventos inexistentes")
    for event_id, measure_index in event_measure_indices.items():
        if not isinstance(measure_index, int) or isinstance(measure_index, bool) or measure_index < 0:
            raise ValueError(f"{event_id}: el índice de compás debe ser entero no negativo")
    for event_id, order_index in event_order_indices.items():
        if not isinstance(order_index, int) or isinstance(order_index, bool) or order_index < 0:
            raise ValueError(f"{event_id}: el orden debe ser entero no negativo")

    used_orders: set[tuple[int, str, int]] = set()
    by_measure_voice: dict[int, dict[str, list[OrderedVoiceEvent]]] = defaultdict(lambda: defaultdict(list))
    unresolved: dict[int, list[dict[str, str]]] = defaultdict(list)

    for event in events:
        # La asignación de compás debe ser explícita; no se deduce del pentagrama.
        measure_index = event_measure_indices.get(event.event_id)
        if measure_index is None or measure_index not in normalized_specs:
            unresolved[-1].append({"event_id": event.event_id, "reason": "missing_or_unknown_measure"})
            continue
        voice_id = event.voice_id_candidate
        order_index = event_order_indices.get(event.event_id)
        if not isinstance(voice_id, str) or not voice_id.strip():
            unresolved[measure_index].append({"event_id": event.event_id, "reason": "missing_voice"})
            continue
        if not isinstance(order_index, int) or isinstance(order_index, bool) or order_index < 0:
            unresolved[measure_index].append({"event_id": event.event_id, "reason": "missing_order"})
            continue
        key = (measure_index, voice_id, order_index)
        if key in used_orders:
            raise ValueError("El orden musical debe ser único dentro de cada voz y compás")
        used_orders.add(key)
        duration = event.duration_quarters_candidate
        if duration is not None:
            duration = duration if isinstance(duration, Fraction) else Fraction(str(duration))
            if duration <= 0:
                raise ValueError("Las duraciones candidatas deben ser positivas")
        by_measure_voice[measure_index][voice_id].append(OrderedVoiceEvent(
            event_id=event.event_id,
            voice_id=voice_id,
            measure_index=measure_index,
            order_index=order_index,
            duration_quarters=duration,
            event_type=event.event_type,
            notehead_ids=event.notehead_candidate_ids,
        ))
        if event.status != "ready_for_review":
            unresolved[measure_index].append({"event_id": event.event_id, "reason": "incomplete_candidate"})

    results = []
    for measure_index, (numerator, denominator) in sorted(normalized_specs.items()):
        sequences = [
            (voice_id, measure_index, voice_events)
            for voice_id, voice_events in sorted(by_measure_voice[measure_index].items())
        ]
        analysis = analyze_ordered_measure_voices(
            sequences, numerator, denominator, measure_index=measure_index
        )
        results.append({
            **analysis.to_dict(),
            "candidate_status": "unconfirmed_timeline",
            "unresolved_candidates": sorted(
                unresolved.get(measure_index, []), key=lambda item: item["event_id"]
            ),
            "warning": (
                "Línea temporal provisional. El orden, voz, compás y duración "
                "deben proceder de entradas explícitas; no representa aprobación musical."
            ),
        })
    if -1 in unresolved:
        results.append({
            "measure_index": None,
            "candidate_status": "unplaced_candidates",
            "unresolved_candidates": sorted(unresolved[-1], key=lambda item: item["event_id"]),
        })
    return results
