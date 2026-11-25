# Aritmética de duraciones escritas

El módulo `palermo_omr.duration_math` ofrece una base matemática exacta para
convertir figuras ya identificadas a unidades de negra.

## Figuras base

| Figura | Negras |
|---|---:|
| Redonda | 4 |
| Blanca | 2 |
| Negra | 1 |
| Corchea | 1/2 |
| Semicorchea | 1/4 |
| Fusa | 1/8 |
| Semifusa | 1/16 |

## Puntillos

Cada puntillo añade la mitad de la duración añadida por el puntillo anterior:
- 1 puntillo: factor 3/2.
- 2 puntillos: factor 7/4.
- 3 puntillos: factor 15/8.
- 4 puntillos: factor 31/16.

El módulo usa `fractions.Fraction`, evitando errores de redondeo acumulados
al construir líneas de tiempo musicales.

## Ligaduras de prolongación

`sum_tied_durations` suma duraciones que ya fueron verificadas como parte
de una ligadura de prolongación. No decide si dos notas deben enlazarse,
no reconoce alturas y no convierte automáticamente un arco visual en tie.
Esa confirmación requiere localizar ambos extremos, comprobar la misma altura
musical y descartar una ligadura de expresión.

## Límite deliberado

Este módulo no analiza imágenes ni alimenta el reproductor. Es una capa
matemática independiente que se podrá utilizar cuando las figuras, puntillos
y ligaduras estén reconocidos con suficiente fiabilidad.
