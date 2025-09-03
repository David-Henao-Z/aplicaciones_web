# crud.py
# ============================================================================
# Módulo con el **CRUD (endpoints FastAPI)** que importa y usa las funciones
# del módulo `functions.py`. Ejecuta la API con:
#    python -m uvicorn crud:app --reload
# ============================================================================

from datetime import date
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, constr

import functions as svc
from functions import (
    Cliente, ClienteCreate, Cuenta, CuentaCreate, Transaccion, TipoCuenta,
    Deposito, Retiro, Transferencia
)

app = FastAPI(
    title="API Banco - Parcial 1 (modular)",
    description="Endpoints FastAPI que delegan la lógica a functions.py",
    version="1.2.0",
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
@app.get("/clientes", response_model=List[Cliente], tags=["Clientes"], summary="Listar clientes")
def listar_clientes():
    return svc.listar_clientes()


@app.get("/clientes/{cliente_id}", response_model=Cliente, tags=["Clientes"], summary="Obtener cliente por ID")
def obtener_cliente(cliente_id: int):
    cliente = svc.obtener_cliente(cliente_id)
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return cliente


@app.post("/clientes", response_model=Cliente, status_code=201, tags=["Clientes"], summary="Crear cliente")
def crear_cliente(payload: ClienteCreate):
    try:
        return svc.crear_cliente(payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.put("/clientes/{cliente_id}", response_model=Cliente, tags=["Clientes"], summary="Actualizar cliente")
def actualizar_cliente(cliente_id: int, payload: ClienteCreate):
    try:
        return svc.actualizar_cliente(cliente_id, payload)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/clientes/{cliente_id}", tags=["Clientes"], summary="Eliminar cliente")
def eliminar_cliente(cliente_id: int):
    try:
        svc.eliminar_cliente(cliente_id)
        return {"message": "Cliente eliminado"}
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    

# -------------------------
# TRANSACCIONES
# -------------------------
@app.get(
    "/transacciones",
    response_model=List[Transaccion],
    tags=["Transacciones"],
    summary="Listar transacciones (filtrable)",
    description="Query params: `cuenta`, `desde`, `hasta` (YYYY-MM-DD)",
)
def listar_transacciones(
    cuenta: Optional[str] = Query(None, description="Filtrar por número de cuenta (origen o destino)"),
    desde: Optional[date] = Query(None, description="Fecha mínima (YYYY-MM-DD)"),
    hasta: Optional[date] = Query(None, description="Fecha máxima (YYYY-MM-DD)"),
):
    return svc.listar_transacciones(cuenta=cuenta, desde=desde, hasta=hasta)


# ---- CRUD extra para cumplir enunciado ----
class TransaccionUpdate(BaseModel):
    nota: constr(min_length=1, max_length=200)


@app.get("/transacciones/{tx_id}", response_model=Transaccion, tags=["Transacciones"], summary="Obtener transacción por ID")
def obtener_tx(tx_id: int):
    tx = svc.obtener_transaccion(tx_id)
    if not tx:
        raise HTTPException(status_code=404, detail="Transacción no encontrada")
    return tx


@app.put("/transacciones/{tx_id}", response_model=Transaccion, tags=["Transacciones"], summary="Actualizar transacción")
def actualizar_tx(tx_id: int, payload: TransaccionUpdate):
    try:
        return svc.actualizar_transaccion(tx_id, payload.nota)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.delete("/transacciones/{tx_id}", tags=["Transacciones"], summary="Eliminar transacción")
def eliminar_tx(tx_id: int):
    try:
        svc.eliminar_transaccion(tx_id)
        return {"message": "Transacción eliminada"}
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))