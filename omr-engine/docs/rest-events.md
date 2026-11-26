# Silencios y colocación temporal por voz

`detect_rest_shape_candidates` sigue siendo un detector geométrico de formas:
puede confundir silencios con texto, articulaciones o fragmentos, y su tipo
visual propuesto tiene confianza baja. No se utiliza para asignar voz ni tiempo.

El adaptador `rest_events.py` añade una compuerta de revisión humana. Para
crear un evento `rest`, la persona revisora debe confirmar explícitamente:

- cuál candidato corresponde al silencio;
- su tipo y duración musical;
- la voz a la que pertenece;
- el compás y el orden del evento dentro de esa voz.

Solo entonces se crea un `OrderedVoiceEvent(event_type="rest")`. La secuencia
temporal posterior suma su duración igual que la de una nota, pero cada voz
mantiene su propio orden y reloj. Así, un silencio de contralto no desplaza
automáticamente el flujo de soprano, y un silencio de una mano del piano no se
confunde con un silencio coral.

El módulo no deduce la posición temporal desde x, no interpreta el símbolo
automáticamente, no divide silencios entre voces y no se conecta al CLI ni a
Sonoro. La duración y el orden son entradas revisadas, no resultados del
detector de imagen.
