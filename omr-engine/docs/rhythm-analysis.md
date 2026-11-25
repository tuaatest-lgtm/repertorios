# Análisis rítmico preliminar

El módulo `palermo_omr.rhythm` recibe candidatos geométricos de cabezas de nota y calcula hipótesis sobre:

- cabeza rellena, hueca o ambigua;
- presencia y dirección de una plica;
- segmentos horizontales cortos que podrían ser barras;
- valor base tentativo: redonda, blanca, negra, corchea, semicorchea, fusa o semifusa.

## Límites actuales

Esta etapa no es todavía un reconocedor de ritmo fiable. Las líneas del pentagrama, las plicas, las barras, los trazos de articulación y los símbolos vecinos pueden confundirse. La clasificación se acompaña de confianza y advertencias.

Todavía no se reconocen de forma fiable:

- silencios;
- puntillos;
- ligaduras de prolongación y de expresión;
- barras compartidas entre varias notas;
- grupos irregulares (tresillos, dosillos, etc.);
- valores ligados entre compases;
- voces simultáneas ni alineación temporal completa.

El conteo de barras es exploratorio y puede confundir trazos próximos. No se deben enviar estas hipótesis al motor Sonoro como eventos definitivos. Antes se necesita validación con partituras reales y revisión humana.

## Próxima ampliación

Separar detección de plicas, barras y banderas; reconocer silencios y puntillos; reconstruir grupos rítmicos y duraciones; luego evaluar compases completos con restricciones métricas.
