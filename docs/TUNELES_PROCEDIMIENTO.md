# Pasos bajo nivel: procedimiento reproducible

Versión del método: 1.0. Piloto incorporado en `web/index.html#tuneles`.

## Reproducir los tres casos

Sólo requiere Python 3.11 o posterior, sin dependencias adicionales. Desde la raíz:

```powershell
python src/tunnels.py
python -m unittest discover -s tests -p test_tunnels.py
python -m http.server 8765 --bind 127.0.0.1
```

Abrir `http://127.0.0.1:8765/web/index.html#tuneles`.
El cálculo usa las instantáneas incluidas en `data/tunnels/`; no consulta Internet.
El mapa y las fichas leen `data/processed/tunnels.json`. La biblioteca MapLibre
del sitio requiere conexión, pero el fondo vial y ferroviario de esta subsección
proviene de los datos locales, sin proveedor de teselas adicional.

## Qué archivos conservar

- `data/tunnels/cases.json`: casos, extremos y objetos OSM del túnel vehicular.
- `data/tunnels/<id>.osm.json`: respuesta completa de Overpass, con fecha OSM.
- `data/tunnels/<id>.overpassql`: consulta usada para extraer la red.
- `src/tunnels.py`: reglas de acceso, distancias, rutas y exportación.
- `data/processed/tunnels.json`: resultados, geometrías, contexto, fecha y SHA-256
  de cada instantánea. El mismo insumo y método producen el mismo archivo.

