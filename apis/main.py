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