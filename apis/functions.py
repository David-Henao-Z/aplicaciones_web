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

# =========================
# Funciones de negocio: CLIENTES
# =========================
def listar_clientes() -> List[Cliente]:
    return list(clientes.values())


def obtener_cliente(cliente_id: int) -> Optional[Cliente]:
    return clientes.get(cliente_id)


def crear_cliente(payload: ClienteCreate) -> Cliente:
    # Email único
    if any(c.email == payload.email for c in clientes.values()):
        raise ValueError("Email ya registrado")

    new_id = 1 if not clientes else max(clientes.keys()) + 1
    cliente = Cliente(id=new_id, **payload.dict())
    clientes[new_id] = cliente
    return cliente


def actualizar_cliente(cliente_id: int, payload: ClienteCreate) -> Cliente:
    if cliente_id not in clientes:
        raise KeyError("Cliente no encontrado")
    # Evitar duplicar email en otro cliente
    if any(c.email == payload.email and c.id != cliente_id for c in clientes.values()):
        raise ValueError("Email ya registrado por otro cliente")

    cliente = Cliente(id=cliente_id, **payload.dict())
    clientes[cliente_id] = cliente
    return cliente


def eliminar_cliente(cliente_id: int) -> None:
    if cliente_id not in clientes:
        raise KeyError("Cliente no encontrado")
    # No borrar si tiene cuentas
    if any(cta.cliente_id == cliente_id for cta in cuentas.values()):
        raise RuntimeError("Cliente con cuentas activas")
    del clientes[cliente_id]


# =========================
# Funciones de negocio: CUENTAS
# =========================
def listar_cuentas(cliente_id: Optional[int] = None, tipo: Optional[TipoCuenta] = None) -> List[Cuenta]:
    resultado = list(cuentas.values())
    if cliente_id is not None:
        resultado = [c for c in resultado if c.cliente_id == cliente_id]
    if tipo is not None:
        resultado = [c for c in resultado if c.tipo == tipo]
    return resultado


def obtener_cuenta(numero: str) -> Optional[Cuenta]:
    return cuentas.get(numero)


def crear_cuenta(payload: CuentaCreate) -> Cuenta:
    if payload.cliente_id not in clientes:
        raise KeyError("Cliente no existe")
    numero = _next_cta_num()
    cuenta = Cuenta(numero=numero, saldo=0.0, **payload.dict())
    cuentas[numero] = cuenta
    return cuenta


def actualizar_cuenta_tipo(numero: str, nuevo_tipo: TipoCuenta) -> Cuenta:
    cta = cuentas.get(numero)
    if not cta:
        raise KeyError("Cuenta no encontrada")
    cta.tipo = nuevo_tipo
    cuentas[numero] = cta
    return cta


def eliminar_cuenta(numero: str) -> None:
    if numero not in cuentas:
        raise KeyError("Cuenta no encontrada")
    if cuentas[numero].saldo != 0:
        raise RuntimeError("No se puede eliminar una cuenta con saldo distinto de 0")
    del cuentas[numero]    


