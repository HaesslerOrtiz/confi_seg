# 🧭 ConfiSeg - Aplicativo Web para Gestión de Segmentación Geográfica

ConfiSeg es una herramienta web para crear proyectos basados en imágenes ráster, asociar usuarios, y gestionar grupos de análisis geográfico. Utiliza FastAPI (backend), HTML/JS (frontend) y PostgreSQL/PostGIS para almacenamiento.

---

## 📦 Requisitos generales

- Python 3.7 o superior
- PostgreSQL 16
- PostGIS 3 y extensiones adicionales
- GDAL (`gdalinfo`)
- Git (opcional)

---

## ⚙️ Instalación y ejecución

### 🔁 Paso 1: Clonar el repositorio

```bash
git clone https://github.com/usuario/confi_seg.git
cd confi_seg
```

---

### 🐧 Instalación en Linux (Ubuntu)

#### 1. Instalar dependencias del sistema

```bash
sudo apt update
sudo apt install -y python3-venv python3-pip gdal-bin   postgresql-16 postgresql-16-postgis-3   postgresql-16-postgis-3-sfcgal postgresql-16-postgis-3-scripts
```

#### 2. Crear entorno virtual e instalar dependencias de Python

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

#### 3. Crear archivo `.env` en la raíz del proyecto

```env
DB_USER=postgres
DB_PASSWORD=tu_contraseña
DB_HOST=localhost
DB_PORT=5432
```

#### 4. Inicializar base de datos (una sola vez)

```bash
psql -U postgres -d postgres -f init_roles_and_users.sql
```

#### 5. Ejecutar servidor

```bash
uvicorn backend.main:app --reload --port 8001
```

Accede desde tu navegador a `http://127.0.0.1:8001/login.html`

---

### 🪟 Instalación en Windows

#### 1. Instalar PostgreSQL y PostGIS

Descargar desde: https://www.enterprisedb.com/downloads/postgres-postgresql-downloads  
Seleccionar las extensiones adicionales (postgis, sfcgal, fuzzystrmatch) durante instalación.

#### 2. Instalar GDAL

Recomendado: instalar desde OSGeo4W o GISInternals.  
Agregar carpeta `bin` al PATH del sistema.

Verifica:

```cmd
gdalinfo --version
```

#### 3. Crear entorno virtual e instalar dependencias

```powershell
python -m venv venv
.env\Scripts\activate
pip install -r requirements.txt
```

#### 4. Crear archivo `.env` en `confi_seg\`

```env
DB_USER=postgres
DB_PASSWORD=tu_contraseña
DB_HOST=localhost
DB_PORT=5432
```

#### 5. Ejecutar el script SQL

Desde `psql` o `pgAdmin`:

```sql
\i init_roles_and_users.sql
```

#### 6. Ejecutar servidor

```powershell
uvicorn backend.main:app --reload --port 8001
```

---

## 🧪 Validación del sistema

1. Accede a `http://localhost:8001/login.html`
2. Carga un TIFF georreferenciado
3. Crea un proyecto
4. Verifica en PostgreSQL la base de datos y los esquemas creados

---

## 🗂 Estructura del proyecto

```
confi_seg/
│
├── backend/
│   ├── main.py
│   ├── __init__.py
│   ├── routers/
│   └── database/
├── frontend/
│   ├── login.html
│   ├── principal.html
│   └── assets/
├── .env
├── requirements.txt
├── init_roles_and_users.sql
└── README.md
```

---

## ❗ Consideraciones importantes

- El archivo `.env` **nunca debe subirse al repositorio**.
- El binario `gdalinfo` debe estar disponible en el sistema (`PATH`).
- En producción, usar `gunicorn` o `uvicorn` con `systemd` y configurar HTTPS.

---

¿Listo para producción o necesitas script de despliegue automatizado? Contáctame.