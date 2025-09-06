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


# =========================
# "Base de datos" en memoria
# =========================
clientes: Dict[int, Cliente] = {}
cuentas: Dict[str, Cuenta] = {}
transacciones: List[Transaccion] = []
_seq_tx = 0
_seq_cta = 0


# =========================
# Utilidades internas
# =========================
def _next_tx_id() -> int:
    """Genera un ID secuencial para transacciones."""
    global _seq_tx
    _seq_tx += 1
    return _seq_tx


def _next_cta_num() -> str:
    """Genera números como ACC0001, ACC0002..."""
    global _seq_cta
    _seq_cta += 1
    return f"ACC{_seq_cta:04d}"


def _registrar_tx(
    tipo: TransaccionTipo, monto: float, cta_origen: Optional[str], cta_destino: Optional[str]
) -> Transaccion:
    """Registra la transacción en memoria y retorna el objeto creado."""
    tx = Transaccion(
        id=_next_tx_id(),
        tipo=tipo,
        cuenta_origen=cta_origen,
        cuenta_destino=cta_destino,
        monto=monto,
        timestamp=datetime.now(),
    )
    transacciones.append(tx)
    return tx