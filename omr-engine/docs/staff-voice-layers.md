# Propuestas de capas de voz dentro de un pentagrama

El módulo `palermo_omr.staff_voice_layers` busca zonas de un mismo pentagrama
donde coexisten cabezas con plicas candidatas hacia arriba y hacia abajo.
Esta coexistencia puede ser una pista de voces independientes en un solo
pentagrama, como ocurre en escritura coral a dos voces o en partituras de
teclado.

## Qué hace

- Compara únicamente cabezas pertenecientes al mismo pentagrama.
- Normaliza la proximidad horizontal por el espaciado entre líneas.
- Propone una zona cuando una ventana horizontal contiene al menos una plica
  candidata hacia arriba y otra hacia abajo.
- Agrupa ventanas solapadas en una propuesta local.
- Mantiene las cabezas sin dirección reconocida fuera de ambas capas.

## Qué no hace

Una propuesta no confirma que existan dos voces. Plicas opuestas también
pueden aparecer por decisiones de grabado, acordes, cruces de voces o errores
de detección. El módulo no asigna soprano/alto, mano derecha/izquierda ni
identificadores de voz; tampoco decide qué cabeza pertenece a qué línea
musical, ni crea eventos para la secuencia temporal.

La confianza es deliberadamente conservadora y fija (0.5), no calibrada. La
ventana horizontal es solo un filtro de coexistencia geométrica; no representa
un ataque ni una medida del tiempo musical. Los resultados deben revisarse
antes de cualquier uso posterior.

## Próximos requisitos

Para resolver realmente dos voces en un pentagrama será necesario combinar
esta pista con continuidad melódica, alturas, ritmos, plicas y barras, además
de permitir una asignación de voz por evento (no una única voz por pentagrama).
Los casos donde no haya evidencia suficiente deben permanecer ambiguos.
