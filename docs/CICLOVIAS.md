# Cuarto análisis: prolongar la red existente

Página: `web/ciclovias.html`. Artefacto: `data/processed/cycle-grid.json`.

## Reproducir

`python src/cycle_grid.py` con Python, shapely y pyproj.
Usa `data/cycling/city-network.osm.json` y `data/schools/streets.geojson`.
La consulta completa está en `data/cycling/city-network.overpassql` y la
fecha OSM se guarda en los metadatos. Servir desde la raíz con HTTP.
MapLibre GL 4.7.1 se incluye en `web/vendor/`, junto a su licencia.

## Modelo v2

Reemplaza la grilla independiente de v1 por prolongaciones exclusivamente.
Se detectan extremos de grado uno de la infraestructura asociada al grafo
vial, con 200 m de continuidad previa. Cada candidato comienza en uno de esos
nodos: nunca se crean corredores independientes. Se elige el siguiente tramo
más recto, con una pequeña preferencia por conservar el nombre de la calle.
Máximo 30 grados entre segmentos y 45 grados respecto de la dirección inicial.
Se detiene al reencontrar la red existente, quedarse sin una continuación
válida o alcanzar 3 km. Se descartan extensiones menores de 150 m.
Se evita infraestructura paralela a 40–400 m lateralmente, con una tolerancia
longitudinal de 50 m y direcciones cuya diferencia es menor a unos 20 grados.
Los tramos nuevos se deduplican por arista; no se garantiza una separación
uniforme de 8–10 cuadras. Es una heurística inicial, no un óptimo.

Infraestructura: highway=cycleway; path/footway con bicycle=designated;
cycleway y sus variantes left/right/both con lane, track, opposite_lane u
opposite_track. No se incluye shared_lane ni separate como geometría propia.
Calles candidatas: residential, living_street, unclassified, primary,
secondary, tertiary y sus enlaces; sin access=private/no. Grafo no dirigido
para diseñar futura infraestructura, no para indicar circulación actual.
Alcance: callejero BA Data con buffer de 60 m en EPSG:32721, no un límite
administrativo exacto. Se asocia un tramo a infraestructura si el 80% de su
longitud queda a menos de 18 m de ella. Esa asociación necesita revisión,
especialmente en vías separadas y calzadas paralelas. Puede omitir extremos.
Las longitudes son cartográficas y pueden incluir duplicaciones OSM en la
red existente; no son cómputos oficiales ni presupuestos de obra.

La página solicita datos sin caché y reajusta el mapa cuando cambia el tamaño
del panel, para conservar a toda la ciudad visible, incluida la zona sur.

## Pendiente

Auditar extremos y cruces; incorporar filtros de avenidas, establecimientos,
conteos y reportes ciudadanos. Esta versión no los usa.

## Fuentes

- https://www.openstreetmap.org/copyright — ODbL.
- https://wiki.openstreetmap.org/wiki/Key:cycleway — etiquetas.
- https://data.buenosaires.gob.ar/dataset/calles — CC-BY-2.5-AR.

## Editor manual

`cycle-routing.json` se exporta con el mismo grafo de calles de CABA al ejecutar
`src/cycle_grid.py`. `cycle-router.js` conecta nodos con Dijkstra por longitud,
sin inventar enlaces entre componentes. Ajusta clics al nodo más cercano con
un límite de 120 m. Los puntos sucesivos son pasos obligatorios del borrador.
El grafo es no dirigido: representa trazado futuro, no navegación ciclista actual.

`cycle-editor.js` permite varios corredores, agregar y arrastrar puntos,
eliminarlos con Suprimir, deshacer hasta 50 cambios y eliminar corredores.
El borrador se guarda en localStorage con clave `pacificando-cycle-draft-v1`.
Descargar genera un JSON versión 1 con corredores (nombre y puntos) y geometría
GeoJSON. Cargar valida el formato y recalcula las rutas sobre el grafo actual;
la carga reemplaza el borrador y se puede deshacer. Límite: 5 MB, 100 corredores,
1.000 puntos. La optimización con nuevas reglas queda para una siguiente etapa.

Pruebas del router: `Get-Content tests/test_cycle_router.cjs -Raw | node`.

## Capa unificada: ciclovías para completar la red

El mapa consume `data/processed/cycle-completion.json`. Se genera mediante
`python src/cycle_completion.py`, después de `cycle_grid.py` si se actualiza
la red. Une las geometrías exportadas por el usuario, conservadas en
`data/cycling/user-proposal.json`, con las extensiones automáticas. No vuelve
a enrutar el dibujo. Todos los segmentos se validan contra el grafo vial.
La clave es el par de coordenadas de extremos redondeadas a 7 decimales,
ordenado para deduplicar también recorridos inversos y coincidencias parciales.
Se excluye infraestructura existente con el mismo criterio 18 m / 80%.
Las propiedades conservan calle, OSM ID, corredores de origen y procedencia.
El reporte `metadata.merge_audit` registra repeticiones y exclusiones.

