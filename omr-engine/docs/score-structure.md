# Modelo de estructura de partitura

El módulo `score_structure.py` define un modelo de datos validable para separar la geometría de la página de la organización musical.

## Entidades

- **Sistema:** conjunto de pentagramas que se leen como una unidad visual en una página.
- **Pentagrama:** región de cinco líneas detectada en la imagen.
- **Parte:** instrumento o grupo vocal (por ejemplo, piano o coro).
- **Voz/flujo:** secuencia musical independiente dentro de una parte. En piano puede representar un flujo instrumental que usa ambos pentagramas; en SATB puede representar soprano, alto, tenor o bajo.
- **Asignación de pentagrama:** relación explícita entre un pentagrama, una parte y, cuando se conoce, una o más voces.
- **Región de compás:** intervalo horizontal de un compás dentro de un pentagrama y sistema concretos.

## Reglas de seguridad estructural

- Las asignaciones admiten los estados `unassigned`, `proposed`, `confirmed` y `ambiguous`.
- Una asignación no resuelta no puede fijar una parte ni voces.
- Una asignación confirmada requiere una parte existente.
- Las voces asignadas deben pertenecer a la parte indicada.
- Un pentagrama no puede pertenecer a dos sistemas de la misma página.
- Una región de compás debe apuntar al pentagrama y sistema que realmente la contienen.
- Dos pentagramas pueden pertenecer a la misma parte y compartir un flujo, como las dos manos de piano.
- Varias voces pueden asociarse a un pentagrama cuando la notación lo requiera; no se presupone una relación uno-a-uno.

## Límites actuales

Este módulo **no detecta** sistemas, llaves, partes, voces ni compases en imágenes. Tampoco decide automáticamente piano frente a coro SATB. Recibe entidades y relaciones propuestas por etapas posteriores o por revisión humana y valida su coherencia. La detección geométrica existente en `measure_layout.py` sigue siendo una fuente de candidatos, no una asignación musical confirmada.

El modelo actual representa una página. La continuidad de sistemas y partes entre páginas, los identificadores globales del documento y la numeración musical definitiva serán una capa posterior.
