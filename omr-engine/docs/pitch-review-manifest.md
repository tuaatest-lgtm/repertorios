# Orden interno de la revisión de alturas

El manifiesto conserva índices sobre las dos listas de candidatos geométricos. Antes de interpretar alteraciones, el CLI ordena internamente las cabezas por pentagrama, compás y posición horizontal para que las alteraciones de compás se apliquen en el orden musical. Cada resultado conserva el índice de origen y se reordena al índice geométrico original antes de alimentar el timeline. Así no se rompe la asociación entre cabeza detectada, altura revisada y evento rítmico.

Este reordenamiento no detecta acordes: los grupos de simultaneidad y los compases siguen siendo decisiones humanas.