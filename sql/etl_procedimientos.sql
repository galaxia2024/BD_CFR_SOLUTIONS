-- Procedimientos del ETL nocturno de DW_CFR_BI (SQL Server Express 2019 o superior)
-- Orden de ejecución: usp_etl_extraer -> usp_etl_limpiar -> usp_etl_cargar -> usp_etl_demanda_modulo_mes
-- Las reglas de limpieza son las mismas que aplica etl_limpieza.py en el experimento.
USE DW_CFR_BI;
GO

-- 1. Extracción: copia el origen transaccional al staging y abre el registro de carga
CREATE OR ALTER PROCEDURE dw.usp_etl_extraer
    @Id_Carga INT OUTPUT
AS
BEGIN
    SET NOCOUNT ON;
    INSERT INTO dw.Log_Carga (Inicio, Estado) VALUES (SYSDATETIME(), 'En curso');
    SET @Id_Carga = SCOPE_IDENTITY();
    BEGIN TRY
        TRUNCATE TABLE stg.Tickets;
        TRUNCATE TABLE stg.Clientes;
        TRUNCATE TABLE stg.Consultores;
        TRUNCATE TABLE stg.Modulos;
        TRUNCATE TABLE stg.Proyectos;

        INSERT INTO stg.Tickets (ID_Ticket, ID_Cliente, ID_Consultor, ID_Modulo, Descripcion,
                                 Prioridad, Fecha_Creacion, Fecha_Cierre, Escalado, Estado)
        SELECT ID_Ticket, ID_Cliente, ID_Consultor, ID_Modulo, Descripcion,
               Prioridad, Fecha_Creacion, Fecha_Cierre, Escalado, Estado
        FROM db_tickets.dbo.Tickets
        WHERE Estado IN ('Cerrado', 'Cerrado por abandono');   -- solo estados finales (inmutables)

        INSERT INTO stg.Clientes (ID_Cliente, Tipo, Cliente, RUC, Estado, Mes_Alta, Mes_Baja)
        SELECT ID_Cliente, tipo, cliente, ruc, estado, mes_alta, mes_baja FROM db_tickets.dbo.Clientes;
        INSERT INTO stg.Consultores (ID_Consultor, Nombres, Apellidos, Area, Estado)
        SELECT ID_Consultor, nombres, apellidos, area, estado FROM db_tickets.dbo.Consultores;
        INSERT INTO stg.Modulos (ID_Modulo, Modulo, Peso_Productividad)
        SELECT ID_Modulo, Modulo, Peso_Productividad FROM db_tickets.dbo.Modulos;
        INSERT INTO stg.Proyectos (ID_Proyecto, Id_Cliente, Fecha_GoLive_Real)
        SELECT ID_Proyecto, Id_Cliente, Fecha_GoLive_Real FROM db_tickets.dbo.Proyectos;

        UPDATE dw.Log_Carga SET Registros_Leidos = (SELECT COUNT(*) FROM stg.Tickets)
        WHERE Id_Carga = @Id_Carga;
    END TRY
    BEGIN CATCH
        UPDATE dw.Log_Carga SET Fin = SYSDATETIME(), Estado = 'Error', Mensaje = ERROR_MESSAGE()
        WHERE Id_Carga = @Id_Carga;
        THROW;
    END CATCH
END;
GO

-- 2. Limpieza: tres reglas sobre el staging
CREATE OR ALTER PROCEDURE dw.usp_etl_limpiar
    @Id_Carga INT
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @dup INT, @inv INT, @imp INT;

    -- Regla 1: eliminar duplicados por ID_Ticket (se conserva la primera fila)
    WITH d AS (
        SELECT ROW_NUMBER() OVER (PARTITION BY ID_Ticket ORDER BY Fecha_Creacion) AS rn FROM stg.Tickets
    )
    DELETE FROM d WHERE rn > 1;
    SET @dup = @@ROWCOUNT;

    -- Regla 2: descartar cierres anteriores a la creación
    DELETE FROM stg.Tickets WHERE Fecha_Cierre < Fecha_Creacion;
    SET @inv = @@ROWCOUNT;

    -- Regla 3: imputar la prioridad vacía como Media y marcarla
    UPDATE stg.Tickets SET Prioridad = 'Media', Prioridad_Imputada = 1 WHERE Prioridad IS NULL;
    SET @imp = @@ROWCOUNT;

    UPDATE dw.Log_Carga SET Duplicados = @dup, Invalidos = @inv, Imputados = @imp
    WHERE Id_Carga = @Id_Carga;
END;
GO

-- 3. Carga: dimensiones y Fact_Tickets en una sola transacción
CREATE OR ALTER PROCEDURE dw.usp_etl_cargar
    @Id_Carga INT,
    @Inicio_Historia DATE = '2023-10-01'     -- mes 1 de la numeración de altas y bajas del origen
