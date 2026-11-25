# Palermo OMR Engine (desarrollo propio)

Motor OMR independiente para Palermo Music. Esta iteración implementa entrada PDF, preprocesamiento de páginas, detección geométrica inicial de pentagramas y propuestas de cabezas de nota.

**Estado:** prototipo geométrico 0.3.0. Incluye candidatos de cabezas, conversión de posición diatónica cuando la clave ya es conocida, análisis rítmico preliminar y candidatos de puntillos, silencios, barras e intervalos de compás. Todo resultado requiere validación; no es una transcripción musical completa. No está integrado con el reproductor ni desplegado como servicio.

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
- grupos geométricos de cinco líneas;
- regiones propuestas como cabezas de nota;
- posición diatónica relativa a la línea inferior del pentagrama (sin asignar todavía una letra o altura absoluta);
- puntuaciones heurísticas de confianza;
- hipótesis de relleno, plicas y barras horizontales de agrupación;
- candidatos de puntillos, formas que podrían corresponder a silencios y trazos verticales que podrían ser barras de compás;
- agrupaciones de barras aproximadamente alineadas entre pentagramas;
- intervalos geométricos entre barras consecutivas del mismo pentagrama.

## Limitaciones conocidas

- Los trazos de barras, texto, ligaduras y otros símbolos pueden producir falsos positivos.
- Las cabezas de nota unidas a plicas o atravesadas por líneas pueden fragmentarse.
- La posición diatónica no equivale a una nota identificada: falta reconocer la clave y aplicar armadura y alteraciones desde la imagen.
- El análisis rítmico no interpreta todavía de forma fiable barras compartidas, grupos irregulares, ligaduras ni voces.
- Los candidatos a barra no determinan todavía sistemas ni límites métricos definitivos.
- Los intervalos entre barras no incluyen los bordes externos que no fueron observados y no son compases musicales validados.
- Las partituras complejas deben evaluarse con ejemplos reales y anotaciones de referencia.
- No se debe enviar esta salida al reproductor.

## Próximas fases

1. Evaluación y calibración con partituras reales vectoriales y escaneadas.
2. Agrupación robusta de sistemas y mejora de límites de compás, incluyendo barras dobles y saltos de sistema.
3. Clasificación robusta de símbolos: claves, armaduras, figuras, silencios, puntillos y ligaduras.
4. Interpretación temporal polifónica y exportación MusicXML.
5. Revisión visual humana y, solo tras aviso y aprobación, diseño del adaptador aislado hacia el motor Sonoro de Palermo.

## Validación métrica preliminar

Se añadió `palermo_omr.measure_validation`, una capa matemática independiente que compara duraciones ya interpretadas con el valor esperado del indicador de compás. Distingue compases completos, incompletos, excedidos y posibles anacrusas. No reconoce figuras desde la imagen y todavía no se conecta al CLI ni al reproductor. Consulta `docs/measure-validation.md`.

## Geometría de compases

Consulta `docs/measure-layout.md` para conocer cómo se detectan y agrupan las barras candidatas y qué limitaciones tienen los intervalos resultantes.
