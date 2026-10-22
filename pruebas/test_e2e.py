"""PE: pruebas de extremo a extremo de la interfaz con Playwright (Chromium)."""
import os
import re
import pandas as pd
from playwright.sync_api import Page, expect

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRED = pd.read_csv(os.path.join(RAIZ, "resultados", "predicciones_prueba.csv"))
ORACULO = PRED[PRED["Modulo"] == "Facturación electrónica"]          # salida de experimento.py


def abrir(page: Page, servidor):
    page.goto(servidor + "/")
    expect(page.locator("body")).to_have_attribute("data-listo", "1")


def test_pe01_ruta_central_proyeccion(page: Page, servidor):
    abrir(page, servidor)
    page.select_option("#f-modulo", "1")
    page.select_option("#f-desde", "2026-03")
    page.select_option("#f-hasta", "2026-09")
    page.click("#btn-proyeccion")
    expect(page.locator("#t-proy tbody tr")).to_have_count(7)
    expect(page.locator("#t-proy tbody tr").first).to_contain_text("7.62")   # oráculo: 7.62 en mar-2026
    expect(page.locator("#k-real")).to_have_text(str(ORACULO["Y_tickets"].sum()))


def test_pe02_bloqueo_de_interacciones_duplicadas(page: Page, servidor):
    abrir(page, servidor)
    solicitudes = []
    page.on("request", lambda r: solicitudes.append(r.url) if "/api/proyeccion" in r.url else None)

    retenidas = []                                   # la respuesta se retiene para simular demora
    page.route("**/api/proyeccion*", lambda route: retenidas.append(route))
    boton = page.locator("#btn-proyeccion")
    boton.click()
    expect(boton).to_be_disabled()
    boton.click(force=True)                          # segundo y tercer clic con la solicitud en curso
    boton.click(force=True)
    page.wait_for_timeout(300)
    assert len(retenidas) == 1
    retenidas[0].continue_()
    expect(page.locator("#t-proy")).to_be_visible()
    expect(boton).to_be_enabled()
    assert len(solicitudes) == 1


def test_pe03_error_del_servidor_conserva_la_vista(page: Page, servidor):
    abrir(page, servidor)
    page.click("#btn-proyeccion")
    expect(page.locator("#t-proy tbody tr")).to_have_count(36)
    page.route("**/api/proyeccion*", lambda route: route.fulfill(status=500, body="fallo"))
    page.click("#btn-proyeccion")
    expect(page.locator("#msg-p01")).to_have_text("Error: Servidor de datos no accesible")
    expect(page.locator("#t-proy tbody tr")).to_have_count(36)          # se conserva la última vista
    page.unroute("**/api/proyeccion*")
    page.route("**/api/proyeccion*", lambda route: route.abort())       # servidor caído
    page.click("#btn-proyeccion")
    expect(page.locator("#msg-p01")).to_have_text("Error: Servidor de datos no accesible")


def test_pe04_historia_insuficiente(page: Page, servidor):
    abrir(page, servidor)
    page.select_option("#f-desde", "2026-08")
    page.select_option("#f-hasta", "2026-09")
    page.click("#btn-proyeccion")
    expect(page.locator("#msg-p01")).to_have_text("Error: Data histórica insuficiente")


def test_pe05_ruta_sla(page: Page, servidor):
    abrir(page, servidor)
    page.click("#tab-p02")
    page.select_option("#f-tipo", "Contrato")
    page.select_option("#f-prio", "Alta")
    page.click("#btn-sla")
    expect(page.locator("#t-sla tbody tr")).to_have_count(15)
    expect(page.locator("#k-cumple")).to_have_text(re.compile(r"\d+\.\d{2} %"))


def test_pe06_registro_de_ejecuciones(page: Page, servidor):
    abrir(page, servidor)
    page.click("#tab-p03")
    page.click("#btn-ejec")
    expect(page.locator("#t-limp")).to_contain_text("Duplicados eliminados")
    expect(page.locator("#t-ejec tbody tr").first).to_contain_text("2.1.0")
