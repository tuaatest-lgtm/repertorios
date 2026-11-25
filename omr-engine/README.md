# Palermo OMR Engine (desarrollo propio)

Motor OMR independiente para Palermo Music. Esta primera base implementa únicamente la entrada PDF, el preprocesamiento de páginas y la detección geométrica inicial de líneas de pentagrama.

**Estado:** prototipo de infraestructura; todavía no reconoce notas, claves, figuras, silencios, armaduras ni estructura musical. No está integrado con el reproductor ni desplegado como servicio.

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

El comando genera una carpeta con una imagen binarizada por página y un archivo `analysis.json` con las líneas horizontales candidatas y los grupos de cinco líneas detectados.

## Próximas fases

1. Evaluación con partituras reales vectoriales y escaneadas.
2. Detección de sistemas, compases y regiones musicales.
3. Reconocimiento de símbolos con modelos entrenados y reglas musicales.
4. Reconstrucción temporal polifónica y exportación MusicXML.
5. Adaptador aislado hacia el motor Sonoro de Palermo.

La salida de esta fase es geométrica y no debe enviarse todavía al reproductor.
