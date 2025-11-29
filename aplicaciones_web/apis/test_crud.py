# test_crud.py
"""
API de Prueba para Autenticación JWT.

Este módulo proporciona una versión simplificada de la API sin base de datos,
diseñada específicamente para probar la autenticación JWT.

Propósito:
    - Validar el flujo de autenticación OAuth2 con JWT
    - Probar que los tokens se generan correctamente
    - Verificar que los endpoints protegidos rechazan requests sin token
    - Comprobar que los tokens válidos permiten acceso a recursos

Diferencias con crud.py:
    - No requiere base de datos PostgreSQL
    - Usa datos hardcodeados en memoria
    - Más simple y rápido para testing
    - Incluye middleware de auditoría (audit.py)

Ejecución:
    Desde la carpeta `apis/` con PYTHONPATH configurado:
    
    PowerShell:
    >>> cd C:\Users\...\aplicaciones_web\aplicaciones_web\apis
    >>> $env:PYTHONPATH="C:\Users\...\aplicaciones_web"
    >>> python -m uvicorn test_crud:app --reload --port 8001
    
    El servidor estará disponible en: http://127.0.0.1:8001

Credenciales de prueba:
    - Email: admin@banco.com
    - Password: admin123

Testing Flow:
    1. POST /token con credenciales → Obtiene access_token
    2. GET /clientes con header Authorization: Bearer <token> → 200 OK
    3. GET /clientes sin header → 401 Unauthorized

Version: 1.0.0
Author: Sistema Bancario - Aplicaciones Web
License: MIT
"""

# ============================================================================
# Importaciones
# ============================================================================
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from datetime import timedelta
from typing import List, Optional
from uuid import UUID
import uuid

from aplicaciones_web.apis.auth import (
    authenticate_user,
    create_access_token,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    Token,
    get_current_user,
    User,
    fake_users_db,
)

# ============================================================================
# Aplicación FastAPI de Testing
# ============================================================================
app = FastAPI(
    title="API Banco - Prueba JWT",
    description="API para probar autenticación JWT sin base de datos",
    version="1.0.0",
)

# ============================================================================
# Middleware - CORS
# ============================================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permite requests desde cualquier origen
    allow_credentials=True,  # Permite cookies/tokens
    allow_methods=["*"],  # Permite todos los métodos HTTP
    allow_headers=["*"],  # Permite todos los headers
)

# ============================================================================
# Middleware - Auditoría
# ============================================================================
# Registrar middleware de auditoría para loguear todas las peticiones
# Crea archivo aplicaciones_web/logs/audit.log con timestamps, IPs, métodos, rutas
from aplicaciones_web.apis.audit import audit_middleware

app.middleware("http")(audit_middleware)

# ============================================================================
# Datos de Prueba (Hardcoded)
# ============================================================================
test_clientes = [
    {"id": str(uuid.uuid4()), "nombre": "Juan Pérez", "documento": "12345678"},
    {"id": str(uuid.uuid4()), "nombre": "María García", "documento": "87654321"},
]


# ============================================================================
# ENDPOINTS - Públicos (No requieren autenticación)
# ============================================================================
@app.get("/", summary="Healthcheck")
def root():
    """
    Verifica que el servidor de testing esté activo.
    
    Returns:
        dict: Estado del servidor y mensaje
    
    Status: 200 OK
    
    Authentication: No requiere autenticación
    
    Example Response:
        {
            "status": "ok",
            "msg": "🔐 API con JWT funcionando"
        }
    """
    return {"status": "ok", "msg": "🔐 API con JWT funcionando"}


@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Genera un token JWT para autenticación.
    
    Este endpoint es idéntico al de crud.py pero en un servidor separado.
    
    Request Body (form-data):
        username (str): Email del usuario (ej: admin@banco.com)
        password (str): Contraseña del usuario (ej: admin123)
    
    Authentication: NO requiere autenticación (endpoint público)
    
    Returns:
        Token:
            - access_token (str): Token JWT válido por 60 minutos
            - token_type (str): Tipo de token (siempre "bearer")
    
    Status Codes:
        - 200 OK: Login exitoso, token generado
        - 401 Unauthorized: Credenciales incorrectas
    
    Credentials (Testing):
        - Email: admin@banco.com
        - Password: admin123
    
    Example Request (form-data):
        username=admin@banco.com
        password=admin123
    
    Example Response:
        {
            "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            "token_type": "bearer"
        }
    
    Testing with curl:
        >>> curl -X POST http://localhost:8001/token \
        ...      -d "username=admin@banco.com&password=admin123"
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


