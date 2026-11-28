"""Herramientas CLI para preparar y revisar manifiestos de anotación."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import fitz

from .annotation_dataset import AnnotatedScore, AnnotationDataset
from fractions import Fraction

from .dataset_evaluation import evaluate_annotation_dataset
from .event_evaluation import ScoreEvent
from .review_package import prepare_review_package
from .section_review import apply_section_range_decisions


def _load_dataset(path: Path) -> AnnotationDataset:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"No se pudo leer el manifiesto {path}: {exc}") from exc
    return AnnotationDataset.from_dict(data)


def _write_dataset(path: Path, dataset: AnnotationDataset) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(dataset.to_dict(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def initialize_score_manifest(
    pdf_path: str | Path,
    manifest_path: str | Path,
    *,
    score_id: str,
    split: str,
    annotation_version: str = "1.0",
) -> AnnotationDataset:
    """Registra un PDF real como borrador vacío; no inventa eventos."""
    import hashlib

    source = Path(pdf_path)
    destination = Path(manifest_path)
    if not source.is_file():
        raise ValueError(f"No existe el PDF: {source}")
    if not score_id.strip():
        raise ValueError("score_id no puede estar vacío")
    if split not in {"train", "validation", "test"}:
        raise ValueError("split debe ser train, validation o test")

    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    try:
        with fitz.open(source) as pdf:
            page_count = len(pdf)
    except Exception as exc:
        raise ValueError(f"No se pudo abrir el PDF: {exc}") from exc
    if page_count < 1:
        raise ValueError("El PDF no contiene páginas")

    if destination.exists():
        dataset = _load_dataset(destination)
    else:
        dataset = AnnotationDataset(dataset_version="0.1", scores=())
    new_score = AnnotatedScore(
        score_id=score_id,
        source_sha256=digest,
        page_count=page_count,
        split=split,
        annotation_version=annotation_version,
        review_status="draft",
        events=(),
    )
    updated = AnnotationDataset(
        dataset_version=dataset.dataset_version,
        scores=dataset.scores + (new_score,),
    )
    updated.validate(require_reviewed=False)
    _write_dataset(destination, updated)
    return updated


def validate_manifest(path: str | Path, *, allow_drafts: bool = False) -> AnnotationDataset:
    dataset = _load_dataset(Path(path))
    dataset.validate(require_reviewed=not allow_drafts)
    return dataset



def import_score_events(
    manifest_path: str | Path,
    score_id: str,
    events_path: str | Path,
) -> AnnotationDataset:
    """Importa eventos revisados/por revisar desde un JSON separado, sin aprobarlos."""
    from dataclasses import replace

    manifest = Path(manifest_path)
    dataset = _load_dataset(manifest)
    matches = [item for item in dataset.scores if item.score_id == score_id]
    if len(matches) != 1:
        raise ValueError(f"No existe una única partitura con score_id={score_id}")
    score = matches[0]
    if score.review_status == "reviewed":
        raise ValueError("No se pueden modificar eventos de una partitura ya revisada")
    try:
        raw_events = json.loads(Path(events_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"No se pudo leer el archivo de eventos: {exc}") from exc
    if not isinstance(raw_events, list) or not raw_events:
        raise ValueError("El archivo de eventos debe ser una lista JSON no vacía")
    parsed = []
    required = {
        "event_id", "page_number", "staff_index", "measure_index",
        "onset_quarters", "event_type", "pitches_midi",
        "duration_quarters", "voice_id",
    }
    allowed = required | {"source_candidate_ids"}
    for raw in raw_events:
        if not isinstance(raw, dict) or set(raw) not in (required, allowed):
            raise ValueError("Cada evento debe contener los campos de ScoreEvent y evidencia opcional")
        if "source_candidate_ids" in raw and not isinstance(raw["source_candidate_ids"], list):
            raise ValueError("source_candidate_ids debe ser una lista")
        parsed.append(raw)
    manifest_data = dataset.to_dict()
    for raw_score in manifest_data["scores"]:
        if raw_score["score_id"] == score_id:
            if raw_score["events"]:
                raise ValueError("La partitura ya tiene eventos; no se sobrescriben ni duplican")
            raw_score["events"] = parsed
            break
    updated = AnnotationDataset.from_dict(manifest_data)
    updated.validate(require_reviewed=False)
    _write_dataset(manifest, updated)
    return updated

def confirm_score_review(
    path: str | Path,
    score_id: str,
    *,
    human_review_confirmed: bool,
) -> AnnotationDataset:
    """Marca una partitura revisada solo tras una confirmación humana explícita."""
    from dataclasses import replace

    if not human_review_confirmed:
        raise ValueError(
            "Se requiere confirmación humana mediante --confirm-human-review: confirma que cada evento fue contrastado visualmente"
        )
    dataset = _load_dataset(Path(path))
    matches = [score for score in dataset.scores if score.score_id == score_id]
    if len(matches) != 1:
        raise ValueError(f"No existe una única partitura con score_id={score_id}")
    score = matches[0]
    if not score.events:
        raise ValueError("No se puede aprobar una partitura sin eventos anotados")
    reviewed = replace(score, review_status="reviewed")
    updated = replace(
        dataset,
        scores=tuple(reviewed if item.score_id == score_id else item for item in dataset.scores),
    )
    updated.validate(require_reviewed=False)
    _write_dataset(Path(path), updated)
    return updated



def evaluate_manifest(manifest_path, predictions_path, *, split="test"):
    """Evalúa predicciones JSON contra una partición revisada."""
    dataset = validate_manifest(manifest_path)
    try:
        raw = json.loads(Path(predictions_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"No se pudo leer el archivo de predicciones: {exc}") from exc
    if not isinstance(raw, dict):
        raise ValueError("Las predicciones deben ser un objeto JSON por score_id")
    predictions = {}
    required = {
        "event_id", "page_number", "staff_index", "measure_index",
        "onset_quarters", "event_type", "pitches_midi",
        "duration_quarters", "voice_id",
    }
    allowed = required | {"source_candidate_ids"}
    for score_id, items in raw.items():
        if not isinstance(score_id, str) or not isinstance(items, list):
            raise ValueError("Cada score_id debe contener una lista de eventos")
        parsed = []
        for item in items:
            if not isinstance(item, dict) or set(item) not in (required, allowed):
                raise ValueError("Predicción con campos ausentes o desconocidos")
            onset = item["onset_quarters"]
            duration = item["duration_quarters"]
            parsed.append(ScoreEvent(
                event_id=item["event_id"],
                page_number=item["page_number"],
                staff_index=item["staff_index"],
                measure_index=item["measure_index"],
                onset_quarters=Fraction(str(onset)) if onset is not None else None,
                event_type=item["event_type"],
                pitches_midi=tuple(item["pitches_midi"]) if item["pitches_midi"] is not None else None,
                duration_quarters=Fraction(str(duration)) if duration is not None else None,
                voice_id=item["voice_id"],
                source_candidate_ids=tuple(item.get("source_candidate_ids", [])),
            ))
        predictions[score_id] = tuple(parsed)
    result = evaluate_annotation_dataset(dataset, predictions, split=split)
    return {
        "split": result.split,
        "score_count": result.score_count,
        "predicted_count": result.predicted_count,
        "reference_count": result.reference_count,
        "true_positive": result.true_positive,
        "false_positive": result.false_positive,
        "false_negative": result.false_negative,
        "precision": result.precision,
        "recall": result.recall,
        "f1": result.f1,
        "event_type_accuracy": result.event_type_accuracy,
        "pitch_accuracy": result.pitch_accuracy,
        "duration_accuracy": result.duration_accuracy,
        "voice_accuracy": result.voice_accuracy,
        "mean_onset_error_quarters": result.mean_onset_error_quarters,
        "per_score": [
            {
                "score_id": item.score_id,
                "precision": item.evaluation.precision,
                "recall": item.evaluation.recall,
                "f1": item.evaluation.f1,
                "true_positive": item.evaluation.true_positive,
                "false_positive": item.evaluation.false_positive,
                "false_negative": item.evaluation.false_negative,
            }
            for item in result.per_score
        ],
    }

def review_section_package(
    package_path: str | Path,
    decisions_path: str | Path,
    output_path: str | Path,
    *,
    human_review_confirmed: bool,
    allow_open_ended: bool = False,
) -> dict:
    """Aplica decisiones humanas explícitas a un paquete de rangos de sección."""
    try:
        package = json.loads(Path(package_path).read_text(encoding="utf-8"))
        decisions = json.loads(Path(decisions_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"No se pudo leer el paquete o las decisiones: {exc}") from exc
    updated = apply_section_range_decisions(
        package,
        decisions,
        human_review_confirmed=human_review_confirmed,
        allow_open_ended=allow_open_ended,
    )
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    temporary.write_text(
        json.dumps(updated, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(destination)
    return updated


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="palermo-omr-dataset",
        description="Prepara y valida corpus de anotaciones humanas para Palermo OMR.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser(
        "init", help="Registra un PDF en el manifiesto como borrador vacío"
    )
    init_parser.add_argument("pdf")
    init_parser.add_argument("--manifest", required=True)
    init_parser.add_argument("--score-id", required=True)
    init_parser.add_argument("--split", choices=("train", "validation", "test"), required=True)
    init_parser.add_argument("--annotation-version", default="1.0")

    prepare_parser = subparsers.add_parser(
        "prepare-review", help="Prepara un paquete de revisión desde analysis.json"
    )
    prepare_parser.add_argument("analysis")
    prepare_parser.add_argument("--score-id", required=True)
    prepare_parser.add_argument("--output", required=True)

    evaluate_parser = subparsers.add_parser(
        "evaluate", help="Evalúa predicciones contra una partición revisada"
    )
    evaluate_parser.add_argument("manifest")
    evaluate_parser.add_argument("--predictions", required=True)
    evaluate_parser.add_argument("--split", choices=("train", "validation", "test"), default="test")
    evaluate_parser.add_argument("--output", required=True)

    validate_parser = subparsers.add_parser("validate", help="Valida el manifiesto")
    validate_parser.add_argument("manifest")
    validate_parser.add_argument(
        "--allow-drafts", action="store_true",
        help="Permite borradores; no los habilita como ground truth de evaluación",
    )

    import_parser = subparsers.add_parser(
        "import-events", help="Importa eventos musicales desde un archivo JSON"
    )
    import_parser.add_argument("manifest")
    import_parser.add_argument("--score-id", required=True)
    import_parser.add_argument("--events", required=True)

    section_review_parser = subparsers.add_parser(
        "review-sections",
        help="Aplica decisiones humanas explícitas a rangos de sección candidatos",
    )
    section_review_parser.add_argument("package")
    section_review_parser.add_argument("--decisions", required=True)
    section_review_parser.add_argument("--output", required=True)
    section_review_parser.add_argument("--confirm-human-review", action="store_true")
    section_review_parser.add_argument("--allow-open-ended", action="store_true")

    review_parser = subparsers.add_parser(
        "review", help="Aprueba una partitura tras revisión humana explícita"
    )
    review_parser.add_argument("manifest")
    review_parser.add_argument("--score-id", required=True)
    review_parser.add_argument(
        "--confirm-human-review", action="store_true",
        help="Confirma que todos los eventos fueron contrastados con la partitura",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "init":
            dataset = initialize_score_manifest(
                args.pdf, args.manifest, score_id=args.score_id,
                split=args.split, annotation_version=args.annotation_version,
            )
            score = dataset.scores[-1]
            print(f"Partitura registrada: {score.score_id}")
            print(f"SHA-256: {score.source_sha256}")
            print(f"Páginas: {score.page_count}")
            print("Estado: draft (sin eventos; aún no es ground truth)")
        elif args.command == "prepare-review":
            package = prepare_review_package(
                args.analysis, args.output, score_id=args.score_id
            )
            print("Paquete de revisión: {}".format(args.output))
            print("Candidatos de cabezas: {}".format(package["summary"]["notehead_candidate_count"]))
            print("Otros candidatos: {}".format(package["summary"]["other_candidate_count"]))
            print("Todos requieren revisión humana; no son eventos confirmados.")
        elif args.command == "evaluate":
            report = evaluate_manifest(args.manifest, args.predictions, split=args.split)
            Path(args.output).parent.mkdir(parents=True, exist_ok=True)
            Path(args.output).write_text(
                json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            print("Evaluación {}: {} partituras".format(args.split, report["score_count"]))
            print("Precisión={} Recall={} F1={}".format(report["precision"], report["recall"], report["f1"]))
            print("Informe: {}".format(args.output))
        elif args.command == "validate":
            dataset = validate_manifest(args.manifest, allow_drafts=args.allow_drafts)
            print(f"Manifiesto válido: {len(dataset.scores)} partituras")
            for score in dataset.scores:
                print(
                    f"- {score.score_id}: {score.page_count} páginas, "
                    f"{len(score.events)} eventos, {score.split}, {score.review_status}"
                )
        elif args.command == "import-events":
            dataset = import_score_events(args.manifest, args.score_id, args.events)
            score = next(item for item in dataset.scores if item.score_id == args.score_id)
            print(f"Eventos importados: {len(score.events)}")
            print("Estado: draft (requiere revisión humana)")
        elif args.command == "review-sections":
            package = review_section_package(
                args.package,
                args.decisions,
                args.output,
                human_review_confirmed=args.confirm_human_review,
                allow_open_ended=args.allow_open_ended,
            )
            summary = package.get("summary", {})
            print("Paquete de secciones actualizado: {}".format(args.output))
            print("Pendientes: {}".format(summary.get("pending_global_section_range_candidate_count", 0)))
            print("Aceptados: {}".format(summary.get("accepted_global_section_range_candidate_count", 0)))
            print("Rechazados: {}".format(summary.get("rejected_global_section_range_candidate_count", 0)))
        elif args.command == "review":
            dataset = confirm_score_review(
                args.manifest, args.score_id,
                human_review_confirmed=args.confirm_human_review,
            )
            print(f"Partitura aprobada por confirmación humana: {args.score_id}")
            print(f"Total de partituras: {len(dataset.scores)}")
        return 0
    except (ValueError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
