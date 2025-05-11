#backend/routers/projects.py
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Literal
from collections import Counter
from tempfile import TemporaryDirectory
from backend.database.database import get_connection
from typing import Optional
from shapely.geometry import box, mapping
import traceback
import tempfile
import rasterio
import subprocess
#import psycopg2
import shutil
import uuid
import time
import os
import re
import json

# Manejo de mensajes en consola 
def debug_print(msg):
    if os.getenv("DEBUG_MODE", "0") == "1":
        print(f"[DEBUG] {msg}")

# Crear carpeta uploads si no existe
UPLOAD_DIR = None  # Carpeta temporal para los TIFFs durante el proceso

router = APIRouter(prefix="/api/projects", tags=["projects"])

class Relation(BaseModel):
    source: str
    target: str

class Segmentacion(BaseModel):
    groupId: str
    groupName: str
    segmentacionName: str

class RasterGroupMapping(BaseModel):
    servantMap: str
    imageId: str
    imageName: str
    srid: str = None
    groups: List[Segmentacion]

class MemberGroupMapping(BaseModel):
    memberId: str
    groupId: str

class Miembro(BaseModel):
    id: str
    email: str
    role: str
    groupId: Optional[str] = None  # Puede no estar asignado si el miembro es un Tutor

class ProjectExecutionRequest(BaseModel):
    projectName: str
    studentTutor: Literal["si", "no"]
    ciafLevel: Literal[1, 2, 3]
    numImages: int
    numGroups: int
    numMembers: int
    groupNames: List[str]
    rasterGroupMappings: List[RasterGroupMapping]
    memberGroupMappings: List[MemberGroupMapping]
    grupoContenedor: str


# Obtiene el SRID de un archivo .tif
def get_raster_srid(tiff_path: str) -> str:
    try:
        with rasterio.open(tiff_path) as src:
            crs = src.crs
            if crs:
                if crs.to_epsg() is not None:
                    srid = str(crs.to_epsg())
                    debug_print(f"SRID detectado para {tiff_path}: {srid}")
                    return srid
                elif crs.is_projected:
                    debug_print(f"SRID no identificado, pero es proyectado: {tiff_path}. Asignando 3116")
                    return "3116"
                elif crs.is_geographic:
                    debug_print(f"SRID no identificado, pero es geográfico: {tiff_path}. Asignando 4686")
                    return "4686"
        raise HTTPException(status_code=400, detail=f"No se pudo determinar el SRID del archivo TIFF '{os.path.basename(tiff_path)}'")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al leer el archivo TIFF '{os.path.basename(tiff_path)}': {str(e)}")

# Validación de imágenes + verificación/asignación de SRID
def validar_y_determinar_srids(raster_mappings: List[RasterGroupMapping]) -> list:

    global UPLOAD_DIR
    errores = []

    for raster in raster_mappings:
        image_name = raster.imageName
        tiff_path = os.path.join(UPLOAD_DIR, image_name)

        if not os.path.exists(tiff_path):
            errores.append({
                "imagen": image_name,
                "error": "El archivo no existe en la ruta temporal esperada."
            })
            continue

        try:
            # Esto lanza HTTPException si falla
            srid = get_raster_srid(tiff_path)
        except HTTPException as e:
            errores.append({
                "imagen": image_name,
                "error": e.detail
            })
        except Exception as ex:
            errores.append({
                "imagen": image_name,
                "error": f"Error inesperado al procesar la imagen: {str(ex)}"
            })

    return errores

# Verifica si ya existe una base de datos con ese nombre
#def database_exists(dbname: str) -> bool:
    conn = get_connection("postgres")
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (dbname,))
    exists = cur.fetchone() is not None
    cur.close()
    conn.close()
    return exists

# Crea la base de datos
def crear_base_de_datos(nombre_db: str):
    try:
        conn_admin = get_connection("postgres")
        conn_admin.autocommit = True
        cur_admin = conn_admin.cursor()
        cur_admin.execute(f"CREATE DATABASE {nombre_db}")
        cur_admin.close()
        conn_admin.close()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al crear la base de datos: {str(e)}")

