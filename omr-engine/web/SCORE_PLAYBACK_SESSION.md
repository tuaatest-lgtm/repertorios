# Sesión de reproducción y cursor visual

`BrowserScorePlaybackSession` conecta `BrowserPlaybackController` con
`ScoreVisualCursor`. El reloj de `AudioContext` determina el instante musical;
la sesión consulta el mapa visual en ese mismo instante y emite `onPageChange`
cuando cambia inequívocamente la página.

Uso conceptual:

```js
const session = new BrowserScorePlaybackSession({
  player,
  visualCursor,
  onPageChange: ({ page_index, system_index }) => {
    pdfViewer.showPage(page_index);
    scoreOverlay.selectSystem(system_index);
  },
});
await session.play();
function renderFrame() {
  const frame = session.frame();
  scoreOverlay.showHighlights(frame.visual.highlights);
  requestAnimationFrame(renderFrame);
}
requestAnimationFrame(renderFrame);
```

El ejemplo ilustra el contrato esperado; `pdfViewer` y `scoreOverlay` pertenecen
al host y deben conectarse a sus APIs reales. Este módulo no toca `index.html`,
Sonoro ni un visor concreto. Las posiciones proceden exclusivamente de anclajes
geométricos explícitos; no se infieren de los tiempos ni del orden de notas.
