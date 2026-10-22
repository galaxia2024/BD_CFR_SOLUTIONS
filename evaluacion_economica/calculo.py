"""Cálculo del Capítulo VI: flujo de caja e indicadores (precios constantes, soles de octubre de 2026)."""
import json
from scipy.optimize import brentq
P = dict(tc=3.447, pbi_usd=14.0, usuarios=4, sueldo_dev=2538, sueldo_jefe=4219, essalud=0.09, horas_mes=208,
         horas_desarrollo=384, horas_capacitacion=16, contingencia=0.10, horas_mant_mes=4,
         horas_reporte_hoy=40, horas_reporte_con=10, horas_jefes_mes=4, tasa=0.16893, n=3)

def evaluar(p):
    r = lambda x: round(x, 2)
    dev = r(p['sueldo_dev'] * (1 + p['essalud']) / p['horas_mes'])
    jefe = r(p['sueldo_jefe'] * (1 + p['essalud']) / p['horas_mes'])
    inv_dev = r(p['horas_desarrollo'] * dev); cap = r(p['horas_capacitacion'] * jefe)
    sub = r(inv_dev + cap); cont = r(sub * p['contingencia']); inv = r(sub + cont)
    lic = r(p['usuarios'] * p['pbi_usd'] * 12 * p['tc']); mant = r(p['horas_mant_mes'] * 12 * dev)
    b1 = r((p['horas_reporte_hoy'] - p['horas_reporte_con']) * 12 * jefe); b2 = r(p['horas_jefes_mes'] * 12 * jefe)
    ben = r(b1 + b2); cos = r(lic + mant); neto = r(ben - cos)
    i, n = p['tasa'], p['n']
    flujos = [-inv] + [neto] * n
    fd = [r(1 / (1 + i) ** t) for t in range(n + 1)]
    fdesc = [r(f / (1 + i) ** t) for t, f in enumerate(flujos)]
    acum = []; s = 0
    for x in fdesc: s = r(s + x); acum.append(s)
    van = acum[-1]
    g = lambda k: sum(f / (1 + k) ** t for t, f in enumerate(flujos))
    tir = brentq(g, -0.99, 100) if g(-0.99) * g(100) < 0 else float('nan')
    vab = r(sum(ben / (1 + i) ** t for t in range(1, n + 1)))
    vac = r(inv + sum(cos / (1 + i) ** t for t in range(1, n + 1)))
    # periodo de recuperación descontado
    pri = None; s = 0
    for t in range(n + 1):
        prev = s; s += flujos[t] / (1 + i) ** t
        if t > 0 and s >= 0 and pri is None:
            pri = (t - 1) + (-prev) / (flujos[t] / (1 + i) ** t)
    return dict(dev=dev, jefe=jefe, inv_dev=inv_dev, cap=cap, sub=sub, cont=cont, inv=inv, lic=lic, mant=mant,
                b1=b1, b2=b2, ben=ben, cos=cos, neto=neto, flujos=flujos, fd=fd, fdesc=fdesc, acum=acum,
                van=van, tir=round(tir * 100, 2), vab=vab, vac=vac, bc=round(vab / vac, 2),
                pri=None if pri is None else round(pri, 2))

if __name__ == '__main__':
    base = evaluar(P)
    print(json.dumps(base, ensure_ascii=False)); print('simple', round(base['inv']/base['neto'],2)); print([round(1/(1+P['tasa'])**t,6) for t in range(4)])
    esc = {
        'Pesimista: ahorro de 20 h (50 %) y sin B2': dict(P, horas_reporte_con=20, horas_jefes_mes=0),
        'Licencia +40 % (US$ 19.60)': dict(P, pbi_usd=19.6),
        'Base a 5 años': dict(P, n=5),
        'Pesimista a 5 años': dict(P, horas_reporte_con=20, horas_jefes_mes=0, n=5),
        'Optimista: ahorro de 35 h': dict(P, horas_reporte_con=5),
    }
    for k, p in esc.items():
        e = evaluar(p); print(k, e['neto'], e['van'], e['tir'], e['bc'], e['pri'])
    # punto de equilibrio: horas ahorradas al mes en B1 (sin B2) con VAN = 0
    def f(h):
        q = dict(P, horas_reporte_con=40 - h, horas_jefes_mes=0); i = q['tasa']
        e = evaluar(q); return -e['inv'] + e['neto'] * sum(1 / (1 + i) ** t for t in range(1, 4))
    print('equilibrio sin B2:', round(brentq(f, 0, 40), 1))
    def f2(h):
        q = dict(P, horas_reporte_con=40 - h); i = q['tasa']
        e = evaluar(q); return -e['inv'] + e['neto'] * sum(1 / (1 + i) ** t for t in range(1, 4))
    print('equilibrio con B2:', round(brentq(f2, 0, 40), 1))
