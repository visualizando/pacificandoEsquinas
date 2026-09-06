# Altolaguirre y contraste con Google Maps

## Hallazgo sobre la corrida conservada

En `tunnels-all.json`, Altolaguirre A → B tiene 1307 m en auto y 341,7 m para ambos perfiles peatonales. La ruta vehicular no usa el túnel objetivo y está marcada como no validada. La caminata sí cruza directamente. El rodeo grande del mapa es la línea azul del auto.

La instantánea `osm_440436964.osm.json` contiene el túnel vehicular 440436964, de mano única, con `sidewalk=left`. El motor permite caminar por esa vereda implícita, representada en el eje vial. Los 341,7 m peatonales completos usan ejes de calle. Hay además pasos peatonales independientes (por ejemplo 1329934694) y escaleras 1250517980 y 1329684693, ambas con `ramp=no`. Por lo tanto, no corresponde atribuir el problema a una ausencia total del paso peatonal en OSM. Hace falta verificar la conectividad de esos accesos, la representación de la vereda y los extremos elegidos antes de interpretar la igualdad entre perfiles como ausencia real de desvío.

La interfaz oculta el indicador de desvío de este caso hasta esa revisión, conserva las estimaciones individuales y explica sus límites. No se modificaron conexiones de OSM ni se agregaron rutas ficticias.

## Google Maps

Cada ficha enlaza a Google Maps con exactamente las coordenadas A/B y el sentido elegido, para contrastar caminata y auto. Abrir un enlace no implica que el recorrido ya haya sido verificado por el proyecto.

Google Routes API permite calcular auto y caminata, pero sus [modificadores documentados](https://developers.google.com/maps/documentation/routes/reference/rest/v2/RouteModifiers) no incluyen evitar escaleras ni un perfil peatonal de silla de ruedas. No sustituye directamente los tres perfiles de este estudio. Sus [políticas de uso](https://developers.google.com/maps/documentation/routes/policies) restringen el almacenamiento de resultados y exigen Google Maps cuando se muestran sobre un mapa; una migración completa requeriría revisar la arquitectura de visualización y conservación de datos. No se activaron servicios pagos ni se almacenaron resultados de Google.

Las miniaturas se dibujan con las mismas geometrías OSM que las fichas. Se enfocan en las dos rutas peatonales; el auto se conserva en el mapa de detalle con su leyenda.
