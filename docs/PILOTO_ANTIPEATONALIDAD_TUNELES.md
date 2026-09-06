# Piloto de antipeatonalidad en pasos bajo nivel

> ARCHIVO HISTÓRICO, SUPERADO. La ruta inicial de Constituyentes no atravesaba
> el Mitre; se retiran su comparación y el ranking provisional de este documento.
> Los resultados vigentes se calculan con OSM y están documentados en
> [TUNELES_PROCEDIMIENTO.md](TUNELES_PROCEDIMIENTO.md), con rutas visibles en
> `web/index.html#tuneles`. Las observaciones siguientes se conservan como
> registro de la prueba exploratoria, no como resultados validados.

Fecha de observación: 2026-09-04.

## Objetivo

Probar si es posible comparar, con puntos equivalentes a ambos lados de una
vía ferroviaria, la continuidad ofrecida a automóviles y peatones. Este piloto
no define todavía un índice: busca comprobar qué variables discriminan los
casos y cuáles requieren verificación de campo.

## Casos y puntos de referencia

| Paso bajo nivel | Ferrocarril | Origen | Destino |
|---|---|---|---|
| Av. Francisco Beiró | Urquiza | Beiró y Terrada | Beiró y Zamudio |
| Av. de los Constituyentes | Mitre, ramal José León Suárez | Constituyentes y Pareja | Constituyentes y Asunción |
| Av. Federico Lacroze | Mitre | Lacroze y Amenábar | Lacroze y Conesa |

Los extremos corresponden a bocacalles reconocibles y no a domicilios
arbitrarios. Para una versión automatizada deberán reemplazarse por puntos
calculados a una distancia uniforme del cruce ferroviario.

## Resultado de la primera observación

Las cifras siguientes son una comprobación manual puntual de Google Maps y no
deben incorporarse todavía como fuente estable del pipeline.

| Paso | Auto | A pie | Exceso peatonal | Razón pie/auto | Recorrido peatonal observado |
|---|---:|---:|---:|---:|---|
| Beiró | 550 m, 1 min | 600 m, 9 min | +50 m | 1,09 | Desvío por Gutenberg, aproximadamente seis cambios de dirección y un tramo indicado con escaleras. Hay una alternativa de 750 m. |
| Constituyentes | 290 m, 2 min | 290 m, 4 min | 0 m | 1,00 | Continuidad recta; el ruteador no indica giros ni escaleras para este par de puntos. |
| Lacroze | 300 m, 1 min | 350 m, 5 min | +50 m | 1,17 | Desvío hacia Crámer, túnel peatonal específico, dos tramos indicados con escaleras y aproximadamente seis cambios de dirección. |

La razón de distancia es `distancia_a_pie / distancia_auto`. Los tiempos se
muestran como información descriptiva, pero no se comparan directamente para
puntuar: expresan velocidades propias de modos distintos y, para el automóvil,
pueden variar con el tránsito.

## Evidencia complementaria

La documentación del Gobierno de la Ciudad describe:

- Beiró como un paso de unos 300 m entre Terrada y Zamudio, con un único paso
  peatonal sobre la vereda norte, escaleras y rampas.
- Constituyentes como un paso con escaleras y rampas para movilidad reducida.
- Lacroze como un paso de unos 267 m entre Amenábar y Conesa, con escaleras y
  rampas para movilidad reducida.

En consecuencia, que exista una rampa no significa que la ruta peatonal más
corta sea accesible. Beiró y Lacroze muestran que el ruteador elige escaleras;
la longitud y complejidad de la alternativa sin escaleras deben medirse por
separado.

## Lectura preliminar

Para este movimiento concreto, la señal inicial es:

1. **Lacroze: fricción alta.** Mayor razón de desvío, recorrido segregado,
   dos escaleras y varios giros.
2. **Beiró: fricción media-alta.** Poco exceso de distancia, pero el recorrido
   deja el eje de la avenida, gira varias veces y usa escaleras.
3. **Constituyentes: fricción baja por distancia.** La ruta se mantiene recta,
   aunque todavía falta auditar la pendiente, el ancho, los cruces laterales y
   la experiencia de la rampa.

Esto confirma que la distancia por sí sola no mide la antipeatonalidad. El
desglose mínimo debería incluir:

- exceso y razón de distancia;
- cantidad de cambios de dirección;
- escaleras en la ruta más corta;
- distancia de una ruta sin escaleras;
- cruces vehiculares laterales;
- continuidad, ancho, iluminación y visibilidad de la pasarela.

## Limitaciones detectadas

- Las capturas iniciales de Beiró no usan el mismo destino en ambas rutas, por
  lo que sus cifras no son directamente comparables.
- Google Maps advierte que las instrucciones peatonales pueden no reflejar las
  condiciones reales.
- La indicación “mayormente plano” no representa bien el esfuerzo de subir y
  bajar escaleras o rampas cortas.
- Falta repetir cada itinerario en sentido inverso y sobre ambas veredas.
- Falta verificar en OpenStreetMap si rampas, escaleras y cruces están
  etiquetados con suficiente detalle para automatizar el análisis.

## Próxima prueba técnica

1. Extraer de OpenStreetMap la geometría de los tres pasos, pasarelas, rampas,
   escaleras y calles laterales.
2. Fijar puntos a 200 m del cruce sobre el eje vial y conservar sus
   coordenadas como fuente de verdad.
3. Calcular tres rutas: automóvil, peatón más corto y peatón sin escaleras.
4. Repetir en ambos sentidos y para ambas veredas cuando sean distinguibles.
5. Dibujar las rutas superpuestas y verificar manualmente los cruces.
6. Sólo después definir una fórmula de puntaje y probarla en más túneles.

## Fuentes de contraste

- Gobierno de la Ciudad, [Paso Bajo Nivel Beiró y vías del FFCC Urquiza](https://buenosaires.gob.ar/gcaba_historico/desarrollourbano/desarrollo/paso-bajo-nivel-beiro-y-vias-del-ffcc-urquiza).
- Gobierno de la Ciudad, [montaje del puente ferroviario del paso bajo nivel de Constituyentes](https://buenosaires.gob.ar/gcaba_historico/noticias/montaje-del-nuevo-puente-ferroviario-del-paso-bajo-nivel-de-av-de-los).
- Gobierno de la Ciudad, [inauguración del paso bajo nivel Federico Lacroze](https://buenosaires.gob.ar/gcaba_historico/noticias/se-inauguro-el-paso-bajo-nivel-de-la-avenida-federico-lacroze).
