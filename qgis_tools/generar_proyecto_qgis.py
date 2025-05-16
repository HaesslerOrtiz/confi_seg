#qgis_tools/generar_proyecto_qgis.py
import sys
import json
import os

# Cargar variables de entorno desde .env sin usar dotenv
import importlib.util

# Ruta absoluta al archivo backend/__init__.py
ruta_backend_init = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend", "__init__.py"))
spec = importlib.util.spec_from_file_location("backend_init", ruta_backend_init)
backend_init = importlib.util.module_from_spec(spec)
spec.loader.exec_module(backend_init)

# Ejecutar función cargar_env_manual
backend_init.cargar_env_manual()

# Ajustar ruta para importar núcleo de QGIS
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from qgis_tools.qgis_init import inicializar_qgis, finalizar_qgis
from qgis_tools.qgis_core import generar_proyectos_qgis, dict_to_request

def main():
    print("Entrando a main()", file=sys.stderr)
    if len(sys.argv) != 2:
        print("Uso: generar_proyecto_qgis.py <ruta_json>", file=sys.stderr)
        sys.exit(1)

    ruta_json = sys.argv[1]

    if not os.path.exists(ruta_json):
        print(f"Archivo no encontrado: {ruta_json}", file=sys.stderr)
        sys.exit(1)

    try:
        print("Abriendo archivo JSON...", file=sys.stderr)
        with open(ruta_json, "r", encoding="utf-8") as f:
            datos = json.load(f)

        print("Archivo cargado", file=sys.stderr)
        payload_dict = datos["payload"]
        nombre_db = datos["nombre_db"]
        grupo_contenedor = datos["grupo_contenedor"]

        print("Reconstruyendo objeto ProjectExecutionRequest...", file=sys.stderr)
        payload = dict_to_request(payload_dict)
        print("Reconstrucción exitosa", file=sys.stderr)

        inicializar_qgis()
        resultado = generar_proyectos_qgis(payload, nombre_db, grupo_contenedor)

        print("Generación completada, resumen:", file=sys.stderr)
        print("Resultado bruto:", resultado, file=sys.stderr)

        try:
            salida = json.dumps(resultado, ensure_ascii=False)
            print("Imprimiendo JSON...", file=sys.stderr)
            print(salida)
        except Exception as e:
            print(f"Error al convertir a JSON: {e}", file=sys.stderr)
            raise
        
    except Exception as e:
        print(f"Error al ejecutar generación de proyecto QGIS: {e}", file=sys.stderr)
        sys.exit(1)

    finally:
        finalizar_qgis()

if __name__ == "__main__":
    main()
