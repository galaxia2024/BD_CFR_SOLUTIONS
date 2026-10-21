"""Experimento comparativo: línea base, RLS, RLM y Ridge (ver PROTOCOLO.md).

Implementa el ajuste por mínimos cuadrados ordinarios y Ridge con NumPy, sin
librerías de caja negra. Uso: python experimento.py
"""
import os, time, json, hashlib, platform, datetime
import numpy as np
import pandas as pd

VERSION = "1.0.0"
SEMILLA = 2026
BASE = os.path.dirname(os.path.abspath(__file__))
ORIG = os.path.join(BASE, "datos", "originales")
PROC = os.path.join(BASE, "datos", "procesados")
RES = os.path.join(BASE, "resultados")
os.makedirs(RES, exist_ok=True)

# ---------------- 1. Construcción del conjunto módulo-mes ----------------
tk = pd.read_csv(os.path.join(PROC, "tickets_limpios.csv"), parse_dates=["Fecha_Creacion"])
mod = pd.read_csv(os.path.join(ORIG, "modulos.csv"))
cli = pd.read_csv(os.path.join(ORIG, "clientes.csv"))
pry = pd.read_csv(os.path.join(ORIG, "proyectos.csv"), parse_dates=["Fecha_GoLive_Real"])

meses = pd.period_range("2023-01", "2025-12", freq="M")
tk["periodo"] = tk["Fecha_Creacion"].dt.to_period("M")
y = tk.groupby(["periodo", "ID_Modulo"]).size()

filas = []
for t_i, p in enumerate(meses, start=1):
    x1 = int(((cli["mes_alta"] <= t_i) & ((cli["mes_baja"].isna()) | (cli["mes_baja"] > t_i)) & (cli["tipo"] != 3)).sum())
    prev = meses[t_i - 2] if t_i > 1 else None
    x2 = int((pry["Fecha_GoLive_Real"].dt.to_period("M") == prev).sum()) if prev is not None else 0
    for _, m in mod.iterrows():
        filas.append({"t": t_i, "Anio": p.year, "Mes": p.month, "ID_Modulo": m["ID_Modulo"],
                      "Modulo": m["Modulo"], "X1_clientes_activos": x1, "X2_golive_mes_anterior": x2,
                      "X3_peso_modulo": m["Peso_Productividad"],
                      "Y_tickets": int(y.get((p, m["ID_Modulo"]), 0))})
ds = pd.DataFrame(filas)
ds.to_csv(os.path.join(PROC, "dataset_modulo_mes.csv"), index=False, encoding="utf-8")

# ---------------- 2. Partición temporal ----------------
train = ds[ds["t"] <= 29].reset_index(drop=True)
test = ds[ds["t"] >= 30].reset_index(drop=True)
FEAT = ["X1_clientes_activos", "X2_golive_mes_anterior", "X3_peso_modulo"]

# ---------------- 3. Núcleo: OLS y Ridge (contrato: arrays en memoria) ----------------
def ols_fit(X, y):
    """Mínimos cuadrados ordinarios: resuelve (X'X) b = X'y con intercepto."""
    Xd = np.column_stack([np.ones(len(X)), X])
    beta, *_ = np.linalg.lstsq(Xd, y, rcond=None)
    return beta

def ols_predict(beta, X):
    return beta[0] + X @ beta[1:]

def ridge_fit(X, y, lam, mu, sd):
    """Ridge sobre X estandarizado; el intercepto no se penaliza."""
    Z = (X - mu) / sd
    ym = y.mean()
    p = Z.shape[1]
    b = np.linalg.solve(Z.T @ Z + lam * np.eye(p), Z.T @ (y - ym))
    return np.concatenate([[ym], b])

def ridge_predict(beta, X, mu, sd):
    return beta[0] + ((X - mu) / sd) @ beta[1:]

rmse = lambda a, b: float(np.sqrt(np.mean((a - b) ** 2)))
mae = lambda a, b: float(np.mean(np.abs(a - b)))

