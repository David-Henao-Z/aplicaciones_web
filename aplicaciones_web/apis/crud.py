# crud.py
# ============================================================================
# Módulo con el **CRUD (endpoints FastAPI)** que importa y usa las funciones
# del módulo `functions.py`. Ejecuta la API con:
#    python -m uvicorn crud:app --reload
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
import functions as svc
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    yield
    # Shutdown
    await close_pool()


app = FastAPI(
    title="API Banco - PostgreSQL",
    description="API completa para gestión bancaria con PostgreSQL",
    version="2.0.0",
    lifespan=lifespan,
)


# -------------------------
# Salud
# -------------------------
@app.get("/", summary="Healthcheck")
def root():
    return {"status": "ok", "msg": "API Banco corriendo (modular)"}


# -------------------------
# CLIENTES
# -------------------------
@app.get(
    "/clientes",
    response_model=List[Cliente],
    tags=["Clientes"],
    summary="Listar clientes",
)
async def listar_clientes(current_user: User = Depends(get_current_user)):
    """Listar todos los clientes - Requiere autenticación JWT"""
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
    """Obtener un cliente específico - Requiere autenticación JWT"""
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
    """Crear un nuevo cliente - Requiere autenticación JWT"""
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
    """Actualizar datos de un cliente - Requiere autenticación JWT"""
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
    """Eliminar un cliente - Requiere autenticación JWT"""
    try:
        await svc.eliminar_cliente(cliente_id)
        return {"message": "Cliente eliminado"}
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))


# -------------------------
# CUENTAS
# -------------------------
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
    """Listar cuentas bancarias - Requiere autenticación JWT"""
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
    """Obtener una cuenta específica - Requiere autenticación JWT"""
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
    """Crear una nueva cuenta bancaria - Requiere autenticación JWT"""
    try:
        return await svc.crear_cuenta(payload)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.delete("/cuentas/{cuenta_id}", tags=["Cuentas"], summary="Eliminar cuenta")
async def eliminar_cuenta(
    cuenta_id: UUID, current_user: User = Depends(get_current_user)
):
    """Eliminar una cuenta bancaria - Requiere autenticación JWT"""
    try:
        await svc.eliminar_cuenta(cuenta_id)
        return {"message": "Cuenta eliminada"}
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))


# -------------------------
# TIPOS DE CUENTA
# -------------------------
@app.get(
    "/tipos-cuenta",
    response_model=List[TipoCuentaModel],
    tags=["Tipos de Cuenta"],
    summary="Listar tipos de cuenta",
)
async def listar_tipos_cuenta():
    return await svc.listar_tipos_cuenta()


# -------------------------
# TRANSACCIONES
# -------------------------
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
    """Listar transacciones - Requiere autenticación JWT"""
    return await svc.listar_transacciones(cuenta_id=cuenta_id, desde=desde, hasta=hasta)


# ---- CRUD extra para cumplir enunciado ----
class TransaccionUpdate(BaseModel):
    nota: str = Field(..., min_length=1, max_length=200)


@app.get(
    "/transacciones/{tx_id}",
    response_model=Transaccion,
    tags=["Transacciones"],
    summary="Obtener transacción por ID",
)
async def obtener_tx(tx_id: UUID, current_user: User = Depends(get_current_user)):
    """Obtener una transacción específica - Requiere autenticación JWT"""
    tx = await svc.obtener_transaccion(tx_id)
    if not tx:
        raise HTTPException(status_code=404, detail="Transacción no encontrada")
    return tx


@app.delete(
    "/transacciones/{tx_id}", tags=["Transacciones"], summary="Eliminar transacción"
)
async def eliminar_tx(tx_id: UUID, current_user: User = Depends(get_current_user)):
    """Eliminar una transacción - Requiere autenticación JWT"""
    try:
        await svc.eliminar_transaccion(tx_id)
        return {"message": "Transacción eliminada"}
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))

    # ---- Operaciones (negocio) ----


@app.post(
    "/transacciones/deposito",
    response_model=Transaccion,
    status_code=201,
    tags=["Transacciones"],
    summary="Depositar",
)
async def depositar(payload: Deposito, current_user: User = Depends(get_current_user)):
    """Depositar dinero en una cuenta - Requiere autenticación JWT"""
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
    """Retirar dinero de una cuenta - Requiere autenticación JWT"""
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
    """Transferir dinero entre cuentas - Requiere autenticación JWT"""
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


@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Endpoint de login que genera un token JWT si las credenciales son válidas.
    """
    user = authenticate_user(fake_users_db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=400, detail="Credenciales incorrectas")

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Cambiar "*" por el dominio del frontend si lo deseas
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