# Habilita las extensiones de la base de datos
def habilitar_extensiones(nombre_db: str):
    extensiones = [
        "postgis",
        "postgis_raster",
        "postgis_topology",
        "postgis_sfcgal",
        "fuzzystrmatch",
        "address_standardizer",
        "address_standardizer_data_us",
        "postgis_tiger_geocoder"
    ]
    try:
        conn_proj = get_connection(nombre_db)
        conn_proj.autocommit = True
        cur_proj = conn_proj.cursor()
        for ext in extensiones:
            cur_proj.execute(f"CREATE EXTENSION IF NOT EXISTS {ext};")
        cur_proj.close()
        conn_proj.close()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al habilitar extensiones: {str(e)}")

# Crea los esquemas en la base de datos
def crear_esquemas(nombre_db: str, payload: ProjectExecutionRequest):
    try:
        conn = get_connection(nombre_db)
        cur = conn.cursor()

        debug_print(f"🧱 Creando esquemas en la base de datos '{nombre_db}'...")

        # 1. Esquemas para grupos (definidos desde la GUI)
        for grupo in payload.groupNames:
            cur.execute(f"CREATE SCHEMA IF NOT EXISTS {grupo};")
            debug_print(f"✅ Esquema de grupo creado: {grupo}")

        # 2. Esquemas para tutores
        tutores = set()
        for miembro in payload.members:
            if miembro.role == "Tutor":
                nombre_esquema = miembro.email.split("@")[0].lower()
                tutores.add(nombre_esquema)
                cur.execute(f"CREATE SCHEMA IF NOT EXISTS {nombre_esquema};")
                debug_print(f"✅ Esquema de tutor creado: {nombre_esquema}")

        # 3. Esquema contenedor de rásters (si aplica)
        grupo_contenedor = payload.grupoContenedor
        es_tutor_contenedor = grupo_contenedor in tutores

        if payload.studentTutor == "no" and not es_tutor_contenedor:
            cur.execute(f"CREATE SCHEMA IF NOT EXISTS {grupo_contenedor};")
            debug_print(f"✅ Esquema contenedor creado: {grupo_contenedor}")

        conn.commit()
        cur.close()
        conn.close()

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al crear esquemas: {str(e)}")

# Importa los rásters como tablas a los esquemas de la base de datos
def importar_rasters(nombre_db: str, raster_mappings: List[RasterGroupMapping], grupo_contenedor: str) -> list:
    global UPLOAD_DIR
    resultados = []

    try:
        # Variables de entorno necesarias para conexión
        db_user = os.getenv("DB_USER")
        db_pass = os.getenv("DB_PASSWORD")
        db_host = os.getenv("DB_HOST")
        db_port = os.getenv("DB_PORT")

        if not all([db_user, db_pass, db_host, db_port]):
            raise HTTPException(status_code=500, detail="Faltan variables de entorno de conexión.")

        conn = get_connection(nombre_db)
        cur = conn.cursor()

        for raster in raster_mappings:
            image_name = raster.imageName
            tiff_path = os.path.join(UPLOAD_DIR, image_name)
            table_name = os.path.splitext(image_name)[0].lower()

            inicio = time.perf_counter()
            try:
                # Paso 1: Crear SQL con raster2pgsql
                sql_file = tiff_path.replace(".tif", ".sql").replace(".tiff", ".sql")
                raster2pgsql_cmd = [
                    "raster2pgsql", "-s", raster.srid, "-I", "-C", "-M", "-t", "512x512",
                    tiff_path, f"{grupo_contenedor}.{table_name}"
                ]

                with open(sql_file, "w", encoding="utf-8") as f:
                    subprocess.run(raster2pgsql_cmd, stdout=f, check=True)

                # Paso 2: Ejecutar SQL con psql
                env = os.environ.copy()
                env["PGPASSWORD"] = db_pass

                subprocess.run(
                    ["psql", "-h", db_host, "-p", db_port, "-U", db_user, "-d", nombre_db, "-f", sql_file],
                    text=True,
                    capture_output=True,
                    env=env,
                    check=True
                )

                duracion = time.perf_counter() - inicio
                resultados.append({
                    "imagen": image_name,
                    "status": "éxito",
                    "duracion_segundos": round(duracion, 2)
                })

            except Exception as e_img:
                duracion = time.perf_counter() - inicio
                debug_print(f"🛰️ Ráster importado como: {grupo_contenedor}.{table_name}")
                resultados.append({
                    "imagen": image_name,
                    "status": "error",
                    "error": str(e_img),
                    "duracion_segundos": round(duracion, 2)
                })

        conn.commit()
        cur.close()
        conn.close()

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error general al importar rásters: {str(e)}"
        )

    return resultados

