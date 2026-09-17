# Alternativa: calles anchas y recorridos más rectos

Estado: diseño del análisis. No se generó todavía una red alternativa ni se modificó la propuesta publicada.

## Qué queremos comparar

1. Red actual.
2. Red actual más la propuesta existente.
3. Red actual más una alternativa que conserve las conexiones principales de la propuesta y busque calles más adecuadas.

La red existente se mantiene. Se reconsideran solamente los tramos propuestos. La alternativa no se considerará superior hasta comparar sus resultados.

## Reglas

- Evitar circular por avenidas en los tramos nuevos. Cruzarlas en una intersección sigue permitido; esos cruces se contabilizan por separado.
- Evitar los frentes de hospitales y comisarías. La proximidad a un edificio es una alerta provisional: no demuestra dónde está su acceso.
- Favorecer mayor ancho de calzada, sin asumir que todo ese ancho está disponible para una ciclovía.
- Reducir los giros y los desvíos, manteniendo las conexiones entre corredores y con la red existente.
- No cambiar el criterio según sentidos actuales de circulación sin decidir antes si se proyectan ciclovías unidireccionales o bidireccionales.

## Datos revisados

- Calles de Buenos Aires Data: disponible `data/schools/streets.geojson`, con clasificación `tipo_c` y geometrías. Se usará para identificar avenidas, no solo su nombre.
- Veredas: disponible `data/raw/veredas-2019.geojson`. Ya existe una función para medir el espacio entre veredas en `src/school_surface.py`. Se reutilizará en puntos interiores de las cuadras, evitando las esquinas. Es una aproximación histórica.
- OpenStreetMap: el archivo local tiene 49.786 vías, de las que solo 477 tienen etiqueta `width`. No alcanza para usarla como fuente principal de ancho. El archivo fue descargado para la red vial y no contiene etiquetas `amenity`: no permite evaluar hospitales ni comisarías.
- Hospitales y comisarías: falta incorporar un inventario geográfico y revisar su cobertura. Cuando se disponga de edificios sin accesos, se marcarán calles próximas para revisión, sin atribuirles un frente confirmado.
- Población: disponible la estimación por radio censal usada en la comparación actual, con año pendiente de confirmar.

## Cómo buscar alternativas

1. Reconstruir corredores, extremos y puntos de conexión de la propuesta actual. Preservar también los cruces que conectan corredores: mantener solo extremos podría desconectar la red.
2. Asociar cada tramo candidato con la clasificación oficial, ancho estimado y posibles frentes sensibles. Los datos faltantes se conservan como desconocidos.
3. Buscar rutas por calles próximas al corredor original. Explorar bandas de 200, 400 y 600 m como parámetros iniciales, no como límites validados.
4. Usar una búsqueda cuyo estado incluya la dirección de llegada para poder penalizar los giros. Contar giros por cambio de rumbo, no por cada segmento cartográfico. Comparar umbrales de 30 y 45 grados.
5. Probar distintas penalizaciones de estrechez, giros y desvíos. No fijar un ancho mínimo universal todavía: primero revisar la distribución de anchos y los requerimientos del tipo de ciclovía.
6. Excluir nuevos recorridos longitudinales por avenidas y frentes sensibles confirmados. Si no queda una ruta viable, informar la conexión pendiente; no relajar la regla silenciosamente.
7. Reunir los corredores, eliminar tramos compartidos y verificar conectividad. Calcular nuevamente el alcance de la red completa.

La búsqueda encuentra la mejor ruta para sus datos, pesos y restricciones. No demuestra un óptimo universal de toda la red. Se conservarán varias alternativas cuando haya intercambios entre rectitud, ancho, longitud y alcance.

## Comparación a entregar

Para cada alternativa y para la propuesta actual:

- Kilómetros nuevos únicos y diferencia respecto de la propuesta actual.
- Giros por corredor y por kilómetro, sin sumar como giros las curvas suaves de una misma calle.
- Ancho mediano y percentil 10, ponderados por longitud; porcentaje de longitud con medición válida.
- Kilómetros sobre avenidas y cantidad de cruces de avenidas.
- Frentes sensibles confirmados y alertas pendientes de revisión.
- Conexiones conservadas, conexiones pendientes y componentes desconectados.
- Población total y de 0–14 años a menos de 100, 250, 500 y 1.000 m, usando el mismo método que la propuesta actual.
- Zonas que ganan o pierden cercanía, aunque el total de la ciudad mejore.

## Primer resultado esperado

Un mapa de comparación separado, con la propuesta actual y dos o tres variantes, más una tabla de resultados. No reemplazar la capa publicada. Primero completar los datos de hospitales/comisarías y medir anchos; después generar rutas y compararlas. Los accesos, cruces y disponibilidad real de calzada requieren revisión antes de presentar una alternativa como viable para obra.
