# Calles escolares de CABA

Explorador: `web/escuelas.html`. Resultado versionable: `data/processed/school-streets.json`.

## Fuentes y cobertura

Snapshots descargados el 11 de septiembre de 2026 UTC:

- [Establecimientos educativos, BA Data](https://data.buenosaires.gob.ar/dataset/establecimientos-educativos): 2.767 registros, GeoJSON EPSG:9498, nombres, CUE, anexo, CUI, oferta, domicilio, gestión y comuna.
- [Calles, BA Data](https://data.buenosaires.gob.ar/dataset/calles): 31.961 segmentos, CRS84, nombre oficial, alturas, tipo y sentido.
- Ambas fichas declaran CC-BY-2.5-AR. Atribución: Gobierno de la Ciudad Autónoma de Buenos Aires / Buenos Aires Data. El mapa base esquemático se deriva del callejero oficial: polígonos cerrados de su red, con superficie mínima de 150 m² y simplificación de 1 m. No son manzanas catastrales. Se guarda en `data/processed/school-blocks-base.json`, sin etiquetas ni teselas externas.

Las URL exactas y hashes SHA-256 de los snapshots quedan en `metadata` del resultado. Los originales permanecen en `data/schools/` y se ignoran en Git; el resultado permite explorar sin descargarlos de nuevo. Algunos nombres del callejero ya contienen caracteres de reemplazo en origen; no se inventan correcciones.

## Unidad y asignación

1. Se unen segmentos del mismo código, tipo y sentido exclusivamente en nodos de grado dos de la red completa. Se mantienen las intersecciones y las calzadas separadas. No se disuelven por nombre toda la calle ni por centena de altura.
2. Se incluyen CALLE, AVENIDA, PASAJE y BOULEVARD con sentido CRECIENTE, DECRECIENTE o DOBLE. Se excluyen autopistas, accesos, privados, senderos y peatonales. Quedan 30.082 tramos elegibles. Es una aproximación de cuadras por eje vial, no un censo de manzanas ni de calzadas físicas.
3. Escuelas reproyectadas de EPSG:9498 a EPSG:32721; calles de CRS84 a EPSG:32721 para medir en metros. El GeoJSON de salida está en longitud/latitud.
4. Para cada domicilio separado por ` - ` se buscan candidatos a 150 m. Se comparan tokens del nombre, ignorando orden, tildes y títulos frecuentes. Entre nombres con Jaccard ≥0,5 se prioriza altura en rango, luego similitud y distancia. Nombre ≥0,65 + altura en rango + distancia ≤100 m se etiqueta `domicilio`; lo demás, incluido el vecino más cercano sin coincidencia nominal, `revisar`.
5. Un mismo establecimiento puede vincularse con dos frentes. Los registros se agrupan por CUE + anexo + CUI y sus niveles se unen. Los vínculos se deduplican dentro de cada cuadra. CUI identifica sedes para el resumen; no equivale necesariamente a edificios físicamente independientes. No se elimina una institución distinta por compartir edificio.

Resultado inicial: 2.762 identificadores únicos, 1.741 cuadras candidatas, 2.816 vinculaciones por domicilio y 197 por revisar. Una escuela queda sin asignar: CENTRO EDUCATIVO DE NIVEL PRIMARIO, Miralla 3838. Los pendientes están en `metadata.unresolved`. De las cuadras candidatas, 96 incluyen alguna vinculación por revisar (otras también contienen vínculos por domicilio).

Este cruce no garantiza todas las instituciones de CABA ni todos sus accesos. No se asigna automáticamente todo el perímetro de un edificio. Un acceso real puede diferir del domicilio administrativo. La confianza por domicilio tampoco es verificación de campo.

## Filtros y métricas

- Nivel, gestión y comuna filtran primero los establecimientos. El nivel primario incluye las ofertas de adultos identificadas como primario; inicial incluye maternal. Otros reúne ofertas sin esos niveles.
- La cantidad mínima se calcula después de filtrar, por establecimiento distinto en esa cuadra. Dos instituciones en una sede cumplen el filtro de dos establecimientos.
- Excluir avenidas excluye también bulevares. Mano única acepta solo CRECIENTE/DECRECIENTE, nunca un sentido desconocido.
- Al desactivar vinculaciones por revisar se quitan esos vínculos, manteniendo la cuadra si todavía cumple el resto de condiciones.
- Conteo de cuadras: ID distinto. Establecimientos y sedes: conjuntos de identificadores distintos en toda la selección, sin duplicación por dos frentes.
- Porcentaje escolar: seleccionadas / 1.741 candidatas. Porcentaje ciudad: seleccionadas / 30.082 tramos elegibles. Los denominadores son fijos para esta corrida; no el área visible del mapa.

## Reproducir

Desde la raíz, con Python y las dependencias GIS del proyecto (shapely y pyproj):

```powershell
python src/school_streets.py --download
# Recalcular con los snapshots locales:
python src/school_streets.py
python -m unittest discover -s tests -p test_school_streets.py
node tests/test_school_filters.cjs
python -m http.server 8766 --bind 127.0.0.1
```

Abrir `http://127.0.0.1:8766/web/escuelas.html`. Las nuevas descargas pueden cambiar los totales. Conservar snapshots y hashes si se comparan escenarios en el tiempo. La fecha de descarga que muestra la página describe este snapshot; actualizarla al publicar nuevas fuentes.


## Superficie entre veredas

El explorador ya no usa el parámetro de ancho. `python src/school_surface.py` agrega `area_m2` y `measured_length_m` a cada cuadra. Ejecutarlo después de reconstruir escuelas si no se dispone de la fuente local durante esa reconstrucción.

Fuente: https://data.buenosaires.gob.ar/dataset/veredas/resource/b1ff503e-1b8e-469a-822d-7bcdc53e51cd/download → `data/raw/veredas-2019.geojson` (CC-BY-2.5-AR). La fecha del relevamiento es 2019; el hash y método quedan en `metadata.surface`.

Se mide el hueco entre veredas con transectos perpendiculares al eje en intervalos de hasta 5 m. Se acepta solo el componente que contiene el eje, limitado por veredas a ambos lados y con ancho entre 2 y 40 m. Se integra ancho × longitud de intervalo. Se dejan fuera los primeros y últimos 10 m de cada línea para no sumar cruces. No se extrapolan intervalos sin medición: el total es un subtotal cartográfico y la interfaz indica el porcentaje de longitud cubierto (incluye los extremos excluidos en el denominador). `null` significa sin superficie calculable, nunca un ancho de respaldo. La geometría histórica puede diferir de la calle actual; no equivale a un levantamiento de campo. No se suman veredas.

Las barras comparan solo áreas calculables de selección y universo. Manzanas equivalentes = subtotal / 10.000 m².
