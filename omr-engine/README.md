# Palermo OMR Engine (desarrollo propio)

Motor OMR independiente para Palermo Music. Esta iteración implementa entrada PDF, preprocesamiento de páginas, detección geométrica inicial de pentagramas y propuestas de cabezas de nota.

**Estado:** prototipo geométrico 0.3.0. Incluye candidatos de cabezas, conversión de posición diatónica cuando la clave ya es conocida, análisis rítmico preliminar, grupos candidatos de barras compartidas, interpretación rítmica candidata y candidatos de puntillos, silencios, barras e intervalos de compás. Todo resultado requiere validación; no es una transcripción musical completa. No está integrado con el reproductor ni desplegado como servicio.

## Requisitos

- Python 3.11 o superior.
- Dependencias instalables con `pip install -e ".[dev]"`.

## Uso

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -e ".[dev]"
palermo-omr "partitura.pdf" --output "./omr-output" --dpi 300
```

El comando genera una imagen binarizada por página y un archivo `analysis.json` con:

- líneas horizontales candidatas;
- grupos geométricos de cinco líneas;\n- duración rítmica candidata por cabeza, con referencia al grupo de barras compartidas y estado explícito de ambigüedad o evidencia insuficiente;
- regiones propuestas como cabezas de nota;
- candidatos separados de cabezas huecas, guardados en `hollow_notehead_candidates` y no usados todavía para interpretar ritmo;
- posición diatónica relativa a la línea inferior del pentagrama (sin asignar todavía una letra o altura absoluta);
- puntuaciones heurísticas de confianza;
- hipótesis de relleno, plicas y barras horizontales de agrupación;
- candidatos de puntillos, formas que podrían corresponder a silencios (con sugerencias geométricas de familias de redonda/blanca y formas verticales), arcos candidatos a ligaduras y trazos verticales que podrían ser barras de compás;
- sistemas geométricos candidatos, separados por grandes saltos verticales entre pentagramas;
- agrupaciones de barras aproximadamente alineadas dentro de cada sistema candidato;
- clasificación visual preliminar de barras simples, dobles y finales candidatas;
- intervalos geométricos entre barras consecutivas del mismo pentagrama.

## Limitaciones conocidas

- Los trazos de barras, texto, ligaduras y otros símbolos pueden producir falsos positivos.
- Las cabezas de nota unidas a plicas o atravesadas por líneas pueden fragmentarse.
- La recuperación de dos cabezas desplazadas que se tocan aplica filtros de compacidad para no confundir vigas diagonales con notas; sigue siendo una hipótesis geométrica y requiere validación visual. Consulta `docs/notehead-detection.md`.
- La posición diatónica no equivale a una nota identificada: falta reconocer la clave y aplicar armadura y alteraciones desde la imagen.
- La sugerencia de familia de silencio es de confianza baja y no distingue todavía de forma fiable todos los tipos; cuartos, corcheas, semicorcheas, silencios compuestos y símbolos fragmentados requieren un clasificador más robusto.
- Los arcos detectados son candidatos visuales: no distinguen ligaduras de prolongación (tie) de ligaduras de expresión (slur), ni se enlazan todavía con cabezas de nota.
- Los grupos de barras compartidas son candidatos geométricos: requieren un trazo horizontal y plicas compatibles, pero no confirman por sí solos corcheas, semicorcheas, grupos irregulares, dirección de lectura ni voces. El análisis rítmico global sigue sin estar validado.
- La agrupación de sistemas es geométrica y heurística: no reconoce llaves, brackets, piano, coro SATB ni la función de cada pentagrama.
- La clasificación simple/doble/final es heurística y no reconoce aún puntos de repetición ni confirma la función musical de una barra.
- Los intervalos entre barras no incluyen los bordes externos que no fueron observados y no son compases musicales validados.
- Las partituras complejas deben evaluarse con ejemplos reales y anotaciones de referencia.
- No se debe enviar esta salida al reproductor.

## Próximas fases

1. Evaluación y calibración con partituras reales vectoriales y escaneadas.
2. Validar sistemas y barras simples/dobles/finales en partituras reales; después abordar puntos de repetición, saltos de sistema y continuidad entre páginas.
3. Calibrar los candidatos rítmicos con partituras reales anotadas y resolver grupos irregulares, barras parciales, ligaduras y puntillos.\n4. Clasificación robusta de símbolos: claves, armaduras, figuras y silencios.
5. Interpretación temporal polifónica y exportación MusicXML.
5. Revisión visual humana y, solo tras aviso y aprobación, diseño del adaptador aislado hacia el motor Sonoro de Palermo.

## Aritmética exacta de duraciones

Se añadió `palermo_omr.duration_math` para calcular valores de figuras, puntillos simples y múltiples, y sumar duraciones de notas cuya ligadura de prolongación ya haya sido confirmada. Utiliza fracciones exactas para evitar deriva de redondeo. No reconoce símbolos ni decide ligaduras a partir de imágenes; consulta `docs/duration-math.md`.

## Validación métrica preliminar

Se añadió `palermo_omr.measure_validation`, una capa matemática independiente que compara duraciones ya interpretadas con el valor esperado del indicador de compás. Distingue compases completos, incompletos, excedidos y posibles anacrusas. No reconoce figuras desde la imagen y todavía no se conecta al CLI ni al reproductor. Consulta `docs/measure-validation.md`.

## Geometría de compases

Consulta `docs/measure-layout.md` para conocer cómo se detectan y agrupan las barras candidatas y qué limitaciones tienen los intervalos resultantes.


## Inferencia de una duración faltante

Se añadió `palermo_omr.duration_completion` para calcular el residuo métrico de un compás con fracciones exactas. Solo asigna ese residuo a una nota cuando exactamente un evento de la misma voz y compás permanece sin duración; si faltan varios, informa el residuo sin inventar cómo repartirlo. Requiere que silencios, puntillos, tresillos y ligaduras estén contabilizados previamente. No está conectado todavía al análisis de imágenes ni al CLI. Consulta `docs/duration-completion.md`.


## Balance rítmico por voz y compás

Se añadió `palermo_omr.voice_measure` para calcular el balance de cada voz o flujo rítmico por separado. Rechaza mezclar voces o compases, contabiliza silencios y solo asigna el residuo si queda exactamente un evento sin duración. No descubre todavía la voz ni el compás desde la imagen. Consulta `docs/voice-measure.md`.
