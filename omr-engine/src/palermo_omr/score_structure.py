"""Modelo explícito de estructura musical, separado de la detección visual.

Las asignaciones entre pentagramas, partes y voces solo son fiables cuando
otra etapa o una revisión humana las confirma. Este módulo valida relaciones;
no infiere instrumentación ni voces a partir de la posición gráfica.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field


_PART_KINDS = {"instrument", "vocal", "unknown"}
_ASSIGNMENT_STATUSES = {"unassigned", "proposed", "confirmed", "ambiguous"}


@dataclass(frozen=True)
class ScoreSystem:
    system_id: str
    page_number: int
    staff_ids: tuple[str, ...]


@dataclass(frozen=True)
class ScoreStaff:
    staff_id: str
    page_number: int
    detected_staff_index: int


@dataclass(frozen=True)
class ScorePart:
    part_id: str
    name: str
    kind: str = "unknown"


@dataclass(frozen=True)
class ScoreVoice:
    voice_id: str
    part_id: str
    name: str


@dataclass(frozen=True)
class StaffAssignment:
    staff_id: str
    status: str = "unassigned"
    part_id: str | None = None
    voice_ids: tuple[str, ...] = ()
    evidence: str = ""


@dataclass(frozen=True)
class MeasureRegion:
    region_id: str
    system_id: str
    staff_id: str
    measure_number: int
    x_start: float
    x_end: float


@dataclass(frozen=True)
class ScoreStructure:
    """Estructura de una página; puede crecer a un documento multipágina después."""

    page_number: int
    systems: tuple[ScoreSystem, ...] = ()
    staves: tuple[ScoreStaff, ...] = ()
    parts: tuple[ScorePart, ...] = ()
    voices: tuple[ScoreVoice, ...] = ()
    staff_assignments: tuple[StaffAssignment, ...] = ()
    measure_regions: tuple[MeasureRegion, ...] = ()

    def validate(self) -> None:
        if not isinstance(self.page_number, int) or isinstance(self.page_number, bool) or self.page_number < 1:
            raise ValueError("page_number debe ser un entero positivo")

        _unique_ids(self.systems, "system_id", "sistemas")
        _unique_ids(self.staves, "staff_id", "pentagramas")
        _unique_ids(self.parts, "part_id", "partes")
        _unique_ids(self.voices, "voice_id", "voces")
        _unique_ids(self.measure_regions, "region_id", "regiones de compás")

        systems = {item.system_id: item for item in self.systems}
        staves = {item.staff_id: item for item in self.staves}
        parts = {item.part_id: item for item in self.parts}
        voices = {item.voice_id: item for item in self.voices}

        for part in self.parts:
            if part.kind not in _PART_KINDS:
                raise ValueError(f"Tipo de parte no válido: {part.kind}")
            if not part.name.strip():
                raise ValueError("Cada parte debe tener un nombre")

        for voice in self.voices:
            if voice.part_id not in parts:
                raise ValueError(f"La voz {voice.voice_id} referencia una parte inexistente")
            if not voice.name.strip():
                raise ValueError("Cada voz debe tener un nombre")

        for system in self.systems:
            _positive_page(system.page_number)
            if system.page_number != self.page_number:
                raise ValueError("Todos los sistemas deben pertenecer a la página de la estructura")
            if not system.staff_ids:
                raise ValueError("Un sistema debe contener al menos un pentagrama")
            if len(set(system.staff_ids)) != len(system.staff_ids):
                raise ValueError("Un sistema no puede repetir pentagramas")
            if any(staff_id not in staves for staff_id in system.staff_ids):
                raise ValueError("Un sistema referencia un pentagrama inexistente")

        for staff in self.staves:
            _positive_page(staff.page_number)
            if staff.page_number != self.page_number:
                raise ValueError("Todos los pentagramas deben pertenecer a la página de la estructura")
            if staff.detected_staff_index < 0:
                raise ValueError("detected_staff_index no puede ser negativo")

        system_for_staff: dict[str, str] = {}
        for system in self.systems:
            for staff_id in system.staff_ids:
                if staff_id in system_for_staff:
                    raise ValueError("Un pentagrama no puede pertenecer a dos sistemas de la misma página")
                system_for_staff[staff_id] = system.system_id

        assigned_staffs: set[str] = set()
        for assignment in self.staff_assignments:
            if assignment.staff_id not in staves:
                raise ValueError("Una asignación referencia un pentagrama inexistente")
            if assignment.staff_id in assigned_staffs:
                raise ValueError("No puede haber más de una asignación por pentagrama")
            assigned_staffs.add(assignment.staff_id)
            if assignment.status not in _ASSIGNMENT_STATUSES:
                raise ValueError(f"Estado de asignación no válido: {assignment.status}")
            if assignment.status == "confirmed" and assignment.part_id is None:
                raise ValueError("Una asignación confirmada debe indicar su parte")
            if assignment.part_id is not None and assignment.part_id not in parts:
                raise ValueError("Una asignación referencia una parte inexistente")
            if assignment.status in {"unassigned", "ambiguous"} and assignment.part_id is not None:
                raise ValueError("Una asignación sin resolver no debe fijar una parte")
            if len(set(assignment.voice_ids)) != len(assignment.voice_ids):
                raise ValueError("Una asignación no puede repetir voces")
            for voice_id in assignment.voice_ids:
                if voice_id not in voices:
                    raise ValueError("Una asignación referencia una voz inexistente")
                if assignment.part_id is not None and voices[voice_id].part_id != assignment.part_id:
                    raise ValueError("La voz asignada debe pertenecer a la parte indicada")
            if assignment.status in {"unassigned", "ambiguous"} and assignment.voice_ids:
                raise ValueError("Una asignación sin resolver no debe fijar voces")

        for region in self.measure_regions:
            if region.system_id not in systems:
                raise ValueError("Una región de compás referencia un sistema inexistente")
            if region.staff_id not in staves:
                raise ValueError("Una región de compás referencia un pentagrama inexistente")
            if system_for_staff.get(region.staff_id) != region.system_id:
                raise ValueError("El pentagrama de la región no pertenece al sistema indicado")
            if not isinstance(region.measure_number, int) or isinstance(region.measure_number, bool) or region.measure_number < 1:
                raise ValueError("measure_number debe ser un entero positivo")
            if region.x_end <= region.x_start:
                raise ValueError("x_end debe ser mayor que x_start")

    def to_dict(self) -> dict:
        self.validate()
        return asdict(self)


def _unique_ids(items: tuple, attribute: str, label: str) -> None:
    values = [getattr(item, attribute) for item in items]
    if any(not isinstance(value, str) or not value.strip() for value in values):
        raise ValueError(f"Los identificadores de {label} deben ser textos no vacíos")
    if len(values) != len(set(values)):
        raise ValueError(f"Los identificadores de {label} deben ser únicos")


def _positive_page(value: int) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ValueError("page_number debe ser un entero positivo")
