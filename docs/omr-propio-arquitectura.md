# Palermo Music — arquitectura del OMR propio

## Objetivo

Crear un sistema de reconocimiento óptico musical desarrollado para Palermo Music. El sistema no dependerá de Audiveris ni de una API externa de reconocimiento. El repositorio almacenará el código fuente; la ejecución en producción requerirá infraestructura administrada por Palermo.

## Límites de la primera iteración

La versión 0.1.0 es una base de investigación ejecutable:
- abre PDFs no cifrados;
- renderiza cada página;
- binariza imágenes;
- detecta trazos horizontales largos;
- propone grupos geométricos de cinco líneas;
- exporta un informe JSON.

Todavía no reconoce símbolos, alturas, ritmos, voces ni MusicXML. No se debe conectar al reproductor.

## Arquitectura objetivo

1. **Entrada PDF:** validación, renderizado por página y metadatos.
2. **Normalización de imagen:** escala, inclinación, ruido, contraste y limpieza.
3. **Análisis de página:** detección de sistemas, pentagramas, barras y regiones.
4. **Reconocimiento visual:** claves, cabezas de nota, plicas, corchetes, silencios, alteraciones, articulaciones y texto.
5. **Interpretación musical:** altura según clave/armadura/alteraciones, duración, voz, compás, simultaneidad y continuidad entre sistemas.
6. **Estructura de obra:** repeticiones, D.C., D.S., Segno, Coda, Fine y cambios de tempo.
7. **Representación intermedia:** eventos musicales tipados con posiciones racionales en el tiempo.
8. **Exportación:** MusicXML y formato interno de eventos Palermo.
9. **Revisión humana:** interfaz para corregir incertidumbres antes de reproducir.
10. **Integración aislada:** adaptador hacia el motor Sonoro existente, sin reemplazarlo.

## Principios no negociables

- Polifonía real: eventos simultáneos con duraciones independientes.
- No confundir pentagramas de piano (mano derecha/izquierda) con voces SATB.
- Conservar alteraciones, ligaduras, silencios, voces y cambios de compás.
- Separar reconocimiento visual de interpretación musical.
- Registrar confianza y procedencia de cada símbolo detectado.
- No ejecutar automáticamente una partitura con errores de reconocimiento no revisados.
- Mantener intacto el `index.html` funcional mientras no exista una integración probada.

## Estrategia de validación

Usar partituras de prueba con variedad de:
- PDF vectorial y PDF escaneado;
- resoluciones, inclinaciones y contraste;
- piano, coro SATB y partituras instrumentales;
- compases simples y compuestos;
- acordes, voces simultáneas, ligaduras, puntillos y silencios;
- saltos y repeticiones.

Medir por separado: detección de pentagramas, reconocimiento de símbolos, altura, duración, asignación de voz, reconstrucción temporal y fidelidad MusicXML.

## Siguiente hito

Evaluar el detector geométrico con el PDF piloto de Palermo. Ajustar la segmentación de sistemas y pentagramas; después crear un conjunto de verdad-terreno anotado para entrenar y medir el reconocedor de símbolos. No declarar precisión global hasta medirla sobre partituras no usadas durante el desarrollo.
