import os
import sys

qgs = None
qgis_ya_inicializado = False  # Control de inicialización única

def inicializar_qgis():
    global qgs, qgis_ya_inicializado

    if qgis_ya_inicializado:
        return

    QGIS_PREFIX_PATH = os.getenv("QGIS_PREFIX_PATH")
    print("QGIS_PREFIX_PATH:", os.getenv("QGIS_PREFIX_PATH"), file=sys.stderr)
    if not QGIS_PREFIX_PATH:
        raise RuntimeError("QGIS_PREFIX_PATH no está definido en el archivo .env")

    # Rutas necesarias
    sys.path.append(os.path.join(QGIS_PREFIX_PATH, "apps", "qgis", "python"))
    sys.path.append(os.path.join(QGIS_PREFIX_PATH, "apps", "qgis", "python", "plugins"))
    os.environ["QGIS_PREFIX_PATH"] = QGIS_PREFIX_PATH
    os.environ["PATH"] += os.pathsep + os.path.join(QGIS_PREFIX_PATH, "bin")

    # Intentar importar QGIS
    try:
        from qgis.core import QgsApplication, Qgis
    except ImportError as e:
        raise RuntimeError("Verifica que QGIS esté instalado correctamente con todas sus dependencias.") from e

    # Inicializar
    QgsApplication.setPrefixPath(QGIS_PREFIX_PATH, True)
    qgs = QgsApplication([], False)
    qgs.initQgis()
    print(f"QGIS inicializado correctamente. Versión: {Qgis.QGIS_VERSION}")
    qgis_ya_inicializado = True

def finalizar_qgis():
    global qgs, qgis_ya_inicializado
    if qgs is not None and qgis_ya_inicializado:
        qgs.exitQgis()
        print("QGIS finalizado correctamente.")
        qgis_ya_inicializado = False
