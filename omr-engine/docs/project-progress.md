# Estado y porcentaje de avance del motor OMR Palermo

**Corte:** 26 de noviembre de 2026  
**Rama:** `feature/omr-propio-palermo`  
**Objetivo medido:** motor OMR propio, capaz de convertir partituras en eventos musicales polifónicos estructurados y verificables.  
**Fuera del alcance de este porcentaje:** integración con Sonoro, publicación, despliegue o cambios al reproductor. Esas acciones requieren autorización independiente.

## Indicador general

- **Avance estimado: 48%**
- **Trabajo restante estimado: 52%**

El porcentaje es una estimación de madurez por hitos ponderados, no un porcentaje de código escrito ni una medición de precisión musical. Se redondea al entero más cercano. Una etapa no se considera completa solo porque tenga módulos o pruebas unitarias.

## Desglose ponderado

| Etapa | Peso | Madurez estimada | Aporte |
|---|---:|---:|---:|
| Imagen, pentagramas y candidatos geométricos | 20% | 60% | 12,00 |
| Interpretación de notación, alturas y ritmo | 20% | 40% | 8,00 |
| Estructura de partitura, sistemas, partes y voces | 15% | 55% | 8,25 |
| Eventos, polifonía y línea temporal | 15% | 70% | 10,50 |
| Revisión humana y ensamblaje musical | 15% | 35% | 5,25 |
| Evaluación contra anotaciones humanas y corpus real | 10% | 30% | 3,00 |
| Orquestación CLI y preparación integral | 5% | 20% | 1,00 |
| **Total ponderado** | **100%** |  | **48,00% = 48%** |

## Qué respalda cada estimación

### 1. Imagen y geometría — 60%

Existe renderizado de PDF, análisis de imagen, candidatos de pentagramas, cabezas de nota, cabezas huecas, plicas/vigas, barras, agrupaciones y regiones. Las limitaciones de escaneos y falsos positivos siguen abiertas; falta calibrar detectores con anotaciones humanas de imágenes reales.

### 2. Interpretación musical — 40%

Hay conversión de posición diatónica a MIDI cuando la clave está dada, manejo parcial de alteraciones, candidatos de duración, puntillos, silencios y arcos. Aún no se reconocen de forma fiable y completa claves, armaduras, compases, articulaciones, tresillos, ligaduras, silencios y grafías complejas desde imagen.

### 3. Estructura de partitura y voces — 55%

Existen modelos para páginas, sistemas, pentagramas, partes, voces, regiones de compás, continuidad entre páginas y evidencia para revisión de identidad. Hay extracción de algunas etiquetas impresas y candidatos de agrupación. Falta resolver automáticamente y validar de forma fiable llaves, corchetes, instrumentos, piano/manos y asignaciones SATB.

### 4. Eventos y polifonía — 70%

Hay agrupación candidata de notas/acordes, capas potenciales en un pentagrama, secuencias temporales por voz y líneas temporales de varias voces con duraciones independientes. También hay candidatos de continuidad melódica. Falta extraer y agrupar eventos completos desde imágenes reales con precisión suficiente.

### 5. Revisión humana y ensamblaje — 35%

Existen compuertas explícitas para confirmar grupos de notas, asignaciones de voz, ligaduras y silencios. Aún no existe una interfaz de revisión integrada ni una sesión persistente que reúna todas las decisiones en un flujo de trabajo completo.

### 6. Evaluación y corpus — 30%

Hay evaluación geométrica de regiones de texto y un evaluador para comparar eventos musicales con anotaciones humanas. También existe un formato reproducible de corpus que valida huellas SHA-256, particiones sin duplicados, eventos completos y estado de revisión. Las pruebas actuales siguen siendo sintéticas: todavía falta incorporar partituras reales anotadas y publicar métricas de precisión/recall.

### 7. CLI e integración de etapas — 20%

Existe CLI y visualización de análisis parciales, pero los módulos nuevos de revisión, ligaduras, silencios y evaluación no conforman todavía un proceso integral de punta a punta. No hay integración con Sonoro.

## Hitos para el trabajo restante

1. Incorporar y anotar un conjunto pequeño de partituras reales representativas usando el formato validado: coral SATB, piano, páginas múltiples, acordes, voces internas, silencios y ligaduras.
2. Medir los detectores existentes contra ese conjunto y corregir los errores de mayor impacto.
3. Construir un flujo de revisión humana persistente para pentagramas, voces, cabezas, acordes, silencios, duraciones y ligaduras.
4. Completar interpretación de notación y continuidad entre sistemas/páginas sin inventar datos faltantes.
5. Conectar los módulos validados en una canalización OMR integral y producir MusicXML/eventos estructurados solo cuando la confianza y revisión lo permitan.
6. Ejecutar regresiones con partituras no usadas durante el ajuste y documentar métricas por tipo de partitura.

## Reglas de actualización

- Actualizar este desglose cuando se cierre un hito verificable.
- Citar el commit y la ejecución CI correspondiente cuando se informe que una etapa pasó.
- Separar siempre pruebas sintéticas de validación en partituras reales.
- No incrementar el porcentaje por documentación o cantidad de líneas de código solamente. La infraestructura de corpus eleva la preparación de evaluación, pero no equivale a tener partituras reales anotadas.
- La integración con Sonoro seguirá fuera de alcance hasta recibir autorización expresa.
