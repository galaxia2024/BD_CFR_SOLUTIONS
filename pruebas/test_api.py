"""PU: pruebas unitarias de la API del prototipo con el cliente de pruebas de Flask."""
import os
import pandas as pd
import pytest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRED = pd.read_csv(os.path.join(RAIZ, "resultados", "predicciones_prueba.csv"))


def test_pu01_catalogo(cliente):
    d = cliente.get("/api/modulos").get_json()
    assert len(d["modulos"]) == 19 and len(d["periodos"]) == 36
    assert d["periodos"][0] == "2023-10" and d["periodos"][-1] == "2026-09"


def test_pu02_proyeccion_coincide_con_oraculo(cliente):
    """El valor estimado de la API debe ser el mismo que calculó experimento.py. La tolerancia de
    0,02 cubre el redondeo de los coeficientes a cuatro decimales, como en dw.Ejecucion_Modelo."""
    d = cliente.get("/api/proyeccion?modulo=1&desde=2026-03&hasta=2026-09").get_json()
    esperado = PRED[PRED["Modulo"] == "Facturación electrónica"]["B. Regresión lineal múltiple"].tolist()
    assert [m["estimado"] for m in d["meses"]] == pytest.approx(esperado, abs=0.02)
    assert [m["real"] for m in d["meses"]] == PRED[PRED["Modulo"] == "Facturación electrónica"]["Y_tickets"].tolist()


def test_pu03_rmse_global_de_prueba(cliente):
    """Agregando los 19 módulos del periodo de prueba se recupera el RMSE dorado 2,6365."""
    sq, n = 0.0, 0
    for mod in range(1, 20):
        d = cliente.get(f"/api/proyeccion?modulo={mod}&desde=2026-03&hasta=2026-09").get_json()
        sq += d["rmse"] ** 2 * len(d["meses"]); n += len(d["meses"])
    assert n == 133 and (sq / n) ** 0.5 == pytest.approx(2.6365, abs=1e-3)


@pytest.mark.parametrize("q", ["modulo=1&desde=2026-08&hasta=2026-09", "modulo=1&desde=2026-09&hasta=2026-09"])
def test_pu04_historia_insuficiente(cliente, q):
    r = cliente.get("/api/proyeccion?" + q)
    assert r.status_code == 422 and r.get_json()["error"] == "Error: Data histórica insuficiente"


@pytest.mark.parametrize("q,codigo", [("modulo=1", 400), ("modulo=x&desde=2024-01&hasta=2024-06", 400),
                                      ("modulo=99&desde=2024-01&hasta=2024-06", 404),
                                      ("modulo=1&desde=2025-06&hasta=2024-06", 400)])
def test_pu05_parametros_invalidos(cliente, q, codigo):
    assert cliente.get("/api/proyeccion?" + q).status_code == codigo


def test_pu06_semaforo_sla_suma_total(cliente):
    tot = 0
    for tipo in ["Contrato", "Bolsa de horas"]:
        d = cliente.get(f"/api/sla?tipo_contrato={tipo}").get_json()
        assert d["verde"] + d["ambar"] + d["rojo"] == d["total"]
        assert 0 <= d["cumplimiento"] <= 100
        tot += d["total"]
    assert tot == 3317


def test_pu07_semaforo_reglas(app):
    """Verde < 70 % del plazo, ámbar entre 70 % y 100 %, rojo si vence."""
    from app import cargar
    tk = cargar()[2]
    assert (tk.loc[tk["Semaforo"] == "Verde", "Uso_Plazo"] < 0.70).all()
    amb = tk.loc[tk["Semaforo"] == "Ámbar", "Uso_Plazo"]
    assert ((amb >= 0.70) & (amb <= 1)).all()
    assert (tk.loc[tk["Semaforo"] == "Rojo", "Uso_Plazo"] > 1).all()
    assert (tk.loc[tk["Estado"] == "Cerrado por abandono", "Semaforo"] == "Rojo").all()


def test_pu08_sla_parametros_invalidos(cliente):
    assert cliente.get("/api/sla?tipo_contrato=Cotización").status_code == 400
    assert cliente.get("/api/sla?tipo_contrato=Contrato&prioridad=Urgente").status_code == 400


def test_pu09_ejecuciones(cliente):
    d = cliente.get("/api/ejecuciones").get_json()
    assert len(d["ejecuciones"]) >= 1 and d["vigente"]["b3"] == pytest.approx(1.4279)
    assert {r["regla"]: r["registros"] for r in d["limpieza"]}["Duplicados eliminados"] == 33


@pytest.mark.parametrize("url", ["/api/proyeccion?modulo=1&desde=2023-10&hasta=2026-09",
                                 "/api/sla?tipo_contrato=Contrato&prioridad=Todas", "/api/ejecuciones"])
def test_pu10_tiempo_de_respuesta(cliente, url):
    """Mediana de 50 respuestas del servidor por debajo de 20 ms (sin contar el dibujo en el navegador)."""
    import statistics, time
    ts = []
    for _ in range(50):
        t = time.perf_counter(); cliente.get(url); ts.append((time.perf_counter() - t) * 1000)
    assert statistics.median(ts) < 20
