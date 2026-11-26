# Detección geométrica de cabezas de nota

El detector de cabezas rellenas usa una apertura morfológica elíptica para recuperar el núcleo ovalado de una nota aunque esté conectado a una plica o a una barra.

## Cabezas desplazadas que se tocan

Cuando una región puede contener dos cabezas de un acorde de segunda, el detector busca dos máximos de la transformada de distancia y verifica que sus centros coincidan aproximadamente con posiciones diatónicas del pentagrama. Las dos salidas se conservan como candidatos separados y su confianza se limita a 0.72.

La separación solo se intenta sobre componentes compactos. Se descartan regiones cuyo aspecto de caja supera 2.2 o cuya elongación principal supera 4.5. Estos límites ayudan a evitar que una barra diagonal larga produzca dos máximos locales que parezcan cabezas.

## Pruebas de regresión

- Una pareja sintética de cabezas rellenas, desplazadas y en contacto debe producir dos candidatos.
- Una viga diagonal gruesa conectada a plicas no debe producir candidatos de cabezas por el mecanismo de separación.

## Límites

Estas reglas son filtros geométricos, no un clasificador musical. Los candidatos recuperados requieren revisión visual y anotación de referencia antes de medir precisión y recall. No se reconocen por este medio las alturas absolutas, la voz, la duración ni la función musical de las notas.

## Candidatos de cabezas huecas

Se añadió una búsqueda independiente de contornos con hueco interior. Primero elimina líneas horizontales largas del pentagrama y cierra interrupciones pequeñas; luego evalúa el tamaño del hueco, el área del contorno exterior, la circularidad del hueco (mínimo 0.66) y la alineación vertical con posiciones del pentagrama. Fragmentos de un mismo hueco se deduplican si sus centros casi coinciden. La prueba de regresión incluye dos cabezas rellenas próximas para evitar interpretar el espacio entre ellas como una cabeza hueca.

Los candidatos huecos se guardan por separado en `hollow_notehead_candidates` dentro de `analysis.json`. No se mezclan todavía con las cabezas rellenas ni se usan para interpretar ritmo: las formas circulares de claves, silencios, letras y otros símbolos pueden contener huecos similares. La puntuación está limitada a 0.68 y todos los resultados requieren revisión visual.

## Diferencia entre blanca y redonda

La cabeza hueca se detecta una sola vez, sin clasificarla todavía como blanca o redonda. Después, el análisis rítmico busca la plica:

- Cabeza hueca con plica: propone `half` (blanca).
- Cabeza hueca sin plica: propone `whole` (redonda).

El CLI conserva esta interpretación en `hollow_rhythm_candidates`, separada de las figuras de cabeza rellena. La presencia o ausencia de plica también es una hipótesis visual: una plica tenue, tapada o cortada puede causar errores. La propuesta no se considera duración confirmada.


### Acordes con cabezas huecas

La revisión de la partitura de validación mostró que algunos acordes con cabezas huecas apiladas no se recuperan completos. Los intentos de corregirlo solo estrechando la deduplicación no superaron una prueba sintética representativa, por lo que esa modificación se retiró. La recuperación de acordes huecos queda como limitación conocida y requiere un método de separación de contornos más robusto antes de considerarse resuelta.

#### Pruebas sintéticas de acordes huecos

Se añadieron pruebas para comprobar que el detector conserva los huecos interiores como candidatos distintos cuando dos o tres cabezas comparten una plica y un contorno exterior. También se cubrió un acorde de segundas, donde las cabezas alternan su desplazamiento horizontal para no superponerse.

Estas pruebas confirman el comportamiento en geometrías sintéticas controladas; **no demuestran que todos los acordes de partituras reales estén recuperados**. La revisión de la partitura de 20 páginas sigue mostrando casos que requieren inspección visual y una validación de cobertura con anotación manual.

