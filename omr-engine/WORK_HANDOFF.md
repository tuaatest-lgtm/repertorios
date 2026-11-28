# Palermo OMR — turno de trabajo vigente

Este archivo es la instrucción operativa que recibe cualquier persona o agente que tome el siguiente turno. Léelo completo antes de tocar el código. No dependas de mensajes de chat anteriores: este documento es la fuente de relevo del proyecto y debe actualizarse al cerrar cada turno.

## Estado verificado al abrir este turno
- Repositorio: `tuaatest-lgtm/repertorios`.
- Rama de desarrollo: `feature/omr-propio-palermo`.
- HEAD base de este relevo: `1288480e562c6a23359f58897d13ec131106fd66`.
- Commit inmediatamente anterior con funcionalidad OMR: `2a291cb2994c9f7706427350b7f0e66ae658ea38`.
- CI observado para ese commit funcional: ejecución `46083299834`, resultado `success`: https://github.com/tuaatest-lgtm/repertorios/actions/runs/46083299834
- El commit base de este relevo añade las reglas de contribución en `AGENTS.md`; no es una mejora de precisión OMR. Verifica CI del HEAD antes de declarar la rama completamente verde.
- `main`, `index.html` de producción y Sonoro permanecen fuera de alcance.

## Qué existe y qué no debe confundirse
- El motor Python procesa PDF y genera detecciones geométricas y candidatos de pentagramas, cabezas, grupos rítmicos, silencios, puntillos, barras y ligaduras.
- Hay un modelo temporal con fracciones exactas que puede conservar ataques simultáneos y duraciones independientes entre voces, siempre que los eventos ya estén correctamente interpretados.
- La construcción de timeline revisado acepta enlaces explícitos de puntillos visuales a eventos confirmados. Requiere la misma lista ordenada de candidatos y no convierte detecciones sin revisar en hechos musicales.
- Las asociaciones de clave, armadura, altura, voz, compás, duración, silencios y ligaduras siguen dependiendo en gran medida de revisión humana.
- No existe aún una transcripción completa, validada y medida de una partitura real. Los tests sintéticos prueban contratos de software, no la exactitud musical.
- El porcentaje publicado en `omr-engine/docs/project-progress.md` es una estimación de madurez funcional, no de precisión. No lo aumentes por agregar infraestructura, tests o candidatos.

## Estado al cierre de esta intervención

- Rama de trabajo: `work/annotation-first-fragment-20261128`.
- Rama base de desarrollo: `feature/omr-propio-palermo`.
- SHA base verificado: `9408a82b44608f1cbf2bfc08b62f7777ebd7d2f6`.
- El SHA base anterior escrito en este archivo (`1288480e562c6a23359f58897d13ec131106fd66`) era dos commits anterior; se comparó con GitHub. Los únicos commits intermedios (`ef38120`, `9408a82`) añadieron este relevo y el enlace desde README, sin modificar el motor. La base actual coincide con el PR #8.
- PR de esta intervención: https://github.com/tuaatest-lgtm/repertorios/pull/9 (draft, abierto, no fusionado).
- PR #8 permanece separado: detector local de barras inclinadas, draft, sin fusionar.
- Se confirmó CI de la fase anterior sobre el HEAD `a1301c13efefe7f42c937db4dfbc2d13439d0f13`: 588 pruebas Python y 4 pruebas del cliente web aprobadas.
- En el turno actual se implementó una herramienta para acotar paquetes de revisión a una página y pentagramas seleccionados. No genera eventos musicales ni ground truth.
- Archivos añadidos: `src/palermo_omr/focused_review.py`, `src/palermo_omr/focused_review_cli.py`, `tests/test_focused_review.py`, `docs/focused-review.md`.
- Archivo modificado: `pyproject.toml` (entrada de consola `palermo-omr-focus-review`) y `README.md` (referencia documental).
- La primera CI del nuevo módulo detectó un fallo en la comprobación de IDs duplicados: 584 aprobadas y 1 fallida. Se corrigió explícitamente la validación. La CI del commit `2f48d1e90fcb9e5ad1e1192ec522212b80720927` pasó con 585 pruebas Python; el cliente web también pasó en esa ejecución. El commit más reciente añade dos pruebas de CLI y requiere la confirmación final de CI antes de dar el PR por validado.
- PDF de referencia disponible en Library: `Clamaré a Dios - Coro.pdf`, SHA-256 `bbf62fa7b3be45585e3d77a7d0b3fe57ab4701ff17c8e821f14dbdc88f64f74c`.
- También está disponible un `analysis.json` histórico de esa partitura, versión 0.3.0. No equivale a una ejecución del HEAD actual ni a una transcripción humana revisada.
- En la imagen original de la primera página se identificó visualmente el primer sistema como dos pentagramas unidos por llave. El análisis histórico enumera esos pentagramas por separado (índices 0 y 1); la selección debe registrarse como región elegida por una persona y no como sistema/parte/voz reconocidos por el motor.
- Se generó fuera del repositorio un paquete de trabajo preliminar `/mnt/data/clamare-first-system-review-draft.json` a partir del `analysis.json` histórico: página 1, pentagramas 0 y 1, 35 candidatos de cabeza y 2 candidatos geométricos de pentagrama. Mantiene todos los candidatos pendientes, `events=[]` y `ground_truth_eligible=false`. Es un paquete manual de inspección, no una ejecución de la CLI nueva ni una anotación humana aprobada.
- Se generó `/mnt/data/clamare-first-system-candidates.png` con la ubicación de los candidatos para revisión visual. Los círculos son propuestas del análisis histórico, no detecciones confirmadas.
- No se ha producido todavía un manifiesto de eventos musicales humanos ni se ha calculado precisión/recall. No aumentar el porcentaje de progreso.

