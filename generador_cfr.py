"""Generador de datos sintéticos con la estructura de la base de datos de CFR (versión 2).

Los datos NO son registros de la empresa. La versión 2 usa los parámetros informados por la
empresa y por la entrevista E-01 (ver DESVIACIONES.md). Uso: python generador_cfr.py
"""
import os
import numpy as np
import pandas as pd

VERSION_GENERADOR = "2.1.0"
SEMILLA = 2026
rng = np.random.default_rng(SEMILLA)
BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, "datos", "originales")
os.makedirs(OUT, exist_ok=True)

MESES = pd.period_range("2023-10", "2026-09", freq="M")  # 36 meses; el último refleja la situación actual
T = len(MESES)

# ---------------- Módulos: 19 (E-01). Los cuatro de mayor demanda tienen peso 5 ----------------
nombres = ["Facturación electrónica", "Compras", "Ventas", "Validaciones",
           "Finanzas", "Bancos", "Inventario",
           "Libros electrónicos (PLE)", "Detracciones y retenciones", "Socios de negocio", "Producción",
           "Gestión de servicios", "Activos fijos", "Informes", "Administración",
           "Oportunidades (CRM)", "Recursos humanos", "MRP", "Gestión de proyectos"]
pesos = [5, 5, 5, 5, 4, 4, 4, 3, 3, 3, 3, 2, 2, 2, 2, 1, 1, 1, 1]
modulos = pd.DataFrame({"ID_Modulo": range(1, 20), "Modulo": nombres, "Peso_Productividad": pesos})

# ---------------- Consultores: 11 (3 consultoría, 6 soporte, 2 desarrollo) ----------------
areas = ["Consultoría"] * 3 + ["Soporte"] * 6 + ["Desarrollo"] * 2
consultores = pd.DataFrame({
    "ID_Consultor": range(1, 12),
    "nombres": [f"Consultor {i:02d}" for i in range(1, 12)],
    "apellidos": ["(sintético)"] * 11,
    "area": areas,
    "telefono": [f"9{rng.integers(10**7, 10**8)}" for _ in range(11)],
    "email": [f"consultor{i:02d}@ejemplo.pe" for i in range(1, 12)],
    "genero": rng.choice([1, 2], size=11),
    "estado": 1,
})
SOPORTE = consultores.loc[consultores["area"] == "Soporte", "ID_Consultor"].to_numpy()
CONSULTORIA = consultores.loc[consultores["area"] == "Consultoría", "ID_Consultor"].to_numpy()

# ---------------- Clientes: 39 = 19 contrato + 3 bolsa + 11 cotización activos + 6 inactivos ----------------
# Los 6 inactivos fueron clientes con contrato o bolsa que dejaron la empresa durante el periodo.
tipo = np.array([1] * 19 + [2] * 3 + [3] * 11 + [1] * 5 + [2] * 1)
N_CLI = len(tipo)                                      # 39
activo_final = np.array([True] * 33 + [False] * 6)
alta = np.zeros(N_CLI, dtype=int)
baja = np.full(N_CLI, T)                               # T = sigue activo
idx_cb_act = np.arange(22)                             # contrato o bolsa, activos al final
iniciales = rng.choice(idx_cb_act, size=10, replace=False)   # 10 activos desde el inicio
for i in idx_cb_act:
    if i not in iniciales:
        alta[i] = int(rng.integers(1, T - 1))          # se incorporan durante el periodo
for i in range(33, 39):                                # inactivos: estaban al inicio y se fueron
    alta[i] = 0
    baja[i] = int(rng.integers(8, T - 2))
for i in range(22, 33):                                # cotización: no generan tickets de soporte
    alta[i] = int(rng.integers(0, T - 1))
clientes = pd.DataFrame({
    "ID_Cliente": range(1, N_CLI + 1),
    "tipo": tipo,
    "cliente": [f"Cliente {i:02d} S.A.C. (sintético)" for i in range(1, N_CLI + 1)],
    "ruc": [f"20{rng.integers(10**8, 10**9)}" for _ in range(N_CLI)],
    "direccion": "—", "distrito": "Lima", "ciudad": "Lima", "departamento": "Lima", "pais": "Perú",
    "estado": activo_final.astype(int),
    "mes_alta": alta + 1, "mes_baja": np.where(baja >= T, np.nan, baja + 1),
})

# ---------------- Proyectos: implementación por cada cliente nuevo y ampliaciones ----------------
proy = []
pid = 1
for i in idx_cb_act:
    if alta[i] > 0:
        proy.append((pid, i + 1, int(alta[i]))); pid += 1
for _ in range(8):
    cli = int(rng.choice(idx_cb_act)) + 1
    proy.append((pid, cli, int(rng.integers(1, T)))); pid += 1
