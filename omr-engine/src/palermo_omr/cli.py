"""Interfaz de línea de comandos del prototipo Palermo OMR."""

from __future__ import annotations

import argparse
from dataclasses import replace
import json
from pathlib import Path

import cv2

from . import __version__
from .imaging import analyze_page, render_pdf
from .pdf_clef_glyphs import detect_embedded_pdf_clef_candidates
from .symbols import (
    detect_hollow_notehead_candidates,
    detect_notehead_candidates,
    filter_notehead_candidates_by_confidence,
)
from .notation_preamble import (
    detect_notation_preamble_candidates,
    export_notation_preamble_crops,
)
from .pitch_candidates import build_pitch_candidates
from .key_signature_candidates import (
    build_key_signature_candidates,
    apply_accepted_key_signature_candidates,
)
from .glyph_labeling import build_staff_clef_map, validate_glyph_manifest
from .visualization import draw_geometry_overlay, draw_notehead_overlay, draw_rhythm_overlay
from .rhythm import analyze_rhythm_candidates
from .beam_groups import detect_beam_group_candidates
from .rhythm_interpretation import interpret_rhythm_from_beam_groups
from .rhythmic_event_groups import build_rhythmic_event_group_candidates
from .reviewed_timeline import build_reviewed_page_timelines
from .reviewed_tie_chains import apply_reviewed_tie_chains_across_pages
from .tie_candidates import TieLinkCandidate, TieReviewConfirmation
from .staff_voice_layers import detect_staff_voice_layer_candidates
from .rhythm_symbols import (detect_augmentation_dot_candidates, detect_rest_shape_candidates, detect_tie_slur_shape_candidates)
from .staff_grouping import detect_staff_grouping_mark_candidates
from .printed_labels import extract_printed_label_candidates
from .section_structure import (
    anchor_section_markers_to_measure_spans,
    detect_section_candidates,
    link_section_ranges_across_pages,
    build_global_measure_sequence,
    resolve_section_range_boundaries,
)
from .identity_evidence import build_page_identity_evidence
from .score_structure import ScoreStaff, ScoreStructure
from .measure_layout import (
    classify_barline_groups,
    detect_barline_candidates,
    detect_staff_systems,
    detect_staff_systems_from_connectors,
    group_system_barlines,
    infer_measure_spans,
    merge_staff_systems_from_grouping_marks,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="palermo-omr",
        description="Analiza geometría y candidatos musicales preliminares en un PDF.",
    )
    parser.add_argument("pdf", help="Ruta al archivo PDF")
    parser.add_argument("--output", default="omr-output", help="Carpeta de salida")
    parser.add_argument("--dpi", type=int, default=300, help="Resolución de renderizado (72-600)")
    parser.add_argument("--min-notehead-confidence", type=float, default=0.0, help="Filtro opcional de confianza para cabezas rellenas (0-1); 0 conserva todos los candidatos")
    parser.add_argument("--embedded-pdf-clef-glyphs", action="store_true", help="Extrae candidatos de clave desde glifos de fuente embebidos en PDFs Sibelius/Reprise; quedan pendientes de revisión")
    parser.add_argument(
        "--staff-clefs", default="{}",
        help="JSON opcional: claves por índice de pentagrama, p. ej. '{\"0\":\"treble\",\"1\":\"bass\"}'. No se detectan visualmente.",
    )
    parser.add_argument(
        "--glyph-manifest", default=None,
        help="Manifiesto de glifos con etiquetas humanas confirmadas; aporta claves por página/pentagrama.",
    )
    parser.add_argument(
        "--key-signatures", default="{}",
        help="JSON opcional: armaduras por índice de pentagrama, p. ej. '{\"0\":{\"F\":1,\"C\":1}}'",
    )
    parser.add_argument(
        "--accept-key-signature-candidates", action="store_true",
        help="Acepta explícitamente candidatos de armadura válidos derivados de etiquetas humanas confirmadas.",
    )
    parser.add_argument(
        "--pitch-review-manifest", default=None,
        help="JSON de asignaciones humanas de compás, acorde y alteraciones.",
    )
    parser.add_argument(
        "--reviewed-rhythm-manifest", default=None,
        help="JSON de eventos rítmicos confirmados por persona; genera líneas temporales polifónicas por compás.",
    )
    args = parser.parse_args()

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    pages = render_pdf(args.pdf, dpi=args.dpi)
    analyses = []
    rhythmic_groups_by_page = {}
    rest_candidates_by_page = {}
    pitch_candidates_by_page = {}
    human_glyph_manifest = (
        validate_glyph_manifest(args.glyph_manifest) if args.glyph_manifest else None
    )
    pitch_review_pages = {}
    if args.pitch_review_manifest:
        review_data = json.loads(Path(args.pitch_review_manifest).read_text(encoding="utf-8"))
        if not isinstance(review_data, dict) or review_data.get("schema_version") != "1" or not isinstance(review_data.get("pages"), list):
            raise ValueError("El manifiesto de alturas requiere schema_version 1 y pages")
        for item in review_data["pages"]:
            if not isinstance(item, dict) or item.get("reviewer_confirmed") is not True:
                raise ValueError("Cada página del manifiesto debe estar confirmada por una persona")
            number = item.get("page_number")
            if not isinstance(number, int) or isinstance(number, bool) or number < 1 or number in pitch_review_pages or not isinstance(item.get("heads"), list):
                raise ValueError("page_number inválido/duplicado o heads ausente")
            pitch_review_pages[number] = item["heads"]

    for page_number, page in enumerate(pages, start=1):
        binary, analysis = analyze_page(page, page_number)
        image_path = output_dir / f"page-{page_number:03d}-binary.png"
        if not cv2.imwrite(str(image_path), binary):
            raise OSError(f"No se pudo escribir {image_path}")

        page_data = analysis.to_dict()
        page_data["render_dpi"] = args.dpi
        embedded_clef_candidates = (
            detect_embedded_pdf_clef_candidates(
                args.pdf, page_number, analysis.staves, dpi=args.dpi
            )
            if args.embedded_pdf_clef_glyphs else ()
        )
        page_data["embedded_clef_candidates"] = [
            item.to_dict() for item in embedded_clef_candidates
        ]
        page_data["embedded_clef_candidate_count"] = len(embedded_clef_candidates)
        raw_noteheads = detect_notehead_candidates(binary, analysis.staves)
        noteheads = filter_notehead_candidates_by_confidence(
            raw_noteheads, args.min_notehead_confidence
        )
        filtered_out_noteheads = [
            item for item in raw_noteheads
            if item.confidence < args.min_notehead_confidence
        ]
        hollow_noteheads = detect_hollow_notehead_candidates(binary, analysis.staves)
        overlay = draw_notehead_overlay(page, noteheads)
        hollow_overlay = draw_notehead_overlay(page, hollow_noteheads)
        hollow_overlay_path = output_dir / f"page-{page_number:03d}-hollow-noteheads-overlay.png"
        if not cv2.imwrite(str(hollow_overlay_path), hollow_overlay):
            raise OSError(f"No se pudo escribir {hollow_overlay_path}")
        overlay_path = output_dir / f"page-{page_number:03d}-noteheads-overlay.png"
        if not cv2.imwrite(str(overlay_path), overlay):
            raise OSError(f"No se pudo escribir {overlay_path}")
        page_data["notehead_confidence_filter"] = args.min_notehead_confidence
        page_data["notehead_candidate_count_before_filter"] = len(raw_noteheads)
        page_data["notehead_candidates_filtered_out"] = [
            item.to_dict() for item in filtered_out_noteheads
        ]
        page_data["notehead_candidates_filtered_out_count"] = len(filtered_out_noteheads)
        page_data["notehead_candidates"] = [item.to_dict() for item in noteheads]
        page_data["notehead_candidate_count"] = len(noteheads)
        page_data["hollow_notehead_candidates"] = [item.to_dict() for item in hollow_noteheads]
        page_data["hollow_notehead_candidate_count"] = len(hollow_noteheads)
        supplied_clefs = json.loads(args.staff_clefs)
        if not isinstance(supplied_clefs, dict):
            raise ValueError("--staff-clefs debe ser un objeto JSON")
        human_clefs = (
            build_staff_clef_map(human_glyph_manifest, page_number=page_number)
            if human_glyph_manifest is not None else {}
        )
        for staff_index, clef in human_clefs.items():
            if str(staff_index) in supplied_clefs and supplied_clefs[str(staff_index)] != clef:
                raise ValueError(
                    f"Conflicto entre --staff-clefs y etiqueta humana en pentagrama {staff_index}"
                )
            supplied_clefs[str(staff_index)] = clef
        # Las armaduras visuales se proponen solo desde etiquetas humanas
        # confirmadas. Siguen siendo candidatas y no alteran las alturas hasta
        # que el operador las acepte y las suministre en --key-signatures.
        key_signature_candidates = []
        if human_glyph_manifest is not None:
            confirmed_clefs = {int(index): clef for index, clef in supplied_clefs.items()}
            staff_lines = {
                index: list(staff.lines_y)
                for index, staff in enumerate(analysis.staves)
            }
            key_signature_candidates = build_key_signature_candidates(
                human_glyph_manifest,
                page_number=page_number,
                staff_clefs=confirmed_clefs,
                staff_lines=staff_lines,
            )
        page_data["key_signature_candidates"] = [
            item.to_dict() for item in key_signature_candidates
        ]
        page_data["key_signature_candidate_count"] = len(key_signature_candidates)

        page_key_signatures = json.loads(args.key_signatures)
        if not isinstance(page_key_signatures, dict):
            raise ValueError("--key-signatures debe ser un objeto JSON")
        if args.accept_key_signature_candidates:
            page_key_signatures = apply_accepted_key_signature_candidates(
                page_key_signatures, key_signature_candidates
            )

        combined_heads = noteheads + hollow_noteheads
        source_kinds = ["filled"] * len(noteheads) + ["hollow"] * len(hollow_noteheads)
        review_heads = pitch_review_pages.get(page_number)
        pitch_kwargs = {}
        if review_heads is not None:
            if len(review_heads) != len(combined_heads):
                raise ValueError("El manifiesto debe asignar todas las cabezas en el orden de candidatos del análisis")
            measure_ids, accidentals, groups, event_orders = [], [], [], []
            for index, item in enumerate(review_heads):
                if not isinstance(item, dict):
                    raise ValueError("Cada asignación de altura debe ser un objeto")
                expected_kind = source_kinds[index]
                expected_local_index = index if expected_kind == "filled" else index - len(noteheads)
                if item.get("source_kind") != expected_kind or item.get("source_index") != expected_local_index:
                    raise ValueError("source_kind/source_index no coincide con el orden de candidatos geométricos")
                measure_id = item.get("measure_id")
                if not isinstance(measure_id, (str, int)) or isinstance(measure_id, bool) or (isinstance(measure_id, str) and not measure_id.strip()):
                    raise ValueError("Cada cabeza revisada requiere measure_id")
                event_order = item.get("event_order")
                if not isinstance(event_order, int) or isinstance(event_order, bool) or event_order < 0:
                    raise ValueError("Cada cabeza revisada requiere event_order entero no negativo")
                accidental = item.get("explicit_accidental")
                if accidental not in (None, "natural", "sharp", "flat", "double_sharp", "double_flat"):
                    raise ValueError("explicit_accidental no válido")
                group = item.get("simultaneous_group_id")
                if group is not None and (not isinstance(group, (str, int)) or isinstance(group, bool)):
                    raise ValueError("simultaneous_group_id no válido")
                measure_ids.append(measure_id)
                accidentals.append(accidental)
                groups.append(group if group is not None else f"single-{index}")
                event_orders.append(event_order)
            attacks = {}
            for index, event_order in enumerate(event_orders):
                attack = (int(combined_heads[index].staff_index), measure_ids[index], event_order)
                attacks.setdefault(attack, []).append(index)
            for attack, indices in attacks.items():
                if len(indices) > 1 and len({groups[index] for index in indices}) != 1:
                    raise ValueError(f"Las cabezas de un mismo ataque {attack!r} deben compartir simultaneous_group_id")
            pitch_kwargs = {
                "measure_ids": measure_ids,
                "explicit_accidentals": accidentals,
                "simultaneous_group_ids": groups,
            }
        if review_heads is not None:
            ordered_indices = sorted(
                range(len(combined_heads)),
                key=lambda index: (
                    int(combined_heads[index].staff_index),
                    str(pitch_kwargs["measure_ids"][index]),
                    event_orders[index],
                    float(getattr(combined_heads[index], "center_x", index)),
                    index,
                ),
            )
            ordered_kwargs = {
                "measure_ids": [pitch_kwargs["measure_ids"][index] for index in ordered_indices],
                "explicit_accidentals": [pitch_kwargs["explicit_accidentals"][index] for index in ordered_indices],
                "simultaneous_group_ids": [pitch_kwargs["simultaneous_group_ids"][index] for index in ordered_indices],
                "source_indices": ordered_indices,
            }
            ordered_candidates = build_pitch_candidates(
                [combined_heads[index] for index in ordered_indices],
                staff_clefs=supplied_clefs,
                key_signatures=page_key_signatures,
                source_kinds=[source_kinds[index] for index in ordered_indices],
                **ordered_kwargs,
            )
            pitch_candidates = [None] * len(combined_heads)
            for candidate in ordered_candidates:
                pitch_candidates[candidate.source_index] = candidate
        else:
            pitch_candidates = build_pitch_candidates(
                combined_heads,
                staff_clefs=supplied_clefs,
                key_signatures=page_key_signatures,
                source_kinds=source_kinds,
            )
        pitch_candidates_by_page[page_number] = pitch_candidates
        page_data["pitch_candidates"] = [item.to_dict() for item in pitch_candidates]
        page_data["pitch_candidate_count"] = len(pitch_candidates)
        page_data["resolved_pitch_candidate_count"] = sum(
            item.status == "resolved_from_supplied_clef" for item in pitch_candidates
        )
        page_data["unresolved_pitch_candidate_count"] = (
            len(pitch_candidates) - page_data["resolved_pitch_candidate_count"]
        )
        preamble_candidates = detect_notation_preamble_candidates(
            binary, analysis.staves, noteheads + hollow_noteheads
        )
        page_data["notation_preamble_candidates"] = [
            item.to_dict() for item in preamble_candidates
        ]
        page_data["notation_preamble_candidate_count"] = len(preamble_candidates)
        preamble_crops = export_notation_preamble_crops(
            binary, preamble_candidates, analysis.staves,
            output_dir / "notation-preamble-crops", page_number=page_number,
        )
        page_data["notation_preamble_crop_exports"] = preamble_crops
        page_data["notation_preamble_crop_export_count"] = len(preamble_crops)
        page_data["hollow_notehead_overlay"] = hollow_overlay_path.name
        page_data["notehead_overlay"] = overlay_path.name
        rhythms = analyze_rhythm_candidates(binary, analysis.staves, noteheads)
        rhythm_overlay = draw_rhythm_overlay(page, noteheads, rhythms)
        rhythm_overlay_path = output_dir / f"page-{page_number:03d}-rhythm-overlay.png"
        if not cv2.imwrite(str(rhythm_overlay_path), rhythm_overlay):
            raise OSError(f"No se pudo escribir {rhythm_overlay_path}")
        page_data["rhythm_overlay"] = rhythm_overlay_path.name
        # Las cabezas huecas se analizan aparte: la presencia de plica propone
        # blanca; su ausencia propone redonda. No se mezclan con cabezas rellenas.
        hollow_rhythms = analyze_rhythm_candidates(
            binary, analysis.staves, hollow_noteheads
        )
        beam_groups = detect_beam_group_candidates(binary, analysis.staves, noteheads, rhythms)
        rhythmic_interpretations = interpret_rhythm_from_beam_groups(rhythms, beam_groups)
        # Las cabezas huecas (blancas/redondas) aportan eventos candidatos
        # independientes. No se les aplican haces de las cabezas rellenas.
        hollow_rhythmic_interpretations = interpret_rhythm_from_beam_groups(
            hollow_rhythms, []
        )
        hollow_rhythmic_interpretations = [
            replace(item, notehead_index=item.notehead_index + len(noteheads))
            for item in hollow_rhythmic_interpretations
        ]
        all_rhythm_heads = noteheads + hollow_noteheads
        all_rhythm_candidates = rhythms + hollow_rhythms
        all_rhythm_interpretations = (
            rhythmic_interpretations + hollow_rhythmic_interpretations
        )
        # Integrar cabezas rellenas y huecas en posibles ataques/acordes.
        # La etapa conserva incertidumbre: no convierte x en tiempo ni
        # asigna voces por dirección de plica.
        rhythmic_event_groups = build_rhythmic_event_group_candidates(
            analysis.staves, all_rhythm_heads, all_rhythm_candidates,
            all_rhythm_interpretations,
        )
        rhythmic_groups_by_page[page_number] = rhythmic_event_groups
        voice_layer_candidates = detect_staff_voice_layer_candidates(
            analysis.staves, noteheads, rhythms
        )
        page_data["rhythm_candidates"] = [item.to_dict() for item in rhythms]
        page_data["rhythm_candidate_count"] = len(rhythms)
        page_data["hollow_rhythm_candidates"] = [item.to_dict() for item in hollow_rhythms]
        page_data["hollow_rhythm_candidate_count"] = len(hollow_rhythms)
        page_data["beam_group_candidates"] = [item.to_dict() for item in beam_groups]
        page_data["beam_group_candidate_count"] = len(beam_groups)
        page_data["rhythmic_interpretation_candidates"] = [item.to_dict() for item in rhythmic_interpretations]
        page_data["rhythmic_interpretation_candidate_count"] = len(rhythmic_interpretations)
        page_data["hollow_rhythmic_interpretation_candidates"] = [item.to_dict() for item in hollow_rhythmic_interpretations]
        page_data["hollow_rhythmic_interpretation_candidate_count"] = len(hollow_rhythmic_interpretations)
        page_data["rhythmic_event_group_candidates"] = [
            item.to_dict() for item in rhythmic_event_groups
        ]
        page_data["rhythmic_event_group_candidate_count"] = len(rhythmic_event_groups)
        page_data["staff_voice_layer_candidates"] = [
            item.to_dict() for item in voice_layer_candidates
        ]
        page_data["staff_voice_layer_candidate_count"] = len(voice_layer_candidates)
        dots = detect_augmentation_dot_candidates(binary, analysis.staves, noteheads)
        rests = detect_rest_shape_candidates(
            binary, analysis.staves, noteheads + hollow_noteheads
        )
        rest_candidates_by_page[page_number] = rests
        tie_slurs = detect_tie_slur_shape_candidates(binary, analysis.staves)
        barlines = detect_barline_candidates(binary, analysis.staves)
        barline_groups = classify_barline_groups(barlines, analysis.staves)
        initial_systems = detect_staff_systems_from_connectors(analysis.staves, binary)
        grouping_marks = detect_staff_grouping_mark_candidates(
            binary, analysis.staves, system_candidates=initial_systems
        )
        staff_systems = merge_staff_systems_from_grouping_marks(
            analysis.staves, initial_systems, grouping_marks
        )
        grouping_marks = detect_staff_grouping_mark_candidates(
            binary, analysis.staves, system_candidates=staff_systems
        )
        system_barlines = group_system_barlines(
            barlines, analysis.staves, system_candidates=staff_systems
        )
        measure_spans = infer_measure_spans(barlines)
        section_data = detect_section_candidates(
            args.pdf, page_number, analysis.staves, measure_spans, dpi=args.dpi
        )
        section_data["section_measure_anchor_candidates"] = anchor_section_markers_to_measure_spans(
            [item.to_dict() for item in section_data["section_marker_candidates"]],
            analysis.staves,
            measure_spans,
            staff_system_candidates=staff_systems,
        )
        section_identifiers = section_data["section_identifier_candidates"]
        section_identifier_boxes = {
            tuple(item.bbox_pdf) for item in section_identifiers
        }
        printed_labels = extract_printed_label_candidates(
            args.pdf, page_number, analysis.staves, dpi=args.dpi
        )
        # Una letra ya vinculada a una marca de sección no debe duplicarse
        # como abreviatura SATB en la misma página.
        printed_labels = [
            item for item in printed_labels
            if tuple(item.bbox_pdf) not in section_identifier_boxes
        ]
        score_structure = ScoreStructure(
            page_number=page_number,
            staves=tuple(
                ScoreStaff(
                    staff_id=f"p{page_number}-staff-{index + 1}",
                    page_number=page_number,
                    detected_staff_index=index,
                )
                for index, _ in enumerate(analysis.staves)
            ),
        )
        identity_evidence = build_page_identity_evidence(
            score_structure,
            printed_labels=printed_labels,
            grouping_marks=grouping_marks,
        )
        page_data["augmentation_dot_candidates"] = [item.to_dict() for item in dots]
        page_data["rest_shape_candidates"] = [item.to_dict() for item in rests]
        page_data["tie_slur_shape_candidates"] = [item.to_dict() for item in tie_slurs]
        page_data["staff_system_candidates"] = [item.to_dict() for item in staff_systems]
        page_data["staff_system_candidate_count"] = len(staff_systems)
        page_data["barline_candidates"] = [item.to_dict() for item in barlines]
        page_data["barline_group_candidates"] = [item.to_dict() for item in barline_groups]
        page_data["barline_group_candidate_count"] = len(barline_groups)
        page_data["barline_candidate_count"] = len(barlines)
        page_data["system_barline_candidates"] = [item.to_dict() for item in system_barlines]
        page_data["measure_span_candidates"] = [item.to_dict() for item in measure_spans]
        page_data["measure_span_candidate_count"] = len(measure_spans)
        page_data["staff_grouping_mark_candidates"] = [item.to_dict() for item in grouping_marks]
        page_data["staff_grouping_mark_candidate_count"] = len(grouping_marks)
        page_data["printed_label_candidates"] = [item.to_dict() for item in printed_labels]
        page_data["printed_label_candidate_count"] = len(printed_labels)
        for key, values in section_data.items():
            page_data[key] = [item.to_dict() if hasattr(item, "to_dict") else item for item in values]
            page_data[key.replace("_candidates", "_candidate_count")] = len(values)
        page_data["staff_identity_evidence"] = [item.__dict__ for item in identity_evidence]
        page_data["staff_identity_evidence_count"] = len(identity_evidence)
        geometry_overlay = draw_geometry_overlay(page, page_data)
        geometry_overlay_path = output_dir / f"page-{page_number:03d}-geometry-overlay.png"
        if not cv2.imwrite(str(geometry_overlay_path), geometry_overlay):
            raise OSError(f"No se pudo escribir {geometry_overlay_path}")
        page_data["geometry_overlay"] = geometry_overlay_path.name
        analyses.append(page_data)

    if args.reviewed_rhythm_manifest:
        reviewed_manifest = json.loads(Path(args.reviewed_rhythm_manifest).read_text(encoding="utf-8"))
        if not isinstance(reviewed_manifest, dict) or not isinstance(reviewed_manifest.get("pages"), list):
            raise ValueError("El manifiesto rítmico debe contener una lista 'pages'")
        seen_review_pages = set()
        for page_manifest in reviewed_manifest["pages"]:
            if not isinstance(page_manifest, dict):
                raise ValueError("Cada página del manifiesto rítmico debe ser un objeto")
            page_number = page_manifest.get("page_number")
            if page_number not in rhythmic_groups_by_page:
                raise ValueError(f"El manifiesto rítmico referencia una página inexistente: {page_number}")
            if page_number in seen_review_pages:
                raise ValueError(f"Página repetida en el manifiesto rítmico: {page_number}")
            seen_review_pages.add(page_number)
            page_data = analyses[page_number - 1]
            page_data["reviewed_measure_timelines"] = build_reviewed_page_timelines(
                rhythmic_groups_by_page[page_number], page_manifest,
                rest_candidates=rest_candidates_by_page[page_number],
                pitch_candidates=pitch_candidates_by_page[page_number],
            )
        raw_cross_page_ties = reviewed_manifest.get("cross_page_tie_candidates", [])
        raw_cross_page_confirmations = reviewed_manifest.get("cross_page_tie_confirmations", [])
        if not isinstance(raw_cross_page_ties, list) or not isinstance(raw_cross_page_confirmations, list):
            raise ValueError("cross_page_tie_candidates y cross_page_tie_confirmations deben ser listas")
        if raw_cross_page_ties or raw_cross_page_confirmations:
            try:
                cross_page_ties = [
                    TieLinkCandidate(**{**item, "warnings": tuple(item.get("warnings", ()))})
                    for item in raw_cross_page_ties
                ]
                cross_page_confirmations = [
                    TieReviewConfirmation(**item) for item in raw_cross_page_confirmations
                ]
            except (TypeError, AttributeError) as exc:
                raise ValueError("La revisión de ligaduras entre páginas contiene campos inválidos") from exc
            reviewed_pages = [
                (page["page_number"], page["reviewed_measure_timelines"])
                for page in analyses if "reviewed_measure_timelines" in page
            ]
            applied_pages = apply_reviewed_tie_chains_across_pages(
                reviewed_pages, cross_page_ties, cross_page_confirmations
            )
            for page_number, timelines in applied_pages:
                analyses[page_number - 1]["reviewed_measure_timelines"] = timelines
        report_reviewed_count = sum(
            len(page.get("reviewed_measure_timelines", [])) for page in analyses
        )
    else:
        report_reviewed_count = 0

    global_measure_sequence = build_global_measure_sequence(analyses)
    global_measure_map = {
        (item["page_number"], item["staff_index"], item["measure_index_on_staff"]):
        item
        for item in global_measure_sequence["staff_measure_map"]
    }
    for page_data in analyses:
        for span in page_data.get("measure_span_candidates", []):
            measure_reference = global_measure_map.get((
                page_data["page_number"], span["staff_index"], span["measure_index"],
            ), {})
            span["global_measure_candidate"] = measure_reference.get("global_measure_candidate")
            span["alignment_status"] = measure_reference.get("alignment_status", "unknown")
            span["staff_support"] = measure_reference.get("staff_support", 0)
            span["possible_global_measure_candidates"] = measure_reference.get(
                "possible_global_measure_candidates", []
            )
        for anchor in page_data.get("section_measure_anchor_candidates", []):
            measure_reference = global_measure_map.get((
                page_data["page_number"], anchor["staff_index"],
                anchor["measure_index_on_staff"],
            ), {})
            anchor["global_measure_candidate"] = measure_reference.get("global_measure_candidate")
            anchor["global_alignment_status"] = measure_reference.get("alignment_status", "unmatched_local_interval")
            anchor["staff_support"] = measure_reference.get("staff_support", 0)
            anchor["warning"] += (
                " El ordinal global asociado también es provisional y depende "
                "de la conciliación geométrica de pentagramas."
            )
    global_section_ranges = link_section_ranges_across_pages(analyses)
    for section_range in global_section_ranges:
        for boundary_name in ("start", "end"):
            boundary = section_range.get(boundary_name)
            if not boundary:
                continue
            for anchor in boundary.get("measure_anchors", []):
                anchor["global_measure_candidate"] = global_measure_map.get((
                    boundary["page_number"], anchor["staff_index"],
                    anchor["measure_index_on_staff"],
                ))
    global_section_ranges = resolve_section_range_boundaries(
        global_section_ranges, global_measure_sequence
    )
    # La clasificación global de encabezados y límites se calcula después de
    # reunir todas las páginas. Redibujar ahora hace visible esa decisión en
    # los overlays, sin perder los candidatos locales originales.
    for page, page_data in zip(pages, analyses):
        geometry_overlay = draw_geometry_overlay(page, page_data)
        geometry_overlay_path = output_dir / page_data["geometry_overlay"]
        if not cv2.imwrite(str(geometry_overlay_path), geometry_overlay):
            raise OSError(f"No se pudo escribir {geometry_overlay_path}")
    report = {
        "global_measure_sequence": global_measure_sequence,
        "engine": "Palermo OMR",
        "global_section_range_candidates": global_section_ranges,
        "global_section_range_candidate_count": len(global_section_ranges),
        "version": __version__,
        "status": "geometric_candidates_prototype",
        "warning": (
            "Los resultados son hipótesis visuales, no una transcripción musical validada. "
            "Todavía no se reconocen de forma fiable claves, armaduras, alturas absolutas, "
            "duraciones, tipos de silencio, puntillos, ligaduras, voces ni estructura métrica. "
            "Los detectores de puntillos, silencios, barras y regiones de compás solo generan candidatos."
        ),
        "source_pdf": Path(args.pdf).name,
        "reviewed_measure_timeline_count": report_reviewed_count,
        "pages": analyses,
    }
    report_path = output_dir / "analysis.json"
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    total_staves = sum(len(page["staves"]) for page in analyses)
    total_heads = sum(page["notehead_candidate_count"] for page in analyses)
    total_hollow_heads = sum(page["hollow_notehead_candidate_count"] for page in analyses)
    total_rhythms = sum(page["rhythm_candidate_count"] for page in analyses)
    total_hollow_rhythms = sum(page["hollow_rhythm_candidate_count"] for page in analyses)
    total_beam_groups = sum(page["beam_group_candidate_count"] for page in analyses)
    total_rhythm_interpretations = sum(page["rhythmic_interpretation_candidate_count"] + page["hollow_rhythmic_interpretation_candidate_count"] for page in analyses)
    total_event_groups = sum(page["rhythmic_event_group_candidate_count"] for page in analyses)
    total_voice_layers = sum(page["staff_voice_layer_candidate_count"] for page in analyses)
    total_dots = sum(len(page["augmentation_dot_candidates"]) for page in analyses)
    total_rests = sum(len(page["rest_shape_candidates"]) for page in analyses)
    total_typed_rest_shapes = sum(
        sum(item["rest_type_candidate"] != "unclassified" for item in page["rest_shape_candidates"])
        for page in analyses
    )
    total_tie_slurs = sum(len(page["tie_slur_shape_candidates"]) for page in analyses)
    total_barlines = sum(page["barline_candidate_count"] for page in analyses)
    total_spans = sum(page["measure_span_candidate_count"] for page in analyses)
    total_grouping_marks = sum(page["staff_grouping_mark_candidate_count"] for page in analyses)
    total_printed_labels = sum(page["printed_label_candidate_count"] for page in analyses)
    total_section_markers = sum(page["section_marker_candidate_count"] for page in analyses)
    total_section_identifiers = sum(page["section_identifier_candidate_count"] for page in analyses)
    total_section_ranges = sum(page["section_range_candidate_count"] for page in analyses)
    total_global_section_ranges = len(global_section_ranges)
    total_identity_evidence = sum(page["staff_identity_evidence_count"] for page in analyses)
    print(f"Análisis terminado: {report_path}")
    print(f"Pentagramas candidatos: {total_staves}")
    print(f"Cabezas de nota rellenas candidatas: {total_heads}")
    print(f"Cabezas de nota huecas candidatas (separadas): {total_hollow_heads}")
    print(f"Análisis rítmicos de cabezas rellenas: {total_rhythms}")
    print(f"Análisis rítmicos de cabezas huecas (blancas/redondas candidatas): {total_hollow_rhythms}")
    print(f"Grupos de barras compartidas candidatos: {total_beam_groups}")
    print(f"Interpretaciones rítmicas candidatas: {total_rhythm_interpretations}")
    print(f"Grupos de ataque/acorde candidatos: {total_event_groups}")
    print(f"Capas de voz candidatas dentro de pentagramas: {total_voice_layers}")
    print(f"Puntillos candidatos: {total_dots}")
    print(f"Formas candidatas a silencio: {total_rests}")
    print(f"Formas con familia de silencio sugerida: {total_typed_rest_shapes}")
    print(f"Arcos candidatos a ligadura: {total_tie_slurs}")
    print(f"Barras de compás candidatas: {total_barlines}")
    print(f"Intervalos entre barras candidatas: {total_spans}")
    print(f"Marcas de agrupación de pentagramas candidatas: {total_grouping_marks}")
    print(f"Etiquetas musicales impresas candidatas: {total_printed_labels}")
    print(f"Marcas de sección candidatas: {total_section_markers}")
    print(f"Identificadores de sección candidatos: {total_section_identifiers}")
    print(f"Rangos de sección candidatos por página: {total_section_ranges}")
    print(f"Rangos globales de sección candidatos: {total_global_section_ranges}")
    print(f"Intervalos globales de compás candidatos: {global_measure_sequence['global_measure_candidate_count']}")
    print(f"Evidencias de identidad pendientes de revisión: {total_identity_evidence}")
    print("Aviso: ningún candidato equivale todavía a un evento musical confirmado.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
