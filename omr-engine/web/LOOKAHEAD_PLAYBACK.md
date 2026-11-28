# Scheduler de audio con anticipación

`LookaheadPlaybackController` programa note_on/note_off en el reloj absoluto de
`AudioContext`, con una ventana configurable de 20 a 500 ms (120 ms por defecto).
Separa dos cursores: `processed_commands` representa el estado musical al instante
actual y `scheduled_commands` representa eventos ya enviados al dispositivo.
El cursor visual debe seguir `current_seconds`, nunca el índice anticipado.

En pausa se cancelan notas y eventos futuros programados; al reanudar se reactivan
las notas que seguían sostenidas y se vuelve a programar desde el siguiente comando
musical. El mute actúa sobre el bus independiente de cada voz sin modificar el
calendario.

La ventana reduce la dependencia de la precisión de requestAnimationFrame, pero no
elimina todos los retrasos: si el hilo principal se bloquea más que la anticipación,
los eventos que aún no se habían programado pueden llegar tarde. Ajustar la ventana
requiere pruebas en dispositivos reales para equilibrar latencia y estabilidad.
