# Análisis rítmico preliminar

El módulo `palermo_omr.rhythm` propone hipótesis geométricas sobre el relleno de las cabezas, las plicas, su dirección, las barras cercanas y una duración base tentativa.

El módulo `palermo_omr.rhythm_symbols` añade:
- candidatos de puntillos de aumento próximos a cabezas de nota;
- regiones compactas que podrían corresponder a símbolos de silencio.

## Límites actuales

Nada de lo anterior equivale a una lectura musical confirmada. Un puntillo puede confundirse con ruido o texto; un candidato de silencio puede ser una articulación, letra, fragmento de símbolo o artefacto. Las barras cercanas pueden pertenecer a otra nota o ser trazos de la página. La agrupación compartida ahora exige además que cada barra candidata cruce una de las posiciones geométricas esperadas de la plica; esto reduce asociaciones por mera proximidad, pero no demuestra todavía la conexión musical ni resuelve vigas parciales.

Todavía no se reconocen de forma fiable:
- tipo y duración exacta de cada silencio;
- ligaduras de prolongación y de expresión;
- agrupaciones de barras compartidas y segmentos parciales asociados a una sola plica; los segmentos parciales se conservan con menor confianza porque pueden confundirse con banderas u otros trazos;
- puntillos dobles y su efecto temporal;
- tresillos, dosillos y otros grupos irregulares;
- valores ligados entre compases;
- voces simultáneas ni alineación temporal completa.

Los resultados incluyen advertencias y puntuaciones heurísticas. No deben enviarse al motor Sonoro como eventos definitivos.

## Próxima ampliación

Evaluar y calibrar con partituras reales anotadas la detección de cabezas, plicas y grupos de una a cuatro barras; distinguir barras parciales y grupos irregulares; reconocer silencios por clase; separar ligaduras de expresión y prolongación; reconstruir duraciones y comprobarlas contra métrica y compás.
