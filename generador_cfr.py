"""Generador de datos sintéticos con la estructura de la base de datos de CFR.

Los datos NO son registros de la empresa. Reproducen la estructura de las tablas
Clientes, Consultores, Modulos, Proyectos y Tickets, con supuestos declarados en
PROTOCOLO.md. Uso: python generador_cfr.py
"""
import os
import numpy as np
import pandas as pd

SEMILLA = 2026
rng = np.random.default_rng(SEMILLA)
BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, "datos", "originales")
os.makedirs(OUT, exist_ok=True)

MESES = pd.period_range("2023-01", "2025-12", freq="M")  # 36 meses
T = len(MESES)

# ---------------- Módulos (supuesto: módulos estándar de SAP Business One) ----------
modulos = pd.DataFrame({
    "ID_Modulo": range(1, 9),
    "Modulo": ["Finanzas", "Ventas", "Compras", "Inventario", "Producción",
               "Bancos", "Socios de negocio", "Gestión de servicios"],
    "Peso_Productividad": [5, 4, 3, 4, 5, 3, 2, 2],
})

# ---------------- Consultores ----------------
consultores = pd.DataFrame({
    "ID_Consultor": range(1, 7),
    "nombres": [f"Consultor {i:02d}" for i in range(1, 7)],
    "apellidos": ["(sintético)"] * 6,
    "telefono": [f"9{rng.integers(10**7, 10**8)}" for _ in range(6)],
    "email": [f"consultor{i:02d}@ejemplo.pe" for i in range(1, 7)],
    "genero": rng.choice([1, 2], size=6),
    "estado": 1,
})

# ---------------- Clientes ----------------
N_CLI = 45
alta = np.concatenate([np.zeros(18, dtype=int),            # 18 clientes activos desde el inicio
                       np.sort(rng.integers(1, T, N_CLI - 18))])  # incorporaciones posteriores
baja = np.full(N_CLI, T)                                     # T = sigue activo
churn = rng.choice(N_CLI, size=7, replace=False)
for c in churn:
    baja[c] = min(T, alta[c] + int(rng.integers(6, 24)))
tipo = rng.choice([1, 2, 3], size=N_CLI, p=[0.35, 0.50, 0.15])  # 1 contrato, 2 bolsa, 3 cotización
clientes = pd.DataFrame({
    "ID_Cliente": range(1, N_CLI + 1),
    "tipo": tipo,
    "cliente": [f"Cliente {i:02d} S.A.C. (sintético)" for i in range(1, N_CLI + 1)],
    "ruc": [f"20{rng.integers(10**8, 10**9)}" for _ in range(N_CLI)],
    "direccion": "—", "distrito": "Lima", "ciudad": "Lima", "departamento": "Lima", "pais": "Perú",
    "estado": (baja >= T).astype(int),
    "mes_alta": alta + 1, "mes_baja": np.where(baja >= T, np.nan, baja + 1),
})

# ---------------- Proyectos de implementación (Consultoría) ----------------
# Cada cliente que se incorpora después del inicio tiene un proyecto cuyo Go-Live
# coincide con su mes de alta; se suman proyectos de ampliación.
proy = []
pid = 1
for i in range(18, N_CLI):
    golive = int(alta[i])
    proy.append((pid, i + 1, golive)); pid += 1
for _ in range(8):  # proyectos de ampliación en clientes existentes
    cli = int(rng.integers(1, N_CLI + 1)); golive = int(rng.integers(1, T))
    proy.append((pid, cli, golive)); pid += 1
proyectos = []
for p, cli, golive in proy:
    ini = MESES[max(0, golive - int(rng.integers(3, 7)))].start_time
    gl = MESES[golive].start_time + pd.Timedelta(days=int(rng.integers(0, 27)))
    plan = gl - pd.Timedelta(days=int(rng.integers(0, 40)))
    proyectos.append({"ID_Proyecto": p, "Nombre_Proyecto": f"Implementación SAP B1 {p:02d}",
                      "ID_Consultor": int(rng.integers(1, 7)), "Id_Cliente": cli,
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
SLA_H = {"Alta": 8, "Media": 24, "Baja": 72}
filas = []
tid = 1
for m in idx:
    mes = MESES[m]
    cli_act = np.where((alta <= m) & (baja > m) & (tipo != 3))[0] + 1
    for _, mod in modulos.iterrows():
        w = mod["Peso_Productividad"]
        cierre_fiscal = 1.15 if (mes.month in (1, 12) and mod["Modulo"] in ("Finanzas", "Bancos")) else 1.0
        lam = (1.5 + 0.22 * activos[m] * (w / 3) + 1.6 * golive_prev[m] * (w / 3) + 0.7 * w) * cierre_fiscal
        lam = rng.gamma(shape=25, scale=lam / 25)          # sobredispersión moderada
        n = rng.poisson(lam)
        for _ in range(n):
            pri = rng.choice(PRIOR, p=[0.2, 0.5, 0.3])
            crea = mes.start_time + pd.Timedelta(days=int(rng.integers(0, mes.days_in_month)),
                                                  hours=int(rng.integers(8, 18)), minutes=int(rng.integers(0, 60)))
            horas = float(rng.lognormal(np.log(SLA_H[pri] * 0.6), 0.6))
            abandono = rng.random() < 0.06
            if abandono:
                horas = 72.0 + float(rng.uniform(0, 2))
            filas.append({
                "ID_Ticket": tid, "ID_Cliente": int(rng.choice(cli_act)),
                "ID_Consultor": int(rng.integers(1, 7)), "ID_Modulo": int(mod["ID_Modulo"]),
                "Descripcion": f"Incidencia en {mod['Modulo']}", "Prioridad": pri,
                "Fecha_Creacion": crea, "Fecha_Cierre": crea + pd.Timedelta(hours=horas),
                "Escalado": "Sí" if rng.random() < 0.10 else "No",
                "Estado": "Cerrado por abandono" if abandono else "Cerrado",
            })
            tid += 1
tickets = pd.DataFrame(filas)

# ---------------- Registros defectuosos (para que la limpieza tenga efecto) ----------
n = len(tickets)
dup = tickets.sample(frac=0.01, random_state=SEMILLA)                       # 1 % duplicados
mal = tickets.sample(frac=0.005, random_state=SEMILLA + 1).index            # 0.5 % cierre < creación
tickets.loc[mal, "Fecha_Cierre"] = tickets.loc[mal, "Fecha_Creacion"] - pd.Timedelta(hours=5)
vac = tickets.sample(frac=0.005, random_state=SEMILLA + 2).index            # 0.5 % prioridad vacía
tickets.loc[vac, "Prioridad"] = None
tickets = pd.concat([tickets, dup]).sort_values(["Fecha_Creacion", "ID_Ticket"]).reset_index(drop=True)

# ---------------- Exportación ----------------
modulos.to_csv(os.path.join(OUT, "modulos.csv"), index=False, encoding="utf-8")
consultores.to_csv(os.path.join(OUT, "consultores.csv"), index=False, encoding="utf-8")
clientes.to_csv(os.path.join(OUT, "clientes.csv"), index=False, encoding="utf-8")
proyectos.to_csv(os.path.join(OUT, "proyectos.csv"), index=False, encoding="utf-8")
tickets.to_csv(os.path.join(OUT, "tickets.csv"), index=False, encoding="utf-8")
print(f"Tickets generados (con defectos): {len(tickets)}; base sin defectos: {n}")
