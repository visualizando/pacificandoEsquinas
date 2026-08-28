# Suplemento anonimizado del Power BI

El dataset extraído del tablero público contiene información útil para
validar el índice —hechos fatales, víctimas y período 2009–2025— pero también
campos personales que no deben copiarse al repositorio ni al sitio.

`src/powerbi_supplement.py` genera un archivo local agregado por `corner_id`.
Solo conserva conteos y aplica una lista blanca de variables. DNI, dominios,
domicilios, números de causa, observaciones y texto libre quedan excluidos.

Ejemplo de ejecución:

```powershell
python src/powerbi_supplement.py `
  --hechos C:\ruta\Base_Hechos.csv `
  --victimas C:\ruta\Base_Victimas.csv `
  --corners data\processed\esquinas.geojson `
  --output data\processed\powerbi_corner_aggregates.json
```

El resultado incluye por esquina:

- hechos fatales totales y para 2019–2025;
- ventanas 2019–2021 y 2023–2025;
- víctimas totales;
- víctimas peatones, ciclistas, menores de 15 y mayores de 64 años.

## Uso metodológico recomendado

Por ahora este suplemento debe usarse para análisis y validación, no como un
nuevo factor del índice. En particular, las tablas de velocidades del Power BI
solo cubren lugares asociados a hechos fatales y no reemplazan una capa completa
de límites de velocidad de la red vial.

El JSON generado se mantiene fuera de Git hasta completar una revisión de
procedencia, privacidad y licencia.

## Validación independiente de las fuentes crudas

Una vez generado el suplemento se puede evaluar el riesgo geométrico contra
las fatalidades recientes, sin incorporar esas fatalidades al predictor:

```powershell
python src/validate_powerbi.py `
  --corners data\processed\esquinas.geojson `
  --supplement data\processed\powerbi_corner_aggregates.json `
  --metadata data\processed\run_metadata.json `
  --output data\processed\powerbi_validation_report.json
```

El informe calcula correlaciones de Spearman y compara la tasa de fatalidades
recientes del decil geométrico superior con el promedio de toda la ciudad.
