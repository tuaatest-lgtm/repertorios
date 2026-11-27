# Evaluación de eventos de partitura

`event_evaluation.py` compara eventos producidos por el motor con eventos
anotados por una persona. Es la base para medir calidad musical, en lugar de
considerar que pasar pruebas unitarias equivale a reconocer bien una partitura.

## Modelo de anotación

Cada evento contiene página, índice de pentagrama, compás, inicio en negras,
tipo (`note` o `rest`), conjunto de alturas MIDI, duración en negras y voz.
Las anotaciones humanas deben tener esos campos completos. En predicciones,
el inicio, la altura, la duración o la voz pueden ser desconocidos; esos
desconocidos no se rellenan por inferencia.

Los acordes se representan como un solo evento con varias alturas MIDI. Los
silencios usan `event_type="rest"` y `pitches_midi=()`.

## Emparejamiento y métricas

Los eventos se emparejan uno a uno cuando coinciden página, pentagrama y
compás, y sus inicios están dentro de `onset_tolerance_quarters` (por defecto
1/8 de negra). El emparejamiento maximiza el número de pares válidos y luego
prefiere el menor error temporal.

El emparejamiento no usa tipo, alturas, duración ni voz. Así, esos errores se
miden como errores de clasificación y no quedan ocultos como eventos ausentes.
El informe separa:

- precisión, recall y F1 de detección de eventos;
- exactitud de tipo de evento;
- exactitud de conjunto completo de alturas (incluidos acordes), calculada solo sobre eventos cuya referencia es una nota; los silencios no tienen altura y no inflan esta métrica;
- exactitud de duración;
- exactitud de asignación de voz;
- error medio absoluto del inicio.

Una predicción sin inicio conocido no se empareja: cuenta como predicción no
localizada y la anotación correspondiente permanece sin detectar. No se
inventan inicios ni se asigna una coincidencia por cercanía visual.

## Alcance y limitaciones

El evaluador no genera anotaciones, no reconoce símbolos, no normaliza
enarmonías y no evalúa todavía ligaduras como una métrica independiente.
Los índices de pentagrama y compás deben estar alineados entre anotación y
predicción. La tolerancia de inicio debe elegirse y documentarse por corpus.

Las pruebas incluidas son sintéticas y validan el evaluador, no la precisión
del OMR. Para conocer la precisión real hace falta un conjunto de partituras
con ground truth musical revisado por personas y una política consistente de
numeración de pentagramas, compases, voces y alturas.
