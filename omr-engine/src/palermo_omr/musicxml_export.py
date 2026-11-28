"""Exporta líneas temporales revisadas a MusicXML 4.0 partwise."""
from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from fractions import Fraction
import math
import xml.etree.ElementTree as ET


_NOTE_TYPES = (
    ("whole", Fraction(4)),
    ("half", Fraction(2)),
    ("quarter", Fraction(1)),
    ("eighth", Fraction(1, 2)),
    ("16th", Fraction(1, 4)),
    ("32nd", Fraction(1, 8)),
    ("64th", Fraction(1, 16)),
    ("128th", Fraction(1, 32)),
)


def _fraction(value, label: str) -> Fraction:
    if isinstance(value, bool) or value is None:
        raise ValueError(f"{label} debe ser un número musical conocido")
    try:
        result = value if isinstance(value, Fraction) else Fraction(str(value))
    except (ValueError, TypeError, ZeroDivisionError) as exc:
        raise ValueError(f"{label} debe ser una fracción válida") from exc
    return result


def _notation(duration: Fraction) -> tuple[str, int, tuple[int, int] | None]:
    for note_type, base in _NOTE_TYPES:
        for dots in range(5):
            dotted = base * (2 - Fraction(1, 2**dots)) if dots else base
            if duration == dotted:
                return note_type, dots, None
    for note_type, base in reversed(_NOTE_TYPES):
        if duration < base:
            ratio = duration / base
            if ratio.numerator <= 16 and ratio.denominator <= 16:
                return note_type, 0, (ratio.denominator, ratio.numerator)
    raise ValueError(f"Duración no representable en MusicXML: {duration}")


def _key_signature(value):
    if value is None:
        return None
    if isinstance(value, Mapping):
        fifths, mode = value.get("fifths"), value.get("mode", "major")
    elif isinstance(value, tuple) and len(value) == 2:
        fifths, mode = value
    else:
        raise ValueError("key_signature debe ser (fifths, mode)")
    if not isinstance(fifths, int) or isinstance(fifths, bool) or not -7 <= fifths <= 7:
        raise ValueError("fifths debe estar entre -7 y 7")
    if isinstance(mode, bool) or mode not in {"major", "minor", 0, 1}:
        raise ValueError("mode debe ser major o minor")
    return fifths, "minor" if mode in {"minor", 1} else "major"


def _time_signature(value):
    if isinstance(value, Mapping):
        numerator, denominator = value.get("numerator"), value.get("denominator")
    elif isinstance(value, (tuple, list)) and len(value) == 2:
        numerator, denominator = value
    else:
        raise ValueError("Cada compás requiere time_signature")
    if (
        not isinstance(numerator, int) or isinstance(numerator, bool) or numerator <= 0
        or not isinstance(denominator, int) or isinstance(denominator, bool) or denominator <= 0
        or denominator & (denominator - 1) or denominator > 128 or numerator > 255
    ):
        raise ValueError("time_signature no es válida")
    return numerator, denominator


def _text(parent, tag: str, value) -> ET.Element:
    child = ET.SubElement(parent, tag)
    child.text = str(value)
    return child


def _pitch_fields(pitch: Mapping) -> tuple[str, int | None, int]:
    step = pitch.get("step")
    octave = pitch.get("octave")
    alter = pitch.get("alteration", pitch.get("alter", 0))
    if step not in {"A", "B", "C", "D", "E", "F", "G"}:
        raise ValueError("Cada nota necesita step musical A-G confirmado")
    if not isinstance(octave, int) or isinstance(octave, bool) or not 0 <= octave <= 9:
        raise ValueError("octave debe ser un entero entre 0 y 9")
    if not isinstance(alter, (int, float)) or isinstance(alter, bool) or alter not in (-2, -1, 0, 1, 2):
        raise ValueError("alteration debe ser -2, -1, 0, 1 o 2")
    return step, int(alter) if alter else None, octave


def _tie_types(event: Mapping) -> tuple[str, ...]:
    values = []
    for key in ("tie_start", "tie_stop"):
        if key in event and not isinstance(event[key], bool):
            raise ValueError(f"{key} debe ser booleano")
    if event.get("tie_stop"):
        values.append("stop")
    if event.get("tie_start"):
        values.append("start")
    raw = event.get("tie_types", ())
    if raw:
        if not isinstance(raw, (list, tuple)):
            raise ValueError("tie_types debe ser una lista")
        values.extend(raw)
    normalized = tuple(dict.fromkeys(values))
    if set(normalized) - {"start", "stop"}:
        raise ValueError("Tipo de ligadura MusicXML no válido")
    return normalized


