# functions.py
# ============================================================================
# Módulo de **funciones y modelos** para la API del Banco con PostgreSQL.
# Contiene:
# - Modelos Pydantic actualizados para usar UUIDs
# - Funciones para interactuar con PostgreSQL
# - Lógica/reglas de negocio (crear/actualizar/eliminar, depositar, retirar, transferir)
# ============================================================================

from __future__ import annotations
from datetime import datetime, date
from enum import Enum
from typing import Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, EmailStr, constr, PositiveFloat
from aplicaciones_web.apis.database import get_db


# =========================
# Modelos (Pydantic)
# =========================
class TipoCuenta(str, Enum):
    AHORROS = "AHORROS"
    CORRIENTE = "CORRIENTE"


class Cliente(BaseModel):
    id: UUID = Field(..., example="123e4567-e89b-12d3-a456-426614174000")
    nombre_completo: str = Field(..., min_length=2, example="David Jiménez")
    documento: str = Field(..., example="12345678")
    fecha_creacion: datetime = Field(default_factory=datetime.now)
    fecha_edicion: Optional[datetime] = None


class ClienteCreate(BaseModel):
    nombre_completo: str = Field(..., min_length=2, example="David Jiménez")
    documento: str = Field(..., example="12345678")


class TipoCuentaModel(BaseModel):
    id: UUID = Field(..., example="123e4567-e89b-12d3-a456-426614174000")
    nombre: str = Field(..., example="AHORROS")
    descripcion: Optional[str] = Field(None, example="Cuenta de ahorros")


class Cuenta(BaseModel):
    id: UUID = Field(..., example="123e4567-e89b-12d3-a456-426614174000")
    numero: str = Field(..., example="ACC0001")
    id_cliente: UUID = Field(..., example="123e4567-e89b-12d3-a456-426614174000")
    id_tipo_cuenta: UUID = Field(..., example="123e4567-e89b-12d3-a456-426614174000")
    saldo: float = Field(0.0, ge=0, example=0.0)
    fecha_creacion: datetime = Field(default_factory=datetime.now)
    fecha_edicion: Optional[datetime] = None


class CuentaCreate(BaseModel):
    id_cliente: UUID = Field(..., example="123e4567-e89b-12d3-a456-426614174000")
    id_tipo_cuenta: UUID = Field(..., example="123e4567-e89b-12d3-a456-426614174000")


class TransaccionTipo(str, Enum):
    DEPOSITO = "DEPOSITO"
    RETIRO = "RETIRO"
    TRANSFERENCIA = "TRANSFERENCIA"


class Transaccion(BaseModel):
    id: UUID = Field(..., example="123e4567-e89b-12d3-a456-426614174000")
    tipo: TransaccionTipo
    id_cuenta_origen: Optional[UUID] = Field(
        None, example="123e4567-e89b-12d3-a456-426614174000"
    )
    id_cuenta_destino: Optional[UUID] = Field(
        None, example="123e4567-e89b-12d3-a456-426614174000"
    )
    monto: PositiveFloat
    momento: datetime = Field(default_factory=datetime.now)
    fecha_creacion: datetime = Field(default_factory=datetime.now)
    fecha_edicion: Optional[datetime] = None


class Deposito(BaseModel):
    id_cuenta: UUID = Field(..., example="123e4567-e89b-12d3-a456-426614174000")
    monto: PositiveFloat = Field(..., example=100000.0)


class Retiro(BaseModel):
    id_cuenta: UUID = Field(..., example="123e4567-e89b-12d3-a456-426614174000")
    monto: PositiveFloat = Field(..., example=50000.0)


class Transferencia(BaseModel):
    id_cuenta_origen: UUID = Field(..., example="123e4567-e89b-12d3-a456-426614174000")
    id_cuenta_destino: UUID = Field(..., example="123e4567-e89b-12d3-a456-426614174000")
    monto: PositiveFloat = Field(..., example=25000.0)


# =========================
# Utilidades internas
# =========================
def _generar_numero_cuenta() -> str:
    """Genera números de cuenta únicos"""
    import random
    import string

    return "ACC" + "".join(random.choices(string.digits, k=7))


# =========================
# Funciones de negocio: CLIENTES
# =========================
async def listar_clientes() -> List[Cliente]:
    async with get_db() as conn:
        rows = await conn.fetch(
            """
            SELECT id_cliente as id, nombre_completo, documento, fecha_creacion, fecha_edicion
            FROM banco.cliente
            ORDER BY fecha_creacion DESC
        """
        )
        return [Cliente(**dict(row)) for row in rows]


async def obtener_cliente(cliente_id: UUID) -> Optional[Cliente]:
    async with get_db() as conn:
        row = await conn.fetchrow(
            """
            SELECT id_cliente as id, nombre_completo, documento, fecha_creacion, fecha_edicion
            FROM banco.cliente
            WHERE id_cliente = $1
        """,
            cliente_id,
        )
        return Cliente(**dict(row)) if row else None


