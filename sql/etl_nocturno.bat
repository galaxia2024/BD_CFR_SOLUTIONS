@echo off
REM Carga nocturna del almacén DW_CFR_BI. Se programa a las 23:00 en el Programador de tareas de Windows,
REM porque SQL Server Express no incluye el Agente SQL Server.
sqlcmd -S .\SQLEXPRESS -E -d DW_CFR_BI -b -Q "EXEC dw.usp_etl_nocturno"
IF %ERRORLEVEL% NEQ 0 (
    echo %DATE% %TIME% Error en la carga nocturna >> C:\CFR_BI\logs\etl_nocturno.log
    exit /b 1
)
echo %DATE% %TIME% Carga nocturna correcta >> C:\CFR_BI\logs\etl_nocturno.log
exit /b 0
