# Protocolo del experimento comparativo (fijado antes de la ejecución)

Proyecto: Sistema de inteligencia de negocios con ETL y regresión lineal múltiple
para la gestión de la información operativa de TI en CFR Business & Solutions E.I.R.L.

## 1. Naturaleza de los datos
- Los datos son **sintéticos**. Se generan con `generador_cfr.py` siguiendo la
  estructura real de la base de datos proporcionada por la empresa (tablas Clientes,
  Consultores, Módulos, Proyectos y Tickets). **No son registros de la empresa.**
- Supuestos declarados y pendientes de validación con la empresa: 8 módulos estándar
  de SAP Business One, 6 consultores de soporte, 45 clientes, 36 meses (enero de 2023
  a diciembre de 2025) y tres niveles de prioridad con SLA de 8, 24 y 72 horas.
- Semilla única del generador: **2026**.

## 2. Recorrido de los datos
1. `generador_cfr.py` escribe las tablas originales en `datos/originales/`, con un
   pequeño porcentaje de registros defectuosos (duplicados, fechas de cierre anteriores
   a la creación y prioridades vacías), para que la limpieza tenga efecto real.
2. `etl_limpieza.py` aplica las reglas de limpieza y produce `datos/procesados/`.
3. `experimento.py` agrega los tickets por módulo y mes, construye las variables,
   particiona, ajusta los candidatos y los evalúa.

## 3. Unidad de análisis y variables
- Unidad: módulo-mes (8 módulos x 36 meses = 288 casos).
- Y: cantidad de tickets creados en el módulo durante el mes (conteo entero observado).
  La predicción Ŷ es continua (número real).
- X1: clientes activos con contrato o bolsa de horas en el mes.
- X2: proyectos con Go-Live real en el mes anterior.
- X3: peso de productividad del módulo (1 a 5).
- t: índice del mes (1 a 36), usado solo por la regresión lineal simple.

## 4. Partición
- Temporal y determinista: entrenamiento = meses 1 a 29 (enero 2023 a mayo 2025,
  232 casos); prueba = meses 30 a 36 (junio a diciembre 2025, 56 casos).
- Ningún dato de prueba interviene en el ajuste ni en la elección de hiperparámetros.

## 5. Candidatos y línea base
- Línea base (proceso histórico): promedio de entrenamiento de cada módulo.
- A. Regresión lineal simple (RLS): Y ~ t, mínimos cuadrados ordinarios.
- B. Regresión lineal múltiple (RLM): Y ~ X1 + X2 + X3, mínimos cuadrados ordinarios.
- C. Regresión Ridge: mismas variables que B, estandarizadas con la media y desviación
  del entrenamiento; λ elegido en {0.01, 0.1, 1, 3, 10, 30, 100, 300, 1000} por
  validación con origen móvil dentro del entrenamiento (bloques de validación:
  meses 18-20, 21-23, 24-26 y 27-29).

## 6. Métricas y regla de decisión
- RMSE y MAE en tickets, sobre entrenamiento y prueba; R² ajustado en entrenamiento;
  VIF de X1, X2 y X3.
- Puntaje por métrica de prueba según la escala de la Tabla de criterios cardinales:
  RMSE: 5 si E ≤ 4.0; 4 si 4.0 < E ≤ 8.0; 3 si 8.0 < E ≤ 12.0; 2 si 12.0 < E ≤ 16.0; 1 si E > 16.0.
  MAE:  5 si E ≤ 2.5; 4 si 2.5 < E ≤ 5.0; 3 si 5.0 < E ≤ 7.5; 2 si 7.5 < E ≤ 10.0; 1 si E > 10.0.
- P_total = 0.60 x P_RMSE + 0.40 x P_MAE.
- Se selecciona el mayor P_total. Empate: menor RMSE de prueba; si persiste,
  el modelo sin hiperparámetros.
- Sobreajuste: se informa la razón RMSE_prueba / RMSE_entrenamiento.

## 7. Medición del núcleo
- Contrato del núcleo: entrada = matriz X (n x p, float64) y vector y (n) en memoria;
  salida = vector de coeficientes y vector Ŷ.
- Se mide solo ajuste + predicción, 200 repeticiones, mediana en milisegundos.
  Quedan fuera la lectura de archivos, el ETL y el renderizado en Power BI.
