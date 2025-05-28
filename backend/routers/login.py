#backend/routers/login.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.database.database import get_connection

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
        return result is not None
    finally:
        cur.close()
        conn.close()

@router.post("/login")
def login(request: LoginRequest):
    username = request.username.strip()

    if not username:
        raise HTTPException(status_code=400, detail="El nombre de usuario es obligatorio")

    if not tiene_rol_configurador(username):
        raise HTTPException(status_code=403, detail="Ingresar un usuario con los permisos adecuados")

    return {"message": "Login exitoso"}
