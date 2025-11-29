# crud.py
"""
Capa de Controladores - Endpoints REST de la API Bancaria.

Este módulo define todos los endpoints de FastAPI que exponen la lógica
de negocio del sistema bancario a través de una API REST.

Arquitectura:
    - Capa de Presentación (este archivo)
    - Importa lógica de negocio desde functions.py
    - Importa autenticación JWT desde auth.py
    - Importa conexiones DB desde database.py

Métodos HTTP soportados:
    - GET: Consultas (listar, obtener)
    - POST: Creación (clientes, cuentas, transacciones)
    - PUT: Actualización (clientes)
    - DELETE: Eliminación (clientes, cuentas, transacciones)

Autenticación:
    - Todos los endpoints (excepto /token y /tipos-cuenta) requieren JWT
    - Token obtenido mediante POST /token con credenciales
    - Token debe enviarse en header: Authorization: Bearer <token>

Documentación interactiva:
    - Swagger UI: http://localhost:8000/docs
    - ReDoc: http://localhost:8000/redoc
    - OpenAPI JSON: http://localhost:8000/openapi.json

Ejecución:
    Desde la carpeta `apis/` con PYTHONPATH configurado:
    
    PowerShell:
    >>> cd C:\Users\...\aplicaciones_web\aplicaciones_web\apis
    >>> $env:PYTHONPATH="C:\Users\...\aplicaciones_web"
    >>> python -m uvicorn crud:app --reload
    
    El servidor estará disponible en: http://127.0.0.1:8000

Códigos de respuesta HTTP:
    - 200 OK: Operación exitosa (GET, PUT, DELETE)
    - 201 Created: Recurso creado exitosamente (POST)
    - 400 Bad Request: Validación fallida o regla de negocio violada
    - 401 Unauthorized: Token inválido o ausente
    - 404 Not Found: Recurso no encontrado

Tags (grupos de endpoints):
    - Clientes: CRUD de clientes
    - Cuentas: CRUD de cuentas bancarias
    - Tipos de Cuenta: Catálogo de tipos (AHORROS, CORRIENTE)
    - Transacciones: CRUD y operaciones bancarias (depósito, retiro, transferencia)

Version: 2.0.0
Author: Sistema Bancario - Aplicaciones Web
License: MIT
"""

# ============================================================================
# Importaciones
# ============================================================================
from fastapi import Depends
from fastapi.security import OAuth2PasswordRequestForm
from auth import (
    authenticate_user,
    create_access_token,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    Token,
    get_current_user,
    User,
    fake_users_db,
)
from datetime import timedelta

from contextlib import asynccontextmanager
from datetime import date
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from uuid import UUID
import functions as svc  # Capa de negocio
from functions import (
    Cliente,
    ClienteCreate,
    Cuenta,
    CuentaCreate,
    Transaccion,
    TipoCuenta,
    TipoCuentaModel,
    Deposito,
    Retiro,
    Transferencia,
)
from database import close_pool