## Encargo del siguiente turno

**Aplicar la nueva herramienta al primer sistema visual de `Clamaré a Dios - Coro.pdf` y preparar un paquete real de revisión pendiente para sus dos pentagramas.**

Instrucciones ejecutables:
1. Verificar el HEAD actual de la rama `work/annotation-first-fragment-20261128`, el SHA de PR #9 y la CI asociada. No continuar sobre un SHA distinto sin inspeccionar su diff.
2. Descargar/materializar desde Library el PDF `Clamaré a Dios - Coro.pdf` y el `analysis.json` histórico. Verificar que el SHA-256 del PDF sea exactamente `bbf62fa7b3be45585e3d77a7d0b3fe57ab4701ff17c8e821f14dbdc88f64f74`.
3. No tratar el análisis histórico como salida del HEAD actual. Si es posible ejecutar el motor actual, generar una salida nueva a 300 DPI; si no, documentar que el paquete usa el análisis histórico y conservar esa procedencia.
4. Crear el paquete completo con `palermo-omr-dataset prepare-review` y después extraer el fragmento con:
   `palermo-omr-focus-review <paquete> --page 1 --staff-indices 0,1 --label "Primer sistema visual, página 1" --output <destino>`.
5. Verificar en el PDF que esos dos pentagramas son la pareja unida por llave del primer sistema. El paquete debe mantener `review_status=pending`, `annotation_status=draft`, `events=[]` y `ground_truth_eligible=false`. No convertir candidatos en ScoreEvent.
6. Inspeccionar los overlays y corregir únicamente errores de integridad o selección de candidatos que se puedan demostrar. No asignar notas, duraciones, voces o compases por intuición.
7. Si el flujo funciona, dejar el paquete como artefacto de revisión descargable y documentar los IDs pendientes. Si no funciona por incompatibilidad del análisis histórico, volver a ejecutar el motor actual o dejar descrito el bloqueo exacto.
8. Ejecutar pruebas específicas, suite completa y CI final. Actualizar este archivo con SHA base/final, resultados observados y la siguiente tarea acotada.
9. No modificar `main`, `index.html` ni Sonoro; no fusionar ni desplegar.

## Instrucción exacta para quien toma el turno
Trabaja como responsable técnico del motor OMR propio de Palermo Music. Empieza verificando la rama y el SHA; lee `AGENTS.md` y este archivo; inspecciona primero lo que ya existe antes de programar. Ejecuta el encargo del siguiente turno con el alcance limitado y los criterios de aceptación indicados. No inventes resultados ni completes datos musicales por intuición. Mantén la polifonía real y la aritmética temporal exacta. Al terminar, actualiza este mismo archivo con el estado comprobado y deja una sola tarea siguiente, concreta y ejecutable para el próximo participante. No hagas push, merge, despliegue ni integración con Sonoro sin autorización expresa.

## Registro de turnos
- Turno inicial de relevo: reglas generales añadidas en `AGENTS.md`; instrucción vigente creada aquí. El commit de este documento y el CI asociado quedan pendientes de verificación al cerrar la operación.
