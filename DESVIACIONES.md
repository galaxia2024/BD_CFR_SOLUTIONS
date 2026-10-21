# Desviaciones respecto del protocolo v1 (registradas antes de ejecutar la versión 2)

Fecha de registro: 21 de octubre de 2026.

## Motivo
La entrevista E-01 al gerente general y los datos entregados por la empresa contradicen varios
supuestos del generador v1. La versión 2 reemplaza esos supuestos por los valores informados.
La versión 1 se conserva completa en `historial_v1/`.

## Cambios en los datos sintéticos (generador_cfr.py v2)
| Parámetro | v1 (supuesto) | v2 (dato de la empresa) | Fuente |
|---|---|---|---|
| Periodo | ene-2023 a dic-2025 | oct-2023 a sep-2026 (36 meses), para que el último mes refleje la situación actual | Diseño |
| Módulos | 8 | 19; los de mayor demanda: facturación electrónica, compras, ventas y validaciones | E-01, pregunta 6 |
| Consultores | 6 | 11 en total: 3 de consultoría, 6 de soporte y 2 de desarrollo; solo los 6 de soporte atienden tickets | Datos de la empresa |
| Clientes | 45 | 39 registrados: 19 con contrato, 3 por bolsa de horas y 11 en cotización activos, más 6 que dejaron la empresa | Datos de la empresa (los 6 inactivos fueron confirmados por la empresa) |
| SLA | 8, 24 y 72 h por prioridad | Pactado por cliente según el tipo de contrato; se usan 24 h (contrato) y 48 h (bolsa) como parámetros pendientes de validar | E-01, pregunta 3 |

## Lo que no cambia
Unidad de análisis (módulo-mes), variables Y, X1, X2 y X3, partición temporal (t <= 29 entrenamiento,
t >= 30 prueba), candidatos, rejilla de lambda, métricas, escala de puntajes, pesos 60/40 y regla de desempate.
La semilla sigue siendo 2026.

## Anotación posterior a la ejecución (21/10/2026)
La empresa confirmó que los 6 clientes inactivos dejaron de trabajar con ella durante el periodo.
Se actualizó solo la columna Fuente de la tabla anterior; los parámetros y los resultados no cambian.
Por ello, la huella SHA-256 de este archivo difiere de la registrada en resultados/registro_protocolo.txt.

## Versión 2.1 (registrada antes de su ejecución, 21/10/2026)
La empresa informó que en el periodo se registraron **3 334 tickets**. El generador 2.1 fija ese total y lo
distribuye entre módulos y meses con una distribución multinomial proporcional a la demanda esperada de
cada módulo-mes (misma fórmula de la versión 2). Los demás parámetros, la semilla y el protocolo no cambian.
Los resultados de la versión 2 se conservan en `historial_v2/`.