# ============================================================================
# Lifecycle Management
# ============================================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Maneja el ciclo de vida de la aplicación FastAPI.
    
    Startup:
        - El pool de conexiones se crea automáticamente en el primer uso
        - No requiere inicialización explícita
    
    Shutdown:
        - Cierra el pool de conexiones PostgreSQL
        - Libera recursos de red y memoria
        - Asegura un cierre ordenado de todas las conexiones
    
    Example:
        Esta función es usada automáticamente por FastAPI:
        >>> app = FastAPI(lifespan=lifespan)
    """
    # Startup - No se requiere inicialización explícita
    yield
    # Shutdown - Cerrar conexiones DB
    await close_pool()


# ============================================================================
# Aplicación FastAPI
# ============================================================================
app = FastAPI(
    title="API Banco - PostgreSQL",
    description="API completa para gestión bancaria con PostgreSQL",
    version="2.0.0",
    lifespan=lifespan,
)


# ============================================================================
# ENDPOINTS - Healthcheck
# ============================================================================
@app.get("/", summary="Healthcheck")
def root():
    """
    Verifica que la API esté activa y respondiendo.
    
    Returns:
        dict: Estado del servidor y mensaje
    
    Status: 200 OK
    
    Authentication: No requiere autenticación
    
    Example Response:
        {
            "status": "ok",
            "msg": "API Banco corriendo (modular)"
        }
    """
    return {"status": "ok", "msg": "API Banco corriendo (modular)"}


# ============================================================================
# ENDPOINTS - Clientes
# ============================================================================
@app.get(
    "/clientes",
    response_model=List[Cliente],
    tags=["Clientes"],
    summary="Listar clientes",
)
async def listar_clientes(current_user: User = Depends(get_current_user)):
    """
    Lista todos los clientes registrados en el sistema.
    
    Authentication: Requiere token JWT válido
    
    Returns:
        List[Cliente]: Lista de todos los clientes (puede estar vacía)
    
    Status Codes:
        - 200 OK: Lista retornada exitosamente
        - 401 Unauthorized: Token inválido o ausente
    
    Example Response:
        [
            {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "nombre_completo": "Juan Pérez",
                "documento": "12345678",
                "fecha_creacion": "2024-01-15T10:30:00",
                "fecha_edicion": "2024-01-15T10:30:00"
            }
        ]
    """
    return await svc.listar_clientes()


@app.get(
    "/clientes/{cliente_id}",
    response_model=Cliente,
    tags=["Clientes"],
    summary="Obtener cliente por ID",
)
async def obtener_cliente(
    cliente_id: UUID, current_user: User = Depends(get_current_user)
):
    """
    Obtiene los detalles de un cliente específico.
    
    Path Parameters:
        cliente_id (UUID): Identificador único del cliente
    
    Authentication: Requiere token JWT válido
    
    Returns:
        Cliente: Datos completos del cliente
    
    Status Codes:
        - 200 OK: Cliente encontrado
        - 401 Unauthorized: Token inválido
        - 404 Not Found: Cliente no existe
    
    Example Response:
        {
            "id": "123e4567-e89b-12d3-a456-426614174000",
            "nombre_completo": "Juan Pérez",
            "documento": "12345678",
            "fecha_creacion": "2024-01-15T10:30:00",
            "fecha_edicion": "2024-01-15T10:30:00"
        }
    """
    cliente = await svc.obtener_cliente(cliente_id)
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return cliente


@app.post(
    "/clientes",
    response_model=Cliente,
    status_code=201,
    tags=["Clientes"],
    summary="Crear cliente",
)
async def crear_cliente(
    payload: ClienteCreate, current_user: User = Depends(get_current_user)
):
    """
    Registra un nuevo cliente en el sistema.
    
    Request Body:
        ClienteCreate:
            - nombre_completo (str): Nombre completo del cliente
            - documento (str): Número de documento único
    
    Authentication: Requiere token JWT válido
    
    Returns:
        Cliente: Datos del cliente recién creado con ID y timestamps
    
    Status Codes:
        - 201 Created: Cliente creado exitosamente
        - 400 Bad Request: Documento duplicado o validación fallida
        - 401 Unauthorized: Token inválido
    
    Business Rules:
        - El documento debe ser único en todo el sistema
        - El ID se genera automáticamente (UUID v4)
    
    Example Request:
        {
            "nombre_completo": "María García",
            "documento": "87654321"
        }
    
    Example Response:
        {
            "id": "456e7890-a12b-34c5-d678-901234567890",
            "nombre_completo": "María García",
            "documento": "87654321",
            "fecha_creacion": "2024-01-20T15:45:00",
            "fecha_edicion": "2024-01-20T15:45:00"
        }
    """
    try:
        return await svc.crear_cliente(payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.put(
    "/clientes/{cliente_id}",
    response_model=Cliente,
    tags=["Clientes"],
    summary="Actualizar cliente",
)
async def actualizar_cliente(
    cliente_id: UUID,
    payload: ClienteCreate,
    current_user: User = Depends(get_current_user),
):
    """
    Actualiza los datos de un cliente existente.
    
    Path Parameters:
        cliente_id (UUID): ID del cliente a actualizar
    
    Request Body:
        ClienteCreate:
            - nombre_completo (str): Nuevo nombre completo
            - documento (str): Nuevo documento (debe ser único)
    
    Authentication: Requiere token JWT válido
    
    Returns:
        Cliente: Datos actualizados del cliente
    
    Status Codes:
        - 200 OK: Cliente actualizado exitosamente
        - 400 Bad Request: Documento duplicado (otro cliente)
        - 401 Unauthorized: Token inválido
        - 404 Not Found: Cliente no existe
    
    Business Rules:
        - El cliente debe existir
        - El nuevo documento debe ser único (excepto el propio cliente)
        - fecha_edicion se actualiza automáticamente
    
    Example Request:
        {
            "nombre_completo": "Juan Pérez Martínez",
            "documento": "12345678"
        }
    """
    try:
        return await svc.actualizar_cliente(cliente_id, payload)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/clientes/{cliente_id}", tags=["Clientes"], summary="Eliminar cliente")
async def eliminar_cliente(
    cliente_id: UUID, current_user: User = Depends(get_current_user)
):
    """
    Elimina un cliente del sistema.
    
    Path Parameters:
        cliente_id (UUID): ID del cliente a eliminar
    
    Authentication: Requiere token JWT válido
    
    Returns:
        dict: Mensaje de confirmación
    
    Status Codes:
        - 200 OK: Cliente eliminado exitosamente
        - 400 Bad Request: Cliente tiene cuentas activas
        - 401 Unauthorized: Token inválido
        - 404 Not Found: Cliente no existe
    
    Business Rules:
        - El cliente no debe tener cuentas asociadas
        - Es una eliminación física (irreversible)
    
    Example Response:
        {
            "message": "Cliente eliminado"
        }
    """
    try:
        await svc.eliminar_cliente(cliente_id)
        return {"message": "Cliente eliminado"}
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================================
# ENDPOINTS - Cuentas
# ============================================================================
@app.get(
    "/cuentas",
    response_model=List[Cuenta],
    tags=["Cuentas"],
    summary="Listar cuentas (filtrable)",
    description="Query params: `cliente_id`, `tipo`",
)
async def listar_cuentas(
    cliente_id: Optional[UUID] = Query(None, description="Filtrar por cliente"),
    tipo: Optional[str] = Query(
        None, description="Filtrar por tipo de cuenta (AHORROS, CORRIENTE)"
    ),
    current_user: User = Depends(get_current_user),
):
    """
    Lista cuentas bancarias con filtros opcionales.
    
    Query Parameters:
        cliente_id (Optional[UUID]): Filtra cuentas de un cliente específico
        tipo (Optional[str]): Filtra por tipo (AHORROS, CORRIENTE, etc.)
    
    Authentication: Requiere token JWT válido
    
    Returns:
        List[Cuenta]: Lista de cuentas (puede estar vacía)
    
    Status Codes:
        - 200 OK: Lista retornada exitosamente
        - 401 Unauthorized: Token inválido
    
    Example Request:
        GET /cuentas?cliente_id=123e4567-e89b-12d3-a456-426614174000&tipo=AHORROS
    
    Example Response:
        [
            {
                "id": "789e0123-b45c-67d8-e901-234567890abc",
                "numero": "1234567890",
                "id_cliente": "123e4567-e89b-12d3-a456-426614174000",
                "id_tipo_cuenta": "456e7890-c12d-34e5-f678-901234567def",
                "saldo": 1500.50,
                "fecha_creacion": "2024-01-20T10:00:00",
                "fecha_edicion": "2024-01-20T10:00:00"
            }
        ]
    """
    return await svc.listar_cuentas(cliente_id=cliente_id, tipo=tipo)


@app.get(
    "/cuentas/{cuenta_id}",
    response_model=Cuenta,
    tags=["Cuentas"],
    summary="Obtener cuenta por ID",
)
async def obtener_cuenta(
    cuenta_id: UUID, current_user: User = Depends(get_current_user)
):
    """
    Obtiene los detalles de una cuenta específica.
    
    Path Parameters:
        cuenta_id (UUID): Identificador único de la cuenta
    
    Authentication: Requiere token JWT válido
    
    Returns:
        Cuenta: Datos completos de la cuenta incluyendo saldo actual
    
    Status Codes:
        - 200 OK: Cuenta encontrada
        - 401 Unauthorized: Token inválido
        - 404 Not Found: Cuenta no existe
    
    Example Response:
        {
            "id": "789e0123-b45c-67d8-e901-234567890abc",
            "numero": "1234567890",
            "id_cliente": "123e4567-e89b-12d3-a456-426614174000",
            "id_tipo_cuenta": "456e7890-c12d-34e5-f678-901234567def",
            "saldo": 1500.50,
            "fecha_creacion": "2024-01-20T10:00:00",
            "fecha_edicion": "2024-01-20T10:00:00"
        }
    """
    cta = await svc.obtener_cuenta(cuenta_id)
    if not cta:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada")
    return cta


@app.post(
    "/cuentas",
    response_model=Cuenta,
    status_code=201,
    tags=["Cuentas"],
    summary="Crear cuenta",
)
async def crear_cuenta(
    payload: CuentaCreate, current_user: User = Depends(get_current_user)
):
    """
    Crea una nueva cuenta bancaria para un cliente.
    
    Request Body:
        CuentaCreate:
            - id_cliente (UUID): ID del cliente propietario
            - id_tipo_cuenta (UUID): ID del tipo de cuenta (AHORROS, CORRIENTE)
    
    Authentication: Requiere token JWT válido
    
    Returns:
        Cuenta: Datos de la cuenta recién creada con saldo inicial de 0
    
    Status Codes:
        - 201 Created: Cuenta creada exitosamente
        - 401 Unauthorized: Token inválido
        - 404 Not Found: Cliente o tipo de cuenta no existe
    
    Business Rules:
        - El cliente debe existir previamente
        - El tipo de cuenta debe existir en el catálogo
        - El número de cuenta se genera automáticamente
        - El saldo inicial es siempre 0.0
    
    Example Request:
        {
            "id_cliente": "123e4567-e89b-12d3-a456-426614174000",
            "id_tipo_cuenta": "456e7890-c12d-34e5-f678-901234567def"
        }
    
    Example Response:
        {
            "id": "789e0123-b45c-67d8-e901-234567890abc",
            "numero": "9876543210",
            "id_cliente": "123e4567-e89b-12d3-a456-426614174000",
            "id_tipo_cuenta": "456e7890-c12d-34e5-f678-901234567def",
            "saldo": 0.0,
            "fecha_creacion": "2024-01-21T14:30:00",
            "fecha_edicion": "2024-01-21T14:30:00"
        }
    """
    try:
        return await svc.crear_cuenta(payload)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.delete("/cuentas/{cuenta_id}", tags=["Cuentas"], summary="Eliminar cuenta")
async def eliminar_cuenta(
    cuenta_id: UUID, current_user: User = Depends(get_current_user)
):
    """
    Elimina una cuenta bancaria del sistema.
    
    Path Parameters:
        cuenta_id (UUID): ID de la cuenta a eliminar
    
    Authentication: Requiere token JWT válido
    
    Returns:
        dict: Mensaje de confirmación
    
    Status Codes:
        - 200 OK: Cuenta eliminada exitosamente
        - 400 Bad Request: La cuenta tiene saldo diferente de 0
        - 401 Unauthorized: Token inválido
        - 404 Not Found: Cuenta no existe
    
    Business Rules:
        - El saldo debe ser exactamente 0 para poder eliminar
        - Es una eliminación física (irreversible)
        - Las transacciones asociadas permanecen en el historial
    
    Example Response:
        {
            "message": "Cuenta eliminada"
        }
    """
    try:
        await svc.eliminar_cuenta(cuenta_id)
        return {"message": "Cuenta eliminada"}
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================================
# ENDPOINTS - Tipos de Cuenta (Catálogo)
# ============================================================================
@app.get(
    "/tipos-cuenta",
    response_model=List[TipoCuentaModel],
    tags=["Tipos de Cuenta"],
    summary="Listar tipos de cuenta",
)
async def listar_tipos_cuenta():
    """
    Lista todos los tipos de cuenta disponibles en el sistema.
    
    Authentication: NO requiere autenticación (endpoint público)
    
    Returns:
        List[TipoCuentaModel]: Lista de tipos de cuenta ordenados alfabéticamente
    
    Status Codes:
        - 200 OK: Lista retornada exitosamente
    
    Use Case:
        - Útil para poblar formularios de creación de cuentas
        - Muestra las opciones disponibles (AHORROS, CORRIENTE, NOMINA, etc.)
    
    Example Response:
        [
            {
                "id": "456e7890-c12d-34e5-f678-901234567def",
                "nombre": "AHORROS",
                "descripcion": "Cuenta de ahorros con intereses"
            },
            {
                "id": "789e0123-d45e-67f8-g901-234567890ghi",
                "nombre": "CORRIENTE",
                "descripcion": "Cuenta corriente para transacciones diarias"
            }
        ]
    
    Note:
        - Este es un endpoint público (no requiere JWT)
        - Los tipos de cuenta son datos maestros del sistema
    """
    return await svc.listar_tipos_cuenta()


# ============================================================================
# ENDPOINTS - Transacciones
# ============================================================================
@app.get(
    "/transacciones",
    response_model=List[Transaccion],
    tags=["Transacciones"],
    summary="Listar transacciones (filtrable)",
    description="Query params: `cuenta_id`, `desde`, `hasta` (YYYY-MM-DD)",
)
async def listar_transacciones(
    cuenta_id: Optional[UUID] = Query(
        None, description="Filtrar por ID de cuenta (origen o destino)"
    ),
    desde: Optional[date] = Query(None, description="Fecha mínima (YYYY-MM-DD)"),
    hasta: Optional[date] = Query(None, description="Fecha máxima (YYYY-MM-DD)"),
    current_user: User = Depends(get_current_user),
):
    """
    Lista transacciones con filtros opcionales por cuenta y rango de fechas.
    
    Query Parameters:
        cuenta_id (Optional[UUID]): Filtra transacciones donde la cuenta aparece
            como origen O destino (incluye depósitos, retiros y transferencias)
        desde (Optional[date]): Fecha mínima en formato YYYY-MM-DD
        hasta (Optional[date]): Fecha máxima en formato YYYY-MM-DD
    
    Authentication: Requiere token JWT válido
    
    Returns:
        List[Transaccion]: Lista de transacciones ordenadas por fecha descendente
    
    Status Codes:
        - 200 OK: Lista retornada exitosamente
        - 401 Unauthorized: Token inválido
    
    Example Request:
        GET /transacciones?cuenta_id=789e0123-b45c-67d8-e901-234567890abc&desde=2024-01-01&hasta=2024-01-31
    
    Example Response:
        [
            {
                "id": "abc12345-d67e-89f0-g123-456789012hij",
                "tipo": "TRANSFERENCIA",
                "id_cuenta_origen": "789e0123-b45c-67d8-e901-234567890abc",
                "id_cuenta_destino": "def45678-i90j-12k3-l456-789012345mno",
                "monto": 250.00,
                "momento": "2024-01-25T14:30:00",
                "fecha_creacion": "2024-01-25T14:30:00",
                "fecha_edicion": "2024-01-25T14:30:00"
            }
        ]
    """
    return await svc.listar_transacciones(cuenta_id=cuenta_id, desde=desde, hasta=hasta)


# ---- CRUD adicional de transacciones ----
class TransaccionUpdate(BaseModel):
    """
    Modelo para actualizar notas de transacción (funcionalidad futura).
    
    Attributes:
        nota (str): Nota descriptiva de la transacción (1-200 caracteres)
    
    Note:
        Este modelo está definido para cumplir con el enunciado,
        pero actualmente no hay endpoint PUT para transacciones.
    """
    nota: str = Field(..., min_length=1, max_length=200)


@app.get(
    "/transacciones/{tx_id}",
    response_model=Transaccion,
    tags=["Transacciones"],
    summary="Obtener transacción por ID",
)
async def obtener_tx(tx_id: UUID, current_user: User = Depends(get_current_user)):
    """
    Obtiene los detalles de una transacción específica.
    
    Path Parameters:
        tx_id (UUID): Identificador único de la transacción
    
    Authentication: Requiere token JWT válido
    
    Returns:
        Transaccion: Datos completos de la transacción
    
    Status Codes:
        - 200 OK: Transacción encontrada
        - 401 Unauthorized: Token inválido
        - 404 Not Found: Transacción no existe
    
    Example Response:
        {
            "id": "abc12345-d67e-89f0-g123-456789012hij",
            "tipo": "DEPOSITO",
            "id_cuenta_origen": null,
            "id_cuenta_destino": "789e0123-b45c-67d8-e901-234567890abc",
            "monto": 1000.00,
            "momento": "2024-01-20T10:15:00",
            "fecha_creacion": "2024-01-20T10:15:00",
            "fecha_edicion": "2024-01-20T10:15:00"
        }
    """
    tx = await svc.obtener_transaccion(tx_id)
    if not tx:
        raise HTTPException(status_code=404, detail="Transacción no encontrada")
    return tx


@app.delete(
    "/transacciones/{tx_id}", tags=["Transacciones"], summary="Eliminar transacción"
)
async def eliminar_tx(tx_id: UUID, current_user: User = Depends(get_current_user)):
    """
    Elimina un registro de transacción del historial.
    
    ADVERTENCIA: Esta operación NO revierte el impacto en los saldos.
    Solo elimina el registro del historial. Usar con precaución.
    
    Path Parameters:
        tx_id (UUID): ID de la transacción a eliminar
    
    Authentication: Requiere token JWT válido
    
    Returns:
        dict: Mensaje de confirmación
    
    Status Codes:
        - 200 OK: Transacción eliminada exitosamente
        - 401 Unauthorized: Token inválido
        - 404 Not Found: Transacción no existe
    
    Warning:
        - Esta función NO ajusta los saldos de las cuentas
        - Puede causar inconsistencias entre saldos y transacciones
        - Recomendado solo para corrección de errores
    
    Recommended Alternative:
        Para revertir una transacción, crear una transacción inversa
        que mantiene la trazabilidad del historial.
    
    Example Response:
        {
            "message": "Transacción eliminada"
        }
    """
    try:
        await svc.eliminar_transaccion(tx_id)
        return {"message": "Transacción eliminada"}
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ============================================================================
# ENDPOINTS - Operaciones Bancarias
# ============================================================================
@app.post(
    "/transacciones/deposito",
    response_model=Transaccion,
    status_code=201,
    tags=["Transacciones"],
    summary="Depositar",
)
async def depositar(payload: Deposito, current_user: User = Depends(get_current_user)):
    """
    Deposita dinero en una cuenta bancaria.
    
    Request Body:
        Deposito:
            - id_cuenta (UUID): ID de la cuenta receptora
            - monto (float): Cantidad a depositar (debe ser > 0)
    
    Authentication: Requiere token JWT válido
    
    Returns:
        Transaccion: Registro de la transacción de depósito
    
    Status Codes:
        - 201 Created: Depósito exitoso
        - 400 Bad Request: Monto inválido (validado por Pydantic)
        - 401 Unauthorized: Token inválido
        - 404 Not Found: Cuenta no existe
    
    Business Rules:
        - El monto debe ser positivo
        - El saldo se incrementa en el monto depositado
        - Se registra como tipo DEPOSITO
        - La cuenta origen es NULL (dinero externo)
    
    Example Request:
        {
            "id_cuenta": "789e0123-b45c-67d8-e901-234567890abc",
            "monto": 1000.00
        }
    
    Example Response:
        {
            "id": "pqr56789-s01t-23u4-v567-890123456wxy",
            "tipo": "DEPOSITO",
            "id_cuenta_origen": null,
            "id_cuenta_destino": "789e0123-b45c-67d8-e901-234567890abc",
            "monto": 1000.00,
            "momento": "2024-01-22T16:45:00",
            "fecha_creacion": "2024-01-22T16:45:00",
            "fecha_edicion": "2024-01-22T16:45:00"
        }
    """
    try:
        return await svc.depositar(payload.id_cuenta, payload.monto)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post(
    "/transacciones/retiro",
    response_model=Transaccion,
    status_code=201,
    tags=["Transacciones"],
    summary="Retirar",
)
async def retirar(payload: Retiro, current_user: User = Depends(get_current_user)):
    """
    Retira dinero de una cuenta bancaria.
    
    Request Body:
        Retiro:
            - id_cuenta (UUID): ID de la cuenta a debitar
            - monto (float): Cantidad a retirar (debe ser > 0)
    
    Authentication: Requiere token JWT válido
    
    Returns:
        Transaccion: Registro de la transacción de retiro
    
    Status Codes:
        - 201 Created: Retiro exitoso
        - 400 Bad Request: Fondos insuficientes o monto inválido
        - 401 Unauthorized: Token inválido
        - 404 Not Found: Cuenta no existe
    
    Business Rules:
        - El monto debe ser positivo
        - El saldo debe ser >= monto (no se permiten sobregiros)
        - El saldo se decrementa en el monto retirado
        - Se registra como tipo RETIRO
        - La cuenta destino es NULL (dinero externo)
    
    Example Request:
        {
            "id_cuenta": "789e0123-b45c-67d8-e901-234567890abc",
            "monto": 500.00
        }
    
    Example Response:
        {
            "id": "xyz78901-z23a-45b6-c789-012345678def",
            "tipo": "RETIRO",
            "id_cuenta_origen": "789e0123-b45c-67d8-e901-234567890abc",
            "id_cuenta_destino": null,
            "monto": 500.00,
            "momento": "2024-01-22T17:00:00",
            "fecha_creacion": "2024-01-22T17:00:00",
            "fecha_edicion": "2024-01-22T17:00:00"
        }
    """
    try:
        return await svc.retirar(payload.id_cuenta, payload.monto)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post(
    "/transacciones/transferencia",
    response_model=Transaccion,
    status_code=201,
    tags=["Transacciones"],
    summary="Transferir",
)
async def transferir(
    payload: Transferencia, current_user: User = Depends(get_current_user)
):
    """
    Transfiere dinero entre dos cuentas bancarias.
    
    Request Body:
        Transferencia:
            - id_cuenta_origen (UUID): ID de la cuenta a debitar
            - id_cuenta_destino (UUID): ID de la cuenta a acreditar
            - monto (float): Cantidad a transferir (debe ser > 0)
    
    Authentication: Requiere token JWT válido
    
    Returns:
        Transaccion: Registro de la transacción de transferencia
    
    Status Codes:
        - 201 Created: Transferencia exitosa
        - 400 Bad Request: Fondos insuficientes, cuentas iguales, o monto inválido
        - 401 Unauthorized: Token inválido
        - 404 Not Found: Alguna cuenta no existe
    
    Business Rules:
        - Las cuentas origen y destino deben ser diferentes
        - Ambas cuentas deben existir
        - El saldo origen debe ser >= monto
        - La operación es atómica (todo o nada)
        - Se registra como tipo TRANSFERENCIA
    
    ACID Transaction:
        Esta operación usa una transacción explícita para garantizar:
        - Atomicidad: Ambas actualizaciones ocurren o ninguna
        - Consistencia: Los saldos son consistentes en todo momento
        - Isolation: Otras transacciones no ven estados intermedios
        - Durability: Una vez completada, los cambios son permanentes
    
    Example Request:
        {
            "id_cuenta_origen": "789e0123-b45c-67d8-e901-234567890abc",
            "id_cuenta_destino": "def45678-i90j-12k3-l456-789012345mno",
            "monto": 250.00
        }
    
    Example Response:
        {
            "id": "ghi90123-j45k-67l8-m901-234567890pqr",
            "tipo": "TRANSFERENCIA",
            "id_cuenta_origen": "789e0123-b45c-67d8-e901-234567890abc",
            "id_cuenta_destino": "def45678-i90j-12k3-l456-789012345mno",
            "monto": 250.00,
            "momento": "2024-01-22T17:30:00",
            "fecha_creacion": "2024-01-22T17:30:00",
            "fecha_edicion": "2024-01-22T17:30:00"
        }
    
    Note:
        Esta es la operación más compleja del sistema. Usa transacciones
        explícitas de PostgreSQL para garantizar consistencia completa.
    """
    try:
        return await svc.transferir(
            payload.id_cuenta_origen, payload.id_cuenta_destino, payload.monto
        )
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================================
# ENDPOINT - Autenticación JWT
# ============================================================================
@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Genera un token JWT para autenticación en la API.
    
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
        - 400 Bad Request: Credenciales incorrectas
    
    Token Usage:
        Una vez obtenido el token, inclúyelo en todas las requests:
        
        Header:
            Authorization: Bearer <access_token>
    
    Token Expiration:
        - El token expira después de 60 minutos (ACCESS_TOKEN_EXPIRE_MINUTES)
        - Después de expirar, debes obtener un nuevo token
    
    Security:
        - Las contraseñas se verifican usando bcrypt
        - Los tokens se firman con HS256 + SECRET_KEY
        - El token contiene el username en el claim "sub"
    
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
    
    Example Usage in Swagger UI:
        1. Ir a /docs
        2. Click en el botón "Authorize" (candado)
        3. Ingresar credenciales: admin@banco.com / admin123
        4. Click "Authorize"
        5. Ahora puedes usar todos los endpoints protegidos
    
    Note:
        - Este endpoint usa OAuth2 Password Flow
        - Los datos se envían como application/x-www-form-urlencoded
        - Swagger UI maneja esto automáticamente
    """
    user = authenticate_user(fake_users_db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=400, detail="Credenciales incorrectas")

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


# ============================================================================
# Configuración de CORS (Cross-Origin Resource Sharing)
# ============================================================================
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    # allow_origins: Lista de orígenes permitidos
    # "*" permite TODOS los orígenes (útil para desarrollo)
    # En producción, especificar dominios exactos: ["https://miapp.com"]
    allow_origins=["*"],
    
    # allow_credentials: Permitir envío de cookies/tokens en requests cross-origin
    # Requerido para autenticación JWT desde frontend en diferente dominio
    allow_credentials=True,
    
    # allow_methods: Métodos HTTP permitidos en requests cross-origin
    # "*" permite GET, POST, PUT, DELETE, OPTIONS, etc.
    allow_methods=["*"],
    
    # allow_headers: Headers personalizados permitidos en requests
    # "*" permite Authorization, Content-Type, etc.
    allow_headers=["*"],
)

# ============================================================================
# Fin del módulo crud.py
# ============================================================================
