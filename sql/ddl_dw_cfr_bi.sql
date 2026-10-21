-- DDL del almacén de datos DW_CFR_BI (SQL Server Express 2019 o superior)
-- Coincide con la Figura del modelo físico y con el apartado 5.2 del proyecto.
CREATE DATABASE DW_CFR_BI;
GO
USE DW_CFR_BI;
GO
CREATE SCHEMA stg;
GO
CREATE SCHEMA dw;
GO
-- Dimensiones
CREATE TABLE dw.Dim_Tiempo (
    SK_Tiempo INT PRIMARY KEY,               -- AAAAMMDD
    Fecha DATE NOT NULL,
    Anio SMALLINT NOT NULL,
    Mes TINYINT NOT NULL,
    Nombre_Mes VARCHAR(15) NOT NULL,
    Trimestre TINYINT NOT NULL
);
CREATE TABLE dw.Dim_Cliente (
    SK_Cliente INT IDENTITY(1,1) PRIMARY KEY,
    BK_Cliente_ID INT NOT NULL,
    Razon_Social VARCHAR(150) NOT NULL,
    RUC CHAR(11) NOT NULL,
    Tipo_Contrato VARCHAR(15) NOT NULL,      -- Contrato, Bolsa de horas, Cotización
    Mes_Alta INT NOT NULL,                   -- AAAAMM
    Mes_Baja INT NULL
);
CREATE TABLE dw.Dim_Consultor (
    SK_Consultor INT IDENTITY(1,1) PRIMARY KEY,
    BK_Consultor_ID INT NOT NULL,
    Nombre_Completo VARCHAR(150) NOT NULL,
    Estado BIT NOT NULL
);
CREATE TABLE dw.Dim_Modulo (
    SK_Modulo INT IDENTITY(1,1) PRIMARY KEY,
    BK_Modulo_ID INT NOT NULL,
    Nombre_Modulo VARCHAR(60) NOT NULL,
    Peso_Productividad TINYINT NOT NULL CHECK (Peso_Productividad BETWEEN 1 AND 5)
);
CREATE TABLE dw.Dim_SLA (
    SK_SLA INT IDENTITY(1,1) PRIMARY KEY,
    Tipo_Contrato VARCHAR(15) NOT NULL,      -- el SLA se pacta por contrato (E-01)
    Prioridad VARCHAR(10) NOT NULL,          -- Alta, Media, Baja
    Horas_Limite SMALLINT NOT NULL
);
-- Hecho por ticket
CREATE TABLE dw.Fact_Tickets (
    Id_Hecho BIGINT IDENTITY(1,1) PRIMARY KEY,
    BK_Ticket_ID INT NOT NULL UNIQUE,
    SK_Tiempo INT NOT NULL REFERENCES dw.Dim_Tiempo(SK_Tiempo),
    SK_Cliente INT NOT NULL REFERENCES dw.Dim_Cliente(SK_Cliente),
    SK_Consultor INT NOT NULL REFERENCES dw.Dim_Consultor(SK_Consultor),
    SK_Modulo INT NOT NULL REFERENCES dw.Dim_Modulo(SK_Modulo),
    SK_SLA INT NOT NULL REFERENCES dw.Dim_SLA(SK_SLA),
    Horas_Resolucion DECIMAL(8,2) NULL,
    Cumple_SLA BIT NULL,
    Escalado BIT NOT NULL DEFAULT 0,
    Cerrado_Por_Abandono BIT NOT NULL DEFAULT 0,
    Prioridad_Imputada BIT NOT NULL DEFAULT 0,
    Bono_Ticket DECIMAL(10,2) NOT NULL DEFAULT 0,
    Conteo_Tickets INT NOT NULL DEFAULT 1
);
-- Hecho agregado por módulo y mes (entrada del modelo)
CREATE TABLE dw.Fact_Demanda_Modulo_Mes (
    SK_Tiempo INT NOT NULL REFERENCES dw.Dim_Tiempo(SK_Tiempo),  -- primer día del mes
    SK_Modulo INT NOT NULL REFERENCES dw.Dim_Modulo(SK_Modulo),
    Y_Tickets INT NOT NULL,
    X1_Clientes_Activos INT NOT NULL,
    X2_GoLive_Mes_Anterior INT NOT NULL,
    X3_Peso_Modulo TINYINT NOT NULL,
    PRIMARY KEY (SK_Tiempo, SK_Modulo)
);
-- Registro de resultados por ejecución del modelo
CREATE TABLE dw.Ejecucion_Modelo (
    Id_Ejecucion VARCHAR(30) PRIMARY KEY,    -- EJ-AAAAMMDD-HHMMSS
    Marca_Tiempo DATETIME2 NOT NULL,
    Version_Algoritmo VARCHAR(10) NOT NULL,
    Semilla INT NULL,
    Parametros NVARCHAR(400) NOT NULL,       -- partición, variables, lambda
    Beta0 DECIMAL(10,4) NOT NULL,
    Beta1 DECIMAL(10,4) NOT NULL,
    Beta2 DECIMAL(10,4) NOT NULL,
    Beta3 DECIMAL(10,4) NOT NULL,
    RMSE_Prueba DECIMAL(8,4) NOT NULL,
    MAE_Prueba DECIMAL(8,4) NOT NULL,
    Vigente BIT NOT NULL DEFAULT 0
);
CREATE TABLE dw.Prediccion_Modulo_Mes (
    Id_Ejecucion VARCHAR(30) NOT NULL REFERENCES dw.Ejecucion_Modelo(Id_Ejecucion),
    SK_Tiempo INT NOT NULL REFERENCES dw.Dim_Tiempo(SK_Tiempo),
    SK_Modulo INT NOT NULL REFERENCES dw.Dim_Modulo(SK_Modulo),
    Y_Estimada DECIMAL(8,2) NOT NULL,
    PRIMARY KEY (Id_Ejecucion, SK_Tiempo, SK_Modulo)
);
-- Bitácora del ETL
CREATE TABLE dw.Log_Carga (
    Id_Carga INT IDENTITY(1,1) PRIMARY KEY,
    Inicio DATETIME2 NOT NULL,
    Fin DATETIME2 NULL,
    Registros_Leidos INT NULL,
    Duplicados INT NULL,
    Invalidos INT NULL,
    Imputados INT NULL,
    Estado VARCHAR(10) NOT NULL,             -- Correcto, Error
    Mensaje NVARCHAR(400) NULL
);
CREATE NONCLUSTERED INDEX IX_Fact_Tickets_Tiempo_Modulo ON dw.Fact_Tickets (SK_Tiempo, SK_Modulo);
GO
-- Vista que entrega el conjunto módulo-mes al núcleo RLM
CREATE VIEW dw.vw_Demanda_Modulo_Mes AS
SELECT d.SK_Tiempo, t.Anio, t.Mes, m.Nombre_Modulo,
       d.Y_Tickets, d.X1_Clientes_Activos, d.X2_GoLive_Mes_Anterior, d.X3_Peso_Modulo
FROM dw.Fact_Demanda_Modulo_Mes d
JOIN dw.Dim_Tiempo t ON t.SK_Tiempo = d.SK_Tiempo
JOIN dw.Dim_Modulo m ON m.SK_Modulo = d.SK_Modulo;
GO
