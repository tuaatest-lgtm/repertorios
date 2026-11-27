# Análisis rítmico preliminar

El módulo `palermo_omr.rhythm` propone hipótesis geométricas sobre el relleno de las cabezas, las plicas, su dirección, las barras cercanas y una duración base tentativa.

El módulo `palermo_omr.rhythm_symbols` añade:
- candidatos de puntillos de aumento próximos a cabezas de nota;
- regiones compactas que podrían corresponder a símbolos de silencio; el detector excluye componentes fuera del interior del pentagrama, formas demasiado estrechas y regiones que se superponen con cabezas de nota detectadas.

## Límites actuales

Nada de lo anterior equivale a una lectura musical confirmada. Un puntillo puede confundirse con ruido o texto; incluso con los filtros geométricos, un candidato de silencio puede ser una articulación, letra, fragmento de símbolo o artefacto. La exclusión de cabezas detectadas reduce duplicados, pero puede omitir un silencio mal segmentado que se solape con una cabeza falsa. Las barras cercanas pueden pertenecer a otra nota o ser trazos de la página. La agrupación compartida ahora exige además que cada barra candidata cruce una de las posiciones geométricas esperadas de la plica; esto reduce asociaciones por mera proximidad. La asociación también comprueba continuidad de tinta entre la plica y la barra, tolerando como máximo un píxel aislado sin tinta; un hueco mayor se rechaza. Esta comprobación es rasterizada y no demuestra por sí sola la conexión musical ni resuelve todas las formas de vigas parciales.

Todavía no se reconocen de forma fiable:
- tipo y duración exacta de cada silencio;
- ligaduras de prolongación y de expresión;
- agrupaciones de barras compartidas y segmentos parciales asociados a una sola plica; los segmentos parciales se conservan con menor confianza porque pueden confundirse con banderas u otros trazos; además, deben mostrar continuidad raster con la plica;
- puntillos dobles y su efecto temporal;
- tresillos, dosillos y otros grupos irregulares;
- valores ligados entre compases;
- voces simultáneas ni alineación temporal completa.

Los resultados incluyen advertencias y puntuaciones heurísticas. No deben enviarse al motor Sonoro como eventos definitivos.

## Próxima ampliación

Evaluar y calibrar con partituras reales anotadas la detección de cabezas, plicas y grupos de una a cuatro barras; distinguir barras parciales y grupos irregulares; reconocer silencios por clase; separar ligaduras de expresión y prolongación; reconstruir duraciones y comprobarlas contra métrica y compás.