# Crea las segmentaciones en cada una de los esquemas
def crear_segmentaciones(payload: ProjectExecutionRequest, nombre_db: str, grupo_contenedor: str):
    try:
        conn = get_connection(nombre_db)
        cur = conn.cursor()

        # Preconstruir mapa de miembros tipo Tutor
        tutores_por_grupo = {}
        for rel in payload.memberGroupMappings:
            miembro = next((m for m in payload.members if m.id == rel.memberId), None)
            if miembro and miembro.role == "Tutor":
                grupo_id = rel.groupId
                tutor_esquema = miembro.email.split("@")[0].lower()
                tutores_por_grupo.setdefault(grupo_id, set()).add(tutor_esquema)

        for mapping_raster in payload.rasterGroupMappings:
            raster_base = os.path.splitext(mapping_raster.imageName)[0].lower()
            tabla_raster = f"{grupo_contenedor}.{raster_base}"

            # Obtener contorno del ráster
            cur.execute(f"SELECT ST_AsText(ST_Envelope(ST_Union(rast))) FROM {tabla_raster};")
            row = cur.fetchone()
            if not row or not row[0]:
                raise HTTPException(status_code=500, detail=f"No se pudo obtener el contorno del ráster: {tabla_raster}")
            geom_wkt = row[0]

            # Obtener el SRID real desde la tabla importada
            cur.execute(f"SELECT ST_SRID(rast) FROM {tabla_raster} LIMIT 1;")
            row_srid = cur.fetchone()
            if not row_srid or not row_srid[0]:
                raise HTTPException(status_code=500, detail=f"No se pudo determinar el SRID del ráster en {tabla_raster}")
            srid = row_srid[0]

            # Determinar campos CIAF según nivel
            nivel = payload.ciafLevel
            ciaf_field = f"ciaf_{nivel}"
            num_field = f"id_ciaf_{nivel}n"

            # Para cada grupo relacionado al ráster
            for grupo in mapping_raster.groups:
                esquemas_destino = {grupo.groupName}
                esquemas_destino.update(tutores_por_grupo.get(grupo.groupId, set()))
                tabla_segmentacion = f"{grupo.groupName}{raster_base}"

                for esquema in esquemas_destino:
                    cur.execute(f"""
                        CREATE TABLE IF NOT EXISTS {esquema}."{tabla_segmentacion}" (
                            id UUID PRIMARY KEY,
                            {ciaf_field} TEXT,
                            {num_field} INTEGER,
                            geom geometry(Polygon, {srid})
                        );
                    """)

                    cur.execute(f"""
                        INSERT INTO {esquema}."{tabla_segmentacion}" (id, {ciaf_field}, {num_field}, geom)
                        VALUES (%s, %s, %s, ST_GeomFromText(%s, %s));
                    """, (
                        str(uuid.uuid4()),
                        f"clase_{nivel}",
                        nivel * 100,
                        geom_wkt,
                        srid
                    ))

                    debug_print(f"🧩 Segmentación creada: {esquema}.{tabla_segmentacion}")

        conn.commit()
        cur.close()
        conn.close()

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al crear segmentaciones: {str(e)}")

