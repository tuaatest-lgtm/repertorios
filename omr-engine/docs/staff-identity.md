# Evidencia para identificar pentagramas

El módulo `palermo_omr.staff_identity` establece una capa de revisión para identificar si un pentagrama corresponde a piano, instrumento, coro o una voz como soprano, alto, tenor o bajo.

## Qué registra

- Evidencias observadas: etiqueta impresa, etiqueta de voz, símbolo de clave, llave, corchete, barra compartida, texto de instrumentación, disposición o revisión humana.
- Origen de la evidencia: candidato visual o revisión humana.
- Propuestas de identidad: parte sugerida, tipo de parte y posible voz.
- Estado: propuesta, confirmada o ambigua.

## Regla de seguridad

Una propuesta nunca se convierte en identidad confirmada solo por proximidad vertical, clave o apariencia geométrica. Para confirmar se exige una revisión humana explícita, evidencia de revisión y una parte identificada. Las propuestas ambiguas no pueden marcarse como confirmadas.

Este módulo es un registro validable; no realiza OCR, no reconoce llaves o claves automáticamente y no asigna voces SATB. Tampoco decide que dos pentagramas sean las dos manos de un piano. Esas conclusiones requieren detectores específicos y verificación.

## Flujo previsto

1. Los detectores futuros generan evidencias visuales localizadas.
2. El sistema formula propuestas sin alterar las asignaciones musicales.
3. Una revisión visual confirma, mantiene ambigua o rechaza cada propuesta.
4. Solo las identidades confirmadas podrán alimentar etapas musicales posteriores.

No se conecta con Sonoro ni con el reproductor.
