# Revisión humana por fragmentos

El paquete completo de revisión puede contener miles de candidatos. Para iniciar
la anotación sin mezclar sistemas, páginas o partes, se puede extraer una región
de trabajo a partir de un paquete `prepare-review` ya generado.

## Crear un fragmento

```bash
palermo-omr-focus-review review/clamare-review.json \
  --page 1 \
  --staff-indices 0,1 \
  --label "Primer sistema, página 1" \
  --output review/clamare-page1-system1-draft.json
```

Los índices empiezan en cero y deben corresponder a pentagramas existentes en
la página seleccionada. El fragmento conserva los IDs de candidatos originales,
sus cajas, coordenadas, hipótesis, referencias y overlays. Incluye solo los
candidatos relacionados con los pentagramas elegidos.

La selección de pentagramas es una delimitación de trabajo, no una confirmación
automática de sistema, instrumento, parte o voz. El paquete mantiene todas las
decisiones en `pending`, declara `annotation_status: draft` y
`ground_truth_eligible: false`. `events` permanece vacío:
no se inventan alturas, compases, voces, onsets ni duraciones.

Después de revisar visualmente el fragmento, los eventos completos se incorporan
al manifiesto del corpus con `import-events`. Solo el flujo existente de
revisión humana puede aprobar una partitura; un fragmento de candidatos nunca
se convierte por sí solo en ground truth.