# Crear miembros y roles
def gestionar_miembros_y_roles(payload: ProjectExecutionRequest, nombre_db: str):
    try:
        conn = get_connection(nombre_db)
        cur = conn.cursor()

        lideres = ["jvalero@udistrital.edu.co", "jherrera@udistrital.edu.co"]

        # 1. Revocar todos los roles asignados a todos los usuarios (excepto rol_lider)
        cur.execute("""
            DO $$
            DECLARE
                usuario TEXT;
                rol_asignado TEXT;
            BEGIN
                FOR usuario IN
                    SELECT rolname FROM pg_roles
                    WHERE rolcanlogin = true
                      AND rolname <> 'postgres'
                LOOP
                    FOR rol_asignado IN
                        SELECT roleid::regrole::text
                        FROM pg_auth_members
                        WHERE member::regrole::text = usuario
                          AND roleid::regrole::text <> 'rol_lider'
                    LOOP
                        EXECUTE format('REVOKE %I FROM %I;', rol_asignado, usuario);
                    END LOOP;
                END LOOP;
            END $$;
        """)

        # 2. Eliminar usuarios (con LOGIN) que no sean líderes ni postgres
        cur.execute("""
            DO $$
            DECLARE
                r RECORD;
            BEGIN
                FOR r IN (
                    SELECT rolname FROM pg_roles
                    WHERE rolcanlogin = true
                      AND rolname NOT IN (
                          'postgres',
                          (
                            SELECT member::regrole::text
                            FROM pg_auth_members
                            WHERE roleid::regrole::text = 'rol_lider'
                          )
                      )
                )
                LOOP
                    EXECUTE format('DROP ROLE IF EXISTS %I;', r.rolname);
                END LOOP;
            END $$;
        """)

        # 3. Eliminar roles sin login excepto los permitidos
        cur.execute("""
            DO $$
            DECLARE
                r RECORD;
            BEGIN
                FOR r IN (
                    SELECT rolname FROM pg_roles
                    WHERE rolcanlogin = false
                      AND rolname NOT IN (
                          'rol_lider', 'rol_tutor', 'rol_estudiante', 'rol_contribuidor', 'postgres'
                      )
                )
                LOOP
                    EXECUTE format('DROP ROLE IF EXISTS %I;', r.rolname);
                END LOOP;
            END $$;
        """)

        # 4. Crear miembros del payload y asignar roles de GUI
        for miembro in payload.members:
            usuario = miembro + "@udistrital.edu.co"
            es_lider = usuario in lideres

            if not es_lider:
                cur.execute(f"""
                    DO $$
                    BEGIN
                        IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = %s) THEN
                            CREATE ROLE {usuario} LOGIN;
                        END IF;
                    END $$;
                """, (usuario,))

            if miembro.role == "Tutor":
                cur.execute(f"GRANT rol_tutor TO {usuario};")
            elif miembro.role == "Estudiante":
                cur.execute(f"GRANT rol_estudiante TO {usuario};")
            elif miembro.role == "Contribuidor":
                cur.execute(f"GRANT rol_contribuidor TO {usuario};")

        # 5. Crear roles de grupo
        for mapping in payload.rasterGroupMappings:
            for grupo in mapping.groups:
                rol_grupo = grupo.groupName
                cur.execute("""
                    DO $$
                    BEGIN
                        IF NOT EXISTS (
                            SELECT FROM pg_roles WHERE rolname = %s
                        ) THEN
                            EXECUTE format('CREATE ROLE %I;', %s);
                        END IF;
                    END $$;
                """, (rol_grupo, rol_grupo))

        # 6. Asignar usuarios a grupos
        for relacion in payload.memberGroupMappings:
            usuario = relacion.memberName + "@udistrital.edu.co"
            grupo = relacion.groupName
            cur.execute(f"GRANT {grupo} TO {usuario};")

        # 7. Crear rol 'owners' y asignar líderes y tutores
        cur.execute("""
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'owners') THEN
                    CREATE ROLE owners;
                END IF;
            END $$;
        """)

        for miembro in payload.members:
            usuario = miembro.name.lower() + "@udistrital.edu.co"
            if miembro.role in ["Líder", "Tutor"]:
                cur.execute(f"GRANT owners TO {usuario};")

        conn.commit()
        cur.close()
        conn.close()

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al gestionar miembros y roles: {str(e)}")

