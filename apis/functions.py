# functions.py
# ============================================================================
# Módulo de **funciones y modelos** para la API del Banco.
# Contiene:
# - Modelos Pydantic (Cliente, Cuenta, Transaccion, etc.)
# - "Base de datos" en memoria
# - Lógica/reglas de negocio (crear/actualizar/eliminar, depositar, retirar, transferir)
# - CRUD de transacciones (obtener/actualizar/eliminar)
# ============================================================================

from __future__ import annotations
from datetime import datetime, date
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, EmailStr, conint, constr, PositiveFloat


# =========================
# Modelos (Pydantic)
# =========================
class TipoCuenta(str, Enum):
    AHORROS = "AHORROS"
    CORRIENTE = "CORRIENTE"
    CREDITO = "CREDITO"


class Cliente(BaseModel):
    id: conint(gt=0) = Field(..., example=1)
    nombre: constr(min_length=2) = Field(..., example="David Jiménez")
    email: EmailStr = Field(..., example="david@example.com")


class ClienteCreate(BaseModel):
    nombre: constr(min_length=2) = Field(..., example="David Jiménez")
    email: EmailStr = Field(..., example="david@example.com")


class Cuenta(BaseModel):
    numero: constr(min_length=6, max_length=20) = Field(..., example="ACC0001")
    cliente_id: conint(gt=0) = Field(..., example=1)
    tipo: TipoCuenta = Field(..., example="AHORROS")
    saldo: float = Field(0.0, ge=0, example=0.0)


class CuentaCreate(BaseModel):
    cliente_id: conint(gt=0)
    tipo: TipoCuenta


class TransaccionTipo(str, Enum):
    DEPOSITO = "DEPOSITO"
    RETIRO = "RETIRO"
    TRANSFERENCIA = "TRANSFERENCIA"


class Transaccion(BaseModel):
    id: int
    tipo: TransaccionTipo
    cuenta_origen: Optional[str] = Field(None, example="ACC0001")
    cuenta_destino: Optional[str] = Field(None, example="ACC0002")
    monto: PositiveFloat
    timestamp: datetime
    nota: Optional[str] = None  # Campo editable para el PUT


class Deposito(BaseModel):
    cuenta: str = Field(..., example="ACC0001")
    monto: PositiveFloat = Field(..., example=100_000.0)


class Retiro(BaseModel):
    cuenta: str = Field(..., example="ACC0001")
    monto: PositiveFloat = Field(..., example=50_000.0)


class Transferencia(BaseModel):
    origen: str = Field(..., example="ACC0001")
    destino: str = Field(..., example="ACC0002")
    monto: PositiveFloat = Field(..., example=25_000.0)
