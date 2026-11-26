# Candidatos de ligadura de prolongación

El módulo `tie_candidates.py` combina tres fuentes que deben estar disponibles
antes de proponer una ligadura:

1. Eventos de nota con altura MIDI, voz revisada, pentagrama, tiempo global y
   caja de la cabeza de nota.
2. Candidatos geométricos de arco de `detect_tie_slur_shape_candidates`.
3. Continuidad temporal exacta entre el final de la nota de origen y el inicio
   de la nota siguiente de esa misma voz.

Solo propone pares consecutivos de la misma voz y pentagrama, con la misma
altura MIDI y un arco cuya caja cubre geométricamente el espacio entre las
cabezas. La comparación temporal usa unidades musicales exactas, no píxeles.
El tiempo debe ser global para poder representar ligaduras que cruzan barras
de compás.

## Estados y límites

- `proposed_tie`: se cumplen las condiciones necesarias, pero no confirma la
  ligadura.
- `ambiguous_tie_candidate`: un arco o un par admite varias correspondencias.

La igualdad MIDI no garantiza que ambas notas tengan la misma escritura
enarmónica. Una curva también puede ser una ligadura de expresión u otra marca.
Por tanto, todas las propuestas requieren revisión humana. No se clasifican
automáticamente los arcos que no cumplen las condiciones como slurs: pueden
ser arcos editoriales, errores geométricos o detecciones incompletas.

La función `build_reviewed_tie_durations` permite sumar las dos duraciones
solo después de que una persona confirme explícitamente que el arco es una
ligadura de prolongación y que ambas notas tienen la misma escritura musical.
Rechaza propuestas ambiguas o confirmaciones incompletas. No modifica los
eventos originales, no asigna voces, no detecta alturas ni tiempos desde la
imagen y no está conectada al CLI ni a Sonoro.
