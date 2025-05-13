#backend/routers/projects.py
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Literal
from collections import Counter
#from tempfile import TemporaryDirectory
from backend.database.database import get_connection
from typing import Optional
from shapely.geometry import box, mapping
from backend.utils.qgis_init import inicializar_qgis, finalizar_qgis
from datetime import datetime
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
    members: List[Miembro]
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

        debug_print(f" Creando esquemas en la base de datos '{nombre_db}'...")

        # 1. Esquemas para grupos (definidos desde la GUI)
        for grupo in payload.groupNames:
            cur.execute(f"CREATE SCHEMA IF NOT EXISTS {grupo};")
            debug_print(f"Esquema de grupo creado: {grupo}")

        # 2. Esquemas para tutores
        tutores = set()
        for miembro in payload.members:
            if miembro.role == "Tutor":
                nombre_esquema = miembro.email.split("@")[0].lower()
                tutores.add(nombre_esquema)
                cur.execute(f"CREATE SCHEMA IF NOT EXISTS {nombre_esquema};")
                debug_print(f"Esquema de tutor creado: {nombre_esquema}")

        # 3. Esquema contenedor de rásters (si aplica)
        grupo_contenedor = payload.grupoContenedor
        es_tutor_contenedor = grupo_contenedor in tutores

        if payload.studentTutor == "no" and not es_tutor_contenedor:
            cur.execute(f"CREATE SCHEMA IF NOT EXISTS {grupo_contenedor};")
            debug_print(f"Esquema contenedor creado: {grupo_contenedor}")

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

                debug_print(f" Ejecutando psql para importar ráster: {table_name}")
                debug_print(f"Comando: psql -h {db_host} -p {db_port} -U {db_user} -d {nombre_db} -f {sql_file}")         
                subprocess.run(
                    ["psql", "-h", db_host, "-p", db_port, "-U", db_user, "-d", nombre_db, "-f", sql_file],
                    text=True,
                    capture_output=True,
                    env=env,
                    check=True
                )

                debug_print(f"✅ Finalizó ejecución de psql para {table_name}")
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

                for esquema in esquemas_destino:
                    esquema = esquema.lower()
                    nombre_tabla = f"{esquema}_{raster_base}"

                    cur.execute(f"""
                        CREATE TABLE IF NOT EXISTS {esquema}.{nombre_tabla} (
                            id UUID PRIMARY KEY,
                            {ciaf_field} TEXT,
                            {num_field} INTEGER,
                            geom geometry(Polygon, {srid})
                        );
                    """)

                    cur.execute(f"""
                        INSERT INTO {esquema}.{nombre_tabla} (id, {ciaf_field}, {num_field}, geom)
                        VALUES (%s, %s, %s, ST_GeomFromText(%s, %s));
                    """, (
                        str(uuid.uuid4()),
                        f"clase_{nivel}",
                        nivel * 100,
                        geom_wkt,
                        srid
                    ))

                    debug_print(f"Segmentación creada: {esquema}_{raster_base}")

        conn.commit()
        cur.close()
        conn.close()

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al crear segmentaciones: {str(e)}")

