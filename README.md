# experimento_cfr

Experimento comparativo del proyecto de tesis *Implementación de un sistema de inteligencia de
negocios basado en procesos ETL y análisis predictivo de regresión lineal múltiple para la gestión
de la información operativa de TI en la empresa CFR Business & Solutions E.I.R.L.*

**Los datos son sintéticos.** Se generan con la estructura de la base de datos de la empresa,
pero no son registros reales. Ver `PROTOCOLO.md`.

## Requisitos
Python 3.10 o superior, NumPy, pandas y SciPy (`pip install numpy pandas scipy`).

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
