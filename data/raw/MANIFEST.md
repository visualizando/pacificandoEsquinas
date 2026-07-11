# Manifiesto de fuentes crudas

Cada fuente usada por el pipeline debe documentarse acá: qué es, cuándo se bajó, de dónde, y con qué licencia.
`ingest.py` no valida este archivo automáticamente; es documentación de procedencia que se copia a los metadatos del output.

## callejero.geojson

- **Contenido:** callejero oficial de CABA, un registro por tramo de calle (LineString), con nombre, tipo, sentido, jerarquía vial, comuna y barrio.
- **Fuente:** BA Data (Buenos Aires Data) — datasets abiertos GCBA.
- **URL de origen:** _(completar — no se registró la URL exacta de descarga)_
- **Fecha de descarga:** 2026-07-08
- **Licencia:** _(completar — verificar términos de BA Data)_

## cruces-semaforizados.geojson

- **Contenido:** puntos de cruces peatonales semaforizados.
- **Fuente:** BA Data.
- **URL de origen:** _(completar)_
- **Fecha de descarga:** 2026-07-08
- **Licencia:** _(completar)_

## semaforos.csv

- **Contenido:** puntos long/lat/tipo de semáforos (vehiculares).
- **Fuente:** BA Data.
- **URL de origen:** _(completar)_
- **Fecha de descarga:** 2026-07-08
- **Licencia:** _(completar)_

## ampliaciones_de_veredas.geojson

- **Contenido:** tramos de ensanche de vereda (orejas / bump-outs), 21 registros.
- **Fuente:** BA Data.
- **URL de origen:** _(completar)_
- **Fecha de descarga:** 2026-07-08
- **Licencia:** _(completar)_

## veredas-2019.geojson

- **Contenido:** polígonos de vereda con ancho equivalente (`ANCHOEQUIV`) y flag de esquina (`ESQUINA`).
- **Fuente:** BA Data.
- **URL de origen:** _(completar)_
- **Fecha de descarga:** 2026-07-08
- **Licencia:** _(completar)_
- Habilita los ejes `crossing_length` y `roadway_width`: el hueco entre veredas enfrentadas, medido por transectos perpendiculares a cada ramal (ver `geometry_axes.measure_roadway_width` y `config.yaml: crossing_measurement`), es la calzada que el peatón cruza.

## establecimientos_educativos.geojson

- **Contenido:** padrón de establecimientos educativos de CABA (jardines, escuelas, etc.), 2767 registros en todo CABA / 168 en comuna 12.
- **Fuente:** BA Data — Mapa Escolar, Ministerio de Educación GCBA.
- **URL de origen:** _(completar — no se registró la URL exacta de descarga)_
- **Fecha de descarga:** 2026-07-08
- **Licencia:** _(completar — verificar términos de BA Data)_
- **Nota de CRS:** este archivo declara `EPSG:9498` (POSGAR 2007 / CABA 2019, coordenadas planas en metros), no WGS84 como el resto de las fuentes. `ingest.py` lee el miembro `crs` del GeoJSON y reproyecta automáticamente a EPSG:4326 (ver `_parse_geojson_crs` / `_load_one`); si se agregan más fuentes de BA Data, verificar su CRS declarado en vez de asumir WGS84.
- Habilita el eje `near_school` (exposure_axes.py).

## siniestros_viales_hechos.csv

- **Contenido:** siniestros viales con víctimas, 2019-2025, 65818 registros en todo CABA / 4748 en comuna 12. Incluye severidad (`gravedad_siniestro`: LEVE/GRAVE/MORTAL) y coordenadas.
- **Fuente:** BA Data — siniestros viales.
- **URL de origen:** _(completar — no se registró la URL exacta de descarga)_
- **Fecha de descarga:** 2026-07-08
- **Licencia:** _(completar — verificar términos de BA Data)_
- **Notas de formato:** separador `;` (no coma); columnas de coordenadas `longitud_siniestro`/`latitud_siniestro`. ~3000 filas sin coordenada geocodificable (`SD`, `#REF!`) se descartan en `ingest.py` (no se puede ubicar el punto).
- Habilita el eje `crash_history` (ponderado por gravedad, ver `crash_severity_weights` en `config.yaml`) y activa `validate.py` (correlación Spearman índice vs. siniestros reales).

## colectivos_caba_paradas.json / estaciones_de_subte.json / estaciones_ferroviarias.json

- **Contenido:** paradas de colectivo (6951), estaciones de subte (90) y estaciones ferroviarias (43) de CABA. GeoJSON EPSG:4326, puntos.
- **Fuente:** BA Data.
- **URL de origen:** _(completar)_
- **Fecha de descarga:** 2026-07-08
- **Licencia:** _(completar)_
- Habilitan el eje `ped_flow_proxy`: conteo ponderado por tipo de transporte (`config.yaml: ped_flow_weights` — colectivo 1, tren 2, subte 3) en `ped_flow_radius_m`.

## red_de_transito_pesado.json

- **Contenido:** red de tránsito pesado (rutas habilitadas para camiones), 2009 tramos LineString.
- **Fuente:** BA Data.
- **URL de origen:** _(completar)_
- **Fecha de descarga:** 2026-07-08
- **Licencia:** _(completar)_
- Habilita el eje `heavy_traffic` (binario, radio `heavy_traffic_radius_m`).

## senderos_escolares.json

- **Contenido:** senderos escolares (recorridos seguros designados, Ministerio de Seguridad), 392 tramos.
- **Fuente:** BA Data.
- **URL de origen:** _(completar)_
- **Fecha de descarga:** 2026-07-08
- **Licencia:** _(completar)_
- No puntúa en el índice: flag de contexto `on_sendero_escolar` en el export, para priorizar intervenciones en el informe.

## ciclovias.json

- **Contenido:** red de ciclovías, 2764 tramos.
- **Fuente:** BA Data.
- **URL de origen:** _(completar)_
- **Fecha de descarga:** 2026-07-08
- **Licencia:** _(completar)_
- No puntúa en el índice: flag de contexto `near_ciclovia` en el export.

## estacionamiento_normativa.json

- **Contenido:** normativa de estacionamiento por cuadra y lado (`rgl`: "PROHIBIDO ESTACIONAR 24 HORAS", etc.), ~26 MB.
- **Fuente:** BA Data — Secretaría de Tránsito.
- **URL de origen:** _(completar)_
- **Fecha de descarga:** 2026-07-08
- **Licencia:** _(completar)_
- **Todavía no integrado**: reservado para la etapa del informe de intervenciones — dónde hay cordón de estacionamiento convertible en oreja de vereda (bulb-out) sin quitar carril de circulación.

## Fuentes pendientes (no cargadas todavía)

Estas fuentes son requeridas por el spec (`README` sección 2) para completar los ejes de exposición/vulnerabilidad, pero todavía no están en `data/raw/`. Mientras falten, los ejes que dependen de ellas quedan `null` en el output:

- Sendas peatonales (senda pintada / demarcada) — eje `crossing_marked`.
- Censo 2022 (radios censales, INDEC) — densidad poblacional (idealmente población 0-14 años por radio censal).
