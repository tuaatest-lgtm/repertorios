"""Modelo de documento multipágina y continuidad explícita de pentagramas.

No deduce identidades musicales por posición ni convierte continuidad gráfica
en asignación de parte o voz.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from .score_structure import ScoreStructure


_CONTINUITY_STATUSES = {"proposed", "confirmed", "ambiguous"}


@dataclass(frozen=True)
class StaffContinuation:
    source_staff_id: str
    target_staff_id: str
    status: str
    evidence: str = ""


@dataclass(frozen=True)
class GlobalMeasureNumber:
    region_id: str
    global_measure_number: int


@dataclass(frozen=True)
class ScoreDocument:
    pages: tuple[ScoreStructure, ...]
    staff_continuities: tuple[StaffContinuation, ...] = ()
    global_measure_numbers: tuple[GlobalMeasureNumber, ...] = ()

    def validate(self) -> None:
        if not self.pages:
            raise ValueError("El documento debe contener al menos una página")

        page_numbers = [page.page_number for page in self.pages]
        if len(page_numbers) != len(set(page_numbers)):
            raise ValueError("El documento no puede repetir números de página")
        if page_numbers != sorted(page_numbers):
            raise ValueError("Las páginas deben estar ordenadas por número")

        staff_ids = {}
        region_ids = set()
        for page in self.pages:
            page.validate()
            for staff in page.staves:
                if staff.staff_id in staff_ids:
                    raise ValueError("Los identificadores de pentagrama deben ser únicos en el documento")
                staff_ids[staff.staff_id] = staff.page_number
            for region in page.measure_regions:
                if region.region_id in region_ids:
                    raise ValueError("Los identificadores de región deben ser únicos en el documento")
                region_ids.add(region.region_id)

        seen_links = set()
        for link in self.staff_continuities:
            pair = (link.source_staff_id, link.target_staff_id)
            if pair in seen_links:
                raise ValueError("No se puede repetir una continuidad")
            seen_links.add(pair)
            if link.source_staff_id not in staff_ids or link.target_staff_id not in staff_ids:
                raise ValueError("Una continuidad referencia un pentagrama inexistente")
            if staff_ids[link.source_staff_id] >= staff_ids[link.target_staff_id]:
                raise ValueError("La continuidad debe avanzar hacia una página posterior")
            if link.status not in _CONTINUITY_STATUSES:
                raise ValueError(f"Estado de continuidad no válido: {link.status}")
            if link.status == "confirmed" and not link.evidence.strip():
                raise ValueError("Una continuidad confirmada debe incluir evidencia")

        numbered_regions = set()
        for item in self.global_measure_numbers:
            if item.region_id not in region_ids:
                raise ValueError("La numeración global referencia una región inexistente")
            if item.region_id in numbered_regions:
                raise ValueError("Una región no puede recibir dos números globales")
            numbered_regions.add(item.region_id)
            if (not isinstance(item.global_measure_number, int)
                    or isinstance(item.global_measure_number, bool)
                    or item.global_measure_number < 1):
                raise ValueError("El número global de compás debe ser un entero positivo")

    @property
    def ordered_system_refs(self) -> tuple[tuple[int, str], ...]:
        self.validate()
        return tuple(
            (page.page_number, system.system_id)
            for page in self.pages
            for system in page.systems
        )

    def to_dict(self) -> dict:
        self.validate()
        return asdict(self)