Resultado inicial: 52 corredores manuales, uno vacío omitido; 53 ocurrencias
repetidas (2,51 km), 119 segmentos existentes excluidos (2,19 km). Resultado:
4.012 segmentos y 162,25 km. El borrador local se conserva y se muestra solo
al activar Ver borrador editable o al dibujar, para no duplicar visualmente
la capa consolidada.

## Distancia por manzana

Después de actualizar la capa unificada, ejecutar `python src/cycle_coverage.py`.
Genera `data/processed/cycle-coverage.json` a partir de las manzanas esquemáticas
y `cycle-completion.json`. Distancias euclídeas en UTM 21S desde el centroide
(si cae fuera, punto representativo interior) a la geometría más cercana.
Campos current_m y total_m (red actual y actual + propuesta consolidada).
No incluye ediciones no consolidadas del editor, barreras ni distancias por calles.
Se conserva el hash y fecha de generación de la red; el frontend rechaza una
capa calculada para otra versión. Añadir ciclovías nunca aumenta la distancia.

14.790 manzanas evaluadas. Escala continua de rojo claro a intenso, común a ambos escenarios: 0 a 1.000 m,
con saturación para valores superiores. Referencia compacta Cerca–Lejos. Un selector
exclusivo permite apagar el coloreado o comparar cualquiera de las dos capas
sin mezclarlas. Seleccionar una manzana muestra ambos valores y la reducción.

## Histograma comparativo

Debajo del mapa, `cycle-histogram.js` agrega las mismas 14.790 manzanas en
intervalos de 100 m [inferior, superior). Cada escenario suma el total de
manzanas. El gráfico tiene un ancho máximo de 700 px y agrupa todas las distancias
de 1.000 m o más en el último intervalo abierto, sin excluir manzanas. Barras verdes: actual; azules: actual
más propuesta. Escala vertical compartida desde cero. Tabla accesible y
selección por teclado/tacto para consultar intervalos. No depende de las
capas visibles. Resumen: menos de 500 m, 78,7% actual frente a 97,1% completa.

## Radios censales y población

El archivo aportado `cabaTopojson.json` es en realidad GeoJSON FeatureCollection.
Se conserva en `data/cycling/census-input.geojson`: 3.820 radios únicos,
3.095.454 habitantes y porcentaje de 0 a 14 años inclusive. El archivo no
identifica año censal; el campo sag=INDEC no verifica por sí solo su procedencia.
Se presenta el año como pendiente de confirmar. No se infiere una cifra exacta
de menores de 14: el grupo incluye a quienes tienen 14 años.

`python src/cycle_population.py` produce `cycle-population.json` con la misma
red consolidada. Se asigna toda la población a la distancia del centroide
interior (o punto interior alternativo) del radio a la ciclovía más próxima.
La población de 0–14 se estima multiplicando población por porcentaje/100;
se conserva la fracción durante las sumas y se redondea solo al mostrarla.
No se supone que todos los domicilios estén en el centro ni se extrapolan
beneficios de salud o uso. Radios grandes/heterogéneos pueden tener errores
importantes de asignación; no se pondera por distribución residencial interna.

El selector de unidad cambia manzanas/radios. El histograma permite manzanas,
población total o población de 0–14, con intervalos iguales y 1.000+ agrupado.
Los polígonos mantienen el color por distancia, no por cantidad de habitantes;
la población pondera las barras y se informa al seleccionar el radio.
Se conservan las sumas de población en ambos escenarios. Resultados con esta
aproximación, a menos de 500 m: 85,5% → 98,7% total; 80,9% → 98,4% de 0–14.
La cifra aproximada de 0–14 en el archivo es 459.875 personas, derivada de
porcentajes redondeados, no un conteo exacto.

## Comparación simplificada (versión vigente)

El mapa muestra exclusivamente manzanas, coloreadas por distancia. Los radios
se usan solo para estimar población en la comparación inferior. Dos barras
horizontales del mismo ancho (máximo 700 px) muestran 100% de la población
seleccionada: actual arriba y con propuesta abajo. Selector: población total
(predeterminada) o 0–14 inclusive. Rangos [0,100), [100,250), [250,500),
[500,1000) y 1000+ metros. Rojo progresivo de cerca a lejos. Porcentajes y
cantidades disponibles por segmento y en tabla. Las barras conservan la misma
población de referencia; sustituye el histograma y el selector de radios.
