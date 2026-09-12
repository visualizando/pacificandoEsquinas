# Matrícula por escuela — fuentes revisadas

Consulta: 11 de septiembre de 2026.

- Base usuaria Matrícula RA 2024: https://data.buenosaires.gob.ar/dataset/base-usuaria
- CSV descargado en `data/raw/matricula-ra2024.csv`: recurso 5ad995d3-0dad-4381-85e7-684c893a88d3. Campos `codigocript`, `turno`, `añoest`, `nivelens`, `totalu`, `Zona`, `sector`, entre otros. No contiene CUE, nombre ni domicilio.
- Documento metodológico: https://buenosaires.gob.ar/sites/default/files/2025-03/Documento%20metodol%C3%B3gico_2024.pdf define `Codigocript` como código seudónimo de unidad educativa. No hay clave pública de cruce identificada con nuestro padrón.
- Matrícula escolar 2024/2025: https://data.buenosaires.gob.ar/dataset/matricula-escolar presenta agregados por nivel/modalidad/gestión; no resuelve el cruce por escuela.
- Busca tu escuela contiene cifras puntuales dentro de descripciones institucionales, con fechas heterogéneas (por ejemplo matrícula 2023). No se adoptan como una base completa ni comparable.

Conclusión: existe matrícula por unidad educativa seudonimizada, pero no se encontró un dataset identificable que permita sumar estudiantes de las escuelas seleccionadas. Para ese cálculo se necesita matrícula por CUE y anexo, nivel y año (preferentemente turno), sin datos personales. No usar un promedio por escuela como si fuera matrícula observada. Tampoco intentar reconstruir los identificadores seudónimos.
## Ampliación de búsqueda: fuentes nacionales

Se revisaron SICDIE (`https://data.educacion.gob.ar/index.php`), el mapa educativo nacional (`https://mapa.educacion.gob.ar/mapa-interactivo`) y el padrón UEICEE por localización/oferta. La ficha nacional consultada para CUE-anexo 020071303 identifica correctamente el jardín de Ayacucho 1670, pero no presenta matrícula ni cantidad de alumnos en su contenido público. Esto verifica una ficha, no prueba ausencia en todas. El tablero nacional ofrece matrícula agregada; no se confirmó una descarga con matrícula y CUE-anexo utilizable para este cruce.

Una alternativa sería estimar estudiantes con promedios por nivel, gestión y zona de la base usuaria; tendría que mostrarse como estimación y tratar escuelas multinivel, turnos y sedes. No se incorporó al mapa como dato observado.
