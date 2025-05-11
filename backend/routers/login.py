from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.database.database import get_connection
import psycopg2

router = APIRouter(prefix="/api", tags=["login"])

class LoginRequest(BaseModel):
    username: str

def tiene_rol_configurador(username: str) -> bool:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT 1
            FROM pg_roles r
            JOIN pg_auth_members m ON r.oid = m.roleid
            JOIN pg_roles u ON u.oid = m.member
            WHERE r.rolname = 'rol_configurador' AND u.rolname = %s
        """, (username,))
        result = cur.fetchone()
        cur.close()
        return result is not None
    finally:
        conn.close()

@router.post("/login")
def login(request: LoginRequest):
    username = request.username.strip()
    try:
        if not tiene_rol_configurador(username):
            raise HTTPException(status_code=403, detail="Ingresar un usuario con los permisos adecuados")
        return {"message": "Login exitoso"}
    except psycopg2.Error as e:
        raise HTTPException(status_code=500, detail="Error en la conexión a la base de datos")
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error inesperado en el servidor")