async def crear_cliente(payload: ClienteCreate) -> Cliente:
    async with get_db() as conn:
        # Verificar documento único
        exists = await conn.fetchval(
            """
            SELECT EXISTS(SELECT 1 FROM banco.cliente WHERE documento = $1)
        """,
            payload.documento,
        )

        if exists:
            raise ValueError("Documento ya registrado")

        row = await conn.fetchrow(
            """
            INSERT INTO banco.cliente (nombre_completo, documento)
            VALUES ($1, $2)
            RETURNING id_cliente as id, nombre_completo, documento, fecha_creacion, fecha_edicion
        """,
            payload.nombre_completo,
            payload.documento,
        )

        return Cliente(**dict(row))


async def actualizar_cliente(cliente_id: UUID, payload: ClienteCreate) -> Cliente:
    async with get_db() as conn:
        # Verificar que existe
        exists = await conn.fetchval(
            """
            SELECT EXISTS(SELECT 1 FROM banco.cliente WHERE id_cliente = $1)
        """,
            cliente_id,
        )

        if not exists:
            raise KeyError("Cliente no encontrado")

        # Verificar documento único (excepto el mismo cliente)
        doc_exists = await conn.fetchval(
            """
            SELECT EXISTS(SELECT 1 FROM banco.cliente WHERE documento = $1 AND id_cliente != $2)
        """,
            payload.documento,
            cliente_id,
        )

        if doc_exists:
            raise ValueError("Documento ya registrado por otro cliente")

        row = await conn.fetchrow(
            """
            UPDATE banco.cliente 
            SET nombre_completo = $2, documento = $3, fecha_edicion = NOW()
            WHERE id_cliente = $1
            RETURNING id_cliente as id, nombre_completo, documento, fecha_creacion, fecha_edicion
        """,
            cliente_id,
            payload.nombre_completo,
            payload.documento,
        )

        return Cliente(**dict(row))


async def eliminar_cliente(cliente_id: UUID) -> None:
    async with get_db() as conn:
        # Verificar que existe
        exists = await conn.fetchval(
            """
            SELECT EXISTS(SELECT 1 FROM banco.cliente WHERE id_cliente = $1)
        """,
            cliente_id,
        )

        if not exists:
            raise KeyError("Cliente no encontrado")

        # Verificar que no tiene cuentas
        has_accounts = await conn.fetchval(
            """
            SELECT EXISTS(SELECT 1 FROM banco.cuenta WHERE id_cliente = $1)
        """,
            cliente_id,
        )

        if has_accounts:
            raise RuntimeError("Cliente con cuentas activas")

        await conn.execute(
            """
            DELETE FROM banco.cliente WHERE id_cliente = $1
        """,
            cliente_id,
        )


# =========================
# Funciones de negocio: CUENTAS
# =========================
async def listar_cuentas(
    cliente_id: Optional[UUID] = None, tipo: Optional[str] = None
) -> List[Cuenta]:
    async with get_db() as conn:
        where_conditions = []
        params = []
        param_count = 0

        if cliente_id is not None:
            param_count += 1
            where_conditions.append(f"c.id_cliente = ${param_count}")
            params.append(cliente_id)

        if tipo is not None:
            param_count += 1
            where_conditions.append(f"tc.nombre = ${param_count}")
            params.append(tipo)

        where_clause = (
            "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
        )

        query = f"""
            SELECT c.id_cuenta as id, c.numero, c.id_cliente, c.id_tipo_cuenta, 
                   c.saldo, c.fecha_creacion, c.fecha_edicion
            FROM banco.cuenta c
            JOIN banco.tipo_cuenta tc ON c.id_tipo_cuenta = tc.id_tipo_cuenta
            {where_clause}
            ORDER BY c.fecha_creacion DESC
        """

        rows = await conn.fetch(query, *params)
        return [Cuenta(**dict(row)) for row in rows]


async def obtener_cuenta(cuenta_id: UUID) -> Optional[Cuenta]:
    async with get_db() as conn:
        row = await conn.fetchrow(
            """
            SELECT id_cuenta as id, numero, id_cliente, id_tipo_cuenta, 
                   saldo, fecha_creacion, fecha_edicion
            FROM banco.cuenta
            WHERE id_cuenta = $1
        """,
            cuenta_id,
        )
        return Cuenta(**dict(row)) if row else None


async def obtener_cuenta_por_numero(numero: str) -> Optional[Cuenta]:
    async with get_db() as conn:
        row = await conn.fetchrow(
            """
            SELECT id_cuenta as id, numero, id_cliente, id_tipo_cuenta, 
                   saldo, fecha_creacion, fecha_edicion
            FROM banco.cuenta
            WHERE numero = $1
        """,
            numero,
        )
        return Cuenta(**dict(row)) if row else None