# ============================================================================
# ENDPOINTS - Protegidos (Requieren token JWT válido)
# ============================================================================
@app.get("/clientes", summary="Listar clientes - PROTEGIDO")
async def listar_clientes(current_user: User = Depends(get_current_user)):
    """
    Retorna una lista de clientes hardcodeados (datos de prueba).
    
    Authentication: Requiere token JWT válido en header Authorization
    
    Returns:
        dict: Mensaje de bienvenida, usuario autenticado y lista de clientes
    
    Status Codes:
        - 200 OK: Token válido, datos retornados
        - 401 Unauthorized: Token ausente, inválido o expirado
    
    Example Request:
        GET /clientes
        Headers:
            Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
    
    Example Response:
        {
            "message": "¡Hola admin@banco.com! Tienes acceso autorizado",
            "user": "admin@banco.com",
            "clientes": [
                {
                    "id": "123e4567-e89b-12d3-a456-426614174000",
                    "nombre": "Juan Pérez",
                    "documento": "12345678"
                },
                {
                    "id": "456e7890-a12b-34c5-d678-901234567890",
                    "nombre": "María García",
                    "documento": "87654321"
                }
            ]
        }
    
    Testing with curl:
        >>> TOKEN="eyJhbGciOi..."
        >>> curl -H "Authorization: Bearer $TOKEN" http://localhost:8001/clientes
    """
    return {
        "message": f"¡Hola {current_user.username}! Tienes acceso autorizado",
        "user": current_user.username,
        "clientes": test_clientes,
    }


@app.post("/transacciones/deposito", summary="Depositar - PROTEGIDO")
async def depositar(current_user: User = Depends(get_current_user)):
    """
    Simula un depósito bancario (sin operación real en BD).
    
    Este endpoint está protegido por JWT y sirve para verificar que
    las operaciones POST también funcionan correctamente con autenticación.
    
    Authentication: Requiere token JWT válido en header Authorization
    
    Returns:
        dict: Mensaje de éxito, usuario autenticado y datos simulados
    
    Status Codes:
        - 200 OK: Token válido, operación simulada
        - 401 Unauthorized: Token ausente, inválido o expirado
    
    Example Request:
        POST /transacciones/deposito
        Headers:
            Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
    
    Example Response:
        {
            "message": "💰 Depósito autorizado",
            "user": "admin@banco.com",
            "status": "success",
            "monto": 1000.0
        }
    
    Note:
        Este endpoint NO modifica ningún dato, solo valida autenticación.
    """
    return {
        "message": "💰 Depósito autorizado",
        "user": current_user.username,
        "status": "success",
        "monto": 1000.0,
    }


@app.get("/info", summary="Info del usuario autenticado")
async def info_usuario(current_user: User = Depends(get_current_user)):
    """
    Retorna información del usuario autenticado extraída del token JWT.
    
    Útil para verificar que los claims del token se decodifican correctamente
    y que la información del usuario está disponible en endpoints protegidos.
    
    Authentication: Requiere token JWT válido en header Authorization
    
    Returns:
        dict: Datos del usuario autenticado y mensaje de confirmación
    
    Status Codes:
        - 200 OK: Token válido, información retornada
        - 401 Unauthorized: Token ausente, inválido o expirado
    
    Example Request:
        GET /info
        Headers:
            Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
    
    Example Response:
        {
            "authenticated_user": "admin@banco.com",
            "full_name": "Admin Banco",
            "disabled": false,
            "message": "✅ Autenticación JWT funcionando correctamente"
        }
    
    Use Case:
        - Verificar que el middleware de autenticación funciona
        - Confirmar que los datos del usuario están disponibles
        - Debugging de problemas de autenticación
    """
    return {
        "authenticated_user": current_user.username,
        "full_name": current_user.full_name,
        "disabled": current_user.disabled,
        "message": "✅ Autenticación JWT funcionando correctamente",
    }


# ============================================================================
# Fin del módulo test_crud.py
# ============================================================================
