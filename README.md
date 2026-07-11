# Índice de Esquinas Peligrosas — CABA

Pipeline de datos que evalúa la peligrosidad de las intersecciones viales de la Ciudad de Buenos Aires para **peatones e infancias**, combinando geometría vial, mitigación existente (semáforos, reductores) y exposición (escuelas, siniestros). Produce artefactos estáticos: GeoPackage, GeoJSON y fichas JSON por esquina, más un mapa interactivo.

## Setup (una sola vez)

Requiere Python 3.11 (en Windows, `py -3.11`):

```
py -3.11 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Correr el pipeline

```
.venv\Scripts\python.exe run.py
```

Opciones: `--config otro.yaml` (config alternativo), `--top 10` (esquinas a mostrar en el resumen final).

Salidas en `data/processed/`:

| Archivo | Qué es |
|---|---|
| `esquinas.gpkg` | capa completa: geometría + todos los atributos y scores |
| `esquinas.geojson` | versión liviana que consume el mapa web |
| `fichas/<corner_id>.json` | una ficha por esquina: índice, desglose por eje, texto explicativo |
| `validation_report.json` | correlación Spearman índice vs. siniestros reales (si hay fuente de siniestros) |
| `run_metadata.json` | trazabilidad: scope, pesos aplicados, métodos de normalización, fuentes usadas |

## Ver el mapa y el reporte

El sitio necesita un servidor HTTP (no funciona abriendo el archivo directo, por CORS). Desde la **raíz del repo**:

```
.venv\Scripts\python.exe -m http.server 8765
```

- **Mapa interactivo**: <http://localhost:8765/web/index.html> — todas las esquinas coloreadas por índice, con filtro por comuna, selector de ranking (global / por comuna), gráficos de distribución y validación.
- **Reporte de intervenciones**: <http://localhost:8765/web/report.html> (o el botón *"Ver reporte detallado"* del mapa) — las top-N esquinas con su desglose por eje y una **propuesta de intervención de bajo costo** derivada de sus factores (acortar el cruce, enderezarlo, semáforo peatonal, calmar el tránsito). Consume `data/processed/reporte.json`.

## Configuración (`config.yaml`)

Todo lo relevante es configurable sin tocar código:

- **`scope`** — alcance geográfico: `comuna: N`, `barrio: <nombre>`, `bbox: [...]` o `all`.
- **`corner_definition`** — qué cuenta como esquina (`hybrid` default).
- **`node_merge_threshold_m`** — distancia para fusionar nodos de una misma esquina real (avenidas con cantero central).
- **`network`** — parámetros de detección: muestreo de rumbo, dedupe de calzadas separadas, mínimo de ramales.
- **`radii`** — radios de proximidad por eje (escuelas, siniestros, semáforos…).
- **`weights`** — peso de cada eje en el índice compuesto, agrupados en geometry / mitigation (resta) / exposure.
- **`normalization`** + **`axis_normalization`** — método global (`percentile`/`minmax`) y overrides por eje (`binary`, `zero_inflated`). Los ejes binarios se detectan solos.
- **`crash_severity_weights`** — ponderación de siniestros por gravedad (LEVE/GRAVE/MORTAL).
- **`ped_flow_weights`** — peso de cada transporte en el flujo peatonal (colectivo/subte/tren).
- **`report.fichas_top_n`** — cuántas fichas JSON escribir (`null` = todas). A escala ciudad conviene limitar.

## Toda la ciudad vs. una comuna

Con `scope.mode: all` el pipeline corre sobre toda CABA (~15.200 esquinas, ~2 min). Cada esquina trae **dos índices**: `indice` (percentil global, contra toda la ciudad) e `indice_comuna` (percentil dentro de su propia comuna, para equidad territorial). El mapa web permite filtrar por comuna y alternar entre ambos rankings; el `esquinas.geojson` y el `esquinas.gpkg` siempre traen todas las esquinas, y las fichas se limitan al `report.fichas_top_n`.

## Agregar una fuente de datos

1. Dejar el archivo en `data/raw/` con el nombre que espera `SOURCE_SPECS` en [src/ingest.py](src/ingest.py).
2. Documentarla en [data/raw/MANIFEST.md](data/raw/MANIFEST.md) (fecha, URL, licencia).
3. Correr `run.py`: los ejes que dependían de esa fuente se activan solos.

Si una fuente falta, los ejes que dependen de ella quedan `null` (no `0`) y el resto del pipeline corre igual. **Ojo**: cada dataset de BA Data tiene sus mañas (encoding mixto, CRS no-WGS84, separador `;`) — revisar el archivo antes de asumir el formato.

## Tests

```
.venv\Scripts\python.exe -m pytest tests/
```
