# Corpus de referencia Palermo OMR

Este directorio contiene metadatos del corpus. Los PDF originales no se
incluyen ni se redistribuyen desde este repositorio.

## Partitura registrada

- ID: `clamare-a-dios-coro`
- Archivo de origen: `Clamaré a Dios - Coro.pdf`
- SHA-256: `bbf62fa7b3be45585e3d77a7d0b3fe57ab4701ff17c8e821f14dbdc88f64f74c`
- Páginas: 3
- Partición prevista: `train`
- Estado: `draft`, sin eventos anotados.

El hash permite comprobar que el PDF usado para anotar es exactamente el
mismo archivo. El registro no declara que se hayan anotado ni validado notas,
voces, alturas, ritmos, compases o instrumentos.

## Próximos pasos

1. Obtener el PDF original localmente y verificar su SHA-256.
2. Ejecutar el análisis visual Palermo y guardar `analysis.json` junto a sus
   overlays.
3. Preparar el paquete de revisión visual con `prepare-review`.
4. Contrastar candidatos con cada página y completar los eventos musicales
   manualmente, con voz, compás, ataque, altura y duración explícitos.
5. Importar los eventos al manifiesto, validar y aprobar tras revisión humana.
6. Reservar partituras distintas para validation y test; nunca duplicar el
   mismo PDF entre particiones.

El manifiesto `manifest.json` se mantiene como borrador hasta completar y
revisar las anotaciones.

## Evaluación geométrica disponible

Se ejecutó el motor sobre el PDF original de 3 páginas y se contrastaron los
centros de candidatos de cabeza con el glifo vectorial `œ` de la fuente
`RepriseStd` embebida en ese mismo PDF. El hash coincide con el registrado
arriba. A 300 DPI y con tolerancia de 3 puntos PDF, el resultado fue:

- 569 candidatos; 534 glifos de referencia.
- 494 correspondencias 1:1, 75 falsos positivos y 40 falsos negativos.
- Precisión geométrica: 86.82%; recall: 92.51%; F1: 89.57%.
- Error medio entre centros emparejados: 1.75 puntos PDF.

El detalle reproducible está en
`clamare-notehead-geometry-evaluation.json`. Esta prueba solo mide localización
de cabezas en un PDF digital cuya fuente/glyph map pudo identificarse. No mide
transcripción musical, alturas, ritmo, duración, silencios, voces ni polifonía.
Por eso `manifest.json` permanece en `draft`, sin eventos aprobados, y esta
métrica no debe interpretarse como precisión OMR global.