Datos © OpenStreetMap contributors, [ODbL 1.0](https://www.openstreetmap.org/copyright).
Las instantáneas son pequeñas y están fuera de `data/raw/` para poder conservarlas
con el proyecto. Las cifras anteriores de Google Maps no alimentan este cálculo.

## Agregar otro paso

1. Agregar un objeto en `cases.json`. Usar un `id` único, estable y compuesto por
   letras minúsculas, números o guiones bajos. `name` es el nombre visible;
   `corridor` debe coincidir exactamente con el nombre OSM de la calle principal.
2. Definir `bbox` como `[sur, oeste, norte, este]` en grados WGS84. Incluir al
   menos 500 m alrededor de ambos extremos y las alternativas de cruce cercanas.
   La ruta óptima se busca únicamente dentro de la red descargada.
3. Definir `origin` y `destination` como `[longitud, latitud]`. Elegir ubicaciones
   sobre el mismo corredor, a lados opuestos del ferrocarril y fuera de las
   entradas vehiculares. `endpoints` describe A → B. Para estudiar una vereda
   concreta, colocar y auditar los puntos sobre esa vereda como otro escenario.
4. Descargar sólo el caso nuevo:

   ```powershell
   python src/tunnels.py --download --case nuevo_id
   python src/tunnels.py --inventory --case nuevo_id
   ```

5. Revisar los candidatos en OSM, confirmar qué calle pasa por debajo del tren y
   guardar sus IDs en `tunnel_way_ids`. Una infraestructura puede tener dos vías
   OSM, una por calzada. El inventario es una lista de candidatos, no un censo
   completo: los pasos etiquetados sólo como puente ferroviario necesitan
   identificación manual y ampliar el detector.
6. Ejecutar `python src/tunnels.py` y revisar las seis rutas (tres modos por dos
   sentidos) en el sitio. Si cambia el conjunto de casos, actualizar la prueba
   de invariantes que comprueba que el piloto contiene tres casos.
7. Conservar el nuevo insumo y el resultado junto con la fecha de revisión.

Ejemplo de configuración (coordenadas ilustrativas, reemplazar antes de usar):

```json
{
  "id": "nuevo_id",
  "name": "Nombre de calle · Ferrocarril",
  "corridor": "Nombre exacto en OSM",
  "bbox": [-34.60, -58.50, -34.58, -58.48],
  "origin": [-58.49, -34.595],
  "destination": [-58.49, -34.585],
  "endpoints": "Esquina A → esquina B",
  "tunnel_way_ids": [123456789]
}
```

El procedimiento es reutilizable para pasos bajo nivel. Una esquina sin túnel
requiere otra validación espacial: el control actual exige un túnel vehicular
que interseque geométricamente una vía ferroviaria.

## Actualizar OSM

```powershell
python src/tunnels.py --download --case beiro
python src/tunnels.py
```

`--download` sin `--case` actualiza todos los insumos. Conservar la versión
anterior mediante el control de versiones si se quiere comparar fechas.
No confundir una mejora del mapeo con una obra física. Ante HTTP 429, esperar
antes de reintentar el caso fallido; los casos ya descargados se conservan.
`--endpoint` permite elegir otra instancia Overpass compatible.

## Reglas del cálculo

- Grafo dirigido formado por nodos y segmentos OSM. Dos líneas que se cruzan
  geométricamente no se conectan salvo que compartan nodo.
- Distancia horizontal sobre cada segmento mediante fórmula de Haversine.
  Dijkstra minimiza metros; no es un ruteador de viaje más rápido.
- Auto: calles públicas motorizables, accesos y manos; restricciones `no_*` y
  `only_*` con nodo `via`. No interpreta restricciones condicionales, relaciones
  `via` por vías, carriles ni tráfico. Las restricciones no soportadas se cuentan.
- Peatón corto: vías caminables, escaleras, acceso `foot` y barreras. La mano
  vehicular no rige al peatón; se respeta `oneway:foot` si existe. Las calles con
  `sidewalk=separate` se excluyen para utilizar las veredas mapeadas aparte.
- Peatón sin escaleras registradas: el grafo peatonal excluye `highway=steps`,
  `wheelchair=no`, molinetes, pasos tipo `stile` y cordones `kerb=raised`.
  No es un perfil certificado de silla de ruedas: un dato ausente sigue siendo
  desconocido. Una rampa puede estar representada como `footway` sin `incline`.
- Los extremos se ajustan al nodo elegible más cercano; en auto se eligen nodos
  de calles principales del corredor configurado. Más de 45 m de ajuste produce
  `snap_too_far`. Las fichas muestran los ajustes; esos metros no se suman.
  No se inventan conexiones entre redes de distinto nivel o calles paralelas.
- La geometría del túnel debe cruzar una vía `railway=rail`, y cada ruta
  vehicular debe recorrer al menos uno de los IDs del túnel. Si el automóvil
  evita el túnel, no se calcula la razón de distancia frente a él.
- Ante desconexión se devuelve `no_path`, sin distancia. No prueba que no exista
  un camino físico: puede faltar una conexión en OSM o ser insuficiente el área.

Los extremos del piloto son bocacalles seleccionadas y documentadas, no puntos
automáticos a exactamente 200 m. Las comparaciones son internas a cada par;
no se presenta un ranking entre estructuras con distintas longitudes de acceso.

## Factor: sobrecosto del recorrido sin escaleras

```text
metros extra = distancia sin escaleras − distancia peatonal más corta
porcentaje extra = 100 × (distancia sin escaleras / distancia peatonal corta − 1)
```

Es el factor que aproxima la carga adicional sobre personas con movilidad
reducida, cochecitos y quienes llevan una bicicleta caminando. La alternativa
puede incluir rampas o un desvío por otra conexión; auditar su trazado antes de
llamarla “ruta por rampas”. Una bicicleta montada tiene reglas de circulación,
anchos y barreras diferentes y requiere un perfil adicional.

Resultados de ida del piloto (OSM 2026-09-04):

| Paso | Auto | Peatón corto | Sin escaleras registradas | Sobrecosto frente a peatón corto |
|---|---:|---:|---:|---:|
| Beiró | 527 m | 550 m | 653 m | +104 m · +18,9% |
| Constituyentes | 472 m | 491 m | 537 m | +46 m · +9,3% |
| Lacroze | 297 m | 300 m | 367 m | +67 m · +22,2% |

Las diferencias se calculan antes de redondear las cifras visibles.
No es una estimación del tiempo ahorrado: caminar sobre escaleras y rampas
tiene velocidades distintas. El campo `extra_minutes_distance_only` convierte
sólo los metros extra a 4,5 km/h; no incorpora pendiente ni esfuerzo.

## Otros indicadores y su alcance

- `step_way_count`: cantidad de objetos OSM de escalera recorridos. Un mismo
  tramo físico puede dividirse en varios objetos, no equivale a escalones.
- `wheelchair_no_way_count`: objetos explícitamente no aptos para silla de ruedas.
- `incline_way_count`: objetos con pendiente etiquetada distinta de cero.
- `turns_approx`: cambios de dirección de al menos 40°, omitiendo vértices
  sucesivos a menos de 8 m. No son maniobras de un navegador ni un conteo de
  todos los giros cerrados en los descansos.
- `mapped_crossings`: nodos `highway=crossing` y vías `footway=crossing`,
  agrupados a 20 m. Es un indicador de anotaciones disponibles: puede fusionar
  cruces cercanos u omitir bocacalles. No usar como total de calles a cruzar.
- `implicit_sidewalk_m`: longitud peatonal representada por ejes de calles.
  Indica dónde falta detalle para distinguir ambas veredas y cruces laterales.
- `model_minutes`: longitud / velocidad. Peatón 4,5 km/h, escaleras 2,5 km/h;
  auto 30 km/h o límite menor numérico. Sin esperas, estacionamiento ni tráfico.

## Auditoría antes de escalar

Verificar que los puntos estén en lados opuestos del ferrocarril y que la ruta
vehicular cruce el túnel elegido. Revisar que peatones no aparezcan sobre la
calzada prohibida, que las rampas se conecten correctamente y que las rutas no
rocen el borde de descarga. Ampliar el área y recalcular si hay dudas sobre una
alternativa más corta fuera del área.

Después contrastar ambas veredas y documentar pendiente, anchos, descansos,
cordones, iluminación, superficie y cruces reales con fecha y evidencia de
campo. Hasta entonces, el sitio presenta un piloto de red con auditoría
pendiente, sin puntaje compuesto ni afirmación de accesibilidad universal.

## Corrección de la primera observación

La comparación inicial de Constituyentes entre Pareja y Asunción era inválida:
ambos extremos quedaban al sur del paso del Mitre. Se reemplazó por un par junto
a Monroe, atravesando el objeto OSM 471284559. Por lo tanto, se retira la
conclusión inicial de “sin desvío ni escaleras”. En Lacroze, OSM no etiqueta
como escaleras todos los accesos cortos, pero marca varios como `wheelchair=no`;
la interfaz explica que cero escaleras registradas no confirma su ausencia.
