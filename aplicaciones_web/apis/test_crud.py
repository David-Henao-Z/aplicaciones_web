# test_crud.py
# ============================================================================
# Versión simplificada del CRUD solo para testear autenticación JWT
# ============================================================================
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from datetime import timedelta
from typing import List, Optional
from uuid import UUID
import uuid

from auth import (
    authenticate_user,
    create_access_token,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    Token,
    get_current_user,
    User,
    fake_users_db,
)

app = FastAPI(
    title="API Banco - Prueba JWT",
    description="API para probar autenticación JWT sin base de datos",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Datos de prueba
test_clientes = [
    {"id": str(uuid.uuid4()), "nombre": "Juan Pérez", "documento": "12345678"},
    {"id": str(uuid.uuid4()), "nombre": "María García", "documento": "87654321"},
]

# -------------------------
# Endpoints públicos
# -------------------------
@app.get("/", summary="Healthcheck")
def root():
    return {"status": "ok", "msg": "🔐 API con JWT funcionando"}

@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    🔑 Endpoint de login - PÚBLICO
    Credenciales: admin@banco.com / admin123
    """
    user = authenticate_user(fake_users_db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

# -------------------------
# Endpoints protegidos
# -------------------------
@app.get("/clientes", summary="Listar clientes - PROTEGIDO")
async def listar_clientes(current_user: User = Depends(get_current_user)):
    """
    🔒 Endpoint protegido con JWT
    Requiere token Bearer en el header Authorization
    """
    return {
        "message": f"¡Hola {current_user.username}! Tienes acceso autorizado",
        "user": current_user.username,
        "clientes": test_clientes
    }

@app.post("/transacciones/deposito", summary="Depositar - PROTEGIDO")
async def depositar(current_user: User = Depends(get_current_user)):
    """
    🔒 Simulación de depósito protegido con JWT
    """
    return {
        "message": "💰 Depósito autorizado",
        "user": current_user.username,
        "status": "success",
        "monto": 1000.0
    }

@app.get("/info", summary="Info del usuario autenticado")
async def info_usuario(current_user: User = Depends(get_current_user)):
    """
    🔒 Información del usuario autenticado
    """
    return {
        "authenticated_user": current_user.username,
        "full_name": current_user.full_name,
        "disabled": current_user.disabled,
        "message": "✅ Autenticación JWT funcionando correctamente"
    }