AS
BEGIN
    SET NOCOUNT ON;
    BEGIN TRY
        BEGIN TRANSACTION;

        MERGE dw.Dim_Modulo AS t
        USING stg.Modulos AS s ON t.BK_Modulo_ID = s.ID_Modulo
        WHEN MATCHED THEN UPDATE SET Nombre_Modulo = s.Modulo, Peso_Productividad = s.Peso_Productividad
        WHEN NOT MATCHED THEN INSERT (BK_Modulo_ID, Nombre_Modulo, Peso_Productividad)
                              VALUES (s.ID_Modulo, s.Modulo, s.Peso_Productividad);

        MERGE dw.Dim_Consultor AS t
        USING stg.Consultores AS s ON t.BK_Consultor_ID = s.ID_Consultor
        WHEN MATCHED THEN UPDATE SET Nombre_Completo = s.Nombres + ' ' + s.Apellidos, Estado = s.Estado
        WHEN NOT MATCHED THEN INSERT (BK_Consultor_ID, Nombre_Completo, Estado)
                              VALUES (s.ID_Consultor, s.Nombres + ' ' + s.Apellidos, s.Estado);

        MERGE dw.Dim_Cliente AS t
        USING stg.Clientes AS s ON t.BK_Cliente_ID = s.ID_Cliente
        WHEN MATCHED THEN UPDATE SET Razon_Social = s.Cliente,
            Mes_Baja = CASE WHEN s.Mes_Baja IS NULL THEN NULL
                            ELSE YEAR(DATEADD(MONTH, s.Mes_Baja - 1, @Inicio_Historia)) * 100 + MONTH(DATEADD(MONTH, s.Mes_Baja - 1, @Inicio_Historia)) END
        WHEN NOT MATCHED THEN INSERT (BK_Cliente_ID, Razon_Social, RUC, Tipo_Contrato, Mes_Alta, Mes_Baja)
            VALUES (s.ID_Cliente, s.Cliente, ISNULL(s.RUC, '00000000000'),
                    CASE s.Tipo WHEN 1 THEN 'Contrato' WHEN 2 THEN 'Bolsa de horas' ELSE 'Cotización' END,
                    YEAR(DATEADD(MONTH, s.Mes_Alta - 1, @Inicio_Historia)) * 100 + MONTH(DATEADD(MONTH, s.Mes_Alta - 1, @Inicio_Historia)),
                    CASE WHEN s.Mes_Baja IS NULL THEN NULL
                         ELSE YEAR(DATEADD(MONTH, s.Mes_Baja - 1, @Inicio_Historia)) * 100 + MONTH(DATEADD(MONTH, s.Mes_Baja - 1, @Inicio_Historia)) END);

        -- Fechas nuevas en Dim_Tiempo (clave AAAAMMDD)
        INSERT INTO dw.Dim_Tiempo (SK_Tiempo, Fecha, Anio, Mes, Nombre_Mes, Trimestre)
        SELECT DISTINCT CONVERT(INT, CONVERT(CHAR(8), CAST(Fecha_Creacion AS DATE), 112)),
               CAST(Fecha_Creacion AS DATE), YEAR(Fecha_Creacion), MONTH(Fecha_Creacion),
               DATENAME(MONTH, Fecha_Creacion), DATEPART(QUARTER, Fecha_Creacion)
        FROM stg.Tickets st
        WHERE NOT EXISTS (SELECT 1 FROM dw.Dim_Tiempo dt
                          WHERE dt.SK_Tiempo = CONVERT(INT, CONVERT(CHAR(8), CAST(st.Fecha_Creacion AS DATE), 112)));

        -- Primer día de cada mes con tickets (clave del hecho agregado módulo-mes)
        INSERT INTO dw.Dim_Tiempo (SK_Tiempo, Fecha, Anio, Mes, Nombre_Mes, Trimestre)
        SELECT DISTINCT CONVERT(INT, CONVERT(CHAR(8), p.Dia1, 112)), p.Dia1, YEAR(p.Dia1), MONTH(p.Dia1),
               DATENAME(MONTH, p.Dia1), DATEPART(QUARTER, p.Dia1)
        FROM stg.Tickets st
        CROSS APPLY (SELECT DATEFROMPARTS(YEAR(st.Fecha_Creacion), MONTH(st.Fecha_Creacion), 1) AS Dia1) p
        WHERE NOT EXISTS (SELECT 1 FROM dw.Dim_Tiempo dt WHERE dt.SK_Tiempo = CONVERT(INT, CONVERT(CHAR(8), p.Dia1, 112)));

        -- Hechos: solo tickets que aún no están en el almacén (inmutabilidad)
        INSERT INTO dw.Fact_Tickets (BK_Ticket_ID, SK_Tiempo, SK_Cliente, SK_Consultor, SK_Modulo, SK_SLA,
                                     Horas_Resolucion, Cumple_SLA, Escalado, Cerrado_Por_Abandono,
                                     Prioridad_Imputada, Bono_Ticket, Conteo_Tickets)
        SELECT st.ID_Ticket,
               CONVERT(INT, CONVERT(CHAR(8), CAST(st.Fecha_Creacion AS DATE), 112)),
               dc.SK_Cliente, dco.SK_Consultor, dm.SK_Modulo, ds.SK_SLA,
               h.Horas,
               CASE WHEN h.Horas <= ds.Horas_Limite THEN 1 ELSE 0 END,
               CASE WHEN st.Escalado = 'Sí' THEN 1 ELSE 0 END,
               CASE WHEN st.Estado = 'Cerrado por abandono' THEN 1 ELSE 0 END,
               st.Prioridad_Imputada,
               CASE WHEN h.Horas <= ds.Horas_Limite AND st.Estado = 'Cerrado' THEN 35.00 ELSE 0 END,
               1
        FROM stg.Tickets st
        CROSS APPLY (SELECT CAST(DATEDIFF(MINUTE, st.Fecha_Creacion, st.Fecha_Cierre) / 60.0 AS DECIMAL(8,2)) AS Horas) h
        JOIN dw.Dim_Cliente dc ON dc.BK_Cliente_ID = st.ID_Cliente
        JOIN dw.Dim_Consultor dco ON dco.BK_Consultor_ID = st.ID_Consultor
        JOIN dw.Dim_Modulo dm ON dm.BK_Modulo_ID = st.ID_Modulo
        JOIN dw.Dim_SLA ds ON ds.Tipo_Contrato = dc.Tipo_Contrato AND ds.Prioridad = st.Prioridad
        WHERE NOT EXISTS (SELECT 1 FROM dw.Fact_Tickets f WHERE f.BK_Ticket_ID = st.ID_Ticket);

        COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        UPDATE dw.Log_Carga SET Fin = SYSDATETIME(), Estado = 'Error', Mensaje = ERROR_MESSAGE()
        WHERE Id_Carga = @Id_Carga;
        THROW;
    END CATCH
