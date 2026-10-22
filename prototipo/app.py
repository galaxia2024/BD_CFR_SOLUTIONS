"""Prototipo web de verificación del sistema BI de CFR (versión 1.0.0).

Power BI es la herramienta de producción. Este prototipo replica sus medidas principales
(proyección RLM, semáforo SLA y registro de ejecuciones) sobre los mismos archivos del
experimento, para que puedan verificarse con pruebas automatizadas.
Uso: python prototipo/app.py  ->  http://127.0.0.1:5000
"""
import os
import pandas as pd
from flask import Flask, jsonify, request, send_from_directory

VERSION = "1.0.0"
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROC = os.path.join(BASE, "datos", "procesados")
ORIG = os.path.join(BASE, "datos", "originales")
RES = os.path.join(BASE, "resultados")
ESTATICO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")

MIN_MESES = 3                                   # mínimo de meses históricos para proyectar
SLA_HORAS = {"Contrato": 24, "Bolsa de horas": 48}   # Dim_SLA (pendiente de validar con la empresa)
TIPO = {1: "Contrato", 2: "Bolsa de horas", 3: "Cotización"}
BONO = 35.00                                    # bono por ticket cerrado dentro del SLA (S/)
UMBRAL_AMBAR = 0.70                             # ámbar desde el 70 % del plazo


def cargar():
    """Lee los archivos una sola vez; equivale a la consulta al almacén."""
    ds = pd.read_csv(os.path.join(PROC, "dataset_modulo_mes.csv"))
    ds["Periodo"] = ds["Anio"].astype(str) + "-" + ds["Mes"].astype(str).str.zfill(2)
    coef = pd.read_csv(os.path.join(RES, "coeficientes.csv")).set_index("Modelo").loc["RLM"]
    tk = pd.read_csv(os.path.join(PROC, "tickets_limpios.csv"))
    cli = pd.read_csv(os.path.join(ORIG, "clientes.csv"))[["ID_Cliente", "tipo"]]
    tk = tk.merge(cli, on="ID_Cliente", how="left")
    tk["Tipo_Contrato"] = tk["tipo"].map(TIPO)
    tk["Horas_Limite"] = tk["Tipo_Contrato"].map(SLA_HORAS)
    tk["Uso_Plazo"] = tk["Horas_Resolucion"] / tk["Horas_Limite"]
    tk["Semaforo"] = "Verde"
    tk.loc[tk["Uso_Plazo"] >= UMBRAL_AMBAR, "Semaforo"] = "Ámbar"
    tk.loc[tk["Uso_Plazo"] > 1, "Semaforo"] = "Rojo"
    ejec = pd.read_csv(os.path.join(RES, "registro_ejecuciones.csv"))
    limp = pd.read_csv(os.path.join(RES, "resumen_limpieza.csv"))
    return ds, coef, tk, ejec, limp


