#backend/__init__.py
def cargar_env_manual(ruta=".env"):
    import os
    if not os.path.exists(ruta):
        return
    with open(ruta, "r", encoding="utf-8") as f:
        for linea in f:
            if "=" in linea and not linea.strip().startswith("#"):
                clave, valor = linea.strip().split("=", 1)
                os.environ.setdefault(clave.strip(), valor.strip())

cargar_env_manual()
