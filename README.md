# bd_cfr

Experimento comparativo del proyecto de tesis *Implementación de un sistema de inteligencia de
negocios basado en procesos ETL y análisis predictivo de regresión lineal múltiple para la gestión
de la información operativa de TI en la empresa CFR Business & Solutions E.I.R.L.*

**Los datos son sintéticos.** Se generan con la estructura de la base de datos de la empresa,
pero no son registros reales. Ver `PROTOCOLO.md`.

## Requisitos
Python 3.10 o superior, NumPy y pandas (`pip install numpy pandas`).

## Ejecución (en este orden)
```
python generador_cfr.py   # crea datos/originales/ con la semilla 2026
python etl_limpieza.py    # crea datos/procesados/tickets_limpios.csv
python experimento.py     # ajusta y evalúa; escribe resultados/
```
Con la misma semilla, las métricas de error se repiten exactamente en cualquier equipo.
Los tiempos de `resultados/tiempos_nucleo.csv` dependen del equipo.
Cada ejecución agrega una fila a `resultados/registro_ejecuciones.csv`.