async def crear_cuenta(payload: CuentaCreate) -> Cuenta:
    async with get_db() as conn:
        # Verificar que cliente existe
        cliente_exists = await conn.fetchval(
            """
            SELECT EXISTS(SELECT 1 FROM banco.cliente WHERE id_cliente = $1)
        """,
            payload.id_cliente,
        )

        if not cliente_exists:
            raise KeyError("Cliente no existe")

        # Verificar que tipo cuenta existe
        tipo_exists = await conn.fetchval(
            """
            SELECT EXISTS(SELECT 1 FROM banco.tipo_cuenta WHERE id_tipo_cuenta = $1)
        """,
            payload.id_tipo_cuenta,
        )

        if not tipo_exists:
            raise KeyError("Tipo de cuenta no existe")

        numero = _generar_numero_cuenta()

        row = await conn.fetchrow(
            """
            INSERT INTO banco.cuenta (numero, id_cliente, id_tipo_cuenta, saldo)
            VALUES ($1, $2, $3, 0.0)
            RETURNING id_cuenta as id, numero, id_cliente, id_tipo_cuenta, 
                      saldo, fecha_creacion, fecha_edicion
        """,
            numero,
            payload.id_cliente,
            payload.id_tipo_cuenta,
        )

        return Cuenta(**dict(row))


async def eliminar_cuenta(cuenta_id: UUID) -> None:
    async with get_db() as conn:
        # Verificar que existe
        row = await conn.fetchrow(
            """
            SELECT saldo FROM banco.cuenta WHERE id_cuenta = $1
        """,
            cuenta_id,
        )

        if not row:
            raise KeyError("Cuenta no encontrada")

        if row["saldo"] != 0:
            raise RuntimeError(
                "No se puede eliminar una cuenta con saldo distinto de 0"
            )

        await conn.execute(
            """
            DELETE FROM banco.cuenta WHERE id_cuenta = $1
        """,
            cuenta_id,
        )


# =========================
# Funciones de negocio: TRANSACCIONES
# =========================
async def listar_transacciones(
    cuenta_id: Optional[UUID] = None,
    desde: Optional[date] = None,
    hasta: Optional[date] = None,
) -> List[Transaccion]:
    async with get_db() as conn:
        where_conditions = []
        params = []
        param_count = 0

        if cuenta_id is not None:
            param_count += 1
            where_conditions.append(
                f"(id_cuenta_origen = ${param_count} OR id_cuenta_destino = ${param_count})"
            )
            params.append(cuenta_id)

        if desde is not None:
            param_count += 1
            where_conditions.append(f"momento::date >= ${param_count}")
            params.append(desde)

        if hasta is not None:
            param_count += 1
            where_conditions.append(f"momento::date <= ${param_count}")
            params.append(hasta)

        where_clause = (
            "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
        )

        query = f"""
            SELECT id_transaccion as id, tipo, id_cuenta_origen, id_cuenta_destino,
                   monto, momento, fecha_creacion, fecha_edicion
            FROM banco.transaccion
            {where_clause}
            ORDER BY momento DESC
        """

        rows = await conn.fetch(query, *params)
        return [Transaccion(**dict(row)) for row in rows]


async def obtener_transaccion(tx_id: UUID) -> Optional[Transaccion]:
    async with get_db() as conn:
        row = await conn.fetchrow(
            """
            SELECT id_transaccion as id, tipo, id_cuenta_origen, id_cuenta_destino,
                   monto, momento, fecha_creacion, fecha_edicion
            FROM banco.transaccion
            WHERE id_transaccion = $1
        """,
            tx_id,
        )
        return Transaccion(**dict(row)) if row else None


async def eliminar_transaccion(tx_id: UUID) -> None:
    async with get_db() as conn:
        # Verificar que existe
        exists = await conn.fetchval(
            """
            SELECT EXISTS(SELECT 1 FROM banco.transaccion WHERE id_transaccion = $1)
        """,
            tx_id,
        )

        if not exists:
            raise KeyError("Transacción no encontrada")

        await conn.execute(
            """
            DELETE FROM banco.transaccion WHERE id_transaccion = $1
        """,
            tx_id,
        )