def crear_app(datos=None):
    app = Flask(__name__, static_folder=None)
    ds, coef, tk, ejec, limp = datos or cargar()
    b0, b1, b2, b3 = (float(coef[c]) for c in ["b0", "b1_X1", "b2_X2", "b3_X3"])
    periodos = sorted(ds["Periodo"].unique())

    def error(msg, codigo):
        return jsonify({"error": msg}), codigo

    @app.get("/")
    def inicio():
        return send_from_directory(ESTATICO, "index.html")

    @app.get("/api/modulos")
    def modulos():
        m = ds[["ID_Modulo", "Modulo", "X3_peso_modulo"]].drop_duplicates().sort_values("ID_Modulo")
        return jsonify({"modulos": [{"id": int(r.ID_Modulo), "nombre": r.Modulo, "peso": int(r.X3_peso_modulo)}
                                    for r in m.itertuples()],
                        "periodos": periodos})

    @app.get("/api/proyeccion")
    def proyeccion():
        try:
            mod = int(request.args["modulo"])
            desde, hasta = request.args["desde"], request.args["hasta"]
        except (KeyError, ValueError):
            return error("Error: parámetros incompletos (modulo, desde, hasta)", 400)
        if mod not in set(ds["ID_Modulo"]):
            return error("Error: módulo no registrado", 404)
        if desde > hasta:
            return error("Error: el periodo inicial es posterior al final", 400)
        sel = ds[(ds["ID_Modulo"] == mod) & (ds["Periodo"] >= desde) & (ds["Periodo"] <= hasta)]
        if len(sel) < MIN_MESES:
            return error("Error: Data histórica insuficiente", 422)
        # Medida DAX equivalente: Y estimada = Beta0 + Beta1*X1 + Beta2*X2 + Beta3*X3 (ejecución vigente)
        yhat = b0 + b1 * sel["X1_clientes_activos"] + b2 * sel["X2_golive_mes_anterior"] + b3 * sel["X3_peso_modulo"]
        err = sel["Y_tickets"] - yhat
        filas = [{"periodo": p, "real": int(y), "estimado": round(float(e), 2),
                  "x1": int(a), "x2": int(b), "x3": int(c)}
                 for p, y, e, a, b, c in zip(sel["Periodo"], sel["Y_tickets"], yhat, sel["X1_clientes_activos"],
                                             sel["X2_golive_mes_anterior"], sel["X3_peso_modulo"])]
        return jsonify({"modulo": sel["Modulo"].iloc[0], "meses": filas,
                        "ecuacion": {"b0": b0, "b1": b1, "b2": b2, "b3": b3},
                        "rmse": round(float((err ** 2).mean() ** 0.5), 4),
                        "mae": round(float(err.abs().mean()), 4),
                        "total_real": int(sel["Y_tickets"].sum()),
                        "total_estimado": round(float(yhat.sum()), 2)})

    @app.get("/api/sla")
    def sla():
        tipo = request.args.get("tipo_contrato", "Contrato")
        prio = request.args.get("prioridad", "Todas")
        if tipo not in SLA_HORAS:
            return error("Error: tipo de contrato no válido", 400)
        if prio not in ("Todas", "Alta", "Media", "Baja"):
            return error("Error: prioridad no válida", 400)
        sel = tk[tk["Tipo_Contrato"] == tipo]
        if prio != "Todas":
            sel = sel[sel["Prioridad"] == prio]
        conteo = sel["Semaforo"].value_counts()
        cumple = sel["Uso_Plazo"] <= 1
        bono = float((cumple & (sel["Estado"] == "Cerrado")).sum() * BONO)
        ult = sel.sort_values("Fecha_Creacion", ascending=False).head(15)
        return jsonify({
            "tipo_contrato": tipo, "prioridad": prio, "horas_limite": SLA_HORAS[tipo],
            "total": int(len(sel)),
            "verde": int(conteo.get("Verde", 0)), "ambar": int(conteo.get("Ámbar", 0)),
            "rojo": int(conteo.get("Rojo", 0)),
            "cumplimiento": round(float(cumple.mean() * 100), 2) if len(sel) else 0.0,
            "bono_soles": round(bono, 2),
            "ultimos": [{"id": int(r.ID_Ticket), "fecha": str(r.Fecha_Creacion)[:16], "prioridad": r.Prioridad,
                         "horas": round(float(r.Horas_Resolucion), 1), "semaforo": r.Semaforo}
                        for r in ult.itertuples()]})

    @app.get("/api/ejecuciones")
    def ejecuciones():
        return jsonify({
            "ejecuciones": [{"id": r.id_ejecucion, "marca_tiempo": r.marca_tiempo,
                             "version_algoritmo": str(r.version_algoritmo), "semilla": int(r.semilla_generador),
                             "version_datos": str(r.version_datos), "particion": r.particion,
                             "sha256_dataset": r.sha256_dataset[:12]}
                            for r in ejec.itertuples()],
            "limpieza": [{"regla": r.Regla, "registros": int(r.Registros)} for r in limp.itertuples()],
            "vigente": {"b0": b0, "b1": b1, "b2": b2, "b3": b3}})

    return app


if __name__ == "__main__":
    crear_app().run(host="127.0.0.1", port=5000, debug=False)
