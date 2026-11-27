# Palermo OMR — turno de trabajo vigente

Este archivo es la instrucción operativa que recibe cualquier persona o agente que tome el siguiente turno. Léelo completo antes de tocar el código. No dependas de mensajes de chat anteriores: este documento es la fuente de relevo del proyecto y debe actualizarse al cerrar cada turno.

## Estado verificado al abrir este turno
- Repositorio: `tuaatest-lgtm/repertorios`.
- Rama base de desarrollo: `feature/omr-propio-palermo`.
- HEAD base verificado al iniciar este turno: `9408a82b44608f1cbf2bfc08b62f7777ebd7d2f6`.
- La discrepancia del relevo anterior (`1288480e...`) quedó reconciliada: `ef38120a...` añadió el documento de relevo y `9408a82...` solo enlazó ambos documentos desde el README del motor; ninguno alteró código funcional OMR.
- CI del HEAD base `9408a82...`: ejecución `46083898050`, resultado `success`: https://github.com/tuaatest-lgtm/repertorios/actions/runs/46083898050
- Rama aislada de este turno: `work/review-index-contract-20261127`.
- Cambios de código y regresiones: commit `40f87583106898b87dbc47af73f5b16c9b9651f2` (incluye el commit previo de código `eb9cc7134cf411ae60010f044a32e7dc83d1371d`). PR de validación en borrador #1: https://github.com/tuaatest-lgtm/repertorios/pull/1; no fusionado.
- CI PR `46085178837`: instalación, suite `pytest` y test del cliente API del navegador observados como `success`; la ejecución seguía finalizando tareas de limpieza al redactar este relevo: https://github.com/tuaatest-lgtm/repertorios/actions/runs/46085178837.
- `main`, `index.html` de producción y Sonoro permanecen fuera de alcance.

## Qué existe y qué no debe confundirse
- El motor Python procesa PDF y genera detecciones geométricas y candidatos de pentagramas, cabezas, grupos rítmicos, silencios, puntillos, barras y ligaduras.
- Hay un modelo temporal con fracciones exactas que puede conservar ataques simultáneos y duraciones independientes entre voces, siempre que los eventos ya estén correctamente interpretados.
- La construcción de timeline revisado acepta enlaces explícitos de puntillos visuales a eventos confirmados. Requiere la misma lista ordenada de candidatos y no convierte detecciones sin revisar en hechos musicales.
- Las asociaciones de clave, armadura, altura, voz, compás, duración, silencios y ligaduras siguen dependiendo en gran medida de revisión humana.
- No existe aún una transcripción completa, validada y medida de una partitura real. Los tests sintéticos prueban contratos de software, no la exactitud musical.
- El porcentaje publicado en `omr-engine/docs/project-progress.md` es una estimación de madurez funcional, no de precisión. No lo aumentes por agregar infraestructura, tests o candidatos.

## Encargo del siguiente turno
**Construir una primera unidad de anotación humana asistida, reproducible y trazable para una sección pequeña de una partitura real**, usando las herramientas y esquemas de anotación que ya existen. El objetivo es cerrar el ciclo entre candidatos visuales y verdad de referencia humana; no inventar una transcripción automática.

### Secuencia de trabajo
1. Verifica el HEAD actual y confirma que contiene este archivo. Si la rama avanzó desde `1288480e562c6a23359f58897d13ec131106fd66`, inspecciona y reconcilia los cambios antes de continuar.
2. Lee `omr-engine/docs/annotation-dataset.md`, `omr-engine/docs/annotation-workflow.md`, `omr-engine/docs/review-package.md`, `omr-engine/docs/event-evaluation.md`, `omr-engine/docs/dataset-evaluation.md` y el esquema del manifiesto/corpus. Inspecciona las implementaciones y pruebas actuales; reutilízalas.
3. Localiza la partitura de referencia `Clamaré a Dios - Coro.pdf`. Su SHA-256 conocido es `bbf62fa7b3be45585e3d77a7d0b3fe57ab4701ff17c8e821f14dbdc88f64f74c`. Si el archivo no está disponible en el entorno, no sustituyas otra partitura ni inventes resultados: deja documentada la dependencia exacta y avanza solo con el diseño/herramientas que puedan probarse.
4. Escoge una sola unidad acotada (preferiblemente el primer sistema completo de la primera página) y verifica que su alcance sea identificable en el PDF y en los candidatos del motor. No intentes anotar las tres páginas en este turno.
5. Implementa o completa, solo si hace falta, una exportación/plantilla de anotación que permita a una persona revisar candidatos con identificadores estables y registrar por evento, como mínimo: sistema/pentagrama, voz o estado sin resolver, compás o estado sin resolver, tipo de evento, cabezas de nota asociadas, alturas escritas/sonoras según el esquema existente, onset y duración exactos o estado desconocido, y evidencia/decisión humana. Los silencios, acordes y ligaduras deben poder permanecer pendientes; nunca fuerces valores.
6. Asegura que la anotación pueda volver a cargarse y validarse sin perder IDs, fracciones, página, coordenadas ni estados de incertidumbre. Si el esquema actual ya lo permite, no dupliques formatos: añade el ejemplo de fixture y la documentación que falten.
7. Crea un fixture de ejemplo claramente marcado como `draft` o `needs_review`. **No lo declares ground truth ni lo uses para publicar precisión** mientras no haya confirmación humana completa.
8. Añade pruebas para exportar, reimportar, validar IDs, preservar fracciones exactas, rechazar referencias inexistentes y bloquear la promoción de borradores a referencia aprobada.
9. Ejecuta pruebas específicas y suite completa. Consulta el resultado CI real del commit final. Documenta límites y cualquier paso de revisión que todavía deba realizar una persona.
10. Actualiza este archivo para entregar el siguiente turno a otra persona, con SHA base/final, evidencia de tests y una única tarea siguiente acotada.

