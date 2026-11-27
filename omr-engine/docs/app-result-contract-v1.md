# Contrato de datos de resultados OMR v1

El esquema JSON de este directorio define el sobre estable que consumirá la aplicación. No cambia el formato interno actual de analysis.json: el backend deberá transformarlo y añadir IDs estables y huella del PDF al crear cada trabajo.

## Reglas de integración

- Cada candidato se identifica de forma estable dentro del trabajo y conserva su página, tipo y geometría de origen.
- El estado distingue candidate, human_confirmed, rejected y unresolved. La existencia de un candidato nunca significa que sea una nota musical confirmada.
- interpretation puede contener pitch, onset, duración, voz o tipo de símbolo, pero solo debe presentarse como confirmado cuando state sea human_confirmed y exista evidencia de revisión.
- Toda revisión incrementa revision y declara base_result_sha256. El servidor debe rechazar escrituras basadas en una revisión o resultado obsoleto.
- La respuesta de resultado solo existe cuando status es completed. queued y processing exponen estado de trabajo, no una transcripción parcial lista para reproducir.
- Los enlaces a imágenes y overlays son relativos al trabajo y deben servirse con autorización; no se aceptan rutas locales ni URLs suministradas por el navegador.
- El adaptador hacia Sonoro queda fuera de v1. Solo consumirá una exportación musical validada y explícitamente aprobada.

El esquema es un contrato objetivo para la API; todavía no hay backend implementado ni desplegado. El identificador de esquema usa un dominio reservado de documentación y no es un endpoint de producción.