# Crear proyectos Qgis
def generar_proyectos_qgis(payload: ProjectExecutionRequest, nombre_db: str, grupo_contenedor: str) -> list:
    inicializar_qgis()
    from qgis.core import QgsProject, QgsRasterLayer, QgsVectorLayer
    resultados = []
    host = os.getenv("QGIS_SERVER_HOST", "localhost")
    port = os.getenv("QGIS_SERVER_PORT", "80")

    for mapping_raster in payload.rasterGroupMappings:
        nombre_raster = os.path.splitext(mapping_raster.imageName)[0].lower()
        nombre_proyecto = payload.projectName.lower()

        # Ruta para entorno de desarrollo
        dev_base = os.getenv("QGIS_PROJECTS_DEV_PATH", "C:/proyectos/dev_qgis_projects")
        carpeta_raster = os.path.join(dev_base, nombre_proyecto, nombre_raster)

        # Ruta para entorno de producción (descomentar cuando se implemente)
        # carpeta_raster = f"/cgi-bin/Segmentations/{nombre_proyecto}/{nombre_raster}"

        os.makedirs(carpeta_raster, exist_ok=True)
        ruta_qgz = os.path.join(carpeta_raster, f"{nombre_raster}.qgz")

        # Eliminar proyecto previo si existe
        if os.path.exists(ruta_qgz):
            os.remove(ruta_qgz)

        # Crear nuevo proyecto
        proyecto = QgsProject.instance()
        proyecto.clear()

        # Capa ráster
        capa_raster = QgsRasterLayer(
            f"dbname='{nombre_db}' table=\"{grupo_contenedor}\".\"{nombre_raster}\"", nombre_raster, "postgresraster"
        )
        if capa_raster.isValid():
            proyecto.addMapLayer(capa_raster)
        else:
            debug_print(f" Capa ráster inválida: {grupo_contenedor}.{nombre_raster}")

        # Esquemas donde hay segmentaciones de este ráster
        esquemas_relevantes = set()
        for grupo in mapping_raster.groups:
            esquemas_relevantes.add(grupo.groupName)
            for rel in payload.memberGroupMappings:
                if rel.groupId == grupo.groupId:
                    miembro = next((m for m in payload.members if m.id == rel.memberId and m.role == "Tutor"), None)
                    if miembro:
                        esquemas_relevantes.add(miembro.email.split("@")[0].lower())

        # Agregar capas vectoriales (segmentaciones)
        for esquema in esquemas_relevantes:
            tabla_segmentacion = f"{esquema}_{nombre_raster}"
            capa_vector = QgsVectorLayer(
                f"dbname='{nombre_db}' table=\"{esquema}\".\"{tabla_segmentacion}\"", tabla_segmentacion, "postgres"
            )
            if capa_vector.isValid():
                proyecto.addMapLayer(capa_vector)
            else:
                debug_print(f" Capa vectorial inválida: {esquema}_{nombre_raster}")

        # Guardar archivo .qgz
        proyecto.write(ruta_qgz)

        # Generar URL servantMap (siempre válida en ambos entornos)
        servant_map = f"https://{host}:{port}/cgi-bin/Segmentations/{nombre_proyecto}/{nombre_raster}/qgis_mapserv.fcgi"

        resultados.append({
            "imagen": mapping_raster.imageName,
            "servantMap": servant_map
        })

        debug_print(f"📄 Proyecto QGIS generado: {ruta_qgz}")

    finalizar_qgis()
    return resultados