def r2_adj(yv, yh, p):
    n = len(yv); r2 = 1 - np.sum((yv - yh) ** 2) / np.sum((yv - yv.mean()) ** 2)
    return float(1 - (1 - r2) * (n - 1) / (n - p - 1)), float(r2)

Xtr, Xte = train[FEAT].to_numpy(float), test[FEAT].to_numpy(float)
ytr, yte = train["Y_tickets"].to_numpy(float), test["Y_tickets"].to_numpy(float)
mu, sd = Xtr.mean(0), Xtr.std(0)

# VIF en entrenamiento
vif = {}
for j, f in enumerate(FEAT):
    others = np.delete(Xtr, j, axis=1)
    b = ols_fit(others, Xtr[:, j]); r2 = 1 - np.sum((Xtr[:, j] - ols_predict(b, others)) ** 2) / np.sum((Xtr[:, j] - Xtr[:, j].mean()) ** 2)
    vif[f] = float(1 / (1 - r2))

# Selección de lambda por origen móvil (solo entrenamiento)
LAMS = [0.01, 0.1, 1, 3, 10, 30, 100, 300, 1000]
BLOQUES = [(18, 20), (21, 23), (24, 26), (27, 29)]
cv = {}
for lam in LAMS:
    errs = []
    for a, b_ in BLOQUES:
        fit_d = train[train["t"] < a]; val_d = train[(train["t"] >= a) & (train["t"] <= b_)]
        Xf = fit_d[FEAT].to_numpy(float); m_, s_ = Xf.mean(0), Xf.std(0)
        be = ridge_fit(Xf, fit_d["Y_tickets"].to_numpy(float), lam, m_, s_)
        errs.append(rmse(val_d["Y_tickets"].to_numpy(float), ridge_predict(be, val_d[FEAT].to_numpy(float), m_, s_)))
    cv[lam] = float(np.mean(errs))
LAM = min(cv, key=cv.get)

# ---------------- 4. Ajuste y evaluación ----------------
res = {}
# Línea base: promedio histórico de entrenamiento por módulo
media_mod = train.groupby("ID_Modulo")["Y_tickets"].mean()
res["Línea base (promedio histórico)"] = dict(
    tr=train["ID_Modulo"].map(media_mod).to_numpy(), te=test["ID_Modulo"].map(media_mod).to_numpy(), p=8, coef=None)
# A. RLS
b_rls = ols_fit(train[["t"]].to_numpy(float), ytr)
res["A. Regresión lineal simple"] = dict(tr=ols_predict(b_rls, train[["t"]].to_numpy(float)),
                                         te=ols_predict(b_rls, test[["t"]].to_numpy(float)), p=1, coef=b_rls)
# B. RLM
b_rlm = ols_fit(Xtr, ytr)
res["B. Regresión lineal múltiple"] = dict(tr=ols_predict(b_rlm, Xtr), te=ols_predict(b_rlm, Xte), p=3, coef=b_rlm)
# C. Ridge
b_rdg = ridge_fit(Xtr, ytr, LAM, mu, sd)
res["C. Regresión Ridge"] = dict(tr=ridge_predict(b_rdg, Xtr, mu, sd), te=ridge_predict(b_rdg, Xte, mu, sd), p=3, coef=b_rdg)

def punt(e, cortes):
    for k, c in zip([5, 4, 3, 2], cortes):
        if e <= c:
            return k
    return 1

filas = []
for nom, r in res.items():
    r2a, r2 = r2_adj(ytr, r["tr"], r["p"])
    r_te, m_te = rmse(yte, r["te"]), mae(yte, r["te"])
    pr, pm = punt(r_te, [4.0, 8.0, 12.0, 16.0]), punt(m_te, [2.5, 5.0, 7.5, 10.0])
    filas.append({"Modelo": nom, "RMSE_entrenamiento": rmse(ytr, r["tr"]), "MAE_entrenamiento": mae(ytr, r["tr"]),
                  "RMSE_prueba": r_te, "MAE_prueba": m_te, "Razon_RMSE_prueba_entrenamiento": r_te / rmse(ytr, r["tr"]),
                  "R2_ajustado_entrenamiento": r2a, "R2_prueba": 1 - np.sum((yte - r["te"]) ** 2) / np.sum((yte - yte.mean()) ** 2),
                  "P_RMSE": pr, "P_MAE": pm, "P_total": round(0.6 * pr + 0.4 * pm, 2)})