proyectos = []
for p, cli, golive in proy:
    ini = MESES[max(0, golive - int(rng.integers(3, 7)))].start_time
    gl = MESES[golive].start_time + pd.Timedelta(days=int(rng.integers(0, 27)))
    plan = gl - pd.Timedelta(days=int(rng.integers(0, 40)))
    proyectos.append({"ID_Proyecto": p, "Nombre_Proyecto": f"Implementación SAP B1 {p:02d}",
                      "ID_Consultor": int(rng.choice(CONSULTORIA)), "Id_Cliente": cli,
                      "Fecha_Inicio": ini.date(), "Fecha_Cierre_Planificada": plan.date(),
                      "Fecha_GoLive_Real": gl.date(), "Estado": "Cerrado"})
proyectos = pd.DataFrame(proyectos)

# ---------------- Variables mensuales del proceso generador ----------------
idx = np.arange(T)
activos = np.array([((alta <= m) & (baja > m) & (tipo != 3)).sum() for m in idx])
golive_mes = np.array([(proyectos["Fecha_GoLive_Real"].map(lambda d: pd.Period(d, "M")) == MESES[m]).sum() for m in idx])
golive_prev = np.concatenate([[0], golive_mes[:-1]])

# ---------------- Tickets ----------------
PRIOR = ["Alta", "Media", "Baja"]
SLA_H = {1: 24, 2: 48}            # horas por tipo de contrato (parámetro pendiente de validar)
FACTOR = {"Alta": 0.4, "Media": 0.7, "Baja": 1.0}
# Demanda esperada por módulo y mes; el total del periodo se fija en 3 334 tickets (dato de la empresa)
TOTAL_TICKETS = 3334
lam = np.zeros((T, len(modulos)))
for m in idx:
    for k, mod in modulos.iterrows():
        w = mod["Peso_Productividad"]
        cierre_fiscal = 1.15 if (MESES[m].month in (1, 12) and mod["Modulo"] in ("Finanzas", "Libros electrónicos (PLE)")) else 1.0
        base = (0.3 + 0.12 * activos[m] * (w / 3) + 0.8 * golive_prev[m] * (w / 3) + 0.4 * w) * cierre_fiscal
        lam[m, k] = rng.gamma(shape=25, scale=base / 25)
conteos = rng.multinomial(TOTAL_TICKETS, (lam / lam.sum()).ravel()).reshape(lam.shape)
filas = []
tid = 1
for m in idx:
    mes = MESES[m]
    cli_act = np.where((alta <= m) & (baja > m) & (tipo != 3))[0] + 1
    for k, mod in modulos.iterrows():
        for _ in range(int(conteos[m, k])):
            cli = int(rng.choice(cli_act))
            pri = rng.choice(PRIOR, p=[0.2, 0.5, 0.3])
            sla = SLA_H[int(tipo[cli - 1])]
            crea = mes.start_time + pd.Timedelta(days=int(rng.integers(0, mes.days_in_month)),
                                                  hours=int(rng.integers(8, 18)), minutes=int(rng.integers(0, 60)))
            horas = float(rng.lognormal(np.log(sla * FACTOR[pri]), 0.6))
            abandono = rng.random() < 0.06
            if abandono:
                horas = 72.0 + float(rng.uniform(0, 2))
            filas.append({
                "ID_Ticket": tid, "ID_Cliente": cli,
                "ID_Consultor": int(rng.choice(SOPORTE)), "ID_Modulo": int(mod["ID_Modulo"]),
                "Descripcion": f"Incidencia en {mod['Modulo']}", "Prioridad": pri,
                "Fecha_Creacion": crea, "Fecha_Cierre": crea + pd.Timedelta(hours=horas),
                "Escalado": "Sí" if rng.random() < 0.10 else "No",
                "Estado": "Cerrado por abandono" if abandono else "Cerrado",
            })
            tid += 1
tickets = pd.DataFrame(filas)

# ---------------- Registros defectuosos (para que la limpieza tenga efecto) ----------
n = len(tickets)
dup = tickets.sample(frac=0.01, random_state=SEMILLA)
mal = tickets.sample(frac=0.005, random_state=SEMILLA + 1).index
tickets.loc[mal, "Fecha_Cierre"] = tickets.loc[mal, "Fecha_Creacion"] - pd.Timedelta(hours=5)
vac = tickets.sample(frac=0.005, random_state=SEMILLA + 2).index
tickets.loc[vac, "Prioridad"] = None
tickets = pd.concat([tickets, dup]).sort_values(["Fecha_Creacion", "ID_Ticket"]).reset_index(drop=True)

for nombre, df in [("modulos", modulos), ("consultores", consultores), ("clientes", clientes),
                   ("proyectos", proyectos), ("tickets", tickets)]:
    df.to_csv(os.path.join(OUT, f"{nombre}.csv"), index=False, encoding="utf-8")
print(f"Generador {VERSION_GENERADOR}: tickets {len(tickets)} (sin defectos: {n}); "
      f"clientes {N_CLI}; activos con contrato o bolsa al final: {activos[-1]}; proyectos: {len(proyectos)}")