# Crear miembros y roles
def gestionar_miembros_y_roles(payload: ProjectExecutionRequest, nombre_db: str, fecha_actual: str):
    try:
        conn = get_connection(nombre_db)
        cur = conn.cursor()

        debug_print(" Gestionando miembros y roles...")

        # Crear todos los usuarios (miembros)
        for miembro in payload.members:
            usuario = miembro.email
            cur.execute(f"""
                DO $$
                BEGIN
                    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = %s) THEN
                        EXECUTE format('CREATE ROLE %I LOGIN;', %s);
                    END IF;
                END $$;
            """, (usuario, usuario))

            # 🔒 Conceder permiso de lectura sobre pg_roles (seguro)
            cur.execute(f'GRANT SELECT ON pg_roles TO "{usuario}";')

        # Asignar roles de grupo (solo a estudiantes y contribuyentes que estén relacionados)
        for relacion in payload.memberGroupMappings:
            miembro = next((m for m in payload.members if m.id == relacion.memberId), None)
            if not miembro or miembro.role in ["Tutor", "Líder"]:
                continue  # Los tutores/líderes no se agrupan así

            usuario = miembro.email
            grupo_id = relacion.groupId
            grupo_nombre = next((g.groupName for mapping in payload.rasterGroupMappings for g in mapping.groups if g.groupId == grupo_id), None)
            if not grupo_nombre:
                continue

            nombre_rol = f"{grupo_nombre}_{fecha_actual}"

            # Crear rol de grupo si no existe
            cur.execute(f"""
                DO $$
                BEGIN
                    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = %s) THEN
                        EXECUTE format('CREATE ROLE %I;', %s);
                    END IF;
                END $$;
            """, (nombre_rol, nombre_rol))

            # Asignar el usuario a ese rol
            cur.execute(f'GRANT "{nombre_rol}" TO "{usuario}";')

        # 🔑 Asignar permisos a roles de grupo
        for mapping in payload.rasterGroupMappings:
            raster = os.path.splitext(mapping.imageName)[0].lower()
            for grupo in mapping.groups:
                esquema = grupo.groupName.lower()
                tabla_segmentacion = f"{esquema}_{raster}"
                nombre_rol = f"{esquema}_{fecha_actual}"

                # GRANT RUD sobre su segmentación
                cur.execute(f"""
                    GRANT SELECT, UPDATE, DELETE ON {esquema}.{tabla_segmentacion}
                    TO "{nombre_rol}";
                """)

                # GRANT SELECT sobre su ráster
                cur.execute(f"""
                    GRANT SELECT ON {payload.grupoContenedor}.{raster}
                    TO "{nombre_rol}";
                """)

                # GRANT SELECT sobre otras segmentaciones del mismo ráster (si studentTutor = "no")
                if payload.studentTutor == "no":
                    for otro_grupo in mapping.groups:
                        if otro_grupo.groupName != esquema:
                            tabla_otra_segmentacion = f"{otro_grupo.groupName.lower()}_{raster}"
                            cur.execute(f"""
                                GRANT SELECT ON {otro_grupo.groupName.lower()}.{tabla_otra_segmentacion}
                                TO "{nombre_rol}";
                            """)

        # 👥 Asignar permisos CRUD directamente a Tutores y Líderes
        for miembro in payload.members:
            if miembro.role not in ["Tutor", "Líder"]:
                continue

            usuario = miembro.email

            for mapping in payload.rasterGroupMappings:
                raster = os.path.splitext(mapping.imageName)[0].lower()

                # permisos sobre ráster
                cur.execute(f"""
                    GRANT SELECT, INSERT, UPDATE, DELETE
                    ON {payload.grupoContenedor}.{raster}
                    TO "{usuario}";
                """)

                for grupo in mapping.groups:
                    esquema = grupo.groupName.lower()
                    tabla_segmentacion = f"{esquema}_{raster}"
                    cur.execute(f"""
                        GRANT SELECT, INSERT, UPDATE, DELETE
                        ON {esquema}.{tabla_segmentacion}
                        TO "{usuario}";
                    """)

        conn.commit()
        cur.close()
        conn.close()

        debug_print("Gestión de miembros y roles completada.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al gestionar miembros y roles: {str(e)}")

