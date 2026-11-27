# Integración de Palermo OMR con la aplicación

## Estado de la aplicación actual

La aplicación del repositorio se sirve como una página estática cuyo punto de
entrada es `index.html`. El motor OMR es un paquete Python independiente que
necesita Python 3.11, NumPy, OpenCV y PyMuPDF. El navegador no puede importar ni
ejecutar ese paquete directamente, y el repositorio no contiene actualmente
un servicio backend desplegado.

Por tanto, la integración debe separar el navegador, el servicio OMR y el
reproductor existente. No se debe cargar el PDF completo ni ejecutar OpenCV en
el hilo principal del navegador, ni modificar el flujo de reproducción actual.

## Arquitectura objetivo

1. **Aplicación web:** permite seleccionar/subir un PDF, iniciar el análisis,
   consultar su estado, visualizar páginas y overlays, y revisar candidatos.
2. **API OMR versionada:** recibe el PDF, crea un trabajo aislado y devuelve un
   identificador. Expone el estado y el resultado JSON del trabajo.
3. **Worker Python:** ejecuta el paquete Palermo OMR en un proceso aislado,
   conserva artefactos temporales y aplica límites de tamaño, tiempo y memoria.
4. **Revisión humana:** confirma pentagramas, claves, armaduras, notas,
   alteraciones, voces, silencios, figuras y ligaduras. Las hipótesis no
   confirmadas permanecen como candidatas.
5. **Adaptador musical futuro:** convierte únicamente eventos revisados y
   validados al contrato de entrada del reproductor. Es una fase posterior y
   no forma parte de la primera integración.

## Contrato HTTP propuesto (v1)

La ruta base es `/api/omr/v1`. Estos endpoints son un contrato de diseño;
todavía no existe un servidor desplegado que los atienda.

### Crear trabajo

`POST /api/omr/v1/jobs`

- Content-Type: `multipart/form-data`
- Campo requerido: `file` (PDF).
- Campos opcionales: `dpi` (entero 150–400; default 300), `options`
  (JSON validado y limitado a opciones permitidas).
- Respuesta `202 Accepted`:

```json
{
  "api_version": "1",
  "job_id": "identificador-opaco",
  "status": "queued",
  "status_url": "/api/omr/v1/jobs/identificador-opaco",
  "result_url": "/api/omr/v1/jobs/identificador-opaco/result"
}
```

### Consultar estado

`GET /api/omr/v1/jobs/{job_id}`

Estados permitidos: `queued`, `processing`, `completed`, `failed`.
La respuesta incluye porcentaje de trabajo técnico, etapa y error seguro si
falló. No presenta una estimación de progreso técnico como precisión musical.

### Obtener resultado

`GET /api/omr/v1/jobs/{job_id}/result`

El resultado conserva la estructura de `analysis.json`, con metadatos de
versión, huella SHA-256 del PDF, número de páginas, advertencias y enlaces a
overlays. Las regiones y eventos no revisados deben conservar un estado
explícito de candidato; no se exponen como notas listas para reproducir.

### Revisión

La revisión se enviará como un documento separado y versionado, con el
identificador del trabajo, página, compás, IDs estables de candidatos,
decisiones humanas y versión del esquema. La API debe rechazar IDs ajenos al
trabajo, decisiones contradictorias y revisiones basadas en una versión
anterior del resultado.

## Seguridad y operación

- Aceptar solo PDF; validar firma y estructura, no confiar en extensión/MIME.
- Limitar tamaño de archivo, páginas, DPI, tiempo de CPU, memoria y concurrencia.
- Generar IDs no predecibles; exigir autenticación/autorización cuando se
  conecte a cuentas de usuario.
- Aislar cada análisis en directorio temporal y limpiar archivos al vencer TTL.
- No ejecutar comandos suministrados por el cliente ni aceptar rutas locales.
- Configurar CORS solo para el origen real de Palermo Music.
- No registrar el contenido del PDF ni datos musicales privados en logs.
- Mantener la API desactivada hasta que exista backend y almacenamiento
  configurados; no colocar secretos en `index.html`.

## Puertas para conectar con el reproductor

El resultado del OMR no debe entrar directamente a Sonoro. Antes se requiere:
1. transcripción revisada y exportable con alturas MIDI, ataques y duraciones
   exactas, silencios, voces y acordes simultáneos;
2. validación contra partitura real anotada;
3. conversión explícita al formato que el reproductor ya consume;
4. modo de prueba que compare eventos sin reproducir ni modificar el estado
   del reproductor;
5. habilitación controlada solo para documentos aprobados.

La primera integración con la aplicación será exclusivamente de carga,
seguimiento, visualización y revisión. No cambia el reproductor, su reloj,
sincronización ni navegación de páginas.