def render_reviewed_timelines_musicxml(
    timelines: Sequence[Mapping],
    *,
    title: str = "Palermo Music score",
    tempo_bpm: int | float | None = None,
    key_signature=None,
    global_measure_numbers: Mapping[str, int] | None = None,
) -> bytes:
    """Genera MusicXML solo desde eventos con tiempo, duración y altura revisados.

    Cada voz se convierte en una parte independiente. Los ataques simultáneos
    de una misma voz se escriben como acordes; voces distintas conservan
    duraciones independientes. No completa alturas, figuras ni silencios.
    """
    if not isinstance(timelines, (list, tuple)) or not timelines:
        raise ValueError("Se requiere una lista no vacía de líneas temporales")
    if not isinstance(title, str) or not title.strip():
        raise ValueError("title debe ser texto no vacío")
    if tempo_bpm is not None and (
        isinstance(tempo_bpm, bool) or not isinstance(tempo_bpm, (int, float))
        or not math.isfinite(tempo_bpm) or not 20 <= tempo_bpm <= 300
    ):
        raise ValueError("tempo_bpm debe estar entre 20 y 300")
    key = _key_signature(key_signature)

    normalized = []
    voice_ids = set()
    divisions = 1
    seen_event_ids = set()
    for timeline in timelines:
        if not isinstance(timeline, Mapping):
            raise ValueError("Cada timeline debe ser un objeto")
        if timeline.get("status") != "placed_events_only":
            raise ValueError("MusicXML requiere líneas temporales completas y sin solapamientos")
        if timeline.get("unknown_onset_event_ids") or timeline.get("unknown_duration_event_ids"):
            raise ValueError("No se exportan eventos con inicios o duraciones desconocidos")
        if timeline.get("out_of_measure_event_ids") or timeline.get("overlapping_event_ids"):
            raise ValueError("No se exportan compases con desbordes o solapamientos")
        if timeline.get("underfilled_voice_ids"):
            raise ValueError("No se exportan voces con compases incompletos")
        page_number = timeline.get("page_number", 1)
        measure_index = timeline.get("measure_index")
        if not isinstance(page_number, int) or isinstance(page_number, bool) or page_number < 1:
            raise ValueError("page_number debe ser positivo")
        if not isinstance(measure_index, int) or isinstance(measure_index, bool) or measure_index < 0:
            raise ValueError("measure_index debe ser no negativo")
        meter_value = timeline.get("time_signature")
        if meter_value is None:
            meter_value = (timeline.get("numerator"), timeline.get("denominator"))
        meter = _time_signature(meter_value)
        events = timeline.get("events")
        if not isinstance(events, (list, tuple)) or not events:
            raise ValueError("Cada compás debe contener eventos")
        parsed_events = []
        for event in events:
            if not isinstance(event, Mapping):
                raise ValueError("Cada evento debe ser un objeto")
            event_id = event.get("event_id")
            voice_id = event.get("voice_id")
            if not isinstance(event_id, str) or not event_id.strip() or event_id in seen_event_ids:
                raise ValueError("event_id debe ser único y no vacío")
            if not isinstance(voice_id, str) or not voice_id.strip():
                raise ValueError("Cada evento requiere voice_id")
            seen_event_ids.add(event_id)
            voice_ids.add(voice_id)
            onset = _fraction(event.get("onset_quarters"), "onset_quarters")
            duration = _fraction(event.get("duration_quarters"), "duration_quarters")
            if onset < 0 or duration <= 0:
                raise ValueError("Inicio y duración deben ser válidos")
            divisions = math.lcm(divisions, onset.denominator, duration.denominator)
            kind = event.get("event_type", "note")
            if kind not in {"note", "rest"}:
                raise ValueError("event_type debe ser note o rest")
            pitches = event.get("confirmed_pitches", ())
            if kind == "note":
                if not isinstance(pitches, (list, tuple)) or not pitches:
                    raise ValueError("Cada nota requiere alturas confirmadas")
                normalized_pitches = [_pitch_fields(pitch) for pitch in pitches]
            else:
                if pitches:
                    raise ValueError("Un silencio no puede contener alturas")
                normalized_pitches = []
            ties = _tie_types(event)
            if kind == "rest" and ties:
                raise ValueError("Un silencio no puede contener ligaduras")
            notation = _notation(duration)
            parsed_events.append({
                "event_id": event_id, "voice_id": voice_id,
                "onset": onset, "duration": duration, "kind": kind,
                "pitches": normalized_pitches, "notation": notation,
                "ties": ties,
            })
        normalized.append({
            "page_number": page_number, "measure_index": measure_index,
            "time_signature": meter, "events": parsed_events,
        })

    if divisions > 15360:
        raise ValueError("La resolución musical requiere demasiadas divisions")
    normalized.sort(key=lambda item: (item["page_number"], item["measure_index"]))
    measure_keys = [f"{item['page_number']}:{item['measure_index']}" for item in normalized]
    if global_measure_numbers is not None:
        if set(global_measure_numbers) != set(measure_keys):
            raise ValueError("global_measure_numbers debe mapear todos los compases exactamente")
        measure_numbers = [global_measure_numbers[key] for key in measure_keys]
        if any(not isinstance(number, int) or isinstance(number, bool) or number < 1 for number in measure_numbers):
            raise ValueError("global_measure_numbers debe contener números de compás positivos")
        if len(set(measure_numbers)) != len(measure_numbers):
            raise ValueError("Los números globales de compás deben ser únicos")
    else:
        measure_numbers = list(range(1, len(normalized) + 1))

    root = ET.Element("score-partwise", {"version": "4.0"})
    work = ET.SubElement(root, "work")
    _text(work, "work-title", title)
    identification = ET.SubElement(root, "identification")
    encoding = ET.SubElement(identification, "encoding")
    _text(encoding, "software", "Palermo OMR")
    part_list = ET.SubElement(root, "part-list")
    ordered_voices = sorted(voice_ids)
    part_ids = {}
    for index, voice in enumerate(ordered_voices, start=1):
        part_id = f"P{index}"
        part_ids[voice] = part_id
        score_part = ET.SubElement(part_list, "score-part", {"id": part_id})
        _text(score_part, "part-name", voice)

    for voice in ordered_voices:
        part = ET.SubElement(root, "part", {"id": part_ids[voice]})
        for measure_index, timeline in enumerate(normalized):
            measure = ET.SubElement(part, "measure", {"number": str(measure_numbers[measure_index])})
            attributes = ET.SubElement(measure, "attributes")
            _text(attributes, "divisions", divisions)
            numerator, denominator = timeline["time_signature"]
            time = ET.SubElement(attributes, "time")
            _text(time, "beats", numerator)
            _text(time, "beat-type", denominator)
            if key is not None:
                key_element = ET.SubElement(attributes, "key")
                _text(key_element, "fifths", key[0])
                _text(key_element, "mode", key[1])
            if tempo_bpm is not None and voice == ordered_voices[0] and measure_index == 0:
                direction = ET.SubElement(measure, "direction", {"placement": "above"})
                direction_type = ET.SubElement(direction, "direction-type")
                metronome = ET.SubElement(direction_type, "metronome")
                _text(metronome, "beat-unit", "quarter")
                _text(metronome, "per-minute", tempo_bpm)
                ET.SubElement(direction, "sound", {"tempo": str(tempo_bpm)})

            voice_events = [
                event for event in timeline["events"] if event["voice_id"] == voice
            ]
            if not voice_events:
                raise ValueError("Cada voz requiere un evento o silencio explícito en cada compás")
            by_onset = defaultdict(list)
            for event in voice_events:
                by_onset[event["onset"]].append(event)
            for onset, simultaneous in sorted(by_onset.items()):
                durations = {event["duration"] for event in simultaneous}
                kinds = {event["kind"] for event in simultaneous}
                if len(durations) != 1 or len(kinds) != 1:
                    raise ValueError("Eventos simultáneos de una voz deben compartir duración y tipo")
                if len(simultaneous) > 1 and kinds != {"note"}:
                    raise ValueError("No se permiten silencios simultáneos en una misma voz")
                for event in simultaneous:
                    note_specs = event["pitches"] if event["kind"] == "note" else [None]
                    for pitch_index, pitch in enumerate(note_specs):
                        note = ET.SubElement(measure, "note")
                        if pitch_index > 0 or (pitch_index == 0 and simultaneous.index(event) > 0):
                            ET.SubElement(note, "chord")
                        if pitch is None:
                            ET.SubElement(note, "rest")
                        else:
                            step, alter, octave = pitch
                            pitch_element = ET.SubElement(note, "pitch")
                            _text(pitch_element, "step", step)
                            if alter is not None:
                                _text(pitch_element, "alter", alter)
                            _text(pitch_element, "octave", octave)
                        _text(note, "duration", int(event["duration"] * divisions))
                        for tie_type in event["ties"]:
                            ET.SubElement(note, "tie", {"type": tie_type})
                        _text(note, "voice", 1)
                        note_type, dots, tuplet = event["notation"]
                        _text(note, "type", note_type)
                        for _ in range(dots):
                            ET.SubElement(note, "dot")
                        if tuplet is not None:
                            actual, normal = tuplet
                            time_mod = ET.SubElement(note, "time-modification")
                            _text(time_mod, "actual-notes", actual)
                            _text(time_mod, "normal-notes", normal)
                        if event["ties"]:
                            notations = ET.SubElement(note, "notations")
                            for tie_type in event["ties"]:
                                ET.SubElement(notations, "tied", {"type": tie_type})
                        _text(note, "staff", 1)

    return ET.tostring(root, encoding="utf-8", xml_declaration=True)
