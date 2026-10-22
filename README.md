# experimento_cfr

Experimento comparativo del proyecto de tesis *Implementación de un sistema de inteligencia de
negocios basado en procesos ETL y análisis predictivo de regresión lineal múltiple para la gestión
de la información operativa de TI en la empresa CFR Business & Solutions E.I.R.L.*

**Los datos son sintéticos.** Se generan con la estructura de la base de datos de la empresa,
pero no son registros reales. Ver `PROTOCOLO.md`.

## Requisitos
Python 3.10 o superior, NumPy, pandas y SciPy (`pip install numpy pandas scipy`).
Para el prototipo y las pruebas: `pip install flask pytest pytest-playwright` y luego `python -m playwright install chromium`.

## Ejecución (en este orden)
```
python generador_cfr.py   # crea datos/originales/ con la semilla 2026
python etl_limpieza.py    # crea datos/procesados/tickets_limpios.csv
python experimento.py     # ajusta y evalúa; escribe resultados/
python contraste_hipotesis.py  # contrasta H1 y H2 (definido después del protocolo)
```
Con la misma semilla, las métricas de error se repiten exactamente en cualquier equipo.
Los tiempos de `resultados/tiempos_nucleo.csv` dependen del equipo.
Cada ejecución agrega una fila a `resultados/registro_ejecuciones.csv`.

## Diagramas UML (carpeta `uml/`)
Los 21 diagramas del proyecto están escritos en PlantUML (`*.puml`) con el estilo común
`estilo_rose.iuml`, inspirado en IBM Rational Rose. Las imágenes ya generadas están en `uml_png/`.
Para regenerarlas: `java -jar plantuml.jar -tpng -o ../uml_png uml/*.puml` (requiere Java y Graphviz).

## Base de datos (carpeta `sql/`)
`ddl_dw_cfr_bi.sql` crea la base `DW_CFR_BI` con los esquemas `stg` y `dw`, las dimensiones,
`Fact_Tickets`, `Fact_Demanda_Modulo_Mes`, `Ejecucion_Modelo`, `Prediccion_Modulo_Mes`,
`Log_Carga` y la vista `vw_Demanda_Modulo_Mes`. Es el mismo script del apartado 5.2 del proyecto.

`etl_procedimientos.sql` contiene los procedimientos del ETL nocturno (`usp_etl_extraer`, `usp_etl_limpiar`,
`usp_etl_cargar`, `usp_etl_demanda_modulo_mes` y el orquestador `usp_etl_nocturno`). `etl_nocturno.bat` lo
ejecuta con `sqlcmd`; se programa a las 23:00 en el Programador de tareas de Windows (SQL Server Express no
tiene Agente SQL Server). Orden: primero `ddl_dw_cfr_bi.sql`, luego `etl_procedimientos.sql`.

## Prototipo web de verificación (carpeta `prototipo/`)
Power BI es la herramienta de producción. El prototipo replica sus medidas principales para poder probarlas:
```
python prototipo/app.py      # abre http://127.0.0.1:5000
```
Pantallas: P-01 Proyección de demanda, P-02 Cumplimiento del SLA y P-03 Ejecuciones y cargas.
Las capturas usadas en el documento están en `capturas_prototipo/`.

## Pruebas automatizadas (carpeta `pruebas/`)
```
python -m pytest pruebas -v --junitxml=pruebas/reporte_pruebas.xml
```
Unitarias de la API (PU-01 a PU-10), regresión contra las métricas doradas (PR-01 a PR-06) y de extremo a
extremo con Playwright (PE-01 a PE-06): 28 ejecuciones. Requiere haber ejecutado antes los cuatro scripts.

## Evaluación económica (carpeta `evaluacion_economica/`)
```
python evaluacion_economica/calculo.py
```
Reproduce el flujo de caja a tres años, el VAN, la TIR, la relación B/C, el periodo de recuperación y el
análisis de sensibilidad del Capítulo VI. Los parámetros y sus fuentes están al inicio del script.
