"""PR-R: pruebas de regresión contra las métricas doradas del experimento v2.1."""
import os
import numpy as np
import pandas as pd
import pytest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
leer = lambda *p: pd.read_csv(os.path.join(RAIZ, *p))
FEAT = ["X1_clientes_activos", "X2_golive_mes_anterior", "X3_peso_modulo"]


def test_pr01_volumen_de_tickets():
    assert len(leer("datos", "originales", "tickets.csv")) == 3367          # 3 334 + 33 duplicados
    assert leer("datos", "originales", "tickets.csv")["ID_Ticket"].nunique() == 3334
    assert len(leer("datos", "procesados", "tickets_limpios.csv")) == 3317


def test_pr02_conjunto_modulo_mes():
    ds = leer("datos", "procesados", "dataset_modulo_mes.csv")
    assert len(ds) == 684 and (ds["t"] <= 29).sum() == 551 and (ds["t"] >= 30).sum() == 133


def test_pr03_coeficientes_rlm_recalculados():
    ds = leer("datos", "procesados", "dataset_modulo_mes.csv")
    tr = ds[ds["t"] <= 29]
    X = np.column_stack([np.ones(len(tr)), tr[FEAT].to_numpy(float)])
    beta = np.linalg.lstsq(X, tr["Y_tickets"].to_numpy(float), rcond=None)[0]
    np.testing.assert_allclose(beta, [-3.5748, 0.1932, 0.6163, 1.4279], atol=5e-5)


def test_pr04_metricas_de_prueba():
    m = leer("resultados", "metricas.csv").set_index("Modelo")
    assert m.loc["B. Regresión lineal múltiple", "RMSE_prueba"] == pytest.approx(2.6365, abs=1e-4)
    assert m.loc["B. Regresión lineal múltiple", "MAE_prueba"] == pytest.approx(1.9036, abs=1e-4)
    assert m.loc["Línea base (promedio histórico)", "RMSE_prueba"] == pytest.approx(2.6916, abs=1e-4)


def test_pr05_contraste_h2():
    c = leer("resultados", "contraste_hipotesis.csv")
    p = float(c[c["Indicador"] == "Valor p (unilateral)"]["Valor"].iloc[0])
    assert p == pytest.approx(0.1269, abs=1e-4)


def test_pr06_multicolinealidad():
    assert leer("resultados", "vif.csv")["VIF"].max() < 5
