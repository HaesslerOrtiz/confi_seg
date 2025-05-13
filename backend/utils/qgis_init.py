#backend/utils/qgis_init.py
import os
import sys

qgs = None  # Objeto de aplicación QGIS compartido

def inicializar_qgis():
    #Inicializa QGIS con base en la ruta definida en QGIS_PREFIX_PATH (por .env). 
    # Lanza una excepción si QGIS no está disponible.

    global qgs

    # ⚠️ Cargar .env si la variable necesaria aún no está presente
    if not os.getenv("QGIS_PREFIX_PATH"):
        from dotenv import load_dotenv
        load_dotenv()
        print("⚠️ QGIS_PREFIX_PATH no estaba definido. Se cargó desde .env")

    QGIS_PREFIX_PATH = os.getenv("QGIS_PREFIX_PATH")

    if not QGIS_PREFIX_PATH:
        raise RuntimeError("QGIS_PREFIX_PATH no está definido en el archivo .env")

    # Agregar rutas a sys.path
    sys.path.append(os.path.join(QGIS_PREFIX_PATH, "apps", "qgis", "python"))
    sys.path.append(os.path.join(QGIS_PREFIX_PATH, "apps", "qgis", "python", "plugins"))
    os.environ["QGIS_PREFIX_PATH"] = QGIS_PREFIX_PATH
    os.environ["PATH"] += os.pathsep + os.path.join(QGIS_PREFIX_PATH, "bin")

    try:
        from qgis.core import QgsApplication, Qgis
    except ImportError as e:
        raise RuntimeError("No se pudo importar qgis.core. Verifica que QGIS esté instalado correctamente.") from e

    QgsApplication.setPrefixPath(QGIS_PREFIX_PATH, True)
    qgs = QgsApplication([], False)
    qgs.initQgis()
    print(f"🎉 QGIS inicializado correctamente. Versión: {Qgis.QGIS_VERSION}")

def finalizar_qgis():
    """Libera recursos de QGIS si fue inicializado."""
    global qgs
    if qgs is not None:
        qgs.exitQgis()
        print("🧹 QGIS finalizado correctamente.")