# Creación y llenado de tabla parametros_configuracion
def crear_configuracion(nombre_db: str, grupo_contenedor: str, payload: ProjectExecutionRequest, fecha_actual: str):
    try:
        conn = get_connection(nombre_db)
        cur = conn.cursor()

        debug_print("⚙️ Creando tabla parametros_configuracion si no existe...")

        # 1. Crear la tabla si no existe
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS {grupo_contenedor}.parametros_configuracion (
                servantMap TEXT PRIMARY KEY,
                hostNames TEXT,
                dbmsNames TEXT,
                imageNames TEXT,
                leaderUsernames TEXT,
                isStudentTutors BOOLEAN,
                CIAFLevels INTEGER,
                shpFields TEXT,
                shpNumFields TEXT,
                segmenterGroups TEXT
            );
        """)

        # 2. Obtener valores comunes
        host = os.getenv("DB_HOST", "localhost")
        port = os.getenv("QGIS_SERVER_PORT", "80")
        is_student_tutor = payload.studentTutor == "si"
        ciaf_level = int(payload.ciafLevel)
        campo_ciaf = f"ciaf_{ciaf_level}"
        campo_id = f"id_ciaf_{ciaf_level}n"

        # Obtener líderes/tutores
        lideres = [m.email for m in payload.members if m.role in ["Líder", "Tutor"]]
        lideres_str = ",".join(lideres)

        # Obtener todos los roles de grupo generados
        roles_segmentacion = set()
        for rel in payload.memberGroupMappings:
            miembro = next((m for m in payload.members if m.id == rel.memberId), None)
            if miembro and miembro.role not in ["Líder", "Tutor"]:
                grupo = next((g.groupName for mapping in payload.rasterGroupMappings for g in mapping.groups if g.groupId == rel.groupId), None)
                if grupo:
                    roles_segmentacion.add(f"{grupo}_{fecha_actual}")

        segmenter_groups_str = ",".join(roles_segmentacion)

        # 3. Insertar una fila por cada imagen
        for mapping in payload.rasterGroupMappings:
            nombre_raster = os.path.splitext(mapping.imageName)[0].lower()
            servant_map = f"https://{host}:{port}/cgi-bin/Segmentations/{nombre_db}/{nombre_raster}/qgis_mapserv.fcgi"

            # Eliminar cualquier configuración anterior con ese servantMap (por seguridad)
            cur.execute(f"DELETE FROM {grupo_contenedor}.parametros_configuracion WHERE servantMap = %s", (servant_map,))

            # Insertar nuevo registro
            cur.execute(f"""
                INSERT INTO {grupo_contenedor}.parametros_configuracion (
                    servantMap, hostNames, dbmsNames, imageNames,
                    leaderUsernames, isStudentTutors, CIAFLevels,
                    shpFields, shpNumFields, segmenterGroups
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                servant_map,
                host,
                nombre_db,
                nombre_raster,
                lideres_str,
                is_student_tutor,
                ciaf_level,
                campo_ciaf,
                campo_id,
                segmenter_groups_str
            ))

            debug_print(f"📝 Registro insertado para servantMap: {servant_map}")

        conn.commit()
        cur.close()
        conn.close()
        debug_print("✅ Tabla parametros_configuracion creada y registros insertados correctamente.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al crear configuración del proyecto: {str(e)}")

