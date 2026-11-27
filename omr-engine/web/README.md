# Cliente web independiente Palermo OMR

`web/omr-client.js` es un cliente ES module aislado para el contrato HTTP v1. Ofrece carga multipart de PDF, consulta de estado, polling cancelable con `AbortSignal` y recuperación del resultado final. Valida la extensión PDF, DPI, identificadores y forma mínima de la respuesta; usa credenciales same-origin y nunca inserta datos en Sonoro.

El módulo no está conectado ni importado desde `index.html`. No debe activarse hasta que exista un backend real en `/api/omr/v1`, autenticación y almacenamiento temporal seguro.

Pruebas con Node: `node --test omr-engine/web/test-omr-client.mjs` (ejecutar desde la raíz del repositorio).