### Criterios de aceptación
- El flujo funciona sobre un fragmento real o, si el PDF no está disponible, el bloqueo queda descrito sin fingir ejecución real.
- La anotación mantiene la distinción entre candidato, decisión humana y ground truth aprobado.
- IDs, coordenadas, fracciones y estados desconocidos sobreviven al ciclo exportar/importar.
- La validación impide aprobar una anotación incompleta o no revisada.
- Las pruebas automatizadas cubren los contratos nuevos y las regresiones.
- No hay cambios en `main`, `index.html` ni Sonoro; no se despliega ni integra.
- No se modifica el porcentaje de progreso salvo evidencia musical real aprobada que cumpla la política del proyecto.

## Instrucción exacta para quien toma el turno
Trabaja como responsable técnico del motor OMR propio de Palermo Music. Empieza verificando la rama y el SHA; lee `AGENTS.md` y este archivo; inspecciona primero lo que ya existe antes de programar. Ejecuta el encargo del siguiente turno con el alcance limitado y los criterios de aceptación indicados. No inventes resultados ni completes datos musicales por intuición. Mantén la polifonía real y la aritmética temporal exacta. Al terminar, actualiza este mismo archivo con el estado comprobado y deja una sola tarea siguiente, concreta y ejecutable para el próximo participante. No hagas push, merge, despliegue ni integración con Sonoro sin autorización expresa.

## Registro de turnos
- Turno inicial de relevo: reglas generales añadidas en `AGENTS.md`; instrucción vigente creada aquí.
- Turno de corrección de referencias: se verificó que `rhythmic_event_groups.py` construye grupos sobre `noteheads + hollow_noteheads`, mientras `staff_voice_layers.py` opera solo sobre cabezas rellenas. `review_package.py` resolvía ambas familias contra `filled_candidate_ids`, causando índices fuera de rango o asociaciones erróneas cuando un grupo incluía cabezas huecas.
- Corrección: el paquete ahora mantiene un mapa de IDs y pentagramas para el espacio combinado, y conserva el mapa exclusivo de cabezas rellenas para capas de voz, haces y puntillos. Añadidas dos regresiones en `tests/test_review_package.py`: vínculo de grupo rítmico a cabeza hueca y conservación del espacio de índices de capas de voz.
- Archivos funcionales modificados: `omr-engine/src/palermo_omr/review_package.py` y `omr-engine/tests/test_review_package.py`. No se modificó `main`, `index.html`, Sonoro ni el porcentaje de progreso.
- Base de trabajo: `9408a82b44608f1cbf2bfc08b62f7777ebd7d2f6`. Rama aislada: `work/review-index-contract-20261127`. Commit de código + pruebas: `40f87583106898b87dbc47af73f5b16c9b9651f2`. PR #1 está abierto en borrador, sin fusionar.
- Validación local: no ejecutada, porque el entorno no pudo clonar el repositorio por falta de resolución DNS. Validación CI PR `46085178837`: instalación, `python -m pytest -q` y `node --test web/test-omr-client.mjs` observados exitosos; el job aún estaba completando limpieza al cerrar este registro. Consultar el estado final antes de considerar el turno completamente verde.
- Siguiente tarea única: una vez confirmado el resultado final de CI, ejecutar el pipeline y `prepare_review_package` sobre `Clamaré a Dios - Coro.pdf` (SHA-256 `bbf62fa7b3be45585e3d77a7d0b3fe57ab4701ff17c8e821f14dbdc88f64f74c`) en el primer sistema de la primera página; comprobar que todos los `rhythmic_event_group` y `staff_voice_layer` se enlazan a los IDs correctos sin errores. Si el PDF no está disponible, registrar el bloqueo exacto y no inventar resultados. Después continuar la primera plantilla de anotación humana draft/needs_review, sin declarar ground truth.
