# backend/database/database.py
import os
import psycopg2

def get_connection(dbname: str = "postgres"):
    user = os.getenv("DB_USER")
    password = os.getenv("DB_PASSWORD")
    host = os.getenv("DB_HOST")
    port = os.getenv("DB_PORT")

    missing = []
    if not user:
        missing.append("DB_USER")
    if not password:
        missing.append("DB_PASSWORD")
    if not host:
        missing.append("DB_HOST")
    if not port:
        missing.append("DB_PORT")

    if missing:
        raise ValueError(f"❌ Variables de entorno faltantes: {', '.join(missing)}")

    return psycopg2.connect(
        dbname=dbname,
        user=user,
        password=password,
        host=host,
        port=port
    )