END;
GO

-- 4. Hecho agregado por módulo y mes: Y, X1, X2 y X3 (entrada del núcleo RLM)
CREATE OR ALTER PROCEDURE dw.usp_etl_demanda_modulo_mes
    @Id_Carga INT
AS
BEGIN
    SET NOCOUNT ON;
    -- Se recalcula completo: 19 módulos x 36 meses = 684 filas
    DELETE FROM dw.Fact_Demanda_Modulo_Mes;

    WITH meses AS (
        SELECT SK_Tiempo AS SK_Primer_Dia, Anio, Mes, (Anio * 100 + Mes) AS Periodo
        FROM dw.Dim_Tiempo WHERE DAY(Fecha) = 1
    ),
    demanda AS (
        SELECT dt.Anio, dt.Mes, f.SK_Modulo, COUNT(*) AS Y
        FROM dw.Fact_Tickets f JOIN dw.Dim_Tiempo dt ON dt.SK_Tiempo = f.SK_Tiempo
        GROUP BY dt.Anio, dt.Mes, f.SK_Modulo
    )
    INSERT INTO dw.Fact_Demanda_Modulo_Mes (SK_Tiempo, SK_Modulo, Y_Tickets, X1_Clientes_Activos,
                                            X2_GoLive_Mes_Anterior, X3_Peso_Modulo)
    SELECT m.SK_Primer_Dia, dm.SK_Modulo,
           ISNULL(d.Y, 0),
           (SELECT COUNT(*) FROM dw.Dim_Cliente c                       -- X1: clientes con contrato o bolsa activos
            WHERE c.Tipo_Contrato IN ('Contrato', 'Bolsa de horas')
              AND c.Mes_Alta <= m.Periodo AND (c.Mes_Baja IS NULL OR c.Mes_Baja > m.Periodo)),
           (SELECT COUNT(*) FROM stg.Proyectos p                        -- X2: salidas en vivo del mes anterior
            WHERE YEAR(DATEADD(MONTH, 1, p.Fecha_GoLive_Real)) = m.Anio
              AND MONTH(DATEADD(MONTH, 1, p.Fecha_GoLive_Real)) = m.Mes),
           dm.Peso_Productividad                                        -- X3: peso del módulo
    FROM meses m
    CROSS JOIN dw.Dim_Modulo dm
    LEFT JOIN demanda d ON d.Anio = m.Anio AND d.Mes = m.Mes AND d.SK_Modulo = dm.SK_Modulo;

    UPDATE dw.Log_Carga SET Fin = SYSDATETIME(), Estado = 'Correcto' WHERE Id_Carga = @Id_Carga;
END;
GO

-- Procedimiento orquestador que invoca el Programador de tareas mediante sqlcmd
CREATE OR ALTER PROCEDURE dw.usp_etl_nocturno
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @id INT;
    EXEC dw.usp_etl_extraer @Id_Carga = @id OUTPUT;
    EXEC dw.usp_etl_limpiar @Id_Carga = @id;
    EXEC dw.usp_etl_cargar @Id_Carga = @id;
    EXEC dw.usp_etl_demanda_modulo_mes @Id_Carga = @id;
END;
GO
