# Inventario cartográfico de pasos bajo nivel

La portada enlaza dos páginas independientes: `web/analisis.html` (esquinas y gráficos) y `web/tuneles.html` (inventario y piloto). Los enlaces antiguos con `#tuneles` redirigen a la segunda.

## Actualizar

Desde la raíz del proyecto:

```sh
python src/tunnel_inventory.py --download
python src/tunnel_inventory.py
```

El primer comando consulta Overpass y conserva la instantánea y consulta en `data/tunnels/city-inventory.osm.json` y `city-inventory.osm.overpassql`. El segundo reconstruye sin red `data/processed/tunnel-inventory.json`.

## Alcance y límites

Se selecciona el área administrativa con ISO3166-2 `AR-C`. Se buscan calles vehiculares etiquetadas como túnel, excluyendo `tunnel=no` y `building_passage`, que intersecten geométricamente vías `railway=rail`. Se agrupan segmentos con igual nombre cuyos centros estén a menos de 100 metros. Los tres casos del piloto se vinculan por identificadores OSM y se incorporan desde su instantánea si faltan en la consulta general.

Es una lista de candidatos, no un censo completo ni verificación del estado actual. Puede omitir calles sin etiqueta `tunnel` bajo puentes ferroviarios, cruces donde las geometrías sólo se tocan en sus extremos y vías con otras etiquetas. La agrupación podría fusionar pasos próximos o no unir segmentos con nombres distintos. Cada candidato debe revisarse antes de analizarlo. No se calculan rutas para los candidatos grises.

El mapa utiliza geometrías ferroviarias locales como contexto. Las ubicaciones también están en una lista con enlaces OSM; los casos analizados abren la comparación. Datos © OpenStreetMap contributors, ODbL. La fecha corresponde a la instantánea de Overpass y se muestra en la página.
