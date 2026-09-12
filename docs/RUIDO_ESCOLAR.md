# Ruido en las cuadras escolares

Fuente: [BA Data, ruido diurno 2018 CSV](https://data.buenosaires.gob.ar/dataset/mapa-ruido/resource/ce377913-43ac-4686-b244-0ac4c55012da/download), CC-BY-2.5-AR. Descarga: 12 de septiembre de 2026. El catálogo también ofrece 2025; este análisis usa expresamente el recurso de 2018 compartido para este cruce. No confundir fecha de descarga con fecha de estimación.

Guardar el CSV como `data/raw/noise-download` y ejecutar `python src/school_noise.py`. El derivado `data/processed/school-noise.json` conserva URL, SHA-256 y resultados por ID de cuadra.

Geometrías WKT en longitud/latitud, transformadas junto con los ejes de calle a EPSG:32721. Cada eje se divide en intervalos iguales de hasta 5 m; se consulta el polígono en el centro de cada intervalo. En límites compartidos se toma el rango superior una sola vez. No hay búsqueda de vecino cercano ni extrapolación sobre huecos.

El porcentaje alto usa puntos cubiertos como denominador y rangos con límite inferior ≥65 dBA como numerador. No se promedian decibeles. Solo se grafican cuadras con al menos 80% de muestras cubiertas. El corte de 65 dBA es una decisión exploratoria, no un umbral legal ni una recomendación OMS (no equivale a Lden ni a ruido interior). El resumen cuenta cuadras con al menos 50% de puntos cubiertos en esos rangos.

Resultado: 1.717 de 1.741 cuadras con cobertura suficiente; 1.477 cumplen el corte de mayoría. Las 24 restantes no se clasifican como silenciosas. El gráfico cruza porcentaje de recorrido en rangos ≥65 dBA con establecimientos distintos por cuadra; hay puntos superpuestos. No mide exposición individual de estudiantes, accesos ni aulas. Las asignaciones aproximadas de escuelas se conservan. Es una línea de base histórica sin filtros; no estima la reducción de ruido que produciría la propuesta.

Las cuatro explicaciones iniciales enlazan publicaciones de OMS y UNICEF. Se describe vulnerabilidad infantil a la contaminación sin afirmar que NO₂ sea el contaminante más peligroso ni atribuir niveles locales de NO₂ sin mediciones.