# Endpoint para creación de elementos en el servidor postgresql
@router.post("/upload-tiffs")
async def upload_tiffs(projectName: str = Form(...), files: List[UploadFile] = File(...)):
    try:
        global UPLOAD_DIR

        # Carpeta base configurable (por defecto: /tmp)
        temp_base = os.getenv("TEMP_UPLOAD_DIR", "/tmp")

        # Crear carpeta temporal si no existe
        if UPLOAD_DIR is None:
            # Para producción se puede usar una ruta fija definida en el archivo .env
            # UPLOAD_DIR = tempfile.mkdtemp(prefix="tiff_uploads_", dir=os.getenv("TEMP_UPLOAD_DIR", "/tmp"))
            UPLOAD_DIR = tempfile.mkdtemp(prefix="tiff_uploads_")
            debug_print(f"🗂️ Carpeta temporal creada: {UPLOAD_DIR}")

        # Validaciones básicas
        allowed_exts = ['tif', 'tiff']
        nombre_invalido = re.compile(r'^[a-z0-9_]+$')

        for file in files:
            filename = file.filename
            ext = filename.split(".")[-1].lower()
            base = ".".join(filename.split(".")[:-1])

            # Validar extensión
            if ext not in allowed_exts:
                raise HTTPException(status_code=400, detail=f"Extensión no permitida: {filename}")

            # Validar nombre base del archivo
            if not nombre_invalido.match(base):
                raise HTTPException(status_code=400, detail=f"Nombre de archivo inválido: {filename} (solo minúsculas, números y guiones bajos)")

            # Guardar archivo
            full_path = os.path.join(UPLOAD_DIR, filename)
            with open(full_path, "wb") as out_file:
                content = await file.read()
                out_file.write(content)

            # Registrar archivo procesado
            debug_print(f"📄 TIFF recibido y guardado: {filename}")

        return {"success": True}

    except HTTPException as he:
        return JSONResponse(status_code=he.status_code, content={"success": False, "detail": he.detail})

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "detail": f"Error al procesar los TIFFs: {str(e)}"}
        )

# Endpoint para creación de elementos en el servidor postgresql
@router.post("/create")
async def create_project(payload: ProjectExecutionRequest):
    global UPLOAD_DIR
    errores_imagenes = []
    try:
        debug_print("📥 JSON recibido en /create:")
        debug_print(json.dumps(payload.model_dump(), indent=2))

        if not UPLOAD_DIR:
            raise HTTPException(
                status_code=500,
                detail="No se encontró la carpeta temporal para los TIFFs."
            )

        # ✅ Validar todas las imágenes (CRS, existencia, SRID)
        errores_imagenes = validar_y_determinar_srids(payload.rasterGroupMappings)

        # 🚫 Si hay errores en imágenes, abortar
        if errores_imagenes:
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "msg": "Hay errores en las imágenes que impiden continuar.",
                    "errores": errores_imagenes
                }
            )


        # ✅ Asignar (y validar) SRID validado a cada raster
        for raster in payload.rasterGroupMappings:
            tiff_path = os.path.join(UPLOAD_DIR, raster.imageName)
            raster.srid = get_raster_srid(tiff_path)
            debug_print(f"✅ SRID asignado para '{raster.imageName}': {raster.srid}")

        # Acciones sobre el servidor PostgreSQL
        crear_base_de_datos(payload.projectName)
        habilitar_extensiones(payload.projectName)
        crear_esquemas(payload.projectName, payload.groupNames)
        resumen_rasters = importar_rasters(payload.projectName, payload.rasterGroupMappings, payload.grupoContenedor)

        # Verificar si hubo errores en al menos una imagen importada
        errores_en_importacion = [r for r in resumen_rasters if r["status"] == "error"]
        if errores_en_importacion:
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "msg": "El proyecto no se creó por errores en las imágenes.",
                    "errores": errores_en_importacion
                }
            )
        
        crear_segmentaciones(payload, payload.projectName)

        return {
            "success": True,
            "msg": f"El proyecto '{payload.projectName}' ha sido creado exitosamente.",
            "resumen_rasters": resumen_rasters
        }

    except HTTPException as he:
        debug_print(f"🧨 Error controlado: {he.detail}")
        return JSONResponse(
            status_code=he.status_code,
            content={"success": False, "detail": he.detail, "errores": errores_imagenes}
        )

    except Exception as e:
        debug_print(f"🧨 ERROR GENERAL EN /create: {str(e)}")
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"success": False, "detail": str(e), "errores": errores_imagenes}
        )

    finally:
        try:
            if UPLOAD_DIR and os.path.exists(UPLOAD_DIR):
                shutil.rmtree(UPLOAD_DIR)
                debug_print(f"🧹 Carpeta temporal eliminada: {UPLOAD_DIR}")
                UPLOAD_DIR = None
        except Exception as cleanup_error:
            debug_print(f"⚠️ No se pudo eliminar la carpeta temporal: {cleanup_error}")