# Función para eliminar/revertir acciones del proyecto
def revertir_proyecto_fallido(nombre_db: str):
    debug_print("Iniciando rollback de proyecto fallido...")

    # === Selección de entorno ===
    # Entorno de desarrollo (comentar en producción)
    qgis_root = os.getenv("QGIS_PROJECTS_DEV_PATH", "C:/proyectos/dev_qgis_projects")

    # Entorno de producción (descomentar para usar)
    # qgis_root = "/cgi-bin/Segmentations"

    ruta_proyecto_qgis = os.path.join(qgis_root, nombre_db.lower())

    # 1. Eliminar carpeta de proyecto QGIS
    try:
        if os.path.exists(ruta_proyecto_qgis):
            shutil.rmtree(ruta_proyecto_qgis)
            debug_print(f"Carpeta de proyecto QGIS eliminada: {ruta_proyecto_qgis}")
    except Exception as e:
        debug_print(f" No se pudo eliminar carpeta QGIS: {e}")

    # 2. Eliminar base de datos si existe
    try:
        conn = get_connection("postgres")
        conn.autocommit = True
        cur = conn.cursor()

        cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (nombre_db,))
        if cur.fetchone():
            cur.execute(f"""
                SELECT pg_terminate_backend(pg_stat_activity.pid)
                FROM pg_stat_activity
                WHERE pg_stat_activity.datname = %s
                  AND pid <> pg_backend_pid();
            """, (nombre_db,))
            cur.execute(f"DROP DATABASE IF EXISTS {nombre_db}")
            debug_print(f"Base de datos eliminada: {nombre_db}")

        cur.close()
        conn.close()
    except Exception as e:
        debug_print(f" No se pudo eliminar base de datos: {e}")
    
        # 3. Revocar y eliminar roles de grupo del proyecto actual
    try:
        conn = get_connection("postgres")
        conn.autocommit = True
        cur = conn.cursor()

        # Extraer fecha desde el nombre del proyecto
        import re
        match = re.search(r'(\d{8})$', nombre_db)
        fecha_proyecto = match.group(1) if match else None

        if not fecha_proyecto:
            debug_print(f" No se pudo extraer la fecha del nombre del proyecto: {nombre_db}")
            cur.close()
            conn.close()
            return

        debug_print(f" Buscando roles de grupo asociados a la fecha del proyecto: {fecha_proyecto}")

        # 3.1 Encontrar roles de grupo del proyecto actual
        cur.execute("""
            SELECT rolname
            FROM pg_roles
            WHERE rolcanlogin = false AND rolname LIKE %s;
        """, (f'%_{fecha_proyecto}',))

        roles_grupo = [row[0] for row in cur.fetchall()]
        debug_print(f"Roles de grupo detectados: {roles_grupo}")

        for rol in roles_grupo:
            # 3.2 Revocar el rol de todos los usuarios que lo tengan asignado
            cur.execute("""
                SELECT member::regrole::text
                FROM pg_auth_members
                WHERE roleid = (SELECT oid FROM pg_roles WHERE rolname = %s)
            """, (rol,))
            miembros = [row[0] for row in cur.fetchall()]

            for miembro in miembros:
                try:
                    cur.execute(f'REVOKE "{rol}" FROM "{miembro}";')
                    debug_print(f"Revocado {rol} de {miembro}")
                except Exception as e_revoke:
                    debug_print(f" Error al revocar {rol} de {miembro}: {e_revoke}")

            # 3.3 Eliminar el rol de grupo
            try:
                cur.execute(f'DROP ROLE IF EXISTS "{rol}";')
                debug_print(f"Rol de grupo eliminado: {rol}")
            except Exception as e_drop:
                debug_print(f" No se pudo eliminar el rol de grupo {rol}: {e_drop}")

        cur.close()
        conn.close()

    except Exception as e:
        debug_print(f" Error en la limpieza de roles de grupo: {e}")

        # 3.1 Encontrar roles de grupo del proyecto actual
        cur.execute("""
            SELECT rolname
            FROM pg_roles
            WHERE rolcanlogin = false AND rolname LIKE %s;
        """, (f'%_{fecha_proyecto}',))

        roles_grupo = [row[0] for row in cur.fetchall()]
        debug_print(f"Roles de grupo detectados: {roles_grupo}")

        for rol in roles_grupo:
            # 3.2 Revocar el rol de todos los usuarios que lo tengan asignado
            cur.execute("""
                SELECT member::regrole::text
                FROM pg_auth_members
                WHERE roleid = (SELECT oid FROM pg_roles WHERE rolname = %s)
            """, (rol,))
            miembros = [row[0] for row in cur.fetchall()]

            for miembro in miembros:
                try:
                    cur.execute(f'REVOKE "{rol}" FROM "{miembro}";')
                    debug_print(f"Revocado {rol} de {miembro}")
                except Exception as e_revoke:
                    debug_print(f" Error al revocar {rol} de {miembro}: {e_revoke}")

            # 3.3 Eliminar el rol de grupo
            try:
                cur.execute(f'DROP ROLE IF EXISTS "{rol}";')
                debug_print(f"Rol de grupo eliminado: {rol}")
            except Exception as e_drop:
                debug_print(f" No se pudo eliminar el rol de grupo {rol}: {e_drop}")

        cur.close()
        conn.close()

    except Exception as e:
        debug_print(f" Error en la limpieza de roles de grupo: {e}")

