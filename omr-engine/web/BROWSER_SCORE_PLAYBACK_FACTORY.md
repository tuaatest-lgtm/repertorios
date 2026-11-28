# Factory de reproducción del navegador

`createBrowserScorePlaybackSession` consume directamente el objeto
`unconfirmed_score_playback_bundle` del motor y conecta:
1. `WebAudioSink` sobre el AudioContext del host,
2. `LookaheadPlaybackController` para programar el audio,
3. `ScoreVisualCursor` para resaltar geometría,
4. `BrowserScorePlaybackSession` para sincronizar el cambio de página.

El host debe crear el AudioContext tras una interacción del usuario, pasar el
callback `onPageChange` para navegar el visor y usar `session.frame()` desde
su ciclo de renderizado. `dispose()` detiene y libera el sink.

No requiere cambiar `index.html` ni Sonoro para probarse en aislamiento; la
conexión a la interfaz productiva sigue siendo una tarea del host.
