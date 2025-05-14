# ConfiSeg - Aplicativo Web para Gestión de Segmentación Geográfica

ConfiSeg es una herramienta web para crear proyectos basados en imágenes ráster, asociar usuarios, y gestionar grupos de análisis geográfico. Utiliza FastAPI (backend), HTML/JS (frontend) y PostgreSQL/PostGIS para almacenamiento.

# Configuración del entorno
# Desarrollo local en Windows con soporte QGIS

## Requisitos previos

- [OSGeo4W64](https://download.osgeo.org/osgeo4w/osgeo4w-setup.exe)
  - Seleccionar en la instalación avanzada: `qgis-ltr-full`, `python3`, `python3-pip`
- [Visual C++ Redistributable 2015–2022](https://aka.ms/vs/17/release/vc_redist.x64.exe)

# Paso 1: Crear entorno virtual con Python funcional

```powershell
cd C:\proyectos\confi_seg
python -m venv qgis_stack_env
.\qgis_stack_env\Scripts\activate
```

# Paso 2: Instalar dependencias

```powershell
pip install -r requirements.txt
```

# Paso 3: Configurar QGIS en el entorno virtual

Editar el archivo:

```
qgis_stack_env\Scripts\activate.bat
```

Agregar al final:

```bat
REM === Configurar entorno QGIS ===
set QGIS_PREFIX_PATH=C:\OSGeo4W64
set PATH=%PATH%;C:\OSGeo4W64\bin;C:\OSGeo4W64\apps\qgis\bin;C:\OSGeo4W64\apps\Qt5\bin
```

---

# Paso 4: Activar entorno y ejecutar backend

```powershell
.\qgis_stack_env\Scripts\activate
uvicorn backend.main:app --reload --port 8001
```

Acceder a la app en:

```
http://127.0.0.1:8001/login.html
```

---

# Entorno de producción en Ubuntu (servidor)

# Requisitos del sistema

- Ubuntu 22.04 o superior
- Python 3.10 o superior
- PostgreSQL + PostGIS
- QGIS Server (`qgis-server`, `qgis-providers`, `python3-qgis`)
- Apache2 o Nginx con soporte WSGI/ASGI o reverse proxy
- SSL configurado si se accede por HTTPS

---

## Paso 1: Clonar el repositorio

```bash
git clone https://github.com/HaesslerOrtiz/confi_seg.git
cd confi_seg
```

# Paso 2: Crear entorno virtual

```bash
python3 -m venv qgis_stack_env
source qgis_stack_env/bin/activate
```

---

# Paso 3: Instalar dependencias

```bash
pip install -r requirements.txt
```

---

# Paso 4: Configurar variables de entorno

Crear el archivo `.env` en la raíz del proyecto:

```env
DB_USER=postgres
DB_PASSWORD=tu_contraseña
DB_HOST=localhost
DB_PORT=5432
DEBUG_MODE=0
TEMP_UPLOAD_DIR=/var/tmp/tiff_cargas
QGIS_PREFIX_PATH=/usr
QGIS_PROJECTS_DEV_PATH=/var/www/qgis_projects
QGIS_SERVER_HOST=mi-servidor-produccion
QGIS_SERVER_PORT=443
```

Asegurar de que `QGIS_PREFIX_PATH` apunte a la raíz de instalación de QGIS.

# Paso 5: Ejecutar backend en producción (manual)

```bash
source qgis_stack_env/bin/activate
# Configurar variables de entorno necesarias para QGIS
export QGIS_PREFIX_PATH=/usr
export PATH=$PATH:/usr/lib/qgis:/usr/lib/x86_64-linux-gnu/qt5/bin
uvicorn backend.main:app --host 0.0.0.0 --port 8001
```

> Para producción real, se recomienda configurar `gunicorn` + `uvicorn.workers.UvicornWorker`, o usar `systemd` para ejecutar el servicio permanentemente.

---

# Variables definidas en `.env`

| Variable                 | Propósito                                                                 |
|--------------------------|---------------------------------------------------------------------------|
| `DB_USER`, `DB_PASSWORD` | Credenciales para PostgreSQL/PostGIS                                     |
| `DB_HOST`, `DB_PORT`     | Conexión al motor de base de datos                                        |
| `DEBUG_MODE`             | `1` para modo desarrollo, `0` para producción                             |
| `TEMP_UPLOAD_DIR`        | Carpeta temporal donde se guardan TIFFs cargados                         |
| `QGIS_PREFIX_PATH`       | Ruta de instalación base de QGIS (`C:/OSGeo4W64` o `/usr`)                |
| `QGIS_PROJECTS_DEV_PATH` | Carpeta donde se generan los `.qgz` por imagen                           |
| `QGIS_SERVER_HOST`       | Dominio o IP pública del servidor donde está desplegado QGIS Server       |
| `QGIS_SERVER_PORT`       | Puerto de QGIS Server (por defecto `80` o `443`)                          |
