# Transformación de coordenadas del cursor visual

`ScoreViewportTransform` convierte los rectángulos de página del análisis OMR a
coordenadas CSS del visor. El host entrega dimensiones de la página de análisis,
dimensiones reales del área renderizada, offsets del visor y scroll actual.
Se calculan escalas X/Y por separado para respetar el tamaño CSS efectivo.

`mapVisualState` solo devuelve resaltados de la página configurada y los oculta
cuando el cursor es ambiguo. El módulo no accede al DOM ni supone zoom, recorte,
rotación o densidad de píxeles; el host debe suministrar las dimensiones y offsets
vigentes después de cada zoom, resize o scroll.
