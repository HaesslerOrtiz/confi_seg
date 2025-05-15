# qgis_tools/qgis_core.py
import os
import uuid
from qgis.core import QgsProject, QgsRasterLayer, QgsVectorLayer

# Construcción de clases nativas
class Segmentacion:
    def __init__(self, groupId, groupName, segmentacionName):
        self.groupId = groupId
        self.groupName = groupName
        self.segmentacionName = segmentacionName

class RasterGroupMapping:
    def __init__(self, servantMap, imageId, imageName, srid, groups):
        self.servantMap = servantMap
        self.imageId = imageId
        self.imageName = imageName
        self.srid = srid
        self.groups = groups  # lista de Segmentacion

class MemberGroupMapping:
    def __init__(self, memberId, groupId):
        self.memberId = memberId
        self.groupId = groupId

class Miembro:
    def __init__(self, id, email, role, groupId=None):
        self.id = id
        self.email = email
        self.role = role
        self.groupId = groupId

class ProjectExecutionRequest:
    def __init__(self, projectName, studentTutor, ciafLevel, numImages, numGroups, numMembers,
                 groupNames, rasterGroupMappings, memberGroupMappings, members, grupoContenedor):
        self.projectName = projectName
        self.studentTutor = studentTutor
        self.ciafLevel = ciafLevel
        self.numImages = numImages
        self.numGroups = numGroups
        self.numMembers = numMembers
        self.groupNames = groupNames
        self.rasterGroupMappings = rasterGroupMappings
        self.memberGroupMappings = memberGroupMappings
        self.members = members
        self.grupoContenedor = grupoContenedor

# Conversión diccionario a ProjectExecutionRequest
def dict_to_request(d):
    return ProjectExecutionRequest(
        d["projectName"],
        d["studentTutor"],
        d["ciafLevel"],
        d["numImages"],
        d["numGroups"],
        d["numMembers"],
        d["groupNames"],
        [RasterGroupMapping(rgm["servantMap"], rgm["imageId"], rgm["imageName"], rgm.get("srid"), [
            Segmentacion(g["groupId"], g["groupName"], g["segmentacionName"]) for g in rgm["groups"]
        ]) for rgm in d["rasterGroupMappings"]],
        [MemberGroupMapping(m["memberId"], m["groupId"]) for m in d["memberGroupMappings"]],
        [Miembro(m["id"], m["email"], m["role"], m.get("groupId")) for m in d["members"]],
        d["grupoContenedor"]
    )

# Lógica de generación QGIS
def generar_proyectos_qgis(payload, nombre_db, grupo_contenedor):
    resultados = []
    host = os.getenv("QGIS_SERVER_HOST", "localhost")
    port = os.getenv("QGIS_SERVER_PORT", "80")

    for mapping_raster in payload.rasterGroupMappings:
        nombre_raster = os.path.splitext(mapping_raster.imageName)[0].lower()
        nombre_proyecto = payload.projectName.lower()

        dev_base = os.getenv("QGIS_PROJECTS_DEV_PATH", "C:/proyectos/dev_qgis_projects")
        carpeta_raster = os.path.join(dev_base, nombre_proyecto, nombre_raster)
        os.makedirs(carpeta_raster, exist_ok=True)
        ruta_qgz = os.path.join(carpeta_raster, f"{nombre_raster}.qgz")

        if os.path.exists(ruta_qgz):
            os.remove(ruta_qgz)

        proyecto = QgsProject.instance()
        proyecto.clear()

        capa_raster = QgsRasterLayer(
            f"dbname='{nombre_db}' table=\"{grupo_contenedor}\".\"{nombre_raster}\"", nombre_raster, "postgresraster"
        )
        if capa_raster.isValid():
            proyecto.addMapLayer(capa_raster)

        esquemas_relevantes = set()
        for grupo in mapping_raster.groups:
            esquemas_relevantes.add(grupo.groupName)
            for rel in payload.memberGroupMappings:
                if rel.groupId == grupo.groupId:
                    miembro = next((m for m in payload.members if m.id == rel.memberId and m.role == "Tutor"), None)
                    if miembro:
                        esquemas_relevantes.add(miembro.email.split("@")[0].lower())

        for esquema in esquemas_relevantes:
            tabla_segmentacion = f"{esquema}_{nombre_raster}"
            capa_vector = QgsVectorLayer(
                f"dbname='{nombre_db}' table=\"{esquema}\".\"{tabla_segmentacion}\"", tabla_segmentacion, "postgres"
            )
            if capa_vector.isValid():
                proyecto.addMapLayer(capa_vector)

        proyecto.write(ruta_qgz)
        servant_map = f"https://{host}:{port}/cgi-bin/Segmentations/{nombre_proyecto}/{nombre_raster}/qgis_mapserv.fcgi"

        resultados.append({
            "imagen": mapping_raster.imageName,
            "servantMap": servant_map
        })

    return resultados
