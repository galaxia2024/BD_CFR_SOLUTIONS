"""Limpieza de las tablas originales (equivalente a la capa de staging del ETL).

Reglas: (1) eliminar tickets duplicados por ID_Ticket;  
(2) descartar tickets cuya fecha de cierre sea anterior a la de creación; 
(3) completar la prioridad vacía con "Media" y marcarla en la columna Prioridad_Imputada. Uso: python etl_limpieza.py
"""
import os
import pandas as pd

BASE = os.path.dirname(os.path.abspath(__file__))
ORIG = os.path.join(BASE, "datos", "originales")
PROC = os.path.join(BASE, "datos", "procesados")
os.makedirs(PROC, exist_ok=True)

t = pd.read_csv(os.path.join(ORIG, "tickets.csv"), parse_dates=["Fecha_Creacion", "Fecha_Cierre"])
n0 = len(t)
t = t.drop_duplicates(subset="ID_Ticket", keep="first")
n_dup = n0 - len(t)
invalidos = t["Fecha_Cierre"] < t["Fecha_Creacion"]
n_inv = int(invalidos.sum())
t = t[~invalidos].copy()
t["Prioridad_Imputada"] = t["Prioridad"].isna()
n_imp = int(t["Prioridad_Imputada"].sum())
t["Prioridad"] = t["Prioridad"].fillna("Media")
t["Horas_Resolucion"] = (t["Fecha_Cierre"] - t["Fecha_Creacion"]).dt.total_seconds() / 3600
t.to_csv(os.path.join(PROC, "tickets_limpios.csv"), index=False, encoding="utf-8")

resumen = pd.DataFrame([
    {"Regla": "Duplicados eliminados", "Registros": n_dup},
    {"Regla": "Cierre anterior a la creación (descartados)", "Registros": n_inv},
    {"Regla": "Prioridad vacía imputada como Media", "Registros": n_imp},
    {"Regla": "Tickets originales", "Registros": n0},
    {"Regla": "Tickets limpios", "Registros": len(t)},
])
resumen.to_csv(os.path.join(BASE, "resultados", "resumen_limpieza.csv"), index=False, encoding="utf-8")
print(resumen.to_string(index=False))
