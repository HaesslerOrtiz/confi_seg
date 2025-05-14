@echo off

REM === Configura entorno QGIS ===
set QGIS_PREFIX_PATH=C:\OSGeo4W64
set PATH=%PATH%;C:\OSGeo4W64\bin;C:\OSGeo4W64\apps\qgis\bin;C:\OSGeo4W64\apps\Qt5\bin

REM === Ejecuta el servidor FastAPI desde entorno de QGIS ===
C:\OSGeo4W64\bin\python-qgis.bat -m uvicorn backend.main:app --reload --port 8001
