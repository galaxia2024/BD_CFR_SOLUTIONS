"""Contraste de las hipótesis específicas H1 y H2 con los resultados del experimento.

H1: proporción de tickets inconsistentes que llega al almacén = 0 %.
H2: mu_d > 0, donde d = (error de la línea base)^2 - (error de la RLM)^2 en los
    casos de prueba; prueba t pareada unilateral con alfa = 0.05.
H3 (tiempo del reporte gerencial) requiere medición en la empresa y no se contrasta aquí.
Uso: python contraste_hipotesis.py  (después de experimento.py)
"""
import os
import numpy as np
import pandas as pd
from scipy import stats

BASE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(BASE, "resultados")
ALFA = 0.05

# ---- H1: inconsistencias antes y después del ETL ----
orig = pd.read_csv(os.path.join(BASE, "datos", "originales", "tickets.csv"), parse_dates=["Fecha_Creacion", "Fecha_Cierre"])
limp = pd.read_csv(os.path.join(BASE, "datos", "procesados", "tickets_limpios.csv"), parse_dates=["Fecha_Creacion", "Fecha_Cierre"])

def inconsistentes(df, marca=None):
    dup = df.duplicated(subset="ID_Ticket", keep="first")
    fechas = df["Fecha_Cierre"] < df["Fecha_Creacion"]
    vacia = df["Prioridad"].isna()
    if marca is not None:  # valores imputados sin marca
        vacia = vacia | (df[marca] & df["Prioridad"].isna())
    return int((dup | fechas | vacia).sum())

n_o, i_o = len(orig), inconsistentes(orig)
n_l, i_l = len(limp), inconsistentes(limp, "Prioridad_Imputada")

# ---- H2: RLM frente a la línea base ----
p = pd.read_csv(os.path.join(RES, "predicciones_prueba.csv"))
y = p["Y_tickets"].to_numpy(float)
d = (y - p["Línea base (promedio histórico)"].to_numpy()) ** 2 - (y - p["B. Regresión lineal múltiple"].to_numpy()) ** 2
t = stats.ttest_1samp(d, 0.0, alternative="greater")

filas = [
    {"Hipotesis": "H1", "Indicador": "Tickets inconsistentes en origen (%)", "Valor": round(100 * i_o / n_o, 2)},
    {"Hipotesis": "H1", "Indicador": "Tickets inconsistentes en el almacén (%)", "Valor": round(100 * i_l / n_l, 2)},
    {"Hipotesis": "H1", "Indicador": "Decisión", "Valor": "Se rechaza H0" if i_l == 0 else "No se rechaza H0"},
    {"Hipotesis": "H2", "Indicador": "Casos de prueba", "Valor": len(d)},
    {"Hipotesis": "H2", "Indicador": "Media de d (tickets^2)", "Valor": round(float(d.mean()), 4)},
    {"Hipotesis": "H2", "Indicador": "Estadístico t", "Valor": round(float(t.statistic), 4)},
    {"Hipotesis": "H2", "Indicador": "Valor p (unilateral)", "Valor": round(float(t.pvalue), 4)},
    {"Hipotesis": "H2", "Indicador": "Decisión", "Valor": "Se rechaza H0" if t.pvalue < ALFA else "No se rechaza H0"},
]
out = pd.DataFrame(filas)
out.to_csv(os.path.join(RES, "contraste_hipotesis.csv"), index=False, encoding="utf-8")
print(out.to_string(index=False))
