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