met = pd.DataFrame(filas)
met.to_csv(os.path.join(RES, "metricas.csv"), index=False, encoding="utf-8", float_format="%.4f")

coef = pd.DataFrame([
    {"Modelo": "RLS", "b0": b_rls[0], "b_t": b_rls[1]},
    {"Modelo": "RLM", "b0": b_rlm[0], "b1_X1": b_rlm[1], "b2_X2": b_rlm[2], "b3_X3": b_rlm[3]},
    {"Modelo": f"Ridge (lambda={LAM}, escala estandarizada)", "b0": b_rdg[0], "b1_X1": b_rdg[1], "b2_X2": b_rdg[2], "b3_X3": b_rdg[3]},
])
coef.to_csv(os.path.join(RES, "coeficientes.csv"), index=False, encoding="utf-8", float_format="%.4f")
pd.DataFrame({"lambda": list(cv), "RMSE_validacion_movil": list(cv.values())}).to_csv(
    os.path.join(RES, "seleccion_lambda.csv"), index=False, float_format="%.4f")
pd.DataFrame({"variable": list(vif), "VIF": list(vif.values())}).to_csv(os.path.join(RES, "vif.csv"), index=False, float_format="%.4f")
pred = test[["Anio", "Mes", "Modulo", "Y_tickets"]].copy()
for nom, r in res.items():
    pred[nom] = np.round(r["te"], 2)
pred.to_csv(os.path.join(RES, "predicciones_prueba.csv"), index=False, encoding="utf-8")

# ---------------- 5. Tiempo del núcleo aislado ----------------
def cronometrar(f, reps=200):
    ts = []
    for _ in range(reps):
        t0 = time.perf_counter(); f(); ts.append((time.perf_counter() - t0) * 1000)
    return float(np.median(ts))
Ttr, Tte = train[["t"]].to_numpy(float), test[["t"]].to_numpy(float)
tiempos = {
    "A. Regresión lineal simple": cronometrar(lambda: ols_predict(ols_fit(Ttr, ytr), Tte)),
    "B. Regresión lineal múltiple": cronometrar(lambda: ols_predict(ols_fit(Xtr, ytr), Xte)),
    "C. Regresión Ridge": cronometrar(lambda: ridge_predict(ridge_fit(Xtr, ytr, LAM, mu, sd), Xte, mu, sd)),
}
pd.DataFrame({"Modelo": list(tiempos), "Mediana_ms_ajuste_prediccion": list(tiempos.values())}).to_csv(
    os.path.join(RES, "tiempos_nucleo.csv"), index=False, float_format="%.4f")

# ---------------- 6. Registro de la ejecución ----------------
def sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()
reg = {"id_ejecucion": datetime.datetime.now().strftime("EJ-%Y%m%d-%H%M%S"),
       "marca_tiempo": datetime.datetime.now().isoformat(timespec="seconds"),
       "version_algoritmo": VERSION, "semilla_generador": SEMILLA, "lambda_ridge": LAM,
       "particion": "entrenamiento t<=29 (232 casos), prueba t>=30 (56 casos)",
       "equipo": f"{platform.processor() or platform.machine()} | {platform.system()} | Python {platform.python_version()} | NumPy {np.__version__}",
       "sha256_dataset": sha(os.path.join(PROC, "dataset_modulo_mes.csv")),
       "sha256_protocolo": sha(os.path.join(BASE, "PROTOCOLO.md"))}
ruta = os.path.join(RES, "registro_ejecuciones.csv")
pd.DataFrame([reg]).to_csv(ruta, mode="a", header=not os.path.exists(ruta), index=False, encoding="utf-8")

print(met.to_string(index=False))
print("VIF:", vif); print("lambda:", LAM, cv); print(coef.to_string(index=False)); print(tiempos)
print("Y entrenamiento: media", ytr.mean(), "min", ytr.min(), "max", ytr.max(), "| prueba media", yte.mean())
