# Conversión de geometría a estructura

El módulo score_geometry.py convierte candidatos geométricos en la estructura validable de una página.

- Crea identidades locales para pentagramas.
- Convierte agrupaciones de pentagramas en sistemas candidatos.
- Asocia intervalos geométricos al sistema de su pentagrama.
- Conserva pentagramas no agrupados sin inventar su sistema.
- Deja todas las asignaciones musicales como unassigned.

No identifica llaves, instrumentos, piano, coro ni voces. Tampoco confirma compases musicales. Los números de compás son locales al pentagrama y página. Es una conversión interna entre modelos de candidatos, no una integración con Sonoro ni una salida lista para reproducir.
