# Recalcular todos los pasos del inventario

Para corregir puntos desde el mapa y exportar revisiones en lote, ver [Revisión de extremos](REVISION_EXTREMOS.md). Los ajustes se conservan separados de la preparación automática y se aplican en cada corrida.

## Corrida reproducible

```powershell
python src/tunnels_batch.py
python -m unittest discover -s tests -p "test_tunnel*.py"
python -m http.server 8765 --bind 127.0.0.1
```

Abrir `http://127.0.0.1:8765/web/tuneles.html#comparacion`.

La corrida lee `data/tunnels/cases_all.json` y las instantáneas locales, y escribe `data/processed/tunnels-all.json`. No descarga datos ni cambia los extremos ya configurados. Editar la configuración para corregir extremos; modificar `src/tunnels.py` para ajustar las reglas compartidas. Volver a ejecutar recalcula todos los casos, sin tocar los resultados históricos del piloto en `tunnels.json`.

## Preparación y descarga

Alternativa cuando Overpass no responde: `python src/refresh_osm_api.py` descarga las zonas configuradas desde la API de lectura de OSM, secuencialmente, y recalcula con el mismo motor. Conserva las descargas y las instantáneas anteriores en `data/tunnels/refresh-runs/`. No cambia los puntos revisados. Si falla la descarga no publica resultados parciales. La fecha indicada corresponde a la consulta de cada zona, no a una instantánea atómica de toda la ciudad.

```powershell
python src/tunnels_batch.py --download
python src/tunnels_batch.py --prepare
```

`--download` descarga de nuevo las instantáneas de todos los cruces de `cases_all.json`, incluidos los tres pilotos, y recalcula los recorridos. No reutiliza los bloques de la descarga urbana ni regenera los extremos: conserva la configuración y aplica las revisiones exportadas. Reintenta hasta tres veces alternando servidores Overpass. Si falla una descarga, detiene la corrida sin publicar resultados nuevos; las instantáneas ya descargadas pueden haberse actualizado. Las consultas y fechas quedan guardadas por cruce. Para preparar nuevos casos con `--prepare` sigue siendo necesario disponer de la instantánea urbana completa.

`--prepare` regenera explícitamente los extremos automáticos y las instantáneas locales; sobrescribe `cases_all.json`. No usar después de corregir extremos manualmente sin conservar la configuración. La corrida normal no lo hace. El inventario se reconstruye separadamente con `src/tunnel_inventory.py`.

## Extremos y comparabilidad

Los tres casos originales conservan sus extremos manuales. Para los otros se toma la componente conectada de la primera geometría vehicular del túnel: si hay varios segmentos unidos, se utilizan sus extremos exteriores, no el punto de unión interno. Se intenta continuar por su misma calle hasta un nodo a aproximadamente 120 m de cada portal, con un máximo de búsqueda de 350 m. Puede fallar si cambia el nombre de la calle o no existe un nodo adecuado. Las extensiones y coordenadas quedan explícitas en la configuración y las fichas. Extensiones menores a 60 m se marcan para revisión.

Se calculan tres modos en ambos sentidos y se verifica si la ruta vehicular usa un ID del túnel. Una mano contraria puede llevar al auto por otro cruce: ese sentido no tiene referencia vehicular validada. Los dos perfiles peatonales deben ajustar a extremos separados como máximo 3 m para publicar el desvío sin escaleras. Si no, las distancias individuales se muestran, pero el desvío queda vacío. Un resultado faltante no significa distancia cero ni imposibilidad física.

Las estimaciones automáticas no son una auditoría visual ni de campo y no se presentan como ranking. Las calzadas segregadas y autopistas (por ejemplo Paseo del Bajo) pueden no tener un viaje peatonal equivalente. El alcance es el inventario de candidatos OSM, no todos los cruces ferroviarios existentes en la ciudad.

Cada instantánea local abarca aproximadamente 1,5 km alrededor del centro e incluye vías completas que tocan la ventana. El cálculo no garantiza que no exista una alternativa más corta fuera de esa red. Revisar trazados y ampliar los insumos cuando corresponda. Los conteos de giros/cruces y tiempos mantienen las limitaciones del procedimiento del piloto.
