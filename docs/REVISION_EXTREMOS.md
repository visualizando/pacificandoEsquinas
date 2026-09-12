# Revisar extremos y repetir el análisis

## Ficha simplificada

La interfaz muestra únicamente A → B: el sentido permitido en túneles de mano única y un sentido fijo en los de doble mano. Los dos sentidos permanecen en los archivos para auditoría, pero ya no hay un selector público. El resumen y el detalle comparten `web/tunnel-chart.js`. El detalle destaca porcentaje y metros frente al auto, con tres barras desde cero: auto, caminata más corta y caminata sin escaleras. Los iconos de bici y cochecito representan llevarlos a pie, no resultados de una red ciclista. Las comparaciones dudosas no muestran una penalización numérica; los datos técnicos quedan plegados.

## Flujo de revisión

1. Abrir un cruce con **Ver más** y desplegar **Revisar los puntos A y B** debajo del mapa.
2. Arrastrar A/B o ingresar longitud y latitud. Elegir referencias a ambos lados del ferrocarril, fuera de los portales, aproximadamente una cuadra después de los accesos, manteniendo el criterio entre casos. Verificar las manos y no ubicar el punto sobre una colectora equivocada. No moverlos sólo para conseguir una diferencia mayor o menor.
3. Anotar qué se comprobó y qué falta: escalera, rampa, conexión, lado de vereda. Las rutas y cifras visibles corresponden a la última corrida. Al cambiar puntos se ocultan las líneas antiguas mientras el editor está abierto.
4. **Guardar revisión y seguir** marca el cruce y abre el siguiente sin revisar. Los borradores se conservan en el almacenamiento local de ese navegador y origen; no se guardan directamente en el repositorio.
5. **Exportar revisiones** descarga `endpoint-reviews.json` con todos los cruces marcados, sus extremos originales, nuevos extremos y notas. Los borradores sin marcar no se exportan. Conservar este archivo; borrar los datos del navegador elimina los borradores.
6. Desde la carpeta del proyecto, importar y recalcular:

```powershell
python src/tunnel_review.py --import-endpoints "C:\ruta\endpoint-reviews.json"
python src/tunnels_batch.py
python src/tunnel_review.py
python -m unittest discover -s tests -p "test_tunnel*.py"
```

El importador comprueba IDs únicos, coordenadas finitas dentro del área de la instantánea, separación mínima de 30 m y que la revisión no esté desactualizada. Guarda ajustes acumulativos en `data/tunnels/endpoint-overrides.json`; no modifica OSM. La corrida normal los aplica sobre `cases_all.json`. Versionar el archivo de ajustes junto con el resultado. Si `--prepare` cambia los extremos de base, el importador puede rechazar ajustes antiguos: rebasarlos explícitamente después de revisar, no descartarlos silenciosamente.

Después de recalcular, recargar la página y revisar **ambos sentidos**, especialmente los ajustes de cada red. La revisión de extremos no es una certificación de rampas ni una auditoría de accesibilidad. Si sigue el rodeo con puntos correctos, revisar la conectividad y los permisos del grafo: no inventar un paso para forzar una ruta.

## Diagnóstico reproducible, método 1.2

`python src/tunnel_review.py` genera `data/processed/tunnel-endpoint-audit.json` a partir del resultado. La misma función se ejecuta en cada nueva corrida y queda en `directions.*.endpoint_audit`.

Se retiene la diferencia principal cuando: el auto no atraviesa el túnel, faltan rutas, un extremo automático está a menos de 60 m de un portal, algún ajuste a la red supera 20 m, los extremos efectivos de auto y caminata difieren más de 20 m, o la ruta vehicular supera 1,6 veces la distancia recta. Estos umbrales son filtros de revisión, no demostraciones de error: una calle curva o una mano pueden justificar un rodeo. No se aplica ese filtro de rodeo a la caminata, porque justamente puede ser la barrera que buscamos medir.

Altolaguirre conserva además una advertencia específica sobre conexiones peatonales pendientes. El caso no queda validado por mover un pin. La corrida inicial detectó extremos cortos en Chorroarín, Monroe y Anchorena y ausencia de cruce vehicular en Altolaguirre, Pacheco y Paseo del Bajo. Tras la corrección direccional, quedan pendientes Chorroarín, Monroe, Avenida Congreso, Libertador, Paseo del Bajo y Zamudio por extremos o trazados, además de los accesos peatonales de Altolaguirre. Libertador ajusta puntos hasta 40 m.

### Túneles de mano única

```powershell
python src/tunnels_batch.py --align-oneway
```

La selección automática ahora recorre la calle **hacia atrás desde la entrada** para elegir A y **hacia adelante desde la salida** para elegir B, respetando la dirección de cada tramo. Prueba los extremos contra las restricciones de giro y exige que el auto use el túnel sin un rodeo mayor al umbral. A → B es la comparación principal; B → A queda como secundaria. Los dos perfiles peatonales usan esas mismas referencias, no otras elegidas para favorecer un resultado.

Las calzadas paralelas de sentidos opuestos no se confunden con un túnel de mano única. Las coordenadas anteriores se conservan en `previous_endpoints`. No se cambian manos ni conexiones de OSM. La revisión corrigió, entre otros, los rodeos vehiculares de Altolaguirre, Pacheco, Congreso, Crisólogo Larralde, Holmberg, Manuela Pedraza y Federico García Lorca. Altolaguirre mantiene pendiente la validación peatonal, aunque el auto ya cruza correctamente.

## Tarjetas

Dos barras: distancia del auto y de la caminata sin escaleras registradas. Comparten escala desde cero entre todos los casos del sentido elegido, incluso al filtrar. El número grande es **distancia sin escaleras − distancia en auto**, no la diferencia entre escaleras y rampas. Un valor negativo se conserva como tal; no se trunca a cero. Una comparación dudosa muestra **A revisar**, manteniendo las distancias individuales y el detalle del motivo. Los iconos de persona y cochecito representan el perfil sin escaleras, no garantizan aptitud física.
