# Palermo OMR Engine (desarrollo propio)

Motor OMR independiente para Palermo Music. Esta iteración implementa entrada PDF, preprocesamiento de páginas, detección geométrica inicial de pentagramas y propuestas de cabezas de nota.

**Estado:** prototipo geométrico 0.2.0. Los resultados son candidatos visuales y requieren validación. No reconoce todavía nombres de notas, claves, armaduras, duraciones, voces ni estructura musical. No está integrado con el reproductor ni desplegado como servicio.

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
- puntuaciones heurísticas de confianza.

## Limitaciones conocidas

- Los trazos de barras, texto, ligaduras y otros símbolos pueden producir falsos positivos.
- Las cabezas de nota unidas a plicas o atravesadas por líneas pueden fragmentarse.
- La posición diatónica no equivale a una nota identificada: falta reconocer la clave y aplicar armadura y alteraciones.
- Las partituras complejas deben evaluarse con ejemplos reales y anotaciones de referencia.
- No se debe enviar esta salida al reproductor.

## Próximas fases

1. Evaluación y calibración con partituras reales vectoriales y escaneadas.
2. Detección de sistemas, compases y regiones musicales.
3. Clasificación de símbolos y reconocimiento de claves, armaduras y figuras.
4. Interpretación temporal polifónica y exportación MusicXML.
5. Revisión visual humana y adaptador aislado hacia el motor Sonoro de Palermo.