async def depositar(cuenta_id: UUID, monto: float) -> Transaccion:
    async with get_db() as conn:
        # Verificar que cuenta existe
        cuenta_exists = await conn.fetchval(
            """
            SELECT EXISTS(SELECT 1 FROM banco.cuenta WHERE id_cuenta = $1)
        """,
            cuenta_id,
        )

        if not cuenta_exists:
            raise KeyError("Cuenta no encontrada")

        # Actualizar saldo
        await conn.execute(
            """
            UPDATE banco.cuenta SET saldo = saldo + $2 WHERE id_cuenta = $1
        """,
            cuenta_id,
            monto,
        )

        # Registrar transacción
        row = await conn.fetchrow(
            """
            INSERT INTO banco.transaccion (tipo, id_cuenta_destino, monto)
            VALUES ($1, $2, $3)
            RETURNING id_transaccion as id, tipo, id_cuenta_origen, id_cuenta_destino,
                      monto, momento, fecha_creacion, fecha_edicion
        """,
            TransaccionTipo.DEPOSITO.value,
            cuenta_id,
            monto,
        )

        return Transaccion(**dict(row))


async def retirar(cuenta_id: UUID, monto: float) -> Transaccion:
    async with get_db() as conn:
        # Verificar saldo suficiente
        saldo_actual = await conn.fetchval(
            """
            SELECT saldo FROM banco.cuenta WHERE id_cuenta = $1
        """,
            cuenta_id,
        )

        if saldo_actual is None:
            raise KeyError("Cuenta no encontrada")

        if saldo_actual < monto:
            raise RuntimeError("Fondos insuficientes")

        # Actualizar saldo
        await conn.execute(
            """
            UPDATE banco.cuenta SET saldo = saldo - $2 WHERE id_cuenta = $1
        """,
            cuenta_id,
            monto,
        )

        # Registrar transacción
        row = await conn.fetchrow(
            """
            INSERT INTO banco.transaccion (tipo, id_cuenta_origen, monto)
            VALUES ($1, $2, $3)
            RETURNING id_transaccion as id, tipo, id_cuenta_origen, id_cuenta_destino,
                      monto, momento, fecha_creacion, fecha_edicion
        """,
            TransaccionTipo.RETIRO.value,
            cuenta_id,
            monto,
        )

        return Transaccion(**dict(row))


async def transferir(
    cuenta_origen_id: UUID, cuenta_destino_id: UUID, monto: float
) -> Transaccion:
    async with get_db() as conn:
        if cuenta_origen_id == cuenta_destino_id:
            raise ValueError("La cuenta de origen y destino deben ser distintas")

        # Verificar saldo suficiente en cuenta origen
        saldo_origen = await conn.fetchval(
            """
            SELECT saldo FROM banco.cuenta WHERE id_cuenta = $1
        """,
            cuenta_origen_id,
        )

        if saldo_origen is None:
            raise KeyError("Cuenta origen no encontrada")

        # Verificar que cuenta destino existe
        destino_exists = await conn.fetchval(
            """
            SELECT EXISTS(SELECT 1 FROM banco.cuenta WHERE id_cuenta = $1)
        """,
            cuenta_destino_id,
        )

        if not destino_exists:
            raise KeyError("Cuenta destino no encontrada")

        if saldo_origen < monto:
            raise RuntimeError("Fondos insuficientes")

        # Realizar transferencia (transacción)
        async with conn.transaction():
            # Debitar cuenta origen
            await conn.execute(
                """
                UPDATE banco.cuenta SET saldo = saldo - $2 WHERE id_cuenta = $1
            """,
                cuenta_origen_id,
                monto,
            )

            # Acreditar cuenta destino
            await conn.execute(
                """
                UPDATE banco.cuenta SET saldo = saldo + $2 WHERE id_cuenta = $1
            """,
                cuenta_destino_id,
                monto,
            )

            # Registrar transacción
            row = await conn.fetchrow(
                """
                INSERT INTO banco.transaccion (tipo, id_cuenta_origen, id_cuenta_destino, monto)
                VALUES ($1, $2, $3, $4)
                RETURNING id_transaccion as id, tipo, id_cuenta_origen, id_cuenta_destino,
                          monto, momento, fecha_creacion, fecha_edicion
            """,
                TransaccionTipo.TRANSFERENCIA.value,
                cuenta_origen_id,
                cuenta_destino_id,
                monto,
            )

        return Transaccion(**dict(row))


# =========================
# Funciones auxiliares para tipos de cuenta
# =========================
async def listar_tipos_cuenta() -> List[TipoCuentaModel]:
    async with get_db() as conn:
        rows = await conn.fetch(
            """
            SELECT id_tipo_cuenta as id, nombre, descripcion
            FROM banco.tipo_cuenta
            ORDER BY nombre
        """
        )
        return [TipoCuentaModel(**dict(row)) for row in rows]


async def obtener_tipo_cuenta_por_nombre(nombre: str) -> Optional[TipoCuentaModel]:
    async with get_db() as conn:
        row = await conn.fetchrow(
            """
            SELECT id_tipo_cuenta as id, nombre, descripcion
            FROM banco.tipo_cuenta
            WHERE nombre = $1
        """,
            nombre,
        )
        return TipoCuentaModel(**dict(row)) if row else None