# Endpoint para creación de elementos en el servidor postgresql
@router.post("/upload-tiffs")
async def upload_tiffs(projectName: str = Form(...), files: List[UploadFile] = File(...)):
    try:
        global UPLOAD_DIR

        # === Selección de entorno ===
        # Entorno de desarrollo (comentar en producción)
        UPLOAD_DIR = tempfile.mkdtemp(prefix="tiff_uploads_")

        # Entorno de producción (descomentar para usar)
        # base_dir = os.getenv("TEMP_UPLOAD_DIR", "/var/tmp/tiff_cargas")
        # UPLOAD_DIR = tempfile.mkdtemp(prefix="tiff_uploads_", dir=base_dir)

        debug_print(f"🗂️ Carpeta temporal creada: {UPLOAD_DIR}")

        # === 📂 Validaciones de archivos ===
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
    debug_print(f"Campos en payload: {list(payload.__dict__.keys())}")
    global UPLOAD_DIR
    errores_imagenes = []
    try:
        debug_print("JSON recibido en /create:")
        debug_print(json.dumps(payload.model_dump(), indent=2))

        if not UPLOAD_DIR:
            raise HTTPException(
                status_code=500,
                detail="No se encontró la carpeta temporal para los TIFFs."
            )

        # Validar todas las imágenes (CRS, existencia, SRID)
        errores_imagenes = validar_y_determinar_srids(payload.rasterGroupMappings)

        # Si hay errores en imágenes, abortar
        if errores_imagenes:
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "msg": "Hay errores en las imágenes que impiden continuar.",
                    "errores": errores_imagenes
                }
            )

        # Asignar (y validar) SRID validado a cada raster
        for raster in payload.rasterGroupMappings:
            tiff_path = os.path.join(UPLOAD_DIR, raster.imageName)
            raster.srid = get_raster_srid(tiff_path)
            debug_print(f"SRID asignado para '{raster.imageName}': {raster.srid}")

        # Acciones sobre el servidor PostgreSQL
        crear_base_de_datos(payload.projectName)
        habilitar_extensiones(payload.projectName)
        crear_esquemas(payload.projectName, payload)
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
        
        crear_segmentaciones(payload, payload.projectName, payload.grupoContenedor)

        # Fecha actual para nombrar roles de grupo y servantMaps
        fecha_actual = datetime.today().strftime("%Y%m%d")

        # 🛰️ Generar proyectos QGIS por imagen
        try:
            resumen_qgis = generar_proyectos_qgis(payload, payload.projectName, payload.grupoContenedor)
            debug_print("✅ Proyectos QGIS generados:")
            for r in resumen_qgis:
                debug_print(f"- {r['imagen']} → {r['servantMap']}")
        except Exception as e_qgis:
            raise HTTPException(status_code=500, detail=f"Error al generar los proyectos QGIS: {str(e_qgis)}")

        # 👥 Asignar usuarios, roles y permisos SQL
        try:
            gestionar_miembros_y_roles(payload, payload.projectName, fecha_actual)
            debug_print("✅ Miembros y roles gestionados correctamente.")
        except Exception as e_roles:
            raise HTTPException(status_code=500, detail=f"Error al gestionar miembros y roles: {str(e_roles)}")

        # Crear e insertar configuración en la tabla parametros_configuracion
        try:
            crear_configuracion(payload.projectName, payload.grupoContenedor, payload, fecha_actual)
        except Exception as e_config:
            raise HTTPException(status_code=500, detail=f"Error al crear configuración del proyecto: {str(e_config)}")

    except HTTPException as he:
        debug_print(f"Error controlado: {he.detail}")
        revertir_proyecto_fallido(payload.projectName)
        return JSONResponse(
            status_code=he.status_code,
            content={"success": False, "detail": he.detail, "errores": errores_imagenes}
        )

    except Exception as e:
        debug_print(f"ERROR GENERAL EN /create: {str(e)}")
        traceback.print_exc()
        revertir_proyecto_fallido(payload.projectName)
        return JSONResponse(
            status_code=500,
            content={"success": False, "detail": str(e), "errores": errores_imagenes}
        )

    finally:
        try:
            if UPLOAD_DIR and os.path.exists(UPLOAD_DIR):
                shutil.rmtree(UPLOAD_DIR)
                debug_print(f"Carpeta temporal eliminada: {UPLOAD_DIR}")
                UPLOAD_DIR = None
        except Exception as cleanup_error:
            debug_print(f" No se pudo eliminar la carpeta temporal: {cleanup_error}")
