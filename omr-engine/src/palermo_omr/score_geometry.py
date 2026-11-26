"""Construcción de estructura de página a partir de candidatos geométricos."""
from __future__ import annotations

from .imaging import StaffCandidate
from .measure_layout import MeasureSpanCandidate, StaffSystemCandidate
from .score_structure import MeasureRegion, ScoreStaff, ScoreStructure, ScoreSystem, StaffAssignment


def build_geometric_score_structure(page_number, staves, system_candidates, measure_span_candidates):
    """Convierte candidatos geométricos sin inferir partes ni voces."""
    if not isinstance(page_number, int) or isinstance(page_number, bool) or page_number < 1:
        raise ValueError("page_number debe ser un entero positivo")

    score_staves = tuple(
        ScoreStaff(f"p{page_number}-staff-{i + 1}", page_number, i)
        for i in range(len(staves))
    )
    staff_ids = {i: item.staff_id for i, item in enumerate(score_staves)}
    systems = []
    staff_to_system = {}

    for candidate in sorted(system_candidates, key=lambda item: item.system_index):
        if candidate.system_index < 0:
            raise ValueError("system_index no puede ser negativo")
        if not candidate.staff_indices:
            raise ValueError("Un sistema candidato debe contener pentagramas")
        system_id = f"p{page_number}-system-{candidate.system_index + 1}"
        members = []
        for index in candidate.staff_indices:
            if index not in staff_ids:
                raise ValueError(f"Índice de pentagrama inexistente: {index}")
            if index in staff_to_system:
                raise ValueError("Un pentagrama no puede pertenecer a dos sistemas candidatos")
            staff_to_system[index] = system_id
            members.append(staff_ids[index])
        systems.append(ScoreSystem(system_id, page_number, tuple(members)))

    assignments = tuple(StaffAssignment(staff_id=item.staff_id) for item in score_staves)
    regions = []
    for candidate in measure_span_candidates:
        if candidate.staff_index not in staff_ids:
            raise ValueError(f"Índice de pentagrama inexistente en intervalo: {candidate.staff_index}")
        system_id = staff_to_system.get(candidate.staff_index)
        if system_id is None:
            continue
        regions.append(MeasureRegion(
            f"p{page_number}-staff-{candidate.staff_index + 1}-measure-{candidate.measure_index}",
            system_id, staff_ids[candidate.staff_index], candidate.measure_index,
            float(candidate.x_start), float(candidate.x_end),
        ))

    result = ScoreStructure(
        page_number=page_number, systems=tuple(systems), staves=score_staves,
        staff_assignments=assignments, measure_regions=tuple(regions),
    )
    result.validate()
    return result
