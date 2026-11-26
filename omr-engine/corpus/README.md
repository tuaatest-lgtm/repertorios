# Corpus de referencia Palermo OMR

Este directorio contiene metadatos del corpus. Los PDF originales no se
incluyen ni se redistribuyen desde este repositorio.

## Partitura registrada

- ID: `clamare-a-dios-coro`
- Archivo de origen: `Clamaré a Dios - Coro.pdf`
- SHA-256: `bbf62fa7b3be45585e3d77a7d0b3fe57ab4701ff17c8e821f14dbdc88f64f74c`
- Páginas: 3
- Partición prevista: `train`
- Estado: `draft`, sin eventos anotados.

El hash permite comprobar que el PDF usado para anotar es exactamente el
mismo archivo. El registro no declara que se hayan anotado ni validado notas,
voces, alturas, ritmos, compases o instrumentos.

## Próximos pasos

1. Obtener el PDF original localmente y verificar su SHA-256.
2. Ejecutar el análisis visual Palermo y guardar `analysis.json` junto a sus
   overlays.
3. Preparar el paquete de revisión visual con `prepare-review`.
4. Contrastar candidatos con cada página y completar los eventos musicales
   manualmente, con voz, compás, ataque, altura y duración explícitos.
5. Importar los eventos al manifiesto, validar y aprobar tras revisión humana.
6. Reservar partituras distintas para validation y test; nunca duplicar el
   mismo PDF entre particiones.

El manifiesto `manifest.json` se mantiene como borrador hasta completar y
revisar las anotaciones.
